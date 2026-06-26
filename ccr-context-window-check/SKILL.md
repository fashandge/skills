---
name: ccr-context-window-check
description: Check whether claude-code-router (ccr) is actually sending a 1M-token context window to the upstream provider. Use when the user asks if ccr/ccr uses "1m context", "context window 1m", whether long-context routing is active, or why a Claude Code session that thinks it's on a 1M-context model may not be getting 1M tokens through ccr. Diagnoses by decoding the real wire requests in ccr's logs and reading the ccr config — it does not trust model-name suffixes.
allowed-tools: Bash(grep:*), Bash(python3:*), Bash(cat:*), Bash(ls:*), Bash(sed:*), Bash(find:*), Bash(wc:*), Bash(readlink:*)
---

# ccr-context-window-check

Determine whether **claude-code-router (ccr)** actually transmits a 1,000,000-token context
window to the upstream LLM provider — by inspecting the **real request bodies** ccr forwards,
not by trusting model-name suffixes like `[1m]`.

## Why this skill exists

Claude Code may report a model ID like `claude-opus-4-8[1m]` (the `[1m]` = 1M context window
for the *Anthropic* model). But when requests go through ccr, ccr **rewrites** them: it maps the
Anthropic-model request onto whatever provider/model `config.json` routes to, and the `[1m]`
designation is **not** forwarded as a 1M parameter. The only token-limit parameter ccr typically
sends is `max_tokens` (an *output* cap, not an input context window), and it's usually far below
1M (e.g. 64000).

So the question "does ccr use 1m context?" has to be answered from the wire, because CC's own
model-ID suffix describes a window ccr discards during routing.

## How ccr decides context limits (ground truth from the v2.0.0 source)

Reproduce these by grepping ccr's installed `dist/cli.js`:

1. **`max_tokens` in the request body is the only token-limit ccr generally forwards.** In
   `convertAnthropic...` ccr builds `{messages, model, max_tokens, temperature, stream, tools...}`
   from the Anthropic request. There is **no** `context_length`/`context_window`/`max_input_tokens`
   field in that body. So `max_tokens` is an *output* cap, and the input context window is whatever
   the provider's model defaults to — ccr does not request a 1M input window.

2. **`[1m]` from CC is never parsed into a 1M parameter.** ccr has no code path that maps a
   `[1m]` model-name suffix to a `1000000` context-window field. (A grep for `\[1m\]` /
   `context_window_size` shows those strings only in *usage-display* / stats code, not in request
   construction.)

3. **`longContext` routing changes the *model*, not the window size.** ccr's router logic:
   `let a = i?.longContextThreshold || 6e4` (default 60000 tokens); if the prompt's
   `input_tokens > a` it switches the route to `config.Router.longContext`. Your `config.json`
   sets `longContext: "neuralwatt,glm-5.2"` — i.e. the **same** model as default — so even when
   long-context routing fires, it targets the same model and still sends no 1M parameter.

4. **`max_tokens` is sometimes *clamped down* by provider transformers**, never raised to 1M.
   e.g. the deepseek transformer caps `max_tokens` at 8192; the `maxtoken` plugin transformer can
   override it. Neither produces a 1M input window.

## Procedure

### 1. Find the config and the active provider/model

```bash
cat ~/.claude-code-router/config.json
```
Note `Router.default`, `Router.longContext`, `Router.longContextThreshold`, and each `Providers`
entry's `api_base_url` + `models`. This tells you *which model* requests are routed to.

### 2. Find the active log

ccr logs each session to `~/.claude-code-router/logs/ccr-<timestamp>.log`; the current/active
one is `~/.claude-code-router/logs/ccr.log`'s target or the **newest** `ccr-*.log` by mtime:

```bash
ls -t ~/.claude-code-router/logs/ccr-*.log | head -1
```

### 3. Confirm *no* 1M parameter is sent (cheap first pass)

A 1M figure can appear as **model output** (the model streaming the literal digits "1000000")
— that is a false positive. The decisive check is the request body's keys and the `max_tokens`
value. First, tally the token-limit fields actually present in request bodies:

```bash
f=$(ls -t ~/.claude-code-router/logs/ccr-*.log | head -1)
grep -aoE '"max_tokens":[0-9]+|"context_window_size":[0-9]+|"context_length":[0-9]+|"max_input_tokens":[0-9]+' "$f" | sort | uniq -c | sort -rn
```

### 4. Decode the actual outgoing request bodies (decisive)

Each request is a JSON log line whose `request.body` is a **JSON-encoded string** containing the
payload POSTed to the provider. Decode it and print the top-level keys + token params. This
prints up to 2 *main* chat requests (skips tiny 1-2 message background calls like title
generation):

```bash
python3 - <<'PY'
import json
f = sorted(__import__("glob").glob("/Users/jianfuchen/.claude-code-router/logs/ccr-*.log"),
          key=lambda p: __import__("os").path.getmtime(p))[-1]
seen = 0
with open(f) as fh:
    for ln in fh:
        if "chat/completions" not in ln:
            continue
        try: obj = json.loads(ln)
        except Exception: continue
        body = (obj.get("request") or {}).get("body")
        if not body: continue
        try: b = json.loads(body)
        except Exception: continue
        if "max_tokens" not in b: continue
        msgs = b.get("messages")
        if isinstance(msgs, list) and len(msgs) <= 2:   # skip title/convo-name generators
            continue
        print("reqId:", obj.get("reqId"))
        print("  TOP-LEVEL KEYS:", list(b.keys()))
        for k in ("model", "max_tokens", "context_length", "context_window",
                  "max_input_tokens", "stream", "temperature"):
            if k in b: print(f"    {k}:", b[k])
        seen += 1
        if seen >= 2: break
if not seen: print("no qualifying main request found in", f)
PY
```

### 5. Read the verdict

- **If `max_tokens` is far below 1,000,000 (e.g. 64000) and no `context_length`/
  `context_window`/`max_input_tokens` key exists** → **ccr is NOT sending a 1M context window.**
  The 1M window the CC session advertises (`[1m]`) is **not** transmitted; the upstream input
  context limit is whatever the routed model defaults to, and the output cap is the `max_tokens`
  value seen.
- **If `longContext` points to the same model as `default`** → long-context routing fires above
  `longContextThreshold` tokens but changes nothing about the window; it's a no-op for context
  size. Flag this to the user.
- **Only if a `context_length`/`context_window` = 1000000 appears in the decoded body** → 1M is
  genuinely being requested. (Not observed on a v2.0.0 + `glm-5.2` setup.)

### What "no 1M parameter sent" actually means here (measured)

This is the subtle and important part — "ccr does not send a 1M context-window parameter" does
**not** mean the session lacks a ~1M-class window. Separately measured (see the empirical section
below): the routed model `glm-5.2` has a **hard 1,048,576-token (2²⁰) context window of its own**,
so CC's `[1m]` designation is effectively backed by reality even though ccr never transmits a
`1m` field. The **practical** synchronous ceiling through `api.neuralwatt.com` is lower (~705K)
because of a Cloudflare ~125s edge timeout during prefill — but the model would accept up to the
full 1,048,480 safe prompt-token input. So in the answer, distinguish:
- **"ccr sends 1M as a parameter?"** → **No** (only `max_tokens: 64000`, an output cap).
- **"is the session actually on a 1M-class model?"** → **Yes** (`glm-5.2`'s native window is
  1,048,576); usable synchronously up to ~705K; hard-rejected only above 1,048,480.

### 6. Reconcile with what Claude Code reports (the trap to call out)

CC's own model ID (e.g. `claude-opus-4-8[1m]`) describes the window *CC thinks* it has against
the Anthropic API. Through ccr that request is **rewritten** onto the provider's model (e.g.
`glm-5.2`) with `model` set to that provider model and the `[1m]` suffix dropped. So CC "being on
1M" and "ccr sending 1M" are different things — say so explicitly in the answer.

## Empirically testing the real context window (measured, 2026-06-24)

Probes POSTed straight to the provider/model ccr routes to (`neuralwatt` → `glm-5.2`,
served as `zai-org/GLM-5.2-FP8`) — the same path the Claude Code session uses. Build a
chat-completions payload with a unique needle buried near the end, ask the model to echo it,
and read the `usage.prompt_tokens` the provider returns. Script:

```bash
python3 - <<'PY'
import json, random, string
rng = random.Random(42)
def words(n): return ' '.join(''.join(rng.choice(string.ascii_letters+string.digits)
                            for _ in range(rng.randint(3,9))) for _ in range(n))
needle="ZEBRA-NEEDLE-9F3C2A"
target_chars = 1_050_000          # tune; ~3.78 chars/token at ~265K tok, ~1.51 at ~2.3M (see below)
big=[]; total=0
while total < target_chars:
    b=words(1400); big.append(b); total+=len(b)+1
big[-1]=big[-1]+(f" \n\n>>> RECALL_MARKER: token={needle}. <<<\n")
ptext=" ".join(big)
body={"model":"glm-5.2","messages":[{"role":"system","content":"recall test"},
    {"role":"user","content":ptext+"\n\nQUESTION: state the token after 'token=' in the RECALL_MARKER. ONLY the token."}],
    "max_tokens":32,"temperature":0}
json.dump(body, open("/tmp/probe.json","w"))
print(f"chars={len(ptext):,}")
PY
source ~/.config/secrets.env   # NEURALWATT_API_KEY
curl -sS -X POST "https://api.neuralwatt.com/v1/chat/completions" \
  -H "Authorization: Bearer $NEURALWATT_API_KEY" -H "Content-Type: application/json" \
  --data @/tmp/probe.json --max-time 540 -o /tmp/probe_resp.json -w "http=%{http_code} time=%{time_total}s\n"
grep -oE '"prompt_tokens":[0-9]+|"context_limit":[0-9]+|"content":"[^"]*"|"reasoning":"[^"]*"' /tmp/probe_resp.json | head
```

### Two limits found — only one is the "context size"

1. **Hard model context window = 1,048,576 tokens (exactly 2²⁰ = 1 MiB·tokens).** Oversized
   probes get HTTP 400 with a body stating `context_limit: 1048576`,
   `safe_max_prompt_tokens: 1048480`. So `glm-5.2` *is* a genuine 1M-context model — the
   `[1m]` Claude Code advertises is backed by reality at the model level.

2. **Practical single-request ceiling through `api.neuralwatt.com` ≈ 705K prompt tokens.**
   Every probe above ~715K prompt tokens fails with **Cloudflare HTTP 524 at exactly ~125s**,
   even with `stream: true`. The edge has a ~100–125s origin-response timeout, and prefill of
   a >715K-token prompt runs longer than that — the 524 fires *before* any byte (incl. the
   first streamed token) is returned. So roughly the top ~340K tokens of the 1M window are
   **unusable for synchronous requests** through this provider's edge, not because the model
   rejects them but because the gateway times out during prefill.

### Confirmed working points (all needle-recalled correctly)

| Prompt tokens (provider-measured) | Result |
|---|---|
| ~702K | ✅ HTTP 200, ~111s, needle recalled in the model's `reasoning` field |
| ~715K–1.04M | ❌ HTTP 524 at ~125s (edge prefill timeout; streaming doesn't help) |
| >1.048M | ❌ HTTP 400 `context_length_exceeded` (the 1M hard cap) |

### Token-size estimation gotcha

**Do NOT estimate prompt tokens by a fixed chars/token ratio.** Same low-redundancy alphanumeric
filler measured at **3.78 chars/tok** for a ~1.06M-char payload (702K tokens) but **1.51 chars/tok**
for a ~3.5M-char payload (2.33M tokens) — the GLM tokenizer compresses large repeated structures
non-linearly, so the ratio shifts with size. **Only the provider's returned `usage.prompt_tokens`
is a trustworthy size signal.** When binary-searching for the 524 boundary, step the *payload size*
and use the 400-rejection's `prompt_tokens` (on an oversized probe) as the authoritative count,
then size down from there; char-ratio extrapolation will mislead you.

### Other limits to note

- **Output cap: `max_tokens` ≤ 64000** in what ccr forwards (set by the request body ccr
  constructs; see step 4). The input window is separate and far larger (~705K usable / 1M hard).
- **glm-5.2 reasoning is emitted in a separate `"reasoning"` field**, not `"content"` — when
  checking recall, grep both fields. A probe that "worked" may show `content: null` with the
  answer living in `reasoning` until `max_tokens` cuts it off.

## Reference (paths on this machine)

- ccr config: `~/.claude-code-router/config.json`
- ccr logs dir: `~/.claude-code-router/logs/` (active = newest `ccr-*.log`)
- ccr package source: `~/.hermes/node/lib/node_modules/@musistudio/claude-code-router/dist/cli.js`
  (v2.0.0; `bin: ccr`)
- ccr version: `cat .../claude-code-router/package.json | python3 -c "import sys,json;print(json.load(sys.stdin)['version'])"`

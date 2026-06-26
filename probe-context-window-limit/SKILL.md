---
name: probe-context-window-limit
description: Empirically measure the actual reachable context-window limit of an LLM provider/model by sending live needle-in-haystack recall probes — not trusting advertised window sizes. Use when the user asks "what's the context window limit", "how big a context can I send", "can I use N tokens / 1M / 300K", "does the 1M window actually work", "test max context", or wants to binary-search the real ceiling. Complements [[ccr-context-window-check]] (which statically inspects config/logs); use this one when you need the measured number.
allowed-tools: Bash(python3:*), Bash(curl:*), Bash(grep:*), Bash(head:*), Bash(wc:*), Bash(ls:*), Bash(rm:*), Bash(mktemp:*)
---

# probe-context-window-limit

Empirically find the **actual reachable** context-window limit of a provider/model — by sending
real prompts the model has to read back — instead of trusting the advertised window size.

This is the dynamic counterpart to [[ccr-context-window-check]]. That skill answers *"is ccr
configured/sending a 1M parameter?"* by reading config and logs. This one answers *"what's the
real limit I can actually use?"* by probing the live endpoint.

## A model has THREE limits — do not conflate them

1. **Advertised window** (model card, or a `[1m]` suffix on a model ID). The vendor's claim.
   Necessary to know, **never sufficient to trust**.
2. **Hard model cap.** The model rejects inputs above this with HTTP 400
   `context_length_exceeded`; the error body states the exact `context_limit` and
   `safe_max_prompt_tokens`. This is the *true* model window.
3. **Practical synchronous ceiling.** The largest input that returns HTTP **200** through the
   provider's edge/gateway. Frequently **lower than the hard cap** — large-prompt *prefill*
   exceeds a gateway timeout (Cloudflare **HTTP 524** / 504) before the model emits a byte. The
   top slice of the advertised window is thus unreachable synchronously.

The job of this skill is to find #2 and #3. They are different numbers.

## Procedure

### Phase 0 — the probe payload

A chat-completions request: **low-redundancy alphanumeric filler** (random letters+digits, *not*
repeated words — a tokenizer collapses repetition and you'll mis-size) plus a **unique needle
buried near the end**, then a question asking the model to echo the needle. If the model returns
the needle, it actually ingested the whole prompt (cheap recall test).

### Phase 1 — find the hard cap cheaply (one oversized request)

Send a deliberately-too-big probe (e.g. ~4M chars). Expect **HTTP 400** with a body like:
```json
{"error":{"message":"...maximum context length is 1048576 tokens. Your request requires at least 2328200 tokens...","code":"context_length_exceeded","prompt_tokens":2328104,"context_limit":1048576,"safe_max_prompt_tokens":1048480}}
```
This single failed request gives you: the **hard cap** (`context_limit`), the safe input max
(`safe_max_prompt_tokens`), **and** the real token count of your probe payload (`prompt_tokens`).
Do not assume the advertised window — read these.

### Phase 2 — binary-search the practical ceiling

Working down from just under the hard cap, find the largest size that returns **HTTP 200** (not
524). Each step: size the payload → POST → time it → classify:

| Response | Meaning | Next step |
|---|---|---|
| **200** + `usage.prompt_tokens` + needle recalled | worked at this size | go bigger |
| **524** / 504 (gateway/origin timeout) | edge timed out during **prefill** | go smaller |
| **400** `context_length_exceeded` | over hard cap (Phase 1) | go smaller |
| **200** but needle NOT recalled | window "held" but model didn't read — treat as failure | investigate (truncation, needle position) |

The exact token count of every 200 comes free from `usage.prompt_tokens`; the 400's
`prompt_tokens` counts the oversized one. **A 524 gives no token count** — its only signal is
"too big to prefill in time"; bracket it with a 200 below and a 524 above.

### Phase 3 — verify recall on every 200

Confirm the model actually returned the needle. Check **both** `content` **and** `reasoning`
fields — some models (e.g. `glm-5.2`) emit chain-of-thought in a separate `reasoning` field and
leave `content` null. If `max_tokens` is tiny the answer may be cut off mid-emit; raise
`max_tokens` and retest.

## Workhorse probe script

Drops a parametrized probe to any OpenAI-compatible `/chat/completions` endpoint. It sizes by
**chars** (not tokens — see gotcha), sends, and prints `http_code`, wall-time, provider-measured
`prompt_tokens`, and whether the needle was recalled.

```bash
python3 - "$@" <<'PY'
import argparse, json, random, string, os, sys, time, urllib.request, urllib.error
ap = argparse.ArgumentParser()
ap.add_argument("--endpoint", required=True)
ap.add_argument("--model",   required=True)
ap.add_argument("--key-env", required=True, help="env var holding the API key")
ap.add_argument("--chars",   type=int, required=True, help="approx payload char size")
ap.add_argument("--max-tokens", type=int, default=32)
ap.add_argument("--timeout", type=int, default=540)
a = ap.parse_args()
key = os.environ.get(a.key_env)
if not key: sys.exit(f"key env var {a.key_env} not set")
needle = f"ZEBRA-NEEDLE-{random.Random().randint(100000,999999)}"
rng = random.Random(4242)
def words(n): return ' '.join(''.join(rng.choice(string.ascii_letters+string.digits) for _ in range(rng.randint(3,9))) for _ in range(n))
big, total = [], 0
while total < a.chars:
    b = words(1400); big.append(b); total += len(b)+1
big[-1] += f" \n\n>>> RECALL_MARKER: token={needle}. Answer the user's question with exactly this token. <<<\n"
ptext = " ".join(big)
body = {"model":a.model,"messages":[
    {"role":"system","content":"recall test"},
    {"role":"user","content":ptext+"\n\nQUESTION: state the token after 'token=' in the RECALL_MARKER. Reply with ONLY that token, nothing else."}],
    "max_tokens":a.max_tokens,"temperature":0}
data = json.dumps(body).encode()
req = urllib.request.Request(a.endpoint, data=data,
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=a.timeout) as r:
        resp, code = r.read().decode(), r.status
except urllib.error.HTTPError as e:
    resp, code = e.read().decode(), e.code
except Exception as e:
    print(f"http=ERR time={time.time()-t0:.1f}s error={e}"); sys.exit(0)
dt = time.time()-t0
try: o = json.loads(resp)
except Exception: print(f"http={code} time={dt:.1f}s nonjson={resp[:200]}"); sys.exit(0)
if "error" in o:
    e = o["error"]; print(f"http={code} time={dt:.1f}s ERROR: {e.get('message','')[:300]}")
    for k in ("prompt_tokens","context_limit","safe_max_prompt_tokens"):
        if k in e: print(f"  {k}: {e[k]:,}")
    sys.exit(0)
u = o.get("usage",{}); pt = u.get("prompt_tokens")
found = False
for ch in o.get("choices",[]):
    msg = ch.get("message",{})
    for f in ("content","reasoning"):
        if isinstance(msg.get(f),str) and needle in msg[f]: found = True
print(f"http={code} time={dt:.1f}s prompt_tokens={pt:,} needle_recalled={found} needle={needle}")
for ch in o.get("choices",[]):
    msg = ch.get("message",{})
    for f in ("content","reasoning"):
        v = msg.get(f)
        if isinstance(v,str) and v: print(f"  {f}: {v[:200]}")
PY
```

Example invocation (this machine, ccr's provider):
```bash
source ~/.config/secrets.env   # sets NEURALWATT_API_KEY
python3 /tmp/probe.py --endpoint https://api.neuralwatt.com/v1/chat/completions \
  --model glm-5.2 --key-env NEURALWATT_API_KEY --chars 1050000 --max-tokens 96
```

## Gotchas (all hard-won from a 2026-06-24 probing session)

- **Char/token ratio is non-linear — do NOT estimate prompt tokens by a fixed ratio.** The same
  low-redundancy filler measured **3.78 chars/token** at 702K tokens but **1.51 chars/token** at
  2.33M tokens. Scaling a ratio up/down mis-sizes wildly. **Size by stepping `--chars` and read
  the provider's `prompt_tokens`** from each response (200 or 400) to see the real count; use
  Phase 1's oversized probe to get an initial anchor, then iterate.

- **Streaming (`stream:true`) does NOT bypass a prefill-timeout 524.** The 524 fires *before any
  byte is sent* (including the first streamed token) because the gateway's origin-response timer
  expires during prefill. Don't reach for streaming to fix a 524 — it can't.

- **A 524 is a *timeout*, not a *size rejection*.** It fires at the **same wall-clock** for every
  over-threshold size (~125s here), independent of how far over. Distinguish: 400 = model says no
  (size); 524/504 = gateway gave up (latency). A 524's practical ceiling is usually far below the
  hard cap and is the *real* limiting number for synchronous use.

- **`max_tokens` is the OUTPUT cap, separate from the input window.** A 1M *input* window does
  not imply 1M output. ccr forwards `max_tokens` (e.g. 64000) and that bounds each reply, not the
  context you can feed in. If a task needs huge *output*, that has its own ceiling to probe.

- **Some models put reasoning in a separate field.** `glm-5.2` emits chain-of-thought in
  `reasoning`, leaving `content` null — grep both when checking recall, or you'll falsely report
  failure on a probe that actually worked.

- **Test direct-to-provider, not through the router, for measurement.** For ccr specifically:
  direct-to-provider is equivalent to through-ccr for *input size* because ccr forwards input
  without truncation/cap (wire-confirmed — see [[ccr-context-window-check]]). Going direct gives
  clean `usage.prompt_tokens` and precise `max_tokens` control that the Anthropic-format
  translation through ccr would muddy. The only through-ccr difference is the 64000 output cap.

- **A 429 "uncached/cold-prefill" limit is a *cumulative* rate limit, not a per-request size cap —
  and it can preempt the slow 524.** neuralwatt/glm-5.2 returns **HTTP 429 in ~5s** with body
  `"Uncached token rate limit exceeded ... Cold-prefill tokens: <N>, Limit: 1000000"` when
  **cumulative** cold-prefill demand in a window exceeds 1,000,000 tokens (re-verified
  2026-06-24). It is NOT per-request: firing a ~745K probe right after a ~722K probe 429'd in 5s;
  firing the same ~745K probe into fresh quota ~2min later proceeded to a normal **524 at ~125s**.
  So which over-ceiling failure you hit depends on quota state: fast 429 when cold/cumulative,
  slow 524 when fresh. Either way the practical ceiling is unchanged (here ~720K); the 429 just
  makes failure arrive faster and cheaper when you've been hammering the endpoint. Classify it as
  a third edge failure mode alongside 524/400.

- **"200 but needle not recalled" at the very top of the window — don't trust recall within ~20K
  tokens of the ceiling.** At exactly 721,841 prompt tokens (just under the ~720–725K edge),
  glm-5.2 returned HTTP 200 in 122s but emitted **degenerate CoT** (`1.2.3.4.5...` counting) and
  never surfaced the needle (re-verified 2026-06-24). This was not a `max_tokens` cutoff — the
  same `max_tokens=512` recalled cleanly on a small payload. The model ingested the size (HTTP
  200 + correct prompt_tokens) but mis-reasoned on a near-saturated context. Treat the recall-
  verified ceiling as ~5–20K *below* the HTTP-200 ceiling; a bare 200 near the top is necessary
  but not sufficient — always check the needle.

## This machine — ccr / neuralwatt / glm-5.2 (measured 2026-06-24)

- **Endpoint:** `https://api.neuralwatt.com/v1/chat/completions` (OpenAI format)
- **Model id:** `glm-5.2` (served as `zai-org/GLM-5.2-FP8`, vLLM)
- **Key:** `$NEURALWATT_API_KEY` in `~/.config/secrets.env` — `source` it first
- **Hard cap (#2):** `1,048,576` tokens (exactly 2²⁰ = 1 MiB·tokens). `safe_max_prompt_tokens`
  `1,048,480`. So `glm-5.2` *is* a genuine 1M-context model — the `[1m]` label is real at model
  level.
- **Practical synchronous ceiling (#3):** **~705K prompt tokens** for *reliable recall*; ~720K
  for a bare HTTP 200. Above ~720K the provider's Cloudflare edge returns **HTTP 524 at ~125s**
  when quota is fresh (prefill exceeds the origin-response timeout; streaming does not help), or a
  fast **HTTP 429 in ~5s** when cumulative cold-prefill demand in the window has already exceeded
  1,000,000 tokens. Measured points (initial + re-verified 2026-06-24):
  - ✅ 702K → HTTP 200 in 111s, needle recalled
  - ⚠️ 722K → HTTP 200 in 122s, **needle NOT recalled** (degenerate CoT) — top of window is fuzzy
  - ❌ 745K into fresh quota → HTTP 524 at ~125s (re-verified 2026-06-24)
  - ❌ 745K into cold/cumulative quota → HTTP 429 in ~5s, `Cold-prefill Limit: 1,000,000`
  - ❌ 720K / 790K / 880K / 950K → HTTP 524 at ~125s (initial session)
- **Output cap:** `max_tokens` ≤ 64000 (what ccr forwards).
- **So in this session the reachable context is ~700K, not 1M** — the top ~340K tokens of the
  window are unreachable synchronously through the edge. To actually use 900K+ in one shot you'd
  need a different `glm-5.2` provider/endpoint lacking the ~125s edge cap, or chunked context.

## This machine — routatic-proxy / opencode-go / glm-5.2 (measured 2026-06-25)

A second `glm-5.2` path on this machine, and the one that **does** reach ~900K+. routatic-proxy is
a local OpenAI/Anthropic-compatible router (`~/.config/routatic-proxy/config.json`, symlinked from
dotfiles) that forwards to opencode-go's `https://opencode.ai/zen/go/v1/chat/completions`. It is
the transport Claude Code itself runs through on this box.

- **Endpoint (inbound):** `http://127.0.0.1:3943/v1/messages` — **Anthropic Messages format**, not
  OpenAI chat-completions. Send `x-api-key`/`Authorization: Bearer`, `anthropic-version:
  2023-06-01`; usage comes back as `input_tokens`/`output_tokens`. The OpenAI workhorse script
  above does NOT apply as-is — write an Anthropic-format probe (system + one user message, bury the
  needle, check both `text` and `thinking` content blocks for recall).
- **Model id:** `glm-5.2` (config alias → `{provider: opencode-go, model_id: glm-5.2}`;
  `respect_requested_model: true`, so it honors whatever model you send rather than remapping).
- **Key:** `$ROUTATIC_PROXY_API_KEY` (in `~/.config/secrets.env`).
- **Upstream timeout:** `opencode_go.timeout_ms = 300000` (300s) — **this is the key difference
  from ccr/neuralwatt.** neuralwatt's Cloudflare edge 524s at ~125s during prefill, capping it at
  ~720K; opencode-go's 300s timeout lets the longer prefill that 900K+ requires actually finish.
  No 524/504/timeout occurred at any size tested here.
- **Hard cap (#2):** router `context_window: 1000000`. The capacity filter gates on
  `estimated_input_tokens + max_tokens ≤ context_window`, so eligible input ≈ 1,000,000 −
  `max_tokens`. Overshoot it and the proxy rejects **pre-forward** with HTTP 500
  `"routing failed"` / `"no eligible model for request capacity"` (fast, ~0.7s, never hits the
  upstream) — *not* the model's own 400 `context_length_exceeded`.
- **Practical synchronous ceiling (#3):** **~982K input tokens with reliable recall.** Measured
  points (2026-06-25):
  - ✅ 598K → HTTP 200 in 110s, needle recalled
  - ✅ 898K → HTTP 200 in 265s, needle recalled
  - ✅ 963K → HTTP 200 in 39s, needle recalled
  - ✅ 982K → HTTP 200 in 100s, needle recalled
  - ❌ 1.49M chars (estimate > cap) → HTTP 500 router reject in 0.7s
- **Latency is volatile, not a size cliff:** 39s–265s for sizes in the same band — upstream
  load/cache warmth, not a ceiling signal. Don't read a slow 200 as "near the edge" here (unlike
  ccr, where ~125s ≈ the 524 wall).
- **Output cap:** `max_tokens` up to 131072 configured for the `glm-5.2` alias (probes used 8192).
- **Char/token ratio ≈ 1.5 chars/token** at ~900K for the same random-alnum filler that measured
  3.78 chars/token on neuralwatt — confirms the ratio is provider/tokenizer-specific, not fixed.
  Size by stepping `--chars` and reading the response `input_tokens`, never by a ratio.
- **Capacity filter rejects tiny `max_tokens`:** a probe with `max_tokens=64` was rejected as
  `"no eligible model for request capacity"` even at 2K chars. Use `max_tokens` ≥ ~8192. (The live
  Claude Code traffic the proxy was simultaneously serving used `max_tokens=32000`.)
- **So through routatic-proxy/opencode-go the reachable context is ~980K, not ~700K** — 900K is
  comfortably usable with recall, and this is the path to pick when a single shot needs >720K.

## Related skills

- [[ccr-context-window-check]] — static check of whether ccr *sends* a 1M parameter (reads
  `~/.claude-code-router/config.json` and decodes wire request bodies in the logs). Run that first
  to understand what the router is configured to do; run *this* skill to measure what actually
  reaches the model and comes back.

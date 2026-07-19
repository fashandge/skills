---
name: codex-first
description: "Route implementation work to Codex CLI only from Anthropic Claude Code sessions running Opus or Fable; keep Sonnet, Haiku, and non-Anthropic sessions local. Claude specs, reviews, verifies."
---

# Codex First

Claude Code sessions only. Codex/other harnesses: skip; never self-delegate.

Opus/Fable models only. If the session runs Sonnet, Haiku, an unknown Claude model, or a non-Anthropic model (e.g. GLM 5.2, Meta muse-spark): skip this skill entirely and implement directly. The economics below don't apply, and the routing assumptions (Claude ergonomics vs Codex generation) are calibrated to Opus/Fable models.

Detecting an eligible session (check before first delegation, once per session):

1. Model name — read "You are powered by the model named ..." in the system prompt. Only a model whose normalized name contains `claude-opus` or `claude-fable` is eligible. `claude-sonnet-*`, `claude-haiku-*`, unknown Claude models, and non-`claude-*` names → skip. This is a hard gate; `CODEX_FIRST=1` does not override it. Not sufficient alone: wrappers can spoof Claude model ids.
2. Env check for an eligible model (authoritative; run in Bash):
   ```bash
   echo "CODEX_FIRST=${CODEX_FIRST:-unset} ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-unset}"
   ```
   - `CODEX_FIRST=0` → skip (explicit off — set by claude-go / claude-meta / ccr wrappers).
   - `CODEX_FIRST=1` → use the skill, provided the model gate passed (explicit on, overrides base-URL inference — e.g. an Anthropic-compatible gateway serving Opus/Fable).
   - unset → infer from `ANTHROPIC_BASE_URL`: unset or `*.anthropic.com` → use the skill; anything else (localhost proxy, api.meta.ai, ccr router) → skip.

Rationale: Claude (Fable/Opus) tokens metered + expensive; Codex flat-rate. The skill defaults Codex to `gpt-5.6-terra` at extra-high reasoning for writing/implementing code (override with `--model`); Claude wins at ergonomics — judgment, design, spec-writing, review, orchestration. So Codex types, Claude thinks and verifies.

## Route

When the Opus/Fable model gate above passes, delegate proper hands-on implementation work to Codex:

- implementation from a frozen spec; refactors; mechanical migrations
- bug fixes with known repro; test writing; coverage fills
- CI fixes, dependency bumps, scripts/tooling
- bulk codebase exploration where raw reading ≫ the answer

Keep in Claude:

- all work when running Sonnet, Haiku, an unknown Claude model, or a non-Anthropic model
- design, API design, architecture, naming, UX judgment
- tasks where writing the spec IS the work (ambiguity = design)
- tiny edits (~<20 lines, single obvious change) — delegation overhead loses
- anything needing session tools: MCP (browser/computer-use/chronicle), 1Password, secrets
- destructive/irreversible ops, releases, pushes, GitHub mutations — Claude-side per git rules
- review of Codex output — never delegated, never skipped

Mixed task: Claude designs first, freezes spec, delegates build-out.
Heuristic: prompt reads as a work order → delegate; writing it forces decisions → design, Claude.
Portfolio/multi-repo work: `$maintainer-orchestrator` instead.

`codex exec` vs `/handoff-agent` — both put Codex to work; the axis is NOT complexity, it is what the run needs. Stay on `codex exec` whenever the task is spec-freezable up front (fire → read `-o` → review), even a large one — it is cheaper (no doorbell/lease/protocol tokens). Escalate to `/handoff-agent` only when the run needs a quality a headless one-shot cannot give: mid-run **steering** or answering the worker's blocking questions; **durability** across your own compaction/session (a long-lived worker you check on over many turns); a **remote box** (SSH) or a separate Codex app task; or **fan-out** of several monitored workers. So simple-but-remote → handoff-agent; complex-but-frozen-spec → codex exec. Do not auto-escalate on size alone.

## Invoke

Prompt via temp file, never inline quoting:

```bash
P=$(mktemp); cat >"$P" <<'EOF'
<goal, repo + key paths, constraints ("don't touch X"), non-goals, proof expected, output shape>
EOF
command codex exec --yolo -C <repo> \
  --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" \
  -o /tmp/codex-last.md - <"$P" 2>/dev/null
```

The skill pins `gpt-5.6-terra` at `xhigh` effort as its default — deliberately, not relying on `~/.codex/config.toml`'s `model`, which the Codex desktop app mutates on its own. To use a different model for one task, swap the `--model` value (e.g. `--model gpt-5.6-luna`, `--model gpt-5.5`); to fall back to the config default, drop the flag.

- `--yolo` is the house default; Codex may run commands/tests freely. Keep prompts scoped to the target repo.
- `command codex` bypasses the interactive zsh wrapper; if not on PATH: `fnm exec --using default -- codex`
- stderr suppressed (thinking noise bloats context); drop `2>/dev/null` only to debug a failing run
- read `-o` file for the result; don't parse the JSONL stream
- run via `run_in_background` (the harness pings you on exit — never poll for it) and read `-o` on completion; **make the run visible by default** (see *Run visibly*); don't kill quiet runs <30 min
- parallel independent tasks OK: separate repos/dirs, separate `-o` files
- outside a git repo add `--skip-git-repo-check`

Follow-up fixes — cheaper than fresh runs, keeps context. `resume` has no `-C`/`--yolo`: run from the repo dir, spell the long flag:

```bash
(cd <repo> && command codex exec resume --last \
  --dangerously-bypass-approvals-and-sandbox \
  -o /tmp/codex-last.md - <"$P2" 2>/dev/null)
```

## Run visibly (default)

Run every delegation in a visible cmux/tmux pane so the user can watch Codex work live — while keeping the harness-tracked `run_in_background` job that pings you on completion (do NOT poll, and do NOT type `codex` into the pane, which would sever completion tracking). The trick: the background job tees its stream to a file, and the pane just `tail -F`s that file. So the background job still owns execution and completion; the pane is a passive live view.

```bash
OUT=/tmp/codex-last.md; STREAM=/tmp/codex-last.stream; : >"$STREAM"
# 1. Open a visible pane tailing the live stream (unfocused):
#    cmux: cmux new-surface --type terminal --workspace "$CMUX_WORKSPACE_ID" --focus false
#          → parse the surface UUID → cmux send/send-key `tail -F "$STREAM"`
#    tmux: tmux new-window -d -n codex "tail -F '$STREAM'"
# 2. Launch the real run as a run_in_background Bash job (completion ping as usual):
command codex exec --yolo -C <repo> --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" -o "$OUT" - <"$P" >"$STREAM" 2>&1
```

- **Zero extra Claude tokens.** The pane shows Codex's own stdout via `tail`; it never enters Claude's context — on the completion ping Claude reads `$OUT` only, exactly as in the headless case. Cost is a couple of pane-management CLI calls.
- The pane is cosmetic: closing it (or `tail` exiting) never affects the run. Close the surface after review, or leave it.
- **Fallback to a plain detached background run (no pane)** only when there is no cmux/tmux surface — headless/cron, or `CMUX_*` and `$TMUX` both unset. Then run the base `Invoke` command directly under `run_in_background`.
- **Not `/handoff-agent`.** Reserve handoff-agent for long, autonomous, *steerable* work that needs durable protocol state; its doorbells and `coordinator pending` reads DO spend Claude tokens each round-trip. `codex exec` is a headless batch with an `-o` contract, not a protocol worker — for a spec-frozen build the visible pane gives the window essentially for free.

## Remote box (only when explicitly asked)

Default is local. Run `codex exec` on a remote box **only when the user explicitly asks for the box**, or the task's code/data lives there — never as an inference. Same headless + visible-pane + `-o`-review contract, wrapped in SSH; the task's `-C` is a **box** repo. Codex must already be authenticated on the box. No extra Claude tokens: the remote stdout is redirected to a box-side stream + `-o` and never returns over SSH; the pane tails it via `ssh tail -F`; you read `-o` once via `ssh box cat` on completion.

```bash
ssh <box> 'mkdir -p <remote-work> && : > <remote-stream>'      # prep; prompt goes over SSH stdin
# visible pane (default): a terminal running  ssh <box> "tail -F <remote-stream>"
# the run as a local run_in_background job — the SSH command exiting IS the completion ping:
ssh <box> 'command codex exec --yolo -C <remote-repo> --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" -o <remote-out> - > <remote-stream> 2>&1' < "$P"
# on the ping: ssh <box> cat <remote-out>  → review; verify with  ssh <box> <test cmd>
```

- For a stopped box with a documented lifecycle helper, bring it up only if the request authorizes using the box (e.g. investment OCI box: `~/projects/investment/src/scripts/oci_box_ctl.sh up`).
- This is still `codex exec`, not `/handoff-agent`. Use handoff-agent's remote SSH adapter instead when the box run needs steering, durability across your session, or fan-out — not for a spec-frozen one-shot.

## Prompt contract

Codex starts with zero session context. Every prompt: goal, exact repo/paths, constraints, non-goals, proof expected (exact test command), output shape ("report files changed + test output"). Spec quality decides success.

## Verify (Claude, always)

- `git status -sb` + read the full diff; judge like a contributor PR
- run focused tests yourself or demand proof output; Codex claims are advisory
- iterate via resume; after 2 failed rounds, take over and do it directly
- normal closeout still applies: `$autoreview` before ship

## Economics

Win = generation + exploration tokens moved to Codex; Claude spends only on spec + diff review. Don't ping-pong trivia through delegation; don't re-read what Codex already summarized.

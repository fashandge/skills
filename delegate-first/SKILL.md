---
name: delegate-first
description: "Delegate implementation work from expensive Opus/Fable Claude Code sessions to cheap headless one-shot workers — Codex CLI (default) or a weaker Claude model via claude -p. Claude specs, reviews, verifies. Steerable/durable/Kimi workers route to handoff-agent instead."
---

# Delegate First

Claude Code sessions only. Codex/other harnesses: skip; never self-delegate.

Opus/Fable models only. If the session runs Sonnet, Haiku, an unknown Claude model, or a non-Anthropic model (e.g. GLM 5.2, Meta muse-spark): skip this skill entirely and implement directly. The economics below don't apply, and the routing assumptions (Claude ergonomics vs worker generation) are calibrated to Opus/Fable models.

Detecting an eligible session (check before first delegation, once per session):

1. Model name — read "You are powered by the model named ..." in the system prompt. Only a model whose normalized name contains `claude-opus` or `claude-fable` is eligible. `claude-sonnet-*`, `claude-haiku-*`, unknown Claude models, and non-`claude-*` names → skip. This is a hard gate; `CODEX_FIRST=1` does not override it. Not sufficient alone: wrappers can spoof Claude model ids.
2. Env check for an eligible model (authoritative; run in Bash):
   ```bash
   echo "CODEX_FIRST=${CODEX_FIRST:-unset} ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-unset}"
   ```
   - `CODEX_FIRST=0` → skip (explicit off — set by claude-go / claude-meta / ccr wrappers).
   - `CODEX_FIRST=1` → use the skill, provided the model gate passed (explicit on, overrides base-URL inference — e.g. an Anthropic-compatible gateway serving Opus/Fable).
   - unset → infer from `ANTHROPIC_BASE_URL`: unset or `*.anthropic.com` → use the skill; anything else (localhost proxy, api.meta.ai, ccr router) → skip.

Rationale: orchestrator (Fable/Opus) tokens are metered + expensive; workers are cheap — Codex is flat-rate, and Haiku/Sonnet via `claude -p` are metered but a fraction of the orchestrator's price. Claude wins at ergonomics — judgment, design, spec-writing, review, orchestration. So workers type, Claude thinks and verifies.

## Choose a worker

| Worker | Invocation | When |
|---|---|---|
| **Codex** (default) | `codex exec --yolo … -o out.md` | Everything below unless a reason says otherwise — flat-rate, strong at code generation |
| **Claude weak model** | `claude -p --model haiku\|sonnet --dangerously-skip-permissions` | Codex unavailable/rate-limited; task leans on Claude-family conventions (CLAUDE.md adherence, Claude-style tools); user asks for it. `haiku` for mechanical edits, `sonnet` for mid-complexity |
| **Kimi Code** | *no headless mode* | Kimi is TUI-only — a Kimi worker can only run through `/handoff-agent` (which drives its TUI). Verify `kimi` is installed first; it currently is not on this Mac or the OCI box |

Both headless workers use the same contract: prompt via temp file, result to a file, review by Claude. `claude -p` prints its final answer to stdout — redirect to the out-file (`> out.md`); its stream is not incremental like Codex's, so the visible pane may show little until completion (acceptable; note it to the user for long runs).

## Route

When the Opus/Fable model gate above passes, delegate proper hands-on implementation work to a worker:

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
- review of worker output — never delegated, never skipped

Mixed task: Claude designs first, freezes spec, delegates build-out.
Heuristic: prompt reads as a work order → delegate; writing it forces decisions → design, Claude.
Portfolio/multi-repo work: `$maintainer-orchestrator` instead.

## vs `/handoff-agent` — when to use which

Both put a worker on the task; the axis is NOT complexity, it is what the run needs.

**Stay here (headless one-shot)** whenever the task is spec-freezable up front — fire → read the out-file → review — even a large one. It is cheaper: no doorbell/lease/protocol tokens, and iteration goes through `resume`.

**Escalate to `/handoff-agent`** only when the run needs a quality a headless one-shot cannot give:

- mid-run **steering** or answering the worker's blocking questions
- **durability** across your own compaction/session (a long-lived worker you check on over many turns)
- an **interactive remote worker** on a box, or a separate Codex app task
- **fan-out** of several monitored workers
- the worker must be **Kimi** (TUI-only)

So simple-but-steerable → handoff-agent; complex-but-frozen-spec → headless here. Do not auto-escalate on size alone. Handoff-agent's doorbells and `coordinator pending` reads DO spend Claude tokens each round-trip; the headless route spends only spec + review.

## Invoke

Prompt via temp file, never inline quoting:

```bash
P=$(mktemp); cat >"$P" <<'EOF'
<goal, repo + key paths, constraints ("don't touch X"), non-goals, proof expected, output shape>
EOF
# Codex (default):
command codex exec --yolo -C <repo> \
  --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" \
  -o /tmp/worker-last.md - <"$P" 2>/dev/null
# Claude weak model (alternative):
(cd <repo> && command claude -p --model haiku \
  --dangerously-skip-permissions \
  "$(cat "$P")" > /tmp/worker-last.md 2>/dev/null)
```

The skill pins Codex to `gpt-5.6-terra` at `xhigh` effort as its default — deliberately, not relying on `~/.codex/config.toml`'s `model`, which the Codex desktop app mutates on its own. To use a different model for one task, swap the `--model` value (e.g. `--model gpt-5.6-luna`, `--model gpt-5.5`); to fall back to the config default, drop the flag.

- `--yolo` (Codex) / `--dangerously-skip-permissions` (Claude) are the house default; workers may run commands/tests freely. Keep prompts scoped to the target repo.
- `command codex` bypasses the interactive zsh wrapper; if not on PATH: `fnm exec --using default -- codex`
- stderr suppressed (thinking noise bloats context); drop `2>/dev/null` only to debug a failing run
- read the out-file for the result; don't parse the JSONL stream
- run via `run_in_background` (the harness pings you on exit — never poll for it) and read the out-file on completion; **make the run visible by default** (see *Run visibly*); don't kill quiet runs <30 min
- parallel independent tasks OK: separate repos/dirs, separate out-files
- outside a git repo: Codex needs `--skip-git-repo-check`

Follow-up fixes — cheaper than fresh runs, keeps context. Codex `resume` has no `-C`/`--yolo`: run from the repo dir, spell the long flag. Claude follow-ups: `claude -p --continue` from the same cwd.

```bash
(cd <repo> && command codex exec resume --last \
  --dangerously-bypass-approvals-and-sandbox \
  -o /tmp/worker-last.md - <"$P2" 2>/dev/null)
```

## Run visibly (default)

Run every delegation in a visible cmux/tmux pane so the user can watch the worker live — while keeping the harness-tracked `run_in_background` job that pings you on completion (do NOT poll, and do NOT type the worker command into the pane, which would sever completion tracking). The trick: the background job tees its stream to a file, and the pane just `tail -F`s that file. So the background job still owns execution and completion; the pane is a passive live view.

```bash
OUT=/tmp/worker-last.md; STREAM=/tmp/worker-last.stream; : >"$STREAM"
# 1. Open a visible pane tailing the live stream (unfocused):
#    cmux: cmux new-surface --type terminal --workspace "$CMUX_WORKSPACE_ID" --focus false
#          → parse the surface UUID → cmux send/send-key `tail -F "$STREAM"`
#    tmux: tmux new-window -d -n worker "tail -F '$STREAM'"
# 2. Launch the real run as a run_in_background Bash job (completion ping as usual):
command codex exec --yolo -C <repo> --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" -o "$OUT" - <"$P" >"$STREAM" 2>&1
```

- **Zero extra Claude tokens.** The pane shows the worker's own stdout via `tail`; it never enters Claude's context — on the completion ping Claude reads `$OUT` only, exactly as in the headless case. Cost is a couple of pane-management CLI calls.
- The pane is cosmetic: closing it (or `tail` exiting) never affects the run. Close the surface after review, or leave it.
- **Fallback to a plain detached background run (no pane)** only when there is no cmux/tmux surface — headless/cron, or `CMUX_*` and `$TMUX` both unset. Then run the base `Invoke` command directly under `run_in_background`.

## Remote box (only when explicitly asked)

Default is local. Run a headless worker on a remote box **only when the user explicitly asks for the box**, or the task's code/data lives there — never as an inference. Same headless + visible-pane + out-file-review contract, wrapped in SSH; the task's `-C`/cwd is a **box** repo. The worker CLI must already be authenticated on the box. No extra Claude tokens: the remote stdout is redirected to a box-side stream + out-file and never returns over SSH; the pane tails it via `ssh tail -F`; you read the out-file once via `ssh box cat` on completion.

```bash
ssh <box> 'mkdir -p <remote-work> && : > <remote-stream>'      # prep; prompt goes over SSH stdin
# visible pane (default): a terminal running  ssh <box> "tail -F <remote-stream>"
# the run as a local run_in_background job — the SSH command exiting IS the completion ping:
ssh <box> 'command codex exec --yolo -C <remote-repo> --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" -o <remote-out> - > <remote-stream> 2>&1' < "$P"
# on the ping: ssh <box> cat <remote-out>  → review; verify with  ssh <box> <test cmd>
```

- For a stopped box with a documented lifecycle helper, bring it up only if the request authorizes using the box (e.g. investment OCI box: `~/projects/investment/src/scripts/oci_box_ctl.sh up`).
- This is still a headless one-shot, not `/handoff-agent`. Use handoff-agent's remote SSH adapter instead when the box run needs steering, durability across your session, or fan-out — not for a spec-frozen one-shot.

## Prompt contract

Workers start with zero session context. Every prompt: goal, exact repo/paths, constraints, non-goals, proof expected (exact test command), output shape ("report files changed + test output"). Spec quality decides success.

## Verify (Claude, always)

- `git status -sb` + read the full diff; judge like a contributor PR
- run focused tests yourself or demand proof output; worker claims are advisory
- iterate via resume/`--continue`; after 2 failed rounds, take over and do it directly
- normal closeout still applies: `$autoreview` before ship

## Economics

Win = generation + exploration tokens moved to a cheap worker; Claude spends only on spec + diff review. Don't ping-pong trivia through delegation; don't re-read what the worker already summarized.

---
name: delegate-first
description: "Delegate implementation work to cheap headless one-shot workers — Codex CLI (default), a weaker Claude model via claude -p, Kimi Code via kimi -p, or pi with MiniMax-M3 or DeepSeek V4 Flash. Orchestrator specs, reviews, verifies. Auto-triggers only in Opus/Fable Claude Code sessions; from Codex/Kimi/pi/other sessions use only on explicit request. Steerable/durable workers route to handoff-agent instead."
---

# Delegate First

Two invocation modes — the gate below decides *automatic* use only:

- **Auto-trigger** (apply this skill proactively for routable work): ONLY in Anthropic Claude Code sessions running Opus or Fable. If the session runs Sonnet, Haiku, an unknown Claude model, a non-Anthropic model (e.g. GLM 5.2, Meta muse-spark), or another harness entirely (Codex, Kimi): never auto-invoke — the economics below don't apply, and the routing assumptions (Claude ergonomics vs worker generation) are calibrated to Opus/Fable orchestrators.
- **Explicit request** (the user invokes `/delegate-first` or says "delegate this to codex/claude/kimi/pi"): usable from ANY harness or model — Codex, Kimi, and pi sessions included. Skip the eligibility gate, keep everything else (worker matrix, spec contract, visible pane, verify-always). Never self-delegate: don't hand work to the same agent CLI the session itself runs on — pick a different worker, or the one the user names.

Detecting an auto-trigger-eligible session (check before first automatic delegation, once per session):

1. Model name — read "You are powered by the model named ..." in the system prompt. Only a model whose normalized name contains `claude-opus` or `claude-fable` is eligible. `claude-sonnet-*`, `claude-haiku-*`, unknown Claude models, and non-`claude-*` names → skip. This is a hard gate; `DELEGATE_FIRST=1` does not override it. Not sufficient alone: wrappers can spoof Claude model ids.
2. Env check for an eligible model (authoritative; run in Bash — `CODEX_FIRST` is the honored legacy name for the same signal):
   ```bash
   echo "DELEGATE_FIRST=${DELEGATE_FIRST:-${CODEX_FIRST:-unset}} ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-unset}"
   ```
   - `DELEGATE_FIRST=0` → skip (explicit off — set by claude-go / claude-muse-spark / ccr wrappers).
   - `DELEGATE_FIRST=1` → use the skill, provided the model gate passed (explicit on, overrides base-URL inference — e.g. an Anthropic-compatible gateway serving Opus/Fable).
   - unset (both names) → infer from `ANTHROPIC_BASE_URL`: unset or `*.anthropic.com` → use the skill; anything else (localhost proxy, api.meta.ai, ccr router) → skip.

Rationale: orchestrator (Fable/Opus) tokens are metered + expensive; workers are cheap — Codex is flat-rate, and Haiku/Sonnet via `claude -p` are metered but a fraction of the orchestrator's price. Claude wins at ergonomics — judgment, design, spec-writing, review, orchestration. So workers type, Claude thinks and verifies.

## Choose a worker

**User override always wins.** When the user names a worker and/or model ("delegate to kimi", "have sonnet do it", "use codex with gpt-5.5", "send it to pi"), use exactly that — the matrix defaults below apply only when the user left the choice open. Model overrides map per CLI: Codex `--model <id>` (+ `-c model_reasoning_effort=…`), Claude `--model <id> --effort <level>`, Kimi `-m <alias>` (+ `KIMI_MODEL_THINKING_EFFORT=…`), pi `--provider <name> --model <id> --thinking <level>`.

| Worker | Invocation | When |
|---|---|---|
| **Codex** (default) | `codex exec --yolo … -o out.md` | Everything below unless a reason says otherwise — flat-rate, strong at code generation |
| **Claude weak model** | `claude -p --model opus --effort high --dangerously-skip-permissions` | Codex unavailable/rate-limited; task leans on Claude-family conventions (CLAUDE.md adherence, Claude-style tools); user asks for it. `opus` at `high` effort by default; drop to `sonnet`/`haiku` for simple mechanical edits |
| **Kimi Code** | `KIMI_MODEL_THINKING_EFFORT=max ~/.kimi-code/bin/kimi -m kimi-code/k3 -p "…"` | User asks for Kimi, or as a third independent perspective. `kimi-code/k3` at `max` thinking effort by default (effort is env-var-only — no CLI flag) |
| **pi** | `pi --provider minimax --model MiniMax-M3 --thinking high -p "…"` | User asks for pi, a very easy task without much judgment (simple script changes, moving files), or the cheapest option for high-volume mechanical work (bulk exploration, wide mechanical migrations, coverage fills). `MiniMax-M3` at `high` thinking by default; switch to `--provider deepseek --model deepseek-v4-flash --thinking max` only when the task needs its 1M context to swallow large-repo reading the others would choke on |

All four use the same contract: prompt via temp file, result to a file, review by Claude. `claude -p`, `kimi -p`, and `pi -p` print the final answer to stdout — redirect to the out-file (`> out.md`); their streams are not incremental like Codex's, so the visible pane may show little until completion (acceptable; note it to the user for long runs).

Kimi gotchas (verified v0.27.0): the binary lives at `~/.kimi-code/bin/kimi` and is on the *interactive* zsh PATH only — use the absolute path from scripts/tool shells. Prompt mode auto-approves actions and **rejects** `--yolo`/`--auto` (`Cannot combine --prompt with --yolo`) — pass neither. The model alias is lowercase `kimi-code/k3`; thinking effort only via `KIMI_MODEL_THINKING_EFFORT=max`. Follow-ups: it prints `To resume this session: kimi -r <session-id>` — reuse that id with `-p` for the next instruction. On the OCI box, `~/.kimi-code/bin/kimi` is a wrapper that execs `kimi-real` via `/lib/ld-linux-aarch64.so.1` (the UEK kernel rejects the binary's ELF property notes at direct execve); `kimi upgrade` overwrites the wrapper — re-create it after upgrading.

pi gotchas (verified 2026-08-05): no `-C`/`--cd` flag — `cd` into the repo like Claude and Kimi. `-p` auto-approves its read/bash/edit/write tools (no `--yolo` equivalent exists or is needed) and prints only the final answer to stdout, so stderr is normally empty. Provider and model are separate flags (`--provider minimax --model MiniMax-M3`); the `provider/id[:thinking]` pattern form works too but the explicit flags are clearer in a spec. Thinking levels are `off|minimal|low|medium|high|xhigh|max` — `high` is the default here. Unlike `kimi`, `pi` is on the non-interactive PATH (`~/.zshenv`), so no absolute path or `command` prefix is needed. Auth reads `MINIMAX_API_KEY` (or `DEEPSEEK_API_KEY` for the deepseek provider) from the environment: interactive shells get it from `~/.config/secrets.env` via the profile, but launchd/cron shells do **not** — source that file first in scheduled contexts. pi discovers `AGENTS.md`/`CLAUDE.md` by default (`--no-context-files` to suppress), so repo conventions land in the worker's context for free.

## Route

When the auto-trigger gate above passes (or the user explicitly asks), delegate proper hands-on implementation work to a worker:

- implementation from a frozen spec; refactors; mechanical migrations
- bug fixes with known repro; test writing; coverage fills
- CI fixes, dependency bumps, scripts/tooling
- bulk codebase exploration where raw reading ≫ the answer

Keep in Claude:

- all work when running an auto-trigger-ineligible session (Sonnet, Haiku, unknown/non-Anthropic models) — unless the user explicitly asked to delegate
- design, API design, architecture, naming, UX judgment
- tasks where writing the spec IS the work (ambiguity = design)
- tiny edits (~<20 lines, single obvious change) — delegation overhead loses
- skill creation or edits (global `~/skills` or a project's `skills/`) — these default to Fable 5 at high effort, so a cheap worker is the wrong tier
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
(cd <repo> && command claude -p --model opus --effort high \
  --dangerously-skip-permissions \
  "$(cat "$P")" > /tmp/worker-last.md 2>/dev/null)
# Kimi Code (alternative; no --yolo/--auto with -p — prompt mode auto-approves;
# thinking effort is env-var-only):
(cd <repo> && KIMI_MODEL_THINKING_EFFORT=max ~/.kimi-code/bin/kimi -m kimi-code/k3 \
  -p "$(cat "$P")" > /tmp/worker-last.md 2>/dev/null)
# pi (alternative; -p auto-approves tools — no --yolo equivalent; no -C, so cd):
(cd <repo> && pi --provider minimax --model MiniMax-M3 \
  --thinking high -p "$(cat "$P")" > /tmp/worker-last.md 2>/dev/null)
```

The skill pins Codex to `gpt-5.6-terra` at `xhigh` effort as its default — deliberately, not relying on `~/.codex/config.toml`'s `model`, which the Codex desktop app mutates on its own. To use a different model for one task, swap the `--model` value (e.g. `--model gpt-5.6-luna`, `--model gpt-5.5`); to fall back to the config default, drop the flag.

- `--yolo` (Codex) / `--dangerously-skip-permissions` (Claude) are the house default; workers may run commands/tests freely. Keep prompts scoped to the target repo.
- `command codex` bypasses the interactive zsh wrapper; if not on PATH: `fnm exec --using default -- codex`
- stderr suppressed (thinking noise bloats context); drop `2>/dev/null` only to debug a failing run
- read the out-file for the result; don't parse the JSONL stream
- run via `run_in_background` (the harness pings you on exit — never poll for it) and read the out-file on completion; **make the run visible by default** (see *Run visibly*); don't kill quiet runs <30 min
- parallel independent tasks OK: separate repos/dirs, separate out-files
- outside a git repo: Codex needs `--skip-git-repo-check`

Follow-up fixes — cheaper than fresh runs, keeps context. Codex `resume` has no `-C`/`--yolo`: run from the repo dir, spell the long flag. Claude follow-ups: `claude -p --continue` from the same cwd. pi follow-ups: `pi … -c -p "…"` from the same cwd (sessions are keyed by project dir; `-r`/`--session <id>` picks a specific one).

```bash
(cd <repo> && command codex exec resume --last \
  --dangerously-bypass-approvals-and-sandbox \
  -o /tmp/worker-last.md - <"$P2" 2>/dev/null)
```

## Run visibly (default)

Run every delegation in a visible cmux/tmux pane so the user can watch the worker live — while keeping the harness-tracked `run_in_background` job that pings you on completion (do NOT poll, and do NOT type the worker command into the pane, which would sever completion tracking). The trick: the background job tees its stream to a file, and the pane just `tail -F`s that file. So the background job still owns execution and completion; the pane is a passive live view.

Open and close the pane **only via the bundled script** — never with hand-rolled `cmux send`/`send-key`/`close-surface` calls:

```bash
OUT=/tmp/worker-last.md; STREAM=/tmp/worker-last.stream; : >"$STREAM"
# 1. Open the unfocused live-view pane (prints one JSON line; see --help for schema):
~/skills/delegate-first/scripts/worker_pane.sh open --stream "$STREAM"
# 2. Launch the real run as a run_in_background Bash job (completion ping as usual):
command codex exec --yolo -C <repo> --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" -o "$OUT" - <"$P" >"$STREAM" 2>&1
```

Only Codex has an `-o` out-file flag. The stdout-only workers (`claude -p`, `kimi -p`, `pi -p`) must tee instead, so the pane and the out-file both get the answer — e.g.
`(cd <repo> && pi --provider minimax --model MiniMax-M3 --thinking high -p "$(cat "$P")" 2>&1 | tee "$STREAM" > "$OUT")`.

- **Why the script is mandatory** (2026-07-25 incident): `cmux send`/`send-key`/`close-surface` all default `--surface` to `$CMUX_SURFACE_ID` — **the surface hosting this very Claude session**. A hand-rolled `cmux send 86 "tail …"` typed into the session's own pane; its `OK surface:44` echo (the default target, i.e. the session itself) was then misread as a stray surface, and `close-surface --surface surface:44` killed the session. The script always passes an explicit `--surface` and its `close` refuses the session's own surface. If you ever bypass it, the invariant is: explicit `--surface` on every call, and never target `$CMUX_SURFACE_ID` or the `caller.surface_ref` that `cmux identify` reports.
- **Zero extra Claude tokens.** The pane shows the worker's own stdout via `tail`; it never enters Claude's context — on the completion ping Claude reads `$OUT` only, exactly as in the headless case. Cost is the two `worker_pane.sh` calls.
- The pane is cosmetic: closing it (or `tail` exiting) never affects the run. After review, run the exact `close` command the open-JSON reported, or leave the pane.
- **Fallback to a plain detached background run (no pane)**: the script prints `{"backend":"none",…}` and exits 0 when there is no cmux/tmux (headless/cron) — then just run the base `Invoke` command under `run_in_background`.

## Remote box (only when explicitly asked)

Default is local. Run a headless worker on a remote box **only when the user explicitly asks for the box**, or the task's code/data lives there — never as an inference. Same headless + visible-pane + out-file-review contract, wrapped in SSH; the task's `-C`/cwd is a **box** repo. The worker CLI must already be authenticated on the box. No extra Claude tokens: the remote stdout is redirected to a box-side stream + out-file and never returns over SSH; the pane tails it via `ssh tail -F`; you read the out-file once via `ssh box cat` on completion.

```bash
ssh <box> 'mkdir -p <remote-work> && : > <remote-stream>'      # prep; prompt goes over SSH stdin
# visible pane (default): ~/skills/delegate-first/scripts/worker_pane.sh open --cmd "ssh <box> tail -F <remote-stream>"
# the run as a local run_in_background job — the SSH command exiting IS the completion ping:
ssh <box> 'command codex exec --yolo -C <remote-repo> --model gpt-5.6-terra \
  -c model_reasoning_effort="xhigh" -o <remote-out> - > <remote-stream> 2>&1' < "$P"
# on the ping: ssh <box> cat <remote-out>  → review; verify with  ssh <box> <test cmd>
```

- For a stopped box with a documented lifecycle helper, bring it up only if the request authorizes using the box (e.g. investment OCI box: `~/projects/investment/src/scripts/oci_box_ctl.sh up`).
- This is still a headless one-shot, not `/handoff-agent`. Use handoff-agent's remote SSH adapter instead when the box run needs steering, durability across your session, or fan-out — not for a spec-frozen one-shot.

## Prompt contract

Workers start with zero session context. Every prompt: goal, exact repo/paths, constraints, non-goals, proof expected (exact test command), output shape ("report files changed + test output"). Spec quality decides success.

Two lines worth carrying in every prompt that touches shared state:

- **Test against copies, not the real thing.** Build throwaway trees with `mktemp -d` and redirect the code at them through whatever env var/parameter it already honors (e.g. `HANDOFF_REGISTRY_FILE`). A path that can't be redirected is a defect worth reporting — it means nobody can test that path safely.
- **Declare durable writes outside the target repo.** Scratch/temp writes are free and expected. But if the task genuinely requires modifying something durable elsewhere (a global skill, a config, an installed hook), back up the original first and say so explicitly in the report — that edit is invisible to the reviewer's `git status` on the target repo.

## Verify (Claude, always)

- `git status -sb` + read the full diff; judge like a contributor PR
- run focused tests yourself or demand proof output; worker claims are advisory
- **sweep every checkout, not just the target repo** — `~/projects/agents/scripts/fleet_status.sh` reports branch/HEAD/dirty/ahead-behind for each known checkout on each host (plus runtime path and pending state migrations). A worker's edit to a checkout outside its target repo is invisible to `git status` in the target and one `git checkout` from being lost; unexpected dirt anywhere is part of the result to review. Also run it *before* delegating to a remote host, so you inherit a known-good baseline
- **when two delegations touched the same file, merge both before reviewing either**, then add at least one test exercising A's feature against B's data path. Isolated workers each ship correct code that composes into a bug neither could see — that interaction is the reviewer's job, and it is the only bug class nobody else can catch
- iterate via resume/`--continue`; after 2 failed rounds, take over and do it directly
- normal closeout still applies: `$autoreview` before ship

## Economics

Win = generation + exploration tokens moved to a cheap worker; Claude spends only on spec + diff review. Don't ping-pong trivia through delegation; don't re-read what the worker already summarized.

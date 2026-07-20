---
name: handoff-agent
description: Hand a coding task to an autonomous Claude Code, Codex, or Kimi Code worker in local cmux/tmux, a remote SSH-hosted tmux session, or a separate task in the same Codex desktop-app project. Use the durable local-v1 protocol for terminal workers or Codex task controls for app-native launch, monitoring, and steering. Use when the user says "hand this off", "delegate this", "spawn a coding-agent session", "start a background Codex task", "run Claude on a remote box", "monitor the worker", "steer the other agent", or asks about an existing handoff run.
---

# Hand off to an autonomous coding agent

For cmux/tmux and SSH workers, use the filesystem protocol on the worker's
owning host as the semantic source of truth. Use cmux/tmux only to launch,
probe, queue a doorbell, capture diagnostics, perform a narrowly authorized
rescue/approval action, or stop a stuck process. For an app-native Codex task,
use Codex task status and history instead of the local-v1 protocol.

Not every delegation needs this machinery: a spec-freezable one-shot that
needs no mid-run steering, cross-session durability, or fan-out is cheaper as
a headless worker via the `delegate-first` skill (its "vs /handoff-agent"
section owns the boundary — defer to it rather than restating it here).

## Prepare the kickoff

1. If the user names a plan/spec, write a thin kickoff that points to it by
   path and calls it authoritative. Do not duplicate the plan.
2. Otherwise write a self-contained kickoff with all conversation-only
   findings, paths, constraints, verification steps, scope fences, commit
   policy, and a checkable done condition. The worker starts with no parent
   conversation context.
3. Save durable kickoffs under `docs/plans/<date>-<slug>-kickoff.md`. For a
   throwaway task, create a mode-`0700` temporary directory outside the
   repository with `mktemp -d`, write the kickoff there, and remove that source
   after a successful launch. The launcher has already copied it into the
   durable run directory by then; later `handoffctl context` reads that durable
   copy, so retaining the temporary source adds no recovery value.
4. Fence shared state in every kickoff that touches it. Have the worker test
   against throwaway copies (`mktemp -d`) redirected through whatever env var
   the code already honors, never against live state; a path that cannot be
   redirected is a defect worth reporting rather than working around. Scratch
   writes outside the repo are free, but a *durable* change elsewhere (a global
   skill, a config, an installed hook) must be backed up first and named in the
   worker's `result` — that edit is invisible to the run repo's `git status`,
   and the durable outbox is the one channel that survives the worker's
   context being compacted or lost.
5. Add `<kickoff>.goal` only when autonomous continuation is wanted. Put one
   complete `/goal ...` command on its first line.
6. Ask only when the repository, agent, or machine is genuinely ambiguous.

## Choose the launch mode

Continuous session-owned monitoring is the default for terminal workers. Lazily
start or reuse one orchestrator watcher on the first handoff in an orchestrator
session, assign every later worker from that session to it, and let the
launcher return promptly. Use unmonitored fire-and-forget mode only when the
user explicitly asks not to monitor the worker.

Starting the watcher is part of launching a monitored handoff, not an optional
extra. Never wait on workers by polling from your own turn — no `watch` (with
or without `--timeout`), no repeated `status`, no sleep-and-check loops. The
watcher pushes a typed doorbell into your surface when a worker needs attention,
and `orchestrator pending` then loads the unread events. A self-run
`watch --timeout` is a debugging tool only. If you find yourself polling, the
watcher is missing or dead: start or relaunch it with `orchestrator start`
instead of working around it.

Before the first monitored launch, bootstrap the session watcher once. The
`--owner-pid` must be the actual long-lived Claude/Codex process PID — never a
transient tool shell's `$$` or `$PPID` (registration binds PID plus
process-start identity, so PID reuse cannot preserve an orphaned watcher).
Keep the printed state path private and reuse it only for this orchestrator
session:

```bash
~/projects/agents/scripts/handoff_orchestrator_ensure.sh \
  --transport cmux --owner-pid "$orchestrator_pid"
# tmux: --transport tmux --target <exact-orchestrator-handle> --owner-pid "$orchestrator_pid"
# already bootstrapped: add --state "$handoff_orchestrator_state" to skip register
```

Retain the printed `state` path as `handoff_orchestrator_state` and pass
`--orchestrator-state "$handoff_orchestrator_state"` to every monitored launcher
invocation. `orchestrator start` returns `started: false` when the same session
watcher is already running — not an error. The watcher is deterministic and
credential-free, discovers newly assigned workers through the registry, sends
opaque doorbells for *actionable* outbox events only, and exits when the exact
registered orchestrator process exits.

For an explicitly unmonitored fire-and-forget launch, invoke the launcher
without `--orchestrator-state`. It returns as soon as the session is started
(and, for Kimi, its run-specific kickoff pointer is delivered), then releases
orchestrator ownership itself. Do not locate credentials or wait for the
worker-ready checkpoint. Use a lowercase `[a-z0-9-]` task slug.

Canonical monitored launches:

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent codex --orchestrator-state "$handoff_orchestrator_state"
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent claude --orchestrator-state "$handoff_orchestrator_state"
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent kimi --orchestrator-state "$handoff_orchestrator_state"
```

With no `--backend`, the launcher uses cmux only when the orchestrator process
inherits a cmux workspace context and the cmux connection is reachable (the
worker launches into that workspace); otherwise it uses tmux. Pass `--backend
cmux` or `--backend tmux` only when the user asks for an override or an
operational constraint requires it. Launcher internals — model/effort defaults,
Kimi delivery mechanics, watcher hosting modes, readiness waits — live in
`references/launch-details.md`.

Parse the launcher's JSON response and retain `run_dir`, `transport`, and
`handle`. When not actively babysitting the worker, verify
`orchestrator_released` is true; the detached watcher still owns notification
delivery. For Kimi, also require `kickoff_sent: true`; otherwise report the
rescue command instead of claiming the worker started. Verify
`registry_recorded` when present: a registry failure does not invalidate the
live run, but later fast dispatch/context must fall back to the retained run
and handle fields. Report the run and handle immediately without polling status.

### Remote Codex folder-trust gate

Remote Codex launches automatically use a 30-second ready gate, then make at
most one exact-handle tmux capture. The launcher sends `C-m` only when it sees
Codex's exact folder-trust dialog for the supplied `--remote-cwd`; otherwise it
returns `startup_unconfirmed`. Treat `folder_trust_rescued` as a successful
transport rescue and resume normal event-driven behavior. Do not inspect the
screen yourself unless the launcher reports `startup_unconfirmed`; then read
`references/rescue-and-close.md`. Pass `--readiness-timeout` only to override
the bounded startup wait.

For a managed run, create one dedicated mode-`0700` private directory and add
`--retain-orchestrator`. When `HANDOFF_CREDENTIAL_DIR` is supplied, the launcher
uses that exact directory, so the orchestrator token is exactly
`$handoff_private_root/orchestrator.token`; never search for it with `find`.
Keep credential paths and contents out of prompts, terminal messages, and user
responses. Do not use the recovery or worker token during ordinary coordination.

```bash
mkdir -p "$HOME/.local/state/agents/handoff/orchestrators"
handoff_private_root=$(mktemp -d "$HOME/.local/state/agents/handoff/orchestrators/<name>.XXXXXX")
chmod 700 "$handoff_private_root"
HANDOFF_CREDENTIAL_DIR="$handoff_private_root" \
  ~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent codex --retain-orchestrator
```

## Observe and coordinate through `handoffctl`

Use the fixed helper:

```text
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python -m agents.orchestration.handoffctl
```

Read operations need no token:

```bash
<helper> runs list
<helper> runs show --run <selector>
<helper> runs doctor
<helper> context --run <selector>
<helper> status --run-dir <absolute-run-dir>
<helper> control show --run-dir <absolute-run-dir>
<helper> read --run-dir <absolute-run-dir> --journal outbox --after <cursor>
<helper> doctor --run-dir <absolute-run-dir>
```

Registry records are removable, registry-only — the run directory, journals,
and credentials are never deleted, and a forgotten run stays inspectable by
absolute `--run-dir`:

```bash
<helper> runs forget --run <selector> [--force]
<helper> runs prune [--older-than DAYS] [--host NAME] [--no-terminal-only] (--dry-run | --yes)
```

`runs forget`/`runs prune` refuse a run that is not known to be terminal
(a missing run directory counts as terminal — a dangling pointer) unless
explicitly overridden; `prune` previews with `--dry-run` and requires `--yes`
for a real run, reporting skipped records with reasons. `runs doctor` names
invalid records individually when one corrupt entry breaks registry reads;
`runs forget` is the remedy it points to.

One exception: a record that is invalid only because it predates the
orchestrator rename is *not* removable. Both commands refuse it and point at
`scripts/migrate_handoff_state_orchestrator.py`, because the migration
restores such a record intact while removing it would destroy state. Migrate
rather than forget when a whole host has drifted.

Every successful terminal launch privately registers the run on its owning
host; a remote launch also registers a credential-free proxy on the orchestrator
host. Selectors may be a run ID, unique prefix, task name, handle, or run URI.
Public registry output redacts credential directories. Prefer `context` after
context compaction or after removing a temporary kickoff source. Treat
`status.json`, `control.json`, and the journals as evidence — never infer
progress, acknowledgment, or success from terminal echoes.

When a cmux-launched worker publishes a `result`, `handoffctl` first makes the
result and `awaiting_review` state durable, then sends a best-effort native
cmux notification titled `Handoff result ready` with body `Awaiting orchestrator
review`, targeting the inherited `CMUX_SURFACE_ID`. Missing cmux context,
command failure, or timeout never invalidates the result and must not make the
worker retry publication or leave `awaiting_review`; the durable outbox event
is always authoritative. Pure tmux runs do not receive this cmux-native alert.

While actively coordinating, renew the orchestrator lease at least every 60
seconds and before other orchestrator mutations:

```bash
HANDOFF_ORCHESTRATOR_TOKEN_FILE=<orchestrator-token-file> \
  <helper> control renew --run-dir <absolute-run-dir>
```

If the user asks to monitor, babysit, or finish the handoff, keep the current
turn active and continue the renew/read/consume loop until the requested
terminal condition. Launch-only mode has already released the orchestrator lease
and intentionally does not wait for worker readiness. For a later one-shot
instruction, use registry-backed `dispatch`; it performs the required takeover
without exposing or rediscovering credential paths. Use explicit low-level
recovery only when the registry is unavailable or repair is required.

Consume-cursor discipline: read outbox events after `control.outbox_cursor`,
handle every event through a contiguous sequence, then call
`control consume --through N`. Re-reading an event is safe; use its stable
`message_id` for idempotent handling.

Blocking-question completeness contract: treat a worker question as
self-contained only when it states the current stage and completed work,
concrete evidence, the exact conflict, the decision or authority needed, a
recommended resolution, the consequences of the available options, and actions
intentionally deferred. Assume the worker knows the kickoff while you do not
know the worker's live progress; do not reconstruct missing context or guess.
Send a `steer` requesting the missing context, ring the normal opaque doorbell,
and answer the substantive question only after the worker supplements the
durable outbox record.

For steering, answers, and reviews:

- Prefer one-shot registry dispatch for a new instruction after launch-only:

  ```bash
  <helper> dispatch --run <selector> --body-file <private-file-or-dash>
  ```

  Pass dynamic content through stdin (`--body-file -`) or a private file.
  `dispatch` takes over the released lease, appends the right message type for
  the worker's state, rings the exact doorbell, releases ownership, and removes
  its ephemeral orchestrator token. State-aware linking: a worker `blocked` on a
  question gets `answer` tied to that exact question — a bare `steer` can never
  unblock it, because the worker cannot advance across an unanswered blocking
  question; a worker `awaiting_review` gets `supersede` tied to the exact
  pending result so it can resume without accepting or mislabeling it; otherwise
  the body goes as `steer`. Verify which happened from the response's
  `answered_question` / `superseded_result` / `message.type` fields — when
  answering a blocking question, confirm `answered_question` matches the question
  you meant to answer. Remote dispatch performs the full owner-side transaction
  and tmux doorbell in one SSH invocation, so it needs an up-to-date `agents`
  package on the owning host; if a dispatched authorization ever still leaves
  the worker `blocked` with `message.type: steer`, the owning host runs a stale
  package — update it rather than hand-rolling a takeover.
- Write body and data to private files or structured stdin. Never interpolate
  user/model content into a shell program.
- Use low-level `send --type steer` only while already holding a managed lease.
- Use `send --type answer --reply-to <question-id>` for a worker question.
- Use `send --type review --reply-to <result-id>` with disposition `accepted`
  or `changes_requested`.
- `send` rings the worker's terminal doorbell automatically for a registered
  run and reports `doorbell_sent` in its response (`--no-doorbell` opts out).
  Confirm `doorbell_sent: true` after every send — including the final stop —
  and fall back to the manual doorbell procedure with the returned `message.seq`
  only when it is `false`.
- Supply the orchestrator credential through
  `HANDOFF_ORCHESTRATOR_TOKEN_FILE` or `--token-file`, never argv token bytes.

Run `<helper> <command> --help` for exact payload flags and schemas.

## Monitoring behavior and doorbells

The worker runs **no** background inbox poller and the launcher installs no
hooks: its kickoff contract tells it to read the inbox at startup,
resume/compaction, turn or stage boundaries, and before irreversible actions,
commits, and results. A message sent during a long model turn may wait until
the next checkpoint.

- The session watcher is started with `orchestrator start`; never replace it with a time-limited generic observer — a self-run `watch --timeout` is for debugging only, never for waiting on worker events.
- A cmux orchestrator's doorbell uses two channels, recorded in the run's `last_doorbell_method` (e.g. `cmux_input+cmux_notify`): typed input into the orchestrator surface — counted only when the text visibly echoes, and the only channel that pushes an idle orchestrator agent to act — plus the visible `cmux notify` alert for the human. The doorbell may arrive as a typed prompt in your own composer; treat it as the trigger to inspect the exact pending prefix with `<helper> orchestrator pending --state "$handoff_orchestrator_state"`.
- `orchestrator pending` **acknowledges** the events it surfaces: it records a per-run `acknowledged_through` cursor in the watcher state, and for a **result** or review the watcher will not re-ring an event you have already loaded. A strictly newer worker event still rings, and each worker is tracked independently, so acking one worker never silences another.
- Ringing is **state-aware**: a worker **blocked** on a question keeps re-ringing until it is answered (a bare ack does not silence a stuck worker — it needs the answer, not just to be seen); a result rings until loaded; pure progress checkpoints and terminal (`succeeded`/`stopped`) states do not ring at all. The cure for a repeating doorbell on a *result* is `orchestrator pending`, never killing or closing the watcher.
- Never close the watcher's surface to stop a repeating doorbell: the watcher is session-scoped — other workers may still be running, and the orchestrator can still spawn new ones that need watching — so it must live until the orchestrator process exits, which it detects on its own. A repeat doorbell can still occur legitimately when delivery to the composer failed (e.g. an unechoed `cmux_input`); `pending` clears that too, and if it truly cannot be delivered the worker state is still durable in the outbox.
- To silence a run's current doorbell **without** consuming it or holding a lease — a completed run parked in `awaiting_review` for viewing, or a `blocked` run you are done with — use the credential-free `<helper> orchestrator dismiss --state "$handoff_orchestrator_state" --run <selector>`. `dismiss` records a per-run `dismissed_through` cursor; it stops ringing even a persistent `blocked` nag, and a strictly newer worker event still re-rings.
- `<helper> watch [--run <selector> ...] --interval 5 --timeout <seconds>` (omit `--run` to watch every registered run; `--once` for one pass; `--notify-cmux` for metadata-only alerts) is an ad-hoc foreground JSONL observer for debugging or rescue only, never a way to wait for worker events in a normal flow. It advances only its private observer cursor: it does not consume protocol outbox events, review a result, answer a question, or hold an orchestrator lease. The detached session watcher likewise never performs semantic actions; it only maintains independent delivery cursors and sends opaque doorbells. Autonomous replies still require an active orchestrator agent with authority for the decision.
- For urgent steering while you hold no active orchestrator lease (external intervention or an expired lease — `dispatch` refuses to run while a managed lease is held; a managed orchestrator driving the normal answer/review/stop lifecycle uses `send`, which rings the doorbell itself): use `handoffctl dispatch` so the instruction is durably appended before the exact registered handle is touched; confirm `doorbell_sent: true`, otherwise use the returned durable message sequence and stored handle for a narrow manual doorbell; never type the steering body or credentials into cmux/tmux — a doorbell contains only `Check handoff run <run-id>; inbox now through seq <N>.`
- A doorbell queues behind a running turn; it cannot interrupt the model. Hooks remain an optimization; the durable journal is authoritative even when a watcher or doorbell fails.

## Review and finish

1. Consume the worker's `result` event.
2. Select review depth proportionally; do not redo the delegated task by default.
   - Always inspect the durable result for completeness, scope compliance, and concrete evidence.
   - For bounded, low-stakes research, treat timestamped primary-source links and an internally consistent report as sufficient evidence. Do not repeat the same retrieval, web search, calculation, or analysis merely to validate it. Audit only when the evidence is missing or conflicting, the output is anomalous, or the user/task requires independent verification.
   - For code, named artifacts, multi-step or materially complex analysis, or high-stakes decisions, verify the relevant artifacts, reported HEAD/dirty state, repository diff, test evidence, and pivotal claims directly. A run may start or finish with pre-existing changes; never require the worker to stash, discard, or commit unrelated user work.
3. For code results, sweep every checkout — not just the run's repo — with
   `~/projects/agents/scripts/fleet_status.sh`. A worker's edit to a checkout
   outside its target repo is invisible to that repo's `git status` and one
   `git checkout` from being lost; unexpected dirt anywhere is part of the
   result to review. Run it before a remote launch too, so the run starts from
   a known-good baseline rather than a host that has silently drifted.
4. With several workers in flight, merge every branch that touched a shared
   file before reviewing any of them, then add a test exercising one worker's
   feature against another's data path. Independently correct changes compose
   into bugs no single worker can see; that interaction is yours to catch.
5. Send an accepted or changes-requested review tied to that exact result ID.
6. Wait for the worker to consume acceptance and emit `succeeded`; do not confuse worker success with orchestrator acceptance or integration. Waiting means watching for the watcher's next doorbell, not polling yourself.
7. Record `control integrate` or `control abandon`, then send a graceful stop and confirm its `doorbell_sent` — without the doorbell the idle worker never learns the run is over.
8. Run read-only `doctor`. Use repair flags only for identified, explicit recovery; never repair implicitly.

## Safety rules

- Never expose token contents or credential paths in prompts, doorbells, logs, notifications, or user-facing summaries.
- Never mutate an active worker's checkout from the orchestrator. Send an `input-changed` or `base-changed` message and let the worker incorporate it.
- Keep worker turns/checkpoints bounded when steering latency matters.
- Do not treat a live terminal, model prose, or screen text as durable state.
- Do not commit, push, stop, integrate, abandon, repair, or rotate unless the user's request authorizes that action.
- Never run `cmux close-window`, even on a vacated mirror window — targeting the wrong window destroys every workspace and session inside it; the user closes a vacated window with ⌘W.
- Never run `cmux close-workspace` except on the exact mirror-workspace UUID parsed from this run's own `ssh-tmux` output, and only when the user asked to remove the mirror (full procedure in `references/remote-and-viewers.md`).
- Never run `tab-action` sweeps (`close-others`, `close-left`, `close-right`) — they close the user's unrelated sessions and possibly your own surface.
- Close a viewer tab only via `~/projects/agents/scripts/cmux_close_surface_safe.sh`, naming the exact surface UUID.
- Never rotate a worker not confirmed dead; a lost SSH connection means state unknown, not dead — fence or confirm the old worker stopped before launching any replacement.

## Reference docs — MUST read before acting

- Before any remote launch, viewer creation, or cmux layout mutation, you MUST read `references/remote-and-viewers.md`.
- Before terminal rescue, closing sessions, or any manual doorbell, you MUST read `references/rescue-and-close.md`.
- For a Codex desktop-app task, you MUST read `references/codex-app-task.md` first.
- Launcher internals (model/effort defaults, Kimi delivery mechanics, watcher hosting modes, readiness waits): `references/launch-details.md`.

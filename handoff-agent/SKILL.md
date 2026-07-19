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
4. Add `<kickoff>.goal` only when autonomous continuation is wanted. Put one
   complete `/goal ...` command on its first line.
5. Ask only when the repository, agent, or machine is genuinely ambiguous.

## Choose the launch mode

Continuous session-owned monitoring is the default for terminal workers. Lazily
start or reuse one coordinator watcher on the first handoff in an orchestrator
session, assign every later worker from that session to it, and let the
launcher return promptly. Use unmonitored fire-and-forget mode only when the
user explicitly asks not to monitor the worker.

Starting the watcher is part of launching a monitored handoff, not an optional
extra. Never wait on workers by polling from your own turn — no `watch` (with
or without `--timeout`), no repeated `status`, no sleep-and-check loops. The
watcher pushes a typed doorbell into your surface when a worker needs
attention, and `coordinator pending` then loads the unread events. A
self-run `watch --timeout` is a debugging tool only. If you find yourself
polling, the watcher is missing or dead: start or relaunch it with
`coordinator start` instead of working around it.

`coordinator start` picks the watcher's hosting by transport (`--mode auto`):
cmux coordinators get a **surface-hosted** watcher — a terminal tab named
`watcher: <coordinator workspace>` parked in the bottom `handoff-watchers`
workspace, kept inside the cmux process tree so typed doorbells and native
alerts work — while tmux and native-app coordinators keep the fully detached
daemon. Closing the watcher tab (or the `handoff-watchers` workspace) kills
the watcher; rerun `coordinator start` to relaunch it. Do not force
`--mode detached` for a cmux coordinator unless degraded transient
macOS-banner doorbells are acceptable (the cmux socket rejects out-of-tree
clients).

Before the first monitored launch, create one unique mode-`0700` coordinator
directory, register the exact orchestrator target plus the PID of the long-lived
orchestrator process, and start the singleton watcher. The caller/session adapter
must supply the actual Claude/Codex process PID; never substitute a transient
tool shell's `$$` or `$PPID`. Registration captures both PID and process-start
identity so PID reuse cannot preserve an orphaned watcher. Keep the state path
private and reuse it only for that orchestrator session.

```bash
mkdir -p "$HOME/.local/state/agents/handoff/coordinators"
handoff_session_root=$(mktemp -d "$HOME/.local/state/agents/handoff/coordinators/session.XXXXXX")
chmod 700 "$handoff_session_root"
handoff_coordinator_state="$handoff_session_root/watcher.json"

# cmux example; tmux uses --transport tmux --target <exact-orchestrator-handle>
<helper> coordinator register --state "$handoff_coordinator_state" \
  --transport cmux --owner-pid "$orchestrator_pid"
<helper> coordinator start --state "$handoff_coordinator_state" --interval 5
```

Pass `--coordinator-state "$handoff_coordinator_state"` to every monitored
launcher invocation. `coordinator start` returns `started: false` when the same
session watcher is already running. The watcher is deterministic and
credential-free, discovers newly assigned workers through the registry, sends
opaque doorbells for *actionable* outbox events (a result, or a worker blocked
on a question — pure progress checkpoints and terminal states do not ring), and
exits when the exact registered orchestrator process exits. On a doorbell, use `coordinator pending` to load the
unread durable events and handle them normally.

For an explicitly unmonitored fire-and-forget launch, invoke the launcher
without `--coordinator-state`. It returns as soon as the session is started
(and, for Kimi, its run-specific kickoff pointer is delivered), then releases
coordinator ownership itself. Do not locate credentials or wait for the
worker-ready checkpoint. Use a lowercase `[a-z0-9-]` task slug.

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent codex --coordinator-state "$handoff_coordinator_state"
```

With no `--backend`, the launcher uses cmux only when the orchestrator process
inherits a cmux workspace context and the cmux connection is reachable; it
launches the worker into that workspace. Otherwise it uses tmux. Pass
`--backend cmux` or `--backend tmux` only when the user asks for an override or
an operational constraint requires it.

Parse the launcher's JSON response and retain `run_dir`, `transport`, and
`handle`. When not actively babysitting the worker, verify `coordinator_released`
is true; the detached watcher still owns notification delivery. Report the run
and handle immediately without polling status. For Kimi, also require
`kickoff_sent: true`; otherwise report the rescue command instead of claiming
the worker started. Verify `registry_recorded` when present. A registry failure
does not invalidate the live run, but later fast dispatch/context must fall back
to the retained run and handle fields.

For a managed run, create one dedicated mode-`0700` private directory and add
`--retain-coordinator`. When `HANDOFF_CREDENTIAL_DIR` is supplied, the launcher
uses that exact directory, so the coordinator token is exactly
`$handoff_private_root/coordinator.token`; never search for it with `find`.
Keep credential paths and contents out of prompts, terminal messages, and user
responses. Do not use the recovery or worker token during ordinary
coordination.

```bash
mkdir -p "$HOME/.local/state/agents/handoff/coordinators"
handoff_private_root=$(mktemp -d "$HOME/.local/state/agents/handoff/coordinators/<name>.XXXXXX")
chmod 700 "$handoff_private_root"
HANDOFF_CREDENTIAL_DIR="$handoff_private_root" \
  ~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent codex --retain-coordinator
```

Canonical monitored Claude launch:

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent claude --coordinator-state "$handoff_coordinator_state"
```

Canonical monitored Kimi Code launch:

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> \
  --agent kimi --coordinator-state "$handoff_coordinator_state"
```

## Launch on a remote SSH host

Use the SSH adapter when the user asks to run on a named remote box. The remote
host must already have key-based SSH access, tmux, the selected agent, and a
compatible installed `agents` package. If the host is stopped and the project
documents a lifecycle helper, use that helper only when the request authorizes
using the box. For the investment OCI box, the documented readiness command is:

```bash
~/projects/investment/src/scripts/oci_box_ctl.sh up
```

Canonical remote Claude launch on that box:

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <local-kickoff.md> \
  --agent claude --remote-host oci-box \
  --remote-cwd /home/opc/projects/investment \
  --remote-python /home/opc/miniforge3/envs/ml/bin/python \
  --coordinator-state "$handoff_coordinator_state"
```

The launcher sends the local kickoff and optional sibling `.goal` as JSON over
SSH stdin. It creates the authoritative run and credentials on the remote host,
starts remote tmux, and returns `run_dir` as an `ssh://` URI plus
`remote_host`, `remote_run_dir`, and `remote_handle`. Retain those remote fields;
`handoffctl` accepts the absolute `remote_run_dir`, not the URI, and must run on
the owning host through SSH. Never rsync, Git-sync, or mount an active remote run
directory as a second writable copy.

When not actively babysitting the run, require `coordinator_released: true` and
report the remote run URI and handle without polling; the local session watcher
observes the credential-free remote registry proxy. For an actively managed
remote run, choose one exact, unique, mode-`0700` path on the remote host and
supply it without discovery:

```bash
HANDOFF_REMOTE_CREDENTIAL_DIR=/home/opc/.local/state/agents/handoff/coordinators/<name>.<unique-id> \
  ~/projects/agents/scripts/handoff_agent.sh <name> <local-kickoff.md> \
  --agent claude --remote-host oci-box \
  --remote-cwd /home/opc/projects/investment \
  --remote-python /home/opc/miniforge3/envs/ml/bin/python \
  --retain-coordinator --coordinator-state "$handoff_coordinator_state"
```

Keep that path private and remember it exactly; the remote coordinator token is
`<remote-private-dir>/coordinator.token`. Execute status/read/doctor with the
remote Python over SSH. Execute coordinator mutations the same way with
`HANDOFF_COORDINATOR_TOKEN_FILE` set inside the remote command. Transfer body or
data through private files or SSH stdin, never shell interpolation. Construct
remote commands as shell-quoted argv and use `handoffctl --help` for exact
payload flags.

For a remote doorbell, append the durable message first, then send only the
opaque run ID and inbox sequence to the exact remote tmux handle, following
the manual-doorbell submit discipline (see "Monitoring behavior and
doorbells"). Probe and
rescue with `ssh <host> tmux capture-pane -p -t <remote-handle> -S -2000`; close
with `ssh <host> tmux kill-session -t <remote-handle>`. A lost SSH connection
means the state is unknown, not dead: do not rotate or launch a replacement
worker until the old one is fenced or confirmed stopped.

After a successful remote launch, also open a local viewer attached to the
worker's remote tmux session so the user can watch it live. Pick the
transport from the orchestrator's own context: inside cmux (an inherited
`CMUX_SURFACE_ID` and a reachable cmux connection), the **default viewer is
a remote-tmux mirror workspace grouped directly below the orchestrator's
workspace** (next section); inside tmux (`$TMUX` set), create a window in
the current session; with neither, skip and report the manual attach
command instead.

```bash
# tmux-hosted orchestrator
tmux new-window -d -n <name>-worker "ssh -t <host> tmux attach -t <remote-handle>"
```

The viewer is deliberately read-write: it is the **user's** window onto the
worker, and they may interact with it directly. The orchestrator itself never
types into the viewer — coordinator steering stays in the durable protocol,
and rescue/approval actions go through the exact `ssh <host> tmux ...`
commands above so they are tied to a verified probe. The viewer is cosmetic
transport: if it disconnects or is closed, the run is unaffected, and its
screen is never durable state.

### cmux viewer default: ssh-tmux mirror under the current workspace

Use the quiet helper — it owns the whole placement flow (RPC attach with no
window when the host connection is already up; otherwise `ssh-tmux
--no-focus` with immediate minimize, workspace move under the current
workspace, and best-effort close of the vacated window):

```bash
~/projects/agents/scripts/cmux_ssh_tmux_quiet.sh <host> <worker-session>
```

Always pass the worker session name(s): the mirror protocol is host-wide,
and an unfiltered run would also grab and re-place mirrors belonging to
other orchestrator sessions. Read the script header for details; do not
re-implement its steps inline. The mirror gives native scrolling,
selection, and splits instead of tmux copy-mode, appears on the worker
session as a `control-mode` client, and requires the "Remote tmux" beta
enabled in cmux Settings (no CLI toggle). The minimize step needs cmux to
have macOS Accessibility access; without it the mirror window simply stays
visible and the user closes it with ⌘W.

Three warts to respect. Zeroth, mirror lifetime: the mirror rides a tmux
control-mode client, and the remote tmux *server* exits when its last
session closes — so killing the final worker session (or the host
stopping) silently kills the mirror, and sessions created afterward live
on a new server the dead mirror cannot see. Re-run the quiet helper to
reconnect; the stale mirror workspace is just a dead view, and
`cmux rpc remote.tmux.attach '{"host":...,"session":...}'` revives it in
place with no window. First, leftover mirror-window husks: cmux may refill
a CLI-closed mirror window with a placeholder workspace instead of dying;
the helper minimizes such husks to the Dock, and AppleScript cannot reach
windows parked on other macOS Spaces — those need a manual ⌘W. Outside the
helper, `close-window` remains forbidden (see the layout-safety invariants
below). Second, the control-mode mapping is
**bidirectional**: renaming the mirrored workspace renames the *remote tmux
session itself*, silently breaking the registered handle that doorbells and
rescue commands target. Leave the mirrored workspace's name untouched while
the run is active; apply the grouping rename
(`workspace-action --action rename --title
"<orchestrator-workspace-name>-<worker-session>"`) only after the worker
finishes, or accept that the handle diverges and re-resolve it with
`ssh <host> tmux ls` before every send.

Fallback — plain attach tab: if the quiet helper fails (Remote tmux beta
disabled, connection error), fall back to an unfocused terminal tab beside
the current one in the current workspace, and tell the user the mirror is
available once they enable the beta (`cmux settings open`). Use a plain
terminal running `ssh -t`, not `cmux ssh` (its managed remote-workspace
daemon flow is unrelated and can sit disconnected):

```bash
cmux --id-format both new-surface --type terminal \
  --workspace "$CMUX_WORKSPACE_ID" --focus false      # parse the surface UUID
cmux rename-tab --workspace "$CMUX_WORKSPACE_ID" --surface <uuid> <name>-worker
cmux send --workspace "$CMUX_WORKSPACE_ID" --surface <uuid> \
  "ssh -t <host> tmux attach -t <remote-handle>"
cmux send-key --workspace "$CMUX_WORKSPACE_ID" --surface <uuid> enter
```

A tmux-hosted orchestrator has no mirror equivalent — plain attach in a
tmux window is already native there.

### Keep viewed sessions showing progress

A viewer is only useful if the pane has something to show. Agent workers
(Claude/Codex/Kimi) render their own TUI, so they need nothing extra. But
an ad-hoc tmux session running a batch command (a rebuild, a sweep, a bulk
download) with output redirected to a log file displays a blank pane that
reads as "dead" — the user cannot tell progress from failure. When
creating any tmux session the user may view, keep the pane live while
still capturing the log:

```bash
tmux new-session -d -s <name> \
  "<command> 2>&1 | tee <logfile>; echo EXIT:\${PIPESTATUS[0]} | tee -a <logfile>"
```

Capture the command's own exit status via `PIPESTATUS` (plain `$?` after a
pipe reports tee's status, not the command's). If a tool is genuinely
silent for long stretches, prefer a variant that emits periodic progress
(verbose/progress flags) so the pane visibly advances.

Every viewer placement or cleanup action must name the exact UUID of the
one thing it creates or removes — nothing positional, nothing by name
pattern, and never a sweep:

- **Snapshot before mutating layout.** Run `cmux --id-format both
  list-pane-surfaces --workspace "$CMUX_WORKSPACE_ID"` and
  `cmux --id-format both list-workspaces` first. After the mutation, list
  again and verify every pre-existing surface and workspace is still
  present. If anything is missing, stop all further layout actions
  immediately and report it to the user.
- **Close a viewer tab only with
  `cmux close-surface --surface <exact-uuid>`.** Never a `tab-action` sweep
  (`close-others`, `close-left`, `close-right`) — those close every *other*
  tab in the workspace, including the user's unrelated sessions and
  possibly the orchestrator's own surface.
- **Never run `cmux close-window`**, even on the vacated mirror window —
  targeting the wrong window destroys every workspace and session inside
  it. The user closes the vacated window with ⌘W.
- **Never run `cmux close-workspace`** except on the exact mirror-workspace
  UUID parsed from this run's own `ssh-tmux` output, and only when the user
  asked to remove the mirror. The mapping is bidirectional, so verify the
  remote worker session survived afterward (`ssh <host> tmux ls`).
- **Replace, then remove — by exact UUID.** When upgrading a viewer (e.g. a
  plain attach tab → mirror workspace), create and verify the new viewer
  first, then close only the old viewer's exact surface UUID. Never "clean
  up" the workspace by closing whatever else is there.

The launcher owns agent model/effort defaults. Use `--effort low` for a trivial
read-only lookup and the normal default for substantial coding. Kimi is launched
explicitly with the configured alias `--model kimi-code/k3` and thinking effort
`max`. The underlying model ID is lowercase `k3`; uppercase `K3` is not a valid
replacement. Kimi starts interactively, then receives a short instruction with
the resolved absolute path to the run's `kickoff.md`; never type the kickoff
contents into its terminal. Kimi does not receive the optional `.goal`
slash command because that command is not part of its documented CLI contract.
The launcher briefly lets the native Kimi TUI finish initializing after its
process appears; do not bypass that boundary with an earlier terminal send. In
both cmux and tmux, the launcher submits this Kimi instruction with
`Ctrl-J`: synthetic `Enter` can become an input newline and leave the text
sitting unsent.

Add `--wait-ready` only when the caller truly needs synchronous readiness
confirmation. A `.goal` launch already waits because the second command cannot
be delivered safely before the ready checkpoint.

## Observe and coordinate through `handoffctl`

Use the fixed helper:

```text
/opt/homebrew/Caskroom/miniconda/base/envs/ml/bin/python -m agents.orchestration.handoffctl
```

Read operations need no token:

```bash
<helper> runs list
<helper> runs show --run <selector>
<helper> context --run <selector>
<helper> status --run-dir <absolute-run-dir>
<helper> control show --run-dir <absolute-run-dir>
<helper> read --run-dir <absolute-run-dir> --journal outbox --after <cursor>
<helper> doctor --run-dir <absolute-run-dir>
```

Every successful terminal launch privately registers the run on its owning host;
a remote launch also registers a credential-free proxy on the coordinator host.
Selectors may be a run ID, unique prefix, task name, handle, or run URI. Public
registry output redacts credential directories. Prefer `context` after context
compaction or after removing a temporary kickoff source.

Treat `status.json`, `control.json`, and the journals as evidence. Do not infer
progress, acknowledgment, or success from terminal echoes.

When a cmux-launched worker successfully publishes a `result`, `handoffctl`
first makes the result and `awaiting_review` state durable, then sends a native
cmux notification titled `Handoff result ready` with body
`Awaiting coordinator review`, explicitly targeting the inherited
`CMUX_SURFACE_ID`. The alert is best-effort and automatic: missing cmux context,
command failure, or timeout does not invalidate the result and must not make the
worker retry publication or leave `awaiting_review`. The durable outbox event is
always authoritative. Pure tmux runs do not receive this cmux-native alert.

While actively coordinating, renew the coordinator lease at least every 60
seconds and before other coordinator mutations:

```bash
HANDOFF_COORDINATOR_TOKEN_FILE=<coordinator-token-file> \
  <helper> control renew --run-dir <absolute-run-dir>
```

If the user asks to monitor, babysit, or finish the handoff, keep the current
turn active and continue the renew/read/consume loop until the requested
terminal condition. Launch-only mode has already released the coordinator
lease and intentionally does not wait for worker readiness. For a later one-shot
instruction, use registry-backed `dispatch`; it performs the required takeover
without exposing or rediscovering credential paths. Use explicit low-level
recovery only when the registry is unavailable or repair is required.

Read outbox events after `control.outbox_cursor`. Handle every event through a
contiguous sequence, then call `control consume --through N`. Re-reading an
event is safe; use its stable `message_id` for idempotent handling.

Treat a blocking worker question as self-contained only when it states the
current stage and completed work, concrete evidence, the exact conflict, the
decision or authority needed, a recommended resolution, the consequences of
the available options, and actions intentionally deferred. Assume the worker
knows the kickoff while the coordinator does not know the worker's live
progress. Do not reconstruct missing context or guess. Send a `steer` requesting
the missing context, ring the normal opaque doorbell, and answer the substantive
question only after the worker supplements the durable outbox record.

For steering, answers, and reviews:

- Prefer one-shot registry dispatch for a new instruction after launch-only:

  ```bash
  <helper> dispatch --run <selector> --body-file <private-file-or-dash>
  ```

  Pass dynamic content through stdin (`--body-file -`) or a private file.
  `dispatch` takes over the released lease, appends the right message type for
  the worker's state, rings the exact doorbell, releases ownership, and removes
  its ephemeral coordinator token. State-aware linking: a worker `blocked` on a
  question gets `answer` tied to that exact question (a bare `steer` can never
  unblock it — the worker cannot advance across an unanswered blocking
  question); a worker `awaiting_review` gets `supersede` tied to the exact
  pending result so it can resume without accepting or mislabeling it; otherwise
  the body goes as `steer`. Verify which happened from the response's
  `answered_question` / `superseded_result` / `message.type` fields — when
  answering a blocking question, confirm `answered_question` matches the
  question you meant to answer. Remote dispatch performs the full owner-side
  transaction and tmux doorbell in one SSH invocation, so the fix requires an
  up-to-date `agents` package on the owning host; if a dispatched authorization
  ever still leaves the worker `blocked` with `message.type: steer`, the owning
  host runs a stale package — update it rather than hand-rolling a takeover.
- Write body and data to private files or structured stdin. Never interpolate
  user/model content into a shell program.
- Use low-level `send --type steer` only while already holding a managed lease.
- Use `send --type answer --reply-to <question-id>` for a worker question.
- Use `send --type review --reply-to <result-id>` with disposition
  `accepted` or `changes_requested`.
- `send` rings the worker's terminal doorbell automatically for a registered
  run and reports `doorbell_sent` in its response (`--no-doorbell` opts out).
  Confirm `doorbell_sent: true` after every send — including the final stop —
  and fall back to the manual doorbell procedure with the returned
  `message.seq` only when it is `false`.
- Supply the coordinator credential through
  `HANDOFF_COORDINATOR_TOKEN_FILE` or `--token-file`, never argv token bytes.

Run `<helper> <command> --help` for exact payload flags and schemas.

## Monitoring behavior and doorbells

The worker does **not** run a background inbox poller and the launcher does not
install hooks. Its kickoff contract tells it to read the inbox at startup,
resume/compaction, turn or stage boundaries, and before irreversible actions,
commits, and results. A message sent during a long model turn may wait until the
next checkpoint.

The default session watcher is started with `coordinator start`; do not
replace it with a time-limited generic observer — `watch --timeout` from your
own shell is for debugging only, never for waiting on worker events. For a
cmux coordinator its
doorbell attempts two complementary channels and records the accepted set in
the run's `last_doorbell_method` (e.g. `cmux_input+cmux_notify`): typed input
into the coordinator surface — counted only when the text visibly echoes, and
the only channel that pushes an idle orchestrator agent to act — plus the
visible `cmux notify` alert for the human. So the doorbell may arrive *as a
typed prompt in the orchestrator's own composer*; treat it as the trigger to
inspect the exact pending prefix:

```bash
<helper> coordinator pending --state "$handoff_coordinator_state"
```

Calling `coordinator pending` **acknowledges** the events it surfaces: it
records a per-run `acknowledged_through` cursor in the watcher state, and for a
**result** or review the watcher will not re-ring an event you have already
loaded. A strictly newer worker event still rings, and each worker is tracked
independently, so acking one worker never silences another. Ringing is
**state-aware**: a worker **blocked** on a question keeps re-ringing until it is
answered (a bare ack does not silence a stuck worker — it needs the answer, not
just to be seen), while pure progress checkpoints and terminal
(`succeeded`/`stopped`) states do not ring at all. This means the cure for a
repeating doorbell on a *result* is to **call `coordinator pending`**, not to
kill the watcher.
Do not close the watcher's surface to stop a repeating doorbell: the watcher is
session-scoped — other workers may still be running, and the orchestrator can
still spawn new ones that need watching — so it must live until the orchestrator
process exits, which it detects on its own. (A repeat doorbell can still occur
legitimately when delivery to the composer failed, e.g. an unechoed
`cmux_input`; `pending` also clears that, and if it truly cannot be delivered
the worker state is still durable in the outbox.)

To silence a run's current doorbell **without** consuming it or holding a lease
— a completed run you have parked in `awaiting_review` for viewing, or a
`blocked` run you are done with — use the credential-free:

```bash
<helper> coordinator dismiss --state "$handoff_coordinator_state" --run <selector>
```

`dismiss` records a per-run `dismissed_through` cursor; it stops ringing even a
persistent `blocked` nag, and a strictly newer worker event still re-rings.

For an ad-hoc foreground JSONL observation that is intentionally independent of
session-owned delivery — debugging or rescue only, never a way to wait for
worker events in a normal flow — run:

```bash
<helper> watch [--run <selector> ...] --interval 5 --timeout <seconds>
```

Omit `--run` to watch every registered run; add `--once` for one pass or
`--notify-cmux` for metadata-only alerts. This generic observer advances only
its private observer cursor: it does not consume protocol outbox events, review
a result, answer a question, or hold a coordinator lease. The detached session
watcher likewise never performs semantic actions; it only maintains independent
delivery cursors and sends opaque doorbells. Autonomous replies still require
an active coordinator agent with authority for the decision.

For urgent steering while you hold no active coordinator lease (external
intervention or an expired lease — `dispatch` refuses to run while a managed
lease is held; a managed coordinator driving the normal answer/review/stop
lifecycle uses `send`, which rings the doorbell itself):

1. Use `handoffctl dispatch` so the instruction is durably appended before the
   exact registered handle is touched.
2. Confirm `doorbell_sent: true`; otherwise use the returned durable message
   sequence and stored handle for a narrow manual doorbell.
3. Never type the steering body or credentials into cmux/tmux. A doorbell
   contains only `Check handoff run <run-id>; inbox now through seq <N>.`

A doorbell queues behind a running turn; it cannot interrupt the model. Hooks
remain an optimization; the durable journal is authoritative even when a
watcher or doorbell fails.

Manual-doorbell submit discipline: agent TUIs (Claude/Codex/Kimi) coalesce a
same-burst text+Enter into a bracketed paste, so the Enter becomes an input
newline and the doorbell sits unsent in the composer while looking delivered.
Launcher/`handoffctl` doorbells handle this automatically (settle + verify +
retry). When sending a doorbell manually, send the literal text and the Enter
as two separate commands with ~1s between them, then capture the pane and
check the bottom lines: if the doorbell text still sits in the composer, send
one more bare Enter (harmless if it already submitted). Never assume delivery
from a zero exit code; on the worker side, only an advanced `inbox_cursor`
proves receipt.

Probe/capture patterns for rescue only:

- cmux: `cmux read-screen --surface <uuid> --scrollback`
- tmux: `tmux capture-pane -p -t <name> -S -2000`

If semantic status is stale, distinguish a live expected agent process from a
folder-trust TUI or dead session before taking action. Never rotate a worker
unless the old process is confirmed dead. If coordinator lease ownership has
expired, use explicit recovery-token takeover; do not keep trying the stale
coordinator token.

## Terminal rescue and approval

Use terminal key input only when the worker is blocked below the agent loop and
therefore cannot consume a protocol message. Examples include a folder-trust
dialog, an already-authorized tool permission prompt, or a known
non-destructive “press Enter to continue” screen.

Before sending any key:

1. Resolve the exact launch handle; never act on a positional or guessed tab.
2. Probe the expected process and capture a fresh screen from that handle.
3. Match a specific prompt and verify its cwd/action against the user's launch
   request and permission policy.
4. Act automatically only when the prompt's effect is already authorized.
   Folder trust is eligible only for the exact repository the user asked to
   launch. Escalate destructive commands, expanded permissions, authentication,
   secret entry, or any ambiguous prompt to the user.
5. Send one exact key action, recapture the screen, and verify that the expected
   agent process or semantic status advances.

Canonical Enter actions after those checks:

```bash
cmux send-key --surface <uuid> enter
tmux send-keys -t <name> Enter
```

Never run a generic loop that repeatedly presses Enter, never infer permission
from the currently highlighted default alone, and never treat disappearance of
the dialog as semantic task success. Terminal approval is an operational rescue
action; it does not advance journal cursors or replace an inbox/outbox event.

To close a single viewer tab, use exactly
`cmux close-surface --surface <exact-surface-handle>` — never a
`tab-action` sweep (`close-others`, `close-left`, `close-right`) and never
`close-window`/`close-workspace`: the layout-safety invariants in the
remote-launch section apply to every cleanup, local or remote. A cleanup
action may only ever name the exact surface being removed.

## Close sessions quickly

Treat an explicit request to "close", "kill", or "terminate" handoff sessions
as a transport-level action. Resolve each exact stored handle, perform at most
one read-only existence check, and close all requested workers directly. Do not
take over or renew a coordinator lease, append a protocol stop, wait for worker
acknowledgment, consume journals, or run doctor before closing.

```bash
cmux close-surface --surface <exact-surface-handle>
tmux kill-session -t <exact-session-handle>
```

For multiple workers, issue independent closes without serial protocol loops.
Never close the orchestrator's own surface unless the user explicitly names it,
and never widen a close beyond the named handles — no `tab-action` sweeps,
`close-window`, or `close-workspace` (except an exact mirror-workspace UUID
per the layout-safety invariants).
Afterward, report whether each handle closed; the durable run may truthfully
remain nonterminal or show an unconsumed stop, and that stale semantic state
must not delay terminal closure.

Use the slower protocol path only when the user asks to stop gracefully,
preserve/report progress, or complete review/integration. Even then, bound the
grace period; if the worker is unresponsive and the user authorized closure,
close the exact transport handle and report that protocol acknowledgment was
not obtained.

## Review and finish

1. Consume the worker's `result` event.
2. Verify its named artifacts, reported HEAD/dirty state, repository diff, and
   test evidence directly. A run may start or finish with pre-existing changes;
   never require the worker to stash, discard, or commit unrelated user work.
3. Send an accepted or changes-requested review tied to that exact result ID.
4. Wait for the worker to consume acceptance and emit `succeeded`; do not
   confuse worker success with coordinator acceptance or integration. Waiting
   means watching for the watcher's next doorbell, not polling yourself.
5. Record `control integrate` or `control abandon`, then send a graceful stop
   and confirm its `doorbell_sent` — without the doorbell the idle worker
   never learns the run is over.
6. Run read-only `doctor`. Use repair flags only for identified, explicit
   recovery; never repair implicitly.

## Launch a Codex desktop-app task

Use this transport only when the coordinator is itself in the Codex app, the
app task controls are available, and the user explicitly asks for a new or
background Codex task. Do not create a task merely because the user asks how
the mode works. The created task is user-owned and appears in the app.

1. Prepare the same durable, self-contained kickoff described above.
2. Call `list_projects`, then select the exact saved project that owns the
   target repository on the intended host. Do not substitute a projectless
   task or a similarly named project.
3. Choose the task environment deliberately:
   - Use `local` when the worker must share the current checkout, including a
     newly written kickoff or authorized uncommitted state. Do not keep editing
     that checkout concurrently with the worker.
   - Use `worktree` for isolation only when the kickoff and required inputs are
     reachable from the worktree's base. Specify `startingState` only when the
     user explicitly requests a particular branch/ref or asks to include the
     current working tree. Never launch a worktree that cannot read its
     authoritative kickoff.
4. Call `create_thread` with that `projectId`, environment, and this initial
   prompt:

   ```text
   Implement per <kickoff-path> — read it fully first and treat it as authoritative.
   ```

   Omit model and reasoning overrides unless the user explicitly requests
   them. Retain the returned `threadId` and `hostId`; a queued worktree may
   initially return only `clientThreadId` and is not yet waitable.
5. After successful creation, report the created task using the app's
   `created-thread` directive. Do not use `fork_thread`: inherited conversation
   history defeats the clean, self-contained kickoff boundary. Do not use
   `handoff_thread`: it moves an existing task rather than creating a worker.

For launch-only mode, return as soon as creation succeeds. Do not read or wait
on the new task.

For a managed run, use `wait_threads` with one target, its latest cursor, and
bounded waits. Use `read_thread` only when the compact status lacks needed
detail, and use `send_message_to_thread` for steering or answers already
authorized by the user's instructions. Surface any request for new authority,
credentials, approval, or a material user choice instead of deciding it for
the worker. Do not narrate unchanged snapshots. Verify artifacts, diffs, and
tests directly before accepting the result.

This app-native transport does not create a local-v1 run directory, lease, or
journal. Codex task status/history is authoritative for orchestration, while
the kickoff remains authoritative for implementation scope.

If the app task controls are unavailable, fall back to manual creation and give
the user this one-line prompt:

```text
Implement per docs/plans/<kickoff>.md — read it fully first.
```

State clearly that the manual fallback provides no automated monitoring or
steering.

## Safety rules

- Never expose token contents or credential paths in prompts, doorbells, logs,
  notifications, or user-facing summaries.
- Never mutate an active worker's checkout from the coordinator. Send an
  `input-changed` or `base-changed` message and let the worker incorporate it.
- Keep worker turns/checkpoints bounded when steering latency matters.
- Do not treat a live terminal, model prose, or screen text as durable state.
- Do not commit, push, stop, integrate, abandon, repair, or rotate unless the
  user's request authorizes that action.

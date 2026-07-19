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

Use launch-only mode unless the user asks to monitor, babysit, steer, review,
or finish the worker. Do not run `--help` before a canonical launch; inspect it
only for an uncommon override or troubleshooting.

For launch-only mode, invoke the launcher directly. It returns as soon as the
session is started (and, for Kimi, its run-specific kickoff pointer is delivered),
then releases coordinator ownership itself. Do not locate credentials or wait
for the worker-ready checkpoint. Use a lowercase `[a-z0-9-]` task slug.

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> --agent codex
```

With no `--backend`, the launcher uses cmux only when the orchestrator process
inherits a cmux workspace context and the cmux connection is reachable; it
launches the worker into that workspace. Otherwise it uses tmux. Pass
`--backend cmux` or `--backend tmux` only when the user asks for an override or
an operational constraint requires it.

Parse the launcher's JSON response and retain `run_dir`, `transport`, and
`handle`. In launch-only mode verify `coordinator_released` is true; report the
run and handle immediately without polling status. For Kimi, also require
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

Canonical Claude launch:

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> --agent claude
```

Canonical Kimi Code launch:

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <kickoff.md> <repo> --agent kimi
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
  --remote-python /home/opc/miniforge3/envs/ml/bin/python
```

The launcher sends the local kickoff and optional sibling `.goal` as JSON over
SSH stdin. It creates the authoritative run and credentials on the remote host,
starts remote tmux, and returns `run_dir` as an `ssh://` URI plus
`remote_host`, `remote_run_dir`, and `remote_handle`. Retain those remote fields;
`handoffctl` accepts the absolute `remote_run_dir`, not the URI, and must run on
the owning host through SSH. Never rsync, Git-sync, or mount an active remote run
directory as a second writable copy.

In launch-only mode, require `coordinator_released: true` and report the remote
run URI and handle without polling. For a managed remote run, choose one exact,
unique, mode-`0700` path on the remote host and supply it without discovery:

```bash
HANDOFF_REMOTE_CREDENTIAL_DIR=/home/opc/.local/state/agents/handoff/coordinators/<name>.<unique-id> \
  ~/projects/agents/scripts/handoff_agent.sh <name> <local-kickoff.md> \
  --agent claude --remote-host oci-box \
  --remote-cwd /home/opc/projects/investment \
  --remote-python /home/opc/miniforge3/envs/ml/bin/python \
  --retain-coordinator
```

Keep that path private and remember it exactly; the remote coordinator token is
`<remote-private-dir>/coordinator.token`. Execute status/read/doctor with the
remote Python over SSH. Execute coordinator mutations the same way with
`HANDOFF_COORDINATOR_TOKEN_FILE` set inside the remote command. Transfer body or
data through private files or SSH stdin, never shell interpolation. Construct
remote commands as shell-quoted argv and use `handoffctl --help` for exact
payload flags.

For a remote doorbell, append the durable message first, then send only the
opaque run ID and inbox sequence to the exact remote tmux handle. Probe and
rescue with `ssh <host> tmux capture-pane -p -t <remote-handle> -S -2000`; close
with `ssh <host> tmux kill-session -t <remote-handle>`. A lost SSH connection
means the state is unknown, not dead: do not rotate or launch a replacement
worker until the old one is fenced or confirmed stopped.

After a successful remote launch, also open a local viewer attached to the
worker's remote tmux session so the user can watch it live — placed exactly
like a local worker: a new unfocused tab beside the current one, not a new
workspace or window. Pick the transport from the orchestrator's own context:
inside cmux (an inherited `CMUX_SURFACE_ID` and a reachable cmux connection)
create a terminal surface in the current workspace; otherwise, inside tmux
(`$TMUX` set) create a window in the current session; with neither, skip and
report the manual attach command instead.

```bash
# cmux-hosted orchestrator: unfocused tab in the current workspace,
# then type the attach command into it (same pattern as the local launcher)
cmux --id-format both new-surface --type terminal \
  --workspace "$CMUX_WORKSPACE_ID" --focus false      # parse the surface UUID
cmux rename-tab --workspace "$CMUX_WORKSPACE_ID" --surface <uuid> <name>-worker
cmux send --workspace "$CMUX_WORKSPACE_ID" --surface <uuid> \
  "ssh -t <host> tmux attach -t <remote-handle>"
cmux send-key --workspace "$CMUX_WORKSPACE_ID" --surface <uuid> enter
# tmux-hosted orchestrator
tmux new-window -d -n <name>-worker "ssh -t <host> tmux attach -t <remote-handle>"
```

The attach is deliberately read-write: it is the **user's** window onto the
worker, and they may interact with it directly. The orchestrator itself never
types into the viewer — coordinator steering stays in the durable protocol,
and rescue/approval actions go through the exact `ssh <host> tmux ...`
commands above so they are tied to a verified probe. Use a plain terminal
running `ssh -t`, not `cmux ssh` (its managed remote-workspace daemon flow is
unrelated and can sit disconnected) and not a new workspace (wrong placement).
The viewer is cosmetic transport: if it disconnects or is closed, the run is
unaffected, and its screen is never durable state.

Optional cmux-only upgrade when the user wants heavy scrollback or richer
interaction: `cmux ssh-tmux <host> --no-focus` mirrors the host's tmux over
control mode (`tmux -CC`) — each remote session becomes a workspace, with
native scrolling, selection, and splits instead of tmux copy-mode. It
requires the "Remote tmux" beta enabled in cmux Settings (there is no CLI
toggle; `cmux settings open` and ask the user), mirrors **all** tmux sessions
on the host, and appears on the worker session as a `control-mode` client.
The mirror opens in a dedicated new window; since the session→workspace
mapping is fixed, it can never be a tab inside an existing workspace, but the
mirrored workspace can be pulled into the orchestrator's window so no extra
app window remains in use, and renamed so it groups with its owner in the
sidebar — `<orchestrator-workspace-name>-<worker-session>`:

```bash
cmux move-workspace-to-window --workspace <mirror-workspace-uuid> \
  --window <orchestrator-window-uuid>
cmux workspace-action --action rename --workspace <mirror-workspace-uuid> \
  --title "<orchestrator-workspace-name>-<worker-session>"
```

Known cosmetic wart: the vacated mirror window refills itself with a
placeholder workspace when closed via CLI — tell the user to close it with
⌘W rather than looping on `close-window`. Offer ssh-tmux as an alternative
when the user asks for better scrolling; keep the plain attach tab as the
default placement. A tmux-hosted orchestrator has no equivalent — plain
attach is already native there.

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

For steering, answers, and reviews:

- Prefer one-shot registry dispatch for a new instruction after launch-only:

  ```bash
  <helper> dispatch --run <selector> --body-file <private-file-or-dash>
  ```

  Pass dynamic content through stdin (`--body-file -`) or a private file.
  `dispatch` takes over the released lease, appends `steer`, rings the exact
  doorbell, releases ownership, and removes its ephemeral coordinator token. If
  the worker is `awaiting_review`, it appends `supersede` tied to the exact
  pending result so the worker can resume without accepting or mislabeling it.
  Remote dispatch performs the full owner-side transaction and tmux doorbell in
  one SSH invocation.
- Write body and data to private files or structured stdin. Never interpolate
  user/model content into a shell program.
- Use low-level `send --type steer` only while already holding a managed lease.
- Use `send --type answer --reply-to <question-id>` for a worker question.
- Use `send --type review --reply-to <result-id>` with disposition
  `accepted` or `changes_requested`.
- Supply the coordinator credential through
  `HANDOFF_COORDINATOR_TOKEN_FILE` or `--token-file`, never argv token bytes.

Run `<helper> <command> --help` for exact payload flags and schemas.

## Monitoring behavior and doorbells

The worker does **not** run a background inbox poller and the launcher does not
install hooks. Its kickoff contract tells it to read the inbox at startup,
resume/compaction, turn or stage boundaries, and before irreversible actions,
commits, and results. A message sent during a long model turn may wait until the
next checkpoint.

For asynchronous coordinator observation, run:

```bash
<helper> watch [--run <selector> ...] --interval 5 --timeout <seconds>
```

Omit `--run` to watch every registered run; add `--once` for one pass or
`--notify-cmux` for metadata-only alerts. Keep the current orchestrator turn
active and handle each emitted JSONL event. The watcher advances only its
private observer cursor: it does not consume protocol outbox events, review a
result, answer a question, or hold a coordinator lease. A persistent watcher
can detect and notify while the model is idle, but autonomous replies still
require an active coordinator agent with authority for the decision.

For urgent steering:

1. Use `handoffctl dispatch` so the instruction is durably appended before the
   exact registered handle is touched.
2. Confirm `doorbell_sent: true`; otherwise use the returned durable message
   sequence and stored handle for a narrow manual doorbell.
3. Never type the steering body or credentials into cmux/tmux. A doorbell
   contains only `Check handoff run <run-id>; inbox now through seq <N>.`

A doorbell queues behind a running turn; it cannot interrupt the model. Hooks
remain an optimization; the durable journal is authoritative even when a
watcher or doorbell fails.

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
Never close the orchestrator's own surface unless the user explicitly names it.
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
   confuse worker success with coordinator acceptance or integration.
5. Record `control integrate` or `control abandon`, then send a graceful stop.
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

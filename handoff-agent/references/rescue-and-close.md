# Manual doorbells, terminal rescue, and closing sessions

You MUST read this before terminal rescue, closing sessions, or any manual
doorbell.

## Manual doorbell (submit discipline)

Agent TUIs (Claude/Codex/Kimi/pi) coalesce a same-burst text+Enter into a
bracketed paste, so the Enter becomes an input newline and the doorbell sits
unsent in the composer while looking delivered. Launcher/`handoffctl`
doorbells handle this automatically (settle + verify + retry). For the narrow
manual fallback — e.g. a `send` that reported `doorbell_sent: false` and
returned a durable `message.seq` — use the scripted helper:

```bash
~/projects/agents/scripts/handoff_doorbell.sh --run-id <id> --seq <n> --cmux-surface <uuid>
~/projects/agents/scripts/handoff_doorbell.sh --run-id <id> --seq <n> --tmux-session <name>
~/projects/agents/scripts/handoff_doorbell.sh --run-id <id> --seq <n> --tmux-session <remote-handle> --remote-host <ssh-host>
```

It sends the fixed opaque text `Check handoff run <id>; inbox now through seq
<n>.`, then Enter as a SEPARATE command ~1s later, captures the pane, and if
the doorbell text still sits in the bottom lines sends one more bare Enter
(harmless if it already submitted).

Retained manual two-step procedure, as background/fallback if the helper is
unavailable: send the literal text and the Enter as two separate commands with
~1s between them — `cmux send --surface <uuid> "<text>"` then `cmux send-key
--surface <uuid> enter`, or `tmux send-keys -t <name> -l "<text>"` then
`tmux send-keys -t <name> Enter` (remote tmux: the same via `ssh <host> tmux
...`) — then capture the pane (`cmux read-screen --surface <uuid>` or
`tmux capture-pane -p -t <name> -S -50`) and check the bottom lines; if the
doorbell text still sits in the composer, send one more bare Enter.

Never assume delivery from a zero exit code; on the worker side, only an
advanced `inbox_cursor` proves receipt.

## Probe/capture patterns (rescue only)

- cmux: `cmux read-screen --surface <uuid> --scrollback`
- tmux: `tmux capture-pane -p -t <name> -S -2000`

If semantic status is stale, distinguish a live expected agent process from a
folder-trust TUI or dead session before taking action. Never rotate a worker
unless the old process is confirmed dead. If orchestrator lease ownership has
expired, use explicit recovery-token takeover; do not keep trying the stale
orchestrator token.

Try `conclude`/`dispatch` first — they take over with their own ephemeral
token and cover ordinary close-out and steering. Manual takeover is
repair-only, for when they refuse or the registry is unavailable:

```bash
handoffctl control takeover --run-dir <absolute-run-dir> \
  --recovery-token-file <credential-dir>/recovery.token \
  --new-token-file <fresh-path-outside-run-dir> \
  --reason-file <private-file>
```

The recovery token is `recovery.token` in the run's credential directory —
for a managed run, the exact private directory created at launch. The
`--new-token-file` must be a fresh, non-existent path outside the run
directory: an existing path exits 4 rather than overwriting, and a path
inside the run directory is refused outright. Without `--force`, takeover
also exits 4 while the recorded lease is still active; use `--force` only for
a provably stale lease — its holder confirmed dead — never to shortcut a live
one.

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

### Codex folder-trust dialog

The launcher handles this automatically for new Codex runs, local and remote
alike (local cmux/tmux launches clear the dialog in the launched surface before
releasing the orchestrator, reporting `folder_trust_rescued`). Use this manual
fallback only for an older run or a launcher result with `startup_unconfirmed`.
For the exact dialog with `1. Yes, continue` selected, use `C-m` for a tmux
worker:

```bash
ssh <host> tmux send-keys -t <remote-handle> C-m
ssh <host> tmux capture-pane -p -t <remote-handle> -S -120
```

Use this only after the five terminal-rescue checks above confirm the exact
user-authorized repository. Send it once, recapture, and require evidence that
the Codex agent started or the semantic status advanced. Do not retry keys in a
loop, use a protocol steer for the dialog, or treat the disappeared prompt as
task completion.

Never run a generic loop that repeatedly presses Enter, never infer permission
from the currently highlighted default alone, and never treat disappearance of
the dialog as semantic task success. Terminal approval is an operational rescue
action; it does not advance journal cursors or replace an inbox/outbox event.

To close a single viewer tab, use exactly
`~/projects/agents/scripts/cmux_close_surface_safe.sh --surface <exact-surface-handle>`
— never a `tab-action` sweep (`close-others`, `close-left`, `close-right`) and
never `close-window`/`close-workspace`: the layout-safety invariants in
`remote-and-viewers.md` apply to every cleanup, local or remote. A cleanup
action may only ever name the exact surface being removed.

## Close sessions quickly

Treat an explicit request to "close", "kill", or "terminate" handoff sessions
as a transport-level action. Resolve each exact stored handle, perform at most
one read-only existence check, and close all requested workers directly. Do not
take over or renew an orchestrator lease, append a protocol stop, wait for worker
acknowledgment, consume journals, or run doctor before closing.

```bash
cmux close-surface --surface <exact-surface-handle>
tmux kill-session -t <exact-session-handle>
```

(For a cmux viewer tab, prefer the guarded
`~/projects/agents/scripts/cmux_close_surface_safe.sh` wrapper above; the raw
`close-surface` form here is for closing *worker* surfaces where the exact
handle is already verified and no other layout doubt exists.)

For multiple workers, issue independent closes without serial protocol loops.
Never close the orchestrator's own surface unless the user explicitly names it,
and never widen a close beyond the named handles — no `tab-action` sweeps,
`close-window`, or `close-workspace` (except an exact mirror-workspace UUID
per the layout-safety invariants).
Afterward, report whether each handle closed; the durable run may truthfully
remain unmarked as finished, and that accurate semantic state must not delay
transport closure. A later `runs clean --dead` may reap it only after the
transport positively reports the session absent.

Use the protocol path when the user asks to preserve/report progress or
complete review/integration. `conclude --stop` or `stop` marks the run finished
but does not ask the TUI to exit; session termination remains the cleanup or
explicit close operation. If the worker is unresponsive and the user
authorized closure, close the exact transport handle and report that no fresh
protocol acknowledgment was obtained.

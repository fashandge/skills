# Remote launch, viewers, and cmux layout safety

You MUST read this before any remote launch, viewer creation, or cmux layout
mutation. Core decision rules and local launches live in `../SKILL.md`; the
manual-doorbell, rescue, and close procedures live in `rescue-and-close.md`.

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
  --orchestrator-state "$handoff_orchestrator_state"
```

Remote Codex automatically uses a 30-second ready gate and, only on timeout,
captures the exact tmux handle once to rescue Codex's exact folder-trust dialog
for the supplied `--remote-cwd`. No extra flags are needed:

```bash
~/projects/agents/scripts/handoff_agent.sh <name> <local-kickoff.md> \
  --agent codex --remote-host oci-box \
  --remote-cwd /home/opc/projects/investment \
  --remote-python /home/opc/miniforge3/envs/ml/bin/python \
  --orchestrator-state "$handoff_orchestrator_state"
```

The JSON reports `folder_trust_rescued` or `startup_unconfirmed`. Inspect the
terminal manually only for the latter; otherwise continue with normal
event-driven coordination. Pass `--readiness-timeout` only to override 30
seconds.

The launcher sends the local kickoff and optional sibling `.goal` as JSON over
SSH stdin. It creates the authoritative run and credentials on the remote host,
starts remote tmux, and returns `run_dir` as an `ssh://` URI plus `remote_host`,
`remote_run_dir`, and `remote_handle`. Retain those remote fields; `handoffctl`
accepts the absolute `remote_run_dir`, not the URI, and must run on the owning
host through SSH. Never rsync, Git-sync, or mount an active remote run
directory as a second writable copy.

When not actively babysitting the run, require `orchestrator_released: true` and
report the remote run URI and handle without polling; the local session watcher
observes the credential-free remote registry proxy. For an actively managed
remote run, choose one exact, unique, mode-`0700` path on the remote host and
supply it without discovery:

```bash
HANDOFF_REMOTE_CREDENTIAL_DIR=/home/opc/.local/state/agents/handoff/orchestrators/<name>.<unique-id> \
  ~/projects/agents/scripts/handoff_agent.sh <name> <local-kickoff.md> \
  --agent claude --remote-host oci-box \
  --remote-cwd /home/opc/projects/investment \
  --remote-python /home/opc/miniforge3/envs/ml/bin/python \
  --retain-orchestrator --orchestrator-state "$handoff_orchestrator_state"
```

Keep that path private and remember it exactly; the remote orchestrator token is
`<remote-private-dir>/coordinator.token`. Execute status/read/doctor with the
remote Python over SSH. Execute orchestrator mutations the same way with
`HANDOFF_COORDINATOR_TOKEN_FILE` set inside the remote command. Transfer body or
data through private files or SSH stdin, never shell interpolation. Construct
remote commands as shell-quoted argv and use `handoffctl --help` for exact
payload flags. (Both hosts now run the post-rename package: new runs use
`orchestrator.token` and `HANDOFF_ORCHESTRATOR_TOKEN_FILE` on either side.
Credential files created before the rename keep their `coordinator.token`
names, so read the exact path from the run rather than assuming a spelling.)

For a remote doorbell, append the durable message first, then send only the
opaque run ID and inbox sequence to the exact remote tmux handle, following the
manual-doorbell submit discipline (see `rescue-and-close.md`; the short form is
`~/projects/agents/scripts/handoff_doorbell.sh --run-id <id> --seq <n>
--tmux-session <remote-handle> --remote-host <host>`). Probe and rescue with
`ssh <host> tmux capture-pane -p -t <remote-handle> -S -2000`; close with
`ssh <host> tmux kill-session -t <remote-handle>`. A lost SSH connection means
the state is unknown, not dead: do not rotate or launch a replacement worker
until the old one is fenced or confirmed stopped.

## Open a viewer after a remote launch

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
types into the viewer — orchestrator steering stays in the durable protocol,
and rescue/approval actions go through the exact `ssh <host> tmux ...`
commands above so they are tied to a verified probe. The viewer is cosmetic
transport: if it disconnects or is closed, the run is unaffected, and its
screen is never durable state.

## cmux viewer default: ssh-tmux mirror under the current workspace

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

## Keep viewed sessions showing progress

A viewer is only useful if the pane has something to show — and the pane
must never own the process. A command run AS the tmux pane command dies
with the pane, and the mirror mapping is bidirectional, so a user
accidentally ⌘W-ing a mirror workspace kills the remote session, SIGHUPs
the pane's process group, and destroys hours of batch work (this happened
2026-07-20 to a resumable-only-by-luck codex run). Agent workers
(Claude/Codex/Kimi) launched by the handoff launcher accept this coupling
deliberately — the durable protocol survives them and `codex exec resume`
can revive a killed worker — but ad-hoc batch commands (a rebuild, a
sweep, a bulk download) must be decoupled. Use the logged-runner helper
for any non-TUI batch job the user may view:

```bash
~/projects/agents/scripts/tmux_run_logged.sh <session-name> <logfile> -- <command...>
```

It runs the command under `setsid nohup` (immune to tmux/SSH/viewer
death) with output to the logfile plus a final `EXIT:<code>` line, and
creates a disposable tmux view session running `tail -F <logfile>` —
closing the view (or its mirror workspace) kills only the tail. Put any
completion chain (notification, watchdog re-arm) inside the command
passed to the helper, never in a tmux session. If a tool is genuinely
silent for long stretches, prefer a variant that emits periodic progress
(verbose/progress flags) so the pane visibly advances.

## Layout-safety invariants

Every viewer placement or cleanup action must name the exact UUID of the
one thing it creates or removes — nothing positional, nothing by name
pattern, and never a sweep:

- **Snapshot before mutating layout.** Run `cmux --id-format both
  list-pane-surfaces --workspace "$CMUX_WORKSPACE_ID"` and
  `cmux --id-format both list-workspaces` first. After the mutation, list
  again and verify every pre-existing surface and workspace is still
  present. If anything is missing, stop all further layout actions
  immediately and report it to the user.
- **Close a viewer tab only through the guarded helper:**

  ```bash
  ~/projects/agents/scripts/cmux_close_surface_safe.sh --surface <exact-uuid>
  ```

  It runs the snapshot/verify procedure above around exactly one
  `cmux close-surface --surface <exact-uuid>`. Never a `tab-action` sweep
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

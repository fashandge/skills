# Launcher internals and delivery details

Background mechanics condensed out of `../SKILL.md`'s core. Nothing here
changes the core decision rules; read this when you need the details behind
them.

## Watcher hosting modes

`orchestrator start` picks the watcher's hosting by transport (`--mode auto`):
cmux orchestrators get a **surface-hosted** watcher — a terminal tab named
`watcher: <orchestrator workspace>` parked in the bottom `handoff-watchers`
workspace, kept inside the cmux process tree so typed doorbells and native
alerts work — while tmux and native-app orchestrators keep the fully detached
daemon. Closing the watcher tab (or the `handoff-watchers` workspace) kills
the watcher; rerun `orchestrator start` to relaunch it. Do not force
`--mode detached` for a cmux orchestrator unless degraded transient
macOS-banner doorbells are acceptable (the cmux socket rejects out-of-tree
clients).

## Model/effort defaults and Kimi delivery quirks

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

## Readiness waits

Add `--wait-ready` only when the caller truly needs synchronous readiness
confirmation. A `.goal` launch already waits because the second command cannot
be delivered safely before the ready checkpoint.

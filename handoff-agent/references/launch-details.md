# Launcher internals and delivery details

Background mechanics condensed out of `../SKILL.md`'s core. Nothing here
changes the core decision rules; read this when you need the details behind
them.

## Watcher hosting modes

`orchestrator start` picks the watcher's hosting by transport (`--mode auto`):
cmux orchestrators get a **surface-hosted** watcher — a terminal tab named
`watcher: <orchestrator workspace>` parked in the bottom `handoff-watchers`
workspace, kept inside the cmux process tree so typed doorbells and native
alerts work — while herdr, tmux, and native-app orchestrators keep the fully
detached daemon. Closing the watcher tab (or the `handoff-watchers` workspace)
kills the watcher; rerun `orchestrator start` to relaunch it. Do not force
`--mode detached` for a cmux orchestrator unless degraded transient
macOS-banner doorbells are acceptable (the cmux socket rejects out-of-tree
clients).

herdr needs no such hosting: its server accepts socket clients from anywhere on
the host, so a detached watcher types into the orchestrator's composer and
raises native notifications exactly as an in-tree one would. `--mode surface`
is rejected for a herdr orchestrator rather than silently ignored.

A herdr doorbell is delivered with `agent prompt`, which submits the text and
Enter in one call against the pane's live bracketed-paste mode — so the
settle-and-retry discipline the cmux and tmux paths need does not apply, and a
companion `notification show` fires as the visible alert. The composer guard
additionally reads herdr's lifecycle state: a `blocked` orchestrator (herdr
recognized an approval or question UI) defers, because the keystrokes a
doorbell submits would answer that dialog instead of landing in a composer. A
`working` orchestrator does not defer — input typed during a turn simply
queues.

## Model/effort defaults and Kimi delivery quirks

The launcher owns agent model/effort defaults. Use `--effort low` for a trivial
read-only lookup and the normal default for substantial coding. pi is launched
with `--model deepseek/deepseek-v4-flash` and `--thinking max` (the launcher
carries one model string, so it uses pi's `provider/id` form rather than the
separate `--provider`/`--model` flags `delegate-first` spells out); its cheap
1M window suits bulk mechanical work, and it is the one worker whose kickoff is
plain argv with no delivery quirk. Its `DEEPSEEK_API_KEY` arrives through
`env.build_env()`, so a pi worker launched from a launchd/cron-context
orchestrator is authenticated like any other. pi has no tool-approval gate at all — no
sandbox, so it never stalls on a permission prompt — and its one interactive
gate, the project-trust dialog, is always resolved on the command line
(`--approve` under the default `bypassPermissions`, `--no-approve` otherwise)
because that dialog blocks below the agent loop. Kimi is launched
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
confirmation. Remote Codex is automatic exception: it uses a 30-second ready
gate so the local launcher can deterministically rescue its exact folder-trust
dialog if needed. A `.goal` launch already waits because the second command
cannot be delivered safely before the ready checkpoint.

## Codex folder-trust gate

Within that 30-second gate the launcher makes at most one exact-handle tmux
capture and sends `C-m` only when it sees Codex's exact folder-trust dialog for
the supplied `--remote-cwd`; otherwise it returns `startup_unconfirmed`.
`folder_trust_rescued` means the transport rescue succeeded — resume normal
event-driven behavior. `--readiness-timeout` overrides the bounded wait.

Local Codex launches (cmux/tmux) get the same rescue in the launched surface,
independent of `--wait-ready`: the launcher polls the surface, and on Codex's
exact dialog for the launch `cwd` it presses Enter once, then reports
`folder_trust_rescued`. Because a narrow surface truncates or wraps the
`You are in <cwd>` line, the directory is verified by prefix, not exact match; a
dialog naming any other directory is left untouched and returns
`startup_unconfirmed`. An already-trusted directory (no dialog) returns promptly
after a short grace rather than blocking for the whole timeout.

## Result notification

When a herdr- or cmux-launched worker publishes a `result`, `handoffctl` makes
the result and `awaiting_review` state durable *first*, then sends a
best-effort native notification titled `Handoff result ready` with body
`Awaiting orchestrator review` — through `herdr notification show` when
`HERDR_PANE_ID` is inherited, or targeting the inherited `CMUX_SURFACE_ID`.
Pure tmux runs get no such alert. Missing cmux context, command failure, or timeout must never make the
worker retry publication or leave `awaiting_review`.

## Doorbell delivery mechanics

Why the core's doorbell rules are what they are:

- A cmux orchestrator's doorbell uses two channels, recorded in the run's
  `last_doorbell_method` (e.g. `cmux_input+cmux_notify`): typed input into the
  orchestrator surface — counted only when the text visibly echoes, and the only
  channel that pushes an idle orchestrator agent to act — plus a visible
  `cmux notify` alert for the human. So a doorbell may arrive as a typed prompt
  in your own composer.
- The watcher gates that typed channel on your composer so a doorbell cannot
  land mid-draft. Two consequences are visible to you: a `deferred_input` in
  `last_doorbell_method` means the ring was withheld because you were typing
  and will retry on the next poll, and a doorbell forced into a parked draft
  arrives with a self-describing prefix to follow. The gating rules themselves
  live in the script, not here.
- Each poll's coalesced doorbell carries an **urgency**: *active* (typed input
  plus alert) or *passive* (alert channels only, never typed input). A new
  actionable event is active at most once per event cycle; its retries are
  passive, as is any re-ring while the run's `control_through` is moving (an
  orchestrator mid-consume — exactly when typed input is most disruptive). A
  worker blocked on a question is the exception: its re-rings stay active
  until it is answered. Retries back off exponentially from the base retry
  interval — default 30 s, doubling to a 300 s cap — and reset when newer
  worker events arrive; `watch` and `orchestrator start` accept
  `--retry-seconds` to change the base.
- `orchestrator pending` records a per-run `acknowledged_through` cursor, so a
  result or review you have already loaded stops re-ringing. A strictly newer
  worker event still rings, and each worker is tracked independently, so acking
  one never silences another. A repeat doorbell can also occur legitimately when
  delivery to the composer failed (e.g. an unechoed `cmux_input`); `pending`
  clears that too, and the worker state is durable in the outbox regardless.
- `orchestrator dismiss --state <state> --run <selector>` silences a run's
  current doorbell *without* consuming it or holding a lease — a completed run
  parked in `awaiting_review` for viewing, or a `blocked` run you are done with.
  It records a per-run `dismissed_through` cursor, stops even a persistent
  `blocked` nag, and a strictly newer worker event still re-rings.
- A finished-marked run quiets itself: the watcher advances
  `dismissed_through` over its current tail on the next poll. A merely paused
  run is resumable, not finished, so it stays quiet only because `paused` is
  not a ringing state and re-rings after resuming and emitting a new result.
  A fatal event in the live worker epoch is the exception: its epoch is stored
  in watcher state and keeps ringing until worker rotation changes the epoch,
  even if the run is marked finished. Legacy `failed` snapshots remain an
  upgrade backfill signal.
- `watch [--run <selector> ...] --interval 5 --timeout <seconds>` (omit `--run`
  for every registered run; `--once` for one pass; `--notify-cmux` for
  metadata-only alerts) is an ad-hoc foreground JSONL observer for debugging or
  rescue only. It advances only its private observer cursor: it never consumes
  protocol outbox events, reviews a result, answers a question, or holds a
  lease. The session watcher likewise performs no semantic actions — it
  maintains delivery cursors and sends opaque doorbells. Autonomous replies
  still require an orchestrator agent with authority for the decision.
- Urgent steering while holding no lease: `dispatch` refuses to run while a
  managed lease is held, and a managed orchestrator driving normal
  answer/review messaging uses `send`, which rings the doorbell itself.
- Closing out a result needs no lease either: `conclude --run <selector>` makes
  the same ephemeral takeover (and likewise refuses while a managed lease is
  active), appends review plus optional integration, and rings one doorbell.
  The worker drains them in order, checkpoints `paused`, and the orchestrator
  never waits for a success checkpoint before integrating. `--stop` writes
  `finished_at` only after the review/integration sequence is durable; retrying
  after a lost response returns idempotent success. It covers
  `awaiting_review`, accepted-but-unintegrated `paused`/legacy `succeeded`, and
  accepted-and-integrated crash recovery, and refuses anything else with a
  pointer to `dispatch` / `control abandon`. A paused worker has no pending
  result, so use `stop --run <selector>` to mark it finished directly; this
  sends no lifecycle message or doorbell.

## Dispatch on a stale remote package

Remote `dispatch` performs the full owner-side transaction and tmux doorbell in
one SSH invocation, so it needs an up-to-date `agents` package on the owning
host. If a dispatched authorization still leaves the worker `blocked` with
`message.type: steer`, that host runs a stale package — update it (see
`scripts/update_agents.sh`) rather than hand-rolling a takeover.

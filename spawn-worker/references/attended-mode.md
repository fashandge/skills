# Attended mode — stay on call for the worker

Opt-in only: the user asked you to stay available, answer the worker's
questions, or unblock it if it gets stuck. Everything else about the spawn is
unchanged — same launcher, same prompt discipline, same manual cleanup. What
this mode adds is a live orchestrator: herdr's lifecycle events wake you when
the worker stops, you read why, and you answer. There is still no file
protocol, no run directory, no registry, no watcher process — herdr is the
watcher, and the worker's pane is the channel.

The trade-off you accepted by not using `/handoff-agent`: attendance lives and
dies with this session. If this session ends or compacts away the handle, the
worker keeps running but nobody is on call anymore — there is no durable
journal to recover from. That is fine for a task that finishes within the
session; it is the wrong tool for one that must outlive it.

## Requires herdr

```bash
test "${HERDR_ENV:-}" = 1
```

Lifecycle waits are herdr-only; cmux and tmux cannot signal "the worker
stopped". If the backend would resolve to cmux or tmux, say attended mode is
not available there and offer the plain spawn or `/handoff-agent`. A remote
worker on a herdr host works — keep the `ssh <host>` prefix on every herdr
command below.

## The one prompt addition

Attended mode relaxes exactly one rule from the main skill: the worker may be
told someone will answer. Append one sentence to the task prompt:

> If you hit a genuine blocker or a decision you cannot make yourself, ask the
> question plainly and end your turn — it will be answered.

Nothing else changes. Still no role assignment, no reporting obligations, no
inbox to check, no mention of an orchestrator or this session. The worker asks
the way it would ask a human sitting at the terminal — because functionally,
one is.

## Spawn, then start the wait

Spawn as usual and retain the `handle` from the JSON line. With several
attended workers, keep the label→handle pairs straight in your own notes —
that mapping is the entire worker registry.

Before waiting, confirm the worker actually started its turn — a wait attached
to a not-yet-started agent can match the pre-start idle state and return
instantly:

```bash
herdr agent get <handle>    # expect agent_status: working; if not, recheck once before waiting
```

Then background the wait — never run it in the foreground, and never poll:

```bash
herdr agent wait <handle> --timeout 3600000   # background task
```

The wait is event-driven over herdr's socket, and being on call is not a
foreground activity: once the background wait is running, **end your turn**.
The session stays fully interactive — the user can keep talking to you about
anything, and you work on whatever they ask, exactly as if no worker existed.
A settled wait arrives as a task notification in its own right; handle it
when it comes, then return to whatever the user and you were doing. Do not
hold a turn open "monitoring", and do not decline or defer the user's other
work because a worker is running — a quiet worker costs you nothing.

A timeout expiry means the worker is still working — re-issue the background
wait and end your turn again; it says nothing about the worker's health.

## On wake: read before deciding

The wait settles on `idle`, `done`, or `blocked`. None of these means "task
finished" by itself — read the pane and classify:

```bash
herdr agent read <handle> --source recent-unwrapped --lines 120
```

- **Finished** — the output is a completed result. Report it to the user;
  attendance for this worker is over.
- **Asking** — the turn ends in a question or a statement of what it needs.
  Answer it (next section).
- **`blocked`** — herdr recognized an approval or question UI. Freshly spawned
  agents sometimes settle on a first-run dialog instead of the task (codex's
  "Hooks need review" prompt is the classic), and a Claude Code worker that
  raises its question through the interactive picker lands here rather than
  idle. While blocked, `agent read --lines` refuses (alternate-screen
  history) — read with `--source visible` instead. Answer the dialog with
  `herdr agent send-keys <handle> ...` (arrows + enter for a picker), or
  surface it to the user if it is a real permission decision; then wait again.
- **Ambiguous** — an agent can trail off without clearly finishing or asking.
  Treat a stopped worker whose status you cannot classify as asking "should I
  continue?", and say what you observed when you answer.

## Answering

Send the answer and the next wait in one stall-protected call, backgrounded:

```bash
herdr agent prompt <handle> "<the answer>" --wait --timeout 3600000   # background task
```

Then end your turn again — the same rule as the first wait: between wake-ups
the session belongs to the user.

Always `prompt --wait`, never a bare submit plus a standalone `agent wait` —
the standalone wait can match the settled state *before* the new turn starts
and return instantly, handing you the previous output as if it were new.

The pane is visible and the user may type into it directly — unsubmitted text
in the worker's composer is theirs. `agent prompt` replaces it rather than
appending, and `send-keys enter` cannot be counted on to submit it. If the
user's typed text answers the worker's question, fold its content into your
own `prompt --wait` message rather than trying to submit it in place.

What to answer from: this session's context, the user's original request, and
anything you can cheaply verify yourself (read the file, check the path).
What never to do: invent a decision that belongs to the user. If the worker
asks something only the user can decide — scope, destructive actions, which
of two valid designs — put the question to the user, and relay their answer.
The worker idles safely while it waits; an idle worker costs nothing, a
guessed answer can cost the whole task.

If the same worker comes back blocked on the same question a third time, stop
answering and escalate: repeated re-asking means the answers are not landing
or the task is underspecified, and that is the user's problem to reframe, not
yours to paper over.

## Multiple workers

One background wait per worker. Notifications arrive independently; classify
each against its own label and pane, and never assume the settled worker is
the one you were thinking about — check the handle in the notification.

## Finishing

When a worker's output is a completed result, report it the same way the main
skill does — one line, label and outcome — plus anything notable from the
question rounds. Cleanup stays manual (`herdr tab close <tab-id>`, the user's
call). If the user's request is fully served and other attended workers are
still going, keep their waits alive until they finish too.

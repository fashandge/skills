---
name: spawn-worker
description: Spawn a coding agent (Claude Code, Codex, Kimi Code, or pi) in a new terminal tab — locally in the current herdr/cmux/tmux session, or on a remote box like oci-box — and walk away. No handoff protocol, no monitoring, no bookkeeping. This is the default way to hand work to another agent. Use when the user says "hand this off", "delegate this", "spawn a worker", "run this in another tab", "start an agent on this", "put a worker on it", "run it on the box", or "have codex/pi/kimi do this". Route to handoff-agent instead only when the user explicitly asks for the durable handoff protocol, a monitored review loop, mid-run steering, or cross-session recovery; route to delegate-first for a headless one-shot whose output you will read back and review yourself.
---

# Spawn a worker in a new tab

This is what a human does: open a tab, start an agent on a task, get on with
something else. The spawned worker is an ordinary agent session. It gets a task
prompt and nothing more — no role, no protocol, no reporting obligations. It
does not know you exist.

Deliberately absent, and not to be added back: run directories, worker tokens,
leases, a registry, a watcher, doorbells, status polling, an outbox, a
review/accept loop. Nothing is written under `~/.local/state/agents/handoff`.
There is no worker list to consult later, by design.

## 1. Write the prompt

For the common short prompt, send it directly with the spawn command via
stdin (`-`) — no file needed. This also works for long and multiline prompts:
the launcher reads all of stdin and keeps a private copy, so nothing is lost.
Use a prompt file only to point at an existing plan or spec by path rather
than copying it. Write the prompt in almost the same words as the user's
request — do not re-engineer it into a brief. Add context only when
necessary: the task description is incomplete, or it depends on something from
this session the worker has no way to know (a path, a constraint, a finding).
A self-contained request stays at one or two sentences; detail we learned in
conversation does not belong in the prompt unless the task fails without it.

Do not add instructions unless the user asked for them or they are absolutely
necessary — no boilerplate process, no extra deliverables, no "be thorough",
no step-by-step how-to for things the worker can figure out. What must never
be in the prompt:

- **No role assignment.** Not "you are a worker", not "you are handling a
  handoff". Just the task.
- **No protocol.** Do not tell it to ask questions, wait for review, publish a
  result, emit anything, or check an inbox — there is nothing on the other end.
- **No mention of an orchestrator**, this session, or the fact that it was
  spawned.

Say what "done" is only when the task is open-ended enough that it might
otherwise keep going or ask — one short sentence, so it stops in the right
place instead of asking.

If the task touches shared state outside the repo, fence it in the prompt: test
against throwaway copies via `mktemp -d`, redirected through whatever env var
the code already honors.

## 2. Spawn

The script picks the local backend itself — herdr when you are inside herdr,
else cmux, else tmux — and creates the tab unfocused, so it never steals the
user's place.

```bash
~/projects/agents/scripts/spawn_worker.sh <label> <prompt.md> <repo> --agent claude
```

On a remote box, the worker lands in that host's own herdr server, in a
`REMOTE_WORKERS` workspace created on first use:

```bash
~/projects/agents/scripts/spawn_worker.sh <label> <prompt.md> \
  --agent pi --remote-host oci-box --remote-cwd /home/opc/projects/<repo>
```

`--split right` (herdr only) puts the worker in a split beside your own pane
instead of its own tab, and hands focus back. Use it for a worker you intend to
watch — a reviewer you read as it works — rather than one you walk away from;
the default tab is right for everything else. `--ratio` tunes the split.

`--agent claude|codex|kimi|pi`, each at its pinned default model and effort;
`--model` / `--effort` override one spawn. Pick **pi** for bulk mechanical work
— it is cheap and fast on a 1M window — and avoid it when the task turns on
judgment. The prompt goes on stdin with `-` (any length, multiline fine — this
is the default for short prompts); a prompt file is only needed to point at an
existing plan or spec.

One JSON line comes back with the `handle` (a herdr pane ID like `w5:p9`, a cmux
surface UUID, or a tmux session name) and the `backend`.

## 3. Report, then stop

Tell the user in one line what was spawned and where — the label, the agent, and
the tab. Then move on to whatever else they asked for.

Do not wait for it, do not poll it, do not open a watcher, and do not start
checking its output on your own initiative. The whole point of this mode is that
nobody is minding it.

## 4. Checking on it later

Only when the user asks. For a local herdr worker:

```bash
herdr agent list
herdr agent read <pane-or-agent-name> --source recent-unwrapped --lines 120
```

Prefix with `ssh <host>` for a remote one (`ssh oci-box herdr agent list`). For
tmux, `tmux capture-pane -pt <session>`. To send a follow-up instruction, type
it into the tab: `herdr agent prompt <target> "<text>"`.

### Waiting, when the user asks you to

Occasionally the user does want a loop — "review this, address what it finds,
then have it review again." Herdr is event-driven, so ask the server to tell you
rather than writing an `until …; do sleep N; done` poll loop. Polling samples
state on a timer: it misses transitions between samples, spends a turn per
sample, and hangs indefinitely when the agent never reaches the state you are
grepping for.

```bash
herdr agent wait <target> --timeout <ms>       # blocks until idle, done, or blocked
herdr agent prompt <target> "<text>" --wait    # submits AND waits, one call
```

Reach for `prompt --wait` in a send-then-read cycle: it is atomic, and if the
prompt produces no lifecycle change within five seconds it returns
`agent_prompt_stalled` rather than waiting on an agent that never started. Add
`--until <idle|working|blocked|done>` only for a state-specific wait, such as
catching an already-running agent the moment it blocks for input. For a pane
running something other than an agent, `herdr pane wait-output <pane> --match
<text>` is the equivalent.

None of this applies to the cmux or tmux backends, which have no such API — and
none of it changes the default posture above: absent a request to wait, spawn
and walk away. `herdr --skill` documents the rest of the API.

Closing a finished worker's tab is the user's call — this mode tracks nothing,
so cleanup is manual by design: `herdr tab close <tab-id>`.

## 5. When this is the wrong tool

Escalate only on an explicit request, and say which you are switching to:

- **`/handoff-agent`** — the user wants the durable handoff protocol, a
  monitored review/accept loop, mid-run steering through a lease, or a worker
  that survives this session being compacted or lost.
- **`/delegate-first`** — the user wants a headless one-shot whose answer you
  read back and review yourself, with no tab at all.

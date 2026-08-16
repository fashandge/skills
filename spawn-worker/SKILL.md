---
name: spawn-worker
description: Spawn a coding agent (Claude Code, Codex, Kimi Code, or pi) in a new terminal tab — locally in the current herdr/cmux/tmux session, or on a remote box like oci-box — and walk away. No handoff protocol, no monitoring, no bookkeeping. This is the default way to hand work to another agent. Use when the user says "hand this off", "delegate this", "spawn a worker", "run this in another tab", "start an agent on this", "put a worker on it", "run it on the box", or "have codex/pi/kimi do this". An opt-in attended mode (herdr only) stays on call to answer the worker's questions via herdr's event-driven waits — use it when the user says "stay on call", "answer its questions", "unblock it if it gets stuck", or "watch for it getting blocked". For a batch of related tasks fanned out across several workers, route to the orchestrate-workers skill instead.
---

# Spawn a worker in a new tab

This is what a human does: open a tab, start an agent on a task, get on with
something else. The spawned worker is an ordinary agent session. It gets a task
prompt and nothing more — no role, no protocol, no reporting obligations. It
does not know you exist. (The opt-in attended mode below relaxes exactly one of
these: the worker is told it may ask questions.)

Deliberately absent, and not to be added back: run directories, worker tokens,
leases, a registry, a watcher, doorbells, status polling, an outbox, a
review/accept loop. Nothing is written under `~/.local/state/agents/handoff`.
There is no worker list to consult later, by design. Attended mode adds none
of these either — it rides on herdr's own events and the worker's pane.

## 1. Write the prompt

Send the prompt via stdin (`-`) — any length, no file needed; the launcher
keeps a private copy. Use a prompt file only to point at an existing plan or
spec by path rather than copying it. Write the prompt in almost the same words
as the user's request — do not re-engineer it into a brief. Add context only
when necessary: the task description is incomplete, or it depends on something
from this session the worker has no way to know (a path, a constraint, a
finding).
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
  (Attended mode, opted into below, adds the single "you may ask" sentence —
  and nothing else.)
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
~/projects/agents/scripts/spawn_worker.sh <label> - <repo> --agent claude <<'EOF'
<task prompt — any length, multiline fine>
EOF
```

On a remote box, the worker lands in that host's own herdr server (the prompt
file here shows the point-at-an-existing-spec form; `-` works remotely too):

```bash
~/projects/agents/scripts/spawn_worker.sh <label> <plan.md> \
  --agent pi --remote-host oci-box --remote-cwd /home/opc/projects/<repo>
```

Pick **pi** for very easy tasks without much judgment (simple script changes,
moving files) and bulk mechanical sweeps, and avoid it when the task turns on
judgment. Run it on MiniMax-M3 at high effort — pass
`--model minimax/MiniMax-M3 --effort high`, since the script's pi default is
still DeepSeek V4 Flash. `--split right` (herdr only) is
for a worker you intend to watch as it works — a reviewer — rather than walk
away from; the default tab is right for everything else. When the task
belongs to a different project than the session, spawn it where it lives:
that project's directory as the worker cwd plus `--workspace-label <label>`
(herdr only), which places the tab in the herdr workspace with that label,
creating it on first use. Remotely the same placement rides on
`--remote-workspace <label>` — the local flag is rejected there, and without
the remote one every worker on that host piles into one default workspace.
`--help` documents the rest: agents, model/effort overrides, workspaces,
split ratio.

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
tmux, `tmux capture-pane -pt <session>`; for a cmux surface,
`cmux read-screen --surface <uuid> --scrollback`.

Anything past a quick read — sending a follow-up prompt, or a loop the user
asked for ("review this, address what it finds, then have it review again") —
is the herdr skill's territory: read it and use its event-driven waits
(`herdr agent prompt --wait`, `herdr agent wait`), never a sleep-and-poll
loop. Its inside-herdr gate applies to the local session only; for a remote
worker keep the `ssh <host>` prefix. cmux and tmux have no such API — and none
of this changes the default posture above: absent a request to wait, spawn and
walk away.

Closing a finished worker's tab is the user's call — this mode tracks nothing,
so cleanup is manual by design: `herdr tab close <tab-id>`.

## 5. Attended mode (opt-in)

Only when the user asks you to stay available — "stay on call", "answer its
questions", "unblock it if it gets stuck". Herdr only: it rides on herdr's
lifecycle events, so it works locally inside herdr or on a remote herdr host,
and is not available on cmux or tmux.

The shape: append one sentence to the task prompt telling the worker it may
ask; retain the spawn's `handle`; background `herdr agent wait <handle>` so
you are woken the moment the worker stops; read the pane to see whether it
finished, asked, or hit a dialog; answer with `herdr agent prompt --wait`
(backgrounded) and repeat until the task is done. Between wake-ups you end
your turn and the session stays fully interactive — the user keeps talking to
you as if no worker existed. No polling, no watcher process, no files —
herdr's events and the worker's pane are the whole protocol.

Before attending a worker, read `references/attended-mode.md` — it owns the
wait/classify/answer loop, the race and stall guards, and the escalation
rules (what you may answer yourself versus what goes to the user).

## 6. When this is the wrong tool

- **A sub-step of your own task** — you need the answer mid-task to continue
  your own work (a second opinion, a review verdict, a computed result): run
  it headless with `agents-cli` (see `~/.claude/docs/agents-cli.md`). A tab
  is for work the user owns — even attended mode reads the pane only to
  unblock the worker, not to consume its result.
- **A batch of related tasks** across several workers — switch to
  `/orchestrate-workers`, which fans out via this skill and owns the
  split/route/review loop.
- **A worker that must outlive this session** (durable protocol, monitored
  review/accept loop, mid-run steering that survives compaction) — no live
  skill covers that anymore; the retired `handoff-agent` protocol is in
  `~/projects/unused_skills`. Say so plainly rather than improvising a
  substitute.

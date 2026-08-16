# Driving a Reviewer Agent in a herdr Pane

Shared mechanics and loop protocol for `review-with-agent`, `skill-review-with-agent`,
and `plan-with-agent`: how to put a reviewer in a visible pane, wait for it without
blocking the session, run the review-address rounds, and decide when to stop. The
consuming skill owns *what* to review — the artifact, the review prompt, and the ground
truth findings are verified against; this file owns the plumbing and the round protocol,
so the consumers cannot drift apart on them.

The reviewer is a full interactive agent, not a one-shot call. Two consequences shape
everything below:

- **It keeps its context between rounds.** Round 2 is a short delta — what you changed
  and what you rejected — not a re-sent packet of everything it already knows.
- **It is visible.** The user watches it work and can type into its pane. That is most
  of the value: a review you cannot see is a review you take on faith.

## Requires herdr

```bash
test "${HERDR_ENV:-}" = 1 && herdr pane current
```

If that fails, say so and offer a headless one-shot reviewer instead (`codex exec` /
`claude -p` piped a review prompt, output read back and verified by you). Don't fall
back to a polling loop or a detached tab you cannot wait on.

## Spawn and place

`--split right` spawns the reviewer, moves it in beside you, and hands focus back. The
prompt goes on stdin, so length is not a constraint:

```bash
~/projects/agents/scripts/spawn_worker.sh <label> - <cwd> \
  --agent codex --model <model> --effort <effort> --split right --ratio 0.5 <<'EOF'
<the review prompt>
EOF
# -> one JSON line with "handle": e.g. "w6:p2"
```

- **Default**: the split above — the user sees the review without switching tabs.
- **New tab**: drop `--split`; spawn_worker's default is its own tab. Use when the
  content is wide, the terminal narrow, or the user asks.
- **Multiple reviewers**: spawn each with its own label; herdr lays out the successive
  splits. Pick models from *different* vendors — two instances of one model mostly
  agree with each other, which buys nothing.

`--split` is herdr-only and cannot combine with `--remote-host`: a remote worker lands
in the remote host's herdr server, where no pane of yours exists to split against.

## Wait, then read

```bash
herdr agent wait <handle> --timeout 1200000   # run this in the background
herdr agent read <handle> --source recent-unwrapped --lines 200
```

`agent wait` is event-driven over herdr's socket — never write a polling loop. With
several reviewers, wait on each in turn; they run in parallel, so the last wait returns
when the slowest finishes.

**Run the wait in the background.** A review takes minutes — 1 to 9 in practice — and a
foreground wait makes the user wait too, queueing anything they want to say behind it
for no gain, since the pane already lets them watch. Background it and a notification
arrives when the agent settles.

**But hold the artifact still while a review is in flight.** Not blocking the session is
not licence to keep editing. If what is under review changes underneath the reviewer,
its findings describe something that no longer exists — line numbers slide, and a fixed
problem gets reported as live. Use the wait for anything *except* touching the reviewed
artifact: answer the user, read surrounding code, prepare your verification plan. If it
did change mid-review, discard that round rather than reasoning about which findings
survived; re-establish scope and re-prompt. A discarded round costs one prompt; a review
silently interpreted against the wrong state costs far more.

**`blocked` is a real outcome, not a slow `idle`.** A freshly spawned agent can settle on
a first-run dialog instead of the task — codex prompts "Hooks need review" whenever a
hook it knows has changed, and then sits there indefinitely. Check rather than assume:

```bash
herdr agent get <handle>    # agent_status: working | idle | blocked | done | unknown
```

If blocked, read the pane, answer the dialog with `herdr agent send-keys` or by telling
the user, and only then wait again. A review you never noticed was blocked reads exactly
like a review that found nothing.

## Next round

The reviewer still has its context, so the follow-up is short:

```bash
herdr agent prompt <handle> "<what you changed, what you rejected and why,
what to re-review>" --wait --timeout 1200000
```

`agent prompt --wait` submits and waits in one call. If the prompt produces no lifecycle
change within five seconds it returns `agent_prompt_stalled` instead of hanging on an
agent that never started. Always use `prompt --wait` for a follow-up rather than a bare
submit plus a standalone `agent wait`: the standalone wait can match the agent's settled
state *before* it starts the turn and return instantly, reading the previous round's
output as if it were the new review. And a follow-up round takes as long as the first,
so the background-wait rule above applies here too — run the command in the background,
and hold the artifact still until it settles.

With multiple reviewers, send every one of them the *same* round summary — including
findings that came from a different reviewer — so each re-reviews knowing what actually
changed, and one that disagrees with another's accepted finding can say so. Background
each `prompt --wait` so they submit and work in parallel, and run the whole block in the
background:

```bash
for h in <handle-1> <handle-2>; do
  herdr agent prompt "$h" "<round summary>" --wait --timeout 1200000 &
done; wait
```

## Keeping the reviewer read-only

A pane agent has write access to whatever it can reach, and will otherwise fix things
itself — which destroys your ability to judge its findings. State the boundary in the
prompt ("Do not change any code" / "treat every file as read-only except …"). Reviewers
comply with this reliably.

When a flow genuinely needs the reviewer to edit, give it a disposable copy and name
that copy as the only writable path, rather than trusting a negative instruction to hold
across many turns.

## The round protocol

**Verify each finding before you act on it** — read the relevant path or reproduce the
failure against the ground truth the consuming skill names. A confident, well-written,
wrong finding is the main hazard of this workflow, and a reviewer that already surfaced
three real bugs earns unearned trust for its fourth. Verifying takes a minute and
settles it.

Then fix blockers and majors; take minors and nits at your judgment. **Record every
finding** — `FIXED`/`ACCEPTED — <what changed>`, `REJECTED — <why it is wrong>`, or
`DEFERRED — <valid, intentionally unchanged, why>` — and never silently drop one. Tell
the reviewer what you rejected and why in the next round; that is how a wrong finding
stops recurring. Push back when you disagree, and tell the user plainly — deference to a
reviewer that is wrong is worse than no review.

Keep the same reviewer across rounds, lowering its effort after the first
(`~/skills/plan-with-agent/references/model-selection.md` owns the roster and effort
mapping).

## Stopping and escalation

**Cap review-address loops at 6 rounds** unless the user says otherwise. Typical
convergence is 1–3, so the cap is a backstop rather than a target — but it is set high
deliberately: later rounds keep finding bugs that earlier *fixes* introduced, so
stopping at the first clean pass is the wrong instinct. In one observed run, rounds 2
and 3 each caught a defect created by the previous round's fix, and the loop converged
only on round 4.

**Stop when** the reviewer approves — no remaining blockers or majors — and addressing
that round changed nothing after the reviewed state, so the final state is exactly what
was approved; if handling an approved round does change the artifact, re-review it. Also
stop when the user accepts an unresolved risk, or at the cap.

**Escalate to the user instead of looping** when the cap is hit without approval — that
is a signal about the artifact rather than the reviewer; say so instead of quietly
raising the cap — when a valid blocker will not be fixed, or when the reviewer re-raises
a rejected finding with a genuinely new argument. Present both positions neutrally.

## Wrap-up

Report to the user: which reviewer model(s), rounds used, the outcome, what changed in
response to the review, any rejected or deferred findings and open disagreements, and
which findings you verified versus took on trust. Approval is not a decision to commit,
merge, or implement — those stay with the user.

## Cleanup

Closing the pane is the user's call — they may want to read it:

```bash
herdr pane close <handle>
```

`herdr --skill` documents the rest of the CLI.

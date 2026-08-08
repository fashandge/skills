---
name: review-with-agent
description: Have one or more other agents (Codex, Claude, pi, kimi) adversarially review code changes in a live herdr pane, then verify and address their findings and repeat the review-address cycle until approval or the round cap. Use when the user explicitly asks for a second agent or second model to review code, e.g. "have codex review this", "get claude to review my diff", "second-model review of these changes", "review this with codex and fix what it finds", "have two agents review this". Do not auto-trigger for ordinary code-review requests that don't ask for a second agent — the harness's own code-review skill covers those. For reviewing a plan/design doc instead of code, use plan-with-agent; for reviewing a skill, use skill-review-with-agent.
---

# Review with Agent

A second frontier model reviews your change set in a **live pane next to you**, you verify and address what it finds, and it reviews again. The reviewer is a real interactive session, not a one-shot call, which is what makes this cheap: it keeps its context between rounds, so round 2 is a three-line delta prompt rather than a re-sent packet of everything it already knows.

It is also visible. The user watches the review happen, can read the reviewer's reasoning as it works, and can type into its pane directly. That visibility is most of the value — a review you cannot see is a review you have to take on faith.

The one hard exclusion is self-review: the reviewer must never be the exact model this session is running. Same vendor at a different tier is fine.

## Requires herdr

This skill drives `herdr`, so it needs a herdr session:

```bash
test "${HERDR_ENV:-}" = 1 && herdr pane current
```

If that fails, say so and offer `/delegate-first` instead — it runs a headless one-shot reviewer whose output you read back. Don't fall back to a polling loop or a detached tab you cannot wait on.

## Modes

- **Default** — one reviewer, in a vertical split beside you in the current tab. You see its output without switching tabs.
- **New tab** — same, but the reviewer keeps its own tab. Use when the diff is wide, the terminal is narrow, or the user asks.
- **Multiple reviewers** — two or three reviewers of *different* models review the same candidate in parallel. Wait for all, combine their findings, address once, then send them all into the next round together. Use when the user asks, or when the change is risky enough that independent perspectives are worth the tokens. Independent agreement is strong signal; a finding only one model raises is worth extra scrutiny, not automatic rejection.

## 1. Scope the change set

Pin down what is under review before spawning anything. Don't make the user commit first.

- **Baseline and candidate**: working-tree change → `HEAD` vs working tree; branch/PR → merge-base vs working tree; explicit range → the range's base vs its tip (confirm the worktree is at the tip before fixing anything).
- **Write an intent brief**: one paragraph on what the change is supposed to do, the key paths, and any non-goals. Without it a reviewer reviews style instead of correctness and cannot flag scope creep.
- **Know the tests pass first.** Don't spend a round on code you already know is broken. If they were just run, don't rerun them — note the result for the prompt.
- **Gather context that defines intent**: design docs, issues, API contracts. Give absolute paths, and mark each `AUTHORITATIVE` or `BACKGROUND`. A plan proves intent, never correctness.

## 2. Choose the reviewer

Never self-review; honor an explicit user choice of model subject to that; otherwise default to a cross-vendor reviewer one tier stronger, or the strongest cross-vendor peer when this session is already top tier. Read `~/skills/plan-with-agent/references/model-selection.md` for the roster, the session→reviewer mapping, and effort. Keep the same reviewer across rounds; lower its effort after the first.

For multiple reviewers, pick models from *different* vendors — two instances of one model mostly agree with each other, which buys nothing.

## 3. Spawn and place

`--split right` does the whole thing: spawns the reviewer, moves it in beside you, and hands focus back. The prompt goes on stdin, so it can be as long as it needs to be:

```bash
~/projects/agents/scripts/spawn_worker.sh review-1 - <repo-path> \
  --agent codex --model gpt-5.6-sol --effort high --split right --ratio 0.5 <<'EOF'
<the review prompt from §4>
EOF
# -> one JSON line with "handle": e.g. "w6:p2"
```

For **new-tab** mode, drop `--split` — spawn_worker's default is its own tab. For **multiple reviewers**, spawn each with its own label; herdr lays out the successive splits.

`--split` is herdr-only and cannot combine with `--remote-host` (a remote worker lands in the remote host's herdr server, so there is no pane of yours to split it against).

## 4. The review prompt

The reviewer is a full agent sitting in the repo, so it reads whatever it needs. Give it only what it cannot infer:

```
Review <exact baseline and candidate, e.g. "the working tree against HEAD"
or "commit abc123">.

Intent: <the brief from §1>
Context: <AUTHORITATIVE|BACKGROUND> <absolute path> — <why it matters>
Tests already run on this candidate: <commands and results>

Review for correctness bugs (logic, edge cases, error handling, concurrency),
regressions in untouched-but-affected behavior, misuse of this codebase's
actual APIs and conventions, missing tests, security issues, and significant
simplification opportunities. Judge the change against its stated intent —
flag scope creep. Verify assumptions from any design docs against the code.

Report findings, correctness first, each with a severity
(blocker|major|minor|nit) and file:line. Say so explicitly if you find
nothing. Do not change any code.
```

"Do not change any code" is the boundary that matters — the reviewer has write access to the repo and will otherwise fix things itself, which destroys your ability to judge its findings. Reviewers comply with this reliably. If a change set genuinely needs isolation, give the reviewer a worktree or clone instead of relying on the instruction.

## 5. Wait, then read

```bash
herdr agent wait <handle> --timeout 1200000
herdr agent read <handle> --source recent-unwrapped --lines 200
```

`agent wait` blocks until the agent settles (idle, done, or blocked) — it is event-driven over herdr's socket, so never write a polling loop. With several reviewers, wait on each in turn; they run in parallel, so the last wait returns when the slowest finishes.

**`blocked` is a real outcome, not a slow `idle`.** A freshly spawned agent can settle on a first-run dialog instead of the task — codex in particular prompts "Hooks need review" whenever a hook it knows has changed, and then sits there indefinitely. Check the state rather than assuming the review ran:

```bash
herdr agent get <handle>    # agent_status: idle | blocked | working
```

If it is blocked, read the pane, answer the dialog with `herdr agent send-keys` or by telling the user, and only then wait again. A review you never notice was blocked reads exactly like a review that found nothing.

## 6. Verify, then address

**Verify each finding before you act on it.** Read the code path or reproduce the failure. A confident, well-written, wrong finding is the main hazard of this whole workflow — and a reviewer that already surfaced three real bugs earns unearned trust for its fourth. Reproducing takes a minute and settles it.

Then:

1. Fix blockers and majors; take minors and nits at your judgment.
2. Re-run the relevant tests after every change.
3. Record every finding as `FIXED — <what changed>`, `DEFERRED — <valid, intentionally unchanged, why>`, or `REJECTED — <why it is wrong>`. Never silently drop one. If you reject a finding, say so to the reviewer next round with the reasoning — that is how a wrong finding stops recurring.
4. Push back when you disagree, and tell the user plainly. Deference to a reviewer that is wrong is worse than no review.

With multiple reviewers, combine before addressing: group findings that make the same claim, note where reviewers independently agree, and keep genuine disagreements visible rather than averaging them away.

## 7. Next round

The reviewer still has its context, so the follow-up is short — what changed and what you rejected, not the whole packet again:

```bash
herdr agent prompt <handle> "I addressed your findings: <one line each>.
I rejected <finding> because <reason>. Please re-review the working tree.
Do not change any code." --wait --timeout 1200000
```

`agent prompt --wait` submits and waits in one call. If the prompt produces no lifecycle change within five seconds it returns `agent_prompt_stalled` instead of hanging on an agent that never started.

With multiple reviewers, send every one of them the *same* round summary — including findings that came from a different reviewer. Each then re-reviews knowing what actually changed, and a reviewer that disagrees with another's accepted finding gets the chance to say so. Send them all before waiting on any, so they work in parallel:

```bash
for h in <handle-1> <handle-2>; do
  herdr agent prompt "$h" "<round summary>" &   # submit to all first
done; wait
for h in <handle-1> <handle-2>; do herdr agent wait "$h" --timeout 1200000; done
```

**Cap at 4 review rounds** unless the user says otherwise. Typical convergence is 2–3. Later rounds surface bugs introduced by earlier fixes, which is exactly why the cycle is worth repeating rather than stopping at the first clean pass.

**Stop when** the reviewer reports no remaining blockers or majors and no code changed after the reviewed state; or the user accepts an unresolved risk; or the cap is hit. Escalate to the user rather than looping when a valid blocker will not be fixed, or when the reviewer re-raises a rejected finding with a genuinely new argument.

## 8. Wrap up

Closing the reviewer's pane is the user's call — they may want to read it:

```bash
herdr pane close <handle>
```

Report: what changed in response to the review, which reviewer models, rounds used, the outcome, test status, and any rejected findings or open disagreements. Say which findings you verified and which you took on trust. Approval is not a merge decision — committing, pushing, and merging stay with the user.

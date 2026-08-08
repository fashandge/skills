---
name: review-with-agent
description: Have one or more other agents (Codex, Claude, pi, kimi) adversarially review code changes in a live herdr pane, then verify and address their findings and repeat the review-address cycle until approval or the round cap. Use when the user explicitly asks for a second agent or second model to review code, e.g. "have codex review this", "get claude to review my diff", "second-model review of these changes", "review this with codex and fix what it finds", "have two agents review this". Do not auto-trigger for ordinary code-review requests that don't ask for a second agent — the harness's own code-review skill covers those. For reviewing a plan/design doc instead of code, use plan-with-agent; for reviewing a skill, use skill-review-with-agent.
---

# Review with Agent

A second frontier model reviews your change set in a live pane next to you, you verify
and address what it finds, and it reviews again.

**Read `references/herdr-review-loop.md` for the mechanics** — spawning, placement,
waiting, reading, and the next-round prompt. It is shared with `skill-review-with-agent`
so the two cannot drift. This file owns what is specific to reviewing *code changes*.

The one hard exclusion is self-review: the reviewer must never be the exact model this
session is running. Same vendor at a different tier is fine.

## Modes

- **Default** — one reviewer, split beside you in the current tab.
- **New tab** — the reviewer keeps its own tab. Wide diffs, narrow terminals, or on request.
- **Multiple reviewers** — two or three models from different vendors review the same
  candidate in parallel; wait for all, combine, address once, then send them all into the
  next round together. Use when the user asks, or when the change is risky enough that
  independent perspectives are worth the tokens. Independent agreement is strong signal;
  a finding only one model raises deserves extra scrutiny, not automatic rejection.

## 1. Scope the change set

Pin down what is under review before spawning anything. Don't make the user commit first.

- **Baseline and candidate**: working-tree change → `HEAD` vs working tree; branch/PR →
  merge-base vs working tree; explicit range → the range's base vs its tip (confirm the
  worktree is at the tip before fixing anything).
- **Write an intent brief**: one paragraph on what the change is supposed to do, the key
  paths, and any non-goals. Without it a reviewer reviews style instead of correctness
  and cannot flag scope creep.
- **Know the tests pass first.** Don't spend a round on code you already know is broken.
  If they were just run, don't rerun them — note the result for the prompt.
- **Gather context that defines intent**: design docs, issues, API contracts. Give
  absolute paths, and mark each `AUTHORITATIVE` or `BACKGROUND`. A plan proves intent,
  never correctness.

## 2. Choose the reviewer

Never self-review; honor an explicit user choice of model subject to that; otherwise
default to a cross-vendor reviewer one tier stronger, or the strongest cross-vendor peer
when this session is already top tier. Read
`~/skills/plan-with-agent/references/model-selection.md` for the roster, the
session→reviewer mapping, and effort. Keep the same reviewer across rounds; lower its
effort after the first.

## 3. The review prompt

The reviewer is a full agent sitting in the repo, so it reads whatever it needs. Give it
only what it cannot infer:

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

Spawn with that prompt, then wait and read, per the shared reference.

## 4. Verify, then address

**Verify each finding before you act on it.** Read the code path or reproduce the
failure. A confident, well-written, wrong finding is the main hazard of this workflow —
and a reviewer that already surfaced three real bugs earns unearned trust for its
fourth. Reproducing takes a minute and settles it.

Then:

1. Fix blockers and majors; take minors and nits at your judgment.
2. Re-run the relevant tests after every change.
3. Record every finding as `FIXED — <what changed>`, `DEFERRED — <valid, intentionally
   unchanged, why>`, or `REJECTED — <why it is wrong>`. Never silently drop one. Tell the
   reviewer what you rejected and why in the next round — that is how a wrong finding
   stops recurring.
4. Push back when you disagree, and tell the user plainly. Deference to a reviewer that
   is wrong is worse than no review.

With multiple reviewers, combine before addressing: group findings that make the same
claim, note where reviewers independently agree, and keep genuine disagreements visible
rather than averaging them away.

## 5. Loop

Send the next round per the shared reference — what changed, what you rejected and why,
and to re-review the working tree.

**Cap at 6 review rounds** unless the user says otherwise. Typical convergence is 2–3, so
the cap is a backstop rather than a target — but it is set high deliberately: later
rounds keep finding bugs that earlier *fixes* introduced, so stopping at the first clean
pass is the wrong instinct. In one observed run, rounds 2 and 3 each caught a defect
created by the previous round's fix, and the loop converged only on round 4.

If a run reaches 6 without converging, that is a signal about the change rather than
about the reviewer — say so to the user instead of quietly raising the cap.

**Stop when** the reviewer reports no remaining blockers or majors and no code changed
after the reviewed state; or the user accepts an unresolved risk; or the cap is hit.
Escalate to the user rather than looping when a valid blocker will not be fixed, or when
the reviewer re-raises a rejected finding with a genuinely new argument.

## 6. Wrap up

Report: what changed in response to the review, which reviewer models, rounds used, the
outcome, test status, and any rejected findings or open disagreements. Say which findings
you verified and which you took on trust. Approval is not a merge decision — committing,
pushing, and merging stay with the user.

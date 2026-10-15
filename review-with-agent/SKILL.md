---
name: review-with-agent
description: Have one or more other agents (Codex or Claude) adversarially review code changes in a live herdr pane, then verify and address their findings and repeat the review-address cycle until approval or the round cap. Use when the user explicitly asks for a second agent or second model to review code, e.g. "have codex review this", "get claude to review my diff", "second-model review of these changes", "review this with codex and fix what it finds", "have two agents review this". Do not auto-trigger for ordinary code-review requests that don't ask for a second agent — the harness's own code-review skill covers those. For reviewing a plan/design doc instead of code, use plan-with-agent; for reviewing a skill, use skill-review-with-agent.
---

# Review with Agent

A second frontier model reviews your change set in a live pane next to you, you verify
and address what it finds, and it reviews again.

**Read `references/herdr-review-loop.md` first** — it owns the mechanics and the round
protocol, shared with `skill-review-with-agent` and `plan-with-agent` so the siblings
cannot drift. This file owns what is specific to reviewing *code changes*.

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

Never self-review: the reviewer is never the exact model this session is running (same
vendor at a different tier is fine). Honor an explicit user choice subject to that.
Otherwise `~/skills/plan-with-agent/references/model-selection.md` owns the default
session→reviewer mapping, the roster, and the effort.

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

Output format — first line exactly:
VERDICT: APPROVE | REVISE
APPROVE if and only if no blocker or major findings remain. Then each
finding on its own bullet, correctness first:
[blocker|major|minor|nit] <title> — <file:line> — <what and why>
Prefer a short list of substantive findings over an exhaustive list of
small ones; do not propose re-architecture or new features unless a real
defect requires it. Do not change any code.
```

Spawn with that prompt, then wait and read, per the shared reference.

## 4. Run the loop

Follow the shared reference's round protocol, next-round prompt, cap, stop and escalation
rules, and wrap-up. Code adds two rules: re-run the relevant tests after every change,
and include the final test status in the wrap-up.

## Multiple reviewers

Two or three models from *different* vendors review the same candidate in parallel — two
instances of one model mostly agree with each other, which buys nothing. Use when the
user asks, or when the change is risky enough that independent perspectives are worth
the tokens.

- **Spawn** each with its own label and the same prompt; herdr lays out the successive
  splits.
- **Wait** on each handle in turn; they run in parallel, so the last wait returns when
  the slowest finishes.
- **Combine before addressing**: group findings that make the same claim, and keep
  genuine disagreements visible rather than averaging them away. Independent agreement is
  strong signal; a finding only one model raises deserves extra scrutiny, not automatic
  rejection.
- **Next round**: send every reviewer the *same* round summary — including findings that
  came from a different reviewer — so each re-reviews knowing what actually changed, and
  one that disagrees with another's accepted finding can say so. Run the block in the
  background:

  ```bash
  for h in <handle-1> <handle-2>; do
    herdr agent prompt "$h" "<round summary>" --wait --timeout 1200000 &
  done; wait
  ```

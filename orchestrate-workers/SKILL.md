---
name: orchestrate-workers
description: Run a multi-task job as an orchestrator - split the work into tasks, gauge each task's difficulty, spawn attended workers (via the spawn-worker skill) on cheaper models to implement them in parallel, review each worker's diff, drive review->follow-up cycles until the work is solid, and finish with a fresh-context cross-model review. Use whenever the user asks to "orchestrate this", "act as orchestrator", "split this into tasks and assign to workers", "parallelize this across workers/agents", "delegate these fixes and review the results", or hands over a batch of related fixes/features in one session and wants them done by multiple agents in parallel with review - especially when the main session runs on an expensive model (Fable/Opus) and implementation should happen on cheaper workers. Not for a single delegated task (use spawn-worker or delegate-first directly) or a durable cross-session protocol (use handoff-agent).
---

# Orchestrate workers

Act as the conductor, not the implementer. The orchestrator session (often on an
expensive model) plans, routes, coordinates, reviews, and commits; spawned
workers (on cheaper models) explore, implement, and test. The economics only
work if you resist doing implementation yourself and resist over-specifying
prompts — both burn orchestrator tokens on work a worker can figure out.

Spawning mechanics, prompt hygiene, and the attended wait/answer loop belong to
the **spawn-worker** skill (read it; use its attended mode — one sentence added
to the prompt, background `herdr agent wait`, `prompt --wait` for answers).
This skill owns what spawn-worker deliberately doesn't: decomposition, routing,
conflict coordination, and the review discipline.

## 1. Plan before spawning

- Write the task breakdown down (goal-mode plan doc, or a scratch list for
  small jobs): tasks, dependencies, which shared resources each touches, and
  planned waves. Mirror progress as you go — the doc is what survives
  compaction and lets the user audit mid-run.
- Do cheap scouting yourself (a grep, reading an issue note) only to *scope*
  tasks, not to solve them. You usually don't need implementation details to
  judge a task's difficulty.

## 2. Route by difficulty

Gauge each task and pick the worker tier (defaults that have worked; adjust to
what's installed):

| Task shape | Worker |
|---|---|
| Straightforward, self-contained fix; worker can explore and figure it out | codex, strong-fast model (e.g. gpt-5.6-terra), xhigh effort |
| Complicated, nuanced, multi-file, or history-rewriting | codex, deepest model (e.g. gpt-5.6-sol), high effort |
| Bulk mechanical sweeps | pi (cheap, 1M window) |
| Final fresh-context review | a *different model family* than the implementers (e.g. kimi k3 max) |

Prompt sizing follows the same judgment: for straightforward tasks give brief
context + the goal + constraints and let the worker explore — do not prescribe
implementation. Only for genuinely error-prone tasks (identity/history
rewrites, safety-critical SQL) write out the mechanism, the acceptance
criteria, and the review artifacts you expect. Always include: the constraint
list (files it may touch, what it must not do), a done condition, and "do not
git commit" (see §4).

## 3. Coordinate shared state

Workers must not step on each other:

- **Same repo, parallel workers**: give each a disjoint file set in the shared
  checkout and say so in each prompt ("other agents are working on other files
  in this checkout; only modify X and Y"). Prefer the shared checkout over git
  worktrees when the project is an editable-installed package — pytest imports
  resolve to the installed checkout, so a worktree silently tests the wrong
  code. Use worktrees only when file sets genuinely overlap.
- **Single-writer resources** (a DuckDB file, a port, a deploy target): at most
  one worker may write it per wave; fence everyone else to read-only in their
  prompts, and sequence the waves so writers never overlap.
- **Dependent tasks run in later waves**: if task B edits a file task A also
  edits, or builds on conventions A may change, B waits until A is reviewed
  and committed.

## 4. Review every worker; workers never commit

Workers leave changes in the working tree; the orchestrator reviews and
commits per task. This keeps mixed parallel output reviewable (disjoint file
sets = clean per-task diffs) and makes you the accountability point.

The review is not reading the worker's summary — it is:

1. Read the pane, then read the **actual diff**.
2. Verify claims empirically when cheap: run the focused tests yourself; if a
   worker claims something was broken/fixed, spot-check (e.g. `git stash` →
   run tests → `git stash pop` proves a suite really was red before the fix).
3. Interrogate the risky part. For history-rewriting or data-facing changes,
   demand a validation artifact (scratch-table rebuild + before/after diff
   report) and read it critically — the most valuable follow-up is often a
   comparison the worker didn't compute (e.g. "show the yearly denominator
   means before/after"). A worker's own tests passing is necessary, never
   sufficient.
4. Send follow-ups with **explicit acceptance criteria** via
   `herdr agent prompt --wait`, and repeat the cycle until the criteria hold.
   Rejecting a round and stating the rework rule precisely ("break identity
   only on positive evidence; gaps alone never break linkage; no year's means
   may degrade") converges in one round; vague dissatisfaction doesn't.
5. Then commit that task's files with a proper message, and update the
   progress doc.

## 5. Finish with a fresh-context cross-model review

After everything is committed, spawn one reviewer from a different model
family, fenced (no commits, no writes to protected resources), over the whole
range (`base..HEAD`), with a review-then-fix mandate: fix real issues directly
+ add tests; report-only anything that is a judgment call or would rewrite
data/history. Fresh context catches what every in-context reviewer misses —
integration seams between tasks (a DAG-position mismatch, a test suite nobody
re-ran after a later commit changed its fixture's assumptions). Review the
reviewer the same way as §4 (verify its critical find empirically before
believing it), then commit its surviving fixes.

## 6. Wrap up

Push once the batch is coherent, write the final progress entry, and report
per task: what landed (commit), what was rejected/reworked and why, what was
report-only. Leave worker tabs for the user to close (spawn-worker's rule).

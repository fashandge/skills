---
name: orchestrate-workers
description: Run a multi-task job as an orchestrator - split the work into tasks, gauge each task's difficulty, spawn workers (via the spawn-worker skill) on cheaper models to implement them in parallel, then either review every diff and close with a fresh-context cross-model review (attended, the default), or hand the tabs back and walk away (unattended). Use whenever the user asks to "orchestrate this", "act as orchestrator", "split this into tasks and assign to workers", "parallelize this across workers/agents", or hands over a batch of related fixes/features to be done by multiple agents in parallel - especially when the main session runs on an expensive model (Fable/Opus) and implementation should happen on cheaper workers. Use unattended mode when the user says "unattended", "fire and forget", "just split it and spawn them", or "don't review the work". Not the entry point for a single delegated task (spawn-worker, delegate-first) or a durable cross-session protocol (handoff-agent).
---

# Orchestrate workers

Act as the conductor, not the implementer. The orchestrator session (often on an
expensive model) plans, routes, coordinates, and — in attended mode — reviews
and commits; spawned workers (on cheaper models) explore, implement, and test.
The economics only work if you resist doing implementation yourself and resist
over-specifying prompts — both burn orchestrator tokens on work a worker can
figure out.

Spawning mechanics and prompt hygiene belong to the **spawn-worker** skill
(read it). This skill owns what spawn-worker deliberately doesn't:
decomposition, routing, conflict coordination, and the review discipline.

## Modes

- **Attended (default)** — workers are spawned in spawn-worker's attended mode
  (one sentence added to the prompt, background `herdr agent wait`,
  `prompt --wait` for answers), you review every diff, and a fresh-context
  reviewer closes the batch. §1–§3, then §5–§7.
- **Unattended** — split if splitting helps, spawn every task at once in
  spawn-worker's plain default mode, report where the tabs are, stop. No
  waiting, no answering, no review. §1–§4, then done.

Pick unattended only when the user asks for it (the triggers in the
description, or a `/orchestrate-workers unattended …` invocation). Everything
in §1–§3 applies to both modes, and matters *more* unattended: a bad split
there has no review pass to catch it.

## 1. Plan before spawning

- **Split only when the split buys something.** Tasks exist to run in
  parallel; a division that yields dependent pieces, or pieces one worker
  would have done anyway, costs coordination and buys nothing. If the job is
  really one task, that is one worker — spawn it and stop, don't manufacture a
  breakdown. Splitting is also wrong when the pieces cannot be made
  file-disjoint or must land in order (both §3).
- **Match the planning to the job.** A handful of obvious tasks needs no
  artifact — work the split out in your head, name each task, note who touches
  what, spawn. Write the breakdown down only when the job is big enough to
  lose track of: many tasks, multiple waves, or a run long enough to be
  compacted. Then it is a goal-mode plan doc holding tasks, dependencies,
  shared resources, and planned waves, mirrored as you go — that doc is what
  survives compaction and lets the user audit mid-run.
- Do cheap scouting yourself (a grep, reading an issue note) only to *scope*
  tasks, not to solve them. You usually don't need implementation details to
  judge a task's difficulty.

## 2. Route by difficulty

Gauge each task and pick the worker tier (defaults that have worked; adjust to
what's installed):

| Task shape | Worker |
|---|---|
| Straightforward, self-contained fix; worker can explore and figure it out | claude, opus, high effort |
| Simple non-coding task needing some judgment and taste (absorb an article into notes, summarize news/articles, research notes, write a wiki) | claude, opus, high effort |
| Complicated and taste-heavy (research articles, investment thesis) | kimi, k3, max effort — if out of quota, codex, gpt-5.6-sol, high effort |
| Complicated coding (nuanced, multi-file, or history-rewriting) | codex, gpt-5.6-sol, high effort |
| Bulk mechanical sweeps | pi (cheap, 1M window) |
| Final fresh-context review (attended only) | a strong model from a *different family* than both the implementers and the orchestrator — pick from kimi k3 max, codex gpt-5.6-sol high, claude fable 5 high |

Prompt sizing follows the same judgment, and the default is **thin**: pass the
task in the user's own words and add nothing. That is spawn-worker's §1 rule
and it holds here — a task carrying little from this session ("summarize the
top 10 posts on my X home feed") gets exactly those words. Workers are
intelligent enough to work out the how; every sentence you add spends
orchestrator tokens to make the worker worse at choosing its own approach.

Add only what the worker cannot know or infer:

- constraints that are actually real — the disjoint file set when parallel
  workers share a checkout (§3), a fenced shared resource, a path or finding
  from this session the task fails without
- a done condition, one sentence, when the task is open-ended enough to run on
  or stop and ask (matters more unattended: nobody is on call, so a worker
  that asks is a wasted worker)
- the mechanism, acceptance criteria, and expected review artifact — only for
  genuinely error-prone tasks (identity/history rewrites, safety-critical SQL)

Never prescribe implementation for a task the worker can explore, and never
add process boilerplate ("be thorough", "write tests first", "report back").

Unattended, route one tier up when you hesitate: there is no follow-up cycle
to correct a worker that guessed wrong, so pay for the deeper model instead.

## 3. Coordinate shared state

Workers must not step on each other:

- **Same repo, parallel workers**: give each a disjoint file set in the shared
  checkout and say so in each prompt ("other agents are working on other files
  in this checkout; only modify X and Y"). Prefer the shared checkout over git
  worktrees when the project is an editable-installed package — pytest imports
  resolve to the installed checkout, so a worktree silently tests the wrong
  code. Use worktrees only when file sets genuinely overlap.
- **Single-writer resources** (a DuckDB file, a port, a deploy target): fence
  everyone but the writer to read-only in their prompts. Attended, at most one
  worker writes it per wave, with waves sequenced so writers never overlap;
  unattended there are no waves, so at most one writer *total*.
- **Dependent tasks**: if task B edits a file task A also edits, or builds on
  conventions A may change — attended, B runs in a later wave, after A is
  reviewed and committed; unattended, fold B into A's prompt as one larger
  task for one worker, or drop it from this run and tell the user it needs a
  second pass after A lands.

## 4. Unattended: spawn in parallel and hand back

Only in unattended mode; attended runs skip to §5.

Waves are a review-gated device, and unattended has no review gate — so
whatever you spawn must be **fully independent** (§3's unattended variants)
before you spawn it. If the split collapses to one task, this reduces to
plain spawn-worker: spawn it, report the tab, stop.

Spawn every task at once in spawn-worker's plain default mode — not attended
mode, no `herdr agent wait`, no retained handles beyond what you report. Say
nothing about commits — there is no orchestrator waiting to commit on the
worker's behalf — unless the task itself calls for one, in which case the
prompt scopes it to that worker's own files (never `git add -A`, never push).

Report once and stop: the per-task split with each task's file set, and one
line per worker giving the label, agent, and tab. That mapping is the whole
deliverable — it is how the user finds and judges the work later. Then do not
poll, wait, read panes, or review on your own initiative, and leave the tabs
for the user to close. If they want a review afterwards, that is a new
request (a §6-style fresh-context reviewer, or `/code-review` over the range).

## 5. Attended: review every worker; workers never commit

Workers leave changes in the working tree; the orchestrator reviews and
commits per task. This keeps mixed parallel output reviewable (disjoint file
sets = clean per-task diffs) and makes you the accountability point — so
"do not git commit" goes in every attended prompt.

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
   progress doc if you kept one.

## 6. Attended: finish with a fresh-context cross-model review

After everything is committed, spawn one reviewer from a different model
family, fenced (no commits, no writes to protected resources), over the whole
range (`base..HEAD`), with a review-then-fix mandate: fix real issues directly
+ add tests; report-only anything that is a judgment call or would rewrite
data/history. Fresh context catches what every in-context reviewer misses —
integration seams between tasks (a DAG-position mismatch, a test suite nobody
re-ran after a later commit changed its fixture's assumptions). Review the
reviewer the same way as §5 (verify its critical find empirically before
believing it), then commit its surviving fixes.

## 7. Attended: wrap up

Push once the batch is coherent, close out the plan doc if there is one, and
report per task: what landed (commit), what was rejected/reworked and why, what
was report-only. Leave worker tabs for the user to close (spawn-worker's rule).

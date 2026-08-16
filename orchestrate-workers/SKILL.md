---
name: orchestrate-workers
description: Run a multi-task job as an orchestrator - split the work into tasks, gauge each task's difficulty, route each to its project's workspace, spawn workers on cheaper models in parallel, then either hand the tabs back and walk away (unattended, the default), or review every diff and close with a fresh-context strong-model review (attended). Use whenever the user asks to "orchestrate this", "act as orchestrator", "split this into tasks and assign to workers", "parallelize this across workers/agents", or hands over a batch of related fixes/features - especially when the main session runs on an expensive model (Fable/Opus) and implementation should happen on cheaper workers. Use attended mode when the user says "attended", "review the work", "stay on call", "answer their questions", or asks you to commit the results. Not the auto-trigger for one delegated task (spawn-worker owns that), but once invoked always delegate: even a one-task or question-shaped prompt goes to a worker as-is, never answered in-session.
---

# Orchestrate workers

Act as the conductor, not the implementer. The orchestrator session (often on an
expensive model) plans, routes, coordinates, and — in attended mode — reviews
and commits; spawned workers (on cheaper models) explore, implement, and test.
The economics only work if you resist doing implementation yourself and resist
over-specifying prompts — both burn orchestrator tokens on work a worker can
figure out. Answering counts as implementing: this session lives across many
rounds of batches, and context spent scouting or solving one prompt's substance
is stolen from every later round.

Spawning mechanics and prompt hygiene belong to the **spawn-worker** skill
(read it). This skill owns what spawn-worker deliberately doesn't:
decomposition, routing, conflict coordination, and the review discipline.

## Modes

- **Unattended (default)** — split if splitting helps, spawn everything in
  spawn-worker's plain default mode (all at once when independent, in
  completion-gated waves when not — §5), report where the tabs are, stop.
  Simple and fast — right for most runs. §1–§5, then done.
- **Attended** — workers spawn in spawn-worker's attended mode, you review
  every diff and commit per task (§6), and a fresh-context reviewer closes
  the batch (§7). §1–§4, then §6–§8.

Pick attended only when the user asks for it (the triggers in the
description, or a `/orchestrate-workers attended …` invocation) — reviewing
and committing on the workers' behalf is what earns its cost. Everything in
§1–§4 applies to both modes, and matters *more* unattended: a bad split there
has no review pass to catch it.

## 1. Plan before spawning

- **Invoked means delegate.** The user chose this skill over just asking you —
  that choice is itself the instruction to keep the work out of this session,
  and it still holds when the prompt turns out to be a single task or a
  question. A design question, an "I wonder what's the best way to…", a
  one-file fix: each is one task for one worker, who investigates and answers
  in its own tab and context. Do not scout the code to answer it yourself, do
  not answer and offer to spawn a worker for the follow-up, and do not turn it
  into an options menu for the user — deciding, or recommending, is part of
  what gets delegated. Handle a prompt inline only when it is about this
  session itself (steering a batch already running, reporting on workers you
  spawned).
- **Split only when the split buys something.** Tasks exist to run in
  parallel; a division that yields dependent pieces, or pieces one worker
  would have done anyway, costs coordination and buys nothing. If the job is
  really one task, that is one worker — spawn it and stop, don't manufacture a
  breakdown. Splitting is also wrong when the pieces cannot be made
  file-disjoint, or when they form a single sequential chain — waves (§4, §5)
  pay only when each wave holds several parallel tasks; a pure chain is one
  worker's job.
- **Match the planning to the job.** A handful of obvious tasks needs no
  artifact — work the split out in your head, name each task, note who touches
  what, spawn. Write the breakdown down only when the job is big enough to
  lose track of: many tasks, multiple waves, or a run long enough to be
  compacted. Then it is a goal-mode plan doc holding tasks, dependencies,
  shared resources, and planned waves, mirrored as you go — that doc is what
  survives compaction and lets the user audit mid-run.
- **A self-contained prompt passes through untouched.** When the prompt leans
  on nothing from this session, the split, tier (§2), and workspace (§3) are
  all decidable from its own words — decide them from the prompt alone and
  spawn with zero file reads. Scout yourself (a grep, reading an issue note)
  only when a split or routing decision genuinely cannot be made from the
  prompt, and then only to *scope* tasks, never to solve them. You don't need
  implementation details to judge a task's difficulty.

## 2. Route by difficulty

Gauge each task and pick the worker tier (defaults that have worked; adjust to
what's installed):

| Task shape | Worker |
|---|---|
| Very easy task without much judgment (simple script changes, moving files) or bulk mechanical sweeps | pi, MiniMax-M3, high effort (`--model minimax/MiniMax-M3 --effort high`) |
| Straightforward self-contained coding task or fix, or simple non-coding task needing some judgment (absorb an article, summarize news, research notes, write a wiki) | claude, opus, high effort |
| Skill creation or edits — global (`~/skills`) or project-local (`skills/`) | claude, Fable 5 (`--model fable`), high effort — always, regardless of gauged difficulty |
| Complicated and taste-heavy (research articles, investment thesis) | claude, Fable 5 (`--model fable`), high effort — if Fable quota is ≥85% used, kimi, k3, max effort |
| Complicated coding (nuanced, multi-file, or history-rewriting) | codex, gpt-5.6-sol, high effort |
| Final fresh-context review (attended only) | prefer the strongest model from a *different family* than both the implementers and the orchestrator (kimi k3 max, codex gpt-5.6-sol high); a same-family model is also fine when it is strictly stronger than both orchestrator and workers (e.g. claude Fable 5 high over opus workers) |

For Claude workers on Fable 5, the value the CLI accepts is `--model fable` —
`fable-5` is rejected at startup ("selected model may not exist").

Check Fable quota with the `claude-quota` command: every percentage it prints
is quota *used*, and any window at ≥85% (session, weekly, or the
Fable-scoped window — all of them gate a Claude worker) flips taste-heavy
routing to kimi. `claude-quota --check 85` does the threshold test in one
call (exit 1 = at least one window ≥85%); run it standalone, never batched
with other commands.

Prompt sizing is spawn-worker §1's rule, unchanged: thin by default — the
task in the user's own words, nothing added. On top of it, add only what
orchestration itself creates:

- the §4 constraints — the worker's disjoint file set in a shared checkout,
  a fenced single-writer resource — plus any path or finding from this
  session the task fails without
- a one-sentence done condition when the task could run on or stop and ask
  (spawn-worker's rule, but it matters more unattended: nobody is on call,
  so a worker that asks is a wasted worker)
- the mechanism, acceptance criteria, and expected review artifact — only for
  genuinely error-prone tasks (identity/history rewrites, safety-critical SQL)

Unattended, route one tier up when you hesitate: there is no follow-up cycle
to correct a worker that guessed wrong, so pay for the deeper model instead.

## 3. Route each task to its project's workspace

Workers run where their project lives, not wherever the orchestrator happens
to sit. Read `references/project-routing.md` before assigning — it owns the
routing rule (current project first, then match by what the task *touches*,
else stay in the orchestrator's workspace) and the project inventory with
labels and match keywords. Out-of-project workers spawn with the owning
project's directory as cwd plus `--workspace-label <label>` (mechanics in
spawn-worker §2). Cross-workspace placement is herdr-only — on cmux/tmux
spawn everything in the orchestrator's session. Waves (§5) and attended
waits work unchanged across workspaces: herdr handles are global within one
herdr server.

Workers on a remote box route the same way — same match rule, same labels —
with the placement details in the routing doc's remote section. Handles live
in the box's herdr server, so every wave gate and attended wait on one takes
an `ssh <host>` prefix. Route there only when the user asks for the box, and
never for a task whose result has to land in the Mac's working tree: a
remote worker edits the box's checkout, so attended review (§6) becomes
reading the diff and committing over ssh.

## 4. Coordinate shared state

Workers must not step on each other:

- **Same repo, parallel workers**: give each a disjoint file set in the shared
  checkout and say so in each prompt ("other agents are working on other files
  in this checkout; only modify X and Y"). Prefer the shared checkout over git
  worktrees when the project is an editable-installed package — pytest imports
  resolve to the installed checkout, so a worktree silently tests the wrong
  code. Use worktrees only when file sets genuinely overlap.
- **Single-writer resources** (a DuckDB file, a port, a deploy target): fence
  everyone but the writer to read-only in their prompts. In either mode, at
  most one worker writes it per wave, with waves sequenced so writers never
  overlap — so a single-wave run gets at most one writer *total*.
- **Dependent tasks**: if task B edits a file task A also edits, or builds on
  conventions A may change — B runs in a later wave than A. Attended, the
  wave boundary is a review gate: B spawns after A is reviewed and committed;
  unattended, §5 owns the gate. When B is small, or the backend cannot wait
  (§5), instead fold B into A's prompt as one larger task for one worker, or
  drop it from this run and tell the user it needs a second pass after A
  lands.

## 5. Unattended: spawn in parallel, wave when dependent, hand back

Only in unattended mode; attended runs skip to §6.

Everything spawned together must be **fully independent** (§4) — one wave,
the common case, means every task at once. If the split collapses to one
task, this reduces to plain spawn-worker: spawn it, report the tab, stop.

Workers go out in spawn-worker's plain default mode — never attended mode:
no "you may ask" sentence, no answering, no reading diffs. Say nothing about
commits — there is no orchestrator waiting to commit on the worker's behalf —
unless the task itself calls for one, in which case the prompt scopes it to
that worker's own files (never `git add -A`, never push).

When the split has genuine dependencies (§4), spawn in **waves**: each wave
a set of mutually independent tasks, each later wave building on the one
before. The gate between waves is **completion, not review** — retain the
current wave's handles, background `herdr agent wait` on them, and spawn the
next wave once they have all finished. Do not judge the work or send
follow-ups at the gate; a worker that stopped by asking instead of finishing
is a wasted worker (§2's done-condition rule) — note it in the report, don't
answer it. The gate needs herdr's event wait; on cmux/tmux there is no wait
API, so fall back to §4's fold-or-drop instead of waving.

**Never wait on the last wave.** Once the final wave is spawned there is
nothing left to gate — spawning it ends the run. Drop any retained handles;
a single-wave run is just this rule applied immediately.

Report once the final wave is spawned, then stop: the per-task split with
each task's file set (grouped by wave if there were waves), and one line per
worker giving the label, agent, and tab. That mapping is the whole
deliverable — it is how the user finds and judges the work later. Then
spawn-worker §3's posture applies unchanged: do not poll, wait, read panes,
or review on your own initiative, and leave the tabs for the user to close.
If they want a review afterwards, that is a new
request (a §7-style fresh-context reviewer, or `/code-review` over the range).

## 6. Attended: review every worker; workers never commit

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

## 7. Attended: finish with a fresh-context strong-model review

After everything is committed, spawn one reviewer on a strong model picked
by §2's review row — fenced (no commits, no writes to protected resources),
over the whole range (`base..HEAD`), with a review-then-fix mandate: fix
real issues directly + add tests; report-only anything that is a judgment
call or would rewrite
data/history. Fresh context catches what every in-context reviewer misses —
integration seams between tasks (a DAG-position mismatch, a test suite nobody
re-ran after a later commit changed its fixture's assumptions). Review the
reviewer the same way as §6 (verify its critical find empirically before
believing it), then commit its surviving fixes.

## 8. Attended: wrap up

Push once the batch is coherent, close out the plan doc if there is one, and
report per task: what landed (commit), what was rejected/reworked and why, what
was report-only. Leave worker tabs for the user to close (spawn-worker's rule).

---
name: plan-with-agent
description: Co-write and adversarially review a plan/design doc with a second agent (Codex or Claude) in a live herdr pane, using a draft-review loop, independent dual drafts followed by synthesis, or an alternating review-and-fix loop where the reviewer edits the plan directly and the two agents fix issues in turns. Use when the user explicitly asks to plan with Codex or Claude, requests a second-model opinion or review of a plan, asks for independent co-drafting, asks the second agent to fix or edit the plan directly, or explicitly requests a two-agent audit that produces a remediation plan. Do not auto-trigger for ordinary planning, diagnosis, code review, or audits that do not request a second agent. For second-agent review of code changes instead of a plan doc, use review-with-agent; for second-agent review of a skill, use skill-review-with-agent.
---

# Plan with Agent

Any harness and session model can drive this skill. The reviewer is a second frontier model — Codex (GPT) or Claude — running in a live pane beside you, chosen by the rules below. The one hard exclusion is self-review: the reviewer must never be the same model the session is running (same vendor at a higher tier is fine).

The output is a plan doc that survived adversarial review by a second frontier model. The reviewer keeps its context across rounds, and the user can watch it work and type into its pane.

## Ground rules (plan-mode discipline)

Planning is read-only with respect to the world:

- Never modify existing source code or production data (databases, data files).
- Allowed writes: the plan doc, the review log, the counterpart draft doc (flow 2), and ad-hoc scratch scripts for probing/debugging (put them in a temp dir, not the repo). Probes read production data; if a probe must write, run it against a scratch copy (e.g. a dev DB).
- The pane agent runs auto-approved with write access to the repo, so **every reviewer prompt must state** "Treat the repo and all data as read-only. Do not create or modify any files" — except the files a flow explicitly hands the reviewer: flow 2's draft turn may write its single draft doc, and flow 3's reviewer turns may write exactly the plan doc and the review log.

## Step 0 — Ground the requirement

Reviews are wasted on a plan built from wrong assumptions. Before drafting: explore the relevant code, run read-only probes if facts are uncertain, and clarify genuinely ambiguous requirements with the user. Distill the result into a **requirement brief** (one tight paragraph + key file paths + constraints/non-goals) — you'll paste it into every reviewer prompt.

## Choose a flow

- **Flow 1 — draft → review loop** (default): you write the plan, the reviewer reviews, you address, repeat.
- **Flow 2 — dual independent drafts**: you and the counterpart agent each write a plan from the same requirement brief *without seeing each other's*, you synthesize one plan, then enter the flow-1 review loop. Use when the solution space is wide (multiple viable architectures), the requirement is high-stakes or ambiguous after grounding, or the user asks for it. Also use it for *discovery-shaped* tasks — auditing an existing system to find all bugs/issues and propose fixes — where the value is coverage: an agent that reads the other's findings first anchors on them and confirms instead of hunting, so two fresh-minded independent sweeps catch more, and the synthesis step doubles as cross-checking each finding. Independent drafting only pays when there is real design freedom or real discovery to do; for a well-constrained requirement it just adds a synthesis step.
- **Flow 3 — alternating review-and-fix** (explicit opt-in only — never auto-select): the reviewer fixes issues directly in the plan doc each round, you verify its edits and fix what remains, alternating until a clean approve. Run it only when the user names it or asks for the reviewer to fix/edit the plan directly. It fits plans whose findings are numerous and mechanical (a dense multi-step plan where relaying findings as prose is the bottleneck); when a flow-1 loop is stalling on sheer volume of findings, you may *suggest* switching, but don't switch without the user's go-ahead. It trades the clean findings-and-dispositions protocol for fewer, cheaper rounds and lets an auto-approved agent edit the plan directly — that trade is the user's to make.

The user can name a flow explicitly; that wins. Between flows 1 and 2, pick by the criteria above. Flows 2 and 3 compose: a flow-2 synthesis can enter either the flow-1 review loop or, if the user opted into it, flow 3.

## Choose the reviewer

Never self-review — not the exact model running this session (if the session's exact model is unknown, choose the other vendor). Honor an explicit user choice of vendor, model, or effort subject to that exclusion; if the user requests the current model, explain the conflict and switch only with their agreement. Otherwise default review rounds (flows 1 and 2) to a cross-vendor reviewer one capability tier stronger, or the strongest cross-vendor peer when the session is already top-tier; a stronger same-vendor model is acceptable for unusually hard requirements when diversity matters less than raw capability.

Read [references/model-selection.md](references/model-selection.md) before selecting a concrete model and effort — it owns the dated roster, the effort mapping, and the rationale for the two deliberate peer-tier exceptions: flow 2's independent draft (competitive alternatives matter more than reviewer authority) and flow 3's direct-edit turns (covered by the alternating reference below).

## Invoking the counterpart

Spawning, placement, waiting, reading, the next-round prompt, and the shared round
protocol — finding verification, dispositions, the round cap, stopping, escalation,
wrap-up — live in
[`~/skills/review-with-agent/references/herdr-review-loop.md`](../review-with-agent/references/herdr-review-loop.md),
shared with both review skills — follow it for every turn.

The counterpart is a live pane agent, so unlike the one-shot calls this skill used to
make, it keeps its context: a follow-up round is what changed and what you rejected, not
a restated requirement brief. Spawn it with the repo as its cwd so it can read the plan
doc and the code the plan is about.

**Flow 2 has an independence hazard the one-shot version did not.** A pane agent can read
the filesystem, so it can find your draft in `docs/plans/` and anchor on it — which
destroys the only thing flow 2 buys. Spawn the counterpart *before* you start writing,
give it the requirement brief and its own output path, and tell it plainly not to read
the other drafts in that folder. Drafting in parallel is also simply faster than the
serialized one-shot version: it works while you write.

## Artifacts

Each planning effort gets its own subfolder `docs/plans/YYYY-MM-DD_<slug>/` (create it if missing) — an effort produces up to three docs, and one folder per effort keeps `docs/plans/` scannable:

- `plan.md` — goal, current state, design, alternatives considered, step-by-step implementation, testing/verification, risks & rollback.
- `review.md` — one `## Round N` section per review: the reviewer's verdict + findings, then your disposition per finding. Name the reviewer model in each round header. In flow 3 the reviewer appends the round section (edits made + findings raised), then you append a `### Session turn` subsection with dispositions (`REVERTED`/`REJECTED`/`DEFERRED`/accepted) and a summary of your own changes.
- `codex-draft.md` / `claude-draft.md` (flow 2 only) — the counterpart's independent draft, named by agent, kept as a record of the road not taken.

## Flow 2 — independent drafts, then synthesize

1. Write your own plan draft (do not read the counterpart's first).
2. In parallel, ask the counterpart agent to write its plan to the effort folder's draft file — give it the same requirement brief you drafted from, and name that file as the one file it may write.
3. Synthesize: don't merge everything — pick the stronger skeleton, graft the other draft's better ideas, and note real divergences (they're usually the decisions worth surfacing to the user).
4. Enter the review loop below (or flow 3, if chosen) with the synthesized plan.

## Flow 3 — alternating review-and-fix

The reviewer fixes the plan doc directly, then you verify its edits, fix what remains, and hand it back, replacing the review loop below. Follow the shared protocol in [references/alternating-review-fix.md](references/alternating-review-fix.md) — reviewer choice, division of labor, turn cap, the per-cycle steps, verdict rubric, and stop/escalation rules. This flow's specifics:

- The writable artifacts are `plan.md` and the append-only `review.md`. Snapshot them into a round temp dir before each turn: copy `plan.md`, and copy `review.md` or record that it does not yet exist (restoring an unusable turn then includes removing a newly created `review.md`).
- The ground truth for verifying reviewer edits and findings is the repo's actual code.
- The explicit write boundary is the guardrail; do not add custom Git-state reconstruction. If an unexpected repository edit is noticed, stop and preserve it for inspection rather than discarding files wholesale.

Reviewer-turn prompt shape:

```
You are reviewing AND fixing an implementation plan. Treat the repo and all
data as read-only, with exactly two files you may edit:
- plan doc: <absolute path to plan.md>
- review log (append-only): <absolute path to review.md>

Requirement: <brief>
Repo: <root>; relevant code: <paths>
Constraint: this is a planning-stage review — the plan must not require
modifying production data; implementation happens later.
Prior rounds (do not re-raise or re-apply items marked REJECTED or REVERTED
unless you have a genuinely new argument): <digest of prior rounds, or "none">

Review for: correctness vs the requirement, feasibility against the actual
code, missing steps / edge cases / risks, sequencing, testability and
verification, scope creep. Then act on each finding:
- Factual or mechanical findings (wrong paths, missing steps, wrong
  sequencing, missing verification): fix directly in the plan doc.
- Design-level disagreements: do NOT rewrite the plan — record the finding
  as RAISED and leave the plan text alone.
- Do not alter or delete existing review-log content. Append exactly one
  "## Round N — <your model> (reviewer turn)" section: each finding as
  [blocker|major|minor|nit] <title> — <what & where> — then
  FIXED — <edit made> or RAISED — <suggested resolution>. Append the section
  even if you have no findings — state your verdict and "No findings".

Output format — first line exactly:
VERDICT: APPROVE | REVISED | REVISE
- APPROVE if and only if you made no edits to the plan doc and no blocker or
  major findings remain (minor/nit RAISED findings may accompany APPROVE).
- REVISED if you edited the plan doc and no blocker or major finding is left
  unfixed.
- REVISE if blocker or major findings remain RAISED (fixable only by a
  design decision).
The required append to the review log does not count as an edit for this
verdict rubric.
Then bullet-summarize your edits and RAISED findings.
```

## The review loop

Flows 1 and 2; flow 3 replaces this loop with the alternating protocol above. Each round, send the reviewer a prompt shaped like:

```
You are reviewing an implementation plan. Reviewing only — treat the repo
and all data as read-only; do not create or modify any files.

Requirement: <brief>
Plan doc: read <absolute path>
Repo: <root>; relevant code: <paths>
Constraint: this is a planning-stage review — the plan must not require
modifying production data; implementation happens later.
Prior rounds (do not re-raise items marked REJECTED unless you have a
genuinely new argument): <digest of prior findings + dispositions, or "none">

Review for: correctness vs the requirement, feasibility against the actual
code, missing steps / edge cases / risks, sequencing, testability and
verification, scope creep.

Output format — first line exactly:
VERDICT: APPROVE | REVISE
Then each finding on its own bullet:
[blocker|major|minor|nit] <title> — <what & where in the plan> — <suggested fix>

Verdict rubric:
- APPROVE if and only if no blocker or major findings remain. Minor and nit
  findings may accompany APPROVE.
- REVISE if one or more blocker or major findings remain.
```

Then address the round per the shared reference's round protocol — verifying the reviewer's factual claims against the code, since a confident-sounding wrong finding rewrites a correct plan — and append it to the review log (verdict, findings, per-finding disposition) before re-reviewing with the updated plan and an updated history digest. The shared reference's cap, stop, and escalation rules apply; flow 2's draft turn doesn't count toward the cap.

## Wrap-up

Wrap up per the shared reference; include the plan doc path, any material capability asymmetry in a flow-3 pairing, and any reverted reviewer edits.

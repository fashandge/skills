---
name: plan-with-agent
description: Co-write and adversarially review a plan/design doc with a second agent (Codex or Claude) in a live herdr pane, using a draft-review loop, independent dual drafts followed by synthesis, or an alternating review-and-fix loop where the reviewer edits the plan directly and the two agents fix issues in turns. Use when the user explicitly asks to plan with Codex or Claude, requests a second-model opinion or review of a plan, asks for independent co-drafting, asks the second agent to fix or edit the plan directly, or explicitly requests a two-agent audit that produces a remediation plan. Do not auto-trigger for ordinary planning, diagnosis, code review, or audits that do not request a second agent. For second-agent review of code changes instead of a plan doc, use review-with-agent; for second-agent review of a skill, use skill-review-with-agent.
---

# Plan with Agent

The output is a plan doc that survived adversarial review by a second frontier model — Codex (GPT) or Claude — running in a live herdr pane beside you, where the user can watch it work and type into it. Any harness and session model can drive this skill.

**Read [`~/skills/review-with-agent/references/herdr-review-loop.md`](../review-with-agent/references/herdr-review-loop.md) for the mechanics and the loop protocol** — spawning, placement, waiting, reading, follow-up prompts, finding verification and dispositions, the round cap, stopping, escalation, and wrap-up. It is shared with `review-with-agent` and `skill-review-with-agent` so the siblings cannot drift. This file owns what is specific to a plan doc.

## Ground rules (plan-mode discipline)

Planning is read-only with respect to the world:

- Never modify existing source code or production data (databases, data files).
- Allowed writes: the effort folder's docs (see Artifacts) and ad-hoc scratch scripts for probing/debugging, kept in a temp dir, not the repo. Probes read production data; if a probe must write, run it against a scratch copy (e.g. a dev DB).
- The pane agent runs auto-approved with write access to the repo, so every prompt names the files it may write (none in a review turn; its draft file in flow 2; `plan.md` and `review.md` in flow 3) and declares everything else read-only. The templates below already do.

## Step 0 — Ground the requirement

Reviews are wasted on a plan built from wrong assumptions. Before drafting: explore the relevant code, run read-only probes if facts are uncertain, and clarify genuinely ambiguous requirements with the user. Distill the result into a **requirement brief** (one tight paragraph + key file paths + constraints/non-goals) — it goes into the spawn prompt.

## Choose a flow

- **Flow 1 — draft → review loop** (default): you write the plan, the reviewer reviews, you address, repeat.
- **Flow 2 — dual independent drafts**: you and the counterpart agent each write a plan from the same requirement brief *without seeing each other's*, you synthesize one plan, then enter the flow-1 review loop. Use when the solution space is wide (multiple viable architectures), the requirement is high-stakes or ambiguous after grounding, or the user asks for it. Also use it for *discovery-shaped* tasks — auditing an existing system to find all bugs/issues and propose fixes — where the value is coverage: an agent that reads the other's findings first anchors on them and confirms instead of hunting, so two fresh-minded independent sweeps catch more, and the synthesis step doubles as cross-checking each finding. For a well-constrained requirement it just adds a synthesis step.
- **Flow 3 — alternating review-and-fix** (explicit opt-in only — never auto-select): the reviewer fixes issues directly in the plan doc each round, you verify its edits and fix what remains, alternating until a clean approve. Run it only when the user names it or asks for the reviewer to fix/edit the plan directly. It fits plans whose findings are numerous and mechanical; when a flow-1 loop is stalling on sheer volume of findings, you may *suggest* switching, but don't switch without the user's go-ahead. It trades the clean findings-and-dispositions protocol for fewer, cheaper rounds and lets an auto-approved agent edit the plan directly — that trade is the user's to make.

The user can name a flow explicitly; that wins. Between flows 1 and 2, pick by the criteria above. Flows 2 and 3 compose: a flow-2 synthesis can enter either the flow-1 review loop or, if the user opted into it, flow 3.

## Choose the reviewer

Never self-review — not the exact model running this session (if unknown, choose the other vendor). Honor an explicit user choice of vendor, model, or effort subject to that; if the user asks for the session's own model, explain the conflict and switch only with their agreement. Otherwise default to a cross-vendor reviewer one tier stronger, or the strongest cross-vendor peer when the session is already top-tier. Read [references/model-selection.md](references/model-selection.md) for the roster, the session→reviewer mapping, and effort — one effort per model, set at spawn and kept for every round. Flow 3 prefers a peer-tier pairing; the alternating reference says why.

Spawn the reviewer with the repo as its cwd so it can read the plan doc and the code the plan is about.

## Artifacts

Each planning effort gets its own subfolder `docs/plans/YYYY-MM-DD_<slug>/`; create it, and an empty `review.md` in it, before drafting:

- `plan.md` — goal, current state, design, alternatives considered, step-by-step implementation, testing/verification, risks & rollback.
- `review.md` — one `## Round N — <reviewer model>` section per round: verdict and findings, then your disposition per finding. In flow 3 the reviewer appends the round section and you append a `### Session turn` subsection (the alternating reference owns the format).
- `codex-draft.md` / `claude-draft.md` (flow 2 only) — the counterpart's independent draft, kept as the road not taken.

## The review loop (flows 1 and 2)

Spawn the reviewer with the prompt below. Later rounds are short follow-ups to the same pane per the shared reference — what changed, what you rejected and why, blockers and majors only — not a restated brief.

```
You are reviewing an implementation plan. Reviewing only — treat the repo
and all data as read-only; do not create or modify any files.

Requirement: <brief>
Plan doc: read <absolute path>
Repo: <root>; relevant code: <paths>
Constraint: this is a planning-stage review — the plan must not require
modifying production data; implementation happens later.

Review for: correctness vs the requirement, feasibility against the actual
code, missing steps / edge cases / risks, sequencing, testability and
verification, scope creep. Prefer a short list of substantive findings over
an exhaustive list of small ones; do not propose re-architecture or added
scope unless a real defect requires it.

Output format — first line exactly:
VERDICT: APPROVE | REVISE
Then each finding on its own bullet:
[blocker|major|minor|nit] <title> — <what & where in the plan> — <suggested fix>

Verdict rubric:
- APPROVE if and only if no blocker or major findings remain. Minor and nit
  findings may accompany APPROVE.
- REVISE if one or more blocker or major findings remain.
```

In flow 2 the reviewer is the drafting pane, so the first review is a follow-up prompt rather than a spawn: point it at the synthesized plan with the review instructions above, and name which of its draft's ideas you adopted and dropped, and why.

Then address the round per the shared reference's round protocol — verifying the reviewer's factual claims against the code, since a confident-sounding wrong finding rewrites a correct plan — and append it to the review log before sending the next round. The shared reference's cap, stop, and escalation rules apply; flow 2's draft turn does not count toward the cap.

## Flow 2 — independent drafts, then synthesize

The hazard is independence: a pane agent can read the filesystem, so it can find your draft and anchor on it, which destroys the only thing flow 2 buys. So spawn the counterpart **before you start writing**, with the review-round model, and draft in parallel:

```
Write an implementation plan. Treat the repo and all data as read-only; the
one file you may create is <absolute path to the draft file>. Do not read
anything else under <effort folder> — another draft is being written there
in parallel and yours must be independent of it.

Requirement: <brief>
Repo: <root>; relevant code: <paths>
Constraint: planning only — the plan must not require modifying production
data; implementation happens later.

Sections: goal, current state, design, alternatives considered,
step-by-step implementation, testing/verification, risks & rollback.
```

Then:

1. Write your own `plan.md` from the same brief without reading the counterpart's draft.
2. Once both exist, synthesize: don't merge everything — pick the stronger skeleton, graft the other draft's better ideas, and note real divergences (they're usually the decisions worth surfacing to the user).
3. Enter the review loop above (or flow 3, if chosen) with the synthesized plan, reusing the drafting pane as the reviewer.

## Flow 3 — alternating review-and-fix

The reviewer fixes the plan doc directly, then you verify its edits, fix what remains, and hand it back, replacing the review loop above. Follow [references/alternating-review-fix.md](references/alternating-review-fix.md) for the turn protocol — reviewer choice, division of labor, turn cap, per-cycle steps, verdict rubric, stop/escalation. This flow's specifics:

- The writable artifacts are `plan.md` and the append-only `review.md`. Before each reviewer turn, copy both to a round temp dir; restoring an unusable turn copies them back.
- Also record `git status --porcelain` before each turn and compare it after. The write boundary in the prompt is the guardrail; this is the cheap check that it held. If the reviewer touched anything else, stop and preserve it for inspection rather than discarding files wholesale — do not add custom Git-state reconstruction.
- The ground truth for verifying reviewer edits and findings is the repo's actual code.

Reviewer-turn prompt — the spawn prompt, or a follow-up to the drafting pane when entering from flow 2; later turns are short follow-ups per the alternating reference:

```
You are reviewing AND fixing an implementation plan. Treat the repo and all
data as read-only, with exactly two files you may edit:
- plan doc: <absolute path to plan.md>
- review log (append-only): <absolute path to review.md>

Requirement: <brief>
Repo: <root>; relevant code: <paths>
Constraint: this is a planning-stage review — the plan must not require
modifying production data; implementation happens later.

Review for: correctness vs the requirement, feasibility against the actual
code, missing steps / edge cases / risks, sequencing, testability and
verification, scope creep. Prefer a short list of substantive findings over
an exhaustive list of small ones; do not propose re-architecture or added
scope unless a real defect requires it. Then act on each finding:
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

## Wrap-up

Wrap up per the shared reference; include the plan doc path, any material capability asymmetry in a flow-3 pairing, and any reverted reviewer edits.

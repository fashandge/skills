---
name: plan-with-agent
description: Co-write and adversarially review a plan/design doc with a second agent (Codex or Claude, called via agents-cli), using a draft-review loop, independent dual drafts followed by synthesis, or an alternating review-and-fix loop where the reviewer edits the plan directly and the two agents fix issues in turns. Use when the user explicitly asks to plan with Codex or Claude, requests a second-model opinion or review of a plan, asks for independent co-drafting, asks the second agent to fix or edit the plan directly, or explicitly requests a two-agent audit that produces a remediation plan. Do not auto-trigger for ordinary planning, diagnosis, code review, or audits that do not request a second agent. For second-agent review of code changes instead of a plan doc, use review-with-agent; for second-agent review of a skill, use skill-review-with-agent.
---

# Plan with Agent

Any harness and session model can drive this skill. The reviewer is a second frontier model called via `agents-cli` — Codex (GPT) or Claude — chosen by the rules below. The one hard exclusion is self-review: the reviewer must never be the same model the session is running (same vendor at a higher tier is fine).

The output is a plan doc that survived adversarial review by a second frontier model. Each `agents-cli` call is fresh-context and one-shot, so every prompt must be fully self-contained.

## Ground rules (plan-mode discipline)

Planning is read-only with respect to the world:

- Never modify existing source code or production data (databases, data files).
- Allowed writes: the plan doc, the review log, the counterpart draft doc (flow 2), and ad-hoc scratch scripts for probing/debugging (put them in a temp dir, not the repo). Probes read production data; if a probe must write, run it against a scratch copy (e.g. a dev DB).
- `agents-cli` runs the reviewer auto-approved, so **every reviewer prompt must state** "Treat the repo and all data as read-only. Do not create or modify any files" — except the files a flow explicitly hands the reviewer: flow 2's draft call may write its single draft doc, and flow 3's reviewer turns may write exactly the plan doc and the review log.

## Step 0 — Ground the requirement

Reviews are wasted on a plan built from wrong assumptions. Before drafting: explore the relevant code, run read-only probes if facts are uncertain, and clarify genuinely ambiguous requirements with the user. Distill the result into a **requirement brief** (one tight paragraph + key file paths + constraints/non-goals) — you'll paste it into every reviewer prompt.

## Choose a flow

- **Flow 1 — draft → review loop** (default): you write the plan, the reviewer reviews, you address, repeat.
- **Flow 2 — dual independent drafts**: you and the counterpart agent each write a plan from the same requirement brief *without seeing each other's*, you synthesize one plan, then enter the flow-1 review loop. Use when the solution space is wide (multiple viable architectures), the requirement is high-stakes or ambiguous after grounding, or the user asks for it. Also use it for *discovery-shaped* tasks — auditing an existing system to find all bugs/issues and propose fixes — where the value is coverage: an agent that reads the other's findings first anchors on them and confirms instead of hunting, so two fresh-minded independent sweeps catch more, and the synthesis step doubles as cross-checking each finding. Independent drafting only pays when there is real design freedom or real discovery to do; for a well-constrained requirement it just adds a synthesis step.
- **Flow 3 — alternating review-and-fix** (explicit opt-in only — never auto-select): the reviewer fixes issues directly in the plan doc each round, you verify its edits and fix what remains, alternating until a clean approve. Run it only when the user names it or asks for the reviewer to fix/edit the plan directly. It fits plans whose findings are numerous and mechanical (a dense multi-step plan where relaying findings as prose is the bottleneck); when a flow-1 loop is stalling on sheer volume of findings, you may *suggest* switching, but don't switch without the user's go-ahead. It trades the clean findings-and-dispositions protocol for fewer, cheaper rounds and lets an auto-approved agent edit the plan directly — that trade is the user's to make.

The user can name a flow explicitly; that wins. Between flows 1 and 2, pick by the criteria above. Flows 2 and 3 compose: a flow-2 synthesis can enter either the flow-1 review loop or, if the user opted into it, flow 3.

## Choose the reviewer

Apply these principles in order:

1. **Never self-review.** Do not use the exact model running this session. If the session's exact model is unknown, choose the other vendor.
2. **Honor an explicit user choice** of vendor, model, or effort unless it violates the self-review exclusion. If the user requests the current model, explain the conflict and use a different model only with their agreement.
3. **Default first-pass reviews one tier up.** For review rounds in flows 1 and 2, use a cross-vendor reviewer one capability tier stronger when available. If the session is already top-tier or no stronger cross-vendor reviewer is available, use the strongest cross-vendor peer. A stronger same-vendor model is acceptable for unusually hard requirements when diversity matters less than raw capability.

Read [references/model-selection.md](references/model-selection.md) before selecting a concrete model and effort. It owns the dated roster and effort mapping so volatile model names do not dominate this workflow. For default selections, keep the same reviewer model for follow-up rounds but lower its effort; an explicit user effort still wins. Flow 2's independent draft and flow 3's direct-edit turns are deliberate peer-tier exceptions, described below.

For flow 2's independent draft, choose a peer-tier cross-vendor counterpart. Drafting wants competitive alternatives; use extra intelligence in the subsequent review path rather than letting a stronger counterpart dominate synthesis.

For flow 3, prefer a **cross-vendor, peer-tier reviewer**; a modestly stronger reviewer is acceptable. Alternating direct edits only provide a meaningful cross-check when both agents can independently detect mistakes made by the other. If the available pairing has a material capability gap in either direction, tell the user and recommend flow 1, where proposed changes remain explicit findings rather than already-applied edits. If they stick with flow 3, honor it, but report the reduced cross-check confidence rather than implying symmetric verification.

## Invoking the reviewer

Command templates, required flags, and the retry/failure rules live in [references/invoking-agents-cli.md](references/invoking-agents-cli.md) (shared with the `review-with-agent` skill — edit them there). Follow it for every call. Remember every call is one-shot: include the requirement brief, paths, constraints, and review history in each prompt.

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

The reviewer doesn't just report findings — it fixes the plan doc directly, then you review its edits, fix what remains, and hand it back. This replaces the review loop below; the loop's discipline (verify before accepting, logged dispositions, escalation rules) carries over, applied to edits instead of findings.

The division of labor is severity-agnostic but *kind*-sensitive: the reviewer fixes **factual and mechanical** findings in place (wrong paths, missing steps, wrong sequencing, missing verification) and must **raise design-level disagreements as findings without rewriting them** — a silently rewritten design decision buries exactly the disagreement the review exists to surface.

Up to **4 reviewer calls**. Each cycle:

1. Create a round temp dir. Snapshot both writable artifacts before the call: copy `plan.md`, and copy `review.md` or record that it does not yet exist. Capture reviewer stdout in this temp dir too.
2. Invoke the reviewer from the repo root with the prompt below and capture stdout. The explicit write boundary is the guardrail; do not add custom Git-state reconstruction. If an unexpected repository edit is noticed, stop and preserve it for inspection rather than discarding files wholesale.
3. Verify `review.md` changed append-only: its previous bytes must be intact and exactly one new `## Round N` reviewer section may have been appended. Treat any overwrite, earlier-round edit, duplicate round, or missing entry as an unusable call.
4. If the result is unusable under the shared retry rules, restore both writable artifacts exactly to their pre-call state (including removing a newly created `review.md`), then retry. Never retry or fall back atop a partial reviewer mutation.
5. Diff `plan.md` against its snapshot and **verify every edit against the code** — a confident wrong fix is worse than a wrong finding, because it is already in the plan. Revert wrong edits and record `REVERTED — <why>` in your `### Session turn` subsection (step 7) — never edit the reviewer's own entry.
6. Address the reviewer's RAISED findings: fix them; reject an incorrect finding with `REJECTED — <why>`; or intentionally leave a valid minor/nit unchanged with `DEFERRED — <why>`. Never silently drop one. Then make any further improvements of your own.
7. Append a `### Session turn` subsection to the round in `review.md`: per-edit and per-finding dispositions, plus a summary of your own changes. If the round has not converged, send the next reviewer turn with an updated history digest.

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

**Stop when:** a reviewer turn returns `VERDICT: APPROVE` **and your handling of that turn makes no further change to `plan.md`**. By the rubric the reviewer made no plan edits, so the final plan state is exactly the state it approved. An `APPROVE` turn may still raise minor/nit findings: record unchanged ones as `REJECTED` or `DEFERRED` to stop; if addressing one changes the plan, send another reviewer turn. Also stop and escalate if the cap is hit, or if a `REVISE` design disagreement remains after your written rebuttal and one follow-up reviewer turn. Present both positions neutrally as in the review loop below.

## The review loop

Flows 1 and 2; flow 3 replaces this loop with its own cycle above. Up to **6 review calls** total (flow 2's draft call doesn't count). Typical convergence is 2–3 rounds; the cap is a backstop, not a target.

Each round, send the reviewer a prompt shaped like:

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

Then you address the round:

1. **Verify before accepting.** Check the reviewer's factual claims against the code — a confident-sounding wrong finding rewrites a correct plan.
2. Fix blockers and majors in the plan; take minors/nits at your judgment.
3. A finding you disagree with: reject with a written rationale — never silently drop it.
4. Append the round to the review log: verdict, findings, and per-finding disposition (`ACCEPTED — <edit made>` / `REJECTED — <why>`).
5. Re-review with the updated plan and an updated history digest.

**Stop when:** the reviewer says `VERDICT: APPROVE`, or the cap is hit. Under the verdict rubric, approval means no blocker or major findings remain; take any accompanying minor or nit findings at your judgment and record their dispositions.

**Escalate to the user instead of looping** when the cap is hit without approval, or the reviewer re-raises a rejected finding a second time with a genuinely new argument. Present both positions, remaining findings, or persistent verdict inconsistency neutrally.

## Wrap-up

Report to the user: plan doc path, reviewer model used, rounds used, final verdict, any material capability asymmetry in a flow-3 pairing, and any rejected or deferred findings, reverted reviewer edits, or open disagreements. Approval of the plan is not approval to implement — implementation is a separate decision for the user.

---
name: skill-review-with-agent
description: Have a second agent (Codex or Claude, called via agents-cli) adversarially review a skill — its SKILL.md and supporting files — either reporting findings for you to fix (review loop) or fixing them directly in alternating turns. The reviewer gathers its own review criteria from the skill-authoring skills and docs available to it, rather than being handed a rubric. Use when the user explicitly asks a second agent or second model to review a skill, e.g. "have codex review this skill", "get claude to review and fix my new skill". Do not auto-trigger for ordinary skill creation or editing — skill-creator owns those, and triggering-description quality is measured with skill-creator's evals, not review. For a plan/design doc use plan-with-agent; for code changes use review-with-agent.
---

# Skill Review with Agent

The skill-doc sibling of `plan-with-agent` and `review-with-agent`: this one hardens a skill. A skill is a prompt executed repeatedly by fresh-context agents — on this machine by both Claude Code and Codex — so a cross-vendor reviewer reading it cold is not just a critic but a stand-in for a real consumer: where it misreads the skill, a runtime agent will too.

The reviewer is a second frontier model called via `agents-cli`. The one hard exclusion is self-review: never the exact model this session is running. Each call is fresh-context and one-shot, so every prompt must be fully self-contained.

Unlike its siblings, this skill hands the reviewer no rubric. The prompt tells it to gather its own criteria — the skill-authoring skills and docs available to it, and whatever the target skill delegates to — so findings reflect real conventions rather than a stale checklist embedded here.

## Ground rules

- A saved skill is live behavior. Before starting, confirm the target skill's directory is git-clean (`git status` on it); if not, ask the user how to proceed. Reviewer edits in flow 3 are then verifiable with `git diff` and revertible with git.
- Flow 1 reviewer calls are read-only: the prompt must say so.
- Flow 3 reviewer calls may write exactly two things: files inside the target skill's directory, and appends to the review log. Anything else the reviewer wants changed (cross-referenced docs, sibling skills) it must raise as a finding.
- Don't commit or push unless the user asked.
- Triggering quality of the `description` is out of scope — it's an empirical question owned by skill-creator's evals. Tell the reviewer to skip it unless plainly broken.

## Step 0 — Ground

Minimal: pin the skill's absolute directory path, read its SKILL.md yourself so you can verify findings, note in one line what the skill is for, and confirm git-clean as above.

## Choose a flow

- **Flow 1 — review loop** (default): the reviewer reviews and reports findings; you verify, fix, and re-review until approve or the cap.
- **Flow 3 — alternating review-and-fix** (explicit opt-in only — never auto-select): the reviewer fixes issues directly in the skill's files each round; you verify its edits with `git diff`, fix what remains, and hand it back. Run it only when the user asks for the reviewer to fix/edit the skill directly.

## Choose the reviewer

Never self-review; honor an explicit user choice of vendor/model/effort subject to that exclusion. Defaults:

- **Flow 1**: a cross-vendor reviewer one capability tier stronger when available; otherwise the strongest cross-vendor peer.
- **Flow 3**: a cross-vendor **peer-tier** reviewer — alternating direct edits only cross-check when both agents can catch each other's mistakes.

Read `~/skills/plan-with-agent/references/model-selection.md` for the current roster and effort mapping. Keep the same reviewer for follow-up rounds at lower effort.

## Invoking the reviewer

Follow `~/skills/plan-with-agent/references/invoking-agents-cli.md` for the command templates (generic calls only — there is no native review surface for skills), required flags, and retry/failure rules. Keep the review log in a temp dir (`mktemp -d`); it's ephemeral unless the user wants it persisted.

## Flow 1 — the review loop

Up to **6 review calls**; typical convergence is 1–2 rounds — the cap is a backstop, not a target. Each round, send:

```
You are reviewing a skill — an instruction document executed by fresh-context
AI coding agents (both Claude Code and Codex). Reviewing only — treat the
repo and all files as read-only; do not create or modify anything.

Skill under review: <absolute path to the skill's directory>
Read all of its files (SKILL.md plus any references/, scripts/, agents/).

Gather your own review criteria first: use the skill-authoring skills and
docs available to you (e.g. skill-creator, ~/.claude/docs/authoring-skills.md),
and read any skills or docs the target skill delegates to, so findings
reflect real conventions and real composition seams. Skip findings about the
description's triggering quality unless it is plainly broken — triggering is
tested empirically with evals, not review.

Prior rounds (do not re-raise items marked REJECTED unless you have a
genuinely new argument): <digest of prior findings + dispositions, or "none">

Review the skill and find any issues. Output format — first line exactly:
VERDICT: APPROVE | REVISE
Then each finding on its own bullet:
[blocker|major|minor|nit] <title> — <what & where> — <suggested fix>
If there are no findings, write "No findings."

Verdict rubric:
- APPROVE if and only if no blocker or major findings remain (minor and nit
  findings may accompany APPROVE).
- REVISE if one or more blocker or major findings remain.
```

Then address the round: verify each finding against the actual conventions and delegated-to docs before accepting (a confident wrong finding rewrites a correct skill); fix blockers and majors; take minors/nits at your judgment; reject with a written rationale rather than silently dropping. Log verdict, findings, and per-finding disposition (`ACCEPTED — <edit>` / `REJECTED — <why>` / `DEFERRED — <why>`) as a `## Round N` section in the review log, reviewer model in the header. Re-review with an updated digest.

**Stop when** the reviewer says `VERDICT: APPROVE`, or the cap is hit. **Escalate to the user** instead of looping when the cap is hit without approval or the reviewer re-raises a rejected finding with a genuinely new argument — present both positions neutrally.

## Flow 3 — alternating review-and-fix

Up to **4 reviewer calls**. The reviewer fixes factual, mechanical, and clarity issues in place, and must raise design-level disagreements (the skill's scope, flow structure, delegation choices) as findings without rewriting them. Each cycle:

1. Snapshot the review log; the skill directory is covered by git.
2. Invoke the reviewer with the prompt below.
3. Verify the review log changed append-only (exactly one new `## Round N` section). If the call is unusable under the shared retry rules, restore the log and `git checkout` the skill directory before retrying — never retry atop a partial mutation.
4. `git diff` the skill directory and verify every edit; revert wrong ones and record `REVERTED — <why>` in your turn.
5. Address RAISED findings: fix, or `REJECTED — <why>` / `DEFERRED — <why>`; never silently drop one.
6. Append a `### Session turn` subsection to the round: per-edit and per-finding dispositions plus your own changes. If not converged, send the next turn with an updated digest.

```
You are reviewing AND fixing a skill — an instruction document executed by
fresh-context AI coding agents (both Claude Code and Codex). Treat the repo
and all files as read-only, with exactly two exceptions you may edit:
- the skill's directory: <absolute path>
- the review log (append-only): <absolute path to review.md>

Read all of the skill's files (SKILL.md plus any references/, scripts/,
agents/).

Gather your own review criteria first: use the skill-authoring skills and
docs available to you (e.g. skill-creator, ~/.claude/docs/authoring-skills.md),
and read any skills or docs the target skill delegates to, so your edits
reflect real conventions and real composition seams. Skip findings about the
description's triggering quality unless it is plainly broken — triggering is
tested empirically with evals, not review.

Prior rounds (do not re-raise or re-apply items marked REJECTED or REVERTED
unless you have a genuinely new argument): <digest, or "none">

Review the skill, find any issues, and fix them:
- Factual, mechanical, and clarity issues (wrong paths, broken delegation
  seams, ambiguous instructions a cold agent would misread): fix directly in
  the skill's files.
- Design-level disagreements (scope, flow structure, delegation choices):
  do NOT rewrite — record the finding as RAISED and leave the text alone.
- Append exactly one "## Round N — <your model> (reviewer turn)" section to
  the review log: each finding as [blocker|major|minor|nit] <title> — <what
  & where> — then FIXED — <edit made> or RAISED — <suggested resolution>.
  Append the section even with no findings — state your verdict and "No
  findings."

Output format — first line exactly:
VERDICT: APPROVE | REVISED | REVISE
- APPROVE iff you made no edits to the skill and no blocker or major
  findings remain (the required review-log append doesn't count as an edit).
- REVISED if you edited the skill and no blocker or major finding is left
  unfixed.
- REVISE if blocker or major findings remain RAISED.
Then bullet-summarize your edits and RAISED findings.
```

**Stop when** a turn returns `VERDICT: APPROVE` and your handling of it makes no further change to the skill — the final state is exactly what was approved. Also stop and escalate if the cap is hit or a design disagreement survives your written rebuttal plus one follow-up turn.

## Wrap-up

Report: skill path, reviewer model, rounds used, final verdict, a summary of what changed in the skill, and any rejected/deferred findings, reverted edits, or open disagreements. Remind the user the edited skill is live and suggest committing it; committing stays with them.

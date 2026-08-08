---
name: skill-review-with-agent
description: Have a second agent (Codex or Claude) adversarially review a skill in a live herdr pane — its SKILL.md and supporting files — either reporting findings for you to fix (review loop) or fixing them directly in alternating turns. The reviewer gathers its own review criteria from the skill-authoring skills and docs available to it, rather than being handed a rubric. Use when the user explicitly asks a second agent or second model to review a skill, e.g. "have codex review this skill", "get claude to review and fix my new skill". Do not auto-trigger for ordinary skill creation or editing — skill-creator owns those, and triggering-description quality is measured with skill-creator's evals, not review. For a plan/design doc use plan-with-agent; for code changes use review-with-agent.
---

# Skill Review with Agent

The skill-doc sibling of `plan-with-agent` and `review-with-agent`: this one hardens a skill. A skill is a prompt executed repeatedly by fresh-context agents — on this machine by both Claude Code and Codex — so a cross-vendor reviewer reading it cold is not just a critic but a stand-in for a real consumer: where it misreads the skill, a runtime agent will too.

The reviewer is a second frontier model running in a live pane beside you. **Read `~/skills/review-with-agent/references/herdr-review-loop.md` for the mechanics** — spawning, placement, waiting, reading, and the next-round prompt — shared with `review-with-agent` so the two cannot drift. The one hard exclusion is self-review: never the exact model this session is running.

Because the reviewer keeps its context between rounds, a follow-up turn is a short delta rather than a restated packet. That matters most in flow 3, where the alternation would otherwise re-send the whole candidate state every turn.

Unlike its siblings, this skill hands the reviewer no rubric. The prompt tells it to gather its own criteria — the skill-authoring skills and docs available to it, and whatever the target skill delegates to — so findings reflect real conventions rather than a stale checklist embedded here.

## Ground rules

- A saved skill is live behavior, so the reviewer never edits the live skill: flow 1 turns are read-only, and flow 3 turns edit a disposable candidate copy in a temp workspace. The live skill changes only when you (the session agent) edit it — flow 1 fixes after verifying findings, or flow 3's single apply-after-approval step. No git state is required and the skill need not be in a repo.
- Flow 3 reviewer turns may write exactly two things: files inside the candidate copy, and appends to the review log — both inside the temp workspace. Anything else the reviewer wants changed (cross-referenced docs, sibling skills) it must raise as a finding.
- Don't commit or push unless the user asked.
- Triggering quality of the `description` is out of scope — it's an empirical question owned by skill-creator's evals. Tell the reviewer to skip it unless plainly broken.

## Step 0 — Ground

Minimal: pin the skill's absolute directory path, read its SKILL.md yourself so you can verify findings, and note in one line what the skill is for.

## Choose a flow

- **Flow 1 — review loop** (default): the reviewer reviews and reports findings; you verify, fix, and re-review until approve or the cap.
- **Flow 3 — alternating review-and-fix** (explicit opt-in only — never auto-select): the reviewer fixes issues directly in a candidate copy of the skill each round; you verify its edits, fix what remains, and hand it back; the verified result is applied to the live skill once, after final approval. Run it only when the user asks for the reviewer to fix/edit the skill directly.

## Choose the reviewer

Never self-review; honor an explicit user choice of vendor/model/effort subject to that exclusion. If the user requests the exact model running this session, explain the conflict and use a different model only with their agreement. Defaults:

- **Flow 1**: a cross-vendor reviewer one capability tier stronger when available; otherwise the strongest cross-vendor peer.
- **Flow 3**: a cross-vendor **peer-tier** reviewer — alternating direct edits only cross-check when both agents can catch each other's mistakes.

Read `~/skills/plan-with-agent/references/model-selection.md` for the current roster and effort mapping. Keep the same reviewer for follow-up rounds at lower effort.

## Invoking the reviewer

Spawn per the shared herdr reference. Work out of a temp workspace (`mktemp -d`): it holds the review log — which must be exactly `<workspace>/review.md`, the one path the helper's round snapshot/restore covers — and in flow 3 also the `original/` and `candidate/` copies of the skill. Everything in it is ephemeral unless the user wants the review log persisted. Spawn the reviewer with the workspace as its cwd, so `candidate/` and the log are the paths nearest to hand.

For flow 3, use `scripts/candidate_workspace.py` for every copy, snapshot, comparison, restore, and apply operation; run it with the configured Python interpreter and use `-h` for its command contract. Do not reimplement those mechanics with `cp`, `diff`, or Git. The helper compares path presence, entry type, permission bits, and contents; safety-checks every entry before filtering junk (`.DS_Store`, `__pycache__`, `.pytest_cache`) from comparisons and copies; normalizes that junk out of `candidate/` before each round snapshot; restores both writable artifacts exactly; detects live drift; stages the replacement beside the live skill; and verifies or rolls it back. It rejects symlinks and special files because they can escape the disposable workspace; if it rejects the live skill at setup, stop and ask the user how to handle that skill.

## Flow 1 — the review loop

Up to **6 review rounds**; typical convergence is 1–2 — the cap is a backstop, not a target. Spawn the reviewer with the prompt below; each later round is a short follow-up prompt to the same pane, so the "prior rounds" block shrinks to what changed since its last turn rather than restating the whole history.

```
You are reviewing a skill — an instruction document executed by fresh-context
AI coding agents (both Claude Code and Codex). Reviewing only — treat every
file as read-only; do not create or modify anything, including the skill
you are reviewing.

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

**Stop when** the reviewer says `VERDICT: APPROVE` and addressing that round makes no further change to the skill — the final state is exactly what was approved. If any accepted finding changes the skill, re-review it even when the preceding verdict was `APPROVE`. Also stop at the cap. **Escalate to the user** instead of looping when the cap is hit without approval or the reviewer re-raises a rejected finding with a genuinely new argument — present both positions neutrally.

## Flow 3 — alternating review-and-fix

Up to **4 reviewer turns**. The reviewer fixes factual, mechanical, and clarity issues in place, and must raise design-level disagreements (the skill's scope, flow structure, delegation choices) as findings without rewriting them.

**Setup:** create the temp workspace, then run `<python> <absolute path to candidate_workspace.py> setup <live skill dir> <workspace>`. The helper creates `original/` (the pristine baseline, never modified) and `candidate/` (the only copy anyone edits). All rounds — reviewer edits and your fixes alike — happen in `candidate/`; the live skill is untouched until the apply step.

Each cycle:

1. Run the helper's `round-snapshot <workspace> N` command to remove ignored junk from `candidate/`, then snapshot that normalized candidate and the review log exactly.
2. Prompt the reviewer — spawn it with the prompt below on the first turn, then `herdr agent prompt --wait` for later ones. It edits `candidate/` only.
3. Verify the review log changed append-only (exactly one new `## Round N` section). If the turn is unusable, run `round-restore <workspace> N` before re-prompting — never retry atop a partial mutation. A live reviewer remembers its rejected turn, so say plainly that you restored the candidate and what to do differently, or it will assume its edits are still there.
4. Run `round-diff <workspace> N` and verify every reported path, type, mode, and content change; inspect ordinary file diffs as needed, revert wrong changes in `candidate/`, and record `REVERTED — <why>` in your turn. If `round-diff` rejects the candidate (the reviewer introduced a symlink or special file), treat the turn as unusable like step 3: `round-restore` and re-prompt — don't ask the user.
5. Address RAISED findings by editing `candidate/`, or `REJECTED — <why>` / `DEFERRED — <why>`; never silently drop one.
6. Append a `### Session turn` subsection to the round: per-edit and per-finding dispositions plus your own changes. If not converged, send the next turn with an updated digest.

**Apply after approval:** run `<python> <absolute path to candidate_workspace.py> apply <workspace> <pinned live skill dir>`. The helper refuses to apply if the live skill drifted, uses a same-filesystem staged replacement, verifies the installed candidate and unchanged backup, and rolls back on failure. If it reports live drift or cannot complete or roll back safely, stop and reconcile with the user; never improvise a partial copy. Report the helper's pending and apply output.

```
You are reviewing AND fixing a skill — an instruction document executed by
fresh-context AI coding agents (both Claude Code and Codex). Treat the repo
and all files as read-only, with exactly two exceptions you may edit:
- the candidate copy of the skill: <absolute path to candidate/>
  (a disposable working copy of <live skill path>; make every fix in the
  copy, never in the live skill)
- the review log (append-only): <absolute path to review.md>

Read all of the candidate's files (SKILL.md plus any references/, scripts/,
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
  the candidate's files.
- Design-level disagreements (scope, flow structure, delegation choices):
  do NOT rewrite — record the finding as RAISED and leave the text alone.
- Append exactly one "## Round N — <your model> (reviewer turn)" section to
  the review log: each finding as [blocker|major|minor|nit] <title> — <what
  & where> — then FIXED — <edit made> or RAISED — <suggested resolution>.
  Append the section even with no findings — state your verdict and "No
  findings."

Output format — first line exactly:
VERDICT: APPROVE | REVISED | REVISE
- APPROVE iff you made no edits to the candidate and no blocker or major
  findings remain (the required review-log append doesn't count as an edit).
- REVISED if you edited the candidate and no blocker or major finding is
  left unfixed.
- REVISE if blocker or major findings remain RAISED.
Then bullet-summarize your edits and RAISED findings.
```

**Stop when** a turn returns `VERDICT: APPROVE` and your handling of it makes no further change to `candidate/` — the state you apply is then exactly the state that was approved. Also stop and escalate if the cap is hit or a design disagreement survives your written rebuttal plus one follow-up turn; on escalation, don't apply — run `pending-diff <workspace>` and show the user the pending changes to decide.

## Wrap-up

Report: skill path, reviewer model, rounds used, final verdict, a summary of what changed in the live skill, and any rejected/deferred findings, reverted edits, or open disagreements. Remind the user the edited skill is live as saved; if it's git-tracked, suggest committing — committing stays with them.

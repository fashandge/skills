---
name: review-with-agent
description: Have a second agent (Codex or Claude, called via agents-cli) adversarially review code changes — a working tree, branch, or commit range — then address its findings and repeat the review-address cycle until approval or the round cap. Use when the user explicitly asks for a second agent or second model to review code, e.g. "have codex review this", "get claude to review my diff", "second-model review of these changes", "review this with codex and fix what it finds". Do not auto-trigger for ordinary code-review requests that don't ask for a second agent — the harness's own code-review skill covers those. For reviewing a plan/design doc instead of code, use plan-with-agent.
---

# Review with Agent

The code-change sibling of `plan-with-agent`: that skill hardens a plan doc through adversarial review; this one hardens a change set. Any harness and session model can drive it. The reviewer is a second frontier model called via `agents-cli` — Codex (GPT) or Claude — and the one hard exclusion is self-review: the reviewer must never be the exact model this session is running (same vendor at a higher tier is fine).

The output is a change set that survived adversarial review by a second frontier model, plus a review log of findings and dispositions. Each `agents-cli` call is fresh-context and one-shot, so every prompt must be fully self-contained.

## Ground rules

- Production is read-only to the reviewer: repository files and production data must not change. Give each round its own temp scratch directory; the reviewer may create scripts and other disposable files there only, and must run write-capable validation against scratch copies rather than production data. `agents-cli` runs auto-approved, so state this boundary in every prompt. Rely on the reviewer workflow and this explicit boundary as in a normal review session; do not reconstruct Git state merely to detect writes. If strict isolation is required, use a disposable worktree/clone or filesystem sandbox instead.
- The session agent owns the authoritative baseline and post-fix test runs. The reviewer supplements that evidence with targeted independent validation when useful; it does not rerun the full suite merely to duplicate current results.
- You (the session agent) do edit code — addressing findings is the point — but stay inside the change's scope: fix findings, don't grow the feature.
- Don't commit or push unless the user asked. If the changes under review are already committed, land fixes as new commits rather than rewriting history, unless the user's workflow says otherwise.

## Step 0 — Scope the change set

Pin down exactly what is under review and why it exists. Do not require the requester to make a preliminary commit.

1. **Identify the stable baseline and editable candidate**:
   - Working-tree change: baseline is `HEAD`; candidate is the current working tree.
   - Checked-out branch or PR: baseline is its merge-base with the base branch; candidate is the current working tree on the change branch.
   - Explicit commit range: baseline is the range's base; before fixing anything, verify the worktree represents the range tip. Use an existing worktree at the tip, or ask before switching branches or creating one.
   - Staged-only review: use the index as the candidate for the first pass. If the user also wants fixes, ask whether to update the index or broaden subsequent rounds to the working tree; never stage changes implicitly.
2. **Verify state alignment**: run tests and make fixes only in the worktree that represents the reviewed candidate. If unrelated dirty changes make the candidate ambiguous, ask the user to narrow the scope or provide a clean worktree; a commit is optional, not required.
3. **Collect relevant context**: identify requester-supplied or clearly relevant design docs, plan docs, issues/PRs, API contracts, schemas, migration notes, and other sources that define intended behavior or constraints. Include only material context, give absolute paths or URLs, label each source `AUTHORITATIVE` or `BACKGROUND`, and flag anything potentially stale. Plans explain intent; they are not proof that the implementation is correct. Also identify ignored or external production-data paths the reviewer could plausibly touch (such as databases or data directories) and any credential sources genuinely required by an authorized validation command. Name paths or sources, never credential values. Credentials may be consumed only through the existing application or credential provider; neither agent may inspect, display, copy, log, or place their values in prompts or scratch files. The reviewer may run authenticated validation only when it is read-only against an external system. If write-capable external validation is necessary, the session agent must use a non-production target or obtain the user's explicit authorization, run it, and give the reviewer the result. Record `none` independently for material context, production-data paths, and credential sources; ask the requester only when an omission would materially change the review or its safety.
4. **Write an intent brief**: one tight paragraph on what the change is supposed to do, key file paths, constraints/non-goals. A reviewer without the intent reviews style instead of correctness, and can't flag scope creep.
5. **Know the tests pass before round 1.** Don't spend a review round on code you already know is broken. If the relevant tests were already run against the current candidate state (e.g. just before this skill was invoked), don't rerun them; run them only if they haven't been, or the code has changed since. Record the commands and results for the review context packet.

## Choose the reviewer

Same principles as `plan-with-agent`, applied in order: never self-review; honor an explicit user choice of vendor/model/effort (unless it violates self-review); default to a cross-vendor, at-least-peer reviewer. Read `~/skills/plan-with-agent/references/model-selection.md` for the current roster, default session→reviewer mapping, and effort mapping — the first review round of a change set is a deep pass; follow-up rounds verify a shrinking delta.

## Invoking the reviewer

Follow `~/skills/plan-with-agent/references/invoking-agents-cli.md` for the command templates (generic and native), required flags, flag exclusions, which slash commands are off-limits, and the retry/failure rules — those mechanics live only there. This skill owns just the decision rule:

- **Prefer the reviewer's native code-review surface** whenever it naturally represents the candidate: Codex via `--codex-review` for the current working-tree changes, Claude via `--claude-review-command code-review` for the current working diff or `--claude-review-command review` for a GitHub PR.
- **Generic fallback**: use the ordinary one-shot prompt when the native surface is unavailable or cannot represent the candidate, such as staged-only changes, arbitrary commit ranges, or local branch comparisons. State the exact Git baseline and candidate; do not silently widen or narrow scope.

Every call is one-shot. Include the intent brief, labeled context sources, repo and scratch paths, exact review scope, and prior-round history in its context packet. Before calling a native reviewer, verify that its selected scope is the intended candidate; otherwise use the generic fallback.

## Artifacts

Work out of a temp dir (`mktemp -d`), not the repo:

- `round-N-review.md` — the captured native or fallback reviewer output, preserved verbatim.
- `round-N-scratch/` — the only location the reviewer may modify; start empty each round so validation artifacts cannot contaminate later reviews.
- `review.md` — the running log: one `## Round N` section per review (reviewer model in the header) with verdict, findings, and your per-finding disposition.

The log is ephemeral by default. If the user wants a record, persist `review.md` to `docs/reviews/YYYY-MM-DD_<slug>.md`; a digest of it also makes a good PR-description section.

## The review loop

Up to **6 review calls** total. Typical convergence is 2–3 rounds; the cap is a backstop, not a target.

### Review context packet

For every call, send the change-specific context the reviewer cannot infer:

```
Treat repository files and all production data as read-only. Production-data
paths: <named ignored/external paths, or "none identified">. Open them only in
explicitly read-only mode, or work on scratch copies. Credential sources
required by authorized validation: <names/paths, or "none">. Credentials may
be consumed only through the existing application or credential provider. Do
not inspect, display, copy, log, or place credential values in prompts, review
output, or scratch files. Do not run authenticated validation that can mutate
an external system; report it as unvalidated so the session agent can use a
non-production target or seek authorization and run it. You may create or
modify disposable scripts and other files only under <absolute path to
round-N-scratch>. Do not write anywhere else. Run any write-capable validation
only against scratch copies, never production data. Do not post comments,
submit reviews, push, commit, or make any other external change.

Intent of the change: <brief>
Relevant context (absolute paths or URLs, why each matters, and whether it is
AUTHORITATIVE or BACKGROUND; flag potentially stale sources, or write "none"):
- <AUTHORITATIVE|BACKGROUND> <source> — <relevance and freshness note>
Repo: <root> — read any file you need for context.
Review scope: <exact baseline and candidate, e.g. "merge-base abc123 to the
current working tree on feature/foo">
Prior rounds (do not re-raise items marked REJECTED or DEFERRED unless you
have a genuinely new argument): <digest of prior findings + dispositions, or
"none">
Validation already performed on this candidate: <commands and results>

Perform targeted validation when it would materially increase confidence in
a finding. Prefer focused existing tests and read-only commands; use the
designated scratch directory for disposable scripts, redirected caches, or
write-capable experiments against scratch copies. Do not rerun the full test
suite merely to duplicate the evidence above. Report the validation performed
and its result, or state when a finding could not be validated.
```

For a native review call, let the reviewer's built-in workflow supply the methodology. Append only:

```
Use the native code-review workflow. Review only the scope described above.
Treat plans and design docs as evidence of intent, not proof of correctness.
Return concrete findings with severity and file/line references when possible;
explicitly say when there are no findings.
```

Native reviewers need not emit this skill's exact verdict syntax. Save their output verbatim, then normalize it in `review.md`:

- Record each original native severity alongside its normalized value: `P0/P1/P2/P3` and `critical/high/medium/low` map in order to `blocker/major/minor/nit`. If a finding has no severity, classify it by impact and record that the classification is yours.
- Compute the normalized verdict from the current findings plus every unresolved prior finding in `review.md`: it is `REVISE` while any blocker or major remains, and `APPROVE` otherwise. A native statement that there are no new findings does not erase an unresolved earlier blocker or major.
- Do not retry an otherwise coherent native review merely because it omitted `VERDICT:`. Retry/failure rules for native and generic calls differ as described in the shared invocation reference.

### Generic fallback prompt

When no native review surface can represent the candidate exactly, send the review context packet followed by this fallback instruction:

```
Review for: correctness bugs (logic, edge cases, error handling,
concurrency), regressions in untouched-but-affected behavior, misuse of
this codebase's actual APIs and conventions, missing or inadequate tests,
security issues, and significant simplification opportunities. Judge the
change against its stated intent — flag scope creep and unintended changes.
Verify assumptions from plans and design docs against the code, and call out
stale or conflicting context.

Output format — first line exactly:
VERDICT: APPROVE | REVISE
Second line exactly:
VALIDATION: <commands/checks and results, or "not performed — reason">
Then write `FINDINGS:` followed by each finding on its own bullet:
[blocker|major|minor|nit] <title> — <file:line & what's wrong> — <suggested fix>
If there are no findings, write `FINDINGS: none`.

Verdict rubric:
- APPROVE if and only if no blocker or major findings remain. Minor and nit
  findings may accompany APPROVE.
- REVISE if one or more blocker or major findings remain.
```

Then address the round (native and fallback rounds alike):

1. **Reject stale rounds before using their findings.** If there is a concrete reason to believe the candidate changed while the reviewer was running (for example, the user edited the working tree), treat the output as unusable: do not address or add its findings to `review.md` or the prior-round digest, exclude it from verdict computation, and do not count the call against the cap. Re-establish the exact scope, refresh any affected context, rerun the relevant baseline tests, and then rerun the same round against the current candidate.
2. **Verify before accepting.** Read the code path or reproduce the failure — a confident-sounding wrong finding can wreck a correct change.
3. Fix blockers and majors; take minors/nits at your judgment.
4. **Re-run the relevant tests** after every code change.
5. Record every finding in `review.md` as `FIXED — <change made>`, `DEFERRED — <valid minor/nit intentionally unchanged, with reason>`, or `REJECTED — <why the finding is incorrect>`; never silently drop one. Do not defer a blocker or major inside the approval loop. If one will remain unfixed, escalate to the user; explicit risk acceptance becomes `ACCEPTED_RISK — <reason>` and immediately ends the loop with the non-approval outcome `STOPPED_WITH_ACCEPTED_RISK`.
6. If any code changed after the reviewed candidate — including a fix for a minor/nit that accompanied `APPROVE` — run another review round with the updated history digest.

**Stop when:** the normalized verdict is `APPROVE` and no code changes follow the reviewed candidate; the user explicitly accepts an unresolved blocker/major risk, producing `STOPPED_WITH_ACCEPTED_RISK` rather than approval; or the cap is hit. Approval means no blocker or major findings remain; record accompanying minors/nits as `DEFERRED` or `REJECTED` if they do not trigger another round.

**Escalate to the user instead of looping** when a blocker/major is valid but will not be fixed, the cap is hit without approval, or the reviewer re-raises a rejected finding a second time with a genuinely new argument. Present both positions neutrally. User acceptance of an unresolved blocker/major stops the loop without approval; declining that risk means fix it or leave the outcome unapproved.

## Wrap-up

Report to the user: what changed in response to the review (files + nature of fixes), reviewer model, rounds used, final outcome (`APPROVE`, `STOPPED_WITH_ACCEPTED_RISK`, or cap reached), test status, and any accepted risks, rejected findings, or open disagreements. Review approval is not a merge decision — committing, pushing, and merging stay with the user.

---
name: plan-with-agent
description: Co-write and adversarially review a plan/design doc with a second agent (Codex or Claude, called via agents-cli), using either a draft-review loop or independent dual drafts followed by synthesis. Use when the user explicitly asks to plan with Codex or Claude, requests a second-model opinion or review of a plan, asks for independent co-drafting, or explicitly requests a two-agent audit that produces a remediation plan. Do not auto-trigger for ordinary planning, diagnosis, code review, or audits that do not request a second agent.
---

# Plan with Agent

Any harness and session model can drive this skill. The reviewer is a second frontier model called via `agents-cli` — Codex (GPT) or Claude — chosen by the rules below. The one hard exclusion is self-review: the reviewer must never be the same model the session is running (same vendor at a higher tier is fine).

The output is a plan doc that survived adversarial review by a second frontier model. Each `agents-cli` call is fresh-context and one-shot, so every prompt must be fully self-contained.

## Ground rules (plan-mode discipline)

Planning is read-only with respect to the world:

- Never modify existing source code or production data (databases, data files).
- Allowed writes: the plan doc, the review log, the counterpart draft doc (flow 2), and ad-hoc scratch scripts for probing/debugging (put them in a temp dir, not the repo). Probes read production data; if a probe must write, run it against a scratch copy (e.g. a dev DB).
- `agents-cli` runs the reviewer auto-approved, so the prompt is the only guardrail: **every reviewer prompt must state** "Treat the repo and all data as read-only. Do not create or modify any files" — except, in flow 2's draft call, the single output file it is told to write.

## Step 0 — Ground the requirement

Reviews are wasted on a plan built from wrong assumptions. Before drafting: explore the relevant code, run read-only probes if facts are uncertain, and clarify genuinely ambiguous requirements with the user. Distill the result into a **requirement brief** (one tight paragraph + key file paths + constraints/non-goals) — you'll paste it into every reviewer prompt.

## Choose a flow

- **Flow 1 — draft → review loop** (default): you write the plan, the reviewer reviews, you address, repeat.
- **Flow 2 — dual independent drafts**: you and the counterpart agent each write a plan from the same requirement brief *without seeing each other's*, you synthesize one plan, then enter the flow-1 review loop. Use when the solution space is wide (multiple viable architectures), the requirement is high-stakes or ambiguous after grounding, or the user asks for it. Also use it for *discovery-shaped* tasks — auditing an existing system to find all bugs/issues and propose fixes — where the value is coverage: an agent that reads the other's findings first anchors on them and confirms instead of hunting, so two fresh-minded independent sweeps catch more, and the synthesis step doubles as cross-checking each finding. Independent drafting only pays when there is real design freedom or real discovery to do; for a well-constrained requirement it just adds a synthesis step.

The user can name a flow explicitly; that wins.

## Choose the reviewer

Apply these principles in order:

1. **Never self-review.** Do not use the exact model running this session. If the session's exact model is unknown, choose the other vendor.
2. **Honor an explicit user choice** of vendor, model, or effort unless it violates the self-review exclusion. If the user requests the current model, explain the conflict and use a different model only with their agreement.
3. **Default to cross-vendor, at-least-peer review.** Use the other model family at the same tier or higher. A stronger same-vendor model is acceptable for unusually hard requirements when diversity matters less than raw capability.

Read [references/model-selection.md](references/model-selection.md) before selecting a concrete model and effort. It owns the dated roster and effort mapping so volatile model names do not dominate this workflow. When the session model is below frontier tier, deliberately choose an above-peer reviewer, then verify its findings against the code before accepting them.

For flow 2's independent draft, choose a peer-tier cross-vendor counterpart. Drafting wants competitive alternatives; use extra intelligence in the subsequent review path rather than letting a stronger counterpart dominate synthesis.

## Invoking the reviewer

Pass the prompt through a quoted stdin heredoc (avoids quoting, ARG_MAX, and persistent prompt files); the answer arrives on stdout — capture it to a file, then read the file. Run long calls in the background and read the output file when it exits; don't kill quiet runs. Full flag list: `agents-cli -h`.

**Codex reviewer:**

```bash
REVIEWER_MODEL="selected-codex-model"
REVIEWER_EFFORT="selected-effort"
agents-cli -a codex -m "$REVIEWER_MODEL" --codex-reasoning "$REVIEWER_EFFORT" \
  --codex-working-dir <repo-root> --timeout 3600 \
  > <round-output-file> <<'PROMPT_EOF'
<self-contained prompt>
PROMPT_EOF
```

**Claude reviewer:**

```bash
REVIEWER_MODEL="selected-claude-model"
REVIEWER_EFFORT="selected-effort"
agents-cli -a claude -m "$REVIEWER_MODEL" --claude-effort "$REVIEWER_EFFORT" --no-mcp \
  --timeout 3600 > <round-output-file> <<'PROMPT_EOF'
<self-contained prompt>
PROMPT_EOF
```

- Always pass `--timeout 3600`: the default is 1200s, which high/xhigh reviews of a substantial plan regularly exceed.
- Claude only: always pass `--no-mcp` (unattended `claude -p` runs can hang on plugin MCP teardown, and reviews need no MCP tools), and note there is no working-dir flag — run the command from the repo root so the paths in the prompt resolve.
- No session resume: include the requirement brief, paths, constraints, and review history in every call.
- Transient or malformed call: if a call times out, exits nonzero for a transient provider reason, returns empty output, lacks the `VERDICT:` first line, or returns a verdict inconsistent with the severity rubric below, retry it once. A call that produced no usable output doesn't count against the review-call cap.
- Persistent failure: do not repeat an invalid model, missing binary, authentication failure, or twice-malformed result with the same configuration. If the user did not name an exact model, select the next eligible reviewer from the roster; if they did, report the failure and ask before substituting another model.

## Artifacts

Each planning effort gets its own subfolder `docs/plans/YYYY-MM-DD_<slug>/` (create it if missing) — an effort produces up to three docs, and one folder per effort keeps `docs/plans/` scannable:

- `plan.md` — goal, current state, design, alternatives considered, step-by-step implementation, testing/verification, risks & rollback.
- `review.md` — one `## Round N` section per review: the reviewer's verdict + findings, then your disposition per finding. Name the reviewer model in each round header.
- `codex-draft.md` / `claude-draft.md` (flow 2 only) — the counterpart's independent draft, named by agent, kept as a record of the road not taken.

## Flow 2 — independent drafts, then synthesize

1. Write your own plan draft (do not read the counterpart's first).
2. In parallel, ask the counterpart agent to write its plan to the effort folder's draft file — give it the same requirement brief you drafted from, and name that file as the one file it may write.
3. Synthesize: don't merge everything — pick the stronger skeleton, graft the other draft's better ideas, and note real divergences (they're usually the decisions worth surfacing to the user).
4. Enter the review loop below with the synthesized plan.

## The review loop

Up to **6 review calls** total (flow 2's draft call doesn't count). Typical convergence is 2–3 rounds; the cap is a backstop, not a target.

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

Report to the user: plan doc path, reviewer model used, rounds used, final verdict, and any rejected findings or open disagreements. Approval of the plan is not approval to implement — implementation is a separate decision for the user.

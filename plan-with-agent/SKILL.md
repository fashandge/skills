---
name: plan-with-agent
description: Co-write a plan/design doc for a requirement together with a second agent (Codex or Claude, called via agents-cli) — the session agent drafts (or both draft independently and the session agent synthesizes), then the reviewer agent reviews and the drafter addresses feedback in a capped loop until approval. Works from any harness and session model (Claude Code, Codex, opencode, etc., running Claude, GPT, GLM, Grok, muse-spark, ...). Use whenever the user asks to plan with codex or claude, wants a plan doc reviewed by a second model, wants a second-model opinion on a design or implementation plan, or says things like "plan this with codex", "have claude review the plan", "co-draft a plan". Also use it for audit-style requirements — find all the bugs/issues in an existing system and propose fixes — where independent sweeps by two models maximize coverage.
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

Two principles, applied in order:

1. **At-least-peer intelligence.** A weaker reviewer rubber-stamps or nitpicks a stronger model's plan; a stronger reviewer is never wasted. Tier ladder (preserve the principle, not the names, as lineups change):
   - Codex: `gpt-5.6-sol` > `gpt-5.6-terra` > `gpt-5.6-luna`
   - Claude: `claude-fable-5` (Fable) > `claude-opus-4-8` (Opus)
   - Cross-vendor calibration: Fable ≈ sol at high effort; Opus ≈ terra at xhigh.
2. **Cross-vendor by default (unless the user specifies otherwise); never self-review.** Different model families have uncorrelated blind spots, so the default reviewer comes from the other family: Claude sessions get a Codex reviewer, Codex sessions get a Claude reviewer, and everything else (GLM, Grok, muse-spark, …) gets a Claude reviewer. Same vendor at a higher tier (e.g. terra → sol) is a legitimate alternative when the task is genuinely hard and raw intelligence trumps diversity. The reviewer must never be the model this session runs.

Reviewer effort is fixed per model (a named effort from the user still wins):

- `gpt-5.6-terra` — always `xhigh`.
- `gpt-5.6-sol` — `xhigh` for deep passes and genuinely hard requirements, `high` otherwise. Deep passes are where fresh whole-problem thinking pays: flow 2's independent draft and the first review round. Follow-up rounds verify fixes against a shrinking delta — `high` is enough there, and a maxed-out reviewer re-scanning a nearly-converged plan tends to manufacture nitpicks that burn rounds.
- `claude-fable-5` — same rule as sol: `xhigh` for deep passes and genuinely hard requirements, `high` otherwise.
- `claude-opus-4-8` — always `high`.

| This session's model | Default reviewer |
|---|---|
| Fable | `gpt-5.6-sol` |
| Opus | `gpt-5.6-terra` |
| `gpt-5.6-sol` | `claude-fable-5` |
| `gpt-5.6-terra` | `claude-opus-4-8`; hard tasks: `claude-fable-5` |
| `gpt-5.6-luna` | `claude-opus-4-8`; hard tasks: `claude-fable-5` |
| Sonnet / Haiku (Claude below frontier) | `gpt-5.6-terra`; hard tasks: `gpt-5.6-sol` |
| Non-Claude, non-GPT vendors (GLM, Grok, muse-spark, …) | `claude-opus-4-8`; hard tasks: `claude-fable-5` |

When the session model is below frontier tier, the default reviewer is deliberately above-peer — expect the review to catch more legitimate issues, but still verify findings against the code before accepting. A model/effort/vendor the user names always wins.

**Flow 2's independent draft** uses a *peer-tier*, cross-vendor counterpart (Fable ↔ `gpt-5.6-sol`, Opus ↔ `gpt-5.6-terra`; for a below-frontier session model, the nearest frontier tier above it). Drafting wants equals: a counterpart a tier above would dominate the synthesis and collapse it into "take the stronger model's plan", while peers produce genuinely competitive alternatives. The review path is where extra intelligence enters — same tier for routine requirements, higher tier for hard/complex ones, per the matrix above.

## Invoking the reviewer

Prompt via temp file on stdin (avoids quoting/ARG_MAX issues); the answer arrives on stdout — capture it to a file, then read the file. Run long calls in the background and read the output file when it exits; don't kill quiet runs. Full flag list: `agents-cli -h`.

**Codex reviewer:**

```bash
P=$(mktemp); cat >"$P" <<'PROMPT_EOF'
<self-contained prompt>
PROMPT_EOF
agents-cli -a codex -m gpt-5.6-sol --codex-reasoning high \
  --codex-working-dir <repo-root> --timeout 3600 <"$P" > <round-output-file>
```

**Claude reviewer:**

```bash
P=$(mktemp); cat >"$P" <<'PROMPT_EOF'
<self-contained prompt>
PROMPT_EOF
agents-cli -a claude -m claude-fable-5 --claude-effort high --no-mcp \
  --timeout 3600 <"$P" > <round-output-file>
```

- Always pass `--timeout 3600`: the default is 1200s, which high/xhigh reviews of a substantial plan regularly exceed.
- Claude only: always pass `--no-mcp` (unattended `claude -p` runs can hang on plugin MCP teardown, and reviews need no MCP tools), and note there is no working-dir flag — run the command from the repo root so the paths in the prompt resolve.
- No session resume: include the requirement brief, paths, constraints, and review history in every call.
- Failed call: if the call times out, exits nonzero, or a review call's output is empty or lacks the `VERDICT:` first line, retry it once; a call that produced no usable output doesn't count against the review-call cap.

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
```

Then you address the round:

1. **Verify before accepting.** Check the reviewer's factual claims against the code — a confident-sounding wrong finding rewrites a correct plan.
2. Fix blockers and majors in the plan; take minors/nits at your judgment.
3. A finding you disagree with: reject with a written rationale — never silently drop it.
4. Append the round to the review log: verdict, findings, and per-finding disposition (`ACCEPTED — <edit made>` / `REJECTED — <why>`).
5. Re-review with the updated plan and an updated history digest.

**Stop when:** the reviewer says `VERDICT: APPROVE`, or a round yields no blocker/major findings (remaining nits at your discretion), or the cap is hit.

**Escalate to the user instead of looping** when the cap is hit with open blockers, or the reviewer re-raises a rejected finding a second time with a genuinely new argument — that's a real design disagreement, and the user should arbitrate. Present both positions neutrally.

## Wrap-up

Report to the user: plan doc path, reviewer model used, rounds used, final verdict, and any rejected findings or open disagreements. Approval of the plan is not approval to implement — implementation is a separate decision for the user.

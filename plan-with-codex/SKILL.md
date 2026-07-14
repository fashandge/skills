---
name: plan-with-codex
description: Co-write a plan/design doc for a requirement together with the Codex agent — Claude drafts (or Claude and Codex draft independently and Claude synthesizes), then Codex reviews and Claude addresses feedback in a capped loop until approval. Use whenever the user asks to plan with codex, wants a plan doc reviewed by codex/GPT, wants a second-model opinion on a design or implementation plan, or says things like "plan this with codex", "have codex review the plan", "co-draft a plan". Also use it for audit-style requirements — find all the bugs/issues in an existing system and propose fixes — where independent Claude and Codex sweeps maximize coverage.
---

# Plan with Codex

Claude Code sessions only. If running inside Codex, skip this skill (never self-review) and write the plan directly.

The output is a plan doc that survived adversarial review by a second frontier model. Codex is called via `agents-cli` — each call is fresh-context and one-shot, so every prompt must be fully self-contained.

## Ground rules (plan-mode discipline)

Planning is read-only with respect to the world:

- Never modify existing source code or production data (databases, data files) — same discipline as `/plan` mode.
- Allowed writes: the plan doc, the review log, a Codex draft doc (flow 2), and ad-hoc scratch scripts for probing/debugging (put them in the session scratchpad, not the repo). Probes read production data; if a probe must write, run it against a scratch copy (e.g. a dev DB).
- `agents-cli` runs Codex auto-approved, so the prompt is the only guardrail: **every Codex prompt must state** "Treat the repo and all data as read-only. Do not create or modify any files" — except, in flow 2's draft call, the single output file it is told to write.

## Step 0 — Ground the requirement

Reviews are wasted on a plan built from wrong assumptions. Before drafting: explore the relevant code, run read-only probes if facts are uncertain, and clarify genuinely ambiguous requirements with the user. Distill the result into a **requirement brief** (one tight paragraph + key file paths + constraints/non-goals) — you'll paste it into every Codex prompt.

## Choose a flow

- **Flow 1 — draft → review loop** (default): Claude writes the plan, Codex reviews, Claude addresses, repeat.
- **Flow 2 — dual independent drafts**: Claude and Codex each write a plan from the same requirement brief *without seeing each other's*, Claude synthesizes one plan, then enter the flow-1 review loop. Use when the solution space is wide (multiple viable architectures), the requirement is high-stakes or ambiguous after grounding, or the user asks for it. Also use it for *discovery-shaped* tasks — auditing an existing system to find all bugs/issues and propose fixes — where the value is coverage: an agent that reads the other's findings first anchors on them and confirms instead of hunting, so two fresh-minded independent sweeps catch more, and the synthesis step doubles as cross-checking each finding. Independent drafting only pays when there is real design freedom or real discovery to do; for a well-constrained requirement it just adds a synthesis step.

The user can name a flow explicitly; that wins.

## Choose the Codex reviewer model

Match the reviewer to the drafter's intelligence tier — the loop only works when Codex is a peer: `gpt-5.6-sol` at high effort is comparable to Fable, `gpt-5.6-terra` at xhigh to Opus. A weaker reviewer rubber-stamps or nitpicks a stronger model's plan; if the model lineup changes, preserve this peer-matching principle rather than these specific names.

| This session's model | Default reviewer |
|---|---|
| Fable | `gpt-5.6-sol` — `xhigh` for deep passes, `high` for follow-up rounds |
| Opus | `gpt-5.6-terra`, `--codex-reasoning xhigh` throughout |
| Other/unknown | same as Fable |

**Deep passes** are where fresh whole-problem thinking pays: flow 2's independent draft and the first review round. Follow-up rounds verify fixes against a shrinking delta — `high` is enough there, and a maxed-out reviewer re-scanning a nearly-converged plan tends to manufacture nitpicks that burn rounds. Codex is flat-rate, so the graded effort is about latency and review noise, not cost.

Adjust by task difficulty: a really hard/complex requirement → `gpt-5.6-sol` at `xhigh` throughout; a simple one → `gpt-5.6-terra` at `xhigh` is enough. A model/effort the user names always wins. Use the same model for flow 2's independent draft as for review.

## Invoking Codex

Prompt via temp file on stdin (avoids quoting/ARG_MAX issues); the answer arrives on stdout — capture it to a file, then read the file:

```bash
P=$(mktemp); cat >"$P" <<'EOF'
<self-contained prompt>
EOF
agents-cli -a codex -m gpt-5.6-sol --codex-reasoning high \
  --codex-working-dir <repo-root> --timeout 3600 <"$P" > <round-output-file>
```

- Always pass `--timeout 3600`: the default is 1200s, which high/xhigh reviews of a substantial plan regularly exceed.
- Run long calls with Bash `run_in_background` and read the output file when it exits; don't kill quiet runs.
- No session resume: include the requirement brief, paths, constraints, and review history in every call.
- Full flag list: `agents-cli -h`.

## Artifacts

Each planning effort gets its own subfolder `docs/plans/YYYY-MM-DD_<slug>/` (create it if missing) — an effort produces up to three docs, and one folder per effort keeps `docs/plans/` scannable:

- `plan.md` — goal, current state, design, alternatives considered, step-by-step implementation, testing/verification, risks & rollback.
- `review.md` — one `## Round N` section per review: Codex's verdict + findings, then Claude's disposition per finding.
- `codex-draft.md` (flow 2 only) — Codex's independent draft, kept as a record of the road not taken.

## Flow 2 — independent drafts, then synthesize

1. Write your own plan draft (do not read Codex's first).
2. In parallel, ask Codex to write its plan to the effort folder's `codex-draft.md` — give it the same requirement brief you drafted from, and name that file as the one file it may write.
3. Synthesize: don't merge everything — pick the stronger skeleton, graft the other draft's better ideas, and note real divergences (they're usually the decisions worth surfacing to the user).
4. Enter the review loop below with the synthesized plan.

## The review loop

Up to **6 review calls** total (flow 2's draft call doesn't count). Typical convergence is 2–3 rounds; the cap is a backstop, not a target.

Each round, send Codex a review prompt shaped like:

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

Then Claude addresses the round:

1. **Verify before accepting.** Check Codex's factual claims against the code — a confident-sounding wrong finding rewrites a correct plan.
2. Fix blockers and majors in the plan; take minors/nits at your judgment.
3. A finding you disagree with: reject with a written rationale — never silently drop it.
4. Append the round to the review log: verdict, findings, and per-finding disposition (`ACCEPTED — <edit made>` / `REJECTED — <why>`).
5. Re-review with the updated plan and an updated history digest.

**Stop when:** Codex says `VERDICT: APPROVE`, or a round yields no blocker/major findings (remaining nits at your discretion), or the cap is hit.

**Escalate to the user instead of looping** when the cap is hit with open blockers, or Codex re-raises a rejected finding a second time with a genuinely new argument — that's a real design disagreement, and the user should arbitrate. Present both positions neutrally.

## Wrap-up

Report to the user: plan doc path, rounds used, final verdict, and any rejected findings or open disagreements. Approval of the plan is not approval to implement — implementation (and its routing, e.g. via codex-first) is a separate decision for the user.

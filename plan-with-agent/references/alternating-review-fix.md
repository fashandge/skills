# Alternating Review-and-Fix (Flow 3)

Shared protocol for flow 3 of `plan-with-agent` and `skill-review-with-agent`: instead
of only reporting findings, the reviewer fixes issues directly in the artifact each
round, and the two agents alternate turns until a clean approve. **Explicit opt-in only
— never auto-select it**; run it only when the user names it or asks for the reviewer to
fix/edit the artifact directly.

The consuming skill owns the artifact, the reviewer prompt, the list of writable paths,
and the snapshot/restore mechanics (plan-with-agent copies files by hand;
skill-review-with-agent drives `candidate_workspace.py`); this file owns the turn
protocol, so the two flows cannot drift apart on it. Pane mechanics — spawning, waiting,
reading, follow-up prompts — stay in
[`herdr-review-loop.md`](../../review-with-agent/references/herdr-review-loop.md).

## Reviewer choice

Prefer a **cross-vendor, peer-tier reviewer**; a modestly stronger one is acceptable.
Alternating direct edits only provide a meaningful cross-check when both agents can
independently detect mistakes made by the other. If the available pairing has a material
capability gap in either direction, tell the user and recommend flow 1, where proposed
changes remain explicit findings rather than already-applied edits; if they stick with
flow 3, honor it, but report the reduced cross-check confidence rather than implying
symmetric verification. `model-selection.md` owns the roster.

## Division of labor

Severity-agnostic but *kind*-sensitive: the reviewer fixes **factual and mechanical**
findings in place (wrong paths, missing steps, wrong sequencing, missing verification,
ambiguous instructions) and must **raise design-level disagreements as `RAISED` findings
without rewriting them** — a silently rewritten design decision buries exactly the
disagreement the review exists to surface.

## The cycle

Up to **4 reviewer turns**. Each cycle:

1. Snapshot every writable artifact exactly, before the turn (the consuming skill says
   how).
2. Send the reviewer turn — spawn the pane with the skill's prompt on the first turn,
   `herdr agent prompt --wait` for later ones — then read its output from the pane.
3. Verify the review log changed **append-only**: its previous bytes intact, and exactly
   one new `## Round N` reviewer section added. Any overwrite, earlier-round edit,
   duplicate round, or missing entry makes the turn unusable.
4. **Unusable turn**: restore every writable artifact exactly to its pre-turn state,
   then re-prompt — never retry atop a partial mutation. A live reviewer remembers the
   turn you discarded, so say plainly that you rolled the artifacts back and what to do
   differently; otherwise it assumes its edits still stand.
5. Diff the artifact against its snapshot and **verify every edit against the ground
   truth** — a confident wrong fix is worse than a wrong finding, because it is already
   applied. Revert wrong edits and record `REVERTED — <why>` in your session turn; never
   edit the reviewer's own log entry.
6. Address `RAISED` findings: fix them, or record `REJECTED — <why>` /
   `DEFERRED — <why>`; never silently drop one. Then make any further improvements of
   your own.
7. Append a `### Session turn` subsection to the round in the review log: per-edit and
   per-finding dispositions plus a summary of your own changes. If not converged, send
   the next turn with an updated digest.

## Verdict and stopping

Every reviewer-turn prompt carries this rubric — first line exactly
`VERDICT: APPROVE | REVISED | REVISE`:

- `APPROVE` iff the reviewer made no artifact edits and no blocker or major findings
  remain (minor/nit `RAISED` findings may accompany it).
- `REVISED` if it edited the artifact and no blocker or major finding is left unfixed.
- `REVISE` if blocker or major findings remain `RAISED`.
- The required review-log append never counts as an edit.

**Stop when** a turn returns `VERDICT: APPROVE` and your handling of it makes no further
change to the artifact — the state you keep is then exactly the state that was approved.
An `APPROVE` turn may still raise minor/nit findings: record unchanged ones as
`REJECTED` or `DEFERRED` to stop; if addressing one changes the artifact, send another
reviewer turn.

**Stop and escalate** when the cap is hit, or when a design disagreement survives your
written rebuttal plus one follow-up turn. Present both positions neutrally, and let the
user decide before any result is applied or acted on.

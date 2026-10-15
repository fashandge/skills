# Reviewer Model Selection

Roster updated: 2026-10-14

Consumed by the `plan-with-agent`, `review-with-agent`, and `skill-review-with-agent` skills. Treat this roster as maintenance data, not a timeless ranking. Preserve the selection principles in the consuming SKILL.md when model lineups change: never self-review, honor explicit user choices subject to that exclusion, and default first-pass reviews to a cross-vendor reviewer one capability tier stronger when available. When the session already uses a top-tier model or no stronger cross-vendor model is available, use the strongest cross-vendor peer.

## Current tier calibration

- Codex: `gpt-6-astra` > `gpt-5.6-sol` > `gpt-5.6-terra` > `gpt-5.6-luna`. Astra is the top
  of the gpt-6 family (no siblings yet) and stronger than every gpt-5.6 model. Both astra
  and sol over-engineer and drift into detail on an open brief (observed 2026-09-10); their
  findings are sound, so scope their later rounds to majors per the shared herdr reference
  rather than avoiding them.
- Claude: `fable` > `opus` (the Claude CLI aliases, so the roster does not need touching when a version bumps)
- Cross-vendor working calibration: Fable at high ≈ astra at high; Fable ≈ sol at
  high effort with Fable ahead; Opus ≈ terra at xhigh.

## Default reviewer mapping

| This session's model | Default reviewer |
|---|---|
| Fable | `gpt-6-astra` (strongest cross-vendor peer; nothing stronger exists) |
| Opus | `gpt-5.6-sol` |
| `gpt-6-astra` | `fable` |
| `gpt-5.6-sol` | `fable` |
| `gpt-5.6-terra` | `opus` |
| `gpt-5.6-luna` | `opus` |
| Sonnet or Haiku | `gpt-5.6-terra` |
| Non-Claude, non-GPT vendors | calibrate first; if uncertain, `fable` |

These mappings apply to the review rounds of all three skills, and to plan-with-agent flow 2's independent draft, which uses the same model and then reuses the pane as the reviewer. Keep the same reviewer, at the same effort, for every round: a pane's effort is fixed at spawn, and later rounds are kept short by scoping them to blockers and majors (the shared herdr reference), not by lowering effort. The one exception is flow 3's direct-edit turns, which prefer a peer-tier pairing because mutual verifiability matters more than maximum strength (`alternating-review-fix.md` says why).

If the session model is missing from the table, compare its documented capability with the current tiers and choose the other vendor one tier stronger when available. If the session is already top-tier, use the strongest cross-vendor peer. If exact capability is uncertain, choose the stronger eligible reviewer.

## Effort

One effort per model, chosen at spawn and kept for the whole run:

- `gpt-6-astra`: `high` — that is already Fable-class; `xhigh` buys detail, not substance.
- `gpt-5.6-sol`: `xhigh`.
- `gpt-5.6-terra`: `xhigh`.
- `fable`: `high` — matches astra at high per the calibration above; `xhigh` buys detail, not substance.
- `opus`: `high`.

A user-specified effort wins. If cost matters for a run, pick a lower effort for the whole loop up front rather than trying to step down mid-loop, which would mean respawning and losing the reviewer's context.

## Availability and fallback

Before a long run, confirm the required provider binary exists and that the chosen model is locally configured or recognized by that provider. `spawn_worker.sh` passes the model string through to the agent, so a successful spawn is not proof the model exists — a bad name surfaces as a pane that dies or sits at an error, which `herdr agent get` reports as `idle` with nothing done.

Handle availability failures without weakening the reviewer requirement:

- Do not retry an unavailable model, missing binary, or authentication failure with the same configuration.
- If the user named only a vendor, try another model from that vendor that meets the applicable strength policy before asking.
- If the user named an exact model, do not silently substitute another model.
- If no one-tier-stronger cross-vendor reviewer is available, fall back to the strongest cross-vendor peer. If no peer-tier reviewer is available, stop and report the constraint rather than weakening further.

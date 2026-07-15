# Reviewer Model Selection

Roster updated: 2026-07-13

Consumed by the `plan-with-agent`, `review-with-agent`, and `skill-review-with-agent` skills. Treat this roster as maintenance data, not a timeless ranking. Preserve the selection principles in the consuming SKILL.md when model lineups change: never self-review, honor explicit user choices subject to that exclusion, and default first-pass reviews to a cross-vendor reviewer one capability tier stronger when available. When the session already uses a top-tier model or no stronger cross-vendor model is available, use the strongest cross-vendor peer.

## Current tier calibration

- Codex: `gpt-5.6-sol` > `gpt-5.6-terra` > `gpt-5.6-luna`
- Claude: `claude-fable-5` (Fable) > `claude-opus-4-8` (Opus)
- Cross-vendor working calibration: Fable ≈ sol at high effort; Opus ≈ terra at xhigh.

## Default first-pass reviewer mapping

| This session's model | Default reviewer |
|---|---|
| Fable | `gpt-5.6-sol` |
| Opus | `gpt-5.6-sol` |
| `gpt-5.6-sol` | `claude-fable-5` |
| `gpt-5.6-terra` | `claude-fable-5` |
| `gpt-5.6-luna` | `claude-opus-4-8` |
| Sonnet or Haiku | `gpt-5.6-terra` |
| Non-Claude, non-GPT vendors | calibrate first; if uncertain, `claude-fable-5` |

These mappings apply to the first review round in `review-with-agent` and to review rounds in plan-with-agent flows 1 and 2. Keep the same reviewer model for follow-up rounds, but lower effort as described below. Two counterpart calls intentionally use peers instead: flow 2's independent draft, where competitive alternatives matter more than reviewer authority, and flow 3's direct-edit turns, where mutual verifiability matters more than maximum strength.

If the session model is missing from the table, compare its documented capability with the current tiers and choose the other vendor one tier stronger when available. If the session is already top-tier, use the strongest cross-vendor peer. If exact capability is uncertain, choose the stronger eligible reviewer.

## Effort mapping

- `gpt-5.6-terra`: `xhigh` for deep passes; `high` for follow-up rounds.
- `gpt-5.6-sol`: `xhigh` for deep passes — an independent draft (plan-with-agent flow 2), the first review round of a new artifact, a genuinely hard requirement; `high` for follow-up rounds.
- `claude-fable-5`: use the same deep-pass versus follow-up rule as sol.
- `claude-opus-4-8`: `high` for deep passes; `medium` for follow-up rounds.

A user-specified effort wins. Deep passes benefit from fresh whole-problem reasoning; follow-up rounds verify a shrinking delta and normally do not need maximum effort.

## Availability and fallback

Before a long run, confirm the required provider binary exists and that the chosen model is locally configured or recognized by that provider. `agents-cli` accepts arbitrary model strings, so argument parsing alone is not proof of availability.

Handle availability failures without weakening the reviewer requirement:

- Do not retry an unavailable model, missing binary, or authentication failure with the same configuration.
- If the user named only a vendor, try another model from that vendor that meets the applicable strength policy before asking.
- If the user named an exact model, do not silently substitute another model.
- If no one-tier-stronger cross-vendor reviewer is available, fall back to the strongest cross-vendor peer. If no peer-tier reviewer is available, stop and report the constraint rather than weakening further.

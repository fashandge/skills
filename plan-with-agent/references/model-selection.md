# Reviewer Model Selection

Roster updated: 2026-07-13

Consumed by the `plan-with-agent` and `review-with-agent` skills. Treat this roster as maintenance data, not a timeless ranking. Preserve the selection principles in the consuming SKILL.md when model lineups change: never self-review, honor explicit user choices subject to that exclusion, default cross-vendor, and use an at-least-peer reviewer.

## Current tier calibration

- Codex: `gpt-5.6-sol` > `gpt-5.6-terra` > `gpt-5.6-luna`
- Claude: `claude-fable-5` (Fable) > `claude-opus-4-8` (Opus)
- Cross-vendor working calibration: Fable ≈ sol at high effort; Opus ≈ terra at xhigh.

## Default reviewer mapping

| This session's model | Default reviewer |
|---|---|
| Fable | `gpt-5.6-sol` |
| Opus | `gpt-5.6-terra` |
| `gpt-5.6-sol` | `claude-fable-5` |
| `gpt-5.6-terra` | `claude-opus-4-8`; hard tasks: `claude-fable-5` |
| `gpt-5.6-luna` | `claude-opus-4-8`; hard tasks: `claude-fable-5` |
| Sonnet or Haiku | `gpt-5.6-terra`; hard tasks: `gpt-5.6-sol` |
| Non-Claude, non-GPT vendors | `claude-opus-4-8`; hard tasks: `claude-fable-5` |

If the session model is missing from the table, compare its documented capability with the current tiers and choose the other vendor at the same tier or higher. If exact capability is uncertain, choose the stronger eligible reviewer.

## Effort mapping

- `gpt-5.6-terra`: always `xhigh`.
- `gpt-5.6-sol`: `xhigh` for deep passes — an independent draft (plan-with-agent flow 2), the first review round of a new artifact, a genuinely hard requirement; `high` for follow-up rounds.
- `claude-fable-5`: use the same deep-pass versus follow-up rule as sol.
- `claude-opus-4-8`: always `high`.

A user-specified effort wins. Deep passes benefit from fresh whole-problem reasoning; follow-up rounds verify a shrinking delta and normally do not need maximum effort.

## Availability and fallback

Before a long run, confirm the required provider binary exists and that the chosen model is locally configured or recognized by that provider. `agents-cli` accepts arbitrary model strings, so argument parsing alone is not proof of availability.

Handle availability failures without weakening the reviewer requirement:

- Do not retry an unavailable model, missing binary, or authentication failure with the same configuration.
- If the user named only a vendor, try another at-least-peer model from that vendor before asking.
- If the user named an exact model, do not silently substitute another model.
- If no eligible reviewer is available, stop and report the constraint rather than weakening the reviewer below peer tier.

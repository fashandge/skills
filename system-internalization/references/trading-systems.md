# Trading-System Specifics

Domain material for coaching trading/investment systems (the original and most common use of this skill). Read this when the documented system is a trading system, especially an IBD/O'Neil-style one from the user's Obsidian wiki.

## Typical layer sequence for a trading system

Most trading systems follow a similar architecture. Adapt to the specific system, but the typical dependency order:

1. **Philosophy and constraints** — What the system believes, what it won't do. "只看图、不看新闻" / "等和跟"
2. **Macro regime gate** — What conditions must be true for ANY entry. Usually an index-level signal (FTD, distribution days).
3. **Entry mechanics** — Exact conditions, sizing, order types (e.g. three-step build, power trend entries).
4. **Position management** — Stop losses, scaling, stop-upgrade rules (e.g. E8→E21→S50→S200 ladder).
5. **Exit rules** — When to take profits, when to cut everything (e.g. S50 blow-through, distribution day count).
6. **Cross-timeframe rules** — When to switch from daily to hourly or weekly.
7. **Account/portfolio structure** — How positions fit into the broader strategy (trading vs long-hold, profit rotation).
8. **Edge cases and known limitations** — What the system admits it can't handle.

## Making scenarios feel real

Use actual tickers the system trades (QQQ, SPY, SMH, NVDA, MU, SNDK, LITE, MRVL, AMD, AVGO). Describe chart conditions concretely.

Good scenario:
> "QQQ made a new low 7 days ago. Since then: Day 1-3: sideways chop. Day 4: +0.8% on average volume. Day 5: -0.3%. Day 6: +2.3% on volume 40% above average. Day 7 (today): +0.5%. What does the system say?"

Bad scenario:
> "Imagine a situation where FTD might be happening."

## Trading-flavored test questions

- **Identification:** "Is FTD confirmed here?"
- **Sizing:** "How much do you buy?"
- **Stop placement:** "Where does your stop go?"
- **Stop upgrade:** "Has the condition for upgrading from E8 to E21 been met?"
- **Cross-check:** "Does the weekly chart confirm the daily signal?"
- **Priority:** "The daily says buy but the weekly MACD histogram is still negative. Which takes priority in this system?"

## Common gap categories in trading systems

- Forgetting volume confirmation requirements
- Misremembering thresholds (which % gain? which day range?)
- Confusing daily vs weekly vs hourly timeframe rules
- Applying stock-entry rules when the macro gate hasn't fired
- Forgetting stop-loss upgrade conditions
- Missing the "do nothing" signal (when the system says wait)

## External verification sources

When the user asks to verify a rule against authoritative sources, the usual origins are IBD, O'Neil, and Minervini. The user's notes often use modified thresholds (e.g. 1.5% FTD gain instead of IBD's 1.25%) — flag these as deliberate customizations, and interpret the trade-off ("slightly more conservative, filters more noise at the cost of entering later"). The standard source may also include conditions absent from the note (e.g. rally attempt validity: index must not break below Day 1's low) — surface those gaps.

## Deep-dive references

- `ibd-ftd-definition-and-rationale.md` — Verified IBD FTD definition, note-vs-standard differences, and the rationale behind the Day 4-10 / volume / gain thresholds. Use when coaching any IBD-based system or when the user asks to verify FTD rules against authoritative sources.
- `multi-position-stop-loss-tension.md` — The practical tension between "independent stops per position" and "unified exit after all positions entered" in scaling-in systems. Use when the user asks about stop management across multi-step entries.
- `stop-loss-upgrade-profit-precondition.md` — The implicit precondition that stop-upgrade target MAs must still protect profit. Use when the user questions upgrade rules at borderline profit levels.

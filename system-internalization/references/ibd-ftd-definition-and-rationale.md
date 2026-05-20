# IBD Follow-Through Day (FTD): Verified Definition and Rationale

Source cross-referenced against Investors Business Daily, O'Neil/MarketSmith documentation, and quantified backtests (quantifiedstrategies.com, quantifiableedges.blogspot.com). Updated 2026-05-02.

## Standard IBD Definition

### Rally Attempt (prerequisite)
- After a market correction of ~10%+, the index must close higher for the first time — this is **Day 1** of the rally attempt
- The rally attempt remains valid **as long as the index does not close below Day 1's low** (if it does, the attempt fails and you wait for a new one)

### Follow-Through Day (the signal)
- Occurs on **Day 4 or later** of the rally attempt
- One or more major indexes (S&P 500, Nasdaq) close **up at least 1.25%**
- Volume must be **higher than the previous trading day** (does NOT need to be above the 50-day average, just higher than the prior day — this is a common misconception)
- Days 4-7 are the **best window**; signals after Day 10 are less reliable but can still work

### What invalidates a confirmed FTD
- The index closes **below the FTD day's low** = FTD failure
- A circuit breaker event (index breaks below the 50-day line while Nasdaq is >10% off its recent high) can negate a power trend in early stages

## Note vs Standard IBD: Common Differences

| Parameter | Standard IBD | Notes may modify to... |
|-----------|-------------|----------------------|
| Gain threshold | ≥ 1.25% | 1.5% (more conservative) |
| Volume requirement | Higher than prior day (any amount) | "放量" (vague) — IBD only requires > prior day |
| Rally attempt rule | Must not break Day 1 low | Often omitted from trader notes |
| Window | Day 4-10 (best 4-7), can stretch | Often written as "4-10" exclusively |

## Why FTD Exists (O'Neil's Rationale)

O'Neil studied market cycles dating back to the 1880s and found:

1. **Day 1-3 rallies can be traps.** Short covering, dead cat bounces, retail panic buys — none reflect institutional accumulation. A bounce that lasts 3 days then fails is common.

2. **Institutions buy gradually.** When large funds decide to re-enter after a correction, they don't buy everything on Day 1. They accumulate over days or weeks. The FTD captures the day when that accumulation becomes visible as a **price surge on above-average participation (volume)**.

3. **Volume confirmation prevents false signals.** Price alone can be deceptive — low-volume rallies lack conviction. A +1.5% day on light volume means few participants believe in the move. A +1.5% day on heavy volume means institutions are committing capital.

4. **The 4-day minimum filters noise.** Wait long enough for the initial bounce emotions to fade, and for genuine buying to emerge or fail. If a real rally is starting, it will still be there on Day 7.

## Practical Consequences

- **If the user's note says 1.5%** and standard IBD says 1.25%: the user is slightly more conservative. They'll enter later, confirm fewer signals, but likely have a higher win rate on the signals they do take.
- **If the note omits the rally attempt rule** (don't break Day 1 low): this is a real gap. Without it, you could get a Day 1 that made a "new low" but the rally attempt never actually started. Flag this to the user.
- **Volume requirement**: Many traders think they need "above average" volume. IBD says "higher than prior day" is sufficient. This matters — in practice, requiring above-average volume misses many valid FTDs.

## References

- investors.com — IBD's official definition
- quantifiedstrategies.com/follow-through-day/ — backtest data on FTD reliability
- quantifiableedges.blogspot.com — independent analysis of FTD predictive value

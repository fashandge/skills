# Stop-Loss Upgrade: Implicit Profit Precondition

## The Rule (as written)

```
沿 E8 上涨超过 20% → 升级为 E21 止损
利润空间继续扩大 → 升级为 S50 止损
利润非常大时 → 可用 S200 止损
```

## The Implicit Precondition

Upgrading from E21 → S50 (or S50 → S200) requires that the **target MA still protects meaningful profit**.

If S50 is at $52 and your cost is $51, upgrading from E21 ($58) to S50 ($52) doesn't protect "expanding profit" — it's actually loosening the stop to protect almost no profit.

**When to NOT follow the upgrade rule:**

- S50 is below your break-even point → stay on E21
- S50 would leave < 5% profit after a major pullback → consider staying on E21 or upgrading to E13
- Wait for S50 to rise closer to price before upgrading

## The Core Logic

| Price direction | Upgrade direction | Rationale |
|---------------|-----------------|-----------|
| Price rising, profit growing | E8 → E21 → S50 → S200 | Give the winning stock room to breathe |
| Price falling, profit shrinking | Do NOT loosen stop | Protect remaining profit |
| Price flat | Hold current stop | No change needed |

## Why This Matters for Internalization

This is the nuance that separates rote rule-following from system understanding. A trader who blindly upgrades from E21 to S50 when S50 is at break-even is applying the rule mechanically, not systemically. The system was designed to protect profits, not to follow a mechanical MA ladder regardless of dollar amounts.

## Cross-reference

- System note section: `止损系统` — "随着利盈空间的扩大，进行均线切换"
- Session insight: user asked "what if S50 means zero profit?" — this is the edge case the written rules don't explicitly address

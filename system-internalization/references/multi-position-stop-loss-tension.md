# Multi-Position Stop Loss Tension

## The Problem

When a system uses **three-step scaling-in** (1/3 + 1/3 + 1/3) with **independent stop losses per position**, a tension arises:

- Each new 1/3 position gets its own initial stop (e.g., 10/20-day low - $0.25)
- Earlier 1/3 positions may have already upgraded to E21 / S50 as profit grew
- Later 1/3 positions have minimal profit and still sit on tight initial stops

This creates an awkward situation where the same stock has multiple stop orders at different levels.

## How Systems Typically Resolve This

### Option A: Strict Independence (literal reading of "each position has its own stop")
- Position 1 (avg cost $50, +35%): stop at E21 or S50
- Position 2 (avg cost $52, +30%): stop at E21 or S50 (same level as P1 since profit threshold met)
- Position 3 (avg cost $55, +23%): stop at E8 or initial 10/20-day low
- Net effect: as price rises, all positions converge to the same MA stop level over time

### Option B: Unified Exit
- Use average cost to determine when to upgrade, and a single stop order for all positions
- Simpler to manage but contradicts "independent stop per position" rule
- Risk: the newest 1/3 doesn't get its own protection period

### Option C: Gradual Convergence (most practical)
- After all 3 positions are entered, treat them as one unit for stop upgrades
- Use avg cost as the reference for % profit calculations
- Once avg cost is up 20%+, all positions share the same E21 (or higher) stop
- Before all 3 positions are entered: each new 1/3 gets independent initial stop for 2-3 trading days

## Key Observation for Coaching

When a user spots this tension, validate it. It's not a bug in the system — it's a real operational question that even experienced traders handle differently. The system's designer may not have addressed it explicitly because they assumed positions would converge naturally as price rises.

## Cross-reference

- System note section: `止损系统` — "每一笔加仓都有对应的独立止损单"
- System note section: `个股买入系统：三步建仓法` — three independent 1/3 entries

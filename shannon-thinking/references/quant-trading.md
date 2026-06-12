# Shannon moves instantiated: quant trading ML models & strategies

How each move typically lands on signal research, model development, strategy design, backtesting, and execution problems. These are *starting instantiations* — adapt to the user's actual P, don't paste them back verbatim.

## 1. Simplification — the toy strategy ladder

Strip to: **one asset, one signal, a linear model, daily bars, no costs, fixed unit sizing.** Rungs to add back, one at a time: transaction costs and slippage → realistic sizing/risk limits → the full universe → nonlinearity/interactions → intraday frequency → capacity and market impact → regime dependence.

The check that the toy still contains the difficulty is critical here, because the difficulty in trading problems is usually the **signal-to-noise ratio or a data pathology** (leakage, survivorship, non-stationarity) — not the plumbing. A toy that keeps the plumbing and strips the noise (e.g., testing on synthetic data where the signal is planted) answers a different question; useful for validating machinery, useless for validating alpha. Conversely, if the strategy only "works" before costs, costs *are* the essential part — simplify everything else and keep them.

Diagnostic use: if the toy version also fails, the problem is upstream (data, labels, signal); if the toy works and rungs break it, the failing rung names the real problem.

## 2. Similar known problems — the nearest solved P′

- **Return forecasting** → supervised learning with weak labels and tiny signal: the solved analogues are noisy-label learning and weather forecasting (probabilistic skill scores, ensembling, sharpened calibration over point accuracy).
- **Execution / order placement** → optimal control and inventory management (Almgren–Chriss, queueing); also RL on simulators.
- **Portfolio construction** → convex optimization with estimation error: the solved literature is robust/regularized optimization (shrinkage, risk parity as a prior).
- **Regime detection** → change-point detection and hidden Markov models from signal processing.
- **Strategy decay** → adversarial/non-stationary learning; ecology (niche crowding) for capacity and alpha erosion.
- **The user's own past problems**: which previously-solved model of theirs is structurally closest (same horizon, same label type, same data geometry)? Transport its validation scheme and failure modes, not just its features.

Always make the return jump: what does P′'s solution concretely become in this strategy? ("Ensembling in weather forecasting" → "average across feature subsets and refit windows, score with IC distribution not point IC.")

## 3. Restatement — change what counts as an answer

- **Prediction ↔ ranking ↔ classification ↔ regime**: "predict next-period return" vs. "rank the cross-section" vs. "classify direction conditional on a filter" vs. "detect when the strategy should be off." Each implies different labels, losses, and validation.
- **The counterparty restatement**: instead of "where is the alpha?", ask "**whose money am I taking and why are they paying it?**" (hedgers paying for immediacy, index flows, forced rebalancers, slower reaction times). If no answer exists, the signal is suspect regardless of backtest.
- **Blotter-space restatement**: describe the strategy purely as its trade blotter — holding period, turnover, hit rate, win/loss skew, when it trades. Many "model problems" become visible as blotter pathologies (e.g., P&L concentrated in 3 days of the year).
- **Risk-space restatement**: state the strategy as the risk premium or behavioral effect it harvests, with the model demoted to a timing/sizing layer.
- **Cost-side inversion of the objective**: not "find more alpha" but "lose less of the alpha I have" (execution, turnover, financing) — often the larger lever.

## 4. Generalization — after anything works

- A signal that works on one asset/market: same economic mechanism elsewhere (other asset classes, other horizons, other geographies)? If it only works in one place, suspect overfitting; if it generalizes, you've found the *principle* and can search its family.
- A fix for one backtest artifact (e.g., a leakage bug): promote it to a general validation rule in the pipeline, not a one-off patch.
- A feature transform that helped one model: is it a general property of the data (e.g., volatility-normalization) that belongs in the data layer for *all* models?

## 5. Structural analysis — decompose the chain, metric each link

Standard chain: **data → labels → features → model → signal → portfolio construction → execution → realized P&L.** Each link gets its own metric so you can find the failing one instead of redesigning everything:

- signal quality: IC / rank-IC distribution by period, decay curve by horizon
- portfolio construction: transfer coefficient (how much of the signal survives constraints)
- execution: implementation shortfall vs. arrival
- end-to-end: realized vs. backtest P&L attribution

A model-development decomposition for the research process itself: data audit → label design → feature set → model class → validation scheme → sizing — debug them in this order, because a flaw upstream invalidates everything downstream.

## 6. Inversion — assume the strategy works, derive what must be true

- **Required-signal inversion**: assume the target Sharpe/capacity. Derive the IC, breadth, horizon, and turnover the signal *must* have (fundamental law of active management as the inversion tool). If the required IC is implausible for the data, the design is dead before any model is fit.
- **Blotter inversion**: write the trade blotter of the working strategy first — what it holds, how long, when it trades — then ask what forecast object produces that blotter. Often reveals you need a different label than the one being modeled.
- **Counterparty inversion**: the strategy makes money ⇒ someone is reliably losing it ⇒ who, and why do they persist? No persistent loser ⇒ no persistent strategy.
- **Premortem**: assume it ran live for a year and failed. Rank the post-mortem causes (overfit validation, regime change, crowding, costs, capacity) and check the current design against each *now*.
- **Feedback-style design** (Shannon's nim move): when computing the optimal action forward is hard, search backward — simulate candidate actions and run the evaluation in reverse until one matches the constraints (e.g., target-risk sizing found by iterating the risk model rather than solving in closed form).

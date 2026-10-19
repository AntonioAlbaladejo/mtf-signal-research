# Research protocol

**Date:** 17 October 2026.

These rules take precedence over every other decision in the project. They exist because, with
enough combinations of indicators, parameters, timeframes and assets, **something always looks good
in a backtest**. The best of a thousand noise series looks like a strategy. More data does not fix
that; counting the trials and fixing the rules before looking does.

---

## 1. Pre-registration

No test runs without a prior entry in [HYPOTHESES.md](HYPOTHESES.md) that states the exact
definition, the null hypothesis, the metric and the decision criterion. That entry is committed
**before** the test runs. Because the repository is public, the commit timestamp is the evidence.

If anything in a definition has to change after the data has been seen, a **new variant** is created
(H1.b, and so on), and it counts as one more trial. The original entry is never edited.

## 2. Trial registry

Every run, including failed and discarded ones, is appended to an append-only registry
(`research/trials`, created in phase 2) with:

- the hypothesis or variant id and the configuration hash;
- the data window, universe and timeframe;
- the number of events or trades, the primary metric and its confidence interval;
- whether the run touched the hold-out.

The total number of trials feeds the **Deflated Sharpe Ratio** and the multiple-testing correction.
A trial that goes unregistered inflates every result.

## 3. Sealed hold-out

- The **most recent 6 months** at the moment the research dataset is frozen (end of phase 1) are
  sealed.
- The data loader **refuses** to serve sealed dates unless called with `unseal=True`, and every such
  access is logged in the trial registry.
- Each hypothesis family touches the hold-out **once**, at the end, to confirm or reject.
- Everything published after the freeze is, by construction, forward data.
- **Structural reads are allowed.** Universe construction and data-quality checks may read sealed
  dates, because they use only volumes, timestamps and bar consistency, never returns or signals.

## 4. Causality (no look-ahead)

**Time convention:** every bar is indexed by its **close**. An event detected at the close of bar
*t* trades at the **open of bar *t+1***. Forward returns are measured from that open.

- **Multi-timeframe alignment:** a 4h bar that opens at 08:00 becomes available at 12:00. Joins
  across timeframes are *as-of* joins on the close time. Using the still-forming 4h bar at 10:15 is
  the most common bug in these backtests.
- **Pivot confirmation:** a swing high or low exists only from the moment it is confirmed (k bars
  later, or once price reverses by k·ATR). Every pivot stores its `confirmed_at`, and no signal may
  use it earlier. The classic ZigZag repaints; using it without this correction is forbidden.
- **Future-invariance test,** mandatory for every feature and signal: alter the data after *t*,
  recompute, and check that every value up to *t* is unchanged.
- **Point-in-time universe:** use the liquidity ranking as it stood on each date, never today's.

## 5. Null hypotheses

No result is read in isolation. Every signal is compared with:

1. **Matched random entries:** same asset, timeframe, regime (R0, see HYPOTHESES.md), number of
   events and holding period, repeated 1,000 times. This gives the null distribution of the effect.
2. **Unconditional baseline:** the distribution of returns over all bars, plus buy-and-hold.
3. **For hypotheses about levels** (Fibonacci, support/resistance): **arbitrary neighbouring
   levels**. A level working is not enough; it must work better than the levels next to it.

## 6. Costs and simulation

- Results are always reported **gross and net**. Decisions are made on net results.
- The cost model is per venue: maker and taker fees, slippage (estimated from the recorded book
  where available, otherwise a conservative multiple of the spread) and funding.
- **Intrabar ambiguity:** if both the SL and the TP fall inside the same bar, resolve it with
  1-minute data. If it is still ambiguous, assume the **worst case**.
- **Zero-volume bars are untradable.** The archive pads exchange outages with flat zero-volume bars
  (DATA.md §3). No order fills in them, and they do not trigger stops. A position held through one
  is exposed to the jump at the next traded bar.
- **Cost-model sanity check:** a random-entry strategy must return ≈ −costs. If it returns
  anything else, the cost model is wrong.

## 7. Statistics

- Effects are measured in **volatility units** (return divided by ATR or rolling σ), so that assets
  and periods are comparable.
- Overlapping returns are autocorrelated, so confidence intervals use a **block bootstrap** (or HAC
  standard errors), never an independence assumption.
- **Multiple comparisons:** the false discovery rate is controlled within each family
  (Benjamini-Hochberg, q = 0.05).
- **Stability:** the sign of the effect must hold in at least 2/3 of the complete years and in at
  least 2/3 of the assets.
- **Validation:** walk-forward for anything with fitted parameters; purged, embargoed
  cross-validation for ML (phase 4).

## 8. Metrics

- **Primary:** Sharpe ratio of daily returns net of costs, annualised with √365.
- **Acceptance gate:** Deflated Sharpe Ratio above 0.95, computed with the actual number of trials.
- **Hard constraints:** maximum drawdown and a minimum number of trades, set per hypothesis.
- **Secondary:** Sortino, Calmar, turnover, average exposure.
- **Horizons and strategies are always compared at equal risk,** with position size set to a
  volatility target. Otherwise, whichever uses the most leverage wins.

## 9. Retraction and stopping rule

- A result that no longer holds when re-measured is **retracted in writing**, with the date and the
  reason. It is never silently deleted.
- If no hypothesis beats its null net of costs by the end of phase 3, that is the project's result
  for that phase. It is documented, and the decision to continue is made then.

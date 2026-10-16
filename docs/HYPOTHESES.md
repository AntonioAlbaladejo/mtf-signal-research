# Pre-registered hypotheses

**Date:** 17 October 2026.

Rules in [PROTOCOL.md](PROTOCOL.md). An entry is never edited after its test runs; changes create a
new variant, which counts as one more trial. Possible statuses: `pre-registered` → `running` →
`confirmed` / `rejected` / `retracted`.

Family A (classical TA) goes first. These tools can be defined precisely, are widely used and are
rarely tested against proper nulls, and testing them exercises the whole pipeline (FOUNDATIONS
D-10). The other families in the research agenda are pre-registered when their turn comes.

---

## Common definitions

### R0: canonical regime

Used to match nulls and to stratify results. It is never optimised.

- **Trend (4h):** up if close > EMA(200) and the EMA(200) is higher than 20 bars earlier; down in the
  symmetric case; neutral otherwise.
- **Volatility (1d):** tercile of ATR(14)/close, computed over a rolling 365-day window that uses
  only past data.

This gives 3 × 3 = 9 regime cells.

### Forward-return horizons

Counted from the open of the bar after the event.

| Event timeframe | Horizons |
|---|---|
| 1h | 4, 12 and 24 bars |
| 4h | 3, 6 and 12 bars |
| 1d | 1, 3 and 5 bars |

### Economic threshold

An effect counts as relevant only if the mean return in the predicted direction exceeds the mixed
round-trip cost (maker entry, taker exit ≈ 0.06 %) plus the estimated slippage.

### Data

Binance USDⓈ-M, point-in-time top-10 universe, from 2020 to the start of the sealed hold-out.

---

## H1: TD Sequential anticipates exhaustion

**Status:** pre-registered.

**Definition** (the canonical version in J. Perl, *DeMark Indicators*, 2008; any other version is a
variant):

- **Sell setup:** 9 consecutive closes with C[t] > C[t−4], preceded by a bullish price flip
  (C[t−1] < C[t−5] on the bar before bar 1). The buy setup is symmetric.
- **Perfection (sell):** the high of bar 8 or bar 9 is ≥ the highs of bars 6 and 7.
- **Sell countdown:** starting from the completed setup, count bars (not necessarily consecutive)
  with C ≥ the high two bars earlier, up to 13. The high of bar 13 must be ≥ the close of countdown
  bar 8. Cancellation rules follow the reference.

**Hypothesis:** after a sell (buy) setup 9, the normalised forward return is lower (higher) than
under the matched null. The same applies to countdown 13.

**Family cells:** {setup 9, perfected setup 9, countdown 13} × {buy, sell} × {1h, 4h, 1d} ×
3 horizons = 54 cells, with FDR control across all of them.

**Causality:** TD Sequential uses only past closes, and the event is known at the close of bar 9.
The future-invariance test is applied anyway.

**Criterion:** confirmed in a cell if it survives FDR, exceeds the economic threshold and is stable
(PROTOCOL §7). Otherwise, rejected in that cell.

---

## H2: Fibonacci retracement levels are special

**Status:** pre-registered.

**Swings:** causal ATR ZigZag. A pivot is confirmed once price reverses by k·ATR(14) from the
extreme, and it stores its `confirmed_at`. Two registered variants: k = 2 and k = 3.

### H2a: Structural. Where do retracements stop?

This part is descriptive, so it may use completed retracements.

- **Measure:** the depth r = |B − C| / |B − A| of each completed retracement, where A→B is the
  impulse and C is the retracement extreme.
- **Hypothesis:** density is higher in the ±0.02 windows around r ∈ {0.382, 0.5, 0.618} than in
  equally wide windows at neighbouring levels.
- **Double null:**
  1. local smoothness of the empirical density;
  2. **synthetic series** (a block bootstrap of returns, which keeps volatility but destroys any
     memory of levels) run **through the same ZigZag**. The pivot algorithm shapes the distribution
     of r by itself, so the null must go through it too.

### H2b: Tradable. Does touching a level anticipate continuation?

This part is causal: it uses confirmed pivots only.

- **Event:** while the R0 trend agrees with the impulse, price touches level r of the last confirmed
  impulse.
- **Hypothesis:** the forward return in the impulse direction is higher after touching a Fibonacci
  level than after touching the control levels {0.45, 0.55, 0.70}.
- **Criterion:** Fibonacci must beat the neighbouring levels, not just random times. A pullback
  bouncing within a trend says nothing specific about Fibonacci.

**Timeframes:** 1h and 4h.

---

## H3: RSI adds information as a confirmation

**Status:** pre-registered.

**Rationale:** RSI is usually used to confirm other signals rather than as a stand-alone rule. The
primary variant therefore does not test a hard filter. It measures how much information RSI adds to
a signal that already exists.

**Definition:** Wilder's RSI(14), canonical 70/30 thresholds, never optimised. RSI is a normalised
momentum oscillator: RSI = 50 + 50·(G − L)/(G + L), where G and L are Wilder averages of gains and
losses.

**Two opposite readings, one test.** The common reading is **mean reversion**: a high RSI supports
shorts and a low RSI supports longs. The opposite reading is **momentum**: a high RSI supports longs,
because strong moves in crypto can persist. The test is two-sided, so it can tell the two apart
without spending an extra trial.

| Variant | What it measures |
|---|---|
| H3.0, confluence (primary) | Over the H1 and H2b events, RSI signed by trade direction: s = 50 − RSI for longs and s = RSI − 50 for shorts. **Hypothesis:** the slope of the normalised forward return against s is non-zero. A positive slope supports the mean-reversion reading; a negative one, the momentum reading. Reported together with a zone table: supportive (s > 20), neutral, opposing (s < −20). |
| H3.1, higher-timeframe RSI | Same as H3.0, using the RSI of the regime timeframe. |
| H3.2, hard veto | RSI > 70 vetoes longs and RSI < 30 vetoes shorts. **Evaluated only if H3.0 or H3.1 yields a positive slope:** if RSI carries no information, turning it into a rule cannot help. Measured as an ablation (with and without the veto), reporting the fraction of events kept. |

**Statistics:** the slope is estimated by regression, with a block-bootstrap confidence interval,
stratified by R0.

**Design issues that are measured, not assumed:**

- **Little variation within TD Sequential.** A sell setup 9 usually coincides with a high RSI, so
  within the H1 events the signed RSI may barely vary. If so, H3.0 on H1 is declared
  **inconclusive** rather than rejected, and the test relies on H2b.
- **Conflict with the trend.** In an uptrend, RSI spends long stretches above 70, so the
  mean-reversion reading would penalise exactly the longs that follow the trend. That is why results
  are stratified by R0.

**Phase 4:** the most faithful form of a non-decisive confirmation is RSI as a feature of the
meta-model, where its weight is learned and the calibrated probability decides. H3.0 tells whether
it is worth including.

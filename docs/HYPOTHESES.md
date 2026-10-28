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

- **Warm-up:** an indicator is undefined until its lookback is filled. That means 200 bars for
  EMA(200), 220 for its 20-bar slope and 14 for ATR(14); the volatility tercile needs at least 180
  daily bars in its window. Events whose R0 is undefined are excluded.

### Forward-return horizons

Counted from the open of the bar after the event: in practice, the first traded 1-minute open at
or after the event bar's close, because zero-volume bars are untradable (PROTOCOL §6). Exits are
taken the same way. Returns are divided by the event bar's ATR(14) as a fraction of its close.

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

### Breakdown by asset

Every result is also reported separately for BTC, for ETH and for the remaining assets, as a point
estimate with its bootstrap interval and no p-value. BTC and ETH are the two most liquid assets
and the cheapest to trade, so an effect pooled across the universe may not hold for them. The
breakdowns only describe where an effect comes from: they decide nothing and enter no FDR family.

---

## H1: TD Sequential anticipates exhaustion

**Status:** rejected in all 54 cells, before the hold-out (26 October 2026;
[RESULTS.md](RESULTS.md)).

**Definition** (the canonical version in J. Perl, *DeMark Indicators*, 2008; any other version is a
variant):

- **Sell setup:** 9 consecutive closes with C[t] > C[t−4], preceded by a bullish price flip
  (C[t−1] < C[t−5] on the bar before bar 1). The buy setup is symmetric.
- **Perfection (sell):** the high of bar 8 or bar 9 is ≥ the highs of bars 6 and 7.
- **Sell countdown:** starting from the completed setup, count bars (not necessarily consecutive)
  with C ≥ the high two bars earlier, up to 13. The high of bar 13 must be ≥ the close of countdown
  bar 8. Cancellation rules follow the reference.

**Reading of the reference,** fixed before the test. It is written for the buy side, and the sell
side mirrors it. The true high and true low of a bar extend its high and low to the previous close.

- A setup's count continues past 9 while the sequence holds, and only a new price flip starts
  another setup, so each setup gives one setup-9 event. Perfection counts bars 8 and 9 only: the
  later perfection that the reference allows is not an event.
- The countdown starts on setup bar 9, inclusive. A bar that qualifies as 13 but fails the bar-8
  condition is deferred, and the 13 falls on the first later bar that meets both conditions.
- A developing buy countdown is erased when a sell setup reaches 9, or when a bar's true low is
  above the highest true high of the setup that started it (TDST). The four bars before the setup,
  whose inclusion the reference describes as under study, are left out.
- A new buy setup that completes during the countdown restarts it from its bar 9 if its true range
  is at least that of the active setup, measured over all of that setup's bars, and less than
  1.618 times it. Otherwise no rule applies and the count continues. The reference states this
  for a smaller setup nested in the active one, and its upper bound keeps larger setups from
  restarting the count.
- A buy setup that reaches 18 bars during the countdown restarts the countdown on that bar.

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

**Status:** rejected in all cells of H2a and H2b, before the hold-out (27 October 2026;
[RESULTS.md](RESULTS.md)).

**Swings:** causal ATR ZigZag. A pivot is confirmed once price reverses by k·ATR(14) from the
extreme, and it stores its `confirmed_at`. Two registered variants: k = 2 and k = 3. The ZigZag
uses bar highs and lows and the ATR of the extreme's bar. A bar that sets a new extreme cannot also
confirm it, because the order of its high and low is unknown.

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
- **Statistic:** for each level L, the share of retracements in [L − 0.02, L + 0.02] minus the
  mean share of the two adjacent windows of the same width, [L − 0.06, L − 0.02) and
  (L + 0.02, L + 0.06]. A retracement is dated at the confirmation of C, and counts only if its
  symbol is in the universe that month.
- **Tests:** null 1 is a calendar-month block bootstrap of that excess, one-sided. For null 2, each
  symbol's bars are rebuilt from blocks of 24 consecutive bars drawn with replacement, keeping each
  bar's open, high, low and close relative to the previous close. Twenty such series go through
  the same ZigZag, and their mean excess is subtracted before the same bootstrap. A cell must
  reject both nulls, so its p-value is the larger of the two.
- **Criterion:** confirmed in a cell if it survives FDR and is stable (PROTOCOL §7).

### H2b: Tradable. Does touching a level anticipate continuation?

This part is causal: an impulse starts at a confirmed pivot and ends at the extreme reached so far.

- **Event:** while the R0 trend agrees with the impulse, price touches level r of the current
  impulse.
- **Impulse** (amended before any test, 27 October 2026): the up impulse runs from the last
  confirmed low A to the highest high since, up to the previous bar; B does not need to be
  confirmed. The down impulse mirrors it. The R0 trend decides which one can produce events. The
  original wording took the last confirmed impulse, with B confirmed. Measured on impulse lengths
  alone, before any test, B's confirmation (a reversal of k·ATR) has already crossed level 0.382
  in 79 % of impulses, 0.5 in 60 % and 0.618 in 42 %, at both k and both timeframes. The touches
  left would come from long impulses only, in a different mix for each level.
- **Touch:** the first bar whose low reaches the level (whose high, for a down impulse), unless it
  also sets a new extreme. Each level counts once per impulse, and a new extreme or a newly
  confirmed pivot starts a new impulse. The event is dated at that bar's close, and its direction is
  the impulse's.
- **Hypothesis:** the forward return in the impulse direction is higher after touching a Fibonacci
  level than after touching the control levels {0.45, 0.55, 0.70}.
- **Statistic:** the mean event-minus-baseline return (ENGINE.md §5) of the Fibonacci touches minus
  that of the control touches, both pooled and bootstrapped jointly by calendar month, one-sided,
  at the common horizons. The control levels are deeper on average (0.567 against 0.5). The pairs
  0.382/0.45, 0.5/0.55 and 0.618/0.70 are reported as a description.
- **Criterion:** Fibonacci must beat the neighbouring levels, not just random times. A pullback
  bouncing within a trend says nothing specific about Fibonacci. Confirmed in a cell if the
  difference survives FDR, the Fibonacci touches clear the economic threshold, and the difference
  is stable.

**Timeframes:** 1h and 4h.

**Families:** FDR is controlled separately for H2a and for H2b (Benjamini-Hochberg, q = 0.05).
H2a: 3 levels × k ∈ {2, 3} × 2 timeframes = 12 cells. H2b: k × timeframe × 3 horizons = 12 cells.

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

**Specification,** fixed before the test (28 October 2026):

- **Events:** H1 setup 9 and countdown 13 at 1h, 4h and 1d, and the H2b Fibonacci touches with
  k = 2 at 1h and 4h, one event per bar. The perfected setup, a subset of setup 9, is left out.
  Buys and sells are pooled, since s already carries the direction.
- **Response:** the event-minus-baseline forward return (ENGINE.md §5) at the common horizons.
- **Slope:** least squares of the response on s, both demeaned within each R0 cell, so that only
  events in the same regime are compared. Its interval and two-sided p-value come from the
  calendar-month block bootstrap. It is reported per 10 RSI points.
- **H3.1:** the RSI of the next timeframe up, as of the event's close: 4h for 1h events and 1d for
  4h events. Daily events have no H3.1.
- **Inconclusive:** a cell where s has a standard deviation below 5 RSI points across its events.
  Measured before the test on the RSI at the events alone, it is about 8 in H1 and 9 in H2b. No H1
  event has s below −20, so the opposing zone of the table stays empty for H1.
- **Criterion:** a slope is confirmed in a cell if it survives FDR and is stable (PROTOCOL §7); its
  sign gives the reading. H3.0 and H3.1 measure information, not a trade: the economic threshold
  applies to H3.2.
- **Families:** FDR is controlled separately for H3.0, with 24 cells (2 H1 signals × 3 timeframes
  × 3 horizons, and H2b × 2 timeframes × 3 horizons), and for H3.1, with 18.

**Phase 4:** the most faithful form of a non-decisive confirmation is RSI as a feature of the
meta-model, where its weight is learned and the calibrated probability decides. H3.0 tells whether
it is worth including.

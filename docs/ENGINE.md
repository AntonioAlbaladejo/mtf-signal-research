# Engine

**Date:** 25 October 2026 · **Phase 2.** Everything a pre-registered test needs except the signals
themselves: bars, alignment, indicators, regime, costs, trade simulation, event studies,
statistics and the trial registry. Each part states what it guarantees and how that is checked.

---

## 1. Bars and alignment

- **Bars** (`src/bars.py`): 15m, 1h, 4h and 1d bars are built from 1-minute klines, aligned to
  UTC like Binance's native klines and indexed by **close**. `tradable` is false for a bar without
  volume, and `minutes` exposes partial bars at a listing.
- **Checked against an independent source.** Binance's native daily klines were compared over
  159,287 symbol-days. OHLC match exactly on all but 18 days, which fall on dates shared by many
  symbols. Volume differs on 731 days, by a median of 0.04 %. The largest gaps cluster on
  2023-09-19 to 09-21, when the 1-minute archive holds up to 2.8× the native daily volume, and on
  2023-11-10 for BTCUSDT. That day, native volume is 12 % above the 1-minute sum, which makes the
  99-minute BTC stall in DATA.md §3 more likely to be missing 1-minute data than a halt. The
  simulator treats those minutes as untradable either way.
- **Alignment** (`asof`): joins across timeframes are as-of on the close. Test: a 15m bar closing
  at 10:15 sees the 4h bar that closed at 08:00, never the one still forming.

## 2. Indicators, regime and causality

- **Indicators** (`src/indicators.py`): EMA, Wilder's average, ATR and RSI, seeded at the first
  value and null until their lookback is filled.
- **R0** (`src/regime.py`): the pre-registered regime: 4h trend (close against a rising or
  falling EMA(200)) × 1d volatility tercile (ATR(14)/close within its trailing 365 days, at least
  180). Its warm-up excludes 141 of 740 universe symbol-months before the hold-out. 53 of them
  are in 2020, when every contract was young; the other 88 are coins in their first 180 days
  after listing, about one or two of the ten slots a month. Hypothesis tests therefore exclude the
  freshest listings, and the results speak only for assets with at least six months of history.
- **Future-invariance test** (`tests/causality.py`): it scrambles every bar after a random cut,
  recomputes and requires identical values up to the cut. Every indicator and R0 pass it. A
  feature that peeks one bar ahead makes it fail, which checks the checker.

## 3. Costs

`src/costs.py` prices every fill with Hyperliquid's own data (PROTOCOL §6). The source is the
archive's asset contexts: one row per coin and minute since 2023-05-20, with the mid, the funding
rate and the impact prices, kept per minute and aggregated to hours by `src.hyperliquid ctx`.
The archive lacks 2026-07-08, inside the hold-out, and 301 scattered hours before it (1.2 %).
Like `scan()`, `costs.hourly()` and `costs.at_minute()` serve nothing from the hold-out.

- **Fees:** taker, 0.045 % per side (base tier). The maker fee (0.015 %) waits for maker
  execution in phase 5.
- **Slippage:** half the spread between the impact bid and ask at the fill's minute, i.e. the
  average cost of a market order of 20,000 USDC on BTC and ETH and 6,000 USDC elsewhere. If that
  minute is missing, the hour's median stands in. The archive writes zero prices before a listing,
  after a delisting and when the book cannot fill the impact notional; those minutes are dropped.
  A minute stamped twice keeps its first snapshot. `at_minute` reads only the days that have fills.
- **Funding:** the settlements over the holding period. They are Hyperliquid's hourly rates when
  the coin was listed there for the whole trade, and Binance's otherwise.
- **Symbol mapping** (`uv run python -m src.costs`): a Binance symbol takes a Hyperliquid coin
  only if their hourly prices agree within 2 % (median ratio, at least 24 hours of overlap). The
  plain ticker and the `k` and `1000` forms are tried with their price factors, and a same-ticker
  token with another price fails the check. 68 of the 105 universe symbols map, all within 0.1 %
  of Binance's price. From June 2023 to the hold-out they cover 325 of 340 universe
  symbol-months, 312 of them listed for the whole month; the other 15 belong to 12 coins never
  listed on Hyperliquid.
- **Fallbacks:** an hour without Hyperliquid data uses the symbol's median slippage, and a symbol
  never listed uses the upper quartile of those medians, 3.6 bps. Before 2023-05-20 every fill
  uses them, with Binance's funding.

Measured slippage, median per fill in basis points (2026: January to March):

| | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| BTC | 2.13 | 0.16 | 0.05 | 0.07 |
| ETH | 2.22 | 0.30 | 0.18 | 0.24 |
| Mapped coins, median | 2.32 | 1.45 | 2.25 | 3.48 |
| Mapped coins, 90th percentile | 7.54 | 4.57 | 6.18 | 11.14 |

A market round trip on BTC costs about 9.2 bps, almost all of it fees; slippage matters on the
thinner coins. Funding averages about 9 % a year paid by longs on the median coin (15 % on BTC),
which counts for trades held over days.

**Why the minute and not the hour.** Fills are not spread at random: entries come right after a
bar's close, often after a large bar, and stops fire in fast minutes, when the book is thinner.
Over 52 days sampled before the hold-out (3.8 million coin-minutes), mean slippage in basis points
per fill:

| | Hour's median | First minute after an hour in its top decile of range | Minutes in the top 1 % of moves |
|---|---|---|---|
| BTC | 0.82 | 1.05 (hour's median: 0.93) | 1.90 (hour's median: 0.86) |
| ETH | 0.95 | 0.62 (0.45) | 1.45 (0.67) |
| Other mapped coins | 5.42 | 5.48 (4.32) | 8.98 (6.41) |

On BTC and ETH the difference is small next to the fees. On the other coins, the hour's median
would undercharge a trade that ends at its stop by about 3-4 bps.

## 4. Trade simulation

`src/backtest.py` walks each trade on 1-minute bars:

- **Entry** at the first traded open at or after the decision time.
- **Exit** at the first of the stop, the target or the time limit. A stop and a target in the same
  minute count as the stop. A stop crossed during untraded minutes fills at the next traded open,
  gap included. A target fills at its price, never better.
- **Costs:** taker fees on both sides, slippage at entry and at exit, and funding over the
  holding period.
- **Daily returns** use equal risk per trade, so that a stop-out costs the same fraction of
  equity. Returns are booked on the exit day; marking open trades to market becomes worth it once
  strategies hold for days.

## 5. Event studies

`src/events.py`:

- **Candidates:** every tradable universe bar of a timeframe, with its R0 cell and its forward
  returns in ATR units, from the first traded open after the close to the first traded open h
  bars later (HYPOTHESES.md horizons). Before the hold-out: 428,697 bars at 1h, 107,177 at 4h and
  17,864 at 1d, over 69 symbols, from 2020-07-12.
- **Baseline:** for each event, the mean forward return of its stratum (symbol × R0 cell). That is
  the exact expectation of a matched random entry (PROTOCOL §5), with no Monte Carlo noise. The
  stratum includes the event bars themselves, which pulls the effect slightly towards zero; this
  is conservative and negligible for sparse signals.
- **Inference:** the event-minus-baseline differences are bootstrapped by calendar month, jointly
  across assets (PROTOCOL §7). Stability is reported as the share of years and of assets whose
  mean has the sign of the overall effect. The breakdown for BTC, ETH and the remaining assets
  (HYPOTHESES.md) gives each group's effect and interval, with no p-value.
- **Tests:** buying in an up-trending regime shows no effect, because the regime's drift is not
  mistaken for a signal. A planted effect of 0.5 ATR is recovered with p < 0.01.

## 6. Statistics

`src/stats.py`: calendar-block bootstrap, Benjamini-Hochberg FDR, Sharpe, Sortino, Calmar, maximum
drawdown, and the probabilistic and deflated Sharpe ratios.

**Calibration**, on synthetic events that share a monthly shock (70 months, 10 events each):

| Resampling | Rejections without an effect (nominal 5 %) |
|---|---|
| Calendar blocks (this engine) | 5.5 % over 200 seeds |
| Events as independent | 22 % over 100 seeds |

A planted effect of 0.5 standard deviations is detected in at least 45 of 50 seeds, with the true
value inside the 95 % interval in at least 42. The second row is why PROTOCOL §5 and §7 were
amended before any test.

## 7. Trial registry and the hold-out

`research/trials.jsonl` is append-only and committed. Every run is stamped with its configuration
hash, the commit it ran on and whether the tree had uncommitted changes, so a logged result can
always be traced to code in the history. `scan(..., unseal_for="H1")` logs the access and refuses a
second one for the same family.

## 8. Validation on real data

Both validations are logged in `research/trials.jsonl`, run on commit `da6b31f` with a clean tree.
A first attempt on `7b9abf1` stopped with an error before logging anything: a minute holding two
Hyperliquid snapshots duplicated a fill. `da6b31f` fixes it.

**Random entries** (`backtest random`, 20,000 draws, seed 0): random universe members at random
1h closes, in a random direction, with stop and target at 2 ATR(1h) and a 24-hour limit. 19,990
trades completed; the rest ran past the data.

| Per trade | Mean |
|---|---|
| Gross | −0.04 bps (95 % interval −6.0 to +5.3, p = 0.99) |
| Costs | 12.5 bps: 9.0 of taker fees, 3.5 of slippage and funding |
| Net | −12.6 bps |

Gross is indistinguishable from zero and net is minus the costs, which is what PROTOCOL §6
requires of the cost model. Exits split into 8,641 targets, 8,595 stops and 2,754 time limits, as
symmetric brackets should. Net is negative in every year; costs peak in 2023 at 15.2 bps, when
Hyperliquid's books were thinnest.

**Random events** (`events random`, 5,000 random candidates per timeframe in a random direction,
seed 0): no effect at any of the nine horizons. The p-values range from 0.24 to 0.98, every
interval contains zero, and the shares of years and assets that share the effect's sign hover
around one half, as noise should. The BTC and ETH breakdowns contain zero too, with intervals
about three times wider than the pooled one, as their share of the events predicts.

## 9. Known limits

- Daily returns are booked at exit rather than marked to market.
- Hourly funding is the hour's last published estimate, which approximates the settled rate.
  Hours missing from the Hyperliquid archive add no funding.
- Slippage is the impact half-spread for 20,000 USDC (BTC, ETH) or 6,000 USDC (others). That is
  conservative for small orders and not valid for larger ones.
- Fills are priced at Binance's 1-minute prices plus Hyperliquid's slippage. Three gaps to live
  execution remain unmodelled: the price gap between the venues (a few bps, mostly the USDC/USDT
  rate; DATA.md §5), the latency between a bar's close and the order, and the book's changes
  within the minute. Phase 5 measures them on the recorded book.
- Before 2023-05-20, costs use each symbol's median Hyperliquid slippage (PROTOCOL §6), which the
  deeper books of 2024-2026 dominate: 0.09 bps on BTC, against 2.1 bps in 2023. Liquidity was
  thinner then, so net results for 2020-2023 are optimistic; the subperiod from 2023-05-20 is
  reported separately.
- Exit policies X2 (ATR trailing) and X3 (moving-average cross) come with phase 3; maker
  execution comes with phase 5.

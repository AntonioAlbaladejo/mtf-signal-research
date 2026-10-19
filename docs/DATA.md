# Data

**Date:** 18 October 2026. Everything here was measured on the data itself. To reproduce, run
the commands in the README.

---

## 1. Binance USDⓈ-M (signal research)

| | |
|---|---|
| Source | `data.binance.vision`, monthly archives: 1d and 1m klines, funding rates |
| Integrity | Every zip is checked against its published SHA-256 before it is converted |
| Coverage | 899 USDT-quoted perpetuals ever archived, including 31 that no longer trade; 2020-01 to 2026-09 |
| Layout | `data/binance/um/<dataset>/<SYMBOL>/<YYYY-MM>.parquet`, generated and never committed |

Format details that the ingestion handles explicitly:

- **Time convention.** `open_time` is the bar open, and `time` is the bar **close**, computed as
  `open_time + interval`. Binance's own close stamp (`open + interval − 1 ms`) is dropped.
  Research joins on `time` (PROTOCOL §4).
- **Headers.** Older kline files have no header row; newer ones do.
- **Dtypes are fixed, not inferred.** A month that starts with integer volumes would otherwise be
  read as integers and break later on a decimal value. It happened on SOLUSDT 2025-04.
- **Timestamps** are milliseconds. Binance moved its spot archives to microseconds in 2025, so
  microsecond values are detected and normalised in case futures follow.
- **Non-ASCII symbols** exist (for example `币安人生USDT`), so archive paths are URL-encoded.
- **Funding** comes with its settlement interval (`interval_hours`), which is not always 8 h.
- **Some monthly files are truncated** and are completed from the daily archives (§3).

## 2. Point-in-time universe

Each month, the top 10 by trailing 30-day quote volume, ranked on the daily bar that closes at the
month boundary (FOUNDATIONS §7). Only USDT-quoted crypto perpetuals are considered:

- **Excluded by name:** quarterly contracts, and stablecoin bases (USDC, BUSD, TUSD, FDUSD, DAI,
  USDP, USDE).
- **Excluded by Binance's contract metadata:** index perpetuals (`underlyingType = INDEX`), and the
  **TradFi perpetuals** on stocks, commodities and FX (`contractType = TRADIFI_PERPETUAL`), listed
  since 2025-12-11. Without this rule, gold, crude oil and several equities would have entered the
  universe by 2026-10.
- **Delisted contracts** are absent from the metadata. They are kept as crypto only if they started
  trading before the first TradFi listing; otherwise the build fails instead of guessing. All 32
  absent contracts qualify. Two of them, `FOOTBALLUSDT` and `BLUEBIRDUSDT`, look like index
  contracts by name, but neither ever ranked in the top 10.

Result: 81 months (2020-02 to 2026-10), **105 distinct symbols**. BTC and ETH are present every
month; most of the others enter for a handful of months. Five members later stopped trading:
YFII, LUNA (May 2022), MATIC (renamed POL, September 2024), EOS and SXP. Keeping such members is
exactly what the point-in-time rule is for: a universe built from today's listings would leave
them out and bias every result towards survivors.

## 3. Data quality (1-minute klines)

Produced by `uv run python -m src.quality` over all 105 universe symbols, for every month each one
traded, not only its universe months: 229.5 million bars.

| Check | Result |
|---|---|
| Duplicated bars | 0 |
| Inconsistent bars (high < open/close, low > open/close, low ≤ 0) | 0 |
| Missing minutes | **0**, after the backfill below |
| Zero-volume bars inside universe months | 0.033 % overall; the highest is XTZ, at 0.77 % |

**Truncated monthly files.** The first run found two gaps, and both were archive artefacts.
About half of the symbols then listed (25 of 54, alphabetically from FIL to ZIL) are missing
2022-02-26 to 02-28 in their monthly file. Nearly the same set (26 of 56) is missing 2022-04-01 to
04-02. The daily archives
have those days, so `src.binance backfill` merges them in, checksum-verified. Each monthly file is
rewritten by a single task, because two concurrent rewrites of the same file corrupted it in a
first attempt.

**Outages are padded, not missing.** The archive fills exchange outages with flat zero-volume bars
instead of leaving gaps, so they look like real prices. `src.quality` reports every run of at
least 5 zero-volume bars as a *stall*. A stall is classed as market-wide when, at its first minute,
at least half of the symbols trading are inside one. Market-wide stalls:

| Start (UTC) | Longest (min) | Symbols affected |
|---|---|---|
| 2020-09-27 11:17-11:25 (staggered) | 15 | 12 |
| 2021-03-02 01:01 | 59 | 43 |
| 2022-05-01 22:26 | 29 | 55 |
| 2022-05-28 16:40 | 35 | 54 |
| 2023-09-12 08:34 | 19 | 67 |
| 2024-10-28 16:21 and 20:00 (two events) | 75 | 81 |
| 2025-01-29 01:23 | 13 | 80 |
| 2025-08-29 06:18-06:19 | 19 | 87 |

The 2020-09-27 event starts over several minutes (11:13 to 11:25), so its earliest stalls fall
below the threshold. Inside
universe months, the stalls that are not market-wide add up to 1,149 minutes:

- the LUNA halt during its collapse: 2022-05-12, 917 minutes;
- BTCUSDT alone, 2023-11-10 15:07: 99 minutes, which the data does not explain;
- the rest of the 2020-09-27 event;
- runs of 5-11 minutes in thin early-2020 markets (XLM, TRX, XTZ).

**Consequence for research.** A zero-volume bar is not a price observation that a strategy can
trade on. PROTOCOL §6 makes such bars untradable.

**Funding.** 573,615 settlements, with intervals of 1, 2, 4 and 8 hours that change over time. Every
step between settlements matches the previous or the new interval, with two exceptions:

- 11 single-symbol realignments to a new interval grid;
- one missed market-wide settlement, at 04:00 on 2026-06-24, for 44 symbols on 4-hour funding.
  It falls inside the hold-out.

## 4. Hyperliquid archive (execution)

Measured by downloading and decoding archive files on 2026-10-18:

| | `hyperliquid-archive` | `hl-mainnet-node-data` |
|---|---|---|
| Content | L2 snapshots per coin and hour (`market_data/<date>/<hour>/l2Book/<coin>.lz4`) | All fills with aggressor side, all coins in one file per hour (`node_fills_by_block/hourly/`) |
| Cadence | One snapshot every ≈5.4 s (median 5,389 ms, range 4.9-5.6 s, BTC) | Every fill |
| Depth | 20 levels per side | n/a |
| Since | 2023-04-15 | 2025-07-27 |
| Freshness | The previous day is available | The previous day is available |
| Size | ≈240 KB per hour for BTC (lz4) | 40-60 MB per hour (lz4) |
| Region | us-east-1 | ap-northeast-1 |

Both buckets are requester-pays, so downloads are billed to the caller's AWS account. Raw files
are cached under `data/hyperliquid/` so each one is paid for once. At these sizes, a year of hourly
snapshots for the 10 universe members is in the tens of GB, and a week of fills is about 8 GB.

This is what settled D-08: a 5-second, 20-level book is enough to model spread and slippage, so
nothing is recorded in-house.

## 5. Venue gap: Hyperliquid versus Binance

The Hyperliquid mid is compared with the Binance 1-minute close at every close. The mid comes from
the last snapshot at or before the close, at most 10 s old. The sample is one hour (00:00-01:00
UTC on the 15th) per month, from 2023-05 to 2026-03, so it is entirely before the hold-out.

| Coin | Minutes | Median gap (bps) | 5th pct | 95th pct | Mean \|gap\| | Median HL spread (bps) |
|---|---|---|---|---|---|---|
| BTC | 2,050 | +3.0 | −1.0 | +12.5 | 4.2 | 0.15 |
| ETH | 2,050 | +2.7 | −2.3 | +11.2 | 3.8 | 0.38 |
| SOL | 2,050 | +3.0 | −2.7 | +12.0 | 4.4 | 0.70 |

| Year | Median gap, BTC / ETH / SOL (bps) | Median HL spread, BTC / ETH / SOL (bps) |
|---|---|---|
| 2023 | +2.4 / +2.3 / +2.1 | 2.38 / 2.71 / 3.20 |
| 2024 | +5.4 / +3.2 / +6.2 | 0.16 / 0.35 / 0.69 |
| 2025 | +3.1 / +2.6 / +2.6 | 0.10 / 0.33 / 0.62 |
| 2026 (to March) | +0.5 / +1.0 / −0.2 | 0.14 / 0.48 / 0.11 |

The Hyperliquid spread narrowed by an order of magnitude after 2023.

How to read it:

- **The gap is not a pure venue effect.** Hyperliquid settles in USDC and Binance in USDT, so it
  includes the USDC/USDT rate, plus up to ≈5 s of snapshot age and any difference in perpetual
  premium. Its drift by year is consistent with a varying stablecoin rate, but that is not tested
  here.
- **Consequence for research.** Signals are defined on Binance in relative terms (returns, ATR
  multiples), never as absolute price levels carried across venues. Costs and fills are always
  modelled on Hyperliquid. A typical gap of a few bps is small next to ATR-scale moves, but it is the
  same order as one taker fee (4.5 bps), so it matters for any edge measured in single bps.

## 6. Freeze and hold-out

The research dataset was frozen on **2026-10-18**: Binance monthly archives up to 2026-09.
The hold-out runs from **2026-04-01 to 2026-09-30** and is sealed. `src.data.scan()` never serves
it, and unsealing is refused until the trial registry exists (PROTOCOL §3). Data published after
the freeze is forward data.

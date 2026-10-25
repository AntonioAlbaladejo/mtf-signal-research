# Project foundations

**Date:** 17 October 2026 · **Status:** phase 0 (foundations).
**Related:** [PROTOCOL.md](PROTOCOL.md) (research rules) · [HYPOTHESES.md](HYPOTHESES.md)
(pre-registration).

This document fixes **what** is built and **why**. The rules for **how** research is done live in
PROTOCOL.md and take precedence: if anything here conflicts with the protocol, the protocol wins.

---

## 1. Purpose

A research platform for systematic trading of crypto perpetual futures, built around
multi-timeframe decisions, with the order book used as an execution tool.

The goal is to find out, rigorously, whether a robust long-term edge exists for systematic trading,
and to explore new research avenues along the way. **Profitability is a hypothesis, not a premise.**
If after phase 3 nothing beats a cost-adjusted random baseline, that is the result, and it is
documented as such. A methodology that explains why most strategies fail is worth more than an
equity curve nobody can audit.

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| D-01 | **Profitability is tested, never assumed** | Every claim is net of costs, measured against a matched null, with every trial counted (PROTOCOL). |
| D-02 | **Live trading is gated** | Paper trading or testnet comes first, with acceptance criteria written *before* it starts. Minimal capital follows only if those criteria are met. |
| D-03 | **The data chooses the horizon** | Intraday (1-8 h holding) and swing (1-5 days) are both candidates. The horizon is a registered hyperparameter, compared at equal risk and selected on validation data (PROTOCOL §3, §8). |
| D-04 | **Execution venue: Hyperliquid perpetuals** | Open API with every order primitive needed (§6), and lower base fees than the large centralised venues. |
| D-05 | **Hybrid data** | Signals are researched on years of Binance USDⓈ-M history, covering several market regimes. Execution and costs are modelled on Hyperliquid. The price gap between the two venues is measured, not assumed. |
| D-06 | **Universe: top 10 by liquidity, point-in-time** | Enough events for statistical power without dropping into thin order books. Point-in-time membership avoids survivorship bias. |
| D-07 | **In-house backtester, built in phases** | A vectorised research layer (Polars/NumPy) comes first; most research happens there. The event-driven layer (NautilusTrader or an in-house C++ engine) is chosen when execution research starts. |
| D-08 | **Research runs locally; no own order-book recording** | Decided in phase 1, against the measured archive: Hyperliquid stores a 20-level snapshot every ≈5.4 s since April 2023. That is enough for spread and slippage modelling. Trades with their aggressor side are archived too (§7), and they are sampled for maker-fill studies in phase 5. No cloud compute is needed. The only cloud cost is the requester-pays download, a few euros at most. |
| D-09 | **Public repository from day one** | Commit timestamps are the evidence of pre-registration (PROTOCOL §1). If something ever works, its parameters live outside the repository. |
| D-10 | **Broad research agenda, with classical TA first** | The agenda (§4) spans trend, derivatives positioning, volatility, cross-section, microstructure and ML. Classical TA goes first because it can be defined precisely, is widely used, is rarely tested against proper nulls, and exercises the whole pipeline (causality, nulls, multiple testing). |
| D-11 | **Stack:** Python 3.12, uv, Polars, Parquet, pytest, ruff | Columnar and fast enough for several years of 1-minute data. Other libraries are added only when code needs them. |
| D-12 | **Language:** English for everything in the repository | |

## 3. Architecture: three layers, three questions

Calling the direction and timing the entry are different problems. Each layer answers its own
question and is evaluated separately.

| Layer | Timeframe | Question | Data |
|---|---|---|---|
| **Regime** | 4h / 1d | Should this asset be traded at all, and in which direction? | Candles, volatility, funding |
| **Setup** | 1h / 15m | Is there a concrete opportunity now? | Levels, moving averages, volume, oscillators |
| **Execution** | 1m / order book | When and how to enter and exit? | L2 book, trade flow |

**Filters** veto setups: they never propose a trade, they only discard one. They are evaluated as
ablations, comparing the same signal with and without the filter. **Confirmations** do not veto;
they add information. First we measure how much (see H3), and from phase 4 on their weight is
learned.

**The order book serves execution first, not prediction.** Entering as maker instead of taker cuts
the fee to a third, the largest cost lever available. The price is uncertain fills and adverse
selection (getting filled precisely when the price moves against you); both are measured. Using the
book as a standalone alpha source requires latency this project does not have.

## 4. Research agenda

When its turn comes, each family turns into pre-registered hypotheses in HYPOTHESES.md. Only family A
is pre-registered today.

| Family | Question | Status |
|---|---|---|
| **A. Classical TA** | Do TD Sequential, Fibonacci retracements and RSI confirmation carry information beyond a matched null? | Pre-registered (H1-H3) |
| **B. Trend and momentum** | Does time-series momentum hold at intraday and swing horizons, net of costs? Can trend filters be designed by their frequency response rather than tuned by trial and error? Moving averages are FIR/IIR filters with a known lag-versus-noise trade-off; Kalman filters estimate the trend directly. | Planned |
| **C. Multi-timeframe confluence** | Does a higher-timeframe regime filter improve lower-timeframe setups? Does agreement across timeframes add information beyond what each timeframe carries alone? | Planned: the core of the project |
| **D. Derivatives positioning** | Do funding rates, basis and open-interest dynamics (crowding) predict returns or reversals? | Planned |
| **E. Volatility** | Volatility clustering is among the most robust stylised facts. Does regime-aware volatility targeting improve the risk-adjusted returns of other signals? | Planned |
| **F. Cross-section** | Does relative strength across the universe persist at these horizons (cross-sectional momentum)? | Planned |
| **G. Microstructure for execution** | Do book imbalance, order-flow imbalance and the microprice improve entry timing and maker fill quality? | Phase 5 |
| **H. Meta-labelling** | Can a calibrated model combine the surviving signals and size positions better than hard rules? | Phase 4 |

Starting points in the literature, not claims about what will hold here:
- Moskowitz, Ooi & Pedersen (2012): time-series momentum.
- Liu & Tsyvinski (2021); Liu, Tsyvinski & Wu (2022): crypto return factors.
- Cont, Kukanov & Stoikov (2014): order-flow imbalance.
- Stoikov (2018): the microprice.
- López de Prado (2018): meta-labelling and purged cross-validation.
- Lo, Mamaysky & Wang (2000): formalising chart patterns.

## 5. Costs: why frequency is an outcome

| Venue (base tier) | Maker | Taker | Round trip, taker | Round trip, maker |
|---|---|---|---|---|
| Hyperliquid perps | 0.015 % | 0.045 % | 0.09 % | 0.03 % |
| Binance USDⓈ-M (reference) | 0.02 % | 0.05 % | 0.10 % | 0.04 % |

Slippage comes on top: half the spread between Hyperliquid's impact bid and ask prices at the
minute of the fill (PROTOCOL §6). So does funding, which Hyperliquid settles hourly.

The example that shapes everything: a strategy that wins 55 % of the time, with an average win and
loss of 0.5 %, expects 0.05 % gross per trade. That is less than a taker round trip. **"Several trades
a day" is not a design goal.** If it happens, it comes from breadth (a few signals on each of the 10
assets), not from frequency on a single one. Effective breadth is smaller than it looks, because
altcoins are strongly correlated with BTC. That is measured too.

## 6. Position management

### What the venue provides and what we build

Checked against the Hyperliquid API documentation (October 2026):

| Need | Native on Hyperliquid |
|---|---|
| Limit entry | Yes: GTC, IOC and **post-only (ALO)**, which guarantees a maker entry |
| Stop loss / take profit | Yes: market or limit trigger orders, reduce-only, attachable to the entry |
| Trailing stop | Yes: `trailingStop` action, by percentage or price, with an activation price |
| TWAP | Yes |
| Auto-cancel if the bot dies | Yes: `scheduleCancel` (≥ 5 s ahead, at most 10 triggers per day) |
| Exit on a moving-average cross; trailing a moving average or swing level | **No, on any venue: this is our own logic** |

### Principle: two layers of protection

1. **On the venue:** a native catastrophe stop is always in place. It protects the position even if
   the bot crashes, the network drops, or our own code fails.
2. **In our engine:** the sophisticated logic *moves* the native stop; it never replaces it.

A native trailing stop follows the mark price tick by tick, while a rule on closed candles only acts
at the close. They behave differently, and the backtest simulates whichever one is actually used.

### Closed menu of exit policies

Exits enlarge the search space as much as entries do. Until phase 4, only these policies exist. They
are evaluated as an ablation over **the same set of entries**:

| Id | Policy |
|---|---|
| X1 | Fixed SL and TP at ATR multiples |
| X2 | ATR trailing stop (chandelier style) |
| X3 | Exit on a moving-average cross at the setup timeframe |
| X4 | Time stop (N bars) |
| X5 | X1 + X4 combined |

Entries are studied through event studies; exits, over a fixed set of entries. **Entries and exits
are never optimised together** before phase 4.

## 7. Data

| Source | What | Used for |
|---|---|---|
| `data.binance.vision` (USDⓈ-M) | 1-minute candles, aggregated trades and funding since 2020, with checksums | Signal research: regime and setup across several market regimes |
| Hyperliquid archive on S3 (`hyperliquid-archive`, requester pays) | L2 snapshots (20 levels per side, ≈5.4 s apart, since 2023-04-15) and asset contexts | Spread and slippage. The archive is documented as **possibly incomplete**, and it holds no candles |
| Hyperliquid node data on S3 (`hl-mainnet-node-data`, requester pays) | Every fill with its aggressor side, in hourly files for all coins (≈1 GB/day, since 2025-07-27) | Maker-fill and adverse-selection studies, on sampled windows |

Hyperliquid candles are neither archived nor served by the API beyond a recent window. Mid prices
are taken from the snapshots instead. Measured details are in [DATA.md](DATA.md).

**Point-in-time universe:** each month, the top 10 by trailing 30-day quote volume on Binance,
ranked on the daily bar that closes at the month boundary. Only USDT-quoted perpetuals are
considered; quarterly contracts and stablecoin bases are excluded. A symbol with no bar on the last
day of the previous month cannot enter. For execution, the universe is intersected with the assets
listed on Hyperliquid on that date.

## 8. Phases and exit criteria

A phase is not closed until its exit criterion is met.

| Phase | Content | Exit criterion |
|---|---|---|
| 0. Foundations | This document, protocol, hypotheses | Documents in the public repository |
| 1. Data | Binance ingestion to Parquet; point-in-time universe; Hyperliquid archive measured; first venue comparison | Quality report with no unexplained gaps. Recording decision taken from the measured archive cadence (D-08). Dataset frozen and hold-out sealed |
| 2. Engine | Multi-timeframe bars and as-of alignment; base indicators and R0; Hyperliquid cost data and cost model; 1-minute trade simulator; event-study engine; trial registry; metrics | Future-invariance test passing on every feature. Multi-timeframe alignment tested. Bars match Binance's native daily klines. **Random entries ≈ −costs**, which validates the cost model. The bootstrap is calibrated: uniform p-values without an effect, and a planted effect recovered |
| 3. Hypotheses | Event studies for family A; multi-timeframe strategies with walk-forward; exit ablation | A written verdict per hypothesis; survivors confirmed once on the sealed hold-out |
| 4. ML | Meta-labelling: triple barrier, purged CV, calibration, SHAP | The calibrated model beats hard filters on validation, net of costs, or it is documented that it does not |
| 5. Execution | Maker versus taker on the recorded book | Implementation shortfall, fill rate and adverse selection measured |
| 6. Paper → capital | Testnet, then minimal capital | Acceptance criteria pre-registered before starting |

## 9. Risks and known limits

- **Costs** are the most likely cause of death for any strategy (§5).
- **Overfitting** is controlled by the protocol, not by more data.
- **Regime change:** what worked in 2021 may not work in 2026. Stability is assessed year by year.
- **Venue gap:** signals researched on Binance may not transfer 1:1 to Hyperliquid.
- **Platform risk:** a decentralised venue carries its own risks (contracts, oracles, tail liquidity).
- **Regulation and tax:** access and the tax treatment of each closed trade are checked before
  phase 6. Many trades will require automated bookkeeping.
- **Credentials:** the bot signs with an API (agent) wallet authorised by the main account, never
  with the main key. The key lives in a secrets manager, never in the repository. Its exact
  permissions are verified when the bot is set up.

## 10. Out of scope

Market making, high-frequency trading, LLM agents that make trading decisions, and model
fine-tuning.

# mtf-signal-research

Research platform for systematic trading of crypto perpetual futures: multi-timeframe signals,
order-book-aware execution, and a research protocol designed to tell a real effect from a lucky
backtest.

**Status:** phases 1 (data) and 2 (engine) complete; phase 3 (hypotheses) in progress. There is **no
claim of profitability**. Profitability is a hypothesis under test. If nothing beats a
cost-adjusted random baseline, that is the result, and it will be documented as such.

## Approach

- **Three layers, three questions.** Regime (4h/1d): should this asset be traded, and in which
  direction? Setup (1h/15m): is there a concrete opportunity now? Execution (1m + order book): when
  and how to enter and exit?
- **A broad research agenda.** Classical technical analysis goes first, followed by trend and
  momentum, multi-timeframe confluence, derivatives positioning (funding, open interest),
  volatility, cross-sectional effects, microstructure for execution, and ML meta-labelling.
- **Hybrid data.** Signals are researched on years of Binance USDⓈ-M history. Execution and costs
  are modelled on Hyperliquid's own archive: impact prices for every minute, hourly funding and
  order-book snapshots.
- **Pre-registration.** Every hypothesis is committed with its null, metric and decision rule before
  it is tested. Every trial is logged, so that the Deflated Sharpe Ratio can account for all of them.
- **Causality, enforced by tests.** Every feature must pass a future-invariance test. Joins across
  timeframes are as-of on the bar close. Swing pivots carry their confirmation time.

## Documents

- [docs/FOUNDATIONS.md](docs/FOUNDATIONS.md): decisions, architecture, research agenda, costs,
  phases and exit criteria
- [docs/PROTOCOL.md](docs/PROTOCOL.md): research protocol
- [docs/HYPOTHESES.md](docs/HYPOTHESES.md): pre-registered hypotheses
- [docs/DATA.md](docs/DATA.md): data sources, universe, quality and measured venue facts
- [docs/ENGINE.md](docs/ENGINE.md): bars, regime, costs, trade simulation, event studies,
  statistics, and their validation
- [docs/RESULTS.md](docs/RESULTS.md): the outcome of each pre-registered test

## Getting the data

Requires [uv](https://docs.astral.sh/uv/). The Hyperliquid archive also requires the AWS CLI with
credentials, because downloads are billed to the requester.

```bash
uv sync
uv run python -m src.binance klines/1d
uv run python -m src.universe
uv run python -m src.binance klines/1m --universe
uv run python -m src.binance fundingRate --universe
uv run python -m src.quality          # then fill any reported gaps:
uv run python -m src.binance backfill
uv run python -m src.quality
uv run python -m src.hyperliquid gap
uv run python -m src.hyperliquid ctx                 # Hyperliquid costs by hour and minute
uv run python -m src.bars                            # 15m, 1h, 4h and 1d bars
uv run python -m src.costs                           # Binance -> Hyperliquid symbol mapping
uv run python -m src.events candidates 1h            # also 4h and 1d
```

## Validating the engine

Both commands log their results in `research/trials.jsonl`.

```bash
uv run python -m src.backtest random      # random entries: ~0 gross, ~minus costs net
uv run python -m src.events random 1h     # random events: no effect (also 4h and 1d)
```

## License

MIT

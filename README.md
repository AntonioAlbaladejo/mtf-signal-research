# mtf-signal-research

Research platform for systematic trading of crypto perpetual futures: multi-timeframe signals,
order-book-aware execution, and a research protocol designed to tell a real effect from a lucky
backtest.

**Status:** phase 1 (data) complete; phase 2 (backtest engine) next. There is **no claim of
profitability**. Profitability is a hypothesis under test. If nothing beats a cost-adjusted random
baseline, that is the result, and it will be documented as such.

## Approach

- **Three layers, three questions.** Regime (4h/1d): should this asset be traded, and in which
  direction? Setup (1h/15m): is there a concrete opportunity now? Execution (1m + order book): when
  and how to enter and exit?
- **A broad research agenda.** Classical technical analysis goes first, followed by trend and
  momentum, multi-timeframe confluence, derivatives positioning (funding, open interest),
  volatility, cross-sectional effects, microstructure for execution, and ML meta-labelling.
- **Hybrid data.** Signals are researched on years of Binance USDⓈ-M history. Execution and costs
  are modelled on Hyperliquid order-book data: its archive snapshots, plus our own recording only if
  their cadence falls short.
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
```

## License

MIT

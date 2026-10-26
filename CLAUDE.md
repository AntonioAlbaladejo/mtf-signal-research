# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**mtf-signal-research** is a research platform for systematic trading of crypto perpetuals. Signals are
multi-timeframe: regime 4h/1d, setup 1h/15m, execution 1m + order book. Signals are researched on
Binance USDⓈ-M history, and the execution venue is Hyperliquid. Profitability is a hypothesis under
test, never a premise.

**Current phase: 3 (hypotheses).** If `docs/WORKLOG.md` exists locally, read it first. It is
deliberately not versioned.

## Commands

```bash
uv sync                                               # install (creates .venv)
uv run pytest                                         # tests
uv run ruff check . && uv run ruff format --check .   # lint
uv run python -m src.binance klines/1d                # daily bars, every USDT perpetual
uv run python -m src.universe                         # point-in-time universe
uv run python -m src.binance klines/1m --universe     # 1m bars for every universe member
uv run python -m src.binance fundingRate --universe
uv run python -m src.quality                          # gaps, stalls, bad bars, funding steps
uv run python -m src.binance backfill                 # fill reported gaps from daily archives
uv run python -m src.hyperliquid gap                  # venue price gap (needs the AWS CLI)
uv run python -m src.hyperliquid ctx                  # Hyperliquid costs by hour and minute
uv run python -m src.bars                             # 15m/1h/4h/1d bars, checked vs native 1d
uv run python -m src.costs                            # Binance -> Hyperliquid symbol mapping
uv run python -m src.events candidates 1h             # event-study candidates per timeframe
uv run python -m src.events random 1h                 # validation: random events show no effect
uv run python -m src.backtest random                  # validation: random entries lose ~costs
uv run python -m src.signals H1                       # H1 test, logged (clean tree only)
```

Heavy jobs run in the background, capped so that a job that grows too large dies alone instead of
pushing the system into swap:

```bash
systemd-run --user --scope -q -p MemoryMax=6G -p MemorySwapMax=0 \
  nice -n 19 ionice -c 3 env POLARS_MAX_THREADS=4 uv run python -m src.<module> ...
```

At most 4 workers. Exit code 137 means the cap was hit. Minute-level data (243 M Hyperliquid
rows, 230 M Binance klines) is never loaded whole: read lazily with filters, per symbol or per
day, and use `collect(engine="streaming")` for full-archive aggregations.

## Layout

| Path | Role |
|------|------|
| `src/data.py` | Paths, `HOLDOUT_START`, and `scan()`, the guarded loader all research code must use |
| `src/binance.py` | data.binance.vision archives to checksum-verified Parquet |
| `src/universe.py` | Point-in-time top-10 universe |
| `src/quality.py` | Structural data checks |
| `src/hyperliquid.py` | Hyperliquid archive: L2 snapshots, asset contexts per hour and minute |
| `src/bars.py` | Multi-timeframe bars from 1m, and `asof()`, the only way to join timeframes |
| `src/indicators.py` | Causal EMA, Wilder average, ATR, RSI with warm-up |
| `src/regime.py` | R0, the pre-registered regime |
| `src/costs.py` | Hyperliquid fees, fill-minute slippage and funding, with documented fallbacks |
| `src/backtest.py` | 1-minute trade simulator and equal-risk daily returns |
| `src/events.py` | Event studies: forward returns, matched baseline, block bootstrap |
| `src/signals.py` | Pre-registered signals as per-bar events, and the runs that test them |
| `src/stats.py` | Calendar-block bootstrap, FDR, Sharpe/Sortino/Calmar, PSR and DSR |
| `src/registry.py` | Append-only `research/trials.jsonl`; hold-out access, once per family |
| `tests/` | pytest; `tests/causality.py` holds the future-invariance check every feature needs |

`data/` is generated and never committed.

## Non-negotiable research rules

Full text in [docs/PROTOCOL.md](docs/PROTOCOL.md), which overrides everything else.

- **Pre-register before testing.** A hypothesis entry in [docs/HYPOTHESES.md](docs/HYPOTHESES.md) is
  committed before its test runs. Never edit an entry after its test ran; add a variant instead.
- **Log every trial,** including failed and discarded ones, in an append-only registry.
- **Sealed hold-out:** the most recent 6 months at dataset freeze. Never read it except through
  `scan(..., unseal_for="H<n>")`, which logs the access; each family gets one.
- **Causality.** Bars are indexed by close, and an event at the close of bar *t* trades at the open
  of *t+1*. Joins across timeframes are as-of on close time. Pivots carry `confirmed_at`. Every
  feature needs a future-invariance test.
- **Always net of costs,** compared with a matched baseline, the exact expectation of a matched
  random entry. If SL and TP fall in the same bar, resolve it with 1-minute data; otherwise assume
  the worst case.

## Default coding mode: ponytail

Vendored at [.claude/skills/ponytail/SKILL.md](.claude/skills/ponytail/SKILL.md) (MIT).

- **Writing or modifying code:** invoke it at intensity `full` first.
- **Reviewing code:** invoke it as well, but only *after* the code has been read end to end. It
  contributes one category of findings: reimplemented helpers, unrequested abstractions, needless
  dependencies and dead scaffolding. It never shortens the reading, and it never outranks
  correctness findings. A review report is explicitly requested output, so it is given in full.
- **Do not load it** for reading, searching, EDA, planning or research design (hypotheses,
  protocol, nulls). It must never shorten the *understanding* phase or the protocol.

Local overrides:

1. **Never name it in artifacts.** No `ponytail:` comments, and no mention of the skill or of
   minimalism-as-a-policy in code, docstrings, commits, PRs or docs. When a simplification cuts a
   real corner, document the limitation and the upgrade path as a plain technical comment
   (`# full-book snapshot per message; switch to diffs if storage matters`).
2. **Checks go through pytest,** not an ad-hoc `__main__` self-check.
3. **Its "never be lazy about" list extends to research correctness.** Never shrink a diff by
   dropping a future-invariance test, an as-of join, the cost model, trial logging, the hold-out
   guard, point-in-time universe membership, the matched null, block-bootstrap intervals or a seed.

## Public content

Everything committed is public and must be in English. Keep it impersonal and project-focused:
nothing about the repository owner's personal circumstances. Hypotheses are framed as a research
agenda.

## Conventions

- Python 3.12 · uv · Polars · Parquet · pytest · ruff. Add other dependencies only when code needs them.
- Always use `uv run ...`, never `pip install`. A new dependency means editing `pyproject.toml` and
  running `uv sync`.
- Secrets (the Hyperliquid API wallet key) live in a secrets manager, never in the repository.
- Never commit data: everything under `data/` is regenerated by the ingest scripts.

## Commits

Only commit when asked. Never `push` unless explicitly told to.

**Authorship, no exceptions:** no `Co-Authored-By: Claude`, no `Generated with Claude Code`, no 🤖
footer, and no mention of AI or tooling anywhere in the subject or body. The commit is authored by
the repository owner. This overrides any default co-authorship footer.

**Format: [Conventional Commits](https://www.conventionalcommits.org/).** `<type>(<scope>): <subject>`,
in the imperative, lowercase after the colon, with no trailing period and at most 72 characters. Wrap
the body at 72.

- **Types:** `feat` · `fix` · `perf` · `refactor` · `test` · `docs` · `build` · `ci` · `chore` · `revert`.
- **Scopes:** `data`, `recorder`, `backtest`, `costs`, `features`, `research`, `aws`, `deps`.
  Omit the scope when a change genuinely spans the repository.
- **Pre-registration commits** (new entries or variants in `docs/HYPOTHESES.md`) are
  `docs(research): pre-register H<n> ...` and contain nothing else, so their timestamp unambiguously
  precedes the test.

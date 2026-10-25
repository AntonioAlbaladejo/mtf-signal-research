"""1-minute trade simulator (PROTOCOL §4, §6).

A trade enters at the first traded 1m open at or after its decision time, and exits at the first
of its stop, its target or its time limit. Zero-volume bars are untradable, so a stop crossed
during an outage fills at the next traded open. If the stop and the target fall in the same
minute, the stop wins. Costs: taker fees on both sides, Hyperliquid slippage and funding.

    uv run python -m src.backtest random     # random entries must lose about their costs
"""

import argparse

import numpy as np
import polars as pl

from src import costs, registry
from src.data import scan
from src.indicators import atr
from src.stats import bootstrap_test
from src.universe import UNIVERSE

RESULT = ["entry_time", "entry", "exit_time", "exit", "reason"]


def walk(trades: pl.DataFrame, m1: pl.DataFrame) -> pl.DataFrame:
    """Entry and exit of each trade on one symbol's 1m bars.

    `trades`: time (decision), direction (±1), stop and target (fractions of the entry price;
    target may be null), hold (minutes). Trades that run past the data are dropped.
    """
    m = m1.filter(pl.col("volume") > 0).sort("open_time")
    t = m["open_time"].dt.epoch("ms").to_numpy()
    o, h, lo = (m[c].to_numpy() for c in ("open", "high", "low"))
    rows = []
    for r in trades.iter_rows(named=True):
        decided = int(r["time"].timestamp() * 1000)
        i = np.searchsorted(t, decided)
        end = np.searchsorted(t, decided + r["hold"] * 60_000)
        if end >= len(t):
            rows.append((None,) * len(RESULT))
            continue
        d, entry = r["direction"], o[i]
        stop = entry * (1 - d * r["stop"])
        target = entry * (1 + d * r["target"]) if r["target"] is not None else np.inf * d
        seg = slice(i, end)
        hit_stop = lo[seg] <= stop if d > 0 else h[seg] >= stop
        hit_target = h[seg] >= target if d > 0 else lo[seg] <= target
        hits = hit_stop | hit_target
        if hits.any():
            k = i + int(np.argmax(hits))
            if hit_stop[k - i]:  # beyond the stop at the open (a gap): filled at the open
                rows.append(
                    (t[i], entry, t[k], min(o[k], stop) if d > 0 else max(o[k], stop), "stop")
                )
            else:
                rows.append((t[i], entry, t[k], target, "target"))
        else:
            rows.append((t[i], entry, t[end], o[end], "time"))
    out = pl.DataFrame(rows, schema=RESULT, orient="row").with_columns(
        pl.col("entry_time", "exit_time").cast(pl.Datetime("ms")).dt.replace_time_zone("UTC")
    )
    return pl.concat([trades, out], how="horizontal")


def simulate(trades: pl.DataFrame) -> pl.DataFrame:
    """Walk every trade on its symbol's guarded 1m data and attach costs and net returns."""
    columns = ["open_time", "open", "high", "low", "volume"]
    walked = [
        walk(group, scan("klines/1m", [symbol]).select(columns).collect())
        for (symbol,), group in trades.group_by("symbol")
    ]
    w = pl.concat(walked).drop_nulls("exit_time")
    hl, mapping = costs.hourly(), pl.read_parquet(costs.MAPPING)
    binance = scan("fundingRate").select("symbol", "time", "funding_rate").collect()
    entries, exits = w.select("symbol", time="entry_time"), w.select("symbol", time="exit_time")
    minute = costs.at_minute(pl.concat([entries, exits]), mapping)
    return w.with_columns(
        gross=pl.col("direction") * (pl.col("exit") / pl.col("entry") - 1),
        fees=pl.lit(2 * costs.TAKER),
        slippage=costs.slippage(entries, hl, mapping, minute)
        + costs.slippage(exits, hl, mapping, minute),
        funding=costs.funding(w, hl, mapping, binance),
    ).with_columns(net=pl.col("gross") - pl.col("fees") - pl.col("slippage") - pl.col("funding"))


def daily(results: pl.DataFrame, risk: float = 0.005) -> np.ndarray:
    """Daily returns with equal risk per trade: a stop-out loses about `risk` of equity.

    Each trade's return is booked on its exit day; marking open trades to market would smooth
    multi-day holds and is worth adding once strategies hold for days.
    """
    pnl = results.group_by(day=pl.col("exit_time").dt.date()).agg(
        r=(risk / pl.col("stop") * pl.col("net")).sum()
    )
    days = pl.date_range(pnl["day"].min(), pnl["day"].max(), "1d", eager=True).alias("day")
    return pl.DataFrame(days).join(pnl, on="day", how="left")["r"].fill_null(0.0).to_numpy()


def random_entries(n: int, seed: int) -> pl.DataFrame:
    """Random universe members at random 1h closes, random direction, ±2 ATR(1h), 24h limit."""
    universe = pl.read_parquet(UNIVERSE).select("symbol", "month")
    bars = (
        scan("bars/1h", universe["symbol"].unique().to_list())
        .select("symbol", "time", "high", "low", "close", "tradable")
        .collect()
        .sort("symbol", "time")
        .with_columns(atr_pct=atr(14).over("symbol") / pl.col("close"))
        .with_columns(month=pl.col("time").dt.truncate("1mo"))
        .join(universe, on=["symbol", "month"])
        .filter(pl.col("tradable"), pl.col("atr_pct").is_not_null())
    )
    rng = np.random.default_rng(seed)
    picked = bars[rng.choice(bars.height, size=n, replace=False)]
    return picked.select(
        "symbol",
        "time",
        direction=pl.Series(rng.choice([-1, 1], size=n)),
        stop=2 * pl.col("atr_pct"),
        target=2 * pl.col("atr_pct"),
        hold=pl.lit(24 * 60),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["random"])
    ap.add_argument("--n", type=int, default=20_000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    r = simulate(random_entries(a.n, a.seed))
    months = r["entry_time"].dt.strftime("%Y-%m")
    summary = {
        "trades": r.height,
        "gross": bootstrap_test(r["gross"], months, alternative="two-sided"),
        "costs": float((r["fees"] + r["slippage"] + r["funding"]).mean()),
        "net": float(r["net"].mean()),
        "exits": dict(r["reason"].value_counts().iter_rows()),
    }
    registry.log("validation", "engine.random_entries", {"n": a.n, "seed": a.seed}, summary)
    print(summary)
    cost = pl.col("fees") + pl.col("slippage") + pl.col("funding")
    by_year = r.group_by(year=pl.col("entry_time").dt.year()).agg(
        trades=pl.len(), gross=pl.col("gross").mean(), costs=cost.mean(), net=pl.col("net").mean()
    )
    print(by_year.sort("year"))


if __name__ == "__main__":
    main()

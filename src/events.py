"""Event studies (PROTOCOL §5, §7): does a signal carry information beyond its matched baseline?

`candidates` takes every tradable universe bar of a timeframe and computes its R0 cell and its
forward returns: from the first traded 1m open after the bar's close to the first traded open h
bars later, divided by the bar's ATR(14)/close. `study` compares each event with the mean of its
stratum (symbol × R0 cell), which is the exact expectation of a matched random entry, and
bootstraps the differences by calendar month.

    uv run python -m src.events candidates 1h    # writes data/events/candidates_1h.parquet
    uv run python -m src.events random 1h        # random events must show no effect
"""

import argparse

import numpy as np
import polars as pl

from src import registry
from src.data import DATA, scan
from src.indicators import atr
from src.regime import r0
from src.stats import bootstrap_test
from src.universe import UNIVERSE

HORIZONS = {"1h": [4, 12, 24], "4h": [3, 6, 12], "1d": [1, 3, 5]}
MINUTES = {"15m": 15, "1h": 60, "4h": 240, "1d": 1440}
OUT = DATA / "events"


def next_open(at: pl.DataFrame, traded: pl.DataFrame) -> pl.Series:
    """The first traded 1m open at or after each (symbol, at)."""
    left = at.with_row_index("i").sort("at")
    right = traded.select("symbol", at="open_time", price="open").sort("at")
    joined = left.join_asof(right, on="at", by="symbol", strategy="forward", check_sortedness=False)
    return joined.sort("i")["price"]


def candidates(tf: str, symbols: list[str]) -> pl.DataFrame:
    universe = pl.read_parquet(UNIVERSE).select("symbol", "month")
    out = []
    for s in symbols:
        b = {t: scan(f"bars/{t}", [s]).collect().sort("time") for t in {tf, "4h", "1d"}}
        bars = b[tf].with_columns(atr_pct=atr(14).over("symbol") / pl.col("close"))
        bars = (
            r0(bars, b["4h"], b["1d"])
            .with_columns(month=pl.col("time").dt.truncate("1mo"))
            .join(universe, on=["symbol", "month"])
            .filter(
                pl.col("tradable"), pl.col("cell").is_not_null(), pl.col("atr_pct").is_not_null()
            )
        )
        traded = scan("klines/1m", [s]).filter(pl.col("volume") > 0).collect()
        entry = next_open(bars.select("symbol", at="time"), traded)
        returns = {}
        for h in HORIZONS[tf]:
            later = pl.col("time") + pl.duration(minutes=h * MINUTES[tf])
            exit_price = next_open(bars.select("symbol", at=later), traded)
            returns[f"r{h}"] = (exit_price / entry - 1) / bars["atr_pct"]
        out.append(
            bars.select("symbol", "time", "month", "cell", "atr_pct").with_columns(**returns)
        )
    return pl.concat(out)


def study(
    events: pl.DataFrame,
    cands: pl.DataFrame,
    tf: str,
    alternative: str = "greater",
    reps: int = 2000,
    seed: int = 0,
) -> pl.DataFrame:
    """One row per horizon for `events` (symbol, time = close of the event bar, direction).

    Events outside the universe, on untradable bars or before R0 exists find no candidate and
    drop out; `matched` reports how many remain.
    """
    matched = events.join(cands, on=["symbol", "time"]).height
    years = complete_years(cands)
    rows = []
    for h in HORIZONS[tf]:
        d = diffs(events, cands, h)
        row = {"horizon": h, "events": events.height, "matched": matched, "n": d.height}
        if d.height:
            row |= bootstrap_test(d["diff"], d["month"], alternative, reps, seed)
            row |= same_sign(d, row["effect"], years)
            row |= breakdown(
                d, lambda g: bootstrap_test(g["diff"], g["month"], alternative, reps, seed)
            )
        rows.append(row)
    return pl.DataFrame(rows)


def diffs(events: pl.DataFrame, cands: pl.DataFrame, h: int) -> pl.DataFrame:
    """Matched events with `diff`: the forward return over h bars minus its stratum's mean, signed
    by the event's direction."""
    r = f"r{h}"
    base = cands.drop_nulls(r).group_by("symbol", "cell").agg(base=pl.col(r).mean())
    e = events.join(cands, on=["symbol", "time"]).drop_nulls(r).join(base, on=["symbol", "cell"])
    return e.with_columns(diff=pl.col("direction") * (pl.col(r) - pl.col("base")))


def complete_years(cands: pl.DataFrame) -> pl.Series:
    """Calendar years with all twelve months of candidates: stability counts these only."""
    by_year = cands.group_by(year=pl.col("month").dt.year()).agg(months=pl.col("month").n_unique())
    return by_year.filter(pl.col("months") == 12)["year"]


def same_sign(
    d: pl.DataFrame, effect: float, years: pl.Series, stat: pl.Expr | None = None
) -> dict:
    """Share of complete years and of assets whose `stat` has the sign of `effect` (PROTOCOL §7)."""
    year, stat = pl.col("month").dt.year(), pl.col("diff").mean() if stat is None else stat
    out = {}
    for name, g, by in (
        ("years", d.filter(year.is_in(years.implode())), year),
        ("assets", d, pl.col("symbol")),
    ):
        means = g.group_by(by).agg(s=stat)["s"].drop_nulls().to_numpy()
        same = np.sign(means) == np.sign(effect)
        out[f"{name}_same_sign"] = float(same.mean()) if len(same) else None
    return out


def breakdown(d: pl.DataFrame, test) -> dict:
    """BTC, ETH and the remaining assets: effect and interval of `test`, with no p-value."""
    major = {"btc": "BTCUSDT", "eth": "ETHUSDT"}
    groups = {k: d.filter(pl.col("symbol") == s) for k, s in major.items()}
    groups["other"] = d.filter(~pl.col("symbol").is_in(list(major.values())))
    out = {}
    for name, g in groups.items():
        if g.height:
            t = test(g)
            out |= {f"{name}_{k}": t[k] for k in ("n", "effect", "ci_low", "ci_high")}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["candidates", "random"])
    ap.add_argument("tf", choices=list(HORIZONS))
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    path = OUT / f"candidates_{a.tf}.parquet"
    if a.command == "candidates":
        symbols = pl.read_parquet(UNIVERSE)["symbol"].unique().sort().to_list()
        OUT.mkdir(parents=True, exist_ok=True)
        cands = candidates(a.tf, symbols)
        cands.write_parquet(path)
        print(cands.height, "candidates;", cands.group_by("cell").len().sort("cell"))
        return
    cands = pl.read_parquet(path)
    rng = np.random.default_rng(a.seed)
    picked = cands[rng.choice(cands.height, size=a.n, replace=False)].select("symbol", "time")
    events = picked.with_columns(direction=pl.Series(rng.choice([-1, 1], size=a.n)))
    result = study(events, cands, a.tf, alternative="two-sided", seed=a.seed)
    registry.log(
        "validation",
        f"engine.random_events_{a.tf}",
        {"n": a.n, "seed": a.seed},
        {"rows": result.to_dicts()},
    )
    print(result)


if __name__ == "__main__":
    main()

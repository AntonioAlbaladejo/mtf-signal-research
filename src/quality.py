"""Structural checks: 1m gaps, stalls, duplicates and bad bars; funding settlement steps.

    uv run python -m src.quality       # writes data/quality/{summary,gaps,stalls,funding}.csv

A gap is a run of missing minutes. A stall is a run of at least STALL_MINUTES zero-volume bars:
the archive pads exchange outages with flat zero-volume bars instead of leaving them out, so they
look like real prices. An event whose first minute falls inside events of at least half the
symbols trading then is classed as market-wide (an outage or maintenance); others need a look.
"""

import polars as pl

from src.data import DATA, files

OUT = DATA / "quality"
COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]
STALL_MINUTES = 5


def check(bars: pl.DataFrame) -> tuple[dict, pl.DataFrame, pl.DataFrame]:
    """One symbol's 1m bars -> summary counts, its gaps and its stalls."""
    t = bars.sort("open_time").with_columns(step=pl.col("open_time").diff())
    gaps = t.filter(pl.col("step") > pl.duration(minutes=1)).select(
        start=pl.col("open_time") - pl.col("step") + pl.duration(minutes=1),
        minutes=pl.col("step").dt.total_minutes() - 1,
    )
    zero = t.filter(pl.col("volume") == 0)
    new_run = (pl.col("open_time").diff() != pl.duration(minutes=1)).fill_null(True)
    stalls = (
        zero.with_columns(run=new_run.cum_sum())
        .group_by("run")
        .agg(start=pl.col("open_time").first(), minutes=pl.len())
        .filter(pl.col("minutes") >= STALL_MINUTES)
        .select("start", pl.col("minutes").cast(pl.Int64))
        .sort("start")
    )
    bad = (
        (pl.col("high") < pl.max_horizontal("open", "close"))
        | (pl.col("low") > pl.min_horizontal("open", "close"))
        | (pl.col("low") <= 0)
    )
    summary = {
        "first": t["open_time"].min(),
        "last": t["open_time"].max(),
        "bars": t.height,
        "duplicates": t.height - t["open_time"].n_unique(),
        "missing_minutes": int(gaps["minutes"].sum()),
        "gaps": gaps.height,
        "stalls": stalls.height,
        "bad_ohlc": t.filter(bad).height,
        "zero_volume": zero.height,
    }
    return summary, gaps, stalls


def classify(events: pl.DataFrame, summary: pl.DataFrame) -> pl.DataFrame:
    """Mark events whose first minute falls inside events of at least half the symbols trading.

    Not an identical start minute, since one outage can begin a minute apart across symbols; and
    not any overlap, since a delisted coin's years-long stall overlaps everything.
    """
    e = events.with_columns(end=pl.col("start") + pl.duration(minutes=pl.col("minutes")))
    other = e.select(other="symbol", o_start="start", o_end="end")
    sharing = (
        e.join(other, how="cross")
        .filter((pl.col("o_start") <= pl.col("start")) & (pl.col("o_end") > pl.col("start")))
        .group_by("symbol", "start")
        .agg(sharing=pl.col("other").n_unique())
    )
    trading = (
        e.select("symbol", "start")
        .join(summary.select("first", "last"), how="cross")
        .filter(pl.col("start").is_between("first", "last"))
        .group_by("symbol", "start")
        .agg(trading=pl.len())
    )
    return (
        e.join(sharing, on=["symbol", "start"])
        .join(trading, on=["symbol", "start"])
        .with_columns(market_wide=pl.col("sharing") >= pl.col("trading") / 2)
        .drop("end")
        .sort("start", "symbol")
    )


def funding_steps(funding: pl.DataFrame) -> pl.DataFrame:
    """Settlement steps that match neither the previous nor the current funding interval.

    Binance changes intervals (1, 2, 4 or 8 h) on the fly, so a step equal to either one is normal;
    anything else is a missed settlement or a realignment to a new interval grid.
    """
    step = pl.col("time").diff().over("symbol").dt.total_minutes() / 60
    return (
        funding.sort("symbol", "time")
        .with_columns(step_h=step.round(0), prev_h=pl.col("interval_hours").shift(1).over("symbol"))
        .filter(
            pl.col("step_h").is_not_null(),
            pl.col("step_h") != pl.col("prev_h"),
            pl.col("step_h") != pl.col("interval_hours"),
        )
        .select("symbol", "time", "step_h", "prev_h", "interval_hours")
    )


def main() -> None:
    # Reads the hold-out too: these checks never compute returns (PROTOCOL §3).
    rows, gaps, stalls = [], [], []
    for s in sorted({p.parent.name for p in files("klines/1m")}):
        summary, g, st = check(pl.read_parquet(files("klines/1m", [s]), columns=COLUMNS))
        rows.append({"symbol": s} | summary)
        gaps.append(g.with_columns(symbol=pl.lit(s)))
        stalls.append(st.with_columns(symbol=pl.lit(s)))
    summary = pl.DataFrame(rows)

    OUT.mkdir(parents=True, exist_ok=True)
    summary.write_csv(OUT / "summary.csv")
    with pl.Config(tbl_rows=-1, tbl_cols=-1):
        print(summary.drop("bars"))
        for name, events in (("gaps", gaps), ("stalls", stalls)):
            events = classify(pl.concat(events), summary)
            events.write_csv(OUT / f"{name}.csv")
            print(
                name,
                events.group_by("market_wide").agg(n=pl.len(), minutes=pl.col("minutes").sum()),
            )
            print(events.filter(~pl.col("market_wide")).sort("minutes", descending=True).head(20))
        steps = funding_steps(pl.read_parquet(files("fundingRate")))
        steps.write_csv(OUT / "funding.csv")
        hours = pl.col("time").dt.truncate("1h").alias("hour")
        print("funding", steps.group_by(hours).agg(symbols=pl.len()).sort("hour"))


if __name__ == "__main__":
    main()

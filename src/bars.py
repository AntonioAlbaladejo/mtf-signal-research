"""Multi-timeframe bars built from 1m klines, and as-of alignment across timeframes.

    uv run python -m src.bars      # writes data/binance/um/bars/<tf>/<SYMBOL>/bars.parquet

Bars are indexed by close (`time`). Research reads them through `src.data.scan("bars/<tf>")`.
"""

import polars as pl

from src.binance import OUT as BINANCE
from src.binance import write
from src.data import files

TIMEFRAMES = ["15m", "1h", "4h", "1d"]
SUMS = ["volume", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume"]
OHLCV = ["open", "high", "low", "close", "volume"]


def resample(m1: pl.DataFrame, every: str) -> pl.DataFrame:
    """1m bars -> `every` bars, aligned to UTC like Binance's native klines.

    `minutes` counts the 1m bars inside, so a partial bar at a listing is visible. A bar without
    volume is untradable (PROTOCOL §6).
    """
    return (
        m1.sort("symbol", "open_time")
        .group_by_dynamic("open_time", every=every, closed="left", label="left", group_by="symbol")
        .agg(
            pl.col("open").first(),
            pl.col("high").max(),
            pl.col("low").min(),
            pl.col("close").last(),
            pl.col(SUMS).sum(),
            minutes=pl.len(),
        )
        .with_columns(time=pl.col("open_time").dt.offset_by(every), tradable=pl.col("volume") > 0)
    )


def asof(left: pl.DataFrame, right: pl.DataFrame, columns: list[str], suffix: str) -> pl.DataFrame:
    """Attach to each `left` bar the latest `right` values whose bar had closed by `left`'s close.

    A 4h bar that opens at 08:00 closes at 12:00, so a 15m bar closing at 10:15 sees the 4h bar
    that closed at 08:00, never the one still forming (PROTOCOL §4).
    """
    r = right.select("symbol", "time", *columns).rename({c: f"{c}_{suffix}" for c in columns})
    # Sorted by time here, hence within each symbol; Polars cannot verify that itself with `by`.
    return left.sort("time").join_asof(
        r.sort("time"), on="time", by="symbol", strategy="backward", check_sortedness=False
    )


def main() -> None:
    # Built over the hold-out too; research reads bars only through the guarded scan().
    symbols = sorted({p.parent.name for p in files("klines/1m")})
    mismatches = []
    for s in symbols:
        m1 = pl.read_parquet(files("klines/1m", [s]))
        for tf in TIMEFRAMES:
            bars = resample(m1, tf)
            write(BINANCE / "bars" / tf / s / "bars.parquet", bars)
        native = pl.read_parquet(files("klines/1d", [s]), columns=["open_time", *OHLCV])
        both = bars.join(native, on="open_time", suffix="_native")
        price_differs = pl.any_horizontal(pl.col(c) != pl.col(f"{c}_native") for c in OHLCV[:4])
        v, nv = pl.col("volume"), pl.col("volume_native")
        bad = both.filter(price_differs | ((v - nv).abs() > 1e-6 * nv.abs() + 1e-9))
        mismatches.append((s, both.height, bad.height, bars.height - both.height))
    report = pl.DataFrame(
        mismatches, schema=["symbol", "days", "mismatched", "not_in_native"], orient="row"
    )
    with pl.Config(tbl_rows=-1):
        print(report.filter((pl.col("mismatched") > 0) | (pl.col("not_in_native") > 0)))
    print(report.select(pl.col("days", "mismatched", "not_in_native").sum()))


if __name__ == "__main__":
    main()

"""R0, the pre-registered regime (HYPOTHESES.md): 4h trend × 1d volatility tercile."""

import polars as pl

from src.bars import asof
from src.indicators import atr, ema


def trend(bars_4h: pl.DataFrame) -> pl.DataFrame:
    """+1 above a rising EMA(200), -1 below a falling one, 0 otherwise; null during warm-up."""
    e = ema(pl.col("close"), 200).over("symbol")
    slope = e - e.shift(20).over("symbol")
    return bars_4h.with_columns(
        trend=pl.when(slope.is_null())
        .then(None)
        .when((pl.col("close") > e) & (slope > 0))
        .then(1)
        .when((pl.col("close") < e) & (slope < 0))
        .then(-1)
        .otherwise(0)
    )


def vol_tercile(bars_1d: pl.DataFrame) -> pl.DataFrame:
    """0, 1, 2: tercile of ATR(14)/close within its trailing 365 daily bars (at least 180)."""
    x = atr(14).over("symbol") / pl.col("close")
    q = [
        x.rolling_quantile(p, window_size=365, min_samples=180).over("symbol")
        for p in (1 / 3, 2 / 3)
    ]
    return bars_1d.with_columns(
        vol=pl.when(q[0].is_null())
        .then(None)
        .when(x <= q[0])
        .then(0)
        .when(x <= q[1])
        .then(1)
        .otherwise(2)
    )


def r0(bars: pl.DataFrame, bars_4h: pl.DataFrame, bars_1d: pl.DataFrame) -> pl.DataFrame:
    """Attach `trend` and `vol` as known at each bar's close; `cell` is null until both exist."""
    out = asof(asof(bars, trend(bars_4h), ["trend"], "r0"), vol_tercile(bars_1d), ["vol"], "r0")
    return out.rename({"trend_r0": "trend", "vol_r0": "vol"}).with_columns(
        cell=pl.when(pl.col("trend").is_null() | pl.col("vol").is_null())
        .then(None)
        .otherwise(pl.format("{}/{}", "trend", "vol"))
    )

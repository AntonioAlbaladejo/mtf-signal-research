"""Causal indicators as Polars expressions. Apply them per symbol: `.over("symbol")`.

Averages are seeded at the first value and stay null until their lookback is filled
(HYPOTHESES.md, warm-up). After a few lookbacks they match the SMA-seeded textbook versions.
"""

import polars as pl


def ema(x: pl.Expr, n: int) -> pl.Expr:
    return x.ewm_mean(span=n, adjust=False, min_samples=n)


def rma(x: pl.Expr, n: int) -> pl.Expr:
    """Wilder's moving average (alpha = 1/n), used by ATR and RSI."""
    return x.ewm_mean(alpha=1 / n, adjust=False, min_samples=n)


def atr(n: int = 14) -> pl.Expr:
    prev = pl.col("close").shift(1)
    true_range = pl.max_horizontal(
        pl.col("high") - pl.col("low"), (pl.col("high") - prev).abs(), (pl.col("low") - prev).abs()
    )
    return rma(true_range, n)


def rsi(n: int = 14) -> pl.Expr:
    delta = pl.col("close").diff()
    gain, loss = rma(delta.clip(lower_bound=0), n), rma((-delta).clip(lower_bound=0), n)
    return 100 * gain / (gain + loss)

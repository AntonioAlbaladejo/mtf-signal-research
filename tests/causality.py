"""The future-invariance test every feature and signal must pass (PROTOCOL §4)."""

import random
from collections.abc import Callable

import polars as pl

PERTURBED = ["open", "high", "low", "close", "volume"]


def assert_causal(
    fn: Callable[[pl.DataFrame], pl.DataFrame],
    bars: pl.DataFrame,
    columns: list[str],
    cuts: int = 5,
) -> None:
    """Scramble every bar after a cut, recompute, and require identical outputs up to the cut."""
    rng = random.Random(0)
    times = bars["time"].unique().sort()
    expected = fn(bars).sort("symbol", "time")
    for _ in range(cuts):
        cut = times[rng.randrange(len(times) // 10, len(times) * 9 // 10)]
        noise = pl.Series([rng.uniform(0.5, 1.5) for _ in range(bars.height)])
        scrambled = bars.with_columns(
            pl.when(pl.col("time") > cut).then(pl.col(c) * noise).otherwise(pl.col(c))
            for c in PERTURBED
        )
        past = pl.col("time") <= cut
        got = fn(scrambled).sort("symbol", "time").filter(past).select(columns)
        assert got.equals(expected.filter(past).select(columns)), (
            f"{columns} depend on data after {cut}"
        )

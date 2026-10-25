"""Data paths, the sealed hold-out, and the guarded loader that research code must use."""

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

DATA = Path("data")

# Research dataset frozen on 2026-10-18: Binance USDⓈ-M monthly archives up to 2026-09.
# The most recent 6 months are sealed (PROTOCOL §3).
HOLDOUT_START = datetime(2026, 4, 1, tzinfo=UTC)


def files(kind: str, symbols: list[str] | None = None) -> list[Path]:
    """Parquet files of a Binance dataset ("klines/1m", "klines/1d", "fundingRate", "bars/1h"...).

    Unguarded: only data building, universe construction and quality checks read these directly.
    """
    root = DATA / "binance" / "um" / kind
    return sorted(p for s in symbols or ["*"] for p in root.glob(f"{s}/*.parquet"))


def scan(
    kind: str, symbols: list[str] | None = None, unseal_for: str | None = None
) -> pl.LazyFrame:
    """Lazy scan of a Binance dataset, with every row from the sealed hold-out removed.

    `unseal_for` names the hypothesis that opens the hold-out; the access is logged, and a second
    one for the same family is refused (PROTOCOL §3).
    """
    lf = pl.scan_parquet(files(kind, symbols))
    if unseal_for is None:
        return lf.filter(pl.col("time") < HOLDOUT_START)
    from src.registry import unseal

    unseal(unseal_for, f"scan {kind}")
    return lf

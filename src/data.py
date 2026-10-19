"""Data paths, the sealed hold-out, and the guarded loader that research code must use."""

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

DATA = Path("data")

# Research dataset frozen on 2026-10-18: Binance USDⓈ-M monthly archives up to 2026-09.
# The most recent 6 months are sealed (PROTOCOL §3).
HOLDOUT_START = datetime(2026, 4, 1, tzinfo=UTC)


def files(kind: str, symbols: list[str] | None = None) -> list[Path]:
    """Monthly Parquet files of a Binance dataset ("klines/1m", "klines/1d", "fundingRate").

    Unguarded: only universe construction and data-quality checks may read these directly.
    """
    root = DATA / "binance" / "um" / kind
    return sorted(p for s in symbols or ["*"] for p in root.glob(f"{s}/*.parquet"))


def scan(kind: str, symbols: list[str] | None = None, unseal: bool = False) -> pl.LazyFrame:
    """Lazy scan of a Binance dataset with every row from the sealed hold-out removed."""
    if unseal:
        raise NotImplementedError("unsealing must be logged in the trial registry (phase 2)")
    return pl.scan_parquet(files(kind, symbols)).filter(pl.col("time") < HOLDOUT_START)

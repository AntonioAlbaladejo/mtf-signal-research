"""Point-in-time universe: each month, the top 10 crypto perpetuals by trailing 30-day quote volume.

uv run python -m src.universe      # needs klines/1d; writes data/universe.parquet
"""

import json
from datetime import UTC, datetime

import polars as pl

from src.binance import get
from src.data import DATA, files

UNIVERSE = DATA / "universe.parquet"
EXCHANGE_INFO = DATA / "binance" / "um" / "exchangeInfo.json"


def exchange_info() -> list[dict]:
    """Contract metadata for currently listed contracts, cached so the classification is stable."""
    if not EXCHANGE_INFO.exists():
        EXCHANGE_INFO.write_bytes(get("https://fapi.binance.com/fapi/v1/exchangeInfo"))
    return json.loads(EXCHANGE_INFO.read_text())["symbols"]


def crypto_only(daily: pl.DataFrame, info: list[dict]) -> pl.DataFrame:
    """Drop index and TradFi perpetuals (stocks, commodities, FX), listed on Binance since 2025-12.

    Delisted contracts are missing from the metadata. They are kept as crypto only if they started
    trading before the first TradFi listing; anything else is an error, not a guess.
    """
    kinds = {s["symbol"]: (s["contractType"], s["underlyingType"]) for s in info}
    tradfi = [s["onboardDate"] for s in info if s["contractType"] == "TRADIFI_PERPETUAL"]
    first_tradfi = datetime.fromtimestamp(min(tradfi) / 1000, UTC)
    unlisted = daily.filter(~pl.col("symbol").is_in(list(kinds)))
    late = (
        unlisted.group_by("symbol")
        .agg(pl.col("open_time").min())
        .filter(pl.col("open_time") >= first_tradfi)
    )
    if late.height:
        raise ValueError(
            f"unclassified contracts listed after TradFi began: {late['symbol'].to_list()}"
        )
    crypto = [s for s, kind in kinds.items() if kind == ("PERPETUAL", "COIN")]
    return daily.filter(pl.col("symbol").is_in(crypto) | ~pl.col("symbol").is_in(list(kinds)))


def monthly_top(daily: pl.DataFrame, n: int = 10) -> pl.DataFrame:
    """Rank each month on the daily bar that closes at the month boundary.

    `daily` has symbol, open_time and quote_volume for 1d bars. The 30-day window ends with the
    bar closing at the boundary, so nothing after it is used. A symbol with no bar on the last day
    of the previous month is not trading at the boundary and cannot enter.
    """
    vol30 = pl.col("quote_volume").rolling_sum_by("open_time", window_size="30d")
    return (
        daily.sort("symbol", "open_time")
        .with_columns(vol30=vol30.over("symbol"), month=pl.col("open_time").dt.offset_by("1d"))
        .filter(pl.col("month").dt.day() == 1)
        .with_columns(rank=pl.col("vol30").rank("ordinal", descending=True).over("month"))
        .filter(pl.col("rank") <= n)
        .select("month", "rank", "symbol", "vol30")
        .sort("month", "rank")
    )


def main() -> None:
    # Reads volumes in the hold-out too: universe membership is structural (PROTOCOL §3).
    daily = pl.read_parquet(files("klines/1d"), columns=["symbol", "open_time", "quote_volume"])
    top = monthly_top(crypto_only(daily, exchange_info()))
    top.write_parquet(UNIVERSE)
    print(f"{top['month'].n_unique()} months, {top['symbol'].n_unique()} distinct symbols")
    with pl.Config(tbl_rows=-1):
        print(top.group_by("symbol").len().sort("len", "symbol", descending=[True, False]))


if __name__ == "__main__":
    main()

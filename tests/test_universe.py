from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from src.universe import crypto_only, monthly_top


def daily(volumes: dict[str, float], days: int = 70, delisted: dict[str, int] | None = None):
    start = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [
        (s, start + timedelta(days=d), v)
        for s, v in volumes.items()
        for d in range(min(days, (delisted or {}).get(s, days)))
    ]
    return pl.DataFrame(rows, schema=["symbol", "open_time", "quote_volume"], orient="row")


def test_ranks_by_trailing_volume_and_keeps_top_n():
    top = monthly_top(daily({"A": 3.0, "B": 2.0, "C": 1.0}), n=2)
    feb = top.filter(pl.col("month") == datetime(2024, 2, 1, tzinfo=UTC))
    assert feb["symbol"].to_list() == ["A", "B"]
    assert feb["vol30"].to_list() == [90.0, 60.0]


FEB = pl.col("month") == datetime(2024, 2, 1, tzinfo=UTC)


def test_symbol_not_trading_at_the_boundary_cannot_enter():
    top = monthly_top(daily({"A": 3.0, "B": 2.0}, delisted={"A": 25}), n=2)
    assert top.filter(FEB)["symbol"].to_list() == ["B"]


def test_ranking_is_invariant_to_data_after_the_boundary():
    base = daily({"A": 3.0, "B": 2.0, "C": 1.0})
    after = pl.col("open_time") >= datetime(2024, 2, 1, tzinfo=UTC)
    future = base.with_columns(  # C's volume explodes from the boundary on
        quote_volume=pl.when(after & (pl.col("symbol") == "C")).then(1e9).otherwise("quote_volume")
    )
    assert monthly_top(base, n=2).filter(FEB).equals(monthly_top(future, n=2).filter(FEB))


def test_only_crypto_perpetuals_and_old_delisted_contracts_are_kept():
    tradfi_start = int(datetime(2025, 12, 11, tzinfo=UTC).timestamp() * 1000)
    info = [
        {"symbol": "BTC", "contractType": "PERPETUAL", "underlyingType": "COIN", "onboardDate": 0},
        {"symbol": "XAU", "contractType": "TRADIFI_PERPETUAL", "underlyingType": "COMMODITY",
         "onboardDate": tradfi_start},
        {"symbol": "DOM", "contractType": "PERPETUAL", "underlyingType": "INDEX", "onboardDate": 0},
    ]  # fmt: skip
    kept = crypto_only(daily({"BTC": 1.0, "XAU": 1.0, "DOM": 1.0, "LUNA": 1.0}), info)
    assert sorted(kept["symbol"].unique()) == ["BTC", "LUNA"]

    late = daily({"NEW": 1.0}).with_columns(pl.col("open_time").dt.offset_by("800d"))
    with pytest.raises(ValueError, match="NEW"):
        crypto_only(late, info)

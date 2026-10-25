from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from src import costs
from src.costs import candidates, funding, match, slippage
from src.data import HOLDOUT_START

T0 = datetime(2024, 1, 1, tzinfo=UTC)
H = timedelta(hours=1)


def test_hourly_costs_stop_at_the_holdout(tmp_path, monkeypatch):
    monkeypatch.setattr(costs, "HL", tmp_path)
    (tmp_path / "ctx_hourly").mkdir()
    times = [HOLDOUT_START - H, HOLDOUT_START]
    pl.DataFrame({"coin": ["BTC", "BTC"], "time": times}).write_parquet(
        tmp_path / "ctx_hourly" / "day.parquet"
    )
    assert costs.hourly()["time"].to_list() == times[:1]


def hl_table(coin: str, hours: int, mid: float, impact_bps: float, rate: float = 0.0001):
    return pl.DataFrame({
        "coin": [coin] * hours, "time": [T0 + i * H for i in range(hours)],
        "mid": [mid] * hours, "impact_bps": [impact_bps] * hours, "funding": [rate] * hours,
    })  # fmt: skip


def test_symbols_match_coins_only_when_prices_agree():
    assert ("kPEPE", 1.0) in candidates("1000PEPEUSDT")
    assert ("kDOGS", 1e-3) in candidates("DOGSUSDT")
    hl = pl.concat(
        [
            hl_table("kPEPE", 48, 0.01, 2.0),
            hl_table("BTC", 48, 50_000.0, 0.1),
            hl_table("NEIRO", 48, 9.0, 1.0),
        ]
    )
    bn = pl.DataFrame({
        "symbol": ["1000PEPEUSDT"] * 48 + ["BTCUSDT"] * 48 + ["NEIROUSDT"] * 48,
        "time": [T0 + (i + 1) * H for i in range(48)] * 3,
        "close": [0.01] * 48 + [50_100.0] * 48 + [0.001] * 48,  # NEIRO: same ticker, other token
    })  # fmt: skip
    m = match(bn, hl)
    assert dict(zip(m["symbol"], m["coin"], strict=True)) == {
        "1000PEPEUSDT": "kPEPE",
        "BTCUSDT": "BTC",
    }


def mapping_for(symbols_coins: list[tuple[str, str, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        [(s, c, T0, T0 + 47 * H, bps) for s, c, bps in symbols_coins],
        schema=["symbol", "coin", "first_hl", "last_hl", "median_impact_bps"],
        orient="row",
    )


def test_slippage_uses_the_minute_then_the_hour_then_the_symbol_median_then_the_upper_quartile():
    hl = hl_table("BTC", 24, 50_000.0, 0.5)
    mapping = mapping_for(
        [("BTCUSDT", "BTC", 0.3), ("A", "A", 1.0), ("B", "B", 2.0), ("C", "C", 3.0)]
    )
    minute = pl.DataFrame({"coin": ["BTC"], "time": [T0 + 2 * H], "impact_bps": [0.8]})
    fills = pl.DataFrame({
        "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT", "NEVERUSDT"],
        "time": [T0 + 2 * H, T0 + timedelta(minutes=90), T0 + timedelta(days=30), T0],
    })  # fmt: skip
    assert slippage(fills, hl, mapping, minute).to_list() == pytest.approx(
        [0.8e-4, 0.5e-4, 0.3e-4, 2.25e-4]
    )


def test_minute_impact_is_read_only_at_the_fills_and_before_the_holdout(tmp_path, monkeypatch):
    monkeypatch.setattr(costs, "HL", tmp_path)
    (tmp_path / "ctx_minute").mkdir()
    before, after = HOLDOUT_START - H, HOLDOUT_START + H
    for t in (before, after):
        pl.DataFrame({
            "coin": ["BTC", "BTC"], "time": [t, t + timedelta(minutes=1)], "impact_bps": [1.0, 2.0],
        }).write_parquet(tmp_path / "ctx_minute" / f"{t:%Y%m%d}.parquet")  # fmt: skip
    fills = pl.DataFrame({"symbol": ["BTCUSDT", "BTCUSDT"], "time": [before, after]})
    got = costs.at_minute(fills, mapping_for([("BTCUSDT", "BTC", 0.5)]))
    assert got.select("time", "impact_bps").rows() == [(before, 1.0)]


def test_funding_sums_settlements_inside_the_holding_period_with_the_right_sign():
    hl = hl_table("BTC", 48, 50_000.0, 0.5, rate=0.0001)  # settles at each hour's end
    mapping = mapping_for([("BTCUSDT", "BTC", 0.5)])
    binance = pl.DataFrame(
        {
            "symbol": ["ETHUSDT"] * 3 + ["BTCUSDT"],
            "time": [T0 + 8 * i * H for i in range(3)] + [T0 + 49 * H],
            "funding_rate": [0.001] * 3 + [0.002],
        }
    )
    trades = pl.DataFrame({
        "symbol": ["BTCUSDT", "BTCUSDT", "ETHUSDT", "BTCUSDT"], "direction": [1, -1, 1, 1],
        "entry_time": [T0 + timedelta(minutes=30)] * 2 + [T0 + timedelta(minutes=1)]
        + [T0 + timedelta(hours=47, minutes=30)],
        "exit_time": [T0 + timedelta(hours=3, minutes=30)] * 2 + [T0 + 16 * H, T0 + 50 * H],
    })  # fmt: skip
    # BTC: settlements at 01:00, 02:00, 03:00; ETH (not on Hyperliquid): 08:00 and 16:00.
    # The last BTC trade outlives its Hyperliquid listing (last settlement at 48h): Binance's.
    assert funding(trades, hl, mapping, binance).to_list() == pytest.approx(
        [0.0003, -0.0003, 0.002, 0.002]
    )

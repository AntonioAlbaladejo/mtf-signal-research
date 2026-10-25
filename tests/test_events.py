from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from src.events import study

T0 = datetime(2022, 1, 1, tzinfo=UTC)


def candidates(n: int = 6000, seed: int = 0) -> pl.DataFrame:
    """Two symbols; R0 cell "up" drifts +1 ATR and "down" -1 ATR, plus noise."""
    rng = np.random.default_rng(seed)
    time = [T0 + timedelta(hours=i) for i in range(n)]
    cell = np.where(np.arange(n) % 3 == 0, "down", "up")
    drift = np.where(cell == "up", 1.0, -1.0)
    frames = [
        pl.DataFrame({"symbol": s, "time": time, "cell": cell, "r4": drift + rng.normal(0, 1, n)})
        for s in ("BTCUSDT", "B")
    ]
    cands = pl.concat(frames).with_columns(month=pl.col("time").dt.truncate("1mo"))
    return cands.with_columns(r12=pl.col("r4"), r24=pl.col("r4"))


def events_at(cands: pl.DataFrame, rows: pl.Expr, direction: int) -> pl.DataFrame:
    return cands.filter(rows).select("symbol", "time", direction=pl.lit(direction))


def test_regime_drift_is_not_mistaken_for_an_effect():
    cands = candidates()
    longs_in_uptrend = events_at(cands, pl.col("cell") == "up", 1)  # earn +1 ATR, like any up bar
    result = study(longs_in_uptrend, cands, "1h", alternative="two-sided", reps=500)
    assert abs(result["effect"][0]) < 0.05 and result["p"][0] > 0.05


def test_planted_effect_and_direction_are_recovered():
    cands = candidates()
    chosen = (pl.col("time").dt.hour() == 6) & (pl.col("cell") == "down")
    cands = cands.with_columns(r4=pl.when(chosen).then(pl.col("r4") - 0.5).otherwise("r4"))
    shorts = events_at(cands, chosen, -1)  # the planted move is down, so shorts gain 0.5
    result = study(shorts, cands, "1h", reps=500)
    assert result["effect"][0] == pytest.approx(0.5, abs=0.15)
    assert result["p"][0] < 0.01
    assert result["years_same_sign"][0] == 1.0 and result["assets_same_sign"][0] == 1.0
    assert result["btc_effect"][0] == pytest.approx(0.5, abs=0.2)  # no ETH in this universe
    assert result["btc_n"][0] + result["other_n"][0] == result["n"][0]
    assert "eth_effect" not in result.columns and "btc_p" not in result.columns


def test_no_matched_event_is_reported_not_crashed():
    cands = candidates(300)
    nowhere = pl.DataFrame({"symbol": ["Z"], "time": [T0], "direction": [1]})
    assert study(nowhere, cands, "1h", reps=50)["n"].to_list() == [0, 0, 0]

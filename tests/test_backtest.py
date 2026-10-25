from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from src.backtest import walk

T0 = datetime(2024, 1, 1, tzinfo=UTC)


def path(bars: list[tuple[float, float, float, float]]) -> pl.DataFrame:
    """1m bars (open, high, low, volume) from T0 on."""
    return pl.DataFrame(
        [(T0 + timedelta(minutes=i), *b) for i, b in enumerate(bars)],
        schema=["open_time", "open", "high", "low", "volume"],
        orient="row",
    )


def trade(direction: int = 1, stop: float = 0.02, target: float | None = 0.02, hold: int = 5):
    return pl.DataFrame(
        {"time": [T0], "direction": [direction], "stop": [stop], "target": [target], "hold": [hold]}
    )


def outcome(t: pl.DataFrame, bars: pl.DataFrame) -> tuple:
    r = walk(t, bars).row(0, named=True)
    return r["exit"], r["reason"], r["exit_time"] - T0 if r["exit_time"] else None


FLAT = (100.0, 100.5, 99.5, 1.0)


def test_target_stop_and_time_exits():
    assert outcome(trade(), path([FLAT, (100, 102.5, 100, 1)] + [FLAT] * 5)) == (
        102.0,
        "target",
        timedelta(minutes=1),
    )
    assert outcome(trade(), path([FLAT, (100, 100, 97, 1)] + [FLAT] * 5)) == (
        98.0,
        "stop",
        timedelta(minutes=1),
    )
    assert outcome(trade(), path([FLAT] * 7)) == (100.0, "time", timedelta(minutes=5))


def test_short_mirrors_long():
    assert outcome(trade(-1), path([FLAT, (100, 100, 97, 1)] + [FLAT] * 5))[:2] == (98.0, "target")


def test_stop_and_target_in_the_same_minute_counts_as_the_stop():
    assert outcome(trade(), path([FLAT, (100, 103, 97, 1)] + [FLAT] * 5))[:2] == (98.0, "stop")


def test_untraded_bars_neither_enter_nor_stop_and_gaps_fill_at_the_open():
    outage = (100.0, 100.0, 100.0, 0.0)
    bars = path([outage, FLAT, outage, (95, 96, 94, 0.0), (95, 96, 94, 1)] + [FLAT] * 5)
    r = walk(trade(), bars).row(0, named=True)
    assert r["entry_time"] - T0 == timedelta(minutes=1)  # first traded open
    assert (r["exit"], r["reason"], r["exit_time"] - T0) == (95.0, "stop", timedelta(minutes=4))


def test_no_target_and_running_past_the_data():
    assert outcome(trade(target=None), path([FLAT, (100, 150, 100, 1)] + [FLAT] * 5))[1] == "time"
    assert walk(trade(hold=60), path([FLAT] * 7))["exit_time"].null_count() == 1


@pytest.mark.parametrize("direction, expected", [(1, 0.02), (-1, -0.02)])
def test_one_rally_is_a_target_for_a_long_and_a_stop_for_a_short(direction, expected):
    r = walk(trade(direction), path([FLAT, (100, 103, 99.9, 1)] + [FLAT] * 5)).row(0, named=True)
    assert direction * (r["exit"] / r["entry"] - 1) == pytest.approx(expected)

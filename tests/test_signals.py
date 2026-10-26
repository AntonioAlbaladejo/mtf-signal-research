from datetime import timedelta

import polars as pl
import pytest

from src.bars import resample
from src.signals import TD, td_sequential
from tests.causality import assert_causal
from tests.test_bars import T0, walk

RISE = [100.0, 101, 102, 103, 104, 105]  # its last bar sets up the bearish price flip


def bars(closes: list[float], mirror: bool = False) -> pl.DataFrame:
    """Hourly bars one point tall around each close; `mirror` reflects prices around 100."""
    c = pl.Series([200 - x for x in closes] if mirror else closes)
    return pl.DataFrame(
        {"symbol": "BTCUSDT", "time": [T0 + timedelta(hours=i) for i in range(len(c))]}
    ).with_columns(close=c, high=c + 0.5, low=c - 0.5)


def at(signals: pl.DataFrame, column: str) -> dict[int, int]:
    return {i: v for i, v in enumerate(signals[column]) if v}


@pytest.mark.parametrize("mirror", [False, True])
def test_setup_18_recycles_the_countdown_and_bar_13_is_deferred(mirror):
    # Setup bars 1-29 fall one point a bar from index 6, so countdown counts every bar from setup
    # bar 9 (index 14). Setup bar 18 (index 23) restarts it: count 8 at index 30 (close 77) and 12
    # at index 34. After a rally, index 38 qualifies but its low (78.5) is above 77: deferred.
    closes = RISE + [107.0 - i for i in range(6, 35)] + [78, 82, 86, 79, 76]
    s = td_sequential(bars(closes, mirror))
    sign = -1 if mirror else 1
    assert at(s, "setup") == {14: sign} and at(s, "perfected") == {14: sign}
    assert at(s, "countdown") == {39: sign}  # 26 without the recycle


def test_a_true_low_above_the_setup_erases_the_countdown():
    # The countdown from setup bar 9 at index 14 has three bars when price jumps to 200; index 18
    # has a true low above the setup's 105. A new setup from index 19 completes at 27, recycles at
    # 36 (bar 18) and counts 13 at 48. Without the erasure, the old count would end at index 28.
    fall, crash = [107.0 - i for i in range(6, 17)], [109.0 - i for i in range(19, 51)]
    s = td_sequential(bars(RISE + fall + [200, 200] + crash))
    assert at(s, "setup") == {14: 1, 27: 1}
    assert at(s, "countdown") == {48: 1}


@pytest.mark.parametrize("step, thirteen", [(2, 45), (1, 28), (3, 28)])
def test_only_a_comparable_new_setup_recycles_the_countdown(step, thirteen):
    # Setup A (indices 6-14, true range 12.5) starts the countdown. After a one-bar bounce, setup
    # B (16-24) falls `step` a bar. At 2, its true range (19.5) is within [1, 1.618) times A's:
    # it restarts the countdown, and its bar 18 (33) restarts it again, so 13 comes at index 45.
    # At 1 (11.5) and 3 (27.5) it is outside: A stays active and its count ends at index 28.
    fall_a, fall_b = [107.0 - i for i in range(6, 15)], [94.0 - step * i for i in range(31)]
    s = td_sequential(bars(RISE + fall_a + [97] + fall_b))
    assert at(s, "setup") == {14: 1, 24: 1}
    assert at(s, "countdown") == {thirteen: 1}


def test_an_opposite_setup_erases_the_countdown():
    # The buy countdown has three bars when a nine-bar rally completes a sell setup (index 25).
    # The decline after it has no price flip, so no new buy setup: without the erasure, the old
    # count would reach 13 at index 36.
    fall, rally = [107.0 - i for i in range(6, 17)], [95.0 + i for i in range(9)]
    s = td_sequential(bars(RISE + fall + rally + [102.0 - i for i in range(15)]))
    assert at(s, "setup") == {14: 1, 25: -1}
    assert not at(s, "countdown")


def test_an_interrupted_setup_is_cancelled():
    closes = RISE + [107.0 - i for i in range(6, 14)] + [200]  # eight bars, then a break
    assert not at(td_sequential(bars(closes)), "setup")


def test_td_sequential_is_causal():
    hourly = resample(walk(40_000, timedelta(minutes=1)), "1h")
    signals = td_sequential(hourly)
    assert signals["setup"].abs().sum() > 5  # the check must see events
    assert_causal(td_sequential, hourly, TD)

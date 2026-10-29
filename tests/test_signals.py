from datetime import timedelta

import numpy as np
import polars as pl
import pytest

from src.bars import resample
from src.signals import (
    FIB,
    TD,
    excess,
    h2a_rows,
    h2b_rows,
    h3_rows,
    retracements,
    signed,
    swings,
    synthetic,
    td_sequential,
    touch_events,
    touches,
    zigzag,
)
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


def test_zigzag_pivots_wait_for_a_k_atr_reversal():
    # ATR 1, k 2. Bar 1 rises 2 from bar 0's low: low pivot at 0. Bar 3's low is 2 under bar 2's
    # high. Bar 8 sets a new high with a low far below it, but cannot confirm its own high; bar 9
    # does, with the ATR of bar 8 (that of bar 9, 5, would not).
    high = [10.5, 12.5, 14.5, 13.5, 12.5, 14.0, 15.5, 16.5, 17.0, 16.0]
    low = [9.5, 11.5, 13.5, 12.5, 11.5, 13.0, 15.0, 16.0, 14.0, 15.0]
    atr = np.array([1.0] * 9 + [5.0])
    assert swings(np.array(high), np.array(low), atr, 2) == [
        (0, -1, 1),
        (2, 1, 3),
        (4, -1, 5),
        (8, 1, 9),
    ]


@pytest.mark.parametrize("k", [2, 3])
def test_zigzag_is_causal(k):
    hourly = resample(walk(40_000, timedelta(minutes=1)), "1h")

    def last_pivot(b: pl.DataFrame) -> pl.DataFrame:
        p = zigzag(b, k).select("symbol", "confirmed_at", "price", "kind", pivot="time")
        return b.sort("time").join_asof(
            p.sort("confirmed_at"),
            left_on="time",
            right_on="confirmed_at",
            by="symbol",
            check_sortedness=False,
        )

    assert last_pivot(hourly)["price"].n_unique() > 10  # the check must see pivots
    assert_causal(last_pivot, hourly, ["price", "kind", "pivot"])


def test_retracement_depth_and_the_excess_around_a_level():
    pivots = pl.DataFrame(
        {"symbol": "BTCUSDT", "time": [T0 + timedelta(hours=i) for i in range(4)],
         "price": [100.0, 110.0, 105.0, 112.0], "kind": [-1, 1, -1, 1],
         "confirmed_at": [T0 + timedelta(hours=i + 2) for i in range(4)]}
    )  # fmt: skip
    r = retracements(pivots)
    assert r["r"].to_list() == [0.5, 1.4]  # |110 - 105| / |110 - 100|, |105 - 112| / |105 - 110|
    assert r["time"].to_list() == [T0 + timedelta(hours=4), T0 + timedelta(hours=5)]
    depth = pl.DataFrame({"r": [0.5, 0.51, 0.45, 0.55, 0.6, 0.3]})
    assert depth.select(excess(0.5))["r"].to_list() == [1, 1, -0.5, -0.5, 0, 0]


def test_synthetic_bars_reuse_whole_bars_relative_to_the_previous_close():
    hourly = resample(walk(6000, timedelta(minutes=1)), "1h").select(
        "symbol", "time", "open", "high", "low", "close"
    )
    fake = synthetic(hourly, np.random.default_rng(0))
    assert fake.height == hourly.height - 1 and fake["time"].equals(hourly["time"][1:])

    def shapes(b: pl.DataFrame) -> set:
        prev = pl.col("close").shift(1)
        rel = pl.concat_list(
            [(pl.col(c) / prev).round(8) for c in ("open", "high", "low", "close")]
        )
        return set(map(tuple, b.select(x=rel).drop_nulls()["x"].to_list()))

    assert shapes(fake) <= shapes(hourly)
    assert not fake["close"].equals(hourly["close"][1:])


def test_touches_wait_for_the_low_and_restart_on_a_new_high():
    # A low at bar 0 (100) is confirmed at bar 1. Bar 2 sets the high (110) and touches nothing.
    # Bar 3 reaches 0.382 (106.18); bar 4, 0.45 and 0.5. Bar 5 sets a new high (111): a new
    # impulse, so its low touches nothing, and bar 7 touches its levels again down to 0.618.
    high = np.array([101.0, 104, 110, 109, 108, 111, 110, 109])
    low = np.array([100.0, 102, 105, 106, 104.9, 103, 106.9, 104])
    hits = touches(high, low, [(0, 1)], [0.382, 0.45, 0.5, 0.55, 0.618, 0.70])
    assert hits == [(3, 0.382), (4, 0.45), (4, 0.5), (7, 0.382), (7, 0.45), (7, 0.5), (7, 0.55),
                    (7, 0.618)]  # fmt: skip


@pytest.mark.parametrize("k", [2, 3])
def test_touch_events_are_causal(k):
    hourly = resample(walk(40_000, timedelta(minutes=1)), "1h")

    def per_bar(b: pl.DataFrame) -> pl.DataFrame:
        e = (
            touch_events(b, k)
            .group_by("symbol", "time")
            .agg(n=pl.len(), fib=pl.col("level").is_in(FIB).sum(), side=pl.col("direction").sum())
        )
        return b.join(e, on=["symbol", "time"], how="left")

    assert per_bar(hourly)["n"].sum() > 50  # the check must see touches
    assert_causal(per_bar, hourly, ["n", "fib", "side"])


def test_the_h2_cells_run_end_to_end_on_a_random_walk():
    hourly = resample(walk(200_000, timedelta(minutes=1)), "1h")
    rng = np.random.default_rng(0)
    cands = hourly.select(
        "symbol", "time", month=pl.col("time").dt.truncate("1mo"), cell=pl.lit("1/0"),
        atr_pct=pl.lit(0.01), r4=pl.lit(rng.normal(size=hourly.height)),
    ).with_columns(r12=pl.col("r4"), r24=pl.col("r4"))  # fmt: skip
    years = pl.Series([2024])
    real = retracements(zigzag(hourly, 2)).with_columns(month=pl.col("time").dt.truncate("1mo"))
    fakes = [retracements(zigzag(synthetic(hourly, rng), 2)) for _ in range(2)]
    for row in h2a_rows("1h", 2, real, fakes, years) + h2b_rows(
        "1h", 2, touch_events(hourly, 2), cands, years
    ):
        assert 0 < row["p"] <= 1 and row["n"] > 0


def test_signed_rsi_is_positive_when_mean_reversion_supports_the_trade():
    events = pl.DataFrame({"direction": [1, -1, 1], "rsi": [30.0, 80.0, None]})
    assert signed(events)["s"].to_list() == [20.0, 30.0]  # warming-up RSI is dropped


def test_h3_recovers_a_planted_slope_within_regime_cells():
    # Each event's forward return rises 0.02 ATR per point of s, on top of a cell-level offset in
    # s that the within-cell demeaning must remove.
    rng = np.random.default_rng(0)
    n = 20_000
    cell = np.where(np.arange(n) % 2 == 0, "1/0", "-1/0")
    s = rng.uniform(-30, 30, n) + np.where(cell == "1/0", 15.0, -15.0)
    time = [T0 + timedelta(hours=i) for i in range(n)]
    cands = (
        pl.DataFrame({"symbol": "BTCUSDT", "time": time, "cell": cell})
        .with_columns(
            month=pl.col("time").dt.truncate("1mo"),
            r4=pl.Series(0.02 * s + rng.normal(0, 1, n)),
        )
        .with_columns(r12=pl.col("r4"), r24=pl.col("r4"))
    )
    events = cands.select("symbol", "time", direction=pl.lit(1), s=pl.Series(s))
    rows = h3_rows("1h", "planted", events, cands, pl.Series([2022]))
    assert rows[0]["effect"] == pytest.approx(0.02, abs=0.003) and rows[0]["p"] < 0.01
    assert rows[0]["supportive_n"] + rows[0]["neutral_n"] + rows[0]["opposing_n"] == n

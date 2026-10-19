from datetime import UTC, datetime, timedelta

import polars as pl

from src.quality import check, classify, funding_steps


def bars(minutes: list[int], volume: list[float], high: list[float] | None = None) -> pl.DataFrame:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    n = len(minutes)
    return pl.DataFrame({
        "open_time": [t0 + timedelta(minutes=m) for m in minutes],
        "open": [1.0] * n, "high": high or [2.0] * n, "low": [0.5] * n,
        "close": [1.0] * n, "volume": volume,
    })  # fmt: skip


def test_gaps_duplicates_and_bad_bars_are_counted():
    # 3 and 4 missing, 5 duplicated, last bar's high below its open
    summary, gaps, _ = check(bars([0, 1, 2, 5, 5, 6], [1.0, 0, 1, 1, 1, 1], [2.0] * 5 + [0.5]))
    assert gaps.rows() == [(datetime(2024, 1, 1, 0, 3, tzinfo=UTC), 2)]
    assert (summary["duplicates"], summary["missing_minutes"]) == (1, 2)
    assert (summary["bad_ohlc"], summary["zero_volume"]) == (1, 1)


def test_only_long_zero_volume_runs_are_stalls():
    volume = [1.0] + [0.0] * 5 + [1.0] + [0.0] * 4 + [1.0]  # a run of 5, then a run of 4
    _, _, stalls = check(bars(list(range(len(volume))), volume))
    assert stalls.rows() == [(datetime(2024, 1, 1, 0, 1, tzinfo=UTC), 5)]


def test_market_wide_means_most_symbols_are_inside_an_event_at_its_first_minute():
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    m, d = timedelta(minutes=1), timedelta(days=1)
    events = pl.DataFrame({
        "start": [t0, t0, t0 + m, t0 + d, t0 + 2 * d],  # outage with a staggered start, a lone
        "minutes": [10, 10, 10, 10, 14400],           # stall, and a delisted coin's long stall
        "symbol": ["A", "B", "C", "A", "D"],
    })  # fmt: skip
    summary = pl.DataFrame({"first": [t0] * 4, "last": [t0 + 30 * d] * 4})
    assert classify(events, summary)["market_wide"].to_list() == [True, True, True, False, False]


def test_funding_steps_flag_only_what_neither_interval_explains():
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    hours = [0, 8, 16, 20, 24, 32]  # 8h, switch to 4h, 4h, then a missed 28:00 settlement
    funding = pl.DataFrame({
        "symbol": ["A"] * 6, "time": [t0 + timedelta(hours=h) for h in hours],
        "interval_hours": [8, 8, 4, 4, 4, 4], "funding_rate": [0.0001] * 6,
    })  # fmt: skip
    assert funding_steps(funding)["time"].to_list() == [t0 + timedelta(hours=32)]

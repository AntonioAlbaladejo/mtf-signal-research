import random
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from src.bars import asof, resample
from src.indicators import atr, ema, rsi
from src.regime import r0
from tests.causality import assert_causal

T0 = datetime(2024, 1, 1, tzinfo=UTC)


def walk(n: int, step: timedelta, symbol: str = "BTCUSDT", seed: int = 1) -> pl.DataFrame:
    """A random-walk kline series; bars 58 and 59 are untraded."""
    rng, price, rows = random.Random(seed), 100.0, []
    for i in range(n):
        o, price = price, price * (1 + rng.gauss(0, 0.002))
        hi, lo = max(o, price) + 0.01, min(o, price) - 0.01
        rows.append((symbol, T0 + i * step, o, hi, lo, price, 0.0 if i in (58, 59) else 1.0))
    cols = ["symbol", "open_time", "open", "high", "low", "close", "volume"]
    return pl.DataFrame(rows, schema=cols, orient="row").with_columns(
        quote_volume=pl.col("volume"),
        count=pl.lit(1),
        taker_buy_volume=pl.lit(0.0),
        taker_buy_quote_volume=pl.lit(0.0),
    )


def test_resample_aggregates_and_indexes_by_close():
    m = walk(120, timedelta(minutes=1))
    h = resample(m, "1h")
    first = h.row(0, named=True)
    assert h["time"].to_list() == [T0 + timedelta(hours=1), T0 + timedelta(hours=2)]
    assert (first["open"], first["close"]) == (m["open"][0], m["close"][59])
    assert (first["high"], first["low"]) == (m["high"].head(60).max(), m["low"].head(60).min())
    assert h["minutes"].to_list() == [60, 60]


def test_asof_never_uses_a_bar_still_forming():
    m = walk(24 * 60, timedelta(minutes=1))
    joined = asof(resample(m, "15m"), resample(m, "4h").with_columns(mark="time"), ["mark"], "4h")

    def seen_at(hours: float) -> datetime:
        return joined.filter(pl.col("time") == T0 + timedelta(hours=hours))["mark_4h"].item()

    assert seen_at(10.25) == T0 + timedelta(hours=8)
    assert seen_at(12) == T0 + timedelta(hours=12)  # closed exactly then: usable


def test_indicators_are_causal_and_warm_up():
    def features(b: pl.DataFrame) -> pl.DataFrame:
        return b.sort("symbol", "time").with_columns(
            ema=ema(pl.col("close"), 20).over("symbol"),
            atr=atr(14).over("symbol"),
            rsi=rsi(14).over("symbol"),
        )

    bars = resample(walk(3000, timedelta(minutes=1)), "15m")
    assert_causal(features, bars, ["ema", "atr", "rsi"])
    f = features(bars)
    assert f["ema"].head(19).is_null().all() and f["ema"][19] is not None
    assert f["atr"].head(13).is_null().all() and f["atr"][13] is not None


def test_rsi_extremes():
    rising = pl.DataFrame({"close": [float(i) for i in range(1, 60)]})
    assert rising.select(rsi(14))[-1].item() == pytest.approx(100)
    zigzag = pl.DataFrame({"close": [100.0 + i % 2 for i in range(200)]})
    assert zigzag.select(rsi(14))[-1].item() == pytest.approx(50, abs=2)


def test_r0_is_causal_and_needs_its_warm_up():
    raw = pl.concat(
        [walk(400 * 24, timedelta(hours=1), s, seed) for s, seed in (("A", 1), ("B", 2))]
    )
    hourly = resample(raw, "1h")

    def regime(b: pl.DataFrame) -> pl.DataFrame:
        return r0(b, resample(b, "4h"), resample(b, "1d"))

    assert_causal(regime, hourly, ["trend", "vol", "cell"], cuts=3)
    cells = regime(hourly)
    assert cells.filter(pl.col("time") < T0 + timedelta(days=179))["vol"].is_null().all()
    assert cells.filter(pl.col("time") > T0 + timedelta(days=200))["cell"].null_count() == 0


def test_the_causality_check_catches_a_leak():
    bars = resample(walk(3000, timedelta(minutes=1)), "15m")
    with pytest.raises(AssertionError, match="depend on data after"):
        assert_causal(lambda b: b.with_columns(peek=pl.col("close").shift(-1)), bars, ["peek"])

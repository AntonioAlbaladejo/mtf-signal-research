"""Pre-registered signals (HYPOTHESES.md) and the runs that test them.

Signals are computed per bar from a symbol's own past and returned as +1 (buy), -1 (sell) or 0,
so that `tests/causality.py` can check them like any other feature.

    uv run python -m src.signals H1    # tests and logs H1 (run on a clean, committed tree)
    uv run python -m src.signals H2    # tests and logs H2a and H2b
"""

import argparse

import numpy as np
import polars as pl

from src import registry
from src.data import scan
from src.events import HORIZONS, OUT, breakdown, complete_years, diffs, same_sign, study
from src.indicators import atr
from src.stats import bootstrap_difference, bootstrap_test, fdr
from src.universe import UNIVERSE

TD = ["setup", "perfected", "countdown"]
RECYCLE = 1.618
FIB, CONTROL = [0.382, 0.5, 0.618], [0.45, 0.55, 0.70]
SYNTHETIC, BLOCK = 20, 24  # H2a null 2: replicates, and bars per resampled block


def setup_counts(close: np.ndarray) -> np.ndarray:
    """Bar number within a TD Buy Setup, 0 outside one.

    A setup is a run of closes below the close four bars earlier whose first bar is a bearish
    price flip: the close before it was above its own close four bars earlier. The count runs past
    nine until the run breaks; only a new flip starts another setup.
    """
    down, up = np.zeros(len(close), bool), np.zeros(len(close), bool)
    down[4:], up[4:] = close[4:] < close[:-4], close[4:] > close[:-4]
    count = np.zeros(len(close), np.int64)
    for t in range(1, len(close)):
        if down[t] and (up[t - 1] or count[t - 1]):
            count[t] = count[t - 1] + 1
    return count


def td_buy(high: np.ndarray, low: np.ndarray, close: np.ndarray, sells: np.ndarray):
    """TD Buy Setup 9, perfected setup 9 and TD Buy Countdown 13 (Perl, 2008), as boolean arrays.

    `sells` marks the bars where a TD Sell Setup reaches nine. Countdown starts on setup bar nine
    inclusive and counts closes at or below the low two bars earlier. Bar 13 also needs its low at
    or below the close of countdown bar 8; otherwise it is deferred to the next bar meeting both.
    A developing countdown is erased by a completed sell setup or by a true low above the highest
    true high of its setup (TDST). A new buy setup restarts it when its true range is at least
    that of the active setup and below 1.618 times it; otherwise the active setup stays. A setup
    extending to 18 bars restarts it on that bar.
    """
    prev = np.r_[close[0], close[:-1]]
    true_high, true_low = np.maximum(high, prev), np.minimum(low, prev)
    count = setup_counts(close)
    setup = count == 9
    perfected = setup.copy()
    for t in np.flatnonzero(setup):
        perfected[t] = min(low[t - 1], low[t]) <= min(low[t - 3], low[t - 2])
    countdown = np.zeros(len(close), bool)
    active, start, k, tdst, top, bottom, close8 = False, -1, 0, 0.0, 0.0, 0.0, 0.0
    for t in range(2, len(close)):
        if active and (sells[t] or true_low[t] > tdst):
            active = False
        if active and t - count[t] + 1 == start:  # the active setup is still extending
            top, bottom = max(top, true_high[t]), min(bottom, true_low[t])
        if count[t] == 9 or (count[t] == 18 and active):
            s = t - count[t] + 1
            hi, lo = true_high[s : t + 1].max(), true_low[s : t + 1].min()
            old = top - bottom
            if not active or count[t] == 18 or old <= hi - lo < RECYCLE * old:
                active, start, k, tdst, top, bottom = True, s, 0, hi, hi, lo
        if active and close[t] <= low[t - 2]:
            if k < 12:
                k += 1
                close8 = close[t] if k == 8 else close8
            elif low[t] <= close8:
                countdown[t], active = True, False
    return setup, perfected, countdown


def td_sequential(bars: pl.DataFrame) -> pl.DataFrame:
    """H1 signals per bar: setup 9, perfected setup 9 and countdown 13; sells are the mirror."""
    out = []
    for _, b in bars.sort("symbol", "time").group_by("symbol", maintain_order=True):
        high, low, close = (b[c].to_numpy() for c in ("high", "low", "close"))
        buy_nines, sell_nines = setup_counts(close) == 9, setup_counts(-close) == 9
        buy = td_buy(high, low, close, sell_nines)
        sell = td_buy(-low, -high, -close, buy_nines)
        out.append(
            b.select("symbol", "time").with_columns(
                pl.Series(name, x.astype(np.int8) - y.astype(np.int8))
                for name, x, y in zip(TD, buy, sell, strict=True)
            )
        )
    return pl.concat(out)


def swings(high: np.ndarray, low: np.ndarray, atr_: np.ndarray, k: float) -> list[tuple]:
    """Causal ATR ZigZag: (extreme bar, kind +1 high / -1 low, confirming bar) of each pivot.

    A high is confirmed by the first later bar whose low is k·ATR below it, ATR being the value at
    the high's bar; lows mirror it. A bar that sets a new extreme cannot also confirm it, because
    the order of its high and low is unknown. Bars with ATR still warming up are skipped.
    """
    pivots, kind, ext, hi, lo = [], 0, -1, -1, -1
    for t in range(len(high)):
        if np.isnan(atr_[t]):
            continue
        if kind == 0:  # before the first pivot, both extremes are tracked
            hi = t if hi < 0 or high[t] > high[hi] else hi
            lo = t if lo < 0 or low[t] < low[lo] else lo
            if hi != t and low[t] <= high[hi] - k * atr_[hi]:
                pivots.append((hi, 1, t))
                kind, ext = -1, t
            elif lo != t and high[t] >= low[lo] + k * atr_[lo]:
                pivots.append((lo, -1, t))
                kind, ext = 1, t
        elif kind == 1:
            if high[t] > high[ext]:
                ext = t
            elif low[t] <= high[ext] - k * atr_[ext]:
                pivots.append((ext, 1, t))
                kind, ext = -1, t
        elif low[t] < low[ext]:
            ext = t
        elif high[t] >= low[ext] + k * atr_[ext]:
            pivots.append((ext, -1, t))
            kind, ext = 1, t
    return pivots


def by_symbol(bars: pl.DataFrame, k: float):
    """(symbol, times, highs, lows, swings) for each symbol in `bars`."""
    bars = bars.sort("symbol", "time").with_columns(atr=atr(14).over("symbol"))
    for (symbol,), b in bars.group_by("symbol", maintain_order=True):
        high, low = b["high"].to_numpy(), b["low"].to_numpy()
        yield (
            symbol,
            b["time"],
            high,
            low,
            swings(high, low, b["atr"].fill_null(np.nan).to_numpy(), k),
        )


def zigzag(bars: pl.DataFrame, k: float) -> pl.DataFrame:
    """Pivots per symbol: time and price of the extreme, kind, and `confirmed_at`, the close of
    the bar that confirmed it. No signal may use a pivot before its `confirmed_at`."""
    out = []
    for symbol, time, high, low, p in by_symbol(bars, k):
        ext, kind, conf = (np.array([x[i] for x in p], dtype=np.int64) for i in range(3))
        out.append(
            pl.DataFrame(
                {
                    "symbol": [symbol] * len(p),
                    "time": time.gather(ext),
                    "price": np.where(kind == 1, high[ext], low[ext]),
                    "kind": kind,
                    "confirmed_at": time.gather(conf),
                }
            )
        )
    return pl.concat(out)


def retracements(pivots: pl.DataFrame) -> pl.DataFrame:
    """Depth r = |B − C| / |B − A| of each completed retracement, dated at C's confirmation."""
    a, b = (pl.col("price").shift(n).over("symbol") for n in (2, 1))
    return (
        pivots.sort("symbol", "time")
        .select("symbol", time="confirmed_at", r=(b - pl.col("price")).abs() / (b - a).abs())
        .drop_nulls("r")
    )


def excess(level: float) -> pl.Expr:
    """1 for r within 0.02 of `level`, -1/2 in either adjacent window of the same width: its mean
    is the window's share of retracements minus the mean share of its two neighbours (H2a)."""
    d = pl.col("r") - level
    beside = ((d >= -0.06) & (d < -0.02)) | ((d > 0.02) & (d <= 0.06))
    return (d.abs() <= 0.02).cast(pl.Float64) - 0.5 * beside.cast(pl.Float64)


def synthetic(bars: pl.DataFrame, rng: np.random.Generator) -> pl.DataFrame:
    """H2a's null 2: each symbol's bars rebuilt from blocks of BLOCK consecutive bars drawn with
    replacement, every bar kept as open, high, low and close relative to the previous close.
    Volatility survives within a block; any memory of price levels does not."""
    out = []
    for (symbol,), b in bars.sort("symbol", "time").group_by("symbol", maintain_order=True):
        c = b["close"].to_numpy()
        rel = np.stack([b[x].to_numpy()[1:] / c[:-1] for x in ("open", "high", "low", "close")])
        n = rel.shape[1]
        size = min(BLOCK, n)
        starts = rng.integers(0, n - size + 1, size=-(-n // size))
        rel = rel[:, (starts[:, None] + np.arange(size)).ravel()[:n]]
        close = c[0] * np.cumprod(rel[3])
        prev = np.r_[c[0], close[:-1]]
        out.append(
            pl.DataFrame(
                {
                    "symbol": [symbol] * n,
                    "time": b["time"][1:],
                    "open": rel[0] * prev,
                    "high": rel[1] * prev,
                    "low": rel[2] * prev,
                    "close": close,
                }
            )  # fmt: skip
        )
    return pl.concat(out)


def touches(high: np.ndarray, low: np.ndarray, lows: list[tuple], levels: list[float]) -> list:
    """(bar, level) of each first touch of an up impulse's retracement levels.

    An impulse runs from a confirmed low, given as (extreme bar, confirming bar), to the highest
    high since, up to the previous bar. A bar that sets a new high starts a new impulse and touches
    nothing; so does the confirmation of a new low. Each level is touched once per impulse.
    """
    out, j, a, top, touched = [], 0, np.nan, np.nan, set()
    for t in range(len(high)):
        while j < len(lows) and lows[j][1] < t:  # confirmed by an earlier close
            a, top, touched = low[lows[j][0]], high[lows[j][0] + 1 : t].max(), set()
            j += 1
        if np.isnan(a):
            continue
        if high[t] > top:
            top, touched = high[t], set()
            continue
        for r in levels:
            if r not in touched and low[t] <= top - r * (top - a):
                out.append((t, r))
                touched.add(r)
    return out


def touch_events(bars: pl.DataFrame, k: float) -> pl.DataFrame:
    """H2b events: symbol, time, direction (+1 for an up impulse, -1 down) and the level touched.
    Down impulses are up impulses of the mirrored prices."""
    levels, out = sorted(FIB + CONTROL), []
    for symbol, time, high, low, p in by_symbol(bars, k):
        lows, highs = ([(e, c) for e, kind, c in p if kind == s] for s in (-1, 1))
        for direction, hits in (
            (1, touches(high, low, lows, levels)),
            (-1, touches(-low, -high, highs, levels)),
        ):
            out.append(
                pl.DataFrame(
                    {
                        "symbol": [symbol] * len(hits),
                        "time": time.gather([t for t, _ in hits]),
                        "direction": [direction] * len(hits),
                        "level": [r for _, r in hits],
                    },
                    schema_overrides={"direction": pl.Int64, "level": pl.Float64},
                )  # fmt: skip
            )
    return pl.concat(out)


def h1() -> None:
    """54 cells: {setup 9, perfected setup 9, countdown 13} × {buy, sell} × timeframe × horizon."""
    rows = []
    for tf in HORIZONS:
        cands = pl.read_parquet(OUT / f"candidates_{tf}.parquet")
        symbols = cands["symbol"].unique().sort().to_list()
        bars = scan(f"bars/{tf}", symbols).select("symbol", "time", "high", "low", "close")
        signals = td_sequential(bars.collect())
        for signal in TD:
            for direction in (1, -1):
                events = signals.filter(pl.col(signal) == direction).select(
                    "symbol", "time", direction=pl.lit(direction)
                )
                matched = events.join(cands, on=["symbol", "time"])
                for row in study(events, cands, tf).to_dicts():
                    r = pl.col("direction") * pl.col(f"r{row['horizon']}") * pl.col("atr_pct")
                    gross = matched.select(r.mean() * 1e4).item()  # in the predicted direction
                    rows.append({"tf": tf, "signal": signal, "direction": direction, **row,
                                 "gross_bps": gross})  # fmt: skip
    for row, discovery in zip(rows, fdr([row.get("p", 1.0) for row in rows]), strict=True):
        row["fdr"] = discovery
    config = {"definition": "TD Sequential, Perl (2008)", "alternative": "greater", "reps": 2000,
              "seed": 0, "fdr_q": 0.05}  # fmt: skip
    registry.log("trial", "H1", config, {"rows": rows})
    columns = ["tf", "signal", "direction", "horizon", "n", "effect", "ci_low", "ci_high", "p",
               "gross_bps", "years_same_sign", "assets_same_sign", "fdr"]  # fmt: skip
    with pl.Config(tbl_rows=-1, tbl_cols=-1):
        print(pl.DataFrame(rows).select(columns))


def h2a_rows(tf: str, k: int, real: pl.DataFrame, fakes: list, years: pl.Series) -> list[dict]:
    """Per Fibonacci level: the excess against both nulls; the cell's p is the larger p."""
    rows = []
    for level in FIB:
        null = float(np.mean([f.select(excess(level).mean()).item() for f in fakes]))
        d = real.select("symbol", "month", v=excess(level)).with_columns(diff=pl.col("v") - null)
        plain, net = (bootstrap_test(d[c], d["month"]) for c in ("v", "diff"))
        row = {
            "tf": tf, "k": k, "level": level, "n": net["n"],
            "share": real.select(((pl.col("r") - level).abs() <= 0.02).mean()).item(),
            "excess": plain["effect"], "p1": plain["p"], "synthetic_excess": null,
            "effect": net["effect"], "ci_low": net["ci_low"], "ci_high": net["ci_high"],
            "p2": net["p"], "p": max(plain["p"], net["p"]),
        }  # fmt: skip
        row |= same_sign(d, net["effect"], years)
        row |= breakdown(d, lambda g: bootstrap_test(g["diff"], g["month"]))
        rows.append(row)
    return rows


IS_FIB = pl.col("level").is_in(FIB)


def contrast(d: pl.DataFrame) -> dict:
    """Fibonacci touches minus control touches, on event-minus-baseline returns (H2b)."""
    f, c = d.filter(IS_FIB), d.filter(~IS_FIB)
    return bootstrap_difference(f["diff"], f["month"], c["diff"], c["month"])


def h2b_rows(tf: str, k: int, events: pl.DataFrame, cands: pl.DataFrame, years) -> list[dict]:
    """Per horizon: the Fibonacci-minus-control contrast, plus descriptions of both sides."""
    trend = pl.col("cell").str.split("/").list.first().cast(pl.Int64)
    events = events.join(cands.select("symbol", "time", "cell"), on=["symbol", "time"])
    events = events.filter(trend == pl.col("direction")).drop("cell")
    diff, level = pl.col("diff"), pl.col("level")
    rows = []
    for h in HORIZONS[tf]:
        d = diffs(events, cands, h)
        row = {"tf": tf, "k": k, "horizon": h} | contrast(d)
        gap = diff.filter(IS_FIB).mean() - diff.filter(~IS_FIB).mean()
        row |= same_sign(d, row["effect"], years, gap) | breakdown(d, contrast)
        gross = pl.col("direction") * pl.col(f"r{h}") * pl.col("atr_pct") * 1e4
        described = {
            "fib_effect": diff.filter(IS_FIB).mean(),
            "control_effect": diff.filter(~IS_FIB).mean(),
            "fib_gross_bps": gross.filter(IS_FIB).mean(),  # for the economic threshold
        } | {  # pairs of neighbouring levels, descriptive only
            f"pair_{a}_{b}": diff.filter(level == a).mean() - diff.filter(level == b).mean()
            for a, b in zip(FIB, CONTROL, strict=True)
        }
        rows.append(row | d.select(**described).row(0, named=True))
    return rows


def h2() -> None:
    """H2a: 3 levels × k × timeframe. H2b: k × timeframe × horizon. One FDR family each."""
    universe = pl.read_parquet(UNIVERSE).select("symbol", "month")
    symbols = universe["symbol"].unique().sort().to_list()

    def members(r: pl.DataFrame) -> pl.DataFrame:
        month = pl.col("time").dt.truncate("1mo")
        return r.with_columns(month=month).join(universe, on=["symbol", "month"])

    rows = {"H2a": [], "H2b": []}
    for tf in ("1h", "4h"):
        cands = pl.read_parquet(OUT / f"candidates_{tf}.parquet")
        years = complete_years(cands)
        bars = scan(f"bars/{tf}", symbols).select("symbol", "time", "open", "high", "low", "close")
        bars = bars.collect()
        rng, fakes = np.random.default_rng(0), {2: [], 3: []}
        for _ in range(SYNTHETIC):
            s = synthetic(bars, rng)
            for k, f in fakes.items():
                f.append(members(retracements(zigzag(s, k))))
        for k in (2, 3):
            real = members(retracements(zigzag(bars, k)))
            rows["H2a"] += h2a_rows(tf, k, real, fakes[k], years)
            rows["H2b"] += h2b_rows(tf, k, touch_events(bars, k), cands, years)
    config = {"fib": FIB, "control": CONTROL, "k": [2, 3], "synthetic": SYNTHETIC, "block": BLOCK,
              "alternative": "greater", "reps": 2000, "seed": 0, "fdr_q": 0.05}  # fmt: skip
    for name, rs in rows.items():
        for row, discovery in zip(rs, fdr([row["p"] for row in rs]), strict=True):
            row["fdr"] = discovery
        registry.log("trial", name, config, {"rows": rs})
        with pl.Config(tbl_rows=-1, tbl_cols=-1):
            print(name, pl.DataFrame(rs))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("hypothesis", choices=["H1", "H2"])
    {"H1": h1, "H2": h2}[ap.parse_args().hypothesis]()


if __name__ == "__main__":
    main()

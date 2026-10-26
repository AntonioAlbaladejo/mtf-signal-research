"""Pre-registered signals (HYPOTHESES.md) and the runs that test them.

Signals are computed per bar from a symbol's own past and returned as +1 (buy), -1 (sell) or 0,
so that `tests/causality.py` can check them like any other feature.

    uv run python -m src.signals H1    # tests and logs H1 (run on a clean, committed tree)
"""

import argparse

import numpy as np
import polars as pl

from src import registry
from src.data import scan
from src.events import HORIZONS, OUT, study
from src.stats import fdr

TD = ["setup", "perfected", "countdown"]
RECYCLE = 1.618


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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("hypothesis", choices=["H1"])
    ap.parse_args()
    h1()


if __name__ == "__main__":
    main()

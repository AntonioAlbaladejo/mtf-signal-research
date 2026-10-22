"""Hyperliquid data from the public requester-pays archive (s3://hyperliquid-archive).

- L2 snapshots: one 20-level snapshot per coin roughly every 5.4 s since 2023-04-15.
- Asset contexts: one row per coin and minute since 2023-05-20, with mid, funding and the impact
  bid/ask prices (average fill for 20,000 USDC on BTC and ETH, 6,000 USDC elsewhere).

Downloads are billed to the caller's AWS account, so raw files are cached and each one is paid
for once. Needs the AWS CLI with credentials.

    uv run python -m src.hyperliquid gap      # writes data/hyperliquid/venue_gap.csv
    uv run python -m src.hyperliquid ctx      # writes data/hyperliquid/ctx_hourly/<day>.parquet
"""

import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import lz4.frame
import polars as pl

from src.binance import write
from src.data import DATA, HOLDOUT_START, scan

HL = DATA / "hyperliquid"
CTX_FIRST, CTX_LAST = date(2023, 5, 20), date(2026, 9, 30)  # archive start, research data end
F = pl.Float64
CTX_SCHEMA = {
    "time": pl.String, "coin": pl.String, "funding": F, "open_interest": F, "prev_day_px": F,
    "day_ntl_vlm": F, "premium": F, "oracle_px": F, "mark_px": F, "mid_px": F,
    "impact_bid_px": F, "impact_ask_px": F,
}  # fmt: skip


def cached(key: str, path: Path) -> bytes | None:
    """An archive object, downloaded once (requester pays); None if the archive lacks it."""
    if not path.exists():
        r = subprocess.run(
            ["aws", "s3", "cp", f"s3://hyperliquid-archive/{key}", "-",
             "--request-payer", "requester", "--only-show-errors"],
            capture_output=True,
        )  # fmt: skip
        if r.returncode:
            if b"(404)" in r.stderr:
                return None
            raise RuntimeError(r.stderr.decode())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_suffix(".tmp").write_bytes(r.stdout)
        path.with_suffix(".tmp").replace(path)
    return path.read_bytes()


def raw_l2(coin: str, day: date, hour: int) -> bytes | None:
    """One hour of L2 snapshots (lz4 JSON lines)."""
    key = f"market_data/{day:%Y%m%d}/{hour}/l2Book/{coin}.lz4"
    return cached(key, HL / "l2" / coin / f"{day:%Y%m%d}-{hour:02d}.lz4")


def hourly(minutes: pl.DataFrame) -> pl.DataFrame:
    """Per-minute asset contexts -> one row per coin and hour, `time` being the hour's start.

    impact_bps is the median half-spread between the impact prices, i.e. the slippage of a market
    order of the impact notional. funding is the hour's last estimate, which approximates the
    rate settled at the end of the hour. Minutes with a zero mid or impact price are dropped: the
    archive writes zeros before a listing, after a delisting, and when the book is too thin to
    fill the impact notional, which is rare (16 minutes on 2023-06-01, none since).
    """
    t = pl.col("time").str.strptime(pl.Datetime("ms", "UTC"), "%Y-%m-%dT%H:%M:%SZ")
    half_spread = (pl.col("impact_ask_px") - pl.col("impact_bid_px")) / 2 / pl.col("mid_px")
    book = pl.min_horizontal("mid_px", "impact_bid_px", "impact_ask_px") > 0
    return (
        minutes.filter(book)
        .with_columns(time=t)
        .sort("coin", "time")
        .group_by("coin", pl.col("time").dt.truncate("1h"))
        .agg(
            mid=pl.col("mid_px").last(),
            impact_bps=(half_spread * 1e4).median(),
            funding=pl.col("funding").last(),
            open_interest=pl.col("open_interest").last(),
            day_ntl_vlm=pl.col("day_ntl_vlm").last(),
        )
        .sort("coin", "time")
    )


def ctx_day(day: date) -> None:
    out = HL / "ctx_hourly" / f"{day:%Y%m%d}.parquet"
    if out.exists():
        return
    raw = cached(f"asset_ctxs/{day:%Y%m%d}.csv.lz4", HL / "ctx" / f"{day:%Y%m%d}.csv.lz4")
    if raw is not None:
        minutes = pl.read_csv(lz4.frame.decompress(raw), schema=CTX_SCHEMA, has_header=True)
        write(out, hourly(minutes))


def top_of_book(raw: bytes) -> pl.DataFrame:
    """Exchange time and best bid/ask. levels[0] are bids (descending), levels[1] asks."""
    rows = []
    for line in lz4.frame.decompress(raw).splitlines():
        d = json.loads(line)["raw"]["data"]
        bids, asks = d["levels"]
        if bids and asks:
            rows.append((d["time"], float(bids[0]["px"]), float(bids[0]["sz"]),
                         float(asks[0]["px"]), float(asks[0]["sz"])))  # fmt: skip
    return pl.DataFrame(
        rows, schema=["time", "bid_px", "bid_sz", "ask_px", "ask_sz"], orient="row"
    ).with_columns(time=pl.col("time").cast(pl.Datetime("ms")).dt.replace_time_zone("UTC"))


def venue_gap(coins: list[str]) -> pl.DataFrame:
    """Hyperliquid mid at each Binance 1m close, as bps over the Binance close.

    One hour (00:00-01:00 UTC on the 15th) per month, from the archive start to the hold-out.
    The mid comes from the last snapshot at or before the close, at most 10 s old. Hyperliquid
    settles in USDC and Binance in USDT, so the gap includes the USDC/USDT rate.
    """
    days = [date(y, m, 15) for y in range(2023, 2027) for m in range(1, 13)]
    days = [d for d in days if date(2023, 5, 1) <= d < HOLDOUT_START.date()]
    out = []
    for coin in coins:
        bars = scan("klines/1m", [f"{coin}USDT"]).select("time", "close").collect()
        for day in days:
            raw = raw_l2(coin, day, 0)
            if raw is None:
                continue
            book = top_of_book(raw).sort("time")
            hour = bars.filter(pl.col("time").dt.date() == day, pl.col("time").dt.hour() == 0)
            j = hour.sort("time").join_asof(book, on="time", strategy="backward", tolerance="10s")
            mid = (pl.col("bid_px") + pl.col("ask_px")) / 2
            out.append(
                j.drop_nulls("bid_px").select(
                    pl.lit(coin).alias("coin"),
                    "time",
                    gap_bps=(mid / pl.col("close") - 1) * 1e4,
                    spread_bps=(pl.col("ask_px") - pl.col("bid_px")) / mid * 1e4,
                )
            )
    return pl.concat(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("command", choices=["gap", "ctx"])
    ap.add_argument("--coins", nargs="+", default=["BTC", "ETH", "SOL"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.command == "ctx":
        days = [CTX_FIRST + timedelta(d) for d in range((CTX_LAST - CTX_FIRST).days + 1)]
        with ThreadPoolExecutor(a.workers) as ex:
            for i, _ in enumerate(ex.map(ctx_day, days), 1):
                if i % 100 == 0 or i == len(days):
                    print(f"  {i}/{len(days)} days", flush=True)
        return
    gap = venue_gap(a.coins)
    gap.write_csv(DATA / "hyperliquid" / "venue_gap.csv")
    q = pl.col("gap_bps").quantile
    print(
        gap.group_by("coin").agg(
            n=pl.len(),
            gap_median=pl.col("gap_bps").median(),
            gap_p5=q(0.05),
            gap_p95=q(0.95),
            abs_gap_mean=pl.col("gap_bps").abs().mean(),
            spread_median=pl.col("spread_bps").median(),
        )
    )
    print(
        gap.group_by("coin", pl.col("time").dt.year().alias("year"))
        .agg(gap_median=pl.col("gap_bps").median(), spread_median=pl.col("spread_bps").median())
        .sort("coin", "year")
    )


if __name__ == "__main__":
    main()

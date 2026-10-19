"""Hyperliquid L2 snapshots from the public requester-pays archive, and their gap to Binance.

The archive (s3://hyperliquid-archive) holds one 20-level snapshot per coin roughly every 5.4 s
since 2023-04-15. Downloads are billed to the caller's AWS account, so raw files are cached and
each one is paid for once. Needs the AWS CLI with credentials.

    uv run python -m src.hyperliquid gap      # writes data/hyperliquid/venue_gap.csv
"""

import argparse
import json
import subprocess
from datetime import date

import lz4.frame
import polars as pl

from src.data import DATA, HOLDOUT_START, scan

RAW = DATA / "hyperliquid" / "l2"


def raw_l2(coin: str, day: date, hour: int) -> bytes | None:
    """One hour of snapshots (lz4 JSON lines), cached; None if the archive lacks that hour."""
    path = RAW / coin / f"{day:%Y%m%d}-{hour:02d}.lz4"
    if not path.exists():
        key = f"s3://hyperliquid-archive/market_data/{day:%Y%m%d}/{hour}/l2Book/{coin}.lz4"
        r = subprocess.run(
            ["aws", "s3", "cp", key, "-", "--request-payer", "requester", "--only-show-errors"],
            capture_output=True,
        )
        if r.returncode:
            if b"(404)" in r.stderr:
                return None
            raise RuntimeError(r.stderr.decode())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_suffix(".tmp").write_bytes(r.stdout)
        path.with_suffix(".tmp").replace(path)
    return path.read_bytes()


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
    ap.add_argument("command", choices=["gap"])
    ap.add_argument("--coins", nargs="+", default=["BTC", "ETH", "SOL"])
    a = ap.parse_args()
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

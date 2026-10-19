"""Binance USDⓈ-M monthly archives (data.binance.vision) to checksum-verified Parquet.

    uv run python -m src.binance klines/1d                 # every USDT perpetual ever listed
    uv run python -m src.binance klines/1m --universe      # symbols that ever enter the universe
    uv run python -m src.binance fundingRate --universe
    uv run python -m src.binance backfill                  # 1m gaps found by src.quality

Output: data/binance/um/<dataset>/<SYMBOL>/<YYYY-MM>.parquet. Months already on disk are skipped.
"""

import argparse
import hashlib
import io
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from functools import partial
from pathlib import Path

import polars as pl

from src.data import DATA

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FILES = "https://data.binance.vision/"
PREFIX = "data/futures/um/monthly/"
OUT = DATA / "binance" / "um"
S3 = "{http://s3.amazonaws.com/doc/2006-03-01/}"

# Fixed dtypes: inference from the first rows breaks when a month starts with integer volumes.
INT, F = pl.Int64, pl.Float64
KLINE_SCHEMA = {
    "open_time": INT, "open": F, "high": F, "low": F, "close": F, "volume": F, "close_time": INT,
    "quote_volume": F, "count": INT, "taker_buy_volume": F, "taker_buy_quote_volume": F,
    "ignore": pl.String,
}  # fmt: skip
KLINE_COLUMNS = list(KLINE_SCHEMA)
FUNDING_SCHEMA = {"calc_time": INT, "funding_interval_hours": INT, "last_funding_rate": F}
# Stablecoin-vs-USDT contracts carry volume but no tradable directional signal.
STABLE_BASES = {"USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "USDE"}


def get(url: str, attempts: int = 4) -> bytes:
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or i == attempts - 1:
                raise
        except OSError:
            if i == attempts - 1:
                raise
        time.sleep(2**i)
    raise AssertionError("unreachable")


def list_s3(prefix: str, delimiter: str | None = None) -> list[str]:
    """Keys under `prefix` (or its common prefixes, with a delimiter), following pagination."""
    out, marker = [], ""
    while True:
        query = {"prefix": prefix, "marker": marker}
        if delimiter:
            query["delimiter"] = delimiter
        root = ET.fromstring(get(f"{BUCKET}?{urllib.parse.urlencode(query)}"))
        path = f"{S3}CommonPrefixes/{S3}Prefix" if delimiter else f"{S3}Contents/{S3}Key"
        page = [e.text for e in root.findall(path)]
        out += page
        if root.findtext(f"{S3}IsTruncated") != "true":
            return out
        marker = root.findtext(f"{S3}NextMarker") or page[-1]


def symbols() -> list[str]:
    """Every USDT-margined perpetual ever archived, delisted ones included (no survivorship)."""
    root = PREFIX + "klines/"
    names = [p.removeprefix(root).rstrip("/") for p in list_s3(root, "/")]
    return [
        s
        for s in names
        if s.endswith("USDT") and "_" not in s and s.removesuffix("USDT") not in STABLE_BASES
    ]


def remote(dataset: str, symbol: str) -> tuple[str, str]:
    """Remote directory and file tag: klines/1m -> klines/BTCUSDT/1m/, '1m'."""
    kind, _, interval = dataset.partition("/")
    return f"{PREFIX}{kind}/{symbol}/" + (f"{interval}/" if interval else ""), interval or kind


def months(dataset: str, symbol: str) -> list[str]:
    return sorted(k[-11:-4] for k in list_s3(remote(dataset, symbol)[0]) if k.endswith(".zip"))


def to_utc(col: str) -> pl.Expr:
    c = pl.col(col)
    # Binance moved spot archives to microseconds in 2025; guard in case futures follow.
    ms = pl.when(c > 10**14).then(c // 1000).otherwise(c)
    return ms.cast(pl.Datetime("ms")).dt.replace_time_zone("UTC")


def parse(dataset: str, symbol: str, raw: bytes) -> pl.DataFrame:
    """Archive zip to a typed frame. `time` is the bar close: bars are indexed by close."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        csv = z.read(z.namelist()[0])
    if dataset == "fundingRate":
        df = pl.read_csv(csv, schema_overrides=FUNDING_SCHEMA).select(
            time=to_utc("calc_time"),
            interval_hours="funding_interval_hours",
            funding_rate="last_funding_rate",
        )
    else:
        # Older kline files have no header row, newer ones do.
        header = csv.startswith(b"open_time")
        df = (
            pl.read_csv(csv, has_header=False, skip_rows=int(header), schema=KLINE_SCHEMA)
            .drop("close_time", "ignore")
            .with_columns(open_time=to_utc("open_time"))
            .with_columns(time=pl.col("open_time").dt.offset_by(dataset.split("/")[1]))
        )
    return df.with_columns(symbol=pl.lit(symbol))


def verified(path: str) -> bytes:
    """Download an archive file and check it against its published SHA-256."""
    url = FILES + urllib.parse.quote(path)  # quoted because non-ASCII symbols exist
    raw = get(url)
    if hashlib.sha256(raw).hexdigest() != get(url + ".CHECKSUM").split()[0].decode():
        raise ValueError(f"checksum mismatch: {url}")
    return raw


def write(out: Path, df: pl.DataFrame) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        df.write_parquet(f)
        f.flush()
        os.fsync(f.fileno())  # a hard reset must not leave a renamed but unwritten file
    tmp.replace(out)  # atomic, so an interrupted run never leaves a half-written month


def fetch(dataset: str, symbol: str, month: str) -> None:
    out = OUT / dataset / symbol / f"{month}.parquet"
    if not out.exists():
        directory, tag = remote(dataset, symbol)
        write(out, parse(dataset, symbol, verified(f"{directory}{symbol}-{tag}-{month}.zip")))


def backfill(symbol: str, days: tuple[str, ...]) -> None:
    """Merge days of 1m bars from the daily archives into their monthly file.

    Some monthly files stop days short (2022-02 and 2022-04, for about half the symbols then
    listed); the daily archives have those days. All `days` belong to one month, so each monthly
    file is rewritten by exactly one task: two concurrent rewrites would lose one of them.
    """
    path = "data/futures/um/daily/klines/{0}/1m/{0}-1m-{1}.zip"
    bars = [parse("klines/1m", symbol, verified(path.format(symbol, d))) for d in days]
    out = OUT / "klines/1m" / symbol / f"{days[0][:7]}.parquet"
    if out.exists():
        bars.insert(0, pl.read_parquet(out))
    write(out, pl.concat(bars).unique("open_time", keep="first").sort("open_time"))


def gap_days() -> list[tuple[str, tuple[str, ...]]]:
    """(symbol, days) per monthly file touched by a gap in the latest quality report."""
    from src.quality import OUT as QUALITY

    days: dict[tuple[str, str], set[str]] = {}
    for r in pl.read_csv(QUALITY / "gaps.csv", try_parse_dates=True).iter_rows(named=True):
        first = r["start"].date()
        last = (r["start"] + timedelta(minutes=r["minutes"] - 1)).date()
        for i in range((last - first).days + 1):
            day = f"{first + timedelta(days=i)}"
            days.setdefault((r["symbol"], day[:7]), set()).add(day)
    return [(s, tuple(sorted(d))) for (s, _), d in sorted(days.items())]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("dataset", help="klines/1d, klines/1m, fundingRate, or backfill")
    ap.add_argument("--symbols", nargs="+")
    ap.add_argument("--universe", action="store_true", help="symbols that ever enter the universe")
    ap.add_argument("--workers", type=int, default=4, help="parallel downloads (default 4)")
    a = ap.parse_args()

    with ThreadPoolExecutor(a.workers) as ex:
        if a.dataset == "backfill":
            job, tasks = backfill, gap_days()
        else:
            if a.universe:
                from src.universe import UNIVERSE

                syms = sorted(pl.read_parquet(UNIVERSE)["symbol"].unique())
            else:
                syms = a.symbols or symbols()
            listed = ex.map(partial(months, a.dataset), syms)
            job = partial(fetch, a.dataset)
            tasks = [(s, m) for s, ms in zip(syms, listed, strict=True) for m in ms]
        print(f"{a.dataset}: {len(tasks)} files", flush=True)

        def safe(task: tuple) -> str | None:
            try:
                job(*task)
            except Exception as e:  # collected and reported, so one bad file doesn't stop the run
                return f"{task}: {e}"
            return None

        errors = []
        for i, err in enumerate(ex.map(safe, tasks), 1):
            if err:
                errors.append(err)
            if i % 1000 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)} done, {len(errors)} errors", flush=True)
    for e in errors:
        print("ERROR", e)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()

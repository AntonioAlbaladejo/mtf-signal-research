import hashlib
import io
import zipfile

import polars as pl
import pytest

from src import binance

ROW = (
    "1577836800000,7189.43,7260.43,7170.15,7197.57,56801.3,1577836859999,"
    "409678760.5,101871,28834.2,208001969.8,0\n"
)
HEADER = ",".join(binance.KLINE_COLUMNS) + "\n"


def zipped(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", text)
    return buf.getvalue()


def parse(text: str):
    return binance.parse("klines/1m", "BTCUSDT", zipped(text))


def test_kline_files_parse_the_same_with_or_without_header():
    old, new = parse(ROW), parse(HEADER + ROW)
    assert old.equals(new)
    assert (old["time"] - old["open_time"]).item().total_seconds() == 60  # indexed by close


def test_dtypes_are_fixed_not_inferred_from_the_first_rows():
    integer_volume = ROW.replace("56801.3", "56801")
    df = parse(HEADER + integer_volume + ROW)
    assert df["volume"].to_list() == [56801.0, 56801.3]
    assert parse(integer_volume).schema == parse(ROW).schema


def test_microsecond_timestamps_are_normalised():
    assert parse(ROW.replace("1577836800000", "1577836800000000", 1)).equals(parse(ROW))


def test_bad_checksum_is_rejected_and_nothing_is_written(tmp_path, monkeypatch):
    def fake_get(url: str) -> bytes:
        return b"0" * 64 + b"  x.zip" if url.endswith("CHECKSUM") else zipped(ROW)

    monkeypatch.setattr(binance, "OUT", tmp_path)
    monkeypatch.setattr(binance, "get", fake_get)
    with pytest.raises(ValueError, match="checksum"):
        binance.fetch("klines/1m", "BTCUSDT", "2020-01")
    assert not list(tmp_path.rglob("*.parquet"))


def test_non_ascii_symbols_are_url_encoded(tmp_path, monkeypatch):
    urls = []

    def fake_get(url: str) -> bytes:
        urls.append(url)
        raise ValueError("stop")

    monkeypatch.setattr(binance, "OUT", tmp_path)
    monkeypatch.setattr(binance, "get", fake_get)
    with pytest.raises(ValueError, match="stop"):
        binance.fetch("klines/1d", "币安人生USDT", "2025-10")
    assert urls[0].isascii()


def test_backfill_merges_a_daily_file_without_duplicates(tmp_path, monkeypatch):
    day = zipped(ROW + ROW.replace("1577836800000", "1577836860000", 1))

    def fake_get(url: str) -> bytes:
        return hashlib.sha256(day).hexdigest().encode() if url.endswith("CHECKSUM") else day

    monkeypatch.setattr(binance, "OUT", tmp_path)
    monkeypatch.setattr(binance, "get", fake_get)
    month = tmp_path / "klines/1m/BTCUSDT/2020-01.parquet"
    binance.write(month, parse(ROW))
    binance.backfill("BTCUSDT", ("2020-01-01",))
    assert pl.read_parquet(month)["open_time"].dt.minute().to_list() == [0, 1]

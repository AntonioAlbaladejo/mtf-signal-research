from datetime import timedelta

import polars as pl
import pytest

from src import data


def test_scan_never_serves_the_holdout(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA", tmp_path)
    path = tmp_path / "binance" / "um" / "klines" / "1d" / "BTCUSDT"
    path.mkdir(parents=True)
    times = [data.HOLDOUT_START + timedelta(days=d) for d in (-2, -1, 0, 1)]
    pl.DataFrame({"time": times, "close": [1.0, 2.0, 3.0, 4.0]}).write_parquet(path / "m.parquet")

    served = data.scan("klines/1d").collect()
    assert served["close"].to_list() == [1.0, 2.0]
    with pytest.raises(NotImplementedError):
        data.scan("klines/1d", unseal=True)

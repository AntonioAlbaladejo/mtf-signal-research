import subprocess
from datetime import timedelta

import polars as pl
import pytest

from src import data, registry


def test_scan_never_serves_the_holdout(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA", tmp_path)
    path = tmp_path / "binance" / "um" / "klines" / "1d" / "BTCUSDT"
    path.mkdir(parents=True)
    times = [data.HOLDOUT_START + timedelta(days=d) for d in (-2, -1, 0, 1)]
    pl.DataFrame({"time": times, "close": [1.0, 2.0, 3.0, 4.0]}).write_parquet(path / "m.parquet")

    served = data.scan("klines/1d").collect()
    assert served["close"].to_list() == [1.0, 2.0]
    monkeypatch.setattr(registry, "TRIALS", tmp_path / "trials.jsonl")
    assert data.scan("klines/1d", unseal_for="H1.b").collect().height == 4
    with pytest.raises(PermissionError, match="H1"):
        data.scan("klines/1d", unseal_for="H1")
    assert [r["kind"] for r in registry.records()] == ["holdout"]


def test_registry_appends_and_stamps_the_config(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "TRIALS", tmp_path / "trials.jsonl")
    a = registry.log("trial", "H1.a", {"tf": "1h", "k": 2}, {"p": 0.2})
    b = registry.log("trial", "H1.a", {"k": 2, "tf": "1h"}, {"p": 0.3})
    assert a["config_hash"] == b["config_hash"]  # key order does not matter
    assert [r["results"]["p"] for r in registry.records()] == [0.2, 0.3]


def test_only_code_changes_make_a_run_dirty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for f in (registry.TRIALS, tmp_path / "code.py"):
        f.parent.mkdir(exist_ok=True)
        f.write_text("")
    for args in (
        ["init", "-q"],
        ["add", "."],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"],
    ):
        subprocess.run(["git", *args], check=True)
    first = registry.log("trial", "H9", {})
    second = registry.log("trial", "H9", {})  # the registry is now modified, the code is not
    (tmp_path / "code.py").write_text("x = 1\n")
    third = registry.log("trial", "H9", {})
    assert [r["dirty"] for r in (first, second, third)] == [False, False, True]

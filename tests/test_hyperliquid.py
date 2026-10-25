import json

import lz4.frame
import polars as pl

from src.hyperliquid import CTX_SCHEMA, clean, hourly, top_of_book


def snapshot(t: int, bids: list[str], asks: list[str]) -> bytes:
    levels = [[{"px": p, "sz": "1.5", "n": 1} for p in side] for side in (bids, asks)]
    data = {"coin": "BTC", "time": t, "levels": levels}
    return json.dumps({"raw": {"channel": "l2Book", "data": data}}).encode()


def test_best_bid_is_first_level_of_first_side_and_empty_sides_are_skipped():
    lines = [snapshot(1000, ["100.0", "99.0"], ["101.0", "102.0"]), snapshot(2000, [], ["101.0"])]
    raw = lz4.frame.compress(b"\n".join(lines))
    book = top_of_book(raw)
    assert book.select("bid_px", "ask_px").rows() == [(100.0, 101.0)]
    assert book["time"].dt.epoch("ms").to_list() == [1000]


def test_hourly_contexts_take_median_impact_and_last_funding():
    rows = [  # coin, minute, funding, mid, impact bid, impact ask
        ("BTC", "2024-01-01T00:00:00Z", 0.1, 100.0, 99.0, 101.0),  # half-spread 100 bps
        ("BTC", "2024-01-01T00:30:16Z", 0.2, 100.0, 99.8, 100.2),  # 20 bps, stamped late
        ("BTC", "2024-01-01T00:59:00Z", 0.3, 100.0, 99.9, 100.1),  # 10 bps
        ("BTC", "2024-01-01T01:00:00Z", 0.4, 200.0, 199.0, 201.0),
        ("BTC", "2024-01-01T01:01:00Z", 0.0, 0.0, 0.0, 0.0),  # delisted: no book, dropped
        ("ETH", "2024-01-01T00:00:00Z", 0.0, 0.0, 0.0, 0.0),
    ]
    minutes = pl.DataFrame(
        [(t, c, f, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, m, b, a) for c, t, f, m, b, a in rows],
        schema=list(CTX_SCHEMA),
        orient="row",
    )
    m = clean(minutes)
    assert m["time"].dt.strftime("%H:%M:%S").to_list() == [
        "00:00:00",
        "00:30:00",
        "00:59:00",
        "01:00:00",
    ]
    assert m["impact_bps"].round(6).to_list() == [100.0, 20.0, 10.0, 50.0]
    h = hourly(minutes)
    assert h["funding"].to_list() == [0.3, 0.4]
    assert h["mid"].to_list() == [100.0, 200.0]
    assert round(h["impact_bps"][0], 6) == 20.0

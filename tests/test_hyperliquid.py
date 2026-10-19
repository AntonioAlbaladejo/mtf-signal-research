import json

import lz4.frame

from src.hyperliquid import top_of_book


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

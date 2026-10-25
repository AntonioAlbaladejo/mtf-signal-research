"""Trading costs on Hyperliquid (PROTOCOL §6): fees, slippage from impact prices, and funding.

    uv run python -m src.costs     # maps Binance symbols to Hyperliquid coins, by price

All costs are fractions of notional. Where Hyperliquid has no data for a symbol at that time, the
symbol's median Hyperliquid slippage stands in (the upper quartile across symbols if it was never
listed), and funding comes from Binance.
"""

from datetime import timedelta

import polars as pl

from src.binance import write
from src.data import HOLDOUT_START, scan
from src.hyperliquid import HL

TAKER, MAKER = 0.00045, 0.00015  # base tier
MAPPING = HL / "mapping.parquet"


def hourly() -> pl.DataFrame:
    """Hyperliquid per coin and hour before the hold-out, like scan(); `time` is the hour's
    start, funding settles at its end."""
    lf = pl.scan_parquet(HL / "ctx_hourly" / "*.parquet")
    return lf.filter(pl.col("time") < HOLDOUT_START).collect()


def candidates(symbol: str) -> list[tuple[str, float]]:
    """Possible Hyperliquid coins for a Binance symbol, with the price factor between them."""
    base = symbol.removesuffix("USDT")
    if base.startswith("1000000"):
        return [(base, 1.0), (base[7:], 1e6)]
    if base.startswith("1000"):
        return [(base, 1.0), ("k" + base[4:], 1.0), (base[4:], 1e3)]
    return [(base, 1.0), ("k" + base, 1e-3)]


def match(binance_1h: pl.DataFrame, hl: pl.DataFrame) -> pl.DataFrame:
    """Accept a candidate coin only if its prices agree with Binance's within 2% (median).

    `binance_1h` has symbol, time (bar close), close; `hl` has coin, time (hour start), mid.
    """
    hl_end = hl.select("coin", time=pl.col("time").dt.offset_by("1h"), mid="mid")
    rows = []
    for symbol in binance_1h["symbol"].unique().sort():
        bn = binance_1h.filter(pl.col("symbol") == symbol)
        for coin, factor in candidates(symbol):
            both = bn.join(hl_end.filter(pl.col("coin") == coin), on="time")
            if both.height < 24:
                continue
            ratio = (both["mid"] * factor / both["close"]).median()
            if abs(ratio - 1) < 0.02:
                rows.append((symbol, coin, factor, both.height, ratio))
                break
    return pl.DataFrame(
        rows, schema=["symbol", "coin", "factor", "hours", "ratio"], orient="row"
    ).join(
        hl.group_by("coin").agg(
            first_hl=pl.col("time").min(),
            last_hl=pl.col("time").max(),
            median_impact_bps=pl.col("impact_bps").median(),
        ),
        on="coin",
    )


def at_minute(fills: pl.DataFrame, mapping: pl.DataFrame) -> pl.DataFrame:
    """Hyperliquid impact (coin, time, impact_bps) at the fills' minutes, before the hold-out.

    Reads only the days that have fills, never the whole minute archive.
    """
    keys = fills.join(mapping.select("symbol", "coin"), on="symbol").select("coin", "time")
    keys = keys.filter(pl.col("time") < HOLDOUT_START).unique()
    days = keys["time"].dt.date().unique()
    paths = [p for d in days if (p := HL / "ctx_minute" / f"{d:%Y%m%d}.parquet").exists()]
    if not paths:
        return keys.clear().with_columns(impact_bps=pl.lit(None, pl.Float64))
    return pl.scan_parquet(paths).join(keys.lazy(), on=["coin", "time"]).collect()


def slippage(
    fills: pl.DataFrame, hl: pl.DataFrame, mapping: pl.DataFrame, minute: pl.DataFrame
) -> pl.Series:
    """Slippage per fill (symbol, time at a minute's open) as a fraction.

    Half the impact spread at that minute (`minute`, from at_minute), else the hour's median,
    else the symbol's median, else the upper quartile across symbols. Fills cluster in fast
    minutes, where the spread is wider than the hour's median.
    """
    fallback = mapping["median_impact_bps"].quantile(0.75, interpolation="linear")
    rows = (
        fills.with_row_index("i")
        .join(mapping.select("symbol", "coin", "median_impact_bps"), on="symbol", how="left")
        .join(
            minute.select("coin", "time", minute_bps="impact_bps"), on=["coin", "time"], how="left"
        )
    )
    hit = rows.sort("time").join_asof(
        hl.select("coin", "time", "impact_bps").sort("time"),
        on="time",
        by="coin",
        strategy="backward",
        tolerance="1h",
        check_sortedness=False,
    )
    bps = pl.coalesce("minute_bps", "impact_bps", "median_impact_bps", pl.lit(fallback))
    return hit.sort("i").select(bps / 1e4).to_series().alias("slippage")


def cumulative(settlements: pl.DataFrame) -> pl.DataFrame:
    """Running sum of funding rates per symbol, from (symbol, time of settlement, rate)."""
    return settlements.sort("symbol", "time").with_columns(
        cum=pl.col("rate").cum_sum().over("symbol")
    )


def cum_at(cum: pl.DataFrame, trades: pl.DataFrame, at: str) -> pl.Series:
    """The running sum up to and including each trade's `at` time (0 before any settlement)."""
    left = trades.with_row_index("i").select("i", "symbol", time=pl.col(at)).sort("time")
    right = cum.select("symbol", "time", "cum").sort("time")
    j = left.join_asof(right, on="time", by="symbol", check_sortedness=False)
    return j.sort("i")["cum"].fill_null(0.0)


def funding(
    trades: pl.DataFrame, hl: pl.DataFrame, mapping: pl.DataFrame, binance: pl.DataFrame
) -> pl.Series:
    """Funding paid per trade (symbol, direction, entry_time, exit_time).

    Sums the settlements in (entry, exit]: Hyperliquid's hourly rates when the coin was listed
    there for the whole trade, Binance's otherwise. Hours missing from the Hyperliquid archive
    (1.2 % before the hold-out) add nothing. A long pays a positive rate, so the cost is
    direction × the sum.
    """
    hl_settled = hl.join(mapping.select("symbol", "coin"), on="coin").select(
        "symbol", time=pl.col("time").dt.offset_by("1h"), rate="funding"
    )
    sources = {
        "hl": cumulative(hl_settled),
        "bn": cumulative(binance.select("symbol", "time", rate="funding_rate")),
    }
    paid = {
        k: cum_at(c, trades, "exit_time") - cum_at(c, trades, "entry_time")
        for k, c in sources.items()
    }
    listed = trades.join(mapping.select("symbol", "first_hl", "last_hl"), on="symbol", how="left")
    on_hl = (
        (listed["entry_time"] >= listed["first_hl"])
        & (listed["exit_time"] <= listed["last_hl"] + timedelta(hours=1))  # its last settlement
    ).fill_null(False)
    rate = pl.select(pl.when(on_hl).then(paid["hl"]).otherwise(paid["bn"])).to_series()
    return (trades["direction"] * rate).alias("funding")


def main() -> None:
    from src.universe import UNIVERSE

    symbols = pl.read_parquet(UNIVERSE)["symbol"].unique().to_list()
    bn = scan("bars/1h", symbols).select("symbol", "time", "close").collect()
    mapping = match(bn, hourly())
    write(MAPPING, mapping)
    with pl.Config(tbl_rows=-1):
        print(mapping.sort("symbol"))
    print(
        f"mapped {mapping.height} of {len(symbols)}; unmapped:",
        sorted(set(symbols) - set(mapping["symbol"])),
    )


if __name__ == "__main__":
    main()

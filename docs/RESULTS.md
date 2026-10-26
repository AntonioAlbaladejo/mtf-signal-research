# Results

**Phase 3.** The outcome of each pre-registered test, as logged in `research/trials.jsonl`.

An effect is the forward return after an event minus its matched baseline (the mean of the same
symbol and R0 cell), in ATR units and in the predicted direction: positive means the signal works
as the hypothesis says. Intervals are 95 % calendar-month block bootstrap intervals, and p-values
are one-sided in the predicted direction (ENGINE.md §5). "Years" counts the complete years, out
of five (2021 to 2025), whose mean has the sign of the effect; "assets" is the same share over
symbols. Stability requires two thirds of each (PROTOCOL §7).

---

## H1: TD Sequential

**Run:** 26 October 2026, commit `e6fba0c`, clean tree. Data from July 2020 to the hold-out, 69
symbols. The hold-out was not opened.

**Verdict: rejected in all 54 cells.** No cell survives the FDR control at q = 0.05. The smallest
p-value, 0.002, would have needed to be below 0.0009, the Benjamini-Hochberg threshold for the
first of 54.

| Timeframe | Signal | Side | n | Horizons (bars) | Effect [95 % interval] · p | | | Years | Assets |
|---|---|---|---|---|---|---|---|---|---|
| 1h | Setup 9 | buy | 5,082 | 4, 12, 24 | -0.01 [-0.07, +0.06] · 0.642 | -0.11 [-0.23, +0.01] · 0.963 | -0.01 [-0.17, +0.16] · 0.533 | 2/4/1 | 0.49/0.55/0.43 |
| 1h | Setup 9 | sell | 5,133 | 4, 12, 24 | +0.00 [-0.05, +0.06] · 0.460 | -0.08 [-0.17, +0.04] · 0.952 | -0.06 [-0.23, +0.12] · 0.749 | 3/5/2 | 0.51/0.56/0.43 |
| 1h | Perfected setup 9 | buy | 3,459 | 4, 12, 24 | +0.02 [-0.05, +0.10] · 0.257 | -0.10 [-0.24, +0.04] · 0.922 | +0.03 [-0.16, +0.21] · 0.392 | 4/3/4 | 0.58/0.57/0.60 |
| 1h | Perfected setup 9 | sell | 3,679 | 4, 12, 24 | +0.02 [-0.05, +0.08] · 0.276 | -0.08 [-0.19, +0.04] · 0.917 | -0.04 [-0.20, +0.14] · 0.670 | 3/4/3 | 0.66/0.52/0.45 |
| 1h | Countdown 13 | buy | 1,638 | 4, 12, 24 | -0.11 [-0.20, -0.02] · 0.993 | -0.25 [-0.42, -0.08] · 0.999 | -0.16 [-0.43, +0.10] · 0.887 | 5/5/4 | 0.61/0.65/0.55 |
| 1h | Countdown 13 | sell | 1,615 | 4, 12, 24 | -0.01 [-0.10, +0.07] · 0.642 | -0.08 [-0.25, +0.08] · 0.834 | +0.01 [-0.22, +0.25] · 0.501 | 3/3/2 | 0.41/0.52/0.55 |
| 4h | Setup 9 | buy | 1,346 | 3, 6, 12 | -0.02 [-0.13, +0.07] · 0.662 | -0.05 [-0.21, +0.09] · 0.761 | -0.13 [-0.37, +0.09] · 0.876 | 3/4/4 | 0.44/0.47/0.56 |
| 4h | Setup 9 | sell | 1,331 | 3, 6, 12 | -0.08 [-0.16, +0.00] · 0.972 | -0.02 [-0.15, +0.10] · 0.622 | -0.05 [-0.23, +0.13] · 0.683 | 3/3/4 | 0.56/0.51/0.41 |
| 4h | Perfected setup 9 | buy | 935 | 3, 6, 12 | -0.07 [-0.19, +0.05] · 0.885 | -0.05 [-0.23, +0.11] · 0.732 | -0.07 [-0.31, +0.17] · 0.717 | 3/4/3 | 0.46/0.49/0.51 |
| 4h | Perfected setup 9 | sell | 942 | 3, 6, 12 | -0.10 [-0.19, -0.01] · 0.979 | -0.11 [-0.25, +0.04] · 0.914 | -0.21 [-0.40, -0.02] · 0.982 | 4/3/4 | 0.53/0.48/0.58 |
| 4h | Countdown 13 | buy | 455 | 3, 6, 12 | -0.01 [-0.14, +0.13] · 0.559 | +0.02 [-0.17, +0.22] · 0.404 | +0.08 [-0.17, +0.35] · 0.275 | 3/2/3 | 0.51/0.58/0.64 |
| 4h | Countdown 13 | sell | 395 | 3, 6, 12 | -0.00 [-0.17, +0.18] · 0.512 | +0.01 [-0.22, +0.25] · 0.475 | -0.19 [-0.53, +0.16] · 0.859 | 3/2/4 | 0.40/0.42/0.60 |
| 1d | Setup 9 | buy | 262 | 1, 3, 5 | +0.11 [+0.02, +0.20] · 0.013 | +0.16 [-0.03, +0.38] · 0.070 | +0.29 [+0.09, +0.51] · 0.003 | 4/5/5 | 0.65/0.58/0.65 |
| 1d | Setup 9 | sell | 211 | 1, 3, 5 | -0.01 [-0.13, +0.12] · 0.574 | -0.00 [-0.26, +0.26] · 0.511 | -0.17 [-0.54, +0.17] · 0.835 | 3/3/2 | 0.59/0.51/0.61 |
| 1d | Perfected setup 9 | buy | 179 | 1, 3, 5 | +0.10 [-0.00, +0.21] · 0.032 | +0.24 [+0.02, +0.50] · 0.033 | +0.33 [+0.12, +0.54] · 0.002 | 4/3/4 | 0.60/0.58/0.67 |
| 1d | Perfected setup 9 | sell | 158 | 1, 3, 5 | -0.05 [-0.18, +0.09] · 0.749 | -0.05 [-0.33, +0.25] · 0.651 | -0.19 [-0.62, +0.20] · 0.826 | 3/3/3 | 0.61/0.56/0.58 |
| 1d | Countdown 13 | buy | 63 | 1, 3, 5 | -0.04 [-0.19, +0.09] · 0.703 | +0.03 [-0.24, +0.26] · 0.404 | -0.01 [-0.34, +0.29] · 0.556 | 4/3/4 | 0.48/0.59/0.52 |
| 1d | Countdown 13 | sell | 63 | 1, 3, 5 | +0.08 [-0.11, +0.25] · 0.178 | +0.14 [-0.26, +0.51] · 0.238 | +0.11 [-0.42, +0.63] · 0.339 | 2/3/3 | 0.64/0.48/0.56 |

**What stands out.** These are descriptive observations, not findings: none of them was tested
as stated here.

- **Daily buy setups** are the closest to the hypothesis: +0.10 to +0.33 ATR, with p-values of
  0.002 to 0.033 taken alone. They fail the FDR control, and their share of assets with the same
  sign (0.58 to 0.67) is at or below the stability bar. In the breakdown by asset, the 5-day effect
  of a setup 9 is +0.70 ATR on BTC (interval +0.07 to +1.38) and +0.76 on ETH (+0.30 to +1.33),
  over 24 and 20 events.
- **Intraday signals point the other way.** After a 1h buy countdown 13, price underperforms its
  baseline by 0.11 and 0.25 ATR over 4 and 12 bars, with intervals that exclude zero and the same
  sign in all five years. 4h perfected sell setups behave the same way (−0.10 and −0.21 ATR over
  3 and 12 bars). On these timeframes, price tends to continue after a TD exhaustion signal rather
  than reverse. The test was one-sided, so this is not a result: a continuation hypothesis would
  be new, informed by these data, and would need data not used here.
- **The hold-out is short for effects of this size.** Six months hold about 23 daily buy setups
  and 140 hourly buy countdowns, so an effect of 0.3 ATR could not be confirmed there on its own.

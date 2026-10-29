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

**Run:** 27 October 2026, commit `254ce82`, clean tree. Data from July 2020 to the hold-out, 69
symbols. The hold-out was not opened. A first run on 26 October (`e6fba0c`) drew its bootstrap
blocks in an order that the seed did not fix (ENGINE.md §6). Its effects and stability are
identical; its intervals and p-values differ by Monte Carlo noise, at most 0.03 in a p-value, and
its verdict is the same.

**Verdict: rejected in all 54 cells.** No cell survives the FDR control at q = 0.05. The smallest
p-value, 0.0025, would have needed to be below 0.0009, the Benjamini-Hochberg threshold for the
first of 54.

| Timeframe | Signal | Side | n | Horizons (bars) | Effect [95 % interval] · p | | | Years | Assets |
|---|---|---|---|---|---|---|---|---|---|
| 1h | Setup 9 | buy | 5,082 | 4, 12, 24 | -0.01 [-0.07, +0.06] · 0.626 | -0.11 [-0.23, +0.01] · 0.967 | -0.01 [-0.18, +0.16] · 0.559 | 2/4/1 | 0.49/0.55/0.43 |
| 1h | Setup 9 | sell | 5,133 | 4, 12, 24 | +0.00 [-0.05, +0.06] · 0.456 | -0.08 [-0.18, +0.03] · 0.929 | -0.06 [-0.24, +0.12] · 0.749 | 3/5/2 | 0.51/0.56/0.43 |
| 1h | Perfected setup 9 | buy | 3,459 | 4, 12, 24 | +0.02 [-0.05, +0.10] · 0.286 | -0.10 [-0.24, +0.04] · 0.928 | +0.03 [-0.16, +0.21] · 0.389 | 4/3/4 | 0.58/0.57/0.60 |
| 1h | Perfected setup 9 | sell | 3,679 | 4, 12, 24 | +0.02 [-0.05, +0.08] · 0.296 | -0.08 [-0.19, +0.03] · 0.908 | -0.04 [-0.22, +0.13] · 0.666 | 3/4/3 | 0.66/0.52/0.45 |
| 1h | Countdown 13 | buy | 1,638 | 4, 12, 24 | -0.11 [-0.19, -0.03] · 0.994 | -0.25 [-0.42, -0.08] · 0.998 | -0.16 [-0.43, +0.11] · 0.881 | 5/5/4 | 0.61/0.65/0.55 |
| 1h | Countdown 13 | sell | 1,615 | 4, 12, 24 | -0.01 [-0.11, +0.07] · 0.623 | -0.08 [-0.26, +0.08] · 0.831 | +0.01 [-0.23, +0.25] · 0.470 | 3/3/2 | 0.41/0.52/0.55 |
| 4h | Setup 9 | buy | 1,346 | 3, 6, 12 | -0.02 [-0.12, +0.08] · 0.670 | -0.05 [-0.21, +0.09] · 0.756 | -0.13 [-0.39, +0.10] · 0.863 | 3/4/4 | 0.44/0.47/0.56 |
| 4h | Setup 9 | sell | 1,331 | 3, 6, 12 | -0.08 [-0.17, -0.00] · 0.963 | -0.02 [-0.15, +0.11] · 0.625 | -0.05 [-0.23, +0.14] · 0.710 | 3/3/4 | 0.56/0.51/0.41 |
| 4h | Perfected setup 9 | buy | 935 | 3, 6, 12 | -0.07 [-0.19, +0.05] · 0.883 | -0.05 [-0.23, +0.11] · 0.726 | -0.07 [-0.33, +0.17] · 0.705 | 3/4/3 | 0.46/0.49/0.51 |
| 4h | Perfected setup 9 | sell | 942 | 3, 6, 12 | -0.10 [-0.19, -0.01] · 0.979 | -0.11 [-0.25, +0.04] · 0.923 | -0.21 [-0.39, -0.01] · 0.980 | 4/3/4 | 0.53/0.48/0.58 |
| 4h | Countdown 13 | buy | 455 | 3, 6, 12 | -0.01 [-0.14, +0.14] · 0.540 | +0.02 [-0.16, +0.22] · 0.402 | +0.08 [-0.17, +0.35] · 0.278 | 3/2/3 | 0.51/0.58/0.64 |
| 4h | Countdown 13 | sell | 395 | 3, 6, 12 | -0.00 [-0.17, +0.19] · 0.522 | +0.01 [-0.22, +0.25] · 0.494 | -0.19 [-0.52, +0.19] · 0.860 | 3/2/4 | 0.40/0.42/0.60 |
| 1d | Setup 9 | buy | 262 | 1, 3, 5 | +0.11 [+0.02, +0.20] · 0.013 | +0.16 [-0.04, +0.38] · 0.070 | +0.29 [+0.10, +0.50] · 0.002 | 4/5/5 | 0.65/0.58/0.65 |
| 1d | Setup 9 | sell | 211 | 1, 3, 5 | -0.01 [-0.14, +0.12] · 0.571 | -0.00 [-0.27, +0.26] · 0.497 | -0.17 [-0.56, +0.16] · 0.816 | 3/3/2 | 0.59/0.51/0.61 |
| 1d | Perfected setup 9 | buy | 179 | 1, 3, 5 | +0.10 [+0.01, +0.21] · 0.030 | +0.24 [+0.03, +0.51] · 0.032 | +0.33 [+0.12, +0.54] · 0.002 | 4/3/4 | 0.60/0.58/0.67 |
| 1d | Perfected setup 9 | sell | 158 | 1, 3, 5 | -0.05 [-0.18, +0.10] · 0.759 | -0.05 [-0.32, +0.25] · 0.668 | -0.19 [-0.63, +0.19] · 0.827 | 3/3/3 | 0.61/0.56/0.58 |
| 1d | Countdown 13 | buy | 63 | 1, 3, 5 | -0.04 [-0.20, +0.09] · 0.683 | +0.03 [-0.25, +0.26] · 0.407 | -0.01 [-0.37, +0.29] · 0.534 | 4/3/4 | 0.48/0.59/0.52 |
| 1d | Countdown 13 | sell | 63 | 1, 3, 5 | +0.08 [-0.10, +0.24] · 0.171 | +0.14 [-0.27, +0.52] · 0.248 | +0.11 [-0.40, +0.65] · 0.347 | 2/3/3 | 0.64/0.48/0.56 |

**What stands out.** These are descriptive observations, not findings: none of them was tested
as stated here.

- **Daily buy setups** are the closest to the hypothesis: +0.10 to +0.33 ATR, with p-values of
  0.0025 to 0.033 taken alone. They fail the FDR control, and their share of assets with the same
  sign (0.58 to 0.67) is at or below the stability bar. In the breakdown by asset, the 5-day effect
  of a setup 9 is +0.70 ATR on BTC (interval +0.06 to +1.35) and +0.76 on ETH (+0.32 to +1.34),
  over 24 and 20 events.
- **Intraday signals point the other way.** After a 1h buy countdown 13, price underperforms its
  baseline by 0.11 and 0.25 ATR over 4 and 12 bars, with intervals that exclude zero and the same
  sign in all five years. 4h perfected sell setups behave the same way (−0.10 and −0.21 ATR over
  3 and 12 bars). On these timeframes, price tends to continue after a TD exhaustion signal rather
  than reverse. The test was one-sided, so this is not a result: a continuation hypothesis would
  be new, informed by these data, and would need data not used here.
- **The hold-out is short for effects of this size.** Six months hold about 23 daily buy setups
  and 140 hourly buy countdowns, so an effect of 0.3 ATR could not be confirmed there on its own.

---

## H2: Fibonacci retracements

**Run:** 27 October 2026, commit `73bf3d6`, clean tree. Data from July 2020 to the hold-out. H2a
counts the retracements of the 105 universe symbols while they are in the universe; H2b uses the
event-study candidates (69 symbols). The hold-out was not opened.

### H2a: where retracements stop

**Verdict: rejected in all 12 cells.** Retracements are no denser within 0.02 of 0.382, 0.5 and
0.618 than in the windows beside them. Excesses are in percentage points of all retracements; the
net excess subtracts the mean excess of 20 synthetic series run through the same ZigZag, and p is
the larger of the two nulls' p-values. Every interval contains zero and the smallest p-value is
0.17. The ZigZag itself adds almost nothing at these levels: at most +0.08 points.

| Timeframe | k | Level | Retracements | Share in window | Excess | Synthetic | Net excess [95 % interval] · p | Years | Assets |
|---|---|---|---|---|---|---|---|---|---|
| 1h | 2 | 0.382 | 53,656 | 2.2 % | +0.09 | +0.06 | +0.03 [-0.13, +0.20] · 0.333 | 3/5 | 0.49 |
| 1h | 2 | 0.5 | 53,656 | 2.9 % | +0.01 | +0.01 | -0.01 [-0.18, +0.16] · 0.537 | 2/5 | 0.52 |
| 1h | 2 | 0.618 | 53,656 | 3.3 % | +0.06 | +0.03 | +0.03 [-0.15, +0.22] · 0.369 | 3/5 | 0.53 |
| 1h | 3 | 0.382 | 23,155 | 2.1 % | +0.03 | +0.03 | +0.00 [-0.24, +0.24] · 0.497 | 2/5 | 0.41 |
| 1h | 3 | 0.5 | 23,155 | 2.9 % | -0.04 | +0.07 | -0.10 [-0.39, +0.20] · 0.754 | 3/5 | 0.58 |
| 1h | 3 | 0.618 | 23,155 | 3.2 % | -0.22 | -0.01 | -0.21 [-0.47, +0.06] · 0.945 | 3/5 | 0.52 |
| 4h | 2 | 0.382 | 13,161 | 2.2 % | -0.02 | -0.00 | -0.02 [-0.27, +0.23] · 0.545 | 3/5 | 0.43 |
| 4h | 2 | 0.5 | 13,161 | 2.9 % | -0.08 | +0.06 | -0.14 [-0.50, +0.24] · 0.771 | 3/5 | 0.61 |
| 4h | 2 | 0.618 | 13,161 | 3.6 % | +0.20 | +0.00 | +0.19 [-0.21, +0.58] · 0.168 | 4/5 | 0.44 |
| 4h | 3 | 0.382 | 5,735 | 2.4 % | +0.22 | +0.06 | +0.16 [-0.30, +0.64] · 0.272 | 4/5 | 0.37 |
| 4h | 3 | 0.5 | 5,735 | 3.5 % | +0.26 | +0.08 | +0.18 [-0.29, +0.65] · 0.236 | 4/5 | 0.33 |
| 4h | 3 | 0.618 | 5,735 | 3.2 % | -0.24 | +0.01 | -0.25 [-0.80, +0.28] · 0.801 | 3/5 | 0.71 |

### H2b: does a touch anticipate continuation?

**Verdict: rejected in all 12 cells.** Two cells survive the FDR control, both at 1h and 12 bars:
Fibonacci touches beat control touches by 0.015 ATR with k = 2 (p = 0.0005) and by 0.023 ATR with
k = 3 (p = 0.0035). Both fail the rest of the criterion. The Fibonacci touches return 2.9 and
3.5 bps gross in the trade's direction, far below the economic threshold, and the gap has the
same sign in only 54 % and 62 % of assets.

| Timeframe | k | Horizon | Touches, Fibonacci / control | Difference [95 % interval] · p | Fibonacci vs baseline | Control vs baseline | Fibonacci gross, bps | Years | Assets |
|---|---|---|---|---|---|---|---|---|---|
| 1h | 2 | 4 | 65,267 / 57,661 | +0.005 [-0.003, +0.013] · 0.0940 | -0.004 | -0.009 | +3.2 | 3/5 | 0.55 |
| 1h | 2 | 12 | 65,243 / 57,637 | +0.015 [+0.005, +0.025] · 0.0005 **FDR** | -0.029 | -0.044 | +2.9 | 4/5 | 0.54 |
| 1h | 2 | 24 | 65,220 / 57,616 | +0.004 [-0.011, +0.018] · 0.2989 | -0.049 | -0.052 | +4.0 | 2/5 | 0.48 |
| 1h | 3 | 4 | 29,800 / 25,851 | +0.013 [+0.002, +0.025] · 0.0155 | +0.017 | +0.003 | +8.2 | 4/5 | 0.54 |
| 1h | 3 | 12 | 29,779 / 25,831 | +0.023 [+0.005, +0.040] · 0.0035 **FDR** | -0.031 | -0.054 | +3.5 | 5/5 | 0.62 |
| 1h | 3 | 24 | 29,763 / 25,816 | -0.000 [-0.029, +0.029] · 0.5142 | -0.091 | -0.091 | +1.2 | 3/5 | 0.46 |
| 4h | 2 | 3 | 15,712 / 13,538 | +0.004 [-0.009, +0.017] · 0.2664 | -0.020 | -0.024 | -3.1 | 3/5 | 0.50 |
| 4h | 2 | 6 | 15,697 / 13,525 | -0.003 [-0.025, +0.017] · 0.6062 | -0.023 | -0.020 | +4.4 | 3/5 | 0.51 |
| 4h | 2 | 12 | 15,682 / 13,512 | +0.002 [-0.022, +0.025] · 0.4278 | -0.044 | -0.046 | +4.6 | 2/5 | 0.53 |
| 4h | 3 | 3 | 6,964 / 5,722 | +0.003 [-0.020, +0.026] · 0.4088 | -0.018 | -0.020 | -4.5 | 2/5 | 0.47 |
| 4h | 3 | 6 | 6,964 / 5,722 | -0.007 [-0.040, +0.028] · 0.6747 | -0.010 | -0.003 | +4.6 | 4/5 | 0.49 |
| 4h | 3 | 12 | 6,950 / 5,711 | +0.015 [-0.026, +0.059] · 0.2334 | -0.028 | -0.043 | +2.2 | 2/5 | 0.51 |

Effects are in ATR units. "Difference" is Fibonacci touches minus control touches, both measured
against their matched baseline, which the next two columns give separately.

**What stands out.** These are descriptive observations, not findings.

- **Touching a level is a poor entry.** In 11 of 12 cells, both kinds of touch return less than
  the matched baseline: buying a pullback in an up-trending regime, or selling a bounce in a
  down-trending one, does worse than a random entry in the same regime. At 1h this reaches −0.05
  to −0.09 ATR over 24 bars, and it matches the intraday continuation seen in H1.
- **The gap may be depth, not Fibonacci.** The control levels are deeper on average (0.567
  against 0.5), as noted when H2 was pre-registered. By pairs, at 1h and 12 bars, 0.382 beats 0.45
  by 0.03 to 0.04 ATR and 0.618 beats 0.70 by 0.02, but 0.5 and 0.55 are even (−0.007 and +0.001).
- **The gap is small.** 0.015 to 0.023 ATR is 2 to 3 bps at the median 1h ATR (1.3 %), against
  round-trip costs of about 12 bps.

---

## H3: RSI as a confirmation

**Run:** 29 October 2026, commit `5588c6b`, clean tree. Data from July 2020 to the hold-out, 69
symbols. The hold-out was not opened.

**Verdict: rejected in all 24 cells of H3.0 and all 18 of H3.1.** No slope survives the FDR
control at q = 0.05. The smallest p-values, 0.0055 in H3.0 and 0.0075 in H3.1, both for 1h
Fibonacci touches over 4 bars, would have needed to be below 0.0021 and 0.0028, the
Benjamini-Hochberg thresholds for the first of 24 and of 18. No cell is inconclusive: the standard
deviation of s ranges from 7.4 to 11.3 RSI points. H3.2, the hard veto, was to be evaluated only
after a positive slope, so it was not run.

Unlike those of H1 and H2, these p-values are two-sided. With s = 50 − RSI for longs and
RSI − 50 for shorts, a positive slope supports the mean-reversion reading of RSI and a negative
one the momentum reading. The slope is that of the event-minus-baseline return, in ATR units, per
10 points of s, with both demeaned within each R0 cell. "Years" and "assets" count the slopes,
computed on the same within-cell values, that have the sign of the pooled one.

### H3.0: RSI of the event's timeframe

| Timeframe | Event | n | SD of s | Horizons (bars) | Slope per 10 RSI points [95 % interval] · p | | | Years | Assets |
|---|---|---|---|---|---|---|---|---|---|
| 1h | Setup 9 | 10,215 | 8.7 | 4, 12, 24 | +0.007 [-0.040, +0.054] · 0.7541 | -0.047 [-0.132, +0.032] · 0.2504 | -0.004 [-0.113, +0.100] · 0.9325 | 3/5/3 | 0.53/0.49/0.41 |
| 1h | Countdown 13 | 3,253 | 7.7 | 4, 12, 24 | +0.009 [-0.055, +0.077] · 0.7841 | -0.018 [-0.148, +0.097] · 0.7646 | +0.179 [-0.001, +0.347] · 0.0450 | 3/3/4 | 0.48/0.55/0.59 |
| 1h | Fibonacci touch | 43,393 | 9.2 | 4, 12, 24 | -0.028 [-0.048, -0.009] · 0.0055 | -0.051 [-0.098, -0.007] · 0.0265 | -0.053 [-0.130, +0.019] · 0.1634 | 5/4/4 | 0.54/0.46/0.46 |
| 4h | Setup 9 | 2,677 | 8.4 | 3, 6, 12 | +0.015 [-0.046, +0.076] · 0.6097 | +0.001 [-0.117, +0.113] · 0.9905 | -0.101 [-0.280, +0.072] · 0.2449 | 4/3/3 | 0.57/0.54/0.48 |
| 4h | Countdown 13 | 850 | 7.4 | 3, 6, 12 | +0.069 [-0.071, +0.214] · 0.3428 | +0.033 [-0.141, +0.210] · 0.7226 | +0.028 [-0.220, +0.270] · 0.8276 | 3/2/2 | 0.54/0.51/0.46 |
| 4h | Fibonacci touch | 10,825 | 8.8 | 3, 6, 12 | -0.028 [-0.065, +0.010] · 0.1474 | -0.039 [-0.095, +0.014] · 0.1644 | -0.085 [-0.186, +0.012] · 0.0935 | 4/4/5 | 0.50/0.51/0.49 |
| 1d | Setup 9 | 473 | 8.8 | 1, 3, 5 | -0.030 [-0.112, +0.052] · 0.4633 | +0.008 [-0.149, +0.181] · 0.9280 | -0.049 [-0.288, +0.189] · 0.6897 | 4/4/2 | 0.43/0.58/0.42 |
| 1d | Countdown 13 | 126 | 8.0 | 1, 3, 5 | +0.115 [-0.057, +0.276] · 0.1619 | +0.075 [-0.228, +0.365] · 0.6172 | -0.039 [-0.409, +0.273] · 0.8311 | 4/2/2 | 0.55/0.53/0.50 |

### H3.1: RSI of the next timeframe up

The 4h RSI for 1h events and the 1d RSI for 4h events, as of the event's close.

| Timeframe | Event | n | SD of s | Horizons (bars) | Slope per 10 RSI points [95 % interval] · p | | | Years | Assets |
|---|---|---|---|---|---|---|---|---|---|
| 1h | Setup 9 | 10,215 | 10.9 | 4, 12, 24 | -0.014 [-0.045, +0.015] · 0.3608 | -0.056 [-0.114, +0.002] · 0.0555 | -0.007 [-0.106, +0.091] · 0.8866 | 3/4/4 | 0.51/0.54/0.43 |
| 1h | Countdown 13 | 3,253 | 8.9 | 4, 12, 24 | +0.020 [-0.037, +0.080] · 0.4783 | -0.025 [-0.148, +0.097] · 0.6762 | +0.115 [-0.076, +0.297] · 0.2169 | 3/3/4 | 0.48/0.55/0.58 |
| 1h | Fibonacci touch | 43,393 | 10.5 | 4, 12, 24 | -0.030 [-0.051, -0.008] · 0.0075 | -0.058 [-0.101, -0.013] · 0.0100 | -0.077 [-0.152, -0.002] · 0.0430 | 4/4/4 | 0.58/0.62/0.54 |
| 4h | Setup 9 | 2,677 | 11.3 | 3, 6, 12 | +0.038 [-0.009, +0.087] · 0.1109 | +0.015 [-0.059, +0.084] · 0.6827 | -0.039 [-0.144, +0.065] · 0.4733 | 4/3/3 | 0.58/0.63/0.49 |
| 4h | Countdown 13 | 850 | 9.6 | 3, 6, 12 | +0.002 [-0.109, +0.114] · 0.9700 | +0.004 [-0.134, +0.147] · 0.9580 | -0.011 [-0.231, +0.195] · 0.9305 | 2/2/3 | 0.61/0.56/0.49 |
| 4h | Fibonacci touch | 10,825 | 7.7 | 3, 6, 12 | +0.003 [-0.029, +0.040] · 0.8551 | -0.020 [-0.076, +0.038] · 0.4783 | +0.001 [-0.079, +0.093] · 0.9790 | 3/3/4 | 0.59/0.37/0.65 |

### Zones

The mean event-minus-baseline return in each zone of s, at the three horizons of the row:
supportive (s > 20, that is, RSI below 30 for a long and above 70 for a short), neutral, and
opposing (s < −20). Unlike the slope, these means are not demeaned within R0 cells, so they mix
regimes.

**H3.0**

| Timeframe | Event | Supportive: n · effect | Neutral: n · effect | Opposing: n · effect |
|---|---|---|---|---|
| 1h | Setup 9 | 2,461 · -0.02 / -0.21 / -0.05 | 7,754 · +0.00 / -0.06 / -0.03 | 0 |
| 1h | Countdown 13 | 739 · -0.02 / -0.16 / +0.12 | 2,514 · -0.07 / -0.17 / -0.13 | 0 |
| 1h | Fibonacci touch | 638 · -0.08 / -0.14 / -0.05 | 41,842 · +0.01 / -0.01 / -0.03 | 913 · +0.00 / +0.05 / +0.05 |
| 4h | Setup 9 | 694 · -0.05 / -0.12 / -0.31 | 1,983 · -0.05 / -0.01 / -0.01 | 0 |
| 4h | Countdown 13 | 184 · +0.04 / +0.10 / +0.04 | 666 · -0.02 / -0.01 / -0.06 | 0 |
| 4h | Fibonacci touch | 35 · -0.04 / -0.19 / +0.39 | 10,397 · -0.03 / -0.04 / -0.07 | 393 · +0.08 / +0.21 / +0.32 |
| 1d | Setup 9 | 118 · -0.04 / +0.02 / -0.04 | 355 · +0.09 / +0.11 / +0.13 | 0 |
| 1d | Countdown 13 | 30 · +0.28 / +0.38 / +0.28 | 96 · -0.06 / -0.01 / -0.02 | 0 |

**H3.1**

| Timeframe | Event | Supportive: n · effect | Neutral: n · effect | Opposing: n · effect |
|---|---|---|---|---|
| 1h | Setup 9 | 1,325 · +0.01 / -0.19 / +0.17 | 8,844 · -0.01 / -0.08 / -0.07 | 46 · +0.06 / -0.11 / +0.11 |
| 1h | Countdown 13 | 530 · -0.05 / -0.18 / +0.18 | 2,722 · -0.06 / -0.17 / -0.13 | 1 · +0.17 / +0.29 / +0.35 |
| 1h | Fibonacci touch | 145 · -0.14 / +0.11 / +0.23 | 38,944 · -0.00 / -0.02 / -0.04 | 4,304 · +0.07 / +0.10 / +0.10 |
| 4h | Setup 9 | 237 · +0.04 / +0.05 / -0.09 | 2,410 · -0.06 / -0.04 / -0.10 | 30 · -0.09 / -0.23 / +0.21 |
| 4h | Countdown 13 | 114 · -0.03 / -0.04 / -0.18 | 736 · -0.00 / +0.03 / -0.02 | 0 |
| 4h | Fibonacci touch | 0 | 9,439 · -0.03 / -0.04 / -0.08 | 1,386 · -0.03 / +0.06 / +0.08 |

**What stands out.** These are descriptive observations, not findings.

- **Where RSI comes closest, it reads as momentum.** For 1h Fibonacci touches the slope is
  negative at all three horizons in both variants, from −0.03 to −0.08 ATR per 10 points, and also
  on BTC and on ETH alone: a pullback bought with a low RSI does worse than one bought with RSI
  still high. It holds in four or five of the five years, but in only 46 % to 62 % of assets, and
  it is small: 0.03 ATR is about 4 bps at the median 1h ATR. In H3.1, the 4,304 touches whose 4h
  RSI is above 70 for a long or below 30 for a short beat the baseline by 0.07 to 0.10 ATR.
- **An extreme RSI does not rescue the TD setups.** At 1h and 4h, setups in the supportive zone
  do worse than neutral ones at 12 bars: −0.21 against −0.06 ATR at 1h and −0.31 against −0.01 at
  4h. This is the intraday continuation seen in H1 and H2b. Countdowns lean the other way, and
  none of these slopes is significant.
- **Daily countdowns** in the supportive zone of H3.0 return +0.28 to +0.38 ATR, against about
  zero for the rest, but there are only 30 of them.
- **For phase 4,** H3.0 gives no evidence that RSI, as a linear term within R0, adds information
  to these events.

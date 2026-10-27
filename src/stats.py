"""Statistics the protocol relies on: calendar-block bootstrap, FDR, and performance metrics."""

import math
from statistics import NormalDist

import numpy as np
import polars as pl

N = NormalDist()


def block_bootstrap(values, blocks, reps: int = 2000, seed: int = 0) -> np.ndarray:
    """Bootstrap distribution of the mean of `values`, resampling whole blocks with replacement.

    Blocks are calendar months shared by all assets (PROTOCOL §7), so that events clustered in
    time or across correlated assets are resampled together instead of as independent evidence.
    """
    g = pl.DataFrame({"v": values, "b": blocks}).group_by("b").agg(s=pl.col("v").sum(), n=pl.len())
    g = g.sort("b")  # group order is not deterministic, and the seed draws positions in it
    s, n = g["s"].to_numpy(), g["n"].to_numpy()
    idx = np.random.default_rng(seed).integers(0, len(s), size=(reps, len(s)))
    return s[idx].sum(axis=1) / n[idx].sum(axis=1)


def bootstrap_test(
    values, blocks, alternative: str = "greater", reps: int = 2000, seed: int = 0
) -> dict:
    """Mean effect, 95% percentile interval and a centred bootstrap p-value (H0: mean = 0)."""
    v = np.asarray(values, dtype=float)
    est, boot = float(v.mean()), block_bootstrap(v, blocks, reps, seed)
    return _summary(est, boot, alternative) | {"n": len(v), "blocks": len(set(blocks))}


def bootstrap_difference(
    a, a_blocks, b, b_blocks, alternative: str = "greater", reps: int = 2000, seed: int = 0
) -> dict:
    """mean(a) − mean(b), resampling calendar blocks jointly for both groups (H2b)."""
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    g = (
        pl.DataFrame(
            {
                "v": np.r_[va, vb],
                "a": np.r_[np.ones(va.size, bool), np.zeros(vb.size, bool)],
                "blk": list(a_blocks) + list(b_blocks),
            }
        )
        .group_by("blk")
        .agg(
            sa=pl.col("v").filter("a").sum(),
            na=pl.col("a").sum(),
            sb=pl.col("v").filter(~pl.col("a")).sum(),
            nb=(~pl.col("a")).sum(),
        )
        .sort("blk")
    )
    idx = np.random.default_rng(seed).integers(0, g.height, size=(reps, g.height))
    sa, na, sb, nb = (
        g[c].to_numpy().astype(float)[idx].sum(axis=1) for c in ("sa", "na", "sb", "nb")
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        boot = sa / na - sb / nb
    est = float(va.mean() - vb.mean())
    sizes = {"n": va.size + vb.size, "n_a": va.size, "n_b": vb.size, "blocks": g.height}
    return _summary(est, boot[np.isfinite(boot)], alternative) | sizes


def _summary(est: float, boot: np.ndarray, alternative: str) -> dict:
    """Estimate, 95% percentile interval and a centred bootstrap p-value (H0: effect = 0)."""
    centred = boot - est
    hits = {
        "greater": centred >= est,
        "less": centred <= est,
        "two-sided": np.abs(centred) >= abs(est),
    }[alternative].sum()
    low, high = np.quantile(boot, [0.025, 0.975])
    return {
        "effect": est,
        "ci_low": float(low),
        "ci_high": float(high),
        "p": float((hits + 1) / (len(boot) + 1)),
    }


def fdr(p: list[float], q: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg: which hypotheses are discoveries at false discovery rate q."""
    order = sorted(range(len(p)), key=p.__getitem__)
    k = max((i + 1 for i, j in enumerate(order) if p[j] <= q * (i + 1) / len(p)), default=0)
    passed = set(order[:k])
    return [i in passed for i in range(len(p))]


def sharpe(daily: np.ndarray) -> float:
    """Annualised Sharpe ratio of daily returns (crypto trades 365 days a year)."""
    return float(daily.mean() / daily.std(ddof=1) * math.sqrt(365))


def sortino(daily: np.ndarray) -> float:
    return float(daily.mean() / math.sqrt(np.mean(np.minimum(daily, 0) ** 2)) * math.sqrt(365))


def max_drawdown(daily: np.ndarray) -> float:
    """Largest peak-to-trough fall of cumulative (additive) returns."""
    cum = np.cumsum(daily)
    return float(np.max(np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:] - cum))


def calmar(daily: np.ndarray) -> float:
    return float(daily.mean() * 365 / max_drawdown(daily))


def psr(daily: np.ndarray, sr0: float = 0.0) -> float:
    """Probabilistic Sharpe ratio (Bailey & López de Prado): P(true SR > sr0), per-period SR."""
    sr = daily.mean() / daily.std(ddof=1)
    z = (daily - daily.mean()) / daily.std()
    skew, kurt = np.mean(z**3), np.mean(z**4)
    return N.cdf(
        (sr - sr0) * math.sqrt(len(daily) - 1) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2)
    )


def dsr(daily: np.ndarray, trials: int, trial_sr_var: float) -> float:
    """Deflated Sharpe ratio: PSR against the best SR expected from `trials` unskilled attempts.

    `trial_sr_var` is the variance of the per-period Sharpe ratios across all trials tried.
    """
    g = 0.5772156649  # Euler-Mascheroni
    sr0 = math.sqrt(trial_sr_var) * (
        (1 - g) * N.inv_cdf(1 - 1 / trials) + g * N.inv_cdf(1 - 1 / (trials * math.e))
    )
    return psr(daily, sr0)

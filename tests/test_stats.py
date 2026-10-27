import numpy as np
import pytest

from src.stats import bootstrap_test, dsr, fdr, max_drawdown, psr, sharpe


def clustered(seed: int, effect: float = 0.0, months: int = 70, per_month: int = 10):
    """Events that share a monthly shock, as events clustered in time and across assets do."""
    rng = np.random.default_rng(seed)
    shock = rng.normal(0, 1, months)
    blocks = np.repeat(np.arange(months), per_month)
    return effect + shock[blocks] + rng.normal(0, 1, blocks.size), blocks


def rejection_rate(blocks_of, seeds: int, effect: float = 0.0) -> float:
    rejected = 0
    for s in range(seeds):
        values, blocks = clustered(s, effect)
        rejected += bootstrap_test(values, blocks_of(blocks), reps=500, seed=s)["p"] < 0.05
    return rejected / seeds


def test_block_bootstrap_is_calibrated_on_clustered_data_without_an_effect():
    assert 0.02 <= rejection_rate(lambda b: b, seeds=200) <= 0.09


def test_treating_clustered_events_as_independent_manufactures_discoveries():
    # Measured at about 22% for a nominal 5%; at least double the nominal rate is the claim.
    assert rejection_rate(lambda b: np.arange(b.size), seeds=100) > 0.10


def test_planted_effect_is_recovered():
    covered = detected = 0
    for s in range(50):
        values, blocks = clustered(s, effect=0.5)
        r = bootstrap_test(values, blocks, reps=500, seed=s)
        detected += r["p"] < 0.05
        covered += r["ci_low"] <= 0.5 <= r["ci_high"]
    assert detected >= 45 and covered >= 42


def test_a_seed_fixes_the_result_whatever_the_row_order():
    values, blocks = clustered(0, effect=0.2)
    order = np.random.default_rng(1).permutation(values.size)
    first = [bootstrap_test(values, blocks, seed=3) for _ in range(3)]
    shuffled = bootstrap_test(values[order], blocks[order], seed=3)
    assert all(r == first[0] for r in first[1:])
    assert shuffled["ci_low"] == pytest.approx(first[0]["ci_low"])
    assert shuffled["p"] == first[0]["p"]


def test_fdr_benjamini_hochberg():
    assert fdr([0.001, 0.008, 0.039, 0.041, 0.6], q=0.05) == [True, True, False, False, False]
    assert fdr([0.01, 0.02, 0.03, 0.04], q=0.05) == [True, True, True, True]


def test_metrics():
    assert max_drawdown(np.array([0.1, -0.05, -0.1, 0.2, -0.01])) == pytest.approx(0.15)
    daily = np.random.default_rng(0).normal(0.001, 0.01, 1500)
    assert sharpe(daily) == pytest.approx(daily.mean() / daily.std(ddof=1) * 365**0.5)
    assert 0.5 < psr(daily) <= 1
    deflated = [dsr(daily, n, trial_sr_var=0.02**2) for n in (2, 10, 100)]
    assert psr(daily) > deflated[0] > deflated[1] > deflated[2]

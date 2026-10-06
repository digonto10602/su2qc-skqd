"""
prompts/33 A3: the statistics of the campaign (src/skqd/campaign33/stats.py).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from skqd.campaign33 import stats as ST  # noqa: E402


def test_garwood_and_wilson():
    lo, hi = ST.garwood(0)
    assert lo == 0.0 and abs(hi - 3.6888794541139363) < 1e-12
    lo, hi = ST.garwood(10)
    assert abs(lo - 4.795389) < 1e-5 and abs(hi - 18.390356) < 1e-5
    lo, hi = ST.wilson(695, 3200)
    assert lo < 695 / 3200 < hi and abs(hi - lo - 0.0286) < 1e-3


def test_poisson_two_sided():
    assert ST.poisson_two_sided(0, 0.19) == 1.0, "0 is the most likely count"
    assert ST.poisson_two_sided(30, 10.0) < 1e-6
    p = ST.poisson_two_sided(10, 10.0)
    assert 0.9 < p <= 1.0


def test_f_hit_cell_is_the_pooled_reference_string_test():
    from skqd.skqd import pooled_reference_string_test
    rows = [(36, 140, 0.89, 6.456e-4, 677), (28, 140, 0.95, 4.06e-4, 426)]
    a = ST.f_hit_cell(rows, kappa=1.0, r_nc=1.115, r_nc_95=[1.03, 1.115])
    b = pooled_reference_string_test(rows, readout_factor=1.0, conf=0.95)
    assert a["f_hit"] == b["f_clean"] and a["f_hit_ci"] == b["f_clean_68"]
    assert abs(a["f_hat_ideal"] - a["f_hit"] / 1.115) < 1e-15
    assert abs(a["f_hat_ideal_ci"][1] - a["f_hit_ci"][1] / 1.115) < 1e-15


def test_per_state_test_passes_a_true_sample_and_catches_a_bias():
    rng = np.random.default_rng(33)
    probs = {0: 0.5, 1: 0.3, 2: 0.15, 3: 0.05}
    N = 20000
    draw = rng.multinomial(N, list(probs.values()))
    counts = dict(zip(probs, draw.tolist()))
    assert ST.per_state_test(counts, probs, N, 5.0)["ok"]
    bad = dict(counts)
    bad[0] -= 1000
    bad[3] += 1000
    r = ST.per_state_test(bad, probs, N, 5.0)
    assert not r["ok"] and {f["state"] for f in r["failures"]} >= {0, 3}


def test_compare_verdicts():
    assert ST.compare(1.0, [0.9, 1.1], 1.0, [0.9, 1.1])["verdict"] == "consistent"
    s = 0.2 / 2 / 1.96
    sig = math.sqrt(2) * s
    assert ST.compare(1.0 + 3 * sig, [0.9 + 3 * sig, 1.1 + 3 * sig], 1.0, [0.9, 1.1])["verdict"] == "tension"
    assert ST.compare(2.0, [1.9, 2.1], 1.0, [0.9, 1.1])["verdict"] == "inconsistent"
    assert ST.compare(1.0, [0.9, 1.1], 0.5, None)["verdict"] == "no_old_uncertainty"
    assert ST.compare(None, None, 0.5, None)["verdict"] == "not_comparable"
    assert abs(ST.seed_spread_sigma([0.953, 0.977, 0.953]) - 0.024 / 2 / 1.96) < 1e-15


def test_bootstrap_counts_is_seeded_and_brackets_the_point():
    c = [{0: 50, 1: 30, 2: 20}, {0: 10, 3: 90}]

    def stat(cl):
        return sum(x.get(0, 0) for x in cl) / sum(sum(x.values()) for x in cl)
    a = ST.bootstrap_counts(c, stat, B=300, seed=33)
    b = ST.bootstrap_counts(c, stat, B=300, seed=33)
    assert a == b and a["ci"][0] <= a["point"] <= a["ci"][1]


def test_tv_and_its_multinomial_null():
    assert ST.tv_distance({1: 5, 2: 5}, {1: 50, 2: 50}) == 0.0
    null = ST.tv_expectation_multinomial({0: 0.5, 1: 0.5}, 100, 100, reps=100)
    assert 0 < null["mean"] < null["p95"] < 0.3


def test_binomial_band_contains_the_mean():
    lo, hi = ST.binomial_band(3200, 695 / 3200)
    assert lo < 695 < hi

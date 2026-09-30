"""The clean-yield statistic of prompts/20 part A (decisions C2', C3', M4.4).

`skqd.skqd.clean_fraction_mixture` fits one parameter w in
P(s | accepted) = w p_ideal(s) + (1 - w)/dim; `skqd.skqd.reference_string_test` counts the
circuit's most probable codeword against its accidental-acceptance expectation;
`skqd.krylov.ideal_sector_distribution` is the p_ideal both of them need.

The numbers the tests pin come from `reports/H0_replan_planner_analysis_20260922.md`
(snippet P8, pooled over the five hardware pubs of the canary circuit) and from the frozen
manifest of `data/hardware/H0_prep/circuits/B0_ref06_k1_rep1.json`.
"""
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.exact import Model  # noqa: E402
from skqd.krylov import ideal_sector_distribution  # noqa: E402
from skqd.skqd import (READOUT_FACTOR, clean_fraction_mixture,  # noqa: E402
                       near_clean_yield, reference_string_test, yield_model)

CANARY = "B0_ref06_k1_rep1"
PREP = os.path.join(ROOT, "data", "hardware", "H0_prep")


@pytest.fixture(scope="module")
def canary():
    """(ideal sector distribution of the canary circuit, its manifest)."""
    with open(os.path.join(PREP, "circuits", f"{CANARY}.json")) as fh:
        man = json.load(fh)
    M = Model(2)
    d = ideal_sector_distribution(M, 4.0, man["twoB"], man["reference"], man["k"],
                                  man["dt"], man["repetitions"])
    return d, man


# ------------------------------------------------------------------ A3
def test_ideal_sector_distribution_reproduces_the_frozen_probabilities(canary):
    """A3: the group evolution must agree with the QPY-derived probabilities to 1e-9.

    `scripts/h0_support_plan.ideal_probabilities` takes the noiseless statevector of the
    FROZEN transpiled circuit, permutes it back with its own final layout and projects it on
    the codeword subspace; `ideal_sector_distribution` evolves the reference with
    `skqd.krylov.apply_groups`.  They are independent routes to the same object.
    """
    import h0_support_plan as sp
    from gate_H0P import load_manifests
    mans, _ = load_manifests(PREP)
    man = next(m for m in mans if m["id"] == CANARY)
    P, _ = sp.ideal_probabilities(PREP, [man], Model(2), 4.0, crosscheck=False)
    d, _ = canary
    assert d["dim"] == len(P[CANARY]) == 38
    assert np.max(np.abs(d["p_unnormalised"] - P[CANARY])) < 1e-9
    assert abs(d["sector_mass"] - 1.0) < 1e-9
    assert d["p_reference"] == pytest.approx(0.8833, abs=5e-5)
    assert abs(float(np.sum(d["p"])) - 1.0) < 1e-12


# ------------------------------------------------------------------ A4 (i)
def test_mixture_estimator_on_synthetic_mixtures(canary):
    """A4 (i): draws at w in {0, 0.1, 0.5, 0.9}, N_acc = 1e4, over the B=0 k=1 distribution.

    The headline criterion is |w_hat - w| <= 0.02 in every case.  The profile-likelihood
    interval is checked for CALIBRATION over a seeded ensemble rather than on the four
    seed-11 draws alone: at seed 11 the interval covers the truth in 2 of the 4 cases (the
    misses are 1.8 and 1.5 sigma), while over 10 seeds per case the coverage is >= 0.68 --
    the interval is right and the four-draw count is draw luck.  Recorded rather than tuned.
    """
    d, _ = canary
    p, dim = d["p"], d["dim"]
    rng = np.random.default_rng(11)
    covered = []
    for w in (0.0, 0.1, 0.5, 0.9):
        n = rng.multinomial(10000, w * p + (1.0 - w) / dim)
        e = clean_fraction_mixture(n, p, dim, 10000)
        assert abs(e["w"] - w) <= 0.02, (w, e["w"])
        assert e["w_68"][0] <= e["w"] <= e["w_68"][1]
        assert e["accepted"] == 10000
        assert e["clean_accepted"] == pytest.approx(e["w"] * 10000)
        assert e["f_clean"] == pytest.approx(e["clean_yield"] / READOUT_FACTOR)
        covered.append(e["w_68"][0] <= w <= e["w_68"][1])
    assert sum(covered) == 2, "the seed-11 count this test records"

    cov = []
    for w in (0.0, 0.1, 0.5, 0.9):
        for s in range(10):
            r = np.random.default_rng(1000 + s)
            n = r.multinomial(10000, w * p + (1.0 - w) / dim)
            e = clean_fraction_mixture(n, p, dim, 10000)
            cov.append(e["w_68"][0] <= w <= e["w_68"][1])
    assert sum(cov) >= 0.68 * len(cov), f"coverage {np.mean(cov):.2f} over {len(cov)} draws"


# ------------------------------------------------------------------ A4 (ii)
def test_flat_histogram_gives_zero_and_a_zero_count_circuit_does_not_raise(canary):
    d, _ = canary
    p, dim = d["p"], d["dim"]
    e = clean_fraction_mixture(np.full(dim, 10.0), p, dim, 1000)
    assert e["w"] == 0.0 and e["logL_gain"] == 0.0
    assert e["f_clean"] == 0.0
    z = clean_fraction_mixture(np.zeros(dim), p, dim, 1000)
    assert z["w"] == 0.0 and z["w_68"] == [0.0, 1.0] and z["f_clean"] == 0.0
    z2 = clean_fraction_mixture(np.zeros(dim), p, dim, 0)
    assert z2["w"] == 0.0 and z2["clean_yield"] == 0.0


def test_mixture_estimator_input_guards(canary):
    d, _ = canary
    p, dim = d["p"], d["dim"]
    with pytest.raises(ValueError):
        clean_fraction_mixture(np.zeros(dim), d["p_unnormalised"] * 1.5, dim, 10)
    with pytest.raises(ValueError):
        clean_fraction_mixture(np.zeros(dim - 1), p, dim, 10)


def test_pure_clean_sample_gives_w_near_one(canary):
    d, _ = canary
    p, dim = d["p"], d["dim"]
    n = np.random.default_rng(3).multinomial(20000, p)
    e = clean_fraction_mixture(n, p, dim, 20000)
    assert e["w"] > 0.98 and e["w_68"][1] == 1.0 or e["w"] > 0.98


# ------------------------------------------------------------------ A4 (iii)
def test_reference_string_test_reproduces_the_pooled_hardware_numbers(canary):
    """A4 (iii): 6 hits over 8267 shots, acceptance 38/4096, dim 38 (P8 of the analysis)."""
    d, _ = canary
    r = reference_string_test(6, 8267, d["p_reference"], 38 / 4096, 38)
    assert r["expected_from_garbage"] == pytest.approx(2.018, abs=1e-3)
    assert r["P_ge"] == pytest.approx(0.017, abs=1e-3)
    assert r["f_clean"] == pytest.approx(6.65e-4, abs=1e-6)
    assert r["excess"] == pytest.approx(3.982, abs=1e-3)
    assert r["z"] == pytest.approx(2.80, abs=0.01)
    # the planner's quoted 1 sigma band used the Gaussian approximation
    assert r["f_clean_68_sqrt_n"][0] == pytest.approx(2.56e-4, abs=1e-6)
    assert r["f_clean_68_sqrt_n"][1] == pytest.approx(1.074e-3, abs=1e-6)
    # the exact Poisson (Garwood) interval is wider on the upper end
    assert r["f_clean_68"][0] < r["f_clean"] < r["f_clean_68"][1]
    assert r["f_clean_68"][1] > r["f_clean_68_sqrt_n"][1]


def test_reference_string_test_zero_hits_and_pure_garbage():
    r = reference_string_test(0, 2000, 0.8833, 38 / 4096, 38)
    assert r["n_reference"] == 0 and r["excess"] < 0 and r["f_clean"] < 0
    assert r["P_ge"] == pytest.approx(1.0)
    # a count exactly at the garbage expectation carries no clean component
    r2 = reference_string_test(2, 8267, 0.8833, 38 / 4096, 38)
    assert abs(r2["f_clean"]) < 5e-6


# ------------------------------------------------------------------ M4.4
def test_near_clean_yield_is_the_residual_of_the_amended_model():
    y, f, a = 0.0175, 6.65e-4, 38 / 4096
    n = near_clean_yield(y, f, a)
    assert n == pytest.approx(y - yield_model(f, a))
    assert near_clean_yield(yield_model(f, a), f, a) == pytest.approx(0.0, abs=1e-15)

import numpy as np
import pytest

from skqd.controls import cipsi, oracle
from skqd.exact import Model
from skqd.krylov import basis_vector, exact_krylov_states, references
from skqd.skqd import certify, ritz, support_metrics


def test_variational_and_certification():
    M = Model(3)
    H = M.H(4.0)
    r = M.reference(4.0, 0)
    prob = np.zeros(M.basis.dim)
    prob[r.indices] = np.abs(r.ground) ** 2
    refs = references(M.basis, 0)
    B = cipsi(H, refs, 160)
    res = ritz(H, B)
    assert res.ER >= r.E0 - 1e-12
    assert res.ER - r.E0 < 2e-3
    cert = certify(res, r.E0, float(r.energies[1]))
    assert cert.weinstein[0] <= r.E0 <= cert.weinstein[1]
    assert cert.gap_assumption_holds
    met = support_metrics(B, prob, 1e-3)
    assert met["recall"] > 0.95
    Bo = oracle(prob, M.basis.sector(0), 160)
    assert ritz(H, Bo).ER - r.E0 < 2e-3


def test_krylov_states_stay_in_sector():
    M = Model(3)
    H = M.H(4.0)
    r = M.reference(4.0, 0)
    psi = exact_krylov_states(H, basis_vector(M.basis.dim, references(M.basis, 0)[0]), r.dt, 3)[-1]
    outside = np.setdiff1d(np.arange(M.basis.dim), r.indices)
    assert np.abs(psi[outside]).max() < 1e-12
    assert abs(np.linalg.norm(psi) - 1) < 1e-10


def test_shot_rule_matches_the_manual_and_a_monte_carlo_check():
    from scipy.stats import poisson

    from skqd.skqd import poisson_lambda_star, shot_rule

    lam = poisson_lambda_star(3, 0.95)
    assert abs(lam - 6.296) < 1e-3                       # manual Step 4.4 ("Poisson mean 6.3")
    assert poisson.sf(2, lam) == pytest.approx(0.95, abs=1e-9)
    assert poisson.sf(2, lam * 0.999) < 0.95             # lam is the SMALLEST such mean

    # eq. (5): S >= 6.3 / (0.82 f p); f = 0.2, p = 1e-3 -> about 3.9e4 shots per circuit
    N = shot_rule(1e-3, 0.82 * 0.2)
    assert N == int(np.ceil(lam / (1e-3 * 0.82 * 0.2)))
    assert 3.8e4 < N < 4.0e4
    assert shot_rule(1e-3, 1.0) == int(np.ceil(lam / 1e-3))
    # monotone in p and in y, and k > 3 or a higher confidence needs more shots
    assert shot_rule(1e-4, 0.5) > shot_rule(1e-3, 0.5) > shot_rule(1e-3, 1.0)
    assert shot_rule(1e-3, 0.5, k=5) > shot_rule(1e-3, 0.5)
    assert shot_rule(1e-3, 0.5, conf=0.99) > shot_rule(1e-3, 0.5)

    # Monte-Carlo: with N = shot_rule(p, y) shots the configuration is seen >= 3 times
    # in about 95 % of the repetitions (binomial sampling, not the Poisson limit)
    rng = np.random.default_rng(20260916)
    p, y, reps = 2e-3, 0.4, 20000
    N = shot_rule(p, y)
    hits = rng.binomial(N, p * y, size=reps)
    frac = float(np.mean(hits >= 3))
    assert abs(frac - 0.95) < 0.01


def test_yield_model_and_its_inverse():
    """Manual Step 4.4: y = 0.82 f plus the garbage that decodes as valid,
    y = 0.82 f + (1 - f) a  (a = the decoder's random-string acceptance)."""
    from skqd.skqd import READOUT_FACTOR, clean_fraction_from_yield, yield_model

    assert READOUT_FACTOR == 0.82

    # a = 0: the clean yield 0.82 f, the form the shot rule uses
    for f in (0.0, 0.002, 0.0154, 0.1261, 0.2, 1.0):
        assert yield_model(f, 0.0) == pytest.approx(0.82 * f)
        assert clean_fraction_from_yield(0.82 * f, 0.0) == pytest.approx(f)

    # limits in f: pure garbage at f = 0, pure readout survival at f = 1
    a0 = 38 / 4096                      # B = 0 at 2x2 (gate E2/H0P, exhaustive)
    a1 = 20 / 4096                      # B = 1 at 2x2
    for a in (a0, a1):
        assert yield_model(0.0, a) == pytest.approx(a)
        assert yield_model(1.0, a) == pytest.approx(0.82)

    # the garbage term is what the 0.82 f model misses, and it matters only when f ~ a/0.82
    assert yield_model(0.0154, a0) > 0.82 * 0.0154
    assert yield_model(0.0154, a0) - 0.82 * 0.0154 == pytest.approx((1 - 0.0154) * a0)
    assert yield_model(0.5, a0) / (0.82 * 0.5) < 1.02          # negligible while f >> a/0.82

    # monotone increasing in f (0.82 > a) and in a
    ys = [yield_model(f, a0) for f in np.linspace(0.0, 1.0, 21)]
    assert all(b > x for x, b in zip(ys, ys[1:]))
    assert yield_model(0.1, a0) > yield_model(0.1, a1) > yield_model(0.1, 0.0)

    # round trip, both directions, for a grid of (f, a)
    for a in (0.0, a1, a0, 0.05):
        for f in (0.0, 1e-3, 0.0154, 0.1261, 0.5, 1.0):
            assert clean_fraction_from_yield(yield_model(f, a), a) == pytest.approx(f, abs=1e-12)
        for y in (a, 0.05, 0.1493, 0.82):
            assert yield_model(clean_fraction_from_yield(y, a), a) == pytest.approx(y, abs=1e-12)

    # a different readout factor (the generic-noise branch of gate L4 uses (1 - p_ro)^n)
    rf = (1 - 0.01) ** 12
    assert yield_model(0.3, 0.0, readout_factor=rf) == pytest.approx(rf * 0.3)
    assert clean_fraction_from_yield(yield_model(0.3, a0, readout_factor=rf), a0,
                                     readout_factor=rf) == pytest.approx(0.3)

    # the inversion needs 0.82 > a
    with pytest.raises(ValueError):
        clean_fraction_from_yield(0.5, 0.82)
    with pytest.raises(ValueError):
        clean_fraction_from_yield(0.5, 0.9)

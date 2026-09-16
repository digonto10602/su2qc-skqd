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

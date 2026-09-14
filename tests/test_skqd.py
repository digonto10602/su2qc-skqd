import numpy as np

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

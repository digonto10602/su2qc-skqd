import numpy as np

from skqd.circuits_ir import CircuitFactory, run_ir, ucrz_gray
from skqd.exact import Model, mass_default
from skqd.krylov import basis_vector, coarse_states, references, term_groups
from skqd.reference_sim import CodewordEmbedding


def test_ucrz_gray():
    rng = np.random.default_rng(0)
    k = 3
    th = rng.uniform(-3, 3, size=2 ** k)
    gates = ucrz_gray(list(th), list(range(k)), k)
    n = k + 1
    U = np.zeros((2 ** n, 2 ** n), complex)
    for c in range(2 ** k):
        for t in range(2):
            U[c + (t << k), c + (t << k)] = np.exp(-1j * th[c] / 2 * (1 - 2 * t))
    v = rng.normal(size=2 ** n) + 1j * rng.normal(size=2 ** n)
    v /= np.linalg.norm(v)
    assert abs(run_ir(gates, n, v) - U @ v).max() < 1e-12


def test_coarse_step_circuits_match_emulation():
    M = Model(2)
    g2 = 4.0
    E = CodewordEmbedding(M)
    F = CircuitFactory(M, g2)
    groups = term_groups(M.terms, g2, mass_default(g2))
    for twoB in (0, 2):
        dt = M.reference(g2, twoB).dt
        for r in references(M.basis, twoB)[:2]:
            for k in (1, 3):
                psi = run_ir(F.coarse_step(r, k, dt), E.n)
                exact = coarse_states(groups, basis_vector(M.basis.dim, r), dt, k)[k]
                assert abs(psi - E.embed(exact)).max() < 1e-10
                assert E.leakage(psi) < 1e-12

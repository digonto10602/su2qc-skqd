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


def test_mcu_gate_matches_dense():
    """The multi-controlled U(2) IR gate (used by the structured decomposition path)."""
    rng = np.random.default_rng(5)
    n = 4
    A = rng.normal(size=(2, 2)) + 1j * rng.normal(size=(2, 2))
    Q, _ = np.linalg.qr(A)
    ctrl_state = 2  # controls (q0, q1, q2) = (0, 1, 0)
    gates = [("mcu", [0, 1, 2, 3], (Q, ctrl_state))]
    U = np.eye(2 ** n, dtype=complex)
    for z in range(2 ** n):
        if (z >> 3) & 1:
            continue
        if (z & 0b111) != ctrl_state:
            continue
        w = z | (1 << 3)
        U[z, z], U[z, w], U[w, z], U[w, w] = Q[0, 0], Q[0, 1], Q[1, 0], Q[1, 1]
    v = rng.normal(size=2 ** n) + 1j * rng.normal(size=2 ** n)
    v /= np.linalg.norm(v)
    assert abs(run_ir(gates, n, v) - U @ v).max() < 1e-12


def test_structured_hopping_equals_local_unitary():
    """Gate S2, step 1: the controlled-Givens-chain hopping gates reproduce the exact local
    block unitary exp(-i theta H_hop_l) on random physical states, for every 2x2 link."""
    from skqd.reference_sim import apply_local, local_unitary, term_support

    M = Model(2)
    g2 = 4.0
    E = CodewordEmbedding(M)
    F = CircuitFactory(M, g2)
    dt = M.reference(g2, 0).dt
    rng = np.random.default_rng(11)
    worst = 0.0
    vecs = []
    for _ in range(20):
        v = rng.normal(size=M.basis.dim) + 1j * rng.normal(size=M.basis.dim)
        vecs.append(E.embed(v / np.linalg.norm(v)))
    for l in range(M.lat.n_links):
        sup = term_support(M, "hop", l)
        for theta in (dt, 2 * dt, 4 * dt):
            gates = F.hop_gates_structured(l, theta)
            assert all(g[0] in ("cx", "ry", "rz", "rx", "x", "h", "p", "cp", "unitary", "gphase", "mcu")
                       for g in gates)
            assert all(g[0] != "unitary" or len(g[1]) == 1 for g in gates)
            U = local_unitary(M, M.terms.hop[l], sup, theta)
            for psi in vecs:
                worst = max(worst, float(abs(run_ir(gates, E.n, psi) - apply_local(psi, U, sup, E.n)).max()))
    assert worst < 1e-10, worst


def test_structured_coarse_steps_and_trotter():
    """The full structured coarse-step and Trotter circuits against the dressed-basis emulation."""
    from skqd.krylov import trotter_states

    M = Model(2)
    g2 = 4.0
    E = CodewordEmbedding(M)
    F = CircuitFactory(M, g2)
    groups = term_groups(M.terms, g2, mass_default(g2))
    worst = 0.0
    for twoB in (0, 2):
        dt = M.reference(g2, twoB).dt
        for r in references(M.basis, twoB)[:2]:
            exact = coarse_states(groups, basis_vector(M.basis.dim, r), dt, 4)
            for k in (1, 2, 3, 4):
                psi = run_ir(F.coarse_step(r, k, dt), E.n)
                worst = max(worst, float(abs(psi - E.embed(exact[k])).max()))
                assert E.leakage(psi) < 1e-9
            tr = trotter_states(groups, basis_vector(M.basis.dim, r), dt, 3)
            for steps in (1, 2):
                psi = run_ir(F.trotter(r, steps, dt), E.n)
                worst = max(worst, float(abs(psi - E.embed(tr[steps])).max()))
    assert worst < 1e-10, worst


def test_dense_and_structured_hopping_agree():
    """The dense (L3 baseline) and structured hopping paths are the same unitary on codewords."""
    M = Model(2)
    E = CodewordEmbedding(M)
    Fd = CircuitFactory(M, 4.0, structured_hopping=False)
    Fs = CircuitFactory(M, 4.0, structured_hopping=True)
    dt = M.reference(4.0, 0).dt
    rng = np.random.default_rng(3)
    v = rng.normal(size=M.basis.dim) + 1j * rng.normal(size=M.basis.dim)
    psi = E.embed(v / np.linalg.norm(v))
    for l in range(M.lat.n_links):
        a = run_ir(Fd.hop_gates(l, dt), E.n, psi)
        b = run_ir(Fs.hop_gates(l, dt), E.n, psi)
        assert abs(a - b).max() < 1e-10

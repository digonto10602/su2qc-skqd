import numpy as np
import pytest

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
    qiskit = pytest.importorskip("qiskit")
    from skqd.circuits_qiskit import ir_to_qiskit

    qc = ir_to_qiskit(gates, n, measure=False)
    Uq = np.asarray(qiskit.quantum_info.Operator(qc).data)
    assert abs(Uq - U).max() < 1e-12


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
    qiskit = pytest.importorskip("qiskit")
    from skqd.circuits_qiskit import ir_to_qiskit

    qc = ir_to_qiskit(gates, n, measure=False)
    Uq = np.asarray(qiskit.quantum_info.Operator(qc).data)
    assert abs(Uq - U).max() < 1e-12


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


def _local_deviation(M, O, support, thetas, rng, nvec=5):
    """max |structured gates - exp(-i theta O_loc)| on the local support (2^k amplitudes).
    The exact exponential comes from the small block h of reference_sim.localize, so the
    dense 14-qubit unitary of a 2x3 plaquette (4 GiB) is never built."""
    import scipy.linalg as sla

    from skqd.circuits_ir import structured_term_gates
    from skqd.reference_sim import localize

    k = len(support)
    states, h, _ = localize(M, O, support)
    idx = np.array(states)
    pos = {q: i for i, q in enumerate(support)}
    vecs = []
    for _ in range(nvec):
        c = rng.normal(size=len(states)) + 1j * rng.normal(size=len(states))
        vecs.append(c / np.linalg.norm(c))
    worst = 0.0
    for theta in thetas:
        gates = structured_term_gates(M, O, support, theta)
        loc = [(nm, [pos[q] for q in qs], par) for nm, qs, par in gates]
        U = sla.expm(-1j * theta * h)
        for c in vecs:
            psi = np.zeros(2 ** k, dtype=complex)
            psi[idx] = c
            out = run_ir(loc, k, psi)
            exact = np.zeros(2 ** k, dtype=complex)
            exact[idx] = U @ c
            worst = max(worst, float(np.abs(out - exact).max()))
    return worst


def test_structured_terms_2x3():
    """Gate S2, step 3: every 2x3 term -- the hopping links (blocks of up to four
    configurations) and the two plaquettes with interior corners (14 qubits) -- as exact
    basic-gate circuits, at theta = dt, 2dt, 4dt."""
    from skqd.reference_sim import term_support

    M = Model(3)
    g2 = 4.0
    dt = M.reference(g2, 0).dt
    rng = np.random.default_rng(17)
    thetas = (dt, 2 * dt, 4 * dt)
    worst = 0.0
    for l in range(M.lat.n_links):
        worst = max(worst, _local_deviation(M, M.terms.hop[l], term_support(M, "hop", l), thetas, rng))
    for P in range(len(M.lat.plaquettes)):
        sup = term_support(M, "plaq", P)
        assert len(sup) == 14
        worst = max(worst, _local_deviation(M, -M.terms.plaq[P] / (2 * g2), sup, thetas, rng, nvec=3))
    assert worst < 1e-10, worst


def test_structured_plaquette_2x3_on_physical_states():
    """The interior-corner plaquette gate on the full 2^20 statevector, against the
    dressed-basis emulation of exp(-i theta H_plaq) (krylov's expm_multiply)."""
    import scipy.sparse.linalg as spl

    M = Model(3)
    g2 = 4.0
    E = CodewordEmbedding(M)
    F = CircuitFactory(M, g2)
    dt = M.reference(g2, 0).dt
    rng = np.random.default_rng(23)
    v = rng.normal(size=M.basis.dim) + 1j * rng.normal(size=M.basis.dim)
    v /= np.linalg.norm(v)
    O = (-M.terms.plaq[1] / (2 * g2)).tocsc()
    psi = run_ir(F.plaq_gates(1, dt, True), E.n, E.embed(v))
    exact = E.embed(spl.expm_multiply(-1j * dt * O, v))
    assert abs(psi - exact).max() < 1e-10
    assert abs(E.leakage(psi)) < 1e-9


# ------------------------------------------------- fixed-angle generator (prompts/11)
def _local_action(M, F, name, O, support, theta):
    """The matrix of the term circuit on the local codeword states (run_ir on 2^k)."""
    from skqd.circuits_ir import run_ir
    from skqd.reference_sim import localize

    states, h, _ = localize(M, O, support)
    k = len(support)
    pos = {q: i for i, q in enumerate(support)}
    gates = F.hop_gates(int(name[3:]), theta) if name.startswith("hop") else \
        F.plaq_gates(int(name[4:]), theta, True)
    loc = [(nm, [pos[q] for q in qs], par) for nm, qs, par in gates]
    idx = np.array(states)
    W = np.zeros((len(states), len(states)), dtype=complex)
    leak = 0.0
    for j in range(len(states)):
        psi = np.zeros(2 ** k, dtype=complex)
        psi[idx[j]] = 1.0
        out = run_ir(loc, k, psi)
        W[:, j] = out[idx]
        leak = max(leak, abs(1.0 - float(np.sum(np.abs(out[idx]) ** 2))))
    return states, h, W, leak


def test_fixed_angle_leakage_and_pair_structure_2x2():
    """angle_mode='fixed': the generator is unitary on the codeword space (leakage < 1e-12),
    it connects only configurations that the exact term connects (same connected blocks),
    and it is NOT the exact exponential (that is the point: it is cheaper)."""
    import scipy.linalg as sla
    import scipy.sparse as sp
    import scipy.sparse.csgraph as csgraph

    from skqd.reference_sim import term_support

    M = Model(2)
    g2 = 4.0
    dt = M.reference(g2, 0).dt
    F = CircuitFactory(M, g2, angle_mode="fixed")
    terms = [(f"hop{l}", M.terms.hop[l], term_support(M, "hop", l)) for l in range(M.lat.n_links)]
    terms += [(f"plaq{P}", -M.terms.plaq[P] / (2 * g2), term_support(M, "plaq", P))
              for P in range(len(M.lat.plaquettes))]
    differs = 0.0
    for name, O, sup in terms:
        for theta in (dt, 2 * dt):
            states, h, W, leak = _local_action(M, F, name, O, sup, theta)
            assert leak < 1e-12, (name, theta, leak)
            assert abs(W.conj().T @ W - np.eye(len(states))).max() < 1e-10, name
            A = np.abs(h) > 1e-12
            np.fill_diagonal(A, False)
            _, lab = csgraph.connected_components(sp.csr_matrix(A), directed=False)
            assert abs(W[lab[:, None] != lab[None, :]]).max(initial=0.0) < 1e-10, \
                f"{name}: the fixed-angle circuit connects different blocks of the term"
            differs = max(differs, float(abs(W - sla.expm(-1j * theta * h)).max()))
    assert differs > 1e-3, "the fixed-angle circuits should differ from the exact exponentials"


def test_fixed_angle_theta_eff_is_the_mean_of_the_merged_elements():
    """theta_eff of every multiplexed rotation = theta x mean of the DISTINCT |elements| of
    the term with that qubit-flip pattern (the contract recorded in validation/S2_fixed.json)."""
    from skqd.circuits_ir import _real_gauge
    from skqd.reference_sim import localize, term_support

    M = Model(2)
    g2 = 4.0
    dt = M.reference(g2, 0).dt
    F = CircuitFactory(M, g2, angle_mode="fixed")
    for l in range(M.lat.n_links):
        sup = term_support(M, "hop", l)
        F.hop_gates(l, dt)
        stats = F.fixed_stats[(f"hop{l}", round(dt, 12))]
        states, h, _ = localize(M, M.terms.hop[l], sup)
        _, A = _real_gauge(states, h)
        want = {}
        for i in range(len(states)):
            for j in range(i + 1, len(states)):
                if abs(A[i, j]) > 1e-12:
                    want.setdefault(states[i] ^ states[j], set()).add(round(abs(float(np.real(A[i, j]))), 12))
        assert {s["flip_pattern"] for s in stats} == set(want), l
        for s in stats:
            mags = sorted(want[s["flip_pattern"]])
            assert s["merged_elements"] == pytest.approx(mags)
            assert s["theta_eff"] == pytest.approx(dt * float(np.mean(mags)))


def test_fixed_angle_terms_2x3_are_leak_free():
    """The hard requirement of prompts/11 at 2x3: every fixed-angle term maps codewords to
    codewords (the interior-corner plaquette is the demanding case, 14 qubits)."""
    from skqd.reference_sim import term_support

    M = Model(3)
    g2 = 4.0
    dt = M.reference(g2, 0).dt
    F = CircuitFactory(M, g2, angle_mode="fixed")
    rng = np.random.default_rng(31)
    worst = 0.0
    for name, O, sup in [("hop0", M.terms.hop[0], term_support(M, "hop", 0)),
                         ("hop4", M.terms.hop[4], term_support(M, "hop", 4)),
                         ("plaq1", -M.terms.plaq[1] / (2 * g2), term_support(M, "plaq", 1))]:
        from skqd.reference_sim import localize
        states, h, _ = localize(M, O, sup)
        k = len(sup)
        pos = {q: i for i, q in enumerate(sup)}
        gates = F.hop_gates(int(name[3:]), dt) if name.startswith("hop") else F.plaq_gates(1, dt, True)
        loc = [(nm, [pos[q] for q in qs], par) for nm, qs, par in gates]
        idx = np.array(states)
        for _ in range(3):
            c = rng.normal(size=len(states)) + 1j * rng.normal(size=len(states))
            psi = np.zeros(2 ** k, dtype=complex)
            psi[idx] = c / np.linalg.norm(c)
            out = run_ir(loc, k, psi)
            worst = max(worst, abs(1.0 - float(np.sum(np.abs(out[idx]) ** 2))))
    assert worst < 1e-12, worst


def test_run_ir_fast_paths_match_apply_local():
    """The in-place permutation/diagonal paths of run_ir are the same operation as
    reference_sim.apply_local (which stays the definition)."""
    from skqd.reference_sim import apply_local

    rng = np.random.default_rng(7)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    CX = np.array([[1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 1, 0, 0]], dtype=complex)
    n = 5
    psi = rng.normal(size=2 ** n) + 1j * rng.normal(size=2 ** n)
    for _ in range(200):
        a, b = rng.choice(n, size=2, replace=False)
        a, b = int(a), int(b)
        th = float(rng.normal())
        for name, qs, par, U in (("x", [a], None, X), ("cx", [a, b], None, CX),
                                 ("p", [a], th, np.diag([1.0, np.exp(1j * th)])),
                                 ("rz", [a], th, np.diag([np.exp(-1j * th / 2), np.exp(1j * th / 2)])),
                                 ("cp", [a, b], th, np.diag([1.0, 1.0, 1.0, np.exp(1j * th)]))):
            assert abs(run_ir([(name, qs, par)], n, psi) - apply_local(psi, U, qs, n)).max() < 1e-13

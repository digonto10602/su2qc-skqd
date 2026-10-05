"""prompts/28 Part A: the Pauli-trajectory engine (scripts/cf_trajectories.py) on small circuits.

The decisive exactness test: on a 3-qubit circuit, the trajectory decomposition summed over EVERY Pauli
draw (weights of Aer's depolarizing_error) equals Aer's own density-matrix simulation of the same noise
model to 1e-12 -- which fixes the error placement (after the gate), the event probabilities (15/16 p2,
3/4 p1) and the Pauli insertion in one go."""
import itertools
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import cf_trajectories as cf  # noqa: E402

pytest.importorskip("qiskit_aer")

IR = [("rx", [0], 0.7), ("rz", [1], 0.3), ("rzz", [0, 1], 0.9), ("ry", [2], 0.4), ("rz", [2], 1.1),
      ("rx", [1], 1.3), ("rzz", [1, 2], 0.5)]


def _sv(gates, n):
    from qiskit.quantum_info import Statevector

    from skqd import circuits_qiskit as cq

    return np.asarray(Statevector(cq.ir_to_qiskit(gates, n, measure=False)).data)


def test_event_probabilities_and_g0():
    e2, e1 = cf.event_probabilities(8.3e-4, 2.8e-5)
    assert e2 == pytest.approx(15 / 16 * 8.3e-4, rel=1e-15)
    assert e1 == pytest.approx(0.75 * 2.8e-5, rel=1e-15)
    # the A6 aer-channel no-error probability of B0_ref25_k1 (predict.json), recomputed from its counts
    g0 = cf.no_error_probability(2158, 3091, 8.3e-4, 2.8e-5)
    bits = [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    f0 = g0 * cf.readout_survival(bits, 6.7e-4, 1.2e-3)
    assert abs(f0 - 0.17208700946729633) < 1e-12


def test_noise_sites_and_insert():
    sites = cf.noise_sites(IR)
    assert [(p, k) for p, k, _ in sites] == [(0, "1q"), (2, "2q"), (3, "1q"), (5, "1q"), (6, "2q")]
    ev = [[1, 2, "2q", [0, 1], "XZ"], [3, 5, "1q", [1], "Y"]]
    out = cf.insert_paulis(IR, ev, 0)
    assert out[3] == ("x", [0], None) and out[4] == ("z", [1], None)
    assert out[8] == ("y", [1], None)
    assert cf.insert_paulis(IR, ev, 2)[0] == IR[2]
    with pytest.raises(ValueError):
        cf.insert_paulis(IR, ev, 3)
    assert cf.is_z_type([[0, 0, "2q", [0, 1], "IZ"], [0, 0, "1q", [0], "Z"]])
    assert not cf.is_z_type([[0, 0, "2q", [0, 1], "XZ"]])


def test_draws_reject_identity_and_match_g0():
    sites = cf.noise_sites(IR) * 40                       # 200 sites
    p2, p1 = 0.02, 0.01
    rng = np.random.default_rng(5)
    trajs, draws = cf.draw_trajectories(rng, sites, 3000, p2, p1)
    assert all(len(t) >= 1 for t in trajs)
    n2 = sum(k == "2q" for _p, k, _q in sites)
    g0 = cf.no_error_probability(n2, len(sites) - n2, p2, p1)
    rej = draws - len(trajs)
    sd = math.sqrt(draws * g0 * (1 - g0))
    assert abs(rej - draws * g0) < 5 * sd
    trajs_xx, _ = cf.draw_trajectories(np.random.default_rng(6), sites, 200, p2, p1, "xx")
    assert {e[4] for t in trajs_xx for e in t} <= {"XX", "X"}


def test_readout_convolve_matches_kron():
    n, p10, p01 = 4, 0.07, 0.19
    rng = np.random.default_rng(1)
    p = rng.random(2 ** n)
    p /= p.sum()
    # column-stochastic per-qubit matrix A[out, in]; qubit k = bit k -> kron order q_{n-1} ... q_0
    A = np.array([[1 - p10, p01], [p10, 1 - p01]])
    K = A
    for _ in range(n - 1):
        K = np.kron(A, K)
    assert np.max(np.abs(cf.readout_convolve(p, n, p10, p01) - K @ p)) < 1e-15


def test_readout_convention_matches_aer_readout_error():
    """Aer ReadoutError([[1-p10, p10], [p01, 1-p01]]): qubit 0 prepared in |0>, qubit 1 in |1>."""
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, ReadoutError

    p10, p01, shots = 0.10, 0.25, 40000
    nm = NoiseModel()
    nm.add_all_qubit_readout_error(ReadoutError([[1 - p10, p10], [p01, 1 - p01]]))
    qc = QuantumCircuit(2, 2)
    qc.x(1)
    qc.measure([0, 1], [0, 1])
    c = AerSimulator(noise_model=nm, seed_simulator=3).run(qc, shots=shots).result().get_counts()
    f0 = sum(v for k, v in c.items() if k[-1] == "1") / shots          # qubit 0 read as 1
    f1 = sum(v for k, v in c.items() if k[-2] == "0") / shots          # qubit 1 read as 0
    p = np.zeros(4)
    p[0b10] = 1.0
    q = cf.readout_convolve(p, 2, p10, p01)
    assert abs(f0 - (q[0b01] + q[0b11])) < 5 * math.sqrt(p10 * (1 - p10) / shots)
    assert abs(f1 - (q[0b00] + q[0b01])) < 5 * math.sqrt(p01 * (1 - p01) / shots)


def test_aer_error_placement_after_gate():
    assert cf.aer_error_placement_check()["error_applied_after_gate"]


@pytest.mark.parametrize("channel", ["depol", "xx"])
def test_trajectory_sum_equals_aer_density_matrix(channel):
    """Exact enumeration of every Pauli draw on a 3-qubit circuit vs Aer density matrix."""
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error

    from skqd import circuits_qiskit as cq

    n, p2, p1 = 3, 0.3, 0.2
    ir = [("rx", [0], 0.7), ("rz", [1], 0.3), ("rzz", [0, 1], 0.9), ("rz", [2], 1.1), ("ry", [1], 1.3)]
    sites = cf.noise_sites(ir)
    lab2, lab1 = cf.CHANNELS[channel]
    e2, e1 = cf.event_probabilities(p2, p1)
    opts = []
    for i, (pos, kind, qs) in enumerate(sites):
        labs, e = (lab2, e2) if kind == "2q" else (lab1, e1)
        opts.append([(None, 1 - e)] + [([i, pos, kind, qs, lab], e / len(labs)) for lab in labs])
    p_mix = np.zeros(2 ** n)
    wsum = 0.0
    for combo in itertools.product(*opts):
        w = float(np.prod([c[1] for c in combo]))
        ev = [c[0] for c in combo if c[0] is not None]
        p_mix += w * np.abs(_sv(cf.insert_paulis(ir, ev, 0), n)) ** 2
        wsum += w
    assert abs(wsum - 1) < 1e-14
    nm = NoiseModel(basis_gates=["rz", "rx", "ry", "rzz"])
    if channel == "depol":
        nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["rzz"])
        nm.add_all_qubit_quantum_error(depolarizing_error(p1, 1), ["rx", "ry"])
    else:
        xx = cf.xx_noise_model(p2, p1, 0.0, 0.0)
        nm = xx
    qc = cq.ir_to_qiskit(ir, n, measure=False)
    qc.save_density_matrix()
    rho = np.asarray(AerSimulator(method="density_matrix", noise_model=nm).run(qc).result().data(0)["density_matrix"])
    assert np.max(np.abs(np.real(np.diag(rho)) - p_mix)) < 1e-12


def test_checkpoint_evolution_is_exact():
    n = 3
    sim = cf.aer_sim(1)
    ev = [[1, 2, "2q", [0, 1], "YX"], [3, 5, "1q", [1], "Z"]]
    full = cf.evolve(None, cf.insert_paulis(IR, ev, 0), n, sim)
    mid = cf.evolve(None, IR[:2], n, sim)
    part = cf.evolve(mid, cf.insert_paulis(IR, ev, 2), n, sim)
    assert np.max(np.abs(np.abs(full) ** 2 - np.abs(part) ** 2)) < 1e-14
    ref = _sv(cf.insert_paulis(IR, ev, 0), n)
    assert np.max(np.abs(np.abs(full) ** 2 - np.abs(ref) ** 2)) < 1e-14


def test_tv_distance():
    a = np.array([0.5, 0.5, 0.0])
    assert cf.tv_distance(a * 0.5, a) == pytest.approx(0.0)
    assert cf.tv_distance(np.array([0.0, 0.0, 1.0]), a) == pytest.approx(1.0)
    d = cf.hamming_distance_table(3, 0b101)
    assert list(d) == [2, 1, 3, 2, 1, 0, 2, 1]


# --------------------------------------------------------------------------- gate_CF_traj formulas
def _synthetic_arm(p_tau_fn, K=50, dim=6):
    """A fake arm: ideal p_c over `dim` sector states, reference at position 0."""
    pc = np.array([0.80, 0.10, 0.05, 0.03, 0.0195, 0.0005])
    trajs = []
    rng = np.random.default_rng(0)
    for i in range(K):
        p = p_tau_fn(pc, rng)
        trajs.append({"p_ref_post": float(p[0]), "p_ref_pre": float(p[0]), "tail_post": float(p[1:5].sum()),
                      "tv_pre": cf.tv_distance(p, pc) if p.sum() > 0 else 1.0, "z_only": bool(i % 3 == 0),
                      "n_2q": 1, "n_1q": 0, "p_sector_post": [float(x) for x in p]})
    base = {"no_error_probability_g0": cf.no_error_probability(10, 10, 0.01, 0.01),
            "readout_survival_reference": cf.readout_survival([0, 1], 0.001, 0.002), "channel": "depol",
            "sector": {"tail_pos": [1, 2, 3, 4], "S99": [0, 1, 2, 3], "S999": [0, 1, 2, 3, 4, 5],
                       "ints": [0, 1, 2, 3, 4, 5], "ref_pos": 0},
            "ideal": {"p_c": list(pc), "p_ref_post_readout": 0.8, "p_sector_vs_verify_json_max_abs": 0.0},
            "chunk": 0, "seed": 1, "K": K, "git_commit": "x", "git_dirty_scripts_src": False, "wall_s": 1.0,
            "workers": 1, "n_draws": K, "n_rejected_all_identity": 0,
            "aer_error_placement_check": {"error_applied_after_gate": True}, "trajectories": trajs}
    man = {"counts": {"n_zz": 10, "n_phasedx": 10}, "reference_bits": [0, 1], "p_reference": 0.8}
    A6 = {"depolarizing_2q_rzz": 0.01, "depolarizing_1q_rx_ry": 0.01, "readout_p1_given_0": 0.001,
          "readout_p0_given_1": 0.002}
    return {"chunks": [("f", base)], "base": base, "trajs": trajs}, man, A6


def test_gate_formulas_limits():
    import gate_CF_traj as g

    # faulty trajectories that never land in the sector: every rate equals f0'
    arm, man, A6 = _synthetic_arm(lambda pc, rng: np.zeros_like(pc))
    s = g.arm_statistics("syn", arm, man, A6, None)
    f0 = s["f0_prime"]
    assert s["stats"]["rho_ref"]["value"] == pytest.approx(1.0)
    assert s["stats"]["rho_T"]["value"] == pytest.approx(1.0)
    assert s["stats"]["min_feff_over_f0_S999"]["value"] == pytest.approx(1.0)
    assert s["stats"]["benign_fraction"]["value"] == 0.0
    # faulty trajectories that reproduce the ideal distribution: every rate equals 1, b = 1
    arm, man, A6 = _synthetic_arm(lambda pc, rng: pc.copy())
    s = g.arm_statistics("syn", arm, man, A6, None)
    assert s["stats"]["f_hit"]["value"] == pytest.approx(1.0)
    assert s["stats"]["f_T"]["value"] == pytest.approx(1.0)
    assert s["stats"]["rho_T"]["value"] == pytest.approx(1.0 / f0)
    assert s["stats"]["benign_fraction"]["value"] == 1.0
    assert s["stats"]["n_S99_feff_below_margin_fT"]["value"] == 0


def test_gate_poisson_helpers():
    import gate_CF_traj as g
    from scipy.stats import poisson

    assert g.two_sided_poisson_p(64, 44.06) == pytest.approx(2 * poisson.sf(63, 44.06))
    lo, hi = g.poisson_band(44.0)
    assert poisson.cdf(lo - 1, 44.0) < 0.025 <= poisson.cdf(lo, 44.0)
    assert hi >= 44 + 1.9 * math.sqrt(44.0)
    lo, hi = g.clopper_pearson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** 0.1)


def test_checkpoint_index_never_skips_the_error_gate():
    bounds = [0, 10, 20, 30]
    assert cf.checkpoint_index(bounds, 0) == 0
    assert cf.checkpoint_index(bounds, 9) == 0
    assert cf.checkpoint_index(bounds, 10) == 1          # state after gates[0:10]; gate 10 re-applied
    assert cf.checkpoint_index(bounds, 29) == 2
    assert cf.checkpoint_index(bounds, 35) == 3
    for first in range(40):
        c = cf.checkpoint_index(bounds, first)
        ev = [[0, first, "1q", [0], "X"]]
        ir = [("rx", [0], 0.1)] * 40
        cf.insert_paulis(ir, ev, bounds[c])               # must not raise

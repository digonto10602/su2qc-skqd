"""
prompts/33 A3: the noise scenarios of the campaign (src/skqd/campaign33/noise.py).

No-fault probabilities, the Pauli-twirled relaxation (non-negative for T2 <= 2 T1, total = the idle.py
per-window term, equal to the numerical twirl of Aer's channel), the angle-dependent two-qubit error at
theta = 0, pi/2, pi, the E5 memory-site count, the matched-f eps2 values, and the class-2 record model
equal to NoiseModel.from_backend(backend_from_record(...)) in every Kraus matrix.
"""
import json
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from skqd.campaign33 import noise as N  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RECORD = os.path.join(ROOT, "data", "hardware", "K0_prep", "ibm_kingston_full_20261006T0652Z.json")


def test_no_fault_probabilities_of_aer_depolarizing():
    from qiskit_aer.noise import depolarizing_error
    for p in (1e-4, 8.3e-4, 1e-2):
        assert abs(N.identity_probability(depolarizing_error(p, 2)) - (1 - 15 * p / 16)) < 1e-14
        assert abs(N.identity_probability(depolarizing_error(p, 1)) - (1 - 3 * p / 4)) < 1e-14


def test_pta_is_a_probability_distribution_iff_t2_le_2t1():
    for t1 in (5e-5, 2e-4):
        for r in (0.05, 0.5, 1.0, 1.5, 2.0):
            for t in (1e-8, 1e-6, 3e-5, 1e-3):
                p = N.pta_relaxation_probs(t, t1, r * t1)
                assert min(p.values()) >= -1e-15 and abs(sum(p.values()) - 1) < 1e-14
    assert N.pta_relaxation_probs(1e-5, 1e-4, 2.5e-4)["Z"] < 0, "T2 > 2 T1 is not a channel"


def test_pta_total_equals_the_idle_py_window_term():
    from skqd import idle
    rec = {"qubits": {"0": {"T1_s": 2e-4, "T2_s": 1.5e-4, "sx_duration_s": 3.2e-8, "sx_error": 2e-4}}}
    w = [1e-7, 2.5e-6, 4e-5]
    sch = {"active": [0], "per_qubit": {0: {"windows_s": w, "busy_s": 0.0, "delay_s": sum(w), "idle_s": sum(w)}}}
    _pq, tot = idle.idle_budget(sch, rec)
    assert abs(sum(N.pta_total(x, 2e-4, 1.5e-4) for x in w) - (tot["S_T1"] + tot["S_T2"])) < 1e-15


def test_pta_equals_the_numerical_twirl_of_aer_thermal_relaxation():
    from qiskit_aer.noise import thermal_relaxation_error
    for t, t1, t2 in ((1e-6, 2e-4, 1.5e-4), (5e-6, 1e-4, 1.9e-4), (3e-5, 8e-5, 2e-5), (4e-7, 3e-4, 6e-4)):
        tw = N.pauli_twirl_probs(thermal_relaxation_error(t1, t2, t))
        cf = N.pta_relaxation_probs(t, t1, t2)
        assert max(abs(tw[k] - cf[k]) for k in "IXYZ") < 1e-13


def test_angle_dependent_two_qubit_error():
    a, b = N.E3["angle_a"], N.E3["angle_b"]
    assert abs(N.angle_factor(0.0, a, b) - b) < 1e-15
    assert abs(N.angle_factor(math.pi, a, b) - (a + b)) < 1e-15
    assert abs(N.angle_factor(math.pi / 2, a, b) - 1.0) < 2e-3, "~1 at ZZMax (the calibrated gate)"
    assert abs(N.angle_factor(2 * math.pi - 0.1, a, b) - N.angle_factor(-0.1, a, b)) < 1e-14
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(2, 2)
    qc.rzz(math.pi, 0, 1)
    qc.rzz(0.0, 0, 1)
    qc.measure([0, 1], [0, 1])
    spec = N.quantinuum_spec("E3", 2)
    out = spec.apply(qc)
    errs = [i.operation for i in out.data if i.operation.name not in ("rzz", "measure", "barrier")]
    two = [e for e in errs if e.num_qubits == 2]
    assert len(two) == 2 and len([e for e in errs if e.num_qubits == 1]) == 2, "two rzz errors, two init flips"
    p_pi = 1 - N.identity_probability(two[0])
    p_0 = 1 - N.identity_probability(two[1])
    assert abs(p_pi - 15 / 16 * N.E3["p2"] * (a + b)) < 1e-15 and abs(p_0 - 15 / 16 * N.E3["p2"] * b) < 1e-15


def test_memory_sites_are_n_qubits_times_layers():
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(4, 4)
    qc.rzz(0.3, 0, 1)
    qc.rx(0.2, 2)
    qc.rzz(0.1, 1, 2)
    qc.rzz(0.4, 0, 3)
    qc.rzz(0.5, 2, 3)
    qc.barrier()
    qc.measure(range(4), range(4))
    layers = N.rzz_layers(qc)
    assert layers == [1, 2, 2, 3]
    out = N.memory_transform(1e-3)(qc)
    assert out.metadata["memory_sites"] == 4 * 3 == sum(1 for i in out.data if i.operation.name not in
                                                         ("rzz", "rx", "barrier", "measure"))
    # every qubit gets exactly one site per layer
    per_q = {}
    for i in out.data:
        if i.operation.name not in ("rzz", "rx", "barrier", "measure"):
            q = out.find_bit(i.qubits[0]).index
            per_q[q] = per_q.get(q, 0) + 1
    assert per_q == {0: 3, 1: 3, 2: 3, 3: 3}


def test_memory_sites_on_a_frozen_native_circuit():
    from skqd.campaign33 import circuits as C
    if not os.path.exists(C.qpy_path("NAT-O0", "B0_ref25_k1")):
        pytest.skip("NAT-O0 not frozen yet")
    qc = C.load_circuit("NAT-O0", "B0_ref25_k1")
    man = C.load_manifest("NAT-O0", "B0_ref25_k1")
    out = N.memory_transform(3.08e-6)(qc)
    assert out.metadata["memory_layers"] == man["native_counts"]["depth_2q"] == 1925
    assert out.metadata["memory_sites"] == 20 * 1925


def test_matched_f_eps2():
    want = {0.05: 1.3390e-3, 0.07: 1.1833e-3, 0.10: 1.0182e-3, 0.15: 8.3048e-4}      # prompts/33 1.2
    for f, e in want.items():
        assert abs(N.matched_f_eps2(f) - e) < 5e-8
        assert abs(N.f_gate(N.matched_f_eps2(f)) - f) < 1e-12
    assert abs(N.matched_f_eps2(0.10) - N.device_table_eps2_f010()) <= 1e-9


def test_f0_of_e1_at_the_mean_counts():
    """g0 = (1 - 15/16 p2)^2158 (1 - 3/4 p1)^3053 = 0.1748 (prompts/33 2.1, planner arithmetic)."""
    g0 = (1 - 15 / 16 * N.E1["p2"]) ** 2158 * (1 - 0.75 * N.E1["p1"]) ** 3053
    assert abs(g0 - 0.1748) < 5e-5


def test_every_quantinuum_scenario_builds_and_describes_itself():
    for sid in N.QUANTINUUM_SCENARIOS:
        spec = N.quantinuum_spec(sid)
        d = spec.description
        assert d["id"] == sid and "not_modelled" in d and d["source"]
        json.dumps(d)
    assert "rz" in N.quantinuum_spec("E8").noise_model.noise_instructions
    assert "rz" not in N.quantinuum_spec("E1").noise_model.noise_instructions, "Rz virtual in E1"


@pytest.fixture(scope="module")
def record():
    with open(RECORD) as fh:
        return json.load(fh)


def test_record_model_equals_from_backend(record):
    pytest.importorskip("qiskit_ibm_runtime")
    from qiskit.quantum_info import SuperOp
    from qiskit_aer.noise import NoiseModel
    from qiskit_ibm_runtime.fake_provider import FakeKingston

    from h0_backends import backend_from_record
    b, _ = backend_from_record(record, base=FakeKingston(), strict=True)
    ref = NoiseModel.from_backend(b)
    mine = N.kraus_record_model(record)
    er, em = N._local_errors(ref), N._local_errors(mine)
    keys = [k for k in er if k[0] in ("cz", "sx", "x")]
    assert len(keys) == 664 and set(keys) == {k for k in em}
    worst = max(float(np.max(np.abs(SuperOp(er[k].to_quantumchannel()).data - SuperOp(em[k].to_quantumchannel()).data)))
                for k in keys)
    assert worst <= 1e-12
    for q, e in ref._local_readout_errors.items():
        assert np.max(np.abs(np.asarray(e.probabilities) - np.asarray(mine._local_readout_errors[q].probabilities))) <= 1e-12
    pr, pm = ref._custom_noise_passes[0], mine._custom_noise_passes[0]
    patch = [q for q in range(156) if str(q) in record["qubits"] and record["qubits"][str(q)]["T1_s"] is not None]
    assert np.max(np.abs(np.asarray(pr._t1s)[patch] - np.asarray(pm._t1s)[patch])) <= 1e-15
    assert np.max(np.abs(np.asarray(pr._t2s)[patch] - np.asarray(pm._t2s)[patch])) <= 1e-15


def test_pta_record_model_keeps_the_no_fault_weight(record):
    k = N.ibm_spec(record, "I-ECHO", "kraus", "echo")
    p = N.ibm_spec(record, "I-ECHO", "pta", "echo")
    for key in [("cz", (92, 93)), ("sx", (50,)), ("x", (51,))]:
        if key not in k.local_errors:
            continue
        assert abs(N.identity_probability(k.local_errors[key]) - N.identity_probability(p.local_errors[key])) < 1e-13
    assert p.description["representation"] == "pta" and p.transform is not None


def test_star_and_coherent_cells(record):
    ratio = N.t2_star_ratio()
    assert abs(ratio - 0.174) < 1e-3
    s = N.ibm_spec(record, "I-STAR", "kraus", "star", ratio)
    q = 50
    assert abs(s.t2s[q] - min(record["qubits"]["50"]["T2_s"] * ratio, 2 * record["qubits"]["50"]["T1_s"])) < 1e-18
    eps, info = N.coherent_eps_for([59, 50])
    assert eps[59] == 0.0181 and eps[50] == info["median_rad"]
    c = N.ibm_spec(record, "I-COH", "kraus", "echo", coherent_eps={59: 0.0181})
    e = N.ibm_spec(record, "I-ECHO", "kraus", "echo")
    assert N.identity_probability(c.local_errors[("x", (59,))]) < N.identity_probability(e.local_errors[("x", (59,))])
    assert "coherent over-rotation Rx(eps_q) after every x" in c.description["channel_classes"]

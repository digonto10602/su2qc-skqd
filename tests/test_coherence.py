"""`skqd.coherence`: the coherence requirement and its anchors (gate S2_2x4, C7 and C8).

Four checks:
 (i)   a hand-built serial circuit on a uniform record -- the ASAP duration is n_2q t_2q and,
       in the linearised limit, the T2 requirement is the serial formula times (1 - qubit-time
       utilisation), which is the exact statement of what premise (b) of the formula costs;
 (ii)  the frozen 2x2 canary on the real ibm_fez record reproduces the committed T_s, S_T1 and
       S_T2 of `data/S2_duration_compare.json` to 1e-9 relative;
 (iii) `serial_bound` on the committed counts reproduces the owner's five numbers to 0.1;
 (iv)  the requirement is monotone in the target and the serial bound in the gate count.
"""
import gzip
import json
import math
import os

import numpy as np
import pytest

from skqd import coherence as coh
from skqd import idle as sk_idle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _serial_cz_circuit(n_pairs=10):
    qiskit = pytest.importorskip("qiskit")
    qc = qiskit.QuantumCircuit(3)
    for _ in range(n_pairs):
        qc.cz(0, 1)
        qc.cz(1, 2)
    return qc, 2 * n_pairs


def test_serial_schedule_and_the_linearised_requirement():
    qc, n_2q = _serial_cz_circuit()
    rec = coh.uniform_record(3, [(0, 1), (1, 2), (0, 2)], t_1q=0.0, T1=1e-3, T2=1e-4)
    sch = sk_idle.schedule_asap(qc, rec)
    t_2q = coh.record_t_2q(rec)
    assert abs(sch["T_s"] - n_2q * t_2q) < 1e-15          # a perfectly serial chain
    assert abs(coh.seriality(sch, n_2q, t_2q) - 1.0) < 1e-12
    util = coh.utilisation(sch)
    assert abs(util - 2.0 / 3.0) < 1e-12                  # q1 busy always, q0 and q2 half
    # f_target close to 1 keeps T2_req far above every window, i.e. the linearised regime
    r = coh.t2_requirement(sch, rec, f_target=0.999, t1_mode="inf", t_2q=t_2q)
    formula = coh.serial_bound(len(sch["active"]), n_2q, 0.999)
    assert r["T2_req_s"] > 100 * sch["T_s"]
    # in the linear limit the requirement is the formula scaled by the CHARGED idle fraction:
    # sum of windows / (n_active T).  That is at most 1 - utilisation, and strictly below it
    # whenever a qubit sits idle after its own last gate (which opens no window).
    w, _t1, _t2 = coh.window_arrays(sch, rec)
    charged = float(w.sum()) / (len(sch["active"]) * sch["T_s"])
    assert charged <= 1.0 - util + 1e-12
    assert abs(r["T2_req_over_t_2q"] / formula / charged - 1.0) < 0.01
    assert abs(r["S_at_T2_req"] - r["budget_log"]) < 1e-6
    assert abs(r["S_fast_minus_S_idle_module"]) < 1e-9


def test_packing_bound_is_a_duration_lower_bound():
    """T_min <= T unconditionally; the packed schedule charges exactly T_min - busy_q per
    qubit, which is the concavity-minimal window structure at that total idle time (and can
    exceed the ASAP budget when the ASAP schedule leaves trailing idle uncharged)."""
    qc, _n = _serial_cz_circuit()
    rec = coh.uniform_record(3, [(0, 1), (1, 2), (0, 2)], t_1q=0.0)
    sch = sk_idle.schedule_asap(qc, rec)
    pb = coh.packing_bound(sch)
    assert pb["T_min_s"] <= sch["T_s"] + 1e-18
    assert pb["speedup_available"] >= 1.0
    for q in sch["active"]:
        b = sch["per_qubit"][q]["busy_s"]
        assert pb["schedule"]["per_qubit"][q]["idle_s"] == pytest.approx(
            max(pb["T_min_s"] - b, 0.0))
        assert len(pb["schedule"]["per_qubit"][q]["windows_s"]) <= 1
    _pq2, tot_packed = sk_idle.idle_budget(pb["schedule"], rec)
    assert tot_packed["idle_s"] == pytest.approx(
        sum(max(pb["T_min_s"] - sch["per_qubit"][q]["busy_s"], 0.0) for q in sch["active"]))
    # splitting the same total idle time into more windows can only cost more (concavity)
    one = {"active": [0], "per_qubit": {0: {"busy_s": 0.0, "delay_s": 0.0, "idle_s": 4e-6,
                                            "windows_s": [4e-6]}},
           "T_s": 4e-6, "T_total_s": 4e-6, "measured_qubits": [], "measure_duration_s": 0.0}
    many = {**one, "per_qubit": {0: {"busy_s": 0.0, "delay_s": 0.0, "idle_s": 4e-6,
                                     "windows_s": [1e-6] * 4}}}
    _p, t1 = sk_idle.idle_budget(one, rec)
    _p, t4 = sk_idle.idle_budget(many, rec)
    assert t1["S_T2"] < t4["S_T2"]


def test_uniform_record_is_read_by_skqd_idle():
    rec = coh.uniform_record(2, [(0, 1)], t_2q=7e-8, t_1q=2e-8, t_ro=1e-6)
    assert sk_idle.instruction_duration_s(rec, "cz", (1, 0)) == 7e-8
    assert sk_idle.instruction_duration_s(rec, "sx", (0,)) == 2e-8
    assert sk_idle.instruction_duration_s(rec, "x", (1,)) == 2e-8
    assert sk_idle.instruction_duration_s(rec, "measure", (0,)) == 1e-6
    assert sk_idle.instruction_duration_s(rec, "rz", (0,)) == 0.0
    assert coh.complete_edges(4) == [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    with pytest.raises(ValueError):
        coh.record_t_2q({"edges": {"0-1": {"cz_duration_s": 1e-8},
                                   "1-2": {"cz_duration_s": 2e-8}}})


def test_frozen_canary_reproduces_the_committed_schedule():
    """Criterion C7: the same code path on the same inputs gives the committed numbers."""
    pytest.importorskip("qiskit")
    from qiskit import qpy

    rp = os.path.join(ROOT, "data", "hardware", "H0_diag_prep",
                      "calibration_20260922T1400Z.json")
    cp = os.path.join(ROOT, "data", "S2_duration_compare.json")
    cdir = os.path.join(ROOT, "data", "hardware", "H0_prep", "circuits")
    for p in (rp, cp, os.path.join(cdir, "B0_ref06_k1_rep1.json")):
        if not os.path.exists(p):
            pytest.skip(f"{p} is not in this checkout")
    with open(rp) as fh:
        real = json.load(fh)
    with open(cp) as fh:
        ref = json.load(fh)["circuits"]["exact|frozen|B0_ref06_k1_rep1"]
    with open(os.path.join(cdir, "B0_ref06_k1_rep1.json")) as fh:
        man = json.load(fh)
    with gzip.open(os.path.join(cdir, man["qpy"]), "rb") as fh:
        qc = qpy.load(fh)[0]
    sch = sk_idle.schedule_asap(qc, real)
    _pq, tot = sk_idle.idle_budget(sch, real)
    for key, got in (("T_s", sch["T_s"]), ("S_T1", tot["S_T1"]), ("S_T2", tot["S_T2"])):
        assert abs(got - ref[key]) / abs(ref[key]) <= 1e-9, key


def test_serial_bound_reproduces_the_committed_numbers():
    """Criterion C8, from the committed JSON only (no number typed in from prose)."""
    with open(os.path.join(ROOT, "validation", "S2.json")) as fh:
        s2 = json.load(fh)["data"]
    with open(os.path.join(ROOT, "data", "S2_duration_compare.json")) as fh:
        sdc = json.load(fh)
    with open(os.path.join(ROOT, "data", "S2D_2x3_device_requirements.json")) as fh:
        sheet = json.load(fh)
    rows = [
        (12, s2["2x2"]["coarse_step"]["all_to_all"]["cz"], 667.1),
        (12, sdc["circuits"]["exact|frozen|B0_ref06_k1_rep1"]["n_cz"], 1727.6),
        (20, sheet["counts"]["per_term_rzz_sum"], 9372.1),
        (20, s2["2x3"]["coarse_step"]["routed"]["cz"], 23786.3),
        (20, sheet["levers"]["fixed_angle_generator"]["counts_rzz_recomputed"]["rzz"], 7035.6),
    ]
    for n, n_2q, owner in rows:
        assert abs(coh.serial_bound(n, int(n_2q), 0.1) - owner) <= 0.1, (n, n_2q)
    with pytest.raises(ValueError):
        coh.serial_bound(12, 256, 1.0)


def test_requirement_is_monotone():
    qc, n_2q = _serial_cz_circuit()
    rec = coh.uniform_record(3, [(0, 1), (1, 2), (0, 2)], t_1q=0.0)
    sch = sk_idle.schedule_asap(qc, rec)
    prev = -1.0
    for f in (0.05, 0.1, 0.3, 0.6, 0.9):
        r = coh.t2_requirement(sch, rec, f_target=f, t1_mode="inf")
        assert r["T2_req_s"] > prev                   # a stricter target needs more coherence
        prev = r["T2_req_s"]
        eq = coh.t2_requirement(sch, rec, f_target=f, t1_mode="equal")
        assert eq["T2_req_s"] >= r["T2_req_s"]        # charging T1 as well can only be harder
    for n in (10, 100, 1000):
        assert coh.serial_bound(12, n, 0.1) < coh.serial_bound(12, 10 * n, 0.1)
    with pytest.raises(ValueError):
        coh.t2_requirement(sch, rec, f_target=0.1, t1_mode="ramsey")


def test_unconstrained_schedule_has_no_requirement():
    """A circuit with no idle window at all: coherence cannot be required by this budget."""
    qiskit = pytest.importorskip("qiskit")
    qc = qiskit.QuantumCircuit(2)
    for _ in range(5):
        qc.cz(0, 1)
    rec = coh.uniform_record(2, [(0, 1)], t_1q=0.0)
    sch = sk_idle.schedule_asap(qc, rec)
    assert sum(len(sch["per_qubit"][q]["windows_s"]) for q in sch["active"]) == 0
    r = coh.t2_requirement(sch, rec, f_target=0.1)
    assert r["unconstrained"] is True
    assert r["T2_req_s"] is None


def test_coherence_scale_one_and_zero_error_record():
    qc, n_2q = _serial_cz_circuit()
    rec = coh.uniform_record(3, [(0, 1), (1, 2), (0, 2)], t_1q=0.0, T1=1e-6, T2=1e-6,
                             cz_error=1e-3, measure_error=2e-3)
    sch = sk_idle.schedule_asap(qc, rec)
    _pq, tot = sk_idle.idle_budget(sch, rec)
    lam, limit = coh.coherence_scale_one(sch, rec, 0.5, 0.1)
    assert limit == 0.5
    if lam is not None:                     # scaling every T1/T2 by lam must reach the target
        t1 = sk_idle.effective_t1(rec, sch["active"], ratio=lam)
        t2 = sk_idle.effective_t2(rec, sch["active"], ratio=lam)
        _p, t = sk_idle.idle_budget(sch, rec, t2_s=t2, t1_s=t1)
        assert sk_idle.f_idle_aware(0.5, t) >= 0.1 - 1e-9
    # a target above the gate-only limit is unreachable at any coherence
    assert coh.coherence_scale_one(sch, rec, 0.05, 0.1)[0] is None
    z = coh.zero_error_record(rec)
    assert all(v["sx_error"] == 0.0 and v["measure_error"] == 0.0
               for v in z["qubits"].values())
    assert all(e["cz_error"] == 0.0 for e in z["edges"].values())
    assert all(e["cz_duration_s"] == rec["edges"][k]["cz_duration_s"]
               for k, e in z["edges"].items())
    assert coh.coherence_scale_one(sch, z, 1.0, 0.1)[0] is not None
    assert tot["S_T2"] > 0.0


def test_window_arrays_reproduce_the_idle_module_budget():
    qc, _n = _serial_cz_circuit()
    rec = coh.uniform_record(3, [(0, 1), (1, 2), (0, 2)], t_1q=0.0, T1=3e-5, T2=1e-5)
    sch = sk_idle.schedule_asap(qc, rec)
    w, t1a, t2a = coh.window_arrays(sch, rec)
    fast = float(0.25 * np.sum(-np.expm1(-w / t1a)) + 0.5 * np.sum(-np.expm1(-w / t2a)))
    _pq, tot = sk_idle.idle_budget(sch, rec)
    assert abs(fast - sk_idle.idle_log_budget(tot)) < 1e-14
    assert w.size == tot["n_windows"]


def test_requirement_row_carries_both_conventions():
    qc, n_2q = _serial_cz_circuit()
    rec = coh.uniform_record(3, [(0, 1), (1, 2), (0, 2)], t_1q=0.0)
    sch = sk_idle.schedule_asap(qc, rec)
    row = coh.requirement_row(sch, rec, n_2q)
    assert set(row["requirements"]) == {"f=0.1|T1=inf", "f=0.1|T1=equal",
                                        "f=0.05|T1=inf", "f=0.05|T1=equal"}
    for key, r in row["requirements"].items():
        assert r["serial_bound_T2_over_t_2q"] == pytest.approx(
            coh.serial_bound(len(sch["active"]), n_2q, r["f_target"]))
        assert 0.0 < r["measured_over_serial"] < 1.0
    assert row["T_min_s"] <= row["T_s"]
    assert math.isfinite(row["seriality"])


def test_coherence_scale_one_accepts_a_t2_convention():
    """The explicit per-qubit T2 override (the convention bracket of `skqd.idle`)."""
    qc, _n = _serial_cz_circuit()
    rec = coh.uniform_record(3, [(0, 1), (1, 2), (0, 2)], t_1q=0.0, T1=1e-5, T2=1e-7)
    sch = sk_idle.schedule_asap(qc, rec)
    echo = sk_idle.effective_t2(rec, sch["active"], ratio=1.0)
    star = sk_idle.effective_t2(rec, sch["active"], ratio=0.174)
    lam_echo, _ = coh.coherence_scale_one(sch, rec, 0.9, 0.1, t2_s=echo)
    lam_star, _ = coh.coherence_scale_one(sch, rec, 0.9, 0.1, t2_s=star)
    assert lam_echo is not None and lam_star is not None
    assert lam_star > lam_echo            # a shorter dephasing time needs more headroom
    assert coh.coherence_scale_one(sch, rec, 0.9, 0.1)[0] == pytest.approx(lam_echo)


def test_uniform_record_substitutes_a_nonzero_one_qubit_duration():
    rec = coh.uniform_record(2, [(0, 1)], t_1q=0.0)
    assert rec["uniform"]["t_1q_requested_s"] == 0.0
    assert rec["qubits"]["0"]["sx_duration_s"] == coh.ZERO_1Q_DURATION_S
    assert coh.ZERO_1Q_DURATION_S < 1e-9 * coh.HERON_T_2Q

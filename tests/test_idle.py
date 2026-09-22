"""Tests of `skqd.idle` -- the idle-time term of the clean-shot fraction f.

The reference is what the hardware and the committed records already say: the budget of the
canary circuit on the calibration record it ran under (`data/hardware/H0_diag_prep/
idle_model_frozen_set_7fd6d65e.json`, written before the diagnostic jobs were submitted) and
the windowed Ramsey measurement of gate H0_diag.  Nothing here touches a QPU or an IBM
account, and nothing here is a criterion: the bars 0.1 / 0.05 belong to the owner and are
only read, never recomputed.
"""
import json
import math
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(ROOT, "src"))

from skqd import device_req as dr  # noqa: E402
from skqd import idle  # noqa: E402

PREP = os.path.join(ROOT, "data", "hardware", "H0_prep")
CANARY_RECORD = os.path.join(ROOT, "data", "hardware", "H0_ibm_fez_canary",
                             "calibration_at_submission_20260922T1400Z.json")
FROZEN = os.path.join(ROOT, "data", "hardware", "H0_diag_prep",
                      "idle_model_frozen_set_7fd6d65e.json")
CANARY_CIRCUIT = "B0_ref06_k1_rep1"


@pytest.fixture(scope="module")
def record():
    with open(CANARY_RECORD) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def canary(record):
    from gate_H0P import load_circuit, load_manifests
    mans, _ = load_manifests(PREP)
    m = next(x for x in mans if x["id"] == CANARY_CIRCUIT)
    qc = load_circuit(PREP, m)
    sch = idle.schedule_asap(qc, record)
    per_q, tot = idle.idle_budget(sch, record)
    return qc, sch, per_q, tot


# ------------------------------------------------------------------ the committed budget
def test_budget_reproduces_the_committed_idle_model(canary):
    """The library must reproduce the preregistered budget of the canary circuit exactly."""
    _qc, sch, _per_q, tot = canary
    with open(FROZEN) as fh:
        ref = json.load(fh)["circuits"][CANARY_CIRCUIT]
    assert sch["T_s"] == pytest.approx(ref["T_s"], abs=1e-15)
    for key in ("S_T1", "S_T2", "S_T2_eligible", "S_T2_ineligible", "S_DD"):
        assert tot[key] == pytest.approx(ref["budget"][key], abs=1e-12)
    assert tot["dd_eligible"] == ref["budget"]["dd_eligible"] == 244
    assert tot["n_windows"] == ref["budget"]["n_windows"]
    # the numbers the planner analysis quotes (prompts/19, section 9)
    assert sch["T_s"] * 1e6 == pytest.approx(43.708, abs=0.01)
    assert tot["S_T1"] + tot["S_T2"] == pytest.approx(3.323, rel=1e-3)


def test_the_script_delegates_to_the_library(record, canary):
    """`h0_idle_model` must not grow a second copy of the schedule or the budget."""
    import h0_idle_model as im
    qc, sch, per_q, tot = canary
    assert im.schedule(qc, record) == sch
    im_per_q, im_tot = im.budgets(sch, record)
    assert im_tot == tot and im_per_q == per_q
    assert im.DD_MIN_LENGTH_RATIO == idle.DD_MIN_LENGTH_RATIO == 2.0
    assert im.XY4_PULSES == idle.XY4_PULSES == 4
    assert im.record_duration(record, "cz", (143, 144), record["dt_s"]) == \
        idle.instruction_duration_s(record, "cz", (143, 144))


# ------------------------------------------------------------------ the f model
def test_f_idle_aware_factorises(canary):
    _qc, _sch, _per_q, tot = canary
    f_gates = 0.2103446469858183          # the record-backed f of the canary (gate H0P chain)
    f = idle.f_idle_aware(f_gates, tot)
    assert f == pytest.approx(f_gates * math.exp(-(tot["S_T1"] + tot["S_T2"])), rel=1e-15)
    assert idle.idle_log_budget(tot) == pytest.approx(tot["S_T1"] + tot["S_T2"], rel=1e-15)
    assert f < f_gates                    # idle time can only cost


def test_zero_idle_is_the_gate_only_model():
    """A circuit with no idle window reproduces `gate_S2D.analyse_on_backend` exactly."""
    zero = {"S_T1": 0.0, "S_T2": 0.0, "S_T2_eligible": 0.0, "S_T2_ineligible": 0.0,
            "S_DD": 0.0, "dd_eligible": 0, "n_windows": 0}
    assert idle.f_idle_aware(0.1234, zero) == 0.1234
    assert idle.relaxation_factor(zero) == 1.0
    assert idle.f_idle_aware(0.1234, zero, rho=0.5) == 0.1234


def test_dd_bracket_is_monotone_in_rho(canary):
    _qc, _sch, _per_q, tot = canary
    f_gates = 0.21
    fs = [idle.f_idle_aware(f_gates, tot, r) for r in (0.0, 0.25, 0.5, 1.0)]
    assert fs == sorted(fs, reverse=True)
    assert fs[-1] < idle.f_idle_aware(f_gates, tot)      # rho = 1: pulse cost, no benefit
    assert fs[0] > idle.f_idle_aware(f_gates, tot)       # rho = 0: the eligible budget is saved


# ------------------------------------------------------------------ the T2 convention
def test_effective_t2_is_a_ratio_on_the_record(record):
    qs = [117, 122, 146]
    echo = idle.effective_t2(record, qs)
    assert echo == {q: record["qubits"][str(q)]["T2_s"] for q in qs}
    half = idle.effective_t2(record, qs, ratio=0.5)
    assert all(half[q] == pytest.approx(0.5 * echo[q]) for q in qs)
    mixed = idle.effective_t2(record, qs, ratio=0.5, per_qubit_ratio={117: 0.25})
    assert mixed[117] == pytest.approx(0.25 * echo[117])
    assert mixed[122] == pytest.approx(0.5 * echo[122])
    t1 = idle.effective_t1(record, qs, ratio=2.0)
    assert all(t1[q] == pytest.approx(2.0 * record["qubits"][str(q)]["T1_s"]) for q in qs)


def test_effective_time_refuses_a_record_without_the_time(record):
    rec = json.loads(json.dumps(record))
    rec["qubits"]["117"]["T2_s"] = None
    with pytest.raises(KeyError):
        idle.effective_t2(rec, [117])


def test_t2_override_equals_substituting_the_record(record, canary):
    """The override must be the same thing gate_H0_diag does by rewriting the record."""
    _qc, sch, _per_q, _tot = canary
    ratios = {117: 0.4, 146: 1.2}
    t2 = idle.effective_t2(record, sch["active"], ratio=0.174, per_qubit_ratio=ratios)
    rec2 = json.loads(json.dumps(record))
    for q, v in t2.items():
        rec2["qubits"][str(q)]["T2_s"] = v
    a = idle.idle_budget(sch, record, t2_s=t2)[1]
    b = idle.idle_budget(sch, rec2)[1]
    for k in ("S_T1", "S_T2", "S_T2_eligible", "S_DD"):
        assert a[k] == pytest.approx(b[k], rel=1e-15)
    # a shorter T2 can only cost more
    assert a["S_T2"] > idle.idle_budget(sch, record)[1]["S_T2"]


def test_t1_override_does_not_touch_t2(record, canary):
    _qc, sch, _per_q, tot = canary
    t1 = idle.effective_t1(record, sch["active"], ratio=10.0)
    _pq, scaled = idle.idle_budget(sch, record, t1_s=t1)
    assert scaled["S_T2"] == pytest.approx(tot["S_T2"], rel=1e-15)
    assert scaled["S_T1"] < tot["S_T1"]


# ------------------------------------------------------------------ the schedule itself
def test_synthetic_schedule_windows(record):
    """rz costs nothing, a barrier opens a window, a delay is busy time of its own qubit."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(200)
    qc.rz(0.3, 117)
    qc.sx(117)
    qc.delay(128, 117, unit="dt")
    qc.sx(122)
    qc.barrier(117, 122)
    sch = idle.schedule_asap(qc, record)
    sx = record["qubits"]["117"]["sx_duration_s"]
    assert sch["active"] == [117, 122]
    assert sch["per_qubit"][117]["busy_s"] == pytest.approx(sx + 128 * record["dt_s"])
    assert sch["per_qubit"][117]["windows_s"] == []
    assert sch["per_qubit"][122]["windows_s"] == pytest.approx([128 * record["dt_s"]])
    # and the budget of that one window is the Pauli-twirled relaxation of its length
    _pq, tot = idle.idle_budget(sch, record)
    w = 128 * record["dt_s"]
    q = record["qubits"]["122"]
    assert tot["S_T1"] == pytest.approx((1 - math.exp(-w / q["T1_s"])) / 4)
    assert tot["S_T2"] == pytest.approx((1 - math.exp(-w / q["T2_s"])) / 2)
    assert tot["dd_eligible"] == (1 if w / (4 * q["sx_duration_s"]) > 2.0 else 0)


def test_unknown_instruction_has_no_duration(record):
    with pytest.raises(KeyError):
        idle.instruction_duration_s(record, "ecr", (117, 122))
    assert idle.instruction_duration_s(record, "rz", (117,)) == 0.0
    assert idle.instruction_duration_s(record, "barrier", (117,)) == 0.0


# ------------------------------------------------------------------ the measured end
def test_measured_t2_ratios_of_H0_diag():
    from gate_S2D_idle import measured_t2_ratios
    m = measured_t2_ratios()
    assert m["n_measured"] == 9
    assert m["qubits_without_a_usable_time"] == [125, 141, 144]
    assert m["fallback_ratio"] == pytest.approx(0.1740, abs=5e-4)
    assert 0.0 < m["ratio_min"] < m["ratio_max"] < 2.0
    assert all(v > 0 for v in m["per_qubit_ratio"].values())


def test_the_criterion_thresholds_are_unchanged():
    """This work changes what f means, never the bar."""
    import gate_S2D
    import gate_S2D_idle
    assert (gate_S2D_idle.F_MEAN_MIN, gate_S2D_idle.F_WORST_MIN) == (0.1, 0.05)
    assert (gate_S2D.F_MEAN_MIN, gate_S2D.F_WORST_MIN) == (0.1, 0.05)
    c = gate_S2D_idle.criterion({"mean": 0.12, "min": 0.06, "max": 0.2})
    assert c["passes"] and c["mean_passes"] and c["worst_passes"]
    assert not gate_S2D_idle.criterion({"mean": 0.12, "min": 0.04, "max": 0.2})["passes"]


# ------------------------------------------------------------------ the requirement algebra
def test_target_with_idle_shifts_the_half_space():
    counts = dr.CircuitCounts(2158, 7310, 4257, 20, "2x3 mean")
    s_idle = 0.4
    eps2 = dr.required_error(counts.n_2q, dr.target_with_idle(0.1, s_idle),
                             dr.channel_factor(counts, "2q", 1e-3, 1e-4, 2e-3))
    f_gates = dr.circuit_f(counts, eps2, 1e-4, 2e-3)
    assert f_gates * math.exp(-s_idle) == pytest.approx(0.1, rel=1e-9)
    # S_idle = 0 is exactly the gate-only requirement the 2x3 sheet states
    assert dr.target_with_idle(0.1, 0.0) == 0.1
    with pytest.raises(ValueError):
        dr.target_with_idle(0.1, 3.0)          # the idle term alone exhausts the budget
    with pytest.raises(ValueError):
        dr.target_with_idle(0.1, -1.0)

"""Tests of the idle-aware yield model (prompts/19 step A5).

The reference is the planner computation P1 of
`reports/H0_canary_planner_analysis_20260922.md` section 9, reproduced here on the
committed calibration record the canary job actually ran under.  Nothing touches a QPU
or an IBM account.
"""
import json
import math
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import h0_idle_model as im  # noqa: E402

PREP = os.path.join(ROOT, "data", "hardware", "H0_prep")
CANARY_RECORD = os.path.join(ROOT, "data", "hardware", "H0_ibm_fez_canary",
                             "calibration_at_submission_20260922T1400Z.json")
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
    sch = im.schedule(qc, record)
    per_q, tot = im.budgets(sch, record)
    return qc, m, sch, per_q, tot


def test_p1_critical_path_and_budgets(canary):
    """P1: T = 43.71 us, S_T1 = 0.755, S_T2 = 2.568, 244 DD-eligible windows, S_DD = 0.317."""
    _qc, _m, sch, _per_q, tot = canary
    assert sch["T_s"] * 1e6 == pytest.approx(43.71, abs=0.01)
    assert tot["S_T1"] == pytest.approx(0.755, rel=1e-3)
    assert tot["S_T2"] == pytest.approx(2.568, rel=1e-3)
    assert tot["S_T1"] + tot["S_T2"] == pytest.approx(3.323, rel=1e-3)
    assert tot["exp_minus_S_T1_S_T2"] == pytest.approx(0.0360, abs=1e-4)
    assert tot["dd_eligible"] == 244
    assert tot["S_DD"] == pytest.approx(0.317, rel=1e-3)
    # the eligible/ineligible split of the T2 budget (planner analysis, section 2)
    assert tot["S_T2_eligible"] == pytest.approx(2.494, rel=1e-3)
    assert tot["S_T2_ineligible"] == pytest.approx(0.073, rel=2e-2)


def test_p1_per_qubit_row_of_146(canary):
    """The worst qubit of the patch: T2 = 16 us, 41.85 us idle, a 25.30 us window."""
    _qc, _m, _sch, per_q, _tot = canary
    v = per_q["146"]
    assert v["T2_s"] * 1e6 == pytest.approx(16.0, abs=0.05)
    assert v["idle_s"] * 1e6 == pytest.approx(41.85, rel=1e-3)
    assert v["longest_window_s"] * 1e6 == pytest.approx(25.30, rel=1e-3)
    assert v["n_windows"] == 14 and v["n_dd_eligible"] == 11
    assert v["S_T2"] == pytest.approx(0.857, rel=1e-2)


def test_the_twelve_active_qubits_are_the_patch(canary):
    _qc, m, sch, _per_q, _tot = canary
    assert sch["active"] == sorted(m["physical_qubits"])
    assert sch["active"] == [117, 122, 123, 124, 125, 136, 141, 142, 143, 144, 145, 146]


def test_schedule_reproduces_h0_qpu_time_on_the_snapshot():
    """T_total must be h0_qpu_time.circuit_duration_s -- the ASAP rule is not re-derived."""
    import h0_qpu_time
    from gate_H0P import load_circuit, load_manifests
    from h0_backends import calibration_record, frozen_qubits_and_edges, resolve_backend

    b = resolve_backend("FakeFez")
    qubits, edges = frozen_qubits_and_edges(PREP)
    rec = calibration_record(b, qubits, edges)
    mans, cals = load_manifests(PREP)
    for m in [mans[0], mans[-1], cals[0]]:
        qc = load_circuit(PREP, m)
        sch = im.schedule(qc, rec)
        d = h0_qpu_time.circuit_duration_s(qc, b.target.durations(), b.target)
        assert sch["T_total_s"] == pytest.approx(d, abs=im.DURATION_TOL)
        assert sch["T_s"] == pytest.approx(d - sch["measure_duration_s"], abs=im.DURATION_TOL)


def test_f_on_record_equals_analyse_on_backend():
    from gate_H0P import load_circuit, load_manifests
    from gate_S2D import analyse_on_backend
    from h0_backends import calibration_record, frozen_qubits_and_edges, resolve_backend

    b = resolve_backend("FakeFez")
    qubits, edges = frozen_qubits_and_edges(PREP)
    rec = calibration_record(b, qubits, edges)
    mans, _ = load_manifests(PREP)
    m = next(x for x in mans if x["id"] == CANARY_CIRCUIT)
    qc = load_circuit(PREP, m)
    f, f_only, ro, n_cz, n_meas = im.f_on_record(qc, rec)
    assert f == pytest.approx(analyse_on_backend(qc, b)["f"], abs=1e-12)
    assert n_cz == 663 and n_meas == 12
    assert f_only == pytest.approx(f / ro, rel=1e-12)


def test_predictions_are_the_planner_bracket(canary, record):
    """P5: f_gates e^{-S_T1 - rho S_T2e - S_T2i - S_DD}; the bracket of section 2."""
    qc, _m, _sch, _per_q, tot = canary
    f_gates, _fo, _ro, _n, _nm = im.f_on_record(qc, record)
    a = 38 / 4096
    p = im.predictions(f_gates, tot, a)
    assert p["dd_off"]["f"] == pytest.approx(f_gates * math.exp(-3.3229), rel=1e-3)
    # yield model: 0.82 f + (1 - f) a, both terms (manual Step 4.4)
    f = p["dd_off"]["f"]
    assert p["dd_off"]["yield"] == pytest.approx(0.82 * f + (1 - f) * a, rel=1e-12)
    # monotone in rho: more refocusing (smaller rho) means a larger clean fraction
    fs = [p["dd_on"][str(r)]["f"] for r in im.RHOS]
    assert fs == sorted(fs, reverse=True)
    assert p["dd_on"]["1.0"]["f"] < p["dd_off"]["f"]        # DD's pulse cost with no benefit


def test_rz_and_barrier_and_delay_in_the_schedule(record):
    """rz costs nothing, a barrier opens a window, a delay is busy time of its own qubit."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(200)
    qc.rz(0.3, 117)
    qc.sx(117)
    qc.delay(128, 117, unit="dt")
    qc.sx(122)
    qc.barrier(117, 122)
    sch = im.schedule(qc, record)
    sx = record["qubits"]["117"]["sx_duration_s"]
    assert sch["active"] == [117, 122]
    assert sch["per_qubit"][117]["busy_s"] == pytest.approx(sx + 128 * record["dt_s"])
    assert sch["per_qubit"][117]["delay_s"] == pytest.approx(128 * record["dt_s"])
    assert sch["per_qubit"][117]["windows_s"] == []          # rz is free, the delay is busy
    # qubit 122 is done after one sx and waits at the barrier for 117
    assert sch["per_qubit"][122]["windows_s"] == pytest.approx([128 * record["dt_s"]])


def test_session_prediction_matches_the_preregistered_numbers(record):
    """The J1 decision of prompts/19: H_A 31 +- 6, H_B 374 +- 17 of 2000, floor 18.6."""
    res = im.analyse(PREP, record, only=[CANARY_CIRCUIT], shots=2000,
                     hb=os.path.join("validation", "H0P_ibm_fez.json"))
    sp = res["session_prediction"]
    assert sp["shots"] == 2000
    assert sp["garbage_acceptance"] == pytest.approx(38 / 4096)
    assert sp["garbage_floor_expected"] == pytest.approx(18.6, abs=0.1)
    assert sp["H_A"]["expected"] == pytest.approx(31.0, abs=1.0)
    assert sp["H_A"]["sigma"] == pytest.approx(5.5, abs=0.5)
    assert sp["H_B"]["expected"] == pytest.approx(374.0, abs=1.0)
    assert sp["H_B"]["sigma"] == pytest.approx(17.4, abs=0.5)
    assert sp["N1_reject_H_B_at_or_below"] == 100
    assert sp["N1_confirm_H_B_at_or_above"] == 250
    assert res["calibration"]["fingerprint"] == record["fingerprint"]


def test_the_model_runs_over_the_whole_frozen_set(record):
    """A5: the 84 frozen circuits on the canary record; the per-patch S_T2 for the re-plan."""
    res = im.analyse(PREP, record, shots=2000, hb=None)
    assert res["n_circuits"] == 126          # 84 coarse-step + 42 readout-calibration
    coarse = [c for c in res["circuits"].values() if c["kind"] == "coarse_step"]
    assert len(coarse) == 84
    # every coarse circuit has a positive idle budget; the cal circuits have none worth the name
    assert all(c["budget"]["S_T2"] > 0.5 for c in coarse)
    assert all(c["budget"]["S_T2"] < 1e-2
               for c in res["circuits"].values() if c["kind"] == "readout_calibration")
    # the budget grows with the repetition count (the circuit is r times as long)
    by_r = {}
    for c in coarse:
        by_r.setdefault(c["repetitions"], []).append(c["budget"]["S_T2"])
    assert min(by_r[1]) > 0 and max(by_r[1]) < min(by_r[2]) < max(by_r[2]) < min(by_r[3])
    keys = set(res["per_patch_S_T2"])
    assert keys <= {f"patch{p} r={r}" for p in (0, 1, 2) for r in (1, 2, 3)}
    assert "patch1 r=1" in keys                    # the canary's patch
    assert sum(v["n_circuits"] for v in res["per_patch_S_T2"].values()) == 84

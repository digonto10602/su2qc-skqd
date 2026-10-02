"""Tests of gate S2D_levers' helpers (prompts/23): the fractional target / record, the delay
windows of a scheduled circuit, the post-optimization rzz fold, and the verdict logic on a
synthetic table.  Nothing here touches a QPU, an IBM account or a committed number."""
import json
import math
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(ROOT, "src"))

import gate_S2D_levers as G  # noqa: E402

pytest.importorskip("qiskit_ibm_runtime")


def _tiny_record():
    return {"dt_s": 4e-9, "default_rep_delay_s": 2.5e-4,
            "qubits": {"0": {"T1_s": 2e-4, "T2_s": 1e-4, "sx_duration_s": 3.2e-8, "x_duration_s": 3.2e-8,
                             "measure_duration_s": 2.18e-6, "sx_error": 3e-4, "x_error": 3e-4,
                             "measure_error": 0.01},
                       "1": {"T1_s": 2e-4, "T2_s": None, "sx_duration_s": 3.2e-8, "x_duration_s": 3.2e-8,
                             "measure_duration_s": 2.18e-6, "sx_error": 3e-4, "x_error": 3e-4,
                             "measure_error": 0.01}},
            "edges": {"0-1": {"target_key": [0, 1], "cz_error": 2e-3, "cz_duration_s": 6.8e-8},
                      "1-0": {"target_key": [1, 0], "cz_error": 2e-3, "cz_duration_s": 6.8e-8}},
            "fingerprint": "plain"}


def test_fractional_record_adds_leaves_and_is_a_different_record():
    from h0_backends import calibration_fingerprint
    rec = _tiny_record()
    rec["fingerprint"] = calibration_fingerprint(rec)
    fj = {"stamp": "S", "last_update_date": "D",
          "qubits": {"0": {"rx_duration_s": 3.2e-8, "rx_error": 4e-4},
                     "1": {"rx_duration_s": None, "rx_error": None}},
          "edges": {"0-1": {"target_key": [0, 1], "rzz_duration_s": 6.8e-8, "rzz_error": 3e-3}}}
    fr = G.fractional_record(rec, fj)
    assert fr["record_kind"] == "fractional"
    assert fr["qubits"]["0"]["rx_error"] == 4e-4
    assert fr["qubits"]["1"]["rx_duration_s"] is None            # None stays None, never defaulted
    assert fr["edges"]["1-0"]["rzz_error"] == 3e-3               # both directed keys carry it
    assert fr["plain_fingerprint"] == rec["fingerprint"]
    assert fr["fingerprint"] != rec["fingerprint"]
    assert calibration_fingerprint(rec) == rec["fingerprint"]    # the plain record is untouched
    assert "rx_error" not in rec["qubits"]["0"]
    ok, why = G.covers(fr, [0, 1], [(0, 1)], fractional=True)
    assert not ok and "T2_s" in why                              # the plain cover check runs first
    fr["qubits"]["1"]["T2_s"] = 1e-4
    ok, why = G.covers(fr, [0, 1], [(0, 1)], fractional=True)
    assert not ok and "rx_duration_s" in why


def test_augment_target_adds_parameterised_rx_and_rzz():
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    b = FakeKingston()
    edges = sorted({(int(a), int(c)) for a, c in b.coupling_map})
    fj = {"qubits": {str(q): {"rx_duration_s": 3.2e-8, "rx_error": 1e-4} for q in range(b.num_qubits)},
          "edges": {f"{a}-{c}": {"target_key": [a, c], "rzz_duration_s": 8e-8, "rzz_error": 2e-3}
                    for a, c in edges if a < c}}
    G.augment_target(b, fj)
    t = b.target
    assert "rx" in t.operation_names and "rzz" in t.operation_names
    a, c = edges[0]
    assert t["rzz"][(a, c)].error == 2e-3 and t["rzz"][(c, a)].duration == 8e-8
    assert t["rx"][(5,)].error == 1e-4
    with pytest.raises(SystemExit):
        G.augment_target(b, fj)                                   # never on an augmented base


def test_delay_windows_split_leading_internal_and_trailing():
    from qiskit import QuantumCircuit
    from skqd import idle
    rec = _tiny_record()
    rec["qubits"]["1"]["T2_s"] = 1e-4
    qc = QuantumCircuit(2, 2)
    qc.delay(100, 1, unit="dt")      # leading on qubit 1: still |0>
    qc.sx(0)
    qc.delay(50, 0, unit="dt")       # internal on qubit 0
    qc.cz(0, 1)
    qc.measure([0, 1], [0, 1])
    qc.delay(20, 0, unit="dt")       # trailing: after the measure, never counted
    ex = G.delay_schedule(qc, rec, include_leading=False)
    inc = G.delay_schedule(qc, rec, include_leading=True)
    assert ex["per_qubit"][0]["windows_s"] == [pytest.approx(50 * 4e-9)]
    assert ex["per_qubit"][1]["windows_s"] == []
    assert ex["leading_s"][1] == pytest.approx(100 * 4e-9)
    assert inc["per_qubit"][1]["windows_s"] == [pytest.approx(100 * 4e-9)]
    _p, tot = idle.idle_budget(ex, rec)
    w = 50 * 4e-9
    assert tot["S_T2"] == pytest.approx((1 - math.exp(-w / 1e-4)) / 2)


def test_aer_r_crit_interpolates_log_linearly():
    f = {"1.0": 0.2, "0.5": 0.1, "0.25": 0.05, "0.174": 0.03}
    r = G.aer_r_crit(f, 0.1)
    assert r["status"] == "interpolated" and r["value"] == pytest.approx(0.5)
    r = G.aer_r_crit(f, 0.141421356)                     # geometric midpoint of (0.5, 1)
    assert r["value"] == pytest.approx(math.sqrt(0.5), rel=1e-6)
    assert G.aer_r_crit({"1.0": 0.08, "0.5": 0.04}, 0.1)["value"] is None
    assert "none" in G.aer_r_crit({"1.0": 0.08, "0.5": 0.04}, 0.1)["status"]
    assert "below the grid" in G.aer_r_crit({"1.0": 0.3, "0.174": 0.2}, 0.1)["status"]


def _summary(f_best_echo, f_best_tr, T_best):
    def row(T, f1, f2, default, extra=False, sched="asap"):
        return {"T_s": T, "T_s_L0": 48e-6, "aer": {"1.0": f1, "0.5": None, "0.25": None, "0.174": f2},
                "aer_68": {}, "pta_r_crit": {"0.1": 0.8, "0.05": 0.5}, "order_is_default": default,
                "executor_addition": extra, "schedule": sched, "order": ["x"], "description": "d"}
    return {"L0_asis_asap": row(48e-6, 0.06, 0.002, True),
            "L0_asis_alap": row(48e-6, 0.08, 0.006, True, sched="alap"),
            "L1_seed": row(44e-6, 0.07, 0.004, True),
            "L4_all": row(T_best, f_best_echo, f_best_tr, False, sched="alap"),
            "L1_seed_alap": row(44e-6, 0.5, 0.5, True, extra=True, sched="alap")}


def test_verdict_on_a_synthetic_table():
    v = G.build_verdict(_summary(0.17, 0.03, 34e-6))
    assert v["best_row"] == "L4_all"                     # the executor-addition row never wins
    assert v["duration_ratio_best"] == pytest.approx(34 / 48)
    assert v["duration_halved_reachable"] is False
    assert v["meets_0.1_at_echo"] and v["meets_0.05_at_echo"]
    assert not v["meets_0.1_at_transfer_0.174"] and not v["meets_0.05_at_transfer_0.174"]
    assert v["family_changes"] is True
    assert v["best_row_in_the_signed_family"] == "L1_seed_alap"
    assert "IonQ" in v["recommendation"] and "CONDITIONAL" in v["recommendation"]
    v2 = G.build_verdict(_summary(0.3, 0.12, 20e-6))
    assert v2["duration_halved_reachable"] is True and v2["meets_0.1_at_transfer_0.174"]
    assert "IonQ" not in v2["recommendation"]


def test_post_optimization_fold_keeps_rzz_in_the_calibrated_range():
    from qiskit import QuantumCircuit
    from qiskit_ibm_runtime.fake_provider import FakeKingston
    b = FakeKingston()
    edges = sorted({(int(a), int(c)) for a, c in b.coupling_map})
    fj = {"qubits": {str(q): {"rx_duration_s": 3.2e-8, "rx_error": 1e-4} for q in range(b.num_qubits)},
          "edges": {f"{a}-{c}": {"target_key": [a, c], "rzz_duration_s": 6.8e-8, "rzz_error": 2e-3}
                    for a, c in edges if a < c}}
    G.augment_target(b, fj)
    qc = QuantumCircuit(3, 3)
    qc.h(0)
    qc.rzz(-0.7, 0, 1)
    qc.rzz(2.9, 1, 2)
    qc.cx(0, 2)
    qc.ry(0.4, 1)
    qc.measure(range(3), range(3))
    tq = G.transpile_fractional(qc, b, 7)
    angs = G.rzz_angles(tq)
    assert all(0.0 <= x <= math.pi / 2 + 1e-12 for x in angs)
    assert G.rzz_valid_for_runtime(tq) == ""
    assert "global_phase" not in tq.count_ops()
    from qiskit.quantum_info import Statevector
    from skqd.hardware import logical_statevector
    want = Statevector(qc.remove_final_measurements(inplace=False)).data
    got = logical_statevector(tq, 3)
    assert abs(abs(sum(w.conjugate() * g for w, g in zip(want, got))) - 1.0) < 1e-9


# ---- the C6 ruling of 2026-10-02 (reports/S2D_levers_C6_ruling_20261002.md; prompts/21 part 0)

def test_c6_low_p_ref_cell_from_the_committed_json():
    with open(os.path.join(ROOT, "validation", "S2D_levers.json")) as fh:
        D = json.load(fh)["data"]
    d = D["e4"]["aer"]["B1_ref07_k4"]["0.174"]
    kind, e = G.c6_classify("E4:B1_ref07_k4", "0.174", d)
    assert kind == "information"
    assert abs(e["z"] - (-1.65)) <= 0.02
    assert round(e["clean_accepted_ceiling"], 1) == 324.9
    assert round(e["clean_accepted_reference"], 1) == 347.9
    assert e["clean_accepted_ceiling"] < e["clean_accepted_reference"] and e["reference_exceeds_ceiling"]


def _synthetic_cell(p_ref, dev):
    fr = 0.10
    return {"shots": 8000, "accepted": 1000, "reference_hits": 100, "p_reference": p_ref,
            "garbage_acceptance": 0.01, "dim": 38, "f_clean_reference": fr,
            "f_clean_reference_68": [0.09, 0.11], "f_clean_mixture": fr * (1 + dev),
            "f_clean_mixture_68": [fr * (1 + dev) - 0.005, fr * (1 + dev) + 0.005], "w": 0.5,
            "c6_relative_deviation": dev, "strided_seeds": True}


def test_c6_high_p_ref_cell_at_0p30_still_fails():
    kind, e = G.c6_classify("X", "1.0", _synthetic_cell(0.9, 0.30))
    assert kind == "checked" and not e["ok"]
    assert not G.c6_verdict([e])


def test_c6_low_p_ref_cell_at_0p30_is_information_not_a_failure():
    kind, e = G.c6_classify("X", "1.0", _synthetic_cell(0.13, 0.30))
    assert kind == "information"
    assert G.c6_verdict([])          # nothing in scope -> no failure
    assert e["dev"] == 0.30 and e["z"] is not None
    s = G.c6_low_summary([e])
    assert s["n_cells"] == 1 and s["max_abs_z"] == abs(e["z"])

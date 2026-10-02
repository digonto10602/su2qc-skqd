"""Tests of gate H0_kpilot's analysis (prompts/21 F3): rule S3 on synthetic P0 tables, the r_eff
bisection, the preregistered decision logic, the prereg-format keys and the dry-run / device mixing
refusal.  Nothing here touches a QPU, an IBM account or a committed number."""
import math
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(os.path.dirname(SCRIPTS), "src"))

pytest.importorskip("qiskit")
import gate_H0_kpilot as K  # noqa: E402


def _w(P0_long, s_long, P0_half, s_half, Tl=44e-6, Th=22e-6):
    return {"long": {"P0": P0_long, "sigma": s_long, "T": Tl},
            "half": {"P0": P0_half, "sigma": s_half, "T": Th}}


def test_s3_rule_measured_upper_bound_and_patch_minimum():
    Tl, Th = 44e-6, 22e-6
    T2 = 30e-6
    pl, ph = (1 + math.exp(-Tl / T2)) / 2, (1 + math.exp(-Th / T2)) / 2
    table = {
        1: _w(pl, 0.004, ph, 0.004),               # both windows resolve
        2: _w(0.49, 0.004, 0.52, 0.004),           # long dephased, half resolves
        3: _w(0.48, 0.004, 0.495, 0.004),          # fully dephased: the 3 sigma bound at the half window
        4: _w(0.40, 0.004, 0.40, 0.004),           # nothing resolvable: the patch minimum
    }
    out = K.t2star_patch(table)
    t, prov, win, rs = out[1]
    assert prov == "measured" and abs(t - T2) / T2 < 1e-9
    # the window with the smaller relative sigma is chosen
    _tl, rl = K.t2star_window(pl, 0.004, Tl)
    _th, rh = K.t2star_window(ph, 0.004, Th)
    assert win == ("long" if rl < rh else "half")
    assert out[2][1] == "measured" and out[2][2] == "half"
    assert abs(out[2][0] - (-Th / math.log(2 * 0.52 - 1))) < 1e-15
    assert out[3][1] == "upper_bound_3sigma_half"
    assert abs(out[3][0] - (-Th / math.log(2 * (0.495 + 3 * 0.004) - 1))) < 1e-15
    assert out[4][1] == "patch_minimum"
    assert out[4][0] == min(out[q][0] for q in (1, 2, 3))


def test_r_eff_bisection_two_window_case():
    # one qubit, two windows: S(r T_echo) = S(T*) has the exact solution r = T*/T_echo
    w = {7: [10e-6, 3e-6]}
    r = K.r_eff_solve(w, {7: 100e-6}, {7: 30e-6})
    assert abs(r - 0.3) < 1e-5
    # two qubits with the same ratio: the uniform r is that ratio
    w2 = {1: [5e-6, 7e-6], 2: [2e-6]}
    r2 = K.r_eff_solve(w2, {1: 80e-6, 2: 200e-6}, {1: 40e-6, 2: 100e-6})
    assert abs(r2 - 0.5) < 1e-5
    # and the solution reproduces the target sum
    S = K.s_t2(w2, {1: 80e-6 * r2, 2: 200e-6 * r2})
    assert abs(S - K.s_t2(w2, {1: 40e-6, 2: 100e-6})) < 1e-6 * S      # log r to 1e-6


def test_decision_logic_all_three_outcomes():
    assert K.decide([0.12, 0.2], {"a": [0.06, 0.2], "b": [0.07, 0.3]}) == "GO"
    assert K.decide([0.02, 0.08], {"a": [0.01, 0.1], "b": [0.02, 0.2]}) == "NO-GO"
    assert K.decide([0.08, 0.15], {"a": [0.01, 0.04], "b": [0.06, 0.2]}) == "NO-GO"   # worst hi < 0.05
    assert K.decide([0.09, 0.13], {"a": [0.06, 0.2], "b": [0.07, 0.3]}) == "AMBIGUOUS"
    assert K.decide([0.12, 0.2], {"a": [0.04, 0.2], "b": [0.07, 0.3]}) == "AMBIGUOUS"
    assert K.r_verdict([0.4, 0.5]) == "above"
    assert K.r_verdict([0.1, 0.2]) == "below"
    assert K.r_verdict([0.3, 0.4]) == "straddles"
    assert K.model_consistent(0.03, 0.031)[1] is True
    assert K.model_consistent(0.03, 0.2)[1] is False


def test_topup_excludes_the_bar_at_the_computed_factor():
    rows = [[60, 4000, 0.88, 0.01, 38], [55, 4000, 0.89, 0.01, 38]]
    f0, iv = K.pooled_interval_scaled(rows, 1.0, K.CONF95)
    assert iv[0] < 0.1 or iv[1] >= 0.1
    m = K.topup_factor(rows, K.BAR_MEAN)
    assert m is not None and m >= 1.0
    _f, iv2 = K.pooled_interval_scaled(rows, m * 1.0000001, K.CONF95)
    assert (iv2[0] >= 0.1) if f0 >= 0.1 else (iv2[1] < 0.1)


def test_prereg_format_keys():
    pre = {"calibration": {"fingerprint": "x" * 64, "path": "a.json", "last_update_date": "d", "stamp": "s"},
           "created": "c", "commit": "abc", "script": "scripts/gate_H0_kpilot.py", "prep": "p"}
    assert K.prereg_keys_ok(pre) == []
    del pre["calibration"]["path"]
    assert K.prereg_keys_ok(pre) == ["calibration.path"]


def test_dry_run_and_device_counts_are_never_mixed():
    recs = [({"id": "a", "dry_run": True}, {})]
    K.check_mixing(True, {"dry_run": True}, recs)
    with pytest.raises(SystemExit):
        K.check_mixing(False, {"dry_run": True}, recs)
    with pytest.raises(SystemExit):
        K.check_mixing(True, {"dry_run": False}, recs)
    with pytest.raises(SystemExit):
        K.check_mixing(False, {"dry_run": False}, recs)      # a record says dry run
    with pytest.raises(SystemExit):
        K.check_mixing(True, None, recs)


def test_decision_completeness():
    dec = {k: 1 for k in K.DECISION_FIELDS}
    dec.update({"decision": "NO-GO", "ambiguous_topup_shots": None, "dry_run": False})
    assert K.decision_complete(dec) == []
    dec["decision"] = "AMBIGUOUS"
    assert K.decision_complete(dec) == ["ambiguous_topup_shots"]

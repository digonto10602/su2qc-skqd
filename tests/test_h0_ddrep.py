"""prompts/32 part A (gate H0_ddrep): the sign alternation and pulse stripping on toy padded
circuits, the M2 = T2 window-set identity, the class function and the reading rule, R2, the
reserve arithmetic, the pulse-train fit, and the K0 NO-GO block against its source."""
import math
import os
import sys
from collections import Counter

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import gate_H0_ddrep as GR  # noqa: E402
import h0_ddrep_circuits as RC  # noqa: E402
import h0_ddtest_circuits as DC  # noqa: E402
import h0_devicewatch as DW  # noqa: E402

DT_S = 4e-9


def toy_rec():
    q = {"x_duration_s": 3.2e-8, "sx_duration_s": 3.2e-8, "measure_duration_s": 2.18e-6, "x_error": 2e-4,
         "sx_error": 2e-4, "measure_error": 1e-2, "T1_s": 2e-4, "T2_s": 1e-4}
    return {"dt_s": DT_S, "default_rep_delay_s": 2.5e-4, "qubits": {"0": dict(q), "1": dict(q)},
            "edges": {"0-1": {"target_key": [0, 1], "cz_duration_s": 6.8e-8, "cz_error": 2e-3}}}


def base_and_padded():
    """q0: x | delay 100 | sx ; q1: sx | delay 100 | x.  The padded copy puts four x into q0's
    window and two x into q1's window (inserted ops), timing preserved."""
    from qiskit import QuantumCircuit
    base = QuantumCircuit(2)
    base.x(0)
    base.delay(100, 0, unit="dt")
    base.sx(0)
    base.sx(1)
    base.delay(100, 1, unit="dt")
    base.x(1)
    out = QuantumCircuit(2)
    out.x(0)
    for d in (10, 20, 20, 18):
        out.delay(d, 0, unit="dt")
        out.x(0)
    out.sx(0)
    out.sx(1)
    out.delay(30, 1, unit="dt")
    out.x(1)
    out.delay(30, 1, unit="dt")
    out.x(1)
    out.delay(100 - 60 - 16, 1, unit="dt")
    out.x(1)
    return base, out


def strip(qc):
    from qiskit import QuantumCircuit
    c = QuantumCircuit(qc.num_qubits)
    c.global_phase = qc.global_phase
    for inst in qc.data:
        if inst.operation.name in ("delay", "barrier", "measure"):
            continue
        c.append(inst.operation, [qc.find_bit(q).index for q in inst.qubits])
    return c


def equal_up_to_phase(a, b):
    from qiskit.quantum_info import Statevector
    sa, sb = Statevector(strip(a)).data, Statevector(strip(b)).data
    ov = np.vdot(sa, sb)
    return np.max(np.abs(sb * np.exp(-1j * np.angle(ov)) - sa)) < 1e-12


# --------------------------------------------------------------------------- alternate_signs / strip
def test_toy_padded_timing():
    base, out = base_and_padded()
    rec = toy_rec()
    ins = RC.inserted_multiset(base, out, rec, names=("x",))
    assert sum(ins.values()) == 6
    assert Counter(q for (_n, q, _s) in ins.elements()) == Counter({0: 4, 1: 2})
    # the base x on q0 at t = 0 and on q1 at the end are base ops, not insertions
    assert ("x", 0, 0) not in ins
    win = DC.window_violations(base, out, rec)
    assert win["missing"] == 0


def test_alternate_signs_toy():
    base, out = base_and_padded()
    rec = toy_rec()
    res, n = RC.alternate_signs(out, base, rec)
    assert n == 3                                  # 2nd and 4th on q0, 2nd on q1
    # the base x on q0 is untouched (still the first op, plain x)
    assert res.data[0].operation.name == "x"
    assert res.count_ops()["rz"] == 6 and res.count_ops()["x"] == out.count_ops()["x"]
    # every wrapped pulse is rz(-pi) x rz(+pi)
    names = [i.operation.name for i in res.data]
    for k, nm in enumerate(names):
        if nm == "rz":
            assert names[k + 1] == "x" or names[k - 1] == "x"
    assert equal_up_to_phase(out, res)
    # start times of every x unchanged
    xs = lambda c: sorted((nm, q, st) for (nm, q, st) in RC.inserted_multiset(base, c, rec, names=("x",)).elements())
    assert xs(res) == xs(out)
    # identical schedule end
    assert RC.instruction_times(res, rec)[-1] == RC.instruction_times(out, rec)[-1]
    # -X exactly: Rz(pi) X Rz(-pi)
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator
    w = QuantumCircuit(1)
    RC.wrap_negative(w, [w.qubits[0]])
    x = QuantumCircuit(1)
    x.x(0)
    assert np.allclose(Operator(w).data, -Operator(x).data, atol=1e-12)


def test_strip_pulses_on_toy():
    base, out = base_and_padded()
    rec = toy_rec()
    res, n = RC.strip_pulses_on(out, base, rec, {0})
    assert n == 4
    ins = RC.inserted_multiset(base, res, rec)
    assert all(q != 0 for (_n, q, _s) in ins)
    assert ins == Counter({k: v for k, v in RC.inserted_multiset(base, out, rec).items() if k[1] != 0})
    # timeline restored: base ops keep their start times, same end per qubit
    assert DC.window_violations(base, res, rec)["missing"] == 0
    _o, e_res, _u = DC.timeline(res, rec)
    _o, e_out, _u = DC.timeline(out, rec)
    assert e_res == e_out
    assert equal_up_to_phase(base, res)


def test_hot_qubits_ties():
    assert RC.hot_qubits({"95": 130, "91": 118, "94": 96}) == [91, 95]
    assert RC.hot_qubits({"5": 10, "3": 10, "7": 9}) == [3, 5]


def test_pulse_train_ops():
    qc = RC.pulse_train([2, 5], 4, True, 8)
    assert RC.op_sequence(qc, 2) == ["x", "rz(-1pi)", "x", "rz(+1pi)", "x", "rz(-1pi)", "x", "rz(+1pi)", "measure"]
    qc = RC.pulse_train([2, 5], 3, False, 8)
    assert RC.op_sequence(qc, 5) == ["x", "x", "x", "measure"]
    m = {qc.find_bit(i.qubits[0]).index: qc.find_bit(i.clbits[0]).index for i in qc.data if i.operation.name == "measure"}
    assert m == {2: 0, 5: 1}


# --------------------------------------------------------------------------- M2 window set = T2's
def test_m2_window_set_equals_t2_toy():
    """One 300-ns window (pulsed by both), one 256-ns (the boundary: pulsed by neither, ratio test is
    strict) and one 200-ns window (neither)."""
    from qiskit import QuantumCircuit
    rec = toy_rec()
    base = QuantumCircuit(2, 2)
    base.sx(0)
    base.delay(75, 0, unit="dt")      # 300 ns
    base.sx(0)
    base.delay(64, 0, unit="dt")      # 256 ns
    base.sx(0)
    base.sx(1)
    base.delay(50, 1, unit="dt")      # 200 ns
    base.sx(1)
    base.delay(147 - 66, 1, unit="dt")
    base.sx(1)
    base.measure(0, 0)
    base.measure(1, 1)
    m2, _par = RC.xx_variant(base, rec, None)
    t2, _ = DC.dd_variant("T2", base, rec, None)
    w_m2 = RC.pulsed_windows(base, m2, rec)
    w_t2 = RC.pulsed_windows(base, t2, rec)
    assert w_m2 == w_t2
    assert (0, 8, 83) in w_m2
    assert all(w[2] - w[1] > 64 for w in w_m2)
    assert sum(RC.inserted_multiset(base, m2, rec, names=("x",)).values()) * 2 == \
        sum(RC.inserted_multiset(base, t2, rec, names=("x",)).values())


# --------------------------------------------------------------------------- classes, reading, R2
def test_classify_boundaries():
    assert GR.classify([0.01, 0.2]) == "COLLAPSED"
    assert GR.classify([0.01, 0.25]) == "INTERMEDIATE"          # hi < 0.25 is strict
    assert GR.classify([1.0, 2.0]) == "INTERMEDIATE"            # lo > 1 is strict
    assert GR.classify([1.01, 2.0]) == "INTACT"
    assert GR.classify([0.5, 1.5]) == "INTERMEDIATE"
    assert GR.classify([None, None]) == "UNDETERMINED"
    assert GR.classify([0.0, 0.1]) == "COLLAPSED"


def test_cell_ratio_branches():
    r = GR.cell_ratio(1000, 10, 400, 10)
    assert r["R"] == pytest.approx(990 / 390) and r["R_95"][0] < r["R"] < r["R_95"][1]
    r = GR.cell_ratio(5, 6.0, 400, 10)                          # no excess: [0, U/L]
    assert r["R_95"][0] == 0.0 and 0 < r["R_95"][1] < 0.1
    assert GR.classify(r["R_95"]) == "COLLAPSED"
    assert GR.cell_ratio(5, 1, 3, 4)["R"] is None              # baseline without excess


def test_reading_four_patterns():
    base = {"T1": "COLLAPSED", "M2": "INTACT", "M3": "INTACT"}
    assert GR.reading({**base, "M1": "INTACT", "M4": "COLLAPSED"}) == "H_A"
    assert GR.reading({**base, "M1": "COLLAPSED", "M4": "INTACT"}) == "H_D"
    assert GR.reading({**base, "M1": "COLLAPSED", "M4": "INTERMEDIATE"}) == "H_B"
    assert GR.reading({**base, "M1": "INTERMEDIATE", "M4": "INTACT"}) == "no single hypothesis"


def test_prediction_matches():
    cl = {"T1": "COLLAPSED", "M1": "COLLAPSED", "M2": "INTACT", "M3": "INTACT", "M4": "INTACT"}
    pm = GR.prediction_matches(cl, {"M2": 2.5, "M3": 2.7})
    assert pm["H_D"]["all_match"] and not pm["H_B"]["all_match"] and not pm["H_A"]["all_match"]


def test_r2_synthetic():
    # the H0_ddtest data themselves: identical ratio -> consistent with zero difference
    r = GR.r2_verdict(984.0703125, 349.0703125)
    assert r["difference"] == pytest.approx(0.0, abs=1e-12) and r["consistent"]
    assert r["tolerance"] == pytest.approx(1.959963984540054 * math.sqrt(2) * GR.R2_SIGMA_OLD, rel=1e-9)
    # equal counts (R = 1) are far from ln 2.82
    assert not GR.r2_verdict(349.0, 349.0)["consistent"]
    # sigma_old from the recorded interval: (ln 3.185 - ln 2.495) / 3.92 within rounding
    assert GR.R2_SIGMA_OLD == pytest.approx((math.log(3.185) - math.log(2.495)) / 3.92, rel=2e-3)


def test_log_ratio_z():
    r = GR.log_ratio_z(400.0, 300.0)
    assert r["lnR"] == pytest.approx(math.log(4 / 3)) and r["compensation_matters"] == (r["z"] > 1.645)
    assert GR.log_ratio_z(-1.0, 300.0)["z"] is None


# --------------------------------------------------------------------------- reserve
def test_reserve_arithmetic():
    assert GR.reserve_fits(498.0, 182.45)["fits"]
    assert not GR.reserve_fits(340.0, 182.45)["fits"]          # 295 < 300
    assert GR.reserve_fits(400.0, 260.0)["fits"]               # 355 >= 338
    assert not GR.reserve_fits(380.0, 260.0)["fits"]           # 335 < 338
    r = GR.reserve_fits(498.0, 182.45)
    assert r["B_need_s"] == 300.0 and r["after_A_s"] == 453.0


# --------------------------------------------------------------------------- the train fit
@pytest.mark.parametrize("eps", [0.0, 0.004, 0.009, 0.02])
def test_train_fit_known_epsilon(eps):
    b, c = 0.012, 2.0e-4
    P = {n: b + n * c + math.sin(n * eps / 2) ** 2 for n in (8, 32, 128)}
    Px = b + 128 * c
    e_hat, c_hat = GR.train_fit(P[8], P[32], P[128], Px)
    # the planner's floor is anchored at XX-8, which carries sin^2(4 eps): the bias is second order
    assert float(e_hat) == pytest.approx(eps, abs=3e-4)
    assert float(c_hat) == pytest.approx(c - math.sin(4 * eps) ** 2 / 120, rel=1e-9)


def test_readout_correct_round_trip():
    p00, p11, p1 = 0.98, 0.95, 0.2
    raw = p1 * p11 + (1 - p1) * (1 - p00)
    assert float(GR.readout_correct(raw, p00, p11)) == pytest.approx(p1, rel=1e-12)


def test_train_readings_patterns():
    def q(eps, x128, xpxm, x32=0.02, fl32=0.02, c=1e-4, xe=1e-4):
        return {"epsilon": eps, "P1": {"train_XX_128": x128, "train_XpXm_128": xpxm, "train_XX_32": x32},
                "floor": {"32": fl32}, "c_per_pulse": c, "x_error_record": xe}
    ha = {str(i): q(0.02, 0.3, 0.03) for i in range(6)} | {str(i): q(0.0, 0.03, 0.03) for i in range(6, 12)}
    r = GR.train_readings(ha, [91, 95])
    assert r["H_A"] and not r["H_B"]
    hb = {str(i): q(0.0, 0.03, 0.03) for i in range(12)}
    r = GR.train_readings(hb, [0, 1])
    assert r["H_B"] and not r["H_A"] and not r["H_D"]
    hd = dict(hb)
    hd["1"] = q(0.0, 0.03, 0.03, c=5e-4)
    assert GR.train_readings(hd, [0, 1])["H_D"]
    hd["7"] = q(0.0, 0.03, 0.03, c=5e-4)
    assert not GR.train_readings(hd, [0, 1])["H_D"]


# --------------------------------------------------------------------------- devicewatch, K0 block
def test_devicewatch_readiness():
    ok = {"status_msg": "active", "operational": True, "patch_qubits_calibrated": 12, "patch_qubits_total": 12,
          "patch_edges_calibrated": 21, "patch_edges_total": 21, "n_cz_keys_with_error": 352, "n_cz_keys_total": 352}
    assert DW.readiness(ok)[0]
    assert not DW.readiness({**ok, "status_msg": "maintenance"})[0]
    assert not DW.readiness({**ok, "n_cz_keys_with_error": 0})[0]
    assert not DW.readiness({**ok, "n_cz_keys_with_error": 0, "n_cz_keys_total": 0})[0]
    assert DW.readiness({**ok, "n_cz_keys_with_error": 317})[0]          # 317 / 352 = 0.9006
    assert not DW.readiness({**ok, "patch_edges_calibrated": 20})[0]


def test_k0_nogo_block_matches_source():
    import k0_nogo_note as K
    k0 = K.load(K.K0_JSON)
    blk = K.nogo_block(k0, 100000)
    assert K.check_block(blk, k0) == []
    assert blk["garbage_reference_hits_per_circuit"]["value"] == pytest.approx(100000 / 2 ** 20)
    assert blk["routed_cz"] == k0["data"]["2x3"]["committed"]["n_cz"]
    bad = dict(blk)
    bad["f_gates_layout"] = 1.0
    assert K.check_block(bad, k0) == ["f_gates_layout"]

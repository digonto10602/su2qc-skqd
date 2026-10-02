"""prompts/24 Stage T (gate H0_ddtest): the ratio interval, the adoption rule P7 on all branches,
the leading/trailing-window check on a toy scheduled circuit, the basis check, the Y translation,
the reserve arithmetic, and the committed DD circuits against their bases."""
import gzip
import json
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import gate_H0_ddtest as GT  # noqa: E402
import h0_ddtest_circuits as DC  # noqa: E402

PREP = os.path.join(ROOT, "data", "hardware", "H0_ddtest_prep")


# --------------------------------------------------------------------------- ratio and adoption
def test_ratio_interval_hand_computed():
    R, iv = GT.ratio_interval(400.0, 100.0)
    s = math.sqrt(1 / 400 + 1 / 100)
    assert R == pytest.approx(4.0)
    assert iv[0] == pytest.approx(4.0 * math.exp(-1.959963984540054 * s), rel=1e-12)
    assert iv[1] == pytest.approx(4.0 * math.exp(+1.959963984540054 * s), rel=1e-12)
    # equal counts: R = 1, interval symmetric in log
    R, iv = GT.ratio_interval(360.0, 360.0)
    assert R == 1.0 and iv[0] * iv[1] == pytest.approx(1.0)
    # the planner's P5 number: X = 360 -> sigma_lnR 0.0745, 95 % factor [0.864, 1.157]
    assert iv[0] == pytest.approx(0.864, abs=1e-3) and iv[1] == pytest.approx(1.157, abs=1e-3)
    # no excess: undefined interval
    assert GT.ratio_interval(-1.0, 100.0)[1] == [None, None]


def _cells(**kw):
    return {c: {"R": r, "R_95": iv} for c, (r, iv) in kw.items()}


def test_adoption_none_qualifies():
    cells = _cells(T1=(0.82, [0.7, 0.95]), T2=(1.1, [0.95, 1.27]), T3=(0.94, [0.8, 1.1]))
    assert GT.adopt(cells) == ("T0", [])


def test_adoption_one_qualifies():
    cells = _cells(T1=(1.6, [1.3, 1.97]), T2=(1.1, [0.95, 1.27]), T3=(0.94, [0.8, 1.1]))
    assert GT.adopt(cells) == ("T1", ["T1"])


def test_adoption_two_qualify_largest_point_wins():
    cells = _cells(T1=(1.4, [1.15, 1.7]), T2=(1.9, [1.5, 2.4]), T3=(0.94, [0.8, 1.1]))
    assert GT.adopt(cells) == ("T2", ["T1", "T2"])


def test_adoption_floor_binds():
    # the interval excludes 1 but the gain is below 1.25: not adopted
    cells = _cells(T1=(1.2, [1.03, 1.4]), T2=(0.9, [0.8, 1.0]), T3=(1.0, [0.9, 1.1]))
    assert GT.adopt(cells) == ("T0", [])
    # R >= 1.25 but the interval touches 1: not adopted
    cells = _cells(T1=(1.3, [1.0, 1.7]), T2=(0.9, [0.8, 1.0]), T3=(1.0, [0.9, 1.1]))
    assert GT.adopt(cells) == ("T0", [])


def test_signed_bar():
    assert GT.signed_bar([0.10, 0.2]) == "GO"
    assert GT.signed_bar([0.03, 0.0999]) == "NO-GO"
    assert GT.signed_bar([0.05, 0.12]) == "AMBIGUOUS"


def test_bootstrap_is_seeded():
    rows_i = [[200, 6000, 0.88, 0.0093, 38], [210, 6000, 0.89, 0.0049, 20]]
    rows_0 = [[180, 6000, 0.88, 0.0093, 38], [182, 6000, 0.89, 0.0049, 20]]
    a = GT.bootstrap_ratio(rows_i, rows_0)
    b = GT.bootstrap_ratio(rows_i, rows_0)
    assert a == b and a["R_95"][0] < 410 / 362 < a["R_95"][1]


# --------------------------------------------------------------------------- windows and basis
TOY_REC = {"dt_s": 4e-9,
           "qubits": {str(q): {"x_duration_s": 32e-9, "sx_duration_s": 32e-9, "measure_duration_s": 400e-9,
                               "x_error": 1e-4} for q in (0, 1)},
           "edges": {"0-1": {"target_key": [0, 1], "cz_duration_s": 80e-9}}}


def _toy_base():
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(2, 2)
    qc.delay(200, 0, unit="dt")       # q0 leading window (still in |0>)
    qc.sx(1)
    qc.delay(200, 1, unit="dt")
    qc.sx(0)                          # q0 first gate at t = 200
    qc.cz(0, 1)                       # both at t = 208
    qc.delay(100, 0, unit="dt")
    qc.delay(100, 1, unit="dt")
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def _toy_with_pulses(where):
    """Insert two x pulses (an identity pair) into a delay of the toy circuit."""
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(2, 2)
    if where == "leading":
        qc.x(0)
        qc.x(0)
        qc.delay(184, 0, unit="dt")
    else:
        qc.delay(200, 0, unit="dt")
    qc.sx(1)
    qc.delay(200, 1, unit="dt")
    qc.sx(0)
    qc.cz(0, 1)
    if where == "window":
        qc.delay(42, 0, unit="dt")
        qc.x(0)
        qc.x(0)
        qc.delay(42, 0, unit="dt")
    else:
        qc.delay(100, 0, unit="dt")
    qc.delay(100, 1, unit="dt")
    qc.measure(0, 0)
    qc.measure(1, 1)
    if where == "trailing":
        qc.x(0)
    return qc


def test_window_check_on_toy_schedule():
    base = _toy_base()
    ok = DC.window_violations(base, _toy_with_pulses("window"), TOY_REC)
    assert ok["missing"] == 0 and not ok["lead"] and not ok["trail"] and not ok["bad_kind"]
    assert ok["pulses"] == {0: 2} and ok["unaligned"] == (0, 0)
    lead = DC.window_violations(base, _toy_with_pulses("leading"), TOY_REC)
    assert lead["lead"] == {0: 2}
    trail = DC.window_violations(base, _toy_with_pulses("trailing"), TOY_REC)
    assert trail["trail"] == {0: 1}


def test_window_check_detects_a_moved_gate():
    from qiskit import QuantumCircuit
    base = _toy_base()
    moved = QuantumCircuit(2, 2)
    moved.delay(100, 0, unit="dt")
    moved.sx(0)                       # 100 dt early
    moved.delay(100, 0, unit="dt")
    moved.sx(1)
    moved.delay(200, 1, unit="dt")
    moved.cz(0, 1)
    moved.delay(100, 0, unit="dt")
    moved.delay(100, 1, unit="dt")
    moved.measure(0, 0)
    moved.measure(1, 1)
    assert DC.window_violations(base, moved, TOY_REC)["missing"] == 1


def test_basis_check():
    assert DC.in_basis({"rz": 3, "sx": 2, "x": 1, "cz": 1, "delay": 4, "measure": 2, "barrier": 1})
    assert not DC.in_basis({"y": 1, "x": 1})
    assert not DC.in_basis({"rzz": 1})


def test_y_translation_is_exactly_y():
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator
    qc = QuantumCircuit(1)
    qc.y(0)
    out, n = DC.translate_y(qc)
    assert n == 1 and set(out.count_ops()) == {"rz", "x"}
    assert np.allclose(Operator(out).data, Operator(qc).data, atol=1e-12)   # no global phase either


# --------------------------------------------------------------------------- reserve arithmetic
def test_reserve_arithmetic():
    shots = {"a": 267, "b": 267, "c": 1000, "cal0": 4000}
    dur = {"a": 40e-6, "b": 50e-6, "c": 46e-6, "cal0": 2e-6}
    g = GT.job_groups(shots, dur, 250e-6, 14)
    assert [(x["shots"], x["n_pubs"]) for x in g] == [(267, 2), (1000, 1), (4000, 1)]
    ex = {x["shots"]: x["execution_s"] for x in g}
    assert ex[267] == pytest.approx(267 * (290e-6 + 300e-6))
    assert ex[1000] == pytest.approx(1000 * 296e-6)
    r = GT.reserve_of(g)
    tot = sum(ex.values())
    assert r["total_execution_s"] == pytest.approx(tot)
    assert r["reserve_s"] == pytest.approx(1.3 * tot + 1.3 * max(ex.values()))
    # chunking by the pub cap
    g = GT.job_groups({f"c{i}": 267 for i in range(21)}, {f"c{i}": 1e-5 for i in range(21)}, 0.0, 14)
    assert [x["n_pubs"] for x in g] == [14, 7]


@pytest.mark.skipif(not os.path.exists(os.path.join(PREP, "reserve.json")), reason="no Stage T reserve on disk")
def test_committed_reserve_is_pure_d3prime_and_reproduces_the_pilot():
    r = json.load(open(os.path.join(PREP, "reserve.json")))
    plan = r["stage_R_plan"]
    assert plan["N4"] == {"B=0": 36200, "B=1": 86300}       # validation/H0_kpilot.json budgets_at_f_pool
    assert plan["total_coarse_shots"] == 359207
    assert "struck" in r["p8_ruling"].lower()
    k1 = [c for c in plan["shots_by_circuit"] if c.endswith("_k1")]
    assert len(k1) == 7 and all(plan["shots_by_circuit"][c] == 267 for c in k1)   # no D3''-H0 lift
    assert plan["reserve_s"] == pytest.approx(1.3 * plan["total_execution_s"] + 1.3 * plan["largest_job"]["execution_s"])
    assert r["fits"] and 40.0 + plan["reserve_s"] <= r["remaining_s_at_check"]


# --------------------------------------------------------------------------- the committed circuits
@pytest.mark.skipif(not os.path.exists(os.path.join(PREP, "index.json")), reason="no Stage T circuits on disk")
def test_committed_dd_circuits_keep_the_base_schedule():
    from qiskit import qpy
    rec = json.load(open(os.path.join(ROOT, json.load(open(os.path.join(PREP, "live.json")))["record"]["path"])))
    for base_id in GT.BASE_IDS:
        with gzip.open(os.path.join(PREP, "circuits", f"{base_id}_T0.qpy.gz"), "rb") as fh:
            base = qpy.load(fh)[0]
        for cell in ("T1", "T2", "T3"):
            man = json.load(open(os.path.join(PREP, "circuits", f"{base_id}_{cell}.json")))
            with gzip.open(os.path.join(PREP, "circuits", man["qpy"]), "rb") as fh:
                out = qpy.load(fh)[0]
            w = DC.window_violations(base, out, rec)
            assert w["missing"] == 0 and not w["lead"] and not w["trail"] and not w["bad_kind"]
            assert int(sum(w["pulses"].values())) == man["dd"]["n_pulses"]
            assert DC.in_basis(man["ops"]) and man["dd"]["checks"]["ok"]
            s = sum(n * rec["qubits"][str(q)]["x_error"] for q, n in w["pulses"].items())
            assert s == pytest.approx(man["dd"]["pulse_cost_nats"], rel=1e-12)

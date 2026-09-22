"""Unit tests for the H0 session scripts (prompts/15 part A).

Nothing here touches a QPU or an IBM account: the live path of `resolve_backend` is
exercised with a stubbed `open_service`, everything else runs on the FakeFez
calibration snapshot that ships with qiskit-ibm-runtime.
"""
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import h0_backends  # noqa: E402
import h0_qpu_time  # noqa: E402


# --------------------------------------------------------------------- name routing
def test_is_fake_names():
    assert h0_backends.is_fake("FakeFez")
    assert h0_backends.is_fake("FakeTorino")
    assert not h0_backends.is_fake("ibm_fez")
    assert not h0_backends.is_fake("ibm_marrakesh")


def test_resolve_backend_fake_names_need_no_account():
    b = h0_backends.resolve_backend("FakeFez")
    assert b.num_qubits == 156
    assert "cz" in b.target.operation_names


def test_resolve_backend_live_name_goes_through_the_service(monkeypatch):
    """Any name that is not a snapshot must be looked up on the account, not guessed."""
    calls = {}

    class _Service:
        def backend(self, name):
            calls["name"] = name
            return f"live backend {name}"

        def backends(self):
            return []

    import ibm_account
    monkeypatch.setattr(ibm_account, "open_service", lambda: _Service())
    assert h0_backends.resolve_backend("ibm_fez") == "live backend ibm_fez"
    assert calls["name"] == "ibm_fez"


def test_resolve_backend_unreachable_name_is_a_clean_exit(monkeypatch):
    class _Service:
        def backend(self, name):
            raise ValueError("no such backend")

        def backends(self):
            return []

    import ibm_account
    monkeypatch.setattr(ibm_account, "open_service", lambda: _Service())
    with pytest.raises(SystemExit):
        h0_backends.resolve_backend("ibm_nonexistent")


# --------------------------------------------------------------------- calibration record
def test_calibration_stamp_is_utc():
    assert h0_backends.calibration_stamp("2025-02-26T15:16:25-05:00") == "20250226T2016Z"
    assert h0_backends.calibration_stamp("2026-09-21T14:23:42+00:00") == "20260921T1423Z"


def test_calibration_record_on_the_snapshot_has_no_missing_errors():
    b = h0_backends.resolve_backend("FakeFez")
    edges = [e for e in b.coupling_map][:6]
    qubits = sorted({q for e in edges for q in e})
    rec = h0_backends.calibration_record(b, qubits, edges)
    assert rec["missing_errors"] == []
    assert rec["n_qubits_frozen_set"] == len(qubits)
    assert rec["last_update_date"] is not None
    assert rec["stamp"] == h0_backends.calibration_stamp(rec["last_update_date"])
    for q in qubits:
        e = rec["qubits"][str(q)]
        assert 0.0 <= e["measure_error"] <= 1.0
        assert e["measure_duration_s"] > 0
        assert e["T1_s"] > 0 and e["T2_s"] > 0
    for v in rec["edges"].values():
        assert 0.0 <= v["cz_error"] <= 1.0
        assert v["cz_duration_s"] > 0


def test_calibration_record_reports_a_none_error_instead_of_defaulting():
    """A None error must be listed in missing_errors: gate_H0P turns that into a stop."""
    b = h0_backends.resolve_backend("FakeFez")
    edge = tuple(next(iter(b.coupling_map)))
    key = h0_backends._cz_key(b.target, edge)
    props = b.target["cz"][key]
    saved = props.error
    try:
        props.error = None
        rec = h0_backends.calibration_record(b, list(edge), [edge])
        assert {"instruction": "cz", "qubits": [int(edge[0]), int(edge[1])]} in rec["missing_errors"]
        assert rec["edges"][f"{min(edge)}-{max(edge)}"]["cz_error"] is None
    finally:
        props.error = saved


# --------------------------------------------------------------------- ASAP schedule
def test_circuit_duration_is_the_asap_critical_path():
    from qiskit import QuantumCircuit

    b = h0_backends.resolve_backend("FakeFez")
    t = b.target
    d = t.durations()
    qc = QuantumCircuit(3, 3)
    qc.sx(0)
    qc.sx(1)          # parallel with the first: does not add to the critical path
    qc.sx(0)          # in series on qubit 0
    qc.measure([0, 1, 2], [0, 1, 2])
    sx0 = t["sx"][(0,)].duration
    sx1 = t["sx"][(1,)].duration
    m = max(t["measure"][(q,)].duration for q in (0, 1, 2))
    got = h0_qpu_time.circuit_duration_s(qc, d, t)
    assert got == pytest.approx(max(2 * sx0 + t["measure"][(0,)].duration,
                                    sx1 + t["measure"][(1,)].duration,
                                    m), rel=1e-12)


def test_rz_and_barrier_cost_no_time():
    from qiskit import QuantumCircuit

    b = h0_backends.resolve_backend("FakeFez")
    t, d = b.target, b.target.durations()
    qc = QuantumCircuit(1, 1)
    qc.rz(0.3, 0)
    qc.barrier()
    qc.rz(0.7, 0)
    assert h0_qpu_time.circuit_duration_s(qc, d, t) == 0.0


# --------------------------------------------------------------------- gate_H0 guards
def test_error_ratios_guard_a_zero_measured_error():
    import gate_H0

    ratio, worst, zeros = gate_H0.error_ratios([0.0, 0.02, 0.005], [0.01, 0.01, 0.01])
    assert zeros == [0]                       # no error event on that qubit
    assert ratio[0] is None                   # 1/0 is not a drift factor
    assert worst == pytest.approx(2.0)        # max(2.0, 1/0.5)
    assert ratio[1] == pytest.approx(2.0)


def test_error_ratios_without_any_event_has_no_worst_ratio():
    import gate_H0

    ratio, worst, zeros = gate_H0.error_ratios([0.0, 0.0], [0.01, 0.01])
    assert worst is None and zeros == [0, 1] and ratio == [None, None]


def test_error_ratios_ignores_a_zero_reference():
    import gate_H0

    ratio, worst, zeros = gate_H0.error_ratios([0.02, 0.01], [0.0, 0.01])
    assert ratio[0] is None and zeros == []
    assert worst == pytest.approx(1.0)


# --------------------------------------------------------------------- rule D3' (prompts/16)
def test_n4_of_sector_reproduces_a_hand_computed_value():
    """Three r = 1 circuits, four sector states, f = 0.1 everywhere.

    y_c = 0.82 * 0.7 * 0.1 = 0.0574 per shot.  With the floor 100 on the two non-k=4
    circuits the base counts are 100 * 0.0574 * (p1 + p2) = [2.87, 1.722, 0.287, 0.0] and
    the k = 4 circuit adds 0.0574 * [0.1, 0.1, 0.1, 0.2] per shot, so the shots needed to
    reach lambda* = 6 are [545.30, 745.30, 995.30, 522.65]; the binding state is the third
    and N4 = ceil(995.30 / 100) * 100 = 1000."""
    import numpy as np

    import h0_support_plan as sp

    p = {"c1": np.array([0.5, 0.1, 0.0, 0.0]),
         "c2": np.array([0.0, 0.2, 0.05, 0.0]),
         "c3": np.array([0.1, 0.1, 0.1, 0.2])}
    f = {"c1": 0.1, "c2": 0.1, "c3": 0.1}
    n4 = sp.n4_of_sector(p, f, ["c1", "c2", "c3"], ["c3"], floor=100, lambda_star=6.0,
                         margin=0.7, readout_factor=0.82, round_to=100)
    assert n4 == 1000
    shots = {"c1": 100, "c2": 100, "c3": n4}
    lam = sp.lambda_of_plan(p, f, shots, margin=0.7)
    assert lam.min() >= 6.0
    assert lam == pytest.approx([2.87 + 5.74, 1.722 + 5.74, 0.287 + 5.74, 11.48], rel=1e-12)
    # one shot less on the k = 4 circuit and the binding state falls short
    lam_short = sp.lambda_of_plan(p, f, {"c1": 100, "c2": 100, "c3": 900}, margin=0.7)
    assert lam_short.min() < 6.0


def test_n4_rounds_up_and_never_goes_below_the_floor():
    import numpy as np

    import h0_support_plan as sp

    p = {"a": np.array([1.0]), "b": np.array([1.0])}
    f = {"a": 1.0, "b": 1.0}
    # the floor alone already gives lambda = 0.82 * 0.7 * 1000 = 574 >> lambda*
    assert sp.n4_of_sector(p, f, ["a", "b"], ["b"], floor=1000, lambda_star=6.2958,
                           margin=0.7, round_to=100) == 1000


def test_garbage_term_is_the_manual_second_yield_term():
    import h0_support_plan as sp

    g = sp.garbage_of_plan({"a": 0.2, "b": 0.5}, {"a": 100, "b": 200}, 0.01, 20)
    assert g == pytest.approx((100 * 0.8 + 200 * 0.5) * 0.01 / 20)


def test_amplitudes_of_the_frozen_qpy_match_apply_groups():
    """The frozen QPY and skqd.krylov.apply_groups must give the same ideal probabilities
    (prompts/16 F1: `amplitude_crosscheck_max_dp` < 1e-9)."""
    import h0_support_plan as sp
    from gate_H0P import load_index, load_manifests
    from skqd.exact import Model

    prep = os.path.join(os.path.dirname(SCRIPTS), "data", "hardware", "H0_prep")
    index = load_index(prep)
    mans, _ = load_manifests(prep)
    two = [m for m in mans if m["id"] in ("B1_ref07_k4_rep1", "B0_ref06_k1_rep1")]
    assert len(two) == 2
    model = Model(int(index["common"]["lattice"].split("x")[1]))
    P, max_dp = sp.ideal_probabilities(prep, two, model, index["common"]["g2"])
    assert max_dp < sp.AMPLITUDE_TOL
    for v in P.values():
        assert v.sum() > 0.0 and v.min() >= 0.0


def test_f_from_a_calibration_record_equals_analyse_on_backend():
    """The offline formula of h0_support_plan must be the f of gate_S2D.analyse_on_backend."""
    import h0_support_plan as sp
    from gate_H0P import load_circuit, load_manifests
    from gate_S2D import analyse_on_backend
    from h0_backends import calibration_record, frozen_qubits_and_edges, resolve_backend

    prep = os.path.join(os.path.dirname(SCRIPTS), "data", "hardware", "H0_prep")
    mans, _ = load_manifests(prep)
    m = next(x for x in mans if x["id"] == "B0_ref06_k1_rep1")
    b = resolve_backend("FakeFez")
    qubits, edges = frozen_qubits_and_edges(prep)
    rec = calibration_record(b, qubits, edges)
    cz = {}
    for e in rec["edges"].values():
        key = tuple(e["target_key"])
        for k in {key, key[::-1]}:
            cz[k] = e["cz_error"]
    meas = {int(q): v["measure_error"] for q, v in rec["qubits"].items()}
    qc = load_circuit(prep, m)
    f_off = sp.f_from_calibration(qc, cz, meas)[0]
    assert f_off == pytest.approx(analyse_on_backend(qc, b)["f"], abs=1e-12)


# --------------------------------------------------------------------- the sampling cache
def _cache_expect():
    return {"backend": "FakeFez", "seed": 11, "sector": "B=0", "repetition": 1,
            "calibration_last_update_date": "snapshot", "shot_plan_stamp": "s1",
            "shots_by_circuit": {"c1": 267, "c2": 11700}}


@pytest.mark.parametrize("field,value", [("seed", 7), ("backend", "FakeTorino"),
                                         ("calibration_last_update_date", "2026-09-21T14:53:59-06:00"),
                                         ("shot_plan_stamp", "s2")])
def test_cache_refuses_a_mismatched_field(field, value):
    import gate_H0P

    exp = _cache_expect()
    found = dict(exp)
    found[field] = value
    with pytest.raises(SystemExit) as e:
        gate_H0P.cache_stamp(exp, found, "/tmp/B=0_r1.json")
    assert field in str(e.value)


def test_cache_refuses_mismatched_shots():
    import gate_H0P

    exp = _cache_expect()
    found = dict(exp, shots_by_circuit={"c1": 267, "c2": 267})
    with pytest.raises(SystemExit) as e:
        gate_H0P.cache_stamp(exp, found, "/tmp/B=0_r1.json")
    assert "c2" in str(e.value)


def test_cache_accepts_a_matching_record_and_a_partial_one():
    import gate_H0P

    exp = _cache_expect()
    gate_H0P.cache_stamp(exp, dict(exp), "/tmp/B=0_r1.json")          # complete
    gate_H0P.cache_stamp(exp, dict(exp, shots_by_circuit={"c1": 267}), "/tmp/B=0_r1.json")


# --------------------------------------------------------------------- six jobs, per-circuit estimate
def test_plan_groups_on_a_shot_plan_gives_the_six_production_jobs():
    """Rule D3' adds one shot count per sector, so the session has 6 jobs of
    21 / 5 / 2 / 28 / 28 / 42 pubs (prompts/16 change 4)."""
    import h0_submit
    from gate_H0P import load_manifests

    prep = os.path.join(os.path.dirname(SCRIPTS), "data", "hardware", "H0_prep")
    mans, cals = load_manifests(prep)
    n4 = {"B=0": 11700, "B=1": 28100}
    shots = {}
    for m in mans:
        if m["repetitions"] == 1:
            shots[m["id"]] = n4[m["sector"]] if m["k"] == 4 else 267
        else:
            shots[m["id"]] = {2: 130, 3: 92}[m["repetitions"]]
    jobs = [(m, shots[m["id"]]) for m in mans] + [(m, 4000) for m in cals]
    plan = h0_submit.plan_groups(jobs, 50)
    by_shots = {sh: len(chunk) for sh, _, chunk in plan}
    assert by_shots == {92: 28, 130: 28, 267: 21, 4000: 42, 11700: 5, 28100: 2}
    assert len(plan) == 6
    assert sum(len(chunk) for _, _, chunk in plan) == 126


def test_estimate_accepts_a_per_circuit_shot_plan():
    """The (kind, shots) grouping: two shot counts inside r = 1 are two groups, not a
    'mixed shot counts' error."""
    import h0_qpu_time

    prep = os.path.join(os.path.dirname(SCRIPTS), "data", "hardware", "H0_prep")
    b = h0_backends.resolve_backend("FakeFez")
    ids = ["B0_ref06_k1_rep1", "B0_ref06_k4_rep1", "B0_ref06_k1_rep2"]
    plan = {"B0_ref06_k1_rep1": 267, "B0_ref06_k4_rep1": 11700, "B0_ref06_k1_rep2": 130}
    est = h0_qpu_time.estimate(prep, b, {}, 4000, only=ids, no_calibration=True,
                               shots_by_circuit=plan)
    assert [g["group"] for g in est["groups"]] == ["r=1 x 267 shots", "r=1 x 11700 shots",
                                                   "r=2 x 130 shots"]
    assert est["total_shots"] == 267 + 11700 + 130
    assert est["shots_by_circuit_source"] is not None
    assert est["total_execution_s"] > 0

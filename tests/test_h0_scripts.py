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


# --------------------------------------------------------------------- calibration fingerprint (prompts/17)
CAL_DIR = os.path.join(os.path.dirname(SCRIPTS), "data", "hardware", "H0_ibm_fez")
FP_2053Z = "54c0a533945c6178a4c5f75584f657d3188a415b6faed7406843796f0a80a795"
FP_NIGHT = "d937c672ec9fce9ab8cf51ed58c70c41b05cd9d4599daee2c42492377886a848"


def _record(stamp):
    import json

    with open(os.path.join(CAL_DIR, f"calibration_{stamp}.json")) as fh:
        return json.load(fh)


def test_fingerprint_of_the_committed_records():
    """The serialization of prompts/17 F1 is pinned by these four hashes: three consecutive
    `last_update_date` changes of ibm_fez left every number the prediction reads untouched."""
    assert h0_backends.calibration_fingerprint(_record("20260921T2053Z")) == FP_2053Z
    for stamp in ("20260922T0544Z", "20260922T0620Z", "20260922T0711Z"):
        assert h0_backends.calibration_fingerprint(_record(stamp)) == FP_NIGHT
    # the fingerprint excludes itself and the device metadata
    rec = dict(_record("20260922T0711Z"), fingerprint="nonsense",
               last_update_date="2099-01-01T00:00:00-06:00", stamp="20990101T0600Z",
               status={"operational": False, "pending_jobs": 999})
    assert h0_backends.calibration_fingerprint(rec) == FP_NIGHT


def test_calibration_diff_reports_the_readout_recalibration():
    """The one content change on record (2026-09-21 14:53:59 -> 23:44:00) was a readout
    recalibration of all 30 qubits of the patch; the two later stamp changes moved nothing."""
    d = h0_backends.calibration_diff(_record("20260921T2053Z"), _record("20260922T0544Z"))
    assert d["n_leaves"] == 30
    assert d["families"] == ["measure_error"]
    assert d["min_ratio"] == pytest.approx(0.3735, abs=5e-4)
    assert d["max_ratio"] == pytest.approx(2.6571, abs=5e-4)
    worst = {v["path"]: v["ratio"] for v in d["leaves"]}
    assert worst["qubits/141/measure_error"] == pytest.approx(d["min_ratio"])
    assert worst["qubits/146/measure_error"] == pytest.approx(d["max_ratio"])
    for a, b in (("20260922T0544Z", "20260922T0620Z"), ("20260922T0620Z", "20260922T0711Z")):
        z = h0_backends.calibration_diff(_record(a), _record(b))
        assert z["n_leaves"] == 0 and z["families"] == [] and z["max_ratio"] is None


def test_fingerprint_is_the_noise_model_key():
    """The fingerprint is exactly the key of the seeded Aer prediction (prompts/17 F6 c).

    A perturbation OUTSIDE the frozen patch leaves both the counts and the fingerprint
    alone; three perturbations INSIDE change both.  The assertion on the fingerprint is the
    load-bearing one: a small in-patch readout change can leave 300 seeded shots identical
    by luck (measured: a x 1.5 on one qubit did), so the perturbations here are hard."""
    from gate_H0P import load_circuit, load_manifests
    from qiskit.providers import QubitProperties
    from qiskit.transpiler import InstructionProperties
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeFez

    prep = os.path.join(os.path.dirname(SCRIPTS), "data", "hardware", "H0_prep")
    qubits, edges = h0_backends.frozen_qubits_and_edges(prep)
    mans, _ = load_manifests(prep)
    man = next(x for x in mans if x["id"] == "B0_ref06_k1_rep1")
    qc = load_circuit(prep, man)

    def run(perturb=None, shots=300):
        b = FakeFez()
        t = b.target
        if perturb:
            perturb(t)
        rec = h0_backends.calibration_record(b, qubits, edges)
        counts = AerSimulator.from_backend(b, seed_simulator=11).run(qc, shots=shots).result().get_counts()
        return counts, h0_backends.calibration_fingerprint(rec)

    base, fp0 = run()

    def out_of_patch(t):
        assert 0 not in qubits
        p = t["measure"][(0,)]
        t.update_instruction_properties("measure", (0,), InstructionProperties(duration=p.duration,
                                                                               error=0.3))
        e0 = next(k for k in t["cz"].keys() if 0 in k)
        pe = t["cz"][e0]
        t.update_instruction_properties("cz", e0, InstructionProperties(duration=pe.duration, error=0.2))
        qp = list(t.qubit_properties)
        q = qp[0]
        qp[0] = QubitProperties(t1=q.t1 * 0.5, t2=min(q.t2, q.t1 * 0.999), frequency=q.frequency)
        t.qubit_properties = qp

    def in_patch_measure(t):
        p = t["measure"][(117,)]
        t.update_instruction_properties("measure", (117,), InstructionProperties(duration=p.duration,
                                                                                 error=0.3))

    def in_patch_sx(t):
        p = t["sx"][(117,)]
        t.update_instruction_properties("sx", (117,), InstructionProperties(duration=p.duration,
                                                                            error=0.2))

    def in_patch_t1(t):
        qp = list(t.qubit_properties)
        q = qp[117]
        qp[117] = QubitProperties(t1=q.t1 * 0.1, t2=min(q.t2, q.t1 * 0.099), frequency=q.frequency)
        t.qubit_properties = qp

    c, fp = run(out_of_patch)
    assert c == base and fp == fp0
    for perturb in (in_patch_measure, in_patch_sx, in_patch_t1):
        c, fp = run(perturb)
        assert fp != fp0, perturb.__name__
        assert c != base, perturb.__name__


def test_fresh_calibration_refreshes_a_live_backend_and_never_a_fake_one(monkeypatch):
    """The cache trap of qiskit-ibm-runtime 0.49.0: `properties(refresh=True)` alone leaves
    `_target` stale, so every live read goes through `IBMBackend.refresh()` -- which must
    never be called on a FakeBackendV2 (it needs a service argument)."""
    prep = os.path.join(os.path.dirname(SCRIPTS), "data", "hardware", "H0_prep")
    qubits, edges = h0_backends.frozen_qubits_and_edges(prep)
    inner = h0_backends.resolve_backend("FakeFez")

    class _Live:
        def __init__(self, wrapped):
            self._w = wrapped
            self.refreshed = 0

        def refresh(self):
            self.refreshed += 1

        def __getattr__(self, name):
            return getattr(self._w, name)

    live = _Live(inner)
    assert not h0_backends._is_live_ibm_backend(inner)      # FakeFez is never "live"
    monkeypatch.setattr(h0_backends, "_is_live_ibm_backend", lambda b: isinstance(b, _Live))
    rec = h0_backends.fresh_calibration(live, qubits, edges)
    assert live.refreshed == 1
    assert rec["fingerprint"] == h0_backends.calibration_fingerprint(rec)

    calls = []
    monkeypatch.setattr(inner, "refresh", lambda *a, **k: calls.append(1), raising=False)
    h0_backends.fresh_calibration(inner, qubits, edges)
    assert calls == []


# --------------------------------------------------------------------- the submission gate (D9)
def test_calibration_gate_on_the_committed_records():
    """Rule D9 on the real records: a stamp that moved while the content did not is a GO;
    a content change is a refusal that names what moved; an f that is not identical is a
    refusal even when the fingerprints agree."""
    import h0_submit

    live_0620 = _record("20260922T0620Z")
    pred = {"data": {"calibration": {
        "fingerprint": h0_backends.calibration_fingerprint(_record("20260922T0711Z")),
        "last_update_date": "2026-09-22T01:11:12-06:00",
        "path": "data/hardware/H0_ibm_fez/calibration_20260922T0711Z.json"},
        "f_recomputed_on_the_day": {"per_circuit": {"c1": {"f_live": 0.17}}}}}
    plan = {"calibration": {"fingerprint": pred["data"]["calibration"]["fingerprint"]},
            "f_by_circuit": {"c1": 0.17}}

    problems, rec = h0_submit.calibration_gate(live_0620, pred, plan, {"c1": 0.17})
    assert problems == []
    assert rec["fingerprint_match"] is True
    assert rec["stamp_match"] is False          # 00:20:08 vs 01:11:12, recorded, not a refusal
    assert rec["f_live_vs_plan_max_abs_diff"] == 0.0

    problems, rec = h0_submit.calibration_gate(_record("20260921T2053Z"), pred, plan, {"c1": 0.17})
    assert len(problems) == 2 and rec["fingerprint_match"] is False
    assert "30 leaf/leaves moved" in problems[0] and "measure_error" in problems[0]
    assert rec["calibration_diff"]["n_leaves"] == 30

    problems, rec = h0_submit.calibration_gate(live_0620, pred, plan, {"c1": 0.17 + 2e-9})
    assert len(problems) == 2                   # against the plan and against the prediction
    assert all("clean-shot fraction" in p for p in problems)
    assert rec["fingerprint_match"] is True


# --------------------------------------------------------------------- the watch log
def test_calwatch_summary_reproduces_hand_computed_windows(tmp_path):
    import json

    import h0_calwatch

    stamps = ["A", "A", "B", "B", "B", "C"]
    fps = ["X", "X", "X", "Y", "Y", "Y"]
    p = tmp_path / "watch.jsonl"
    with open(p, "w") as fh:
        for i, (s, f) in enumerate(zip(stamps, fps)):
            fh.write(json.dumps({"utc": f"2026-09-22T12:{5 * i:02d}:00Z", "backend": "ibm_fez",
                                 "last_update_date": s, "fingerprint": f}) + "\n")
    out = h0_calwatch.summarise(str(p))
    assert out["polls"] == 6
    # stamps: A held 12:00 -> 12:05 (300 s, next value seen at 12:10), B 12:10 -> 12:20 (600 s),
    # C is the open window at 12:25 (0 s so far)
    assert out["stamp"]["values"] == 3 and out["stamp"]["closed_windows"] == 2
    assert out["stamp"]["min_s"] == 300 and out["stamp"]["median_s"] == 450
    assert out["stamp"]["max_s"] == 600 and out["stamp"]["open_window_s"] == 0
    assert [w["seconds_upper_bound"] for w in out["stamp"]["windows"]] == [600, 900, 0]
    # fingerprints: X 12:00 -> 12:10 (600 s), Y open since 12:15 (600 s so far)
    assert out["fingerprint"]["values"] == 2 and out["fingerprint"]["closed_windows"] == 1
    assert out["fingerprint"]["max_s"] == 600 and out["fingerprint"]["open_window_s"] == 600
    assert out["fingerprint"]["open_value"] == "Y"


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
            "calibration_fingerprint": "a" * 64,
            "calibration_last_update_date": "snapshot", "shot_plan_stamp": "s1",
            "shots_by_circuit": {"c1": 267, "c2": 11700}}


@pytest.mark.parametrize("field,value", [("seed", 7), ("backend", "FakeTorino"),
                                         ("calibration_fingerprint", "b" * 64),
                                         ("sector", "B=1")])
def test_cache_refuses_a_mismatched_field(field, value):
    import gate_H0P

    exp = _cache_expect()
    found = dict(exp)
    found[field] = value
    with pytest.raises(SystemExit) as e:
        gate_H0P.cache_stamp(exp, found, "/tmp/B=0_r1.json")
    assert field in str(e.value)


@pytest.mark.parametrize("field,value", [
    ("calibration_last_update_date", "2026-09-22T00:20:08-06:00"),
    ("shot_plan_stamp", "20260922T0620Z"),
    ("shots_plan_file", "data/hardware/H0_ibm_fez/shot_plan_20260922T0620Z.json")])
def test_cache_accepts_a_record_that_differs_only_in_the_timestamps(field, value):
    """prompts/17 D11: the cache is keyed by the calibration CONTENT.  ibm_fez moved its
    `last_update_date` three times in one night without changing one number the seeded Aer
    sampling reads, so a stamp difference must not invalidate the counts."""
    import gate_H0P

    exp = _cache_expect()
    gate_H0P.cache_stamp(exp, dict(exp, **{field: value}), "/tmp/B=0_r1.json")


def test_cache_refuses_a_file_without_a_fingerprint():
    import gate_H0P

    exp = _cache_expect()
    found = {k: v for k, v in exp.items() if k != "calibration_fingerprint"}
    with pytest.raises(SystemExit) as e:
        gate_H0P.cache_stamp(exp, found, "/tmp/B=0_r1.json")
    assert "calibration_fingerprint" in str(e.value)
    assert "A''6" in str(e.value)


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


def test_the_committed_caches_all_belong_to_one_calibration_content():
    """prompts/16 B'4 as corrected by prompts/17: every cache file of a session, the
    prediction and the calibration record it names carry the SAME fingerprint -- the
    invariant that makes the seven files one experiment (the stamps may differ)."""
    import glob
    import json

    import h0_backends as hb

    root = os.path.dirname(SCRIPTS)
    files = sorted(glob.glob(os.path.join(root, "data", "hardware", "H0_ibm_fez",
                                          "sim_cache", "*.json")))
    assert len(files) == 7
    fps = set()
    for p in files:
        d = json.load(open(p))
        fp = d["calibration_fingerprint"]
        assert len(fp) == 64, p
        fps.add(fp)
        src = d.get("calibration_fingerprint_source") or ""
        sp = src if os.path.isabs(src) else os.path.join(root, src)
        if os.path.isfile(sp):                      # the record the class was sampled on
            assert hb.calibration_fingerprint(json.load(open(sp))) == fp, p
    assert len(fps) == 1, "the sampling cache mixes two calibration contents"
    pred = json.load(open(os.path.join(root, "validation", "H0P_ibm_fez.json")))
    assert pred["data"]["calibration"]["fingerprint"] in fps
    assert pred["data"]["shot_plan_calibration_fingerprint"] in fps
    for p in sorted(glob.glob(os.path.join(root, "data", "hardware", "H0_rehearsal_cache",
                                           "*.json"))):
        assert len(json.load(open(p))["calibration_fingerprint"]) == 64, p


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

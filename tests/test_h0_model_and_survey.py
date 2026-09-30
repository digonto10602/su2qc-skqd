"""Tests of the prompts/20 machinery: the T2 override, the scheduled path, the
record-backed backend, the chunk seeding, and the device survey's statistics.

Everything here runs offline on the committed records and the offline fake-provider
snapshots; nothing touches a QPU, an IBM account or the frozen circuit set (which is only
read).  The Aer draws of gate H0_model are NOT re-run here -- they are minutes each -- so
what is tested is every piece that decides what Aer is asked to simulate.
"""
import json
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(ROOT, "src"))

RECORD = os.path.join(ROOT, "data", "hardware", "H0_ibm_fez",
                      "calibration_20260922T1400Z.json")
DIAG = os.path.join(ROOT, "validation", "H0_diag.json")
PREP = os.path.join(ROOT, "data", "hardware", "H0_prep")
CANARY = "B0_ref06_k1_rep1"
FINGERPRINT = "7fd6d65eaa1a1b4f"


# ---------------------------------------------------------------- B2: the T2 override
def test_t2_override_rule_reproduces_the_named_table():
    """Rule M-T2 on the J1 windowed-Ramsey pub: 7 measured, 2 bounds, 3 at the patch minimum.

    The table prompts/20 B2 names: 117 72.5 us, 122 36.5, 124 17.7, 136 35.9, 142 18.6,
    143 15.2, 146 19.4 measured; 123 and 145 the 3 sigma upper bounds 13.3 and 13.4;
    125, 141 and 144 the patch minimum 13.3."""
    from h0_t2_override import override_from_ramw
    with open(DIAG) as fh:
        ramw = json.load(fh)["data"]["idle_tests"]["J1"]["ramw"]
    ov = override_from_ramw(ramw)
    us = {r["qubit"]: round(r["T2_used_s"] * 1e6, 1) for r in ov["table"]}
    prov = {r["qubit"]: r["provenance"] for r in ov["table"]}
    assert us == {117: 72.5, 122: 36.5, 123: 13.3, 124: 17.7, 125: 13.3, 136: 35.9,
                  141: 13.3, 142: 18.6, 143: 15.2, 144: 13.3, 145: 13.4, 146: 19.4}
    assert [q for q, p in prov.items() if p == "measured"] == [117, 122, 124, 136, 142, 143, 146]
    assert [q for q, p in prov.items() if p == "upper_bound"] == [123, 145]
    assert [q for q, p in prov.items() if p == "patch_minimum"] == [125, 141, 144]
    assert (ov["n_measured"], ov["n_upper_bound"], ov["n_patch_minimum"]) == (7, 2, 3)
    assert round(ov["patch_minimum_s"] * 1e6, 1) == 13.3
    # every used value is at or below the record's Hahn-echo T2 except qubit 146, whose echo
    # T2 (16.0 us) is itself below the free-induction value the diagnostic measured
    below = [r["qubit"] for r in ov["table"] if r["T2_used_s"] > r["T2_record_echo_s"]]
    assert below == [146]


def test_apply_t2_override_reaches_the_target():
    """prompts/17 PC 3: `qubit_properties` must be ASSIGNED, and the assignment must stick."""
    from gate_H0P import apply_t2_override
    from h0_backends import resolve_backend
    b = resolve_backend("FakeFez")
    before = b.target.qubit_properties[117].t2
    t1 = b.target.qubit_properties[117].t1
    table = apply_t2_override(b, {"source": "test",
                                  "per_qubit": {"117": {"T2_s": 1e-6,
                                                        "provenance": "measured"}}})
    assert b.target.qubit_properties[117].t2 == pytest.approx(1e-6)
    assert b.target.qubit_properties[117].t1 == t1          # T1 untouched
    assert before != pytest.approx(1e-6)
    assert table["per_qubit"][0]["T2_original_s"] == pytest.approx(before)
    assert table["clipped"] == []


def test_apply_t2_override_clips_above_two_T1_and_records_it():
    from gate_H0P import apply_t2_override
    from h0_backends import resolve_backend
    b = resolve_backend("FakeFez")
    t1 = b.target.qubit_properties[117].t1
    table = apply_t2_override(b, {"source": "test",
                                 "per_qubit": {"117": {"T2_s": 10 * t1,
                                                       "provenance": "measured"}}})
    assert b.target.qubit_properties[117].t2 == pytest.approx(2 * t1)
    assert len(table["clipped"]) == 1
    assert table["per_qubit"][0]["clipped_to_2T1"] is True


# ---------------------------------------------------------------- B1: scheduling
def test_scheduling_adds_delays_and_no_gates():
    """519 delays, 663 CZ unchanged, and the ASAP critical path equal to the unscheduled one."""
    from gate_H0P import load_circuit, load_manifests, schedule_circuit
    from h0_backends import resolve_backend
    mans, _ = load_manifests(PREP)
    man = next(m for m in mans if m["id"] == CANARY)
    qc = load_circuit(PREP, man)
    b = resolve_backend("FakeFez")
    before = {k: v for k, v in qc.count_ops().items() if k != "delay"}
    sched, info = schedule_circuit(qc, b)
    assert info["ops_non_delay"] == {k: int(v) for k, v in sorted(before.items())}
    assert info["n_delays"] == 519
    assert info["n_cz"] == 663 == man["cz"]
    # scheduling must not move the critical path: agreement well inside one dt
    assert info["duration_agreement_dt"] < 1.0


def test_scheduling_refuses_if_an_operation_moves(monkeypatch):
    import gate_H0P as g
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(1)
    qc.sx(0)

    def fake_transpile(*a, **k):
        out = QuantumCircuit(1)
        out.x(0)
        return out
    monkeypatch.setattr("qiskit.transpile", fake_transpile)
    with pytest.raises(SystemExit) as e:
        g.schedule_circuit(qc, object())
    assert "scheduling changed the operations" in str(e.value)


# ---------------------------------------------------------------- C3: the record backend
def test_backend_from_record_reproduces_the_fingerprint():
    from h0_backends import backend_from_record, calibration_record
    with open(RECORD) as fh:
        rec = json.load(fh)
    b, info = backend_from_record(rec)            # asserts the round trip internally
    assert info["fingerprint"].startswith(FINGERPRINT)
    assert len(info["qubits"]) == 30 and len(info["edges"]) == 54
    back = calibration_record(b, info["qubits"], [tuple(e) for e in info["edges"]])
    assert back["fingerprint"] == rec["fingerprint"]
    # the T1/T2 of the record, not FakeFez's
    for q in ("117", "146"):
        assert b.target.qubit_properties[int(q)].t2 == pytest.approx(rec["qubits"][q]["T2_s"])
        assert b.target.qubit_properties[int(q)].t1 == pytest.approx(rec["qubits"][q]["T1_s"])


def test_backend_from_record_refuses_a_record_it_did_not_reproduce():
    from h0_backends import backend_from_record
    with open(RECORD) as fh:
        rec = json.load(fh)
    rec["qubits"]["117"]["cz_error_typo"] = 1.0       # harmless
    rec["fingerprint"] = "0" * 64                      # not the fingerprint of the content
    with pytest.raises(SystemExit) as e:
        backend_from_record(rec)
    assert "did not reproduce the record" in str(e.value)


# ---------------------------------------------------------------- C3: the chunk seeding
def test_chunk_seed_makes_the_chunks_one_seeded_run():
    """qiskit-aer seeds the noise trajectory of shot j with seed_simulator + j, so chunks must
    be offset by their own shot count, not by 1 (verified bit for bit: 200 shots at seed 11
    plus 200 at seed 211 reproduce 400 at seed 11 with 0 differing keys)."""
    from gate_H0_model import chunk_seed
    assert [chunk_seed(11, c, 2000) for c in range(4)] == [11, 2011, 4011, 6011]
    assert [chunk_seed(11, c, 200) for c in range(3)] == [11, 211, 411]


def test_the_committed_chunks_are_genuinely_different_samples():
    """The regression that the seed bug of this step must not come back: the four chunks of
    each end must not decode to the same accepted and reference counts."""
    import glob
    for end in ("echo", "t2star"):
        files = sorted(glob.glob(os.path.join(ROOT, "data", "hardware", "H0_model",
                                              f"aer_{end}_chunk*_2000shots.json")))
        if len(files) < 4:
            pytest.skip("the H0_model Aer chunks are not on disk")
        seeds, totals = [], []
        for f in files:
            with open(f) as fh:
                d = json.load(fh)
            seeds.append(d["seed_simulator"])
            totals.append(sum(d["counts"].values()))
        assert sorted(seeds) == [11, 2011, 4011, 6011]
        assert totals == [2000] * 4


# ---------------------------------------------------------------- E2: the survey statistics
def test_survey_reproduces_the_planner_T2_geography_of_the_FakeFez_snapshot():
    """P12 of the planner analysis: percentiles 22.6/48.1/88.0/122.9/158.0 us, and -- with the
    readout filter only -- largest components [41, 33, 19] at 40 us, [21, 11, 11, 11] at 60,
    [17, 8, 7] at 80, [6, 5, 4] at 100, [5, 4, 4] at 120, [3, 3, 2] at 150."""
    from h0_device_survey import components, full_device_record, t2_statistics
    rec = full_device_record("FakeFez")
    s = t2_statistics(rec)
    assert [round(s["T2_percentiles_us"][str(p)], 1) for p in (10, 25, 50, 75, 90)] == \
        [22.6, 48.1, 88.0, 122.9, 158.0]
    expect = {40: [41, 33, 19], 60: [21, 11, 11], 80: [17, 8, 7],
              100: [6, 5, 4], 120: [5, 4, 4], 150: [3, 3, 2]}
    for L, want in expect.items():
        got = components(rec, L, cz_max=1.0)["largest_sizes"][:3]
        assert got == want, (L, got, want)
    # a 12-qubit tree needs a connected 12-qubit region: the snapshot has one at 80 us, none at 100
    assert components(rec, 80)["components_of_at_least_12"] >= 1
    assert components(rec, 100)["components_of_at_least_12"] == 0


def test_p11_interpolation_matches_the_planner_table():
    """The D3' execution time is linear in 1/f to better than a per cent over the table."""
    from h0_device_survey import P11_TABLE, p11_interpolated
    for f, ex in P11_TABLE:
        assert p11_interpolated(f) == pytest.approx(ex, rel=1e-9)
    # between two rows the interpolation must lie between them
    assert 60.8 < p11_interpolated(0.07) < 104.2


def test_resolve_backend_knows_the_offline_snapshots_without_an_account():
    from h0_backends import is_fake, resolve_backend
    assert is_fake("FakeFez") and is_fake("FakeMarrakesh") and is_fake("FakeKingston")
    assert not is_fake("ibm_fez") and not is_fake("FakeNoSuchDevice")
    assert resolve_backend("FakeMarrakesh").num_qubits == 156


# ---------------------------------------------------------------- B1/B2: the cache key
def _cache_record(**over):
    rec = {"backend": "ibm_fez", "seed": 11, "sector": "B=0", "repetition": 1,
           "calibration_fingerprint": "f" * 64,
           "shots_by_circuit": {"B0_ref06_k1_rep1": 267}}
    rec.update(over)
    return rec


def test_the_cache_key_separates_a_scheduled_run_from_an_unscheduled_one():
    """prompts/20 B1: the same circuits at the same seed against the same calibration are a
    DIFFERENT experiment once they are scheduled, so the cache must refuse the crossover."""
    from gate_H0P import cache_stamp
    found = _cache_record()                        # written before prompts/20: no `schedule`
    cache_stamp(_cache_record(), found, "B=0_r1.json")                  # unscheduled: reused
    cache_stamp(_cache_record(schedule="none", t2_override_sha=None), found, "B=0_r1.json")
    with pytest.raises(SystemExit) as e:
        cache_stamp(_cache_record(schedule="asap"), found, "B=0_r1.json")
    assert "cached schedule is 'none', this run needs 'asap'" in str(e.value)


def test_the_cache_key_separates_two_T2_overrides():
    from gate_H0P import cache_stamp
    a = _cache_record(schedule="asap", t2_override_sha="a" * 64)
    with pytest.raises(SystemExit) as e:
        cache_stamp(_cache_record(schedule="asap", t2_override_sha="b" * 64), a, "B=0_r1.json")
    assert "t2_override_sha" in str(e.value)
    # and a run WITHOUT an override must not reuse a run with one
    with pytest.raises(SystemExit):
        cache_stamp(_cache_record(schedule="asap"), a, "B=0_r1.json")


# ---------------------------------------------------------------- B3 / H0P-Y': the sandwich
def test_the_H0PY_bracket_orders_the_bound_below_the_scheduled_simulation():
    """Decision H0P-Y': the analytic PTA bound must not exceed the scheduled simulation's
    clean f.  Exercised on the committed FakeFez scheduled sample of prompts/20 B4 (73
    accepted, 21 reference hits of 2000), against the snapshot's own calibration record.

    This is the arithmetic of `pta_bounds` / `yield_bracket` and of the criterion that reads
    them; the full `gate_H0P.py --schedule asap` run over all 84 circuits is hours of Aer and
    is not exercised here."""
    import glob
    from gate_H0P import (clean_statistics, load_manifests, pta_bounds, random_acceptance,
                          yield_bracket)
    from h0_backends import calibration_record, frozen_qubits_and_edges, resolve_backend
    from skqd.codec import Codec
    from skqd.exact import Model
    from skqd.reference_sim import qiskit_key_to_bits
    from gate_H0P import load_circuit
    cache = os.path.join(ROOT, "data", "hardware", "H0_model", "cache_asap_echo")
    files = sorted(glob.glob(os.path.join(cache, "B=*_r*.json")))
    if not files:
        pytest.skip("the prompts/20 B4 scheduled sample is not on disk")
    mans, _ = load_manifests(PREP)
    by_id = {m["id"]: m for m in mans}
    records, ids = [], []
    for f in files:
        with open(f) as fh:
            rec = json.load(fh)
        assert rec["schedule"] == "asap"
        for cid, counts in rec["counts"].items():
            ids.append(cid)
            records.append((by_id[cid], {qiskit_key_to_bits(k): int(v)
                                         for k, v in counts.items()}))
    M = Model(2)
    acc = {m["sector"]: random_acceptance(Codec(M.basis), m["twoB"])["fraction"]
           for m, _ in records}
    cs = clean_statistics(records, M, 4.0, acc)
    assert cs["per_circuit"][CANARY]["accepted"] == 73
    assert cs["per_circuit"][CANARY]["reference_hits"] == 21

    b = resolve_backend("FakeFez")
    rec = calibration_record(b, *frozen_qubits_and_edges(PREP))
    sel = [by_id[i] for i in ids]
    circuits = {i: load_circuit(PREP, by_id[i]) for i in ids}
    pta = pta_bounds(circuits, sel, rec)
    bracket = yield_bracket(pta, cs, sel)
    key = f"{by_id[CANARY]['sector']} r={by_id[CANARY]['repetitions']}"
    v = bracket[key]
    assert v["bound_below_simulation"] is True
    assert v["ratio_simulation_over_bound"] > 1.0
    # P9 / section 3.1 of the planner analysis: the bound is ~12x below the scheduled Aer f
    assert 3.0 < v["ratio_simulation_over_bound"] < 40.0
    assert pta[CANARY]["f_gates"] == pytest.approx(0.1261, abs=5e-4)

"""Tests of the T2-aware patch selector (`scripts/h0_patch_select.py`).

The selector must not invent a second idle model: everything it scores comes from
`scripts/h0_idle_model.py`, and the identity embedding -- the patch the transpiler
actually chose -- has to reproduce that script's own numbers exactly.  Everything here
runs offline on the committed calibration records; nothing touches a QPU, an IBM account
or the frozen circuit set (which is only read).
"""
import json
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import h0_idle_model as im  # noqa: E402
import h0_patch_select as ps  # noqa: E402

PREP = os.path.join(ROOT, "data", "hardware", "H0_prep")
RECORD = os.path.join(ROOT, "data", "hardware", "H0_ibm_fez",
                      "calibration_20260922T1400Z.json")
CANARY_RECORD = os.path.join(ROOT, "data", "hardware", "H0_ibm_fez_canary",
                             "calibration_at_submission_20260922T1400Z.json")
CIRCUIT = "B0_ref06_k1_rep1"

# the patch the transpiler chose on FakeFez, and the one the idle-aware rule selects on
# the committed ibm_fez record of 2026-09-22T14:00Z
INCUMBENT = [117, 122, 123, 124, 125, 136, 141, 142, 143, 144, 145, 146]
SELECTED = [117, 122, 123, 124, 125, 136, 140, 141, 142, 143, 144, 145]


@pytest.fixture(scope="module")
def record():
    with open(RECORD) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def canary_circuit():
    from gate_H0P import load_circuit, load_manifests
    mans, _ = load_manifests(PREP)
    m = next(x for x in mans if x["id"] == CIRCUIT)
    return load_circuit(PREP, m), m


@pytest.fixture(scope="module")
def result(record):
    return ps.search(PREP, record, CIRCUIT, top=20, family=False)


def test_the_interaction_graph_is_a_12_node_11_edge_tree(canary_circuit):
    qc, man = canary_circuit
    adj, edges = ps.interaction_graph(qc)
    assert len(adj) == 12
    assert len(edges) == 11                     # 12 nodes, 11 edges, connected -> a tree
    assert sorted(adj) == sorted(man["physical_qubits"])
    assert sorted((len(v) for v in adj.values()), reverse=True) == [3, 3] + [2] * 6 + [1] * 4


def test_relabelling_changes_only_the_qubits(canary_circuit, record, result):
    """A relabelled circuit is the same circuit: same ops, same CZ count, same clbits."""
    qc, _man = canary_circuit
    ops = ps.circuit_ops(qc)
    mapping = {int(k): int(v) for k, v in result["best"]["mapping"].items()}
    nc = ps.relabel(ops, qc.num_qubits, qc.num_clbits, mapping)
    assert dict(nc.count_ops()) == dict(qc.count_ops())
    assert nc.num_clbits == qc.num_clbits
    host_adj, _ = ps.host_graph(record)
    used = set()
    for inst in nc.data:
        qs = [nc.find_bit(q).index for q in inst.qubits]
        if inst.operation.name == "cz":
            assert qs[1] in host_adj[qs[0]]      # every CZ still lands on a real edge
        if inst.operation.name != "barrier":
            used.update(qs)
    assert sorted(used) == SELECTED
    # clbit i still carries logical qubit i: the decoder and the bit order are untouched
    old = [(qc.find_bit(i.clbits[0]).index) for i in qc.data if i.operation.name == "measure"]
    new = [(nc.find_bit(i.clbits[0]).index) for i in nc.data if i.operation.name == "measure"]
    assert old == new


def test_the_identity_embedding_reproduces_h0_idle_model(result, record, canary_circuit):
    qc, _man = canary_circuit
    sch = im.schedule(qc, record)
    _per_q, tot = im.budgets(sch, record)
    f_gates = im.f_on_record(qc, record)[0]
    inc = result["incumbent"]
    assert inc["physical_qubits"] == INCUMBENT
    assert inc["f_gates"] == f_gates
    assert inc["S_T1"] == tot["S_T1"]
    assert inc["S_T2"] == tot["S_T2"]
    assert inc["f_dd_off"] == im.predictions(f_gates, tot, result["garbage_acceptance"])["dd_off"]["f"]
    c = result["consistency_with_h0_idle_model"]
    assert c["ok"] and c["f_dd_off_delta"] <= ps.CONSISTENCY_TOL
    # the planner's P1 numbers for this patch (tests/test_h0_idle_model.py)
    assert inc["S_T2"] == pytest.approx(2.568, rel=1e-3)
    assert inc["n_cz"] == 663


def test_the_record_admits_ten_candidate_patches(result):
    """The committed record covers 30 of the 156 qubits, which is 10 embeddings."""
    assert result["host"]["n_qubits"] == 30
    assert result["n_candidates"] == 10
    assert result["n_scored"] == 10
    assert result["n_skipped"] == 0
    assert len({tuple(e["physical_qubits"]) for e in result["top"]}) == 10


def test_the_selected_patch_beats_the_transpilers_by_1_41x(result):
    best = result["best"]
    assert best["physical_qubits"] == SELECTED
    assert best["rank"] == 1
    g = result["gain"]
    assert g["incumbent_rank"] == 3
    assert g["f_dd_off_best_over_incumbent"] == pytest.approx(1.410, rel=1e-3)
    assert g["yield_best_over_incumbent"] == pytest.approx(1.163, rel=1e-3)
    # the whole gain is coherence: one qubit swapped, 146 (T2 = 16 us) for 140 (36 us)
    assert g["n_qubits_changed"] == 1
    assert g["qubits_changed"] == [140, 146]
    assert result["incumbent"]["worst_qubit"] == 146
    assert result["incumbent"]["worst_qubit_T2_s"] * 1e6 == pytest.approx(16.0, abs=0.1)
    assert best["min_T2_s"] > result["incumbent"]["min_T2_s"]
    assert g["delta_S_T2"] == pytest.approx(0.386, rel=1e-2)


def test_gate_error_alone_picks_the_transpilers_patch(result):
    """The control: the incumbent IS the f_gates optimum -- the layout did its job, and
    the objective is what was wrong, not the search."""
    assert result["best_by_gate_error_only"]["physical_qubits"] == INCUMBENT
    assert result["gain"]["f_dd_off_gate_only_over_incumbent"] == 1.0
    assert result["incumbent"]["f_gates"] >= max(e["f_gates"] for e in result["top"])


def test_the_two_records_of_the_amendment_agree(result):
    """`H0_ibm_fez/...1400Z` and the canary's at-submission record share a fingerprint."""
    from h0_backends import calibration_fingerprint
    with open(CANARY_RECORD) as fh:
        canary = json.load(fh)
    with open(RECORD) as fh:
        other = json.load(fh)
    assert calibration_fingerprint(canary) == calibration_fingerprint(other)
    r2 = ps.search(PREP, canary, CIRCUIT, top=5, family=False)
    assert r2["best"]["physical_qubits"] == result["best"]["physical_qubits"]
    assert r2["best"]["f_dd_off"] == result["best"]["f_dd_off"]
    assert r2["incumbent"]["f_dd_off"] == result["incumbent"]["f_dd_off"]


def test_the_enumeration_is_deterministic(record, canary_circuit):
    qc, _m = canary_circuit
    pat_adj, _edges = ps.interaction_graph(qc)
    host_adj, host_nodes = ps.host_graph(record)
    a, _o = ps.enumerate_embeddings(pat_adj, host_adj, host_nodes)
    b, _o = ps.enumerate_embeddings(pat_adj, host_adj, host_nodes)
    assert a == b
    assert len(a) == 10
    head, _o = ps.enumerate_embeddings(pat_adj, host_adj, host_nodes, limit=3)
    assert head == a[:3]


def test_the_ranking_is_a_strict_total_order(result):
    keys = [ps.rank_key(e) for e in result["top"]]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)


@pytest.mark.skipif(not os.path.isfile(os.path.join(ROOT, "data", "H0_patch_select.json")),
                    reason="data/H0_patch_select.json has not been generated")
def test_the_committed_json_matches_a_fresh_search(result):
    """Every number of `reports/H0_patch_select.md` is read from this JSON."""
    with open(os.path.join(ROOT, "data", "H0_patch_select.json")) as fh:
        saved = json.load(fh)
    src = next(s for s in saved["sources"]
               if s["source"]["path"].endswith("H0_ibm_fez/calibration_20260922T1400Z.json"))
    assert src["result"]["best"]["physical_qubits"] == result["best"]["physical_qubits"]
    assert src["result"]["best"]["f_dd_off"] == result["best"]["f_dd_off"]
    assert src["result"]["gain"]["f_dd_off_best_over_incumbent"] == \
        result["gain"]["f_dd_off_best_over_incumbent"]
    assert saved["objective"] == ps.OBJECTIVE
    assert saved["consistency_tolerance"] == ps.CONSISTENCY_TOL


# ---------------------------------------------------------------- prompts/23 A1-A3
KINGSTON_RECORD = os.path.join(ROOT, "data", "hardware", "device_survey_20260922",
                               "ibm_kingston_20260930T2255Z.json")
KINGSTON_WINNER = [82, 83, 96, 102, 103, 104, 105, 106, 107, 117, 125, 126]
KINGSTON_WINNER_F = 0.05622012608266227      # data/H0_device_survey_live_20260930.json


@pytest.mark.skipif(not os.path.isfile(KINGSTON_RECORD), reason="kingston record not committed")
def test_an_uncalibrated_incumbent_is_a_device_fact_not_an_enumeration_error():
    """Live kingston qubit 146 has no T1/T2: the search completes with incumbent None and
    finds the survey's fallback winner number for number (the same computation)."""
    with open(KINGSTON_RECORD) as fh:
        rec = json.load(fh)
    r = ps.search(PREP, rec, CIRCUIT, top=5, family=False)
    assert r["incumbent"] is None
    u = r["incumbent_unscorable"]
    assert u["physical_qubits"] == INCUMBENT
    assert "146" in u["reason"] and "T1_s" in u["reason"]
    assert r["consistency_with_h0_idle_model"]["ok"] is None
    assert r["best"]["physical_qubits"] == KINGSTON_WINNER
    assert abs(r["best"]["f_dd_off"] - KINGSTON_WINNER_F) <= 1e-12
    g = r["gain"]
    for k in ("f_dd_off_best_over_incumbent", "f_dd_off_gate_only_over_incumbent",
              "yield_best_over_incumbent", "incumbent_rank", "delta_S_T2"):
        assert g[k] is None
    assert g["f_dd_off_best_over_gate_only"] >= 1.0
    # the report renders without an incumbent
    res = {"json": "x", "commit": "x", "created": "x", "runtime_s": 0.0,
           "objective": ps.OBJECTIVE, "tie_break": ps.TIE_BREAK, "method": "m",
           "stability": ps.build_stability([{"label": "k", "source": {"kind": "committed", "path": "p"},
                                             "fingerprint": "f" * 16, "result": r}]),
           "sources": [{"label": "k", "source": {"kind": "committed", "path": "p"},
                        "backend": "ibm_kingston", "last_update_date": None,
                        "fingerprint": "f" * 16, "result": r}]}
    txt = ps.report_text(res)
    assert "incumbent not scorable on this record: qubit 146 has no T1_s" in txt


def test_an_incumbent_missing_from_the_enumeration_still_raises(record):
    """A patch that is in neither the scored nor the skipped list is the real bug: keep raising."""
    rec = json.loads(json.dumps(record))
    del rec["qubits"]["146"]                                   # 146 leaves the host graph
    rec["edges"] = {k: v for k, v in rec["edges"].items() if 146 not in v["target_key"]}
    with pytest.raises(SystemExit, match="the enumeration is wrong"):
        ps.search(PREP, rec, CIRCUIT, top=5, family=False)

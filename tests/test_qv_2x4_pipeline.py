"""prompts/36: the 2x4 pipeline's new functions at the smallest size (2x2) -- plan, GPU shot rule, slot segments, the
sampling run kind, the generalised campaign-33 analysis.  qiskit-aer is needed only by the sampling test."""
import json
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def test_circuits_L_2x4_family_order():
    import gate_CV as CV
    m = CV.circuits_L(4)
    assert len(m) == 60
    assert sorted(v["family_index"] for v in m.values()) == list(range(60))
    assert sum(1 for v in m.values() if v["twoB"] == 0) == 44 and sum(1 for v in m.values() if v["twoB"] == 2) == 16
    assert {v["k"] for v in m.values()} == {1, 2, 3, 4}


def test_plan_noiseless_2x2_feasible_and_floored():
    import gate_CV as CV
    M, codec, acc, sectors = CV.sectors_L(2)
    mans = CV.circuits_L(2)
    pl = CV.plan_noiseless_L(M, sectors, mans)
    for sec in ("B=0", "B=1"):
        nl = pl["noiseless"][sec]
        assert nl["lp_status"] == "optimal"
        assert min(nl["shots"].values()) >= 267
        assert nl["P_recall_S999_ge_target"] >= 0.95
        assert pl["information"]["f=0.10"][sec]["shots_total"] >= nl["shots_total"]


def test_gpu_plan_rule():
    import gate_CV as CV
    mans = {"a": {"twoB": 0}, "b": {"twoB": 0}, "c": {"twoB": 2}}
    final = {"a": 267, "b": 1300, "c": 6400}
    g, U = CV.gpu_plan(final, mans, {0: 800, 2: 6400})
    assert U == {0: 100000, 2: 200000}
    assert g["a"]["shots"] == 6250 + 100000 and g["b"]["shots"] == 10400 + 100000 and g["c"]["shots"] == 51200 + 200000
    assert g["a"]["prefix_lengths"][-1] <= g["a"]["cv_block"] and 800 in g["a"]["prefix_lengths"]
    assert {17, 33, 67, 134, 267} <= set(g["a"]["prefix_lengths"])
    g2, _ = CV.gpu_plan({"a": 267}, mans, {0: 4000})     # 2 N_eq beyond the CV block: dropped (information only)
    assert 4000 in g2["a"]["prefix_lengths"] and 8000 not in g2["a"]["prefix_lengths"]
    with pytest.raises(SystemExit):
        CV.gpu_plan({"a": 267}, mans, {0: 7000})          # N_eq itself beyond the CV block


def test_segments_tile_and_reproduce_prefix_counts():
    import quantinuum_lattice_tests as QL
    rng = np.random.default_rng(1)
    seq = rng.integers(0, 50, size=1000).astype(np.uint32)
    run = {"shots": 1000, "uniform_shots": 300, "prefix_lengths": [10, 100, 700]}
    seg = QL.segments_of(seq, run)
    assert [s["start"] for s in seg] == [0, 10, 100, 700] and sum(s["shots"] for s in seg) == 1000
    assert [s["uniform"] for s in seg] == [False, False, False, True]
    tot = {}
    for s in seg:
        if s["start"] + s["shots"] <= 100:
            for k, v in s["counts"].items():
                tot[int(k)] = tot.get(int(k), 0) + v
    u, c = np.unique(seq[:100], return_counts=True)
    assert tot == {int(a): int(b) for a, b in zip(u, c)}


def test_sample_aer_2x2_amplitudes_and_measure_sampling():
    pytest.importorskip("qiskit_aer")
    import quantinuum_lattice_tests as QL
    from gate_S2D import circuit_set
    from skqd import circuits_qiskit as cq
    M, F, cset = circuit_set(2)
    tb, r, k, gates = cset[1]
    qc = cq.ir_to_qiskit(gates, 12, measure=True)
    P = QL.Phys(2)
    amps, seq, res, _s = QL.sample_aer(qc, P.emb.ints, 2000, 123, "CPU", 2)
    assert res.results[0].metadata.get("measure_sampling") is True
    sv, _ = QL._statevector_gpu(qc, "CPU", 2)
    assert np.abs(sv[P.emb.ints] - amps).max() <= 1e-12
    assert len(seq) == 2000 and set(int(x) for x in np.unique(seq)) <= set(int(x) for x in P.emb.ints)
    amps2, seq2, _r, _s = QL.sample_aer(qc, P.emb.ints, 2000, 123, "CPU", 2)
    assert np.array_equal(seq, seq2)                         # seed_simulator fixes the sequence


def test_phys_acceptance_source():
    import quantinuum_lattice_tests as QL
    P = QL.Phys(2)
    assert P.sector[0]["a_source"] == "assumed"             # no data/cv/acceptance_2x2.json
    if os.path.exists(os.path.join(ROOT, "data", "cv", "acceptance_2x3.json")):
        P3 = QL.Phys(3)
        assert P3.sector[0]["a_source"] == "data/cv/acceptance_2x3.json"
        assert P3.sector[0]["a"] == P3.sector[0]["dim"] / 2 ** 20      # the 2x3 count equals the dimension


def test_ir_text_sha256_deterministic():
    import quantinuum_lattice_tests as QL
    g = [("cx", [0, 1], None), ("ry", [2], 0.25), ("unitary", [0], np.eye(2, dtype=complex))]
    assert QL.ir_text_sha256(g) == QL.ir_text_sha256(list(g))
    assert QL.ir_text_sha256(g) != QL.ir_text_sha256(g[:2])


def test_dry_part_36_structure():
    pytest.importorskip("qiskit")
    import quantinuum_lattice_tests as QL
    from skqd.campaign33 import tokens as T
    p = QL.dry_part_36("QV_2x4_02")
    assert p["runs"] and all(r["kind"] == "sample" and r["twoB"] == 2 for r in p["runs"])
    assert {r["k"] for r in p["runs"]} == {1, 2, 3, 4, 5}         # R14: the B=1 family and its k = 5 circuits
    assert all("prefix_lengths_dropped" in r for r in p["runs"])
    n5 = QL.dry_part_36("QV_2x4_05")
    assert n5["runs"] and all(r["kind"] == "native" for r in n5["runs"])
    for r in p["runs"]:
        assert r["seed"] == T.chunk_seed(T.base_seed("QV_2x4_02"), r["circuit_index"], 0, r["shots"])
        assert max(r["prefix_lengths"]) <= r["shots"]


def test_campaign33_physics_lat2_cv_reading_with_k():
    from skqd.campaign33 import analysis as A
    P = A.Physics(lat=2)
    assert P.M.basis.lat.n_sites == 4 and P.S["B=0"].lattice == "2x2"
    S = P.S["B=0"]
    rng = np.random.default_rng(3)
    ids = ["c1", "c2"]
    chunks = {}
    for c in ids:
        rows, start = [], 0
        for L in (17, 16, 34, 67, 133, 533):                 # boundaries 17, 33, 67, 134, 267 (PHI x 267), 800
            acc = {}
            for i in rng.choice(S.sector_idx, size=L):
                acc[int(i)] = acc.get(int(i), 0) + 1
            rows.append({"start": start, "shots": L, "accepted": acc, "rejected": 0})
            start += L
        chunks[c] = rows
    pre = A.Prefixes.from_chunks(P, 0, chunks)
    assert pre.covered("c1", 267) and pre.covered("c1", 800)
    et = A.e_tol(P, "B=0")
    assert et["ok"] is None and et["value"] > 0
    out = A.cv_reading(P, "B=0", pre, {c: 267 for c in ids}, et["value"], with_random=False)
    assert "krylov_equal" not in out and len(out["shots_curve"]) == 5
    out2 = A.cv_reading(P, "B=0", pre, {c: 267 for c in ids}, et["value"], eq=(pre, 267, pre), with_random=False,
                        k_of={"c1": 1, "c2": 3})
    assert [q["k"] for q in out2["krylov_equal"]] == [1, 2, 3, 4] and out2["criteria"]["CV3"]["ok"] is not None

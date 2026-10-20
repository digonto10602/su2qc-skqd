"""prompts/36a: the re-plan functions at the smallest size (2x2) -- the 8N -> 32N extension, the R13 shot rule, the R14
prediction, the owner-decision parser, the cluster diagnostic, the segments rebuild check, the slot-01 cost fit."""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


@pytest.fixture(scope="module")
def cv22():
    import gate_CV as CV
    M, codec, acc, sectors = CV.sectors_L(2)
    mans = CV.circuits_L(2)
    return CV, M, codec, sectors, mans


def test_extend_sequences_keeps_block0(cv22, tmp_path):
    CV, M, codec, sectors, mans = cv22
    S = sectors["B=1"]
    states, dt, _ = CV.circuit_states_L(S, mans)
    cw = codec.all_codewords()
    plan = {c: 40 for c in states}
    with pytest.raises(SystemExit):                       # no block-0 cache: block 0 is never drawn by the extension
        CV.extend_sequences(S, states, plan, 2, 6, 1.0, 7, codec, cw, "t", cache_dir=str(tmp_path))
    base, _ = CV.sample_sequences(S, states, plan, 2, 1.0, 7, codec, cw, "t", p_ro=0.0, dtype=np.int32,
                                  cache_dir=str(tmp_path))
    ext, info = CV.extend_sequences(S, states, plan, 2, 6, 1.0, 7, codec, cw, "t", cache_dir=str(tmp_path))
    assert info["prefix_identical"] and not info["hit"]
    assert all(len(ext[c]) == 240 and np.array_equal(ext[c][:80], base[c]) for c in states)
    ext2, info2 = CV.extend_sequences(S, states, plan, 2, 6, 1.0, 7, codec, cw, "t", cache_dir=str(tmp_path))
    assert info2["hit"] and all(np.array_equal(ext[c], ext2[c]) for c in states)


def test_gpu_plan_r13_rule(cv22):
    CV = cv22[0]
    mans = {"a": {"twoB": 2}, "b": {"twoB": 2}, "z": {"twoB": 0}}
    plan1x = {"a": 267, "b": 4400, "z": 267}
    final = {"a": CV.resized_shots(267, 12), "b": CV.resized_shots(4400, 12), "z": 267}
    n_eq = {2: CV.n_eq_of(final["a"] + final["b"], 2), 0: 300}
    g, U = CV.gpu_plan_r13(final, plan1x, {0: 1, 2: 12}, mans, n_eq)
    assert U == {2: 100000, 0: 200000}
    a = g["a"]
    assert a["cv_block"] == max(2 * final["a"], 8 * 267, n_eq[2], 6250) and a["shots"] == a["cv_block"] + 100000
    assert n_eq[2] in a["prefix_lengths"] and 2 * final["a"] in a["prefix_lengths"]
    assert all(x <= a["cv_block"] for x in a["prefix_lengths"])
    assert all(x > a["cv_block"] for x in a["prefix_lengths_dropped"])
    r8 = CV.resized_shots(267, 8)
    assert r8 in a["prefix_lengths"] and CV.rnd(r8 / 2) in a["prefix_lengths"]
    assert g["z"]["cv_block"] == max(8 * 267, 6250)          # B=0 at s = 1: prompts/36 R5's block
    k5 = CV.k5_plan_r13(cv22[3], {0: 400, 2: 9000})
    r = next(v for v in k5.values() if v["twoB"] == 2)
    assert r["shots"] == 9000 and r["prefix_lengths"] == [9000] and r["prefix_lengths_dropped"] == [18000]


def test_slot_prediction_three_models():
    import gate_CV as CV
    cost = {"models": {"ratio_of_totals": {"s_per_instruction": 1e-4}, "S2_2x4_rate": {"s_per_instruction": 2e-4},
                       "fit": {"a_s": 50.0, "b_s_per_instruction": 1e-5}}}
    runs = [{"n_instructions": 100000, "shots": 1000}, {"n_instructions": 100000}]
    p = CV.slot_prediction(runs, cost)
    assert p["statevector_s"] == pytest.approx({"ratio_of_totals": 20.0, "S2_2x4_rate": 40.0, "fit": 102.0})
    assert p["predicted_s"] == pytest.approx(102.0 + 2 * (4.1 + 1.1) + 0.1)
    assert p["predicted_s_slow_sampling"] == pytest.approx(102.0 + 10.4 + 1.0) and p["fits"]


def test_owner_lines_parser():
    import gate_CV as CV
    st = CV.parse_owner_lines("OD1: SIGNED\n  OD2: STRUCK\nOD3 : UNSIGNED\nnotes OD4: SIGNED\n")
    assert st == {"OD1": "SIGNED", "OD2": "STRUCK", "OD3": "UNSIGNED", "OD4": "UNSIGNED"}


def test_cluster_diag_2x2(cv22):
    CV, M, codec, sectors, mans = cv22
    S = sectors["B=1"]
    B = list(S.refs) + [int(x) for x in S.sector_idx[:5]]
    out = CV.cluster_diag(S, {"x": B}, n_states=3)
    d1, d2 = out["D1"], out["D2"]["x"]
    assert abs(d1["energies"][0] - S.E0) < 1e-9
    for i, r in enumerate(S.refs):                        # |<psi_0|r>|^2 = the ground-state weight of r
        assert d1["psi0_overlap_vs_ground_weight"][i][0] == pytest.approx(S.prob[r], abs=1e-9)
    assert d2["size_O"] >= d2["size_B_and_O"]


def test_segments_cumulative_check():
    import quantinuum_lattice_tests as QL
    seq = np.random.default_rng(2).integers(0, 9, size=300).astype(np.uint32)
    run = {"shots": 300, "uniform_shots": 100, "prefix_lengths": [7, 50, 200]}
    seg = QL.segments_of(seq, run)
    assert QL.segments_cumulative_check(seg, seq, run)
    seg[0]["counts"] = {k: v + 1 for k, v in seg[0]["counts"].items()}
    assert not QL.segments_cumulative_check(seg, seq, run)


def test_gpu_cost_model_fit_from_slot01():
    import gate_CV as CV
    if not os.path.exists(os.path.join(ROOT, "validation", "QV_2x4_01.json")):
        pytest.skip("slot 01 not harvested")
    m = CV.gpu_cost_model()
    assert len(m["fit"]["points"]) == 9 and m["fit"]["rms_ok"]
    assert sum(p["residual_s"] for p in m["fit"]["points"]) == pytest.approx(0.0, abs=1e-6)


def test_d2_scratch_flags_relabel():
    import gate_CV as CV
    cd = {"D2": {"a": {"rH_O": 0.07, "rH_O_oracle_b1_json": 0.07 + 2e-6, "oracle_rH_reproduced_1e-9": False},
                 "b": {"rH_O": 0.06, "rH_O_oracle_b1_json": 0.06 + 2e-5}}, "oracle_rH_reproduced_1e-9": False}
    out = CV.d2_scratch_flags(cd)
    assert "oracle_rH_reproduced_1e-9" not in out and "oracle_rH_reproduced_1e-9" not in out["D2"]["a"]
    assert out["D2"]["a"]["scratch_rH_reproduced_1e-5"] and not out["D2"]["b"]["scratch_rH_reproduced_1e-5"]
    assert out["scratch_rH_reproduced_1e-5"] is False


def test_od3_nx_text():
    import gate_CV as CV
    bd = {"n_x_by_reference": {"2B=0 ref 102": [4], **{f"2B=0 ref {r}": [5] for r in range(14)}}}
    assert CV.od3_nx_text(bd) == "4 for the Dirac-sea reference 102, 5 for the other fourteen references"


def test_bundles_corrected_popcount_identity():
    import gate_CV as CV
    if not os.path.exists(CV.BUNDLE_INDEX_2X4):
        pytest.skip("no 2x4 bundle index")
    b = CV.bundles_corrected({"within_cap": True, "slot01_sources_ok": True, "roundtrip_ok": True})
    assert b["popcount_identity_holds"] and b["C_constant"] and b["rule_corrected_holds"]

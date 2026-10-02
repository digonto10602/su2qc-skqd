"""prompts/24 Stage R (gate H0_2x2): B_sig on a synthetic count table, the baselines' seeding,
the D3' plan reproducing validation/H0_kpilot.json data.budgets_at_f_pool at the pilot's f (P8 lift
struck), the energy block on the exact support, and the prereg keys."""
import glob
import json
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))

import gate_H0_2x2 as GR  # noqa: E402
import gate_H0_ddtest as GT  # noqa: E402

PREP = os.path.join(ROOT, "data", "hardware", "H0_2x2_prep")


def test_b_sig_excludes_the_garbage_level_and_keeps_a_5_sigma_state():
    mu = 25.0
    n = {0: 25, 1: int(mu + 5 * math.sqrt(mu)), 2: 0, 3: 33}
    B, pv = GR.sig_support(n, {s: mu for s in n})
    assert 0 not in B and 2 not in B and 1 in B
    assert pv[1] <= GR.SIG_P < pv[0]
    assert pv[3] > GR.SIG_P             # +1.6 sigma: not signal


def test_baselines_are_seeded():
    from skqd.codec import Codec
    from skqd.exact import Model
    codec = Codec(Model(2).basis)
    tables = {0: GR.decode_table(codec, 0), 2: GR.decode_table(codec, 2)}
    # the decode table reproduces gate E2's exhaustive acceptances
    assert np.mean(tables[0] >= 0) == pytest.approx(0.00927734375, abs=0)
    assert np.mean(tables[2] >= 0) == pytest.approx(0.0048828125, abs=0)
    shots = {"a": 3000, "b": 500, "c": 2000}
    tb = {"a": 0, "b": 0, "c": 2}
    g1 = GR.garbage_baseline(tables, shots, tb, seeds=[11, 12])
    g2 = GR.garbage_baseline(tables, shots, tb, seeds=[11, 12])
    assert g1 == g2 and g1[11] != g1[12]
    r1 = GR.random_subsets(list(range(38)), [3, 5], 10, seeds=[23, 24])
    r2 = GR.random_subsets(list(range(38)), [3, 5], 10, seeds=[23, 24])
    assert r1 == r2 and all(len(v) == 10 and {3, 5} <= set(v) for v in r1.values())


def _family_P():
    import gate_S2D_levers as G
    fam = json.load(open(os.path.join(ROOT, "data", "S2D_levers", "family.json")))["families"][
        "diag-hop0-hop1-hop2-hop3-plaq0_s2"]
    P = {c["id"]: G.ideal_distribution(list(G.DEFAULT_ORDER), c["twoB"], c["reference"], c["theta"])["p_unnormalised"]
         for c in fam["circuits"]}
    mans = [{"id": c["id"], "sector": c["sector"], "repetitions": 1, "k": c["k"]} for c in fam["circuits"]]
    return P, mans


def test_plan_reproduces_the_pilot_budget_at_f_pilot():
    import h0_device_survey as ds
    from skqd.skqd import READOUT_FACTOR, poisson_lambda_star
    kp = json.load(open(os.path.join(ROOT, "validation", "H0_kpilot.json")))["data"]
    f = kp["budgets_at_f_pool"]["f"]
    P, mans = _family_P()
    shots, n4 = GT.d3_shots(P, mans, f, poisson_lambda_star(ds.D3_K, ds.D3_CONF), ds.D3_FLOOR, ds.D3_MARGIN,
                            READOUT_FACTOR, ds.D3_ROUND)
    assert n4 == kp["budgets_at_f_pool"]["D3prime_N4"] == {"B=0": 36200, "B=1": 86300}
    assert sum(shots.values()) == kp["budgets_at_f_pool"]["D3prime_total_coarse_shots"] == 359207
    # P8 struck: every k = 1 circuit stays at the 267 floor (no D3''-H0 lift)
    assert all(v == 267 for c, v in shots.items() if c.endswith("_k1"))
    assert len(GT.job_groups({**shots, "cal_patch_all0": 4000, "cal_patch_all1": 4000},
                             {c: 4.6e-5 for c in list(shots) + ["cal_patch_all0", "cal_patch_all1"]}, 250e-6, 14)) == 5


def test_energy_block_on_the_exact_support():
    from skqd.exact import Model
    M = Model(2)
    refs = json.load(open(os.path.join(ROOT, "data", "references.json")))["references"]
    for twoB in (0, 2):
        H, idx, ev, ref, rr = GR.sector_tables(M, 4.0, twoB)
        e = GR.energy_block(H, list(idx), rr, float(ref.E0), float(ref.energies[1]), ev, dt=0.245)
        assert abs(e["E_R"] - ref.E0) < 1e-12
        assert abs(e["E_R"] - refs[f"2x2|g2=4.0|2B={twoB}"]["energies"][0]) < 1e-12
        assert e["weinstein_contains_some_sector_eigenvalue"] and e["rH"] < 1e-10
        # a support that misses most of the ground state still yields a valid (variational) certificate
        e2 = GR.energy_block(H, rr, rr, float(ref.E0), float(ref.energies[1]), ev)
        assert e2["variational_ok"] and e2["weinstein_contains_some_sector_eigenvalue"]


def test_percentile_and_summary():
    v = [1.0, 2.0, 3.0, 4.0]
    assert GR.percentile_of(2.0, v) == 50.0
    s = GR.dist_summary(v)
    assert s["mean"] == 2.5 and s["n"] == 4


@pytest.mark.skipif(not glob.glob(os.path.join(PREP, "prereg_*.json")), reason="no Stage R prereg on disk")
def test_prereg_keys():
    import gate_H0_kpilot as GK
    pre = json.load(open(sorted(glob.glob(os.path.join(PREP, "prereg_*.json")))[-1]))
    assert GK.prereg_keys_ok(pre) == []
    assert pre["owner_decision"]["path"] == GR.OWNER_DECISION and os.path.exists(os.path.join(ROOT, GR.OWNER_DECISION))
    assert set(pre["criteria"]) == {f"R{i}" for i in range(1, 9)}
    assert "struck" in pre["p8_ruling"].lower()
    plan = json.load(open(os.path.join(PREP, "shot_plan.json")))
    assert plan["calibration"]["fingerprint"] == pre["calibration"]["fingerprint"]
    assert all(v == 267 for c, v in plan["shots_by_circuit"].items() if c.endswith("_k1"))

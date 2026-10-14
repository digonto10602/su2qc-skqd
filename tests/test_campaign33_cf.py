"""
prompts/33c step 3: the C4_CF owner-item rule (prompts/33 sections 6 and 8) and the `cf` part content (sizing from the
harvested C4_CF, seeds, the merge of the parts).
"""
import json
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd.campaign33 import cf_gpu as CFG  # noqa: E402
from skqd.campaign33 import tokens as TK  # noqa: E402
from skqd.campaign33 import tokens_run as TR  # noqa: E402

CF_JSON = os.path.join(ROOT, "validation", "C4_CF.json")
RNC = os.path.join(ROOT, "data", "cf_trajectories", "r_nc.json")


def test_owner_item_rule_both_sections():
    # section 6 fires (new interval excludes the old r_nc), section 8 does not (new r_nc inside the old interval)
    oi = CFG.owner_item_r_nc([1.03, 1.078], 1.115, [1.0286, 1.1151])
    assert oi["fires"] and oi["section6_new_interval_excludes_old_r_nc"] and not oi["section8_new_r_nc_outside_old_interval"]
    # section 8 alone
    oi = CFG.owner_item_r_nc([1.10, 1.20], 1.115, [1.0286, 1.1151])
    assert oi["fires"] and oi["section8_new_r_nc_outside_old_interval"] and not oi["section6_new_interval_excludes_old_r_nc"]
    # neither
    oi = CFG.owner_item_r_nc([1.05, 1.11], 1.09, [1.0286, 1.1151])
    assert not oi["fires"] and oi["why"] == "neither rule fires"


@pytest.mark.skipif(not os.path.exists(CF_JSON), reason="validation/C4_CF.json not harvested")
def test_owner_item_on_the_harvested_c4_cf_fires_without_rewriting_it():
    """prompts/33c R4 (b): job 59736866's field compared the section-8 quantity (false); evaluated from the stored
    intervals by the section-6 rule the item fires."""
    d = json.load(open(CF_JSON))
    rnc = json.load(open(RNC))
    iv = d["data"]["pooled"]["r_d1e-03"]["ci95"]
    oi = CFG.owner_item_r_nc(iv, rnc["r_nc"], rnc["pooled_r_ci95"])
    assert d["data"]["owner_item_r_nc_outside_old_interval"] is False          # as harvested, not rewritten
    assert oi["section6_new_interval_excludes_old_r_nc"] and not oi["section8_new_r_nc_outside_old_interval"]
    assert oi["fires"] and iv[1] < rnc["r_nc"]
    from skqd.campaign33 import assemble as AS
    row = next(r for r in AS.comparisons(False, {}) if r["redo"].startswith("C4_CF"))
    assert row["owner_item"] is True and row["owner_item_field_as_harvested"] is False
    assert row["r_nc_in_use"] == rnc["r_nc"] and "k = 1" in row["k4_note"]


@pytest.mark.skipif(not os.path.exists(CF_JSON), reason="validation/C4_CF.json not harvested")
def test_cf_part_plan_from_the_harvested_job():
    d = json.load(open(CF_JSON))
    plan = CFG.cf_part_plan(d)
    k_min = min(v["K"] for v in d["data"]["trajectory_runs"].values())
    K = math.floor(CFG.CF_PART_MARGIN * k_min)
    assert plan["K_per_part"] == K and plan["parts"] == math.ceil(CFG.K_TARGET / K) and plan["K_total"] >= CFG.K_TARGET
    idx = TK.token_index("C4_CF")
    s0 = TK.base_seed("C4_CF")
    # the harvested job seeded arm i with chunk index 0 of C4_CF's own base seed
    for i, (k, v) in enumerate(d["data"]["trajectory_runs"].items()):
        assert v["seed"] == TK.chunk_seed(s0, i, 0, 1)
    seeds = set()
    for desc in plan["descriptors"]:
        assert desc["content"] == "cf" and desc["seed_token_index"] == idx and desc["seed_chunk_index"] == desc["part"] >= 1
        assert TR.part_copy_name(desc) == f"C33_CF_part{desc['part']}of{plan['parts']}"
        assert TR.expected_seed_token_index(desc, "C4_PART_01")[0] == idx
        seeds |= {TK.chunk_seed(s0, i, desc["seed_chunk_index"], 1) for i in range(len(CFG.ARMS))}
    assert len(seeds) == len(CFG.ARMS) * plan["parts"]
    assert not seeds & {v["seed"] for v in d["data"]["trajectory_runs"].values()}


def _real_arm(cid, channel):
    import gate_CF_traj as G
    from quantinuum_submit import A6_NOISE
    arm = G.load_arm(cid, channel)
    if arm is None:
        pytest.skip(f"no CF_traj chunks for {cid} {channel}")
    man = json.load(open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", cid + ".manifest.json")))
    return arm, G.arm_statistics(cid, arm, man, A6_NOISE, None)


def test_merge_of_one_part_reproduces_the_arm_statistics():
    """A single part merged through the compact arrays gives gate_CF_traj.arm_statistics' r(1e-3) (value and
    bootstrap interval) and P17 floor value exactly; two halves merged equal the whole."""
    import gate_CF_traj as G
    arm, st = _real_arm("B1_ref57_k1", "depol")
    c = CFG.compact_arm(arm, st)
    m = CFG.merge_cf_parts([{"B1_ref57_k1": c}])
    a = m["arms"]["B1_ref57_k1"]
    want = st["stats"]["r_d1e-03"]
    assert a["r"]["value"] == pytest.approx(want["value"], abs=1e-14)
    assert a["r"]["ci95"] == pytest.approx(want["ci95"], abs=1e-14)
    assert a["floor_min_feff_over_fideal_S99"]["value"] == pytest.approx(
        st["stats"]["min_feff_over_fideal_S99_d1e-03"]["value"], abs=1e-12)
    # halves: the point values of the concatenation are those of the whole
    K = c["K"]
    half = K // 2
    P = np.asarray(st["_P"], float)[:, c["S99"]]
    c1 = dict(c, K=half, h=c["h"][:half], tv_pre=c["tv_pre"][:half], sum_p_post_S99=list(P[:half].sum(axis=0)))
    c2 = dict(c, K=K - half, h=c["h"][half:], tv_pre=c["tv_pre"][half:], sum_p_post_S99=list(P[half:].sum(axis=0)))
    m2 = CFG.merge_cf_parts([{"B1_ref57_k1": c1}, {"B1_ref57_k1": c2}])["arms"]["B1_ref57_k1"]
    assert m2["K"] == K and m2["K_by_part"] == [half, K - half]
    assert m2["r"]["value"] == pytest.approx(a["r"]["value"], abs=1e-14)
    assert m2["floor_min_feff_over_fideal_S99"]["value"] == pytest.approx(a["floor_min_feff_over_fideal_S99"]["value"],
                                                                         abs=1e-12)
    assert m["pooled"] is None and G.POOL_SHOTS        # one k = 1 arm only: no pooled ratio


def test_merge_refuses_inconsistent_parts():
    c = {"K": 2, "h": [0.1, 0.2], "tv_pre": [0.0, 0.5], "f0_prime": 0.2, "p_ref": 0.9, "S99": [0, 1],
         "pc_S99": [0.5, 0.4], "sum_p_post_S99": [0.9, 0.7]}
    with pytest.raises(ValueError):
        CFG.merge_cf_parts([{"B0_ref25_k1": c}, {"B0_ref25_k1": dict(c, p_ref=0.8)}], n_boot=10)


def test_cf_part_dispatch_checks_the_seed_index(tmp_path, monkeypatch):
    """run_part runs a cf content through cf_gpu.run(ctx, part=...) and P0 demands seed_token_index = C4_CF's."""
    calls = []
    monkeypatch.setattr(CFG, "run", lambda ctx, part=None: calls.append(part))

    class R:
        def __init__(self):
            self.rows = []

        def add(self, name, value, thr, passed):
            self.rows.append((name, passed))
    for idx, ok in ((TK.token_index("C4_CF"), True), (TK.token_index("C4_PART_01"), False)):
        p = tmp_path / "p.json"
        desc = {"content": "cf", "token": "C4_CF", "run": "CF", "part": 1, "parts": 2, "K_per_arm": 10,
                "seed_chunk_index": 1, "seed_token_index": idx, "slot": "C4_PART_01"}
        p.write_text(json.dumps(desc))
        from types import SimpleNamespace
        ctx = SimpleNamespace(args=SimpleNamespace(parts_file=str(p)), token="C4_PART_01", data={}, notes=[], R=R(),
                              dry=True, min_shots_ok=True)
        calls.clear()
        TR.run_part(ctx)
        assert ctx.R.rows[0][1] is ok and ctx.copy_to == "C33_CF_part1of2"
        assert (len(calls) == 1) is ok

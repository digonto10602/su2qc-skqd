"""
prompts/33a step D: class-4 re-sizing by measurement and the generic part slots.

Pinned here: the 20 slots C4_PART_01..20 in the token table (after the 33; their seeds disjoint from the 33's),
ci/allowed_jobs.campaign33a generated from the table; the resize arithmetic (fit t = c + b chunk, N_max, parts)
including the prompt's synthetic case b = 0.02, c = 2.7 (n = 2 for 100 000 shots at share 0.75, n = 1 for
27 309 at 0.6); the split of a run into parts whose concatenation is exactly the unsplit chunk plan (every
gate_CV prefix point a boundary); the slot content files; and that the assembly of parts rebuilds the
unsplit prefix boundaries and the same E_tol.
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import campaign33_resize as RS  # noqa: E402
from skqd.campaign33 import sampling as SM  # noqa: E402
from skqd.campaign33 import tokens as TK  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SLOTS = [f"C4_PART_{i:02d}" for i in range(1, 21)]


# --------------------------------------------------------------------------- the slots
def test_twenty_slots_in_the_table():
    tok = TK.load_tokens()
    assert list(TK.slot_tokens()) == SLOTS and list(tok)[-20:] == SLOTS
    for t in SLOTS:
        v = tok[t]
        assert (v["class"], v["walltime"], v["gpus"], v["env"]) == (4, "01:00:00", 1, "skqd")
        assert v["script"] == "scripts/campaign33.py" and v["args"] == ["--token", t]


def test_allowlist_33a_is_generated_from_the_table():
    txt = open(TK.ALLOWLIST_FILE_33A).read()
    assert txt == TK.allowlist_text(TK.slot_tokens())
    assert txt.splitlines() == [f"{t}  01:00:00 1" for t in SLOTS]
    assert len(open(TK.ALLOWLIST_FILE).read().splitlines()) == 33, "the prompts/33 allowlist is unchanged"


def test_slot_seeds_are_disjoint_from_the_33():
    s33 = [TK.base_seed(t) for t in TK.campaign_tokens()]
    ss = [TK.base_seed(t) for t in SLOTS]
    assert max(s33) < min(ss) and len(set(ss)) == 20
    assert TK.base_seed("C4_CF") == TK.BASE_SEED + 32 * TK.SEED_PER_TOKEN, "the 33 indices are unchanged"


def test_driver_dispatches_slots():
    import campaign33 as C33
    a = C33.build_parser({"CI_GATE": "C4_PART_07"}).parse_args(["--token", "C4_PART_07"])
    assert a.parts_file is None and a.budget_minutes == 50.0
    src = open(os.path.join(ROOT, "scripts", "campaign33.py")).read()
    assert "TK.is_slot(t)" in src and "TR.run_part(ctx)" in src


# --------------------------------------------------------------------------- the resize arithmetic
def synthetic_ladder(b=0.02, c=2.7, big_ok=False):
    pts = []
    for mode in ("custatevec", "batched"):
        for ch in (476, 952, 1428):
            if ch > 476 and not big_ok:
                pts.append({"mode": mode, "chunk": ch, "error": "out of memory (synthetic)"})
                continue
            t = c + b * ch if mode == "custatevec" else 2 * (c + b * ch)
            pts.append({"mode": mode, "chunk": ch, "gpu_memory_bytes_model": ch / 476 * 8e9, "seconds": t,
                        "seconds_per_shot": t / ch, "success": True})
    return {"points": pts, "fastest_mode": "custatevec", "fastest_chunk": 476}


def test_fit_and_the_prompt_case():
    lad = synthetic_ladder()
    fit = RS.fit_ladder(lad["points"], "custatevec")
    assert fit["single_chunk"] is True, "one chunk size: c cannot be separated"
    lad = synthetic_ladder(big_ok=True)
    fit = RS.fit_ladder(lad["points"], "custatevec")
    assert abs(fit["b_s_per_shot"] - 0.02) < 1e-12 and abs(fit["c_s"] - 2.7) < 1e-9 and fit["residual_rms_s"] < 1e-9
    reff = RS.r_eff(0.02, 2.7, 476)
    assert RS.parts_for(100000, RS.n_max(0.75, reff, 3000.0)) == 2
    assert RS.parts_for(27309, RS.n_max(0.6, reff, 3000.0)) == 1
    # the chunk rule: 476 unless a larger point succeeded at >= 1.6e10 bytes, then the largest
    assert RS.choose_chunk(synthetic_ladder()["points"], "custatevec")["chunk"] == 476
    assert RS.choose_chunk(synthetic_ladder(big_ok=True)["points"], "custatevec")["chunk"] == 1428


@pytest.mark.parametrize("n,chunk,parts", [(67600 // 44, 476, 2), (3125, 476, 2), (1537, 476, 3), (37, 16, 2),
                                           (17600, 476, 4), (1, 476, 2)])
def test_split_parts_concatenate_to_the_unsplit_plan(n, chunk, parts):
    full = SM.chunk_plan(n, chunk)
    rng = SM.split_ranges(n, chunk, parts)
    assert rng[0][0] == 0 and rng[-1][1] == n and all(rng[i][1] == rng[i + 1][0] for i in range(len(rng) - 1))
    cat = [c for a, b in rng for c in SM.part_plan(n, chunk, a, b)]
    assert cat == full
    bounds = [0] + list(np.cumsum([s for _a, s, _i in cat]))
    assert all(SM.rnd(phi * n) in bounds for phi in SM.PHI if SM.rnd(phi * n) > 0)


def test_split_run_respects_n_max():
    plan = {f"c{i}": 1537 for i in range(44)}            # B=1 plan of record ~ 67 600 shots
    sp = RS.split_run(plan, 476, 40000)
    assert sp["parts"] >= 2 and max(sp["part_shots"]) <= 40000 and sum(sp["part_shots"]) == 44 * 1537


def test_build_on_a_synthetic_fcells_a(tmp_path, monkeypatch):
    """The resize script on a synthetic C4_FCELLS_A JSON (b = 0.02, c = 2.7, only the 476 point succeeds):
    every F run sized, B=1 plan runs and the 1e5 quota halves split in 2, B=0 plan runs in 1, slot files written
    with the slot's own seed index, and the script names its input.  Hermetic: the plan tier is read through
    tokens_run.validation_path, which would otherwise find the harvested validation/C4_FCELLS_A.json (its
    plan_tiers put E3 at 0.05, i.e. 193 600 shots for F3_B1); here every token JSON is the synthetic one (no
    plan_tiers -> the default tier 0.15 this test is written for)."""
    from skqd.campaign33 import tokens_run as TR
    monkeypatch.setattr(TR, "validation_path", lambda ctx, tok: str(tmp_path / f"{tok}.json"))
    fa = tmp_path / "C4_FCELLS_A.json"
    json.dump({"status": "PASS", "data": {"ladder": synthetic_ladder(), "cells_dropped": ["E4|NAT-O3"],
                                         "run": {"ci": {"SLURM_JOB_ID": "12345"}}}}, open(fa, "w"))
    out = RS.build(str(fa), str(tmp_path / "absent.json"), dry=False, budget_s=3000.0)
    assert out["fit"]["chunk"] == 476 and "12345" in out["from"]
    assert out["budget"]["N_max"]["s3quota"] == RS.n_max(0.75, RS.r_eff(0.02, 2.7, 476), 3000.0)
    r = out["runs"]
    assert {k: v["parts"] for k, v in r.items() if k.startswith(("F4", "F8"))} == {k: 2 for k in r if k.startswith(("F4", "F8"))}
    assert all(v["parts"] == 2 for k, v in r.items() if k.endswith("_B1") and v["kind"] == "plan")
    assert all(v["parts"] == 1 for k, v in r.items() if k.endswith("_B0") and v["kind"] == "plan")
    files = out["slot_files"]
    assert out["slots_used"] == len(files) <= 20
    for s, d in files.items():
        # prompts/33b R4: frun / cv3 seed from the run's own F token; f-cells (no run) from the slot's own index
        want = TK.token_index(d["token"]) if d["content"] in ("frun", "cv3") else TK.token_index(s)
        assert d["seed_token_index"] == want and d["slot"] == s and d["written_by"] == RS.WRITTEN_BY
    frun = [d for d in files.values() if d["content"] == "frun"]
    assert frun and all(d["part"] >= 2 for d in frun)
    assert any(d["content"] == "fcells" and d["cells"] == [["E4", "NAT-O3"]] for d in files.values())
    written = RS.write(dict(out), str(tmp_path / "sizing.json"), str(tmp_path / "parts"))
    assert len(written) == len(files) and json.load(open(tmp_path / "sizing.json"))["from"] == out["from"]
    # every part's ranges tile the plan exactly
    for run, v in r.items():
        for c, n in v["part_descriptors"][0]["plan_shots_by_circuit"].items():
            rr = [d["ranges_by_circuit"][c] for d in v["part_descriptors"]]
            assert rr[0][0] == 0 and rr[-1][1] == n and all(rr[i][1] == rr[i + 1][0] for i in range(len(rr) - 1))


# --------------------------------------------------------------------------- assembly of parts
@pytest.fixture(scope="module")
def P():
    from skqd.campaign33.analysis import Physics
    return Physics()


def test_parts_reassemble_the_unsplit_prefixes_and_E_tol(P):
    """Synthetic decoded chunks of an unsplit run and of the same run cut in two parts: Prefixes.from_chunks gives
    the unsplit bounds and the same prefix counts at every gate_CV point; E_tol is the unsplit dry run's."""
    from skqd.campaign33 import analysis as A
    rng = np.random.default_rng(7)
    S = P.sector(0)
    ids = ["B0_ref25_k1", "B0_ref25_k2"]
    plan = {"B0_ref25_k1": 37, "B0_ref25_k2": 23}
    unsplit = {}
    for c in ids:
        rows = []
        for a, s, _i in SM.chunk_plan(plan[c], 16):
            pick = rng.choice(S.sector_idx, size=3)
            rows.append({"start": a, "shots": s, "accepted": {str(int(i)): 1 for i in pick}, "rejected": s - 3})
        unsplit[c] = rows
    pre_u = A.Prefixes.from_chunks(P, 0, unsplit)
    parts = []
    for i in range(2):
        part = {}
        for c in ids:
            a, b = SM.split_ranges(plan[c], 16, 2)[i]
            part[c] = [r for r in unsplit[c] if a <= r["start"] < b]
        parts.append(part)
    merged = {c: parts[1][c] + parts[0][c] for c in ids}          # any order: from_chunks sorts by start
    pre_m = A.Prefixes.from_chunks(P, 0, merged)
    assert pre_m.bounds == pre_u.bounds
    for phi in SM.PHI:
        L = {c: SM.rnd(phi * plan[c]) for c in ids}
        nu, su = pre_u.counts(L)
        nm, sm = pre_m.counts(L)
        assert su == sm and np.array_equal(nu, nm)
    with pytest.raises(ValueError):
        A.Prefixes.from_chunks(P, 0, {c: parts[1][c] for c in ids})   # a missing part 1 is a gap, not a prefix
    et = A.e_tol(P, "B=0")
    p = os.path.join(ROOT, "validation", "dryrun", "C4_F4_B0a.json")
    if os.path.exists(p):
        assert json.load(open(p))["data"]["frun"]["E_tol"]["value"] == et["value"]
    assert et["ok"]


def test_dry_part_slot_and_assembly_if_run():
    """The dry C4_PART_01 with a synthetic parts file (prompts/33a D5) and its assembly, when they have been run
    on the laptop: the slot JSON and its content-named copy agree, and the merged run lists its parts and has the
    same bounds as the unsplit plan.  prompts/33b A4: when the dry sizing gave the run a cv3 content of 2 parts
    (C4_PART_02 / 03), both content-named copies PASS and the assembly merged them before reading CV3."""
    sp = os.path.join(ROOT, "validation", "dryrun", "C4_PART_01.json")
    if not os.path.exists(sp):
        pytest.skip("no dry run of C4_PART_01 yet")
    d = json.load(open(sp))
    part = d["data"]["part"]
    run = part["run"]
    copy = os.path.join(ROOT, "validation", "dryrun", f"C33_{run}_part{part['part']}of{part['parts']}.json")
    assert json.load(open(copy)) == d and d["status"] == "PASS"
    assert part["seed_token_index"] == TK.token_index(part["token"]), "R4: the run's own F token seeds the part"
    assert d["data"]["seeds"]["s0"] == TK.base_seed(part["token"])
    cv3 = [os.path.join(ROOT, "validation", "dryrun", f"C33_{run}_cv3_part{i}of2.json") for i in (1, 2)]
    m = os.path.join(ROOT, "validation", "dryrun", f"C33_{run}.json")
    if os.path.exists(m):
        md = json.load(open(m))
        assert md["data"]["parts"] and len(md["data"]["parts"]) == part["parts"]
        for c, n in md["data"]["plan_shots_by_circuit"].items():
            assert md["data"]["bounds"][c] == [0] + list(np.cumsum([s for _a, s, _i in SM.chunk_plan(n, 16)]))
        assert all(c["passed"] for c in md["criteria"] if c["name"].startswith(("every part", "the concatenated")))
        if all(os.path.exists(f) for f in cv3):
            for f in cv3:
                x = json.load(open(f))
                assert x["status"] == "PASS" and x["data"]["cv3"]["full"] and x["data"]["cv3"]["parts"] == 2
                assert x["data"]["seeds"]["s0"] == TK.base_seed("C4_" + run)
            assert md["data"]["cv3_parts"] == 2
            assert md["data"]["frun"]["cv3_status"].startswith("evaluated from"), md["data"]["frun"]["cv3_status"]
            assert all(os.path.relpath(f, ROOT) in md["data"]["cv3_slot"] for f in cv3)


# --------------------------------------------------------------------------- prompts/33b step A
def _cell(b, c=0.4, sizes=(50, 50, 100, 200, 400, 13, 12, 25, 50, 100)):
    """A synthetic f-cell: chunks whose seconds lie exactly on t = c + b n; seconds of the 2 000-shot cell."""
    ch = {"x": [{"start": 0, "shots": n, "seed": 0, "seconds": c + b * n} for n in sizes]}
    return {"chunks": ch, "seconds": 2000 * b + 10 * c, "shots": 2000, "complete": True}


def test_scenario_rates_ratio_rule_on_a_synthetic_fcells_a():
    """prompts/33b A4: two scenarios whose chunk slopes are b and 3b give rho = 1, 3, N_max in the ratio 3 : 1 and
    1 / 3 parts for the same shot count; unmeasured scenarios carry their R2 labels."""
    b = 0.025
    fa = {"data": {"cells": {"E1|NAT-O0": _cell(b), "E3|NAT-O0": _cell(3 * b)}, "run": {"ci": {"SLURM_JOB_ID": "1"}}}}
    fit = {"b_s_per_shot": 0.0245, "c_s": 1.737}
    sr = RS.scenario_rates([("validation/C4_FCELLS_A.json", fa, "1")], fit, 1428,
                           {"s_per_shot": 0.0199, "source": "validation/S3.json data.cost.seconds_per_shot_best_ladder"})
    r = sr["scenario_rates"]
    assert abs(r["E1"]["rho"] - 1.0) < 1e-12 and abs(r["E3"]["rho"] - 3.0) < 1e-12
    assert abs(r["E3"]["s_per_shot"] - 3 * r["E1"]["s_per_shot"]) < 1e-15
    assert abs(r["E1"]["s_per_shot"] - RS.r_eff(0.0245, 1.737, 1428)) < 1e-15
    assert r["E6a"]["label"].startswith("assumed: E1") and r["E7_0.07"]["rho"] == r["E1"]["rho"]
    assert r["E8"]["label"].startswith("upper bound") and "validation/S3.json" in r["E8"]["label"]
    assert r["E2"]["label"].startswith("assumed: E1")
    n1, n3 = (RS.n_max(0.75, r[s]["s_per_shot"]) for s in ("E1", "E3"))
    assert abs(n1 / n3 - 3.0) < 1e-3
    shots = 5 * n3 // 2
    assert RS.parts_for(shots, n1) == 1 and RS.parts_for(shots, n3) == 3
    plan = {f"c{i}": shots // 40 for i in range(40)}
    assert RS.split_run(plan, 476, n1)["parts"] == 1 and RS.split_run(plan, 476, n3)["parts"] == 3
    # E8 measured by C4_FCELLS_B's s3_redo replaces the upper bound
    fb = {"data": {"s3_redo": {"seconds": 63.6, "shots": 3200, "chunk": 476}, "run": {"ci": {"SLURM_JOB_ID": "2"}}}}
    r2 = RS.scenario_rates([("a", fa, "1"), ("validation/C4_FCELLS_B.json", fb, "2")], fit, 1428)["scenario_rates"]
    assert abs(r2["E8"]["s_per_shot"] - 63.6 / 3200) < 1e-15 and "s3_redo" in r2["E8"]["source"]


@pytest.fixture(scope="module")
def real_sizing():
    p = os.path.join(ROOT, "validation", "C4_FCELLS_A.json")
    if not os.path.exists(p):
        pytest.skip("validation/C4_FCELLS_A.json not harvested")
    return RS.build(p, os.path.join(ROOT, "validation", "C4_FCELLS_B_absent_for_this_test.json"), dry=False)


SECTION1_33B = {"F3_B0": 4, "F3_B1": 11, "F6_B0": 3, "F6_B1": 7}
PARTS_33A = {"F1_B0": 1, "F1_B1": 2, "F2_B0": 1, "F2_B1": 2, "F5_B0": 1, "F5_B1": 2, "F7_B0": 1, "F7_B1": 2,
             "F4_B0a": 2, "F4_B0b": 2, "F4_B1a": 2, "F4_B1b": 2, "F8_B0a": 2, "F8_B0b": 2, "F8_B1a": 2, "F8_B1b": 2}


def test_real_fcells_a_reproduces_section_1(real_sizing):
    """prompts/33b section 1 on the harvested C4_FCELLS_A (job 59570315): F3_B0 4, F3_B1 11, F6_B0 3, F6_B1 7 parts,
    every other run as 33a sized it, and every part within its budget (shots x r_s x 1.25 <= share x 2880)."""
    out = real_sizing
    assert out["prompt"] == "prompts/33b"
    r = out["runs"]
    assert {k: r[k]["parts"] for k in SECTION1_33B} == SECTION1_33B
    assert {k: r[k]["parts"] for k in PARTS_33A} == PARTS_33A
    for run, v in r.items():
        for d in v["part_descriptors"]:
            shots = sum(d["shots_by_circuit"].values())
            assert shots * v["rate_s_per_shot"] * RS.CONTINGENCY <= v["share"] * (3000 - RS.SETUP_S) + 1e-9, (run, d["part"])
            assert d["seed_token_index"] == TK.token_index(v["token"])
        # the parts tile the unsplit chunk plan of every circuit, chunk for chunk
        ch = v["part_descriptors"][0]["chunk"]
        for c, n in v["part_descriptors"][0]["plan_shots_by_circuit"].items():
            got = sorted(t for d in v["part_descriptors"] for t in SM.part_plan_ranges(n, ch, d["ranges_by_circuit"][c]))
            assert got == SM.chunk_plan(n, ch), (run, c)
    sr = out["scenario_rates"]
    assert abs(sr["E3"]["rho"] - 2.804) < 5e-4 and abs(sr["E5b"]["rho"] - 5.511) < 5e-4
    assert sr["E1"]["rho"] == 1.0 and sr["E8"]["label"].startswith("upper bound")
    cv = out["cv3"]
    assert cv["F5_B1"]["parts"] == 2 and cv["F1_B1"]["parts"] == 2
    assert cv["F3_B1"]["status"].startswith("not_evaluated: deferred")
    assert len(out["slots"]) <= 20 and all(d["generation"] == 2 for d in out["deferred"])


def test_fcell_packing_of_the_real_dropped_list(real_sizing):
    """prompts/33b R5: the 32 dropped cells of C4_FCELLS_A in 4 slots, the first the 16 cells E1/E2/E3 x {O2, O3,
    O4, O6} + E4 x {O1, O2, O3, O4}, every slot's predicted seconds <= 0.75 x 2880 / 1.25 = 1728."""
    fc = real_sizing["fcells"]
    assert len(fc["slots"]) == 4 and abs(fc["slot_capacity_s"] - 1728.0) < 1e-9
    first = {tuple(c) for c in fc["slots"][0]["cells"]}
    want = {(s, f) for s in ("E1", "E2", "E3") for f in ("NAT-O2", "NAT-O3", "NAT-O4", "NAT-O6")} | \
        {("E4", f) for f in ("NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4")}
    assert first == want and len(fc["slots"][0]["cells"]) == 16
    assert all(s["predicted_s"] <= 1728.0 for s in fc["slots"])
    assert sum(len(s["cells"]) for s in fc["slots"]) == 32
    offs = [s["cell_index_offset"] for s in fc["slots"]]
    assert offs == [0, 16, 22, 27], "global cell offsets: f-cell contents never share a seed on a re-used slot"


def test_generation_1_slot_queue(real_sizing):
    """prompts/33b A1e: the first 20 queue items on C4_PART_01..20 in the prompt's order, the rest deferred."""
    q = [d["copy"] for d in real_sizing["slot_queue"]]
    want = (["C33_F5_B1_part2of2", "C33_F4_B0a_part2of2", "C33_F4_B1a_part2of2", "C33_F4_B0b_part2of2",
             "C33_F4_B1b_part2of2", "C33_F8_B0a_part2of2", "C33_F8_B1a_part2of2", "C33_F8_B0b_part2of2",
             "C33_F8_B1b_part2of2", "C33_F1_B1_part2of2", "C33_F7_B1_part2of2", "C33_F2_B1_part2of2",
             "C33_fcells_part1of4", "C33_F5_B1_cv3_part1of2", "C33_F5_B1_cv3_part2of2", "C33_F1_B1_cv3_part1of2",
             "C33_F1_B1_cv3_part2of2", "C33_F3_B0_part2of4", "C33_F3_B0_part3of4", "C33_F3_B0_part4of4"]
            + [f"C33_F3_B1_part{i}of11" for i in range(2, 12)] + [f"C33_F6_B0_part{i}of3" for i in (2, 3)]
            + [f"C33_F6_B1_part{i}of7" for i in range(2, 8)] + [f"C33_fcells_part{i}of4" for i in (2, 3, 4)]
            + ["C33_F2_B1_cv3_part1of2", "C33_F2_B1_cv3_part2of2"])
    assert q == want
    assert [real_sizing["slots"][s]["copy"] for s in SLOTS] == want[:20]
    assert [d["copy"] for d in real_sizing["deferred"]] == want[20:] and not real_sizing["unassigned"]
    for s, d in real_sizing["slot_files"].items():
        exp = TK.token_index(s) if d["content"] == "fcells" else TK.token_index(d["token"])
        assert d["slot"] == s and d["seed_token_index"] == exp and d["written_by"] == RS.WRITTEN_BY
        assert "C4_FCELLS_A.json job 59570315" in d["from"] and "C4_FCELLS_B" in d["from"]


def test_reassign_frees_only_done_slots_with_their_copy(tmp_path, monkeypatch):
    """prompts/33b R4: --reassign refuses a slot whose ci/status is not done or whose content-named copy is missing,
    gives a free one the next deferred item (its file overwritten) and records slot_history."""
    fa = tmp_path / "C4_FCELLS_A.json"
    json.dump({"status": "PASS", "data": {"ladder": synthetic_ladder(), "cells_dropped": [],
                                         "run": {"ci": {"SLURM_JOB_ID": "12345"}}}}, open(fa, "w"))
    from skqd.campaign33 import tokens_run as TR
    monkeypatch.setattr(TR, "validation_path", lambda ctx, tok: str(tmp_path / f"{tok}.json"))
    sizing, parts, status, val = (tmp_path / "sizing.json", tmp_path / "parts", tmp_path / "status",
                                  tmp_path / "validation")
    status.mkdir()
    val.mkdir()
    # a budget that splits every run in many parts, so that the queue is longer than 20 slots
    args = ["--fcells-a", str(fa), "--fcells-b", str(tmp_path / "none.json"), "--out", str(sizing), "--parts-dir",
            str(parts), "--budget-s", "1200"]
    assert RS.main(args) == 0
    g1 = json.load(open(sizing))
    assert len(g1["deferred"]) >= 3
    held = {s: TR.part_copy_name(json.load(open(parts / f"{s}.json"))) for s in SLOTS}
    # slot 01: done + copy present -> free; 02: done, copy missing; 03: pending, copy present; 04: no status
    json.dump({"state": "done", "jobid": "1"}, open(status / "C4_PART_01.json", "w"))
    json.dump({"status": "PASS"}, open(val / f"{held['C4_PART_01']}.json", "w"))
    json.dump({"state": "done", "jobid": "2"}, open(status / "C4_PART_02.json", "w"))
    json.dump({"state": "pending", "jobid": "3"}, open(status / "C4_PART_03.json", "w"))
    json.dump({"status": "PASS"}, open(val / f"{held['C4_PART_03']}.json", "w"))
    rc = RS.main(args + ["--reassign", "--status-dir", str(status), "--validation-dir", str(val)])
    assert rc == 0
    g2 = json.load(open(sizing))
    first_deferred = g1["deferred"][0]["copy"]
    assert TR.part_copy_name(json.load(open(parts / "C4_PART_01.json"))) == first_deferred
    for s in ("C4_PART_02", "C4_PART_03", "C4_PART_04"):
        assert TR.part_copy_name(json.load(open(parts / f"{s}.json"))) == held[s], s
        assert not g2["reassign"]["slots"][s]["free"]
    assert "missing" in g2["reassign"]["slots"]["C4_PART_02"]["reason"]
    assert "pending" in g2["reassign"]["slots"]["C4_PART_03"]["reason"]
    h = g2["slot_history"]["C4_PART_01"]
    assert [x["copy"] for x in h] == [held["C4_PART_01"], first_deferred] and h[1]["generation"] == 2
    assert [d["copy"] for d in g2["deferred"]] == [d["copy"] for d in g1["deferred"][1:]]
    d1 = json.load(open(parts / "C4_PART_01.json"))
    exp = TK.token_index("C4_PART_01") if d1["content"] == "fcells" else TK.token_index(d1["token"])
    assert d1["slot"] == "C4_PART_01" and d1["seed_token_index"] == exp
    # a plain (generation-1) run is refused once a slot has been re-used
    assert RS.main(args) == 2

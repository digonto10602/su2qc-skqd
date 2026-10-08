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
    bounds = [0] + list(np.cumsum([s for _a, s in cat]))
    assert all(SM.rnd(phi * n) in bounds for phi in SM.PHI if SM.rnd(phi * n) > 0)


def test_split_run_respects_n_max():
    plan = {f"c{i}": 1537 for i in range(44)}            # B=1 plan of record ~ 67 600 shots
    sp = RS.split_run(plan, 476, 40000)
    assert sp["parts"] >= 2 and max(sp["part_shots"]) <= 40000 and sum(sp["part_shots"]) == 44 * 1537


def test_build_on_a_synthetic_fcells_a(tmp_path):
    """The resize script on a synthetic C4_FCELLS_A JSON (b = 0.02, c = 2.7, only the 476 point succeeds):
    every F run sized, B=1 plan runs and the 1e5 quota halves split in 2, B=0 plan runs in 1, slot files written
    with the slot's own seed index, and the script names its input."""
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
        assert d["seed_token_index"] == TK.token_index(s) and d["slot"] == s and d["written_by"] == RS.WRITTEN_BY
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
        for a, s in SM.chunk_plan(plan[c], 16):
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
    same bounds as the unsplit plan."""
    sp = os.path.join(ROOT, "validation", "dryrun", "C4_PART_01.json")
    if not os.path.exists(sp):
        pytest.skip("no dry run of C4_PART_01 yet")
    d = json.load(open(sp))
    part = d["data"]["part"]
    run = part["run"]
    copy = os.path.join(ROOT, "validation", "dryrun", f"C33_{run}_part{part['part']}of{part['parts']}.json")
    assert json.load(open(copy)) == d and d["status"] == "PASS"
    m = os.path.join(ROOT, "validation", "dryrun", f"C33_{run}.json")
    if os.path.exists(m):
        md = json.load(open(m))
        assert md["data"]["parts"] and len(md["data"]["parts"]) == part["parts"]
        for c, n in md["data"]["plan_shots_by_circuit"].items():
            assert md["data"]["bounds"][c] == [0] + list(np.cumsum([s for _a, s in SM.chunk_plan(n, 16)]))
        assert all(c["passed"] for c in md["criteria"] if c["name"].startswith(("every part", "the concatenated")))

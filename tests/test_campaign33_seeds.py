"""
prompts/33b R4 (step A4): the seed rule that makes the C4_PART slots re-usable.

Every part of a split class-4 run -- part 1 on its F token, parts >= 2 on any slot -- seeds from the run's own F
token (s0 = tokens.base_seed(F token)), with the chunk index of the UNSPLIT chunk plan and stride = the sizing's
chunk.  Pinned here:
  * for a run split into n parts (the 33a equal-fraction cut, the round-major cut and the chunk packing of
    prompts/33b), the sorted (circuit, seed, start, shots) over all parts equals the unsplit run's;
  * two parts of one run never share a seed (no overlap of [seed, seed + shots) -- Aer seeds shot j with seed + j);
  * two different runs never share a seed; the cv3 parts (circuit offsets 100 / 200) are disjoint from the plan
    circuits of the same run;
  * end to end through the driver (stub simulator): part 1 on C4_F5_B1 + part 2 on C4_PART_01 sample exactly the
    unsplit run's seeds, the 2-part cv3 content on C4_PART_02 / 03 the unsplit cv3 seeds, P0 refuses a slot file
    written with the slot's own index (the 33a rule), and the assembly merges the cv3 parts before CV3.
"""
import json
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import campaign33_resize as RS  # noqa: E402
from skqd.campaign33 import sampling as SM  # noqa: E402
from skqd.campaign33 import tokens as TK  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class _Res:
    def __init__(self, n):
        self.success, self._n = True, n

    def get_counts(self, i=0):
        return {"0" * 20: self._n}


class RecSim:
    """Records nothing itself; the Sampler records every chunk's seed.  Returns all-zero strings."""

    def run(self, circ, shots, seed_simulator):
        return SimpleNamespace(result=lambda: _Res(int(shots)))


def chunks_of(res):
    return [(r["label"], int(ch["seed"]), int(ch["start"]), int(ch["shots"])) for r in res for ch in r["chunks"]]


def unsplit(plan, chunk, s0, offset=0):
    ids = list(plan)
    res, info = SM.Sampler(RecSim(), s0, chunk).run(ids, [plan[c] for c in ids], ids, offset)
    assert info["stride"] == chunk, "the test plans hold a full chunk, so the unsplit stride is the chunk"
    return chunks_of(res)


def parts(plan, chunk, s0, ranges, offset=0):
    ids = list(plan)
    out = []
    for rr in ranges:
        plans = [SM.part_plan_ranges(plan[c], chunk, rr[c]) for c in ids]
        res, info = SM.Sampler(RecSim(), s0, chunk).run(ids, [SM.range_shots(rr[c]) for c in ids], ids, offset,
                                                        plans=plans, stride=chunk)
        assert info["stride"] == chunk and info["s0"] == s0
        out.append(chunks_of(res))
    return out


def disjoint(chunks):
    """No two chunks' shot-seed intervals [seed, seed + shots) overlap."""
    iv = sorted((s, s + n) for _c, s, _a, n in chunks)
    return all(iv[i][1] <= iv[i + 1][0] for i in range(len(iv) - 1))


PLAN = {"B1_a_k1": 600, "B1_b_k1": 15000, "B1_c_k2": 4400, "B1_d_k4": 3000, "B1_e_k1": 600}
CHUNK = 476


def splits(plan=PLAN, chunk=CHUNK):
    tot = sum(plan.values())
    nmax = tot // 3 + 600
    return {"equal_fraction": RS.equal_fraction_split(plan, chunk, 3),
            "round_major": RS.round_major_split(plan, chunk, nmax),
            "chunk_packing": RS.chunk_packing_split(plan, chunk, nmax),
            "split_run": RS.split_run(plan, chunk, nmax)["ranges"]}


@pytest.mark.parametrize("method", ["equal_fraction", "round_major", "chunk_packing", "split_run"])
def test_parts_reproduce_the_unsplit_run_seed_for_seed(method):
    s0 = TK.base_seed("C4_F6_B1")
    ref = unsplit(PLAN, CHUNK, s0)
    ps = parts(PLAN, CHUNK, s0, splits()[method])
    assert len(ps) >= 2
    assert sorted(x for p in ps for x in p) == sorted(ref)
    seeds = [{s for _c, s, _a, _n in p} for p in ps]
    assert all(not (seeds[i] & seeds[j]) for i in range(len(ps)) for j in range(i + 1, len(ps))), \
        "two parts of one run share a seed"
    assert disjoint([x for p in ps for x in p])


def test_seed_rule_is_independent_of_the_slot():
    """The slot that runs a part plays no role: a part re-run on any slot draws the same seeds (s0 of the F token),
    and the old 33a rule (s0 of the slot, chunk index within the part) would have repeated part 1's stream."""
    s0 = TK.base_seed("C4_F5_B1")
    rr = RS.equal_fraction_split(PLAN, CHUNK, 2)
    a = parts(PLAN, CHUNK, s0, rr)
    b = parts(PLAN, CHUNK, s0, rr)
    assert a == b
    # 33a: both parts on one slot, local chunk indices -> identical seeds for the first chunks of each part
    slot_s0 = TK.base_seed("C4_PART_01")
    old = []
    for p in rr:
        ids = list(PLAN)
        plans = [[(x[0], x[1], j) for j, x in enumerate(SM.part_plan_ranges(PLAN[c], CHUNK, p[c]))] for c in ids]
        res, _ = SM.Sampler(RecSim(), slot_s0, CHUNK).run(ids, [SM.range_shots(p[c]) for c in ids], ids, 0, plans=plans)
        old.append({s for _c, s, _a, _n in chunks_of(res)})
    assert old[0] & old[1], "the 33a rule duplicated streams when two parts of one run shared a slot"


def test_two_runs_never_share_a_seed():
    runs = [("C4_F5_B1", PLAN), ("C4_F1_B1", PLAN), ("C4_F6_B1", {"x_k1": 27400, "y_k1": 600})]
    allc = []
    for tok, plan in runs:
        for p in parts(plan, CHUNK, TK.base_seed(tok), RS.round_major_split(plan, CHUNK, sum(plan.values()) // 3 + 600)):
            allc += p
    assert disjoint(allc)


def test_cv3_parts_are_disjoint_from_the_plan_circuits_of_the_same_run():
    """The cv3 content of a run uses the run's s0 with circuit offsets 100 (k <= 4) / 200 (k = 5), so its parts
    never touch the seeds of the run's plan circuits (offset 0), and its parts reproduce the unsplit cv3 sample."""
    s0 = TK.base_seed("C4_F5_B1")
    n_eq = 8300
    eq = {c: n_eq for c in PLAN}
    k5 = {"B1_a_k5": n_eq, "B1_e_k5": n_eq}
    both = dict(eq, **k5)
    sp = RS.split_run(both, 1428, 30000)            # 58 100 shots at N_max 30 000: >= 2 parts
    assert sp["parts"] >= 2
    cv3 = []
    for rr in sp["ranges"]:
        cv3 += parts(eq, 1428, s0, [{c: rr[c] for c in eq}], offset=100)[0]
        cv3 += parts(k5, 1428, s0, [{c: rr[c] for c in k5}], offset=200)[0]
    ref = unsplit(eq, 1428, s0, 100) + unsplit(k5, 1428, s0, 200)
    assert sorted(cv3) == sorted(ref)
    plan_chunks = [x for p in parts(PLAN, CHUNK, s0, RS.equal_fraction_split(PLAN, CHUNK, 2)) for x in p]
    assert disjoint(plan_chunks + cv3)


def test_real_sizing_unsplit_stride_equals_the_chunk():
    """For every split run of the committed sizing the unsplit plan holds a full chunk, so the R4 stride (the
    sizing's chunk) is also the stride the unsplit run would use: 'seed-identical to the unsplit run' holds with
    either reading."""
    p = os.path.join(ROOT, "data", "campaign33", "sizing_33a.json")
    if not os.path.exists(p):
        pytest.skip("no sizing")
    s = json.load(open(p))
    if s.get("prompt") != "prompts/33b":
        pytest.skip("sizing not yet regenerated under prompts/33b")
    for run, r in s["runs"].items():
        if r["parts"] < 2:
            continue
        d = r["part_descriptors"][0]
        ch = int(d["chunk"])
        big = max(x[1] for n in d["plan_shots_by_circuit"].values() for x in SM.chunk_plan(int(n), ch))
        assert big == ch == d["stride"], run


# --------------------------------------------------------------------------- end to end through the driver
class FakeResult:
    def __init__(self, counts):
        self.success, self._c = True, counts

    def get_counts(self, i=0):
        return self._c


class FakeSim:
    """Seeded strings: half random 20-bit garbage, half codewords (as tests/test_campaign33_paths.py)."""

    def __init__(self, codewords, n_bits=20):
        self.cw, self.n = list(codewords), n_bits

    def run(self, circ, shots, seed_simulator):
        rng = np.random.default_rng(int(seed_simulator) % (2 ** 32))
        out = {}
        for _ in range(int(shots)):
            x = int(rng.choice(self.cw)) if rng.random() < 0.5 else int(rng.integers(0, 2 ** self.n))
            k = format(x, f"0{self.n}b")
            out[k] = out.get(k, 0) + 1
        return SimpleNamespace(result=lambda: FakeResult(out))


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    import campaign33 as C33
    import skqd.report as REP
    from skqd.campaign33 import assemble as AS
    from skqd.campaign33 import tokens_run as TR
    from skqd.campaign33.analysis import Physics
    for sub in ("validation/dryrun", "reports/dryrun"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(REP, "ROOT", str(tmp_path))
    monkeypatch.setattr(C33, "ROOT", str(tmp_path))
    monkeypatch.setattr(AS, "ROOT", str(tmp_path))
    monkeypatch.setattr(TR, "validation_path",
                        lambda ctx, tok: os.path.join(str(tmp_path), "validation", "dryrun" if ctx.dry else "", tok + ".json"))
    P = Physics(with_sectors=False)
    cws = [int(x) for x in P.emb.ints]
    monkeypatch.setattr(TR, "simulator", lambda ctx, nm, mode: (FakeSim(cws), {"stub": True}))
    return tmp_path


def run_dry(token, extra=()):
    import campaign33 as C33
    args = C33.apply_dry_defaults(C33.build_parser({}).parse_args(["--token", token, "--dry-run"] + list(extra)))
    return C33.run_token(args, {})


def test_driver_parts_and_cv3_parts_follow_the_run_token_seed_rule(sandbox, monkeypatch):
    from skqd.campaign33 import assemble as AS
    from skqd.campaign33 import tokens_run as TR
    tmp = sandbox
    fa = tmp / "C4_FCELLS_A.json"
    json.dump({"data": {"ladder": {"points": [{"mode": "cpu", "chunk": 16, "seconds": 16.0, "success": True,
                                               "gpu_memory_bytes_model": 2.7e8}], "fastest_mode": "cpu"},
                        "cells_dropped": [], "run": {"ci": {}}}}, open(fa, "w"))
    out = RS.build(str(fa), str(tmp / "none.json"), dry=True, force_parts=2, runs_only=["F5_B1"])
    sizing = tmp / "sizing_33a.json"
    RS.write(out, str(sizing), str(tmp / "parts"))
    monkeypatch.setattr(TR, "sizing_path", lambda dry: str(sizing))
    sl = out["slots"]
    assert (sl["C4_PART_01"]["copy"], sl["C4_PART_02"]["copy"], sl["C4_PART_03"]["copy"]) == \
        ("C33_F5_B1_part2of2", "C33_F5_B1_cv3_part1of2", "C33_F5_B1_cv3_part2of2")
    s0 = TK.base_seed("C4_F5_B1")
    for s in ("C4_PART_01", "C4_PART_02", "C4_PART_03"):
        assert out["slot_files"][s]["seed_token_index"] == TK.token_index("C4_F5_B1")
    assert run_dry("C4_F5_B1") == 0
    rcs = [run_dry(s, ["--parts-file", str(tmp / "parts" / f"{s}.json")]) for s in ("C4_PART_01", "C4_PART_02",
                                                                                  "C4_PART_03")]
    vd = tmp / "validation" / "dryrun"
    js = {s: json.load(open(vd / f"{s}.json")) for s in ("C4_F5_B1", "C4_PART_01", "C4_PART_02", "C4_PART_03")}
    assert rcs == [0, 0, 0], {s: [c for c in d["criteria"] if not c["passed"]] for s, d in js.items()}
    # ---- the plan parts: exactly the unsplit run's seeds (F-token s0, global chunk index, stride = chunk)
    d1 = out["runs"]["F5_B1"]["part_descriptors"][0]
    plan, ch = d1["plan_shots_by_circuit"], d1["chunk"]
    want = sorted((c, TK.chunk_seed(s0, k, j, ch)) for k, c in enumerate(plan) for (_a, _s, j) in SM.chunk_plan(plan[c], ch))
    got = sorted((c, x["seed"]) for t in ("C4_F5_B1", "C4_PART_01") for c, v in js[t]["data"]["frun"]["chunks"].items()
                 for x in v)
    assert got == want
    assert js["C4_PART_01"]["data"]["seeds"]["s0"] == s0 != TK.base_seed("C4_PART_01")
    # ---- the cv3 parts: the unsplit cv3 seeds (offsets 100 / 200, the same s0)
    e = out["cv3"]["F5_B1"]
    cd = e["part_descriptors"][0]
    n_eq = cd["N_eq"]
    want3 = sorted([(c, TK.chunk_seed(s0, 100 + k, j, ch)) for k, c in enumerate(plan)
                    for (_a, _s, j) in SM.chunk_plan(n_eq, ch)]
                   + [(c, TK.chunk_seed(s0, 200 + k, j, ch)) for k, c in enumerate(cd["k5_circuits"])
                      for (_a, _s, j) in SM.chunk_plan(n_eq, ch)])
    got3 = sorted((c, x["seed"]) for t in ("C4_PART_02", "C4_PART_03") for c, v in js[t]["data"]["cv3"]["chunks"].items()
                  for x in v)
    assert got3 == want3
    for t in ("C4_PART_02", "C4_PART_03"):
        assert js[t]["data"]["cv3"]["full"] and js[t]["data"]["seeds"]["s0"] == s0
    assert (vd / "C33_F5_B1_cv3_part1of2.json").exists() and (vd / "C33_F5_B1_cv3_part2of2.json").exists()
    # ---- the assembly merges the plan parts and the cv3 parts
    split, _P = AS.assemble_split_runs(True)
    assert split["F5_B1"]["status"] == "PASS", split
    m = json.load(open(vd / "C33_F5_B1.json"))
    assert m["data"]["cv3_parts"] == 2 and m["data"]["frun"]["cv3_status"].startswith("evaluated from")
    assert m["data"]["frun"]["cv"] is not None, "CV0-CV5 read on the merged run with the merged cv3 sample"
    # ---- P0 refuses a slot file written under the 33a rule (seed_token_index = the slot's own index)
    bad = dict(out["slot_files"]["C4_PART_01"], seed_token_index=TK.token_index("C4_PART_01"))
    json.dump(bad, open(tmp / "bad.json", "w"))
    assert run_dry("C4_PART_01", ["--parts-file", str(tmp / "bad.json")]) == 1
    d = json.load(open(vd / "C4_PART_01.json"))
    assert any(c["name"].startswith("P0 ") and not c["passed"] for c in d["criteria"])

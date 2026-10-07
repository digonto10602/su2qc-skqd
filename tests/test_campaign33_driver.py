"""
prompts/33 A4: the campaign driver (scripts/campaign33.py + src/skqd/campaign33/sampling.py).

Pinned here, as tests/test_s3_ci_mode.py does for gate S3: the CI defaults of every token (GPU, a budget
inside run_gate.py's 3600 s timeout and 10 minutes below the token's walltime, the 476-shot chunk, 2000
bootstrap resamples), that explicit arguments win, the dry-run defaults, the chunk plan (exact prefixes at
the gate_CV points), disjoint seeds, an out-of-memory split that keeps the shot stream, and that a budget
overrun REDUCES shots at a round boundary instead of running past the walltime.  The GPU lines run only
on Perlmutter; here a stub simulator stands in for Aer.
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import campaign33 as C33  # noqa: E402
from skqd.campaign33 import sampling as SM  # noqa: E402
from skqd.campaign33 import tokens as TK  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOKENS = list(TK.load_tokens())


@pytest.mark.parametrize("tok", TOKENS)
def test_ci_defaults_per_token(tok):
    a = C33.build_parser({"CI_GATE": tok}).parse_args(["--token", tok])
    wall = TK.walltime_seconds(TK.load_tokens()[tok]["walltime"])
    assert a.device == "GPU" and a.max_shots_per_run == C33.CI_CHUNK == 476 and a.bootstrap == 2000
    assert 0 < a.budget_minutes <= 50, "run_gate.py kills a gate at 3600 s"
    assert a.budget_minutes * 60 + 600 <= wall, "10 minutes below the allowlist walltime"
    assert a.shots_scale == 1.0 and not a.dry_run


def test_laptop_defaults_without_the_ci():
    a = C33.build_parser({}).parse_args(["--token", "C4_F1_B0"])
    assert a.device == "auto" and a.budget_minutes == 0.0 and a.max_shots_per_run == 0 and a.shots_scale == 1.0


def test_explicit_arguments_win_over_the_ci_defaults():
    a = C33.build_parser({"CI_GATE": "C4_F1_B0"}).parse_args(
        ["--token", "C4_F1_B0", "--budget-minutes", "5", "--device", "CPU", "--max-shots-per-run", "64"])
    assert (a.budget_minutes, a.device, a.max_shots_per_run) == (5.0, "CPU", 64)
    assert a.bootstrap == 2000, "the remaining CI defaults still apply"


def test_dry_run_defaults():
    a = C33.apply_dry_defaults(C33.build_parser({}).parse_args(["--token", "C2_CAL", "--dry-run"]))
    assert (a.shots_scale, a.max_shots_per_run, a.device) == (0.01, 16, "CPU")
    assert a.budget_minutes <= 10, "every dry run <= 10 min (prompts/33 A4)"
    b = C33.apply_dry_defaults(C33.build_parser({}).parse_args(["--token", "C2_CAL", "--dry-run", "--shots-scale", "0.02"]))
    assert b.shots_scale == 0.02, "explicit values win over the dry-run table"


def test_chunk_plan_has_the_gate_cv_prefixes_and_the_bound():
    for n in (1, 2, 17, 267, 1367, 17600, 41200):
        for m in (16, 476):
            plan = SM.chunk_plan(n, m)
            assert sum(s for _a, s in plan) == n and all(1 <= s <= m for _a, s in plan)
            ends = {a + s for a, s in plan}
            for phi in SM.PHI:
                L = SM.rnd(phi * n)
                assert L == 0 or L in ends, (n, m, phi)
            starts = [a for a, _s in plan]
            assert starts == sorted(starts) and starts[0] == 0


class StubResult:
    def __init__(self, shots, fail=False):
        self.success = True
        self._shots = shots

    def get_counts(self, i):
        return {"0" * 20: self._shots}


class StubSim:
    """Records (shots, seed) of every run(); raises an Aer-style OOM above `oom_above` shots."""

    def __init__(self, oom_above=None, delay=0.0):
        self.calls, self.oom_above, self.delay = [], oom_above, delay

    def run(self, circ, shots, seed_simulator):
        if self.oom_above is not None and shots > self.oom_above:
            raise RuntimeError("ERROR: std::bad_alloc: cudaErrorMemoryAllocation: out of memory")
        self.calls.append((circ, int(shots), int(seed_simulator)))
        time.sleep(self.delay)
        return type("J", (), {"result": lambda s, n=shots: StubResult(n)})()


def test_sampler_seeds_are_disjoint_and_recorded():
    sim = StubSim()
    s = SM.Sampler(sim, s0=TK.base_seed("C4_F1_B0"), max_chunk=476)
    res, info = s.run(["c0", "c1", "c2"], [267, 1367, 9000], ["a", "b", "c"])
    ranges = sorted((seed, seed + shots) for _c, shots, seed in sim.calls)
    assert all(ranges[i][1] <= ranges[i + 1][0] for i in range(len(ranges) - 1)), "no shot stream shared"
    assert all(len(r["chunks"]) and all("seed" in ch for ch in r["chunks"]) for r in res)
    assert [r["shots_done"] for r in res] == [267, 1367, 9000]
    assert info["stopped"] is None and info["calls"] == len(sim.calls)


def test_oom_split_keeps_the_shot_stream():
    sim = StubSim(oom_above=100)
    s = SM.Sampler(sim, s0=33_000_000, max_chunk=476)
    res, info = s.run(["c0"], [300], ["a"])
    assert res[0]["shots_done"] == 300 and info["oom_retries"]
    first = res[0]["chunks"][0]
    seeds = [seed for _c, shots, seed in sim.calls]
    # the chunk's shots ran as consecutive sub-calls seeded seed, seed + a, ...: one unbroken stream
    run = sorted((seed, shots) for _c, shots, seed in sim.calls if first["seed"] <= seed < first["seed"] + first["shots"])
    pos = first["seed"]
    for seed, shots in run:
        assert seed == pos
        pos += shots
    assert pos == first["seed"] + first["shots"]
    assert all("split" in o for o in info["oom_retries"]), "every OOM retry recorded"
    assert len(set(seeds)) == len(seeds)


def test_a_budget_overrun_reduces_shots_at_a_round_boundary():
    sim = StubSim(delay=0.01)
    s = SM.Sampler(sim, s0=33_000_000, max_chunk=16, deadline=time.time() + 0.05)
    res, info = s.run(["c0", "c1"], [400, 400], ["a", "b"])
    assert info["stopped"] is not None and info["stopped"]["reason"] == "deadline"
    done = [r["shots_done"] for r in res]
    assert all(d < 400 for d in done), "shots reduced, not the walltime exceeded"
    # every circuit holds a complete prefix: chunk starts are contiguous from 0
    for r in res:
        pos = 0
        for ch in r["chunks"]:
            assert ch["start"] == pos
            pos += ch["shots"]
        assert pos == r["shots_done"]


def test_f_token_parsing_and_family_rules():
    from skqd.campaign33 import tokens_run as TR
    assert TR.parse_f_token("C4_F4_B0a") == ("F4", 0, "a")
    assert TR.parse_f_token("C4_F1_B1") == ("F1", 2, None)
    assert set(TR.F_SPECS) == {f"F{i}" for i in range(1, 9)}
    assert TR.F_SPECS["F5"][3] == 0.10 and TR.F_SPECS["F5"][0] == "E7_0.07"


@pytest.mark.parametrize("tok", TOKENS)
def test_dry_run_json_exists_and_passes_its_structural_criteria(tok):
    p = os.path.join(ROOT, "validation", "dryrun", tok + ".json")
    if not os.path.exists(p):
        pytest.skip(f"no dry run of {tok} yet")
    d = json.load(open(p))
    assert d["data"]["dry_run"] is True and d["data"]["token"] == tok
    names = [c["name"] for c in d["criteria"]]
    assert all(any(n.startswith(f"S{i} ") for n in names) for i in range(1, 7)), "S1-S6 present"
    if d["data"].get("dropped"):
        # an engine token whose engine cannot be set up (data/campaign33/engines.json: drop) records the
        # reason and fails S1 honestly; its job is never requested
        assert d["data"]["engines_json_decision"]["decision"] == "drop"
        failed = [c["name"] for c in d["criteria"] if not c["passed"]]
        assert d["status"] == "FAIL" and len(failed) == 1 and failed[0].startswith("S1 ")
    else:
        assert d["status"] == "PASS", [c for c in d["criteria"] if not c["passed"]]
    assert d["data"]["run"]["wall_seconds"] <= 600, "every dry run <= 10 min"


def test_dry_run_assembly_skeleton():
    """prompts/33 A7 done-check: assembly on the dry-run JSONs gives the full report skeleton with banners."""
    p = os.path.join(ROOT, "validation", "dryrun", "C33_campaign.json")
    if not os.path.exists(p):
        pytest.skip("the dry-run assembly has not been run")
    d = json.load(open(p))
    assert d["data"]["dry_run"] is True and len(d["data"]["tokens"]) == 33
    assert len(d["data"]["comparison"]) >= 10 and d["data"]["matrix"]
    assert set(d["data"]["merged_s3_quota"]) == {"F4|B=0", "F4|B=1", "F8|B=0", "F8|B=1"}
    txt = open(os.path.join(ROOT, "reports", "dryrun", "C33_campaign_report.md")).read()
    assert "DRY RUN SKELETON" in txt and "## Comparison with the earlier 2x3 results" in txt

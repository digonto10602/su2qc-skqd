"""
prompts/33e R1-R3: C2_KCHK run 2 (`--content cpu_only`, the default) -- the run-1 archive (byte-identical, sha256),
its GPU arms read as evidence of record, the 128-shot RM anchor, the CPU process with --chunk 1 --min-shots 8 and
Kraus : RM = 1 : 2, K1-K3 on run 1's GPU arms + run 2's CPU arms, K4 against the laptop CPU reference; the CPU
affinity clause of S3; the c33c_diag summary with two GPU sources.  Stub simulator and a fake CPU process, as in
tests/test_campaign33_kchk.py (a real 21-qubit Kraus shot costs minutes on the laptop CPU).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

from test_campaign33_paths import (C33, ROOT, FakeSim, N, SM, TK, TR, fake_spec, run_dry,  # noqa: E402,F401
                                   sandbox)


def _structure(w, n, p1=0.37, sd=2.5):
    return {"shots": n, "n_bits": 20, "mean_hamming_weight": w, "sd_hamming_weight": sd,
            "se_mean_hamming_weight": sd / n ** 0.5, "marginals_by_clbit": [p1] * 20,
            "se_marginals_by_clbit": [(p1 * (1 - p1) / n) ** 0.5] * 20}


# ----------------------------------------------------------------------------------------------- constants and rules
def test_run2_design_is_the_prompts():
    assert TR.KCHK_DEFAULT_CONTENT == "cpu_only" and set(TR.KCHK_CONTENTS) == {"full", "cpu_only"}
    assert TR.KCHK_RUN2_CPU == {"chunk": 1, "min": 8, "ratio": (1, 2)}, "33e R1/R2: --chunk 1 --min-shots 8, RM:Kraus 2:1"
    assert TR.KCHK_RUN2_WINDOW_SHARE == 0.9
    assert TR.KCHK_ANCHOR[:4] == ("rm_gpu_cusv_anchor", "rm", "custatevec", 128), "33e R2: rm_gpu_cusv at 128 shots"
    used = {TR.KCHK_SEED_OFFSET + i for i in range(len(TR.KCHK_GPU_ARMS))} | {TR.KCHK_SEED_OFFSET + 10,
                                                                              TR.KCHK_SEED_OFFSET + 11}
    assert TR.KCHK_ANCHOR_OFFSET not in used, "the anchor draws its own seed stream"
    assert TK.token_index("C2_KCHK") == 53, "campaign-33 token indices unchanged"


def test_run1_archive_is_the_harvested_bytes_and_its_gpu_arms_recompute():
    arch = TR.kchk_run1_archive()
    assert arch["ok"] and arch["sha256"] == TR.KCHK_RUN1_SHA256, arch["reason"]
    clb = arch["doc"]["data"]["arms"]["kraus_gpu_cusv"]["structure"]["physical_by_clbit"]
    g = TR.kchk_run1_gpu_arms(arch["doc"], clb)
    assert list(g) == list(TR.KCHK_GPU_ARM_NAMES)
    assert [g[a]["shots_done"] for a in g] == [256, 512, 256, 128]
    for a, v in g.items():
        assert v["raw_counts_sum"] == v["shots_done"] and v["structure_recomputed_max_abs_diff"] <= 1e-12, a


def test_kchk_cpu_pattern_and_the_alternation(tmp_path, monkeypatch):
    """kchk_cpu with --ratio 1,2 --chunk 1: kraus, rm, rm, kraus, ...; every chunk is one shot with its own seed."""
    from skqd.campaign33 import circuits as C
    from skqd.campaign33 import kchk_cpu as K
    assert K.pattern(["kraus_cpu", "rm_cpu"], [1, 2]) == ["kraus_cpu", "rm_cpu", "rm_cpu"]
    assert K.pattern(["kraus_cpu", "rm_cpu"], [1, 1]) == ["kraus_cpu", "rm_cpu"]
    monkeypatch.setattr(TR, "load_record", lambda: {"fingerprint": "x"})
    monkeypatch.setattr(C, "load_circuit", lambda fam, cid: None)
    monkeypatch.setattr(N, "ibm_spec", lambda rec, cell, rep, conv="echo", *a, **k: fake_spec(rep))
    monkeypatch.setattr(SM, "make_simulator", lambda *a, **k: (FakeSim([0, 1, 3]), {"stub": True}))
    out = tmp_path / "cpu.json"
    rc = K.main(["--out", str(out), "--deadline", "1e12", "--s0", "38300000", "--offsets", "610,611", "--chunk", "1",
                 "--min-shots", "2", "--max-shots", "3", "--ratio", "1,2", "--threads", "1"])
    d = json.load(open(out))
    assert rc == 0 and d["status"] == "done"
    assert d["sequence"][:3] == ["kraus_cpu", "rm_cpu", "rm_cpu"] and d["cycle"] == ["kraus_cpu", "rm_cpu", "rm_cpu"]
    assert d["sequence"] == ["kraus_cpu", "rm_cpu", "rm_cpu", "kraus_cpu", "rm_cpu", "kraus_cpu"]
    for arm in ("kraus_cpu", "rm_cpu"):
        a = d["arms"][arm]
        assert a["shots_done"] == 3 and all(c["shots"] == 1 for c in a["chunks"])
    seeds = [c["seed"] for a in d["arms"].values() for c in a["chunks"]]
    assert len(seeds) == len(set(seeds))
    assert d["cpu_affinity"] == len(os.sched_getaffinity(0)) and "aer" in d


def test_k4_rules():
    lap = {"present": True, "path": "x", "arms": {"cpu_kraus": {**_structure(7.47, 64), "structure": _structure(7.47, 64)},
                                                  "cpu_rm": {**_structure(7.0, 64), "structure": _structure(7.0, 64)}}}
    ci = {"kraus_cpu": _structure(7.3, 40), "rm_cpu": _structure(7.2, 80)}
    k = TR.kchk_k4(ci, lap)
    assert k["evaluated"] and k["status"] == "agree" and not k["stop_planner"]
    assert "marginals_information" in k["per_representation"]["kraus_cpu"]
    ci["kraus_cpu"] = _structure(3.0, 40)
    k = TR.kchk_k4(ci, lap)
    assert k["status"] == "disagree" and k["stop_planner"], "a disagreement is a STOP for the planner"
    k = TR.kchk_k4(ci, {"present": False, "path": "data/campaign33/c33c_diag/summary.json"})
    assert not k["evaluated"] and k["status"] == "not_evaluated" and not k["stop_planner"]


def test_cpu_affinity_clause_of_s3():
    from skqd.hpc import cpu_affinity, cpu_affinity_check
    assert cpu_affinity() == len(os.sched_getaffinity(0))
    assert cpu_affinity_check(32, 32, True)["ok"]
    assert not cpu_affinity_check(1, 32, True)["ok"], "job 59780907: 1 CPU of 32 -> S3 FAIL on the CI"
    assert not cpu_affinity_check(32, None, True)["ok"], "unverifiable on the CI -> FAIL"
    assert cpu_affinity_check(12, None, False)["ok"], "the laptop: recorded only"


# ----------------------------------------------------------------------------------------------- the driver path
class _FakeCPUProcess:
    """Writes what kchk_cpu would: n_kraus / n_rm one-shot chunks with the token's seeds."""

    def __init__(self, cmd, n_kraus, n_rm, cws, seen, **kw):
        seen["cmd"] = cmd
        out = cmd[cmd.index("--out") + 1]
        s0 = int(cmd[cmd.index("--s0") + 1])
        offs = [int(x) for x in cmd[cmd.index("--offsets") + 1].split(",")]
        arms = {}
        for (arm, rep), off, n in zip(TR.KCHK_CPU_ARMS, offs, (n_kraus, n_rm)):
            chunks = []
            for j in range(n):
                seed = TK.chunk_seed(s0, off, j, 1)
                c = SM.counts_to_int(FakeSim(cws).run(None, 1, seed).result().get_counts())
                chunks.append({"index": j, "seed": seed, "shots": 1, "start": j, "seconds": 0.1,
                               "counts": {str(k): v for k, v in c.items()}})
            arms[arm] = {"representation": rep, "planned_representation": rep, "engine": "fake CPU process",
                         "chunks": chunks, "shots_done": n, "stopped": "deadline"}
        with open(out, "w") as fh:
            json.dump({"pid": 1, "threads": 8, "cpu_affinity": 12, "ratio": {"kraus_cpu": 1, "rm_cpu": 2},
                       "cycle": ["kraus_cpu", "rm_cpu", "rm_cpu"], "sequence": [], "status": "done", "arms": arms,
                       "aer": {"distributions": ["qiskit-aer"]}}, fh)
        self.pid, self.returncode = 1, 0

    def communicate(self, timeout=None):
        return "", None

    def kill(self):
        pass


def _patch(monkeypatch, n_kraus, n_rm, seen):
    monkeypatch.setattr(N, "ibm_spec", lambda rec, cell, rep, conv="echo", *a, **k: fake_spec(rep))
    from skqd.campaign33.analysis import Physics
    cws = [int(x) for x in Physics(with_sectors=False).emb.ints]
    monkeypatch.setattr(SM, "make_simulator", lambda *a, **k: (FakeSim(cws), {"stub": True}))
    real = subprocess.Popen

    def popen(cmd, **kw):
        if "skqd.campaign33.kchk_cpu" not in cmd:
            return real(cmd, **kw)
        return _FakeCPUProcess(cmd, n_kraus, n_rm, cws, seen)
    monkeypatch.setattr(subprocess, "Popen", popen)


def test_run2_dry_path(sandbox, monkeypatch):  # noqa: F811
    tmp, _ = sandbox
    seen = {}
    _patch(monkeypatch, 2, 2, seen)
    rc = run_dry("C2_KCHK")                 # the default content is run 2
    d = json.load(open(tmp / "validation" / "dryrun" / "C2_KCHK.json"))
    assert rc == 0 and d["status"] == "PASS", [c for c in d["criteria"] if not c["passed"]]
    D = d["data"]
    assert D["calibration_run"] == 2 == D["run"]["calibration_run"] and D["kchk_content"] == "cpu_only"
    assert D["supersedes"]["sha256"] == TR.KCHK_RUN1_SHA256 and D["supersedes"]["job"] == "59780907"
    assert D["supersedes"]["archived"] == "validation/archive/C2_KCHK_job59780907.json"
    assert D["supersedes_decision_of"]["job"] == "59736871"
    assert set(D["arms"]) == {"rm_gpu_cusv_anchor", "kraus_cpu", "rm_cpu"}
    assert set(D["run1_gpu_arms"]) == set(TR.KCHK_GPU_ARM_NAMES)
    for a, v in D["arms"].items():
        assert v["raw_counts"]["sum_counts"] == v["shots_done"] > 0, a
    cmd = seen["cmd"]
    for flag, val in (("--chunk", "1"), ("--min-shots", "2"), ("--ratio", "1,2"), ("--max-shots", "2")):
        assert cmd[cmd.index(flag) + 1] == val, flag
    assert "--stand-in" in cmd
    dec = D["decision"]
    assert dec["production_representation"] in ("rm", "blocked") and D["bug_confirmed"] in (True, False)
    assert dec["validated_kraus_gpu_path"] in ("kraus_gpu_native", "kraus_gpu_cusv_nofusion", "none")
    assert dec["evidence"]["gpu_arms"].startswith("run 1, job 59780907")
    assert dec["production_seconds_per_shot"] == D["run1_gpu_arms"]["rm_gpu_cusv"]["seconds_per_shot"]
    assert D["k4"]["status"] in ("agree", "disagree", "partial", "not_evaluated")
    assert D["laptop_reference"]["present"] == os.path.exists(os.path.join(ROOT, TR.KCHK_LAPTOP_SUMMARY))
    names = [x["name"] for x in D["physics_criteria_information_dry_run"]]
    for k in ("K1 ", "K2 ", "K3 ", "K4 "):
        assert any(n.startswith(k) for n in names), k
    crit = {c["name"].split()[0]: c for c in d["criteria"]}
    assert crit["P0a"]["passed"] and crit["P0b"]["passed"] and crit["P0"]["passed"]
    assert D["run"]["cpu_affinity"] == len(os.sched_getaffinity(0))
    assert D["run"]["cpu_affinity_check"]["applies"] is False


def test_run2_real_command_and_minimums(sandbox, monkeypatch):  # noqa: F811
    """Not a dry run (stub simulator, fake CPU process): the CPU command is --chunk 1 --min-shots 8 --ratio 1,2 on
    the step's CPUs minus 4 with no stand-in; the anchor draws 128 shots; S6 needs >= 8 shots per CPU arm."""
    tmp, _ = sandbox
    seen = {}
    _patch(monkeypatch, 8, 16, seen)
    args = C33.build_parser({}).parse_args(["--token", "C2_KCHK", "--device", "CPU", "--budget-minutes", "5"])
    rc = C33.run_token(C33.apply_dry_defaults(args), {})
    d = json.load(open(tmp / "validation" / "C2_KCHK.json"))
    assert rc == 0 and d["status"] == "PASS", [c for c in d["criteria"] if not c["passed"]]
    cmd = seen["cmd"]
    for flag, val in (("--chunk", "1"), ("--min-shots", "8"), ("--ratio", "1,2"),
                      ("--threads", str(max(1, len(os.sched_getaffinity(0)) - 4)))):
        assert cmd[cmd.index(flag) + 1] == val, flag
    assert "--stand-in" not in cmd and "--max-shots" not in cmd
    D = d["data"]
    assert D["arms"]["rm_gpu_cusv_anchor"]["shots_done"] == 128
    assert [D["arms"][a]["shots_done"] for a in ("kraus_cpu", "rm_cpu")] == [8, 16]
    assert D["minimum_shots"]["kraus_cpu"] == [8, 8]
    assert D["decision"]["k1_evaluated"] and D["decision"]["k2_evaluated"]
    # one shot short of the minimum -> S6 FAIL with the reduction recorded
    seen.clear()
    _patch(monkeypatch, 7, 16, seen)
    rc = C33.run_token(C33.apply_dry_defaults(C33.build_parser({}).parse_args(
        ["--token", "C2_KCHK", "--device", "CPU", "--budget-minutes", "5"])), {})
    d = json.load(open(tmp / "validation" / "C2_KCHK.json"))
    s6 = [c for c in d["criteria"] if c["name"].startswith("S6")][0]
    assert rc == 1 and not s6["passed"] and d["data"]["minimum_shots"]["kraus_cpu"] == [7, 8]


def test_run2_refuses_without_the_archive(sandbox, monkeypatch):  # noqa: F811
    tmp, _ = sandbox
    seen = {}
    _patch(monkeypatch, 2, 2, seen)
    monkeypatch.setattr(TR, "KCHK_RUN1_SHA256", "0" * 64)       # as if the archive had been edited
    rc = run_dry("C2_KCHK")
    d = json.load(open(tmp / "validation" / "dryrun" / "C2_KCHK.json"))
    assert rc == 1 and d["status"] == "FAIL" and "cmd" not in seen, "nothing is sampled"
    assert not [c for c in d["criteria"] if c["name"].startswith("P0a")][0]["passed"]


# ----------------------------------------------------------------------------------------------- the laptop summary
def test_c33c_summary_with_two_gpu_sources(tmp_path, monkeypatch):
    import c33c_diag_full as DG
    from skqd.campaign33 import stats as ST
    arch = json.load(open(os.path.join(ROOT, TR.KCHK_RUN1_ARCHIVE)))
    clb = arch["data"]["arms"]["kraus_gpu_cusv"]["structure"]["physical_by_clbit"]
    monkeypatch.setattr(DG, "OUT_DIR", str(tmp_path))

    def seg(name, rep, seed0, counts, secs):
        st = ST.garbage_structure(counts, 20, clb)
        n = sum(counts.values())
        doc = {"git_commit": "abc1234", "command": f"python scripts/c33c_diag_full.py --rep {rep} --threads 10",
               "versions": {"qiskit": "1.4.3", "qiskit_aer": "0.15.1"}, "machine": {}, "created": "t",
               "plan": {"seed0": seed0, "shots_per_call": n}, "status": "done", "stop": "x",
               "calls": [{"index": 0, "seed": seed0, "shots": n, "seconds": secs}],
               "counts": {str(k): v for k, v in counts.items()}, "structure": st}
        (tmp_path / name).write_text(json.dumps(doc))
    seg("full_IBM-T0_B0_ref117_k1_kraus_cpu.json", "kraus", 33033000, {0b1111111: 20}, 100.0)
    seg("full_IBM-T0_B0_ref117_k1_kraus_cpu_seg4.json", "kraus", 33433000, {0b11: 40}, 400.0)   # w = 2: outside
    seg("full_IBM-T0_B0_ref117_k1_rm_cpu.json", "rm", 33033000, {0b1111111: 10, 0b11111111: 10}, 50.0)
    seg("full_IBM-T0_B0_ref117_k1_kraus_cpu_seg5.json", "kraus", 33533000, {0: 2}, 10.0)
    d5 = json.loads((tmp_path / "full_IBM-T0_B0_ref117_k1_kraus_cpu_seg5.json").read_text())
    d5["status"] = "running"                                      # a segment still sampling is never merged
    (tmp_path / "full_IBM-T0_B0_ref117_k1_kraus_cpu_seg5.json").write_text(json.dumps(d5))
    DG.main(["--summarize", "--gpu-source", "validation/C2_CAL.json", "--gpu-source", TR.KCHK_RUN1_ARCHIVE,
             "--kchk-run2", str(tmp_path / "absent.json")])
    s = json.load(open(tmp_path / "summary.json"))
    assert set(s["gpu_sources"]) == {"C2_CAL_job59736871", "C2_KCHK_job59780907"}
    assert s["gpu_sources"]["C2_KCHK_job59780907"]["sha256"] == TR.KCHK_RUN1_SHA256
    assert "gpu:C2_KCHK_job59780907:kraus_gpu_cusv" in s["arms"] and "gpu:C2_CAL_job59736871:rm" in s["arms"]
    assert not any(k.endswith(("kraus_cpu", "rm_cpu")) for k in s["arms"] if k.startswith("gpu:")), "CPU arms are not GPU"
    assert "cpu_kraus_vs_gpu:C2_KCHK_job59780907:kraus_gpu_native" in s["comparisons"]
    assert s["arms"]["cpu_kraus"]["shots"] == 60 and s["arms"]["cpu_kraus"]["structure"]["marginals_by_clbit"]
    assert [os.path.basename(p) for p in s["segments_excluded_running"]["kraus"]] == [
        "full_IBM-T0_B0_ref117_k1_kraus_cpu_seg5.json"]
    rows = s["segments"]["kraus"]
    assert [r["shots"] for r in rows] == [20, 40] and [r["prompt_33e"] for r in rows] == [False, True]
    assert rows[1]["threads"] == 10 and rows[1]["seconds_per_shot"] == 10.0
    assert s["stop_33e"]["kraus"]["evaluated"] and s["stop_33e"]["kraus"]["stop"], "w = 2 at 40 shots: STOP"
    assert not s["stop_33e"]["rm"]["evaluated"]
    assert s["k4"]["status"] == "not_evaluated"


def test_s3_fails_on_the_ci_when_the_step_affinity_is_not_the_allocation(sandbox, monkeypatch):  # noqa: F811
    """finish() under a CI context: S3 PASSes only when run.cpu_affinity == SLURM_CPUS_PER_TASK (telemetry stubbed
    non-null; S1 fails on this GPU-less laptop and is not what is tested here)."""
    tmp, _ = sandbox
    monkeypatch.setattr(C33, "gpu_telemetry", lambda: {"source": "stub", "samples": 1, "peak_memory_mib": 1.0,
                                                       "mean_utilization_pct": 1.0, "max_utilization_pct": 1.0})
    monkeypatch.setattr(C33, "gpu_count", lambda layout: 1)
    aff = len(os.sched_getaffinity(0))
    for cpt, ok in ((aff, True), (aff + 1, False)):
        monkeypatch.setenv("SLURM_CPUS_PER_TASK", str(cpt))
        _patch(monkeypatch, 8, 16, {})
        args = C33.build_parser({}).parse_args(["--token", "C2_KCHK", "--device", "CPU", "--budget-minutes", "5"])
        C33.run_token(args, {"CI_GATE": "C2_KCHK"})
        d = json.load(open(tmp / "validation" / "C2_KCHK.json"))
        s3 = [c for c in d["criteria"] if c["name"].startswith("S3")][0]
        assert s3["passed"] is ok and d["data"]["run"]["cpu_affinity_check"]["applies"], (cpt, s3)
        assert s3["value"]["cpu_affinity"] == aff and s3["value"]["slurm_cpus_per_task"] == cpt

"""
prompts/33d R3: C2_KCHK -- the power statement, the K1 / K2 / K3 decision rules, and the driver path end to end with
the stub simulator of test_campaign33_paths and a fake CPU process (subprocess.Popen).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from test_campaign33_paths import FakeSim, N, SM, TK, TR, fake_spec, run_dry, sandbox  # noqa: E402,F401


def test_kchk_power_and_decision_rules():
    """The stated power (40 CPU shots: a marginal difference below about 0.24 is invisible) and the K1 / K2 / K3
    rules on synthetic structures."""
    a = {"shots": 40, "sd_hamming_weight": 2.4}
    b = {"shots": 10 ** 9, "sd_hamming_weight": 2.4}
    p = TR.kchk_power(a, b)
    assert abs(p["min_visible_marginal_diff"] - 3 * (0.25 / 40) ** 0.5) < 1e-6
    assert 0.23 < p["min_visible_marginal_diff"] < 0.24

    def st(w, n, p1=0.37):
        return {"shots": n, "n_bits": 20, "mean_hamming_weight": w, "sd_hamming_weight": 2.5,
                "se_mean_hamming_weight": 2.5 / n ** 0.5, "marginals_by_clbit": [p1] * 20,
                "se_marginals_by_clbit": [(p1 * (1 - p1) / n) ** 0.5] * 20}
    S = {"kraus_gpu_cusv": st(2.4, 256, 0.12), "rm_gpu_cusv": st(7.4, 512), "kraus_cpu": st(7.4, 20),
         "rm_cpu": st(7.3, 20), "kraus_gpu_native": st(7.5, 64), "kraus_gpu_cusv_nofusion": st(2.5, 32, 0.12)}
    pairs = [("kraus_gpu_cusv", "kraus_cpu"), ("rm_gpu_cusv", "rm_cpu"), ("rm_gpu_cusv", "kraus_cpu"),
             ("kraus_gpu_native", "kraus_cpu"), ("kraus_gpu_cusv_nofusion", "kraus_cpu")]

    def decide():
        return TR.kchk_decide({f"{x}~{y}": TR.kchk_compare(S, x, y) for x, y in pairs}, S)
    d = decide()
    assert d["bug_confirmed"] is True and d["production_representation"] == "rm"
    assert d["validated_kraus_gpu_path"] == "kraus_gpu_native"
    S["kraus_gpu_native"] = st(2.5, 64, 0.12)
    assert decide()["validated_kraus_gpu_path"] == "none"
    S["rm_gpu_cusv"] = st(5.0, 512)
    assert decide()["production_representation"] == "blocked"
    S["kraus_cpu"] = {"shots": 0, "n_bits": 20}
    d = decide()
    assert d["bug_confirmed"] is None and not d["k1_evaluated"] and d["production_representation"] == "blocked"


def test_c2_kchk_dry_path_with_a_fake_cpu_process(sandbox, monkeypatch):  # noqa: F811
    """Every arm's raw counts sum to its shots; seeds distinct; the decision block, K1-K3 and
    supersedes_decision_of exist; the CPU process is started with the worker module and the stand-in."""
    import subprocess
    tmp, _ = sandbox
    monkeypatch.setattr(N, "ibm_spec", lambda rec, cell, rep, conv="echo", *a, **k: fake_spec(rep))
    from skqd.campaign33.analysis import Physics
    cws = [int(x) for x in Physics(with_sectors=False).emb.ints]
    monkeypatch.setattr(SM, "make_simulator", lambda *a, **k: (FakeSim(cws), {"stub": True}))
    seen = {}
    real_popen = subprocess.Popen

    def popen(cmd, **kw):
        if "skqd.campaign33.kchk_cpu" not in cmd:            # platform.processor() etc. use Popen too
            return real_popen(cmd, **kw)
        return FakeProc(cmd, **kw)

    class FakeProc:
        def __init__(self, cmd, **kw):
            seen["cmd"] = cmd
            out = cmd[cmd.index("--out") + 1]
            s0 = int(cmd[cmd.index("--s0") + 1])
            offs = [int(x) for x in cmd[cmd.index("--offsets") + 1].split(",")]
            arms = {}
            for (arm, rep), off in zip(TR.KCHK_CPU_ARMS, offs):
                chunks = []
                for j in range(2):
                    seed = TK.chunk_seed(s0, off, j, 2)
                    c = SM.counts_to_int(FakeSim(cws).run(None, 2, seed).result().get_counts())
                    chunks.append({"index": j, "seed": seed, "shots": 2, "start": 2 * j, "seconds": 0.1,
                                   "counts": {str(k): v for k, v in c.items()}})
                arms[arm] = {"representation": "pta", "planned_representation": rep, "engine": "fake CPU process",
                             "chunks": chunks, "shots_done": 4, "stopped": "max_shots"}
            with open(out, "w") as fh:
                json.dump({"pid": 1, "threads": 1, "status": "done", "arms": arms}, fh)
            self.pid, self.returncode = 1, 0

        def communicate(self, timeout=None):
            return "", None

        def kill(self):
            pass
    monkeypatch.setattr(subprocess, "Popen", popen)
    rc = run_dry("C2_KCHK")
    d = json.load(open(tmp / "validation" / "dryrun" / "C2_KCHK.json"))
    assert rc == 0 and d["status"] == "PASS", [c for c in d["criteria"] if not c["passed"]]
    D = d["data"]
    assert set(D["arms"]) == {a[0] for a in TR.KCHK_GPU_ARMS} | {a[0] for a in TR.KCHK_CPU_ARMS}
    for a, v in D["arms"].items():
        assert v["raw_counts"]["sum_counts"] == v["shots_done"] > 0, a
    dec = D["decision"]
    assert dec["production_representation"] in ("rm", "blocked")
    assert dec["validated_kraus_gpu_path"] in ("kraus_gpu_native", "kraus_gpu_cusv_nofusion", "none")
    assert D["bug_confirmed"] in (True, False) and D["supersedes_decision_of"]["job"] == "59736871"
    assert "skqd.campaign33.kchk_cpu" in seen["cmd"] and "--stand-in" in seen["cmd"]
    names = [x["name"] for x in D["physics_criteria_information_dry_run"]]
    for k in ("K1 ", "K2 ", "K3 "):
        assert any(n.startswith(k) for n in names), k
    seeds = [ch["seed"] for v in D["arms"].values() for ch in v["raw_counts"]["chunks"]]
    assert len(seeds) == len(set(seeds))
    assert set(D["raw_counts_npz"]) == set(D["arms"])

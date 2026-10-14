#!/usr/bin/env python
"""
prompts/33c R2 diagnostic (CPU): the IBM-T0 circuit B0_ref117_k1 under the class-2 record model I-ECHO in one
representation (kraus | rm | pta), sampled with Aer on the CPU exactly as the C2 cells sample it
(`campaign33.sampling.make_simulator("CPU")`, the model of `noise.ibm_spec`, `spec.apply`), in calls of
--shots-per-call shots with disjoint seeds (seed0 + 1000 x call index; Aer seeds shot j of a call with seed + j).

The JSON is rewritten after every call (a stopped run keeps its completed calls) and records the garbage structure
(`stats.garbage_structure`: mean Hamming weight with its per-shot standard error, per-clbit marginals with the
physical qubit), every call's seed / shots / seconds, the raw counts, the software versions and the commit.
Time cap (30-minute rule): no call is started whose predicted time (the last call's) would pass --max-seconds.

    python scripts/c33c_diag_full.py --rep kraus --shots-per-call 4 --max-shots 48 --max-seconds 1700
    python scripts/c33c_diag_full.py --summarize      # CPU arms vs the GPU arms of validation/C2_CAL.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")]
OUT_DIR = os.path.join(ROOT, "data", "campaign33", "c33c_diag")
CID = "B0_ref117_k1"
C2_CAL = os.path.join(ROOT, "validation", "C2_CAL.json")


def git_commit() -> str:
    try:
        c = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", ROOT, "diff", "--quiet", "--", "src", "scripts"]) != 0
        return c + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def provenance(argv) -> dict:
    import numpy
    import qiskit
    import qiskit_aer
    return {"git_commit": git_commit(), "command": "python " + " ".join([os.path.relpath(__file__, ROOT)] + argv),
            "versions": {"python": platform.python_version(), "qiskit": qiskit.__version__,
                         "qiskit_aer": qiskit_aer.__version__, "numpy": numpy.__version__},
            "machine": {"host": platform.node(), "processor": platform.processor() or platform.machine(),
                        "cpu_count": os.cpu_count()},
            "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}


def run(a, argv):
    from skqd.campaign33 import circuits as C
    from skqd.campaign33 import noise as N
    from skqd.campaign33 import sampling as SM
    from skqd.campaign33 import stats as ST
    from skqd.campaign33 import tokens_run as TR

    rec = TR.load_record()
    circ = C.load_circuit(a.family, CID)
    man = C.load_manifest(a.family, CID)
    if rec["fingerprint"] != man["record_fingerprint"]:
        raise SystemExit("the record is not the one the IBM circuits were built on")
    clb = TR.clbit_physical(circ)
    t_b = time.time()
    spec = N.ibm_spec(rec, "I-ECHO", a.rep, "echo")
    build_s = time.time() - t_b
    sim, kw = SM.make_simulator("CPU", "policy", spec.noise_model, threads=a.threads)
    ct = spec.apply(circ)
    out_path = a.out or os.path.join(OUT_DIR, f"full_{a.family}_{CID}_{a.rep}_cpu.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc = {"title": f"prompts/33c R2 diagnostic: {a.family} {CID} under I-ECHO ({a.rep}) on the CPU",
           "prompt": "prompts/33c R2 (coordinator's resume order 2026-10-13: Kraus and RM on one CPU engine)",
           **provenance(argv), "representation": a.rep, "family": a.family, "circuit": CID, "model": "I-ECHO (echo T2)",
           "record": {"path": os.path.relpath(TR.RECORD, ROOT), "fingerprint": rec["fingerprint"]},
           "simulator_options": kw, "noise_model_build_s": build_s,
           "plan": {"shots_per_call": a.shots_per_call, "max_shots": a.max_shots, "max_seconds": a.max_seconds,
                    "seed0": a.seed, "seed_rule": "seed0 + 1000 x call index"},
           "calls": [], "counts": {}, "status": "running"}
    total = {}
    t0 = time.time()
    i = 0
    stop = "max_shots reached"
    while sum(total.values()) < a.max_shots:
        if doc["calls"]:
            last = doc["calls"][-1]["seconds"]
            if time.time() - t0 + last > a.max_seconds:
                stop = f"time cap: the next call (predicted {last:.0f} s) would pass {a.max_seconds:.0f} s"
                break
        k = min(a.shots_per_call, a.max_shots - sum(total.values()))
        seed = a.seed + 1000 * i
        t_c = time.time()
        res = sim.run(ct, shots=k, seed_simulator=seed).result()
        if not res.success:
            raise RuntimeError(str(getattr(res, "status", "")))
        cnt = SM.counts_to_int(res.get_counts(0))
        for key, v in cnt.items():
            total[key] = total.get(key, 0) + v
        doc["calls"].append({"index": i, "seed": seed, "shots": k, "seconds": time.time() - t_c})
        doc["counts"] = {str(key): v for key, v in sorted(total.items())}
        doc["structure"] = ST.garbage_structure(total, len(clb), clb)
        doc["wall_s"] = time.time() - t0
        with open(out_path, "w") as fh:
            json.dump(doc, fh, indent=1)
        st = doc["structure"]
        print(f"call {i}: {k} shots in {doc['calls'][-1]['seconds']:.1f} s; total {st['shots']}, mean weight "
              f"{st['mean_hamming_weight']:.3f} +- {st['se_mean_hamming_weight']:.3f}", flush=True)
        i += 1
    doc["status"] = "done"
    doc["stop"] = stop
    doc["seconds_per_shot"] = sum(c["seconds"] for c in doc["calls"]) / max(1, sum(c["shots"] for c in doc["calls"]))
    with open(out_path, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"wrote {os.path.relpath(out_path, ROOT)} ({stop})")


def summarize(a, argv):
    """CPU arms (this script's JSONs) against the GPU arms of validation/C2_CAL.json: z of the mean weight and of
    every marginal (stats.structure_compare, the P4a statistic)."""
    import glob
    from skqd.campaign33 import stats as ST
    cpu = {}
    for rep in ("kraus", "rm", "pta"):
        # segments (30-minute rule): full_..._<rep>_cpu.json and full_..._<rep>_cpu_seg<k>.json, disjoint seeds
        files = sorted(glob.glob(os.path.join(OUT_DIR, f"full_IBM-T0_{CID}_{rep}_cpu*.json")))
        if not files:
            continue
        docs = [json.load(open(p)) for p in files]
        seeds = [c["seed"] + j for d in docs for c in d["calls"] for j in range(c["shots"])]
        if len(set(seeds)) != len(seeds):
            raise SystemExit(f"{rep}: segments share shot seeds")
        tot = {}
        for d in docs:
            for k, v in d["counts"].items():
                tot[int(k)] = tot.get(int(k), 0) + int(v)
        clb = docs[0]["structure"]["physical_by_clbit"]
        merged = {"status": "done" if all(d.get("status") == "done" for d in docs) else "partial",
                  "structure": ST.garbage_structure(tot, len(clb), clb),
                  "seconds_per_shot": sum(c["seconds"] for d in docs for c in d["calls"]) / max(1, len(seeds)),
                  "versions": docs[0]["versions"], "segments": [os.path.relpath(p, ROOT) for p in files],
                  "git_commits": sorted({d["git_commit"] for d in docs})}
        cpu[rep] = (", ".join(merged["segments"]), merged)
    cal = json.load(open(C2_CAL))
    gpu = {rep: v["structure"] for rep, v in cal["data"]["arms"].items()}
    out = {"title": "prompts/33c R2 diagnostic summary: CPU (this laptop) vs GPU (C2_CAL job "
                    + str(cal.get("run", {}).get("ci", {}).get("SLURM_JOB_ID", "")) + ")",
           **provenance(argv), "gpu_source": os.path.relpath(C2_CAL, ROOT),
           "gpu_versions": cal.get("run", {}).get("versions") or cal.get("data", {}).get("run", {}).get("versions"),
           "arms": {}, "comparisons": {}}
    for rep, (p, d) in cpu.items():
        s = d.get("structure") or {}
        out["arms"][f"cpu_{rep}"] = {"source": p, "shots": s.get("shots"), "status": d.get("status"),
                                     "mean_hamming_weight": s.get("mean_hamming_weight"),
                                     "se_mean_hamming_weight": s.get("se_mean_hamming_weight"),
                                     "sd_hamming_weight": s.get("sd_hamming_weight"),
                                     "seconds_per_shot": d.get("seconds_per_shot"), "versions": d.get("versions")}
    for rep, s in gpu.items():
        out["arms"][f"gpu_{rep}"] = {"source": f"{os.path.relpath(C2_CAL, ROOT)} data.arms.{rep}.structure",
                                     "shots": s.get("shots"), "mean_hamming_weight": s.get("mean_hamming_weight"),
                                     "se_mean_hamming_weight": s.get("se_mean_hamming_weight"),
                                     "sd_hamming_weight": s.get("sd_hamming_weight")}
    pairs = [("cpu_kraus", "cpu_rm"), ("cpu_kraus", "gpu_kraus"), ("cpu_rm", "gpu_rm"), ("cpu_rm", "gpu_kraus"),
             ("cpu_kraus", "gpu_rm")]
    structs = {f"cpu_{r}": (d.get("structure") or {}) for r, (_p, d) in cpu.items()}
    structs.update({f"gpu_{r}": s for r, s in gpu.items()})
    for x, y in pairs:
        if structs.get(x, {}).get("shots") and structs.get(y, {}).get("shots"):
            c = ST.structure_compare(structs[x], structs[y])
            out["comparisons"][f"{x}_vs_{y}"] = {k: c.get(k) for k in (
                "shots", "mean_hamming_weight", "delta_mean_hamming_weight", "z_mean_hamming_weight",
                "max_abs_z_marginal", "clbits_outside", "pass")}
    p = os.path.join(OUT_DIR, "summary.json")
    with open(p, "w") as fh:
        json.dump(out, fh, indent=1)
    for k, v in out["comparisons"].items():
        print(k, v["mean_hamming_weight"], "z_w", v["z_mean_hamming_weight"], "max|z| marg", v["max_abs_z_marginal"])
    print(f"wrote {os.path.relpath(p, ROOT)}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--rep", choices=("kraus", "rm", "pta"), default="kraus")
    ap.add_argument("--family", default="IBM-T0")
    ap.add_argument("--shots-per-call", type=int, default=4)
    ap.add_argument("--max-shots", type=int, default=48)
    ap.add_argument("--max-seconds", type=float, default=1700.0)
    ap.add_argument("--seed", type=int, default=33033000)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--summarize", action="store_true")
    a = ap.parse_args(argv)
    if a.shots_per_call > 1000:
        raise SystemExit("--shots-per-call must be <= 1000 (seed stride)")
    (summarize if a.summarize else run)(a, argv)


if __name__ == "__main__":
    main()

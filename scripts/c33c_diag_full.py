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
    python scripts/c33c_diag_full.py --summarize --gpu-source validation/C2_CAL.json \
        --gpu-source validation/archive/C2_KCHK_job59780907.json     # prompts/33e R3: both GPU sources, K4
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


GPU_SOURCES_DEFAULT = ("validation/C2_CAL.json",)
KCHK_RUN2 = os.path.join(ROOT, "validation", "C2_KCHK.json")
# prompts/33e section 1 step 3: STOP if the 33e segments of a representation, pooled at >= 32 shots (or one segment
# with >= 32 shots), give a mean weight outside 7.47 +- 3 x 0.56 (the 33c laptop Kraus arm of 19 shots); the band is
# applied to both representations as the prompt states it
STOP_BAND = {"center": 7.47, "se": 0.56, "n_sigma": 3.0, "min_shots": 32,
             "source": "prompts/33e section 1 step 3 (7.47 +- 0.56: data/campaign33/c33c_diag/summary.json of 33c, cpu_kraus)"}
SEG33E_MIN_SEED0 = 33333000          # 33e segments: seed0 = 33033000 + 1e5 x k with k >= 3 (scripts/c33e_diag_segments.sh)


def _segment_row(path, d, ST):
    clb = d["structure"]["physical_by_clbit"]
    tot = {int(k): int(v) for k, v in d["counts"].items()}
    s = ST.garbage_structure(tot, len(clb), clb)
    shots = sum(int(c["shots"]) for c in d["calls"])
    secs = sum(float(c["seconds"]) for c in d["calls"])
    cmd = d.get("command", "")
    thr = None
    if "--threads" in cmd.split():
        parts = cmd.split()
        thr = int(parts[parts.index("--threads") + 1])
    return {"file": os.path.relpath(path, ROOT), "seed0": d["plan"]["seed0"], "shots_per_call": d["plan"]["shots_per_call"],
            "threads": thr, "calls": len(d["calls"]), "shots": shots, "mean_hamming_weight": s.get("mean_hamming_weight"),
            "se_mean_hamming_weight": s.get("se_mean_hamming_weight"), "seconds": secs,
            "seconds_per_shot": secs / shots if shots else None,
            "seconds_per_call": [round(float(c["seconds"]), 1) for c in d["calls"]], "status": d.get("status"),
            "stop": d.get("stop"), "git_commit": d.get("git_commit"), "created": d.get("created"),
            "versions": d.get("versions"), "machine": d.get("machine"), "prompt_33e": d["plan"]["seed0"] >= SEG33E_MIN_SEED0}


def _stop_check(rows, tot_by_file, clb_of, ST):
    """The 33e STOP rule on the segments of one representation (see STOP_BAND)."""
    lo = STOP_BAND["center"] - STOP_BAND["n_sigma"] * STOP_BAND["se"]
    hi = STOP_BAND["center"] + STOP_BAND["n_sigma"] * STOP_BAND["se"]
    seg = [r for r in rows if r["prompt_33e"]]
    checks = []
    for r in seg:
        if r["shots"] >= STOP_BAND["min_shots"]:
            checks.append({"what": r["file"], "shots": r["shots"], "mean_hamming_weight": r["mean_hamming_weight"],
                           "inside": lo <= r["mean_hamming_weight"] <= hi})
    pooled = {}
    for r in seg:
        for k, v in tot_by_file[r["file"]].items():
            pooled[k] = pooled.get(k, 0) + v
    if seg and sum(pooled.values()) >= STOP_BAND["min_shots"]:
        s = ST.garbage_structure(pooled, len(clb_of), clb_of)
        checks.append({"what": "the 33e segments pooled", "shots": s["shots"], "mean_hamming_weight": s["mean_hamming_weight"],
                       "se_mean_hamming_weight": s["se_mean_hamming_weight"], "inside": lo <= s["mean_hamming_weight"] <= hi})
    return {"band": [lo, hi], "evaluated": bool(checks), "checks": checks,
            "stop": any(not c["inside"] for c in checks), "rule": STOP_BAND}


def _gpu_arms(path, ST):
    """The GPU arms (shots > 0, device GPU) of one harvested or archived token JSON, named <token>_job<id>:<arm>."""
    import hashlib
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    raw = open(full, "rb").read()
    d = json.loads(raw)
    D = d.get("data", {})
    run = D.get("run", {})
    job = (run.get("ci") or {}).get("SLURM_JOB_ID", "")
    tag = f"{D.get('token', os.path.basename(path).split('.')[0])}_job{job}"
    src = {"path": os.path.relpath(full, ROOT), "sha256": hashlib.sha256(raw).hexdigest(), "job": job,
           "status": d.get("status"), "versions": run.get("versions"), "device": run.get("device"),
           "calibration_run": D.get("calibration_run")}
    arms = {}
    for name, v in (D.get("arms") or {}).items():
        st = v.get("structure") or {}
        engine = str(v.get("engine", ""))
        is_gpu = (run.get("device") == "GPU") and ("CPU" not in engine)
        if st.get("shots") and is_gpu:
            arms[f"{tag}:{name}"] = {"source": f"{src['path']} data.arms.{name}.structure", "job": job,
                                     "engine": engine or f"GPU ({v.get('mode')})", "shots": st["shots"],
                                     "mean_hamming_weight": st["mean_hamming_weight"],
                                     "se_mean_hamming_weight": st["se_mean_hamming_weight"],
                                     "sd_hamming_weight": st["sd_hamming_weight"], "structure": st}
    return tag, src, arms


def summarize(a, argv):
    """CPU arms (this script's segment JSONs, merged per representation) against the GPU arms of every
    --gpu-source (default validation/C2_CAL.json): z of the mean weight and of every marginal
    (stats.structure_compare, the P4a statistic); the per-segment table; the 33e STOP rule; K4 against the CPU arms of
    C2_KCHK run 2 when validation/C2_KCHK.json is run 2 (prompts/33e R3)."""
    import glob

    from skqd.campaign33 import stats as ST
    from skqd.campaign33 import tokens_run as TR
    from skqd.campaign33.kchk_cpu import aer_distribution
    cpu, segments, stops, excluded = {}, {}, {}, {}
    for rep in ("kraus", "rm", "pta"):
        # segments (30-minute rule): full_..._<rep>_cpu.json and full_..._<rep>_cpu_seg<k>.json, disjoint seeds
        files = sorted(glob.glob(os.path.join(OUT_DIR, f"full_IBM-T0_{CID}_{rep}_cpu*.json")))
        # a segment still running (status != done) is listed, never merged: its calls are not final yet
        docs_all = [(p, json.load(open(p))) for p in files]
        excluded[rep] = [os.path.relpath(p, ROOT) for p, d in docs_all if d.get("status") != "done"]
        files = [p for p, d in docs_all if d.get("status") == "done"]
        docs = [d for _p, d in docs_all if d.get("status") == "done"]
        if not files:
            continue
        seeds = [c["seed"] + j for d in docs for c in d["calls"] for j in range(c["shots"])]
        if len(set(seeds)) != len(seeds):
            raise SystemExit(f"{rep}: segments share shot seeds")
        tot, tot_by_file = {}, {}
        for p, d in zip(files, docs):
            tf = {int(k): int(v) for k, v in d["counts"].items()}
            tot_by_file[os.path.relpath(p, ROOT)] = tf
            for k, v in tf.items():
                tot[k] = tot.get(k, 0) + v
        clb = docs[0]["structure"]["physical_by_clbit"]
        if any(d["structure"]["physical_by_clbit"] != clb for d in docs):
            raise SystemExit(f"{rep}: segments disagree on the clbit -> physical map")
        rows = [_segment_row(p, d, ST) for p, d in zip(files, docs)]
        segments[rep] = rows
        stops[rep] = _stop_check(rows, tot_by_file, clb, ST)
        merged = {"status": "done" if all(d.get("status") == "done" for d in docs) else "partial",
                  "structure": ST.garbage_structure(tot, len(clb), clb),
                  "seconds_per_shot": sum(c["seconds"] for d in docs for c in d["calls"]) / max(1, len(seeds)),
                  "versions": docs[0]["versions"], "segments": [os.path.relpath(p, ROOT) for p in files],
                  "git_commits": sorted({d["git_commit"] for d in docs}),
                  "versions_all_equal": all(d["versions"] == docs[0]["versions"] for d in docs)}
        cpu[rep] = merged
    lap_aer = aer_distribution()
    out = {"title": "prompts/33c R2 / 33e R3 diagnostic summary: CPU (this laptop, the qiskit 1.4.3 twin) vs the GPU arms "
                    "of " + ", ".join(a.gpu_source or GPU_SOURCES_DEFAULT),
           **provenance(argv), "aer": lap_aer,
           "aer_wheel_note": ("the CPU statevector code is the same source on every stack; the wheel is qiskit-aer here "
                              "and qiskit-aer-gpu on the CI (prompts/33e R3 (a))"),
           "gpu_sources": {}, "arms": {}, "segments": segments, "segments_excluded_running": excluded,
           "stop_33e": stops, "comparisons": {}}
    gpu = {}
    for src in (a.gpu_source or GPU_SOURCES_DEFAULT):
        tag, meta, arms = _gpu_arms(src, ST)
        out["gpu_sources"][tag] = meta
        gpu.update(arms)
    for rep, d in cpu.items():
        s = d.get("structure") or {}
        out["arms"][f"cpu_{rep}"] = {"source": ", ".join(d["segments"]), "shots": s.get("shots"), "status": d.get("status"),
                                     "mean_hamming_weight": s.get("mean_hamming_weight"),
                                     "se_mean_hamming_weight": s.get("se_mean_hamming_weight"),
                                     "sd_hamming_weight": s.get("sd_hamming_weight"),
                                     "seconds_per_shot": d.get("seconds_per_shot"), "versions": d.get("versions"),
                                     "versions_all_equal": d["versions_all_equal"], "git_commits": d["git_commits"],
                                     "aer": lap_aer, "structure": s}
    for name, v in gpu.items():
        out["arms"][f"gpu:{name}"] = {k: v[k] for k in ("source", "job", "engine", "shots", "mean_hamming_weight",
                                                        "se_mean_hamming_weight", "sd_hamming_weight")}
    structs = {f"cpu_{r}": (d.get("structure") or {}) for r, d in cpu.items()}
    structs.update({f"gpu:{n}": v["structure"] for n, v in gpu.items()})
    pairs = [("cpu_kraus", "cpu_rm")] + [(c, g) for c in ("cpu_kraus", "cpu_rm") for g in structs if g.startswith("gpu:")]
    for x, y in pairs:
        if structs.get(x, {}).get("shots") and structs.get(y, {}).get("shots"):
            c = ST.structure_compare(structs[x], structs[y])
            out["comparisons"][f"{x}_vs_{y}"] = {k: c.get(k) for k in (
                "shots", "mean_hamming_weight", "delta_mean_hamming_weight", "z_mean_hamming_weight",
                "max_abs_z_marginal", "clbits_outside", "pass")}
            out["comparisons"][f"{x}_vs_{y}"]["power"] = TR.kchk_power(structs[x], structs[y])
    # ---- K4 (prompts/33e R3 (b)): the CI CPU arms of C2_KCHK run 2 against this summary's CPU arms
    k4 = {"evaluated": False, "status": "not_evaluated"}
    kp = a.kchk_run2 if os.path.isabs(a.kchk_run2) else os.path.join(ROOT, a.kchk_run2)
    if os.path.exists(kp):
        kd = json.load(open(kp))
        D = kd.get("data", {})
        if D.get("calibration_run") == 2 and not D.get("dry_run"):
            ci_arms = {arm: D["arms"][arm]["structure"] for arm, _k in TR.KCHK_K4_REPS if arm in D.get("arms", {})}
            lap = {"present": True, "path": "this summary",
                   "arms": {f"cpu_{r}": {**out["arms"][f"cpu_{r}"]} for r in ("kraus", "rm") if f"cpu_{r}" in out["arms"]}}
            k4 = TR.kchk_k4(ci_arms, lap)
            k4["ci_source"] = os.path.relpath(kp, ROOT)
        else:
            job = (D.get("run", {}).get("ci") or {}).get("SLURM_JOB_ID")
            k4["reason"] = (f"{os.path.relpath(kp, ROOT)} is not C2_KCHK run 2 (calibration_run "
                            f"{D.get('calibration_run')}, job {job}, dry_run {D.get('dry_run')}): run 2 not harvested yet")
    else:
        k4["reason"] = f"{os.path.relpath(kp, ROOT)} absent"
    out["k4"] = k4
    p = os.path.join(OUT_DIR, "summary.json")
    with open(p, "w") as fh:
        json.dump(out, fh, indent=1)
    for rep, rows in segments.items():
        for r in rows:
            print(f"{rep:6s} {os.path.basename(r['file']):48s} {r['shots']:4d} shots  w {r['mean_hamming_weight']:.3f} +- "
                  f"{r['se_mean_hamming_weight']:.3f}  {r['seconds_per_shot']:.1f} s/shot  {r['git_commit']}")
        print(f"{rep:6s} merged {cpu[rep]['structure']['shots']} shots, w {cpu[rep]['structure']['mean_hamming_weight']:.3f} "
              f"+- {cpu[rep]['structure']['se_mean_hamming_weight']:.3f}; 33e STOP {stops[rep]['stop']} "
              f"(evaluated {stops[rep]['evaluated']})")
    for k, v in out["comparisons"].items():
        print(k, v["mean_hamming_weight"], "z_w", v["z_mean_hamming_weight"], "max|z| marg", v["max_abs_z_marginal"])
    print("K4:", k4.get("status"), k4.get("reason", ""))
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
    ap.add_argument("--gpu-source", action="append", default=None,
                    help="--summarize: a token JSON whose GPU arms are compared (repeatable; default "
                         "validation/C2_CAL.json; prompts/33e R3 adds validation/archive/C2_KCHK_job59780907.json)")
    ap.add_argument("--kchk-run2", default="validation/C2_KCHK.json",
                    help="--summarize: K4 against this file's CPU arms when it is C2_KCHK run 2 (prompts/33e R3 (b))")
    a = ap.parse_args(argv)
    if a.shots_per_call > 1000:
        raise SystemExit("--shots-per-call must be <= 1000 (seed stride)")
    (summarize if a.summarize else run)(a, argv)


if __name__ == "__main__":
    main()

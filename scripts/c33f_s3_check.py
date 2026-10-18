#!/usr/bin/env python3
"""
prompts/33f, coordinator's R4 question: with OMP_PROC_BIND=spread + OMP_PLACES=threads still exported (jobs/gate.sbatch
as it is), does S3 (run.cpu_affinity == SLURM_CPUS_PER_TASK on the CI) pass?  Two claims were on the table:
  planner (33f R4):    every token FAILs S3 until the binding is removed;
  33e executor:        run.cpu_affinity is the step's CPU set recorded at process start (skqd.hpc.record_step_cpus,
                       before any OpenMP runtime loads), so S3 passes with the binding in place.

The test (laptop, qiskit 1.4.3 / aer 0.15.1 twin): scratch/c33f/cisim.sh runs a token's dry run through the CI's own
chain (`python scripts/run_gate.py <TOKEN> --dry-run ...` -> campaign33.py in a subprocess) in the gate.sbatch thread
environment, with the variables that make the driver take its CI branch (CI_GATE, SLURM_JOB_ID, SLURM_CPUS_PER_TASK =
the laptop's 12 CPUs, CUDA_VISIBLE_DEVICES, a fake nvidia-smi telemetry file).  S1 FAILs there by construction (no GPU
on the laptop); S3 is the criterion under test.  This script collects the copied token JSONs into
data/campaign33/c33f_s3_check/summary.json.

    python scripts/c33f_s3_check.py
"""
import glob
import json
import os
import re
import shutil
import subprocess
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "scratch", "c33f", "logs")
OUT = os.path.join(ROOT, "data", "campaign33", "c33f_s3_check")


def main():
    os.makedirs(OUT, exist_ok=True)
    runs = {}
    for p in sorted(glob.glob(os.path.join(SRC, "cisim_*_bind*.json"))):
        m = re.search(r"cisim_(.+)_bind(\d)\.json$", p)
        tok, bind = m.group(1), int(m.group(2))
        d = json.load(open(p))
        crit = {c["name"].split(" ")[0]: c["passed"] for c in d["criteria"]}
        s3 = [c for c in d["criteria"] if c["name"].startswith("S3")][0]
        run = d["data"]["run"]
        log = p[:-5] + ".log"
        shutil.copyfile(p, os.path.join(OUT, os.path.basename(p)))
        if os.path.exists(log):
            shutil.copyfile(log, os.path.join(OUT, os.path.basename(log)))
        runs[f"{tok}|bind{bind}"] = {
            "token": tok, "omp_binding": bool(bind),
            "env": ("OMP_PROC_BIND=spread, OMP_PLACES=threads" if bind else "OMP_PROC_BIND / OMP_PLACES unset (R4)")
            + ", SLURM_CPU_BIND=cores, OMP/MKL/OPENBLAS_NUM_THREADS=12, CI_GATE set, SLURM_CPUS_PER_TASK=12",
            "status": d["status"], "criteria": crit, "failing": [k for k, v in crit.items() if not v],
            "S3_passed": s3["passed"], "S3_value": s3["value"],
            "cpu_affinity_recorded": run.get("cpu_affinity"), "cpu_affinity_source": run.get("cpu_affinity_source"),
            "cpu_affinity_main_thread_now": run.get("cpu_affinity_main_thread_now"),
            "cpu_affinity_check": run.get("cpu_affinity_check"), "ci": run.get("ci"),
            "versions": run.get("versions"), "wall_seconds": run.get("wall_seconds"),
            "preflight_modules": len((d["data"].get("preflight") or {}).get("modules") or []),
            "git_commit": d.get("environment", {}).get("git_commit"), "json": os.path.basename(p)}
    commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
    doc = {"title": "prompts/33f: S3 with the OpenMP binding in place (laptop CI simulation)",
           "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "git_commit": commit,
           "command": "bash scratch/c33f/cisim.sh <TOKEN> <BIND>; python scripts/c33f_s3_check.py",
           "runs": runs,
           "verdict": {
               "S3_passes_with_binding": all(r["S3_passed"] for r in runs.values() if r["omp_binding"]),
               "main_thread_pinned_with_binding": all(r["cpu_affinity_main_thread_now"] == 1
                                                      for r in runs.values() if r["omp_binding"]),
               "claim_supported": ("33e executor" if all(r["S3_passed"] for r in runs.values() if r["omp_binding"])
                                   else "planner")},
           "limits": ("a laptop simulation: Slurm, srun --cpus-per-task and SLURM_CPU_BIND=cores are not exercised (no "
                      "Slurm here); the CI's own start affinity under srun is first recorded by the next CI job.  S1 FAILs "
                      "in the simulation by construction (no GPU).")}
    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump(doc, fh, indent=1)
    for k, r in runs.items():
        print(f"{k}: S3 {'PASS' if r['S3_passed'] else 'FAIL'} (recorded {r['cpu_affinity_recorded']}, main thread now "
              f"{r['cpu_affinity_main_thread_now']}), failing {r['failing']}")
    print("verdict:", doc["verdict"])


if __name__ == "__main__":
    main()

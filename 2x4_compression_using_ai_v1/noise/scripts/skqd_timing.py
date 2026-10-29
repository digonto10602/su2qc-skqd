"""Timing probes for the noisy SKQD campaign budget (notes/campaign_budget.md): seconds per noisy trajectory per
(lattice, family, device, circuit), measured with scripts/skqd_sample.run on probe circuits, W probes in parallel
(one BLAS thread each), every probe bounded by a wall-clock limit.  Probe samples go to noise/.cache/timing/
(gitignored); the timing table goes to noise/data/checks/skqd_timing.json.

Usage: taskset -c 5-9 nice -n 10 python scripts/skqd_timing.py --workers 5
"""
import os as _os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(NOISE, "src"))
sys.path.insert(0, HERE)
OUT = os.path.join(NOISE, "data", "checks", "skqd_timing.json")
PROBE_DIR = os.path.join(NOISE, ".cache", "timing")

LIMIT = {"2x2": 20.0, "2x3": 60.0, "2x4": 240.0}
SHOTS = {"2x2": 4000, "2x3": 3000, "2x4": 2000}


def probes():
    import campaign as C
    P = []
    for dev in (C.PRIMARY, C.SECONDARY):
        for lat in ("2x2", "2x3", "2x4"):
            fams = C.FAMILIES[lat] if dev == C.PRIMARY else [f for f in C.FAMILIES[lat] if not f.endswith("_v1")]
            for fam in fams:
                ids = C.circuits(lat, fam)
                b0 = sorted(c for c in ids if c.startswith("B0"))
                b1 = sorted(c for c in ids if c.startswith("B1"))
                ref0 = b0[0].rsplit("_", 1)[0]
                ref1 = b1[0].rsplit("_", 1)[0]
                want = [f"{ref0}_k1", f"{ref0}_k4", f"{ref0}_k5", f"{ref1}_k4"]
                if fam.endswith("_v1") or dev == C.SECONDARY:
                    want = [f"{ref0}_k4", f"{ref1}_k4"]
                for c in want:
                    if c in ids:
                        P.append((lat, fam, dev, c))
    return P


def one(job):
    import campaign as C
    import skqd_sample as S
    lat, fam, dev, cid = job
    C.chunk_path = lambda *a: os.path.join(PROBE_DIR, lat, fam, dev, f"{cid}_{time.time_ns()}.npz")
    m = S.run(lat, fam, dev, cid, 0, 0, SHOTS[lat], time_limit=LIMIT[lat])
    return {"lattice": lat, "family": fam, "device": dev, "circuit": cid, "shots": m["shots"],
            "init_s": m["timing_s"]["init"], "per_shot_s": m["timing_s"]["per_shot"], "f_gate": m["f_gate"],
            "fault_free_fraction": m["fault_free_fraction"], "n_2q": m["budget"]["n_2q"],
            "clean_state_max_abs_dpsi": m["clean_state_max_abs_dpsi"], "affinity": m["threads"]["affinity"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    jobs = probes()
    print(len(jobs), "probes", flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(one, jobs):
            rows.append(r)
            print(json.dumps(r), flush=True)
    from provenance import provenance, dump
    dump({"what": "seconds per noisy trajectory (one shot) for the noisy SKQD campaign budget",
          "workers_parallel": a.workers, "omp_threads_per_worker": 1, "limits_s": LIMIT, "rows": rows,
          "wall_s": time.time() - t0, "provenance": provenance()}, OUT)
    print("DONE", time.time() - t0)

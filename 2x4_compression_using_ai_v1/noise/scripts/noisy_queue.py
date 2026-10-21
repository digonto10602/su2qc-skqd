"""Background queue for C5 test 2 (noisy behaviour), resumable; every job is capped at 30 min.

Usage: nohup nice -n 10 python scripts/noisy_queue.py [--workers 3] > logs/noisy_queue.log 2>&1 &
Jobs are run in priority order; a job whose result file exists is skipped.  2x4 runs use the fixed subset S2X4
(the same circuits for both classes, including the reviewer's B0_ref102_k1/k5, B1_ref230_k1/k5, B0_ref345_k4).
"""
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(NOISE, "src"))
import circuits  # noqa: E402

S2X4 = ["B0_ref102_k1", "B0_ref102_k3", "B0_ref102_k5", "B0_ref345_k1", "B0_ref345_k4", "B0_ref345_k5",
        "B0_ref16833_k1", "B0_ref1338_k1", "B1_ref230_k1", "B1_ref230_k3", "B1_ref230_k5", "B1_ref103_k1"]
A, B = "compressed_circuit_llm_2x4_classA", "compressed_circuit_llm_2x4_classB"
F23 = circuits.frozen_2x3_ids()


def jobs():
    J = []
    for dev in ("quantinuum_h2_2",):
        for t in S2X4:
            J += [("2x4", B, dev, t, 300), ("2x4", A, dev, t, 300)]
        J += [("2x3", "frozen", dev, t, 400) for t in F23]
    for dev in ("quantinuum_helios_1",):
        for t in S2X4:
            J += [("2x4", B, dev, t, 300), ("2x4", A, dev, t, 300)]
        J += [("2x3", "frozen", dev, t, 400) for t in F23]
    for dev in ("quantinuum_h2_2_nomem", "ionq_tempo_noidle", "ionq_forte_noidle"):
        for t in S2X4:
            J += [("2x4", B, dev, t, 300), ("2x4", A, dev, t, 300)]
        J += [("2x3", "frozen", dev, t, 300) for t in F23]
    for dev in ("ionq_forte", "ionq_tempo"):
        J += [("2x3", "frozen", dev, t, 200) for t in F23 if t.endswith("_k1")]
        J += [("2x4", fam, dev, t, 200) for t in S2X4 if t.endswith("_k1") for fam in (B, A)]
    return J


def run(job):
    lat, fam, dev, tag, shots = job
    out = os.path.join(NOISE, "data", "results", lat, fam, dev, "noisy_runs", tag + ".json")
    if os.path.exists(out):
        return
    t0 = time.time()
    print(f"START {time.strftime('%H:%M:%S')} {lat} {fam} {dev} {tag}", flush=True)
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "noisy_run.py"), lat, fam, dev, tag,
                            "--shots", str(shots)], capture_output=True, text=True, timeout=1800, cwd=NOISE)
        print((r.stdout.strip().splitlines() or [""])[-1], f"({time.time() - t0:.0f}s)", flush=True)
        if r.returncode != 0:
            print(f"FAILED {lat} {fam} {dev} {tag} rc={r.returncode}: {r.stderr.strip()[-400:]}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT {lat} {fam} {dev} {tag} (30 min)", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    J = jobs()
    print(f"QUEUE {len(J)} jobs, {a.workers} workers", flush=True)
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(run, J))
    print("QUEUE_DONE", time.strftime("%Y-%m-%dT%H:%M:%S"), flush=True)

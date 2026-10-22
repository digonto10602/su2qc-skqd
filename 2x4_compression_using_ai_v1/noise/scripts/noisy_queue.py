"""Background queue for C5 test 2 (noisy behaviour), resumable, 30-min cap per job.

Usage: nohup nice -n 10 python scripts/noisy_queue.py [--workers 3] >> logs/noisy_queue.log 2>&1 &
Before every job the plan (scripts/queue_plan.py: noisy_jobs) is re-read, so families genie-opus publishes later join
without a restart; a job whose result file exists, or that is running in this queue, is skipped.
"""
import argparse
import importlib
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import queue_plan  # noqa: E402

LOCK = threading.Lock()
RUNNING, FAILED = set(), set()


def out_path(job):
    lat, fam, dev, tag, _ = job
    return os.path.join(NOISE, "data", "results", lat, fam, dev, "noisy_runs", tag + ".json")


def running_elsewhere():
    """Jobs whose noisy_run.py process is alive (e.g. left over from a previous queue instance)."""
    out = set()
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            a = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
        except OSError:
            continue
        a = [x.decode(errors="replace") for x in a if x]
        for i, x in enumerate(a):
            if x.endswith("noisy_run.py") and len(a) >= i + 5:
                out.add(tuple(a[i + 1:i + 5]))
    return out


def next_job():
    with LOCK:
        importlib.reload(queue_plan)
        busy = running_elsewhere()
        for job in queue_plan.noisy_jobs():
            k = job[:4]
            if k in RUNNING or k in FAILED or k in busy or os.path.exists(out_path(job)):
                continue
            RUNNING.add(k)
            return job
    return None


def worker():
    while True:
        job = next_job()
        if job is None:
            return
        lat, fam, dev, tag, shots = job
        t0 = time.time()
        print(f"START {time.strftime('%H:%M:%S')} {lat} {fam} {dev} {tag}", flush=True)
        try:
            r = subprocess.run([sys.executable, os.path.join(HERE, "noisy_run.py"), lat, fam, dev, tag,
                                "--shots", str(shots)], capture_output=True, text=True, timeout=1800, cwd=NOISE)
            print((r.stdout.strip().splitlines() or [""])[-1], f"({time.time() - t0:.0f}s)", flush=True)
            if r.returncode != 0:
                print(f"FAILED {lat} {fam} {dev} {tag} rc={r.returncode}: {r.stderr.strip()[-400:]}", flush=True)
                FAILED.add(job[:4])
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT {lat} {fam} {dev} {tag} (30 min)", flush=True)
            FAILED.add(job[:4])
        with LOCK:
            RUNNING.discard(job[:4])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    print(f"QUEUE {len(queue_plan.noisy_jobs())} planned jobs, {a.workers} workers", flush=True)
    ts = [threading.Thread(target=worker) for _ in range(a.workers)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print("QUEUE_DONE", time.strftime("%Y-%m-%dT%H:%M:%S"), "failed:", sorted(FAILED), flush=True)

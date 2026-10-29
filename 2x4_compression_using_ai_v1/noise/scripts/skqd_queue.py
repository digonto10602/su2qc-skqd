"""Background queue of the noisy SKQD campaign: resumable, one chunk (< 30 min) per job, CPU set and worker count
re-read from a control file before every dispatch (so the owner's "now you may use 10 threads" needs no restart).

Usage: nohup nice -n 10 python scripts/skqd_queue.py >> logs/skqd_queue.log 2>&1 &
Control file logs/skqd_queue.ctl (JSON, re-read every few seconds):
    {"workers": 5, "cpus": "5-9", "stop": false}
Jobs: notes/campaign_budget.json "jobs" (priority order), each [lattice, family, device, cid, chunk, start, shots].
A job whose chunk file exists is skipped; a failed job is retried once, then logged FAILED and skipped.
Every job runs as `taskset -c <cpus> nice -n 10 python scripts/skqd_sample.py ...` with OMP/BLAS threads = 1 and a
1800 s timeout (the 30-minute rule).
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NOISE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(NOISE, "src"))
import campaign as C  # noqa: E402

CTL = os.path.join(NOISE, "logs", "skqd_queue.ctl")
STATE = os.path.join(NOISE, "logs", "skqd_queue_state.json")


def ctl():
    try:
        d = json.load(open(CTL))
    except (OSError, ValueError) as exc:
        print(f"CTL unreadable ({exc}); using workers 5 cpus 5-9", flush=True)
        d = {}
    w = min(int(d.get("workers", 5)), 10)          # owner rule: never more than 10
    return w, str(d.get("cpus", "5-9")), bool(d.get("stop", False))


def main():
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    tries, failed, running = {}, set(), {}
    t_start = time.time()
    done_count = 0
    while True:
        jobs = [tuple(j) for j in C.load_budget()["jobs"]]
        todo = [j for j in jobs if j not in running and j[:5] not in failed
                and not os.path.exists(C.chunk_path(*j[:5]))]
        # reap
        for j, (p, t0, fh) in list(running.items()):
            rc = p.poll()
            if rc is None:
                if time.time() - t0 > 1800:
                    p.kill()
                    print(f"TIMEOUT {' '.join(map(str, j[:5]))}", flush=True)
                    rc = -9
                else:
                    continue
            out = fh.read().strip().splitlines()
            fh.close()
            del running[j]
            if rc == 0 and os.path.exists(C.chunk_path(*j[:5])):
                done_count += 1
                print(f"DONE {time.strftime('%m-%d %H:%M:%S')} ({time.time() - t0:.0f}s) {(out or [''])[-1]}", flush=True)
            else:
                tries[j[:5]] = tries.get(j[:5], 0) + 1
                print(f"FAILED rc={rc} try {tries[j[:5]]} {' '.join(map(str, j[:5]))}: {' | '.join(out[-4:])}", flush=True)
                if tries[j[:5]] >= 2:
                    failed.add(j[:5])
        workers, cpus, stop = ctl()
        if not todo and not running:
            break
        if stop and not running:
            print("STOP requested via control file", flush=True)
            break
        while not stop and len(running) < workers and todo:
            j = todo.pop(0)
            lat, fam, dev, cid, chunk, start, shots = j
            cmd = ["taskset", "-c", cpus, "nice", "-n", "10", sys.executable, os.path.join(HERE, "skqd_sample.py"),
                   lat, fam, dev, cid, "--chunk", str(chunk), "--start", str(start), "--shots", str(shots)]
            fh = open(os.path.join(NOISE, ".cache", f"q_{os.getpid()}_{len(running)}_{time.time_ns()}.out"), "w+")
            p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=NOISE, env=env)
            fh2 = open(fh.name)
            fh.close()
            running[j] = (p, time.time(), fh2)
            print(f"START {time.strftime('%m-%d %H:%M:%S')} [{len(running)}/{workers} on {cpus}] "
                  f"{lat} {C.short(fam)} {dev} {cid} c{chunk} {shots} shots", flush=True)
        try:
            with open(STATE + ".tmp", "w") as fh:
                json.dump({"updated": time.strftime("%Y-%m-%d %H:%M:%S"), "jobs_total": len(jobs),
                           "jobs_left": len(todo) + len(running), "running": [list(j[:5]) for j in running],
                           "failed": sorted(map(list, failed)), "done_this_run": done_count,
                           "elapsed_h": (time.time() - t_start) / 3600, "workers": workers, "cpus": cpus}, fh, indent=1)
            os.replace(STATE + ".tmp", STATE)
        except OSError:
            pass
        time.sleep(3)
    print("QUEUE_DONE", time.strftime("%Y-%m-%dT%H:%M:%S"), "failed:", sorted(failed), flush=True)


if __name__ == "__main__":
    main()

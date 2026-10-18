"""
prompts/33e part 2: why C2_KCHK run 2 (job 59828887) still ran its CPU arm on 1 thread with the srun
--cpus-per-task fix in place.  jobs/gate.sbatch exports OMP_PROC_BIND=spread and OMP_PLACES=threads (RUNBOOK policy);
when qiskit_aer's OpenMP runtime initialises under them it binds the initial thread to the first place, so after
`import qiskit_aer` (the campaign preflight does it first) the main thread's os.sched_getaffinity(0) is 1 CPU and
every subprocess inherits that mask.  The fix: the driver records the step's CPU set before any OpenMP runtime loads
(skqd.hpc.record_step_cpus -> SKQD_STEP_CPUS), the thread count and S3 read that set, and the CPU worker takes it
back (restore_step_affinity) before it loads qiskit_aer.  These tests run the real mechanism in subprocesses with the
gate.sbatch environment.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
N_CPU = len(os.sched_getaffinity(0))
pytestmark = pytest.mark.skipif(N_CPU < 6, reason="needs a machine with at least 6 CPUs to see the pinning")


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OMP_", "GOMP_", "SKQD_STEP"))}
    env.update({"OMP_PROC_BIND": "spread", "OMP_PLACES": "threads", "OMP_NUM_THREADS": str(N_CPU),
                "PYTHONPATH": os.pathsep.join([os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")])})
    env.update(extra)
    return env


PARENT = r"""
import json, os, subprocess, sys
from skqd.hpc import record_step_cpus, step_cpu_count, cpu_affinity
if sys.argv[1] == "fixed":
    record_step_cpus()
import qiskit_aer  # noqa: F401  -- what the campaign preflight imports first
from skqd.campaign33.kchk_cpu import cpu_threads
child = r'''
import json, os
from skqd.hpc import restore_step_affinity
r = restore_step_affinity()
import qiskit_aer  # noqa: F401
r["after_import"] = len(os.sched_getaffinity(0))
print(json.dumps(r))
'''
c = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True)
print(json.dumps({"main_thread_after_import": cpu_affinity(), "step_cpus": step_cpu_count(),
                  "threads": cpu_threads(0), "child": json.loads(c.stdout.strip().splitlines()[-1])}))
"""


def _run(mode):
    p = subprocess.run([sys.executable, "-c", PARENT, mode], env=_env(), capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0, p.stderr[-1500:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_job_59828887_mechanism_without_the_start_record():
    """No start record (as in job 59828887): the main thread is pinned to 1 CPU by the import, the worker thread
    count comes out 1 and the child inherits 1 CPU."""
    r = _run("unfixed")
    assert r["main_thread_after_import"] == 1, "qiskit_aer's OpenMP runtime pins the main thread under OMP_PROC_BIND"
    assert r["threads"] == 1 and r["child"]["before"] == 1 and r["child"]["after"] == 1


def test_the_start_record_gives_the_worker_the_step_cpus():
    r = _run("fixed")
    assert r["main_thread_after_import"] == 1, "the policy environment is unchanged: the main thread is still pinned"
    assert r["step_cpus"] == N_CPU and r["threads"] == max(1, N_CPU - 4)
    assert r["child"]["before"] == 1 and r["child"]["after"] == N_CPU and r["child"]["step_cpus"] == N_CPU


def test_driver_records_the_step_cpus_before_the_preflight_imports():
    """scripts/campaign33.py: run.cpu_affinity (S3) is the step's CPU count even though the preflight has imported
    qiskit_aer under the gate.sbatch environment; the main thread's current affinity is recorded beside it."""
    code = ("import sys, json; sys.argv = ['campaign33.py']; import campaign33 as C; C.preflight('C2_KCHK', write=False);"
            "from skqd.hpc import step_cpu_count, cpu_affinity;"
            "print(json.dumps({'step': step_cpu_count(), 'now': cpu_affinity()}))")
    p = subprocess.run([sys.executable, "-c", code], env=_env(), capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0, p.stderr[-1500:]
    r = json.loads(p.stdout.strip().splitlines()[-1])
    assert r == {"step": N_CPU, "now": 1}


def test_record_step_cpus_keeps_an_earlier_record_and_restore_is_a_noop_without_one():
    from skqd.hpc import STEP_CPUS_ENV, record_step_cpus, restore_step_affinity, step_cpus
    env = {STEP_CPUS_ENV: "0,1"}
    assert record_step_cpus(env) == [0, 1] and env[STEP_CPUS_ENV] == "0,1"
    env = {}
    assert record_step_cpus(env) == sorted(os.sched_getaffinity(0))
    assert step_cpus({}) == []
    r = restore_step_affinity({})
    assert r["before"] == r["after"] == N_CPU and r["step_cpus"] is None

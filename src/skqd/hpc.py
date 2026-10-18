"""
CI / Slurm / GPU-telemetry helpers shared by the gate scripts that may run on Perlmutter.

These four functions were written for gate L4 (`scripts/laptop_L4_aer_noise.py`) and are moved
here unchanged so that gate S3 (`scripts/s3_device_model.py`) uses the SAME detection, the same
Slurm fallbacks and the same telemetry parser rather than a copy that can drift.  L4 imports them
back under their original names, so its behaviour is exactly what it was.

Nothing here imports qiskit (the CI runs qiskit 1.4.3, the laptop 2.5.2), and nothing here reads
or writes a validation file: the caller decides what to record.

Reference: the owner's engine and HPC policy in RUNBOOK.md, "Engine and HPC policy for Perlmutter
runs" -- every GPU job records wall time, per-phase timings, GPUs and tasks used, seconds per shot,
peak GPU memory and mean GPU utilization.
"""
import os

GPU_TELEMETRY_FILE = "gpu_telemetry.csv"   # written by jobs/gate.sbatch, read back below


def ci_context() -> dict:
    """Non-empty when this run is the Perlmutter CI job rather than a laptop run.

    The CI passes only the gate token: it runs `python scripts/run_gate.py <GATE>` with no extra
    arguments (ci/README.md), so the gate has to choose GPU mode itself.  CI_GATE is set by the
    poller; SLURM_JOB_ID is the fallback for a hand-submitted Slurm job."""
    ctx = {k: os.environ[k] for k in ("CI_GATE", "SLURM_JOB_ID", "SLURM_JOB_NODELIST")
           if os.environ.get(k)}
    return ctx if ("CI_GATE" in ctx or "SLURM_JOB_ID" in ctx) else {}


def qiskit_versions() -> dict:
    """Recorded in the gate JSON: the CI runs qiskit 1.4.3, the laptop 2.5.2."""
    out = {}
    for mod in ("qiskit", "qiskit_aer"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception as exc:                                  # pragma: no cover
            out[mod] = f"unavailable: {exc}"
    return out


def slurm_layout() -> dict:
    """GPUs, tasks and rank of this job, from Slurm's own environment (RUNBOOK.md asks every GPU
    job to record them).  All None on a laptop, where none of these variables exist."""
    def _int(name):
        v = os.environ.get(name)
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    # ci/poll.sh submits with --gpus-per-task, but Slurm does not always export
    # SLURM_GPUS_PER_TASK to the step (job 58741899 reported it unset while running on one A100),
    # so fall back to the variables it does set and finally to the visible-device list.
    gpus = (_int("SLURM_GPUS_PER_TASK") or _int("SLURM_GPUS_ON_NODE") or _int("SLURM_GPUS")
            or (len([x for x in os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",") if x])
                or None))
    return {"gpus_per_task": _int("SLURM_GPUS_PER_TASK"), "gpus": gpus,
            "gpus_on_node": _int("SLURM_GPUS_ON_NODE"),
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "tasks": _int("SLURM_NTASKS"),
            "rank": _int("SLURM_PROCID"), "cpus_per_task": _int("SLURM_CPUS_PER_TASK"),
            "nodelist": os.environ.get("SLURM_JOB_NODELIST")}


STEP_CPUS_ENV = "SKQD_STEP_CPUS"


def record_step_cpus(environ=None) -> list:
    """Capture the CPU set Slurm gave this job step, BEFORE any OpenMP runtime is loaded, into the environment
    variable SKQD_STEP_CPUS (inherited by every subprocess); an existing value (set by an earlier process of the
    same step) is kept.  Returns the recorded set.

    Why (prompts/33e part 2, C2_KCHK job 59828887): jobs/gate.sbatch exports OMP_PROC_BIND=spread and
    OMP_PLACES=threads (the RUNBOOK policy).  When qiskit_aer's OpenMP runtime initialises under those variables
    it binds the initial thread to the first place, so after `import qiskit_aer` (the campaign preflight does it
    first) `os.sched_getaffinity(0)` of the main thread is 1 CPU, and every subprocess started afterwards inherits
    that 1-CPU mask -- the CPU arm ran on 1 thread although the step had 32 CPUs."""
    env = os.environ if environ is None else environ
    if not env.get(STEP_CPUS_ENV):
        try:
            env[STEP_CPUS_ENV] = ",".join(str(c) for c in sorted(os.sched_getaffinity(0)))
        except AttributeError:                                     # pragma: no cover (not Linux)
            return []
    return step_cpus(env)


def step_cpus(environ=None) -> list:
    """The step's CPU set recorded by record_step_cpus (empty when nothing was recorded)."""
    v = (os.environ if environ is None else environ).get(STEP_CPUS_ENV, "")
    return [int(x) for x in v.split(",") if x.strip()]


def restore_step_affinity(environ=None) -> dict:
    """Give the calling process (a worker started by a pinned parent) the step's CPU set back; a no-op when none
    was recorded.  Returns the CPU counts before and after."""
    before = cpu_affinity()
    cpus = step_cpus(environ)
    if cpus and before is not None and before != len(cpus):
        os.sched_setaffinity(0, cpus)
    return {"before": before, "after": cpu_affinity(), "step_cpus": len(cpus) or None}


def cpu_affinity():
    """The number of CPUs the calling thread may run on now (`os.sched_getaffinity(0)`).  NB: once an OpenMP
    runtime has initialised under OMP_PROC_BIND this is 1 on the main thread even when the step has more (see
    record_step_cpus); the step's own count is step_cpu_count().  None where the call does not exist."""
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:                                         # pragma: no cover
        return None


def step_cpu_count():
    """The CPUs this job step was granted: len(step_cpus()) when recorded, else the current affinity."""
    s = step_cpus()
    return len(s) if s else cpu_affinity()


def cpu_affinity_check(affinity, cpus_per_task, ci: bool) -> dict:
    """prompts/33e R1 (S3 clause): on the CI the step's CPU affinity must equal SLURM_CPUS_PER_TASK (a missing
    value on either side is a failure there); off the CI it is recorded only."""
    if not ci:
        return {"applies": False, "ok": True, "affinity": affinity, "slurm_cpus_per_task": cpus_per_task,
                "rule": "recorded only (not the CI)"}
    ok = affinity is not None and cpus_per_task is not None and int(affinity) == int(cpus_per_task)
    return {"applies": True, "ok": bool(ok), "affinity": affinity, "slurm_cpus_per_task": cpus_per_task,
            "rule": ("on the CI: the step's CPU count (os.sched_getaffinity(0) recorded at process start, before any "
                     "OpenMP runtime pins the main thread) == SLURM_CPUS_PER_TASK (prompts/33e R1 + part 2)")}


def gpu_telemetry(path: str = None) -> dict:
    """Peak GPU memory and mean GPU utilization from the background nvidia-smi sampler that
    jobs/gate.sbatch starts before `srun` (policy: sample
    `nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv` every 10 s).

    Lines are `<unix seconds>,<utilization>,<memory>` with or without the ` %` / ` MiB` units and
    with or without nvidia-smi's header; one line per GPU per sample.  On a laptop the file does
    not exist, and then every field is None and nothing in the gate changes."""
    path = path or os.environ.get("SKQD_GPU_TELEMETRY", GPU_TELEMETRY_FILE)
    empty = {"source": path, "samples": 0, "peak_memory_mib": None,
             "mean_utilization_pct": None, "max_utilization_pct": None}
    if not os.path.exists(path):
        return empty
    util, mem = [], []
    with open(path) as fh:
        for line in fh:
            parts = [c.strip() for c in line.split(",")]
            if len(parts) < 2:
                continue
            nums = []
            for c in parts:
                tok = c.split()[0] if c.split() else ""
                try:
                    nums.append(float(tok))
                except ValueError:
                    nums = []                 # a header line, or nvidia-smi error text
                    break
            if len(nums) >= 3:                # unix seconds, utilization, memory
                util.append(nums[-2])
                mem.append(nums[-1])
            elif len(nums) == 2:              # no timestamp column
                util.append(nums[0])
                mem.append(nums[1])
    if not util:
        return empty
    return {"source": path, "samples": len(util), "peak_memory_mib": float(max(mem)),
            "mean_utilization_pct": float(sum(util) / len(util)),
            "max_utilization_pct": float(max(util))}


def gpu_count(layout: dict = None):
    """GPUs this job actually has, from `slurm_layout()`; None when it cannot be determined.

    `layout["gpus"]` already falls back through SLURM_GPUS_ON_NODE and CUDA_VISIBLE_DEVICES,
    because Slurm did not export SLURM_GPUS_PER_TASK to the step in job 58741899 even though
    ci/poll.sh requested --gpus-per-task=1, which left this null in that run."""
    layout = slurm_layout() if layout is None else layout
    return (layout["gpus_per_task"] * (layout["tasks"] or 1)
            if layout["gpus_per_task"] else layout["gpus"])

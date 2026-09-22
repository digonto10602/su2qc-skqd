#!/usr/bin/env python3
"""
Laptop gate L4 (= gate S3 preparation) — Aer noise-model sampling of the 2x2
coarse-step circuits, decoding, yield, support recall and Ritz error, compared
with the manual's Step-4.4 yield model y = 0.82 f + (1 - f) a (f = (1 - eps)^N_CZ, a = the
decoder's random-string acceptance of the target sector, measured exhaustively here).

The 30-minute rule: the script measures the time of a small pilot (1000 shots of
one circuit) and scales the shots per circuit so that the whole run fits the
--budget-minutes (default 25); the chosen shots are recorded in the report
together with what a bigger machine would allow.

With --backend FakeFez|FakeTorino the generic depolarizing model is replaced by
NoiseModel.from_backend(backend) and every circuit is transpiled ONTO that backend, so the
calibration snapshot's per-edge CZ errors and per-qubit readout errors act on the physical
qubits the circuit really uses (prompts/12 step 4, the H0 rehearsal).  The yield model is
then the manual's y = 0.82 f + (1 - f) a with the f of gate S2D (per-edge CZ x readout of the
used patch) and the decoder's exhaustive random-string acceptance a, and the comparison is
with validation/S2D.json.

Under the Perlmutter CI (CI_GATE or SLURM_JOB_ID in the environment) the gate switches itself to
device GPU with Aer batched_shots_gpu and adds a timing ladder, because the CI passes only the gate
token: it runs `python scripts/run_gate.py L4` with no arguments.  Every physics parameter keeps its
default there, so the CI run is a parameter-for-parameter counterpart of a laptop run.  The CI runs
qiskit 1.4.3 + qiskit-aer-gpu 0.15.1; this module therefore stays on the API that both it and the
laptop's qiskit 2.5.2 accept (QuantumCircuit, transpile, AerSimulator, NoiseModel) and imports
nothing from the qiskit family at module load.

The owner's engine and HPC policy (RUNBOOK.md, "Engine and HPC policy for Perlmutter runs") governs
how the run is laid out and what it must measure:

  * the shots of a whole sector go through ONE `AerSimulator.run([...])` call
    (`skqd.circuits_qiskit.sample_many`), not a Python loop of runs, with the circuits transpiled
    once; on the GPU the simulator is the policy's
    `AerSimulator(method="statevector", device="GPU", cuStateVec_enable=True, batched_shots_gpu=True)`
    at double precision (`precision="single"` needs a tolerance check and is not used);
  * `validation/<out>.json` carries a `run` block with the engine, device, GPUs/tasks/rank, wall
    time, per-phase times (ladder, per-sector pilot, per-sector sampling, per-sector analysis),
    s/shot at every ladder point, GPU node-hours, peak GPU memory and mean GPU utilization from the
    `nvidia-smi` sampler that `jobs/gate.sbatch` runs every 10 s, all seeds and the package
    versions, plus what a full-size run of this gate would cost at the measured s/shot;
  * E(p) stays null until two task counts have been measured -- it is never estimated.

On a laptop there is no sampler file and no Slurm environment, so those fields are null and the run
is otherwise unchanged.

Usage: python scripts/laptop_L4_aer_noise.py [--p2 3e-3] [--p1 3e-4] [--pro 0.01]
                                             [--budget-minutes 25] [--pilot-shots 1000]
                                             [--min-shots 500] [--gpu] [--batched-shots-gpu]
                                             [--timing-ladder 20 100 500 1000]
                                             [--backend FakeFez|FakeTorino] [--out L4_fez]
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import certify, ritz, support_metrics, yield_model  # noqa: E402

from gate_H0P import YIELD_MODEL_NAME, random_acceptance  # noqa: E402  (same a as gate H0P)
from gate_S2D import YIELD_FACTOR, analyse_on_backend  # noqa: E402  (same f as gate S2D)


def ci_context() -> dict:
    """Non-empty when this run is the Perlmutter CI job rather than a laptop run.

    The CI passes only the gate token: it runs `python scripts/run_gate.py L4` with no extra
    arguments (ci/README.md), so the gate has to choose GPU mode itself.  CI_GATE is set by the
    poller; SLURM_JOB_ID is the fallback for a hand-submitted Slurm job."""
    ctx = {k: os.environ[k] for k in ("CI_GATE", "SLURM_JOB_ID", "SLURM_JOB_NODELIST")
           if os.environ.get(k)}
    return ctx if ("CI_GATE" in ctx or "SLURM_JOB_ID" in ctx) else {}


def qiskit_versions() -> dict:
    """Recorded in validation/L4.json: the CI runs qiskit 1.4.3, the laptop 2.5.2."""
    out = {}
    for mod in ("qiskit", "qiskit_aer"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception as exc:                                  # pragma: no cover
            out[mod] = f"unavailable: {exc}"
    return out


SAMPLE_SEED = 11        # Aer seed_simulator and seed_transpiler of every sample here
S2D_SEED_TRANSPILER = 7  # the seed gate S2D uses for its f analysis (kept identical)
GPU_TELEMETRY_FILE = "gpu_telemetry.csv"   # written by jobs/gate.sbatch, read back below


def slurm_layout() -> dict:
    """GPUs, tasks and rank of this job, from Slurm's own environment (RUNBOOK.md asks every GPU
    job to record them).  All None on a laptop, where none of these variables exist."""
    def _int(name):
        v = os.environ.get(name)
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    return {"gpus_per_task": _int("SLURM_GPUS_PER_TASK"), "tasks": _int("SLURM_NTASKS"),
            "rank": _int("SLURM_PROCID"), "cpus_per_task": _int("SLURM_CPUS_PER_TASK"),
            "nodelist": os.environ.get("SLURM_JOB_NODELIST")}


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


def s2d_shots_per_sector() -> int:
    """The per-sector shot quota at which the operational S1 criterion holds on the device model
    (`data/S2D_recall_at_f.json`: 32 circuits x 6250 shots), used below to extrapolate what a
    full-size run of this gate would cost from the measured s/shot.  Never hard-coded: it is read
    from the data file, and is None when the file is absent."""
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data",
                      "S2D_recall_at_f.json")
    try:
        import json
        with open(fp) as fh:
            res = json.load(fh)["results"]
        e = next(iter(res.values()))
        return int(e["circuits"]) * int(e["shots_per_circuit"])
    except Exception:                                              # pragma: no cover
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p2", type=float, default=3e-3)
    ap.add_argument("--p1", type=float, default=3e-4)
    ap.add_argument("--pro", type=float, default=0.01)
    ap.add_argument("--budget-minutes", type=float, default=25.0)
    ap.add_argument("--pilot-shots", type=int, default=1000, help="shots of the pilot used to time one circuit")
    ap.add_argument("--min-shots", type=int, default=500, help="floor for the shots per circuit")
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--batched-shots-gpu", action="store_true",
                    help="Aer batched_shots_gpu (GPU only): many shots of one circuit per batch")
    ap.add_argument("--gpu-memory-bytes", type=float, default=8e9,
                    help="GPU memory the batched sampling may assume (default 8e9, far below an "
                         "A100's 80 GB: the noise model and any co-tenant job also need room)")
    ap.add_argument("--timing-ladder", type=int, nargs="*", default=[], metavar="SHOTS",
                    help="before sampling, time one circuit at each of these shot counts and record "
                         "s/shot, so the full run can be sized from a measurement")
    ap.add_argument("--backend", default=None, choices=("FakeFez", "FakeTorino"),
                    help="calibration snapshot: NoiseModel.from_backend + transpilation onto that backend")
    ap.add_argument("--out", default="L4", help="name of validation/<out>.json and reports/<out>_aer_noise.md")
    ci = ci_context()
    if ci:
        # The CI runs `python scripts/run_gate.py L4` with no arguments, so CI mode changes
        # ONLY the device, the GPU batching and the timing ladder: every physics parameter keeps
        # the script's own default, which makes the GPU run a parameter-for-parameter counterpart
        # of a laptop run (pilot 1000, min-shots 500 -- the "full 1000 + 500 shot run").
        #
        # Deliberately NOT the shot budget of the 2026-09-14 run (validation/L4.json: p2 1e-3,
        # pilot 20, min-shots 1, budget 12 min, 8 shots x 20 circuits and 22 x 8, 1012 s at
        # 2.16 / 1.98 s per shot).  That run sampled the DENSE generic-synthesis circuits at
        # 35670 CZ; since the structured circuits of gate S2 became the CircuitFactory default
        # (2026-09-15, commit 5d60461) the same script samples 288 CZ at 0.046 s/shot on the same
        # laptop CPU -- 124x fewer CZ, 47x faster -- so that budget is about a second of GPU work
        # and would measure nothing.  The ladder is what sizes the larger runs.
        ap.set_defaults(gpu=True, batched_shots_gpu=True,
                        timing_ladder=[20, 100, 500, 1000, 2000])
    args = ap.parse_args()
    t0 = time.time()
    R = GateResult(args.out, "Aer noise-model sampling at 2x2 (S3 preparation)"
                   + (f", calibration snapshot {args.backend}" if args.backend else ""))
    from skqd import circuits_qiskit as cq
    device = "GPU" if args.gpu else "CPU"
    backend = None
    if args.backend:
        from qiskit import transpile
        from qiskit_aer.noise import NoiseModel
        from qiskit_ibm_runtime.fake_provider import FakeFez, FakeTorino
        backend = {"FakeFez": FakeFez, "FakeTorino": FakeTorino}[args.backend]()
    g2 = 4.0
    M = Model(2)
    F = CircuitFactory(M, g2)
    codec = Codec(M.basis)
    n = codec.n_qubits
    nm = NoiseModel.from_backend(backend) if backend is not None else \
        cq.generic_noise_model(args.p1, args.p2, args.pro)
    bsg = bool(args.batched_shots_gpu and device == "GPU")
    if ci:
        print(f"CI run ({', '.join(f'{k}={v}' for k, v in ci.items())}): device {device}, "
              f"batched_shots_gpu {bsg}, qiskit {qiskit_versions()}", flush=True)

    # Timing ladder: one circuit, several shot counts.  The pilot below measures s/shot at a
    # single point, which is enough to fit a run into a budget but NOT enough to size a run at a
    # different shot count -- on a GPU the per-shot cost falls as the batch grows, so the full
    # 1000 + 500 shot run cannot be sized from a 20-shot pilot.
    ladder = []
    batching = {}       # what sample_many actually did, per sector
    phases = {}          # per-phase wall times, recorded per the HPC policy
    t_ladder = time.time()
    if args.timing_ladder:
        ref0 = M.reference(g2, 0)
        g0 = F.coarse_step(references(M.basis, 0)[0], 1, ref0.dt)
        # one discarded sample first: the first call pays the transpiler and simulator warm-up
        # (on the laptop CPU 1.4 s against 0.18 s for the next call; on a GPU it is the CUDA
        # context), which would otherwise land entirely on the smallest ladder point and make the
        # per-shot cost there look an order of magnitude worse than it is.
        tw = time.time()
        cq.sample(g0, n, max(1, min(args.timing_ladder)), noise_model=nm, device=device,
                  backend=backend, batched_shots_gpu=bsg, seed=SAMPLE_SEED)
        warmup_s = time.time() - tw
        print(f"timing ladder: warm-up discarded ({warmup_s:.2f} s)", flush=True)
        for s in args.timing_ladder:
            tt = time.time()
            cq.sample(g0, n, int(s), noise_model=nm, device=device, backend=backend,
                      batched_shots_gpu=bsg, seed=SAMPLE_SEED)
            el = time.time() - tt
            ladder.append({"shots": int(s), "seconds": el, "seconds_per_shot": el / int(s)})
            print(f"timing ladder: {s:>6} shots -> {el:7.2f} s ({el / int(s):.5f} s/shot)", flush=True)
    phases["ladder_s"] = time.time() - t_ladder if args.timing_ladder else 0.0
    rows = []
    for twoB in (0, 2):
        ref = M.reference(g2, twoB)
        refs = references(M.basis, twoB)
        circuits = [(r, k, F.coarse_step(r, k, ref.dt)) for r in refs for k in (1, 2, 3, 4)]
        # pilot timing -> shots per circuit within the budget
        tp = time.time()
        cq.sample(circuits[0][2], n, args.pilot_shots, noise_model=nm, device=device, backend=backend,
                  batched_shots_gpu=bsg, seed=SAMPLE_SEED)
        pilot_s = time.time() - tp
        phases[f"pilot_s|B={twoB // 2}"] = pilot_s
        t_per_shot = pilot_s / args.pilot_shots
        print(f"B={twoB // 2}: pilot {args.pilot_shots} shots -> {t_per_shot:.3f} s/shot", flush=True)
        budget_s = args.budget_minutes * 60 / 2  # half the budget per sector
        shots = int(min(20000, max(args.min_shots, budget_s / (t_per_shot * len(circuits)))))
        print(f"B={twoB // 2}: {len(circuits)} circuits, {shots} shots/circuit (min-shots {args.min_shots})", flush=True)
        # the decoder's random-string acceptance a of this sector, exhaustive over all 2^n
        # strings: the "garbage that decodes as valid" term of the manual's yield model
        ra = random_acceptance(codec, twoB)
        a = ra["fraction"]
        prob = np.zeros(M.basis.dim)
        prob[ref.indices] = np.abs(ref.ground) ** 2
        acc_all, rej_all, total = {}, {}, 0
        # ONE AerSimulator.run([...]) call for all circuits of the sector, per the owner's HPC
        # policy (RUNBOOK.md: "submit many circuits in ONE run([...]) call ... rather than a
        # Python loop of run calls; transpile once and reuse").  A loop of cq.sample calls paid
        # the simulator/transpiler set-up per circuit (1.4 s for the first call against 0.18 s
        # for the next on this laptop CPU) and on a GPU re-entered the CUDA context each time.
        # One run() call per sector is the policy, but the allocation grows as
        # experiments x shots x 2^n: gate L4's first GPU run chose 20000 shots (the device is
        # fast) and 20 x 20000 at 12 qubits exhausted an 80 GB A100 (job 58737320).  On the GPU
        # the shots per call are therefore bounded up front, and sample_many halves adaptively if
        # even that does not fit.  On the CPU no bound is imposed and the call stays single.
        chunk = cq.shot_chunk_for(n, len(circuits), args.gpu_memory_bytes) \
            if device == "GPU" else None
        t_samp = time.time()
        counts_list, batch_info = cq.sample_many(
            [g for _, _, g in circuits], n, shots, noise_model=nm, device=device,
            backend=backend, batched_shots_gpu=bsg, seed=SAMPLE_SEED,
            max_shots_per_run=chunk, return_info=True)
        phases[f"sampling_s|B={twoB // 2}"] = time.time() - t_samp
        batching[f"B={twoB // 2}"] = batch_info
        print(f"B={twoB // 2}: sampled {len(circuits)} circuits x {shots} shots in "
              f"{batch_info['run_calls']} run() call(s) (<= {batch_info['max_experiments']} "
              f"circuits x {batch_info['max_shots_per_run']} shots each, "
              f"{len(batch_info['oom_retries'])} OOM retries) "
              f"({phases[f'sampling_s|B={twoB // 2}']:.1f} s)", flush=True)
        t_ana = time.time()
        for counts in counts_list:
            acc, rej = codec.decode_counts(counts, target_twoB=twoB)
            for kk, c in acc.items():
                acc_all[kk] = acc_all.get(kk, 0) + c
            for kk, c in rej.items():
                rej_all[kk] = rej_all.get(kk, 0) + c
            total += shots
        if backend is not None:
            # the f of gate S2D: per-edge CZ errors and per-qubit readout errors of the patch
            # the transpiler chose on this calibration snapshot
            an = [analyse_on_backend(transpile(cq.ir_to_qiskit(g, n, measure=True), backend=backend,
                                               optimization_level=3,
                                               seed_transpiler=S2D_SEED_TRANSPILER), backend)
                  for _, _, g in circuits]
            czs = [e["cz"] for e in an]
            f_model = float(np.mean([e["f"] for e in an]))
            readout_factor = YIELD_FACTOR
            proxy_name = (f"{YIELD_MODEL_NAME}, f from the {args.backend} calibration (gate S2D), "
                          f"a = {a:.5f} exhaustive")
        else:
            czs = [cq.transpile_counts(g, n, optimization_level=1)["cz"] for _, _, g in circuits]
            # f = (1-p2)^<CZ> for the two-qubit gates; the readout survival (1-p_ro)^n is the 0.82 factor
            f_model = float(np.mean([(1 - args.p2) ** c for c in czs]))
            readout_factor = (1 - args.pro) ** n
            proxy_name = f"(1-p_ro)^n f + (1-f) a, f = <(1-p2)^CZ>, a = {a:.5f} exhaustive"
        predicted_clean = readout_factor * f_model            # the first term alone (old model)
        predicted = yield_model(f_model, a, readout_factor)   # manual Step 4.4, both terms
        cz = float(np.mean(czs))
        y = sum(acc_all.values()) / total
        B = np.array(sorted(set(acc_all) | set(refs)))
        res = ritz(M.H(g2), B)
        met = support_metrics(B, prob, 1e-3)
        cert = certify(res, ref.E0, float(ref.energies[1]))
        phases[f"analysis_s|B={twoB // 2}"] = time.time() - t_ana
        rows.append([f"B={twoB // 2}", len(circuits), shots, f"{cz:.0f}", f"{f_model:.3f}",
                     f"{a:.5f}", f"{predicted_clean:.3f}", f"{predicted:.3f}", f"{y:.3f}",
                     f"{y / predicted_clean:.2f}", f"{y / predicted:.2f}", len(B),
                     f"{res.ER - ref.E0:.1e}", f"{met['recall']:.2f}", met["false_positives"],
                     f"[{cert.weinstein[0]:.4f}, {cert.weinstein[1]:.4f}]", str(rej_all)])
        R.add(f"B={twoB // 2}: measured yield within a factor 3 of the model {proxy_name}",
              f"{y:.3f} vs {predicted:.3f} (ratio {y / predicted:.2f}; the first term alone, "
              f"{readout_factor:.4f} f = {predicted_clean:.3f}, gives {y / predicted_clean:.2f})",
              "ratio in [1/3, 3] (the model is a rough proxy)", predicted / 3 <= y <= 3 * predicted + 1e-9)
        R.add(f"B={twoB // 2}: exact E0 inside the Weinstein interval", f"{ref.E0:.4f}", "inside",
              cert.weinstein[0] - 1e-9 <= ref.E0 <= cert.weinstein[1] + 1e-9)
        R.data[f"B={twoB // 2}"] = dict(shots=shots, circuits=len(circuits), cz=cz, yield_=y, size=len(B), err=res.ER - ref.E0,
                                       recall=met["recall"], t_per_shot=t_per_shot,
                                       pilot_shots=args.pilot_shots, min_shots=args.min_shots,
                                       f_model=f_model, garbage_acceptance=float(a),
                                       yield_model=YIELD_MODEL_NAME, readout_factor=float(readout_factor),
                                       predicted_yield=predicted,
                                       ratio_measured_over_predicted=float(y / predicted),
                                       predicted_yield_clean_term_only=predicted_clean,
                                       ratio_measured_over_clean_term_only=float(y / predicted_clean),
                                       random_acceptance=ra,
                                       proxy=proxy_name, total_shots=total,
                                       rejections={k: int(v) for k, v in rej_all.items()},
                                       weinstein=[float(cert.weinstein[0]), float(cert.weinstein[1])],
                                       exact_E0=float(ref.E0))
    wall = time.time() - t0
    layout = slurm_layout()
    tele = gpu_telemetry()
    # the best measured cost per shot on THIS device: the ladder's cheapest point if a ladder was
    # run (on a GPU the per-shot cost falls as the batch grows), otherwise the pilot
    best = min([e["seconds_per_shot"] for e in ladder], default=None)
    pilot_sps = {f"B={tb // 2}": R.data[f"B={tb // 2}"]["t_per_shot"] for tb in (0, 2)}
    if best is None:
        best = min(pilot_sps.values())
        best_from = "pilot"
    else:
        best_from = f"timing ladder at {max(e['shots'] for e in ladder)} shots"
    # what a full-size run of THIS gate would cost: the same 2x2 circuits at the per-sector shot
    # quota of data/S2D_recall_at_f.json, at the measured s/shot.  The 2x3 cost of gate S3 is NOT
    # extrapolated here: 20 qubits is a different simulation, so a 2x2 ladder cannot size it.
    q = s2d_shots_per_sector()
    full = {"definition": ("the same 2x2 circuits at the per-sector shot quota of "
                           "data/S2D_recall_at_f.json (32 circuits x 6250 shots), both sectors"),
            "shots_per_sector": q, "sectors": 2,
            "shots": None if q is None else 2 * q,
            "seconds_per_shot_used": best, "seconds_per_shot_from": best_from,
            "seconds": None if q is None else 2 * q * best,
            "hours": None if q is None else 2 * q * best / 3600.0}
    gpus = (layout["gpus_per_task"] or 0) * (layout["tasks"] or 1) if layout["gpus_per_task"] else None
    R.data["run"] = {
        "engine": "Qiskit Aer statevector" + (" (GPU, cuStateVec/batched shots)" if device == "GPU"
                                              else " (CPU)"),
        "device": device,
        "batched_shots_gpu": bsg,
        "cu_statevec_enable": device == "GPU",
        "precision": "double",
        "active_qubits": n,
        "ci": ci or None,
        "slurm": layout,
        "gpus": gpus,
        "tasks": layout["tasks"],
        "rank": layout["rank"],
        "wall_seconds": wall,
        "gpu_node_hours": None if not gpus else gpus * wall / 3600.0,
        "parallel_efficiency_Ep": None,
        "parallel_efficiency_note": ("E(p) needs T_1 and T_p from at least two task counts; this "
                                     "run is a single task, so it is not measured"),
        "phases_s": phases,
        "gpu_telemetry": tele,
        "versions": qiskit_versions(),
        "seeds": {"aer_seed_simulator": SAMPLE_SEED, "seed_transpiler": SAMPLE_SEED,
                  "s2d_analysis_seed_transpiler": S2D_SEED_TRANSPILER},
        "shots_per_circuit": {r[0]: int(r[2]) for r in rows},
        "seconds_per_shot_pilot": pilot_sps,
        "timing_ladder": ladder,
        "batching": batching,
        "gpu_memory_bytes_assumed": args.gpu_memory_bytes,
        "full_size_estimate": full,
        "pilot_shots": args.pilot_shots,
        "min_shots": args.min_shots,
        "budget_minutes": args.budget_minutes,
        "noise": ({"backend": args.backend} if backend is not None
                  else {"p1": args.p1, "p2": args.p2, "p_ro": args.pro}),
    }
    R.runtime_s = wall
    R.save()
    run = R.data["run"]
    def _fmt(x, fmt="{:.3g}"):
        return "not measured" if x is None else fmt.format(x)
    gpus_txt = ("none (CPU run)" if device != "GPU" and gpus is None else _fmt(gpus, "{:d}"))
    nodeh_txt = ("0 (CPU run)" if not gpus and device != "GPU" else
                 _fmt(run["gpu_node_hours"], "{:.4f}"))
    mem_txt = ("not measured (no nvidia-smi sampler file in the working directory)"
               if tele["peak_memory_mib"] is None else f"{tele['peak_memory_mib']:.0f} MiB")
    util_txt = ("not measured" if tele["mean_utilization_pct"] is None else
                f"{tele['mean_utilization_pct']:.1f} % mean, {tele['max_utilization_pct']:.0f} % peak "
                f"over {tele['samples']} nvidia-smi samples")
    policy_line = (
        f"**Engine and resources** (RUNBOOK.md policy): engine {run['engine']}, qiskit "
        f"{run['versions']['qiskit']} / aer {run['versions']['qiskit_aer']}, device {device}, "
        f"GPUs {gpus_txt}, tasks {_fmt(layout['tasks'], '{:d}')}, walltime "
        f"{wall:.0f} s, E(p) {_fmt(run['parallel_efficiency_Ep'])} ({run['parallel_efficiency_note']}), "
        f"GPU node-hours used {nodeh_txt}, peak GPU memory {mem_txt}, GPU utilization {util_txt}. "
        f"Cheapest measured cost {best:.5f} s/shot ({best_from}), so a full-size run of this gate "
        f"({full['definition']}, {_fmt(full['shots'], '{:d}')} shots) would take "
        f"{_fmt(full['hours'], '{:.2f}')} h on this device.  The 2x3 cost of gate S3 is not "
        f"extrapolated from this ladder: 20 qubits is a different simulation.")
    noise_desc = (f"NoiseModel.from_backend({args.backend}) (calibration snapshot: per-edge CZ, per-qubit "
                  f"readout, T1/T2), circuits transpiled onto {args.backend} at optimization level 3, seed 7"
                  if backend is not None else f"generic depolarizing model p1 = {args.p1}, p2 = {args.p2}, readout {args.pro}")
    write_report(f"{args.out}_aer_noise.md", f"""# Laptop gate {args.out} — Aer noise-model sampling at 2x2 (S3 preparation)

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/laptop_L4_aer_noise.py`, {noise_desc},
device {device}, budget {args.budget_minutes} min, pilot {args.pilot_shots} shots, min-shots {args.min_shots}.  {env_block()}  Runtime {R.runtime_s:.0f} s.

{md_table(["sector", "circuits", "shots/circuit", "mean CZ", "f (model)", "a (garbage)",
           f"predicted {readout_factor:.4f} f (first term only)",
           f"predicted {readout_factor:.4f} f + (1−f) a", "measured yield",
           "measured / first term", "measured / full model", "\\|B\\|", "E_R − E_0", "recall 99.9%",
           "fp", "Weinstein", "rejections"], rows)}

{R.criteria_table()}

{policy_line}

{("" if not ladder else "Timing ladder on one circuit, device " + device
   + (" with batched_shots_gpu" if bsg else "") + " (the per-shot cost falls as the batch grows, so a "
   "run at a different shot count cannot be sized from a single pilot point):\n\n"
   + md_table(["shots", "seconds", "s/shot"],
              [[str(e["shots"]), f"{e['seconds']:.2f}", f"{e['seconds_per_shot']:.5f}"] for e in ladder])
   + "\n")}
Note: at 2x2 the sectors saturate (38 and 20 states), so the Ritz error is a consistency check only (manual
Step 9.1).  The prediction the criterion uses is the manual's Step-4.4 yield model with BOTH its terms,
y = {YIELD_MODEL_NAME} ("the accepted-shot yield is ~ 0.82 f plus the garbage that decodes as valid",
`skqd.skqd.yield_model`): a = the decoder's random-string acceptance of the sector, measured exhaustively
over all {2 ** n} bit strings ({rows[0][5]} for B=0, {rows[1][5]} for B=1), and with --backend f is the
0.82 f-fraction of gate S2D computed from the same calibration snapshot as `validation/S2D.json`.  The column
"measured / 0.82 f" is the first term alone, the model this gate used before prompts/14, kept for comparison.
The ratio against the full model is the H0 rehearsal number (how well the manual's yield model describes a
full device simulation).
""")
    print(R.criteria_table())
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())

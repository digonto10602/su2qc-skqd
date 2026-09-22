#!/usr/bin/env python3
"""
Gate S3 as a one-command job (prompts/13 step 4): device-model sampling of the exact
structured circuits of ONE lattice and ONE sector, decoding, and the S3 criterion.

Two device models, selected by the arguments:

  --backend FakeFez|FakeTorino   Heron-class superconducting snapshot (the 2x2 path):
                                 circuits are transpiled onto the snapshot and sampled
                                 with NoiseModel.from_backend, so the per-edge CZ errors
                                 and per-qubit readout errors act on the physical qubits
                                 the circuit really uses.
  (no --backend)                 all-to-all trapped ion (the 2x3 path, prompts/12): basis
                                 ['rz','rx','ry','rzz'], no coupling map, and a depolarizing
                                 model built from the DECLARED inputs --eps2/--eps1/--eps-ro
                                 (vendor-class specifications, recorded in the JSON).

S3 criterion (manual Step 10 / gate S1): recall of the 99.9 % support of the exact sector
ground state >= 0.9 with the production shot budget.

CALIBRATION MODE (--calibration, and automatically under the Perlmutter CI).
-----------------------------------------------------------------------------
The CI passes only the gate token -- it runs `python scripts/run_gate.py S3` with no arguments
(ci/README.md, jobs/gate.sbatch) -- so this script recognises the CI itself (CI_GATE, else
SLURM_JOB_ID; `skqd.hpc.ci_context`, shared with gate L4) and switches to Aer on the GPU with the
policy's options, a timing ladder and the nvidia-smi telemetry.

The first S3 job on Perlmutter is a REDUCED-SIZE CALIBRATION, not production
(prompts/18 sec. 2.1, and RUNBOOK.md: "the first run of any new heavy workload is a calibration at
reduced size").  In calibration mode the gate's criteria are therefore about COMPUTE THROUGHPUT at
20 qubits -- device, ladder, memory fit, walltime -- and the S3 recall criterion is NOT evaluated:
the recall and yield measured at a calibration shot count are recorded as measurements, never as a
gate result.  L4's 19.8x GPU speed-up must not be extrapolated to this gate either: L4 is 12
qubits, S3 is 20, so each statevector is 256x larger and, at the 3.5x model factor measured in
L4 job 58741899 (8.0 GB predicted for its 20x6103 chunk against 27915 MiB measured), a single
20-qubit circuit holds only about 476 shots per `run` call inside the default 8 GB model budget.
That is what the ladder measures.

Engine and HPC policy (RUNBOOK.md, "Engine and HPC policy for Perlmutter runs"):
  * the shots of the whole circuit set go through `skqd.circuits_qiskit.sample_many`, i.e. ONE
    `AerSimulator.run([...])` call, chunked by `shot_chunk_for` so the batched GPU allocation
    stays inside --gpu-memory-bytes, and not a Python loop of `run` calls;
  * on the GPU the simulator is the policy's `AerSimulator(method="statevector", device="GPU",
    cuStateVec_enable=True, batched_shots_gpu=True)` at double precision;
  * `validation/<gate>.json` carries a `run` block with engine, device, GPUs/tasks/rank, wall
    time, per-phase timings, seconds per shot at every ladder point, peak GPU memory and mean GPU
    utilization from the sampler `jobs/gate.sbatch` writes, all seeds and the package versions;
  * E(p) stays null until two task counts have been measured -- it is never estimated.

The CI runs qiskit 1.4.3 + qiskit-aer-gpu 0.15.1 and the laptop 2.5.2 + 0.17.2, so this module
stays on the API both accept (QuantumCircuit, transpile, AerSimulator, NoiseModel, run([...]),
Result.get_counts(i)) and imports nothing from the qiskit family at module load.

Usage:
  python scripts/s3_device_model.py --lattice 3 --sector 1 --shots-per-sector 24 --tag smoke
  python scripts/s3_device_model.py --lattice 3 --sector 0 --shots-per-sector 200000 --tag B0_r1
  python scripts/s3_device_model.py --lattice 2 --sector 0 --backend FakeFez --tag 2x2
  python scripts/s3_device_model.py --calibration --budget-minutes 40 --ladder-auto --tag calib
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.circuits_qiskit import shot_chunk_for  # noqa: E402  (pure arithmetic, imports no qiskit)
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.hpc import (ci_context, gpu_count, gpu_telemetry,  # noqa: E402
                      qiskit_versions, slurm_layout)
from skqd.krylov import references  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import certify, ritz, shot_rule, support_metrics  # noqa: E402

from h0_build_circuits import repeated_coarse_step  # noqa: E402

RECALL_MIN = 0.9             # gate S3 / S1 criterion
EPS_SUPPORT = 1e-3           # the 99.9 % support
YIELD_FACTOR = 0.82
PRODUCTION_SHOTS_PER_SECTOR = 2e5     # manual Step 9.2

# The factor by which the `shot_chunk_for` allocation model under-estimated the real peak GPU
# memory in gate L4's GPU run (job 58741899: 8.0 GB predicted for the 20 x 6103 chunk, 27915 MiB
# measured).  Recorded, not applied: the default --gpu-memory-bytes 8e9 is a model budget, so the
# real budget it implies is 8 GB x this factor, comfortably inside an A100's 80 GB.
MEASURED_MEMORY_MODEL_FACTOR = 3.5
L4_SPEEDUP_NOTE = ("gate L4's 19.8x GPU speed-up is at 12 qubits and must NOT be extrapolated to "
                   "this gate: at 20 qubits each statevector is 256x larger and the run is "
                   "chunk-dominated (prompts/18 sec. 2.1)")


def s2d_cost():
    """The 2x3 per-shot cost gate S2D measured (10 shots in one call), for comparison."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation", "S2D.json")
    try:
        import json
        d = json.load(open(p))["data"]["per_shot_cost_2x3"]
        return {"seconds_per_shot": d["seconds_per_shot"], "shots_per_simulator_call": d["shots_timed"],
                "source": "validation/S2D.json"}
    except Exception:
        return None


def pick_device(requested: str):
    from qiskit_aer import AerSimulator
    avail = list(AerSimulator().available_devices())
    if requested == "CPU":
        return "CPU", avail
    if "GPU" in avail:
        return "GPU", avail
    if requested == "GPU":
        raise SystemExit(f"GPU requested but Aer reports devices {avail}")
    return "CPU", avail


def default_ladder(n_qubits: int, max_bytes: float) -> list:
    """Timing-ladder shot counts for a lattice of `n_qubits`, derived from the memory bound.

    NOT gate L4's ladder ([20, 100, 500, 1000, 2000]): at 12 qubits one `run` call holds 122 070
    shots of a single circuit inside the 8 GB model budget, so every L4 ladder point lives in the
    same single-call regime and measures only how the fixed per-call cost amortises.  At 20 qubits
    the same budget holds c = `shot_chunk_for(20, 1, 8e9)` = 476 shots, so a production run is
    chunk-dominated, and the ladder has to measure BOTH regimes:

      c/10, c/2   inside one chunk: how the fixed per-call cost amortises as the batch grows;
      c           the largest batch one `run` call may take under the memory model (the knee);
      3c          three chunked calls: the regime production is in, which L4 could not measure.

    The points are derived from `shot_chunk_for` rather than written down, so they follow
    --gpu-memory-bytes and the lattice instead of going stale."""
    c = shot_chunk_for(n_qubits, 1, max_bytes)
    pts = sorted({max(1, c // 10), max(2, c // 2), c, 3 * c})
    return [int(x) for x in pts]


def gate_name_for(tag: str) -> str:
    """validation/<gate>.json and reports/<gate>_device_model.md for this run.

    An empty --tag means the gate's own slot, `S3`, which is what `run_gate.py S3` (and therefore
    the CI) reads; any other tag keeps the run in its own file, as the smoke and per-sector
    production runs do."""
    return f"S3_{tag}" if tag else "S3"


def build_parser(ci: dict = None) -> argparse.ArgumentParser:
    """The command line, with the CI defaults applied when `ci` is non-empty.

    Split out of `main` so that the CI-mode defaults can be checked on a machine without a GPU
    (tests/test_s3_ci_mode.py); `ci` defaults to `ci_context()`."""
    ci = ci_context() if ci is None else ci
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice", type=int, default=3, help="Lx of the 2 x Lx ladder")
    ap.add_argument("--sector", type=int, default=0, choices=(0, 1), help="baryon number B")
    ap.add_argument("--shots-per-sector", type=float, default=PRODUCTION_SHOTS_PER_SECTOR)
    ap.add_argument("--kmax", type=int, default=4)
    ap.add_argument("--reps", type=int, default=1, help="repetitions r of the coarse step (U^r)")
    ap.add_argument("--g2", type=float, default=4.0)
    ap.add_argument("--backend", default=None, choices=("FakeFez", "FakeTorino"))
    ap.add_argument("--eps2", type=float, default=1e-3, help="DECLARED two-qubit (RZZ) error")
    ap.add_argument("--eps1", type=float, default=1e-4, help="DECLARED one-qubit error")
    ap.add_argument("--eps-ro", type=float, default=2e-3, help="DECLARED readout error")
    ap.add_argument("--device", default="auto", choices=("auto", "GPU", "CPU"))
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--p", type=float, default=1e-3, help="ideal probability in the shot rule")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--conf", type=float, default=0.95)
    ap.add_argument("--tag", default="run",
                    help="validation/S3_<tag>.json; an empty tag writes validation/S3.json "
                         "(what the CI needs, since run_gate.py reads validation/<token>.json)")
    # --- GPU batching, timing ladder and budget (the CI / calibration hooks) -------------------
    ap.add_argument("--gpu-memory-bytes", type=float, default=8e9,
                    help="GPU memory one batched run() call may assume (default 8e9; the measured "
                         f"model factor is ~{MEASURED_MEMORY_MODEL_FACTOR}x, so this is a ~28 GB "
                         "real budget on an 80 GB A100)")
    ap.add_argument("--max-shots-per-run", type=int, default=0,
                    help="override the chunk size from shot_chunk_for (0 = derive it on the GPU, "
                         "no chunking on the CPU)")
    ap.add_argument("--timing-ladder", type=int, nargs="*", default=[], metavar="SHOTS",
                    help="time ONE circuit at each of these shot counts before sampling")
    ap.add_argument("--ladder-auto", action="store_true",
                    help="use default_ladder(n_qubits, --gpu-memory-bytes) when no explicit "
                         "--timing-ladder is given")
    ap.add_argument("--budget-minutes", type=float, default=0.0,
                    help="wall-clock budget for the whole job (0 = no budget, the laptop default). "
                         "The shots per circuit are reduced to fit what is left of it.")
    ap.add_argument("--ladder-budget-minutes", type=float, default=0.0,
                    help="share of the budget the timing ladder may use (0 = one third of it)")
    ap.add_argument("--min-shots", type=int, default=1, help="floor for the shots per circuit")
    ap.add_argument("--walltime-budget-s", type=float, default=0.0,
                    help="calibration criterion: the job must finish inside this wall time "
                         "(0 = not checked)")
    ap.add_argument("--calibration", action="store_true",
                    help="throughput calibration: the criteria are device/ladder/memory/walltime "
                         "and the S3 recall criterion is NOT evaluated")
    if ci:
        # The CI runs `python scripts/run_gate.py S3` with no arguments, so the reduced-size
        # calibration of prompts/18 sec. 2.1 has to be the DEFAULT here: one lattice, one sector,
        # one repetition, a few thousand shots, the ladder and the telemetry.  Explicit arguments
        # still win (argparse defaults), so a hand-submitted Slurm job can ask for anything else.
        #
        # Budget: the allowlist line is `S3 04:00:00 1`, but run_gate.py kills a gate after its
        # default --timeout 3600 s, so the calibration is sized to finish well inside one hour:
        # 40 minutes of budget (transpilation + ladder + sampling), of which the ladder may take
        # 12, leaves the analysis and the report inside the timeout with room to spare.
        ap.set_defaults(lattice=3, sector=0, reps=1, kmax=4, shots_per_sector=3200.0,
                        calibration=True, ladder_auto=True, budget_minutes=40.0,
                        ladder_budget_minutes=12.0, min_shots=8, walltime_budget_s=3300.0,
                        tag="")
    return ap


def main():
    ci = ci_context()
    ap = build_parser(ci)
    args = ap.parse_args()
    t0 = time.time()
    deadline = t0 + 60.0 * args.budget_minutes if args.budget_minutes > 0 else None
    ladder_deadline = None
    if deadline is not None:
        lb = args.ladder_budget_minutes if args.ladder_budget_minutes > 0 else args.budget_minutes / 3.0
        ladder_deadline = t0 + 60.0 * lb

    from qiskit import transpile

    from skqd import circuits_qiskit as cq

    device, avail = pick_device(args.device)
    want_gpu = bool(ci or args.device == "GPU")
    bsg = device == "GPU"
    twoB = 2 * args.sector
    M = Model(args.lattice)
    F = CircuitFactory(M, args.g2)
    codec = Codec(M.basis)
    n = codec.n_qubits
    ref = M.reference(args.g2, twoB)
    refs = references(M.basis, twoB)
    circuits = [(r, k) for r in refs for k in range(1, args.kmax + 1)]

    gate_name = gate_name_for(args.tag)
    title = (f"GPU throughput calibration of the 2x{args.lattice} B={args.sector} circuit set "
             f"(reduced size; the S3 recall criterion is NOT evaluated)" if args.calibration else
             f"Device-model sampling of the 2x{args.lattice} B={args.sector} circuit set (gate S3)")
    R = GateResult(gate_name, title)
    if ci:
        print(f"CI run ({', '.join(f'{k}={v}' for k, v in ci.items())}): device {device} "
              f"(available {avail}), batched_shots_gpu {bsg}, qiskit {qiskit_versions()}",
              flush=True)
    backend = None
    if args.backend:
        from qiskit_aer.noise import NoiseModel
        from qiskit_ibm_runtime.fake_provider import FakeFez, FakeTorino
        backend = {"FakeFez": FakeFez, "FakeTorino": FakeTorino}[args.backend]()
        nm = NoiseModel.from_backend(backend)
        model_name = f"NoiseModel.from_backend({args.backend}) (calibration snapshot)"
        basis = None
    else:
        from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
        basis = ["rz", "rx", "ry", "rzz"]
        nm = NoiseModel(basis_gates=basis)
        nm.add_all_qubit_quantum_error(depolarizing_error(args.eps2, 2), ["rzz"])
        nm.add_all_qubit_quantum_error(depolarizing_error(args.eps1, 1), ["rz", "rx", "ry"])
        nm.add_all_qubit_readout_error(ReadoutError([[1 - args.eps_ro, args.eps_ro],
                                                     [args.eps_ro, 1 - args.eps_ro]]))
        model_name = (f"all-to-all RZZ depolarizing model of the declared inputs "
                      f"eps2 = {args.eps2}, eps1 = {args.eps1}, eps_ro = {args.eps_ro}")
    print(f"2x{args.lattice} B={args.sector}: {len(circuits)} circuits on {n} qubits, "
          f"Aer {device} (available: {avail})", flush=True)
    print(f"noise: {model_name}", flush=True)

    # --- transpilation (once; the transpiled circuits are handed to sample_many) ---------------
    phases = {}
    t_tr = time.time()
    tqs, czs, dropped = [], [], 0
    # half the budget is the most transpilation may take: level 3 on a 20-qubit, ~2000-RZZ
    # circuit is a few seconds here, but if it is slower on the CI node the job must still get
    # to the measurement it exists for, so the remaining circuits are dropped and recorded.
    tr_deadline = t0 + 0.5 * (deadline - t0) if deadline is not None else None
    for i, (r, k) in enumerate(circuits):
        if i and tr_deadline is not None and time.time() > tr_deadline:
            dropped = len(circuits) - i
            print(f"  transpilation stopped after {i} circuits: half the budget is spent "
                  f"({dropped} circuits dropped, recorded in the JSON)", flush=True)
            break
        gates = repeated_coarse_step(F, r, k, float(ref.dt), args.reps)
        qc = cq.ir_to_qiskit(gates, n, measure=True)
        if backend is not None:
            tq = transpile(qc, backend=backend, optimization_level=args.level, seed_transpiler=7)
            two_q = int(tq.count_ops().get("cz", 0))
        else:
            tq = transpile(qc, basis_gates=basis, coupling_map=None,
                           optimization_level=args.level, seed_transpiler=7)
            two_q = int(tq.count_ops().get("rzz", 0))
        tqs.append(tq)
        czs.append(two_q)
        print(f"  transpiled [{i + 1}/{len(circuits)}] ref {r} k {k}: {two_q} 2q gates "
              f"({time.time() - t0:.0f} s total)", flush=True)
    circuits = circuits[:len(tqs)]
    phases["transpile_s"] = time.time() - t_tr

    # --- timing ladder: one circuit, several shot counts ---------------------------------------
    # The ladder is what sizes a production run: on a GPU the per-shot cost falls as the batch
    # grows until the chunk bound is reached and then flattens, so a single pilot point cannot be
    # extrapolated.  Every point goes through the same chunked `sample_many` path the sampling
    # below uses, so the points above the chunk measure the chunked regime rather than an
    # impossible single allocation.
    ladder_points = list(args.timing_ladder)
    if not ladder_points and args.ladder_auto:
        ladder_points = default_ladder(n, args.gpu_memory_bytes)
    ladder, ladder_skipped, warmup_sps = [], [], None
    chunk_one = shot_chunk_for(n, 1, args.gpu_memory_bytes)   # recorded on every device
    # chunk the ladder exactly as the sampling below is chunked: on the GPU by the memory model,
    # on the CPU not at all (no OOM occurs there and a chunked CPU call would only add per-call
    # set-up that the sampling does not pay), unless --max-shots-per-run forces a size.
    ladder_chunk = (args.max_shots_per_run if args.max_shots_per_run > 0 else
                    (chunk_one if device == "GPU" else None))
    t_ladder = time.time()
    if ladder_points:
        print(f"timing ladder {ladder_points} (chunk bound for one circuit: {chunk_one} shots, "
              f"chunk used: {ladder_chunk})",
              flush=True)
        # one discarded sample first: the first call pays the transpiler/simulator warm-up, on a
        # GPU the CUDA context (7-8 s in both L4 GPU jobs), which would otherwise land entirely on
        # the smallest ladder point.
        warmup_shots = max(1, min(min(ladder_points), 32))   # enough to pay the set-up, cheap
        tw = time.time()
        cq.sample_many(None, n, warmup_shots, noise_model=nm, device=device,
                       batched_shots_gpu=bsg, seed=args.seed, transpiled=tqs[:1],
                       max_shots_per_run=ladder_chunk)
        warmup_s = time.time() - tw
        warmup_sps = warmup_s / warmup_shots
        print(f"timing ladder: warm-up of {warmup_shots} shots discarded ({warmup_s:.2f} s)",
              flush=True)
        for s in ladder_points:
            # skip a point when the ladder budget is already spent, and also when the point is
            # PREDICTED to overrun it at the cost measured so far: a ladder point cannot be
            # interrupted once it is inside sample_many, so the check has to be made in advance.
            est = int(s) * (ladder[-1]["seconds_per_shot"] if ladder
                            else warmup_s / warmup_shots)
            if ladder_deadline is not None and (time.time() > ladder_deadline
                                                or time.time() + est > ladder_deadline):
                ladder_skipped.append(int(s))
                continue
            tt = time.time()
            _, binfo = cq.sample_many(None, n, int(s), noise_model=nm, device=device,
                                      batched_shots_gpu=bsg, seed=args.seed, transpiled=tqs[:1],
                                      max_shots_per_run=ladder_chunk, return_info=True)
            el = time.time() - tt
            ladder.append({"shots": int(s), "seconds": el, "seconds_per_shot": el / int(s),
                           "run_calls": binfo["run_calls"],
                           "oom_retries": len(binfo["oom_retries"])})
            print(f"timing ladder: {s:>7} shots -> {el:8.2f} s ({el / int(s):.5f} s/shot, "
                  f"{binfo['run_calls']} run call(s))", flush=True)
        if ladder_skipped:
            print(f"timing ladder: {ladder_skipped} skipped (ladder budget spent or the point was "
                  f"predicted to overrun it)", flush=True)
    phases["ladder_s"] = time.time() - t_ladder if ladder_points else 0.0
    best_sps = min([e["seconds_per_shot"] for e in ladder], default=None)

    # --- shots per circuit: the request, reduced to what is left of the budget -----------------
    requested = max(1, int(args.shots_per_sector) // len(circuits))
    shots, shots_reason = requested, "as requested"
    # the cheapest ladder point sizes the run; if every ladder point was skipped (a tight ladder
    # budget) the discarded warm-up is the only measurement there is, and it is used rather than
    # letting an unbounded sampling phase run past the walltime
    size_sps = best_sps or warmup_sps
    size_from = "the ladder's cheapest point" if best_sps else "the discarded warm-up sample"
    if deadline is not None and size_sps:
        # 25 % of what is left is reserved for decoding, the Ritz step and the report
        allowed = int(0.75 * max(0.0, deadline - time.time()) / (size_sps * len(circuits)))
        if allowed < requested:
            shots = max(args.min_shots, allowed)
            shots_reason = (f"reduced from {requested} to fit the {args.budget_minutes:g}-minute "
                            f"budget at {size_sps:.5f} s/shot from {size_from} (floor "
                            f"--min-shots {args.min_shots})")
    print(f"sampling {len(circuits)} circuits x {shots} shots/circuit ({shots_reason})", flush=True)

    # --- sampling: ONE chunked run([...]) call set, per the HPC policy -------------------------
    chunk = (args.max_shots_per_run if args.max_shots_per_run > 0 else
             (shot_chunk_for(n, len(circuits), args.gpu_memory_bytes) if device == "GPU" else None))
    t_samp = time.time()
    counts_list, batch_info = cq.sample_many(
        None, n, shots, noise_model=nm, device=device, batched_shots_gpu=bsg, seed=args.seed,
        transpiled=tqs, max_shots_per_run=chunk, return_info=True)
    phases["sampling_s"] = time.time() - t_samp
    print(f"sampled {len(circuits)} circuits x {shots} shots in {batch_info['run_calls']} run() "
          f"call(s) (<= {batch_info['max_experiments']} circuits x "
          f"{batch_info['max_shots_per_run']} shots each, {len(batch_info['oom_retries'])} OOM "
          f"retries) ({phases['sampling_s']:.1f} s)", flush=True)

    # --- decoding and analysis -----------------------------------------------------------------
    t_ana = time.time()
    acc_all, rej_all, total, per = {}, {}, 0, []
    for (r, k), two_q, counts in zip(circuits, czs, counts_list):
        acc, rej = codec.decode_counts(counts, target_twoB=twoB)
        for kk, c in acc.items():
            acc_all[kk] = acc_all.get(kk, 0) + c
        for kk, c in rej.items():
            rej_all[kk] = rej_all.get(kk, 0) + c
        total += shots
        per.append({"reference": int(r), "k": int(k), "two_qubit_gates": int(two_q),
                    "shots": int(shots), "accepted": int(sum(acc.values()))})

    prob = np.zeros(M.basis.dim)
    prob[ref.indices] = np.abs(ref.ground) ** 2
    B = np.array(sorted(set(acc_all) | set(refs)))
    res = ritz(M.H(args.g2), B)
    met = support_metrics(B, prob, EPS_SUPPORT)
    cert = certify(res, ref.E0, float(ref.energies[1]))
    y = sum(acc_all.values()) / total
    phases["analysis_s"] = time.time() - t_ana
    sps = phases["sampling_s"] / max(1, total)      # measured over the whole batched sector
    proj_sps = best_sps if best_sps else sps
    proj_hours = PRODUCTION_SHOTS_PER_SECTOR * proj_sps / 3600.0
    wall = time.time() - t0
    layout = slurm_layout()
    tele = gpu_telemetry()
    gpus = gpu_count(layout)
    if args.calibration:
        run_kind = ("CALIBRATION (throughput at %d qubits; the S3 recall criterion is NOT "
                    "evaluated and the yield/recall below are measurements at the calibration "
                    "shot count, not gate results)" % n)
    elif args.tag == "smoke":
        run_kind = "smoke (pipeline test, NOT the production budget)"
    else:
        run_kind = "production"
    data = {
        "lattice": f"2x{args.lattice}", "sector": f"B={args.sector}", "twoB": twoB,
        "repetitions": args.reps, "kmax": args.kmax, "g2": args.g2,
        "n_qubits": n, "n_circuits": len(circuits), "shots_per_circuit": shots,
        "circuits_dropped_for_budget": dropped,
        "shots_per_circuit_requested": requested, "shots_per_circuit_reason": shots_reason,
        "shots_per_sector_requested": args.shots_per_sector, "total_shots": total,
        "run_kind": run_kind,
        "calibration": bool(args.calibration),
        "gate_S3_criterion": ("NOT EVALUATED in a calibration run (recall >= %.1f with the "
                              "production budget is the gate; this job measures compute "
                              "throughput)" % RECALL_MIN) if args.calibration else
                             f"recall >= {RECALL_MIN} with the production budget",
        "noise_model": model_name,
        "declared_inputs": (None if backend is not None else
                            {"eps2": args.eps2, "eps1": args.eps1, "eps_ro": args.eps_ro,
                             "note": "vendor-class specifications, declared inputs (prompts/12)"}),
        "aer": {"device": device, "available_devices": avail,
                "batched_shots_gpu": bool(bsg), "method": "statevector" if bsg else "automatic"},
        "two_qubit_gates": {"mean": float(np.mean(czs)), "min": int(min(czs)), "max": int(max(czs))},
        "yield": float(y), "accepted": int(sum(acc_all.values())),
        "rejections": {k2: int(v) for k2, v in rej_all.items()},
        "f_implied_by_yield": float(y / YIELD_FACTOR),
        "support": {"size_decoded": len(acc_all), "size_with_references": int(len(B)),
                    "sector_dimension": int(len(ref.indices)),
                    "recall_99.9pct": float(met["recall"]),
                    "exact_support_size": met["exact_support_size"],
                    "false_positives": met["false_positives"],
                    "captured_weight": met["captured_weight"]},
        "ritz": {"ER": float(res.ER), "exact_E0": float(ref.E0), "error": float(res.ER - ref.E0),
                 "rH": float(res.rH),
                 "weinstein": [float(cert.weinstein[0]), float(cert.weinstein[1])],
                 "exact_E0_inside_weinstein": bool(cert.weinstein[0] - 1e-9 <= ref.E0 <= cert.weinstein[1] + 1e-9)},
        "cost": {"seconds_per_shot_mean": sps, "shots_per_simulator_call": batch_info["max_shots_per_run"],
                 "seconds_per_shot_best_ladder": best_sps,
                 "seconds_per_shot_used_for_projection": proj_sps,
                 "wall_seconds": wall,
                 "projected_hours_per_sector_at_2e5_shots": proj_hours,
                 "projected_hours_four_sectors": 4 * proj_hours,
                 "reference_S2D": s2d_cost(),
                 "projected_hours_per_sector_at_reference_rate": (
                     None if not s2d_cost() else
                     PRODUCTION_SHOTS_PER_SECTOR * s2d_cost()["seconds_per_shot"] / 3600.0),
                 "note": ("the seconds per shot are measured over the whole batched sector and "
                          "include the per-call set-up of every chunked run (circuit load, "
                          "noise-model binding); the projection uses the cheapest ladder point "
                          "when a ladder was run"),
                 "extrapolation_note": L4_SPEEDUP_NOTE},
        "shot_rule": {"p": args.p, "k": args.k, "confidence": args.conf,
                      "N_circuit_at_measured_yield": int(shot_rule(args.p, max(y, 1e-12), args.k, args.conf))
                      if y > 0 else None,
                      "N_sector_at_measured_yield": int(shot_rule(args.p, max(y, 1e-12), args.k, args.conf)
                                                        * len(circuits)) if y > 0 else None},
        "per_circuit": per,
    }
    data["run"] = {
        "engine": "Qiskit Aer statevector" + (" (GPU, cuStateVec/batched shots)" if device == "GPU"
                                              else " (CPU)"),
        "device": device, "device_requested": args.device, "available_devices": avail,
        "batched_shots_gpu": bool(bsg), "cu_statevec_enable": device == "GPU",
        "precision": "double", "active_qubits": n,
        "ci": ci or None, "slurm": layout, "gpus": gpus, "tasks": layout["tasks"],
        "rank": layout["rank"],
        "wall_seconds": wall,
        "gpu_node_hours": None if not gpus else gpus * wall / 3600.0,
        "parallel_efficiency_Ep": None,
        "parallel_efficiency_note": ("E(p) needs T_1 and T_p from at least two task counts; this "
                                     "run is a single task, so it is not measured"),
        "phases_s": phases,
        "gpu_telemetry": tele,
        "versions": qiskit_versions(),
        "seeds": {"aer_seed_simulator": args.seed, "seed_transpiler": 7,
                  "chunk_seed_rule": "seed + chunk index (skqd.circuits_qiskit.sample_many)"},
        "timing_ladder": ladder,
        "timing_ladder_requested": ladder_points,
        "timing_ladder_skipped_for_budget": ladder_skipped,
        "timing_ladder_warmup_seconds_per_shot": warmup_sps,
        "batching": batch_info,
        "gpu_memory_bytes_assumed": args.gpu_memory_bytes,
        "gpu_memory_model_factor_measured_in_L4": MEASURED_MEMORY_MODEL_FACTOR,
        "gpu_memory_bytes_implied_real": args.gpu_memory_bytes * MEASURED_MEMORY_MODEL_FACTOR,
        "shot_chunk_one_circuit": chunk_one,
        "shot_chunk_all_circuits": shot_chunk_for(n, len(circuits), args.gpu_memory_bytes),
        "budget_minutes": args.budget_minutes,
        "ladder_budget_minutes": args.ladder_budget_minutes,
        "walltime_budget_s": args.walltime_budget_s,
        "min_shots": args.min_shots,
        "noise": ({"backend": args.backend} if backend is not None
                  else {"eps2": args.eps2, "eps1": args.eps1, "eps_ro": args.eps_ro}),
    }

    if args.calibration:
        # Throughput criteria ONLY.  The S3 physics criterion is deliberately absent: a reduced
        # -size calibration cannot decide it, and prompts/18 sec. 2.1 asks for the walltime of a
        # production run to be sized from this measurement first.
        R.add(f"calibration: Aer ran on the requested device ({args.device}"
              + (", GPU under the CI" if ci else "") + ")",
              f"{device} (available {avail})",
              "GPU" if want_gpu else "as requested",
              (device == "GPU") if want_gpu else True)
        R.add("calibration: the timing ladder measured at least two shot counts",
              f"{len(ladder)} of {len(ladder_points)} points"
              + (f", {ladder_skipped} skipped for the ladder budget" if ladder_skipped else ""),
              ">= 2 points", len(ladder) >= 2)
        R.add("calibration: the batched sampling fitted the assumed GPU memory",
              f"{len(batch_info['oom_retries'])} out-of-memory retries at "
              f"{batch_info['max_experiments']} circuits x {batch_info['max_shots_per_run']} "
              f"shots per run() call", "no OOM retry", not batch_info["oom_retries"])
        R.add("calibration: wall time inside the budget the CI allows",
              f"{wall:.0f} s", f"<= {args.walltime_budget_s:.0f} s"
              if args.walltime_budget_s > 0 else "not checked",
              wall <= args.walltime_budget_s if args.walltime_budget_s > 0 else True)
    else:
        R.add(f"2x{args.lattice} B={args.sector}: recall of the {100 * (1 - EPS_SUPPORT):.1f} % support "
              f"({met['exact_support_size']} states) with {total} shots",
              round(float(met["recall"]), 4), f">= {RECALL_MIN}", met["recall"] >= RECALL_MIN)
        R.add(f"2x{args.lattice} B={args.sector}: exact E0 = {ref.E0:.4f} inside the Weinstein interval",
              f"[{cert.weinstein[0]:.4f}, {cert.weinstein[1]:.4f}]", "contains the exact E0",
              data["ritz"]["exact_E0_inside_weinstein"])
    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report(f"{gate_name}_device_model.md", report_text(args, R, data))
    print(R.criteria_table())
    print(f"seconds per shot {sps:.4f} measured, {proj_sps:.4f} used for the projection; a "
          f"{PRODUCTION_SHOTS_PER_SECTOR:.0e}-shot sector costs {proj_hours:.1f} h on this device, "
          f"four sectors {4 * proj_hours:.1f} h")
    return 0 if R.passed else 1


def _fmt(x, fmt="{:.3g}"):
    return "not measured" if x is None else fmt.format(x)


def report_text(args, R, D):
    rows = [[p["reference"], p["k"], p["two_qubit_gates"], p["shots"], p["accepted"],
             f"{p['accepted'] / p['shots']:.3f}"] for p in D["per_circuit"]]
    run = D["run"]
    tele = run["gpu_telemetry"]
    ladder = run["timing_ladder"]
    banner = ("" if not D["calibration"] else f"""
> **This is a reduced-size THROUGHPUT CALIBRATION, not gate S3.**  {D['gate_S3_criterion']}.
> The yield and recall below are measurements at the calibration shot count and are **not** gate
> results.  {D['cost']['extrapolation_note']}.
""")
    mem_txt = ("not measured (no nvidia-smi sampler file in the working directory)"
               if tele["peak_memory_mib"] is None else f"{tele['peak_memory_mib']:.0f} MiB")
    util_txt = ("not measured" if tele["mean_utilization_pct"] is None else
                f"{tele['mean_utilization_pct']:.1f} % mean, {tele['max_utilization_pct']:.0f} % peak "
                f"over {tele['samples']} nvidia-smi samples")
    policy_line = (
        f"**Engine and resources** (RUNBOOK.md policy): engine {run['engine']}, qiskit "
        f"{run['versions']['qiskit']} / aer {run['versions']['qiskit_aer']}, device {run['device']} "
        f"(requested {run['device_requested']}, available {run['available_devices']}), GPUs "
        f"{_fmt(run['gpus'], '{:d}')}, tasks {_fmt(run['tasks'], '{:d}')}, walltime "
        f"{run['wall_seconds']:.0f} s, E(p) {_fmt(run['parallel_efficiency_Ep'])} "
        f"({run['parallel_efficiency_note']}), GPU node-hours used "
        f"{_fmt(run['gpu_node_hours'], '{:.4f}')}, peak GPU memory {mem_txt}, GPU utilization "
        f"{util_txt}.  Phases (s): "
        + ", ".join(f"{k} {v:.1f}" for k, v in run["phases_s"].items()) + ".  "
        f"Memory model: {run['shot_chunk_one_circuit']} shots per run() call for one circuit and "
        f"{run['shot_chunk_all_circuits']} for all {D['n_circuits']} at "
        f"{run['gpu_memory_bytes_assumed']:.2g} model bytes "
        f"(x{run['gpu_memory_model_factor_measured_in_L4']} measured in L4 = "
        f"{run['gpu_memory_bytes_implied_real']:.2g} real bytes); the sampling used "
        f"{run['batching']['max_experiments']} circuits x {run['batching']['max_shots_per_run']} "
        f"shots in {run['batching']['run_calls']} run() call(s) with "
        f"{len(run['batching']['oom_retries'])} out-of-memory retries.")
    ladder_block = ("" if not ladder else
                    "Timing ladder on one circuit (chunked exactly as the sampling is, so the "
                    "points above the chunk bound measure the chunked regime):\n\n"
                    + md_table(["shots", "seconds", "s/shot", "run calls"],
                               [[str(e["shots"]), f"{e['seconds']:.2f}",
                                 f"{e['seconds_per_shot']:.5f}", str(e["run_calls"])]
                                for e in ladder])
                    + (f"\n\nSkipped for the ladder budget: {run['timing_ladder_skipped_for_budget']}."
                       if run["timing_ladder_skipped_for_budget"] else "")
                    + "\n")
    ref_s2d = D["cost"]["reference_S2D"]
    s2d_line = ("" if not ref_s2d else
                f"For comparison, gate S2D measured {ref_s2d['seconds_per_shot']:.2f} s/shot at "
                f"{ref_s2d['shots_per_simulator_call']} shots per call on the laptop CPU "
                f"({ref_s2d['source']}), which projects to "
                f"{D['cost']['projected_hours_per_sector_at_reference_rate']:.0f} h per sector.")
    status_line = ("**Status: " + ("PASS" if R.passed else "FAIL") + "**"
                   + (" (calibration criteria only — gate S3 itself is NOT evaluated here)"
                      if D["calibration"] else ""))
    return f"""# Gate {R.gate} — {R.title}

{status_line} — `scripts/s3_device_model.py --lattice {args.lattice} --sector {args.sector}
--shots-per-sector {args.shots_per_sector:.0f}{' --calibration' if D['calibration'] else ''}
--tag {args.tag or '""'}`.  Run kind: **{D['run_kind']}**.  {env_block()}  Runtime {R.runtime_s:.0f} s.
{banner}
Noise model: {D['noise_model']}.
Aer device **{D['aer']['device']}** (available: {D['aer']['available_devices']},
batched_shots_gpu = {D['aer']['batched_shots_gpu']}).

## Sampling

{D['n_circuits']} circuits (references x k = 1..{D['kmax']}, r = {D['repetitions']} repetition(s) of the coarse step) on
{D['n_qubits']} qubits, {D['shots_per_circuit']} shots each = {D['total_shots']} shots
({D['shots_per_circuit_reason']}; {D['shots_per_circuit_requested']} requested);
{D['two_qubit_gates']['mean']:.0f} two-qubit gates per circuit on average.

{md_table(["reference", "k", "2q gates", "shots", "accepted", "yield"], rows)}

Accepted yield {D['yield']:.4f} (implied f = yield / {YIELD_FACTOR} = {D['f_implied_by_yield']:.4f});
rejections {D['rejections']}.  Per-circuit times are not separable: the whole sector goes through
one chunked `sample_many` call set, which is what the HPC policy asks for.

## Support and certification

|B| = {D['support']['size_with_references']} ({D['support']['size_decoded']} decoded + the references) of a
{D['support']['sector_dimension']}-dimensional sector; recall of the 99.9 % support
({D['support']['exact_support_size']} states) = **{D['support']['recall_99.9pct']:.4f}**, captured weight
{D['support']['captured_weight']:.6f}, false positives {D['support']['false_positives']}.
E_R = {D['ritz']['ER']:.6f} against the exact E_0 = {D['ritz']['exact_E0']:.6f} (error {D['ritz']['error']:.2e}),
r_H = {D['ritz']['rH']:.3e}, Weinstein [{D['ritz']['weinstein'][0]:.4f}, {D['ritz']['weinstein'][1]:.4f}].

## Cost and the production job

{policy_line}

{ladder_block}
{D['cost']['seconds_per_shot_mean']:.4f} s per shot measured over the batched sector;
{_fmt(D['cost']['seconds_per_shot_best_ladder'], '{:.5f}')} s per shot at the cheapest ladder point.
{D['cost']['note']}.  {s2d_line}
A {PRODUCTION_SHOTS_PER_SECTOR:.0e}-shot sector at
{D['cost']['seconds_per_shot_used_for_projection']:.5f} s/shot costs
**{D['cost']['projected_hours_per_sector_at_2e5_shots']:.1f} h** on this device and the four 2x3 jobs of manual
Step 9.2 (B = 0 and B = 1, r = 1 and r = 2) cost {D['cost']['projected_hours_four_sectors']:.1f} h.

## Criteria

{R.criteria_table()}

Every number above is computed by `scripts/s3_device_model.py` and stored in `validation/{R.gate}.json`.
"""


if __name__ == "__main__":
    sys.exit(main())

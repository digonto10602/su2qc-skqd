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

Aer runs on the GPU with batched shots when one is available
(`'GPU' in AerSimulator().available_devices()`) and on the CPU otherwise; the laptop of this
project has no compatible qiskit-aer-gpu wheel, so the production runs belong on the RTX 3070
desktop or on the Slurm GPU cluster (`slurm/s3_2x3.sbatch`).

S3 criterion (manual Step 10 / gate S1): recall of the 99.9 % support of the exact sector
ground state >= 0.9 with the production shot budget.  The script also records the accepted
yield, |B|, the Ritz error and the certification, the measured seconds per shot and the
projected size of a 2e5-shot-per-sector job.

Usage:
  python scripts/s3_device_model.py --lattice 3 --sector 1 --shots-per-sector 24 --tag smoke
  python scripts/s3_device_model.py --lattice 3 --sector 0 --shots-per-sector 200000 --tag B0_r1
  python scripts/s3_device_model.py --lattice 2 --sector 0 --backend FakeFez --tag 2x2
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
from skqd.reference_sim import qiskit_key_to_bits  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.skqd import certify, ritz, shot_rule, support_metrics  # noqa: E402

from h0_build_circuits import repeated_coarse_step  # noqa: E402

RECALL_MIN = 0.9             # gate S3 / S1 criterion
EPS_SUPPORT = 1e-3           # the 99.9 % support
YIELD_FACTOR = 0.82
PRODUCTION_SHOTS_PER_SECTOR = 2e5     # manual Step 9.2


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


def main():
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
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()
    t0 = time.time()

    from qiskit import transpile
    from qiskit_aer import AerSimulator

    from skqd import circuits_qiskit as cq

    device, avail = pick_device(args.device)
    twoB = 2 * args.sector
    M = Model(args.lattice)
    F = CircuitFactory(M, args.g2)
    codec = Codec(M.basis)
    n = codec.n_qubits
    ref = M.reference(args.g2, twoB)
    refs = references(M.basis, twoB)
    circuits = [(r, k) for r in refs for k in range(1, args.kmax + 1)]
    shots = max(1, int(args.shots_per_sector) // len(circuits))

    R = GateResult(f"S3_{args.tag}", f"Device-model sampling of the 2x{args.lattice} B={args.sector} "
                                     f"circuit set (gate S3)")
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
    sim_kwargs = dict(noise_model=nm, device=device, seed_simulator=args.seed)
    if device == "GPU":
        sim_kwargs.update(batched_shots_gpu=True)
    sim = AerSimulator(**sim_kwargs)
    print(f"2x{args.lattice} B={args.sector}: {len(circuits)} circuits x {shots} shots "
          f"on Aer {device} (available: {avail})", flush=True)
    print(f"noise: {model_name}", flush=True)

    acc_all, rej_all, total, czs, per = {}, {}, 0, [], []
    for i, (r, k) in enumerate(circuits):
        gates = repeated_coarse_step(F, r, k, float(ref.dt), args.reps)
        qc = cq.ir_to_qiskit(gates, n, measure=True)
        if backend is not None:
            tq = transpile(qc, backend=backend, optimization_level=args.level, seed_transpiler=7)
            two_q = int(tq.count_ops().get("cz", 0))
        else:
            tq = transpile(qc, basis_gates=basis, coupling_map=None,
                           optimization_level=args.level, seed_transpiler=7)
            two_q = int(tq.count_ops().get("rzz", 0))
        czs.append(two_q)
        ts = time.time()
        counts = sim.run(tq, shots=shots).result().get_counts()
        dts = time.time() - ts
        counts = {qiskit_key_to_bits(kk): v for kk, v in counts.items()}
        acc, rej = codec.decode_counts(counts, target_twoB=twoB)
        for kk, c in acc.items():
            acc_all[kk] = acc_all.get(kk, 0) + c
        for kk, c in rej.items():
            rej_all[kk] = rej_all.get(kk, 0) + c
        total += shots
        per.append({"reference": int(r), "k": int(k), "two_qubit_gates": two_q, "shots": shots,
                    "accepted": int(sum(acc.values())), "seconds": dts,
                    "seconds_per_shot": dts / shots})
        print(f"  [{i + 1}/{len(circuits)}] ref {r} k {k}: {two_q} 2q gates, "
              f"{sum(acc.values())}/{shots} accepted, {dts / shots:.2f} s/shot "
              f"({time.time() - t0:.0f} s total)", flush=True)

    prob = np.zeros(M.basis.dim)
    prob[ref.indices] = np.abs(ref.ground) ** 2
    B = np.array(sorted(set(acc_all) | set(refs)))
    res = ritz(M.H(args.g2), B)
    met = support_metrics(B, prob, EPS_SUPPORT)
    cert = certify(res, ref.E0, float(ref.energies[1]))
    y = sum(acc_all.values()) / total
    sps = float(np.mean([p["seconds_per_shot"] for p in per]))
    proj_hours = PRODUCTION_SHOTS_PER_SECTOR * sps / 3600.0
    data = {
        "lattice": f"2x{args.lattice}", "sector": f"B={args.sector}", "twoB": twoB,
        "repetitions": args.reps, "kmax": args.kmax, "g2": args.g2,
        "n_qubits": n, "n_circuits": len(circuits), "shots_per_circuit": shots,
        "shots_per_sector_requested": args.shots_per_sector, "total_shots": total,
        "run_kind": "smoke (pipeline test, NOT the production budget)" if args.tag == "smoke" else "production",
        "noise_model": model_name,
        "declared_inputs": (None if backend is not None else
                            {"eps2": args.eps2, "eps1": args.eps1, "eps_ro": args.eps_ro,
                             "note": "vendor-class specifications, declared inputs (prompts/12)"}),
        "aer": {"device": device, "available_devices": avail,
                "batched_shots_gpu": bool(device == "GPU"), "method": "automatic"},
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
        "cost": {"seconds_per_shot_mean": sps, "shots_per_simulator_call": shots,
                 "wall_seconds": time.time() - t0,
                 "projected_hours_per_sector_at_2e5_shots": proj_hours,
                 "projected_hours_four_sectors": 4 * proj_hours,
                 "reference_S2D": s2d_cost(),
                 "projected_hours_per_sector_at_reference_rate": (
                     None if not s2d_cost() else
                     PRODUCTION_SHOTS_PER_SECTOR * s2d_cost()["seconds_per_shot"] / 3600.0),
                 "note": ("the measured seconds per shot include the fixed per-call overhead of one "
                          "AerSimulator.run (circuit load, noise-model binding); it amortises at large "
                          "shot counts, so a short run over-estimates the production cost")},
        "shot_rule": {"p": args.p, "k": args.k, "confidence": args.conf,
                      "N_circuit_at_measured_yield": int(shot_rule(args.p, max(y, 1e-12), args.k, args.conf))
                      if y > 0 else None,
                      "N_sector_at_measured_yield": int(shot_rule(args.p, max(y, 1e-12), args.k, args.conf)
                                                        * len(circuits)) if y > 0 else None},
        "per_circuit": per,
    }
    R.add(f"2x{args.lattice} B={args.sector}: recall of the {100 * (1 - EPS_SUPPORT):.1f} % support "
          f"({met['exact_support_size']} states) with {total} shots",
          round(float(met["recall"]), 4), f">= {RECALL_MIN}", met["recall"] >= RECALL_MIN)
    R.add(f"2x{args.lattice} B={args.sector}: exact E0 = {ref.E0:.4f} inside the Weinstein interval",
          f"[{cert.weinstein[0]:.4f}, {cert.weinstein[1]:.4f}]", "contains the exact E0",
          data["ritz"]["exact_E0_inside_weinstein"])
    R.data = data
    R.runtime_s = time.time() - t0
    R.save()
    write_report(f"S3_{args.tag}_device_model.md", report_text(args, R, data))
    print(R.criteria_table())
    print(f"seconds per shot {sps:.2f}; a {PRODUCTION_SHOTS_PER_SECTOR:.0e}-shot sector costs "
          f"{proj_hours:.1f} h on this device, four sectors {4 * proj_hours:.1f} h")
    return 0 if R.passed else 1


def report_text(args, R, D):
    rows = [[p["reference"], p["k"], p["two_qubit_gates"], p["shots"], p["accepted"],
             f"{p['accepted'] / p['shots']:.3f}", f"{p['seconds_per_shot']:.2f}"] for p in D["per_circuit"]]
    return f"""# Gate S3 ({args.tag}) — device-model sampling of the {D['lattice']} {D['sector']} circuit set

**Status: {'PASS' if R.passed else 'FAIL'}** — `scripts/s3_device_model.py --lattice {args.lattice}
--sector {args.sector} --shots-per-sector {args.shots_per_sector:.0f} --tag {args.tag}`.
Run kind: **{D['run_kind']}**.  {env_block()}  Runtime {R.runtime_s:.0f} s.

Noise model: {D['noise_model']}.
Aer device **{D['aer']['device']}** (available: {D['aer']['available_devices']},
batched_shots_gpu = {D['aer']['batched_shots_gpu']}).

## Sampling

{D['n_circuits']} circuits (references x k = 1..{D['kmax']}, r = {D['repetitions']} repetition(s) of the coarse step) on
{D['n_qubits']} qubits, {D['shots_per_circuit']} shots each = {D['total_shots']} shots;
{D['two_qubit_gates']['mean']:.0f} two-qubit gates per circuit on average.

{md_table(["reference", "k", "2q gates", "shots", "accepted", "yield", "s/shot"], rows)}

Accepted yield {D['yield']:.4f} (implied f = yield / {YIELD_FACTOR} = {D['f_implied_by_yield']:.4f});
rejections {D['rejections']}.

## Support and certification

|B| = {D['support']['size_with_references']} ({D['support']['size_decoded']} decoded + the references) of a
{D['support']['sector_dimension']}-dimensional sector; recall of the 99.9 % support
({D['support']['exact_support_size']} states) = **{D['support']['recall_99.9pct']:.4f}**, captured weight
{D['support']['captured_weight']:.6f}, false positives {D['support']['false_positives']}.
E_R = {D['ritz']['ER']:.6f} against the exact E_0 = {D['ritz']['exact_E0']:.6f} (error {D['ritz']['error']:.2e}),
r_H = {D['ritz']['rH']:.3e}, Weinstein [{D['ritz']['weinstein'][0]:.4f}, {D['ritz']['weinstein'][1]:.4f}].

## Cost and the production job

{D['cost']['seconds_per_shot_mean']:.3f} s per shot measured here, at {D['cost']['shots_per_simulator_call']} shots per simulator call.
{D['cost']['note']}: gate S2D measured {D['cost']['reference_S2D']['seconds_per_shot']:.2f} s/shot at
{D['cost']['reference_S2D']['shots_per_simulator_call']} shots per call on the same laptop CPU ({D['cost']['reference_S2D']['source']}), which projects to
{D['cost']['projected_hours_per_sector_at_reference_rate']:.0f} h per sector instead.
A {PRODUCTION_SHOTS_PER_SECTOR:.0e}-shot sector at the rate measured HERE costs
**{D['cost']['projected_hours_per_sector_at_2e5_shots']:.1f} h** on this device and the four 2x3 jobs of manual Step 9.2
(B = 0 and B = 1, r = 1 and r = 2) cost {D['cost']['projected_hours_four_sectors']:.1f} h.  The same command with a GPU
available uses `device='GPU', batched_shots_gpu=True`; `slurm/s3_2x3.sbatch` submits the four jobs.

## Criteria

{R.criteria_table()}

Every number above is computed by `scripts/s3_device_model.py` and stored in `validation/{R.gate}.json`.
"""


if __name__ == "__main__":
    sys.exit(main())

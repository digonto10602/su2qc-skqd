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

Usage: python scripts/laptop_L4_aer_noise.py [--p2 3e-3] [--p1 3e-4] [--pro 0.01]
                                             [--budget-minutes 25] [--pilot-shots 1000]
                                             [--min-shots 500] [--gpu]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p2", type=float, default=3e-3)
    ap.add_argument("--p1", type=float, default=3e-4)
    ap.add_argument("--pro", type=float, default=0.01)
    ap.add_argument("--budget-minutes", type=float, default=25.0)
    ap.add_argument("--pilot-shots", type=int, default=1000, help="shots of the pilot used to time one circuit")
    ap.add_argument("--min-shots", type=int, default=500, help="floor for the shots per circuit")
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--backend", default=None, choices=("FakeFez", "FakeTorino"),
                    help="calibration snapshot: NoiseModel.from_backend + transpilation onto that backend")
    ap.add_argument("--out", default="L4", help="name of validation/<out>.json and reports/<out>_aer_noise.md")
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
    rows = []
    for twoB in (0, 2):
        ref = M.reference(g2, twoB)
        refs = references(M.basis, twoB)
        circuits = [(r, k, F.coarse_step(r, k, ref.dt)) for r in refs for k in (1, 2, 3, 4)]
        # pilot timing -> shots per circuit within the budget
        tp = time.time()
        cq.sample(circuits[0][2], n, args.pilot_shots, noise_model=nm, device=device, backend=backend)
        t_per_shot = (time.time() - tp) / args.pilot_shots
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
        cz_counts = []
        for r, k, g in circuits:
            counts = cq.sample(g, n, shots, noise_model=nm, device=device, backend=backend)
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
                                               optimization_level=3, seed_transpiler=7), backend)
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
    R.runtime_s = time.time() - t0
    R.save()
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

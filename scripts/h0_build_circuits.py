#!/usr/bin/env python3
"""
Step 1 of prompts/13 — freeze the H0 circuit set (manual Step 9.1, prompts/07 step 1).

For both sectors (B = 0, B = 1), every reference, every coarse step k = 1..4 and
r = 1, 2, 3 repetitions of that coarse step, transpile the exact structured circuit
of gate S2 onto a Heron-class calibration snapshot (FakeFez by default,
optimization level 3, seed 7) and write it to `data/hardware/H0_prep/circuits/` as

    <id>.qpy.gz     the transpiled circuit (qiskit.qpy.dump into a gzip stream)
    <id>.json       the manifest: sector, reference, k, r, CZ count, depth, physical
                    qubits, logical -> physical map, measurement map, the codeword bit
                    order and the flux-bit link-consistency checks the decoder applies,
                    and the clean-shot fraction f of that snapshot (as gate S2D computes it)

r repetitions mean U^r with U = the coarse step at angle theta = k dt: the reference
state is prepared once and the IR gate list of the step is concatenated r times, so
every circuit of the set is a valid gauge-invariant generator whose ideal output is a
codeword.  This is the manual's "yield versus CZ count by repetition" axis.

Every transpiled circuit is verified leak-free: the noiseless statevector of the
transpiled circuit (measurements removed, compacted onto the physical qubits it uses)
is permuted back to logical order with the circuit's OWN final layout, and the weight
outside the codeword subspace must be < 1e-9.  This is the check a real hardware run
gets wrong when the layout permutation or the measurement mapping is mishandled.

The readout-calibration circuits (all-0, all-1 and the 12 single-qubit flips) are built
for every distinct physical patch the transpiler chose, with initial_layout fixed to
that patch.

Usage: python scripts/h0_build_circuits.py [--backend FakeFez] [--lattice 2] [--g2 4.0]
                                           [--reps 1 2 3] [--kmax 4] [--level 3] [--seed 7]
                                           [--out data/hardware/H0_prep] [--no-verify]
Runtime: about 2 minutes on the i7-8750H (CPU only).
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.hardware import codeword_bit_order, link_consistency_checks, logical_statevector, transpiled_layout  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.reference_sim import CodewordEmbedding  # noqa: E402

from gate_S2D import analyse_on_backend  # noqa: E402  (the f of gate S2D, same definition)
from h0_backends import is_fake, last_update_date, resolve_backend  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAK_TOL = 1e-9
FROZEN_SET = os.path.join("data", "hardware", "H0_prep")


def step_gates(F, k, dt, structured_plaquette=True):
    """The gate list of ONE coarse step at angle theta = k dt (no state preparation)."""
    theta = k * dt
    g = F.diag_gates(theta)
    for l in range(F.lat.n_links):
        g += F.hop_gates(l, theta)
    for P in range(len(F.lat.plaquettes)):
        g += F.plaq_gates(P, theta, structured_plaquette)
    return g


def repeated_coarse_step(F, ref_index, k, dt, r):
    """prepare(reference) followed by r repetitions of the coarse step -> U^r |ref>."""
    return F.prepare(ref_index) + step_gates(F, k, dt) * r


def dump_qpy_gz(tq, path):
    buf = io.BytesIO()
    from qiskit import qpy
    qpy.dump(tq, buf)
    raw = buf.getvalue()
    with gzip.open(path, "wb") as fh:
        fh.write(raw)
    return len(raw), hashlib.sha256(open(path, "rb").read()).hexdigest()


def load_qpy_gz(path):
    from qiskit import qpy
    with gzip.open(path, "rb") as fh:
        return qpy.load(fh)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="FakeFez",
                    help="FakeFez / FakeTorino (calibration snapshots, offline) or the name of a "
                         "live IBM backend (prompts/15 A1; --out is then mandatory)")
    ap.add_argument("--lattice", type=int, default=2, help="Lx of the 2 x Lx ladder")
    ap.add_argument("--g2", type=float, default=4.0)
    ap.add_argument("--reps", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--kmax", type=int, default=4)
    ap.add_argument("--level", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=None,
                    help=f"output directory (default {FROZEN_SET} for a calibration snapshot; "
                         f"mandatory, and different from it, for a live backend)")
    ap.add_argument("--no-verify", action="store_true", help="skip the leakage verification (not for production)")
    args = ap.parse_args()
    t0 = time.time()

    # prompts/15 D1: the frozen set data/hardware/H0_prep is submitted byte-for-byte; a live
    # backend re-freeze is the contingency of step B3b and always writes somewhere else.
    if is_fake(args.backend):
        out_rel = args.out or FROZEN_SET
    else:
        if not args.out:
            raise SystemExit(f"--out is mandatory for the live backend '{args.backend}': the frozen "
                             f"set {FROZEN_SET} is never rebuilt on a live calibration (prompts/15 D1)")
        if os.path.normpath(args.out) == os.path.normpath(FROZEN_SET):
            raise SystemExit(f"refusing to rebuild {FROZEN_SET} on the live backend "
                             f"'{args.backend}': it is the frozen set of gate H0P (prompts/15 D1). "
                             f"Choose another --out, e.g. data/hardware/H0_prep_{args.backend}")
        out_rel = args.out
    args.out = out_rel

    from qiskit import QuantumCircuit, transpile

    from skqd import circuits_qiskit as cq

    backend = resolve_backend(args.backend)
    cal_date = last_update_date(backend)
    M = Model(args.lattice)
    F = CircuitFactory(M, args.g2)
    codec = Codec(M.basis)
    emb = CodewordEmbedding(M)
    n = codec.n_qubits
    bit_order = codeword_bit_order(codec)
    link_checks = link_consistency_checks(codec)

    outdir = os.path.join(ROOT, args.out)
    cdir = os.path.join(outdir, "circuits")
    os.makedirs(cdir, exist_ok=True)

    common = {
        "lattice": f"2x{args.lattice}", "n_logical_qubits": n, "g2": args.g2,
        "circuit_family": "exact structured circuits, CircuitFactory default (gate S2 / validation/S2.json)",
        "backend": args.backend, "backend_qubits": int(backend.num_qubits),
        "backend_calibration_last_update": cal_date,
        "transpiler": {"optimization_level": args.level, "seed_transpiler": args.seed},
        "bit_order_convention": ("classical bit i of a counts key = logical qubit i = bit i of the codeword "
                                 "(skqd.reference_sim.qiskit_key_to_bits, skqd.codec.Codec)"),
        "codeword_bit_order": bit_order,
        "link_consistency_checks": link_checks,
    }

    manifests, leaks = [], []
    for twoB in (0, 2):
        ref = M.reference(args.g2, twoB)
        dt = float(ref.dt)
        for rix in references(M.basis, twoB):
            for k in range(1, args.kmax + 1):
                for r in args.reps:
                    cid = f"B{twoB // 2}_ref{rix:02d}_k{k}_rep{r}"
                    gates = repeated_coarse_step(F, rix, k, dt, r)
                    qc = cq.ir_to_qiskit(gates, n, measure=True)
                    tq = transpile(qc, backend=backend, optimization_level=args.level,
                                   seed_transpiler=args.seed)
                    lay = transpiled_layout(tq, n)
                    a = analyse_on_backend(tq, backend)
                    leak = None
                    if not args.no_verify:
                        psi = logical_statevector(tq, n)
                        leak = emb.leakage(psi)
                        leaks.append(leak)
                        if leak > LEAK_TOL:
                            raise SystemExit(f"{cid}: leakage {leak:.3e} > {LEAK_TOL:g} after transpilation; "
                                             f"layout {lay['logical_to_physical']}")
                        if not lay["measurement_consistent"]:
                            raise SystemExit(f"{cid}: measurement map {lay['measurement_map']} does not match "
                                             f"the final layout {lay['logical_to_physical']}")
                    qpy_name = cid + ".qpy.gz"
                    raw_bytes, sha = dump_qpy_gz(tq, os.path.join(cdir, qpy_name))
                    man = dict(common)
                    man.update({
                        "id": cid, "kind": "coarse_step", "sector": f"B={twoB // 2}", "twoB": twoB,
                        "reference": int(rix), "k": k, "repetitions": r, "dt": dt, "theta": k * dt,
                        "cz": a["cz"], "n_1q": a["n_1q"], "depth": int(tq.depth()),
                        "ops": {kk: int(v) for kk, v in tq.count_ops().items()},
                        "physical_qubits": lay["active_physical"],
                        "readout_patch": sorted(lay["logical_to_physical"]),
                        "logical_to_physical": lay["logical_to_physical"],
                        "measurement_map_clbit_to_physical": lay["measurement_map"],
                        "measurement_consistent": lay["measurement_consistent"],
                        "f_calibration_snapshot": a["f"], "f_including_1q_errors": a["f_including_1q_errors"],
                        "mean_edge_error": a["mean_edge_error"], "mean_readout_error": a["mean_readout_error"],
                        "leakage_noiseless_transpiled": leak,
                        "qpy": qpy_name, "qpy_bytes_uncompressed": raw_bytes, "qpy_gz_sha256": sha,
                    })
                    manifests.append(man)
        print(f"B={twoB // 2}: {len([m for m in manifests if m['twoB'] == twoB])} circuits "
              f"({time.time() - t0:.0f} s)", flush=True)

    # ------------------------------------------------------------- readout calibration
    # a "patch" is the set of qubits that are READ OUT (the measured physical qubits);
    # routing ancillas are touched by SWAPs but never measured, so they need no calibration
    patches = sorted({tuple(m["readout_patch"]) for m in manifests})
    patch_index = {p: i for i, p in enumerate(patches)}
    for m in manifests:
        m["patch_index"] = patch_index[tuple(m["readout_patch"])]
        with open(os.path.join(cdir, m["id"] + ".json"), "w") as fh:
            json.dump(m, fh, indent=1)
    cal = []
    for pi, patch in enumerate(patches):
        preps = [("all0", (0,) * n), ("all1", (1,) * n)]
        preps += [(f"flip{q:02d}", tuple(1 if i == q else 0 for i in range(n))) for q in range(n)]
        for name, bits in preps:
            cid = f"cal_patch{pi}_{name}"
            qc = QuantumCircuit(n, n)
            for q, b in enumerate(bits):
                if b:
                    qc.x(q)
            qc.barrier()
            qc.measure(range(n), range(n))
            tq = transpile(qc, backend=backend, initial_layout=list(patch),
                           optimization_level=1, seed_transpiler=args.seed)
            lay = transpiled_layout(tq, n)
            if not lay["measurement_consistent"]:
                raise SystemExit(f"{cid}: measurement map does not match the final layout")
            if not args.no_verify:
                psi = logical_statevector(tq, n)
                want = sum(int(b) << q for q, b in enumerate(bits))
                if abs(abs(psi[want]) - 1.0) > 1e-9:
                    raise SystemExit(f"{cid}: transpiled preparation does not produce {bits}")
            qpy_name = cid + ".qpy.gz"
            raw_bytes, sha = dump_qpy_gz(tq, os.path.join(cdir, qpy_name))
            man = dict(common)
            tgt = backend.target
            man.update({"id": cid, "kind": "readout_calibration", "patch_index": pi,
                        "readout_error_snapshot": [float(tgt["measure"][(q,)].error)
                                                   for q in lay["logical_to_physical"]],
                        "prep_bits": list(bits), "prep_name": name,
                        "physical_qubits": lay["active_physical"],
                        "readout_patch": sorted(lay["logical_to_physical"]),
                        "logical_to_physical": lay["logical_to_physical"],
                        "measurement_map_clbit_to_physical": lay["measurement_map"],
                        "measurement_consistent": lay["measurement_consistent"],
                        "transpiler": {"optimization_level": 1, "seed_transpiler": args.seed,
                                       "initial_layout": list(patch)},
                        "ops": {kk: int(v) for kk, v in tq.count_ops().items()},
                        "qpy": qpy_name, "qpy_bytes_uncompressed": raw_bytes, "qpy_gz_sha256": sha})
            with open(os.path.join(cdir, cid + ".json"), "w") as fh:
                json.dump(man, fh, indent=1)
            cal.append(man)
    print(f"readout calibration: {len(cal)} circuits on {len(patches)} patch(es) "
          f"({time.time() - t0:.0f} s)", flush=True)

    # ------------------------------------------------------------------------ index
    by_rep = {}
    for r in args.reps:
        ms = [m for m in manifests if m["repetitions"] == r]
        by_rep[str(r)] = {
            "n_circuits": len(ms),
            "cz": {"mean": float(np.mean([m["cz"] for m in ms])), "min": int(min(m["cz"] for m in ms)),
                   "max": int(max(m["cz"] for m in ms))},
            "depth": {"mean": float(np.mean([m["depth"] for m in ms]))},
            "f": {"mean": float(np.mean([m["f_calibration_snapshot"] for m in ms])),
                  "min": float(min(m["f_calibration_snapshot"] for m in ms)),
                  "max": float(max(m["f_calibration_snapshot"] for m in ms))},
        }
    index = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "script": "scripts/h0_build_circuits.py",
        "arguments": vars(args),
        "common": common,
        "n_circuits": len(manifests), "n_calibration_circuits": len(cal),
        "repetitions": args.reps, "kmax": args.kmax,
        "sectors": {f"B={tb // 2}": len([m for m in manifests if m["twoB"] == tb]) for tb in (0, 2)},
        "references": {f"B={tb // 2}": references(M.basis, tb) for tb in (0, 2)},
        "per_repetition": by_rep,
        "distinct_readout_patches": [list(p) for p in patches],
        "distinct_active_qubit_sets": sorted({tuple(m["physical_qubits"]) for m in manifests}),
        "leakage": ({"max": float(max(leaks)), "mean": float(np.mean(leaks)), "tolerance": LEAK_TOL,
                     "n_checked": len(leaks)} if leaks else None),
        "circuits": [{kk: m[kk] for kk in ("id", "kind", "sector", "reference", "k", "repetitions", "cz",
                                           "depth", "f_calibration_snapshot", "physical_qubits",
                                           "readout_patch", "patch_index", "logical_to_physical",
                                           "leakage_noiseless_transpiled", "qpy")}
                     for m in manifests],
        "calibration_circuits": [{kk: m[kk] for kk in ("id", "kind", "patch_index", "prep_name",
                                                       "prep_bits", "physical_qubits",
                                                       "logical_to_physical", "qpy")} for m in cal],
        "runtime_s": time.time() - t0,
    }
    with open(os.path.join(outdir, "index.json"), "w") as fh:
        json.dump(index, fh, indent=1)
    size = sum(os.path.getsize(os.path.join(cdir, f)) for f in os.listdir(cdir))
    print(f"wrote {len(manifests)} + {len(cal)} circuits to {cdir} ({size / 1e6:.1f} MB on disk)")
    if leaks:
        print(f"max leakage {max(leaks):.3e} (tolerance {LEAK_TOL:g})")
    print(f"CZ per repetition: " + ", ".join(f"r={r}: {by_rep[str(r)]['cz']['mean']:.0f}" for r in args.reps))
    print(f"total {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

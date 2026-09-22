#!/usr/bin/env python3
"""
The diagnostic circuit set of prompts/19 step B — `data/hardware/H0_diag_prep/`.

Five circuits on patch 1 of the frozen set, in the `h0_build_circuits.py` format so that
`h0_submit.py`, `h0_qpu_time.py` and `ibm_account.check_backend` read them unchanged:

  `diag_patch1_t1w`   x on all 12, then 85 x [delay(128 dt) on all 12; barrier], measure.
                      A windowed T1 measurement at the production window length.
  `diag_patch1_ramw`  sx on all 12, the same 85 windows, then rz(pi) sx rz(pi) (= sx^dagger
                      up to a global phase), measure.  A windowed Ramsey (free-induction)
                      measurement: P(0) = (1 + e^{-T/T2*})/2 with no detuning.
  `B0_ref06_k1_rep1`  the FROZEN canary circuit, copied byte for byte from
                      `data/hardware/H0_prep` (sha256 asserted).  It is never rebuilt.
  `cal_patch1_all0`, `cal_patch1_all1`   the two patch-1 readout-calibration circuits,
                      also copied byte for byte.

The two new circuits are transpiled with `initial_layout = patch`, `optimization_level 0`
and `seed_transpiler 7` — exactly the recipe `h0_build_circuits.py` uses for the readout
calibration, so nothing is merged across a delay — and are verified before anything can be
submitted: the transpiled op multiset is the intended one, the noiseless statevector of the
TRANSPILED circuit gives the expected bit string with probability 1 - 1e-9, and the client
`PadDynamicalDecoupling` pass is run over the windows to record how many XY4 pulses a
scheduler inserts (information: the server-side pass may differ).

No QPU time, no account: everything is built on the calibration snapshot of the frozen set.

Usage: python scripts/h0_diag_circuits.py [--out data/hardware/H0_diag_prep]
Runtime: about 30 s on the i7-8750H.
"""
import argparse
import glob
import gzip
import hashlib
import json
import os
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.hardware import logical_statevector, transpiled_layout  # noqa: E402

from h0_backends import last_update_date, resolve_backend  # noqa: E402
from h0_build_circuits import dump_qpy_gz  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FROZEN_SET = os.path.join(ROOT, "data", "hardware", "H0_prep")
PATCH1 = [117, 122, 123, 124, 125, 136, 141, 142, 143, 144, 145, 146]
WINDOW_DT = 128            # 512 ns at dt = 4 ns
N_WINDOWS = 85             # 43.52 us of delay, the production circuit's 43.71 us
COPY_SHA = {
    "B0_ref06_k1_rep1": "8f372da0f5e88bdc404cf148d747024510501ee2822bdd35e63bf77375e8ada9",
}
COPY_IDS = ("B0_ref06_k1_rep1", "cal_patch1_all0", "cal_patch1_all1")
STATEVECTOR_TOL = 1e-9


def sha256_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build_t1w(n):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n, n)
    for q in range(n):
        qc.x(q)
    windows(qc, n)
    qc.barrier()
    qc.measure(range(n), range(n))
    return qc, tuple([1] * n)


def build_ramw(n):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(n, n)
    for q in range(n):
        qc.sx(q)
    windows(qc, n)
    for q in range(n):                  # rz(pi) sx rz(pi) = sx^dagger up to a global phase
        qc.rz(np.pi, q)
        qc.sx(q)
        qc.rz(np.pi, q)
    qc.barrier()
    qc.measure(range(n), range(n))
    return qc, tuple([0] * n)


def windows(qc, n):
    for _ in range(N_WINDOWS):
        for q in range(n):
            qc.delay(WINDOW_DT, q, unit="dt")
        qc.barrier()


def expected_ops(kind, n):
    """The op multiset the transpiled circuit must have, exactly."""
    base = {"delay": N_WINDOWS * n, "barrier": N_WINDOWS + 1, "measure": n}
    if kind == "t1w":
        base["x"] = n
    else:
        base["sx"] = 2 * n
        base["rz"] = 2 * n
    return base


def dd_padding_check(tq, record):
    """How many XY4 pulses the CLIENT PadDynamicalDecoupling inserts per qubit (prompts/19 B3)."""
    from collections import Counter

    from qiskit.circuit.library import XGate, YGate
    from qiskit.transpiler import InstructionDurations, PassManager
    from qiskit_ibm_runtime.transpiler.passes.scheduling import (ALAPScheduleAnalysis,
                                                                 PadDynamicalDecoupling)
    entries = []
    for q, v in record["qubits"].items():
        q = int(q)
        entries += [("sx", [q], v["sx_duration_s"], "s"), ("x", [q], v["x_duration_s"], "s"),
                    ("y", [q], v["x_duration_s"], "s"), ("rz", [q], 0.0, "s"),
                    ("measure", [q], v["measure_duration_s"], "s")]
    for v in record["edges"].values():
        a, b = v["target_key"]
        entries.append(("cz", [a, b], v["cz_duration_s"], "s"))
    dur = InstructionDurations(entries, dt=record["dt_s"])
    pm = PassManager([ALAPScheduleAnalysis(durations=dur),
                      PadDynamicalDecoupling(durations=dur,
                                             dd_sequences=[XGate(), YGate(), XGate(), YGate()],
                                             sequence_min_length_ratios=[2.0])])
    out = pm.run(tq)
    c = Counter()
    for circ, sign in ((out, +1), (tq, -1)):       # inserted = after - before
        for inst in circ.data:
            if inst.operation.name in ("x", "y"):
                c[int(circ.find_bit(inst.qubits[0]).index)] += sign
    before = {k: int(v) for k, v in tq.count_ops().items()}
    return {
        "pass": ("qiskit_ibm_runtime ALAPScheduleAnalysis + PadDynamicalDecoupling, XY4 = "
                 "X Y X Y, sequence_min_length_ratios 2.0, on the calibration record's durations"),
        "durations_from": record.get("stamp"),
        "pulses_per_physical_qubit": {str(k): int(v) for k, v in sorted(c.items())},
        "expected_per_qubit": 4 * N_WINDOWS,
        "ops_before": before,
        "ops_after": {k: int(v) for k, v in out.count_ops().items()},
        "note": ("this is the CLIENT pass with the client's defaults; the runtime applies its own "
                 "pass server-side and may differ.  It is information, never a criterion."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("data", "hardware", "H0_diag_prep"))
    ap.add_argument("--frozen", default=os.path.join("data", "hardware", "H0_prep"))
    ap.add_argument("--record", default=os.path.join("data", "hardware", "H0_ibm_fez_canary",
                                                     "calibration_at_submission_20260922T1400Z.json"),
                    help="durations for the (informational) DD padding check")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    t0 = time.time()

    frozen = os.path.join(ROOT, args.frozen) if not os.path.isabs(args.frozen) else args.frozen
    outdir = os.path.join(ROOT, args.out) if not os.path.isabs(args.out) else args.out
    cdir = os.path.join(outdir, "circuits")
    os.makedirs(cdir, exist_ok=True)
    with open(os.path.join(frozen, "index.json")) as fh:
        findex = json.load(fh)
    common = dict(findex["common"])
    n = int(common["n_logical_qubits"])
    if n != len(PATCH1):
        raise SystemExit(f"patch 1 has {len(PATCH1)} qubits, the codec has {n} logical qubits")
    if list(findex["distinct_readout_patches"][1]) != PATCH1:
        raise SystemExit(f"patch 1 of {args.frozen} is {findex['distinct_readout_patches'][1]}, "
                         f"not {PATCH1}")

    from qiskit import transpile
    backend = resolve_backend(common["backend"])
    target = backend.target
    dt = float(target.dt)
    if WINDOW_DT % int(target.granularity or 1):
        raise SystemExit(f"window {WINDOW_DT} dt is not a multiple of the target granularity "
                         f"{target.granularity}")
    if WINDOW_DT % int(target.pulse_alignment or 1):
        raise SystemExit(f"window {WINDOW_DT} dt is not a multiple of pulse_alignment "
                         f"{target.pulse_alignment}")
    window_s = WINDOW_DT * dt
    total_delay_s = N_WINDOWS * window_s
    print(f"window {WINDOW_DT} dt = {window_s * 1e9:.0f} ns, {N_WINDOWS} windows = "
          f"{total_delay_s * 1e6:.2f} us on {common['backend']} (dt {dt})")

    rp = args.record if os.path.isabs(args.record) else os.path.join(ROOT, args.record)
    with open(rp) as fh:
        record = json.load(fh)

    manifests = []
    for kind, builder in (("t1w", build_t1w), ("ramw", build_ramw)):
        cid = f"diag_patch1_{kind}"
        qc, expected = builder(n)
        tq = transpile(qc, backend=backend, initial_layout=list(PATCH1),
                       optimization_level=0, seed_transpiler=args.seed)
        ops = {k: int(v) for k, v in tq.count_ops().items()}
        want = expected_ops(kind, n)
        if ops != want:
            raise SystemExit(f"{cid}: transpiled ops {ops} != the intended {want}; the optimizer "
                             f"touched a level-0 circuit")
        lay = transpiled_layout(tq, n)
        if lay["logical_to_physical"] != list(PATCH1):
            raise SystemExit(f"{cid}: final layout {lay['logical_to_physical']} != patch {PATCH1}")
        if not lay["measurement_consistent"]:
            raise SystemExit(f"{cid}: measurement map {lay['measurement_map']} does not match "
                             f"the final layout")
        psi = logical_statevector(tq, n)
        want_index = sum(int(b) << q for q, b in enumerate(expected))
        p = float(abs(psi[want_index]) ** 2)
        if p < 1.0 - STATEVECTOR_TOL:
            raise SystemExit(f"{cid}: noiseless P({''.join(str(b) for b in expected)}) = {p!r} "
                             f"< 1 - {STATEVECTOR_TOL:g}")
        dd = dd_padding_check(tq, record)
        qpy_name = cid + ".qpy.gz"
        raw_bytes, sha = dump_qpy_gz(tq, os.path.join(cdir, qpy_name))
        man = dict(common)
        man.update({
            "id": cid, "kind": "idle_test", "test": kind, "patch_index": 1,
            "expected_bits": list(expected),
            "expected_key": "".join(str(b) for b in reversed(expected)),
            "n_windows": N_WINDOWS, "window_dt": WINDOW_DT, "window_s": window_s,
            "total_delay_s": total_delay_s,
            "noiseless_probability_of_the_expected_string": p,
            "physical_qubits": lay["active_physical"],
            "readout_patch": sorted(lay["logical_to_physical"]),
            "logical_to_physical": lay["logical_to_physical"],
            "measurement_map_clbit_to_physical": lay["measurement_map"],
            "measurement_consistent": lay["measurement_consistent"],
            "transpiler": {"optimization_level": 0, "seed_transpiler": args.seed,
                           "initial_layout": list(PATCH1)},
            "depth": int(tq.depth()), "ops": ops,
            "dd_padding_check": dd,
            "qpy": qpy_name, "qpy_bytes_uncompressed": raw_bytes, "qpy_gz_sha256": sha,
            "purpose": ("prompts/19 D3: the per-qubit T1 and T2* of the patch at the production "
                        "window length, with and without dynamical decoupling"),
        })
        with open(os.path.join(cdir, cid + ".json"), "w") as fh:
            json.dump(man, fh, indent=1)
        manifests.append(man)
        print(f"  {cid}: {ops}, P(expected) = {p:.12f}, DD pulses per qubit "
              f"{sorted(set(dd['pulses_per_physical_qubit'].values()))}")

    copied = []
    for cid in COPY_IDS:
        src_q = os.path.join(frozen, "circuits", cid + ".qpy.gz")
        src_m = os.path.join(frozen, "circuits", cid + ".json")
        with open(src_m) as fh:
            man = json.load(fh)
        sha = sha256_of(src_q)
        if man.get("qpy_gz_sha256") != sha:
            raise SystemExit(f"{cid}: the frozen manifest records {man.get('qpy_gz_sha256')}, the "
                             f"file on disk hashes to {sha}")
        if cid in COPY_SHA and sha != COPY_SHA[cid]:
            raise SystemExit(f"{cid}: sha256 {sha} != the frozen {COPY_SHA[cid]} of prompts/19")
        if man.get("patch_index") != 1:
            raise SystemExit(f"{cid}: patch_index {man.get('patch_index')} is not 1")
        shutil.copyfile(src_q, os.path.join(cdir, cid + ".qpy.gz"))
        if sha256_of(os.path.join(cdir, cid + ".qpy.gz")) != sha:
            raise SystemExit(f"{cid}: the copy does not hash to the original")
        man = dict(man)
        man["copied_from"] = os.path.relpath(src_q, ROOT)
        man["copied_byte_for_byte"] = True
        with open(os.path.join(cdir, cid + ".json"), "w") as fh:
            json.dump(man, fh, indent=1)
        copied.append(man)
        print(f"  {cid}: copied byte for byte ({man['kind']}, sha256 {sha[:16]})")

    allm = manifests + copied
    qubits, edges, ops = set(), set(), set()
    from qiskit import qpy as _qpy
    for m in allm:
        qubits.update(m["physical_qubits"])
        ops.update(m["ops"])
        with gzip.open(os.path.join(cdir, m["qpy"]), "rb") as fh:
            qc = _qpy.load(fh)[0]
        for inst in qc.data:
            if len(inst.qubits) == 2 and inst.operation.name != "barrier":
                a, b = (qc.find_bit(q).index for q in inst.qubits)
                edges.add((a, b))
            for q in inst.qubits:
                qubits.add(qc.find_bit(q).index)
    index = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "script": "scripts/h0_diag_circuits.py",
        "arguments": vars(args),
        "purpose": ("prompts/19: the diagnostic set that separates hypothesis H_A (idle-time "
                    "relaxation omitted from the prediction) from H_B (the SamplerV2 options)"),
        "common": common,
        "frozen_set_source": os.path.relpath(frozen, ROOT),
        "frozen_set": {"qubits": sorted(qubits), "edges": sorted(map(list, edges)),
                       "ops": sorted(ops), "n_edges": len(edges)},
        "patch_index": 1, "patch": list(PATCH1),
        "window_dt": WINDOW_DT, "window_s": window_s, "n_windows": N_WINDOWS,
        "total_delay_s": total_delay_s,
        "n_circuits": len([m for m in allm if m["kind"] != "readout_calibration"]),
        "n_calibration_circuits": len([m for m in allm if m["kind"] == "readout_calibration"]),
        "circuits": [{k: m.get(k) for k in ("id", "kind", "patch_index", "physical_qubits",
                                            "logical_to_physical", "ops", "qpy", "qpy_gz_sha256")}
                     for m in allm],
        "runtime_s": time.time() - t0,
    }
    with open(os.path.join(outdir, "index.json"), "w") as fh:
        json.dump(index, fh, indent=1)
    print(f"wrote {len(allm)} circuits to {os.path.relpath(cdir, ROOT)} "
          f"({len(qubits)} physical qubits, {len(edges)} edges, ops {sorted(ops)}) "
          f"in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

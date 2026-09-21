#!/usr/bin/env python3
"""
Compare two frozen H0 circuit sets circuit by circuit (prompts/15 step A1).

Part A of prompts/15 touches `scripts/h0_build_circuits.py`; the frozen set
`data/hardware/H0_prep` is the one artefact of gate H0P that must not move, so the
change is verified by rebuilding the set into a scratch directory and comparing:

  * `qpy.load` both circuits and require `QuantumCircuit.__eq__`,
  * equal `count_ops()`,
  * equal `layout.final_index_layout()` (the physical qubits the transpiler chose),
  * equal manifest fields cz, depth, physical_qubits, logical_to_physical,
    measurement_map_clbit_to_physical, f_calibration_snapshot (to 1e-12).

The sha256 of the .qpy.gz files is NOT the comparison: the gzip container stores a
timestamp, so two byte-identical circuits give two different archives.

Usage: python scripts/h0_compare_prep.py data/hardware/H0_prep /tmp/H0_prep_repro
Exit code 0 when every id is identical, 1 otherwise.
"""
import glob
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
F_TOL = 1e-12
FIELDS = ("cz", "depth", "physical_qubits", "logical_to_physical",
          "measurement_map_clbit_to_physical", "f_calibration_snapshot")


def manifests(prep):
    out = {}
    for p in sorted(glob.glob(os.path.join(prep, "circuits", "*.json"))):
        with open(p) as fh:
            m = json.load(fh)
        out[m["id"]] = m
    return out


def load_qpy(prep, man):
    from qiskit import qpy
    with gzip.open(os.path.join(prep, "circuits", man["qpy"]), "rb") as fh:
        return qpy.load(fh)[0]


def final_layout(qc):
    lay = getattr(qc, "layout", None)
    if lay is None:
        return None
    try:
        return list(lay.final_index_layout())
    except Exception:
        return None


def compare(a_dir, b_dir):
    A, B = manifests(a_dir), manifests(b_dir)
    problems = []
    if set(A) != set(B):
        only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
        problems.append(f"different circuit ids: only in {a_dir}: {only_a[:5]}; only in {b_dir}: {only_b[:5]}")
    same = 0
    for cid in sorted(set(A) & set(B)):
        ma, mb = A[cid], B[cid]
        bad = []
        for k in FIELDS:
            if (k in ma) != (k in mb):
                bad.append(f"{k}: present in only one manifest")
                continue
            if k not in ma:
                continue
            va, vb = ma[k], mb[k]
            if isinstance(va, float) or isinstance(vb, float):
                if va is None or vb is None:
                    if va is not vb:
                        bad.append(f"{k}: {va} != {vb}")
                elif abs(float(va) - float(vb)) > F_TOL:
                    bad.append(f"{k}: {va} != {vb}")
            elif va != vb:
                bad.append(f"{k}: {va} != {vb}")
        qa, qb = load_qpy(a_dir, ma), load_qpy(b_dir, mb)
        if qa != qb:
            bad.append("QuantumCircuit.__eq__ is False")
        if dict(qa.count_ops()) != dict(qb.count_ops()):
            bad.append(f"count_ops {dict(qa.count_ops())} != {dict(qb.count_ops())}")
        la, lb = final_layout(qa), final_layout(qb)
        if la != lb:
            bad.append(f"final_index_layout {la} != {lb}")
        if bad:
            problems.append(f"{cid}: " + "; ".join(bad))
        else:
            same += 1
    return same, len(set(A) & set(B)), problems


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python scripts/h0_compare_prep.py <prep dir A> <prep dir B>")
    dirs = [d if os.path.isabs(d) else os.path.join(ROOT, d) for d in sys.argv[1:3]]
    for d in dirs:
        if not os.path.isdir(os.path.join(d, "circuits")):
            raise SystemExit(f"{d} is not a frozen circuit set (no circuits/ directory)")
    same, total, problems = compare(*dirs)
    for p in problems:
        print(f"  x {p}")
    print(f"{same}/{total} identical  ({sys.argv[1]} vs {sys.argv[2]}: "
          f"QuantumCircuit equality, count_ops, final_index_layout and the manifest fields "
          f"{', '.join(FIELDS)})")
    if problems:
        print(f"{len(problems)} difference(s)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

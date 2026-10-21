"""Freeze a compressed family into data/families/<name>.json.gz (the file `c2x4.families.get_family` loads).

Builds every circuit from the construction code (cache allowed: the content hash recorded here is what the loader
re-checks), records per-circuit counts and metadata, and the family-level provenance.  It does NOT verify: the
verification record is a separate file named in --verification (eval_family.py / verify_aer_family.py output), and
this script refuses to freeze if that file is missing, does not list every circuit, or any circuit there fails or has
different two-qubit counts from the frozen gate list.

Usage:
  python scripts/freeze_family.py --name compressed_circuit_llm_2x4_classB_v1 --spec arch:it5:input:pp --lx 4 \
      --kmax 5 --verification data/eval_arch_it5_input_pp_all75_pruned.json --version v1 \
      --source "loop iteration 5 (data/archive_it5.json), peephole pass; reviewed in reviews/001"
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import STUDY, git_commit, machine                       # noqa: E402
from c2x4.evaluate import counts                                      # noqa: E402
from c2x4.families import CONTRACTS, FAMILY_DIR, canonical_name, encode_gates, gates_sha256   # noqa: E402
from c2x4.family import archive_family, circuit                      # noqa: E402
from c2x4.problem import get_problem                                  # noqa: E402


def build_family(spec: str, lx: int):
    parts = spec.split(":")
    if parts[0] != "arch":
        raise ValueError("only archive families (arch:<label>:<input|operator>[:pp]) are frozen")
    return archive_family(parts[1], parts[2], peephole=(len(parts) > 3 and parts[3] == "pp"), lx=lx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--lx", type=int, default=4)
    ap.add_argument("--kmax", type=int, default=5)
    ap.add_argument("--verification", required=True, nargs="+")
    ap.add_argument("--version", required=True)
    ap.add_argument("--source", required=True)
    args = ap.parse_args()
    t0 = time.time()
    name = canonical_name(args.name)
    P = get_problem(args.lx)
    fam = build_family(args.spec, args.lx)
    cls = "B" if fam["class"] == "input" else "A"
    # verification records (all must pass and cover every circuit)
    ver = {}
    for vp in args.verification:
        with open(os.path.join(STUDY, vp)) as fh:
            vd = json.load(fh)
        for cid, row in vd["circuits"].items():
            ver[cid] = (vp, row)
    ids = P.circuit_ids(args.kmax)
    circuits = []
    for (twoB, ref, k) in ids:
        cid = P.tag(twoB, ref, k)
        g = circuit(P, fam, twoB, ref, k)
        c = counts(g)
        if cid not in ver:
            raise SystemExit(f"{cid}: no verification record in {args.verification}")
        vp, row = ver[cid]
        if not row["verification"]["pass"]:
            raise SystemExit(f"{cid}: verification record says FAIL")
        if row["counts"]["n_2q"] != c["n_2q"] or row["counts"]["depth_2q"] != c["depth_2q"]:
            raise SystemExit(f"{cid}: counts differ from the verification record "
                             f"({c['n_2q']}/{c['depth_2q']} vs {row['counts']['n_2q']}/{row['counts']['depth_2q']})")
        enc = encode_gates(g)
        th = P.theta(twoB, k)
        phi = float(th * P.diag_index[ref]) if fam["drop_diag"] else 0.0
        v = row["verification"]
        md = {"circuit_id": cid, "lattice": P.lattice, "family": name, "class": cls, "version": args.version,
              "twoB": int(twoB), "reference": int(ref), "reference_bits": int(P.ref_int(ref)), "k": int(k),
              "dt": float(P.dt[twoB]), "theta": float(th), "n_qubits": int(P.n), "n_2q": c["n_2q"],
              "n_1q": c["n_1q"], "depth_2q": c["depth_2q"], "ops": c["by_name"],
              "contract": CONTRACTS[cls][0], "valid_use": CONTRACTS[cls][1],
              "global_phase_vs_target": phi,
              "content_sha256": gates_sha256(enc), "source": args.source,
              "verification": {"file": vp, "pass": bool(v["pass"]),
                               "max_dev_phase_aligned": v["max_dev_phase_aligned"],
                               "certified_max_dev": v.get("certified_max_dev"),
                               "certified_leakage": v.get("certified_leakage"),
                               "leakage_direct": v.get("leakage_direct")}}
        circuits.append({"metadata": md, "gates": enc})
        print(f"{cid}: 2q {c['n_2q']} depth {c['depth_2q']} sha {md['content_sha256'][:12]}", flush=True)
    n2 = [c["metadata"]["n_2q"] for c in circuits]
    d2 = [c["metadata"]["depth_2q"] for c in circuits]
    out = {"name": name, "lattice": P.lattice, "class": cls, "version": args.version, "spec": args.spec,
           "source": args.source, "contract": CONTRACTS[cls][0], "valid_use": CONTRACTS[cls][1],
           "n_circuits": len(circuits), "n_qubits": int(P.n), "kmax": args.kmax,
           "dt": {str(k): v for k, v in P.dt.items()}, "dt_source": P.dt_source, "g2": P.g2, "m": P.m,
           "n_2q": {"min": min(n2), "max": max(n2), "mean": sum(n2) / len(n2)},
           "depth_2q": {"min": min(d2), "max": max(d2), "mean": sum(d2) / len(d2)},
           "verification_files": args.verification,
           "conventions": "IR qubit k = qiskit qubit k = bit k of the basis integer (skqd.reference_sim, "
                          "little-endian); codec layout of skqd.codec; term order of krylov.apply_groups",
           "produced_by": "2x4_compression_using_ai_v1/scripts/freeze_family.py", "git_commit": git_commit(),
           "machine": machine(), "written_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
           "wall_s": time.time() - t0, "circuits": circuits}
    os.makedirs(FAMILY_DIR, exist_ok=True)
    p = os.path.join(FAMILY_DIR, name + ".json.gz")
    with gzip.open(p, "wt", compresslevel=9) as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("wrote", p, os.path.getsize(p), "bytes")


if __name__ == "__main__":
    main()

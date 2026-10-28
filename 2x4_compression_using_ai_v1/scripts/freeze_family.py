"""Freeze a compressed family into <lattice folder>/data/families/<name>.json.gz (the file `c2x4.families.get_family`
loads; lattice folder = 2x4_/2x3_/2x2_compression_using_ai_v1, notes/012).

Builds every circuit from the construction code (cache allowed: the content hash recorded here is what the loader
re-checks), records per-circuit counts and metadata, and the family-level provenance.  It does NOT verify: the
verification record is a separate file named in --verification (eval_family.py / verify_aer_family.py output), and
this script refuses to freeze if that file is missing, does not list every circuit, or any circuit there fails or has
different two-qubit counts from the frozen gate list.

Usage:
  python scripts/freeze_family.py --name compressed_circuit_llm_2x4_classB_v1 --spec arch:it5:input:pp --lx 4 \
      --kmax 5 --verification data/eval_arch_it5_input_pp_all75_pruned.json --version v1 \
      --source "loop iteration 5 (data/archive_it5.json), peephole pass; reviewed in reviews/001"
--verification paths are relative to 2x4_compression_using_ai_v1/, or to the repository root when they start with a
study folder name (e.g. 2x3_compression_using_ai_v1/data/c2x3/eval_....json).

Add-on families (owner 2026-10-28, notes/014): `--kmin 5 --kmax 5 --addon-of <base family>` freezes only the k = 5
circuit of every reference, built from the SAME spec (same loop-archive choices) as the frozen base family.  The script
refuses to write unless (i) the spec, lattice, class and dt equal the base family's header and (ii) every circuit's gate
skeleton (gate names and qubits, angles ignored) and its counts (n_2q, n_1q, depth_2q, ops) equal those of EVERY k = 1..4
circuit of the same (2B, reference) in the base file.  The base file is only read.
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
from c2x4.env import ROOT                                                                        # noqa: E402
from c2x4.families import CONTRACTS, canonical_name, encode_gates, family_dir, family_path, gates_sha256   # noqa: E402
from c2x4.family import archive_family, circuit                      # noqa: E402
from c2x4.problem import get_problem                                  # noqa: E402


def build_family(spec: str, lx: int):
    parts = spec.split(":")
    if parts[0] != "arch":
        raise ValueError("only archive families (arch:<label>:<input|operator>[:pp]) are frozen")
    from c2x4.family import family_from_spec
    return family_from_spec(spec, lx=lx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--lx", type=int, default=4)
    ap.add_argument("--kmax", type=int, default=5)
    ap.add_argument("--kmin", type=int, default=1, help="freeze only k = kmin..kmax (add-on families: 5)")
    ap.add_argument("--addon-of", default=None, help="frozen base family whose k = 1..4 skeletons/counts must match")
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
        base = ROOT if vp.split("/")[0].endswith("_compression_using_ai_v1") else STUDY
        with open(vp if os.path.isabs(vp) else os.path.join(base, vp)) as fh:
            vd = json.load(fh)
        for cid, row in vd["circuits"].items():
            ver[cid] = (vp, row)
    ids = [x for x in P.circuit_ids(args.kmax) if x[2] >= args.kmin]
    base = None
    if args.addon_of:
        import hashlib
        from c2x4.families import decode_gates, family_header, load_frozen
        bh = family_header(args.addon_of)
        for key, want in (("spec", args.spec), ("lattice", P.lattice), ("class", cls)):
            if bh[key] != want:
                raise SystemExit(f"add-on: base family {key} {bh[key]!r} != {want!r}")
        if {int(k_): v for k_, v in bh["dt"].items()} != {int(k_): v for k_, v in P.dt.items()}:
            raise SystemExit(f"add-on: base family dt {bh['dt']} != {P.dt}")

        def _skel(gl):
            return hashlib.sha256(repr([(str(nm_), [int(q_) for q_ in qs_]) for nm_, qs_, _p in gl]).encode()).hexdigest()
        base = {}
        for c in load_frozen(args.addon_of)["circuits"]:
            bm = c["metadata"]
            base.setdefault((bm["twoB"], bm["reference"]), []).append(
                (bm["k"], _skel(decode_gates(c["gates"])), bm["n_2q"], bm["n_1q"], bm["depth_2q"], bm["ops"]))
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
        addon = None
        if base is not None:
            rows_b = base.get((twoB, ref))
            if not rows_b or sorted(r_[0] for r_ in rows_b) != [1, 2, 3, 4]:
                raise SystemExit(f"{cid}: base family {args.addon_of} lacks k = 1..4 for this reference")
            sk = _skel(g)
            for (kb, skb, n2b, n1b, d2b, opsb) in rows_b:
                if (sk, c["n_2q"], c["n_1q"], c["depth_2q"], c["by_name"]) != (skb, n2b, n1b, d2b, opsb):
                    raise SystemExit(f"{cid}: skeleton/counts differ from the base family's k = {kb} circuit")
            addon = {"base_family": canonical_name(args.addon_of), "skeleton_sha256": sk,
                     "same_skeleton_and_counts_as_base_k": [1, 2, 3, 4]}
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
        if addon is not None:
            md["addon"] = addon
        circuits.append({"metadata": md, "gates": enc})
        print(f"{cid}: 2q {c['n_2q']} depth {c['depth_2q']} sha {md['content_sha256'][:12]}", flush=True)
    n2 = [c["metadata"]["n_2q"] for c in circuits]
    d2 = [c["metadata"]["depth_2q"] for c in circuits]
    out = {"name": name, "lattice": P.lattice, "class": cls, "version": args.version, "spec": args.spec,
           "source": args.source, "contract": CONTRACTS[cls][0], "valid_use": CONTRACTS[cls][1],
           "n_circuits": len(circuits), "n_qubits": int(P.n), "kmax": args.kmax, "kmin": args.kmin,
           "dt": {str(k): v for k, v in P.dt.items()}, "dt_source": P.dt_source, "g2": P.g2, "m": P.m,
           "n_2q": {"min": min(n2), "max": max(n2), "mean": sum(n2) / len(n2)},
           "depth_2q": {"min": min(d2), "max": max(d2), "mean": sum(d2) / len(d2)},
           "verification_files": args.verification,
           "conventions": "IR qubit k = qiskit qubit k = bit k of the basis integer (skqd.reference_sim, "
                          "little-endian); codec layout of skqd.codec; term order of krylov.apply_groups",
           "produced_by": "2x4_compression_using_ai_v1/scripts/freeze_family.py", "git_commit": git_commit(),
           "machine": machine(), "written_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
           "wall_s": time.time() - t0, "circuits": circuits}
    if base is not None:
        from c2x4.families import family_path as _fp
        import hashlib as _hl
        with open(_fp(args.addon_of), "rb") as fh:
            out["addon_of"] = {"family": canonical_name(args.addon_of),
                               "file": os.path.relpath(_fp(args.addon_of), ROOT),
                               "file_sha256": _hl.sha256(fh.read()).hexdigest(),
                               "rule": "same spec (loop-archive choices), same dt; every circuit's skeleton and counts "
                                       "equal the base family's k = 1..4 circuits of the same reference (checked)"}
    os.makedirs(family_dir(name), exist_ok=True)
    p = family_path(name)
    if os.path.exists(p):
        raise SystemExit(f"{p} exists: frozen files are never rewritten (notes/009)")
    with gzip.open(p, "wt", compresslevel=9) as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("wrote", p, os.path.getsize(p), "bytes")


if __name__ == "__main__":
    main()

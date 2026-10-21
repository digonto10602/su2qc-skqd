"""Write the IR of selected circuits of a family to data/cache/finalists_<label>.pkl (input of native_check.py),
plus data/cache/codeword_ints.npy and the exact targets (data/cache/target_<tag>.npy).

Usage: python scripts/dump_finalists.py --family arch:it4:input:pp --circuits 0:102:1,2:230:1 --label it4_input
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.env import CACHE                                       # noqa: E402
from c2x4.family import FAMILIES, archive_family, circuit         # noqa: E402
from c2x4.problem import get_problem                              # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True)
    ap.add_argument("--circuits", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--kmax", type=int, default=5)
    args = ap.parse_args()
    P = get_problem()
    if args.family.startswith("arch:"):
        parts = args.family.split(":")
        fam = archive_family(parts[1], parts[2], peephole=(len(parts) > 3 and parts[3] == "pp"))
    else:
        fam = FAMILIES[args.family]
    ids = P.circuit_ids(args.kmax) if args.circuits == "all" else \
        [tuple(int(v) for v in s.split(":")) for s in args.circuits.split(",")]
    items = []
    for (twoB, ref, k) in ids:
        g = circuit(P, fam, twoB, ref, k)
        P.target(twoB, ref, k)                        # makes sure the target is cached
        items.append({"tag": P.tag(twoB, ref, k), "twoB": twoB, "ref": ref, "k": k, "family": args.family,
                      "gates": g})
    os.makedirs(CACHE, exist_ok=True)
    np.save(os.path.join(CACHE, "codeword_ints.npy"), P.ints)
    with open(os.path.join(CACHE, f"finalists_{args.label}.pkl"), "wb") as fh:
        pickle.dump(items, fh)
    print("wrote", len(items), "circuits")


if __name__ == "__main__":
    main()

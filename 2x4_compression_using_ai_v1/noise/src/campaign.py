"""Noisy SKQD campaign (owner 2026-10-29: "do the noise sampling with the compressed circuits for all lattices"):
families, circuit lists, sample-file layout and the shot plan.  Read by scripts/skqd_sample.py (one chunk of
trajectories), scripts/skqd_queue.py (the background queue) and scripts/skqd_analyse.py (the SKQD pipeline).

Campaign family -> circuits (all k = 1..4 and k = 5 where it exists, which CV3 needs):
  2x2 / 2x3 compressed classA, classB  : genie family <name> (k 1..4) + <name>_k5 (k = 5), notes/009 + notes/014
  2x4 compressed classA_v2, classB_v2   : genie family <name> (k 1..5 in one family)
  2x4 compressed classA_v1, classB_v1   : genie family <name> (k 1..5), only if time allows
  frozen 2x2 / 2x3                      : the package's coarse_step IR (circuits.ir_gates), ids from
                                          data/quantinuum/circuits_2x{L} (k 1..4) and circuits_2x{L}_k5 (k = 5)
Sample files: <lattice results>/<family>/<device>/skqd_samples/<cid>/c<NNN>.npz (+ .json meta), chunk NNN covers
shots [start, start + shots) of that circuit's shot sequence; the analysis concatenates chunks in order.
"""
from __future__ import annotations

import glob
import json
import os
import zlib

from circuits import ROOT, NOISE, genie_ir
from results import lattice_results

PRIMARY = "quantinuum_h2_2"
SECONDARY = "quantinuum_helios_1"
BUDGET_JSON = os.path.join(NOISE, "notes", "campaign_budget.json")

FAMILIES = {
    "2x2": ["compressed_circuit_llm_2x2_classA", "compressed_circuit_llm_2x2_classB", "frozen"],
    "2x3": ["compressed_circuit_llm_2x3_classA", "compressed_circuit_llm_2x3_classB", "frozen"],
    "2x4": ["compressed_circuit_llm_2x4_classA_v2", "compressed_circuit_llm_2x4_classB_v2",
            "compressed_circuit_llm_2x4_classA_v1", "compressed_circuit_llm_2x4_classB_v1"],
}


def short(family: str) -> str:
    return family.replace("compressed_circuit_llm_", "")


def parse(cid: str):
    b, r, k = cid.split("_")
    return 2 * int(b[1:]), int(r[3:]), int(k[1:])


def circuits(lattice: str, family: str) -> dict:
    """{cid: source} with source = (ir family name or 'frozen')."""
    out = {}
    if family == "frozen":
        L = lattice.split("x")[1]
        for sub in (f"circuits_2x{L}", f"circuits_2x{L}_k5"):
            for p in sorted(glob.glob(os.path.join(ROOT, "data", "quantinuum", sub, "B*_ref*_k*.qasm"))):
                out[os.path.basename(p)[:-5]] = "frozen"
        return out
    for cid in genie_ir(family):
        out[cid] = family
    if lattice in ("2x2", "2x3"):
        for cid in genie_ir(family + "_k5"):
            out[cid] = family + "_k5"
    return out


def sample_dir(lattice, family, device, cid):
    return os.path.join(lattice_results(lattice), family, device, "skqd_samples", cid)


def chunk_path(lattice, family, device, cid, chunk):
    return os.path.join(sample_dir(lattice, family, device, cid), f"c{int(chunk):03d}.npz")


def chunk_seed(lattice, family, device, cid, chunk) -> int:
    return zlib.crc32(f"{lattice}|{family}|{device}|{cid}|skqd|{int(chunk)}".encode()) % 2 ** 31


def load_budget() -> dict:
    with open(BUDGET_JSON) as fh:
        return json.load(fh)

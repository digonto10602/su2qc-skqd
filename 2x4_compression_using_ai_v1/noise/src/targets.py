"""Exact targets from the package (read-only): krylov.coarse_states, codeword embedding, sectors.

Target for circuit (lattice Lx, twoB, ref, k): coarse_states(term_groups(Model(Lx).terms, g2, mass_default(g2)),
basis_vector(ref), dt, k)[k] with dt read from validation/E3.json (the value the circuits were built with),
embedded on the codewords CodewordEmbedding(Model(Lx)).ints (qubit k = bit k, little-endian).
"""
from __future__ import annotations

import functools
import json
import os

import numpy as np

from circuits import ROOT

G2 = 4.0


@functools.lru_cache(maxsize=None)
def model(Lx: int):
    from skqd.exact import Model, mass_default
    from skqd.krylov import term_groups
    from skqd.reference_sim import CodewordEmbedding
    M = Model(Lx)
    m = mass_default(G2)
    groups = term_groups(M.terms, G2, m)
    E = CodewordEmbedding(M)
    return {"M": M, "m": m, "groups": groups, "ints": np.asarray(E.ints, dtype=np.int64), "n": int(E.n),
            "dim": M.basis.dim, "codec": E.codec}


def dt_of(Lx: int, twoB: int) -> float:
    E3 = json.load(open(os.path.join(ROOT, "validation", "E3.json")))["data"]["references"]
    return float(E3[f"2x{Lx}|g2={G2}|2B={twoB}"]["dt"])


def sector(Lx: int, twoB: int) -> np.ndarray:
    return np.asarray(model(Lx)["M"].basis.sector(twoB))


@functools.lru_cache(maxsize=256)
def target(Lx: int, twoB: int, ref: int, k: int) -> np.ndarray:
    """Exact coarse state in the dressed basis (complex128), length = basis dim."""
    from skqd.krylov import basis_vector, coarse_states
    d = model(Lx)
    return coarse_states(d["groups"], basis_vector(d["dim"], ref), dt_of(Lx, twoB), k)[k]


def ideal_distribution(Lx: int, twoB: int, ref: int, k: int) -> dict:
    """Ideal computational-basis distribution {28/20-bit integer: probability} on the codewords."""
    t = target(Lx, twoB, ref, k)
    ints = model(Lx)["ints"]
    p = np.abs(t) ** 2
    nz = np.nonzero(p > 0)[0]
    return {int(ints[i]): float(p[i]) for i in nz}

"""The fixed 2xLx problem (Lx = 4 by default, Lx = 3 for C3): model, term groups, codewords, references, dt,
exact target states.

Everything is read from the package (read-only).  The lattice is a parameter (C3, notes/010): Lx = 4 reads dt from
`data/quantinuum/circuits_2x4/index.json` (copied from validation/E3.json), Lx = 3 from the frozen 2x3 family's
manifests `data/quantinuum/circuits_2x3/<id>.manifest.json` (gate_S2D.circuit_set(3): `Model(3).reference(4, 2B).dt`),
cross-checked against the package call.  Cache files of Lx != 4 carry the prefix `L<Lx>_`.  The exact target of circuit (2B, reference, k)
is `krylov.apply_groups(groups, e_ref, k dt)` -- the same call as `krylov.coarse_states` -- in
complex128 with `scipy.sparse.linalg.expm_multiply`, on the 37 165-dimensional dressed basis.
"""
from __future__ import annotations

import gzip
import json
import os
import pickle
from functools import cached_property

import numpy as np
import scipy.sparse as sp

from . import env  # noqa: F401  (puts the package on sys.path)
from .env import CACHE, ROOT

from skqd.circuits_ir import CircuitFactory, structured_term_gates   # noqa: E402
from skqd.exact import Model, mass_default                            # noqa: E402
from skqd.krylov import apply_groups, basis_vector, references        # noqa: E402
from skqd.reference_sim import CodewordEmbedding, localize, term_support   # noqa: E402

G2 = 4.0
LX = 4                                  # default lattice (2x4); Problem(lx=3) for 2x3


class Problem:
    """Lazy container for the 2xLx model data used by every evaluator and family."""

    def __init__(self, lx: int = LX):
        self.lx = int(lx)
        self.lattice = f"2x{self.lx}"
        self.cache_prefix = "" if self.lx == 4 else f"L{self.lx}_"
        self.M = Model(self.lx)
        self.g2 = G2
        self.m = mass_default(G2)
        self.groups = self.M.terms.groups(G2, self.m)          # ordered: diag, hop0..9, plaq0..2
        self.names = list(self.groups)
        self.mats = [sp.csr_matrix(self.groups[nm]) for nm in self.names]
        self.E = CodewordEmbedding(self.M)
        self.n = int(self.E.n)
        self.ints = self.E.ints                                 # basis index -> n-bit integer
        self.refs = {twoB: [int(r) for r in references(self.M.basis, twoB)] for twoB in (0, 2)}
        if self.lx == 4:
            with open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x4", "index.json")) as fh:
                self.dt = {int(k): float(v) for k, v in json.load(fh)["dt"].items()}
            self.dt_source = "data/quantinuum/circuits_2x4/index.json (copied from validation/E3.json)"
        elif self.lx == 3:
            self.dt = {}
            for twoB in (0, 2):
                tag = self.tag(twoB, self.refs[twoB][0], 1)
                with open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", f"{tag}.manifest.json")) as fh:
                    self.dt[twoB] = float(json.load(fh)["dt"])
            self.dt_source = "data/quantinuum/circuits_2x3/<B*_ref*_k1>.manifest.json (frozen 2x3 family)"
        else:
            self.dt = {twoB: float(self.M.reference(G2, twoB).dt) for twoB in (0, 2)}
            self.dt_source = f"Model({self.lx}).reference({G2}, 2B).dt"

    # ---------------------------------------------------------------- circuits
    def circuit_ids(self, kmax: int = 4) -> list:
        return [(twoB, r, k) for twoB in (0, 2) for r in self.refs[twoB] for k in range(1, kmax + 1)]

    def term_names(self) -> list:
        """Every non-diagonal term in the package order (hop0.., plaq0..)."""
        return list(self.names[1:])

    def cpath(self, fname: str) -> str:
        """Cache path with the lattice prefix (2x4 caches keep their historical names)."""
        return os.path.join(CACHE, self.cache_prefix + fname)

    @staticmethod
    def tag(twoB: int, ref: int, k: int) -> str:
        return f"B{twoB // 2}_ref{ref}_k{k}"

    def theta(self, twoB: int, k: int) -> float:
        return k * self.dt[twoB]

    # ---------------------------------------------------------------- exact targets
    def target(self, twoB: int, ref: int, k: int) -> np.ndarray:
        """Exact coarse state prod_gamma exp(-i k dt H_gamma) e_ref (dressed basis, complex128)."""
        p = self.cpath(f"target_{self.tag(twoB, ref, k)}.npy")
        if os.path.exists(p):
            return np.load(p)
        psi = apply_groups(self.mats, basis_vector(self.M.basis.dim, ref), self.theta(twoB, k))
        os.makedirs(CACHE, exist_ok=True)
        np.save(p, psi)
        return psi

    def ref_int(self, ref: int) -> int:
        return int(self.ints[ref])

    # ---------------------------------------------------------------- terms
    def support(self, name: str) -> list:
        if name == "diag":
            return list(range(self.n))
        kind, idx = ("hop", int(name[3:])) if name.startswith("hop") else ("plaq", int(name[4:]))
        return [int(q) for q in term_support(self.M, kind, idx)]

    def local(self, name: str):
        """(support, local codeword ints (sorted), h on them, {int: position})."""
        key = f"_local_{name}"
        if not hasattr(self, key):
            sup = self.support(name)
            states, h, pos = localize(self.M, self.groups[name], sup)
            setattr(self, key, (sup, [int(s) for s in states], np.asarray(h), pos))
        return getattr(self, key)

    # ---------------------------------------------------------------- baseline IR
    @cached_property
    def factory(self) -> CircuitFactory:
        return CircuitFactory(self.M, G2)

    @cached_property
    def diag_index(self) -> np.ndarray:
        """Diagonal of the diag group (dressed basis): the global phase class B drops is theta * diag[ref]."""
        return np.real(sp.csr_matrix(self.groups["diag"]).diagonal())

    def baseline_term_ir(self, name: str, theta: float) -> list:
        """The package's structured exact IR of one term (cached on disk in this study's folder)."""
        tag = f"{theta:.17g}".replace("-", "m").replace(".", "p")
        p = self.cpath(f"baseline_ir_{name}_{tag}.pkl.gz")
        if os.path.exists(p):
            with gzip.open(p, "rb") as fh:
                return pickle.load(fh)
        sup = self.support(name)
        if name.startswith("plaq"):
            gates = self.factory.plaq_gates(int(name[4:]), theta)
        else:
            gates = self.factory.hop_gates(int(name[3:]), theta)
        os.makedirs(CACHE, exist_ok=True)
        with gzip.open(p, "wb", compresslevel=1) as fh:
            pickle.dump(gates, fh)
        return gates

    def baseline_circuit(self, twoB: int, ref: int, k: int) -> list:
        """CircuitFactory(Model(lx), 4.0).coarse_step(ref, k, dt): the frozen family's IR."""
        th = self.theta(twoB, k)
        gates = self.factory.prepare(ref) + self.factory.diag_gates(th)
        for nm in self.names[1:]:
            gates += self.baseline_term_ir(nm, th)
        return gates


_PROBLEMS = {}


def get_problem(lx: int = LX) -> Problem:
    if lx not in _PROBLEMS:
        _PROBLEMS[lx] = Problem(lx)
    return _PROBLEMS[lx]


__all__ = ["Problem", "get_problem", "structured_term_gates", "G2"]

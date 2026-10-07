"""Planner prototype (2026-10-07): Pauli-string count and weight of the local Hamiltonian
term blocks in the current codec and in the dedup codec (2x2: all terms; 2x3: hopping
terms only -- the 14-qubit plaquette blocks are too large for a dense decomposition).
PLANNER ARITHMETIC, not a gate.  Output: scratch/planner/encodings_pauli_20261007.json"""
from __future__ import annotations
import json, sys, time
import numpy as np
sys.path.insert(0, "src"); sys.path.insert(0, "scratch/planner")
from skqd.codec import Codec
import skqd.reference_sim as rs
from skqd.exact import Model
from encodings_prototype_20261007 import DedupCodec

t0 = time.time()
out = {}
from qiskit.quantum_info import SparsePauliOp
for Lx in (2, 3):
    M = Model(Lx)
    terms = [(f"hop{l}", M.terms.hop[l], "hop", l) for l in range(M.lat.n_links)]
    if Lx == 2:
        terms += [(f"plaq{P}", -M.terms.plaq[P] / 8.0, "plaq", P) for P in range(len(M.lat.plaquettes))]
    out[f"2x{Lx}"] = {}
    for enc in ("current", "dedup"):
        rs.Codec = Codec if enc == "current" else DedupCodec
        codec = rs.Codec(M.basis)
        sup_of = (lambda k, i: rs.term_support(M, k, i)) if enc == "current" else codec.support
        rows = {}
        for name, O, kind, i in terms:
            sup = sup_of(kind, i)
            states, h, _ = rs.localize(M, O, sup)
            k = len(sup)
            Hd = np.zeros((2 ** k, 2 ** k), dtype=complex)
            Hd[np.ix_(states, states)] = h
            op = SparsePauliOp.from_operator(Hd).simplify(atol=1e-12)
            ws = [sum(1 for ch in p.to_label() if ch != "I") for p in op.paulis]
            rows[name] = {"support": k, "local_states": len(states), "nnz_offdiag": int((np.abs(h) > 1e-12).sum() - (np.abs(np.diag(h)) > 1e-12).sum()),
                          "pauli_terms": len(op), "max_weight": max(ws), "mean_weight": float(np.mean(ws))}
            print(f"[{time.time()-t0:6.1f}s] 2x{Lx} {enc} {name}: {rows[name]}", flush=True)
        out[f"2x{Lx}"][enc] = rows
rs.Codec = Codec
json.dump(out, open("scratch/planner/encodings_pauli_20261007.json", "w"), indent=1)

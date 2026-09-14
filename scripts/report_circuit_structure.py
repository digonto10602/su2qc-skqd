#!/usr/bin/env python3
"""
Structural analysis of the Hamiltonian terms in codeword space — the input to the
S2 compilation work (writes reports/circuit_structure.md and validation/CS.json).

For every term: the qubits it acts on, the qubit-flip patterns of its off-diagonal
elements, the size of the largest connected block (chain), the number of distinct
|matrix element| values, and, at 2x2, the exact IR gate counts of one coarse step.
"""
import os
import sys
import time

import numpy as np
import scipy.sparse.csgraph as cg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.circuits_ir import CircuitFactory, gate_counts, run_ir  # noqa: E402
from skqd.codec import Codec  # noqa: E402
from skqd.exact import Model  # noqa: E402
from skqd.krylov import references  # noqa: E402
from skqd.reference_sim import (CodewordEmbedding, apply_local, local_unitary, plaquette_pair_amplitudes,  # noqa: E402
                                term_support)
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402


def analyse(M: Model, kind: str, index: int, O):
    C = Codec(M.basis)
    cw = C.all_codewords()
    O = O.tocoo()
    flips = set()
    for r, c in zip(O.row, O.col):
        if r != c:
            flips.add(tuple(int(q) for q in np.where(cw[r] != cw[c])[0]))
    ncomp, lab = cg.connected_components(abs(O).tocsr(), directed=False)
    sizes = np.bincount(lab)
    vals = len(set(round(abs(v), 8) for v in O.data if abs(v) > 1e-12))
    deg = np.bincount(O.col, minlength=M.basis.dim)
    sup = term_support(M, kind, index)
    return dict(support=sup, n_support=len(sup), flip_patterns=len(flips), flipped_qubits=sorted(set(q for f in flips for q in f)),
                max_block=int(sizes.max()), max_degree=int(deg.max()), distinct_abs=vals, nnz=int(O.nnz))


def main():
    t0 = time.time()
    R = GateResult("CS", "Structure of the Hamiltonian terms in codeword space (input to S2)")
    rows = []
    for Lx in (2, 3):
        M = Model(Lx)
        for l in range(M.lat.n_links):
            a = analyse(M, "hop", l, M.terms.hop[l])
            rows.append([f"2x{Lx}", f"hop {l} {M.lat.links[l][:2]}", a["n_support"], a["flipped_qubits"], a["flip_patterns"], a["max_block"], a["max_degree"], a["distinct_abs"]])
            R.data[f"2x{Lx}|hop{l}"] = a
        for P in range(len(M.lat.plaquettes)):
            a = analyse(M, "plaq", P, M.terms.plaq[P])
            rows.append([f"2x{Lx}", f"plaquette {P}", a["n_support"], a["flipped_qubits"], a["flip_patterns"], a["max_block"], a["max_degree"], a["distinct_abs"]])
            R.data[f"2x{Lx}|plaq{P}"] = a
    M2 = Model(2)
    table = plaquette_pair_amplitudes(M2, 0)
    R.add("2x2 plaquette: one partner per state (pair structure)", R.data["2x2|plaq0"]["max_degree"], "= 1", R.data["2x2|plaq0"]["max_degree"] == 1)
    R.add("2x2 plaquette: distinct pair amplitudes", len(set(round(v, 8) for v in table.values())), "= 4 (-2, -1, +1, 1/2)",
          set(round(v, 8) for v in table.values()) == {-2.0, -1.0, 1.0, 0.5})
    F = CircuitFactory(M2, 4.0)
    dt = M2.reference(4.0, 0).dt
    gc = gate_counts(F.coarse_step(references(M2.basis, 0)[0], 1, dt))
    # structured plaquette gate versus the dense exponential on random physical states
    E = CodewordEmbedding(M2)
    sup = term_support(M2, "plaq", 0)
    rng = np.random.default_rng(3)
    worst = 0.0
    for theta in (dt, 2 * dt, 4 * dt):
        Ud = local_unitary(M2, -M2.terms.plaq[0] / (2 * 4.0), sup, theta)
        pg = F.plaq_gates(0, theta, True)
        for _ in range(5):
            v = rng.normal(size=M2.basis.dim) + 1j * rng.normal(size=M2.basis.dim)
            v /= np.linalg.norm(v)
            worst = max(worst, abs(run_ir(pg, E.n, E.embed(v)) - apply_local(E.embed(v), Ud, sup, E.n)).max())
    n_cx_plaq = sum(1 for g in F.plaq_gates(0, dt, True) if g[0] == "cx")
    R.add("2x2 structured plaquette gate vs dense exponential (random physical states, 3 angles)", worst, "< 1e-12", worst < 1e-12)
    R.add("2x2 structured plaquette gate: CNOT count", n_cx_plaq, "= 30 (8 parity + 6 ladder + 16 UCRz)", n_cx_plaq == 30)
    R.data["plaquette_structured_vs_dense"] = worst
    R.data["plaquette_cx"] = n_cx_plaq
    R.data["2x2_coarse_step_ir_counts"] = gc
    R.data["plaquette_pair_table"] = {str(k): v for k, v in table.items()}
    R.runtime_s = time.time() - t0
    R.save()
    prow = [[k, round(v, 6)] for k, v in sorted(table.items())]
    write_report("circuit_structure.md", f"""# Structure of the Hamiltonian terms in codeword space (input to gate S2)

Produced by `scripts/report_circuit_structure.py`; numbers stored in `validation/CS.json`.  {env_block()}

Every term of $H$ is exactly gauge invariant on the codeword subspace and acts on a small set of qubits:
the *support* (touched vertices plus, for hopping, the flux bits of the Jordan–Wigner sites in between, whose
parity is the XOR of their flux bits).  Off-diagonal elements flip a fixed small set of qubits (the *flip
patterns*), the rest of the support only controls the angle.  The largest connected block of a term is the
longest chain of configurations it connects (e.g. $|0,2\\rangle \\to |1,1\\rangle \\to |2,0\\rangle$ for a hopping link
between an empty and a doubly occupied site).

{md_table(["lattice", "term", "support qubits", "flipped qubits", "flip patterns", "largest block", "max degree", "distinct |element|"], rows)}

## The 2x2 plaquette is a pair rotation

At 2x2 every physical state has exactly one plaquette partner (all four link spins flipped = all eight flux
bits flipped); the pair amplitude $w$ is real and depends only on which corners carry one quark
(parities $p_c = q_1 \\oplus q_2$; key order $(p_{{00}}, p_{{10}}, p_{{11}}, p_{{01}})$):

{md_table(["corner parities", "w"], prow)}

so $W + W^\\dagger = D\\,X^{{\\otimes 8}}$ and $e^{{-i\\theta H_{{\\rm plaq}}}} = \\exp(+i\\tfrac{{\\theta}}{{2g^2}} D X^{{\\otimes 8}})$ is
implemented exactly by: CNOT($q_1\\to q_2$) per corner (so $q_2$ holds $p_c$), $H$ on the four $q_1$, a CNOT ladder,
one uniformly controlled $R_z(-\\theta w(p)/g^2)$ with the four parity qubits as controls (Gray-code
decomposition: 16 $R_z$ + 16 CNOT), and the inverse.  Verified in this run against the dense exponential on random
physical states at three angles: max deviation {worst:.2e}; CNOT count of the plaquette gate: {n_cx_plaq}.

## IR gate counts of one exact coarse step at 2x2

{gc}

The four hopping terms are dense local unitaries (6 or 8 qubits) in this first version; generic synthesis of an
8-qubit unitary costs $\\mathcal O(10^4)$ CX, which is why gate S2 (routed CZ $\\le 250$ per step at 2x2, $\\le 500$ at
2x3) is open.  The table above says what a structured hopping gate must do: flip at most four qubits (the flux
bit of the link at both ends and the occupation bits of both vertices), with blocks of at most three (2x2) or
four (2x3) configurations and only four flip patterns per link, i.e. a handful of controlled Givens rotations.
At 2x3 the plaquettes with interior corners have degree up to 4 (intertwiner multiplicity) and 2–4 flip
patterns — the pair trick generalizes to a uniformly controlled small unitary (S2-b).

{R.criteria_table()}
""")
    print(R.criteria_table())
    return 0


if __name__ == "__main__":
    sys.exit(main())

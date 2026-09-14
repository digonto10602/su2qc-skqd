#!/usr/bin/env python3
"""
Gate E1 — Gauss's law, the 82-dimensional kernel, sector split, and agreement of
the two independent Hamiltonian constructions at 2x2 (Step 10 of the manual:
"[G_a(x),H] = 0; 82-dim kernel; sector split; two builders agree to 1e-12").

Route A: dressed-site builder (src/skqd/hamiltonian.py).
Route B: redundant-basis construction in the 160 000-dimensional product space
         (src/skqd/fullspace.py): operators U, L, R, psi with explicit JW strings;
         kernel of sum G_a(x)^2 by block diagonalization.

Runtime: ~2 minutes on 2 CPUs (dominated by the 4096-dimensional blocks of the
kernel computation).
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.basis import enumerate_basis, count_labels_without_intertwiner  # noqa: E402
from skqd.fullspace import FullSpace  # noqa: E402
from skqd.hamiltonian import HamiltonianBuilder  # noqa: E402
from skqd.lattice import Ladder  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.su2 import LinkSpace, SIGMA  # noqa: E402

MANUAL = {  # Table 1 of the manual, 2x2, g^2 = 4, m = 0.75 (4 decimals as printed)
    "B0_E0": -3.6408, "B0_E1": -0.9622, "B0_piW": 0.245,
    "B1_E0": -1.8616, "B1_E1": -1.8197, "B1_E2": 0.2082, "B1_piW": 0.332,
}


def main():
    t0 = time.time()
    R = GateResult("E1", "Gauss's law, kernel dimension, sector split, two-builder agreement (2x2)")
    g2, m = 4.0, 0.75

    # --- link-operator conventions -------------------------------------------------
    T = [s / 2 for s in SIGMA]
    conv_err = 0.0
    for jmax in (0.5, 1.0):
        L = LinkSpace(jmax)
        U = L.U()
        Lg, Rg = L.generators()
        for a in range(3):
            for i in range(2):
                for j in range(2):
                    lhs = Lg[a] @ U[i][j] - U[i][j] @ Lg[a]
                    rhs = -sum(T[a][i, k] * U[k][j] for k in range(2))
                    conv_err = max(conv_err, abs(lhs - rhs).max())
                    lhs = Rg[a] @ U[i][j] - U[i][j] @ Rg[a]
                    rhs = sum(U[i][k] * T[a][k, j] for k in range(2))
                    conv_err = max(conv_err, abs(lhs - rhs).max())
    R.add("link covariance [L_a,U]=-(T_a U), [R_a,U]=+(U T_a), jmax=1/2 and 1", conv_err, "< 1e-12", conv_err < 1e-12)

    # --- route A ---------------------------------------------------------------------
    lat = Ladder(2)
    basis = enumerate_basis(lat)
    hb = HamiltonianBuilder(basis)
    terms = hb.build()
    Hd = terms.H(g2, m).toarray()
    herm = abs(Hd - Hd.conj().T).max()
    R.add("dressed-site H Hermitian", herm, "< 1e-12", herm < 1e-12)
    R.add("dressed-site basis dimension", basis.dim, "= 82", basis.dim == 82)
    secs = basis.sector_dims()
    R.add("sector split {2B: dim}", str(secs), "= {-4:2,-2:20,0:38,2:20,4:2}",
          secs == {-4: 2, -2: 20, 0: 38, 2: 20, 4: 2})
    R.add("distinct ({j},{n}) labels", count_labels_without_intertwiner(basis), "= 82 (no intertwiner multiplicity at 2x2)",
          count_labels_without_intertwiner(basis) == 82)

    # --- route B ---------------------------------------------------------------------
    fs = FullSpace(lat)
    H = fs.hamiltonian(g2, m)
    R.add("redundant-basis dimension", fs.dim, "= 160000", fs.dim == 160000)
    hermB = abs(H - H.conj().T).max()
    R.add("redundant-basis H Hermitian", hermB, "< 1e-12", hermB < 1e-12)
    comm = 0.0
    for x in range(4):
        for a in range(3):
            G = fs.gauss(x, a)
            C = G @ H - H @ G
            comm = max(comm, abs(C).max() if C.nnz else 0.0)
    R.add("max |[G_a(x), H]| over x, a", comm, "< 1e-12", comm < 1e-12)
    tk = time.time()
    P, twoB = fs.physical_kernel()
    t_kernel = time.time() - tk
    R.add("kernel dimension of sum G_a(x)^2 (block diagonalization)", P.shape[1], "= 82", P.shape[1] == 82)
    secB = {int(k): int(v) for k, v in zip(*np.unique(twoB, return_counts=True))}
    R.add("kernel sector split", str(secB), "= {-4:2,-2:20,0:38,2:20,4:2}", secB == {-4: 2, -2: 20, 0: 38, 2: 20, 4: 2})
    orth = abs(P.conj().T @ P - np.eye(P.shape[1])).max()
    R.add("kernel basis orthonormal", orth, "< 1e-12", orth < 1e-12)
    gP = max(abs(fs.gauss(x, a) @ P).max() for x in range(4) for a in range(3))
    R.add("max |G_a(x) P|", gP, "< 1e-12", gP < 1e-12)
    Hp = P.conj().T @ (H @ P)
    wp = np.linalg.eigvalsh((Hp + Hp.conj().T) / 2)
    wd = np.linalg.eigvalsh(Hd)
    eig_diff = abs(np.sort(wp) - np.sort(wd)).max()
    R.add("max |eig(P^dag H P) - eig(H_dressed)| (all 82 levels)", eig_diff, "< 1e-12", eig_diff < 1e-12)

    # --- dressed-site states embedded in the redundant space ----------------------------
    D = fs.embed_dressed(basis, hb)
    orthD = abs(D.conj().T @ D - np.eye(basis.dim)).max()
    R.add("embedded dressed states orthonormal", orthD, "< 1e-12", orthD < 1e-12)
    gD = max(abs(fs.gauss(x, a) @ D).max() for x in range(4) for a in range(3))
    R.add("max |G_a(x) |b>| for embedded dressed states", gD, "< 1e-12", gD < 1e-12)
    elem = abs(D.conj().T @ (H @ D) - Hd).max()
    R.add("element-wise |<b'|H_full|b> - H_dressed[b',b]|", elem, "< 1e-12", elem < 1e-12)

    # --- comparison with the manual's Table 1 ----------------------------------------------
    rows = []
    vals = {}
    for twoB_, tag in ((0, "B0"), (2, "B1")):
        idx = basis.sector(twoB_)
        w = np.linalg.eigvalsh(Hd[np.ix_(idx, idx)])
        vals[tag] = w
        piW = np.pi / (w[-1] - w[0])
        rows.append([f"B = {twoB_ // 2}", len(idx), f"{w[0]:.4f}", ", ".join(f"{e:.4f}" for e in w[1:4]), f"{piW:.3f}"])
        R.add(f"2x2 {tag} E0 vs manual {MANUAL[tag + '_E0']}", round(float(w[0]), 4), "|diff| <= 5e-5",
              abs(w[0] - MANUAL[tag + "_E0"]) <= 5e-5)
        R.add(f"2x2 {tag} E1 vs manual {MANUAL[tag + '_E1']}", round(float(w[1]), 4), "|diff| <= 5e-5",
              abs(w[1] - MANUAL[tag + "_E1"]) <= 5e-5)
        R.add(f"2x2 {tag} pi/W vs manual {MANUAL[tag + '_piW']}", round(float(piW), 3), "|diff| <= 5e-4",
              abs(piW - MANUAL[tag + "_piW"]) <= 5e-4)
    R.add("2x2 B1 E2 vs manual 0.2082", round(float(vals["B1"][2]), 4), "|diff| <= 5e-5",
          abs(vals["B1"][2] - MANUAL["B1_E2"]) <= 5e-5)
    R.data = {
        "g2": g2, "m": m, "spectrum_B0": vals["B0"], "spectrum_B1": vals["B1"], "kernel_time_s": t_kernel,
        "full_space_nnz_H": int(H.nnz),
    }
    R.runtime_s = time.time() - t0
    path = R.save()

    report = f"""# Gate E1 — Gauss's law, kernel, sector split, two-builder agreement (2x2)

**Status: {'PASS' if R.passed else 'FAIL'}** — produced by `scripts/gate_E1.py`; every number below was computed in this run
and is stored in `validation/E1.json`.  {env_block()}  Runtime {R.runtime_s:.0f} s.

## What was checked

The 2x2 open patch (one plaquette: 4 sites, 4 links, 12 qubits) at $g^2 = {g2}$, $m = {m}$, links truncated at
$j_{{\\max}} = \\tfrac12$.  Two independent constructions of the Hamiltonian of eq. (1) of the manual:

* **Route A (dressed-site builder, `skqd.hamiltonian`)**: local singlet tensors of every vertex (kernel of
  $\\sum_a G_a(x)^2$ with the fusion-tree intertwiner label), basis $|b\\rangle = |\\{{j_\\ell\\}},\\{{n_x\\}},\\{{\\iota_x\\}}\\rangle$,
  matrix elements by local contraction with the Jordan–Wigner sign
  $s_{{JW}} = \\prod_{{x<z<y}}(-1)^{{n_z}}$.
* **Route B (redundant basis, `skqd.fullspace`)**: the full product space of four 5-state links and four 4-state
  sites ($5^4\\cdot 4^4 = 160\\,000$ states); $U_{{ij}}$, $L_a$, $R_a$, $\\psi_{{x,i}}$ (with explicit JW strings),
  $Q_a = \\psi^\\dagger \\tfrac{{\\sigma_a}}{{2}} \\psi$ built directly; Gauss generators
  $G_a(x) = \\sum_{{\\text{{out}}}} L_a + \\sum_{{\\text{{in}}}} R_a + Q_a(x)$; the physical space is the kernel of
  $\\sum_{{x,a}} G_a(x)^2$ computed block by block (blocks of fixed link spins and site occupations) by dense
  diagonalization.

Here $g^2$ is the gauge coupling, $m$ the staggered mass, $j_\\ell$ the spin on link $\\ell$, $n_x$ the quark
occupation of site $x$, $\\iota_x$ the intertwiner label, $L_a/R_a$ the left/right electric generators and
$Q_a$ the matter colour charge.

The link-operator conventions are fixed by the exact relations
$[L_a, U_{{ij}}] = -(T_a U)_{{ij}}$, $[R_a, U_{{ij}}] = +(U T_a)_{{ij}}$, $T_a = \\sigma_a/2$, which hold in the
truncated space for every $j_{{\\max}}$ (checked at $j_{{\\max}} = \\tfrac12, 1$).

## Results

{R.criteria_table()}

## 2x2 spectrum (route A = route B to {eig_diff:.1e}) versus Table 1 of the manual

{md_table(["sector", "dim", "E0", "next levels", "pi/W"], rows)}

Manual (Table 1): $B=0$: $E_0 = -3.6408$, next $-0.9622$, $\\pi/W = 0.245$; $B=1$: $E_0 = -1.8616$, next
$-1.8197, 0.2082$, $\\pi/W = 0.332$.  All reproduced to the printed precision.

## Interpretation

* $[G_a(x), H] = 0$ to machine precision confirms that the truncated $U$, the generators and the matter charge
  form a consistent gauge-covariant set (the truncation keeps whole $j$ multiplets, so covariance survives
  exactly).
* The block-diagonalization kernel has dimension 82 with sectors 2/20/38/20/2, and the embedded dressed-site
  states are annihilated by every $G_a(x)$ and reproduce the builder's matrix elements **element by element**
  (not only the spectrum), which validates the contraction formula, the JW signs and the hopping phases.
* Route A builds the 2x2 Hamiltonian in well under a second; route B needs {t_kernel:.0f} s for the kernel and is
  used only as the independent check.

## Reproduce

```
python scripts/gate_E1.py        # writes validation/E1.json and this report
```
"""
    write_report("E1_gauss_law_two_builders.md", report)
    print(R.criteria_table())
    print("STATUS", "PASS" if R.passed else "FAIL", "->", path)
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())

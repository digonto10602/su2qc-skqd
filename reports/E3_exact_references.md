# Gate E3 — exact references, static sectors, derived quantities, Krylov step

**Status: PASS** — produced by `scripts/gate_E3.py`; all numbers computed in this run, stored in
`validation/E3.json` and `data/references.json`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 57b3bff, 2026-09-14 16:44:36 MDT.  Runtime 36 s.

Parameters: $m = 3g^2/16$ (the manual's line), $j_{\max} = \tfrac12$.  Dense diagonalization for sectors up to
4 000 states, Lanczos (`scipy.sparse.linalg.eigsh`) above.  $W = E_{\max} - E_{\min}$ is the spectral width of the
sector block and $\Delta t = \pi/W$ the anti-aliasing Krylov step; the support $S_\epsilon$ is the smallest set of
configurations carrying $1-\epsilon$ of the ground-state weight; $\mathrm{PR} = 1/\sum_b |\langle b|\Omega\rangle|^4$
is the participation ratio.  Builder times: 2x2 0.2 s, 2x3 1.5 s, 2x4 10.0 s, 2x3+static(0, 2) 3.0 s, 2x3+static(0, 4) 1.9 s
(the manual quotes 22 s for 2x3 and 17 min for 2x4 in plain numpy; this builder caches matrix elements by local
signature).

## Table 1 reproduced

| lattice | g² | B | dim | E0 | next levels | π/W | support 99% / 99.9% | PR | manual E0 | manual next | manual π/W | manual support | manual PR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2x2 | 4.0 | 0 | 38 | -3.6408 | -0.9622 | 0.245 | 9 / 16 | 1.5 | -3.6408 | -0.9622 | 0.245 | 9 / 16 | 1.5 |
| 2x2 | 4.0 | 1 | 20 | -1.8616 | -1.8197, 0.2082 | 0.332 | 8 / 13 | 2.6 | -1.8616 | -1.8197, 0.2082 | 0.332 | 8 / 13 | 2.6 |
| 2x3 | 4.0 | 0 | 677 | -5.6026 | -2.8886, -2.8652 | 0.156 | 31 / 86 | 1.9 | -5.6026 | -2.8886, -2.8652 | 0.156 | 31 / 86 | 1.9 |
| 2x3 | 4.0 | 1 | 426 | -3.8261 | -3.8017, -3.6687, -1.6529 | 0.187 | 42 / 95 | 3.6 | -3.8261 | -3.8017, -3.6687, -1.6529 | 0.187 | 42 / 95 | 3.6 |
| 2x3 | 4.0 | 2 | 95 | -2.0118 | -1.8622, -1.8439 | 0.234 | 15 / 22 | 1.5 | -2.0118 | -1.8622, -1.8439 | 0.234 | 15 / 22 | 1.5 |
| 2x3 | 2.0 | 0 | 677 | -4.2216 | -2.7236, -2.7032 | 0.257 | 137 / 326 | 5.9 | -4.2216 | -2.7236, -2.7032 | 0.257 | 137 / 326 | 5.9 |
| 2x3 | 2.0 | 1 | 426 | -3.0866 | -2.9730, -2.7940 | 0.305 | 135 / 240 | 11.9 | -3.0866 | -2.9730, -2.7940 | 0.305 | 136 / 243 | 11.9 |
| 2x3 | 1.0 | 0 | 677 | -4.3918 | -3.4201 | 0.303 | 396 / 549 | 33.8 | -4.3918 | -3.4201 | 0.303 | 396 / 549 | 33.8 |
| 2x4 | 4.0 | 0 | 12843 | -7.5652 | -4.8436, -4.8375 | 0.115 | 76 / 305 | 2.5 | -7.5652 | -4.8436, -4.8375 | 0.115 | 76 / 305 | 2.5 |
| 2x4 | 4.0 | 1 | 8934 | -5.7802 | -5.7741, -5.6541 | 0.130 | 127 / 470 | 4.8 | -5.7802 | -5.7741, -5.6541 | — | 127 / 470 | 4.8 |

## Derived quantities

| lattice | g² | Δ0 | M_B | E(B=2)−E(B=0)−2M_B | V(1) | V(2) | manual |
|---|---|---|---|---|---|---|---|
| 2x3 | 4.0 | 2.7140 | 1.7765 | 0.0377 | 1.3872 | 2.5898 | D0=2.714, MB=1.7765, binding=0.038, V1=1.3872, V2=2.5898 |
| 2x3 | 2.0 | 1.4980 | 1.1350 | 0.1748 | 0.7820 | 1.3740 | D0=1.498, MB=1.135, V1=0.782, V2=1.374 |
| 2x4 | 4.0 | 2.7216 | 1.7851 | — | — | — | D0=2.7216, MB=1.7851 |
| 2x4 | 2.0 | 1.5028 | 1.1560 | — | — | — | MB=1.156 |

$\Delta_0 = E_1^{B=0} - E_0^{B=0}$ (meson-like gap), $M_B = E_0^{B=1} - E_0^{B=0}$ (baryon mass),
$V(r) = E_0^{\text{static pair at distance } r, B=0} - E_0^{B=0}$ (static potential, charges on the bottom row).
The static sectors have 2729 ($r=1$, $B=0$: 1089) and 2418 ($r=2$, $B=0$: 978) states (computed here).

## $B = 1$ near-degenerate clusters (Step 1.5)

| lattice | lowest splittings at g²=4 | manual |
|---|---|---|
| 2x2 | 0.042 | 0.042 |
| 2x3 | 0.024, 0.133 | 0.024, 0.13 |
| 2x4 | 0.006, 0.120 | 0.006, 0.12 |

The diquark can sit on any even site, so the lowest $B=1$ levels form a cluster of $L_x$ states; the baryon mass is
defined from the lowest level with the cluster reported, and certification treats the cluster as a whole.

## Truncation check at 2x2 ($j_{\max} = \tfrac12 \to 1$, error budget of Step 10)

| g² | states (j_max=1/2) | E0 (j_max=1/2) | states (j_max=1) | E0 (j_max=1) | shift |
|---|---|---|---|---|---|
| 4.0 | 38 | -3.6408 | 74 | -3.6427 | -0.0019 |
| 2.0 | 38 | -2.6712 | 74 | -2.7097 | -0.0385 |
| 1.0 | 38 | -2.7175 | 74 | -3.0586 | -0.3411 |

With $j_{\max} = 1$ the one-plaquette model has 152 states (manual: 82 → 152).  The ground-state shift is the
truncation entry of the error budget at 2x2; it is computed exactly here and is not a gate criterion.

## All checks

| check | value | criterion | result |
|---|---|---|---|
| 2x2|g2=4.0|2B=0: dim | 38 | = 38 | PASS |
| 2x2|g2=4.0|2B=0: E0 | -3.6408 | manual -3.6408 (|diff| <= 5e-5) | PASS |
| 2x2|g2=4.0|2B=0: level 1 | -0.9622 | manual -0.9622 (|diff| <= 5e-5) | PASS |
| 2x2|g2=4.0|2B=0: pi/W | 0.245 | manual 0.245 (|diff| <= 5e-4) | PASS |
| 2x2|g2=4.0|2B=0: support 99%/99.9% | 9/16 | manual 9/16 (each within 3) | PASS |
| 2x2|g2=4.0|2B=0: participation ratio | 1.5 | manual 1.5 (|diff| <= 0.1) | PASS |
| 2x2|g2=4.0|2B=2: dim | 20 | = 20 | PASS |
| 2x2|g2=4.0|2B=2: E0 | -1.8616 | manual -1.8616 (|diff| <= 5e-5) | PASS |
| 2x2|g2=4.0|2B=2: level 1 | -1.8197 | manual -1.8197 (|diff| <= 5e-5) | PASS |
| 2x2|g2=4.0|2B=2: level 2 | 0.2082 | manual 0.2082 (|diff| <= 5e-5) | PASS |
| 2x2|g2=4.0|2B=2: pi/W | 0.332 | manual 0.332 (|diff| <= 5e-4) | PASS |
| 2x2|g2=4.0|2B=2: support 99%/99.9% | 8/13 | manual 8/13 (each within 3) | PASS |
| 2x2|g2=4.0|2B=2: participation ratio | 2.6 | manual 2.6 (|diff| <= 0.1) | PASS |
| 2x3|g2=4.0|2B=0: dim | 677 | = 677 | PASS |
| 2x3|g2=4.0|2B=0: E0 | -5.6026 | manual -5.6026 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=0: level 1 | -2.8886 | manual -2.8886 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=0: level 2 | -2.8652 | manual -2.8652 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=0: pi/W | 0.156 | manual 0.156 (|diff| <= 5e-4) | PASS |
| 2x3|g2=4.0|2B=0: support 99%/99.9% | 31/86 | manual 31/86 (each within 3) | PASS |
| 2x3|g2=4.0|2B=0: participation ratio | 1.9 | manual 1.9 (|diff| <= 0.1) | PASS |
| 2x3|g2=4.0|2B=2: dim | 426 | = 426 | PASS |
| 2x3|g2=4.0|2B=2: E0 | -3.8261 | manual -3.8261 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=2: level 1 | -3.8017 | manual -3.8017 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=2: level 2 | -3.6687 | manual -3.6687 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=2: level 3 | -1.6529 | manual -1.6529 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=2: pi/W | 0.187 | manual 0.187 (|diff| <= 5e-4) | PASS |
| 2x3|g2=4.0|2B=2: support 99%/99.9% | 42/95 | manual 42/95 (each within 3) | PASS |
| 2x3|g2=4.0|2B=2: participation ratio | 3.6 | manual 3.6 (|diff| <= 0.1) | PASS |
| 2x3|g2=4.0|2B=4: dim | 95 | = 95 | PASS |
| 2x3|g2=4.0|2B=4: E0 | -2.0118 | manual -2.0118 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=4: level 1 | -1.8622 | manual -1.8622 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=4: level 2 | -1.8439 | manual -1.8439 (|diff| <= 5e-5) | PASS |
| 2x3|g2=4.0|2B=4: pi/W | 0.234 | manual 0.234 (|diff| <= 5e-4) | PASS |
| 2x3|g2=4.0|2B=4: support 99%/99.9% | 15/22 | manual 15/22 (each within 3) | PASS |
| 2x3|g2=4.0|2B=4: participation ratio | 1.5 | manual 1.5 (|diff| <= 0.1) | PASS |
| 2x3|g2=2.0|2B=0: dim | 677 | = 677 | PASS |
| 2x3|g2=2.0|2B=0: E0 | -4.2216 | manual -4.2216 (|diff| <= 5e-5) | PASS |
| 2x3|g2=2.0|2B=0: level 1 | -2.7236 | manual -2.7236 (|diff| <= 5e-5) | PASS |
| 2x3|g2=2.0|2B=0: level 2 | -2.7032 | manual -2.7032 (|diff| <= 5e-5) | PASS |
| 2x3|g2=2.0|2B=0: pi/W | 0.257 | manual 0.257 (|diff| <= 5e-4) | PASS |
| 2x3|g2=2.0|2B=0: support 99%/99.9% | 137/326 | manual 137/326 (each within 3) | PASS |
| 2x3|g2=2.0|2B=0: participation ratio | 5.9 | manual 5.9 (|diff| <= 0.1) | PASS |
| 2x3|g2=2.0|2B=2: dim | 426 | = 426 | PASS |
| 2x3|g2=2.0|2B=2: E0 | -3.0866 | manual -3.0866 (|diff| <= 5e-5) | PASS |
| 2x3|g2=2.0|2B=2: level 1 | -2.973 | manual -2.973 (|diff| <= 5e-5) | PASS |
| 2x3|g2=2.0|2B=2: level 2 | -2.794 | manual -2.794 (|diff| <= 5e-5) | PASS |
| 2x3|g2=2.0|2B=2: pi/W | 0.305 | manual 0.305 (|diff| <= 5e-4) | PASS |
| 2x3|g2=2.0|2B=2: support 99%/99.9% | 135/240 | manual 136/243 (each within 3) | PASS |
| 2x3|g2=2.0|2B=2: participation ratio | 11.9 | manual 11.9 (|diff| <= 0.1) | PASS |
| 2x3|g2=1.0|2B=0: dim | 677 | = 677 | PASS |
| 2x3|g2=1.0|2B=0: E0 | -4.3918 | manual -4.3918 (|diff| <= 5e-5) | PASS |
| 2x3|g2=1.0|2B=0: level 1 | -3.4201 | manual -3.4201 (|diff| <= 5e-5) | PASS |
| 2x3|g2=1.0|2B=0: pi/W | 0.303 | manual 0.303 (|diff| <= 5e-4) | PASS |
| 2x3|g2=1.0|2B=0: support 99%/99.9% | 396/549 | manual 396/549 (each within 3) | PASS |
| 2x3|g2=1.0|2B=0: participation ratio | 33.8 | manual 33.8 (|diff| <= 0.1) | PASS |
| 2x4|g2=4.0|2B=0: dim | 12843 | = 12843 | PASS |
| 2x4|g2=4.0|2B=0: E0 | -7.5652 | manual -7.5652 (|diff| <= 5e-5) | PASS |
| 2x4|g2=4.0|2B=0: level 1 | -4.8436 | manual -4.8436 (|diff| <= 5e-5) | PASS |
| 2x4|g2=4.0|2B=0: level 2 | -4.8375 | manual -4.8375 (|diff| <= 5e-5) | PASS |
| 2x4|g2=4.0|2B=0: pi/W | 0.115 | manual 0.115 (|diff| <= 5e-4) | PASS |
| 2x4|g2=4.0|2B=0: support 99%/99.9% | 76/305 | manual 76/305 (each within 3) | PASS |
| 2x4|g2=4.0|2B=0: participation ratio | 2.5 | manual 2.5 (|diff| <= 0.1) | PASS |
| 2x4|g2=4.0|2B=2: dim | 8934 | = 8934 | PASS |
| 2x4|g2=4.0|2B=2: E0 | -5.7802 | manual -5.7802 (|diff| <= 5e-5) | PASS |
| 2x4|g2=4.0|2B=2: level 1 | -5.7741 | manual -5.7741 (|diff| <= 5e-5) | PASS |
| 2x4|g2=4.0|2B=2: level 2 | -5.6541 | manual -5.6541 (|diff| <= 5e-5) | PASS |
| 2x4|g2=4.0|2B=2: support 99%/99.9% | 127/470 | manual 127/470 (each within 3) | PASS |
| 2x4|g2=4.0|2B=2: participation ratio | 4.8 | manual 4.8 (|diff| <= 0.1) | PASS |
| 2x3 g2=4.0: D0 | 2.714 | manual 2.714 (|diff| <= 0.0002) | PASS |
| 2x3 g2=4.0: MB | 1.7765 | manual 1.7765 (|diff| <= 0.0002) | PASS |
| 2x3 g2=4.0: binding | 0.0377 | manual 0.038 (|diff| <= 0.002) | PASS |
| 2x3 g2=4.0: V1 | 1.3872 | manual 1.3872 (|diff| <= 0.0002) | PASS |
| 2x3 g2=4.0: V2 | 2.5898 | manual 2.5898 (|diff| <= 0.0002) | PASS |
| 2x3 g2=2.0: D0 | 1.498 | manual 1.498 (|diff| <= 0.0002) | PASS |
| 2x3 g2=2.0: MB | 1.135 | manual 1.135 (|diff| <= 0.0002) | PASS |
| 2x3 g2=2.0: V1 | 0.782 | manual 0.782 (|diff| <= 0.0002) | PASS |
| 2x3 g2=2.0: V2 | 1.374 | manual 1.374 (|diff| <= 0.0002) | PASS |
| 2x4 g2=4.0: D0 | 2.7216 | manual 2.7216 (|diff| <= 0.0002) | PASS |
| 2x4 g2=4.0: MB | 1.7851 | manual 1.7851 (|diff| <= 0.0002) | PASS |
| 2x4 g2=2.0: MB | 1.156 | manual 1.156 (|diff| <= 0.0002) | PASS |
| 2x3 static sectors: states (r=1, r=1 B=0, r=2, r=2 B=0) | {'r1': 2729, 'r1_B0': 1089, 'r2': 2418, 'r2_B0': 978} | = 2729, 1089, 2418, 978 | PASS |
| 2x2 B=1 cluster splittings (g2=4) | 0.042 | manual [0.042] (within 0.006) | PASS |
| 2x3 B=1 cluster splittings (g2=4) | 0.024, 0.133 | manual [0.024, 0.13] (within 0.006) | PASS |
| 2x4 B=1 cluster splittings (g2=4) | 0.006, 0.120 | manual [0.006, 0.12] (within 0.006) | PASS |
| 2x2 with j_max = 1: states | 152 | = 152 | PASS |

## Reproduce

```
python scripts/gate_E3.py     # ~1-2 min
```

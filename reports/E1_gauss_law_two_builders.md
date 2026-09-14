# Gate E1 — Gauss's law, kernel, sector split, two-builder agreement (2x2)

**Status: PASS** — produced by `scripts/gate_E1.py`; every number below was computed in this run
and is stored in `validation/E1.json`.  Environment: Python 3.11.15, numpy 2.4.4, scipy 1.17.1, Linux-6.18.44-fc-v24-x86_64-with-glibc2.39, 2 CPUs, commit 5e3fe61, 2026-09-14 20:40:08 UTC.  Runtime 104 s.

## What was checked

The 2x2 open patch (one plaquette: 4 sites, 4 links, 12 qubits) at $g^2 = 4.0$, $m = 0.75$, links truncated at
$j_{\max} = \tfrac12$.  Two independent constructions of the Hamiltonian of eq. (1) of the manual:

* **Route A (dressed-site builder, `skqd.hamiltonian`)**: local singlet tensors of every vertex (kernel of
  $\sum_a G_a(x)^2$ with the fusion-tree intertwiner label), basis $|b\rangle = |\{j_\ell\},\{n_x\},\{\iota_x\}\rangle$,
  matrix elements by local contraction with the Jordan–Wigner sign
  $s_{JW} = \prod_{x<z<y}(-1)^{n_z}$.
* **Route B (redundant basis, `skqd.fullspace`)**: the full product space of four 5-state links and four 4-state
  sites ($5^4\cdot 4^4 = 160\,000$ states); $U_{ij}$, $L_a$, $R_a$, $\psi_{x,i}$ (with explicit JW strings),
  $Q_a = \psi^\dagger \tfrac{\sigma_a}{2} \psi$ built directly; Gauss generators
  $G_a(x) = \sum_{\text{out}} L_a + \sum_{\text{in}} R_a + Q_a(x)$; the physical space is the kernel of
  $\sum_{x,a} G_a(x)^2$ computed block by block (blocks of fixed link spins and site occupations) by dense
  diagonalization.

Here $g^2$ is the gauge coupling, $m$ the staggered mass, $j_\ell$ the spin on link $\ell$, $n_x$ the quark
occupation of site $x$, $\iota_x$ the intertwiner label, $L_a/R_a$ the left/right electric generators and
$Q_a$ the matter colour charge.

The link-operator conventions are fixed by the exact relations
$[L_a, U_{ij}] = -(T_a U)_{ij}$, $[R_a, U_{ij}] = +(U T_a)_{ij}$, $T_a = \sigma_a/2$, which hold in the
truncated space for every $j_{\max}$ (checked at $j_{\max} = \tfrac12, 1$).

## Results

| check | value | criterion | result |
|---|---|---|---|
| link covariance [L_a,U]=-(T_a U), [R_a,U]=+(U T_a), jmax=1/2 and 1 | 1.110e-16 | < 1e-12 | PASS |
| dressed-site H Hermitian | 0 | < 1e-12 | PASS |
| dressed-site basis dimension | 82 | = 82 | PASS |
| sector split {2B: dim} | {-4: 2, -2: 20, 0: 38, 2: 20, 4: 2} | = {-4:2,-2:20,0:38,2:20,4:2} | PASS |
| distinct ({j},{n}) labels | 82 | = 82 (no intertwiner multiplicity at 2x2) | PASS |
| redundant-basis dimension | 160000 | = 160000 | PASS |
| redundant-basis H Hermitian | 0 | < 1e-12 | PASS |
| max |[G_a(x), H]| over x, a | 0 | < 1e-12 | PASS |
| kernel dimension of sum G_a(x)^2 (block diagonalization) | 82 | = 82 | PASS |
| kernel sector split | {-4: 2, -2: 20, 0: 38, 2: 20, 4: 2} | = {-4:2,-2:20,0:38,2:20,4:2} | PASS |
| kernel basis orthonormal | 1.110e-15 | < 1e-12 | PASS |
| max |G_a(x) P| | 4.458e-16 | < 1e-12 | PASS |
| max |eig(P^dag H P) - eig(H_dressed)| (all 82 levels) | 2.132e-14 | < 1e-12 | PASS |
| embedded dressed states orthonormal | 4.441e-16 | < 1e-12 | PASS |
| max |G_a(x) |b>| for embedded dressed states | 0 | < 1e-12 | PASS |
| element-wise |<b'|H_full|b> - H_dressed[b',b]| | 3.553e-15 | < 1e-12 | PASS |
| 2x2 B0 E0 vs manual -3.6408 | -3.6408 | |diff| <= 5e-5 | PASS |
| 2x2 B0 E1 vs manual -0.9622 | -0.9622 | |diff| <= 5e-5 | PASS |
| 2x2 B0 pi/W vs manual 0.245 | 0.245 | |diff| <= 5e-4 | PASS |
| 2x2 B1 E0 vs manual -1.8616 | -1.8616 | |diff| <= 5e-5 | PASS |
| 2x2 B1 E1 vs manual -1.8197 | -1.8197 | |diff| <= 5e-5 | PASS |
| 2x2 B1 pi/W vs manual 0.332 | 0.332 | |diff| <= 5e-4 | PASS |
| 2x2 B1 E2 vs manual 0.2082 | 0.2082 | |diff| <= 5e-5 | PASS |

## 2x2 spectrum (route A = route B to 2.1e-14) versus Table 1 of the manual

| sector | dim | E0 | next levels | pi/W |
|---|---|---|---|---|
| B = 0 | 38 | -3.6408 | -0.9622, -0.8506, -0.8506 | 0.245 |
| B = 1 | 20 | -1.8616 | -1.8197, 0.2082, 0.4506 | 0.332 |

Manual (Table 1): $B=0$: $E_0 = -3.6408$, next $-0.9622$, $\pi/W = 0.245$; $B=1$: $E_0 = -1.8616$, next
$-1.8197, 0.2082$, $\pi/W = 0.332$.  All reproduced to the printed precision.

## Interpretation

* $[G_a(x), H] = 0$ to machine precision confirms that the truncated $U$, the generators and the matter charge
  form a consistent gauge-covariant set (the truncation keeps whole $j$ multiplets, so covariance survives
  exactly).
* The block-diagonalization kernel has dimension 82 with sectors 2/20/38/20/2, and the embedded dressed-site
  states are annihilated by every $G_a(x)$ and reproduce the builder's matrix elements **element by element**
  (not only the spectrum), which validates the contraction formula, the JW signs and the hopping phases.
* Route A builds the 2x2 Hamiltonian in well under a second; route B needs 95 s for the kernel and is
  used only as the independent check.

## Reproduce

```
python scripts/gate_E1.py        # writes validation/E1.json and this report
```

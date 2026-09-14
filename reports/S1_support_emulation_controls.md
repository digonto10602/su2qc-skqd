# Gate S1 — emulated support generation, certification and classical controls

**Status: PASS** — produced by `scripts/gate_S1.py` (means over 3 repetitions); every number computed in this
run, stored in `validation/S1.json` and `data/S1_emulation.json`.  Environment: Python 3.11.15, numpy 2.4.4, scipy 1.17.1, Linux-6.18.44-fc-v24-x86_64-with-glibc2.39, 2 CPUs, commit 1a578c9, 2026-09-14 20:47:01 UTC.  Runtime 86 s.

Setting: 2x3 ladder (20 qubits, 1 727 states; sectors $B=0$: 677, $B=1$: 426), $g^2 = 4$, $m = 0.75$,
$\Delta t = \pi/W_B$ per sector (0.156 for $B=0$, 0.187 for $B=1$).
Device proxy (Step 8.2): a shot is clean with probability $f$; otherwise with equal probability a uniformly random
bit string or the clean sample with Poisson(2) bit flips (conditioned on at least one flip); independent readout flips at
$p_{ro} = 1\%$ per qubit on every shot; then the decoder with the sector filter.  $B$ is the union of the accepted
configurations and the references.  Symbols: $E_R$ = lowest Ritz value on $B$, $E_0$ = exact sector ground energy,
recall = fraction of the exact 99.9 % support $S_{10^{-3}}$ contained in $B$, fp = configurations of $B$ with exact
weight $< 10^{-8}$, yield = accepted shots / total shots, $r_H = \|(H - E_R)\psi_R\|$.

## 1. Which configurations the circuits can reach (no sampling)

Configurations of the 99.9 % support that reach probability $> 10^{-3}$ in at least one circuit state:

| sector | circuit family | circuits | reached |
|---|---|---|---|
| B=0 | single ref, 5 exact Krylov | 5 | 41 of 86 |
| B=0 | single ref, 5 first-order Trotter | 5 | 41 of 86 |
| B=0 | single ref, coarse k=1..4 | 5 | 61 of 86 |
| B=0 | all refs, coarse k=1..4 | 40 | 86 of 86 |
| B=0 | all refs, 5 exact Krylov | 40 | 86 of 86 |
| B=1 | single ref, 5 exact Krylov | 5 | 35 of 95 |
| B=1 | single ref, 5 first-order Trotter | 5 | 35 of 95 |
| B=1 | single ref, coarse k=1..4 | 5 | 34 of 95 |
| B=1 | all refs, coarse k=1..4 | 15 | 89 of 95 |
| B=1 | all refs, 5 exact Krylov | 15 | 76 of 95 |

Manual (Step 4.2–4.3): single reference with $d=5$ exact Krylov states reaches 41 of 86 ($B=0$) and 35 of 95 ($B=1$);
single-reference coarse steps reach 62 of 86; multi-reference coarse circuits reach 86 of 86 and 94 of 95.
The coarse single-step family and the multi-reference set are therefore the production choice, as in the manual.

## 2. Device-proxy emulation, single reference, five exact Krylov states, $B = 0$ (Table 4 analogue)

Entries: Ritz error / $|B|$ / recall / false positives (yield in parentheses).

| f | 10³ shots per circuit | 10⁴ shots per circuit | 3·10⁴ shots per circuit |
|---|---|---|---|
| 1.0 | 1.6e-02 / 76 / 0.68 / 0 (y=0.819) | 1.9e-03 / 162 / 1.00 / 0 (y=0.819) | 8.3e-04 / 230 / 1.00 / 1 (y=0.819) |
| 0.3 | 3.7e-02 / 55 / 0.53 / 0 (y=0.255) | 4.7e-03 / 148 / 0.95 / 7 (y=0.252) | 1.4e-03 / 215 / 1.00 / 10 (y=0.252) |
| 0.1 | 8.0e-02 / 45 / 0.43 / 1 (y=0.091) | 9.6e-03 / 122 / 0.86 / 6 (y=0.090) | 4.0e-03 / 187 / 0.97 / 14 (y=0.090) |
| 0.03 | 1.3e-01 / 32 / 0.29 / 1 (y=0.032) | 2.0e-02 / 105 / 0.71 / 6 (y=0.033) | 8.1e-03 / 168 / 0.89 / 15 (y=0.033) |

Manual, Table 4 (same protocol):

| f | 10³ | 10⁴ | 3·10⁴ |
|---|---|---|---|
| 1.0 | 1.5e-2 / 79 / 0.74 / 0 | 1.8e-3 / 166 / 1.00 / 0 | 7.6e-4 / 228 / 1.00 / 2 |
| 0.3 | 3.0e-2 / 58 / 0.56 / 0 | 5.7e-3 / 140 / 0.93 / 5 | 1.5e-3 / 209 / 1.00 / 11 |
| 0.1 | 8.4e-2 / 41 / 0.40 / 0 | 1.1e-2 / 119 / 0.81 / 6 | 3.4e-3 / 191 / 0.97 / 15 |
| 0.03 | 1.5e-1 / 32 / 0.29 / 1 | 1.9e-2 / 101 / 0.71 / 5 | 7.9e-3 / 171 / 0.89 / 14 |

Multi-reference coarse circuits, $5\times10^4$ shots in total at $f = 0.1$:
$B=0$: 32 circuits × 1562 shots → error 2.4e-03 / $|B|$ = 203 /
recall 0.99 / fp 10 (manual: 2.9e-3 / 190 / 0.97);
$B=1$: 12 circuits × 4167 shots → error 4.9e-03 / $|B|$ = 159 /
recall 0.93 / fp 3 (manual: 4.6e-3 / 154 / 0.94).

## 3. Production budget (S1 criterion): $2\times10^5$ shots per sector, multi-reference coarse circuits

| sector | f | circuits | shots/circuit | yield | |B| | E_R − E_0 | recall | fp | r_H | Weinstein [E_R−r_H, E_R] | Kato–Temple (α = 2nd Ritz) | exact E_0 | gap assumption r_H < E_1 − E_R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B=0 | 0.3 | 32 | 6250 | 0.252 | 370 | 1.4e-04 | 1.000 | 25 | 0.035 | [-5.6377, -5.6025] | [-5.6029, -5.6025] | -5.6026 | yes |
| B=0 | 0.2 | 32 | 6250 | 0.169 | 364 | 2.0e-04 | 1.000 | 25 | 0.044 | [-5.6467, -5.6024] | [-5.6031, -5.6024] | -5.6026 | yes |
| B=0 | 0.1 | 32 | 6250 | 0.089 | 347 | 3.2e-04 | 1.000 | 27 | 0.054 | [-5.6565, -5.6023] | [-5.6034, -5.6023] | -5.6026 | yes |
| B=1 | 0.3 | 12 | 16667 | 0.250 | 291 | 3.4e-04 | 1.000 | 19 | 0.050 | [-3.8758, -3.8257] | [-3.9291, -3.8257] | -3.8261 | no |
| B=1 | 0.2 | 12 | 16667 | 0.169 | 272 | 5.4e-04 | 1.000 | 18 | 0.065 | [-3.8910, -3.8255] | [-4.0034, -3.8255] | -3.8261 | no |
| B=1 | 0.1 | 12 | 16667 | 0.088 | 253 | 9.9e-04 | 0.989 | 12 | 0.084 | [-3.9088, -3.8251] | [-4.1176, -3.8251] | -3.8261 | no |

The Weinstein interval is rigorous for *some* eigenvalue; identifying it with $E_0$ needs $r_H < E_1 - E_R$, which
is checked against the exact $E_1$ here (last column).  The Kato–Temple interval uses the second Ritz value as
$\alpha$ and is therefore gap-assumed (Step 5.3 of the manual).

## 4. Ritz error at equal support size (Table 3 analogue)

| sector | protocol | |B|=20 | |B|=40 | |B|=80 | |B|=160 | |B|=320 |
|---|---|---|---|---|---|---|
| B=0 | oracle | 1.1e-01 | 2.5e-02 | 1.0e-02 | 1.2e-03 | 6.7e-05 |
| B=0 | CIPSI | 1.1e-01 | 2.5e-02 | 1.0e-02 | 1.2e-03 | 6.5e-05 |
| B=0 | ML alone (ridge) | 1.1e-01 | 2.6e-02 | 1.3e-02 | 3.5e-03 | 3.0e-04 |
| B=0 | BFS | 1.6e-01 | 8.4e-02 | 1.8e-02 | 6.8e-03 | 6.1e-04 |
| B=0 | random (refs incl.) | 2.0e-01 | 2.0e-01 | 1.8e-01 | 1.8e-01 | 1.2e-01 |
| B=0 | random (no refs) | 5.1e+00 | 4.9e+00 | 4.1e+00 | 2.8e+00 | 1.5e+00 |
| B=0 | device proxy | 1.6e-01 | 2.9e-02 | 1.7e-02 | 1.0e-02 | 1.0e-02 |
| B=0 | device-seeded CIPSI | 1.1e-01 | 2.6e-02 | 1.1e-02 | 1.4e-03 | 8.0e-05 |
| B=1 | oracle | 1.3e-01 | 5.7e-02 | 1.0e-02 | 9.8e-04 | 6.5e-06 |
| B=1 | CIPSI | 6.6e-02 | 2.4e-02 | 1.4e-02 | 1.0e-03 | 6.7e-06 |
| B=1 | ML alone (ridge) | 1.4e-01 | 7.1e-02 | 1.5e-02 | 3.9e-03 | 9.5e-05 |
| B=1 | BFS | 2.1e-01 | 1.0e-01 | 4.6e-02 | 9.0e-03 | 5.9e-04 |
| B=1 | random (refs incl.) | 7.7e-01 | 6.6e-01 | 4.7e-01 | 2.7e-01 | 1.0e-01 |
| B=1 | random (no refs) | 1.7e+00 | 2.6e+00 | 1.5e+00 | 5.6e-01 | 3.7e-01 |
| B=1 | device proxy | 7.3e-02 | 2.8e-02 | 2.0e-02 | 2.0e-02 | 2.0e-02 |
| B=1 | device-seeded CIPSI | 6.2e-02 | 2.4e-02 | 1.4e-02 | 1.2e-03 | 7.5e-06 |

Manual, Table 3 ($B=0$, $|B|$ = 20/40/80/160/320): oracle 1.1e-1 / 2.5e-2 / 1.0e-2 / 1.2e-3 / 6.7e-5;
CIPSI 1.1e-1 / 2.5e-2 / 1.0e-2 / 1.2e-3 / 6.5e-5; ML alone — / 2.6e-2 / 1.5e-2 / 3.5e-3 / 3.4e-4;
BFS 1.5e-1 / 8.4e-2 / 1.8e-2 / 7.6e-3 / 6.2e-4; random 1.05 / 1.05 / 0.86 / 0.88 / 0.73;
device proxy 1.6e-1 / 3.5e-2 / 1.7e-2 / 8.6e-3 / 6.3e-3.  ($B=1$: oracle 1.3e-1 / 5.7e-2 / 1.0e-2 / 9.8e-4 / 6.5e-6;
CIPSI 5.1e-2 / 2.3e-2 / 1.4e-2 / 1.0e-3 / 6.7e-6; device 7.3e-2 / 2.8e-2 / 2.1e-2 / 1.7e-2 / 1.2e-2.)
"random (refs incl.)" keeps the references (the Dirac sea alone carries 0.72 of the $B=0$ weight), which is
why it is far below the manual's random row; "random (no refs)" is the manual's protocol.
Device proxy: single reference, five exact Krylov states, $f = 0.1$, $10^4$ shots per circuit, top-$|B|$ by count.
Device-seeded CIPSI: CIPSI growth from the top-$|B|/2$ device configurations.

ML ranker: ridge regression on 16 gauge-invariant features conditioned on $(g^2, m, B, L_x)$, trained on 2x2 at
$g^2 \in \{1, 1.5, 2, 3, 6\}$ and 2x3 at $g^2 \in \{1, 2, 6\}$ (test coupling $g^2 = 4$ excluded on every lattice),
Spearman rank correlation with $\log|\langle b|\Omega\rangle|$ on the test sectors:

| sector | Spearman ρ |
|---|---|
| B=0 | 0.861 |
| B=1 | 0.888 |

(manual: 0.85 for $B=0$, 0.89 for $B=1$ with its own 16 features).

## 5. Recall of the 99.9 % support versus shots and fidelity (single reference, five exact Krylov states, $B=0$)

| f | 10³ shots | 3·10³ | 10⁴ | 3·10⁴ |
|---|---|---|---|---|
| 1.0 | 0.73 | 0.95 | 1.00 | 1.00 |
| 0.3 | 0.51 | 0.79 | 0.95 | 0.99 |
| 0.1 | 0.45 | 0.65 | 0.84 | 0.97 |
| 0.03 | 0.29 | 0.47 | 0.72 | 0.88 |

## 6. 2x4 transfer and scaling (simulator only)

| protocol | |B| | E_R − E_0 | recall | fp |
|---|---|---|---|---|
| device proxy (multi-ref coarse, f=0.1, 2e5 shots) | 626 | 8.2e-03 | 0.93 | 73 |
| oracle, |B|=320 | 320 | 8.2e-03 | 1.00 | 0 |
| oracle, |B|=640 | 640 | 2.8e-03 | 1.00 | 0 |
| CIPSI, |B|=320 | 320 | 8.2e-03 | 1.00 | 0 |
| CIPSI, |B|=640 | 640 | 2.7e-03 | 1.00 | 0 |
| ML alone (ridge, transfer), |B|=320 | 320 | 1.5e-02 | 0.84 | 24 |
| ML alone (ridge, transfer), |B|=640 | 640 | 7.1e-03 | 0.98 | 94 |

Manual (Step 6.2): device support with f = 0.1 and 2e5 shots: |B| = 544, error 7.5e-3, recall 0.94; CIPSI 2.7e-3 at |B| = 640 (oracle 2.75e-3); ML-alone 8.4e-3 and recall 0.95 at |B| = 640.
ML transfer Spearman on 2x4 B=0: 0.765.

## Interpretation

* The emulation reproduces the manual's qualitative picture: at these sizes the classical CIPSI control tracks the
  oracle and matches or beats the device support at equal $|B|$; the expected hardware outcome is a characterized
  null on the primary endpoint, with the certified spectra as the physics deliverable.
* With the production budget the multi-reference coarse circuits reach the S1 recall criterion at $f = 0.1$ in
  both sectors (see section 3), which fixes the shot rule of eq. (5) of the manual for the hardware run.
* All numbers here are proxy emulations; gate S3 (Aer device-model simulation of the transpiled circuits) is the
  laptop/desktop step that replaces the proxy by a calibrated noise model.

## All checks

| check | value | criterion | result |
|---|---|---|---|
| S1 criterion: 2x3 B=0, f=0.1, 2e5 shots: recall of 99.9% support | 1 | >= 0.9 | PASS |
| 2x3 B=0, f=0.1: exact E0 inside the Weinstein interval | -5.6026 in [-5.6565, -5.6023] | contains E0 | PASS |
| S1 criterion: 2x3 B=1, f=0.1, 2e5 shots: recall of 99.9% support | 0.989 | >= 0.9 | PASS |
| 2x3 B=1, f=0.1: exact E0 inside the Weinstein interval | -3.8261 in [-3.9088, -3.8251] | contains E0 | PASS |
| ML ridge (leakage-safe) Spearman rank correlation, 2x3 g2=4 B=0 | 0.861 | > 0.7 (manual 0.85 / 0.89) | PASS |
| ML ridge (leakage-safe) Spearman rank correlation, 2x3 g2=4 B=1 | 0.888 | > 0.7 (manual 0.85 / 0.89) | PASS |
| controls: CIPSI within 3x of oracle at |B|=160, B=0 | 1.2e-03 vs 1.2e-03 | CIPSI <= 3 x oracle | PASS |
| controls: CIPSI within 3x of oracle at |B|=320, B=0 | 6.5e-05 vs 6.7e-05 | CIPSI <= 3 x oracle | PASS |
| controls: CIPSI within 3x of oracle at |B|=160, B=1 | 1.0e-03 vs 9.8e-04 | CIPSI <= 3 x oracle | PASS |
| controls: CIPSI within 3x of oracle at |B|=320, B=1 | 6.7e-06 vs 6.5e-06 | CIPSI <= 3 x oracle | PASS |
| 2x4 device proxy (f=0.1, 2e5 shots) recall of the 99.9% support | 0.934 | >= 0.85 (manual 0.94) | PASS |

## Reproduce

```
python scripts/gate_S1.py            # full, ~10 min on 2 CPUs
python scripts/gate_S1.py --quick    # 1 repetition, no 2x4, ~3 min
```

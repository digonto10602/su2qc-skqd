# Gate S2 escalation — what compilation and term ablation can and cannot gain

Produced by `scripts/s2_escalation_experiments.py` for the planner decision in `prompts/11_S2_planner_decision_20260915.md`;
numbers in `data/S2_escalation_experiments.json`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 77fb407, 2026-09-15 15:28:40 MDT.  Runtime 110 s.

Reference (`validation/S2.json`, exact structured circuits, level 3): 2x2 coarse step 256 CZ
all-to-all / 516 routed per-term sum (step as one circuit: see S2.json);
2x3 2164 / 4734.  Budget: 250 (2x2) and 500 (2x3) routed.

## 1. Coupling maps (CZ after transpilation at level 3)

| lattice | circuit | all-to-all | heavy-hex seed 7 / best of 8 / mean | square grid best of 8 / mean | line |
|---|---|---|---|---|---|
| 2x2 | coarse step k=1 | 256 | 618 / 600 / 633 | 454 / 480 | 797 |
| 2x3 | coarse step k=1 | 2164 | 5477 / 5401 / 5559 | 4026 / 4127 | 7052 |
| 2x3 | plaq1 | 764 | 1698 / 1621 / 1712 | 1302 / 1318 | 2166 |
| 2x3 | hop4 | 358 | 846 / 776 / 810 | 561 / 573 | 1118 |

Heavy-hex costs 2.4-2.5x the all-to-all count and a seed sweep recovers only a few percent; a square lattice
(Nighthawk-like, degree 4) costs about 1.8x.  No map brings the exact 2x3 step near 500.

## 2. Term ablation at 2x3 (S1 production budget: 2e5 shots per sector, proxy fidelity f, all references, k = 1..4)

Entries: recall of the 99.9 % support / |B| / E_R - E_0 / exact E_0 inside the Weinstein interval.

| sector | generator | reachable (p > 1e-3) | f = 0.2 | f = 0.1 |
|---|---|---|---|---|
| B=0 | full (S1 generator) | 86 of 86 | 1.000 / 367 / 2.6e-04 / yes | 1.000 / 347 / 2.7e-04 / yes |
| B=0 | no plaq1 (interior-corner plaquette) | 83 of 86 | 1.000 / 339 / 1.4e-03 / yes | 0.977 / 321 / 8.8e-03 / yes |
| B=0 | no plaquettes | 79 of 86 | 0.977 / 300 / 3.2e-03 / yes | 0.930 / 293 / 1.8e-02 / yes |
| B=0 | no diag | 86 of 86 | 1.000 / 367 / 2.6e-04 / yes | 1.000 / 347 / 2.7e-04 / yes |
| B=1 | full (S1 generator) | 89 of 95 | 1.000 / 279 / 4.7e-04 / yes | 1.000 / 246 / 8.0e-04 / yes |
| B=1 | no plaq1 (interior-corner plaquette) | 86 of 95 | 0.947 / 240 / 9.3e-03 / yes | 0.937 / 212 / 9.8e-03 / yes |
| B=1 | no plaquettes | 82 of 95 | 0.884 / 201 / 1.8e-02 / yes | 0.895 / 188 / 1.4e-02 / yes |
| B=1 | no diag | 89 of 95 | 1.000 / 279 / 4.7e-04 / yes | 1.000 / 246 / 8.0e-04 / yes |

The diagonal terms cost nothing to keep (8 / 20 CZ) and change nothing.  Dropping only the interior-corner plaquette
keeps the S1 criterion (recall >= 0.9 at f = 0.1) in both sectors; dropping both plaquettes fails it in B = 1.

## 3. Clean-shot fraction f = (1 - eps)^N_CZ (manual eq. 5)

| N_CZ | eps = 1e-3 | eps = 2e-3 | eps = 3e-3 |
|---|---|---|---|
| 250 | 0.779 | 0.606 | 0.472 |
| 500 | 0.606 | 0.368 | 0.223 |
| 618 | 0.539 | 0.290 | 0.156 |
| 1000 | 0.368 | 0.135 | 0.050 |
| 1500 | 0.223 | 0.050 | 0.011 |
| 2164 | 0.115 | 0.013 | 0.002 |
| 5477 | 0.004 | 0.000 | 0.000 |

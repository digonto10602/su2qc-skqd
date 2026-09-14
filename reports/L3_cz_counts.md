# Laptop gate L3 — transpiled CZ counts at 2x2 (gate S2 measurement)

**Status: FAIL (expected for the generic baseline — this is the S2 work item)** —
`scripts/laptop_L3_cz_counts.py`, optimization level 3.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 6972fd5, 2026-09-14 16:58:20 MDT.  Runtime 15 s.

| circuit | CZ | depth |
|---|---|---|
| diag | 8 | 11 |
| hop0 | 16806 | 78297 |
| hop1 | 990 | 4629 |
| hop2 | 16790 | 78270 |
| hop3 | 990 | 4625 |
| plaq0 (structured) | 30 | 109 |
| coarse step k=1 (all-to-all) | 35606 | 165693 |
| coarse step k=1 (heavy-hex d=3, routed) | 55459 | 210356 |

| check | value | criterion | result |
|---|---|---|---|
| CZ per coarse step, all-to-all | 35606 | <= 250 (manual budget) | FAIL |
| CZ per coarse step, routed on heavy-hex | 55459 | <= 250 | FAIL |

Interpretation: the diagonal and the structured plaquette gates are cheap; the four exact hopping block
unitaries (6- and 8-qubit `UnitaryGate`s) dominate.  Their internal structure (chains of at most three
configurations, four flip patterns per link, angles depending on a handful of control bits — see
`reports/circuit_structure.md`) is what a structured decomposition must exploit to reach the budget.

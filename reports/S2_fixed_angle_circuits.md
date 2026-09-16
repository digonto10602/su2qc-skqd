# Fixed-angle generator (gate-S2 escalation, prompts/11) — cost floor, leakage and recall

**This is a MEASUREMENT, not a gate.**  Gate S2 and its criteria are unchanged
(`validation/S2.json`, FAIL on the CZ budget); this file measures the cheapest circuit family
that keeps exact gauge invariance, written by `scripts/gate_S2.py --angle-mode fixed --out S2_fixed`,
optimization level 3, basis {rz, sx, x, cz}, seed 7.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 2fbcf29, 2026-09-15 20:18:31 MDT.  Runtime 301 s.

## What "fixed angle" means

`skqd.circuits_ir.structured_term_gates(..., angle_mode="fixed")` keeps the two-level rotations
between the SAME pairs of codewords as the exact circuits and the same validity controls (a pair
that the term does not connect is left alone, so codewords still map to codewords), but gives every
pair of one qubit-flip pattern the SAME angle: theta_eff = theta x (mean of the distinct |elements|
of the term with that flip pattern), with the sign of each element kept.  With one magnitude per
pattern the generator splits pattern by pattern into disjoint commuting pairs, so one multiplexed
rotation per flip pattern is exact for that flattened generator -- the schedule of the exact mode
(rounds x patterns) collapses to one round per pattern.  The circuit is therefore NOT
exp(-i theta H_gamma); SKQD only needs the support (the classical step diagonalises the exact H on
it and E_R >= E_0 holds for any support), so the recall criterion of gate S1 is re-established by
emulation below.

## 2x2 (12 qubits, heavy-hex d=3, grid (3, 4))

| term | IR gates | CZ all-to-all | CZ heavy-hex | CZ grid | leakage | distance to the exact exp | multiplexed rotations (controls) | merged elements per rotation |
|---|---|---|---|---|---|---|---|---|
| diag | 20 | 8 | 8 | 8 | - | - | - | - |
| hop0 | 108 | 60 | 139 | 90 | 3.3e-15 | 1.1e-01 | 4 (3,3,3,3) | 1,2,2,1 |
| hop1 | 82 | 44 | 97 | 69 | 3.3e-15 | 1.3e-01 | 4 (2,2,2,3) | 1,2,2,1 |
| hop2 | 108 | 54 | 123 | 84 | 3.2e-15 | 9.9e-02 | 4 (3,3,3,3) | 1,2,2,1 |
| hop3 | 86 | 44 | 73 | 64 | 3.6e-15 | 1.1e-01 | 4 (2,2,3,3) | 1,2,2,1 |
| plaq0 | 54 | 30 | 73 | 42 | 1.9e-15 | 3.0e-02 | 1 (4) | 3 |
| coarse step k=1 | 460 | 240 | 671 | 474 | - | - | - | - |

IR gate counts of the coarse step: {'x': 2, 'cx': 278, 'p': 16, 'unitary1q': 32, 'ry': 108, 'h': 8, 'rz': 16}.

## 2x3 (20 qubits, heavy-hex d=5, grid (4, 5))

| term | IR gates | CZ all-to-all | CZ heavy-hex | CZ grid | leakage | distance to the exact exp | multiplexed rotations (controls) | merged elements per rotation |
|---|---|---|---|---|---|---|---|---|
| diag | 37 | 20 | 20 | 20 | - | - | - | - |
| hop0 | 536 | 152 | 247 | 227 | 8.4e-15 | 5.1e-02 | 4 (6,6,6,6) | 3,3,3,3 |
| hop1 | 82 | 44 | 101 | 69 | 4.8e-15 | 7.3e-02 | 4 (2,2,2,3) | 1,2,2,1 |
| hop2 | 544 | 154 | 277 | 217 | 7.9e-15 | 3.4e-02 | 4 (6,6,6,6) | 3,3,3,3 |
| hop3 | 544 | 154 | 290 | 211 | 8.0e-15 | 3.4e-02 | 4 (6,6,6,6) | 3,3,3,3 |
| hop4 | 538 | 244 | 373 | 312 | 9.2e-15 | 4.6e-02 | 4 (6,6,6,6) | 3,3,3,3 |
| hop5 | 536 | 152 | 275 | 208 | 8.9e-15 | 4.5e-02 | 4 (6,6,6,6) | 1,2,2,1 |
| hop6 | 86 | 44 | 71 | 64 | 4.6e-15 | 7.4e-02 | 4 (2,2,3,3) | 1,2,2,1 |
| plaq0 | 548 | 260 | 492 | 382 | 1.2e-14 | 8.0e-03 | 2 (7,7) | 3,2 |
| plaq1 | 910 | 402 | 831 | 585 | 2.0e-14 | 8.9e-03 | 4 (5,7,7,7) | 4,3,3,2 |
| coarse step k=1 | 4364 | 1626 | 3736 | 2803 | - | - | - | - |

IR gate counts of the coarse step: {'x': 3, 'cx': 2266, 'p': 29, 'cp': 2, 'unitary1q': 68, 'ry': 1996}.

## Cost floor against the exact circuits (validation/S2.json)

| lattice | exact all-to-all | fixed all-to-all | ratio | exact heavy-hex | fixed heavy-hex | ratio | fixed grid | budget (routed) |
|---|---|---|---|---|---|---|---|---|
| 2x2 | 256 | 240 | 0.94 | 618 | 671 | 1.09 | 474 | 250 |
| 2x3 | 2164 | 1626 | 0.75 | 5477 | 3736 | 0.68 | 2803 | 500 |

## Recall of the fixed-angle generator at 2x3 (gate-S1 production budget, 2e5 shots per sector)

Entries: recall of the 99.9 % support / |B| / E_R - E_0 / exact E_0 inside the Weinstein interval.
The `exact` rows are the same emulation driven by the exact structured circuits through `run_ir`
on the 2^20 statevector: they must reproduce the gate-S1 numbers (recall 1.000 at f = 0.1,
|B| = 347 in B = 0 and 246 in B = 1), which is the consistency check of the route.

| generator | sector | circuits | shots/circuit | reachable (p > 1e-3) | f = 0.2 | f = 0.1 | run time (s) |
|---|---|---|---|---|---|---|---|
| exact | B=0 | 32 | 6250 | 86 of 86 | 1.000 / 367 / 2.6e-04 / yes | 1.000 / 347 / 2.7e-04 / yes | 1304 |
| exact | B=1 | 12 | 16667 | 89 of 95 | 1.000 / 279 / 4.7e-04 / yes | 1.000 / 246 / 8.0e-04 / yes | 519 |
| fixed | B=0 | 32 | 6250 | 86 of 86 | 1.000 / 324 / 4.7e-04 / yes | 1.000 / 304 / 6.9e-04 / yes | 1190 |
| fixed | B=1 | 12 | 16667 | 72 of 95 | 0.989 / 238 / 1.6e-03 / yes | 0.937 / 204 / 3.2e-03 / yes | 467 |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| 2x2: CZ per coarse step, routed on heavy-hex d=3 | 671 | <= 250 (manual Step 4.3) | FAIL |
| 2x2: CZ per coarse step, routed on the square grid (3, 4) | 474 | <= 250 (manual Step 4.3) | FAIL |
| 2x3: CZ per coarse step, routed on heavy-hex d=5 | 3736 | <= 500 (manual Step 4.3) | FAIL |
| 2x3: CZ per coarse step, routed on the square grid (4, 5) | 2803 | <= 500 (manual Step 4.3) | FAIL |
| leakage of the fixed-angle term circuits (codewords -> codewords, theta = dt, 2dt, 4dt) | 1.998e-14 | < 1e-12 | PASS |
| leakage of the noiseless compiled circuits | 5.496e-14 | < 1e-9 | PASS |
| 2x3 B=0: emulated recall of the 99.9 % support at f = 0.1 | 1 | >= 0.9 (gate S1 criterion) | PASS |
| 2x3 B=1: emulated recall of the 99.9 % support at f = 0.1 | 0.937 | >= 0.9 (gate S1 criterion) | PASS |
| pytest -q tests | 24 passed in 81.96s (0:01:21) | all pass | PASS |

## Verification detail

Leakage was measured per term on 20 random physical states of the local codeword space
(5 for the 14-qubit plaquette supports) at
theta = dt, 2dt, 4dt (columns above), and on the full statevectors of
20 2x2 and 2 2x3 coarse-step circuits
(1.8e-14 worst case, transpiled circuits included).
The deviation column is the distance to the exact local exponential: it is O(0.1) by construction,
and that is the price of the cost reduction in the table above.

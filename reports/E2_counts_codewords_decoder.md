# Gate E2 — state counts, vertex tables, codewords and decoder

**Status: PASS** — produced by `scripts/gate_E2.py`; numbers stored in `validation/E2.json`.
Environment: Python 3.11.15, numpy 2.4.4, scipy 1.17.1, Linux-6.18.44-fc-v24-x86_64-with-glibc2.39, 2 CPUs, commit 5e3fe61, 2026-09-14 20:41:00 UTC.  Runtime 8 s.

## Vertex-type tables (Step 2.1 of the manual)

| vertex type | allowed ({j_e}, n) combinations | physical states | manual: combinations | manual: states |
|---|---|---|---|---|
| corner | 6 | 6 | 6 | 6 |
| interior | 12 | 13 | 12 | 13 |
| corner + static 1/2 | 6 | 7 | 6 | 7 |
| interior + static 1/2 | 12 | 17 | 12 | 17 |

The 13th interior state is the second singlet of $(\tfrac12)^{\otimes 4} = 2(0)\oplus 3(1)\oplus(2)$
(three flux ends and one quark); the fusion-tree label $\iota_x \in \{0,1\}$ is the intermediate spin
$J_{12}$ of the first two link ends.  A charged corner with two flux ends and one quark also has two states.

## State counts (Table 2 of the manual)

| lattice | static sites | states | distinct ({j},{n}) labels | sectors {2B: dim} |
|---|---|---|---|---|
| 2x2 | - | 82 | 82 | {-4: 2, -2: 20, 0: 38, 2: 20, 4: 2} |
| 2x3 | - | 1727 | 1460 | {-6: 4, -4: 95, -2: 426, 0: 677, 2: 426, 4: 95, 6: 4} |
| 2x4 | - | 37165 | 26248 | {-8: 8, -6: 350, -4: 2869, -2: 8934, 0: 12843, 2: 8934, 4: 2869, 6: 350, 8: 8} |
| 2x2 | [0, 2] | 113 | 82 | {-4: 2, -2: 27, 0: 55, 2: 27, 4: 2} |
| 2x2 | [0, 3] | 112 | 82 | {-4: 2, -2: 27, 0: 54, 2: 27, 4: 2} |
| 2x3 | [0, 2] | 2729 | 1460 | {-6: 5, -4: 141, -2: 674, 0: 1089, 2: 674, 4: 141, 6: 5} |
| 2x3 | [0, 4] | 2418 | 1460 | {-6: 4, -4: 119, -2: 597, 0: 978, 2: 597, 4: 119, 6: 4} |

Every count of Table 2 is reproduced: 82 / 1 727 / 37 165 states versus 82 / 1 460 / 26 248 labels, 113 and 112
with a static pair at 2x2, 2 729 ($B=0$: 1 089) and 2 418 ($B=0$: 978) with a static pair at 2x3.

## Codewords and decoder (Steps 2.4–2.5)

| lattice | static | qubits | test | accepted | dim / 2^n | rejection reasons |
|---|---|---|---|---|---|---|
| 2x2 | - | 12 | exhaustive: 82/4096 | 2.002% | 2.002% | {'link': 1214, 'flag': 2800} |
| 2x3 | - | 20 | random: 292/200000 | 0.146% | 0.165% | {'flag': 158515, 'link': 41193} |
| 2x4 | - | 28 | random: 24/200000 | 0.012% | 0.014% | {'flag': 172401, 'link': 27575} |
| 2x2 | [0, 2] | 12 | exhaustive: 113/4096 | 2.759% | 2.759% | {'link': 1651, 'flag': 2332} |
| 2x2 | [0, 3] | 12 | exhaustive: 112/4096 | 2.734% | 2.734% | {'flag': 2332, 'link': 1652} |
| 2x3 | [0, 2] | 21 | random: 259/200000 | 0.130% | 0.130% | {'flag': 167985, 'link': 31756} |
| 2x3 | [0, 4] | 20 | random: 484/200000 | 0.242% | 0.231% | {'flag': 143065, 'link': 56451} |

The decoder accepts exactly the codewords (exhaustively verified at 12 qubits: 82 of 4 096, and 113 of 4 096 with
a static pair); the fraction of uniformly random strings accepted equals $\dim/2^n$ within statistics
(manual: 0.15 % at 20 qubits, $1727/2^{20} = 0.16\%$), so uncorrelated garbage is almost always rejected and the
residual acceptances are valid but unrelated configurations (false positives that enlarge $B$ without biasing the
variational energy).

## All checks

| check | value | criterion | result |
|---|---|---|---|
| vertex table: corner (combinations, states) | (6, 6) | = (6, 6) | PASS |
| vertex table: interior (combinations, states) | (12, 13) | = (12, 13) | PASS |
| vertex table: corner + static 1/2 (combinations, states) | (6, 7) | = (6, 7) | PASS |
| vertex table: interior + static 1/2 (combinations, states) | (12, 17) | = (12, 17) | PASS |
| interior vertex, three flux ends, n=1: singlet multiplicity (13th state) | 2 | = 2 | PASS |
| charged corner, two flux ends, n=1: multiplicity | 2 | = 2 | PASS |
| 2x2 static=[]: states | 82 | = 82 | PASS |
| 2x2 static=[]: distinct ({j},{n}) labels | 82 | = 82 | PASS |
| 2x2 static=[]: sector dims | {-4: 2, -2: 20, 0: 38, 2: 20, 4: 2} | = {-4: 2, -2: 20, 0: 38, 2: 20, 4: 2} | PASS |
| 2x2 static=[]: qubits | 12 | = 12 | PASS |
| 2x2 static=[]: encode-decode round trip | 82/82 | all states | PASS |
| 2x2 static=[]: codewords distinct | 82 | = 82 | PASS |
| 2x2 static=[]: exhaustive acceptance | 82 of 4096 | = 82 | PASS |
| 2x3 static=[]: states | 1727 | = 1727 | PASS |
| 2x3 static=[]: distinct ({j},{n}) labels | 1460 | = 1460 | PASS |
| 2x3 static=[]: sector dims | {-6: 4, -4: 95, -2: 426, 0: 677, 2: 426, 4: 95, 6: 4} | = {-6: 4, -4: 95, -2: 426, 0: 677, 2: 426, 4: 95, 6: 4} | PASS |
| 2x3 static=[]: qubits | 20 | = 20 | PASS |
| 2x3 static=[]: encode-decode round trip | 1727/1727 | all states | PASS |
| 2x3 static=[]: codewords distinct | 1727 | = 1727 | PASS |
| 2x3 static=[]: random-string acceptance | 0.146% | = dim/2^n = 0.165% within 4 sigma (0.036%) | PASS |
| 2x4 static=[]: states | 37165 | = 37165 | PASS |
| 2x4 static=[]: distinct ({j},{n}) labels | 26248 | = 26248 | PASS |
| 2x4 static=[]: sector dims | {-8: 8, -6: 350, -4: 2869, -2: 8934, 0: 12843, 2: 8934, 4: 2869, 6: 350, 8: 8} | = {-8: 8, -6: 350, -4: 2869, -2: 8934, 0: 12843, 2: 8934, 4: 2869, 6: 350, 8: 8} | PASS |
| 2x4 static=[]: qubits | 28 | = 28 | PASS |
| 2x4 static=[]: encode-decode round trip | 37165/37165 | all states | PASS |
| 2x4 static=[]: codewords distinct | 37165 | = 37165 | PASS |
| 2x4 static=[]: random-string acceptance | 0.012% | = dim/2^n = 0.014% within 4 sigma (0.011%) | PASS |
| 2x2 static=[0, 2]: states | 113 | = 113 | PASS |
| 2x2 static=[0, 2]: distinct ({j},{n}) labels | 82 | = 82 | PASS |
| 2x2 static=[0, 2]: qubits | 12 | = 12 | PASS |
| 2x2 static=[0, 2]: encode-decode round trip | 113/113 | all states | PASS |
| 2x2 static=[0, 2]: codewords distinct | 113 | = 113 | PASS |
| 2x2 static=[0, 2]: exhaustive acceptance | 113 of 4096 | = 113 | PASS |
| 2x2 static=[0, 3]: states | 112 | = 112 | PASS |
| 2x2 static=[0, 3]: distinct ({j},{n}) labels | 82 | = 82 | PASS |
| 2x2 static=[0, 3]: qubits | 12 | = 12 | PASS |
| 2x2 static=[0, 3]: encode-decode round trip | 112/112 | all states | PASS |
| 2x2 static=[0, 3]: codewords distinct | 112 | = 112 | PASS |
| 2x2 static=[0, 3]: exhaustive acceptance | 112 of 4096 | = 112 | PASS |
| 2x3 static=[0, 2]: states | 2729 | = 2729 | PASS |
| 2x3 static=[0, 2]: sector dims | {0: 1089} | = {0: 1089} | PASS |
| 2x3 static=[0, 2]: qubits | 21 | = 21 | PASS |
| 2x3 static=[0, 2]: encode-decode round trip | 2729/2729 | all states | PASS |
| 2x3 static=[0, 2]: codewords distinct | 2729 | = 2729 | PASS |
| 2x3 static=[0, 2]: random-string acceptance | 0.130% | = dim/2^n = 0.130% within 4 sigma (0.032%) | PASS |
| 2x3 static=[0, 4]: states | 2418 | = 2418 | PASS |
| 2x3 static=[0, 4]: sector dims | {0: 978} | = {0: 978} | PASS |
| 2x3 static=[0, 4]: qubits | 20 | = 20 | PASS |
| 2x3 static=[0, 4]: encode-decode round trip | 2418/2418 | all states | PASS |
| 2x3 static=[0, 4]: codewords distinct | 2418 | = 2418 | PASS |
| 2x3 static=[0, 4]: random-string acceptance | 0.242% | = dim/2^n = 0.231% within 4 sigma (0.043%) | PASS |

## Reproduce

```
python scripts/gate_E2.py
```

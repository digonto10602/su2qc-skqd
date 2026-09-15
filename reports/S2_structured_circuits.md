# Gate S2 — structured circuits for the hopping and interior-corner plaquette terms

**Status: FAIL** — `scripts/gate_S2.py`, optimization level 3,
basis {rz, sx, x, cz}, seed 7.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 5d60461, 2026-09-15 15:12:59 MDT.  Runtime 436 s.

The hopping terms and the 2x3 plaquettes are compiled by `skqd.circuits_ir.structured_term_gates`:
inside every connected block of the term the exact exponential is written as two-level (Givens)
rotations between computational basis states (bipartite block, singular value decomposition of the
off-diagonal part), rotations of one schedule step that share the qubit-flip pattern are merged into
a single Gray-code uniformly controlled rotation, and the control set is minimised by an
invariance-subspace search that is allowed to act arbitrarily on strings that are not codewords.
A diagonal gauge makes every block generator purely imaginary, so that all two-level rotations are
real and one uniformly controlled Ry per step suffices.  The dense 2x3 plaquette unitary (4 GiB) is
never built; its verification uses the small block `h` of `reference_sim.localize` and the
dressed-basis emulation `krylov.coarse_states`.

## 2x2 (12 qubits, heavy-hex d=3)

| term | IR gates | CZ all-to-all | CZ routed | max deviation | multiplexed rotations (controls) |
|---|---|---|---|---|---|
| diag | 20 | 8 | 8 | - | - |
| hop0 | 132 | 60 | 122 | 1.0e-15 | 5 (3,3,3,3,4) |
| hop1 | 94 | 48 | 92 | 1.2e-15 | 5 (2,2,2,3,3) |
| hop2 | 132 | 66 | 149 | 1.2e-15 | 5 (3,3,3,3,4) |
| hop3 | 90 | 44 | 72 | 1.3e-15 | 5 (2,2,2,2,3) |
| plaq0 | 54 | 30 | 73 | 2.8e-16 | 1 (3) |
| coarse step k=1 | 524 | 256 | 618 | - | - |

IR gate counts of the coarse step: {'x': 2, 'cx': 294, 'p': 16, 'unitary1q': 40, 'ry': 148, 'h': 8, 'rz': 16}.
Baseline (gate L3, dense block unitaries): 35606 CZ all-to-all, 55459 routed.

## 2x3 (20 qubits, heavy-hex d=5)

| term | IR gates | CZ all-to-all | CZ routed | max deviation | multiplexed rotations (controls) |
|---|---|---|---|---|---|
| diag | 37 | 20 | 20 | - | - |
| hop0 | 536 | 194 | 433 | 2.0e-15 | 9 (3,3,4,4,5,5,5,5,6) |
| hop1 | 94 | 48 | 82 | 1.7e-15 | 5 (2,2,2,3,3) |
| hop2 | 484 | 182 | 415 | 1.6e-15 | 9 (3,3,4,4,5,5,5,5,5) |
| hop3 | 486 | 184 | 396 | 1.3e-15 | 9 (3,3,4,4,5,5,5,5,5) |
| hop4 | 746 | 358 | 846 | 2.4e-15 | 9 (3,3,5,5,5,5,6,6,6) |
| hop5 | 478 | 156 | 275 | 1.3e-15 | 5 (4,4,6,6,6) |
| hop6 | 90 | 44 | 72 | 1.7e-15 | 5 (2,2,2,2,3) |
| plaq0 | 430 | 214 | 497 | 6.7e-16 | 4 (5,5,6,6) |
| plaq1 | 1546 | 764 | 1698 | 1.5e-15 | 17 (4,4,4,4,5,5,5,5,5,5,5,5,6,6,6,6,7) |
| coarse step k=1 | 4930 | 2164 | 5477 | - | - |

IR gate counts of the coarse step: {'x': 3, 'cx': 2588, 'p': 29, 'cp': 2, 'unitary1q': 144, 'ry': 2164}.
There is no dense baseline at 2x3: the interior-corner plaquettes act on 14 qubits, where the dense
local unitary would need 4 GiB.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| 2x2: CZ per coarse step, routed on heavy-hex d=3 | 618 | <= 250 (manual Step 4.3) | FAIL |
| 2x3: CZ per coarse step, routed on heavy-hex d=5 | 5477 | <= 500 (manual Step 4.3) | FAIL |
| max |structured circuit - reference| (all terms and circuits, theta = dt, 2dt, 4dt) | 1.874e-14 | < 1e-10 | PASS |
| leakage of the noiseless compiled circuits | 4.508e-14 | < 1e-9 | PASS |
| pytest -q tests | 20 passed in 84.80s (0:01:24) | all pass | PASS |

The routed counts are the ones the budget applies to; the all-to-all counts are the logical cost.
Dominant terms (routed): 2x2 `hop2` with 149 CZ,
2x3 `plaq1` with 1698 CZ.

## Why it is over budget, and what the planner has to decide

The circuits are exact and leak-free (criteria 3 and 4): this is a cost result, not a correctness
problem.  Against the dense-block-unitary baseline of gate L3 at 2x2 (35606 CZ all-to-all,
55459 routed) the structured construction is a factor 90 cheaper routed and
139 cheaper all-to-all; at 2x3 there was no baseline at all, because the dense
14-qubit plaquette unitary would need 4 GiB.  The budget is still exceeded by a factor
2.5 at 2x2 and 11.0 at 2x3.

The last column of the tables above is the anatomy of the cost.  Each term is a sequence of
multiplexed (uniformly controlled) rotations, and one with c controls costs 2^c CNOTs in the
Gray-code form.  Two independent drivers:

1. the **number of rotations** = (rounds of the block schedule) x (distinct qubit-flip patterns):
   five per hopping link at 2x2, nine at 2x3 (blocks of four configurations appear once an interior
   vertex carries an intertwiner label), and 17 for the 2x3 plaquette with two interior
   corners, whose blocks reach five configurations with degree four;
2. the **number of controls** = the qubits the angle depends on (the other flux bits of both
   vertices, the Jordan-Wigner parity, and the bits that select the slot): 2-4 at 2x2 and 4-7 at
   2x3, because the amplitude table has six (hopping) to nine (plaquette) distinct values instead
   of three.

Routing on heavy-hex multiplies this by 2.4 (2x2) and 2.5 (2x3): a multiplexed rotation is a
star of CNOTs from its controls onto one target, and the heavy-hex degree is three.

The budget is not relaxed here.  The escalation clause of `prompts/06` leaves the choice to the
planner: (i) dropping the diagonal terms from the generator cannot close the gap (they cost
8 CZ at 2x2 and 20 at 2x3 all-to-all); (ii) a different vertex qubit layout that
shortens the flip patterns and, above all, reduces the number of angle-selecting controls -- that
changes `codec.py` and requires re-running E1-E3; (iii) raising the budget in the preregistration
with the yield consequence from eq. (5) of the manual, i.e. (1 - p2)^618 at 2x2 and (1 - p2)^5477
at 2x3.

## Verification detail

20 circuits at 2x2 (both sectors, k = 1..4 and the Trotter family) and
2 at 2x3 were compared with `krylov.coarse_states`; every term was compared with the
exact local exponential at theta = dt, 2dt, 4dt on random vectors of its codeword space.  Leakage of the
noiseless compiled statevectors: [2.220446049250313e-16, 1.1102230246251565e-15, 1.2212453270876722e-15, 1.1102230246251565e-16] (2x2), [3.375077994860476e-14] (2x3).
Runtime 436 s on the laptop CPU, inside the 30-minute rule; `--quick` (about one minute) skips
the 2^20 statevector checks at 2x3.

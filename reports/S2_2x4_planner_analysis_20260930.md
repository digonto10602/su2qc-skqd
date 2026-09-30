# 2x4 compilation and device requirement — planner analysis (2026-09-30)

Written by planner-fable at max effort before `prompts/22_2x4_compilation_and_device_requirement.md`.
**Nothing here is a gate result.**  Every number below is either read from a committed JSON (named) or is a
labelled planner computation (P1–P7) whose reproduction snippet is given in section 9; the executor's gate
`S2_2x4` recomputes all of them and writes them to `validation/S2_2x4.json`, which is then the record.
0 QPU seconds.  No file of the prompts/20 do-not-touch list was read for writing, none was modified.

## 0. The question and the answer in one paragraph

The owner's device requirement for these nearly serial circuits is one dimensionless number,
T2/t_2q >= n_qubits x n_2q / (2 ln(1/f_target)) (the serial, linearised, T2-only form of the idle budget of
`skqd.idle`).  It is 667 / 1728 at 2x2 (all-to-all / routed), 9372 / 23786 at 2x3 and 7036 for the 2x3
fixed-angle generator — reproduced from the committed counts in P3.  **For 2x4 no number existed because the
circuits had never been compiled.**  The gating measurement (P1) shows the 2x4 coarse step has 14 term groups on
28 qubits; the middle plaquette `plaq1` acts on **16 qubits** (four interior corners, 1831 local codewords,
811 connected blocks, the largest with 9 configurations of degree 8, 10 distinct |elements|, 8 flip patterns),
and the two interior-to-interior x-links `hop3`/`hop5` are a link type absent at 2x3 (11-qubit support, blocks
of up to 6 configurations).  The structured engine of `skqd.circuits_ir` synthesised and verified **13 of the
14 term groups without any change** at the gate-S2 standard (max deviation 4.2e-15 on the local codeword space,
P5); the 16-qubit `plaq1` is the only term whose cost and synthesis time are not yet on record as this analysis
is written (its row in P5 is filled in below when the run completes).  The dense 2^28 statevector route for the
full coarse step is dead on this CPU (P4: 0.7–3.8 s per gate, i.e. hours per circuit), so the full-circuit
check goes through an exact sparse simulator whose regressions against `run_ir` at 2x2/2x3 and against one
2^28 dense run of a small 2x4 term are the evidence; the Perlmutter Aer-GPU run is the optional independent
cross-check.

## 1. P1 — term supports and block structure at 2x3 and 2x4 (no synthesis)

`term_support` and `localize` only (`src/skqd/reference_sim.py`).  `Model(4)` builds in 9.9 s; `localize` takes
1.4–3.9 s per 2x4 term.  Sites are indexed `x1*2 + x2`; the 2x4 links are
`[(0,2,x),(0,1,y),(1,3,x),(2,4,x),(2,3,y),(3,5,x),(4,6,x),(4,5,y),(5,7,x),(6,7,y)]`; codec widths
`[3,3,4,4,4,4,3,3]` (28 qubits); references B=0: 11 (Dirac sea + 10 one-meson), B=1: 4 diquarks.

| lattice | term | support (qubits) | local codewords | blocks | largest block | max degree | distinct \|elements\| | flip patterns |
|---|---|---|---|---|---|---|---|---|
| 2x3 | hop0 | 9 | 78 | 40 | 4 | 2 | 6 | 4 |
| 2x3 | hop1 | 6 | 18 | 10 | 3 | 2 | 3 | 4 |
| 2x3 | hop2 | 10 | 156 | 80 | 4 | 2 | 6 | 4 |
| 2x3 | hop3 | 10 | 156 | 80 | 4 | 2 | 6 | 4 |
| 2x3 | hop4 | 8 | 85 | 47 | 4 | 2 | 6 | 4 |
| 2x3 | hop5 | 9 | 78 | 46 | 3 | 2 | 3 | 4 |
| 2x3 | hop6 | 6 | 18 | 10 | 3 | 2 | 3 | 4 |
| 2x3 | plaq0 | 14 | 383 | 194 | 3 | 2 | 5 | 2 |
| 2x3 | plaq1 | 14 | 383 | 162 | 5 | 4 | 9 | 4 |
| 2x4 | hop0 | 9 | 78 | 40 | 4 | 2 | 6 | 4 |
| 2x4 | hop1 | 6 | 18 | 10 | 3 | 2 | 3 | 4 |
| 2x4 | hop2 | 10 | 156 | 80 | 4 | 2 | 6 | 4 |
| 2x4 | **hop3** (2→4, interior→interior) | **11** | 340 | 160 | **6** | 4 | 9 | 4 |
| 2x4 | hop4 | 8 | 85 | 47 | 4 | 2 | 6 | 4 |
| 2x4 | **hop5** (3→5, interior→interior) | **11** | 340 | 188 | 4 | 2 | 6 | 4 |
| 2x4 | hop6 | 10 | 156 | 80 | 4 | 2 | 6 | 4 |
| 2x4 | hop7 | 8 | 85 | 47 | 4 | 2 | 6 | 4 |
| 2x4 | hop8 | 9 | 78 | 46 | 3 | 2 | 3 | 4 |
| 2x4 | hop9 | 6 | 18 | 10 | 3 | 2 | 3 | 4 |
| 2x4 | plaq0 | 14 | 383 | 194 | 3 | 2 | 5 | 2 |
| 2x4 | **plaq1** (four interior corners) | **16** | 1831 | 811 | **9** | **8** | 10 | 8 |
| 2x4 | plaq2 | 14 | 383 | 162 | 5 | 4 | 9 | 4 |

Every block has a zero diagonal (`diag_nz False` for all 22 terms), which is the premise of the
bipartite SVD construction of `circuits_ir._block_rounds`.  Block-size histograms: 2x4 plaq1
`{1: 163, 2: 375, 3: 225, 4: 9, 5: 36, 9: 3}`; 2x4 hop3 `{1: 64, 2: 32, 3: 52, 4: 8, 6: 4}`.

**What "16 qubits" does and does not mean.**  The dense local unitary of a 16-qubit support is 2^32 complex
entries (68 GB) and is never built — it was never built at 14 qubits either.  Term verification at the gate-S2
standard uses `localize`'s block `h` (1831 x 1831 here) and `run_ir` on the 2^16 local statevector (1 MB), so
the width of the plaquette support is **not** what decides the route.  What it decides is the synthesis cost
(the control-minimisation search runs over 2^15-entry tables per candidate target) and the gate count.

## 2. P2 — the disjoint-term fraction and the term-overlap chromatic number

From the same supports (the diagonal term touches every qubit and is excluded from the "hop/plaq" count):

| lattice | terms (hop+plaq) | pairs | disjoint pairs | fraction | pairs incl. diag | chromatic number of the overlap graph | serial rounds |
|---|---|---|---|---|---|---|---|
| 2x2 (`data/S2_duration_compare.json` rescheduling_headroom.terms) | 5 | 10 | 1 (hop1, hop3) | 0.10 | 1 of 15 | — | 6 |
| 2x3 | 9 | 36 | 10 | 0.28 | 10 of 45 | 6 | 9 |
| 2x4 | 13 | 78 | 35 | 0.45 | 35 of 91 | 6 | 13 |

Reading: at 2x4 nearly half of the term pairs commute trivially (disjoint supports), and the overlap graph is
6-colourable at both 2x3 and 2x4, so a coarse step could in principle be executed in 6 rounds of mutually
disjoint term gates instead of 13 serial ones.  Two caveats that the prompt carries: (i) the ASAP scheduler
already exploits disjointness present in the *given* order (the transpiled DAG has disjoint terms as parallel
branches), and the measured seriality tells how much of it is realised; (ii) **reordering the terms to reach
the 6-round packing changes the coarse-step state** (the order of the groups in `krylov.term_groups` /
`CircuitFactory.coarse_step` is a convention of this package that the emulated recall of gates S1/S2_fixed
was established on), so it is a method decision with a recall re-emulation, not a compilation option; the
prompt measures the packing bound and stops there.  The intra-term seriality is the other half of the
picture: a uniformly controlled rotation with c controls is a chain of 2^c rotations and 2^c CNOTs on **one
target qubit**, and no reordering shortens it.

## 3. P3 — the owner's serial formula reproduced from the committed counts

`T2/t_2q >= n x n_2q / (2 ln 10)` at f_target = 0.1:

| circuit | n | n_2q | source | T2/t_2q |
|---|---|---|---|---|
| 2x2 all-to-all | 12 | 256 | `validation/S2.json` 2x2 all_to_all.cz | 667.1 |
| 2x2 routed, the frozen canary | 12 | 663 | `data/S2_duration_compare.json` frozen n_cz | 1727.6 |
| 2x2 routed heavy-hex d=3 | 12 | 618 | `validation/S2.json` 2x2 routed.cz | 1610.4 |
| 2x3 all-to-all (RZZ) | 20 | 2158 | `data/S2D_2x3_device_requirements.json` | 9372.1 |
| 2x3 all-to-all (CZ) | 20 | 2164 | `validation/S2.json` | 9398.1 |
| 2x3 routed heavy-hex d=5 | 20 | 5477 | `validation/S2.json` | 23786.3 |
| 2x3 fixed-angle all-to-all (RZZ 1620 / CZ 1626) | 20 | 1620 / 1626 | sheet / `validation/S2_fixed.json` | 7035.6 / 7061.6 |

The owner's 667, 1728, 9372, 23786 and 7036 are these rows.  The formula assumes (a) a perfectly serial
circuit, T = n_2q t_2q; (b) every qubit idle for the whole of T; (c) the linearised T2 term only (no T1 term,
no saturation of 1 − e^{−w/T2}).  On the frozen 2x2 canary (a) holds to 3 % (T = 43.71 us against
663 x 68 ns = 45.08 us: seriality 0.969) and (b) does not (qubit-time utilisation 0.233, i.e. the qubits are
idle 77 % of T — `data/S2_duration_compare.json` rescheduling_headroom).  The prompt therefore asks for the
**scheduled** number (`skqd.idle.schedule_asap` + `idle_budget` on a uniform record, T2 solved by bisection)
next to the formula, so that the ratio of the two is measured rather than assumed.

Heron r2 for comparison (`data/hardware/H0_diag_prep/calibration_20260922T1400Z.json`, the 12 qubits the
canary ran on; cz 68 ns, sx 24 ns): T2 mean 119.1 us, median 111.9, min 16.0, max 265.1, harmonic mean 70.6,
so T2/t_cz = 1751 (mean), 1038 (harmonic), 3898 (max).  The owner's "3897 at its best coherence" is the
max row; the owner's "1912 on the patch that flew" is not reproduced by any single statistic of this record
(the 30-qubit record `data/hardware/H0_ibm_fez/calibration_20260922T1400Z.json` gives 1695 / 1077 / 3856) and
is left as the owner's figure.  The idle budget is a per-qubit sum, so the honest device-side comparison is
the coherence scale factor on a real record (`gate_S2D_idle.coherence_scale`: 5.51x on the live record for
2x2, `validation/S2D_idle.json`), which the prompt also asks for at 2x4 on the FakeFez full-device snapshot.

## 4. P4 — the dense 2^28 route is dead on this CPU, per gate

`run_ir` per-gate wall time (numpy, in-place strided views for cx/p, `apply_local` copies for ry), this
laptop, 2026-09-30:

| statevector | cx (low qubits) | cx (high qubits) | ry | p | peak RSS |
|---|---|---|---|---|---|
| 2^24 | 0.133 s | 0.045 s | 0.251 s | 0.063 s | 1.1 GB |
| 2^26 | 0.514 s | 0.169 s | 0.932 s | 0.254 s | 4.3 GB |
| 2^28 | 2.079 s | 0.691 s | 3.848 s | 1.021 s | 16.9 GB |

A 2x4 coarse step has of order 10^4 cx and 10^4 ry (P5), i.e. **10–20 h per circuit** at 2^28; even one
hop term (hop0: 278 cx + 240 ry) is 20–25 min.  The 62 GiB hold it (16.9 GB peak with the work copies), the
30-minute rule does not.  The only dense 2^28 run the prompt keeps is the smallest term, `hop1` (54 cx,
28 ry, 10 unitary1q: about 3 min, 17 GB), as the cross-check of the sparse simulator on a genuine 28-qubit
circuit.  Qiskit's `Statevector` and Aer-CPU at 28 qubits are of the same order (memory-bound); Aer-GPU on
one A100 is the natural place for the full dense run, and `scripts/ci_smoke.py` already verified that a
28-qubit statevector fits on one GPU (`aer_28q_memory`).

## 5. P5 — synthesis scale of the 2x4 terms (structured engine, unchanged code)

`circuits_ir.structured_term_gates` at theta = dt (2x4, B = 0: 0.11469820342078263, `validation/E3.json`),
exact mode, this laptop.  One scratch patch only: `ucr_gray`'s O(N^2) Python construction of the Gray-code
transform matrix was replaced by the fast Walsh–Hadamard form for the measurement (checked equal to the
original to 1.1e-16 for every k <= 8; the gate lists are the same up to that rounding).  Verification =
`run_ir` on the 2^k local statevector against `expm(-i theta h)` on 5 (k <= 11) or 3 (k >= 14) random
vectors of the local codeword space — the gate-S2 standard.

| term | k | IR gates | cx | ry | unitary1q | multiplexed rotations | controls min/med/max | synthesis | verification | max deviation | leakage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hop0 | 9 | 536 | 278 | 240 | 18 | 9 | 3/5/6 | 3 s | <1 s | 2.4e-15 | 1.4e-14 |
| hop1 | 6 | 94 | 54 | 28 | 10 | 5 | 2/2/3 | 4 s | <1 s | 1.2e-15 | 5.2e-15 |
| hop2 | 10 | 484 | 258 | 208 | 18 | 9 | 3/5/5 | 3 s | <1 s | 1.3e-15 | 1.3e-14 |
| hop3 | 11 | 3000 | 1548 | 1408 | 44 | 22 | 5/6/7 | 7 s | 1 s | 4.1e-15 | 3.2e-14 |
| hop4 | 8 | 746 | 390 | 336 | 18 | 9 | 3/5/6 | 4 s | <1 s | 3.4e-15 | 2.4e-14 |
| hop5 | 11 | 1040 | 542 | 480 | 18 | 9 | 4/5/7 | 5 s | <1 s | 1.8e-15 | 1.7e-14 |
| hop6 | 10 | 486 | 260 | 208 | 18 | 9 | 3/5/5 | 3 s | <1 s | 1.4e-15 | 1.3e-14 |
| hop7 | 8 | 746 | 390 | 336 | 18 | 9 | 3/5/6 | 4 s | <1 s | 3.7e-15 | 2.5e-14 |
| hop8 | 9 | 478 | 244 | 224 | 10 | 5 | 4/6/6 | 3 s | <1 s | 1.7e-15 | 1.2e-14 |
| hop9 | 6 | 90 | 54 | 24 | 10 | 5 | 2/2/3 | 5 s | <1 s | 1.4e-15 | 5.8e-15 |
| plaq0 | 14 | 430 | 228 | 192 | 8 | 4 | 5/6/6 | 3 s | <1 s | 4.2e-16 | 3.1e-15 |
| plaq1 | 16 | 132554 | **66468** | 65920 | 164 | 82 | 7/9/11 | 152 s | 172 s | 4.1e-14 | 5.5e-14 |
| plaq2 | 14 | 1546 | 806 | 704 | 34 | 17 | 4/5/7 | 9 s | 1 s | 9.8e-16 | 1.1e-15 |

Sum over the 13 hop/plaq terms other than plaq1: **5052 cx** in the IR (the 2x3 coarse step has 2588 IR cx
for 2164 CZ after level-3 transpilation, `validation/S2.json` ir_gate_counts_coarse_step).  **No obstruction
was met**: every block is bipartite with a zero diagonal, `_real_gauge` found a real gauge for every term
(all rotations are Ry, no zyz fallback), no assertion fired, and every term is exact to <= 4.2e-15.  The
generalisation risk the owner named is therefore a cost question for one term, not a construction question.
**The 16-qubit `plaq1` synthesised in 152 s and verified in 172 s (3 random vectors on the 2^16 local space) at
4.1e-14, again with no obstruction — but it costs 66468 IR cx, 93 % of the step's 71520 (13 hop/plaq terms; the
diagonal term adds a few tens), i.e. 5.1x the whole 2x3 step.**  Its 82 multiplexed rotations carry 7–11
controls (histogram 7:1, 8:23, 9:29, 10:14, 11:15), and a Gray-code rotation with c controls is 2^c CNOTs, so
the cost is where the angle table's dependence on the four interior corners' recoupling data puts it.  Two
cost levers are visible in the code and are **not** part of prompts/22: (a) `_reduce_controls` searches
invariance directions exhaustively only up to m = 10 control bits (`max_full=10`) and restricts itself to
weight <= 3 directions above that — every plaq1 rotation starts at m = 15, so its control count is an upper
bound of what the minimisation could reach; (b) a block that is a star K_{1,8} (the 9-configuration blocks)
is diagonalised through a full 8 x 8 Givens elimination of the singular-vector basis, where a 7-rotation
chain would do.  Both are compilation improvements to be measured in their own prompt, after this one has
put the baseline on record.

Fixed-angle mode (`angle_mode="fixed"`, one rotation per flip pattern, the generator of `validation/S2_fixed.json`;
leakage is the hard requirement, the deviation is a reported number): hop0 272 cx, hop1 52, hop2 280, hop3 536,
hop4 272, hop5 536, hop6 280, hop7 272, hop8 272, hop9 52, plaq0 286, **plaq1 12952** (8 rotations, 9–11
controls, 32 s + 58 s), plaq2 484 — **16546 IR cx for the step**, every term leak-free (worst 3.2e-13 < 1e-12),
per-term deviation from the exact exponential 1.8e-3 … 1.3e-2 (the plaquette angles are small, theta/(2 g^2)).
Its recall at 2x4 is not established (section 8).

## 6. P6 — transpilation is cheap

qiskit 2.5.2 on the 2x3 coarse step (4930 IR gates, 20 qubits), seed 7: level 1 all-to-all 1.9 s (2570 CZ),
level 1 heavy-hex d=5 0.3 s (7817 CZ), level 3 all-to-all 0.2 s (2164 CZ = `validation/S2.json`), level 3
heavy-hex d=5 0.5 s (5477 CZ = `validation/S2.json`).  Level 3 is therefore the standard at 2x4 as well; a
10^5-gate circuit is expected to transpile in well under a minute (the executor records the time).

## 7. What the prompt decides on the strength of P1–P6

1. Route: the structured engine as it is, plus one additive change (the fast Walsh–Hadamard angle transform
   in `ucr_gray`, switched on only above 10 controls so that every 2x2/2x3 gate list stays bit-for-bit what
   it was) and per-term IR caching so that each command stays inside the 30-minute rule.
2. Verification: the gate-S2 term standard (1e-10 on the local codeword space at theta = dt, 2dt, 4dt;
   leakage 1e-12), the full coarse step against `krylov.coarse_states` through an exact sparse simulator
   (regressed against `run_ir` at 2x2/2x3 to 1e-13 and against one dense 2^28 run of `hop1`), the compiled
   circuit's leakage < 1e-9 through the same simulator, and the E3 link (dt and sector dimensions read from
   `validation/E3.json`, equal to the model's to 1e-12).
3. Measurements: CZ all-to-all and routed (heavy-hex d=5, the 2x3 map, and d=7; plus the FakeFez map), depth,
   CZ depth, ASAP duration and idle budget on a uniform record at the Heron durations (cz 68 ns, sx 24 ns) and at
   t_1q = 0 (the formula's premise), the T2 requirement by bisection with T1 = infinity and with T1 = T2, the serial
   formula next to it, the gate-only eps2 bound, the FakeFez coherence scale, the disjoint-term fraction, the
   chromatic number and the packing bound — for 2x2 (anchored to the committed canary numbers), 2x3 and 2x4,
   exact and fixed-angle.
4. No hardware verdict: the gate produces the requirement; whether any device meets it is the owner's match.

## 8. Honest limits

- The fixed-angle numbers at 2x4 are a cost floor only: the generator's recall has been emulated at 2x3
  (`validation/S2_fixed.json`, 1.0 / 0.937) and never at 2x4.
- The uniform-record requirement is a PTA bound (`skqd.idle` is a bound, not a prediction — prompts/20 M-A);
  the Aer-scheduled prediction at 28 qubits is a Perlmutter job, not a laptop one, and is not part of this
  prompt.
- The T2 convention (Hahn-echo vs in-circuit T2*) is the vendor's to declare; the requirement is quoted as a
  ratio T2/t_2q and the owner attaches the convention when matching a device (amendment 01 item 2).
- Term reordering (section 2) is not evaluated: it is a convention change with a recall re-emulation.

## 9. Reproduction snippets

P1/P2 (`/tmp` scratch, 60 s): `Model(Lx)`, `term_support`, `localize` per term; components with
`scipy.sparse.csgraph.connected_components`; disjoint pairs by set intersection of the supports; chromatic
number by backtracking on the overlap graph.  P3: the table's counts from the named JSON keys, times
n / (2 ln 10).  P4: `run_ir([("cx",[0,1],None)]*4, n, state)` etc., timed per gate at n = 24, 26, 28.
P5: `structured_term_gates(M, O, sup, dt, stats=st)` per term with `ucr_gray` patched to the Walsh–Hadamard
form; verification as in `scripts/gate_S2.py:term_deviation`.  P6: `qiskit.transpile` of
`ir_to_qiskit(F.coarse_step(ref, 1, dt), 20)` at levels 1 and 3, all-to-all and `CouplingMap.from_heavy_hex(5)`.
Heron statistics: the `T2_s` and `cz_duration_s` leaves of the named records.  The executor's gate script
recomputes every P1–P6 quantity; where a value here differs from `validation/S2_2x4.json`, the JSON wins.

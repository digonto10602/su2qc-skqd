# Manual: compressing Trotterised coarse-step circuits of lattice gauge theories (the genie-opus technique)

- **Written:** 2026-10-26 by genie-opus (Opus 5.5, high effort), for agents working on *other* lattice-gauge-theory
  projects in parallel with this one.
- **Repository it describes:** `su2qc-skqd` (owner Digonto), study folder `2x4_compression_using_ai_v1/`.  Every path
  below is relative to the repository root unless it starts with `src/c2x4/`, `scripts/`, `data/`, `lean/`,
  `notes/`, `reports/`, `reviews/` or `noise/`, which are inside `2x4_compression_using_ai_v1/`.  Package code
  (read-only for the study) is under `src/skqd/` at the repository root; I write it as `skqd.<module>`.
- **Git state described:** commit `bf55f30` and earlier (results), plus this manual.  No new compression run was
  made for this manual; every number is quoted from a file that is named next to it.
- **Related documents (read them if you can):** `reports/003-full-compression-report.md` (the first round, v1, with
  the full story), `reports/004-c4-c3-second-round-and-2x3.md` (second round, v2, and 2x3),
  `reviews/001-independent-verification.md` (independent review), `notes/007-planner-review-ultimate-compression.md`
  (lower bounds, planner's view), `notes/008-owner-decisions-C1-C6.md` (naming and separation rule),
  `notes/009-family-api.md` (loader API), `notes/010-c4-c3-work-plan.md`, `noise/reports/003-noise-results.md`.

**How claims are marked in this manual.**

| mark | meaning |
|---|---|
| **[Lean]** | proved in Lean 4 / Mathlib in `lean/Compress2x4/*.lean`; `lake build` passes, no `sorry`, standard axioms only |
| **[num]** | checked numerically, per instance, by a script whose output file is named |
| **[heur]** | a heuristic, an estimate, or a judgement; not a computed fact |

---

## Contents

1. Purpose and results
2. Prerequisites and inputs
3. The procedure, step by step (a)–(k)
4. Generalisation guide (U(1), SU(2) at other truncations, SU(3), 2D, other fermion encodings)
5. Verification protocol (mandatory)
6. Lean workflow
7. Loop and process
8. Dead ends and pitfalls
9. Usage limits (class B) and noise behaviour
10. Rules for the parallel projects (naming and separation)
11. Quick-start checklist
12. Appendix: code map, data files, commands, environments

---

## Glossary (every term is also defined where it is first used)

| term | meaning |
|---|---|
| qubit, gate | a two-level quantum memory element; an elementary operation on one or two qubits |
| ZZ count | the number of two-qubit gates (CX, CZ, controlled phase, RZZ). Each becomes exactly one Quantinuum `ZZPhase` in the package's conversion. It is the cost that matters most on hardware |
| two-qubit depth | the longest chain of two-qubit gates in the as-soon-as-possible schedule, one-qubit gates counted as free (pytket's `depth_2q`) |
| codeword | a bit string of the full register that encodes a physical, gauge-invariant basis state of the model |
| local codeword | the restriction of codewords to the qubits a term acts on (its *support*) |
| leakage | the probability weight of a state on non-codeword strings (and, separately, on codewords of another symmetry sector) |
| term group | one summand $H_\gamma$ of the Hamiltonian that the coarse step exponentiates as a whole: here `diag`, `hop0..`, `plaq0..` |
| coarse step | one first-order Trotter product $U_k=\prod_\gamma e^{-i\,k\,dt\,H_\gamma}$ at angle $\theta=k\,dt$, applied to one reference basis state |
| block | a connected component of the graph of a term's matrix on its local codewords; inside a block the term mixes states, between blocks it does not |
| multiplexor (uniformly controlled rotation) | a rotation of one *target* qubit whose angle depends on the values of several *control* qubits |
| Walsh support | the number of nonzero coefficients $a_S$ in $\theta(c)=\sum_{S}a_S(-1)^{\lvert S\cap c\rvert}$ of a multiplexor's angle table; each nonempty mask $S$ costs at least one CNOT in walk form |
| frame (my label) | a cheap change of basis applied before a term and undone after it |
| clean ancilla | a qubit of the term's support that is $\lvert0\rangle$ on every codeword because its information is duplicated elsewhere; usable as scratch |
| flag (my label) | a Boolean AND of a few bits written into a clean ancilla so that a multiplexor can be controlled by it |
| relative-phase Toffoli | a cheaper Toffoli that is correct only up to a phase diagonal in the computational basis; used only as compute … uncompute |
| class A | a compressed circuit that is exact on **every** codeword (operator-exact) |
| class B | a compressed circuit that is exact only on its **own reference input** (one basis state) |
| reachable set | the codewords that can carry amplitude before a given term when the circuit starts from the reference; computed from the graph of the Hamiltonian, never from amplitudes |
| skeleton | a gate list with the angles removed (gate names and qubits only) |
| MILP | mixed-integer linear programme (here solved by HiGHS through `scipy.optimize.milp`) |
| $f$ | the package's gate-only clean-shot fraction $f=(1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{\rm ro})^{n_m}$ (`skqd.device_req.clean_shot_fraction`), with device numbers from `data/quantinuum/devices_20261002.json` |
| H2-2 | the Quantinuum H2-2 device row of that file |
| Q1L | the package's conversion proof that a pytket level-0 native circuit equals the IR circuit (two-qubit skeleton, one-qubit segments, rounding bound $B$), `skqd.quantinuum_native.local_equivalence_35a` |
| IR | the package's gate-list format: a list of tuples `(name, [qubits], parameter)` (`skqd.circuits_ir`) |

---

## 1. Purpose and results

### 1.1 What problem the technique solves

The package runs sample-based Krylov quantum diagonalisation (SKQD) of SU(2) lattice gauge theory with staggered
quarks on $2\times L_x$ ladders.  The quantum circuits are **coarse steps**: prepare one reference basis state
$\lvert b_0\rangle$ with X gates, then apply

$$U_k=\prod_{\gamma}e^{-i\,k\,dt\,H_\gamma},\qquad \gamma=\texttt{diag},\texttt{hop}_0,\dots,\texttt{plaq}_0,\dots$$

in the package's fixed order (first group first), and measure in the computational basis.  The register is a
**compact gauge-invariant encoding** (`skqd.codec`): only gauge-invariant basis states are codewords, each vertex
owns a block of qubits (its link-end flux bits and one vertex bit), and every link is stored twice (once at each end).

The package's own circuits (the *frozen* families) are built term by term with a generic exact synthesis
(block-wise SVD rounds, Gray-code multiplexors, `skqd.circuits_ir.structured_term_gates`).  At 2x4 that gave
71 548 two-qubit gates per circuit — far beyond any device.  The technique in this manual exploits exact structure of
the gauge-invariant Hamiltonian (vertex/corner factorisation, uniform hop couplings, redundant link copies, the small
reachable set of a single basis state) to compress each term while keeping the package's accuracy bar.

### 1.2 Results

The bar (package, prompts/35b R1): for every (reference, $k$), the circuit's full state compared with the package's
exact coarse state `skqd.krylov.coarse_states` (complex128) must satisfy $\max_s\lvert\psi_se^{-i\varphi}-t_s\rvert<
10^{-10}$ after removing the global phase $\varphi$, and leakage $<10^{-9}$.

| lattice | family | circuits | ZZ count (min–max, mean) | 2q depth | accuracy (max) | $f$ H2-2 gate-only (mean) | sources |
|---|---|---|---|---|---|---|---|
| 2x2 | frozen (package) | 28 | 252 | 201 | passes package Q1 | 0.793 | `data/quantinuum/circuits_2x2/index.json` (`summary.n_zz`); `data/quantinuum/circuits_2x2/B0_ref06_k1.manifest.json` (`levels.0.counts.depth_2q`); `validation/Q0P_2x2.json` (`data.Q5.devices.quantinuum_h2_2.f_gate_only_mean`) |
| 2x2 | classA / classB | — | **not built** (see 1.3) | — | — | — | — |
| 2x3 | frozen (package) | 44 | 2 158 | 1 925 | passes package Q1 | 0.150 | `data/quantinuum/circuits_2x3/index.json`; `.../B0_ref25_k1.manifest.json`; `validation/Q0P_2x3.json` (`data.stage_A.predict.devices.quantinuum_h2_2`) |
| 2x3 | `compressed_circuit_llm_2x3_classA` | 44 | **871** | 611 | certified $9.41\times10^{-13}$; Aer $3.05\times10^{-14}$ (44/44) | **0.445** | `data/c2x3/eval_arch_L3_it1_operator_pp2_all44_pruned.json`, `data/c2x3/aer_compressed_circuit_llm_2x3_classA.json`, `data/c2x3/native_compressed_circuit_llm_2x3_classA.json` |
| 2x3 | `compressed_circuit_llm_2x3_classB` | 44 | **309–465 (387.6)** | 170–290 | certified $4.37\times10^{-13}$; Aer $2.10\times10^{-14}$ (44/44) | **0.692** | same paths with `input` / `classB` |
| 2x4 | frozen (package, structured source) | 75 | 71 548 | 70 300 | passes package Q1 | $4.18\times10^{-29}$ | `data/quantinuum/circuits_2x4/B0_ref102_k1.structured.manifest.json` (`levels.0.counts`); `validation/QN_2x4.json` (`data.analytic.devices.quantinuum_h2_2.f_gate_only_mean`) |
| 2x4 | `compressed_circuit_llm_2x4_classA_v1` | 75 | 1 736–1 740 (1 739.2) | 1 275–1 280 | certified incl. rounding $1.72\times10^{-12}$ | 0.2005–0.2009 (4 circuits) | `data/eval_arch_it5_operator_pp_all75_pruned.json`, `data/rounding_v1.json`, `data/native_it5_operator.json` |
| 2x4 | `compressed_circuit_llm_2x4_classB_v1` | 75 | 582–800 (683.5) | 292–469 | certified incl. rounding $7.72\times10^{-13}$ | 0.4718–0.5751 (4 circuits) | `data/eval_arch_it5_input_pp_all75_pruned.json`, `data/rounding_v1.json`, `data/native_it5_input.json` |
| 2x4 | `compressed_circuit_llm_2x4_classA_v2` | 75 | **1 492** | **948** | certified $1.75\times10^{-12}$; Aer sample $1.91\times10^{-14}$ | **0.2512** | `data/eval_arch_it6_operator_pp2_all75_pruned.json`, `data/aer_compressed_circuit_llm_2x4_classA_v2_sample_B1_ref230_k5.json`, `data/native_compressed_circuit_llm_2x4_classA_v2.json` |
| 2x4 | `compressed_circuit_llm_2x4_classB_v2` | 75 | **580–763 (675.0)** | 292–429 | certified $7.70\times10^{-13}$; Aer sample $2.83\times10^{-14}$ | **0.5293** (0.4881–0.5763) | `data/eval_arch_it6_input_pp2_all75_pruned.json`, `data/aer_compressed_circuit_llm_2x4_classB_v2_sample_B0_ref345_k1.json`, `data/native_compressed_circuit_llm_2x4_classB_v2.json` |

All numbers above are also collected in `data/report004_tables.json` (`scripts/report004_tables.py`).
"Certified" = measured deviation + pruned norm + floating-point rounding bound (§5.2).  The 2x4 frozen numbers are the
package's structured source, verified by the package (`validation/S2_2x4.json`, `validation/QV_2x4_01.json`).
Independent verification of v1 by another agent: `reviews/001-independent-verification.md` (verdict CONFIRMED WITH
NOTES).  The noise agent re-ran Aer on all 75 class-B v2 circuits and 40 of 75 class-A v2 circuits with zero failures
(`noise/reports/003-noise-results.md` §3.1).

Ratios to the frozen circuits (computed from the table): 2x4 class A v2 48×, class B v2 106×; 2x3 class A 2.48×,
class B 5.57×.

### 1.3 2x2 — not compressed; how to do it

**I did not compress the 2x2 circuits.**  The package's frozen 2x2 family has 28 circuits (5 references at $B=0$:
6, 43, 30, 21, 17; 2 at $B=1$: 14, 7; $k=1..4$), 12 qubits, 252 ZZ, two-qubit depth 201, and gate-only $f=0.793$ on
H2-2 (sources in the table).  The planner's remark (`notes/007-planner-review-ultimate-compression.md` §8.3):
"Already 252 ZZ with $f=0.79$ on H2-2 … Apply the technique only for uniformity of the hardware story; no cost case."

How to run it with the parameterised code (no new code paths are needed for the physics; three small bookkeeping
edits are needed first — I checked the inputs below on 2026-10-26 without running any compression):

1. `Problem(lx=2)` already works: for $L_x\notin\{3,4\}$ it takes `dt` from `Model(2).reference(4, 2B).dt`, which
   equals the frozen manifests (0.24501194722475933 at $B=0$, 0.33194310785049674 at $B=1$, checked against
   `data/quantinuum/circuits_2x2/B0_ref06_k1.manifest.json` and `B1_ref14_k1.manifest.json`), and
   `krylov.references(Model(2).basis, 2B)` returns `[6, 43, 30, 21, 17]` and `[14, 7]`, the frozen list.  Terms:
   `diag, hop0..hop3, plaq0`; 12 qubits; 82 basis states.
2. Bookkeeping edits before running (each one line or a few lines):
   - `src/c2x4/env.py:archive_path` routes only labels starting with `L3_` to `data/c2x3/`; add `L2_` →
     `data/c2x2/`.
   - `scripts/eval_family.py`: the `baseline` block and the output sub-folder are written for $L_x\in\{3,4\}$ (any
     other $L_x$ would be labelled with the 2x3 baseline 2158); add a 2x2 branch with baseline 252 from
     `data/quantinuum/circuits_2x2/index.json` and sub-folder `c2x2/`.
   - `scripts/certify_family.py`, `scripts/verify_aer_family.py`, `scripts/native_family.py`: their sub-folder rule
     is `c2x3/` if 2x3 else none; add 2x2.  Add the names `compressed_circuit_llm_2x2_classA/_classB` to
     `FAMILY_NAMES` in `src/c2x4/families.py`.
   - Circuit ids: `Problem.tag` writes `B0_ref6_k1`; the frozen 2x2 files zero-pad (`B0_ref06_k1`).  Keep the study's
     tag and record the mapping in the metadata.
3. Run (commands as in §11, with `--lx 2`, labels `L2_it1…`, `--kmax 4`).  The 2x2 plaquette has four *corner*
   vertices (two links each, no intertwiner), so `cfg_lin` applies; the hops are corner–corner; there is no
   all-interior plaquette.
4. **Expected effort [heur]:** at 2x3 the class-A loop took 125 s (`data/c2x3/loop_L3_it1_op.log`) and a class-B
   batch of 5–6 references about 510–560 s (`data/c2x3/archive_L3_it1i{0,1}.json` `wall_s`); 2x2 is smaller
   (5 terms, 12 qubits), so expect minutes per run and well under an hour in total including verification.
   Whether it beats 252 ZZ is **unknown** — I have no 2x2 number.  The corner–corner terms of 2x3/2x4 cost 52 ZZ
   (hop1, hop6 at 2x3; `data/report004_tables.json` `per_term_2x3`), so a guess for class A is in the low hundreds,
   but that is a guess, not a measurement.

---

## 2. Prerequisites and inputs

### 2.1 What the method needs from a project

| input | what exactly | where it came from here |
|---|---|---|
| codeword set and qubit layout | the list of codewords as integers (qubit $k$ = bit $k$ of the integer, little-endian) and, per vertex, which qubits hold which link ends and the vertex bit | `skqd.reference_sim.CodewordEmbedding(Model(Lx))` → `.ints`, `.codewords`, `.codec` (offsets, widths, `decode_vertex`); `skqd.lattice.Ladder` (`ends()`, `links`, `plaquettes`) |
| term groups | the Hamiltonian as an ordered dictionary of sparse matrices on the dressed (codeword) basis | `Model(Lx).terms.groups(g2, m)` → `diag`, `hop<l>`, `plaq<p>` |
| term support and local matrix | for each term: the qubits it acts on, the local codewords (restrictions of codewords to those qubits), and the term restricted to them | `skqd.reference_sim.term_support(model, kind, idx)` and `localize(model, H, support)` → `(states, h, pos)`; wrapped by `src/c2x4/problem.py:Problem.local` |
| reference states | basis indices of the circuit inputs, per sector | `skqd.krylov.references(basis, twoB)` |
| $dt$ and $k$ convention | $\theta=k\,dt$, $dt$ per sector, $k=1..k_{\max}$ | 2x4: `data/quantinuum/circuits_2x4/index.json` (copied from `validation/E3.json`), $k=1..5$; 2x3: manifests, $k=1..4$ |
| exact reference | the target state of each circuit | `skqd.krylov.apply_groups(mats, basis_vector(dim, ref), k*dt)` = `coarse_states(...)[k]` (scipy `expm_multiply`, complex128); `Problem.target` |
| the baseline circuit | the frozen IR of each term, to reproduce first | `skqd.circuits_ir.CircuitFactory(Model, g2).hop_gates/plaq_gates/diag_gates/prepare`; `Problem.baseline_term_ir` |
| device numbers (optional) | $\varepsilon_2,\varepsilon_1,\varepsilon_{\rm ro}$ for $f$ | `data/quantinuum/devices_20261002.json` |

### 2.2 Questions to ask in a new project (checklist)

1. What is the term order of the coarse step, and is it a convention that defines the target state?  (Here yes:
   reordering terms that do not commute changes the target; only disjoint-support terms may be reordered —
   **[Lean]** `kron_disjoint_comm`.)
2. What is the encoding of one vertex?  Which qubits are link-end fluxes, which are vertex labels (occupation,
   intertwiner/multiplicity labels)?  Are links stored once or twice?
3. Is every term *local*: does it act only on a known support, and is its matrix on the full basis equal to
   $h_{\rm loc}\otimes 1$ on codewords?  (Here: `localize` gives exactly that; it is the package's own convention.)
4. Which bit convention is used (little/big endian)?  Here qubit $k$ = bit $k$ (`skqd.reference_sim`).
5. What is the accuracy bar, phase-aligned or not, and how is leakage defined?
6. Which inputs will the circuits ever see?  (One basis state → class B is possible; superpositions, repeated steps or
   controlled versions → class A only.)
7. Which device and native gate set is the cost model?  (Here Quantinuum ZZPhase; IBM would add routing.)
8. Is there a fermion ordering (Jordan–Wigner) and where do its signs sit?
9. Are matrix elements real in some diagonal gauge?  (`skqd.circuits_ir._real_gauge`; here yes, with $\eta=i$ on
   x-links.)
10. Which numbers are frozen and must never be changed (conventions, references, $dt$)?

### 2.3 If the encoding differs

- **Links stored once:** the clean-ancilla trick of step (e) and (g) needs another source of redundancy.  Compute the
  affine $\mathbb F_2$ relations of the occupied strings (`src/c2x4/plaqfactor.py:f2_relations`); every relation is a
  qubit that a CNOT network can clear.  If there is none, flags need an extra qubit (support extension) or must be
  dropped.
- **Vertex label not a single bit:** factorisation tests (step b) still apply; corner/vertex blocks get bigger; use the
  SVD-based frame (step c, general form) instead of the "pair + one three-state block" rule.
- **Big-endian or permuted layout:** keep the project's convention; the study code only assumes the IR convention
  "qubit $k$ = bit $k$ of the integer" — translate at the boundary, never inside.
- **Complex matrix elements without a real gauge:** the bipartite block rounds (step h) need real antisymmetric
  generators; generic blocks fall back to Givens elimination, which is not angle-linear (step h fails loudly with
  `NotImplementedError`).

---

## 3. The procedure, step by step

Overview (the order I recommend; it is also the order in the quick start §11):

```
(a) harness ─► (b) structure tests ─► (c) plaquettes: corner frames + one rotation ─► (d) signs over F2
     ─► (e) clean ancillas + flags ─► (f) sparse-Walsh multiplexors + MILP certificates
     ─► (g) hops: vertex frames, flags, JW sign ─► (h) angle-linear synthesis (k-independent)
     ─► (i) class B restriction ─► (j) peephole + CX-run resynthesis ─► (k) native conversion
```

Every construction is wrapped as a **proposal** (a function `(P, name, theta, contract_states|None,
reach_local|None) -> gate list`, registry `src/c2x4/proposals.py:PROPOSALS`) and judged only by the evaluator.

### (a) Evaluator harness — reproduce the baseline first

**Purpose.**  An evaluator that shares no construction code with any proposal, and that reproduces the package's
numbers exactly before anything is compressed.

**Math.**
- *Counts:* ZZ count and two-qubit depth from the gate list (`src/c2x4/evaluate.py:counts`).  Multi-qubit `unitary`
  gates are refused (they have no honest cost).
- *Term check (A1), all columns in one run:* append $\lceil\log_2N\rceil$ index qubits that carry the column label,
  start from $\sum_s\lvert s\rangle\lvert{\rm idx}(s)\rangle/\sqrt N$ over the $N$ local codewords, run the exact sparse
  simulator.  By linearity the amplitude on $\lvert o\rangle\lvert{\rm idx}(s)\rangle$ is $U_{os}/\sqrt N$, so one run
  gives every column of the candidate's unitary $U$ (rows over all $2^k$ local strings).  Compare with
  $e^{-i\theta h}$ (`evaluate.py:term_unitary_columns`, `verify_term_operator`).  Contract option: only the columns of
  a given subset (class B).
- *Circuit check (A2):* full state from $\lvert0\cdots0\rangle$ (the circuit prepares its own reference), read on the
  codewords, compared with `Problem.target`; phase-aligned deviation, leakage summed directly on non-codeword strings
  (`verify_circuit`, `verify_circuit_pruned` — use the pruned one, §5.2).

**Decision rule.**  Do not start compressing until the harness reproduces the frozen numbers.  Here:
71 548 ZZ and depth 70 300 on `B0_ref102_k1`, state deviation $4.54\times10^{-14}$, every frozen term on all codeword
columns to $\le4.1\times10^{-13}$ (`data/p2_0_harness_baseline.json`, `scripts/p2_0_harness_baseline.py`) **[num]**.

**Cost.**  Seconds per term; the A1 check of a 16-qubit term with 1 831 columns runs in seconds to a minute.

### (b) Structure tests

**Purpose.**  Find the exact structure that makes compression possible, before writing constructions.  Everything
in this manual was found by these tests, not by blind search.

**Tests to run (code: `scripts/p2_1_structure.py` → `data/p2_1_structure.json`; `scripts/hop_coeff_values.py` →
`data/hop_coefficient_values.json`; `notes/007` §5.2 with `scripts/planner_bounds_007.py` →
`data/planner_bounds_007.json`):**

1. **Blocks** of each term on its local codewords (`reach.py:components`, `scipy.sparse.csgraph.connected_components`
   on $\lvert h\rvert>10^{-12}$).  Count blocks, block sizes, and whether each block is bipartite with zero diagonal
   (`skqd.circuits_ir._bipartition`).  Here every block of every term is bipartite with zero diagonal (a hop changes
   $n_x$ by one; a plaquette flips all four link spins), which is what makes the SVD rounds of step (h) work.
2. **Plaquette corner factorisation:** is $h_P\big\vert_C=A_{c_{00}}\otimes A_{c_{10}}\otimes A_{c_{11}}\otimes
   A_{c_{01}}$, with $A_c$ a real matrix on corner $c$'s qubits?  Fit $\log\lvert h\rvert$ by least squares over the
   corner-pair keys and the signs over $\mathbb F_2$, then check the product on every codeword column and every row
   of the $2^k$ local space (`src/c2x4/plaqfactor.py:factorise`).  Result here: exact, residual $\le2.6\times10^{-15}$
   for all plaquettes **[num]** (`data/p2_1_structure.json`).
3. **Hop vertex factorisation:** is $T=\eta\,a_x\otimes b_y\otimes s_{\rm JW}$ with $H_{\rm hop}=T+T^\dagger$, $\eta=i$
   on x-links and real on y-links (`src/c2x4/hopframe.py:hop_vertex_factors`)?  Here exact, residual
   $\le2.7\times10^{-15}$, and each vertex factor is an equal-step three-level chain $n=0\to1\to2$ (spin-1 raising
   operator) **[num]** (`data/p2_1_structure.json`).
4. **Pair-magnitude ratios at corners:** at every corner of every plaquette the two pair magnitudes have ratio
   $1/\sqrt2$ to $10^{-10}$, so on non-dark labels the plaquette angle table is
   $\theta(x)=\pm\theta_0A\prod_c(-1/\sqrt2)^{x_c}$, a product of four one-bit functions with exactly 16 Walsh masks
   **[num]** (`data/planner_bounds_007.json`, planner's observation, notes/007 §5.2).
5. **Coefficient tables of the hop multiplexors in the bright frame:** every pair coupling is $d=0.5$ or $1.0$ for all
   ten 2x4 hops and all seven 2x3 hops, although the raw hop matrix elements take 3–9 distinct magnitudes between
   0.177 and 0.707 **[num]** (`data/hop_coefficient_values.json`).  Consequence: the hop multiplexor cost comes from
   the zero slots and the signs, not from the magnitudes — that motivated the flags of step (g).
6. **Reachable support** from one reference (`scripts/p1_reachable_support.py` → `data/p1_reachable_support.json`):
   here `plaq1` can touch 344–578 of its 648 non-trivial blocks and each hop only 0–12 **[num]**.  Small reachable
   sets mean class B will gain a lot on hops.

**Decision rules.**  Factorisation exact (residual at round-off) → use step (c)/(g).  Factorisation fails → see §4.6
(signs that the factorisation fails, fallback order).

### (c) Plaquettes: corner factorisation → corner frames → CNOT ladder → one multiplexed rotation

**Purpose.**  Turn a plaquette term (four corners, eight link bits flipped together) into **one** multiplexed
rotation on **one** qubit, inside a cheap frame.

**Math.**
1. *Corner frame.*  At each corner $c$ with plaquette-link qubits $p_a,p_b$: apply ${\rm CX}(p_a\to p_b)$; now
   $p_b$ holds $x_c=p_a\oplus p_b$, and every pair block of $A_c$ differs only in $p_a$.  For a three-state block
   $s_0\leftrightarrow\{s_1,s_2\}$ with $A s_0=v_1s_1+v_2s_2$ (the intertwiner case at interior corners), apply the
   two-level rotation $R=\frac1{\lvert v\rvert}\begin{pmatrix}v_1&v_2\\-v_2&v_1\end{pmatrix}$ on $(s_1,s_2)$: the *bright*
   combination goes to $s_1$, the *dark* one to $s_2$, and the dark state decouples.  Afterwards
   $A_c=X_{p_a}\otimes D_c(\ell)$ with $D_c$ diagonal in the corner's labels $\ell$ (checked entry by entry,
   `plaqfactor.py:corner_frame`).
2. *Ladder.*  $L=\prod_{c\neq1}{\rm CX}(p_1\to p_{a,c})$ gives $L\,(X^{\otimes4})\,L^{-1}=X_{p_1}$ on the four $p_a$:
   the simultaneous flip of eight link bits becomes the flip of one qubit **[Lean]** `xorLinear_conj_flip`
   (Bits.lean).
3. *One rotation.*  On the occupied strings the frame generator is $X_{p_1}\otimes{\rm diag}(F)$ (checked), so
   $$e^{-i\theta X_{p_1}{\rm diag}(F)}=H_{p_1}\,{\rm diag}\bigl(e^{-i\theta(-1)^{s_{p_1}}F(s)}\bigr)\,H_{p_1}$$
   **[Lean]** `exp_xt_diag` (Pair.lean) — a multiplexed $R_x(2\theta F)$ on $p_1$; the term is
   frame$^{-1}\cdot$rotation$\cdot$frame **[Lean]** `exp_conj_frame` (Exp.lean); non-occupied strings are don't-cares
   **[Lean]** `exp_agree_mulVec` (Exp.lean).

**Pseudo-code** (`plaqfactor.py:cf1_gates`; the general version with flags is `cfg_gates`):

```
corners = corners_of(P, p)                     # c00, c10, c11, c01 with qubits, plinks, third link, vertex bit q
fac = factorise(P, name, corners)              # A_c and residuals; raise if signs do not factorise
frame = []
for c in corners: frame += corner_frame(A_c)   # CX(p_a -> p_b) + bright rotations of three-state blocks
frame += [CX(p1 -> p_a[c]) for c != c00]       # ladder
H2, omega = frame_generator(P, name, frame)    # F h F^dag on the occupied strings omega
assert every element of H2 flips only p1      # X_{p1} (x) diag(F)
items = [(s0, s0|p1, exp(-i theta F(s0) X)) for s0 in occupied pairs if F != 0]
core = multiplexed_two_level(1<<p1, items, valid=omega)   # step (f)
return frame + core + invert(frame)
```

**Cost.**  Frame: 4 corner CX + bright rotations (a few CNOTs per interior corner) + 3 ladder CX, each way; plus one
multiplexor.  First result: `plaq1` 66 468 → 2 110 two-qubit gates with an 11-control multiplexor (CF1), all 1 831
columns to $3.4\times10^{-14}$ **[num]** (report 003 §2.3.4).  The multiplexor's controls are the reason the next two
steps exist.

### (d) Sign fixing over $\mathbb F_2$

**Purpose.**  After the frames, $F$ carries label-dependent signs.  Signs that are *not* a function the multiplexor
already represents cheaply must be removed by cheap diagonal corrections before the multiplexor is built.

**Math.**  Write the sign of each sample $s$ as $b(s)\in\{0,1\}$.  "Free" sign sources (cost 0): all monomials of the
four $x_c$ (they are inside the multiplexor's own table), the sign of each bright rotation ($R_y(\varphi+2\pi)=-R_y(\varphi)$,
**[Lean]** `ry_add_two_pi`, Reach.lean), and each flag $g_c$.  "Costed" sources: ${\rm CZ}(c,p_a)$ (1 ZZ),
${\rm CZ}(q,p_a)$ (1 ZZ), and a doubly-controlled Z ${\rm CCZ}(p_a,\bar x,c)$ built from 3 controlled phases + 2 CX
(5 ZZ) via
$$\tfrac\pi2\bigl(bc-(a\oplus b)c+ac\bigr)=\pi abc$$
**[Lean]** `ccz_phase`, `ccz_circuit` (Bits.lean).  Solve the linear system $F_{\rm free}\,u\oplus F_{\rm cost}[:,{\rm sel}]\,w=b$
over $\mathbb F_2$ for every subset `sel` of costed sources in increasing total cost; the first consistent one wins
(`plaqfactor.py:f2_solve`, inside `cf2_gates`/`cfg_gates`).

**Decision rule.**  Cheapest consistent correction set; if none exists, raise ("sign structure not absorbable").

**Pitfall from this project:** offer the CCZ as a costed option; without it, plaq1 needed an 8th control (see §8.4).

### (e) Clean ancillas from redundant link bits; dark-state flags with relative-phase Toffolis

**Purpose.**  Remove control qubits from the plaquette multiplexor by computing the few Boolean conditions it needs
(dark states) into scratch qubits that are free on every codeword.

**Math.**
1. *Clean ancillas.*  Every link is stored at both ends; after the ladder, $p_{a,c}$ ($c\neq1$) holds
   $p_{a,c}\oplus p_1$, a parity of $x$-labels.  The affine relations of the occupied set (`f2_relations`) say which
   qubit is a fixed parity of others; a CNOT network from those others clears it to $\lvert0\rangle$ on every
   codeword.  Here up to four clean ancillas per plaquette, 6 CX to clear and 6 to restore (report 003 §2.4.3).
2. *Dark flags.*  The dark state of corner $c$ is $(x_c=0,c_c=1,q_c=1)$ ($c_c$ the third link, $q_c$ the vertex bit).
   A relative-phase Toffoli (Margolus, 3 CX, `plaqfactor.py:rtof`) writes $g_c=c_c\wedge q_c$ into an ancilla.  The
   angle table becomes $F(x,g)=\theta\,M(x)\prod_c(1-\bar x_cg_c)$ with 7 controls for plaq1.  The relative phase
   cancels between compute and uncompute because the multiplexor is block-diagonal in its controls **[Lean]**
   `relphase_cancel` (Reach.lean), `ucr_comm_ctrl_phase` (Conj.lean).
3. *Corner rule.*  Only corners that *have* a dark state get a flag ("dark" rule: a three-state block or an isolated
   valid state annihilated by $A_c$; `cfg_gates(flag_rule="dark")`; the "triple" rule is kept as a second proposal).

**Pseudo-code** (`plaqfactor.py:cfg_gates`):

```
frame = corner frames with sign corrections (step d) + ladder
rel = f2_relations(occupied strings)
clear = pick pivots: cleared p_a's first, then x of corner c01; one relation per pivot
frame += CX networks that zero the pivots ; assert pivots are 0 on every occupied string
frame += [rtof(third_c, q_c -> ancilla_c) for corners with a dark state]
H3 = frame generator ; items = rotations with angle theta*F
core = multiplexor over relabelled bits (flag source bits first, so the greedy reducer drops them)
return frame + core + invert(frame)
```

**Cost (2x4, class A, `data/report004_tables.json` per term):** plaq0 88, plaq1 202 (v2; 220 in v1), plaq2 96.  At
2x3: plaq0 88, plaq1 96.  For plaq1 v2 the multiplexor is 7 controls, support 85, walk 92 CNOTs; frames are the rest
(`data/cert_it6_operator.json`).

### (f) Sparse-Walsh multiplexors, walk ordering, and the MILP minimum-support certificate

**Purpose.**  The package builds every multiplexor as a Gray-code chain over all $2^m$ masks ($2^m$ CNOTs).  When most
slots of the table are free (unoccupied) or the table has structure, far fewer masks suffice.

**Math.**  A uniformly controlled $R_y$ decomposes as
$$\sum_c\lvert c\rangle\langle c\rvert\otimes R_y(\theta_c)=\prod_S\exp\bigl(-\tfrac i2a_SZ_SY_t\bigr),\qquad
\theta_c=\sum_Sa_S(-1)^{\lvert S\cap c\rvert},$$
each factor being ${\rm CX}_S\,R_y(a_S)\,{\rm CX}_S$ **[Lean]** `cx_conj_yt`, `exp_conj_cx_yt`, `exp_sum_commuting`,
`walk_factors_comm` (Ucr.lean, Pair.lean).  Consecutive factors share CNOTs, so the cost is the length of a closed
walk from $\emptyset$ through the nonzero masks in the Hamming metric.  A closed walk through $s$ distinct nonzero
masks has $s+1$ edges, so **walk CNOTs $\ge s+1$**.

**Algorithm (`src/c2x4/sparsemux.py:sw_two_level`, `sparse_walsh`, `mask_walk`; angle-linear version
`src/c2x4/linsynth.py:lin_two_level`, `_solve_table`):**

```
for t in first 3 bits of the flip pattern:               # target choice
    compress the pattern onto t (CX from t to the other flipped bits)
    build the slot table over the other k-1 bits; mark occupied-but-unrotated slots fixed (identity)
    control reduction: package _reduce_controls (invariance directions, CNOT frame on controls)
    fixed slots -> values; free slots -> don't-care
    LP:  minimise ||a||_1  s.t.  W_fixed a = theta_fixed    (HiGHS)
    prune greedily while an exact solution remains; re-solve exactly on the support (residual <= 1e-12)
    [MILP mode: exact minimum support, below]
    order masks by nearest neighbour + 2-opt; cost = walk + 2*frame + 2*(|pattern|-1)
keep the cheapest target
```

**MILP certificate (`src/c2x4/certify.py:min_walsh_support`, `scripts/certify_family.py`).**  With fixed slots $F$, free
angles $y$ ($\lvert y_i\rvert\le M_\theta=8\pi$), $a=a_0+Ky$ ($a_0=2^{-m}W_{:,F}\theta_F$, $K=2^{-m}W_{:,\rm free}$),
binaries $z_S$ with $\lvert a_S\rvert\le M_Sz_S$, $M_S=\lvert a_{0,S}\rvert+\lVert K_S\rVert_1M_\theta$:
$$\min\sum_{S\neq\emptyset}z_S.$$
The HiGHS dual bound is a lower bound on the support of every completion with free angles in the box; an upper bound
is accepted only after an exact least-squares re-solve.  `certified_optimal` := support used equals the lower bound.
Tables with no free slot have a unique Walsh transform and need no MILP.  Results are cached on disk keyed by the
table (`cached_min_walsh_support`).

**What the certificate means.**  Minimal Walsh support *for this target, this control reduction and this frame*,
free angles in $[-8\pi,8\pi]$, HiGHS trusted (not verified).  It says nothing about other constructions **[num]**.

**Results:** 2x4 class A v2: 64 of 65 multiplexors support-optimal, support 643 vs lower bound 632, walk 750 vs 697;
class B v2: 813 of 852; 2x3 class A 43 of 43; class B 388 of 396 (`data/cert_it6_{operator,input}.json`,
`data/c2x3/cert_L3_it1_{operator,input}.json`).  The one open class-A table is plaq1's (support 85, lower bound 78
after 1 500 s, `data/cert_it6_operator_plaq1_long.json`).

**Cost of the step itself.**  LP: milliseconds to seconds.  MILP: instant for $m\le5$, up to the time limit for
$m=7$ with free slots.  As a synthesis option the MILP rarely beat the LP heuristic and sometimes lost on walk length
(`data/loop_it6a.log`) — use it mainly to certify.

### (g) Hops: vertex factorisation, parity fold, bright frames, flags, JW sign

**Purpose.**  Compress the hopping terms $H_{\rm hop}=T+T^\dagger$, $T=\eta\,a_x\otimes b_y\otimes s_{\rm JW}$.

**Math and constructions (code `src/c2x4/hopframe.py`):**
1. *Parity fold* (`vertex_parity_frame`): at each end vertex, ${\rm CX}(f\to L_v)$ for the other flux bits $f$, so
   $L_v$ holds the vertex's flux parity ($n_v$ odd iff $L_v=1$).  Then $n=0\mapsto(L,q)=(0,0)$, $1\mapsto(1,0)$,
   $2\mapsto(0,1)$, dark intertwiner $\mapsto(1,1)$.
2. *Bright frame* (`vertex_bright_frame`, `_bright_rotations`): where the vertex factor maps one state onto two
   intertwiner states (or is reached from two), one two-level rotation of the vertex bit makes the bright combination a
   basis state.  After this, the framed generator has only pair blocks ($N=n_x+n_y=1$ and $3$) and three-state chains
   ($N=2$: $(2,0)$–$(1,1)$–$(0,2)$); no 4- or 6-state blocks.  hop3 then needs 5 multiplexors instead of 22
   (report 003 §2.4.5).
3. *Block synthesis* (`framed_gates` → `reach.py:synth_on`): the package's bipartite SVD rounds, now angle-linear
   (step h).  A chain costs a $\theta$-independent basis change (two Givens rotations), one pair rotation, and the
   inverse basis change.
4. *Clean ancilla and flags* (`vertex_bright_frame_clean`, `linsynth.py:_flag_variants`, `_flag_gates`; proposals
   `cb0`, `cb1`, `cb0_jwc`, `cb1_jwc`): the hopping link is stored at both end vertices.  Fold vertex $B$'s parity into
   its first *other* flux qubit, apply $B$'s bright rotations, clear $B$'s copy of the hopping link by
   ${\rm CX}(f_l^A\to f_l^B)$ (before $A$'s fold changes $f_l^A$), then fold and rotate at $A$: one clean ancilla for
   1 CX each way.  For every multiplexor the synthesis also tries a flag $g=$ AND of 2–3 control literals that is 1 on
   every nonzero slot (the literal must be constant on all nonzero slots; candidates ranked by how many zero slots they
   exclude), written into the ancilla by a relative-phase AND (Margolus 3 CX or the RC3X of qiskit's `RC3XGate`,
   6 CX).  The nonzero entries move to the ancilla = 1 half of the table, where the zero-coefficient slots no longer
   constrain it.  Constant multiplexors (basis changes) go through the same path (`CONST_LIN`).
5. *JW sign as a conjugation* (`jwc_framed_gates`, proposals `jwc_*`): check $H_2=(-1)^{{\rm par}(J)}h_0$ element by
   element ($J$ = support qubits outside the two end vertices); fold ${\rm par}(J)$ into $p=J[0]$; synthesise
   $e^{-i\theta h_0}$ without $J$; conjugate every $\theta$-multiplexor's target by ${\rm CZ}(p,t)$ (in the $R_y$ frame:
   $Z R_y(\varphi)Z=R_y(-\varphi)$, and the closed walk's CNOT signs cancel in pairs).  Valid because
   $e^{\theta(-A)}=B^{T}P(-\theta)B$ when $e^{\theta A}=B^TP(\theta)B$ **[Lean]** `z_ry_z`, `cz_conj_ucr`,
   `neg_generator_conj` (Conj.lean).

**Decision rules.**  Run all hop proposals (`full_lin`, `framed_lin`, `bframed_lin`, `jwc_*`, `cb*`, `*_milp`) and keep
the cheapest verified one per term.  Observed: `cb1`/`cb1_jwc` win on interior hops, `full_lin` on corner–corner
y-hops, `bframed_lin` on hop2 (`data/report004_tables.json` `per_term_2x4`).  JW conjugation alone gains little (a
parity sign only shifts masks, it does not add them: hop3 256 → 264 with LP, `data/loop_it6a.log`).

**Cost (2x4 class A, it5 → it6, `data/report004_tables.json`):** hop0 140→130, hop3 256→168, hop4 166→130, hop5
178→134, hop6 134→124, hop7 166→130, hop8 116→114; hop1, hop2, hop9 unchanged (52, 110, 52).  Hop sum 1 370 → 1 144.

### (h) Angle-linear synthesis — the skeleton must not depend on $k$

**Purpose.**  The SKQD pipeline's gate Q0P requires the ZZ count of a reference to be equal for all $k$ (criterion
Q2).  In v1 the count varied (class A 1 736–1 740 within a reference; class B `B0_ref1338` 760/762;
`data/report004_tables.json` `2x4.*_v1.k_dependent_references_by_count`).  Cause: $\theta$-dependent rotations reached
the multiplexor synthesis as $2\times2$ unitaries at the circuit's own angle, and structural decisions (control
reduction by numerical equality, axis orientation, zero tests) were taken on those unitaries.

**Method (`src/c2x4/linsynth.py`).**
- A $\theta$-dependent two-level op is carried as its **generator**: `LinRot(G, θ)` = $e^{-i\theta G}$, $G$ a fixed
  traceless Hermitian $2\times2$ matrix.  Every decision (target, control reduction, Walsh support, walk order, flags)
  is taken on the $\theta$-free coefficient table $c({\rm slot})$ with slot unitary $R_{\hat n}(\theta c)$; only the
  emitted angles are multiplied by $\theta$.
- `lin_block_rounds` re-implements the package's bipartite rounds: $e^{\theta A}=B^{T}P(\theta)B$, $A=\begin{pmatrix}0&K\\-K^T&0\end{pmatrix}$,
  $K=USV^T$, $B$ from $U,V$ ($\theta$-free), $P(\theta)$ the pair rotations $e^{\theta[[0,d_i],[-d_i,0]]}=$
  `LinRot(-d_i σ_y, θ)`.  **The gauge fix of $U,V$ flips signs, so use $D=U^TKV$, $d_i=D_{ii}$, not the singular
  values** (this was a bug, §8.6).  Non-bipartite blocks raise `NotImplementedError` (no angle-linear form).
- Switch it on with `with use_linear(mode)` (`mode` = `"lp"` or `"milp"`); proposals `*_lin`, `*_lin_milp`, `jwc_*`,
  `cb*` all use it.

**Done-check.**  `scripts/eval_family.py` records a skeleton hash per circuit and `summary.skeleton_k_independent`;
it is `true` in all four new families (`data/eval_arch_it6_*_pp2_all75_pruned.json`,
`data/c2x3/eval_arch_L3_it1_*_pp2_all44_pruned.json`) **[num]**.  Unit tests: `tests/test_linsynth.py`.

### (i) Class B: reachable-set restriction, dropping the diagonal group, the input contract

**Purpose.**  When a circuit only ever runs on its own reference basis state, most blocks of most terms are never
touched; they become don't-cares.

**Math.**
- *Reachable set* (`src/c2x4/reach.py:Reach.before`): $S_\gamma$ = codewords that can carry amplitude before term
  $\gamma$ = the union of the connected components of the earlier terms' graphs reached from the reference.  An exact
  upper bound, independent of $\theta$ and of every amplitude.
- *Restriction* (`restricted_term_gates`, `contract_states`): term $\gamma$ is synthesised exactly on every local string
  of the blocks touched by the local parts of $S_\gamma$ (the **contract**); every other local string is free.
- *Why exact on the reference:* by induction over the terms, **[Lean]** `agree_on_reachable_n` (Reach.lean), with the
  linear-algebra glue `kron_agree_of_support`, `reindex_kron_agree`, `exp_mulVec_supported`, `exp_step_maps`,
  `circuit_exact_on_reachable` (Glue.lean).  The hypotheses for the actual circuits are numerical (§6.3).
- *Dropping the diagonal group:* `diag` acts first on a basis state, so
  $e^{-i\theta H_{\rm diag}}e_r=e^{-i\theta(H_{\rm diag})_{rr}}e_r$ — a global phase **[Lean]**
  `diagonal_mulVec_single` (Sanity.lean).  The bar is phase-aligned; the frozen family metadata records
  $\varphi=\theta(H_{\rm diag})_{rr}$ as `global_phase_vs_target`; the reviewer measured the predicted phase to
  $2.8\times10^{-14}$ rad (reviews/001 §3.2).

**Decision rule.**  Every proposal runs in both contracts; the loop keeps the best per (reference, term) for class B
and per term for class A.

**Effect.**  2x4 class B v2: 580–763 ZZ against class A 1 492; per-term class-B means are a fraction of class A for
hops (e.g. hop0 10.9 vs 130) but not for plaquettes (plaq1 154.7 vs 202, plaq2 95.2 vs 96)
(`data/report004_tables.json` `per_term_2x4`).

**The input contract is binding** — see §9.

### (j) Peephole and CNOT-run resynthesis

**Purpose.**  Clean up across term boundaries.

- *Peephole* (`src/c2x4/peephole.py:optimise`, `cancel_cx`, `merge_1q`): cancel identical CX pairs across gates that
  commute with them — R1 disjoint qubits **[Lean]** `kron_disjoint_comm`; R2 diagonal gates not on the target
  `cx_comm_diagonal_of_indep`; R3 CNOTs where neither control is the other's target `cx_comm_cx`; R4 X-type gates on the
  target `cx_comm_flip_target`; C1 ${\rm CX}^2=1$ `cx_involutive` — and merge equal-axis one-qubit rotations.  Gain
  about 4–5 % (report 003 §2.4.8).
- *CNOT-run resynthesis* (`resynth_cx_runs`): replace every maximal run of consecutive CX gates by a shorter circuit
  with the same permutation (Gaussian elimination on $A$ and on $A^T$ mirrored); equality checked exhaustively on all
  $2^{\lvert Q\rvert}$ labels (`_same_permutation`) and **[Lean]** `perm_eq_of_fun_eq` (Conj.lean).  On the frozen v1
  circuits it removes 13–14 (class A) and 2–11 (class B) CX per circuit (`data/cxr_gain_v1.json`).
- Finishing pass `pp2` = peephole → resynthesis → peephole (`src/c2x4/family.py:finish`).  It is structural, so the
  skeleton stays $k$-independent.

### (k) Native conversion

**Purpose.**  Count and check what the device would run.

- Run in the isolated venv `~/.local/share/su2qc-quantinuum/venv/bin/python` (never in the `coding` conda env):
  `scripts/native_family.py --family <name>`.  It uses the package's `ir_to_pytket` → `compile_native("H2-2",
  optimisation_level=0)` → `native_counts`, the conversion proof Q1L `local_equivalence_35a(..., structured=True)`
  (two-qubit skeleton, one-qubit segments, rounding bound $B$), and `clean_shot_fraction` with $n_{1q}$ = PhasedX and
  $n_m$ = number of qubits.
- **Workaround:** the package converter has no `cz`; rewrite `cz` as `cp(π)` (identical matrix
  ${\rm diag}(1,1,1,-1)$; one ZZPhase either way) before conversion (done in `native_family.py`).
- Level 0 only.  Level 2 removes a few more gates but rewrites them, so Q1L does not apply (§8.2).
- Results: Q1L passes on 75/75 (each 2x4 v2 class) and 44/44 (each 2x3 class), native ZZ = IR two-qubit count,
  rounding bound $B\le1.13\times10^{-13}$ (`data/native_compressed_circuit_llm_2x4_class{A,B}_v2.json`,
  `data/c2x3/native_compressed_circuit_llm_2x3_class{A,B}.json`, field `summary`).

---

## 4. Generalisation guide

The physics behind the two key facts (corner factorisation, vertex factorisation) is gauge invariance: in a basis of
vertex singlets, every term is a product of link operators whose colour indices are contracted at vertices, and by
the Wigner–Eckart theorem each vertex contributes a reduced matrix element.  **That reading is mine and the reviewer
called it plausible but not needed for correctness [heur]**; everything used is tested per instance.  So in another
theory: **test first, construct second.**

### 4.1 U(1) (link bits, no intertwiners)

- Gauss law fixes the electric flux pattern; in a vertex-local encoding there are no multiplicity labels, so corner
  factors are scalars times flips.  For spin-$\tfrac12$ quantum-link models each link is one qubit and the plaquette
  is $U_1U_2U_3^\dagger U_4^\dagger+{\rm h.c.}$, a flip of four bits on the "flippable" pattern: steps (c)+(f) apply
  directly — CX frame + ladder → one multiplexed rotation whose table is the indicator of flippability.  No bright
  frames; no dark flags unless the encoding has redundant states.
- Higher U(1) truncations (link integer $E\in[-\Lambda,\Lambda]$, $\lceil\log_2(2\Lambda+1)\rceil$ qubits): the
  plaquette is a product of four raising/lowering operators; in a Gray-code or binary encoding the raising operator is
  not a single bit flip — first write each link raising as a cyclic shift and test whether, after a per-link frame
  (incrementer), the plaquette becomes a flip of one qubit per link.  If not, treat each link factor as a block
  structure and use the SVD frame of §4.2.
- Fermions/hops: same as here (step g), without intertwiners; JW handling unchanged.

### 4.2 SU(2) at other truncations ($j_{\max}>\tfrac12$)

- Links need more qubits; vertex singlet spaces grow (several intertwiners per vertex).  Corner maps become
  Clebsch–Gordan / $6j$-structured matrices.  Run `factorise` first: if $h_P=\bigotimes_cA_c$ holds, the remaining
  problem is per-corner.
- **General corner frame (not built here; the recipe):** each $A_c$ is bipartite (link quantum numbers change by
  $\pm\tfrac12$).  Take its SVD per block, $A_c=U\,S\,V^T$; a corner frame $W_c$ that maps column/row singular vectors to
  basis strings differing in one chosen qubit turns $A_c$ into $X_{p_a}\otimes{\rm diag}(S)$.  This replaces the
  "pair + one three-state block" rule of `corner_frame` (which raises `NotImplementedError` for block sizes other
  than 2 or 3).  The frame costs a multiplexed basis change per corner; check that it is cheaper than the plain
  synthesis before committing.
- Expect more distinct magnitudes; the pair-ratio regularity ($1/\sqrt2$ here, §3b item 4) becomes ratios of $6j$
  symbols.  Measure the Walsh support of the resulting angle table (step b item 5) before deciding.

### 4.3 SU(3)

- Same logic with SU(3) recoupling: vertex singlets with multiplicity labels; the corner factor is a reduced matrix
  element times a multiplicity-space map.  The dark/bright idea generalises to "the image of the corner map inside a
  multiplicity space": rotate the image onto basis states, flag the kernel.
- Signs: SU(3) phase conventions produce more sign structure; step (d) generalises unchanged (solve over
  $\mathbb F_2$ with costed corrections), but you may need more costed sources (e.g. CCZ on other bit triples).

### 4.4 2D lattices

- Every bulk plaquette has four interior corners (like plaq1 here, the expensive one: 66 468 → 202).  Expect plaq1
  costs everywhere unless the corner multiplexor problem is solved better (the open item of §8.8).
- Vertices with four links: a larger vertex register and more intertwiners; the parity fold generalises (fold all
  other flux bits into the hopping link's copy); bright frames become multi-state (use SVD frames).
- Clean ancillas are more plentiful (every link duplicated; more relations); use them for flags.
- Reachable sets (class B) grow faster with more terms per step, so class B gains less after the first few terms.

### 4.5 Other fermion encodings

- JW: hop sign = parity of the sites in between (here a parity of flux bits, since $n$ odd iff flux parity odd).
  Handle it either inside the multiplexor (mask shift, cheap) or by conjugation (step g.5).
- Other encodings (Bravyi–Kitaev, Verstraete–Cirac, gauge-fermion elimination): test whether
  $H_{\rm hop}=(-1)^{\ell(s)}h_0$ with $\ell$ a linear function of bits that the term does not flip; if yes, fold $\ell$
  into one qubit and conjugate.  If the sign depends on flipped bits, it is part of $h_0$ and the multiplexor carries
  it.

### 4.6 What to test first; signs that the factorisation fails; fallback order

**Test first, in this order:** (1) harness reproduces the baseline; (2) blocks bipartite with zero diagonal; (3)
`factorise` on plaquettes (product residual); (4) `hop_vertex_factors` on hops (sign solve consistent); (5) coefficient
tables in the frame (`hop_coeff_values.py`-style); (6) reachable support per term.

**Signs of failure:**
- `factorise` raises "signs do not factorise over the corners" (the $\mathbb F_2$ sign system is inconsistent) → the
  basis is not vertex-local, or a corner was mis-assigned (`corners_of` uses the lattice's plaquette dictionary
  `c00, c10, c11, c01`).
- Product residual far above round-off → the term is not a product (e.g. a non-local constraint, or a dressed basis
  with global rotations).
- `corner_frame` raises "corner block of size …" → bigger blocks (use the SVD frame of §4.2).
- `frame generator is not X on p_1 (x) diagonal` → the ladder or corner CX choice is wrong for this encoding.
- `lin_block_rounds` raises "non-bipartite block" → angle-linear synthesis impossible for that term; use the generic
  path and accept $k$-dependence (or find a frame that makes it bipartite).

**Fallback order (cheapest effort first, each verified):**
1. package synthesis + sparse-Walsh multiplexors (`full_lin`, `rpkg_lin` for class B);
2. parity/bright vertex frames + sparse Walsh (`framed_lin`, `bframed_lin`);
3. clean ancilla + flags (`cb*`), JW conjugation (`jwc_*`);
4. corner factorisation (`cfg_lin`, `cfg_t_lin`, `cf2_lin`) for plaquettes;
5. MILP supports (`*_milp`) and the finishing pass `pp2`.

---

## 5. Verification protocol (mandatory before claiming a result)

### 5.1 Term checks (A1)

For every term, every $\theta$ used, every proposal that wins: all codeword columns (class A) or all contract columns
(class B) of the candidate's unitary against $e^{-i\theta h}$ (`evaluate.py:verify_term_operator`).  Acceptance in the
loop: deviation $\le10^{-10}$ and per-column leakage $\le10^{-12}$ (`scripts/loop_select.py`, constants `A1_DEV`,
`A1_LEAK`).  Observed v2: worst $1.03\times10^{-14}$ over 130 class-A checks, $8.77\times10^{-15}$ over 975 class-B
checks (`data/eval_arch_it6_operator_pp2_all75_pruned.json` `terms`, `data/eval_arch_it6_input_pp2_terms.json`).

### 5.2 Certified pruned simulation with the rounding term (A2)

`evaluate.py:verify_circuit_pruned` (`scripts/eval_family.py --prune-tau 1e-15`): run the package's exact sparse
simulator; after every 32 gates remove amplitudes with $\lvert a\rvert<\tau=10^{-15}$ and add the removed norm to
$B_{\rm prune}$.  With $v$ the computed and $u$ the exact state,
$$\lVert v-u\rVert_2\le B_{\rm prune}+B_{\rm round}$$
**[Lean]** `telescoping_bound_mirror` (Reach.lean), where each step's error is $\lVert V_i(v_i)-U_i(v_i)\rVert$.  The
rounding term (`evaluate.py:rounding_bound`) adds per non-permutation gate
$$\delta=\gamma\lVert G'\rVert_F+\lVert G'-G\rVert_F,\qquad \gamma=\mu+u+\mu u,\quad u=2^{-53},\quad
\mu=\sqrt2\,\gamma_2=\frac{2\sqrt2\,u}{1-2u},$$
with $\lVert G'-G\rVert_F\le2\cdot2u$ for gates built from an angle (entries within one ulp — libm assumption) and the
measured distance to the unitary polar factor for stored one-qubit `unitary` matrices; X, CX, CZ cost nothing; the sum is
multiplied by $(1+10^{-9})$.  The per-pair algebra is **[Lean]** `pair_round_bound`, `row_sq_le`, `gate_round_sq`,
`entry_err_sq` (Rounding.lean); the constants $u$, $\mu$ (Higham, *Accuracy and Stability of Numerical Algorithms*,
2nd ed., Lemma 3.5) and one-ulp libm are a cited model, **not provable in Lean** (no IEEE-754 semantics in Mathlib).

Pass criterion: $\max\lvert\Delta\psi\rvert_{\rm measured}+B_{\rm prune}+B_{\rm round}<10^{-10}$ and
$(\sqrt{L_{\rm direct}}+B_{\rm prune}+B_{\rm round})^2<10^{-9}$, $L_{\rm direct}$ = weight on non-codeword strings
summed directly.  Size of the terms: largest $B_{\rm round}$ $1.59\times10^{-12}$ (2x4 class A v2), largest
$B_{\rm prune}$ $1.05\times10^{-13}$ (`data/report004_tables.json` `2x4.A_v2`).

### 5.3 Independent Aer statevector check (by a different agent, different engine)

Follow `reviews/001-independent-verification.md` §2 (and its scripts `reviews/001_verify_aer.py`,
`reviews/001_build_circuits.py`):
- build circuits from the proposer's builders with the proposer's cache **bypassed** (redirect every cache path);
- convert IR → qiskit with the reviewer's own converter (refuse multi-qubit `unitary`);
- `AerSimulator(method="statevector", precision="double")`, complex128;
- target computed with the **package's** call (`coarse_states(term_groups(...), basis_vector(ref), dt, k)[k]`, $dt$
  read from `validation/E3.json`), never the proposer's target cache;
- leakage summed directly: $L_{\rm nc}$ on non-codeword strings and $L_{\rm sec}$ on codewords of the other sector;
- check the X-gate prefix equals `prepare(ref)`;
- for class B, check the measured global phase against $\theta(H_{\rm diag})_{rr}$.
The proposer may also run `scripts/verify_aer_family.py` on its frozen families (it uses the loader, the package
target, fusion off by default), but that does not replace an independent agent.  Cost on this laptop: 2x3 (20 qubits)
seconds per circuit (`data/c2x3/aer_*.json` `aer_s`); 2x4 (28 qubits) 750–1 310 s per circuit with fusion on
(`data/aer_compressed_circuit_llm_2x4_*_v2_sample_*.json`).

### 5.4 Class A operator test on random superpositions

Load $\mathrm{Prep}\,\lvert\phi\rangle$ with $\phi$ a random normalised superposition of all sector codewords (complex
Gaussian, fixed seeds, e.g. `numpy.random.default_rng(11)` and `(12)`), compare with
`krylov.apply_groups(groups, phi, k*dt)`.  Reviewer result: 8 class-A runs, $\lVert\Delta\psi\rVert_2\le5.03\times
10^{-14}$; the same test on a class-B circuit gives $\max\lvert\Delta\psi\rvert=2.30\times10^{-2}$ — the expected
failure that defines class B (reviews/001 §3.1).

### 5.5 Bar and leakage definitions

- $\max_s\lvert\psi_se^{-i\varphi}-t_s\rvert<10^{-10}$, $\varphi=\arg\langle t\vert\psi\rangle$ (package bar).
- Leakage $<10^{-9}$: weight outside the sector's codewords, **summed directly** over strings, never as
  $1-\sum_{\rm codewords}\lvert\psi\rvert^2$ (§8.5).

### 5.6 What NOT to do

- **Do not use the exact (unpruned) sparse simulator on compressed circuits.**  Frames that cancel exactly leave
  round-off residues ($\sim10^{-17}$) on non-codeword strings; later don't-care slots scatter them.  Observed: one
  class-B circuit reached 4 184 564 strings (33 s), `B0_ref345_k4` 33 472 800 strings (201 s), a class-A circuit grew
  to $2^{16}$ strings within 2 000 gates and did not finish; the leakage itself was $\le1.6\times10^{-30}$
  (report 003 §2.3.6).  Use the certified pruned simulation.  Cross-check: exact vs pruned on three class-B circuits
  agree ($2.37$ vs $2.39$, $2.33$ vs $2.36$, $1.24$ vs $1.19\times10^{-14}$; `data/eval_arch_it5_input_pp_exact_crosscheck.json`).
- Do not judge a circuit by its counts alone, never load the classical output state into a construction (class B uses
  the *graph*, not amplitudes), never change the term order of non-commuting terms, never type numbers into reports
  by hand.
- Do not simulate the native (PhasedX/ZZPhase) circuit with the pruned sparse simulator: native one-qubit gates open
  genuine superpositions on many qubits and pruning cannot help (a first attempt timed out at 900 s and 4.3 GB;
  report 003 §2.3.7).  Native correctness comes from Q1L.

---

## 6. Lean workflow

### 6.1 Setup

- Toolchain `leanprover/lean4:v4.35.0` (`lean/lean-toolchain`), Mathlib tag `v4.35.0` (`lean/lakefile.toml`),
  installed with `elan` in `~/.elan`.
- Build: `export PATH=$HOME/.elan/bin:$PATH && cd 2x4_compression_using_ai_v1/lean && lake build`
  (≈30–90 s once Mathlib is cached; `data/c4_lean_build.log`).  One file: `lake env lean Compress2x4/<File>.lean`.
- Acceptance rule: `lake build` succeeds; `grep -rn "sorry\|admit" lean/Compress2x4/` is empty; every
  `#print axioms` line lists only `propext`, `Classical.choice`, `Quot.sound` (or a subset).  Last build: "Build completed
  successfully (9059 jobs)", 63 `#print axioms` lines, all within that set (`data/c4_lean_build.log`).
- API tips: `open scoped Kronecker` for `⊗ₖ`; `(open scoped Norms.Operator in h.exp_left)` turns `Commute M P` into
  `Commute (exp M) P`; matrix exponential is `NormedSpace.exp` written `exp` after `open NormedSpace`;
  `Matrix.exp_conj`, `Matrix.reindex_apply`, `Matrix.submatrix_mulVec_equiv`, `blockDiagonal_mul`;
  `set_option backward.isDefEq.respectTransparency false in` before generic Banach-algebra lemmas on matrices.

### 6.2 What exists (file — statements — content in words)

| file | statements | content |
|---|---|---|
| `Sanity.lean` | `CZ_mul_CZ`, `RZZ_mul_RZZ`, `RZZ_comm`, `diagonal_mulVec_single`, `kron_disjoint_comm`, `agree_on_reachable` | setup checks; a diagonal acting first on a basis vector is a phase; disjoint-support gates commute; one-step reachability agreement |
| `Exp.lean` | `exp_intertwine`, `exp_agree_of_intertwine`, `exp_agree_on_invariant`, `exp_agree_mulVec`, `exp_conj_frame`, `smul_intertwine` | exponentials of generators that agree on an invariant subspace agree there (don't-care slots); exponential of a conjugated generator |
| `Bits.lean` | `perm_*`, `perm_conj_diagonal`, `xorLinear_trans`, `xorLinear_conj_flip`, `cxFun_cxFun`, `cx_involutive`, `cx_xorLinear`, `ccz_phase`, `ccz_circuit`, … (14) | bit-vector model: CNOT networks as xor-linear permutations; ladder turns a multi-bit flip into one flip; CCZ from 3 CP + 2 CX |
| `Peephole.lean` | `cx_comm_diagonal_of_indep`, `cxFun_comm`, `cx_comm_cx`, `cx_comm_flip_target`, `cx_comm_lincomb_flip_target`, … (8) | the peephole commutation rules R2–R4 |
| `Reach.lean` | `agree_on_reachable_n`, `telescoping_bound`, `telescoping_bound_mirror`, `ry_add_two_pi`, `relphase_cancel` | n-step reachable-set induction; error budgets; free sign of a bright rotation; relative-phase compute/uncompute |
| `Budget.lean` | `dropped_part_bound`, `normSq_sub_le`, `tv_le_norm_sub` | approximate class bounds; total variation $\le\lVert a-b\rVert$ |
| `Ucr.lean` | `xt_comm_zd`, `cx_conj_zd_target`, `cx_conj_xt_target`, `cx_conj_yt`, `exp_conj_cx_yt`, `exp_sum_commuting`, … (7) | identities behind the multiplexor walk |
| `Pair.lean` | `exp_xt_diag`, `diag_comm_xt`, `ht_diag_ht`, `walk_factors_comm`, … (13) | frame generator $X_t\,{\rm diag}(D)$ → multiplexed rotation |
| `Glue.lean` | `kron_one_mulVec_apply`, `kron_agree_of_support`, `reindex_kron_agree`, `commute_proj_of_block`, `projOn_mulVec_of_support`, `exp_mulVec_supported`, `exp_step_maps`, `circuit_exact_on_reachable`, `single_supported` | local exactness on touched blocks ⇒ agreement of $W\otimes1$ on the span of reachable states; reachability map; circuit-level induction |
| `Rounding.lean` | `pair_round_bound`, `row_sq_le`, `gate_round_sq`, `entry_err_sq` | per-gate floating-point bound under the standard model |
| `Conj.lean` | `z_ry_z`, `cz_conj_ucr`, `neg_generator_conj`, `ucr_comm_ctrl_phase`, `perm_eq_of_fun_eq` | JW conjugation; flags cancel around a multiplexor; CX-run resynthesis equality |

### 6.3 Reuse in another project; what remains numerical

All statements are generic (any register size, any index type); copy the folder, rename the namespace, keep
`lakefile.toml`.  **What remains numerical in every project** (the hypotheses the Lean theorems need for actual
circuits): each term's factorisation, each frame generator's form, each Walsh solve, each term's column agreement
(A1), that the dressed-basis term equals $h_{\rm loc}\otimes1$ on codewords (`localize`), the block-diagonality of
each term for the specific reachable sets, the per-term qubit relabelling, each 28/20-qubit circuit (A2), the native
conversion (Q1L), the rounding constants, and the correctness of HiGHS and of numpy/scipy/Aer.  Say so in every report.

---

## 7. Loop and process

### 7.1 The loop (arXiv:2610.22367 style, run by hand)

The paper (Gu, Kemeny, Yelin, Lukin, *Discovering state-of-the-art quantum circuits with large language models*)
separates a **proposer** (writes programs that build circuits) from an **independent evaluator** (checks each
candidate exactly), keeps an **archive** of the best verified candidate, and grows **families of ideas**.  Here the
proposer was me, turn by turn (no automated API loop; owner answer O5).

- **Proposals:** `src/c2x4/proposals.py:PROPOSALS` (label → function, applicable terms, contract
  `operator`/`input`/`both`); term classes are lattice-generic (`hop`, `plaq`, `hop+plaq_small`, `plaq_interior`).
- **One iteration:** `scripts/loop_select.py --label <it> --classes operator,input --proposals a,b,c [--lx L]
  [--refs …] [--merge]`: run every applicable proposal for every term (class A) and every (reference, term) (class B)
  at $\theta=1\cdot dt$ (counts do not depend on $\theta$ once angle-linear), A1-check each, keep the best
  (**score: ZZ count, then two-qubit depth**), write `data/archive_<it>.json` (`{"operator": {term: {candidates,
  best}}, "input": {ref: {twoB, term: {candidates, best, n_contract_states}}}}`).  Failed proposals are recorded with
  their error, never silently dropped.
- **Family:** `arch:<it>:<operator|input>:<pp|pp2>` (`src/c2x4/family.py:family_from_spec`) = the archive's best per
  term in package order + prepare + (class A) diag + finishing pass.
- **Verify all circuits:** `scripts/eval_family.py`; **freeze:** `scripts/freeze_family.py` (refuses on any mismatch).
- **History here:** it1–it5 (report 003 §2.3.5: class A term sum 4 588 → 1 774), it6 (C4: → 1 530), 2x3 `L3_it1`.

### 7.2 Stopping rule

Stop when the certificates (step f) show that the remaining multiplexors are support-optimal in their class and the
remaining headroom needs a new construction, or when the time budget ends (C4 hard stop: planner steps 1–3 +
certificates, or two laptop-days).  Freeze then; never let the pipeline chase a moving family (notes/007 §9).

### 7.3 Time budgets observed (laptop i7-8750H, 6 cores/12 threads, 62 GiB, no usable GPU)

| run | wall | file |
|---|---|---|
| class-A loop, 13 terms, 14 lin/MILP proposals | 916 s | `data/archive_it6a.json` `wall_s` |
| class-B loop, 5 references, 16 proposals | 1 307–1 432 s | `data/archive_it6b{0,1,2}.json` |
| 2x3 class-B loop, 5–6 references | 513–561 s | `data/c2x3/archive_L3_it1i{0,1}.json` |
| verify 75 class-A circuits (pruned) + terms | 528 s | `data/eval_arch_it6_operator_pp2_all75_pruned.json` |
| class-B term checks, 15 refs × 13 terms × 5 θ | 1 298 s | `data/eval_arch_it6_input_pp2_terms.json` |
| MILP certificates, class A / class B | 433 s / 370 s | `data/cert_it6_{operator,input}.json` |
| native conversion + Q1L, 75 class-A v2 | 847 s | `data/native_compressed_circuit_llm_2x4_classA_v2.json` |
| Aer, 44 2x3 class-A circuits | 518 s | `data/c2x3/aer_compressed_circuit_llm_2x3_classA.json` |

### 7.4 Process rules learned the hard way

- **30-minute rule per run.**  Every script has a `--max-wall` guard that stops *starting* new items; split class-B
  loops into reference batches (`--refs`) and merge (`scripts/merge_archives.py`).  Write results after each item if an
  item can take long (the first 28-qubit Aer attempt with two circuits per process would have exceeded the limit
  before writing anything; report 004 §3.2).
- **CPU oversubscription.**  Five loops plus Aer on 12 threads slowed everything (the noise agent's 28-qubit runs hit
  their cap while my loops ran; `noise/reports/003-noise-results.md` §5).  Run at most ~3 heavy jobs at once; give Aer
  `--threads` explicitly; coordinate with other agents on a shared machine.
- **`pkill -f <pattern>` kills your own shell** when the pattern appears in the invoking command line (exit 144); a
  waiter with `pgrep -f` can match itself.  List PIDs with `ps -eo pid,args | grep …` and `kill <pid>` in a separate
  call (report 003 §2.3.9).
- Never install into the shared `coding` env; pytket work in `~/.local/share/su2qc-quantinuum/venv`.
- Every JSON carries git commit, machine, parameters, seed (`src/c2x4/env.py:write_json`); every number in a report
  is read from such a file (`scripts/report004_tables.py` pattern).

---

## 8. Dead ends and pitfalls (with evidence)

1. **The approximate class gives no gain.**  Tolerance fixed in advance ($\varepsilon\le10^{-8}$ in $\ell_2$ per circuit,
   justified by identical SKQD samples, notes/004); at $10^{-8}$ only 0–3 blocks can be dropped (smallest reachable
   plaq1 block amplitude $8.2\times10^{-11}$–$1.7\times10^{-9}$); even at $10^{-6}$ and $10^{-4}$ the ZZ counts stay
   identical (660, 582, 660) because dropping rare blocks never removes a whole label class from a multiplexor
   (`data/approx_tiers.json`, report 003 §2.3.8).  It also reads classical amplitudes (reviews/001 note 4).  Do not
   pursue it.
2. **Native level 2 is unverified.**  It removes 1–5 % of ZZ and 57–62 % of PhasedX (`data/native_it5_*.json`) but
   rewrites gates, so Q1L does not apply; record for information only.
3. **Parity-frame-only hops.**  The vertex parity fold alone barely helped class A (hop3 1 548 → 1 152 IR CX) and
   made restricted hops worse (412 → 466 summed on reference 102) — measured interactively, not archived (report 003
   §2.3.3).  The bright frame (it5) and flags (it6) superseded it.
4. **plaq1 before 238** (report 003 §2.3.4): CF1 2 110 with 11 controls; CF2 first try 356 with 8 controls instead of
   7 — *failure 1*: the package's greedy control reduction dropped a flag and kept its source bits (fixed by
   relabelling bit order so flag sources come first, `mux_relabelled`); *failure 2*: the sign fit used a "free" sign
   flip at a corner with no bright rotation to absorb it (fixed by offering CCZ as a costed correction).  Final CF2: 238
   with 7 controls; later sparse Walsh 220 (it3), MILP 202 (it6).  Also: the first `cfg` put flags only on
   three-state corners and made plaq1 worse (354) because one corner's dark state is an isolated basis state ("has a
   dark state" rule).
5. **The $\sqrt{\text{leakage}}$ bug.**  I first computed the approximate-class $\varepsilon$ from leakage defined as
   $1-\sum_{\rm codewords}\lvert\psi\rvert^2$; that quantity carries the $10^{-14}$ round-off of the norm, and its square
   root reported $\varepsilon=2.3\times10^{-7}$.  Fix: sum the weight on non-codeword strings directly (report 003
   §2.3.8).
6. **The $k$-dependent skeleton** (§3h).  Plus the sign bug in my first angle-linear rounds (singular values instead
   of $D=U^TKV$), caught by a per-block reconstruction test with deviation $\propto\theta$ (report 004 §2.2).
7. **No `cz` in `ir_to_pytket`.**  `ValueError: ir_to_pytket: unsupported IR gate cz`; rewrite as `cp(π)` (§3k).
   Recommendation for the package: add `cz` to the converter.
8. **What did not move:** class B gained only $-1.2\,\%$ from v1 to v2 (plaquettes dominate); the planner's OR'd dark
   flag for plaq1 was evaluated and not built (net $-34+2c_4$ CX with $c_4$ the unknown cost of a 4-input relative-phase
   AND; ≤ 22 CX if $c_4=6$ **[heur]**; report 004 §2.5); plaq1's multiplexor certificate is open (85 used vs 78 lower
   bound).  The planner's targets (class A ≈ 1 000–1 200, class B 350–450, notes/007 §6) were **[heur]** and were not
   reached (1 492 and 580–763).
9. **Slow first sparse-Walsh code.**  An LP over up to $2^{15}$ unknowns with quadratic pruning was stopped; run the LP
   only *after* the package's control reduction (report 003 §2.3.5).

---

## 9. Usage limits (class B) and noise behaviour

**Class B is valid only for: prepare its own reference with X gates, one coarse step, measure in the computational
basis.**  It is **not** valid for: another reference or any superposition input; $r>1$ repetitions of the step;
controlled versions or Hadamard tests; reuse inside a longer circuit.  On a random superposition a class-B circuit is
off by $2.3\times10^{-2}$ (reviews/001 note 1).  Any change of use pattern must switch to class A.

**Under noise** the near-clean statistics are a property of the circuit family and must be **re-measured** for each new
family — in particular the near-clean ratio $r_{\rm nc}=f_{\rm hit}/f_{\rm ideal}(10^{-3})$ of the package's gate CF_traj
(notes/007 §7 item 4).  The noise agent's results (`noise/reports/003-noise-results.md`, Pauli noise models from
published device data, no hardware):
- 2x4 v2 on H2-2 (analytic, all 75 each): $f$ = 0.401 (class B) and 0.136 (class A) (§4).
- 2x4 v1 on H2-2, sampled on the same 12 circuits per class: acceptance 0.592 (B) vs 0.273 (A), pooled $f_{\rm hit}$
  0.558 vs 0.191, $r_{\rm nc}$ 1.08 vs 1.10, TV of the accepted distribution 0.194 vs 0.374 (floors 0.144 / 0.189) (§4).
- 2x3 on H2-2: frozen $f$ 0.0552, acceptance 0.162, $r_{\rm nc}$ 1.28; class A $f$ 0.311, acceptance 0.496, $r_{\rm nc}$
  1.06; class B $f$ 0.59, acceptance 0.732, $r_{\rm nc}$ 1.02 (§4).
- "Under these Pauli models class B shows no sign of handling errors worse than class A: its $r_{\rm nc}$ is not larger
  and its accepted distribution is closer to the ideal one, because it has fewer gates.  (A model with coherent or
  leakage errors could behave differently; those are not modelled.)" (§4, quoted).
- The frozen 2x4 circuits give no clean shots under any published model (H2-2 $f\le4.71\times10^{-41}$) (§4).

---

## 10. Rules for the parallel projects (naming and separation)

The owner's rule here (`notes/008-owner-decisions-C1-C6.md`, quoted): "keep the frozen circuits that have already been
tested separate from Class A and Class B, these will be known as compressed_circuit_llm_2x4_class[A,B] from now on.
I will tell you what to test when …" and "like i said, keep them separate and I will tell you what to use where."

Apply the same in every project:
- Name families `compressed_circuit_llm_<lattice>_class[A,B][_vN]` (e.g. `compressed_circuit_llm_2x3_classA`,
  `compressed_circuit_llm_4x4_classB_v2`); if the project has several gauge groups in one repo, put the group in the
  lattice tag (e.g. `su3_2x2`) — **ask the owner first**, this suggestion is mine.
- Compressed families are **never** substituted into the project's frozen circuits, gates, preregistrations, GPU slots
  or hardware plans until the owner says which to use where and when.  Results go to separate, clearly named files,
  never into the project's own validation/gate JSONs.
- Freeze every family into an immutable file with a content hash and a loader (`src/c2x4/families.py` pattern,
  `notes/009`); a changed family gets a new version name; aliases without a version point to the reviewed version.
- Independent verification by another agent before anyone builds on a family.

---

## 11. Quick-start checklist (zero → verified class A/B families)

1. **Read the project's conventions** (codec, lattice, bit order, term order, $dt$, references, bar).  *Outcome:* the
   §2.2 questions answered in a plan note.
2. **Wrap the project in a `Problem`** (`src/c2x4/problem.py` pattern: model, groups, codewords, references, $dt$,
   `target`, `support`, `local`, `baseline_term_ir`).  *Outcome:* `Problem.target` reproduces the project's exact
   coarse state.
3. **Build the harness** (`evaluate.py`: counts, term check, pruned certified circuit check with rounding).
   *Outcome:* the frozen circuits reproduce their published counts and pass the bar (§3a).
4. **Run the structure tests** (§3b).  *Outcome:* JSON with block structure, factorisation residuals, coefficient
   magnitudes, reachable supports; a decision which constructions apply.
5. **Port the constructions** (`plaqfactor.py`, `hopframe.py`, `reach.py`, `sparsemux.py`, `linsynth.py`,
   `certify.py`, `peephole.py`, `proposals.py`), adapting only the layout helpers (`corners_of`, vertex qubit lists).
   *Outcome:* every proposal passes A1 on one small term.
6. **Turn on the angle-linear synthesis** (`use_linear`).  *Outcome:* identical skeletons for all $k$ on test terms.
7. **Run the loop** for class A (`loop_select.py --classes operator`), then class B in reference batches.
   *Outcome:* archives with the best verified candidate per term.
8. **Assemble and verify all circuits** (`eval_family.py --prune-tau 1e-15 --kmax <k>`; class-B term checks with
   `--terms-only`).  *Outcome:* `n_pass` = number of circuits, `skeleton_k_independent.all = true`.
9. **Certify the multiplexors** (`certify_family.py`).  *Outcome:* the fraction certified optimal and the open
   cases.
10. **Freeze** (`freeze_family.py`) and write the loader note.  *Outcome:* hashed frozen files; tests pass.
11. **Native conversion** (`native_family.py` in the pytket venv).  *Outcome:* Q1L passes; $f$ for information.
12. **Independent check** by another agent (Aer + random-superposition test for class A, §5.3–5.4).  *Outcome:* a
    review with a verdict.
13. **Prove what you introduce in Lean** (§6).  *Outcome:* `lake build` clean, standard axioms only; a table of what is
    proved and what is numerical.
14. **Report** with every number read from a JSON; state the class-B use limit.

---

## 12. Appendix

### 12.1 Code map `src/c2x4/`

| module | functions (one line each) |
|---|---|
| `env.py` | `write_json` (provenance block: commit, machine, parameters, seed, wall time); `git_commit`; `machine`; `archive_path` (2x4 → `data/`, `L3_` → `data/c2x3/`); paths `STUDY`, `DATA`, `CACHE` |
| `problem.py` | `Problem(lx)`: model, `groups`, `names`, `mats`, `E` (codeword embedding), `ints`, `refs`, `dt`; `circuit_ids`, `tag`, `theta`, `target`, `support`, `local`, `baseline_term_ir`, `baseline_circuit`, `diag_index`, `cpath`, `term_names`; `get_problem(lx)` |
| `evaluate.py` | `counts`; `verify_circuit` (exact, do not use on compressed circuits); `term_unitary_columns`; `verify_term_operator`; `verify_circuit_pruned` (certified); `certified_state_check`; `rounding_bound`; constants `BAR_DEV`, `BAR_LEAK`, `U_ROUND`, `GAMMA_PAIR` |
| `plaqfactor.py` | `corners_of`; `factorise`; `corner_blocks`; `corner_frame`; `frame_generator`; `cf1_gates` (CF1); `cf2_gates` (CF2, four interior corners); `cfg_gates` (CFG, general corners, dark/triple flag rules); `f2_solve`; `f2_relations`; `toffoli`; `ccz`; `rtof`; `invert`; `mux_relabelled`; `_rot_item`, `LINEAR` (angle-linear items) |
| `hopframe.py` | `vertex_parity_frame`; `framed_gates` (frame + block synthesis, optional clean ancilla); `hop_vertex_factors`; `vertex_bright_frame`; `_bright_rotations`; `vertex_bright_frame_clean` (clean ancilla from the duplicated link); `jwc_framed_gates` (JW conjugation); `SOLVER_MODE` |
| `reach.py` | `components`; `Reach.before`, `Reach.local_reachable`; `restricted_term_gates`; `contract_states`; `synth_on` (block synthesis on an explicit string list); `exact_trajectory`, `approx_contracts` (approximate class only, dead end) |
| `sparsemux.py` | `walsh_matrix`; `sparse_walsh` (LP + pruning + exact re-solve); `mask_walk` (NN + 2-opt); `walk_cost`; `sw_two_level` (drop-in multiplexor); `use_sparse_mux`; `SOLVER` |
| `linsynth.py` | `LinRot`; `lin_block_rounds`; `_solve_table`; `_flag_variants`; `_flag_gates`; `lin_two_level`; `_as_const_linrot`; `two_level` (dispatcher); `use_linear`; switches `FLAG`, `CONST_LIN`, `CONJ` |
| `certify.py` | `min_walsh_support` (MILP certificate); `cached_min_walsh_support`; `milp_walsh` (MILP as a synthesis option); `M_THETA` |
| `peephole.py` | `commutes_with_cx`; `cancel_cx`; `merge_1q`; `optimise`; `resynth_cx_runs`; `_synth_gauss`; `_same_permutation`; `_cx_matrix` |
| `proposals.py` | `PROPOSALS` registry (pkg, rpkg, cf1, cf2, cfg, cfg_t, *_sw, full_sw, framed_sw, bframed(_sw), *_lin, *_lin_milp, jwc_*, cb*); `applicable`; `register`; wrappers `_lin`, `_jwc`, `_cb` |
| `family.py` | `_cached` (disk cache per builder/term/θ); `proposal_builder`; `archive_builder`; `archive_family`; `family_from_spec`; `circuit` (prepare + diag + terms in package order + finish); `finish` (pp/pp2); `get_reach`; legacy `FAMILIES` |
| `families.py` | loader: `get_family`, `get_family_ir`, `family_header`, `exact_target`, `available_families`, `ir_to_qiskit`, `FAMILY_NAMES`, `ALIASES` (shim `2x4_compression_using_ai_v1/families.py`) |

### 12.2 Scripts `scripts/`

`p2_0_harness_baseline.py` (baseline), `p2_1_structure.py` (factorisation), `p1_reachable_support.py`,
`p1_device_threshold.py`, `planner_bounds_007.py`, `hop_coeff_values.py`, `loop_select.py`, `merge_archives.py`,
`eval_family.py`, `certify_family.py`, `cert_long_plaq1.py`, `freeze_family.py`, `verify_aer_family.py`,
`native_family.py` (pytket venv), `native_check.py` + `dump_finalists.py` (v1 native path), `rounding_v1.py`,
`cxr_gain_v1.py`, `approx_tiers.py` (dead end), `summarise.py`, `report003_tables.py`, `report004_tables.py`.
Tests: `tests/test_evaluate.py`, `tests/test_families.py`, `tests/test_linsynth.py`.

### 12.3 Data files (main)

| file | content |
|---|---|
| `data/families/*.json.gz` | frozen families (hashes in `notes/009`) |
| `data/archive_it{1..6}*.json`, `data/c2x3/archive_L3_it1*.json` | loop archives |
| `data/eval_arch_it{5,6}_*_all75_pruned.json`, `data/c2x3/eval_arch_L3_it1_*_all44_pruned.json` | full verification |
| `data/cert_it6_*.json`, `data/c2x3/cert_L3_it1_*.json` | MILP certificates |
| `data/native_*.json`, `data/c2x3/native_*.json` | native counts, Q1L, $f$ |
| `data/aer_*.json`, `data/c2x3/aer_*.json` | Aer statevector checks |
| `data/rounding_v1.json`, `data/cxr_gain_v1.json`, `data/hop_coefficient_values.json` | evidence for §3 |
| `data/p2_0_harness_baseline.json`, `data/p2_1_structure.json`, `data/p1_*.json`, `data/planner_bounds_007.json`, `data/approx_tiers.json` | baseline, structure, dead ends |
| `data/report004_tables.json` | the tables of report 004 and of §1.2 |
| `data/c4_lean_build.log` | last Lean build |

### 12.4 Exact commands (as run here; run from `2x4_compression_using_ai_v1/`)

```bash
# environment: the shared 'coding' conda env python (qiskit 2.5.2, qiskit-aer 0.17.2, scipy 1.18) for everything
# except pytket; pytket in ~/.local/share/su2qc-quantinuum/venv; Lean via ~/.elan
python scripts/p2_0_harness_baseline.py                       # (a) baseline
python scripts/p2_1_structure.py                              # (b) structure
python scripts/loop_select.py --label it6a --classes operator \
   --proposals bframed_lin,framed_lin,full_lin,jwc_bframed,cfg_lin,cfg_t_lin,cf2_lin,cfg_lin_milp,cf2_lin_milp
python scripts/loop_select.py --label it6 --merge --classes operator --terms hop0,hop1,hop2,hop3,hop4,hop5,hop6,hop7,hop8,hop9 \
   --proposals cb0,cb1,cb0_jwc,cb1_jwc,cb0_milp,cb1_milp,cb0_jwc_milp,cb1_jwc_milp
python scripts/loop_select.py --label it6b0 --classes input --refs 102,16833,11026,6930,3166 \
   --proposals rpkg_lin,cfg_lin,cfg_t_lin,cf2_lin,cfg_lin_milp,cf2_lin_milp,bframed_lin,framed_lin,jwc_bframed,jwc_framed,cb0,cb1,cb0_jwc,cb1_jwc,cb0p,cb1p
python scripts/merge_archives.py --out it6 --operator it6 --inputs it6b0,it6b1,it6b2
python scripts/eval_family.py --family arch:it6:operator:pp2 --circuits all --kmax 5 --prune-tau 1e-15 --label all75_pruned
python scripts/eval_family.py --family arch:it6:input:pp2 --circuits all --kmax 5 --prune-tau 1e-15 --no-terms --label all75_pruned
python scripts/eval_family.py --family arch:it6:input:pp2 --circuits all --kmax 5 --terms-only --label terms
python scripts/certify_family.py --archive it6 --cls operator --time-limit 300
python scripts/freeze_family.py --name compressed_circuit_llm_2x4_classA_v2 --spec arch:it6:operator:pp2 --lx 4 --kmax 5 \
   --verification data/eval_arch_it6_operator_pp2_all75_pruned.json --version v2 --source "..."
~/.local/share/su2qc-quantinuum/venv/bin/python scripts/native_family.py --family compressed_circuit_llm_2x4_classA_v2
python scripts/verify_aer_family.py --family compressed_circuit_llm_2x3_classA --threads 4
# 2x3: the same with --lx 3, labels L3_it1 / L3_it1i0 / L3_it1i1, --kmax 4
export PATH=$HOME/.elan/bin:$PATH; (cd lean && lake build)
python -m pytest -q tests/
```

### 12.5 Package functions imported (read-only)

`skqd.exact.Model`, `mass_default`; `skqd.krylov.apply_groups`, `coarse_states`, `term_groups`, `basis_vector`,
`references`; `skqd.reference_sim.CodewordEmbedding`, `localize`, `term_support`; `skqd.circuits_ir.CircuitFactory`,
`structured_term_gates`, `run_ir`, and the private helpers `_block_rounds`, `_multiplexed_two_level`,
`_reduce_controls`, `_frame_cnot`, `_pack`, `_real_gauge`, `_gauge_gates`, `_bipartition`, `_generic_two_level`,
`_basis_change_to_y`, `_axis_angle`, `_phase_su2`; `skqd.sparse_sim.SparseState`, `apply_ir`, `run_sparse`;
`skqd.quantinuum_native.ir_to_pytket`, `compile_native`, `native_counts`, `local_equivalence_35a`, `pytket_to_ir`;
`skqd.device_req.clean_shot_fraction`.  A new project needs equivalents of these (or copies).

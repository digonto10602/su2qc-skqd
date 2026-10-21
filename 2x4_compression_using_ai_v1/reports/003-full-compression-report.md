# 003 — Full report: compressing the 2x4 SKQD coarse-step circuits from 71 548 to 582–1 740 two-qubit gates

- **Date:** 2026-10-21.  **Author:** genie-opus (Opus 5.5, high effort), study folder `2x4_compression_using_ai_v1/`.
- **Commits:**
  - all code and data quoted here are as of **`6eb4528`** (results);
  - independent review `4b839ba`;
  - planner review `a9cd136`;
  - owner decisions `caceada`;
  - this report: the commit that adds it (`git log -- 2x4_compression_using_ai_v1/reports/003*`).
- **What was in force while the work was done:**
  - plans `notes/001-phase2-plan.md` (acceptance criteria A1–A7) and `notes/003-phase2-iteration-plan-corner-factorisation.md`;
  - tolerance note `notes/004-approximate-class-tolerance.md`;
  - verification-method note `notes/006-certified-pruned-verification.md`.
- **What is in force now:** the owner's naming and separation rule, `notes/008-owner-decisions-C1-C6.md`.
- **Related documents:**
  - `reports/001-phase1-study-and-comparison.md` (phase 1);
  - `reports/002-phase2-compression-results.md` (phase-2 results);
  - `reviews/001-independent-verification.md` and `.json` (reviewer-opus: **CONFIRMED WITH NOTES**);
  - `notes/007-planner-review-ultimate-compression.md` (planner-fable).
- **Status:** this report was written for the owner to read before signing C3–C6.  It contains **no new compression
  work and no new loop iteration**.  The only new script, `scripts/report003_tables.py`, re-reads the archives and
  writes `data/report003_tables.json`.
- **Where the numbers come from:** every number names the JSON that produced it.  Anything marked
  **ESTIMATE / planner arithmetic** is not a computed value.

**Names used throughout** (owner rule, note 008):

| Name | Meaning |
|---|---|
| **the frozen circuits** | the package's tested 2x4 circuits; the structured source was chosen by `validation/QV_2x4_01.json` |
| **`compressed_circuit_llm_2x4_classA`** | operator-exact (internal label `arch:it5:operator:pp`) |
| **`compressed_circuit_llm_2x4_classB`** | exact on its own reference input (internal label `arch:it5:input:pp`) |

The compressed circuits are kept separate.  They are **not** substituted anywhere in the package until the owner says
where and when.

---

## Glossary

Every term is defined at first use in the text as well; this list is for reference.

| Term | Meaning |
|---|---|
| **Qubit** | A two-level quantum memory element. |
| **Gate** | An elementary operation on one or two qubits. |
| **Two-qubit gate / ZZ count** | The number of CX, CZ, controlled-phase or ZZPhase gates.  Each one becomes one Quantinuum `ZZPhase` gate (package rule, prompts/35b R4).  It is the cost that dominates hardware error. |
| **Two-qubit depth** | The longest chain of two-qubit gates when one-qubit gates are counted as free (pytket's `depth_2q`). |
| **Codeword** | A 28-bit string that encodes a physical, gauge-invariant basis state.  There are 37 165 of them. |
| **Leakage** | The probability weight of a state that sits outside the codewords. |
| **Block** | A connected component of a term's matrix on its local codewords.  Inside a block the term mixes states; between blocks it does not. |
| **Multiplexor** (uniformly controlled rotation) | A rotation of one qubit whose angle depends on the values of other "control" qubits. |
| **Walsh–Hadamard (Walsh) spectrum** | The coefficients $a_S$ of the expansion $\theta(c)=\sum_S a_S(-1)^{\lvert S\cap c\rvert}$ of a multiplexor's angle table.  Each nonzero coefficient costs CNOTs. |
| **Frame** (my label) | A cheap change of basis applied before a term and undone after it. |
| **Intertwiner** | The label $\iota$ that distinguishes the two SU(2) singlets of a vertex whose three links all carry $j=\tfrac12$ and which holds one quark. |
| **Bright / dark state** | Of two intertwiner states coupled to the same partner, the bright one is the combination the term reaches; the dark one is the orthogonal combination, which the term annihilates. |
| **Clean ancilla** | A qubit that is $\lvert0\rangle$ on every codeword because its information is stored elsewhere.  It can be used as scratch space and restored. |
| **Relative-phase Toffoli** | A 3-CNOT Toffoli gate that is correct only up to a phase on the control states.  It is used only in compute/uncompute pairs, where the phase cancels. |
| **Peephole pass** | Cancelling or merging adjacent gates that provably commute. |
| **Lean 4 / Mathlib** | A proof assistant and its mathematics library; a statement proved there is checked by the computer. |
| **Clean-shot fraction $f$** | The probability that a shot has no gate or readout error.  The package's gate-only model is $f=(1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{\rm ro})^{n_m}$ (`skqd.device_req.clean_shot_fraction`). |

---

## 1. What was asked

**Phase 1** (2026-10-19, report 001):
- read the two reference documents;
- map the package's 2x4 compilation;
- estimate what an AI-guided compression loop could do;
- set up Lean 4.

**Phase 2** (approved by the owner, note 002):
- build and run the evaluator-guided loop of arXiv:2610.22367 on the 2x4 circuits;
- produce an **exact class** that meets the package bar on each circuit's own state;
- produce an **approximate class** whose tolerance is justified before it is used;
- prove every rewrite identity in Lean 4 and check the full 28-qubit circuits numerically;
- score by ZZ count first, then two-qubit depth;
- never load the classically computed output state.

**This report** (coordinator, on the owner's behalf): one document that lets a physicist reproduce and judge the
whole compression.  It covers the starting point, the papers, what happened step by step including the dead ends,
how the compression works, accuracy (mine and the independent reviewer's), what class B may be used for, limits,
open decisions, and reproduction.

---

## 2. Actions taken

### 2.1 The starting point: what the 2x4 SKQD circuits are

**Lattice and Hamiltonian** (`src/skqd/hamiltonian.py`, `lattice.py`, conventions fixed in `su2.py`):
- **Lattice.** A $2\times4$ ladder with 8 sites, 10 links and 3 plaquettes.  The site index is $x_1L_y+x_2$; links run
  in the $+x$ and $+y$ directions.
- **Gauge field.** SU(2), truncated at link spin $j\le\tfrac12$.  Each link carries one bit.
- **Matter.** Staggered quarks with occupation $n_x\in\{0,1,2\}$.

$$H=-\tfrac12\sum_{l=(x\to y)}\bigl[\eta_l\,\psi^\dagger_{x}U(l)\psi_{y}+{\rm h.c.}\bigr]
+m\sum_x(-1)^{x_1+x_2}n_x+\frac{g^2}{2}\sum_lE_l^2-\frac1{2g^2}\sum_P\bigl(W_P+W_P^\dagger\bigr),$$

with:
- $\eta_l=i$ on x-links and $(-1)^{x_1+x_2}$ on y-links;
- $g^2=4$ and $m=0.75$ (`mass_default(4)`; the values used are recorded in `data/p2_0_harness_baseline.json` parameters).

**Term groups.**  The coarse step uses 14 groups $H_\gamma$, applied in the package's fixed order
(`Terms.groups`, `krylov.apply_groups`, the first group acting first):
- `diag`: $m\cdot$mass $+\tfrac{g^2}2\cdot$electric;
- `hop0`–`hop9`: one per link;
- `plaq0`–`plaq2`: $-(W_P+W_P^\dagger)/(2g^2)$, one per plaquette.

**Codec and qubit layout** (`src/skqd/codec.py`, fixed convention):
- Every vertex owns a contiguous block of qubits.  The block holds the flux bits of the vertex's link ends (link
  index order, $j=\tfrac12\leftrightarrow1$), then a vertex bit $q$.
- **Corner vertices** (two links) have 3 qubits.  If the two flux bits are equal, $q=n/2$; if they differ, $n=1$ and $q=0$.
- **Interior vertices** (three links) have 4 qubits:
  - even flux parity: $q=n/2$;
  - one flux: $n=1$, $q=0$;
  - three fluxes: $n=1$, $q=\iota$ (the intertwiner).
- Widths are $[3,3,4,4,4,4,3,3]$ and offsets $[0,3,6,10,14,18,22,25]$, giving 28 qubits.
- Each link is stored **twice**, once at each end.  This redundancy becomes important in §4.3.
- The **little-endian** convention is used: qubit $k$ is bit $k$ of the basis integer (`reference_sim`).
- There are 37 165 codewords.  The sectors have dimension 12 843 (baryon number $B=0$) and 8 934 ($B=1$).

**Which qubits each term touches** (computed by `reference_sim.term_support`):

| term | support | qubits |
|---|---|---|
| hops | the two end vertices plus the flux bits of the Jordan–Wigner (JW) sites in between | 6–11 |
| `plaq0`, `plaq2` | four corners | 14 |
| `plaq1` | four interior corners (sites 2, 4, 5, 3) | 16 |

**The circuits.**  For each reference basis state $b_0$ (11 at $B=0$, 4 at $B=1$, from `krylov.references`) and each
$k=1,\dots,5$:

$$|\psi_k\rangle=\prod_{\gamma}e^{-i\,k\,dt\,H_\gamma}\,|b_0\rangle ,$$

prepared by X gates on $|0\cdots0\rangle$.  This is **one** first-order Trotter product at angle $\theta=k\,dt$; the
package calls it a *coarse step*.  The time steps are $dt=0.11469820342078263$ ($B=0$) and $0.1303127653995423$ ($B=1$),
read from `data/quantinuum/circuits_2x4/index.json`, which copies `validation/E3.json`.  That gives 60 circuits for
$k=1..4$, plus 15 at $k=5$ for the pipeline's check CV3.

**How the frozen circuits were built** (report 001 §4; package `circuits_ir.structured_term_gates`):
1. **Local generator.**  Each term's matrix is restricted to its qubit support (`localize`), giving the local
   generator $h$ on its local codewords.
2. **Real gauge.**  A diagonal gauge makes $h$ real.
3. **Blocks.**  Each connected block is exponentiated through its singular-value decomposition, as *rounds* of
   two-level rotations: basis change, pair rotations, inverse basis change.
4. **Multiplexors.**  All two-level rotations of one round that share a bit-flip pattern are merged into one
   uniformly controlled $R_y$.  It is written as a *Gray-code chain*, with $2^m$ CNOTs for $m$ controls.
5. **Don't-cares.**  Non-codeword slots are used to drop controls.

The result is the **structured IR-L0** source: 142 288 instructions per circuit (cx 71 544, ry 70 308, one-qubit
unitary 388, p 40, cp 4, x 4; manifest `original_ir_counts`).  "IR" is the package's own gate list.  Two native
versions were then produced:
- **Qiskit opt-3** (IBM's level-3 optimiser, then pytket): **69 676** ZZPhase, two-qubit depth 68 648.  Its source
  missed the bar at $3.5\times10^{-10}$ (`validation/QV_2x4_01.json`).
- **Structured → pytket level 0** (Quantinuum's compiler; level 0 means rebase to native gates only): **71 548**
  ZZPhase, two-qubit depth **70 300**, 210 994 PhasedX.  The *QV_2x4_01* measurement froze this structured source
  (`data/quantinuum/circuits_2x4/*.structured.manifest.json`).

**Per-term cost of the frozen circuits** (IR CX; package `validation/S2_2x4.json data.term_cost`, reproduced by my
harness in `data/p2_0_harness_baseline.json`):

| term | qubits | local codewords | blocks | IR CX | multiplexed rotations | controls (min / median / max) |
|---|---|---|---|---|---|---|
| hop0–hop9 (sum) | 6–11 | 18–340 | 10–188 | 4 018 | 5–22 each | 2–7 |
| plaq0 | 14 | 383 | 194 | 228 | 4 | 5/5/6 |
| **plaq1** | **16** | **1 831** | **811** | **66 468** | **82** | **7/9/11** |
| plaq2 | 14 | 383 | 162 | 806 | 17 | 4/5/7 |
| diag | 28 | — | — | 24 CX + 4 CP | — | — |

**Why `plaq1` was so large.**  The middle plaquette is the only one whose four corners are all interior vertices.
- Its 16-qubit support holds 1 831 local codewords in 811 blocks.
- Several blocks are larger than pairs, because of intertwiner mixing; they need several SVD rounds.
- Each (round × flip pattern) becomes one multiplexor whose angle depends on almost the whole support: median 9
  controls, up to 11.
- A Gray-code multiplexor costs $2^m$ CNOTs, about 512 at the median, and there are 82 of them.

So `plaq1` was 66 468 of the 71 520 term CX, or 92.9 % (report 001).

**The verification bar** (prompts/35b R1, kept by prompts/36).  For each (reference, $k$) the circuit's 28-qubit
state, compared with the package's exact `krylov.coarse_states` (complex128), must satisfy:
- $\max_s|\psi_s e^{-i\varphi}-t_s|<10^{-10}$ after removing the global phase $\varphi$;
- leakage $<10^{-9}$.

The frozen circuits pass at $1.07\times10^{-13}$ (`validation/S2_2x4.json`) and $9.85\times10^{-13}$ native
(`validation/QV_2x4_01.json`).  Their gate-only clean-shot fraction on Quantinuum's H2-2 is $4.18\times10^{-29}$
(`validation/QN_2x4.json`).

### 2.2 The papers

**arXiv:2610.22367** (Gu, Kemeny, Yelin, Lukin, *Discovering state-of-the-art quantum circuits with large language
models*).
- **What it does.** An LLM proposes *Python programs that build circuits*, not gate lists.  An independent evaluator
  checks every candidate exactly on its specification, and invalid candidates are rejected with the reason.  The
  valid ones are kept in an archive over two cost axes (MAP-Elites over Toffoli count and qubit count).  An
  *ideation* stage first creates several distinct algorithm families, which evolve separately and share good ideas.
- **What I took from it:**
  - the separation of *proposer* and *independent evaluator*;
  - programs as candidates;
  - families of ideas;
  - the archive keeping the best verified candidate;
  - two of its three design principles:
    - *conditional routing into a shared kernel*: here, corner frames route every block of a plaquette into one
      rotation;
    - *exploiting what the inputs actually are*: here, the reachable-set restriction.
- **What I did not take:**
  - its third principle, the *failure budget*, which became the approximate class and gave nothing (§2.3.8);
  - Toffoli × qubit costs and measurement-based uncomputation, because these circuits have no ancilla budget and
    are scored by physical two-qubit gates;
  - the automated OpenEvolve loop over the API: per owner answer O5, the proposer was me, turn by turn.
- **Its statistical guarantees** (sampled test inputs) were not needed.  Each of our circuits has a single input,
  so verification is exhaustive and exact.

**The file `2512.22932v2.pdf`, which is arXiv:2408.08292** (Jordan et al., *Optimization by Decoded Quantum
Interferometry*, Nature 646, 831 (2025)).  This is an algorithm paper with no optimisation loop.  Its circuit content
is reversible Berlekamp–Massey decoding, the baseline that the first paper's decoder task improves.
- **It contributed nothing concrete to this compression.**  No technique of it applies to a Trotter product of 14
  exponentials.
- The owner allowed me to use it "if useful" (O1); it was not useful here.
- I did not download arXiv:2512.22932 (Hanada et al., gauge symmetry).  The gauge-structure ideas used here came from
  the package's own term matrices.

### 2.3 Step by step: what actually happened

#### 2.3.1 Phase 1 (2026-10-19, commit `e33e052`, report 001)
- **Reading and mapping.**  I read both papers and mapped the compilation above.
- **Reachable support** (`data/p1_reachable_support.json`).  From one reference basis state, `plaq1` can touch
  344–578 of its 648 non-trivial blocks, and each hop only 0–12 of its blocks.
- **Device threshold** (`data/p1_device_threshold.json`).  On H2-2, $f\ge0.1$ needs at most 2 493–2 741 two-qubit
  gates, a compression of 26–29×.
- **My guess was too pessimistic.**  I estimated "2–3× likely; 10× or more needs `plaq1` structure; 26–29× unlikely".
- **Lean.**  I set up Lean 4 v4.35.0 with Mathlib v4.35.0 and proved six sanity lemmas.

#### 2.3.2 The evaluator harness (P2-0)
The harness lives in `src/c2x4/problem.py` and `evaluate.py` and shares no construction code with any proposal.
- **Counts.**  ZZ count and two-qubit depth are read from the gate list.
- **Term check (A1).**  Index qubits carry a column label, so one exact sparse run yields **every** codeword column
  of a term's unitary.  It is compared with $e^{-i\theta h}$.
- **Circuit check (A2).**  The full 28-qubit state is computed with the package's exact sparse simulator
  `skqd.sparse_sim` and compared against `krylov.apply_groups`.
- **Baseline reproduced exactly** (`data/p2_0_harness_baseline.json`):
  - 71 548 two-qubit gates and two-qubit depth 70 300 on `B0_ref102_k1`, the manifest's numbers;
  - state deviation $4.54\times10^{-14}$;
  - every frozen term, on all codeword columns, to $\le4.1\times10^{-13}$.
- Unit tests: `tests/test_evaluate.py`, 3 passing.

#### 2.3.3 Structure tests (P2-1, `scripts/p2_1_structure.py` → `data/p2_1_structure.json`)
- **Plaquettes factorise over their corners.**  Every plaquette's local generator is, on its local codewords,
  **exactly** a tensor product of four real corner matrices.  The residual is $\le2.6\times10^{-15}$ on every codeword
  column and every one of the $2^k$ rows.
- **Hops factorise over their end vertices.**  Every hop is $T+T^\dagger$ with $T=\eta\,a_x\otimes b_y\otimes s_{\rm JW}$,
  where $s_{\rm JW}$ is the Jordan–Wigner sign.  The fit residual is $\le2.7\times10^{-15}$; $\eta=i$ on x-links and real
  on y-links, agreeing with `lattice.py`.
- **The hop vertex factors are three-level chains** $n=0\to1\to2$ with equal steps, i.e. spin-1 raising operators.
- **A dead end found here.**  A hop vertex frame that only folds the flux parity barely helped in the operator class
  (hop3 went from 1 548 to 1 152 IR CX) and made the restricted hops worse (412 → 466 two-qubit gates summed on
  reference 102, measured interactively and not archived).  It was dropped until iteration 4.

#### 2.3.4 First verified family and the corner-frame constructions (before and inside iteration 1)

**`plaq1` construction trials** (interactive tests; the numbers that survived are archived in `data/archive_it1.json`):

| construction | `plaq1` two-qubit gates | what happened |
|---|---|---|
| frozen | 66 468 | starting point |
| CF1 (corner frames + one multiplexor, 11 controls) | 2 110 | worked first time, all 1 831 columns to $3.4\times10^{-14}$ |
| CF2, first try (clean ancillas + dark-state flags) | 356, 8 controls instead of the expected 7 | **failure 1:** the package's greedy control reduction dropped the flag qubit of corner `c11` and kept its two source bits; fixed by relabelling the bit order |
| CF2, after fix 1 | still 8 controls | **failure 2:** my sign fit allowed a "free" sign flip on `c11`, which has no bright rotation to absorb it |
| CF2, final | **238**, 7 controls | fixed by offering a doubly-controlled Z (3 controlled phases + 2 CX) as a costed sign correction |

**First verified whole-circuit family.**  Family F2a (frozen hops, compressed plaquettes) has **4 616** two-qubit gates,
3 971 two-qubit depth, and passes **60/60** circuits at $\le9.1\times10^{-14}$ (`data/eval_F2a_all60_part{0,1,2}.json`).

**Reachable-set restriction, smoke test.**  Restricting the hops to their reachable blocks gave 982 (B0_ref102_k1) and
894 (B1_ref230_k1), both passing (`data/eval_F12a_smoke.json`).

#### 2.3.5 The loop, iterations 1–5 (`scripts/loop_select.py` → `data/archive_it{1..5}.json`)
Each iteration does the following:
1. Run every applicable proposal program (fourteen in all, listed below) for every (reference, term) in class B and
   every term in class A.
2. Check each candidate on its contract (A1: deviation $\le10^{-10}$, leakage $\le10^{-12}$).
3. Keep the verified candidate with the fewest two-qubit gates, then the smallest depth.

Selection uses $\theta=dt$, because the counts do not depend on $\theta$; every final circuit is re-verified at its own
angle.

**Proposal labels** (mine): `pkg` is the package synthesis; `rpkg` the package synthesis restricted to reachable
blocks; `cf1`, `cf2`, `cfg`, `cfg_t` are corner frames; `_sw` means sparse-Walsh multiplexors; `full_sw` is the package
block synthesis with sparse-Walsh multiplexors; `framed_sw` is the hop parity frame; `bframed(_sw)` is the hop parity
plus bright frame.

| iteration | new proposals | why | class A term sum | class B term sum per reference (min / mean / max) |
|---|---|---|---|---|
| it1 | `pkg`, `rpkg`, `cf1`, `cf2` | baseline, restriction, corner frames | 4 588 | 734 / 888.0 / 1 044 |
| it2 | `cfg`, `cfg_t` | CF2 generalised to corners with only two links (`plaq0`, `plaq2`) | 4 440 | 636 / 762.1 / 934 |
| it3 | `rpkg_sw`, `full_sw`, `cfg_sw`, `cfg_t_sw`, `cf2_sw` | the multiplexors still used full Gray chains despite free slots | 3 074 | 606 / 716.5 / 846 |
| it4 | `framed_sw` | hop parity frame, now with sparse multiplexors | 2 734 | 606 / 715.5 / 844 |
| it5 | `bframed`, `bframed_sw` | hop3 needed 22 multiplexors because of intertwiner-mixed blocks; add the bright rotation | 1 774 | 606 / 713.6 / 828 |

Term sums exclude the diagonal group (`data/summary_it5.json` history).

**Per-term class A, per iteration** (`python scripts/report003_tables.py` → `data/report003_tables.json`):

| term | frozen | it1 | it2 | it3 | it4 | it5 |
|---|---|---|---|---|---|---|
| hop0 | 278 | 278 (pkg) | 278 (pkg) | 178 (full_sw) | 178 (full_sw) | 140 (bframed_sw) |
| hop1 | 54 | 54 | 54 | 52 (full_sw) | 52 | 52 (full_sw) |
| hop2 | 258 | 258 | 258 | 182 (full_sw) | 182 | 110 (bframed_sw) |
| hop3 | 1 548 | 1 548 | 1 548 | 1 068 (full_sw) | 790 (framed_sw) | 256 (bframed_sw) |
| hop4 | 390 | 390 | 390 | 274 | 254 (framed_sw) | 166 (bframed_sw) |
| hop5 | 542 | 542 | 542 | 284 | 268 (framed_sw) | 178 (bframed_sw) |
| hop6 | 260 | 260 | 260 | 184 | 184 | 134 (bframed_sw) |
| hop7 | 390 | 390 | 390 | 274 | 254 (framed_sw) | 166 (bframed_sw) |
| hop8 | 244 | 244 | 244 | 122 | 116 (framed_sw) | 116 (framed_sw) |
| hop9 | 54 | 54 | 54 | 52 | 52 | 52 (full_sw) |
| plaq0 | 228 | 158 (cf1) | 88 (cfg) | 88 | 88 | 88 (cfg) |
| plaq1 | 66 468 | 238 (cf2) | 238 | 220 (cfg_sw) | 220 | 220 (cfg_sw) |
| plaq2 | 806 | 174 (cf1) | 96 (cfg) | 96 | 96 | 96 (cfg) |
| **sum** | **71 520** | **4 588** | **4 440** | **3 074** | **2 734** | **1 774** |

**Per-term class B, mean over the 15 references, per iteration** (same file):

| term | frozen | it1 | it2 | it3 | it4 | it5 |
|---|---|---|---|---|---|---|
| hop0 | 278 | 10.9 | 10.9 | 10.9 | 10.9 | 10.9 |
| hop1 | 54 | 26.4 | 26.4 | 26.4 | 26.4 | 26.4 |
| hop2 | 258 | 29.7 | 29.7 | 27.5 | 27.5 | 27.5 |
| hop3 | 1 548 | 27.5 | 27.5 | 25.5 | 25.5 | 25.5 |
| hop4 | 390 | 81.1 | 81.1 | 73.7 | 73.3 | 72.5 |
| hop5 | 542 | 46.3 | 46.3 | 43.5 | 43.5 | 43.5 |
| hop6 | 260 | 36.7 | 36.7 | 34.3 | 34.3 | 34.3 |
| hop7 | 390 | 86.5 | 86.5 | 75.6 | 75.2 | 74.1 |
| hop8 | 244 | 36.8 | 36.8 | 34.3 | 34.0 | 34.0 |
| hop9 | 54 | 54.0 | 54.0 | 52.0 | 52.0 | 52.0 |
| plaq0 | 228 | 96.1 | 63.2 | 61.2 | 61.2 | 61.2 |
| plaq1 | 66 468 | 182.0 | 167.1 | 155.7 | 155.7 | 155.7 |
| plaq2 | 806 | 174.0 | 96.0 | 96.0 | 96.0 | 96.0 |

**What failed or was discarded during the iterations:**
- **The generalised corner construction overshot at first.**  Its first version of `cfg` put flags only on corners
  with a three-state block.  That made `plaq1` worse (354), because corner `c11`'s dark state is an isolated basis
  state.  Fixed with a "has a dark state" rule; both rules are kept as proposals, since each wins on some references.
- **The first sparse-Walsh code was too slow.**  It ran a linear programme over up to $2^{15}$ unknowns with quadratic
  pruning and was stopped.  It was reworked to run *after* the package's control reduction.
- **The parity-only hop frame lost in class B and won only partly in class A** (it4); the bright frame (it5) superseded it.
- **The bright frame did not help class B.**  The restricted hops were already small.

#### 2.3.6 Full verification and the exact-simulator blow-up (`notes/006`)
- **What went wrong.**  On the compressed circuits the package's exact sparse simulator became slow:
  - one class-B circuit reached **4 184 564** strings and took 33 s;
  - B0_ref345_k4 reached 33 472 800 strings and took 201 s;
  - a class-A circuit grew to $2^{16}$ strings within 2 000 gates and did not finish.
- **The cause is round-off.**  Frames that cancel exactly leave residues of about $10^{-17}$ on non-codeword strings,
  and later don't-care slots scatter them.  There was no accuracy problem: the measured leakage was
  $\le1.6\times10^{-30}$.
- **The fix: a certified pruned simulation** (`evaluate.verify_circuit_pruned`).
  - Every 32 gates, amplitudes with $|a|<10^{-15}$ are removed, and the removed norm is summed as $B_{\rm prune}$.
  - By Lean `telescoping_bound_mirror`, $\lVert v-u\rVert_2\le B_{\rm prune}$, where $v$ is the computed state and $u$ the
    exact state.
  - The pass test uses the certified value: measured deviation $+\,B_{\rm prune}$.
  - Wall time fell from hours to under 1 s per circuit.
- **Cross-check on three class-B circuits:** exact unpruned versus pruned gives $2.37$ vs $2.39$, $2.33$ vs $2.36$, and
  $1.24$ vs $1.19\times10^{-14}$ (`data/eval_arch_it5_input_pp_exact_crosscheck.json`).
- **A first verification attempt was abandoned.**  The iteration-2 family was being verified when iteration 3 made it
  obsolete, so I stopped it on purpose.

#### 2.3.7 Native conversion (`scripts/native_check.py`, isolated venv)
- **Level 0, verified.**  pytket level 0 runs through the package's own `ir_to_pytket` and `compile_native`, and is
  verified by the package's conversion proof Q1L and rounding bound $B$ (§2.5).
- **Native-state simulation was abandoned.**  The PhasedX/ZZPhase form opens *genuine* superpositions on many qubits
  at once, so pruning cannot help.  A first attempt timed out at 900 s and 4.3 GB on one circuit.
- **Level 2 (the dead end): unverified.**  It removes a further 1–5 % of ZZ and 57–62 % of PhasedX
  (`data/native_it5_*.json`), but it rewrites
  gates, so Q1L does not apply and the circuits were not simulated.  It is recorded for information only.

#### 2.3.8 The approximate class (dead end; `notes/004`, `data/approx_tiers.json`)
- **Tolerance, fixed before any circuit was built.**  The tolerance is $\varepsilon:=\min_\alpha\lVert\psi_{\rm approx}-e^{i\alpha}\psi_{\rm exact}\rVert_2\le10^{-8}$ per circuit.
  - **Justification.**  The measured distributions differ in total variation by at most $\varepsilon$ (Lean
    `tv_le_norm_sub`).  By coupling, $N$ shots are identical with probability $\ge1-N\varepsilon$.  The signed plan's
    1 411 324 GPU shots give 0.014 (`validation/CV_2x4_plan.json`).
- **Error budget.**  Blocks are dropped by their weight along the exact trajectory.  The error is bounded by
  $\sum_\gamma 2\lVert\Pi_D\varphi_\gamma\rVert$ (Lean `telescoping_bound`, `dropped_part_bound`).
- **Result: no gain.**
  - At $10^{-8}$ only 0–3 blocks can be dropped: the smallest reachable `plaq1` block amplitude is
    $8.2\times10^{-11}$–$1.7\times10^{-9}$ (`data/p2_1_structure.json block_amplitudes`).
  - At $10^{-6}$ and $10^{-4}$ (information only, not justified) 13–145 blocks are dropped, but the ZZ counts stay
    identical (660, 582, 660).
  - Dropping rare blocks never removes a whole label class from a multiplexor.
- **A bug in my first measurement.**  I computed $\varepsilon$ from "leakage" defined as $1-\sum_{\rm codewords}|\psi|^2$.
  That quantity carries the $10^{-14}$ round-off of the norm, so its square root reported $\varepsilon=2.3\times10^{-7}$.
  I fixed it by summing the weight on non-codeword strings directly.
- **The planner's ruling (note 007 §4 item 5):** stop the approximate class.

#### 2.3.9 Operational incidents (no data lost)
- **`pkill` killed my own shell.**  Several times `pkill -f <pattern>` matched the invoking bash, because the pattern
  was in its own command line.  The shell was killed (exit 144); in one case the approximate-tier run was stopped and
  later re-run.
- **A queue waiter never woke up.**  A waiter using `pgrep -f "all75_pruned"` matched itself and would have waited
  forever; it was killed and the job started by hand.
- **Killing a runner skipped later steps.**  Killing the stuck class-A exact runs also stopped a parent queue script,
  so the native dump and the class-A term checks were started by hand.
- Every JSON quoted in this report comes from a run that completed.

### 2.4 How the compression works (enough to redo it)

#### 2.4.1 Corner factorisation of the plaquettes
On the local codeword space $C$ of a plaquette $P$, the local generator is a product of four corner factors
(`plaqfactor.factorise`).  The fit uses least squares on $\log|h|$ and solves the signs over $\mathbb F_2$; it is then
checked on every column and every row:

$$h_P\big|_C=A_{c_{00}}\otimes A_{c_{10}}\otimes A_{c_{11}}\otimes A_{c_{01}}.$$

- **Physics reading** (mine; the reviewer calls it plausible but not needed for correctness).  The colour indices of
  the Wilson loop are contracted around the corners.  Each corner is an SU(2)-invariant map, so by Wigner–Eckart it is
  a scalar times $\delta_{ij}$.
- **Corner blocks.**  Each corner matrix is block diagonal.
  - Blocks are pairs related by flipping the corner's two plaquette-link bits, plus, at interior corners, one
    three-state block: the $n=1$, all-flux vertex couples to the two intertwiner states.
  - Blocks with equal plaquette-link bits and blocks with unequal bits have opposite symmetry types (symmetric or
    antisymmetric).  Which type goes with which depends on the sign gauge of the fit.
- **Planner's observation** (note 007 §5.2, `data/planner_bounds_007.json`, which genie did not use).  At every corner
  the two pair magnitudes have the ratio $1/\sqrt2$, to within $1\times10^{-10}$.  Hence on non-dark labels

$$\theta(x)=\pm\,\theta_0A\prod_c\bigl(-\tfrac1{\sqrt2}\bigr)^{x_c},\qquad x_c=p_a\oplus p_b\ \text{at corner }c,$$

a product of four one-bit functions with **exactly 16 Walsh masks** and five distinct magnitudes.

**Worked example: corner `c00` of `plaq1`** (site 2; qubits 6, 7, 8, 9 = link 0 (third link), link 3 ($b$),
link 4 ($l$), vertex bit $q$; strings below are written $q\,l\,b\,{\rm third}$).
- **Blocks.**  There are 13 valid corner states and 6 blocks (`data/p2_1_structure.json`):
  - $\{0000,0110\}$, $\{1000,1110\}$: link bits equal, singular value 0.74139;
  - $\{0010,0100\}$, $\{0011,0101\}$, $\{1011,1101\}$: link bits unequal, singular value 0.52424 (ratio 0.70711);
  - the three-state block $0001\leftrightarrow\{0111,1111\}$, singular values $0.74139$ and $0$.  The zero is the dark
    intertwiner state.
- **The frame.**  Apply $\mathrm{CX}(q_7\to q_8)$: $q_8$ now holds $x=b\oplus l$.  The pair $\{0000,0110\}$ becomes
  $\{0000,0010\}$, which differs only in $q_7$.  The plaquette therefore flips only $p_a=q_7$ at this corner.
- **The bright rotation.**  In the three-state block, one rotation of $q_9$ maps the bright combination of
  $\{0111,1111\}$ to a basis state and leaves the dark state alone.

#### 2.4.2 Corner frames, the ladder, and the single rotation
1. **Per corner** $c$: apply $\mathrm{CX}(p_a\to p_b)$ on the two plaquette-link qubits.  For a three-state block
   $s_0\leftrightarrow\{s_1,s_2\}$ with $A s_0=v_1s_1+v_2s_2$, apply the two-level rotation

   $$R=\frac1{\lvert v\rvert}\begin{pmatrix}v_1&v_2\\-v_2&v_1\end{pmatrix}$$

   on $(s_1,s_2)$: bright goes to $s_1$ and dark to $s_2$.  Now $A_c=X_{p_a}\otimes D_c(\ell)$, with $D_c$ diagonal in the
   corner's label bits $\ell$.
2. **Ladder.**  $L=\prod_{c\ne1}\mathrm{CX}(p_1\to p_{a,c})$ gives $L\,(X^{\otimes4})\,L^{-1}=X_{p_1}$ (Lean
   `xorLinear_conj_flip`).  The simultaneous flip of eight link bits becomes the flip of **one** qubit.
3. **One rotation.**  On the occupied strings the frame generator is $X_{p_1}\otimes\mathrm{diag}(F)$, checked entry by
   entry.  Hence

   $$e^{-i\theta X_{p_1}\mathrm{diag}(F)}=H_{p_1}\,\mathrm{diag}\bigl(e^{-i\theta(-1)^{s_{p_1}}F(s)}\bigr)\,H_{p_1}$$

   (Lean `exp_xt_diag`): one multiplexed $R_x(2\theta F)$ on $p_1$.  The term is $\text{frame}^{-1}\cdot\text{rotation}\cdot\text{frame}$
   (Lean `exp_conj_frame`).  Strings outside the occupied set are don't-cares, which is allowed by Lean
   `exp_agree_mulVec`.
4. **Signs.**  Label-dependent signs of $D_c$ are fitted over $\mathbb F_2$, and the cheapest set of corrections is
   chosen among:
   - a free flip of a bright rotation ($R_y(\varphi+2\pi)=-R_y(\varphi)$, Lean `ry_add_two_pi`);
   - $\mathrm{CZ}(c,p_a)$;
   - a doubly-controlled Z built as 3 controlled phases + 2 CX, because
     $\tfrac\pi2\bigl(bc-(a\oplus b)c+ac\bigr)=\pi abc$ (Lean `ccz_phase`, `ccz_circuit`).

#### 2.4.3 Clean ancillas and dark-state flags (CF2 / CFG)
- **Clean ancillas.**  After the ladder, the qubits $p_{a,c}$ for $c\ne1$ hold $p_{a,c}\oplus p_1$, which is a parity of
  the $x$ labels.  CNOTs from the $x$ qubits clear them to $|0\rangle$ on every codeword, and $x_{c_{01}}$ is cleared
  likewise.  This gives up to four clean ancillas, at 6 CX to clear and 6 to restore.
- **Dark-state flags.**  Into these ancillas a relative-phase Toffoli (3 CX) writes the flag $g_c=c_c\wedge q_c$.  The
  dark state of corner $c$ is $(x_c=0,c_c=1,q_c=1)$.  The phase cancels between compute and uncompute (Lean
  `relphase_cancel`).
- **The resulting angle table:**

  $$F(x,g)=\theta\,M(x)\prod_c\bigl(1-\bar x_c\,g_c\bigr),$$

  with 7 controls for `plaq1`, i.e. at most 128 CX.  The frozen `plaq1` used 82 multiplexors with up to 11 controls.

#### 2.4.4 Sparse-Walsh multiplexors (`sparsemux.py`)
A uniformly controlled rotation decomposes as

$$\sum_c|c\rangle\langle c|\otimes R_y(\theta_c)=\prod_S\exp\!\bigl(-\tfrac i2 a_S Z_SY_t\bigr),\qquad \theta_c=\sum_S a_S(-1)^{|S\cap c|},$$

where each factor is $\mathrm{CX}_S\,R_y(a_S)\,\mathrm{CX}_S$.  This uses two Lean lemmas:
- `cx_conj_yt`: a CX from control $i$ to the target maps $Y_t\mapsto Z_iY_t$;
- `exp_sum_commuting` and `walk_factors_comm`: commuting exponentials split.

Consecutive factors share CNOTs, so the cost is the length of a closed walk through the nonzero masks.  The package's
Gray chain walks all $2^m$ masks.

The construction:
1. Apply the package's control reduction.
2. Pick the free slots to minimise $\lVert a\rVert_1$ subject to $W_{\rm fixed}a=\theta_{\rm fixed}$ (a linear programme,
   HiGHS).
3. Prune greedily.
4. Re-solve exactly on the support and accept only if the residual is $\le10^{-12}$.
5. Order the masks by nearest neighbour plus 2-opt.

#### 2.4.5 Hop frames (`hopframe.py`)
- **Factorisation.**  $T=\eta\,a_x\otimes b_y\otimes s_{\rm JW}$.  Each vertex factor is
  $a=\mu(|1\rangle\langle0|\pm|2\rangle\langle1|)$ on each chain of $n$, with equal steps.
- **Parity fold.**  At each end vertex, $L_v\leftarrow L_v\oplus f_1\oplus f_2$ (2 CX), so $L_v=1$ exactly when $n_v$ is
  odd.
- **Bright frame.**  The intertwiner pair reached by a chain is rotated to bright/dark.
- **Remaining blocks.**  The framed generator then has only pairs ($M=\pm1$) and three-state chains ($M=0$), with no
  4- or 6-state blocks.  The package block synthesis, with sparse-Walsh multiplexors, exponentiates it.
- **Effect on hop3:** 22 multiplexors (parity frame only) become **5** (with bright rotation), and the cost goes from
  1 548 to 256.

#### 2.4.6 Reachable-set restriction (class B, `reach.py`)
- **The reachable set.**  Let $S_\gamma$ be the codewords that can carry amplitude before term $\gamma$.  It is the
  union of the connected components of the earlier terms' graphs, reached from the reference.  It is an exact upper
  bound and does not depend on the angle or on any amplitude.
- **The restriction.**  Term $\gamma$ is synthesised exactly on the blocks touched by $S_\gamma$; every other local
  string is a don't-care.
- **Why it is exact on the reference input.**  By induction (Lean `agree_on_reachable_n`) the whole circuit equals the
  exact coarse step on the reference input.  The reviewer notes that the linear-algebra glue of this argument is not
  formalised (§2.5).

#### 2.4.7 Dropping the diagonal group (class B)
The diagonal group acts first, on a basis state:

$$e^{-i\theta H_{\rm diag}}e_r=e^{-i\theta(H_{\rm diag})_{rr}}e_r$$

(Lean `diagonal_mulVec_single`).  It is a global phase, and the bar is phase-aligned.  The reviewer measured the
predicted phase to within $2.8\times10^{-14}$ rad.

#### 2.4.8 Peephole pass (`peephole.py`)
- **CNOT cancellation.**  Identical CNOT pairs cancel when every gate between them commutes with the CNOT:
  - R1: disjoint qubits;
  - R2: diagonal gates that avoid the target;
  - R3: CNOTs where neither control is the other's target;
  - R4: X-type gates on the target;
  - and C1, CX·CX = 1.
  Lean lemmas: `kron_disjoint_comm`, `cx_comm_diagonal_of_indep`, `cx_comm_cx`, `cx_comm_flip_target`, `cx_involutive`.
- **Rotation merging.**  Equal-axis one-qubit rotations are merged.
- **Gain:** about 4–5 %, e.g. 854 → 818 two-qubit gates on B0_ref102_k1 at iteration 1 (interactive test, not
  archived; the archived whole-circuit counts in §2.5 include the pass).

#### 2.4.9 Before and after, per term (it5; class B as min–max over 15 references)

| term | frozen | `compressed_circuit_llm_2x4_classA` | `compressed_circuit_llm_2x4_classB` |
|---|---|---|---|
| hop0 | 278 | 140 | 0–14 |
| hop1 | 54 | 52 | 0–38 |
| hop2 | 258 | 110 | 14–44 |
| hop3 | 1 548 | 256 | 6–44 |
| hop4 | 390 | 166 | 52–112 |
| hop5 | 542 | 178 | 40–58 |
| hop6 | 260 | 134 | 30–44 |
| hop7 | 390 | 166 | 68–108 |
| hop8 | 244 | 116 | 30–56 |
| hop9 | 54 | 52 | 52 |
| plaq0 | 228 | 88 | 54–84 |
| plaq1 | 66 468 | 220 | 152–208 |
| plaq2 | 806 | 96 | 96 |
| diag | 28 | 28 (kept) | 0 (dropped) |

Sources: `data/summary_it5.json`, `data/report003_tables.json`.  The whole-circuit counts in §2.5 are lower than these
sums because of the peephole pass.

### 2.5 Accuracy

**My verification** (all 75 circuits per class; certified pruned method; `data/summary_it5.json`):

| | `..._classB` | `..._classA` | frozen |
|---|---|---|---|
| circuits passing / total | 75 / 75 | 75 / 75 | — |
| ZZ count | 582–800 (mean 683.5) | 1 736–1 740 (mean 1 739.2) | 71 548 |
| ratio vs 71 548 (mean) | 104.7× | 41.1× | 1 |
| two-qubit depth | 292–469 | 1 275–1 280 | 70 300 |
| max measured $\lvert\Delta\psi\rvert$ | $3.14\times10^{-14}$ | $5.84\times10^{-14}$ | $4.54\times10^{-14}$ |
| max **certified** $\lvert\Delta\psi\rvert$ | $1.16\times10^{-13}$ | $1.54\times10^{-13}$ | — |
| max certified leakage | $7.7\times10^{-27}$ | $1.1\times10^{-26}$ | — |
| term checks (A1) | 975, worst $1.05\times10^{-14}$ | 130, worst $1.01\times10^{-14}$ | — |

Files: `data/eval_arch_it5_{input,operator}_pp_all75_pruned.json` and `data/eval_arch_it5_*_terms*.json`.

**Independent verification** (`reviews/001-independent-verification.md`/`.json`, reviewer-opus, verdict **CONFIRMED WITH
NOTES**).
- **Method:**
  - circuits regenerated from genie's builders with genie's cache bypassed;
  - the reviewer's own IR→qiskit converter;
  - **qiskit-aer** dense 28-qubit statevector, complex128;
  - target computed from the package's `coarse_states` with `dt` read from `validation/E3.json`;
  - leakage summed directly: $L_{\rm nc}$ (non-codeword strings) and $L_{\rm sec}$ (codewords of the other sector).
- **Per-run table** (reviewer §3.1).  Deviation is phase-aligned.  The class-A seed rows apply the circuit to a random
  normalised superposition of all sector codewords (seeds 11 and 12):

| run | class | input | ZZ | 2q depth | $\max\lvert\Delta\psi\rvert$ | $\lVert\Delta\psi\rVert_2$ | $L_{\rm nc}+L_{\rm sec}$ | bar |
|---|---|---|---|---|---|---|---|---|
| B0_ref102_k1 | B | own ref | 660 | 349 | 2.80e-14 | 2.89e-14 | 1.2e-31 | PASS |
| B0_ref102_k5 | B | own ref | 660 | 349 | 2.05e-14 | 4.83e-14 | 1.7e-31 | PASS |
| B1_ref230_k1 | B | own ref | 582 | 292 | 2.44e-14 | 2.52e-14 | 1.3e-31 | PASS |
| B1_ref230_k5 | B | own ref | 582 | 292 | 1.73e-14 | 4.30e-14 | 1.9e-31 | PASS |
| B0_ref345_k4 (max ZZ) | B | own ref | 800 | 469 | 1.50e-14 | 2.52e-14 | 4.1e-31 | PASS |
| B0_ref102_k1 | A | own ref | 1740 | 1280 | 4.50e-14 | 4.67e-14 | 4.2e-31 | PASS |
| B0_ref102_k5 | A | own ref | 1738 | 1278 | 2.49e-14 | 6.14e-14 | 5.7e-31 | PASS |
| B1_ref230_k1 | A | own ref | 1740 | 1280 | 2.10e-14 | 2.19e-14 | 4.8e-31 | PASS |
| B1_ref230_k5 | A | own ref | 1740 | 1280 | 1.67e-14 | 4.40e-14 | 5.9e-31 | PASS |
| B0_ref102_k1 | A | seed 11 / 12 | 1740 | 1280 | 1.57e-15 / 1.34e-15 | 5.03e-14 / 5.03e-14 | 4.4e-31 | PASS |
| B0_ref102_k5 | A | seed 11 / 12 | 1738 | 1278 | 1.17e-15 / 1.17e-15 | 4.31e-14 / 4.30e-14 | 1.1e-30 / 1.0e-30 | PASS |
| B1_ref230_k1 | A | seed 11 / 12 | 1740 | 1280 | 7.42e-16 / 7.14e-16 | 2.34e-14 / 2.34e-14 | 4.6e-31 / 4.5e-31 | PASS |
| B1_ref230_k5 | A | seed 11 / 12 | 1740 | 1280 | 9.54e-16 / 9.38e-16 | 2.54e-14 / 2.55e-14 | 1.2e-30 | PASS |
| B0_ref102_k1 (contrast) | B | seed 11 | 660 | 349 | **2.30e-02** | 4.52e-01 | 3.0e-02 | (not claimed) |

- **Counts and $f$.**  The reviewer recounted all 150 rebuilt circuits with 0 mismatches against my JSON, and
  recomputed $f$ (H2-2) as 0.5751 (class B, B1_ref230_k1) and 0.2006 (class A, B0_ref102_k1), identical to mine.
- **Lean.**  `lake build` OK; no `sorry`, `admit`, `axiom`, `native_decide`, `extern` or `unsafe`; standard axioms only.

**The reviewer's seven notes, in substance:**
1. **Class B is not operator-exact.**  On a random superposition its error is $2.3\times10^{-2}$.  It is valid only for
   "prepare own reference, one coarse step, sample".  It is invalid for:
   - repeated steps ($r>1$);
   - Hadamard-test or controlled versions;
   - another reference.
   Any change of use pattern must switch to class A.
2. **"Certified" in note 006 leaves out floating-point rounding.**  $B_{\rm prune}$ sums only the pruned norms, not
   the rounding of each gate (about $10^{-16}$ per gate, about $10^{-13}$ over 3 000 gates).  Not blocking, because the
   unpruned Aer runs give the same $10^{-14}$ level.
3. **The Lean statements are general lemmas, not the specific circuits.**
   - `agree_on_reachable_n` is pointwise agreement on sets.  Three steps are not formalised: the step from "local $W$
     agrees on touched blocks" to "$W\otimes1$ agrees on the span" (linearity and tensoring); the term-specific
     hypotheses; and the reachability map.
   - `exp_intertwine`, `exp_conj_frame` and `exp_xt_diag` are correct general identities.
   - How `telescoping_bound_mirror` is applied to the pruned run is not formalised.
   - `dropped_part_bound` serves only the unused approximate class.
   - Each term's factorisation, frame form, Walsh solve and circuit rests on numerical checks.  Genie states this split
     honestly.
4. **The approximate class reads classical amplitudes** (block weights along the exact trajectory).  That is a
   different kind of input-specificity from class B.  It is not part of the claim and gave no gain; adopting it would
   need a separate review.
5. **Noise is not covered.**  Class B acts arbitrarily on unreachable blocks, so errors are propagated differently.
   Nobody has studied the noisy output distribution of class B versus class A.
6. **Coverage.**  9 own-reference circuits (5 class B including the maximum-ZZ one, 4 class A), 8 class-A operator
   tests and 1 contrast run, out of 150.  The full 150 would take about 22 h.  The other 66 class-B and 71 class-A
   circuits were recounted but not re-simulated.
7. **Assumptions.**
   - The simulated circuits are the ones genie's builders produce at `6eb4528`; genie's own cached pickles were not
     compared directly, but their counts agree on all 150.
   - Aer gate fusion was on; its effect is about $3\times10^{-14}$.

**Native conversion and $f$** (`data/native_it5_{input,operator}.json`; pytket level 0, H2-2 target):
- **Q1L** (the conversion proof of prompts/35a–35b: two-qubit skeleton, per-qubit one-qubit segments, qubit and
  measurement maps) passes on all 8 finalists.
- **Rounding bound** $B\le1.4\times10^{-13}$, which bounds $\lVert U_{\rm native}-U_{\rm IR}\rVert_{\rm op}$.
- **Counts and $f$:**

| finalist | native ZZPhase | two-qubit depth | PhasedX | $f$(H2-2), gate-only | $f$(Helios-1), gate-only |
|---|---|---|---|---|---|
| class B, 4 circuits | 582–800 | 292–469 | 1 564–2 168 | 0.472–0.575 | 0.491–0.594 |
| class A, 4 circuits | 1 738–1 740 | 1 278–1 280 | 4 841–4 847 | 0.201 | 0.216 |
| frozen | 71 548 | 70 300 | 210 994 | $4.18\times10^{-29}$ | — |

- **With the package's memory model** (`devices_20261002.json memory_model`, flagged ESTIMATE by the package; three
  $t_{\rm round}$ scenarios), H2-2 gives:
  - class B: $0.428$–$0.571$;
  - class A: $0.154$–$0.195$.
- **Threshold.**  Both classes are above the signed criterion (mean $f\ge0.1$, worst $\ge0.05$) and below the
  phase-1 threshold of 2 493–2 741 ZZ.
- **Caveats.**  These $f$ values come from the package's model, not from hardware.  H1-1 has only 20 qubits, so the
  28-qubit circuits cannot run on it.

**Proved in Lean versus numerically checked.**  48 statements, `lake build` OK, standard axioms only
(`data/p2_lean_build.log`; table in report 002 §3.6).
- **Proved: general identities**, true for every register size, that back the construction steps:
  - exponential intertwining, restriction and frame conjugation;
  - CNOT-network action on flips and phases;
  - CX·CX = 1;
  - CCZ from controlled phases;
  - the peephole commutation rules;
  - CX mapping $Y_t\to Z_iY_t$, and the commuting-exponential split;
  - the frame generator to multiplexed rotation step (G5);
  - the reachable-set induction (L5);
  - the error budgets (L6, its mirrored form, L6b, L6c).
- **Only numerically checked:**
  - each specific term's factorisation;
  - each frame generator's form;
  - each Walsh solve;
  - each term on its contract (A1);
  - each 28-qubit circuit (A2, by me on all 150 with pruning, by the reviewer on 9 + 8 with Aer);
  - the native conversion.
- **As the reviewer stresses, the Lean statements are general lemmas, not statements about these specific circuits.**

---

## 3. What the result means

- **The headline.**  The two-qubit cost of a 2x4 coarse step falls from **71 548** (the frozen circuits) to
  **582–800** (`compressed_circuit_llm_2x4_classB`) or **1 736–1 740** (`compressed_circuit_llm_2x4_classA`).  Two-qubit
  depth falls from 70 300 to 292–469 and to 1 275–1 280.  Both classes are verified by me on all 75 circuits each and
  independently confirmed by reviewer-opus.
- **The gain is structural.**  Three exact facts about this Hamiltonian do the work:
  - the vertex factorisation of every term;
  - the corner frame that turns a plaquette into one rotation;
  - the small reachable set from a single basis state.
  The LLM loop's role was to propose construction programs and keep the best verified one per term.  Its largest gains
  came from ideas found by structure tests, not from blind search.
- **The hardware consequence comes from the package's model, not from hardware.**  The gate-only $f$ on H2-2 rises
  from $4\times10^{-29}$ to $0.47$–$0.58$ (class B) and $0.20$ (class A).  Per the planner (note 007 §3), the feasibility
  question is answered at these counts; further compression buys shots, not feasibility.

## 4. Problems and assumptions

### 4.1 What `compressed_circuit_llm_2x4_classB` can and cannot be used for
- **Valid use.**  Each circuit is valid only as "prepare its own reference with X gates, apply one coarse step at
  $k\,dt$, sample in the computational basis".  That is the package's 2x4 plan pattern (60 + 15 circuits,
  `validation/CV_2x4_plan.json`).
- **Invalid uses**, where class A must be used instead:
  - repeated steps ($r>1$ repetitions);
  - controlled or Hadamard-test versions;
  - any other input state or another reference.
  The reviewer measured an error of $2.3\times10^{-2}$ on a random input.
- **It drops a global phase.**  That is harmless for sampling and wrong for any interferometric use.
- **Noise behaviour is untested.**  After a gate error, class B's later gates act arbitrarily off the reachable set.
  The near-clean statistics $r_{\rm nc}$ (prompts/28–29) and the estimator $\hat f_{\rm ideal}=f_{\rm hit}/r_{\rm nc}$ **must
  be re-measured** for class B before use on noisy devices (note 007 §7 item 4).
- **Bookkeeping criteria assume a reference-independent gate count**, so class B fails them as written; they need a
  re-ruling, not a weakening (note 007 §7 item 5):
  - CV_2x4_plan A7 (one instruction count per sector);
  - Q0P Q2 (equal ZZ across $k$).  Class B varies by up to 2 within a reference, through peephole merges that depend
    on the angle.
- **Planner's recommendation** (note 007 §7): class B for production, class A as the hardware control.  This is not
  yet signed by the owner, and the in-force rule keeps both separate.

### 4.2 Limits and lower bounds (planner, note 007 §5; `data/planner_bounds_007.json`)
- **"Ultimate" cannot be certified for circuits of this size.**  The rigorous lower bounds are far below the achieved
  counts:

| bound | what it says | gives |
|---|---|---|
| Schmidt-rank growth | the Schmidt rank across the mid-ladder cut is 23–30, so at least $\lceil\log_4 30\rceil$ gates | $\ge3$ two-qubit gates |
| light cone | 27–28 qubits are entangled, and one gate touches two | $\ge14$ |
| per-hop column rank | | $\le1$ per hop |

- **Structural floors within the construction class:**
  - each plaquette multiplexor has an exact 16-mask floor, or 32 with one folded "any dark" flag (genie's `plaq1`
    multiplexor uses about 110);
  - the frames are now the dominant cost.
- **Headroom: ESTIMATE, planner arithmetic, not computed.**  About **1.5–2×** more is available: class A to roughly
  **1 000–1 200**, class B to roughly **350–450** mean.  The changes needed:
  - one folded dark flag in a fifth clean ancilla;
  - an exact minimum Walsh support per multiplexor by MILP (mixed-integer programming), which would also *certify*
    optimality within the class;
  - the JW sign as a CZ-pair conjugation;
  - shared Givens compression CNOTs;
  - cross-term frame merging;
  - interleaving disjoint terms for depth;
  - a strictly $k$-independent skeleton.
- **Going lower would mean loading the output state**, which owner answer O3 excludes.

### 4.3 Open items and the pending decisions (note 008)

**In force now (C1/C2):**
- The frozen circuits stay as they are.
- `compressed_circuit_llm_2x4_classA` and `..._classB` are kept separate and are not substituted anywhere: not in
  prompts/36, the GPU slots, Q0P/QN gates, preregistrations or hardware plans, until the owner says which to use where
  and when.
- Their results stay in separately named files, never in `validation/`.
- The 2x3 analogues will be `compressed_circuit_llm_2x3_classA` / `..._classB`.

**Pending the owner's signature after this report:**
- **C3:** extend to 2x3, kept separate; test with and without noise, all in Qiskit, on CPU or GPU, whichever is
  fastest without errors.
- **C4:** one more genie run, to check whether the circuits compress further.  The planner's step list and targets are
  in note 007 §6.
- **C5:** check circuit accuracy on the laptop, and behaviour under IBM, Quantinuum and IonQ noise models; keep the
  results separate and easily callable.
- **C6:** no Quantinuum access yet; device information to come from public sources until the owner provides access.

**Other open items:**
- the Q2 / A7 re-rulings (§4.1);
- the $r_{\rm nc}$ re-measurement for class B;
- formalising the linear-algebra glue of `agree_on_reachable_n` (reviewer note 3);
- including floating-point rounding in the pruned bound (reviewer note 2);
- verifying native level 2 (dropped per the planner);
- the 2x3 cost estimate of note 007 §8.2: ESTIMATE, HQC (Quantinuum billing units) down 3–10× — to be computed under C3.

### 4.4 Other problems and assumptions
- **The A2 verification method changed** to certified pruned simulation (note 006, §2.3.6), with the bar unchanged.
  The exact unpruned simulator agrees on three circuits; Aer (the reviewer) agrees on 17 runs.
- **Native circuits are verified by Q1L plus the rounding bound only**, as the package's Q0P was before its GPU slot.
- **$f$ values use the package's device table and models unchanged.**  Transport and crosstalk are not modelled.
- **About the loop.**  The proposer was me, turn by turn.  I make no claim about what an automated OpenEvolve loop
  would find.
- **Data stamps.**  The `git_commit` field of most data JSONs reads `13d87c8+dirty` or `3eb1017+dirty`: the study code
  was uncommitted at run time.  That code is exactly what was committed in `6eb4528`.  The reviewer regenerated all 150
  circuits at `6eb4528` with identical counts.

---

## 5. Reproduction

**Environments:**
- **Main computation:** the `coding` conda env, used read-only (Python 3.12.14, numpy 2.5.2, scipy 1.18.0 with HiGHS,
  qiskit 2.5.2, qiskit-aer 0.17.2); nothing was installed into it.
- **Native conversion:** the isolated venv `~/.local/share/su2qc-quantinuum/venv` (Python 3.12.14, pytket 2.18.4,
  qiskit 2.5.2).
- **Lean:** elan in `~/.elan`, toolchain `leanprover/lean4:v4.35.0`, Mathlib tag `v4.35.0` (commit `56a005855ea1`,
  `lean/lake-manifest.json`).
- **Machine:** i7-8750H, 12 threads, 62 GiB, no usable GPU.  Every run stays under the 30-minute rule.

**Commands** (from `2x4_compression_using_ai_v1/`, at commit `6eb4528` or later; `--merge` adds to an archive copied
from the previous iteration):

```bash
# P2-0 harness: reproduces 71 548 / 70 300 (writes data/p2_0_harness_baseline.json, ~8 min)
python scripts/p2_0_harness_baseline.py --circuits 0:0:1
# P2-1 structure tests (data/p2_1_structure.json, ~2 min)
python scripts/p2_1_structure.py
# loop iterations (archives; run the reference sets in chunks of < 30 min)
python scripts/loop_select.py --label it1 --proposals pkg,rpkg,cf1,cf2 [--refs ...] [--merge]
cp data/archive_it1.json data/archive_it2.json
python scripts/loop_select.py --label it2 --proposals cfg,cfg_t --terms plaq0,plaq1,plaq2 --merge
cp data/archive_it2.json data/archive_it3.json
python scripts/loop_select.py --label it3 --proposals rpkg_sw,full_sw,cfg_sw,cfg_t_sw,cf2_sw --merge
cp data/archive_it3.json data/archive_it4.json
python scripts/loop_select.py --label it4 --proposals framed_sw --terms hop0,...,hop9 --merge
cp data/archive_it4.json data/archive_it5.json
python scripts/loop_select.py --label it5 --proposals bframed,bframed_sw --terms hop0,...,hop9 --merge
# full verification, both classes, all 75 circuits (certified pruned, ~1 and ~3 min)
python scripts/eval_family.py --family arch:it5:input:pp    --circuits all --kmax 5 --label all75_pruned --no-terms --prune-tau 1e-15
python scripts/eval_family.py --family arch:it5:operator:pp --circuits all --kmax 5 --label all75_pruned --no-terms --prune-tau 1e-15
# term checks (A1), chunked by reference lists
python scripts/eval_family.py --family arch:it5:input:pp --circuits <twoB:ref:k list> --kmax 5 --label terms_partN --terms-only
# exact unpruned cross-check
python scripts/eval_family.py --family arch:it5:input:pp --circuits 0:102:1,2:230:1,0:345:4 --kmax 5 --label exact_crosscheck --no-terms
# native (isolated venv)
python scripts/dump_finalists.py --family arch:it5:input:pp --circuits 0:102:1,2:230:1,0:345:4,0:1338:5 --label it5_input
~/.local/share/su2qc-quantinuum/venv/bin/python scripts/native_check.py --ir data/cache/finalists_it5_input.pkl --label it5_input --levels 0,2
# approximate class tiers
python scripts/approx_tiers.py --circuits 0:102:1,2:230:1,0:102:4 --budgets 1e-8,1e-6,1e-4
# tables
python scripts/summarise.py --label it5 --history it1,it2,it3,it4,it5
python scripts/report003_tables.py
# Lean
cd lean && lake build          # 48 statements; grep "axioms" in the log; no sorry/admit
# independent review (reviewer-opus): see reviews/001-independent-verification.json "commands"
```

**Key files:**
- code: `src/c2x4/{problem,evaluate,plaqfactor,reach,sparsemux,hopframe,peephole,proposals,family}.py`;
- archives: `data/archive_it1..5.json`;
- verification: `data/eval_arch_it5_*`;
- native: `data/native_it5_*.json`;
- approximate class: `data/approx_tiers.json`;
- structure: `data/p2_1_structure.json`;
- summaries: `data/summary_it5.json`, `data/report003_tables.json`;
- planner bounds: `data/planner_bounds_007.json` (`scripts/planner_bounds_007.py`);
- independent review: `reviews/001-*`.

`data/cache/` (term-circuit and target caches) is gitignored and regenerable.

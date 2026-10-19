# 001 — Phase 1: the two reference documents, the package's 2x4 compilation, and what an AI-guided compression loop could do to it

- Date: 2026-10-19.  Author: genie-opus (Opus 5.5, high effort), study `2x4_compression_using_ai_v1/`.
- Git commit when the numbers were produced: `db0bd79` (master; recorded inside each JSON of `data/`).
- Plan in force: none (phase 1 is set-up and study; the proposed plan is `notes/001-phase2-plan.md`).
- Related: `notes/001-phase2-plan.md`; `data/p1_reachable_support.json`; `data/p1_device_threshold.json`;
  `lean/Compress2x4/Sanity.lean`.  Package files read (never edited): `validation/S2_2x4.json`,
  `validation/Q0P_2x4.json`, `validation/QN_2x4.json`, `validation/QV_2x4_01.json`,
  `data/quantinuum/circuits_2x4/`, `reports/S2_2x4_compilation_and_device_requirement.md`,
  `reports/S2_2x4_planner_analysis_20260930.md`, `prompts/35*.md`, `prompts/36_2x4_full_pipeline.md`,
  `reports/PROJECT_FULL_REPORT_20261015.md`.
- This folder carries no gate status of the package; none of its numbers are package results.

**Terms used throughout (defined once).**
*Qubit* — a two-level quantum memory element.  *Gate* — an elementary operation on one or two qubits.
*Two-qubit gate count* (CX, CZ or ZZPhase, depending on the gate set) — the main cost of a circuit on today's
hardware, because two-qubit gates are the noisiest.  *Depth* — the number of time steps when gates on different
qubits run in parallel.  *Native gate set* — the gates a device executes directly; for Quantinuum trapped-ion
devices: `ZZPhase` (a two-qubit rotation $e^{-i\frac{\pi\alpha}{2} Z\otimes Z}$), `PhasedX` (a one-qubit rotation
about an axis in the x–y plane) and `Rz` (a one-qubit z rotation, applied in software, so not counted as a
gate error).  *IR* — the package's own intermediate gate list (`skqd.circuits_ir`).  *Qiskit opt-3* — IBM's
Qiskit compiler at optimisation level 3, a generic local rewriting compiler.  *pytket* — Quantinuum's compiler
(level 0 = rebase to native gates plus merging of one-qubit gates).  *Codeword* — a 28-bit string that encodes
a physical, gauge-invariant basis state of the SU(2) ladder in the package's codec (37 165 of the $2^{28}$
strings are codewords).  *Trotter step* — the approximation $e^{-i\theta H}\approx\prod_\gamma e^{-i\theta H_\gamma}$
of a time evolution by a product of exponentials of the Hamiltonian's term groups $H_\gamma$.  *Coarse step* —
the package's name for one such product at the angle $\theta = k\,dt$ (one Trotter step per circuit, not $k$
steps).  *Krylov index* $k$ — which of the sampled states $k = 1,\dots,5$ the circuit prepares.
*Uniformly controlled rotation (multiplexor)* — a rotation of one target qubit whose angle depends on the
values of $c$ control qubits; the standard (Gray-code) circuit for it uses $2^c$ CNOTs.  *Clean fraction*
$f$ — the probability that a shot of a circuit suffers no gate or readout error; the package's "gate-only"
model is $f = (1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{ro})^{n_m}$
(`skqd.device_req.clean_shot_fraction`).  *LLM* — large language model.  *Lean 4 / Mathlib* — a proof assistant
and its mathematics library; a statement proved there is checked by the computer.

---

## 1. What was asked

Phase 1 only (no optimisation code, no loop): (1) read both documents in
`~/Documents/QC_Papers/circuit_optimization_through_claude/` completely and summarise them; (2) map the package's
traditional 2x4 compilation with every number's source; (3) compare, name the redundancies a loop could attack,
estimate the reachable compression honestly, state the verification bar and what would make the effort not worth
it; (4) propose a phase-2 build plan; (5) install Lean 4 and Mathlib and prove one sanity lemma; (6) this report.

## 2. Actions taken

1. Read `2610.22367v1.pdf` (46 pages: main text, Methods, Extended Data, Supplementary Information I–V and
   Appendix A) and `2512.22932v2.pdf` (80 pages, all sections and appendices A–C and references), 20 pages per
   read.
2. **Found that the file `2512.22932v2.pdf` does not contain arXiv:2512.22932.**  Its pages carry the arXiv stamp
   "arXiv:2408.08292v5 [quant-ph] 22 Oct 2025": it is Jordan *et al.*, *Optimization by Decoded Quantum
   Interferometry* (Nature 646, 831 (2025)).  The arXiv abstract page of 2512.22932 (fetched 2026-10-19) gives a
   different paper: Hanada, Matsuura, Schäfer, Sun, *Gauge Symmetry in Quantum Simulation* (submitted
   2025-12-28, revised 2026-03-04).  I have read only that abstract, not the paper.  This is owner question O1.
3. Oriented in the package with `graphify query` / `graphify explain` (`structured_term_gates`, `_block_rounds`,
   `coarse_states`, `localize`, `SparseState`), then read only the functions needed and the 2x4 validation files.
4. Wrote and ran two phase-1 diagnostics (measurements, not optimisation code):
   - `scripts/p1_reachable_support.py` → `data/p1_reachable_support.json` (66.7 s on this laptop): for each of
     the 15 references, which codewords and which local blocks of each term the coarse step can touch.
   - `scripts/p1_device_threshold.py` → `data/p1_device_threshold.json` (< 1 s): the two-qubit count at which
     each Quantinuum row of the package reaches $f\ge0.1$ / $0.05$, using the package's own formula and device
     table.  It reproduces the package's baseline values exactly (H2-2: $5.781\times10^{-27}$ opt3,
     $4.184\times10^{-29}$ structured, equal to `validation/QN_2x4.json` / `Q0P_2x4.json`).
5. Installed elan and Lean, created the Lake project `lean/` pinned to Mathlib `v4.35.0`, and proved six small
   lemmas (section 6).
6. Wrote `notes/001-phase2-plan.md` and this report.  Nothing outside the study folder was edited; no CI request,
   no QPU, no push.

## 3. The two documents

### 3.1 arXiv:2610.22367v1 — Gu, Kemeny, Yelin, Lukin, *Discovering state-of-the-art quantum circuits with large language models* (15 Oct 2026)

**Problem.**  Compile classical-function subroutines of fault-tolerant quantum algorithms (decoders, modular
inversion, numerical functions, chemistry SELECT, a lattice-gauge magnetic layer) into reversible circuits
$|x\rangle|y\rangle\mapsto|x\rangle|y\oplus f(x)\rangle$ that are cheap in Toffoli gates $T$ and peak qubits $Q$
(main text p. 1; Methods Eq. (10)).

**The loop** (Fig. 1(a); Methods "Evolutionary search"; Extended Data Fig. 1):
- *What the AI proposes:* Python programs that build a circuit through a small builder interface (allocate/free,
  `ccx`, `cx`, X-basis measurement, conditional `cz`), not gate lists.  An *ideation* stage first asks the LLM
  (Claude Mythos 5, inside OpenEvolve) for up to five distinct algorithm families from the task specification
  alone; each family then evolves separately; good programs are periodically shared between families.
- *What verifies it:* an independent evaluator.  The circuit model is "KICKMIX" (Methods Eqs. (10)–(16)):
  reversible classical gates, diagonal sign gates and destructive X-basis measurements, so a computational-basis
  input can be followed as one bit string plus a sign.  A candidate is correct when, for every input and every
  measurement record, the output, the restored inputs, every ancilla returned to $|0\rangle$ and the phase match
  the specification (Eq. (16)).  Large input domains are sampled: $10^5$, $9\times10^3$ or $2\times10^7$ tests
  per task (Extended Data Table 1).
- *What is scored:* $TQ$-cost $=$ Toffoli count $\times$ peak qubit count (Eq. (22)); any computable objective
  can replace it.
- *How it iterates:* each iteration is a fresh agent session given the task, a parent program, its evaluator
  feedback and a limited archive; it may run drafts, query a classical oracle and delegate to subagents, then
  submits a full program; invalid programs are rejected with the reason; valid ones are kept in a MAP-Elites
  grid over $(T, Q)$ (Methods; Extended Data Fig. 2 shows 94 iterations of one lineage).

**Circuit transformations used.**  Three recurring principles (main text "Design principles"):
(i) *conditional routing* — replace separately controlled branches by cheap controlled swaps into one shared
kernel, $U_b = R_b^{-1}KR_b$ (Eq. (1); Fig. 1(b): $T_{\rm naive}=3n^2+17n-2$ to $T_{\rm routed}=(3n^2+17n-2)/2$);
(ii) *branch decoding* — recover a branch decision from the registers during uncomputation instead of storing
a history (Eqs. (2), (7)–(9); Appendix A, Theorem A.6, Corollaries A.7–A.8);
(iii) a *failure budget* — omit circuitry needed only by rare inputs (Fig. 1(d); SI Table S4).
Task-specific ones: measurement-based uncomputation (Eqs. (11)–(14)), Berlekamp–Massey with a rescaled shared
update (Eqs. (4)–(5), SI Eqs. (33)–(34)), evaluation–interpolation (SI Eq. (46)), dyadic intervals with a shared
local coordinate (SI Eqs. (62)–(64)), Clifford "frames" from the Hamiltonian's spin symmetries that group
Pauli terms in SELECT (SI IV), and, for the non-Abelian lattice gauge task (SI V), a specialised group-element
representation, reuse of partial loop products using cyclicity and inversion of the trace (SI Eq. (86)), and
reading the trace directly instead of a lookup table.

**Mathematical guarantees.**  Proved by hand: the divstep invariants and the decoding rule (Appendix A, Lemma
A.1 – Corollary A.8).  Statistical: if all $k$ sampled tests pass, the failure probability satisfies
$\varepsilon \le 1-\delta^{1/k}\approx\ln(1/\delta)/k$ with confidence $1-\delta$ (Eq. (20)), and the state error
is $\|\Phi_V-\Phi_U\|\le2\sqrt{\varepsilon}$ (Eq. (19)); for the DQI decoders
$|\langle f\rangle_{\rm impl}-\langle f\rangle|\le4\varepsilon\langle f\rangle$ (SI Eq. (25)).  No formal
(machine-checked) proof of any circuit.

**Reported gains** (Table I; Extended Data Table 1; baselines are the authors' reconstructions of published
constructions): Reed–Solomon DQI decoder $(T,Q)=(5.1\times10^6,1938)\to(4.4\times10^5,1837)$, $G_{TQ}=12$;
Hermitian-code decoder vs a naive reversible baseline $(1.0\times10^8,1.9\times10^5)\to(9.3\times10^5,2395)$;
HHL rotation angle $(1.6\times10^4,300)\to(1348,115)$, 32x; Coulomb potential $(6355,252)\to(1140,142)$, 9.9x;
fixed-point Gaussian $(2.4\times10^4,362)\to(1583,139)$, 39x; Fe$_2$S$_2$ alias-SELECT
$(5.5\times10^4,139)\to(1.5\times10^4,126)$, 4.1x; **non-Abelian lattice-gauge magnetic layer**
(group $\Sigma(72\times3)\subset SU(3)$, $4^3$ lattice) $(1.3\times10^6,1927)\to(1.7\times10^5,1859)$, 7.7x,
"exact on the entire domain", $10^5$ tests; prime-field modular inversion $(4.0\times10^6,935)$, no single
baseline.  All counts are fault-tolerant logical resources (Toffolis), not physical NISQ two-qubit gates.
The authors state the limits themselves (p. 8): the specification fixes the computational basis, so
encoding changes are outside the framework, and the task boundary and input distribution encode assumptions
about how the circuit is used.

### 3.2 The file `2512.22932v2.pdf` = arXiv:2408.08292v5 — Jordan *et al.*, *Optimization by Decoded Quantum Interferometry*

**Problem.**  Approximate optimisation (max-LINSAT over $\mathbb{F}_p$, Definition 2.1; optimal polynomial
intersection OPI, Definition 2.2; sparse max-XORSAT, §6) by a quantum algorithm, DQI, that prepares
$|P(f)\rangle=\sum_x P(f(x))|x\rangle$ (Eq. (8)) via a Dicke-state superposition, a phase, the syndrome
$B^Ty$, reversible syndrome decoding to uncompute $y$, and a quantum Fourier transform (Figs. 1, 4;
Eqs. (29)–(36), (53)–(64)).

**Optimisation loop.**  There is none, and no AI: this is an algorithm paper.  Its circuit content is a
reversible Berlekamp–Massey implementation (Algorithm 2) and Qualtran resource estimates (§16, Table 3: e.g.
$RS_{521}$ needs $1.01\times10^8$ Toffolis and 8 850 qubits) — the baseline that 2610.22367's first task
improves.

**Guarantees.**  The semicircle law (Theorem 4.1, Eq. (9)); an exact finite-size quadratic form (Lemma 9.2,
Eqs. (69)–(70)) and its asymptotic eigenvalue (Lemma 9.3); a bound with imperfect decoding (Theorem 10.1,
Eqs. (172)–(173)); information-theoretic limits for classical decoders (Theorem 13.2) and quantum decoders
(Holevo bound, Eqs. (231)–(232)); max-2-XORSAT limit (Theorem 13.4).

**Reported gains** (performance, not circuit cost): OPI at $n/p=1/10$, DQI with Berlekamp–Massey satisfies
$\langle s\rangle/p=1/2+\sqrt{19}/20\simeq0.7179$ vs 0.55 for Prange's algorithm (Fig. 3); at $n/p=1/2$, 0.933
vs 0.75.  Sparse max-XORSAT (31 216 variables, 50 000 constraints): DQI with belief propagation $\ge0.831$
against simulated annealing 0.764 in 8 s and 0.832 after 73 h on 5 cores, and a tailored classical heuristic
0.880 in 7 min (Table 1, §12).

**Relevance to this study:** none of its techniques compresses a Trotter circuit; it is background for the
decoder task of 3.1.  If the owner meant arXiv:2512.22932 (gauge symmetry in quantum simulation), that paper
should be supplied and read before phase 2 (O1).

## 4. The package's traditional 2x4 compilation (every number with its file)

**What the circuit is.**  For one reference basis state $b_0$ and $k\in\{1,\dots,4\}$ (and $k=5$ for the CV3
check of prompts/36 R4) the circuit is
$\;X\text{-gates preparing }b_0,\;\text{then}\;\prod_\gamma e^{-i\,k\,dt\,H_\gamma}$ with the groups in the fixed
order diag (mass + electric), hop0–hop9, plaq0–plaq2 (`src/skqd/krylov.py` docstring; `CircuitFactory.coarse_step`
in `src/skqd/circuits_ir.py`).  One coarse step per circuit at the angle $k\,dt$: the gate skeleton does not
depend on $k$ (prompts/35a R1).  $dt = 0.11469820342078263$ (B=0) and $0.1303127653995423$ (B=1)
(`data/quantinuum/circuits_2x4/index.json`).  28 qubits, codeword widths [3,3,4,4,4,4,3,3], 37 165 codewords,
sector dimensions 12 843 (B=0) / 8 934 (B=1) (`validation/S2_2x4.json data.refs`, as quoted in prompts/36 §0).
Eleven references at B=0 and four at B=1 (`index.json`; 60 circuits at $k=1..4$).

**How each term is built** (`structured_term_gates`, `_block_rounds`, `_multiplexed_two_level`): the term's local
generator on its qubit support is split into connected blocks; a diagonal "real gauge" makes every block real;
each bipartite block is exponentiated through its singular-value decomposition as basis change – pair
rotations – inverse basis change; all two-level rotations of one round and one bit-flip pattern are merged into
one uniformly controlled $R_y$, whose non-codeword slots are don't-cares used to drop controls.  The result is
exact on the term's local codewords (max deviation $3.40\times10^{-14}$ over all 2x4 terms; full report §6.12).

**Per-term cost** (IR CX, $\theta=dt$; `reports/S2_2x4_compilation_and_device_requirement.md` from
`validation/S2_2x4.json data.term_cost`):

| term | qubits | local codewords | blocks | IR CX | multiplexed rotations | controls min/med/max |
|---|---|---|---|---|---|---|
| hop0–hop9 (sum of 10) | 6–11 | 18–340 | 10–188 | 4 018 | 5–22 each | 2–7 |
| plaq0 | 14 | 383 | 194 | 228 | 4 | 5/5/6 |
| **plaq1** | **16** | **1 831** | **811** | **66 468** | **82** | **7/9/11** |
| plaq2 | 14 | 383 | 162 | 806 | 17 | 4/5/7 |
| sum of the 13 terms | | | | 71 520 | | |

So `plaq1` alone is $66\,468/71\,520 = 92.9\,\%$ of the two-qubit cost.  The same table in the package's
"fixed-angle" mode (one angle per flip pattern — cheaper but **not** the exponential, recall at 2x4 never
emulated) gives 12 952 CX for `plaq1` and 16 546 in total.

**IR-L0** (the structured IR as a whole circuit; per coarse step): 142 288 instructions — cx 71 544, ry 70 308,
one-qubit unitary 388, p 40, cp 4, x 4 (manifest `original_ir_counts`; prompts/36 §0).  The difference between
cx 71 544 and the 71 520 of the terms is the diagonal group: 24 CX + 4 CP (arithmetic on those two file values).

**Qiskit opt-3, CZ basis, all-to-all** (`B0_ref0_k1`, S2_2x4 report table): 69 688 CZ, 209 395 one-qubit
gates, depth 272 923, CZ depth 68 653; routed on the FakeFez map 148 726 CZ.

**Quantinuum native, pytket level 0** (`data/quantinuum/circuits_2x4/*.manifest.json`, summarised in
`validation/Q0P_2x4.json data.index.sources`):

| source | circuits built | ZZPhase | PhasedX | Rz | depth | two-qubit depth | HQC per shot |
|---|---|---|---|---|---|---|---|
| opt3 (Qiskit opt-3 transpile, then pytket) | 19 (+4 pure rebase) | 69 676 | 90 272–90 646 | 139 266–139 273 | 205 128–205 159 | 68 648 | 157.46–157.54 |
| structured (exact IR → pytket) | 60 | **71 548** | 210 994–210 995 | 143 140 | 347 827–347 828 | 70 300 | 185.35 |

Qiskit opt-3 removed only $1-69\,676/71\,548 = 2.6\,\%$ of the two-qubit gates (arithmetic on the two counts),
so the IR has little *local* redundancy left that a generic peephole compiler sees.

**Verification bars and what was measured.**
- The bar (prompts/35b R1, kept by prompts/36): the circuit's 28-qubit state against `krylov.coarse_states`,
  $\max|\Delta\psi|<10^{-10}$ after removing the global phase, leakage (weight outside the codewords) $<10^{-9}$,
  **measured** on a full statevector, never replaced by a bound.
- `validation/S2_2x4.json` (PASS 12/12): structured IR $1.07\times10^{-13}$ from the exact state on the laptop's
  exact sparse simulator (191 s); the opt-3 CZ circuit's leakage $1.10\times10^{-12}$ on the A100 (job 59162991);
  its amplitude distance $1.528\times10^{-9}$ (phase-aligned) — above the bar.
- `validation/Q0P_2x4.json` (FAIL by construction, 4/6): the conversion proof Q1L passes on 79/79 built circuits
  (two-qubit angles to $4.4\times10^{-15}$ half-turns, one-qubit frames to $8.04\times10^{-13}$); the rigorous
  rounding bound $B$ is $4.96$–$4.98\times10^{-9}$ (opt3) and $5.76$–$6.71\times10^{-12}$ (structured); the
  state bar Q1 was deferred to the GPU.
- `validation/QN_2x4.json` (PASS 2/2, analytic, nothing sampled): $\log_{10}f_0$ under the E1 scenario between
  $-26.12$ and $-24.39$; gate-only mean $f$ on H2-2 $5.78\times10^{-27}$ (opt3) and $4.18\times10^{-29}$
  (structured).
- **`validation/QV_2x4_01.json` exists now (job 60009475, harvested in commit `c1fc785`) and PASSES 4/4:** native
  circuits $1.48\times10^{-12}$ (opt3) and $9.85\times10^{-13}$ (structured) from the exact state, leakage
  $\le2.2\times10^{-12}$; the structured IR source $4.92\times10^{-13}$ / $4.56\times10^{-13}$; the opt3 source
  circuit $3.50\times10^{-10}$ (misses the bar); S2_2x4's $1.528\times10^{-9}$ reproduced; **frozen source:
  structured.**  So the family a compressed circuit must beat is the structured native one: 71 548 ZZPhase.

**prompts/35, 35a, 35b, 36 in one paragraph.**  35 built and costed native circuits for 2x2, 2x3, 2x4; 35a ruled
that the coarse step is $k$-independent in gate count and that 2x4 is compiled at pytket level 0 only (a
level-2 compile exceeded 1 800 s); 35b kept the $10^{-10}$ bar as a GPU measurement, added the structured
source, and defined slot QV_2x4_01 (now PASS); 36 runs the noiseless 2x4 SKQD pipeline on the GPU from the
IR-L0 family (142 288 instructions per unit, 33.08 s per $k=1$ statevector, the 60-circuit family ≈ 1.38
GPU-hours, *planner arithmetic*) and skips every noisy 2x4 cell because $f\approx4\times10^{-25}$ (R8).

## 5. Comparison: what applies, the redundancies, an honest estimate

### 5.1 What transfers from the paper and what does not

| paper element | transfers? | why |
|---|---|---|
| LLM proposes *circuit-generating programs*, evaluator scores, MAP-Elites archive, family ideation | **yes** | nothing in it is specific to reversible arithmetic; the package already writes circuits as programs over a gate IR |
| independent exact evaluator | **yes, stronger** | each 2x4 circuit has **one** input (its reference basis state), so a single exact statevector run is a complete test — no sampling, no statistical guarantee needed (the paper needs Eqs. (19)–(21) only because its input domain is huge) |
| conditional routing into a shared kernel | **yes, the main lever** | `plaq1` applies separately synthesised rotations to 648 non-trivial blocks that come in few types (10 distinct $|$matrix elements$|$, 8 flip patterns, planner analysis §0); routing blocks to a canonical form and applying one kernel is exactly $U_b=R_b^{-1}KR_b$ |
| reuse of symmetry ("frames", SI IV; trace cyclicity, SI V) | partly | the plaquette operator's raising part plausibly factorises over the four corners (a product of vertex recoupling factors); if so, the 2x2 dedicated corner gate generalises — untested, step P2-1 |
| restriction to the inputs actually received (p. 3, "reachable from the prescribed initialization") | yes, but weak here | computed below: the coarse step reaches most of `plaq1`'s blocks |
| failure budget | only in a restricted form | the bar is an absolute $10^{-10}$ on amplitudes, so "rare inputs" become "blocks reached with amplitude norm $\ll10^{-10}$"; bounded by a telescoping inequality (plan lemma L6); owner decision O2 |
| Toffoli × qubit cost, measurement-based uncomputation, ancilla reuse | **no** | our circuits have no ancillas and no Toffoli cost model; the cost is physical two-qubit gates at fixed 28 qubits |
| changing the encoding | excluded by both | the paper excludes it (p. 8); the package fixes the codec as a convention (CLAUDE.md rule 2) |

### 5.2 Concrete redundancies the loop could attack

1. **Gauge/encoding structure (don't-cares).**  Already partly used: non-codeword slots are free in
   `_multiplexed_two_level`, but `_reduce_controls` only drops a control when the angle table is invariant under
   a *linear* direction.  Choosing the free angles so that the table's Walsh–Hadamard spectrum is sparse
   (phase-polynomial view, item 5) is not used.
2. **Commuting-term grouping.**  Only terms with disjoint supports commute exactly; 35 of 78 hop/plaquette
   pairs are disjoint and the overlap graph is 6-colourable against 13 serial terms (planner analysis §2).
   Reordering commuting terms leaves `coarse_states` unchanged (proved in Lean as `kron_disjoint_comm`) and
   helps depth, not count.  `plaq1` overlaps `plaq0`, `plaq2` and every x-link hop touching an interior corner,
   so it cannot be moved first.  Grouping in the Pauli sense does not apply (the terms are not Pauli strings).
3. **Cancellation across Trotter steps: does not apply.**  Each circuit is one coarse step at angle $k\,dt$
   (prompts/35a R1), so there is no second step to cancel against; only the boundaries between consecutive
   terms (gauge gates $D$, $D^\dagger$ and frame CNOTs) can merge.
4. **Restriction to the physical subspace and the actual input** — computed in `data/p1_reachable_support.json`:
   - The diagonal group acts first on a basis state, so it is a global phase and can be deleted on that input
     (Lean: `diagonal_mulVec_single`): saves the 24 CX + 4 CP of section 4 — 0.04 %.
   - Before `plaq1` the state can be supported on 1 460–5 731 codewords (by reference), which touch **344–578 of
     `plaq1`'s 648 non-trivial blocks** (53–89 %) and 593–1 104 of its 1 831 local codewords.  Each hop term
     sees only 0–12 of its 6–96 non-trivial blocks, but those terms are cheap (4 018 CX for all hops).
   - The final structural support is 3 470–11 300 codewords; at $k=1$, 1 004–2 018 codewords carry probability
     above $10^{-12}$ and 3 360–10 741 above $10^{-24}$.
   So restricting to the reachable states removes at most $1-344/648=47\,\%$ and at least $1-578/648=11\,\%$ of
   `plaq1`'s blocks — **if** the cost fell in proportion (an assumption, ESTIMATE), 1.1–1.8x on the whole circuit.
5. **Phase polynomials.**  Every uniformly controlled $R_y$ is a uniformly controlled $R_z$ conjugated by fixed
   one-qubit gates, i.e. a phase polynomial on its controls; a sparse spectrum (from don't-cares) removes CNOT
   pairs.  Not measured yet (step P2-1).
6. **Template rewriting.**  Qiskit opt-3 found only 2.6 % (section 4) and cost $1.5\times10^{-9}$ in accuracy;
   exact templates (CNOT/CZ cancellation, merging multiplexors with equal target and controls,
   RZZ(a)RZZ(b) = RZZ(a+b)) are safe but small — ESTIMATE ≤ 5 %.
7. **The real one: a different exact synthesis of `plaq1`.**  82 multiplexed rotations with median 9 controls
   ($\approx2^9$ CNOTs each) are what costs 66 468 CX.  Two routes may cut this by one to two orders of
   magnitude: corner factorisation (redundancy 1 + the 2x2 corner gate generalised) and conditional routing into
   canonical block types.  Neither is shown to exist yet; the structure test is cheap (≤ 30 min, step P2-1).

### 5.3 Estimate of the reachable compression

| quantity | traditional (computed) | reachable (label) | basis |
|---|---|---|---|
| ZZ per circuit, frozen native | 71 548 (structured) / 69 676 (opt3) | — | manifests, `QV_2x4_01` chose structured |
| `plaq1` IR CX | 66 468 | 35 000–59 000 with reachable restriction only (**ESTIMATE**) | 344–578 of 648 blocks touched (computed) × cost-proportional-to-blocks (assumption) |
| `plaq1` IR CX | 66 468 | 1 000–20 000 with a new exact synthesis (**ESTIMATE, speculative**) | 8 flip patterns; the inexact fixed-angle mode already needs only 12 952 (computed); a corner-factorised gate would need a few hundred CX if the factorisation holds (untested) |
| hops + plaq0 + plaq2 IR CX | 5 052 | 2 000–5 000 (**ESTIMATE**) | same methods, smaller terms |
| diagonal group | 28 two-qubit | 0 on the reference input (exact; arithmetic on file values) | Lean `diagonal_mulVec_single` |
| whole coarse step, ZZ | 71 548 | **about 25 000 (2.9x) if only restriction + peepholes work; 3 000–25 000 (3–24x) if the new `plaq1` synthesis works (ESTIMATE)** | sum of the rows |
| two-qubit depth | 70 300 (structured) | tracks the count while `plaq1`'s single-target multiplexor chains dominate; reordering disjoint terms cannot shorten a chain (ESTIMATE) | planner analysis §2 |
| needed for $f\ge0.1$, H2-2 (gate only) | — | ≤ 2 493–2 741 ZZ, i.e. **26–29x** (computed) | `data/p1_device_threshold.json`, one-qubit count modelled as ratio × two-qubit count |
| needed for $f\ge0.1$, Helios-1 / H2-1 | — | ≤ 2 604–2 896 / 1 966–2 066 ZZ (computed) | same file; H1-1 has 20 qubits and cannot hold 28 |

My honest reading: a 2–3x gain is likely with low risk; 10x or more needs the `plaq1` structure to cooperate and
is not shown; the 26–29x that would make any Quantinuum device row reach $f=0.1$ (gate errors only, transport
errors not even included) is unlikely.

### 5.4 The verification bar a compressed circuit must meet

For the 2x4 pipeline to use a compressed circuit, the same bar as the frozen family, per circuit:
(a) its state against `krylov.coarse_states` for its own (reference, $k$): $\max|\Delta\psi|<10^{-10}$ after
global-phase removal, leakage $<10^{-9}$, measured on an exact statevector (this study: the package's sparse
simulator on the laptop; adoption: the package's own GPU measurement, as `QV_2x4_01`);
(b) its native conversion: Q1L (i)+(ii) and a rounding bound $B$ well under the bar ($\le10^{-11}$ proposed);
(c) a stated input contract: exact on every codeword (operator level, reusable for every reference and $k$) or
exact only on its reference input (input-specific; then each of the 60 + 15 circuits needs its own
measurement); (d) the term order of `krylov.term_groups` unchanged except for provably commuting swaps — any
other reordering changes the target state and needs the package's recall re-emulation (planner analysis §2, §8).

### 5.5 What would make the effort not worth it

1. **No hardware consequence.**  Below about 26x (section 5.3) no Quantinuum row reaches $f\ge0.1$; IBM Heron
   is further away.  Then the only gain is cheaper GPU emulation of the noiseless pipeline, whose whole
   60-circuit family is ≈ 1.4 GPU-hours (*planner arithmetic*, prompts/36 R6) — not worth a week.
2. **`plaq1` has no exploitable structure.**  If step P2-1 finds no corner factorisation and few repeated block
   types, the reachable gains are the 1.1–1.8x of item 4 plus a few per cent of peepholes.  The plan's
   go/no-go (stop if `plaq1` stays above 20 000 CX) catches this after about 3 days.
3. **A shortcut that changes the question.**  Preparing the classically known output state directly (sparse
   state preparation from `coarse_states`) would pass the bar but is no longer a time-evolution circuit and
   does not scale; I propose to exclude it (O3).  The same caution, weaker, applies to input-specific circuits:
   they use a classical simulation of the circuit's own support, which is possible at 2x4 only because 2x4 is
   classically small.
4. **Exactness costs.**  If the cheaper constructions need numerically resynthesised one-qubit gates, the
   accumulated error may exceed $10^{-10}$ (the opt-3 source missed it at $3.5\times10^{-10}$, `QV_2x4_01`).

## 6. Lean 4 set-up

**Status: working.**  `lake build` of `lean/` succeeds ("Build completed successfully (9049 jobs)", log
`data/p1_lean_build.log`); no `sorry` or `admit` in the project (grep); `#print axioms` shows only `propext`,
`Classical.choice`, `Quot.sound` (and none at all for `agree_on_reachable`).

| item | value |
|---|---|
| elan | 4.2.4 (227caca13 2026-08-25), installed to `~/.elan` with the official `elan-init.sh -y` |
| Lean toolchain | `leanprover/lean4:v4.35.0` (= `stable` on 2026-10-19), commit `eb6cafb7290e8bd5f2937522d8d804f58f02bafc` |
| Lake | 5.0.0-src+eb6cafb |
| Mathlib | tag `v4.35.0`, commit `56a005855ea1` (`lean/lake-manifest.json`); 9 031 prebuilt files from `lake exe cache get` (cache.mathlib.org), nothing compiled from source; `.lake/` is 7.2 GB and gitignored |
| build time | 33 s wall for the first `lake build` (the study's one file plus loading Mathlib) |

Lemmas proved (`lean/Compress2x4/Sanity.lean`), each with the circuit fact it backs:

| lemma | statement | backs |
|---|---|---|
| `CZ_mul_CZ` | $\mathrm{CZ}\cdot\mathrm{CZ}=I_4$ | CZ pair cancellation |
| `RZZ_mul_RZZ` | $R_{ZZ}(a)R_{ZZ}(b)=R_{ZZ}(a+b)$, $R_{ZZ}(\theta)=\mathrm{diag}(e^{-i\theta s_j/2})$, $s=(1,-1,-1,1)$ | merging ZZPhase gates on one pair |
| `RZZ_comm` | $R_{ZZ}(a)R_{ZZ}(b)=R_{ZZ}(b)R_{ZZ}(a)$ | commuting ZZ rotations |
| `diagonal_mulVec_single` | $\mathrm{diag}(d)\,e_i=d_i\,e_i$ | deleting the diagonal term group acting first on the reference basis state |
| `kron_disjoint_comm` | $(A\otimes I)(I\otimes B)=(I\otimes B)(A\otimes I)$ | reordering terms with disjoint qubit supports |
| `agree_on_reachable` | if $V_1=U_1$ on $S_1$, $U_1(S_1)\subseteq S_2$ and $V_2=U_2$ on $S_2$, then $V_2V_1=U_2U_1$ on $S_1$ | restricting a circuit to the states it can receive |

One installation incident, recorded for the owner: the first `elan-init.sh` run downloaded the 594 MB toolchain
archive from `releases.lean-lang.org` at about 0.2 MB/s and was stopped by my 30-minute background limit at
400 MB.  I then downloaded the same archive from the GitHub release and checked it against GitHub's published
digest (sha256 `7289597a…268f6d`, match), but a manual install from that file was refused by the permission
system, so I did not pursue it; the toolchain was installed by `elan toolchain install leanprover/lean4:v4.35.0`
(the official route, about 25 min).  No system package manager and no sudo were used.

## 7. What the result means

- The paper's *method* (LLM-written circuit programs, an exact independent evaluator, an archive over two cost
  axes, separate families) transfers directly, and the evaluator is easier here than in the paper: one input
  per circuit means exhaustive, exact verification.
- The paper's *gains* do not transfer as numbers: they are Toffoli × qubit savings on reversible arithmetic,
  where large classical-algorithm redesigns are possible; our circuits are a fixed product of 14 exponentials
  whose cost is 93 % one term.
- The decisive quantity is whether `plaq1`'s exponential has an exact construction far cheaper than 82
  multiplexors with ~9 controls.  That is a cheap, early, measurable question (P2-1), and the plan stops early if
  the answer is no.
- Even the optimistic outcome (≈ 24x) stays just short of the 26–29x a Quantinuum device row would need for
  $f\ge0.1$ at published gate errors, before transport (memory) errors.

## 8. Problems, assumptions and owner decisions

**Problems found.**
- The PDF named `2512.22932v2.pdf` contains arXiv:2408.08292v5 (DQI); arXiv:2512.22932 itself is a different
  paper (abstract only seen).
- `ci/status.json` and `validation/QV_2x4_01.json` changed during this session (commit `c1fc785`); this report
  uses the harvested file.
- graphify warns that its skill (0.9.74) is newer than the installed package (0.9.53); queries worked.

**Assumptions (mine, labelled).**  Cost proportional to touched blocks (5.2 item 4); one-qubit count ≈ ratio ×
two-qubit count in the device threshold; the speculative `plaq1` range of 5.3.

**Questions the owner must decide before phase 2.**
- O1 Which second paper: the DQI paper in the file, or arXiv:2512.22932 (*Gauge Symmetry in Quantum
  Simulation*)?  If the latter, please add the PDF.
- O2 May the loop use amplitude-budgeted don't-cares (the paper's failure budget, bounded by lemma L6), or only
  exact identities?
- O3 Input contract: operator-level exact circuits only, or also input-specific circuits exact only on their
  reference input?  I propose both as separate classes and to exclude direct state preparation of the output.
- O4 Is the bar on the state (package convention, my proposal) or only on the output distribution (which would
  also allow deleting diagonal gates before measurement)?
- O5 Proposer: genie-opus turn by turn in Claude Code (no API cost, my proposal), or an automated
  OpenEvolve-style loop over the Anthropic API (key handling and cost to be approved)?
- O6 Score: ZZ count (my proposal) with two-qubit depth as the second axis, or the package's gate-only $-\ln f$
  on H2-2, or HQC per shot?
- O7 Is the go/no-go after the `plaq1` loop (stop above 20 000 CX) acceptable?
- O8 If a compressed family passes, should the coordinator take it to the planner for a package proposal (a GPU
  re-measurement slot)?  This study will not request one.
- O9 Lean scope: prove the rewrite identities (plan §4) and check each 28-qubit circuit numerically — agreed?

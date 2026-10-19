# 001 — Phase-2 build plan: an evaluator-guided compression loop for the 2x4 coarse-step circuits

- Date: 2026-10-19.  Author: genie-opus (Opus 5.5, high).  Status: **PROPOSAL — not approved; nothing in
  this plan runs until the owner approves phase 2.**
- Git commit at writing: `db0bd79` (master).  Plan in force: none yet (this is the first plan of the study).
- Inputs: `reports/001-phase1-study-and-comparison.md` (the study, with every number's source),
  `data/p1_reachable_support.json`, `data/p1_device_threshold.json`.
- Rule for every number below: "computed" means it is read from a JSON named next to it; "ESTIMATE" means it is
  my arithmetic or judgement and will be replaced by a computed value when the step that measures it runs.

## 1. What the loop is for

The package's frozen 2x4 family (structured source, chosen by `validation/QV_2x4_01.json` V4) costs 71 548
ZZPhase gates per circuit (computed: `data/quantinuum/circuits_2x4/*.structured.manifest.json`), of which the
middle-plaquette term `plaq1` is 66 468 of the 71 520 IR CX gates of the hopping and plaquette terms (computed:
`reports/S2_2x4_compilation_and_device_requirement.md`, from `validation/S2_2x4.json`).  A Quantinuum device row
of the package reaches a gate-only clean fraction $f \ge 0.1$ only below about 2 500–2 700 two-qubit gates at 28
qubits (computed: `data/p1_device_threshold.json`, H2-2 and Helios-1), i.e. after a compression of 26–29x.  The
loop's job is to find out, with verified circuits, how far an evaluator-guided search (the technique of
arXiv:2610.22367) gets below 71 548, and whether it gets anywhere near that threshold.

## 2. Loop design

### 2.1 Proposer
- **Who.** genie-opus itself, turn by turn inside Claude Code (no API key, no external cost).  An automated
  OpenEvolve-style loop over the Anthropic API is the paper's set-up (arXiv:2610.22367, Methods "Evolutionary
  search") and is listed as an owner option, not the default (question O5 of the report).
- **What it proposes.** Python *programs that generate circuits* for one term (or one coarse step), not gate
  lists — the paper's representation (Methods: "We encode each candidate as Python code that constructs a
  circuit").  Each program may call the package's synthesis primitives read-only (`circuits_ir.ucr_gray`,
  `circuits_ir._multiplexed_two_level`, `circuits_ir._block_rounds`, `reference_sim.localize`) and must emit the
  package IR (`(name, qubits, param)` tuples) so that the package's own simulators can run it.
- **Families** (the paper's ideation stage; each family is evolved separately and the best ideas are shared):
  - F1 *reachable-set restriction*: synthesise each term only on the local blocks the incoming state can touch
    (computed upper bound on the gain for `plaq1`: it touches 344–578 of its 648 non-trivial blocks,
    `data/p1_reachable_support.json`); the other blocks become don't-care slots for the multiplexors.
  - F2 *corner-factorised plaquette / hop gates*: generalise the package's dedicated 2x2 corner plaquette gate
    (`CircuitFactory.plaq_gates`, Gray-code pair rotation) to interior corners, if the structure test of step
    P2-1 shows the plaquette's raising part factorises over the four corners.
  - F3 *conditional routing into canonical blocks* (the paper's first design principle, Eq. (1) and
    $U_b = R_b^{-1} K R_b$): permute each block of a term into a canonical register pattern with cheap controlled
    permutations, apply one shared rotation kernel per block type, permute back.
  - F4 *don't-care multiplexor resynthesis*: choose the angles of the free (non-codeword, non-reachable) slots of
    each uniformly controlled rotation so that its Walsh–Hadamard angle spectrum is sparse; zero spectral
    entries let adjacent CNOTs of the Gray-code chain cancel (phase-polynomial view).
  - F5 *peephole and boundary rewrites*: CNOT pair cancellation, merging of the diagonal gauge gates
    (`circuits_ir._gauge_gates`) between consecutive terms, merging uniformly controlled rotations with equal
    target, axis and control set, removal of the diagonal term group acting first on the reference basis state,
    reordering of terms with disjoint supports only.
  - F6 *amplitude-budgeted don't-cares* (the paper's "failure budget" in its only admissible form here): treat
    as don't-care a block whose incoming amplitude norm is so small that the error it can cause stays inside a
    stated share of the $10^{-10}$ bar (bounded by the telescoping lemma L6 below).  Off by default; owner
    decision O2.

### 2.2 Verifier (deterministic, float64/complex128, never the proposer)
1. **Term level** (operator rewrites, families F2–F5): the gate-S2 term standard — max deviation from
   $\exp(-i\theta h)$ on the term's local codeword space (or, for F1/F6, on the stated restricted subspace)
   $\le 10^{-10}$ and leakage $\le 10^{-12}$, at $\theta = k\,dt$ for $k = 1,\dots,5$ and both sectors' $dt$
   (`data/quantinuum/circuits_2x4/index.json` `dt`), using `circuits_ir.run_ir` on the $2^{|{\rm support}|}$
   local statevector (at most $2^{16}$ amplitudes for `plaq1`).
2. **Circuit level** (every assembled candidate): the package's state bar of prompts/35b R1 — the candidate's
   28-qubit state against `krylov.coarse_states` for its (reference, $k$): $\max|\Delta\psi| < 10^{-10}$ after
   global-phase removal and leakage $< 10^{-9}$, measured with the exact sparse simulator
   `skqd.sparse_sim` (no magnitude threshold; 191 s for the 142 288-gate baseline step on this laptop, computed:
   `validation/S2_2x4.json data.circuits.circuits_4_exact.coarse_steps.B0_ref0_k1.sparse_wall_s`).
3. **Native level** (only for finalists): `skqd.quantinuum_native` in the isolated venv
   `~/.local/share/su2qc-quantinuum`, pytket level 0, the Q1L conversion proof (i) + (ii) and the rounding
   bound $B$ recorded; finalists need $B \le 10^{-11}$ so that the bar keeps a margin.
4. A candidate that fails any check is rejected with the failing number returned to the proposer (the paper's
   feedback loop, Extended Data Fig. 1(c)).

### 2.3 Score
- Primary: the ZZ (two-qubit) count of the native circuit, or of the IR CX count while a candidate is not yet
  converted (the conversion maps `cx` and `cp` one to one onto ZZPhase, computed:
  `validation/Q0P_2x4.json` Q2, structured `rzz_before` 71 548 = cx 71 544 + cp 4).
- Secondary axis for MAP-Elites cells (the paper keeps a $(T, Q)$ grid; here the analogue is):
  (two-qubit count, two-qubit depth).  Qubit count is fixed at 28 by the codec and is not a search axis.
- Reported alongside, never optimised alone: one-qubit count, the package's gate-only $-\ln f$ on H2-2
  (`skqd.device_req.clean_shot_fraction`), synthesis wall time.

### 2.4 Stopping rule
- Per family: stop after 8 consecutive verified candidates without a lower score, or after 1 laptop-day.
- **Go/no-go after step P2-2** (the `plaq1` loop): if no verified `plaq1` candidate is below 20 000 CX, stop the
  study there and report — with the other terms unchanged (71 520 − 66 468 = 5 052 CX) the whole-circuit
  compression would then be at most about 2.9x (71 520 → ~25 000, arithmetic on the computed term costs), far
  from the 26–29x device threshold, and the only benefit would be cheaper GPU emulation.
- Whole study: stop when the device threshold of `data/p1_device_threshold.json` is reached on every circuit,
  or when every family has hit its own stop.

## 3. Acceptance criteria (a compressed circuit counts only if all hold)

| id | criterion | bar | how measured |
|---|---|---|---|
| A1 | term rewrite exactness | $\le 10^{-10}$ max deviation, $\le 10^{-12}$ leakage, $k = 1..5$, both $dt$ | `run_ir` on the local space |
| A2 | full-circuit state | $\max|\Delta\psi| < 10^{-10}$ (phase-aligned), leakage $< 10^{-9}$, against `krylov.coarse_states` | `sparse_sim`, every (reference, $k$) circuit claimed |
| A3 | input contract stated | the circuit's claim says whether it is exact on all codewords (operator level) or only on its reference input (input-specific) | manifest field |
| A4 | native conversion | Q1L (i) + (ii) pass; $B \le 10^{-11}$ | `quantinuum_native` |
| A5 | counted against the frozen baseline | ZZ and two-qubit depth below 71 548 / 70 300 on the same (reference, $k$) | manifest counts |
| A6 | every rewrite rule used has a Lean proof | `lake build` passes, no `sorry`/`admit`, `#print axioms` only propext / Classical.choice / Quot.sound | `lean/` |
| A7 | reproducibility | JSON with git commit, parameters, seed (where any), machine, wall time; rerun gives identical counts | `data/` |

A2 is the package's bar; for adoption by the pipeline the package would re-measure it on the Aer GPU as it did
for the frozen family (prompts/35b R1, `validation/QV_2x4_01.json`) — that request is the coordinator's, never
this study's.

## 4. What needs a Lean proof

Proved in phase 1 (`lean/Compress2x4/Sanity.lean`): CZ·CZ = 1; RZZ(a)·RZZ(b) = RZZ(a+b) and commutation;
a diagonal operator on a basis vector gives a phase times it (drops the diagonal term on the reference input);
operators on disjoint tensor factors commute (reordering of disjoint-support terms); two-step agreement on
reachable sets.

To prove in phase 2 (each before the loop uses the rule it backs):
- L1 CNOT·CNOT = 1 and CNOT conjugation of Z-parities ($\mathrm{CX}\,(Z_c Z_t)\,\mathrm{CX} = Z_t$ etc.) — the
  peephole and phase-polynomial rules of F4/F5.
- L2 uniformly controlled rotations with equal target, axis and controls merge by adding their angle tables;
  a uniformly controlled rotation whose table does not depend on one control equals the one without it (the
  package's `_reduce_controls` premise).
- L3 the Gray-code/Walsh–Hadamard identity: a uniformly controlled $R_z$ on $m$ controls equals the alternating
  CNOT–$R_z$ chain with angles $\mathbf{a} = 2^{-m} H^{\otimes m}\boldsymbol{\theta}$ (Möttönen et al.), and a zero
  entry of $\mathbf{a}$ lets the two neighbouring CNOTs cancel — the cost rule of F4.
- L4 the bipartite block identity behind `_block_rounds`: for $A = \begin{pmatrix}0 & K\\ -K^{T} & 0\end{pmatrix}$
  with $K = U S V^{T}$, $e^{\theta A} = (U \oplus V)\,R(\theta S)\,(U \oplus V)^{T}$ with $R$ the pair rotations.
- L5 the n-step reachable-set lemma (induction over a list of steps), generalising `agree_on_reachable`.
- L6 the error-budget (telescoping) bound for unitary steps:
  $\|\prod_i V_i\psi - \prod_i U_i\psi\| \le \sum_i \|(V_i - U_i)\varphi_i\|$ with $\varphi_i$ the exact intermediate
  states — needed only if F6 is approved.
- L7 for F2, if the structure test supports it: the exponential of $c(A + A^\dagger)$ with $A$ a tensor product
  of corner operators, reduced to a uniformly controlled rotation after local basis changes (statement fixed
  after P2-1).

Only these identities are proved.  The equality of a specific 28-qubit circuit with `coarse_states` is checked
numerically (A2) and reported as "numerically checked", never as "proved".

## 5. Steps and laptop time (i7-8750H, 62 GiB; every command ≤ 30 min, chunked otherwise)

| step | content | laptop time (ESTIMATE) | done when |
|---|---|---|---|
| P2-0 | evaluator harness in `src/`: load the baseline IR from the package cache `data/S2_2x4/cache` (read-only), count, term verifier, full-circuit sparse verifier, score; tests in `tests/` | 0.5 day of work; compute < 10 min | reproduces cx 71 544 / ry 70 308 and the baseline state deviation $\sim10^{-13}$ on `B0_ref102_k1` (computed reference 1.07e-13 sparse, `validation/S2_2x4.json`) |
| P2-1 | structure tests: corner factorisation (operator-Schmidt rank across the four corners) of `plaq1`/`plaq0`/`plaq2` and of the hop terms; isomorphism classes of blocks; Walsh-spectrum sparsity with don't-cares; amplitude per block for F6 | 0.5 day; compute < 30 min | JSON with each number; decides which of F2/F3 is worth running |
| P2-2 | the `plaq1` loop (families F1–F4, F6 if approved); baseline `plaq1` synthesis takes 180 s (computed, S2_2x4 report table), each candidate ≤ 5 min | 2 days | go/no-go of §2.4 |
| P2-3 | hops, `plaq0`, `plaq2`, term boundaries (F5) | 1 day | per-term A1 |
| P2-4 | assembly of all 60 + 15 ($k=5$) circuits, A2 on each with the sparse simulator (≈ 3 min each at baseline size, less when compressed) | 0.5–1 day, background chunks | A2 on every circuit |
| P2-5 | native conversion of the finalists (baseline level-0 build 328 s per circuit, computed: manifest `compile_s`), A4, counts | 0.5 day | A4, A5 |
| P2-6 | Lean L1–L5 (L6, L7 if needed), in parallel with P2-0..P2-3 | 1–2 days | A6 |
| P2-7 | report `reports/002-…` in the owner's format; recommendation to the package if any | 0.5 day | — |

Total: about 6–8 working days, all on the laptop, 0 QPU seconds, 0 CI jobs.

## 6. What the package is imported for (read-only; nothing outside this folder is edited)

| import | used for |
|---|---|
| `skqd.exact.Model`, `mass_default` | the 2x4 model, basis and term matrices ($g^2 = 4$, $m = 0.75$) |
| `skqd.hamiltonian.Terms.groups` | the term order (diag, hop0–hop9, plaq0–plaq2) |
| `skqd.krylov.references`, `apply_groups`, `coarse_states` | the reference indices and the exact target states |
| `skqd.codec.Codec` | the fixed qubit layout and the codewords (convention, never redefined) |
| `skqd.reference_sim.term_support`, `localize` | term supports and local generators |
| `skqd.circuits_ir` (`structured_term_gates`, `CircuitFactory`, `ucr_gray`, `_multiplexed_two_level`, `_block_rounds`, `run_ir`, `gate_counts`) | the baseline IR, synthesis building blocks, local verification |
| `skqd.sparse_sim` | exact 28-qubit verification on the laptop |
| `skqd.device_req.clean_shot_fraction` | the device threshold and the secondary score |
| `skqd.quantinuum_native` (isolated venv) | native conversion and the Q1L proof |
| `scripts/gate_S2_2x4.py` `dt_of`, IR cache `data/S2_2x4/cache` | the frozen $dt$ and the baseline term IR without re-synthesis |

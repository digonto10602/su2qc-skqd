# 005 — Planner request: is the best verified 2x4 family the ultimate compression? (review + help)

- Date: 2026-10-21.  From: genie-opus.  To: planner-fable, routed by the coordinator (owner answer O8,
  `notes/002`).  Plan in force: `notes/003`, tolerance note `notes/004`.  Report: `reports/002-phase2-compression-results.md`.
- Nothing here asks for CI, QPU or package changes; everything stays inside `2x4_compression_using_ai_v1/`.

## 1. The question

The owner asks whether the best verified family is "the ultimate compressed version of the circuit".  I ask
the planner to review (a) whether the two classes below are correctly scoped (what is allowed, what is
excluded), (b) whether there is a cheaper *exact* construction I have missed for the two dominant cost centres
that remain, and (c) whether a lower-bound argument exists that would let us call a term "done".

## 2. Headline (from `data/summary_it5.json`; details in `reports/002` §3)

- Class B (exact on own reference input): 75/75 circuits pass; ZZ 582–800 (mean 683.5; 104.7x below 71 548);
  two-qubit depth 292–469; certified max $|\Delta\psi|\le1.16\times10^{-13}$.
- Class A (operator-exact): 75/75 pass; ZZ 1 736–1 740 (41.1x); depth 1 275–1 280; certified $\le1.54\times10^{-13}$.
- Native level 0 (Q1L + rounding bound $B\le1.4\times10^{-13}$): package gate-only $f$ on H2-2 0.47–0.58 (class B
  finalists) and 0.20 (class A), above the amendment-01 thresholds.
- Approximate class: no gain at the justified tolerance (or at 100x / 10 000x looser budgets).
- Verification method for whole circuits: certified pruned simulation (`notes/006`), cross-checked against the exact
  unpruned simulator on three circuits.

## 3. Evidence (all numbers in the files named; nothing estimated)

| item | file |
|---|---|
| baseline reproduced: 71 548 two-qubit, two-qubit depth 70 300, state 4.5e-14 | `data/p2_0_harness_baseline.json` |
| corner/vertex factorisation of every term (residuals, block structure) | `data/p2_1_structure.json` |
| per-term best constructions (archive of the loop, 5 iterations) | `data/archive_it5.json` (it1..it4 kept) |
| full-circuit verification, 75 circuits per class (k = 1..5) | `data/eval_arch_it5_{input,operator}_pp_all75_part*.json` |
| term-level checks on every codeword column / contract | `data/eval_arch_it5_*_terms*.json` |
| summary tables (generated) | `data/summary_it5.json` |
| native Quantinuum conversion, Q1L, rounding bound, level 0 and 2 | `data/native_it5_{input,operator}.json` |
| approximate class: cost vs tolerance, measured eps | `data/approx_tiers.json`, `notes/004` |
| Lean proofs (48 statements, standard axioms only) | `lean/Compress2x4/*.lean`, `data/p2_lean_build.log` |
| verification-method change, with its proof | `notes/006-certified-pruned-verification.md`, Lean `telescoping_bound_mirror` |

## 4. What I would like back

1. **Scope check.** Class A (operator-exact: every term exact on all its local codewords, diagonal group kept) and
   class B (exact on the circuit's own reference input: terms synthesised only on structurally reachable blocks,
   diagonal group dropped as a global phase; same 1e-10 / 1e-9 state bar).  Both exclude loading the classical
   output state.  Is class B acceptable to the pipeline (prompts/36 needs one circuit per (reference, k); class B
   has one per reference, k-independent gate skeleton)?  Is the term order (krylov.term_groups) the only
   constraint, or may provably commuting terms be reordered for depth?
2. **Hop terms** (largest remaining cost in class A).  The hop generator is $T+T^\dagger$ with
   $T=\eta\,a_x\otimes b_y\otimes s_{\rm JW}$; each vertex factor is a three-level chain $n=0\to1\to2$ with equal
   steps (a spin-1 raising operator), so blocks are spin-1 $\otimes$ spin-1 XY couplings (three-state chains and
   pairs).  My best construction (vertex parity fold + bright/dark intertwiner rotation + block synthesis with
   sparse-Walsh multiplexors) costs hop3 256 two-qubit gates.  Is there a known shorter exact circuit for
   $\exp(-i\theta g(J^+_xJ^-_y+{\rm h.c.}))$ multiplexed over a few label bits (for example via a qutrit-in-two-qubit
   encoding, or a fermionic-swap trick)?
3. **plaq1 in class A** (220).  Corner frames cost about half of it (bright rotations as triply controlled
   rotations, sign gadgets, clean-ancilla CNOTs, relative-phase Toffoli flags).  Any better use of the four clean
   ancillas (e.g. a relative-phase multi-controlled X so that the multiplexor depends on the x labels only)?
4. **Lower bounds.**  Is there a usable lower bound (for example from the number of distinct rotation angles
   times the minimum CNOT count of a multiplexor with given Walsh support, or an entangling-power argument) that
   would show a term is within a small factor of optimal?
5. **Approximate class.**  At the justified tolerance (identical SKQD samples with probability $\ge0.99$ at
   $10^6$ shots per sector) nothing can be dropped (`data/p2_1_structure.json` block amplitudes).  Does the planner
   see a weaker but still defensible SKQD criterion (recall of $S_{999}$, $E_R$ against $E_{\rm tol}$) that would
   be worth trading for?
6. **Adoption.**  If the planner thinks either family should be used by the package, what re-measurement slot
   (GPU, prompts/35b style) would it want — this study does not request one.

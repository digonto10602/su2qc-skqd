# 010 — Work plan for C4 (one more 2x4 round, hard stop) and C3 (2x3)

- Date: 2026-10-21.  Author: genie-opus.  Commit at writing: `a07ba6d` (+ uncommitted C4 code).
- In force: owner decisions `notes/008` (naming/separation rule; C3, C4 signed), planner review `notes/007` §6,
  reviewer notes `reviews/001` §5 (notes 2 and 3).  API for the noise agent: `notes/009`.

## C4 — one more 2x4 round

Hard stop: when planner steps 1–3 of notes/007 §6 and the multiplexor certificates are done, or after 2 laptop-days,
whichever comes first.  v1 (it5) stays untouched; anything better becomes `compressed_circuit_llm_2x4_class{A,B}_v2`.

| step (notes/007 §6) | what I do | done-check |
|---|---|---|
| 6 (first, because everything below builds on it) | **angle-linear synthesis** `src/c2x4/linsynth.py`: theta-dependent two-level ops carried as generators, every structural decision on the theta-free coefficient table | gate skeleton (names + qubits) identical for $k=1..5$ on every circuit; A1 term checks pass |
| 2 | **exact minimum Walsh support** per multiplexor, `src/c2x4/certify.py` (HiGHS MILP), both as a synthesis option (`*_milp` proposals) and as a certificate on every multiplexor of the final families | per multiplexor: `support_lb`, `support_used`, `certified_optimal`, walk lower bound `support+1` |
| 3 | hops: (a) JW sign as a CZ conjugation of the rotation target (`hopframe.jwc_framed_gates`); (b) clean ancilla from the duplicated hopping-link copy + **flags** (relative-phase AND of 2–3 literals) that move the nonzero rotations into their own half of the table (`hopframe.vertex_bright_frame_clean`, `linsynth._flag_variants`) | per-hop counts in the archive vs it5 |
| 1 | plaquettes: evaluate the "one OR'd dark flag" construction (cost of computing $G=\bigvee_c d_c$ vs the multiplexor saving), MILP on the present corner-frame multiplexor | archive numbers; a written cost comparison if the OR flag does not pay |
| 4, 5 | only if time remains: 4 cross-term frame merging; 5 depth — the two-qubit depth is already an ASAP longest path, so disjoint terms are already interleaved; report it | — |

Loop: `scripts/loop_select.py --label it6 ...` (archive `data/archive_it6.json`), families `arch:it6:<class>:pp`,
verification `scripts/eval_family.py --prune-tau 1e-15` on all 75 circuits per class, then freeze with
`scripts/freeze_family.py`.  Only k-independent (angle-linear) proposals are eligible for v2.

Reviewer note 2 (rounding): add a floating-point rounding term to the certified bound from the standard model of
complex arithmetic (per non-permutation gate), with a number per circuit; the algebra is proved in Lean, the unit
roundoff model is cited (not provable in Lean/Mathlib).  Reviewer note 3: formalise in Lean "local $W$ exact on the
touched blocks $\Rightarrow$ $W\otimes 1$ exact on the span of the reachable basis states" and "the exact term maps
the span of a union of components into itself"; say what remains numerical.

## C3 — 2x3

The code is parameterised by $L_x$ (`Problem(lx)`), not forked.  Circuit list and $k$ range: the frozen 2x3 family
(`data/quantinuum/circuits_2x3/index.json`: 44 circuits = 8 references at $B=0$, 3 at $B=1$, $k=1..4$, `dt` from the
manifests = `Model(3).reference(4, 2B).dt`).  Loop at 2x3, families `compressed_circuit_llm_2x3_class{A,B}`, verified
(a) by my harness (certified pruned sparse simulation) and (b) by an independent qiskit-aer statevector on all
20-qubit circuits, both against `krylov.apply_groups` with the bar $\max|\Delta\psi|<10^{-10}$, leakage $<10^{-9}$.
Counts against the frozen 2x3 family (2 158 ZZ), $f$ with the package formula for information.  Outputs under
`data/c2x3/`.

# 003 — Phase-2 plan in force: corner-factorised plaquette (family F2) first, then hops

- Date: 2026-10-21.  Author: genie-opus.  Supersedes the step order of `notes/001-phase2-plan.md` §5 (the
  acceptance criteria A1–A7 of 001 §3 stay in force, and the owner's answers `notes/002` apply).
- Trigger: the P2-1 structure test (2026-10-21, interactive, to be written to
  `data/p2_1_plaq_structure.json` by `scripts/p2_1_plaq_structure.py`) found that the local generator of
  `plaq1` on its 1 831 local codewords equals a tensor product of four corner matrices
  $h = A_{c_{00}}\otimes A_{c_{10}}\otimes A_{c_{11}}\otimes A_{c_{01}}$ to $1.8\times10^{-15}$
  (all $2^{16}$ rows, all codeword columns).  Each corner matrix is block diagonal; its blocks are pairs
  (and one three-state block coupling the two intertwiner states of $n=1$, all-flux vertices); a block is
  antisymmetric when the two plaquette-link bits of the corner are equal and symmetric otherwise; the two pair
  magnitudes of a corner differ by $\sqrt2$.  Physics reason (my reading, to be stated as such): the colour
  indices of the plaquette loop are contracted around the four corners and each corner tensor is an SU(2)
  invariant map, so it is proportional to $\delta_{ij}$ in colour space (Wigner–Eckart), leaving a product of
  scalar corner factors.

## Construction (my label: "corner frame + one rotation", CF1)

1. Per corner $c$: $\mathrm{CX}(p_a\to p_b)$ on its two plaquette-link qubits (the plaquette then flips only
   $p_a$; $p_b$ holds $x_c=p_a\oplus p_b$), and for the three-state block one two-level real rotation on the
   intertwiner qubit that maps the "bright" combination onto a basis state (the orthogonal "dark" state is
   annihilated by the plaquette).  In this frame $A_c = X_{p_a}\otimes D_c$ with $D_c$ diagonal.
2. A CNOT ladder from $p_1$ (one corner's $p_a$) to the other three $p_a$ turns $X^{\otimes4}$ into $X_{p_1}$;
   linear relations among the remaining bits on the occupied states are used to clear redundant qubits.
3. One uniformly controlled $R_x$ on $p_1$ whose angle table is read from the frame generator, synthesised by
   the package's `_multiplexed_two_level` (don't-cares = unoccupied slots), then all frames undone.
4. Stage B (after A verifies): clean ancillas from the redundant qubits carry per-corner flags so that the
   multiplexer needs fewer controls.

Verification: A1 on every local codeword column (`evaluate.verify_term_operator`, max deviation and leakage),
then A2 on full circuits.  Lean: the conjugation, restriction (agreement on an invariant subspace), CNOT-ladder,
uniformly-controlled-rotation and compute/uncompute lemmas the construction relies on.

## Then

Hops (4 018 IR CX) and `plaq0`/`plaq2` (228 / 806) with the same factorisation test (a hop is
$T+T^\dagger$ with $T$ a product of two vertex factors and a Jordan–Wigner sign); the diagonal group dropped
on the reference input (exact on that input; Lean `diagonal_mulVec_single`).  Approximate class: only after
the exact class, with the tolerance stated in a note before use (owner O2) and lemma L6.

/-
Phase-1 sanity lemmas for the 2x4 compression study (genie-opus, 2026-10-19).

Conventions: a two-qubit gate is a 4x4 complex matrix in the computational basis
|00>, |01>, |10>, |11>.  These are setup checks of the Lean environment and the first members
of the rewrite-rule library that phase 2 will extend; each one names the circuit fact it backs.
-/
import Mathlib

open Matrix
open scoped Kronecker

namespace Compress2x4

/-- The controlled-Z gate, diag(1, 1, 1, -1). -/
noncomputable def CZ : Matrix (Fin 4) (Fin 4) ℂ := Matrix.diagonal ![1, 1, 1, -1]

/-- Two adjacent CZ gates on the same pair cancel (template: CZ CZ = I). -/
theorem CZ_mul_CZ : CZ * CZ = 1 := by
  rw [CZ, Matrix.diagonal_mul_diagonal, ← Matrix.diagonal_one]
  congr 1
  funext i
  fin_cases i <;> simp

/-- Sign pattern of Z (x) Z on |00>, |01>, |10>, |11>. -/
def zzSign : Fin 4 → ℂ := ![1, -1, -1, 1]

/-- The ZZ rotation exp(-i (theta/2) Z (x) Z), written as the diagonal matrix it is. -/
noncomputable def RZZ (θ : ℝ) : Matrix (Fin 4) (Fin 4) ℂ :=
  Matrix.diagonal fun i => Complex.exp (-((θ : ℂ) / 2) * Complex.I * zzSign i)

/-- Two ZZ rotations on the same pair merge by adding their angles (rewrite: RZZ a RZZ b =
RZZ (a + b)); in particular they commute. -/
theorem RZZ_mul_RZZ (a b : ℝ) : RZZ a * RZZ b = RZZ (a + b) := by
  simp only [RZZ, Matrix.diagonal_mul_diagonal]
  congr 1
  funext i
  rw [← Complex.exp_add]
  congr 1
  push_cast
  ring

theorem RZZ_comm (a b : ℝ) : RZZ a * RZZ b = RZZ b * RZZ a := by
  rw [RZZ_mul_RZZ, RZZ_mul_RZZ, add_comm]

/-- A diagonal operator acting on a computational-basis vector returns that vector times one
phase.  This is the fact behind dropping the diagonal term group of the coarse step when it acts
first on the reference basis state: its effect is a global phase. -/
theorem diagonal_mulVec_single {n : Type*} [Fintype n] [DecidableEq n] (d : n → ℂ) (i : n) :
    (Matrix.diagonal d).mulVec (Pi.single i 1) = d i • Pi.single i 1 := by
  funext j
  rw [Matrix.mulVec_diagonal]
  by_cases h : j = i
  · subst h
    simp
  · simp [h]

/-- Operators on disjoint tensor factors commute: (A (x) 1)(1 (x) B) = (1 (x) B)(A (x) 1).
This is the fact behind reordering coarse-step terms whose qubit supports are disjoint. -/
theorem kron_disjoint_comm {m n : Type*} [Fintype m] [Fintype n] [DecidableEq m] [DecidableEq n]
    (A : Matrix m m ℂ) (B : Matrix n n ℂ) :
    (A ⊗ₖ (1 : Matrix n n ℂ)) * ((1 : Matrix m m ℂ) ⊗ₖ B) =
      ((1 : Matrix m m ℂ) ⊗ₖ B) * (A ⊗ₖ (1 : Matrix n n ℂ)) := by
  rw [← Matrix.mul_kronecker_mul, ← Matrix.mul_kronecker_mul]
  simp

/-- Restriction to reachable states, two steps: if the candidate step V1 agrees with the exact
step U1 on a set S1 of inputs, U1 maps S1 into S2, and V2 agrees with U2 on S2, then the two-step
products agree on S1.  A circuit only has to be exact on the states it can actually receive. -/
theorem agree_on_reachable {M : Type*} (U1 V1 U2 V2 : M → M) (S1 S2 : Set M)
    (h1 : ∀ x ∈ S1, V1 x = U1 x) (hmap : ∀ x ∈ S1, U1 x ∈ S2)
    (h2 : ∀ y ∈ S2, V2 y = U2 y) : ∀ x ∈ S1, V2 (V1 x) = U2 (U1 x) := by
  intro x hx
  rw [h1 x hx, h2 _ (hmap x hx)]

end Compress2x4

#print axioms Compress2x4.CZ_mul_CZ
#print axioms Compress2x4.RZZ_mul_RZZ
#print axioms Compress2x4.RZZ_comm
#print axioms Compress2x4.diagonal_mulVec_single
#print axioms Compress2x4.kron_disjoint_comm
#print axioms Compress2x4.agree_on_reachable

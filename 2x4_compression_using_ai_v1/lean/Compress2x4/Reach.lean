/-
Lemma L5 (n-step restriction to reachable sets) and lemma L6 (error budget, telescoping), plus the two
small facts used by the frames (genie-opus, phase 2, 2026-10-21).

* `run`: the product of the first k steps applied to x (the first step acts first).
* `agree_on_reachable_n` (L5): if every candidate step V_i agrees with the exact step U_i on a set S_i and
  U_i maps S_i into S_{i+1}, then the first k candidate steps agree with the exact ones on S_0, and the
  exact run stays in S_k.  This is what makes the input-specific circuits (family F1: each term synthesised
  only on the blocks reachable from the reference) exact on their reference input.
* `telescoping_bound` (L6): if every candidate step is 1-Lipschitz (true for unitaries), then
  || V_{k-1} ... V_0 psi - U_{k-1} ... U_0 psi || <= sum_{i<k} || V_i(phi_i) - U_i(phi_i) || with phi_i the
  exact intermediate states.  This bounds the error of the approximate class (dropped near-zero-amplitude
  parts) by the sizes of the parts dropped along the exact trajectory.
* `ry_add_two_pi`: Ry(phi + 2 pi) = - Ry(phi) (the free sign flip of a bright rotation).
* `relphase_cancel`: a compute ... uncompute pair that is correct only up to a phase D cancels the phase if
  D commutes with what happens in between (relative-phase Toffoli).
-/
import Mathlib

open Matrix

namespace Compress2x4

section Reach

variable {M : Type*}

/-- The first k steps applied to x (step 0 acts first). -/
def run (U : ℕ → M → M) : ℕ → M → M
  | 0, x => x
  | k + 1, x => U k (run U k x)

theorem agree_on_reachable_n (U V : ℕ → M → M) (S : ℕ → Set M)
    (hagree : ∀ i, ∀ x ∈ S i, V i x = U i x) (hmap : ∀ i, ∀ x ∈ S i, U i x ∈ S (i + 1)) :
    ∀ k, ∀ x ∈ S 0, run V k x = run U k x ∧ run U k x ∈ S k := by
  intro k
  induction k with
  | zero => intro x hx; exact ⟨rfl, hx⟩
  | succ k ih =>
    intro x hx
    obtain ⟨h1, h2⟩ := ih x hx
    refine ⟨?_, hmap k _ h2⟩
    show V k (run V k x) = U k (run U k x)
    rw [h1, hagree k _ h2]

end Reach

section Budget

variable {E : Type*} [SeminormedAddCommGroup E]

theorem telescoping_bound (U V : ℕ → E → E) (hV : ∀ i x y, ‖V i x - V i y‖ ≤ ‖x - y‖) (ψ : E) :
    ∀ k, ‖run V k ψ - run U k ψ‖ ≤
      ∑ i ∈ Finset.range k, ‖V i (run U i ψ) - U i (run U i ψ)‖ := by
  intro k
  induction k with
  | zero => simp [run]
  | succ k ih =>
    rw [Finset.sum_range_succ]
    show ‖V k (run V k ψ) - U k (run U k ψ)‖ ≤ _
    calc ‖V k (run V k ψ) - U k (run U k ψ)‖
        = ‖(V k (run V k ψ) - V k (run U k ψ)) + (V k (run U k ψ) - U k (run U k ψ))‖ := by
          congr 1; abel
      _ ≤ ‖V k (run V k ψ) - V k (run U k ψ)‖ + ‖V k (run U k ψ) - U k (run U k ψ)‖ :=
          norm_add_le _ _
      _ ≤ ‖run V k ψ - run U k ψ‖ + ‖V k (run U k ψ) - U k (run U k ψ)‖ := by
          gcongr; exact hV k _ _
      _ ≤ _ := by gcongr

/-- L6 mirrored (used by the pruned simulator): if every EXACT step is 1-Lipschitz (unitary), the distance between
the computed run (each step followed by pruning tiny amplitudes, V) and the exact run (U) is at most the sum of
what was changed along the COMPUTED trajectory: sum_i || V_i(v_i) - U_i(v_i) ||, v_i = run V i psi. -/
theorem telescoping_bound_mirror (U V : ℕ → E → E) (hU : ∀ i x y, ‖U i x - U i y‖ ≤ ‖x - y‖) (ψ : E) :
    ∀ k, ‖run V k ψ - run U k ψ‖ ≤
      ∑ i ∈ Finset.range k, ‖V i (run V i ψ) - U i (run V i ψ)‖ := by
  intro k
  induction k with
  | zero => simp [run]
  | succ k ih =>
    rw [Finset.sum_range_succ]
    show ‖V k (run V k ψ) - U k (run U k ψ)‖ ≤ _
    calc ‖V k (run V k ψ) - U k (run U k ψ)‖
        = ‖(V k (run V k ψ) - U k (run V k ψ)) + (U k (run V k ψ) - U k (run U k ψ))‖ := by
          congr 1; abel
      _ ≤ ‖V k (run V k ψ) - U k (run V k ψ)‖ + ‖U k (run V k ψ) - U k (run U k ψ)‖ :=
          norm_add_le _ _
      _ ≤ ‖V k (run V k ψ) - U k (run V k ψ)‖ + ‖run V k ψ - run U k ψ‖ := by
          gcongr; exact hU k _ _
      _ ≤ _ := by linarith

end Budget

/-- The one-qubit y rotation Ry(phi) = [[cos(phi/2), -sin(phi/2)], [sin(phi/2), cos(phi/2)]]. -/
noncomputable def Ry (φ : ℝ) : Matrix (Fin 2) (Fin 2) ℂ :=
  !![(Real.cos (φ / 2) : ℂ), -(Real.sin (φ / 2) : ℂ); (Real.sin (φ / 2) : ℂ), (Real.cos (φ / 2) : ℂ)]

theorem ry_add_two_pi (φ : ℝ) : Ry (φ + 2 * Real.pi) = -Ry φ := by
  have h : (φ + 2 * Real.pi) / 2 = φ / 2 + Real.pi := by ring
  ext i j
  fin_cases i <;> fin_cases j <;>
    simp [Ry, h, Real.cos_add_pi, Real.sin_add_pi]

/-- Relative-phase compute/uncompute: with R = D T (T the exact gate, D a phase that commutes with the
middle block B), R^-1 B R = T^-1 B T. Stated with explicit inverses. -/
theorem relphase_cancel {n : Type*} [Fintype n] [DecidableEq n]
    (D Dinv T Tinv B : Matrix n n ℂ) (hD : Dinv * D = 1) (hcomm : D * B = B * D) :
    (Tinv * Dinv) * B * (D * T) = Tinv * B * T := by
  calc (Tinv * Dinv) * B * (D * T) = Tinv * (Dinv * (B * D)) * T := by
        simp only [Matrix.mul_assoc]
    _ = Tinv * (Dinv * (D * B)) * T := by rw [hcomm]
    _ = Tinv * B * T := by rw [← Matrix.mul_assoc Dinv D B, hD, Matrix.one_mul]

end Compress2x4

#print axioms Compress2x4.agree_on_reachable_n
#print axioms Compress2x4.telescoping_bound
#print axioms Compress2x4.telescoping_bound_mirror
#print axioms Compress2x4.ry_add_two_pi
#print axioms Compress2x4.relphase_cancel

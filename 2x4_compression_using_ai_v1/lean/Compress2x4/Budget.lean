/-
Bounds for the approximate class (notes/004-approximate-class-tolerance.md), genie-opus, 2026-10-21.

* `dropped_part_bound` (L6c): if two norm-preserving additive maps V, U agree on phi - p, then
  || V phi - U phi || <= 2 || p ||.  With p = Pi_D phi (the part of the exact intermediate state on the
  dropped blocks) and V = U on the kept blocks, each term contributes at most 2 || Pi_D phi || to the
  telescoping sum of `Compress2x4.telescoping_bound` (L6).
* `normSq_sub_le` and `tv_le_norm_sub` (L6b): sum_s | |a_s|^2 - |b_s|^2 | <= ||a - b|| ||a + b||, so the
  total-variation distance of the two measurement distributions is at most ||a - b|| for unit vectors
  (||a + b|| <= 2); the global phase is free because |e^{i alpha} b_s| = |b_s|.
-/
import Mathlib

namespace Compress2x4

section Dropped

variable {E : Type*} [SeminormedAddCommGroup E]

theorem dropped_part_bound (V U : E →+ E) (hV : ∀ x, ‖V x‖ = ‖x‖) (hU : ∀ x, ‖U x‖ = ‖x‖)
    (φ p : E) (hagree : V (φ - p) = U (φ - p)) : ‖V φ - U φ‖ ≤ 2 * ‖p‖ := by
  have hφ : φ = (φ - p) + p := by abel
  have : V φ - U φ = V p - U p := by
    rw [hφ, map_add, map_add, hagree]; abel
  rw [this]
  calc ‖V p - U p‖ ≤ ‖V p‖ + ‖U p‖ := norm_sub_le _ _
    _ = 2 * ‖p‖ := by rw [hV, hU]; ring

end Dropped

section TV

/-- Pointwise: | |a|^2 - |b|^2 | <= |a - b| |a + b| for complex numbers. -/
theorem normSq_sub_le (a b : ℂ) : |‖a‖ ^ 2 - ‖b‖ ^ 2| ≤ ‖a - b‖ * ‖a + b‖ := by
  have hre : ‖a‖ ^ 2 - ‖b‖ ^ 2 = ((a - b) * (starRingEnd ℂ) (a + b)).re := by
    rw [Complex.sq_norm, Complex.sq_norm, Complex.normSq_apply, Complex.normSq_apply]
    simp only [Complex.mul_re, Complex.sub_re, Complex.sub_im, Complex.conj_re, Complex.conj_im,
      Complex.add_re, Complex.add_im]
    ring
  rw [hre]
  calc |((a - b) * (starRingEnd ℂ) (a + b)).re| ≤ ‖(a - b) * (starRingEnd ℂ) (a + b)‖ :=
        Complex.abs_re_le_norm _
    _ = ‖a - b‖ * ‖a + b‖ := by rw [norm_mul, Complex.norm_conj]

/-- Summed: sum_s | |a_s|^2 - |b_s|^2 | <= sqrt(sum |a_s - b_s|^2) sqrt(sum |a_s + b_s|^2). -/
theorem tv_le_norm_sub {ι : Type*} (s : Finset ι) (a b : ι → ℂ) :
    ∑ i ∈ s, |‖a i‖ ^ 2 - ‖b i‖ ^ 2| ≤
      Real.sqrt (∑ i ∈ s, ‖a i - b i‖ ^ 2) * Real.sqrt (∑ i ∈ s, ‖a i + b i‖ ^ 2) := by
  calc ∑ i ∈ s, |‖a i‖ ^ 2 - ‖b i‖ ^ 2| ≤ ∑ i ∈ s, ‖a i - b i‖ * ‖a i + b i‖ :=
        Finset.sum_le_sum fun i _ => normSq_sub_le (a i) (b i)
    _ ≤ _ := Real.sum_mul_le_sqrt_mul_sqrt s _ _

end TV

end Compress2x4

#print axioms Compress2x4.dropped_part_bound
#print axioms Compress2x4.normSq_sub_le
#print axioms Compress2x4.tv_le_norm_sub

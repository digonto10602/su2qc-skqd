/-
Reviewer note 2 (reviews/001 §5): the floating-point rounding term of the certified bound (genie-opus, C4, 2026-10-21).

Model (standard; Higham, "Accuracy and Stability of Numerical Algorithms", 2nd ed., §2.2 and Lemma 3.5 -- cited,
not provable in Lean/Mathlib, which has no IEEE-754 semantics): every computed complex product is the exact product
times (1 + e) with |e| <= mu, every computed complex sum the exact sum times (1 + e) with |e| <= u.  The sparse
simulator applies a one-qubit gate to an amplitude pair (x, y) as (a x + b y, c x + d y) (skqd.sparse_sim.mix), a
diagonal gate as one product per amplitude, and CX / X / CZ as exact permutations or sign changes.

* `pair_round_bound`: |fl(a x + b y) - (a x + b y)| <= (mu + u + mu u)(|a||x| + |b||y|).
* `row_sq_le`: (|a||x| + |b||y|)^2 <= (|a|^2 + |b|^2)(|x|^2 + |y|^2)  (Cauchy-Schwarz).
* `gate_round_sq`: hence, for the two output components, |err_top|^2 + |err_bot|^2 <=
  gamma^2 (|a|^2+|b|^2+|c|^2+|d|^2)(|x|^2+|y|^2) with gamma = mu + u + mu u, i.e. ||err|| <= gamma ||G||_F ||(x,y)||.
* `entry_err_sq`: a perturbation of the stored matrix entries (stored or computed matrix G' vs the exact unitary G)
  costs ||(G' - G)(x, y)||^2 <= ||G' - G||_F^2 ||(x, y)||^2.
Summed over the disjoint amplitude pairs of one gate, the computed state after the gate differs from the exact gate
applied to the computed state by at most delta ||v|| with delta = gamma ||G'||_F + ||G' - G||_F, and the telescoping
bound `telescoping_bound_mirror` (Reach.lean) adds these per-gate terms (they are the ||V_i(v_i) - U_i(v_i)|| there).
-/
import Mathlib

namespace Compress2x4

theorem pair_round_bound (a b x y e1 e2 e3 : ℂ) (μ u : ℝ) (h1 : ‖e1‖ ≤ μ) (h2 : ‖e2‖ ≤ μ)
    (h3 : ‖e3‖ ≤ u) (hμ : 0 ≤ μ) (hu : 0 ≤ u) :
    ‖(a * x * (1 + e1) + b * y * (1 + e2)) * (1 + e3) - (a * x + b * y)‖ ≤
      (μ + u + μ * u) * (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖) := by
  have hexp : (a * x * (1 + e1) + b * y * (1 + e2)) * (1 + e3) - (a * x + b * y) =
      (a * x + b * y) * e3 + (a * x * e1 + b * y * e2) * (1 + e3) := by ring
  rw [hexp]
  have hA : ‖(a * x + b * y) * e3‖ ≤ (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖) * u := by
    rw [norm_mul]
    apply mul_le_mul _ h3 (norm_nonneg _) (by positivity)
    calc ‖a * x + b * y‖ ≤ ‖a * x‖ + ‖b * y‖ := norm_add_le _ _
      _ = ‖a‖ * ‖x‖ + ‖b‖ * ‖y‖ := by rw [norm_mul, norm_mul]
  have hB : ‖(a * x * e1 + b * y * e2) * (1 + e3)‖ ≤ (‖a‖ * ‖x‖ * μ + ‖b‖ * ‖y‖ * μ) * (1 + u) := by
    rw [norm_mul]
    apply mul_le_mul _ _ (norm_nonneg _) (by positivity)
    · calc ‖a * x * e1 + b * y * e2‖ ≤ ‖a * x * e1‖ + ‖b * y * e2‖ := norm_add_le _ _
        _ = ‖a‖ * ‖x‖ * ‖e1‖ + ‖b‖ * ‖y‖ * ‖e2‖ := by rw [norm_mul, norm_mul, norm_mul, norm_mul]
        _ ≤ ‖a‖ * ‖x‖ * μ + ‖b‖ * ‖y‖ * μ := by gcongr
    · calc ‖(1 : ℂ) + e3‖ ≤ ‖(1 : ℂ)‖ + ‖e3‖ := norm_add_le _ _
        _ ≤ 1 + u := by rw [norm_one]; linarith
  calc ‖(a * x + b * y) * e3 + (a * x * e1 + b * y * e2) * (1 + e3)‖
      ≤ ‖(a * x + b * y) * e3‖ + ‖(a * x * e1 + b * y * e2) * (1 + e3)‖ := norm_add_le _ _
    _ ≤ (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖) * u + (‖a‖ * ‖x‖ * μ + ‖b‖ * ‖y‖ * μ) * (1 + u) := add_le_add hA hB
    _ = (μ + u + μ * u) * (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖) := by ring

theorem row_sq_le (a b x y : ℂ) :
    (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖) ^ 2 ≤ (‖a‖ ^ 2 + ‖b‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2) := by
  nlinarith [sq_nonneg (‖a‖ * ‖y‖ - ‖b‖ * ‖x‖)]

theorem gate_round_sq (a b c d x y et eb : ℂ) (γ : ℝ) (hγ : 0 ≤ γ)
    (ht : ‖et‖ ≤ γ * (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖)) (hb : ‖eb‖ ≤ γ * (‖c‖ * ‖x‖ + ‖d‖ * ‖y‖)) :
    ‖et‖ ^ 2 + ‖eb‖ ^ 2 ≤ γ ^ 2 * (‖a‖ ^ 2 + ‖b‖ ^ 2 + ‖c‖ ^ 2 + ‖d‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2) := by
  have h1 : ‖et‖ ^ 2 ≤ γ ^ 2 * (‖a‖ ^ 2 + ‖b‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2) := by
    calc ‖et‖ ^ 2 ≤ (γ * (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖)) ^ 2 := by gcongr
      _ = γ ^ 2 * (‖a‖ * ‖x‖ + ‖b‖ * ‖y‖) ^ 2 := by ring
      _ ≤ γ ^ 2 * ((‖a‖ ^ 2 + ‖b‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2)) := by gcongr; exact row_sq_le a b x y
      _ = _ := by ring
  have h2 : ‖eb‖ ^ 2 ≤ γ ^ 2 * (‖c‖ ^ 2 + ‖d‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2) := by
    calc ‖eb‖ ^ 2 ≤ (γ * (‖c‖ * ‖x‖ + ‖d‖ * ‖y‖)) ^ 2 := by gcongr
      _ = γ ^ 2 * (‖c‖ * ‖x‖ + ‖d‖ * ‖y‖) ^ 2 := by ring
      _ ≤ γ ^ 2 * ((‖c‖ ^ 2 + ‖d‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2)) := by gcongr; exact row_sq_le c d x y
      _ = _ := by ring
  nlinarith [h1, h2]

theorem entry_err_sq (p q r s x y : ℂ) :
    ‖p * x + q * y‖ ^ 2 + ‖r * x + s * y‖ ^ 2 ≤
      (‖p‖ ^ 2 + ‖q‖ ^ 2 + ‖r‖ ^ 2 + ‖s‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2) := by
  have h1 : ‖p * x + q * y‖ ≤ ‖p‖ * ‖x‖ + ‖q‖ * ‖y‖ := by
    calc ‖p * x + q * y‖ ≤ ‖p * x‖ + ‖q * y‖ := norm_add_le _ _
      _ = _ := by rw [norm_mul, norm_mul]
  have h2 : ‖r * x + s * y‖ ≤ ‖r‖ * ‖x‖ + ‖s‖ * ‖y‖ := by
    calc ‖r * x + s * y‖ ≤ ‖r * x‖ + ‖s * y‖ := norm_add_le _ _
      _ = _ := by rw [norm_mul, norm_mul]
  have h1' : ‖p * x + q * y‖ ^ 2 ≤ (‖p‖ ^ 2 + ‖q‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2) :=
    le_trans (by gcongr) (row_sq_le p q x y)
  have h2' : ‖r * x + s * y‖ ^ 2 ≤ (‖r‖ ^ 2 + ‖s‖ ^ 2) * (‖x‖ ^ 2 + ‖y‖ ^ 2) :=
    le_trans (by gcongr) (row_sq_le r s x y)
  nlinarith [h1', h2']

end Compress2x4

#print axioms Compress2x4.pair_round_bound
#print axioms Compress2x4.row_sq_le
#print axioms Compress2x4.gate_round_sq
#print axioms Compress2x4.entry_err_sq

/-
G5: from the frame generator X_t diag(D) (D independent of the target bit t) to a multiplexed rotation.
genie-opus, phase 2, 2026-10-21.

In every CF / hop-frame construction the generator in the frame is, on the occupied strings,
X_t diag(D) with D(s) independent of bit t (numerically checked per instance).  Here, for every n:

* `xt_mul_xt`, `zd_mul_zd`: X_t^2 = 1, Z_t^2 = 1.
* `xt_zd_anticomm`: X_t Z_t = - Z_t X_t.
* `ht` := (X_t + Z_t)/sqrt 2 (the Hadamard on qubit t); `ht_mul_ht`: H_t^2 = 1; `ht_xt_ht`: H_t X_t H_t = Z_t.
* `diag_comm_xt`: diag(D) commutes with X_t when D ignores bit t; `ht_diag_ht`: then H_t diag(D) H_t = diag(D).
* `exp_xt_diag` (G5): exp(c X_t diag(D)) = H_t exp(c Z_t diag(D)) H_t, and Z_t diag(D) is the diagonal
  s -> (-1)^{s_t} D(s), so its exponential is the diagonal of exp(c (-1)^{s_t} D(s)) (Matrix.exp_diagonal): the
  multiplexed rotation about x on qubit t with angle table D, which W1/W2 (Ucr.lean) decompose into CNOTs.
-/
import Compress2x4.Ucr

open Matrix NormedSpace

namespace Compress2x4

variable {n : ℕ}

theorem flipE_unitVec_t (t : Fin n) (s : Q n) : (flipE (unitVec t)) s t = !(s t) := by
  simp [flipE, bxor, unitVec]

theorem xt_mul_xt (t : Fin n) : xt t * xt t = 1 := by
  unfold xt
  rw [perm_mul]
  convert perm_one (n := n)
  ext s i
  simp [flipE, bxor]

theorem zd_mul_zd (t : Fin n) : zd t * zd t = 1 := by
  unfold zd
  rw [diagonal_mul_diagonal, ← diagonal_one]
  congr 1
  funext s
  by_cases h : s t <;> simp [h]

/-- X_t Z_t X_t = - Z_t, written as an anticommutation. -/
theorem xt_zd_anticomm (t : Fin n) : xt t * zd t = -(zd t * xt t) := by
  have hc := perm_conj_diagonal (flipE (unitVec t)) (fun s => if s t then (-1 : ℂ) else 1)
  have hf : ((fun s : Q n => if s t then (-1 : ℂ) else 1) ∘ (flipE (unitVec t)).symm) =
      fun s => -(if s t then (-1 : ℂ) else 1) := by
    funext s
    have : (flipE (unitVec t)).symm s t = !(s t) := by simp [flipE, bxor, unitVec]
    simp only [Function.comp_apply, this]
    by_cases h : s t <;> simp [h]
  rw [hf] at hc
  have hneg : diagonal (fun s : Q n => -(if s t then (-1 : ℂ) else 1)) = -zd t := by
    unfold zd; rw [← diagonal_neg]
  rw [hneg] at hc
  unfold xt
  calc perm (flipE (unitVec t)) * zd t
      = perm (flipE (unitVec t)) * zd t * (perm (flipE (unitVec t)).symm * perm (flipE (unitVec t))) := by
        rw [perm_symm_mul, Matrix.mul_one]
    _ = (perm (flipE (unitVec t)) * zd t * perm (flipE (unitVec t)).symm) * perm (flipE (unitVec t)) := by
        simp only [Matrix.mul_assoc]
    _ = -(zd t * perm (flipE (unitVec t))) := by
        unfold zd at hc ⊢; rw [hc, Matrix.neg_mul]

/-- The Hadamard on qubit t. -/
noncomputable def ht (t : Fin n) : Matrix (Q n) (Q n) ℂ := ((Real.sqrt 2 : ℂ)⁻¹) • (xt t + zd t)

theorem sqrt2_inv_sq : ((Real.sqrt 2 : ℂ)⁻¹) * ((Real.sqrt 2 : ℂ)⁻¹) = (1 / 2 : ℂ) := by
  rw [← mul_inv, ← Complex.ofReal_mul, Real.mul_self_sqrt (by norm_num : (0 : ℝ) ≤ 2)]
  push_cast; ring

theorem ht_mul_ht (t : Fin n) : ht t * ht t = 1 := by
  unfold ht
  rw [Matrix.smul_mul, Matrix.mul_smul, smul_smul, sqrt2_inv_sq, Matrix.add_mul, Matrix.mul_add,
    Matrix.mul_add, xt_mul_xt, zd_mul_zd, xt_zd_anticomm]
  have : (1 : Matrix (Q n) (Q n) ℂ) + -(zd t * xt t) + (zd t * xt t + 1) = (2 : ℂ) • 1 := by
    rw [two_smul]; abel
  rw [this, smul_smul]; norm_num

theorem ht_xt_ht (t : Fin n) : ht t * xt t * ht t = zd t := by
  unfold ht
  rw [Matrix.smul_mul, Matrix.smul_mul, Matrix.mul_smul, smul_smul, sqrt2_inv_sq]
  have hx := xt_mul_xt t
  have hz := zd_mul_zd t
  have ha := xt_zd_anticomm t
  -- (X + Z) X (X + Z) = X X X + X X Z + Z X X + Z X Z = X + Z + Z - X = 2 Z
  have key : (xt t + zd t) * xt t * (xt t + zd t) = (2 : ℂ) • zd t := by
    rw [Matrix.add_mul, Matrix.add_mul, Matrix.mul_add, Matrix.mul_add, hx, Matrix.one_mul,
      Matrix.one_mul, Matrix.mul_assoc (zd t) (xt t) (xt t), hx, Matrix.mul_one,
      Matrix.mul_assoc (zd t) (xt t) (zd t), ha, Matrix.mul_neg, ← Matrix.mul_assoc, hz,
      Matrix.one_mul, two_smul]
    abel
  rw [key, smul_smul]; norm_num

/-- A phase table that ignores bit t commutes with X_t. -/
theorem diag_comm_xt (t : Fin n) (D : Q n → ℂ) (hD : ∀ s, D ((flipE (unitVec t)) s) = D s) :
    xt t * diagonal D = diagonal D * xt t := by
  have hc := perm_conj_diagonal (flipE (unitVec t)) D
  have hf : D ∘ (flipE (unitVec t)).symm = D := by
    funext s
    have : (flipE (unitVec t)).symm s = (flipE (unitVec t)) s := rfl
    simp only [Function.comp_apply, this, hD]
  rw [hf] at hc
  unfold xt
  calc perm (flipE (unitVec t)) * diagonal D
      = perm (flipE (unitVec t)) * diagonal D * (perm (flipE (unitVec t)).symm * perm (flipE (unitVec t))) := by
        rw [perm_symm_mul, Matrix.mul_one]
    _ = (perm (flipE (unitVec t)) * diagonal D * perm (flipE (unitVec t)).symm) * perm (flipE (unitVec t)) := by
        simp only [Matrix.mul_assoc]
    _ = diagonal D * perm (flipE (unitVec t)) := by rw [hc]

theorem ht_diag_ht (t : Fin n) (D : Q n → ℂ) (hD : ∀ s, D ((flipE (unitVec t)) s) = D s) :
    ht t * diagonal D * ht t = diagonal D := by
  have hzD : zd t * diagonal D = diagonal D * zd t := by
    unfold zd; rw [diagonal_mul_diagonal, diagonal_mul_diagonal]; congr 1; funext s; ring
  have hHD : ht t * diagonal D = diagonal D * ht t := by
    unfold ht
    rw [Matrix.smul_mul, Matrix.mul_smul, Matrix.add_mul, Matrix.mul_add, diag_comm_xt t D hD, hzD]
  rw [hHD, Matrix.mul_assoc, ht_mul_ht, Matrix.mul_one]

/-- G5: exp(c X_t diag D) = H_t exp(c Z_t diag D) H_t for D ignoring bit t. -/
theorem exp_xt_diag (t : Fin n) (D : Q n → ℂ) (hD : ∀ s, D ((flipE (unitVec t)) s) = D s) (c : ℂ) :
    exp (c • (xt t * diagonal D)) = ht t * exp (c • (zd t * diagonal D)) * ht t := by
  have hU : IsUnit (ht t) := ⟨⟨ht t, ht t, ht_mul_ht t, ht_mul_ht t⟩, rfl⟩
  have hinv : (ht t)⁻¹ = ht t := Matrix.inv_eq_right_inv (ht_mul_ht t)
  have hconj : ht t * (c • (zd t * diagonal D)) * ht t = c • (xt t * diagonal D) := by
    -- H (Z D) H = (H Z H)(H D H) = X D, using H Z H = X (from H X H = Z and H^2 = 1)
    have hzx : ht t * zd t * ht t = xt t := by
      rw [← ht_xt_ht t]
      simp only [← Matrix.mul_assoc]
      rw [ht_mul_ht, Matrix.one_mul, Matrix.mul_assoc, ht_mul_ht, Matrix.mul_one]
    rw [Matrix.mul_smul, Matrix.smul_mul]
    congr 1
    calc ht t * (zd t * diagonal D) * ht t
        = (ht t * zd t * ht t) * (ht t * diagonal D * ht t) := by
          simp only [Matrix.mul_assoc]
          rw [← Matrix.mul_assoc (ht t) (ht t), ht_mul_ht, Matrix.one_mul]
      _ = xt t * diagonal D := by rw [hzx, ht_diag_ht t D hD]
  rw [← hconj]
  have := Matrix.exp_conj (ht t) (c • (zd t * diagonal D)) hU
  rw [hinv] at this
  exact this

/-- The diagonal in the frame: Z_t diag(D) = diag(s -> (-1)^{s_t} D(s)). -/
theorem zd_mul_diag (t : Fin n) (D : Q n → ℂ) :
    zd t * diagonal D = diagonal (fun s => (if s t then (-1 : ℂ) else 1) * D s) := by
  unfold zd; rw [diagonal_mul_diagonal]

/-- Z_i commutes with Y_t for i != t (Y_t = i X_t Z_t). -/
theorem zd_comm_yt (i t : Fin n) (h : i ≠ t) : zd i * yt t = yt t * zd i := by
  have hzz : zd i * zd t = zd t * zd i := by
    unfold zd; rw [diagonal_mul_diagonal, diagonal_mul_diagonal]; congr 1; funext s; ring
  unfold yt
  rw [Matrix.mul_smul, Matrix.smul_mul, ← Matrix.mul_assoc, ← xt_comm_zd t i h, Matrix.mul_assoc,
    hzz, ← Matrix.mul_assoc]

/-- The factors Z_i Y_t and Z_j Y_t of the parity walk commute (i, j != t), the premise of W2. -/
theorem walk_factors_comm (i j t : Fin n) (hi : i ≠ t) (hj : j ≠ t) :
    Commute (zd i * yt t) (zd j * yt t) := by
  have hzz : zd i * zd j = zd j * zd i := by
    unfold zd; rw [diagonal_mul_diagonal, diagonal_mul_diagonal]; congr 1; funext s; ring
  unfold Commute SemiconjBy
  calc zd i * yt t * (zd j * yt t) = zd i * (yt t * zd j) * yt t := by simp only [Matrix.mul_assoc]
    _ = zd i * (zd j * yt t) * yt t := by rw [zd_comm_yt j t hj]
    _ = (zd i * zd j) * (yt t * yt t) := by simp only [Matrix.mul_assoc]
    _ = (zd j * zd i) * (yt t * yt t) := by rw [hzz]
    _ = zd j * (zd i * yt t) * yt t := by simp only [Matrix.mul_assoc]
    _ = zd j * (yt t * zd i) * yt t := by rw [zd_comm_yt i t hi]
    _ = zd j * yt t * (zd i * yt t) := by simp only [Matrix.mul_assoc]

end Compress2x4

#print axioms Compress2x4.xt_mul_xt
#print axioms Compress2x4.zd_mul_zd
#print axioms Compress2x4.xt_zd_anticomm
#print axioms Compress2x4.ht_mul_ht
#print axioms Compress2x4.ht_xt_ht
#print axioms Compress2x4.diag_comm_xt
#print axioms Compress2x4.ht_diag_ht
#print axioms Compress2x4.exp_xt_diag
#print axioms Compress2x4.zd_mul_diag
#print axioms Compress2x4.zd_comm_yt
#print axioms Compress2x4.walk_factors_comm

/-
The identities behind every uniformly controlled rotation used by the study (the package's Gray-code chain
and the sparse-Walsh walk of src/c2x4/sparsemux.py), in the bit-vector model of Bits.lean.
genie-opus, phase 2, 2026-10-21.

* `zd`, `xt`, `yt`: Z_i, X_t and Y_t = i X_t Z_t on the n-qubit register.
* `xt_comm_zd`: X_t commutes with Z_i for i != t.
* `cx_conj_zd_target`: CX(i -> t) Z_t CX(i -> t) = Z_i Z_t.
* `cx_conj_yt` (W1): CX(i -> t) Y_t CX(i -> t) = Z_i Y_t -- one CNOT from a control into the target turns the
  target's y rotation generator into the generator controlled by the parity of that control.
* `exp_conj_cx_yt`: hence exp(c Z_i Y_t) = CX exp(c Y_t) CX (exponential of a conjugated generator).
* `exp_sum_commuting` (W2): exp(sum_S A_S) = prod_S exp(A_S) for pairwise commuting A_S (Mathlib), which splits
  exp(-i/2 sum_S a_S Z_S Y_t) into the factors of the parity walk.
-/
import Compress2x4.Peephole

open Matrix NormedSpace

namespace Compress2x4

variable {n : ℕ}

/-- Z on qubit i. -/
noncomputable def zd (i : Fin n) : Matrix (Q n) (Q n) ℂ :=
  diagonal fun s => if s i then -1 else 1

/-- X on qubit t. -/
noncomputable def xt (t : Fin n) : Matrix (Q n) (Q n) ℂ := perm (flipE (unitVec t))

/-- Y on qubit t, Y = i X Z. -/
noncomputable def yt (t : Fin n) : Matrix (Q n) (Q n) ℂ := Complex.I • (xt t * zd t)

theorem flipE_unitVec_apply_ne (t i : Fin n) (h : i ≠ t) (s : Q n) :
    (flipE (unitVec t)).symm s i = s i := by
  simp [flipE, bxor, unitVec, h]

theorem xt_comm_zd (t i : Fin n) (h : i ≠ t) : xt t * zd i = zd i * xt t := by
  have hc := perm_conj_diagonal (flipE (unitVec t)) (fun s => if s i then (-1 : ℂ) else 1)
  have hf : ((fun s : Q n => if s i then (-1 : ℂ) else 1) ∘ (flipE (unitVec t)).symm) =
      (fun s => if s i then -1 else 1) := by
    funext s
    simp only [Function.comp_apply, flipE_unitVec_apply_ne t i h s]
  rw [hf] at hc
  unfold xt zd
  calc perm (flipE (unitVec t)) * diagonal (fun s => if s i then (-1 : ℂ) else 1)
      = perm (flipE (unitVec t)) * diagonal (fun s => if s i then (-1 : ℂ) else 1) *
          (perm (flipE (unitVec t)).symm * perm (flipE (unitVec t))) := by
        rw [perm_symm_mul, Matrix.mul_one]
    _ = (perm (flipE (unitVec t)) * diagonal (fun s => if s i then (-1 : ℂ) else 1) *
          perm (flipE (unitVec t)).symm) * perm (flipE (unitVec t)) := by
        simp only [Matrix.mul_assoc]
    _ = _ := by rw [hc]

theorem cx_conj_zd_target (i t : Fin n) (hit : i ≠ t) :
    perm (cxE i t hit) * zd t * perm (cxE i t hit).symm = zd i * zd t := by
  unfold zd
  rw [perm_conj_diagonal, diagonal_mul_diagonal]
  congr 1
  funext s
  simp only [Function.comp_apply, cxE_symm, cxE_apply, cxFun, ite_true]
  cases s t <;> cases s i <;> simp

theorem cx_conj_xt_target (i t : Fin n) (hit : i ≠ t) :
    perm (cxE i t hit) * xt t * perm (cxE i t hit).symm = xt t := by
  unfold xt
  rw [cx_comm_flip_target i t hit, Matrix.mul_assoc, perm_mul_symm, Matrix.mul_one]

/-- W1: one CNOT from control i into the target turns Y_t into Z_i Y_t. -/
theorem cx_conj_yt (i t : Fin n) (hit : i ≠ t) :
    perm (cxE i t hit) * yt t * perm (cxE i t hit).symm = zd i * yt t := by
  have key : perm (cxE i t hit) * (xt t * zd t) * perm (cxE i t hit).symm =
      (perm (cxE i t hit) * xt t * perm (cxE i t hit).symm) *
        (perm (cxE i t hit) * zd t * perm (cxE i t hit).symm) := by
    simp only [Matrix.mul_assoc]
    rw [← Matrix.mul_assoc (perm (cxE i t hit).symm) (perm (cxE i t hit)), perm_symm_mul,
      Matrix.one_mul]
  unfold yt
  rw [Matrix.mul_smul, Matrix.smul_mul, key, cx_conj_xt_target, cx_conj_zd_target,
    ← Matrix.mul_assoc, xt_comm_zd t i hit, Matrix.mul_assoc, Matrix.mul_smul]

/-- The exponential form used by the circuits: exp(c Z_i Y_t) = CX exp(c Y_t) CX. -/
theorem exp_conj_cx_yt (i t : Fin n) (hit : i ≠ t) (c : ℂ) :
    exp (c • (zd i * yt t)) =
      perm (cxE i t hit) * exp (c • yt t) * perm (cxE i t hit).symm := by
  have hU : IsUnit (perm (cxE i t hit)) :=
    ⟨⟨perm (cxE i t hit), perm (cxE i t hit).symm, perm_mul_symm _, perm_symm_mul _⟩, rfl⟩
  have hinv : (perm (cxE i t hit))⁻¹ = perm (cxE i t hit).symm :=
    Matrix.inv_eq_right_inv (perm_mul_symm _)
  rw [← hinv, ← Matrix.exp_conj _ _ hU, hinv, Matrix.mul_smul, Matrix.smul_mul, cx_conj_yt]

/-- W2: the exponential of a sum of pairwise commuting generators is the product of the exponentials. -/
theorem exp_sum_commuting {ι : Type*} (s : Finset ι) (f : ι → Matrix (Q n) (Q n) ℂ)
    (h : (s : Set ι).Pairwise (fun a b => Commute (f a) (f b))) :
    exp (∑ i ∈ s, f i) = s.noncommProd (fun i => exp (f i))
      (fun _ hi _ hj _ => (h.forall₂ hi hj).exp) :=
  Matrix.exp_sum_of_commute s f h

end Compress2x4

#print axioms Compress2x4.xt_comm_zd
#print axioms Compress2x4.cx_conj_zd_target
#print axioms Compress2x4.cx_conj_yt
#print axioms Compress2x4.exp_conj_cx_yt
#print axioms Compress2x4.exp_sum_commuting

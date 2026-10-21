/-
JW-sign conjugation (C4 step 3, hopframe.jwc_framed_gates; genie-opus, 2026-10-21).

* `pz`: the one-qubit Z.
* `z_ry_z`: Z Ry(phi) Z = Ry(-phi).
* `cz_conj_ucr`: for a uniformly controlled rotation sum_c |c><c| (x) Ry(theta_c) (as a block-diagonal matrix over the
  control labels c) and a further control bit p, conjugating by CZ(p, t) = diag over (p, c) of (if p then Z else 1)
  gives Ry(theta_c) on p = 0 and Ry(-theta_c) on p = 1: one CZ pair implements the sign (-1)^p of every angle.
* `neg_generator_conj`: if exp(theta A) = B^T P(theta) B with P(theta) = exp(theta L) (bipartite block rounds,
  B theta-independent), then exp(theta (-A)) = B^T P(-theta) B, i.e. the sign of the generator (the JW parity) only
  negates the middle pair rotations; it is stated for any invertible frame B (exp_conj_frame).
-/
import Compress2x4.Reach
import Compress2x4.Exp
import Compress2x4.Bits

open Matrix NormedSpace

namespace Compress2x4

/-- One-qubit Z. -/
def pz : Matrix (Fin 2) (Fin 2) ℂ := !![1, 0; 0, -1]

theorem z_ry_z (φ : ℝ) : pz * Ry φ * pz = Ry (-φ) := by
  have hc : Real.cos (-φ / 2) = Real.cos (φ / 2) := by rw [neg_div, Real.cos_neg]
  have hs : Real.sin (-φ / 2) = -Real.sin (φ / 2) := by rw [neg_div, Real.sin_neg]
  ext i j
  fin_cases i <;> fin_cases j <;> simp [pz, Ry, hc, hs, Matrix.mul_apply, Fin.sum_univ_two]

theorem cz_conj_ucr {c : Type*} [Fintype c] [DecidableEq c] (θ : c → ℝ) :
    blockDiagonal (fun pc : Bool × c => if pc.1 then pz else (1 : Matrix (Fin 2) (Fin 2) ℂ)) *
        blockDiagonal (fun pc : Bool × c => Ry (θ pc.2)) *
        blockDiagonal (fun pc : Bool × c => if pc.1 then pz else (1 : Matrix (Fin 2) (Fin 2) ℂ)) =
      blockDiagonal (fun pc : Bool × c => if pc.1 then Ry (-θ pc.2) else Ry (θ pc.2)) := by
  rw [← blockDiagonal_mul, ← blockDiagonal_mul]
  congr 1
  funext pc
  by_cases hp : pc.1 = true
  · simp only [hp, ite_true]; exact z_ry_z (θ pc.2)
  · simp [hp]

theorem neg_generator_conj {m : Type*} [Fintype m] [DecidableEq m] (B L : Matrix m m ℂ) (hB : IsUnit B)
    (A : Matrix m m ℂ) (hA : A = B⁻¹ * L * B) (t : ℂ) :
    exp (t • (-A)) = B⁻¹ * exp ((-t) • L) * B := by
  have hBi : IsUnit B⁻¹ := (Matrix.isUnit_nonsing_inv_iff).mpr hB
  have hinv : B⁻¹⁻¹ = B := Matrix.nonsing_inv_nonsing_inv B ((Matrix.isUnit_iff_isUnit_det B).mp hB)
  have h1 : t • (-A) = B⁻¹ * ((-t) • L) * B⁻¹⁻¹ := by
    rw [hinv, hA, Matrix.mul_smul, Matrix.smul_mul]; simp [neg_smul, smul_neg]
  rw [h1, exp_conj_frame B⁻¹ ((-t) • L) hBi, hinv]

/-- Flags (linsynth._flag_gates): a uniformly controlled rotation commutes with any phase that is diagonal in its
control labels (here: the relative phase of a Margolus/RC3X AND whose inputs and output are all controls of the
multiplexor), so a relative-phase compute ... uncompute pair around it cancels (with `relphase_cancel`). -/
theorem ucr_comm_ctrl_phase {c : Type*} [Fintype c] [DecidableEq c] (R : c → Matrix (Fin 2) (Fin 2) ℂ)
    (d : c → ℂ) :
    blockDiagonal R * blockDiagonal (fun i => d i • (1 : Matrix (Fin 2) (Fin 2) ℂ)) =
      blockDiagonal (fun i => d i • (1 : Matrix (Fin 2) (Fin 2) ℂ)) * blockDiagonal R := by
  rw [← blockDiagonal_mul, ← blockDiagonal_mul]
  congr 1
  funext i
  simp [Matrix.mul_smul, Matrix.smul_mul]

/-- CNOT-run resynthesis (peephole.resynth_cx_runs): two CNOT lists that are the same relabelling of the basis
labels (checked exhaustively by the code) are the same operator. -/
theorem perm_eq_of_fun_eq {n : ℕ} (σ τ : Q n ≃ Q n) (h : ∀ s, σ s = τ s) : perm σ = perm τ := by
  have : σ = τ := Equiv.ext h
  rw [this]

end Compress2x4

#print axioms Compress2x4.perm_eq_of_fun_eq
#print axioms Compress2x4.ucr_comm_ctrl_phase
#print axioms Compress2x4.z_ry_z
#print axioms Compress2x4.cz_conj_ucr
#print axioms Compress2x4.neg_generator_conj

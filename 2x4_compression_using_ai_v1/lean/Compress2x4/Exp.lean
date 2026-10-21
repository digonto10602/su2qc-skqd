/-
Exponential lemmas behind the corner-frame (CF1/CF2) and restricted (F1) constructions
(genie-opus, phase 2, 2026-10-21).

* `exp_intertwine`: if A P = P C then exp A * P = P * exp C.
* `exp_agree_of_intertwine`: two generators that intertwine the same P with the same C have equal
  exponentials on the range of P.  With P the projector onto the local codeword space (or onto the
  frame image of it) this is the statement "a generator that is only correct on the codeword space (and
  arbitrary elsewhere -- the don't-care slots) has the correct exponential on that space".
* `exp_agree_on_invariant`: the projector form: P^2 = P, A P = B P and B P = P B P imply
  exp A * P = exp B * P.
* `exp_agree_mulVec`: the vector form used by the circuits: for every v with P v = v,
  exp A v = exp B v.
* `exp_conj_frame`: exp (U G U^-1) = U exp(G) U^-1 for an invertible frame U (Mathlib's `exp_conj`).
-/
import Mathlib

open Matrix NormedSpace

namespace Compress2x4

variable {m : Type*} [Fintype m] [DecidableEq m]

set_option backward.isDefEq.respectTransparency false in
/-- Intertwining passes to the exponential. -/
theorem exp_intertwine (A P C : Matrix m m ℂ) (h : A * P = P * C) :
    exp A * P = P * exp C := by
  have hs : SemiconjBy P C A := h.symm
  have := (open scoped Norms.Operator in hs.exp_right)
  exact this.symm

/-- Two generators that intertwine P with the same C have the same exponential on the range of P. -/
theorem exp_agree_of_intertwine (A B P C : Matrix m m ℂ) (hA : A * P = P * C)
    (hB : B * P = P * C) : exp A * P = exp B * P := by
  rw [exp_intertwine A P C hA, exp_intertwine B P C hB]

/-- Projector form: if P is idempotent, A and B agree on the range of P, and B maps the range of P
into itself, then exp A and exp B agree on the range of P. -/
theorem exp_agree_on_invariant (A B P : Matrix m m ℂ) (hP : P * P = P) (hAB : A * P = B * P)
    (hinv : B * P = P * B * P) : exp A * P = exp B * P := by
  have hB : B * P = P * (P * B * P) := by
    rw [hinv, ← Matrix.mul_assoc, ← Matrix.mul_assoc, hP]
  have hA : A * P = P * (P * B * P) := by rw [hAB, hB]
  exact exp_agree_of_intertwine A B P (P * B * P) hA hB

/-- Vector form: the exponentials agree on every vector fixed by the projector. -/
theorem exp_agree_mulVec (A B P : Matrix m m ℂ) (hP : P * P = P) (hAB : A * P = B * P)
    (hinv : B * P = P * B * P) (v : m → ℂ) (hv : P *ᵥ v = v) :
    exp A *ᵥ v = exp B *ᵥ v := by
  rw [← hv, Matrix.mulVec_mulVec, Matrix.mulVec_mulVec, exp_agree_on_invariant A B P hP hAB hinv]

/-- Changing frame: the exponential of a conjugated generator is the conjugated exponential. -/
theorem exp_conj_frame (U G : Matrix m m ℂ) (hU : IsUnit U) :
    exp (U * G * U⁻¹) = U * exp G * U⁻¹ :=
  Matrix.exp_conj U G hU

/-- Scalar multiples: (t G) intertwines P with t C when G intertwines P with C, so the restriction
lemmas apply at every angle theta (generator -i theta h). -/
theorem smul_intertwine (t : ℂ) (A P C : Matrix m m ℂ) (h : A * P = P * C) :
    (t • A) * P = P * (t • C) := by
  rw [Matrix.smul_mul, h, Matrix.mul_smul]

end Compress2x4

#print axioms Compress2x4.exp_intertwine
#print axioms Compress2x4.exp_agree_of_intertwine
#print axioms Compress2x4.exp_agree_on_invariant
#print axioms Compress2x4.exp_agree_mulVec
#print axioms Compress2x4.exp_conj_frame
#print axioms Compress2x4.smul_intertwine

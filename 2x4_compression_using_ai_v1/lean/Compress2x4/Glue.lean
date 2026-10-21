/-
Reviewer note 3 (reviews/001 §5): the glue between "a local term circuit W is exact on the touched blocks" and
"the circuit is exact on the span of the reachable basis states", plus the reachability map itself
(genie-opus, C4, 2026-10-21).

* `kron_one_mulVec_apply`: ((W ⊗ 1) v)(i, e) = Σ_j W i j v(j, e)  (index type σ × τ: local × environment).
* `kron_agree_of_support` (G1): if W and U have equal columns j ∈ T (T = the local strings of the touched blocks),
  then W ⊗ 1 and U ⊗ 1 agree on every vector supported on {p | p.1 ∈ T} -- the span of the reachable basis states
  whose local parts lie in T.
* `commute_proj_of_block` and `exp_mulVec_supported` (G2): if a generator M has no element between C and its
  complement (C a union of connected components of the graph of M), then exp M maps vectors supported on C to
  vectors supported on C.  This is the reachability map U_i(span S_i) ⊆ span S_{i+1} of reach.py, with
  S_{i+1} = the union of the components of term i's graph that meet S_i.
* `circuit_exact_on_reachable` (G3): the induction over the terms (L5 = `agree_on_reachable_n`) instantiated with
  vector sets "supported on S_i": per-term column agreement on T_i ⊇ local parts of S_i, block-diagonality of the
  exact steps with respect to S_{i+1} ⊇ S_i, and S_0 = {reference} give: the candidate circuit equals the exact
  product on the reference basis vector.
The qubit layout enters only through an equivalence ι ≃ σ_i × τ_i per term (`Matrix.reindex`), i.e. the choice of
which qubits are the term's support; G3 is stated with these equivalences.
-/
import Compress2x4.Reach

open Matrix NormedSpace
open scoped Kronecker

namespace Compress2x4

section Kron

variable {σ τ : Type*} [Fintype σ] [DecidableEq σ] [Fintype τ] [DecidableEq τ]

theorem kron_one_mulVec_apply (W : Matrix σ σ ℂ) (v : σ × τ → ℂ) (i : σ) (e : τ) :
    ((W ⊗ₖ (1 : Matrix τ τ ℂ)) *ᵥ v) (i, e) = ∑ j, W i j * v (j, e) := by
  simp only [Matrix.mulVec, dotProduct, Matrix.kroneckerMap_apply, Fintype.sum_prod_type,
    Matrix.one_apply]
  apply Finset.sum_congr rfl
  intro j _
  rw [Finset.sum_eq_single e]
  · simp
  · intro b _ hb
    simp [Ne.symm hb]
  · intro h; exact absurd (Finset.mem_univ e) h

theorem kron_agree_of_support (W U : Matrix σ σ ℂ) (T : Set σ)
    (hcol : ∀ i, ∀ j ∈ T, W i j = U i j) (v : σ × τ → ℂ) (hv : ∀ p : σ × τ, p.1 ∉ T → v p = 0) :
    (W ⊗ₖ (1 : Matrix τ τ ℂ)) *ᵥ v = (U ⊗ₖ (1 : Matrix τ τ ℂ)) *ᵥ v := by
  funext p
  obtain ⟨i, e⟩ := p
  rw [kron_one_mulVec_apply, kron_one_mulVec_apply]
  apply Finset.sum_congr rfl
  intro j _
  by_cases hj : j ∈ T
  · rw [hcol i j hj]
  · rw [hv (j, e) hj]; simp

end Kron

section Block

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

/-- The diagonal projector onto the coordinates in C. -/
noncomputable def projOn (C : Set ι) [DecidablePred (· ∈ C)] : Matrix ι ι ℂ :=
  diagonal fun i => if i ∈ C then 1 else 0

theorem commute_proj_of_block (M : Matrix ι ι ℂ) (C : Set ι) [DecidablePred (· ∈ C)]
    (hM : ∀ i j, (i ∈ C ∧ j ∉ C) ∨ (i ∉ C ∧ j ∈ C) → M i j = 0) : Commute M (projOn C) := by
  show M * projOn C = projOn C * M
  ext i j
  simp only [projOn, Matrix.mul_diagonal, Matrix.diagonal_mul]
  by_cases hi : i ∈ C <;> by_cases hj : j ∈ C
  · simp [hi, hj]
  · simp [hi, hj, hM i j (Or.inl ⟨hi, hj⟩)]
  · simp [hi, hj, hM i j (Or.inr ⟨hi, hj⟩)]
  · simp [hi, hj]

theorem projOn_mulVec_of_support (C : Set ι) [DecidablePred (· ∈ C)] (v : ι → ℂ)
    (hv : ∀ i, i ∉ C → v i = 0) : projOn C *ᵥ v = v := by
  funext i
  simp only [projOn, Matrix.mulVec_diagonal]
  by_cases hi : i ∈ C
  · simp [hi]
  · simp [hi, hv i hi]

set_option backward.isDefEq.respectTransparency false in
theorem exp_mulVec_supported (M : Matrix ι ι ℂ) (C : Set ι) [DecidablePred (· ∈ C)]
    (hM : ∀ i j, (i ∈ C ∧ j ∉ C) ∨ (i ∉ C ∧ j ∈ C) → M i j = 0) (v : ι → ℂ)
    (hv : ∀ i, i ∉ C → v i = 0) : ∀ i, i ∉ C → (exp M *ᵥ v) i = 0 := by
  have hc : Commute M (projOn C) := commute_proj_of_block M C hM
  have he : Commute (exp M) (projOn C) := (open scoped Norms.Operator in hc.exp_left)
  have hfix : projOn C *ᵥ (exp M *ᵥ v) = exp M *ᵥ v := by
    rw [Matrix.mulVec_mulVec, ← he.eq, ← Matrix.mulVec_mulVec, projOn_mulVec_of_support C v hv]
  intro i hi
  rw [← hfix]
  simp [projOn, Matrix.mulVec_diagonal, hi]

end Block

section Circuit

variable {ι : Type*} [Fintype ι] [DecidableEq ι]

/-- G1 on the global register: the term's support is chosen by an equivalence e : ι ≃ σ × τ (which qubits are
local), and the candidate W ⊗ 1 agrees with the exact U ⊗ 1 on every vector supported on the strings whose local
part lies in T. -/
theorem reindex_kron_agree {σ τ : Type*} [Fintype σ] [DecidableEq σ] [Fintype τ] [DecidableEq τ]
    (e : ι ≃ σ × τ) (W U : Matrix σ σ ℂ) (T : Set σ) (hcol : ∀ i, ∀ j ∈ T, W i j = U i j)
    (v : ι → ℂ) (hv : ∀ p, (e p).1 ∉ T → v p = 0) :
    reindex e.symm e.symm (W ⊗ₖ (1 : Matrix τ τ ℂ)) *ᵥ v =
      reindex e.symm e.symm (U ⊗ₖ (1 : Matrix τ τ ℂ)) *ᵥ v := by
  simp only [Matrix.reindex_apply, Equiv.symm_symm, Matrix.submatrix_mulVec_equiv]
  congr 1
  apply kron_agree_of_support W U T hcol
  intro q hq
  simp only [Function.comp_apply]
  apply hv
  simpa using hq

/-- G3: per-step agreement on vectors supported on S_i and the reachability map S_i -> S_{i+1} of the exact steps
give: the candidate circuit equals the exact one on the reference basis vector (and every vector supported on S_0). -/
theorem circuit_exact_on_reachable (V U : ℕ → (ι → ℂ) → (ι → ℂ)) (S : ℕ → Set ι)
    (hagree : ∀ i v, (∀ p, p ∉ S i → v p = 0) → V i v = U i v)
    (hmap : ∀ i v, (∀ p, p ∉ S i → v p = 0) → ∀ p, p ∉ S (i + 1) → U i v p = 0)
    (v : ι → ℂ) (hv : ∀ p, p ∉ S 0 → v p = 0) : ∀ k, run V k v = run U k v := by
  intro k
  have h := agree_on_reachable_n U V (fun i => {w : ι → ℂ | ∀ p, p ∉ S i → w p = 0})
    (fun i x hx => hagree i x hx) (fun i x hx => hmap i x hx) k v hv
  exact h.1

/-- The reference basis vector is supported on {r}. -/
theorem single_supported (r : ι) (S : Set ι) (hr : r ∈ S) :
    ∀ p, p ∉ S → (Pi.single r (1 : ℂ) : ι → ℂ) p = 0 := by
  intro p hp
  have : p ≠ r := fun h => hp (h ▸ hr)
  simp [Pi.single_apply, this]

/-- G2 in the form G3 needs: an exact step exp(M) with M block diagonal for C = S_{i+1} ⊇ S_i maps vectors
supported on S_i to vectors supported on S_{i+1}. -/
theorem exp_step_maps (M : Matrix ι ι ℂ) (Si Sj : Set ι) [DecidablePred (· ∈ Sj)] (hsub : Si ⊆ Sj)
    (hM : ∀ i j, (i ∈ Sj ∧ j ∉ Sj) ∨ (i ∉ Sj ∧ j ∈ Sj) → M i j = 0) (v : ι → ℂ)
    (hv : ∀ p, p ∉ Si → v p = 0) : ∀ p, p ∉ Sj → (exp M *ᵥ v) p = 0 :=
  exp_mulVec_supported M Sj hM v (fun p hp => hv p (fun h => hp (hsub h)))

end Circuit

end Compress2x4

#print axioms Compress2x4.kron_one_mulVec_apply
#print axioms Compress2x4.kron_agree_of_support
#print axioms Compress2x4.commute_proj_of_block
#print axioms Compress2x4.exp_mulVec_supported
#print axioms Compress2x4.reindex_kron_agree
#print axioms Compress2x4.circuit_exact_on_reachable
#print axioms Compress2x4.single_supported
#print axioms Compress2x4.exp_step_maps
#print axioms Compress2x4.projOn_mulVec_of_support

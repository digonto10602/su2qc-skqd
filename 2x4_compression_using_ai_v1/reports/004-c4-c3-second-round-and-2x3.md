# 004 — C4: one more 2x4 round (v2 families) and C3: the 2x3 compressed families

- **Date:** 2026-10-21.  **Author:** genie-opus (Opus 5.5, high effort), study folder `2x4_compression_using_ai_v1/`.
- **Commits:** family loader API `f0b2363` (notes/009 `a07ba6d`); C4 code + frozen v2 and 2x3 families `390629e`;
  notes/009 update `040c95d`; this report and the remaining checks: the commit that adds this file.
- **Plan in force:** `notes/010-c4-c3-work-plan.md` (written for this round), under the owner decisions
  `notes/008` (naming/separation rule; C3, C4 signed) and the planner's step list `notes/007` §6.
- **Related:** `reports/003-full-compression-report.md` (v1), `reviews/001-independent-verification.md` (notes 1–7),
  `notes/009-family-api.md` (loader for the noise agent).
- **Where the numbers come from:** every number names its JSON.  The tables of this report are collected by
  `python scripts/report004_tables.py` → `data/report004_tables.json` (a re-read of the run outputs, nothing recomputed).

**Names** (owner rule, notes/008).  The package's frozen circuits stay as they are and are not replaced anywhere.

| name | what it is |
|---|---|
| `compressed_circuit_llm_2x4_classA_v1` / `_classB_v1` | the it5 families the reviewer verified (aliases without suffix still point here) |
| `compressed_circuit_llm_2x4_classA_v2` / `_classB_v2` | this round (C4) |
| `compressed_circuit_llm_2x3_classA` / `_classB` | the 2x3 families (C3) |

Class A = operator-exact (correct on every codeword).  Class B = exact only on the circuit's own reference input
(the binding use limit of reviews/001 note 1 is unchanged: prepare own reference, one coarse step, sample).

---

## Glossary (terms used below; each is also defined where it first appears)

| term | meaning |
|---|---|
| ZZ count | number of two-qubit gates (CX, CZ, controlled phase); each becomes one Quantinuum ZZPhase |
| two-qubit depth | longest chain of two-qubit gates, one-qubit gates free (as-soon-as-possible schedule) |
| multiplexor | a rotation of one "target" qubit whose angle depends on several "control" qubits |
| Walsh support | number of nonzero coefficients $a_S$ in $\theta(c)=\sum_S a_S(-1)^{\lvert S\cap c\rvert}$ of a multiplexor's angle table; in "walk form" each nonempty mask costs at least one CNOT |
| skeleton | the gate list with the angles removed (gate names and qubits only) |
| clean ancilla | a qubit that is $\lvert0\rangle$ on every codeword because its information is stored elsewhere |
| flag (my label) | a Boolean AND of 2–3 control bits written into a clean ancilla so that a multiplexor's nonzero entries separate from its zero entries |
| MILP | mixed-integer linear programme; here solved by HiGHS through `scipy.optimize.milp` |
| JW sign | the Jordan–Wigner sign $(-1)^{\text{parity of the sites between the hop's ends}}$ |
| $f$ | the package's gate-only clean-shot fraction $f=(1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{\rm ro})^{n_m}$ (`skqd.device_req.clean_shot_fraction`) |

---

## 1. What was asked

**Part 1 — C4.**  One more 2x4 round with a hard stop (steps 1–3 of notes/007 §6 and the multiplexor certificates
done, or two laptop-days): (1) an OR'd "any corner dark" flag for the plaquettes; (2) an exact minimum-Walsh-support
MILP per multiplexor, recorded as `certified_optimal` within the class; (3) cheaper hops; (4) cross-term frame
merging; (5) depth by interleaving; (6) a strictly $k$-independent skeleton.  Address reviewer note 2 (rounding
term in the certified bound) and note 3 (Lean glue from "local term exact on touched blocks" to "the 28-qubit
term agrees on the span of the reachable states").  New families as v2; v1 untouched; verify all 75 circuits of
each class.  Expose `get_family(name)` early for the noise agent.

**Part 2 — C3.**  Parameterise the code by the lattice (no fork); build the 2x3 class A and class B families for
the circuit list and $k$ range of the frozen 2x3 family; verify against the package's 2x3 coarse states at the same
bar, also with an independent qiskit-aer statevector on all circuits; compare with the frozen 2x3 family (2 158 ZZ);
compute $f$ with the package formula for information; keep the 2x3 outputs separate.

## 2. Actions taken

### 2.1 Loader API first (for the noise agent)

`src/c2x4/families.py` (shim `families.py` in the study root): `get_family(name, measure=False)` →
`[(circuit_id, qiskit.QuantumCircuit, metadata)]`, plus `get_family_ir`, `family_header`, `exact_target`,
`available_families`.  Each family is a frozen file `data/families/<name>.json.gz` written once by
`scripts/freeze_family.py`, which refuses to write unless every circuit's two-qubit count and depth equal its
verification record; the loader re-checks a sha256 per circuit.  Committed at `f0b2363` (v1), documented in
`notes/009` (`a07ba6d`), extended with v2 and 2x3 at `390629e` / `040c95d` without changing the signature.
`tests/test_families.py` (loads, counts, one state check per 2x4 family) passes.

### 2.2 Step 6 first: an angle-linear synthesis (`src/c2x4/linsynth.py`)

**Diagnosis.**  In v1 the two-qubit count of a (reference, term) varied with $k$: class A 1 736–1 740 within one
reference, class B `B0_ref1338` 760/762 (`data/report004_tables.json` `2x4.A_v1.k_dependent_references_by_count`:
all 15 class-A references; `B_v1`: `B0_ref1338`).  Cause: every $\theta$-dependent rotation reached the multiplexor
synthesis as a $2\times2$ unitary at the circuit's own angle, and structural decisions (control reduction by
numerical equality of slot unitaries, axis orientation, zero tests) were taken on those unitaries.

**Fix.**  A $\theta$-dependent two-level operation is carried as its generator: `LinRot(G, θ)` means
$e^{-i\theta G}$ with $G$ a fixed traceless Hermitian $2\times2$ matrix.  Target choice, control reduction, Walsh
support and walk order are decided on the $\theta$-free coefficient table $c(\text{slot})$ with slot unitary
$R_{\hat n}(\theta c)$; only the emitted angles are multiplied by $\theta$.  The package's bipartite block rounds are
re-implemented (`lin_block_rounds`): $e^{\theta A}=B^{T}P(\theta)B$ with $B$ $\theta$-independent and $P(\theta)$ the
pair rotations $e^{\theta\,[[0,d_i],[-d_i,0]]}$.  One bug on the way: I first used the singular values $S_i$ for
$d_i$, but the gauge fix of $U,V$ flips signs, so $d_i=\pm S_i$; the per-block reconstruction test exposed it
(deviation $\propto\theta$), fixed by $D=U^{T}KV$.  Unit tests `tests/test_linsynth.py` (3 pass).

**Result.**  The skeleton (names and qubits) is identical for $k=1..5$ in every reference of both v2 classes and for
$k=1..4$ in both 2x3 classes (`skeleton_k_independent.all = true` in all four eval files, §3).  So gate Q0P's
criterion Q2 ("ZZ count equal across $k$ within a reference") holds as written.

### 2.3 Step 2: exact minimum Walsh support by MILP (`src/c2x4/certify.py`, `scripts/certify_family.py`)

For a reduced table on $m$ controls with fixed slots $F$ and free slots, the free angles $y$ ($\lvert y_i\rvert\le
M_\theta=8\pi$) give $a=a_0+Ky$; binaries $z_S$ with $\lvert a_S\rvert\le M_S z_S$ ($M_S$ valid on the whole box);
minimise $\sum_{S\neq\emptyset}z_S$.  The MILP's dual bound is a lower bound on the support of every completion
in that box; an upper bound is accepted only after an exact least-squares re-solve on the support (residual
$\le10^{-12}$).  `certified_optimal` := support used = MILP lower bound.  A closed walk through $s$ nonzero masks
has $s+1$ edges, so walk CNOTs $\ge s+1$ ("walk lower bound").  Tables with no free slot have a unique Walsh
transform and are certified without a MILP.  The MILP is also offered as a synthesis option (`*_milp`
proposals); it rarely beat the LP heuristic and sometimes lost on walk length (`data/loop_it6a.log`).

### 2.4 Step 3: cheaper hops (`src/c2x4/hopframe.py`, `linsynth.py`)

What I measured first: in the bright-rotated vertex frame every pair coupling of every hop is $d=0.5$ or $d=1.0$
(the $\theta$-multiplexor tables hold $\lvert c\rvert=2d\in\{0,1,2\}$ for all ten 2x4 hops and all seven 2x3 hops,
`scripts/hop_coeff_values.py` → `data/hop_coefficient_values.json`), although the Hamiltonian's own hop matrix
elements take three to nine distinct magnitudes between 0.177 and 0.707 (same file, `distinct_abs_hamiltonian_elements`).  So the
multiplexor cost (31–41 masks for hop3 in v1) came from the **zero** slots — occupied strings with the same flip
pattern that must not rotate — and from the label-dependent signs, not from the magnitudes.

1. **JW sign as a conjugation** (`jwc_framed_gates`, label JWC): fold the JW parity into one qubit $p$, synthesise
   $e^{-i\theta h_0}$ without the JW bits, and conjugate every $\theta$-multiplexor's target by CZ$(p,t)$ (Lean
   `z_ry_z`, `cz_conj_ucr`, `neg_generator_conj`).  Alone it gained little (hop3 256 → 264 with LP, 244 with MILP;
   `data/loop_it6a.log`): a parity sign only shifts masks, it does not add them.
2. **Clean ancilla + flags** (`vertex_bright_frame_clean`, `_flag_variants`, labels `cb0/cb1`): the hopping link is
   stored at both ends; clearing one copy by a CX from the other (before the other end's parity fold) gives a clean
   ancilla for 1 CX each way.  For each multiplexor the synthesis also tries a flag $g=$ AND of 2–3 control literals
   that is 1 on every nonzero slot, written into the ancilla by a relative-phase AND (Margolus 3 CX or RC3X 6 CX;
   the phase is diagonal on the multiplexor's controls and cancels, Lean `ucr_comm_ctrl_phase`, `relphase_cancel`);
   constant multiplexors go through the same path.  hop3 256 → 168, hop4/hop7 166 → 130, hop5 178 → 134.
3. "Share the compression CNOTs" and "product-form tables": the LP already finds the product-form supports (the
   certificates in §3.3 show the supports are minimal in their class), so nothing separate was built.

### 2.5 Step 1: the OR'd dark flag for the plaquettes — evaluated, not built

The certificates show where the plaquette cost sits (`data/cert_it6_operator.json`): plaq0 and plaq2's corner-frame
multiplexor already has 5 controls and a fully fixed table, 31 masks, walk 32 CNOTs — the same as the planner's
target for the $(x_1..x_4,G)$ table ($2^5$ masks).  Only plaq1 is above: 7 controls, support 85, walk 92 CNOTs.
Replacing it by the $G$-table needs (i) the dark indicators $d_c=\bar x_c\wedge c_c\wedge q_c$ (3 inputs; RC3X 6 CX
instead of the present Margolus 3 CX for $c_c\wedge q_c$: $+3$ per corner each way, $+24$), (ii) a fifth clean qubit
(none is left inside the 16-qubit support after the four flags: $+2$ CX from a link copy outside), (iii) $G=\bigvee_c
d_c$, a 4-input OR, cost $c_4$ each way.  Net change $(32-92)+24+2+2c_4=-34+2c_4$ CX.  With an optimistic
$c_4=6$ (the cost of a 3-input relative-phase AND; **an assumption, not a bound I can prove**) the gain is at most 22
CX on one term, about 1.5 % of class A.  I judged that not worth a fifth support qubit and a new 4-input gadget under
the hard stop; the MILP option (step 2) took plaq1 from 220 to 202 instead.

### 2.6 Steps 4 and 5

- **Step 4, partly:** `peephole.resynth_cx_runs` replaces every maximal run of consecutive CX gates by a shorter
  CNOT circuit with the same permutation (Gaussian elimination on $A$ and on $A^T$; the equality is checked
  exhaustively on all $2^{\lvert Q\rvert}$ labels; Lean `perm_eq_of_fun_eq`).  Finishing pass `pp2` = peephole →
  resynthesis → peephole.  Applied to the frozen v1 circuits it removes 13–14 (class A) and 2–11 (class B) CX per circuit
  (`scripts/cxr_gain_v1.py` → `data/cxr_gain_v1.json`, all 75 + 75).  A full "synthesise $F_{i+1}F_i^{-1}$" across terms (frames that interleave with
  rotations) was not built.
- **Step 5:** nothing separate was built.  The two-qubit depth is the as-soon-as-possible longest path, so terms on
  disjoint qubits already run in parallel in the count; any further reordering of overlapping terms would change the
  package's target state (notes/007 §4).  The v2 depth drop (below) comes from the new constructions.

### 2.7 Loop, selection, verification, freeze

- Loop iteration 6: `scripts/loop_select.py` (now `--lx`, `--classes`, 30-minute guard); class A
  `data/archive_it6a.json` + `data/archive_it6.json` (`data/loop_it6a.log`, `data/loop_it6_opA.log`), class B in three
  reference batches `data/archive_it6b{0,1,2}.json`, merged by `scripts/merge_archives.py` into
  `data/archive_it6.json`.  Only angle-linear proposals took part, so every winner is $k$-independent.
- Verification: `scripts/eval_family.py --family arch:it6:<class>:pp2 --kmax 5 --prune-tau 1e-15` on all 75 circuits
  per class (certified pruned simulation, now including the rounding term of §2.8); term checks on every codeword
  column (class A) or on the contract columns (class B, `data/eval_arch_it6_input_pp2_terms.json`).
- Certificates: `scripts/certify_family.py` → `data/cert_it6_{operator,input}.json`; a longer (1 500 s) MILP on the
  one open class-A table: `scripts/cert_long_plaq1.py` → `data/cert_it6_operator_plaq1_long.json`.
- Freeze: `compressed_circuit_llm_2x4_class{A,B}_v2` (`390629e`), hashes in notes/009.
- Native: `scripts/native_family.py` (isolated `su2qc-quantinuum` venv, package `ir_to_pytket` → `compile_native(H2-2,
  level 0)`, the package's conversion proof Q1L, `clean_shot_fraction`) on all 75 circuits of each v2 class.
  The package converter has no `cz`; it is rewritten as `cp(π)` (the same matrix) before conversion.
- Independent check: `scripts/verify_aer_family.py` (qiskit-aer statevector, double precision; fusion off for the
  2x3 runs, on for the two 28-qubit runs as in reviews/001; target
  from the package's `coarse_states` with `dt` from `validation/E3.json`; circuits taken through the loader API, i.e.
  exactly what the noise agent receives) on a sample of 28-qubit v2 circuits (§3.2).

### 2.8 Reviewer note 2: the floating-point rounding term

`evaluate.rounding_bound` adds, per non-permutation gate, $\delta=\gamma\lVert G'\rVert_F+\lVert G'-G\rVert_F$ with
$\gamma=\mu+u+\mu u$, $u=2^{-53}$, $\mu=\sqrt2\,\gamma_2=2\sqrt2u/(1-2u)$ (complex product, Higham, *Accuracy and
Stability of Numerical Algorithms*, 2nd ed., Lemma 3.5), $\lVert G'-G\rVert_F\le 2\cdot2u$ for gates built from an
angle (entries within one ulp each; libm assumption) and the measured distance to the unitary polar factor for stored
one-qubit `unitary` matrices.  X, CX and CZ are exact.  The per-pair algebra is proved in Lean (`pair_round_bound`,
`row_sq_le`, `gate_round_sq`, `entry_err_sq`); the sum over gates is `telescoping_bound_mirror`.  The constants $u$,
$\mu$ and the one-ulp libm property are a cited model, not provable in Lean/Mathlib (no IEEE-754 semantics).
The certified bar is now: measured $\max\lvert\Delta\psi\rvert$ + pruned norm + rounding term $<10^{-10}$, and
$(\sqrt{\text{leak}}+\text{pruned}+\text{rounding})^2<10^{-9}$.  For v1, `scripts/rounding_v1.py` →
`data/rounding_v1.json`: largest rounding term $1.56\times10^{-12}$ (class A) and $6.86\times10^{-13}$ (class B);
with it the largest certified deviation is $1.72\times10^{-12}$ and $7.72\times10^{-13}$; 75/75 pass in both classes.

### 2.9 Reviewer note 3: Lean glue (`lean/Compress2x4/Glue.lean`)

Proved (no `sorry`, standard axioms only, `data/c4_lean_build.log`):

| statement | content |
|---|---|
| `kron_one_mulVec_apply` | $((W\otimes1)v)(i,e)=\sum_jW_{ij}v(j,e)$ on the index type $\sigma\times\tau$ (local × environment) |
| `kron_agree_of_support` (G1) | if $W$ and $U$ have equal columns on the touched local strings $T$, then $W\otimes1$ and $U\otimes1$ agree on every vector supported on $\{p:p_1\in T\}$ — the span of the reachable basis states |
| `reindex_kron_agree` | the same on the global register, with the term's support chosen by an equivalence $\iota\simeq\sigma\times\tau$ (`Matrix.reindex`) |
| `commute_proj_of_block`, `projOn_mulVec_of_support`, `exp_mulVec_supported` (G2) | a generator with no element between $C$ and its complement commutes with the projector onto $C$, hence $e^{M}$ maps vectors supported on $C$ to vectors supported on $C$ — the reachability map $U_i(\mathrm{span}\,S_i)\subseteq\mathrm{span}\,S_{i+1}$ |
| `exp_step_maps` | G2 in the form used: $S_i\subseteq S_{i+1}$ and $M$ block-diagonal for $S_{i+1}$ |
| `circuit_exact_on_reachable` (G3), `single_supported` | per-step agreement on vectors supported on $S_i$ + the reachability map ⇒ the candidate circuit equals the exact product on the reference basis vector (instantiates `agree_on_reachable_n`) |

**What remains numerical** (the hypotheses G3 needs for the actual circuits): (a) each term's column agreement on its
touched blocks (the A1 term checks, $\le1.03\times10^{-14}$, §3); (b) that the package's dressed-basis term equals
$h_{\rm loc}\otimes1$ on the codewords (the package's `localize`; confirmed end to end by every circuit check);
(c) the block-diagonality of each term for the specific $S_{i+1}$ (computed by `reach.py` from connected components
with a $10^{-12}$ threshold); (d) the qubit equivalences $e_i$ (bookkeeping, not stated per term in Lean).

Other new Lean statements (`Rounding.lean`, `Conj.lean`): the four rounding lemmas above; `z_ry_z`, `cz_conj_ucr`,
`neg_generator_conj` (JW conjugation); `ucr_comm_ctrl_phase` (flags); `perm_eq_of_fun_eq` (CX resynthesis).  In total
18 new theorems (and the definitions `projOn`, `pz`); `lake build` "Build completed successfully (9059 jobs)", 63 `#print axioms` lines, each of the 18 new theorems
on {propext, Classical.choice, Quot.sound}, no `sorry`/`admit` (`data/c4_lean_build.log`, final rebuild).

### 2.10 Part 2 (C3): the 2x3 families

- `Problem(lx)`: the lattice is a parameter.  2x3 `dt` from the frozen family's manifests
  (`data/quantinuum/circuits_2x3/<id>.manifest.json`: $0.15644331744992473$ at $B=0$, $0.1869734214853983$ at $B=1$),
  identical to `Model(3).reference(4, 2B).dt` (checked by `verify_aer_family.py`: `dt_consistent = true`).
  References from `krylov.references`: 8 at $B=0$ (25, 795, 525, 333, 169, 117, 86, 70), 3 at $B=1$ (57, 29, 27),
  $k=1..4$ — the 44 circuits of `data/quantinuum/circuits_2x3/index.json`.  2x3 caches carry the prefix `L3_`,
  archives and results live in `data/c2x3/`.
- Every proposal ran unchanged at 2x3 (the 2x3 terms are the same types as 2x4's: corner/interior hops, plaquettes
  with two corner and two interior vertices).  Loop `data/c2x3/archive_L3_it1.json` (class A in one run, class B in
  two reference batches, merged), verification `data/c2x3/eval_arch_L3_it1_{operator,input}_pp2_all44_pruned.json`,
  certificates `data/c2x3/cert_L3_it1_{operator,input}.json`, freeze `compressed_circuit_llm_2x3_class{A,B}`,
  independent Aer statevector on **all 44** circuits of each class `data/c2x3/aer_compressed_circuit_llm_2x3_class{A,B}.json`,
  native `data/c2x3/native_compressed_circuit_llm_2x3_class{A,B}.json`.

## 3. What the result means

### 3.1 2x4: v1 versus v2 (all 75 circuits per class, my certified harness)

| | class A v1 | **class A v2** | class B v1 | **class B v2** |
|---|---|---|---|---|
| ZZ count min–max (mean) | 1 736–1 740 (1 739.2) | **1 492–1 492 (1 492)** | 582–800 (683.5) | **580–763 (675.0)** |
| two-qubit depth min–max | 1 275–1 280 | **948–948** | 292–469 | **292–429** |
| circuits passing | 75/75 | **75/75** | 75/75 | **75/75** |
| max measured $\lvert\Delta\psi\rvert$ | $5.84\times10^{-14}$ | $5.58\times10^{-14}$ | $3.14\times10^{-14}$ | $3.15\times10^{-14}$ |
| max certified $\lvert\Delta\psi\rvert$ incl. rounding | $1.72\times10^{-12}$ | $1.75\times10^{-12}$ | $7.72\times10^{-13}$ | $7.70\times10^{-13}$ |
| max certified leakage incl. rounding | $2.77\times10^{-24}$ | $2.88\times10^{-24}$ | $5.52\times10^{-25}$ | $5.48\times10^{-25}$ |
| skeleton identical for $k=1..5$ in every reference | no (15/15 references vary) | **yes** | no (`B0_ref1338`) | **yes** |
| term checks (worst deviation) | $1.01\times10^{-14}$ | $1.03\times10^{-14}$ (130 checks) | $1.05\times10^{-14}$ | $8.77\times10^{-15}$ (975 checks) |

Sources: `data/report004_tables.json` keys `2x4.A_v1/B_v1/A_v2/B_v2` (from `data/eval_arch_it5_*_pp_all75_pruned.json`,
`data/eval_arch_it6_*_pp2_all75_pruned.json`) and `2x4.v1_with_rounding` (`data/rounding_v1.json`); v1 term checks
from report 003 §2.5.  The certified columns are dominated by the rounding term (largest $1.59\times10^{-12}$ in v2
class A); the measured deviations are at the $10^{-14}$ level.  Every v2 class-B circuit has at most as many ZZ as its
v1 counterpart (checked over all 75).

- **Class A:** $-14.2\,\%$ ZZ (1 739.2 → 1 492 mean) and $-26\,\%$ two-qubit depth (1 279 → 948).  Ratio to the
  frozen circuits (71 548 ZZ): 48.0×.
- **Class B:** $-1.2\,\%$ ZZ on the mean (683.5 → 675.0), $-2.3\,\%$ depth on the mean (373.3 → 364.6,
  `data/report004_tables.json`).  Class B was already dominated by the plaquettes, which did not move.  Its v2 value is
  mainly the $k$-independent skeleton and the certificates.  Ratio to the frozen circuits: 106×.

**Per term** (class A best per term, class B mean over the 15 references; `data/report004_tables.json` `per_term_2x4`):

| term | A it5 | **A it6** (winner) | B it5 mean | B it6 mean |
|---|---|---|---|---|
| hop0 | 140 | **130** (cb1) | 10.9 | 10.9 |
| hop1 | 52 | 52 (full_lin) | 26.4 | 26.4 |
| hop2 | 110 | 110 (bframed_lin) | 27.5 | 27.5 |
| hop3 | 256 | **168** (cb1_jwc) | 25.5 | 25.5 |
| hop4 | 166 | **130** (cb1) | 72.5 | 71.7 |
| hop5 | 178 | **134** (cb1_jwc) | 43.5 | 43.5 |
| hop6 | 134 | **124** (jwc_bframed_milp) | 34.3 | 34.3 |
| hop7 | 166 | **130** (cb1) | 74.1 | 73.2 |
| hop8 | 116 | **114** (cb1) | 34.0 | 34.0 |
| hop9 | 52 | 52 (full_lin) | 52.0 | 52.0 |
| plaq0 | 88 | 88 (cfg_lin) | 61.2 | 61.2 |
| plaq1 | 220 | **202** (cfg_lin_milp) | 155.7 | 154.7 |
| plaq2 | 96 | 96 (cfg_lin) | 96.0 | 95.2 |
| **sum** | **1 774** | **1 530** | **713.6** | **710.0** |

(Term sums exclude the diagonal group; the circuit counts above include it for class A and the finishing pass.)

**Planner targets (notes/007 §6) against what was computed:** class A hop sum $\le900$ — achieved 1 144
(1 370 → 1 144); `hop3` $\le130$ — achieved 168; class A `plaq1` $\le140$ — achieved 202; class A total
1 000–1 200 — achieved 1 492; class B 350–450 — achieved 580–763.  The planner's targets were his heuristic; the
certificates (§3.3) show that inside the present constructions there is almost nothing left — the remaining headroom
needs new constructions (plaq1's multiplexor, the hop flag/sign structure), not better solvers.

### 3.2 Independent 28-qubit cross-check of v2 (sample) and native counts

qiskit-aer statevector (28 qubits, complex128, fusion on as in reviews/001, 6 threads), circuits taken through
`get_family` (the noise agent's objects), target from the package's `coarse_states` with `dt` from `validation/E3.json`:

| circuit | ZZ | $\max\lvert\Delta\psi\rvert$ (phase-aligned) | $\lVert\Delta\psi\rVert_2$ incl. leakage | leakage (non-codeword + other sector) | phase − predicted | wall | file |
|---|---|---|---|---|---|---|---|
| class B v2 `B0_ref345_k1` (largest ZZ) | 763 | $2.83\times10^{-14}$ | $2.93\times10^{-14}$ | $3.2\times10^{-31}$ | $0$ rad | 750 s | `data/aer_compressed_circuit_llm_2x4_classB_v2_sample_B0_ref345_k1.json` |
| class A v2 `B1_ref230_k5` | 1 492 | $1.91\times10^{-14}$ | $4.99\times10^{-14}$ | $3.0\times10^{-30}$ | $4.5\times10^{-15}$ rad | 1 310 s | `data/aer_compressed_circuit_llm_2x4_classA_v2_sample_B1_ref230_k5.json` |

Only two of the 150 v2 circuits were re-simulated this way (a 28-qubit Aer run takes 12–22 minutes on this laptop);
all 150 pass my certified harness (§3.1).  A first attempt with fusion off and two circuits per process would have
exceeded the 30-minute rule and was stopped before writing anything; it was re-run as above.

**Native counts and $f$** (all 75 circuits per class, pytket level 0 for H2-2, Q1L passes on all;
`data/native_compressed_circuit_llm_2x4_class{A,B}_v2.json`):

| | class A v1 (4 finalists, report 003) | **class A v2** | class B v1 (4 finalists) | **class B v2** |
|---|---|---|---|---|
| ZZPhase | 1 738–1 740 | **1 492** | 582–800 | **580–763** |
| PhasedX mean | — | 4 164.9 | — | 1 800.0 |
| $f$ H2-2, gate-only | 0.2005–0.2009 | **0.2512** | 0.4718–0.5751 | **0.4881–0.5763 (mean 0.5293)** |
| $f$ Helios-1 | — | 0.2678 | — | 0.5076–0.5955 |

v1 values from `data/native_it5_{operator,input}.json`.  $f$ is the package's gate-only model, for information.

### 3.3 Certificates (step 2)

| family | multiplexors | support-optimal (certified) | walk = support + 1 | support used / lower bound (sum) | walk used / lower bound (sum) |
|---|---|---|---|---|---|
| 2x4 class A v2 | 65 | 64 | 45 | 643 / 632 | 750 / 697 |
| 2x4 class B v2 | 852 | 813 | 590 | 4 735 / 4 652 | 5 960 / 5 501 |
| 2x3 class A | 43 | 43 | 30 | 397 / 397 | 464 / 440 |
| 2x3 class B | 396 | 388 | 283 | 1 857 / 1 847 | 2 390 / 2 240 |

Sources `data/cert_it6_{operator,input}.json`, `data/c2x3/cert_L3_it1_{operator,input}.json` (summaries copied into
`data/report004_tables.json`).  Meaning: in all but one class-A multiplexor the support is provably minimal for its
control set and target (the class of the certificate; free angles in $[-8\pi,8\pi]$); the one open case is plaq1's
7-control table (support 85, MILP lower bound 74 after 300 s, 78 after 1 500 s, §4 item 7).  In class B, 39
multiplexors have a MILP solution with fewer masks than used (83 masks in total); these were found after the v2
freeze and are recorded, not adopted (they would be a v3).  The walk column is the gap left by the walk ordering:
53 CNOTs over all class-A multiplexors.

### 3.4 2x3: compressed families versus the frozen 2x3 family

| | frozen 2x3 family | `compressed_circuit_llm_2x3_classA` | `compressed_circuit_llm_2x3_classB` |
|---|---|---|---|
| circuits | 44 | 44 | 44 |
| ZZ count min–max (mean) | 2 158–2 158 | **871–871** | **309–465 (387.6)** |
| ratio to the frozen family (mean) | 1 | 2.48× | 5.57× |
| two-qubit depth | — (not in index.json) | 611 | 170–290 |
| my harness: passing / max measured / max certified $\lvert\Delta\psi\rvert$ | — | 44/44, $3.50\times10^{-14}$, $9.41\times10^{-13}$ | 44/44, $2.16\times10^{-14}$, $4.37\times10^{-13}$ |
| **Aer statevector** (all 44, independent target): passing / max $\lvert\Delta\psi\rvert$ / max leakage | — | **44/44**, $3.05\times10^{-14}$, $1.3\times10^{-30}$ | **44/44**, $2.10\times10^{-14}$, $1.8\times10^{-31}$ |
| Aer: measured global phase − predicted | — | $\le1.92\times10^{-14}$ rad | $\le1.69\times10^{-14}$ rad |
| skeleton identical for $k=1..4$ | — | yes | yes |
| native ZZPhase (pytket level 0), Q1L | 2 158 | 871, Q1L 44/44 | 309–465, Q1L 44/44 |
| PhasedX mean | 3 052.95 | 2 415.9 | 1 024.3 |
| $f$ H2-2, gate-only (mean) | 0.150 | **0.445** | **0.692** (min 0.644) |
| $f$ Helios-1 (mean) | 0.164 | 0.463 | 0.707 |

Sources: frozen family `data/quantinuum/circuits_2x3/index.json` (`summary.n_zz`, `n_phasedx`) and
`validation/Q0P_2x3.json` (`data.stage_A.predict.devices.*.f_gate_only_mean`); mine
`data/c2x3/eval_arch_L3_it1_*_pp2_all44_pruned.json`, `data/c2x3/aer_compressed_circuit_llm_2x3_class*.json`,
`data/c2x3/native_compressed_circuit_llm_2x3_class*.json`; all collected in `data/report004_tables.json`.
$f$ uses the package formula with $\varepsilon$ values of `data/quantinuum/devices_20261002.json`, $n_{1q}$ = PhasedX,
$n_m=20$ — **for information only**; it is the package's gate-only model, not a hardware number.

The 2x3 per-term costs (`per_term_2x3` in `data/report004_tables.json`) are the 2x4 ones for the same term types
(hop0 130, hop3 124, hop4 130, plaq0 88, plaq1 96 in class A), as expected from the parameterised code.

## 4. Problems, assumptions, what remains

1. **Hard stop.**  Steps 1–3 and the certificates are done in the sense stated above: step 1 evaluated and not built
   (gain $\le22$ CX under an assumption on $c_4$), step 2 done and certified, step 3 built.  Steps 4 (partly) and 6
   built, step 5 not separate.  The round took one working session, inside the two laptop-days.
2. **Class B gained little** ($-1.2\,\%$).  Its cost is in plaq1 (≈155), plaq2 (≈95), plaq0 (≈61) and hop4/7/9.
   Further gains need a new plaquette construction (the plaq1 multiplexor) — not a better solver.
3. **v3 candidates found after the freeze (not adopted):** the class-B MILP supports of §3.3 (83 masks over 39
   multiplexors) and the walk-order gap (53 CNOTs in class A).  The frozen v2 files are not rewritten (notes/009).
4. **What the certificate certifies.**  Minimality of the Walsh support for the given target, control reduction and
   frame, with free angles in $[-8\pi,8\pi]$; HiGHS is trusted, not verified.  It does not say anything about
   other constructions.
5. **Rounding model.**  $u$, the complex-product constant and the one-ulp libm property are cited assumptions; the
   algebra is proved.  The package's reference state (`expm_multiply` in double) is the bar's reference as defined by
   the package; its own rounding is not part of my bound.
6. **28-qubit Aer coverage.**  Two v2 circuits (§3.2), the largest class-B one included.  All 88 2x3 circuits were
   checked with Aer.  A full 28-qubit Aer pass over the 150 v2 circuits would take about 43 hours on this laptop
   ($75\times750\,{\rm s}+75\times1\,310\,{\rm s}$, my arithmetic from the two wall times — an estimate, not a
   measurement); it needs the desktop/GPU or several overnight runs.
7. **plaq1's multiplexor is the one open certificate.**  After 1 500 s the MILP lower bound is 78 masks against 85
   used (`data/cert_it6_operator_plaq1_long.json`, status "time or iteration limit"); at most 7 masks (≈ 7 CNOTs) can
   be gained there inside this construction.
8. **Lean.**  The circuit-level hypotheses of G3 remain numerical (§2.9 a–d).  `H1-1` (20 qubits) cannot run the
   28-qubit 2x4 circuits; its $f$ for them is a formula value only.
9. **Noise.**  Not part of this report (a separate agent, `noise/`).  Class B's use limit (reviews/001 note 1) applies
   to v2 and to the 2x3 class B unchanged.
10. **Machine/time.**  All runs on the laptop (i7-8750H, 62 GiB), each under 30 minutes; parallel runs were batched
    by references to stay inside the rule.

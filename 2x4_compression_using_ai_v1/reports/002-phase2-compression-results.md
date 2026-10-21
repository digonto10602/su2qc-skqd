# 002 — Phase 2: the 2x4 coarse-step circuits compressed 25–120x, verified at the package bar, with the rewrite rules proved in Lean

- Date: 2026-10-21.  Author: genie-opus (Opus 5.5, high effort), study `2x4_compression_using_ai_v1/`.
- Git commit: the commit that adds this report (see `git log -- 2x4_compression_using_ai_v1/reports/002*`);
  every JSON quoted carries the commit at which its numbers were produced (`git_commit`, `+dirty(study folder)`
  when the study folder had uncommitted changes at run time).
- Plan in force: `notes/003-phase2-iteration-plan-corner-factorisation.md` (steps), `notes/001-phase2-plan.md`
  §3 (acceptance criteria A1–A7), `notes/002-owner-answers-phase2-go.md` (owner answers), tolerance
  `notes/004-approximate-class-tolerance.md`.
- Related: `reports/001-phase1-study-and-comparison.md`; planner request `notes/005-planner-request-ultimate-compression-review.md`;
  generated tables `data/summary_it5.json` (`python scripts/summarise.py --label it5 --history it1,it2,it3,it4,it5`).
- This folder carries no gate status of the package; none of its numbers are package results.

**Terms (defined once; labels marked "mine" are this study's names, not physics terms).**
*Two-qubit gate / ZZ count* — the number of CX, CZ, controlled-phase or ZZPhase gates; each becomes one Quantinuum
`ZZPhase` (package rule, prompts/35b R4).  *Two-qubit depth* — the longest chain of two-qubit gates when one-qubit
gates are free (pytket's `depth_2q`).  *Local codewords* of a term — the bit strings its qubits take in the 37 165
valid codewords.  *Block* — a connected component of a term's generator on its local codewords.
*Multiplexor (uniformly controlled rotation)* — a one-qubit rotation whose angle depends on the values of other
"control" qubits; the standard (Gray-code) circuit costs $2^m$ CNOTs for $m$ controls.  *Walsh–Hadamard
spectrum* — the coefficients $a_S$ in $\theta(c)=\sum_S a_S(-1)^{|S\cap c|}$; each nonzero $a_S$ costs CNOTs.
*Frame* (mine) — a cheap change of basis applied before a term and undone after it.  *Bright/dark state* —
of two intertwiner states coupled to the same partner, the combination the term actually reaches (bright) and the
orthogonal one it annihilates (dark).  *Clean ancilla* (mine, standard idea) — a qubit that is $|0\rangle$ on every
codeword because its information is stored elsewhere (here: a redundant copy of a link bit), so it can be used as
scratch space and restored.  *Relative-phase Toffoli* — a 3-CNOT Toffoli that is correct up to a phase on the control
states; used only in compute/uncompute pairs.  *Class A* (operator-exact) — every term exact on all its local
codewords; *class B* (exact on own input) — each term exact on the blocks reachable from the circuit's own
reference state.  *Loop* — the evaluator-guided search of arXiv:2610.22367 (§2.4).

---

## 1. What was asked

Phase 2 (approved, `notes/002`): build and run the AI-guided compression loop of arXiv:2610.22367 on the 2x4 SKQD
coarse-step circuits (frozen family: 71 548 ZZ, two-qubit depth 70 300).  Two classes: exact (package bar
$\max|\Delta\psi|<10^{-10}$, leakage $<10^{-9}$ on each circuit's own (reference, $k$) state) and approximate
(drop near-zero-amplitude parts under a tolerance stated and justified first, error bound L6 proved in Lean).
Develop provable reduction techniques, especially for `plaq1`; prove every rewrite identity in Lean (`lake build`,
no `sorry`/`admit`, standard axioms); check full 28-qubit circuits numerically and keep "proved" and
"numerically checked" apart.  Score: ZZ count, then two-qubit depth.  No output-state loading, no CI, no QPU,
nothing outside the study folder.  Hand back with the best verified family and a planner-review request.

## 2. Actions taken

1. **Evaluator harness (P2-0, `src/c2x4/{problem,evaluate}.py`).**  Independent of every construction: counts and
   two-qubit depth from the gate list; the full-circuit state check runs the package's exact sparse simulator
   (`skqd.sparse_sim`, complex128, no thresholds) against `krylov.apply_groups` (the `coarse_states` target); the term
   check runs a term's gate list on *every* local codeword at once by appending index qubits (one sparse run returns
   every codeword column of the term's unitary).  It reproduces the frozen family exactly:
   **71 548 two-qubit gates and two-qubit depth 70 300** on `B0_ref102_k1` (the native manifest's numbers), state
   deviation $4.54\times10^{-14}$, and every baseline term to $\le4.1\times10^{-13}$ on all codeword columns
   (`data/p2_0_harness_baseline.json`, 176 s for the baseline circuit).  Unit tests: `tests/test_evaluate.py` (3 pass).
2. **Structure tests (P2-1, `scripts/p2_1_structure.py` → `data/p2_1_structure.json`).**
   - Every plaquette term factorises exactly over its four corners: on its local codewords
     $h=A_{c_{00}}\otimes A_{c_{10}}\otimes A_{c_{11}}\otimes A_{c_{01}}$ with real corner matrices, residual
     $\le2.6\times10^{-15}$ on every codeword column and every one of the $2^{k}$ rows (`plaq1`: 1 831 codewords,
     $1.6\times10^{-15}$).  My reading of why (physics, not a new term): the colour indices of the Wilson loop are
     contracted around the corners and each corner is an SU(2)-invariant map, so by Wigner–Eckart each corner tensor is
     a scalar times $\delta_{ij}$.
   - Corner blocks are pairs plus one three-state block per interior corner (the two intertwiner states of the
     all-flux, $n=1$ vertex): one bright combination and one dark state.  A block is antisymmetric when the corner's
     two plaquette-link bits are equal and symmetric otherwise, and the two pair magnitudes of a corner differ by
     $\sqrt2$ (`plaq1` corner `c00`: 0.7414 and 0.5242).
   - Every hop term factorises as $T+T^\dagger$, $T=\eta\,a_x\otimes b_y\otimes s_{\rm JW}$ ($\eta=i$ on x-links, real on
     y-links; fit residual $\le2.7\times10^{-15}$).  Each vertex factor is a three-level chain $n=0\to1\to2$ with equal
     steps (a spin-1 raising operator), so hop blocks are three-state chains and pairs; no vertex-local frame turns
     them into pairs (the bright combination of $(0,2)$ and $(2,0)$ is entangled across the two vertices).
3. **Constructions (proposal programs, `src/c2x4/`).**
   - *CF1* (mine; `plaqfactor.cf1_gates`): per corner $\mathrm{CX}(p_a\to p_b)$ and one two-level "bright" rotation;
     a CNOT ladder from one corner's $p_a$ turns the simultaneous flip of eight link bits into a flip of one qubit
     $p_1$; the generator in that frame is $X_{p_1}\otimes\mathrm{diag}(F)$ on the occupied strings (checked entry by
     entry), so the whole term is ONE multiplexed rotation between the frame and its inverse.  `plaq1`: 66 468 → 2 110.
   - *CF2 / CFG* (mine; `cf2_gates`, `cfg_gates`): the angle table $F$ depends on the corners' parity bits $x_c$ and is
     zero on dark states.  Clearing the redundant link copies by CNOTs gives four clean ancillas; relative-phase
     Toffolis put the dark flags $g_c=c_c\wedge q_c$ into them; label-dependent signs are absorbed for free (a bright
     rotation by $\varphi+2\pi$ is $-R_y(\varphi)$), by CZ, or by a CCZ written as 3 controlled phases + 2 CNOTs, the cheapest
     set chosen by an $\mathbb F_2$ fit.  The multiplexor then has 5–7 controls.  `plaq1`: 66 468 → **220** (class A).
   - *F1 restriction* (`reach.py`): the structural support before each term (union of the blocks reached from the
     reference, angle-independent) makes every other local codeword a don't-care.  Hops touch 0–12 blocks.
   - *Sparse-Walsh multiplexors* (F4, `sparsemux.py`): after the package's control reduction, choose the free slots so
     that the Walsh spectrum is sparse (L1 linear programme, greedy pruning, exact re-solve, residual $\le10^{-12}$) and
     walk only the nonzero masks.
   - *Hop frames* (mine; `hopframe.py`): per end vertex, fold the spectator flux parity into the hopping-link bit
     (2 CNOTs) and rotate the intertwiner pair to bright/dark; then the package's block synthesis (with sparse-Walsh
     multiplexors) on the framed generator.  hop3: 1 548 → **256** (class A).
   - *Peephole* (F5, `peephole.py`): cancel identical CNOT pairs across gates that provably commute with them; merge
     equal-axis one-qubit rotations.
4. **The loop** (`scripts/loop_select.py`, archives `data/archive_it1..5.json`): I propose construction programs turn
   by turn (no API loop, owner O5); for every (reference, term) and every term (class A) every applicable proposal is
   built and checked by the evaluator on its contract (A1: max deviation $\le10^{-10}$, leakage $\le10^{-12}$), and the
   archive keeps the verified one with the fewest two-qubit gates, then the smallest depth.  Five iterations (table §3.2).
5. **Approximate class** (`notes/004`, `scripts/approx_tiers.py`): tolerance fixed before any circuit was built,
   lemmas L6b/L6c proved first; blocks dropped by weight along the exact trajectory.
6. **Full-circuit verification** of the iteration-5 families, both classes, all 60 + 15 circuits ($k=1..5$)
   (`scripts/eval_family.py`, three chunks per class, each under 30 minutes).
7. **Native conversion** (A4) of finalists in the isolated venv `~/.local/share/su2qc-quantinuum`
   (`scripts/native_check.py`: the package's `ir_to_pytket`, `compile_native` at level 0 and level 2,
   `local_equivalence_35a`, `rounding_bound`, the native circuit read back and simulated).
8. **Lean 4** (`lean/Compress2x4/*.lean`): 8 files, `lake build` succeeds (log `data/p2_lean_build.log`).

## 3. Results

Every table below is printed by `python scripts/summarise.py --label it5 --history it1,it2,it3,it4,it5`
(output `data/summary_it5_tables.md`, numbers `data/summary_it5.json`); nothing is typed by hand.

### 3.1 Per-term two-qubit cost (IR CX, $\theta=dt$; class B is the minimum–maximum over the 15 references)

| term | baseline IR CX | class A best (proposal) | class B best, range over 15 references (proposals) |
|---|---|---|---|
| hop0 | 278 | 140 (bframed_sw) | 0–14 (rpkg) |
| hop1 | 54 | 52 (full_sw) | 0–38 (rpkg) |
| hop2 | 258 | 110 (bframed_sw) | 14–44 (rpkg, rpkg_sw) |
| hop3 | 1548 | 256 (bframed_sw) | 6–44 (rpkg, rpkg_sw) |
| hop4 | 390 | 166 (bframed_sw) | 52–112 (bframed_sw, framed_sw, rpkg, rpkg_sw) |
| hop5 | 542 | 178 (bframed_sw) | 40–58 (rpkg_sw) |
| hop6 | 260 | 134 (bframed_sw) | 30–44 (rpkg, rpkg_sw) |
| hop7 | 390 | 166 (bframed_sw) | 68–108 (bframed_sw, framed_sw, rpkg, rpkg_sw) |
| hop8 | 244 | 116 (framed_sw) | 30–56 (framed_sw, rpkg_sw) |
| hop9 | 54 | 52 (full_sw) | 52–52 (rpkg_sw) |
| plaq0 | 228 | 88 (cfg) | 54–84 (cfg_sw, cfg_t_sw) |
| plaq1 | 66468 | 220 (cfg_sw) | 152–208 (cfg_sw, cfg_t_sw) |
| plaq2 | 806 | 96 (cfg) | 96–96 (cfg) |
| sum | 71520 | 1774 | 594–958 (term-wise extremes) |

Proposal labels (mine): `pkg` the package synthesis; `rpkg` the package synthesis restricted to reachable blocks;
`cf1`, `cf2`, `cfg`, `cfg_t` the corner-frame constructions (`cfg_t`: flags only on corners with a three-state block);
`full_sw` the package block synthesis with sparse-Walsh multiplexors; `framed_sw`, `bframed(_sw)` the hop frames
(parity fold; parity fold + bright rotation); suffix `_sw` = sparse-Walsh multiplexors.  `plaq1` alone goes from
66 468 to 220 (class A, $302\times$) and to 152–208 (class B).

### 3.2 The loop, iteration by iteration (archives `data/archive_it1..5.json`; term sums, diagonal group excluded)

| iteration | proposals available | class A term sum | class B term sum per reference (min / mean / max) |
|---|---|---|---|
| it1 | cf1, cf2, pkg, rpkg | 4588 | 734 / 888.0 / 1044 |
| it2 | + cfg, cfg_t | 4440 | 636 / 762.1 / 934 |
| it3 | + cf2_sw, cfg_sw, cfg_t_sw, full_sw, rpkg_sw | 3074 | 606 / 716.5 / 846 |
| it4 | + framed_sw | 2734 | 606 / 715.5 / 844 |
| it5 | + bframed, bframed_sw | 1774 | 606 / 713.6 / 828 |

### 3.3 Whole circuits: the best verified families (all 60 + 15 circuits, $k=1..5$, both sectors)

| | class B: exact on own reference input (`arch:it5:input:pp`) | class A: operator-exact (`arch:it5:operator:pp`) | frozen baseline |
|---|---|---|---|
| circuits verified / passing the bar | 75 / 75 | 75 / 75 | — |
| two-qubit (ZZ) count | **582–800**, mean 683.5 | **1 736–1 740**, mean 1 739.2 | 71 548 |
| compression vs 71 548 (mean) | **104.7×** | **41.1×** | 1 |
| two-qubit depth | **292–469** | **1 275–1 280** | 70 300 |
| one-qubit IR gates (mean; not scored) | 549.9 | 1 472.7 | 70 740 (ry 70 308, one-qubit unitary 388, p 40, x 4; manifest `original_ir_counts`) |
| max measured $\lvert\Delta\psi\rvert$ (phase-aligned) | $3.14\times10^{-14}$ | $5.84\times10^{-14}$ | $4.54\times10^{-14}$ |
| max pruned norm $B_{\rm prune}$ (notes/006) | $8.48\times10^{-14}$ | $9.82\times10^{-14}$ | — |
| max **certified** $\lvert\Delta\psi\rvert$ | $1.16\times10^{-13}$ | $1.54\times10^{-13}$ | — |
| max certified leakage | $7.7\times10^{-27}$ | $1.1\times10^{-26}$ | — |
| term checks A1 (every term, every angle used; contract) | 975 checks, worst $1.05\times10^{-14}$, leakage $\le6.2\times10^{-31}$ | 130 checks, worst $1.01\times10^{-14}$, leakage $\le1.4\times10^{-29}$ | — |
| files | `data/eval_arch_it5_input_pp_all75_pruned.json`, `..._terms_part{0,1,2}.json` | `data/eval_arch_it5_operator_pp_all75_pruned.json`, `..._terms.json` | `data/p2_0_harness_baseline.json` |

Bar: certified $\max\lvert\Delta\psi\rvert<10^{-10}$ and certified leakage $<10^{-9}$ (package bar, prompts/35b R1; method
note 006).  Class B also drops the diagonal group (exact on the reference input, Lean `diagonal_mulVec_single`); class A
keeps it (28 two-qubit gates).  Cross-check of the pruned method against the exact unpruned simulator:
B0_ref102_k1: exact unpruned $\max|\Delta\psi|$ 2.37e-14, max support 16739916, 112 s vs pruned 2.39e-14 (certified 6.83e-14); B1_ref230_k1: exact unpruned $\max|\Delta\psi|$ 2.33e-14, max support 4184564, 28 s vs pruned 2.36e-14 (certified 3.48e-14); B0_ref345_k4: exact unpruned $\max|\Delta\psi|$ 1.24e-14, max support 33472800, 201 s vs pruned 1.19e-14 (certified 1.49e-14) (`data/eval_arch_it5_input_pp_exact_crosscheck.json`).

### 3.4 Native Quantinuum circuits (A4) and the device threshold

pytket level 0 through the package's own converter; the conversion proof Q1L ((i) skeleton, (ii) per-qubit
segments, maps) and the rounding bound $B$ as in prompts/35a–35b.  $f$ is the package's gate-only clean-shot fraction
(`skqd.device_req.clean_shot_fraction`, $n_{1q}$ = PhasedX, 28 measurements, `data/quantinuum/devices_20261002.json`).
Level 2 rewrites gates, so Q1L does not apply and those circuits are **not verified** (counts for information only);
simulating native circuits on this laptop is not practical (genuine superpositions from the PhasedX/ZZPhase form,
notes/006).

**Class B** (`data/native_it5_input.json`):

| circuit (input) | level | ZZ | 2q depth | PhasedX | Q1L | rounding bound B | f H1-1 | f H2-1 | f H2-2 | f Helios-1 |
|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref102_k1 | 0 | 660 | 349 | 1760 | True | 1.4e-14 | 0.479 | 0.455 | 0.536 | 0.556 |
| B0_ref102_k1 | 2 | 629 | 330 | 750 | not applicable (level 2 rewrites gates; unverified) | – | 0.502 | 0.480 | 0.566 | 0.587 |
| B1_ref230_k1 | 0 | 582 | 292 | 1564 | True | 1.0e-14 | 0.518 | 0.497 | 0.575 | 0.594 |
| B1_ref230_k1 | 2 | 560 | 279 | 662 | not applicable (level 2 rewrites gates; unverified) | – | 0.538 | 0.518 | 0.601 | 0.621 |
| B0_ref345_k4 | 0 | 800 | 469 | 2168 | True | 3.9e-14 | 0.415 | 0.387 | 0.472 | 0.491 |
| B0_ref345_k4 | 2 | 775 | 451 | 899 | not applicable (level 2 rewrites gates; unverified) | – | 0.435 | 0.407 | 0.499 | 0.521 |
| B0_ref1338_k5 | 0 | 762 | 428 | 2058 | True | 4.2e-15 | 0.431 | 0.404 | 0.488 | 0.508 |
| B0_ref1338_k5 | 2 | 737 | 412 | 857 | not applicable (level 2 rewrites gates; unverified) | – | 0.452 | 0.425 | 0.516 | 0.537 |

**Class A** (`data/native_it5_operator.json`):

| circuit (operator) | level | ZZ | 2q depth | PhasedX | Q1L | rounding bound B | f H1-1 | f H2-1 | f H2-2 | f Helios-1 |
|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref102_k1 | 0 | 1740 | 1280 | 4846 | True | 3.9e-14 | 0.159 | 0.131 | 0.201 | 0.216 |
| B0_ref102_k1 | 2 | 1725 | 1278 | 1858 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |
| B1_ref230_k1 | 0 | 1740 | 1280 | 4847 | True | 3.1e-14 | 0.159 | 0.131 | 0.201 | 0.216 |
| B1_ref230_k1 | 2 | 1725 | 1278 | 1861 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |
| B0_ref345_k4 | 0 | 1738 | 1278 | 4841 | True | 1.4e-13 | 0.159 | 0.131 | 0.201 | 0.216 |
| B0_ref345_k4 | 2 | 1724 | 1277 | 1862 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |
| B0_ref1338_k5 | 0 | 1738 | 1278 | 4841 | True | 1.9e-14 | 0.159 | 0.131 | 0.201 | 0.216 |
| B0_ref1338_k5 | 2 | 1724 | 1277 | 1859 | not applicable (level 2 rewrites gates; unverified) | – | 0.170 | 0.141 | 0.221 | 0.239 |

With the package's own memory model (`devices_20261002.json memory_model`, flagged ESTIMATE by the package:
$S_{\rm idle}=n_{\rm qubits}\times{\rm rounds}\times t_{\rm round}\times{\rm rate}$, three $t_{\rm round}$ scenarios), H2-2 gives
$f=0.428$–$0.571$ for the class-B finalists and $0.154$–$0.195$ for class A (native level 0, all three scenarios; `data/summary_it5.json`
`native_*[].f_with_memory_ESTIMATE`).  H1-1 has 20 qubits and cannot hold the 28-qubit circuits.  The phase-1
threshold for $f\ge0.1$ on H2-2 was 2 493–2 741 ZZ (`data/p1_device_threshold.json`); **both classes are below it**.

### 3.5 Approximate class (notes/004; `data/approx_tiers.json`)

| circuit | budget $\varepsilon_{\rm total}$ | status | blocks dropped | L6 bound | certified $\varepsilon$ (measured) | ZZ | 2q depth |
|---|---|---|---|---|---|---|---|
| B0_ref102_k1 | 1e-08 | adopted tolerance | 3 | 4.1e-10 | 7.0e-14 | 660 | 355 |
| B0_ref102_k1 | 1e-06 | information only | 28 | 1.8e-07 | 7.0e-14 | 660 | 355 |
| B0_ref102_k1 | 1e-04 | information only | 145 | 2.0e-05 | 7.0e-14 | 660 | 355 |
| B1_ref230_k1 | 1e-08 | adopted tolerance | 0 | 0.0e+00 | 3.6e-14 | 582 | 298 |
| B1_ref230_k1 | 1e-06 | information only | 13 | 1.7e-07 | 3.6e-14 | 582 | 298 |
| B1_ref230_k1 | 1e-04 | information only | 105 | 2.3e-05 | 3.6e-14 | 582 | 298 |
| B0_ref102_k4 | 1e-08 | adopted tolerance | 0 | 0.0e+00 | 1.7e-14 | 660 | 355 |
| B0_ref102_k4 | 1e-06 | information only | 0 | 0.0e+00 | 1.7e-14 | 660 | 355 |
| B0_ref102_k4 | 1e-04 | information only | 0 | 0.0e+00 | 1.7e-14 | 660 | 355 |

At the adopted tolerance ($\varepsilon\le10^{-8}$) almost nothing can be dropped: the smallest reachable block
amplitude of `plaq1` is $8.2\times10^{-11}$ (B0_ref102_k1) – $1.7\times10^{-9}$ (B1_ref230_k1), the per-term budget is
$7.7\times10^{-10}$ (`data/p2_1_structure.json block_amplitudes`).  Even at budgets $10^{2}$ and $10^{4}$ times larger
(information only, not justified for SKQD) the gate count does not change: dropping rare blocks does not remove a whole
label class from any multiplexor, and the cheapest constructions happen to remain exact on the dropped blocks (measured
$\varepsilon$ stays at the $10^{-14}$ level).  **The approximate class gives no gain over the exact class here.**

### 3.6 Lean 4: what is proved (48 statements, `lake build` OK, no `sorry`/`admit`, axioms only propext / Classical.choice / Quot.sound; log `data/p2_lean_build.log`)

Model: an $n$-qubit basis label is a function `Fin n → Bool`; X-type gates are permutation matrices, Z-type gates
diagonal matrices; every statement below holds for every register size $n$ unless it is a fixed small matrix.

| file | statement (Lean name) | what it backs in the constructions |
|---|---|---|
| Sanity | `CZ_mul_CZ`, `RZZ_mul_RZZ`, `RZZ_comm` | merging/cancelling two-qubit diagonal gates |
| Sanity | `diagonal_mulVec_single` | dropping the diagonal group on the reference basis state (class B) |
| Sanity | `kron_disjoint_comm` | gates on disjoint qubits commute (peephole rule R1) |
| Sanity, Reach | `agree_on_reachable`, `agree_on_reachable_n` (L5) | class B: exact on reachable blocks ⇒ exact on the reference input |
| Exp | `exp_intertwine`, `exp_agree_of_intertwine`, `exp_agree_on_invariant`, `exp_agree_mulVec`, `smul_intertwine` | a generator correct only on the codeword (or frame-image) subspace, arbitrary on don't-cares, has the correct exponential there |
| Exp | `exp_conj_frame` | $e^{UGU^{-1}}=Ue^{G}U^{-1}$: every frame |
| Bits | `perm_mul`, `perm_conj_diagonal`, `xorLinear_trans`, `xorLinear_conj_flip` | a CNOT network maps the flip $X_v$ to $X_{Lv}$ and a phase table $d$ to $d\circ L^{-1}$: the corner CX, the ladder (eight link flips → one qubit), clearing redundant copies |
| Bits | `cx_involutive`, `cx_xorLinear` | CX CX = 1; CNOT networks are xor-linear |
| Bits | `ccz_phase`, `ccz_circuit` | CCZ = 3 controlled phases + 2 CNOTs (sign gadget) |
| Peephole | `cx_comm_diagonal_of_indep`, `cx_comm_cx`, `cx_comm_flip_target`, `cx_comm_lincomb_flip_target` | the commutation rules R2–R4 of the peephole pass |
| Ucr | `cx_conj_zd_target`, `xt_comm_zd`, `cx_conj_yt` (W1), `exp_conj_cx_yt`, `exp_sum_commuting` (W2) | a CNOT from control $i$ into the target turns $Y_t$ into $Z_iY_t$; commuting exponentials split: the multiplexor as a product of CNOT-conjugated $R_y$'s (Gray chain and sparse-Walsh walk alike) |
| Pair | `xt_mul_xt`, `zd_mul_zd`, `xt_zd_anticomm`, `ht_mul_ht`, `ht_xt_ht`, `diag_comm_xt`, `ht_diag_ht`, `exp_xt_diag` (G5), `zd_mul_diag`, `zd_comm_yt`, `walk_factors_comm` | the frame generator $X_t\,\mathrm{diag}(D)$ ($D$ ignoring bit $t$) exponentiates to $H_t\,\mathrm{diag}(e^{c(-1)^{s_t}D(s)})H_t$, i.e. a multiplexed rotation; the walk factors commute (premise of W2) |
| Reach | `telescoping_bound` (L6), `telescoping_bound_mirror`, `ry_add_two_pi`, `relphase_cancel` | error budget of the approximate class; the certified pruned simulation (notes/006); free sign flip of a bright rotation; relative-phase Toffoli compute/uncompute |
| Budget | `dropped_part_bound` (L6c), `normSq_sub_le`, `tv_le_norm_sub` (L6b) | a dropped block costs at most $2\lVert\Pi_D\varphi\rVert$; total variation of the measured distributions $\le$ state distance |

**Numerically checked, not proved** (each instance, by the evaluator): that each term's generator factorises over its
corners/vertices (residual $\le2.7\times10^{-15}$); that the frame generator has the form $X_{p_1}\otimes\mathrm{diag}(F)$ on the
occupied strings; that the Walsh coefficients reproduce every fixed angle (residual $\le10^{-12}$); every term's
equality with $e^{-i\theta h}$ on its contract (A1); every full 28-qubit circuit's equality with the exact coarse state
(A2); the native conversion (Q1L, rounding bound $B$).  The identity "Walsh–Hadamard inversion exists for every angle
table" (used by the package's Gray chain) is not formalised; my circuits never rely on it because the Walsh
coefficients are solved and checked per instance.

## 4. What the result means

- **The two-qubit cost of a 2x4 coarse step drops from 71 548 to 582–800 (exact on the circuit's own input) or to
  about 1 740 (exact as an operator on every codeword), with the package's state bar certified on all 75 circuits of
  each class.**  Two-qubit depth drops from 70 300 to 292–469 and 1 275–1 280.
- The gain is structural, not a peephole effect.  Three facts about the Hamiltonian do the work, and each was found
  by a structure test before any loop ran: (i) every term factorises exactly over its vertices; (ii) in a corner
  frame the plaquette is one flip of one qubit, so the 82 multiplexors of the package's `plaq1` become one, with
  6–7 controls, plus four flags computed into clean ancillas from the duplicated link bits; (iii) from a single
  reference basis state each hop reaches only 0–12 of its blocks.  The loop (14 proposal programs, 5 iterations)
  then picked, per term and per reference, the cheapest construction that the independent evaluator verified.
- **Hardware consequence (package's own model, not a measurement).**  With the package's gate-only clean-shot
  fraction, the class-B finalists reach $f=0.47$–$0.58$ on H2-2 and $0.49$–$0.59$ on Helios-1 at native level 0. Class A
  reaches $f=0.20$ (H2-2) and $0.22$ (Helios-1).  Both are above the amendment-01 thresholds (mean $\ge0.1$, worst
  $\ge0.05$, `devices_20261002.json criterion`), where the frozen family sat at $4\times10^{-29}$
  (`validation/QN_2x4.json`).  With the package's memory estimate, H2-2 stays at $0.428$–$0.571$ (class B) and
  $0.154$–$0.195$ (class A).  Transport and crosstalk errors beyond that model are not included.
- Relative to phase 1's honest guess ("2–3x likely; 26–29x unlikely", `reports/001` §5.3), the result is far better.
  The guess assumed `plaq1` had no exploitable structure; the corner factorisation showed that it has.

## 5. Problems, assumptions, and what is NOT shown

- **Class B is input-specific.**  Each circuit is exact only on its own reference basis state, and its term
  circuits differ by reference.  The gate skeleton depends on $k$ only through rare merges by the peephole pass: ZZ
  varies by at most 2 within a reference in class B and by at most 4 across the class-A circuits.  It uses the structural reachable set, which is classical knowledge of
  the Hamiltonian's graph, not of the output state; no output state is loaded.  Whether the pipeline accepts
  input-specific circuits is a planner and owner question (`notes/005` item 1).
- **Verification method changed for A2** (`notes/006`): certified pruned simulation instead of the unpruned exact
  sparse simulator, because round-off residues made the exact simulator blow up (4.2 million strings for one class-B
  circuit; $2^{16}$ strings within 2 000 gates for class A).  The bar is unchanged and stated as a certified bound
  (Lean `telescoping_bound_mirror`).
- **Native circuits are verified by Q1L + rounding bound only** (as the package's Q0P_2x4 did before its GPU slot), not
  by simulating the native circuit.  Level-2 counts are information only.
- **Not proved in Lean, numerically checked per instance:** the factorisation of each specific term; the form
  $X_{p_1}\otimes{\rm diag}(F)$ of each frame generator; each Walsh solve; every term (A1) and every circuit (A2).
  The general identities these rely on are proved (§3.6).
- **Assumptions (mine).**  The gate-only and memory $f$ values use the package's device table and models unchanged.
  The approximate-class design value $N_{\rm sector}\le10^{6}$ shots is met by the signed plan
  (1 411 324 GPU shots over both sectors, `validation/CV_2x4_plan.json`).
- **Loop scale.**  The paper ran OpenEvolve with many LLM sessions.  Here the proposer is me, turn by turn (owner O5),
  with 14 proposal programs over 5 archived iterations; I make no claim about what an automated loop would find.
- Housekeeping: `pkill -f` patterns matched my own shell several times and stopped two background jobs early (re-run
  since; no data lost, the JSONs quoted here are from complete runs).

## 6. What I would try next

1. **Class A hops** (1 370 of 1 774): a dedicated spin-1 chain construction.  Fix the two basis-change rounds at
   $\pm\pi/4$, make the pair rotations multiplexors over the vertex labels only, and add dark/selection flags in clean
   ancillas, as for `plaq1`.  Today hop3 (256 CX) uses 5 multiplexors with 6–7 controls each; the parity-fold frame
   alone needed 22.
2. **`plaq1` frames** (about half of its 152–220): cheaper bright rotations (triply controlled $R_y$, 8 CX each, three per
   side), and a relative-phase multi-controlled X so that the multiplexor depends on the parity labels only.
3. **Cross-term frame merging**: adjacent terms share vertices; synthesise $F_{i+1}F_i^\dagger$ jointly instead of
   cancelling only identical CNOTs.
4. **Native level 2 with verification**: Q1L does not cover it; a GPU statevector slot (the package's) or a
   Clifford-aware local-equivalence check would turn the 3–5% ZZ gain and the 2.3x PhasedX reduction into a verified
   gain.
5. Lower bounds (planner request item 4).

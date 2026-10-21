# 001 — Independent verification of the phase-2 compression claim (class A 1 736–1 740 ZZ, class B 582–800 ZZ)

- Date: 2026-10-21.  Reviewer: reviewer-opus (independent check; not the proposer).
- Git commit at the start of the review: `6eb4528`.  `a9cd136` (notes/007) landed while the runs were going.
  `git diff 6eb4528..a9cd136` is empty for `2x4_compression_using_ai_v1/src`, `data/archive_it5.json`, `lean/`,
  `src/skqd`, `validation/E3.json` and `data/quantinuum/devices_20261002.json`.
- Claim under review: `reports/002-phase2-compression-results.md` §3.3, plus notes 003, 004 and 006.
- Every number below is taken from `reviews/001-independent-verification.json`, which is built from
  `reviews/001_runs/*.json`, `reviews/001_counts_all.json`, `reviews/001_native_f.json` and the two Lean logs.
  None is typed by hand.
- Nothing outside `reviews/` was written.  None of genie's files was modified.  Nothing was committed.

**Verdict: CONFIRMED WITH NOTES.**

## 1. What was asked

The task was to check genie's claim independently.  The claim is that the 2x4 coarse-step circuits, which use
71 548 ZZ gates in the frozen family, compress as follows:

- **Class A (operator-exact):** 1 736–1 740 ZZ.  "Operator-exact" means each term is exact on every codeword.
- **Class B (exact on the circuit's own reference input):** 582–800 ZZ.

The claim also says both classes meet the package bar, $\max|\Delta\psi|<10^{-10}$ and leakage $<10^{-9}$.

The check had to avoid genie's simulator and verification code.  It had to compare against the package's own
coarse state and use an independent engine (qiskit-aer) on all 28 qubits.

## 2. Actions taken

### 2.1 Circuits came only from genie's builders, with genie's cache bypassed

`001_build_circuits.py` imports `c2x4.family.archive_family("it5", cls, peephole=True)` and `circuit()`.  It
redirects every module-level `CACHE` to `reviews/001_cache/`, so the pickles in genie's `data/cache` are never
read and all 150 circuits are regenerated from source.  The 150 circuits are 2 classes $\times$ 15 references
$\times$ $k=1..5$.

### 2.2 Target and inputs (task item 1)

I inspected the code paths:

- **Genie's target.** `src/c2x4/problem.py:57-67`: `Problem.target` = `krylov.apply_groups(groups, basis_vector(ref), k*dt)`.
  This is the body of `krylov.coarse_states` (`src/skqd/krylov.py:59-64`).
  - The groups come from `Model(4).terms.groups(4.0, mass_default(4.0))`.
  - The references come from `krylov.references`.
  - `dt` comes from `data/quantinuum/circuits_2x4/index.json`, which records it as copied from `validation/E3.json`.
- **My target.** I recomputed it with the package call `coarse_states(term_groups(...), basis_vector(ref), dt, 5)[k]`,
  with `dt` read directly from `validation/E3.json`.  It is embedded with the package's
  `CodewordEmbedding(Model(4)).ints` (`Codec` layout; qubit $k$ = bit $k$, little-endian, `reference_sim.bits_to_int`).
- **What the builders read.** Only these inputs:
  - the local term matrices: `Problem.local` → `reference_sim.localize` of the package's groups;
  - $\theta=k\,dt$;
  - for class B, the structural reachable set `reach.Reach.before` (`reach.py:44-60`).  This is the union of the
    connected components of the earlier terms' graphs, starting from the reference bit string, with an entry
    threshold of $10^{-12}$ on matrix elements.  It depends on neither $\theta$ nor the amplitudes.
- **What the builders do not read.** `apply_groups`, `expm_multiply`, `Problem.target` and any exact output state.
  - `plaqfactor.py` and `hopframe.py` call genie's `term_unitary_columns` and `run_ir`, but only on the
    frame gate lists, to read off the framed local generator.  That is construction, not loading of a result.
  - The only output-state-dependent code is `reach.exact_trajectory` / `approx_contracts` (`reach.py:155-205`).  It is
    used only by the approximate class (note 004), which is not part of either claimed family.

### 2.3 Full 28-qubit statevectors with qiskit-aer (task item 2)

`001_verify_aer.py` does the following:

- **Conversion.** It uses its own IR→qiskit converter, which rejects any multi-qubit `unitary`.
- **Engine.** `AerSimulator(method="statevector", precision="double")`, fusion on, 12 threads, CPU, `coding` env
  (qiskit 2.5.2, aer 0.17.2).
- **Reading the output.** The output is read on the 37 165 codewords.
- **Leakage**, summed directly with no subtraction:
  - $L_{\rm nc}$: the weight on non-codeword strings;
  - $L_{\rm sec}$: the weight on codewords of the other baryon sector.
- **Deviation.** Reported after removing the global phase $\varphi=\arg\langle t|g\rangle$, as
  $\max_s|g_se^{-i\varphi}-t_s|$.
- **Run time.** Each run took 246–932 s, inside the 30-minute rule.

### 2.4 Class A operator test (task item 3)

- **Inputs.** Each of the 4 class-A circuits got two random normalised superpositions $|\phi\rangle$ of all
  sector codewords: complex Gaussian amplitudes, `numpy.random.default_rng(11)` and `(12)`, 12 843 (B=0) or
  8 934 (B=1) components.
- **How they were applied.** The input was loaded with `set_statevector` as $\mathrm{Prep}\,|\phi\rangle$.  The
  circuit begins with its X-gate preparation, and I checked that this prefix is exactly `prepare(ref)`
  (`prepare_prefix_ok`).
- **Reference.** The output was compared with the package's exact `krylov.apply_groups(groups, \phi, k\,dt)`.
- **Contrast run.** The same test was run once on a class-B circuit, to show what "input-specific" means.

### 2.5 Counts and $f$ (task item 5)

- **Counts.** `001_counts_all.py` recounts ZZ and two-qubit depth for all 150 rebuilt circuits from the qiskit
  circuit objects, in two ways: my own layer count, and `QuantumCircuit.depth(filter=2q)`.  It compares them with
  genie's JSON.
- **$f$.** `001_native_f.py` runs in the isolated `su2qc-quantinuum` venv.  It compiles with the package's
  `ir_to_pytket` → `compile_native(H2-2, level 0)` and counts ZZPhase and PhasedX from the pytket commands.  It then
  computes $f$ with `skqd.device_req.clean_shot_fraction`, using $\varepsilon_{\rm ro}$ = mean of the two SPAM values
  and $n_{\rm meas}=28$, which is the rule of `p1_device_threshold.py` and of the package.

### 2.6 Lean (task item 7)

- **Build.** `lean/` was copied to `reviews/001_lean/` with `.lake/packages` symlinked, and `lake build` was run there.
- **Axioms.** A separate file `Review001.lean` prints `#check` and `#print axioms` for the named lemmas.
- **Search for holes.** I grepped for `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `extern` and `unsafe`.

## 3. Results

### 3.1 Per-run table (28-qubit Aer statevector, complex128)

The columns are:

- "qubits": the circuit width / the number of qubits actually touched;
- ZZ and depth: recounted from the qiskit object;
- "genie dev": genie's own measured value for the same circuit, for comparison only.

| run | class | input | qubits | ZZ | 2q depth | $\max\lvert\Delta\psi\rvert$ (phase-aligned) | $\lVert\Delta\psi\rVert_2$ | $L_{\rm nc}$ | $L_{\rm nc}+L_{\rm sec}$ | global phase (rad) | bar | genie dev |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0_ref102_k1 | B | own ref | 28/28 | 660 | 349 | 2.80e-14 | 2.89e-14 | 7.7e-32 | 1.2e-31 | -0.688 | PASS | 2.39e-14 |
| B0_ref102_k5 | B | own ref | 28/28 | 660 | 349 | 2.05e-14 | 4.83e-14 | 1.1e-31 | 1.7e-31 | 2.842 | PASS | 2.14e-14 |
| B1_ref230_k1 | B | own ref | 28/28 | 582 | 292 | 2.44e-14 | 2.52e-14 | 5.3e-32 | 1.3e-31 | -0.586 | PASS | 2.36e-14 |
| B1_ref230_k5 | B | own ref | 28/28 | 582 | 292 | 1.73e-14 | 4.30e-14 | 1.4e-31 | 1.9e-31 | -2.932 | PASS | 1.73e-14 |
| B0_ref345_k4 (max ZZ) | B | own ref | 28/28 | 800 | 469 | 1.50e-14 | 2.52e-14 | 3.5e-31 | 4.1e-31 | -1.376 | PASS | 1.19e-14 |
| B0_ref102_k1 | A | own ref | 28/28 | 1740 | 1280 | 4.50e-14 | 4.67e-14 | 1.3e-31 | 4.2e-31 | -0.000 | PASS | 5.72e-14 |
| B0_ref102_k5 | A | own ref | 28/28 | 1738 | 1278 | 2.49e-14 | 6.14e-14 | 3.4e-31 | 5.7e-31 | -0.000 | PASS | 2.98e-14 |
| B1_ref230_k1 | A | own ref | 28/28 | 1740 | 1280 | 2.10e-14 | 2.19e-14 | 2.4e-31 | 4.8e-31 | 0.000 | PASS | 2.32e-14 |
| B1_ref230_k5 | A | own ref | 28/28 | 1740 | 1280 | 1.67e-14 | 4.40e-14 | 4.2e-31 | 5.9e-31 | 0.000 | PASS | 2.14e-14 |
| B0_ref102_k1 | A | seed 11 | 28/28 | 1740 | 1280 | 1.57e-15 | 5.03e-14 | 2.4e-31 | 4.4e-31 | -0.000 | PASS | – |
| B0_ref102_k1 | A | seed 12 | 28/28 | 1740 | 1280 | 1.34e-15 | 5.03e-14 | 2.4e-31 | 4.4e-31 | -0.000 | PASS | – |
| B0_ref102_k5 | A | seed 11 | 28/28 | 1738 | 1278 | 1.17e-15 | 4.31e-14 | 8.3e-31 | 1.1e-30 | 0.000 | PASS | – |
| B0_ref102_k5 | A | seed 12 | 28/28 | 1738 | 1278 | 1.17e-15 | 4.30e-14 | 8.2e-31 | 1.0e-30 | 0.000 | PASS | – |
| B1_ref230_k1 | A | seed 11 | 28/28 | 1740 | 1280 | 7.42e-16 | 2.34e-14 | 2.6e-31 | 4.6e-31 | -0.000 | PASS | – |
| B1_ref230_k1 | A | seed 12 | 28/28 | 1740 | 1280 | 7.14e-16 | 2.34e-14 | 2.5e-31 | 4.5e-31 | -0.000 | PASS | – |
| B1_ref230_k5 | A | seed 11 | 28/28 | 1740 | 1280 | 9.54e-16 | 2.54e-14 | 1.0e-30 | 1.2e-30 | -0.000 | PASS | – |
| B1_ref230_k5 | A | seed 12 | 28/28 | 1740 | 1280 | 9.38e-16 | 2.55e-14 | 9.8e-31 | 1.2e-30 | -0.000 | PASS | – |
| B0_ref102_k1 (contrast) | B | seed 11 | 28/28 | 660 | 349 | **2.30e-02** | 4.52e-01 | 1.6e-02 | 3.0e-02 | 0.966 | (not claimed) | – |

All 9 own-reference runs and all 8 class-A operator runs meet the bar.  The largest own-reference deviation is
4.50e-14, about $2000\times$ below $10^{-10}$.  For the random-superposition inputs every amplitude is about
$1/\sqrt{12\,843}\approx 9\times10^{-3}$, so the max-entry number is naturally small; the $\ell_2$ norm of the
difference ($\le 5.03\times10^{-14}$) is the meaningful number there.

### 3.2 Class B: the dropped diagonal group (task item 4)

- **The group is diagonal.** The diagonal group `groups["diag"]` has 0 off-diagonal non-zeros.
- **What dropping it does.** On a reference basis state, $e^{-i\theta H_{\rm diag}}e_{r}=e^{-i\theta (H_{\rm diag})_{rr}}e_r$.
  Leaving it out multiplies the output by exactly $e^{+i\theta (H_{\rm diag})_{rr}}$.
- **Measured.** The measured global phase minus the prediction $\theta (H_{\rm diag})_{rr}$ is at most
  $2.8\times10^{-14}$ rad over the five class-B runs.  For example, B1_ref230_k1 has $(H_{\rm diag})_{rr}=-4.5$,
  a predicted phase of $-0.586407$ rad, and a residual of $5.6\times10^{-16}$ rad.
- **Conclusion.** It is a pure global phase, and it is invisible to computational-basis sampling.

### 3.3 Counts and $f$ (task item 5)

**Counts, all 150 rebuilt circuits.** There are 0 mismatches with genie's `eval_arch_it5_*_pp_all75_pruned.json`.

| | class A | class B |
|---|---|---|
| ZZ | 1736–1740 (mean 1739.2) | 582–800 (mean 683.52) |
| 2q depth | 1275–1280 | 292–469 |
| qubits touched | 28 | 28 |
| multi-qubit `unitary` gates | 0 | 0 |

My layer depth equals qiskit's filtered depth on every circuit.

**$f$ on H2-2, gate-only, native level 0:**

| circuit | ZZ | PhasedX | $f$ (package formula) | genie's value |
|---|---|---|---|---|
| class B, B1_ref230_k1 | 582 | 1564 | **0.5751** | 0.5751 (identical to 16 digits) |
| class A, B0_ref102_k1 | 1740 | 4846 | **0.2006** | 0.2006 (identical) |

Here $f=(1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{\rm ro})^{28}$ with
$\varepsilon_2=8.3\times10^{-4}$, $\varepsilon_1=2.8\times10^{-5}$ and $\varepsilon_{\rm ro}=9.35\times10^{-4}$.

### 3.4 Lean (task item 7)

- **Build.** `lake build` completes with "Build completed successfully (9056 jobs)" and 0 errors (`001_lake_build.log`).
- **Holes.** There are no `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, `extern` or `unsafe`.
- **Axioms.** `#print axioms` (`001_lean_axioms.log`) gives:
  - `telescoping_bound_mirror`, `exp_intertwine`, `dropped_part_bound`, `diagonal_mulVec_single`, `exp_conj_frame`,
    `ccz_circuit` and `exp_xt_diag`: [propext, Classical.choice, Quot.sound];
  - `agree_on_reachable_n`: no axioms.

## 4. What the result means

- **The claim reproduces.**
  - The compressed circuits really are 28-qubit circuits with the stated ZZ counts and depths.
  - On an engine that shares no code with genie's evaluator (Aer dense statevector, my own converter, my own
    target computed with `coarse_states` and the E3 `dt`), they reproduce the package's coarse states to
    $\le4.5\times10^{-14}$, with leakage $\le1.2\times10^{-30}$.
  - Class A also reproduces the exact coarse-step operator on random sector superpositions, global phase
    included (phase $|\varphi|\le10^{-13}$ rad).
- **What "exact on own input" means for SKQD.** Each class-B circuit equals $\prod_\gamma e^{-ik\,dt\,H_\gamma}$ only
  when it is applied to its own reference bit string (up to the known global phase).  The package's 2x4 plan uses
  each (reference, $k$) circuit exactly that way: one coarse step from $|0\rangle$ through `prepare(ref)`, then
  computational-basis sampling (`validation/CV_2x4_plan.json`, 60 circuits).  So class B is usable in the pipeline
  as it stands.
- **No hidden dependence on the output state.** Class B knows only the structural reachable set, which is the
  graph of the Hamiltonian's terms.  It does not know amplitudes.
- **Physics of the corner factorisation (task item 6).**
  - **Inherits the package's conventions.** The factorisation is a numerical fact about the package's own term
    matrices: it is fitted to `localize(Model.terms.groups)`, so it carries `su2.py` and `lattice.py` conventions
    with it.  No convention is reintroduced by hand.
  - **Hop phases agree with `lattice.py`.** The hop structure genie found ($\eta=i$ on x-links, real on y-links;
    for example hop0 = link (0,2,x), hop1 = link (0,1,y), in `data/p2_1_structure.json`) agrees with `lattice.py`
    (`eta = i` on x-links, $(-1)^{x_1+x_2}$ on y-links).
  - **Physics reading.** The Wigner–Eckart reading (each corner is an SU(2)-invariant map, so the colour
    contraction leaves scalar corner factors) is a plausible reason.  It matches the known factorisation of
    plaquette matrix elements into vertex recoupling coefficients in a gauge-invariant basis.  It is not needed for
    correctness, because every circuit is checked end to end.
  - I found no convention mismatch.  The end-to-end agreement at $10^{-14}$ would have exposed a wrong sign of
    $\eta$, a wrong qubit order or a wrong codeword layout.

## 5. Problems, notes and assumptions

1. **Class B is not operator-exact, and must not be used as if it were.**
   - On a random B=0 superposition, B0_ref102_k1 (class B) gives $\max|\Delta\psi|=2.30\times10^{-2}$ and a
     sector leakage of $3.0\times10^{-2}$ (contrast row in 3.1).  This is expected and is not a failure of the claim.
   - It does mean class B is invalid for any use other than "prepare own reference, one coarse step, sample".
     Invalid uses include repeated steps ($r>1$ repetitions, as the 2x2 H0 circuits had), Hadamard-test or
     controlled versions, or reusing one circuit for another reference.
   - Any later plan that changes the use pattern must switch to class A.
2. **"Certified" in note 006 leaves out floating-point rounding.**
   - `telescoping_bound_mirror` bounds $\lVert v-u\rVert$ by $\sum_i\lVert V_i(v_i)-U_i(v_i)\rVert$.  In the pruned
     simulator each $V_i$ is a floating-point gate followed by pruning, but $B_{\rm prune}$ adds up only the pruned
     norms.
   - So "certified" holds modulo rounding (about $10^{-16}$ per gate, about $10^{-13}$ over 3 000 gates).
   - Not blocking: my unpruned Aer runs give the same $10^{-14}$ level without any pruning.
3. **The Lean statements are generic lemmas, not the instances the circuits rely on.**
   - **`agree_on_reachable_n`** is pointwise agreement on sets.  Three steps of the argument are not formalised:
     - the step from "a local term circuit $W$ agrees with $e^{-i\theta h}$ on touched blocks" to "$W\otimes 1$
       agrees on the span of the reachable basis states" (linearity, tensoring with the environment);
     - the hypotheses for the actual terms;
     - the reachability map $U_i(S_i)\subseteq S_{i+1}$.
   - **`exp_intertwine`, `exp_conj_frame` and `exp_xt_diag`** are correct general matrix identities.
   - **`telescoping_bound_mirror`** is the abstract telescoping bound; how it is applied to the pruned run is not
     formalised (see note 2).
   - **`dropped_part_bound`** serves only the approximate class, which is not used.
   - **Rests on numerical checks only:** each term's factorisation, each frame generator's form, each Walsh solve,
     and every circuit.
   - Genie states this split honestly (002 §3.6, §5).  My Aer runs now give an independent numerical check of
     the circuit-level claims for the 9 circuits listed above and the 8 operator tests.  The remaining 66 class-B
     and 71 class-A circuits were not re-simulated; their counts were recounted.
4. **The approximate class does read classical amplitudes.** `reach.approx_contracts` drops blocks by their weight
   along the exact classical trajectory.  That is a different kind of input-specificity from class B, which is
   structural only.  It is not part of the claim, and 002 §3.5 reports no gain from it.  If it is ever adopted it
   needs its own review.
5. **Noise is not covered.** Class B acts arbitrarily on unreachable blocks, so a gate error that moves amplitude
   off the reachable set is propagated differently than in an operator-exact circuit.  The gate-only $f$ is
   unaffected; the noisy output distribution of class B versus class A was not studied here, by anyone.
6. **Coverage.** I simulated 9 own-reference circuits: 5 class B, including the maximum-ZZ one, B0_ref345_k4,
   and 4 class A.  I also ran 8 class-A operator tests and 1 contrast run, out of 150 circuits.  The time cost was
   246–335 s per class-B run and 740–932 s per class-A run.  At that cost the full 150 would take about 22 h, so I
   did not run them.
7. **Assumptions.**
   - The circuits I simulated are the ones genie's builders produce at `6eb4528` from source.  I did not check
     whether genie's own cached pickles are identical to them.  Their counts agree on all 150.
   - Aer's gate fusion was on.  The package measured fusion's effect at about $3\times10^{-14}$ (`circuits_qiskit.statevector_aer` docstring).

## Files

`reviews/001-independent-verification.json` (all numbers, commit, machine, seeds, commands);
`reviews/001_build_circuits.py`, `001_verify_aer.py`, `001_counts_all.py`, `001_native_f.py`, `001_aggregate.py`,
`001_queue.sh`; per-run JSON `reviews/001_runs/`; logs `001_queue.log`, `001_build.log`, `001_lake_build.log`,
`001_lean_axioms.log`; Lean copy `reviews/001_lean/`; rebuilt circuits `reviews/001_cache/circuits.pkl` (regenerable).

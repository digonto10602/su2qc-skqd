# 22 — 2x4: compile the coarse step to exact circuits, measure its duration and idle budget, derive the device requirement
executor: executor-opus   effort: high (xhigh on the second attempt); runner-sonnet low for the staged runs and the regressions; scribe-haiku low for the status tables
time budget: 2 days of laptop work in commands < 30 min each; **0 QPU seconds**; Perlmutter only as the optional independent cross-check of part F (owner adds the token)   machine: laptop CPU (i7-8750H, 62 GiB; no usable GPU)

> Written by planner-fable at max effort on 2026-09-30.  The planner's own computations (P1–P7, with snippets)
> are in `reports/S2_2x4_planner_analysis_20260930.md`; read it first.  This prompt runs **in parallel with
> prompts/20**: the do-not-touch list at the end is binding, and every file this prompt creates is new.  It changes
> **no criterion constant, no convention, no decoder, no existing validation JSON**.

## Goal
The owner asked what a device must deliver to run 2x3 and 2x4.  For nearly serial circuits the requirement reduces
to one dimensionless number, T2/t_2q >= n_qubits x n_2q / (2 ln(1/f_target)): 667 / 1728 at 2x2 (all-to-all /
routed), 9372 / 23786 at 2x3, 7036 for the 2x3 fixed-angle generator (P3 reproduces all five from the committed
counts).  **For 2x4 there is no number, because the circuits were never compiled**; the owner's "above 1e5" is an
extrapolation from two points.  Replace it by a measurement: compile the 2x4 coarse step (28 qubits, 14 term groups,
`validation/E3.json` references) to exact basic-gate circuits with the structured engine of `skqd.circuits_ir`,
verify them at least as strongly as gate S2 verified 2x3, measure two-qubit counts (all-to-all and routed), depth,
the ASAP-scheduled duration and the per-qubit idle budget through `skqd.idle`, and derive the T2/t_2q requirement
for 2x4 on the same footing as 2x2 and 2x3 — exact and fixed-angle — so that the vendor specification covers all
three lattice sizes.  The deliverable is gate **`S2_2x4`** (a measurement gate: PASS means *compiled, verified,
measured*, never *affordable*; the manual's Step 4.3 budget has no 2x4 line and none is invented here).

### What the planner already measured (P1–P6), so that the executor confirms rather than discovers
- 2x4: 28 qubits (codec widths `[3,3,4,4,4,4,3,3]`), 37165 states, 10 links, 3 plaquettes, references 11 (B = 0) + 4
  (B = 1).  **`plaq1` acts on 16 qubits** (four interior corners: 1831 local codewords, 811 blocks, largest block 9
  configurations of degree 8, 10 distinct |elements|, 8 flip patterns); `hop3`/`hop5` (sites 2→4, 3→5) are the
  interior-to-interior x-link type absent at 2x3 (11 qubits, blocks up to 6).  All 22 hop/plaq blocks of 2x3 and 2x4
  have a zero diagonal (P1).
- The structured engine synthesised and verified **all 14 term groups with no code change** at the gate-S2 standard:
  max deviation 4.2e-15 (hops, plaq0, plaq2) and 4.1e-14 (plaq1) on the local codeword space (P5).  No block was
  non-bipartite, `_real_gauge` succeeded everywhere (all rotations are Ry), no assertion fired.  **The risk the owner
  named is cost, not construction.**
- Cost (IR, theta = dt): hop0 278 cx, hop1 54, hop2 258, hop3 1548, hop4 390, hop5 542, hop6 260, hop7 390, hop8 244,
  hop9 54, plaq0 228, **plaq1 66468**, plaq2 806 — **71520 IR cx for the 13 hop/plaq terms** (the 2x3 step has 2588
  IR cx for 2164 CZ after level-3 transpilation).  plaq1 has 82 multiplexed rotations with 7–11 controls; synthesis
  152 s, verification 172 s per theta.  Fixed-angle: 16546 IR cx (plaq1 12952), all terms leak-free (worst 3.2e-13).
- Dense 2^28 statevectors cost 0.7–3.8 s **per gate** on this CPU (P4): the full coarse step is 10–20 h per circuit,
  one hop term 20 min.  Only `hop1` (94 IR gates: about 4 min and 17 GB peak, a planner estimate from P4's per-gate costs, not a
  measurement) is affordable dense at 28 qubits.
- qiskit 2.5.2 transpiles the 4930-gate 2x3 step in 0.2–1.9 s at any level and map (P6): transpilation is not a
  budget item; level 3 stays the standard.
- Disjoint term pairs (hop/plaq): 2x2 1 of 10, 2x3 10 of 36, 2x4 **35 of 78**; the term-overlap graph is
  6-colourable at both 2x3 and 2x4 (P2).

## Inputs
- `reports/S2_2x4_planner_analysis_20260930.md` (P1–P7 and snippets), `prompts/06`, `prompts/11`,
  `validation/S2.json`, `validation/S2_fixed.json`, `validation/E3.json` (2x4: dt 0.11469820342078263 at 2B = 0,
  0.1303127653995423 at 2B = 2; dims 12843 / 8934), `data/S2_duration_compare.json` (the frozen canary's schedule:
  T_s 4.3708e-05, S_T1 0.7552952713856562, S_T2 2.5675961961706695, n_cz 663, depth 1328, cz_depth 455),
  `data/S2D_2x3_device_requirements.json` (2x3 RZZ 2158, the declared error triple 1e-3 / 1e-4 / 2e-3),
  `validation/S2D_idle.json` (`data.device_requirement`, the coherence-scale convention),
  `data/hardware/H0_diag_prep/calibration_20260922T1400Z.json` (Heron durations: cz 68 ns, sx 24 ns, measure
  1.66 us; the 12 canary qubits' T1/T2), `data/hardware/H0_prep/circuits/B0_ref06_k1_rep1.{json,qpy.gz}` (the frozen
  canary QPY — read only).
- Code (read before writing): `src/skqd/circuits_ir.py` (`ucr_gray`, `_real_gauge`, `_block_rounds`,
  `_multiplexed_two_level`, `_reduce_controls`, `structured_term_gates`, `CircuitFactory`, `run_ir`),
  `src/skqd/reference_sim.py` (`term_support`, `localize`, `CodewordEmbedding`), `src/skqd/idle.py` (**import, never
  edit**: `schedule_asap`, `idle_budget`, `idle_log_budget`, `f_idle_aware`), `src/skqd/device_req.py`
  (`required_error`, `target_with_idle`), `scripts/gate_S2.py` (`term_deviation`, `term_leakage_and_deviation`, the
  transpile settings: `cq.transpile_counts`, level 3, seed 7), `scripts/s2_duration_compare.py` (`term_supports`,
  `packing_bound`, `measure` — the schedule/idle/packing pattern to reuse), `scripts/gate_S2D_idle.py`
  (`coherence_scale`, `f_gates_on_record`, `log_budget_accounting` — importable, not editable), `scripts/h0_backends.py`
  (`calibration_record`: the record format `skqd.idle` reads), `scripts/h0_build_circuits.py` (`repeated_coarse_step`),
  `src/skqd/hpc.py` (`ci_context`), `scripts/s3_device_model.py` (the CI-aware GPU pattern), `tests/test_circuits_ir.py`,
  `tests/test_idle.py`.
- Environment: qiskit 2.5.2 / qiskit-aer 0.17.2 / qiskit-ibm-runtime 0.49.0 on the laptop; the Perlmutter CI runs
  qiskit 1.4.3 / aer 0.15.1 (part F must load on both; no qiskit import at module load of a gate module).

## Planner decisions carried by this prompt
- **Route.**  The structured engine as it stands.  One additive change to `circuits_ir.py` (A1) and one additive
  instrumentation (A2); nothing in the 2x2/2x3 gate lists may change bit for bit (C9 checks it).
- **The gating question is answered, the branch is kept.**  The support width decides nothing about correctness —
  term verification never needed the dense local unitary (it was never built at 14 qubits either; `localize`'s block
  `h` and `run_ir` on 2^k do the job at k = 16 in 1 MB).  It decides synthesis time and gate count.  The executor
  nevertheless re-measures the supports first (B2) and stops if any differs from P1.
- **Full-circuit verification** goes through an exact *sparse* statevector simulator (D), regressed against `run_ir`
  at 2x2/2x3 and against one dense 2^28 run of `hop1`; the dense route is used nowhere else on the laptop.
- **The requirement is computed, not assumed**: the serial formula is printed next to the scheduled PTA number from
  `skqd.idle` on a uniform record, at the Heron durations and at t_1q = 0, with T1 = infinity and T1 = T2.
- **No affordability criterion, no device verdict.**  The gate produces the requirement; the owner matches hardware.
- **Not in this prompt** (each is its own method decision): term reordering to the 6-round packing (changes the
  coarse-step state; needs a recall re-emulation), the two compilation levers of P5 (control minimisation above
  m = 10; star-block diagonalisation), the fixed-angle recall at 2x4, the Aer-scheduled prediction at 28 qubits.

## Steps

### A. Engine (`src/skqd/circuits_ir.py`, additive; about 2 h)
A1. `ucr_gray`: the Gray-code angle transform `alpha = M^T theta / N` builds `M` (N x N) in a Python double loop —
    N = 2^c, so at c = 11 that is 4.2e6 Python operations per rotation and at c = 15 it is 1e9.  Add the fast form:
    `alpha_j = (1/N) (WHT theta)[gray(j)]` with an O(N log N) Walsh–Hadamard butterfly in numpy.  **Use it only when
    c > 10** (module constant `UCR_FAST_MIN_CONTROLS = 11`); for c <= 10 the existing construction runs unchanged, so
    every 2x2 and 2x3 gate list (max 7 controls) is bit for bit what it was.  Test (`tests/test_circuits_ir.py`):
    for k = 0..8 the two constructions give the same gate names/qubits and |delta alpha| <= 1e-15 (P5 measured
    1.1e-16); for k = 11 the fast form matches the old one on one random angle table to 1e-12 (the old O(N^2)
    construction runs in the test only; about 5 s).
A2. `structured_term_gates(..., stats=...)`: add to every stats entry the keys `real_gauge_found` (bool: `_real_gauge`
    returned a nonzero mask or the generator was already imaginary) and `block_rounds_fallback` (bool: `_block_rounds`
    took the `_generic_two_level(expm)` branch because a block was non-bipartite or had a nonzero diagonal), and to the
    module a function `term_structure(model, O, support)` returning P1's row (support, local states, blocks, largest
    block, block-size histogram, max degree, distinct |elements|, flip patterns, `diag_nonzero`).  Additive keys only;
    `scripts/gate_S2.py` reads none of them.
A3. Regression, run by the runner after A1–A2: `python scripts/gate_S2.py --quick --no-tests --out S2_repro` (about 3
    min) and `python scripts/gate_S2.py --angle-mode fixed --quick --no-tests --out S2_fixed_repro` (about 3 min):
    `data.2x2.per_term_cz`, `per_term_cz_routed`, `coarse_step.*.cz`, `coarse_step.*.depth` and the same 2x3 keys must be
    **identical** to `validation/S2.json` / `validation/S2_fixed.json` (the fixed run also compares `per_term_leakage`
    to 1e-15).  Record the comparison in `validation/S2_2x4.json` (criterion C9) and delete `validation/S2_repro.json`,
    `validation/S2_fixed_repro.json` and the two reports they wrote (test outputs, not gate outputs).

### B. Gate script `scripts/gate_S2_2x4.py`, staged for the 30-minute rule (about 1 day)
Every stage writes its fragment to `data/S2_2x4/<stage>_<tag>.json` and its IR caches to `data/S2_2x4/cache/` (gitignored:
add the line to `.gitignore`; caches are regenerable in < 20 min); `--stage assemble` reads the fragments and writes the
gate JSON and report.  `python scripts/run_gate.py S2_2x4` runs `--stage assemble` (so the CI and the runner see one
command); the stages are run by hand in the order below.  `--lattice 4` is the default; `--lattice 2|3` runs the same
stages on the smaller lattices for the regressions and the like-for-like rows.
B1. `--stage refs`: `Model(4)` (10 s); read `validation/E3.json` and assert `|Model(4).reference(4.0, twoB).dt − dt_E3|
    <= 1e-12` and the dims for 2B = 0, 2; `references(basis, 0)` has 11 entries, `references(basis, 2)` 4.  About 1 min.
B2. `--stage structure`: `term_structure` (A2) for every hop/plaq term of 2x3 and 2x4, the disjoint-pair count among
    hop/plaq terms and including diag, the chromatic number of the overlap graph (exact backtracking; 13 nodes).  Must
    reproduce P1/P2 (supports 9,6,10,11,8,11,10,8,9,6,14,16,14 at 2x4; 35 of 78 disjoint; chromatic 6 at both).
    **Stop here if any value differs from P1/P2** — that is a change in the model, not in this prompt.  About 2 min.
B3. `--stage synth --angle-mode exact|fixed --only <terms>`: `structured_term_gates` per term at theta = dt, 2dt, 4dt
    (exact) or dt (fixed), verification exactly as `gate_S2.term_deviation` / `term_leakage_and_deviation` (random
    vectors of the local codeword space: 20 for k <= 10, 5 for k = 11 and 14 — gate S2's counts — and 3 for k = 16,
    where one vector costs 57 s per theta; `--nvec 5` for plaq1 is an optional second command if the 30 minutes allow), stats (controls
    histogram, `real_gauge_found`, `block_rounds_fallback`), synthesis and verification wall time, IR gate counts;
    cache the IR per (term, mode, theta).  Commands and budgets: `--only hop0,hop1,hop2,hop3,hop4,hop5,hop6,hop7,hop8,
    hop9,plaq0,plaq2` exact (about 4 min), the same fixed (about 2 min), `--only plaq1 --angle-mode exact` (3 theta x
    (152 + 172) s = about 17 min — **one command**), `--only plaq1 --angle-mode fixed` (about 2 min).  The verification
    of plaq1 at 2^16 with 132554 gates is 57 s per vector: keep 3 vectors per theta.
B4. `--stage compile`: assemble the coarse-step IR from the caches for (B = 0, ref index 0 = Dirac sea, k = 1),
    (B = 0, ref 0, k = 4), (B = 0, ref 1, k = 1) and (B = 1, ref 0, k = 1) — exact and fixed; transpile with
    `cq.transpile_counts` settings (basis rz/sx/x/cz, level 3, seed 7) on all-to-all, `CouplingMap.from_heavy_hex(5)`
    (57 qubits, the 2x3 map of gate S2), `from_heavy_hex(7)` (115) and the FakeFez coupling map (156, the Heron r2
    layout); record per circuit n_2q, n_1q, n_rz, depth, cz_depth (`s2_duration_compare.cz_depth`), transpile time;
    per-term counts on the same four maps for the k = 1 term gates.  Record the **structure identity**: whether the term-gate IR
    counts are identical across k and references of a sector, and whether the transpiled n_2q is (it was at 2x3:
    2158 RZZ on every one of 44 circuits); a difference is reported with the term that carries it, not asserted away.  Also transpile the 2x3 k = 1 step on all-to-all, d = 5 and FakeFez, and the
    2x2 step on all-to-all and d = 3 in the same run (like-for-like rows; the S2 counts must reappear).  About 10 min.
B5. `--stage schedule`: for every transpiled circuit of B4, `skqd.idle.schedule_asap` and `idle_budget` on a **uniform
    record** built by `skqd.coherence.uniform_record` (E1) with the Heron durations of the named record (cz 68 ns, sx and
    x 24 ns, measure 1.66 us, dt 4e-9 s) and again with t_1q = 0 (the formula's premise); outputs per circuit: T_s,
    T_total_s, seriality T / (n_2q t_2q), qubit-time utilisation, idle_total, idle_max, n_windows, the packing bound
    T_min = max_q busy_q and T_min / T (`s2_duration_compare.packing_bound` logic), and the requirement of E2:
    T2_req at f_target 0.1 and 0.05 with T1 = infinity and with T1 = T2, T2_req / t_2q, the serial formula
    n x n_2q / (2 ln(1/f)) and the ratio measured / formula.  Then on the **FakeFez full-device record**
    (`h0_backends.calibration_record(FakeFez(), all qubits, all edges)`, as `s2_duration_compare.py` builds it) for the
    FakeFez-routed circuits: S_T1, S_T2, the coherence scale `lam` for mean f >= 0.1 with the record's gate errors
    (`gate_S2D_idle.coherence_scale` semantics; expect `None` = unreachable at any coherence at 2x4, and say why:
    `log_budget_accounting`) and the **coherence-only** scale (gate and readout errors set to zero) which always exists.
    2x2 anchor in the same stage: the frozen canary QPY on the real record must reproduce T_s, S_T1, S_T2 of
    `data/S2_duration_compare.json` to 1e-9 relative (C7).  About 10 min (the 2x4 circuits have about 3e5 instructions;
    `schedule_asap` is a Python loop — time it and report).
B6. `--stage circuits` (part D's simulator): the sparse statevector of the four 2x4 coarse-step circuits (exact) against
    `krylov.coarse_states` embedded on the codeword integers (`CodewordEmbedding.ints`): max |delta| and leakage; the
    sparse statevector of the level-3 all-to-all **transpiled** k = 1 B = 0 circuit: leakage (C6); the dense 2^28
    cross-check of `hop1` (D3).  Expect < 10 min per coarse step (D2's budget); if a circuit exceeds 20 min, stop that
    circuit, record the wall time and the sparse support size, and report — do not reduce the check silently.
B7. `--stage assemble`: criteria C1–C10, `validation/S2_2x4.json`, `reports/S2_2x4_compilation_and_device_requirement.md`
    (sections: what PASS means; the gating table; per-term cost exact/fixed with the 2x3 columns beside; coarse-step
    counts per map for 2x2/2x3/2x4; the duration/idle/requirement table with the serial-formula column; disjointness,
    chromatic number, packing bound; verification detail; honest limits; criteria).  Every number from the JSON.

### C. Gate-only requirement (in B5's fragment; about 30 min)
For every (lattice, map, family) row: the two-qubit error bound at zero idle and zero one-qubit/readout error,
`device_req.required_error(n_2q, 0.1, 1.0)` (and at 0.05), and at the S2D declared eps1 = 1e-4 / eps_ro = 2e-3
(`required_error_for_set` on the single circuit; at 2x4 the one-qubit channel alone exceeds the budget — report
`None` with the budget accounting, not a number).  These sit next to the coherence numbers so that the vendor reads one
table: the criterion is one half-space, n_2q eps2~ + n_1q eps1~ + n_meas eps_ro~ + S_idle <= ln(1/f_target)
(`device_req.target_with_idle`), and the T2/t_2q number is its coherence-only face.

### D. The exact sparse simulator `src/skqd/sparse_sim.py` (new; about 4 h)
D1. State = (sorted unique int64 index array, complex amplitude array).  Gates: `x`, `cx`, `p`, `cp`, `rz`, `gphase`
    are permutations/phases (vectorised on the index array; re-sort only when the index set changes); `ry`, `rx`, `h`,
    `unitary` (1 qubit), `sx` on qubit t first **close the set under the flip of t** (union with `idx ^ (1 << t)`, zero
    amplitudes for new entries) and then mix pairs in place through the partner index; `mcu` masks by the control state;
    `cz` is a phase.  Provide `run_sparse(gates, n, init_int)` for IR lists and `run_sparse_qiskit(tq)` for transpiled
    circuits (ops rz, sx, x, cz, barrier, measure ignored, global phase), `project(idx, amps, ints)` returning the dense
    vector on given integers and the leakage 1 − sum |proj|^2.  Two facts make it cheap: within a multiplexed rotation
    every Ry and every CX(control -> target) acts on one target, and once the set is closed under that target's flip,
    CX(c -> t) maps the set to itself (c differs from t), so the set changes only at the compression/frame CNOTs and at
    the first rotation of a new target; the support stays <= (codewords present) x 2^(distinct targets).  Never drop an
    entry by magnitude: exactness is by construction.
D2. Budget: a 2x4 k = 1 coarse step is about 142000 IR gates; at about 1 ms per gate on a 2e5-entry support that is
    2–3 min plus the set changes.  Measure and record `sparse_max_support`, `sparse_wall_s` per circuit.
D3. Regressions (`tests/test_sparse_sim.py`, and repeated inside `--stage circuits --lattice 2|3`): at 2x2 the 20
    circuits of gate S2 (both sectors, k = 1..4, Trotter) against `run_ir` to **1e-13**; at 2x3 the k = 1, 2 circuits of
    ref 0 (2^20, about 40 s each dense) to 1e-13; at 2x4 the `hop1` term gate applied to the Dirac-sea codeword,
    `run_ir` at n = 28 (94 gates, about 4 min by P4's per-gate costs, 17 GB peak — check `/proc/meminfo` MemAvailable >= 24 GB first; if less,
    the criterion FAILS with the reason recorded, the run is not skipped silently) against the sparse result to 1e-13.
    Keep the 2x3 and 2x4 dense checks out of the default pytest run (mark `slow`; the gate runs them).

### E. The coherence module `src/skqd/coherence.py` (new; about 3 h; `skqd.idle` imported, never edited)
E1. `uniform_record(n_qubits, edges, t_2q, t_1q, t_ro, T1, T2, dt=4e-9, sx_error=0.0)` in the exact
    `h0_backends.calibration_record` format (`qubits[str q]`: `sx_duration_s`, `x_duration_s`, `measure_duration_s`,
    `T1_s`, `T2_s`, `sx_error`, `measure_error`, ...; `edges["a-b"]`: `cz_duration_s`, `cz_error`; `dt_s`).
E2. `t2_requirement(sch, record, f_target, t1_mode)`: the uniform T2 at which `idle_log_budget(idle_budget(sch, record,
    t2_s, t1_s)[1]) = ln(1/f_target)`, by bisection on log T2 (monotone), `t1_mode in {"inf", "equal"}`; returns T2_req,
    T2_req / t_2q, S at T2_req (must equal the budget to 1e-9), the T1 share.  `serial_bound(n_qubits, n_2q, f_target)
    = n_qubits n_2q / (2 ln(1/f_target))`.  `seriality`, `utilisation`, `packing_bound` (from the schedule).
    `coherence_scale_one(tq, record, f_gates, f_target)` = `gate_S2D_idle.coherence_scale` for one circuit with an
    explicit `f_gates` (1.0 for coherence-only).
E3. Tests (`tests/test_coherence.py`): (i) a hand-built 3-qubit circuit of serial CZs on a uniform record: the ASAP T
    equals n_2q t_2q and, with t_1q = 0, `t2_requirement` at small windows reproduces the serial formula to 1 % (the
    linearised limit — use T2 >> window); (ii) the frozen canary QPY on the real record reproduces T_s 4.3708e-05,
    S_T1 0.7552952713856562, S_T2 2.5675961961706695 to 1e-9 relative (C7); (iii) the serial formula on the committed
    counts gives 667.1, 1727.6, 9372.1, 23786.3, 7035.6 to 0.1 (C8); (iv) `t2_requirement` is monotone in f_target and
    in n_2q on the same schedule.

### F. Perlmutter cross-check branch (code only; about 2 h; the job is the owner's decision)
`--stage gpu` under `skqd.hpc.ci_context()`: Aer statevector on the GPU (`circuits_qiskit._aer_simulator(device="GPU",
method="statevector")`, double precision) of the k = 1 B = 0 exact 2x4 circuit and of the `plaq1` term gate applied to the
Dirac-sea codeword, noiseless, `save_statevector`; write **only** the projected amplitudes on the 37165 codeword integers,
the leakage and the max |delta| against `coarse_states` / the sparse simulator (never the 4.3 GB vector) to
`validation/S2_2x4_gpu.json` with the telemetry block of `s3_device_model.py`.  Same code path on the laptop with
`--stage gpu --lattice 2 --device CPU` (12 qubits, seconds) must agree with `run_ir` to 1e-13 before the branch is
considered tested.  Proposed allowlist line for the hand-back: `S2_2x4 00:30:00 1`.  Until the owner adds it, the laptop
result stands on D3's regressions; nothing is requested from the CI by this prompt.

### G. Bookkeeping (about 1 h)
`pytest -q tests` (the default run must stay under 8 min: mark the 2x3/2x4 dense checks `slow`);
`python scripts/check_package.py`; `graphify update .`; append the row `("S2_2x4", "2x4 coarse step compiled to exact
circuits and verified (measurement gate: counts, duration, idle budget, T2/t_2q requirement; no budget criterion)",
"laptop")` at the **end** of `GATES` in `scripts/update_status.py` (one appended line, so that prompts/20's `H0_model`
row cannot conflict; if the file is already modified in the working tree by the other executor, leave it and hand the
row back instead); `python scripts/update_status.py`.  Do **not** edit the CLAUDE.md status paragraph (the scribe
does it once prompts/20 and this prompt have both landed).  LOG rows; commits: "prompts/22 part A: fast UCR transform
above 10 controls, term_structure, S2/S2_fixed reproduced", "prompts/22 parts D–E: sparse simulator and coherence
module with regressions", "gate S2_2x4: <status> (2x4 all-to-all <n_2q> CZ, T2/t_2q <value>)".  Push per the owner's
rule.  Build on the current HEAD; if prompts/20 lands first, rebase — the only shared files are `scripts/update_status.py`
(append) and `.gitignore` (append).

## Pass criteria (gate S2_2x4; all machine-checked in `validation/S2_2x4.json`)
- C1 E3 link: |dt − dt_E3| <= 1e-12 for 2B = 0 and 2; dims 12843 / 8934; 11 + 4 references.
- C2 exact term circuits (13 hop/plaq terms, theta = dt, 2dt, 4dt): max |circuit − exp(−i theta h)| on the local
  codeword space < 1e-10 (planner: <= 4.1e-14).
- C3 leakage of every term circuit, exact and fixed, every theta: < 1e-12 (planner: <= 3.2e-13).
- C4 sparse simulator: 2x2 (20 circuits) and 2x3 (2 circuits) vs `run_ir` < 1e-13; the 2^28 `hop1` dense cross-check
  < 1e-13 (or FAIL with the memory reason recorded).
- C5 the four 2x4 coarse-step circuits vs `coarse_states`: max |delta| on the codewords < 1e-10, leakage < 1e-12.
- C6 leakage of the level-3 all-to-all transpiled k = 1 B = 0 circuit (sparse statevector) < 1e-9.
- C7 the frozen canary on the real record: T_s, S_T1, S_T2 equal to `data/S2_duration_compare.json` to 1e-9 relative.
- C8 `serial_bound` on the committed counts reproduces 667.1, 1727.6, 9372.1, 23786.3, 7035.6 to 0.1.
- C9 `validation/S2.json` and `S2_fixed.json` counts reproduced identically after the `circuits_ir.py` change (A3).
- C10 `pytest -q tests` all pass.
- Status PASS iff C1–C10.  No criterion on any count, duration or requirement value.  `block_rounds_fallback` true for
  any term is **not** a failure but must be printed in the report's verification section (planner expectation: false
  for all 13 terms).

## Outputs
`src/skqd/circuits_ir.py` (A1–A2, additive), `src/skqd/sparse_sim.py`, `src/skqd/coherence.py`,
`scripts/gate_S2_2x4.py`, `tests/test_sparse_sim.py`, `tests/test_coherence.py`, additions to
`tests/test_circuits_ir.py` (A1 test; a 2x4 term test on hop1/hop9/plaq0 in the default run, plaq1 marked `slow`),
`data/S2_2x4/*.json` (stage fragments, committed), `data/S2_2x4/cache/` (gitignored), `validation/S2_2x4.json`,
`reports/S2_2x4_compilation_and_device_requirement.md`, `.gitignore` (+1 line), `scripts/update_status.py` (+1 row),
`prompts/LOG.md` rows (executor's), `validation/gates.md` / `reports/PROJECT_STATUS.md` regenerated.  Optional:
`data/S2_2x4/circuit_2x4_B0_ref0_k1_all_to_all.qpy.gz` if under 5 MB.  Push: yes on PASS per the owner's rule.

## Time and memory budget per command (this laptop, measured by the planner where stated)
| command | expected | limit | memory |
|---|---|---|---|
| A3 S2 / S2_fixed reproduction (`--quick`) | 3 + 3 min | 30 min | < 2 GB |
| B1 refs, B2 structure | 1 + 2 min | 30 min | < 2 GB |
| B3 synth, 12 terms exact (3 theta) | about 4 min (P5) | 30 min | < 1 GB |
| B3 synth, plaq1 exact (3 theta) | about 17 min (P5: 152 + 172 s per theta) | 30 min (**one command**) | < 1 GB |
| B3 synth, all terms fixed | about 4 min | 30 min | < 1 GB |
| B4 compile (4 circuits x 4 maps + per-term + 2x2/2x3 rows) | about 10 min (P6 scales linearly) | 30 min | < 4 GB |
| B5 schedule (2x4 circuits have about 3e5 instructions) | about 10 min | 30 min | < 2 GB |
| B6 circuits: sparse x 4 + compiled + hop1 dense 2^28 | 4 x 3 min + 5 min + 4 min (D2/P4 estimates) | 30 min (split per circuit if needed) | 17 GB peak (hop1 dense) |
| D3 dense 2x3 regressions | 2 x 40 s | — | < 1 GB |
| pytest default | < 8 min | — | — |
If any command exceeds 30 min: stop it, split it (per term, per theta, per circuit — the stages are built for that),
record the split in the LOG, and never reduce a tolerance or a vector count to make it fit.  Perlmutter is the fallback
for a full dense 28-qubit statevector only (F); nothing else in this prompt needs it.

## Honest limits (to be stated in the report verbatim, with the numbers from the JSON)
- The gate says what the 2x4 circuits cost and what coherence they need; it does not say whether any device meets it.
- The requirement is a PTA bound on a uniform record (`skqd.idle` is a bound, prompts/20 M-A), quoted as a ratio
  T2/t_2q; the T2 convention (Hahn-echo vs in-circuit T2*) is the vendor's to declare (amendment 01 item 2), and a real
  device is a per-qubit sum, for which the coherence-scale number on the FakeFez record is the like-for-like reading.
- The fixed-angle rows are a cost floor: that generator's recall is established at 2x3 only.
- The 6-round packing and the two compilation levers of P5 are measured or named, not spent.
- The 2x4 hardware run is "optional" in the manual (Step 10 row 5); nothing here changes the hardware programme.

## Escalation
- Any term with deviation >= 1e-10, or an assertion inside `_block_rounds` / `_multiplexed_two_level`, or a
  `NotImplementedError`: stop; write `validation/BLOCKED.md` with the term, its P1 row, `real_gauge_found`,
  `block_rounds_fallback`, the block-size histogram and the traceback verbatim.  Do not switch that term to a dense
  unitary or to the fixed-angle mode to get past it; the planner returns at max.  (A `block_rounds_fallback == True`
  with deviation < 1e-10 is a finding to report, not a block.)
- B2 differs from P1/P2 in any support width, block size or disjoint count: stop and report (the model or the codec
  changed under this prompt).
- C4 fails at 2x2 or 2x3: the simulator is wrong, not the circuits — fix and re-run; two honest attempts, then BLOCKED.md.
- C5 fails while C2–C4 pass: a wiring/order/angle problem in `CircuitFactory.coarse_step` at 2x4 (support indices,
  term order, diag gates for interior vertices); report which term's removal makes the residual vanish (bisect by
  truncating the gate list at term boundaries) and stop.
- C7 or C8 fails: the coherence module is wrong; fix — the committed numbers are the record.
- C9 fails: the A1 switch is wrong (the fast path leaked below 11 controls) — fix before anything else.
- Two honest failures on the same step: stop and hand back with the traceback verbatim.

## Do-not-touch list (prompts/20 runs in parallel; binding)
`src/skqd/skqd.py`, `src/skqd/idle.py` (import only), `scripts/gate_H0P.py`, `scripts/gate_H0.py`,
`scripts/gate_H0_diag.py`, `scripts/h0_*.py`, `scripts/gate_S2D*.py` (import only), `data/hardware/`, `data/H0_*`,
every existing `validation/*.json`, `proposal/`, `prompts/LOG.md` for the planner's row (the executor appends its own
rows only), CLAUDE.md's status paragraph.  New files and `src/skqd/circuits_ir.py` are this prompt's territory; the
`circuits_ir.py` change is additive and leaves the 2x2 and 2x3 paths bit for bit unchanged (C9).

# 25 — 2x3 and 2x4: the ibm_kingston readiness check (gate K0_2x3_2x4) and the IonQ preparation (gates I0P_2x3, I0P_2x4)
executor: executor-opus   effort: high
time budget: 2 working days of executor time, no single command above 30 min   machine: laptop (0 QPU seconds on every provider; no push)

Planner analysis behind this prompt: `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md`
(every vendor number with its URL and read date; every repository number with its path).  Read it
first; this prompt tells you what to build, the report tells you why the answer is already known.

## Goal

The owner asked (2026-10-02): "check 2x3 is ready to run on ibm kingston machine using the techniques we
used for 2x2 case, if not prepare it for ionq devices and let me know, i will try to get access to ionq
qpus. same for 2x4."

The planner's arithmetic (report section 2) says 2x3 and 2x4 are **not** ready on kingston and cannot be
made ready by any 2x2 technique: with 5477 routed CZ (2x3) the clean-shot fraction is bounded by
$(1-\epsilon_{2,\min})^{5477} = 1.14\times10^{-2} < 0.05$ even if every CZ sat on the record's best edge
and nothing else went wrong; for 2x4 (148,726 routed CZ) the bound is $10^{-53}$.  Dynamical
decoupling, ALAP scheduling and patch selection act on the idle term only, which this bound already sets
to zero.  Part A makes that computation a gate on the day's record so the verdict is a JSON, not prose.

Part B prepares the IonQ path, knowing (report section 4) that 2x3 and 2x4 are infeasible on every IonQ
device that exists today (2x3: gate-only $f = 8.6\times10^{-5}$ on the Forte spec, $10^{-5}$–$10^{-7}$ on
the day-measured DRB values; 2x4: $f < 10^{-130}$).  What the preparation buys: the circuit families in
IonQ native gates, exactly verified; a submission path with dry run, preflight, preregistration and key
hygiene mirroring the IBM one; a requirement table per device and a cost/shot table the owner can hand to
IonQ; and a validation gate per lattice that says, with numbers, what a given device would deliver.

## Inputs (read these before writing code; use graphify first)

- `graphify-out/graph.json` exists: orient with `graphify query "<question>"`, `graphify explain "<symbol>"`,
  `graphify path "A" "B"`, `graphify affected "<symbol>"` before grepping or reading whole files; after
  changing code run `graphify update .` (seconds, no API cost).  Start with
  `graphify explain "analyse_on_backend"`, `graphify explain "clean_shot_fraction"`,
  `graphify explain "run_sparse_qiskit"`, `graphify explain "preflight"`, `graphify explain "verify_term"`.
- Planner report: `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md`.
- Kingston record of the H0_2x2 day: `data/hardware/H0_ddtest_prep/ibm_kingston_full_20261002T1906Z.json`
  (fingerprint `e4ecac38...`); the record reader `scripts/h0_backends.py` (`fresh_calibration`,
  `calibration_record`, `calibration_fingerprint`).
- 2x3 circuits and counts: `scripts/gate_S2D.py` (`circuit_set(3)`, `analyse_rzz`, `analyse_on_backend`),
  `data/S2D_2x3_device_requirements.json`, `validation/S2.json`, `data/S2_2x4/circuits_3_exact.json`.
- 2x4 circuits: `scripts/gate_S2_2x4.py` (`term_ir`, `verify_term`, `coarse_step_ir`, `transpile_ir`,
  `stage_compile`, `stage_probe`), `data/S2_2x4/` fragments, `validation/S2_2x4.json`.
- Clean-shot algebra: `src/skqd/device_req.py`; idle budget: `src/skqd/idle.py` (`schedule_asap`,
  `idle_budget`, `f_idle_aware`), the ALAP scheduling used for the 2x2 circuits in
  `scripts/h0_ddtest_circuits.py` / `scripts/h0_2x2_circuits.py`.
- The DD gain measured at 2x2: `validation/H0_ddtest.json data.decision.cells.T3` ($R = 2.8191$,
  95 % [2.4951, 3.1852]) and the DD ceiling `validation/S2D_levers.json data.dd_ceiling`.
- Submission path to mirror: `scripts/h0_submit.py` (phases, session.json, counts files as raw data),
  `scripts/ibm_account.py` (key handling: token file / env / hidden prompt / stdin, never argv),
  `scripts/h0_qpu_time.py`, `scripts/h0_support_plan.py` (D3' rule), `scripts/gate_H0_2x2.py`
  (`stage_plan`, `stage_predict`, `stage_prereg_md`, `stage_assemble`).
- Shot-rule evidence for 2x3: `data/S2D_recall_at_f.json results.*.shot_rule_union_reading_N_sector`.
- Existing IonQ feasibility script: `scripts/ionq_2x3_feasibility.py` -> `data/ionq_2x3_feasibility_20261001.json`
  (keep it; the new device table supersedes it and must reproduce its 2x3 rows to 1e-12).
- Package pins: the `coding` env (qiskit 2.5.2, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.49.0, numpy 2.5.2,
  scipy 1.18.0, Python 3.12.14) must not change.

## Conventions that must not change (CLAUDE.md rule 2)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py` (qubit $k$ = bit $k$, little-endian).
IonQ's results are also keyed by little-endian integers ("integer keys (little-endian bitstrings)",
https://docs.ionq.com/guides/direct-api-submission) — verify, do not assume (step B3).  The signed term
family, the signed budget (mean $f \ge 0.1$, worst $\ge 0.05$), $\lambda^* = 6.2958$, the D3' rule
(margin 0.7, floor 267, round to 100) are unchanged.  No tolerance of any existing gate changes.

## Steps

### Part A — gate K0_2x3_2x4: the kingston verdict on the day's record (about 3 h; 0 QPU s)

Script `scripts/gate_K0_2x3_2x4.py`, output `validation/K0_2x3_2x4.json` + `reports/K0_2x3_2x4.md`
(generated by `skqd.report.GateResult`; never a typed number).

A1. Record.  Default input: the committed record `data/hardware/H0_ddtest_prep/ibm_kingston_full_20261002T1906Z.json`.
    With `--live` (optional, metadata only, 0 QPU s) also fetch today's record through
    `h0_backends.fresh_calibration("ibm_kingston")`, save it under `data/hardware/K0_prep/`, and compute
    every quantity below on both; the gate's verdict uses the committed record and reports the live one
    beside it.  Record both fingerprints.

A2. Device statistics from the record: over the edges with `cz_error < 1`: minimum, 10th percentile,
    median, mean of `cz_error`; count of edges carrying the uncalibrated marker 1.0; over the qubits:
    medians of `sx_error`, `measure_error`, `T1_s`, `T2_s`; the set of `cz_duration_s` values.
    Expected on the committed record (planner arithmetic, report section 2.2): min $8.164\times10^{-4}$,
    p10 $1.146\times10^{-3}$, median $1.804\times10^{-3}$, 342 calibrated edges, 10 uncalibrated.

A3. Routed 2x3 circuit on the live-shaped target.  Build the 2x3 B = 0 ref0 k = 1 coarse-step circuit from
    `gate_S2D.circuit_set(3)` (or `data/S2_2x4/circuits_3_exact.json`), transpile it onto the kingston
    target (`resolve_backend`, `optimization_level=3`, `seed_transpiler` in 0..7; the record's basis
    `{rz, sx, x, cz}`; route on the live coupling map excluding the 10 uncalibrated edges), keep the seed
    with the fewest CZ.  Record per seed: CZ count, one-qubit count, depth, the physical qubits used.
    Reproduction check: the all-to-all CZ count of the same IR must be 2164 (`validation/S2.json`).

A4. The three f's of the routed 2x3 circuit, each with its formula in the JSON:
    - `f_ceiling_2q`: $(1-\epsilon_{2,\min})^{n_{\rm CZ}}$ with the record's best edge and the seed's CZ count
      (the bound no technique can beat);
    - `f_gates_layout`: `gate_S2D.analyse_on_backend(tq, backend)` on the transpiler's own layout
      (per-edge CZ error, per-qubit sx/x and readout error of the record);
    - `f_gates_best_patch_bound`: $(1-\epsilon_{2,\min})^{n_{\rm CZ}}(1-\epsilon_{1,\min})^{n_{1q}}(1-\epsilon_{ro,\min})^{20}$
      (every gate on the best element of the record: an upper bound on any patch selection).
    Then the idle term: schedule the routed circuit ALAP with explicit delays exactly as
    `scripts/h0_2x2_circuits.py` does for the 2x2 family, compute `skqd.idle.idle_budget` with the
    record's $T_1$, $T_2$ on the layout's qubits (echo convention, ratio 1, and the transferred ratio
    0.174 of prompts/21), and report `f_idle_aware = f_gates_layout * exp(-S_idle)`, then
    `f_idle_aware_xy4 = min(f_gates_layout, f_idle_aware * R)` with $R = 2.8191$ and its 95 % interval
    from `validation/H0_ddtest.json` (the 2x2-measured XY4 gain applied as a multiplicative factor on
    the idle part, capped by the gate-only value: the DD ceiling).  Label it as a transfer from 2x2, not
    a 2x3 measurement.

A5. 2x4: the same four numbers with the committed FakeFez-routed count 148,726 and the all-to-all count
    69,688 (`validation/S2_2x4.json`), ceilings only (do not re-route a 2x4 circuit on the laptop; the
    2x4 transpile is recorded in `validation/S2_2x4.json data.compile_4_exact_routed_k1`).

A6. Signed-bar verdict fields: for 2x3 and 2x4, `meets_mean_0.1` and `meets_worst_0.05` for each f, and
    `eps2_needed_for_f_0.05_nothing_else_wrong = -ln(0.05)/n_CZ` and the factor by which the record's
    best edge misses it.  Expected (planner): 2x3 $5.47\times10^{-4}$, factor 1.49; 2x4 (148,726)
    $2.01\times10^{-5}$, factor 40.6.

Pass criteria of K0 (status PASS iff all hold; **the verdict fields carry no criterion — they are the
result**):
- K0.1 the all-to-all 2x3 CZ count reproduces 2164 (`validation/S2.json`) exactly;
- K0.2 the record statistics of A2 reproduce the planner's values on the committed record to 1e-12
  (min, p10, median of cz_error; counts 342 / 10);
- K0.3 `f_ceiling_2q` equals $(1-\epsilon_{2,\min})^{n_{\rm CZ}}$ recomputed from the JSON's own fields
  to 1e-12, and `f_gates_layout <= f_gates_best_patch_bound <= f_ceiling_2q`;
- K0.4 the ALAP schedule moves no non-delay operation and its duration equals
  `h0_qpu_time.circuit_duration_s` to 1e-12 (the C7 check of gate S2D_levers);
- K0.5 `f_idle_aware_xy4 <= f_gates_layout` (the cap is applied);
- K0.6 `pytest -q tests` and `python scripts/check_package.py` pass (add `tests/test_k0_kingston.py`:
  the ceiling formula, the ordering of the three f's, the cap, on a synthetic 3-edge record).

Expected verdict (information, planner): 2x3 `f_ceiling_2q` about $1.1\times10^{-2}$ at 5477 CZ
(somewhat different at your seed's count), `f_gates_layout` about $10^{-5}$–$10^{-4}$; 2x4 ceilings
$10^{-53}$ / $10^{-25}$.  If `f_ceiling_2q >= 0.05` for 2x3 on the day's record, STOP and report: the
record would have changed qualitatively (best edge below $5.5\times10^{-4}$) and the planner must look.

### Part B — IonQ preparation (gates I0P_2x3 and I0P_2x4; about 1.5 days; 0 QPU s; no IonQ key exists yet)

B0. Software stack (30 min).  Run, in the `coding` env, `pip install --dry-run qiskit-ionq==1.1.1` and
    record its output in `data/ionq/stack_check_20261002.json` (packages it would add/change).  The
    planner read the wheel metadata (report section 6): qiskit-ionq 1.1.1 needs `qiskit>=2.0.0`,
    decorator, requests, importlib-metadata, python-dotenv — nothing pinned.  Install it **only** if the
    dry run changes none of qiskit, qiskit-aer, qiskit-ibm-runtime, numpy, scipy; otherwise do not
    install it and note that an isolated env `su2qc-ionq` would be needed.  Do not install
    amazon-braket-sdk or qiskit-braket-provider in `coding` (the Braket SDK pins `cloudpickle==2.2.1`).
    Nothing in Parts B1–B8 may depend on qiskit-ionq: it is a cross-check only (B2).

B1. Native-gate conversion, `src/skqd/ionq_native.py` (3 h).  Implement the IonQ native gates with the
    documented matrices (parameters in **turns**; https://docs.ionq.com/guides/getting-started-with-native-gates,
    read 2026-10-02; the report quotes them):
    $\mathrm{GPi}(\phi) = \begin{pmatrix} 0 & e^{-2\pi i\phi}\\ e^{2\pi i\phi} & 0\end{pmatrix}$,
    $\mathrm{GPi2}(\phi) = \tfrac{1}{\sqrt2}\begin{pmatrix} 1 & -ie^{-2\pi i\phi}\\ -ie^{2\pi i\phi} & 1\end{pmatrix}$,
    $\mathrm{ZZ}(\theta) = \exp(-i\pi\theta\,Z\otimes Z)$.
    Conversion from the `{rz, sx, x, rzz}` basis (transpile the IR with `basis_gates=["rz","sx","x","rzz"]`,
    `coupling_map=None`, `optimization_level=3`, fixed `seed_transpiler`; the RZZ count must reproduce
    2158 for 2x3, `data/S2D_2x3_device_requirements.json counts.coarse_step.rzz`): keep a frame phase
    $\lambda_q$ per qubit (radians, starts at 0); `rz(\alpha)` on $q$: $\lambda_q \mathrel{+}= \alpha$, emit nothing;
    `sx` on $q$: emit $\mathrm{GPi2}(\phi)$ with $\phi = -\lambda_q/2\pi$ (derive the sign by the identity
    $R_z(\lambda)\,\mathrm{GPi2}(0)\,R_z(-\lambda) = \mathrm{GPi2}(\lambda/2\pi)$ up to global phase — check it
    numerically in the unit test and fix the sign from the test, never from memory); `x`: $\mathrm{GPi}(\phi)$ the
    same way; `rzz(\varphi)`: $\mathrm{ZZ}(\varphi/2\pi)$ (commutes with the frames); measurement in $Z$ is
    unaffected by the frames.  Emit (i) an IR list our simulators run (`run_ir` / `sparse_sim.apply_ir`:
    add `gpi`, `gpi2`, `zz` as 1q/2q unitaries — `SparseState.mix` and a diagonal `zz` via two `rz`-like
    phase maps, or `cphase`-style), (ii) the `ionq.circuit.v1` JSON (`{"gate":"gpi","target":q,"phase":phi}`,
    `{"gate":"gpi2",...}`, `{"gate":"zz","targets":[a,b],"angle":theta}` — confirm the field names
    against https://docs.ionq.com/api-reference/v0.4/jobs/create-job and the native-gates page; if a
    field name is uncertain, record both candidates in the manifest and let B6 settle it), and (iii) a
    qiskit circuit of the same gates for QPY.  Count native gates per circuit.

B2. Exactness, 2x3 (1 h run).  For all 44 production circuits of `circuit_set(3)` (B = 0: 32, B = 1: 12;
    references x k = 1..4): dense statevector of the native IR (20 qubits, $2^{20}$ complex128 = 16 MB)
    vs `circuits_qiskit.statevector` of the pre-conversion circuit, max $|\Delta|$ after removing the global
    phase; leakage out of the codeword space.  If qiskit-ionq was installed in B0, also transpile one
    circuit with `transpile(qc, backend=IonQProvider(token="dummy").get_backend("simulator", gateset="native"))`
    (no network is needed to build the backend; if it needs one, skip and say so) and compare its
    statevector to ours — information only.

B3. Endianness and JSON round trip (1 h).  Parse the emitted `ionq.circuit.v1` JSON back into the IR with
    an independent reader and simulate: identical statevector to 1e-12.  Then a fixed asymmetric circuit
    (X on qubit 0 only, 3 qubits) through the same JSON path: the integer key our decoder expects is 1
    (little-endian, `reference_sim.qiskit_key_to_bits`); record in the manifest the convention assumed
    for IonQ's result keys and the sentence of the IonQ documentation it rests on; the live check of the
    convention is a preflight item of B7 (an all-zeros / single-X calibration pub, as the 2x2 run's
    `cal_patch_all0/all1`).

B4. Exactness, 2x4 (laptop, cap 600 s per circuit; 2 h).  Per-term verification first: convert each of
    the 13 term circuits (`gate_S2_2x4.term_ir(4, name, "exact", theta)` for theta = dt, 2dt, 4dt) and
    verify on the local codeword space with the C2 method of gate S2_2x4 (`verify_term`: random
    codeword vectors, max deviation from $\exp(-i\theta h)$ < 1e-10, leakage < 1e-12).  Then the coarse-step
    circuit B0_ref0_k1 through `sparse_sim.run_sparse` with the 600 s cap: if it completes, compare with
    `krylov.coarse_states` on the codewords (< 1e-10); if it does not (the all-to-all 2x4 circuit did
    not complete on the laptop: `validation/S2_2x4.json
    data.compiled_probe.probe_4_exact.circuits["B0_ref0_k1|all_to_all"]`, `completed: false` after 711 s;
    the committed C6 came from the Perlmutter GPU job 59162991, `data.gpu.gpu_4_GPU`), record `completed: false`, the support growth reached, and name the GPU
    path.  **Do not request a CI token for it**: `S2_2x4` is not in the allowlist of CLAUDE.md's skqd-ci
    section and a new token is an owner decision (report section 7, D3).  Native gate count of the 2x4
    coarse step (expected about 208,400) against the API's "150,000 total gates" limit: a verdict field.

B5. Device table, `scripts/ionq_device_table.py` -> `data/ionq/devices_20261002.json` (2 h).  Encode the
    specs **verbatim with URL and read date** exactly as the planner report section 3 lists them (Forte,
    Forte Enterprise, their day-measured DRB values from arXiv:2506.07866v2 Sec. IV.1, Aria marked
    retired, Tempo marked targets), the gate times 950 / 130 $\mu$s with their source, the API limits, the
    three price lists.  For each device row and each lattice (2x2, 2x3, 2x4, plus the two unsigned 2x3
    levers and the 2x4 fixed family, marked unsigned): gate-only f (virtual and physical rz), the
    $\epsilon_2$ for mean $f = 0.1$ at that row's $\epsilon_1, \epsilon_{ro}$, the serial-duration and idle
    ESTIMATE with the assumption string, the qubit fit, the API-limit fit, the per-shot cost on Azure
    and Braket, the D3-type shot count (2x3: `data/S2D_recall_at_f.json` scaled as $1/f$ from the
    0.0534 row; 2x2: `validation/H0_2x2.json data.shot_plan.total_coarse_shots` scaled from 0.1129;
    2x4: "not computable" when $f < 10^{-12}$), the dollar cost and the wall-time ESTIMATE.  Reproduce
    `data/ionq_2x3_feasibility_20261001.json results.2x3|ionq_forte|*` and `scenario_eps2_for_2x3` to
    1e-12 (same function, same counts).  Expected (planner, report 4.2): 2x3 Forte spec vrz
    $8.608\times10^{-5}$, Tempo targets $7.70\times10^{-2}$; 2x4 Forte spec $3.9\times10^{-134}$.

B6. Local noisy dry run, 2x3 only (about 25 min of compute; 0 QPU s).  Build an Aer noise model from the
    Forte spec row (depolarizing 2q at $\epsilon_2 = 0.004$ on `zz`/`rzz`, 1q at $2\times10^{-4}$ on
    `gpi`/`gpi2` (or on `sx`/`x` of the pre-conversion circuit if Aer cannot take custom gates: say which),
    readout flips at 0.005, thermal relaxation on explicit delays with $T_1 = 10$ s, $T_2 = 1$ s and the
    950 / 130 $\mu$s durations under serial scheduling — the ESTIMATE of the report, labelled as such).
    Run the 2 k = 1 circuits B0_ref0_k1, B1_ref0_k1 at 200 shots each (the S3 laptop calibration is
    about 3.2 s per noisy 2x3 shot; stop at 25 min and reduce shots if needed) through the same
    `clean_statistics` / `pooled_reference_string_test` path the IBM gates use; report $f$ with its
    Garwood interval.  This is a path check: with $f \sim 10^{-4}$ and 400 shots the expected clean count
    is 0.03, so the interval must contain 0 and must be reported as "consistent with the prediction
    $8.6\times10^{-5}$", nothing more.  For 2x4: **no noisy run** (28 qubits x $2\times10^{5}$ gates; and
    $f = 0$ to every precision); write the reason into the gate JSON.
    If an IonQ API key exists by then (it does not today): the cloud simulator with
    `"noise": {"model": "forte-enterprise-1"}` and `"dry_run": true` on the QPU target are the two
    no-spend checks to add — but only after the owner confirms the account's simulator is free of charge
    for that job (`GET /v0.4/jobs/estimate` first).  Never submit to `qpu.*` under this prompt.

B7. Submission path (4 h), `scripts/ionq_account.py` and `scripts/ionq_submit.py`, mirroring
    `scripts/ibm_account.py` / `scripts/h0_submit.py`:
    - key: read from `--token-file`, `$IONQ_API_KEY`, a hidden prompt, or piped stdin; **never** from argv;
      never printed; stored only in a mode-600 file under `~/.ionq/` if the owner asks (`--save`), with
      the same diagnostics style; `--check` calls `GET /v0.4/backends` and
      `GET /v0.4/backends/{backend}/characterizations` (metadata, free) and writes the characterization
      (qubits, connectivity, fidelity medians, timing t1/t2/1q/2q/readout/reset) to
      `data/hardware/ionq_<backend>_<stamp>.json` with a sha256 fingerprint over the leaves the prediction
      reads — the D9 analogue;
    - `--dry-run` builds every job body (`type`, `backend`, `shots`, `name`, `metadata` with git commit
      and circuit id, `input.qubits`, `input.gateset: "native"`, `input.circuit`,
      `settings.error_mitigation.debiasing: false`), writes them to `<out>/session.json` with
      `job_id: null`, runs the circuits on the local Aer path of B6 (few shots) and writes counts files
      in the same raw-data format as `h0_submit.write_counts_for_job` (refuse to overwrite);
    - `--preflight` (needs a key; not run under this prompt): fingerprint identity with the preregistered
      characterization, `GET /v0.4/jobs/estimate` for every body, sum against a `--cap-usd`, backend
      status, and the two calibration pubs (all-zeros, single X on qubit 0) in the plan;
    - `--submit` requires a preregistration JSON committed before (K1-style), the preflight record, and
      refuses when any of them is missing; `--retrieve` polls `GET /v0.4/jobs/{id}` and
      `GET /v0.4/jobs/{id}/results/probabilities`, converts probabilities x shots to integer counts and
      records that the API returns probabilities, not raw counts (a limitation to flag to the owner:
      the counts are reconstructed, and the rounding must be recorded per key);
    - tests `tests/test_ionq_submit.py`: the parser has no key argument; a dry run leaves no key string
      in any written file or log; the session format fields; the little-endian decode of a probabilities
      dict.

B8. Preregistration and cost/shot table (2 h), `scripts/gate_I0P.py --lattice 3|4` with stages
    `predict`, `prereg-md`, `assemble`: the prediction per device row (f, shots by the D3' rule at
    $0.7 f$ with the 2x2 constants where $f$ is non-negligible, cost on Azure/Braket, wall-time ESTIMATE),
    `reports/I0P_<lattice>_prereg.md` generated from the JSON, and the gates:

Pass criteria of **I0P_2x3** (`validation/I0P_2x3.json`, PASS iff I1–I7; the device verdicts are
result fields, not criteria):
- I1 native conversion exact on all 44 circuits: max $|\Delta\psi| < 10^{-10}$ (global phase removed),
  leakage $< 10^{-9}$; RZZ count 2158 reproduced before conversion; ZZ count = RZZ count;
- I2 JSON round trip identical to 1e-12; endianness test circuit decodes to key 1;
- I3 device table reproduces `data/ionq_2x3_feasibility_20261001.json` 2x3 Forte rows and the scenario
  rows to 1e-12; every spec entry carries `source`, `read_on`, `verbatim`;
- I4 dry run of `ionq_submit.py --dry-run` writes session.json + counts for the 2 circuits + 2 calibration
  pubs; no key string in any output (test); `settings.error_mitigation.debiasing` is `false` and
  `input.gateset` is `"native"` in every body;
- I5 the local noisy path check of B6 ran and its $f$ interval is reported with the shots used;
- I6 the preregistration JSON has every field the `assemble` stage reads (K7-style completeness check,
  recomputed verdicts equal stored ones);
- I7 `pytest -q tests` and `check_package.py` pass.

Pass criteria of **I0P_2x4** (`validation/I0P_2x4.json`, PASS iff J1–J5):
- J1 per-term native conversion exact on the local codeword space for all 13 terms x 3 thetas
  ($< 10^{-10}$, leakage $< 10^{-12}$);
- J2 the coarse-step sparse check either completes ($< 10^{-10}$ vs `krylov.coarse_states`) or records
  `completed: false` with the support reached and the cap — both are PASS for this gate; what is not
  allowed is silence;
- J3 native gate count recorded and compared with the API limit (verdict field `fits_api_gate_limit`);
- J4 device table rows for 2x4 present with f, qubit fit, API fit, "shots not computable" where
  $f < 10^{-12}$;
- J5 pytest + check_package.

`what_pass_means` of both gates, verbatim: "compiled, verified, costed and packaged; PASS is NOT a
statement that any IonQ device can run these circuits — the verdict fields say what a device would
deliver, and today every one of them says NO-GO for 2x3 and 2x4".

## QPU seconds and money

0 on IBM, 0 on IonQ, 0 on Braket/Azure.  No key exists; nothing in this prompt obtains one.  If a key
appears during the work, the only permitted calls are `GET /backends*`, `GET /jobs/estimate` and
`POST /jobs` with `"dry_run": true` or `"backend": "simulator"` after the owner confirms it is free.

## Outputs

- `validation/K0_2x3_2x4.json`, `reports/K0_2x3_2x4.md`, `data/hardware/K0_prep/` (if `--live`);
- `src/skqd/ionq_native.py`, `scripts/ionq_device_table.py`, `scripts/ionq_account.py`,
  `scripts/ionq_submit.py`, `scripts/gate_I0P.py`, `scripts/gate_K0_2x3_2x4.py`;
- `data/ionq/devices_20261002.json`, `data/ionq/stack_check_20261002.json`,
  `data/ionq/circuits_2x3/` (44 manifests + `ionq.circuit.v1` JSON + QPY, gzip), `data/ionq/circuits_2x4/`
  (13 term circuits x 3 thetas + the coarse step), `data/hardware/I0P_2x3_dryrun/` (session + counts);
- `validation/I0P_2x3.json`, `validation/I0P_2x4.json`, `reports/I0P_2x3.md`, `reports/I0P_2x4.md`,
  `reports/I0P_3_prereg.md`, `reports/I0P_4_prereg.md`;
- tests: `tests/test_k0_kingston.py`, `tests/test_ionq_native.py`, `tests/test_ionq_submit.py`,
  `tests/test_ionq_device_table.py`;
- `validation/gates.md`: rows for K0_2x3_2x4, I0P_2x3, I0P_2x4; `reports/PROJECT_STATUS.md`: one
  paragraph; `graphify update .` after the code changes;
- git: commit after each gate (`git commit <paths>`; retry if `.git/index.lock` exists); **no push**
  (owner's call, as for the whole 2026-10-02 day).

## Escalation and STOP conditions

- STOP (binding) if K0's `f_ceiling_2q` for 2x3 is $\ge 0.05$ on the committed record: the planner's
  arithmetic would be wrong or the record changed qualitatively; write `validation/BLOCKED.md`.
- STOP if the native conversion cannot reach $10^{-10}$ after two honest attempts (most likely a sign or
  turns-vs-radians convention): write the residual, the gate at which it first appears, and the two
  candidate conventions into BLOCKED.md; do not loosen I1.
- STOP if any step needs an IonQ key, a CI token not in the allowlist, a package change in `coding`, or
  a change to the signed family.
- Retry rule for the 2x4 sparse run: one attempt at the 600 s cap; a second only with `--nseg` style
  segmentation if `gate_S2_2x4.py` already supports it; otherwise record `completed: false`.
- After two failed attempts at any pass criterion: BLOCKED.md and stop; the planner returns.

## Do-not-touch list (binding)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py`, `device_req.py` (add nothing that
changes a value), every existing `validation/*.json`, every frozen circuit under `data/hardware/`,
the signed family, every criterion constant of every existing gate, `ci/`, `prompts/00`–`24`.
`scripts/ionq_2x3_feasibility.py` stays as it is (the new table must reproduce it).

## LOG row (append to `prompts/LOG.md`, one row per gate; the planner's own row is already there)

| date | prompts/25_2x3_2x4_kingston_check_and_ionq_prep.md Part A / Part B | K0_2x3_2x4 / I0P_2x3 / I0P_2x4 | executor-opus | PASS/FAIL with the verdict numbers from the JSON (2x3 and 2x4 f ceilings on the day's record; 2x3 and 2x4 gate-only f per IonQ device; native gate counts; API-limit fit; dry-run f interval; stack check result) | commit | open issues (owner decisions D1–D3 of the report section 7) |

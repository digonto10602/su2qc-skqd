# 26 — The signed 2x3 circuits for Quantinuum H2-2 / Helios-1 (gate Q0P_2x3): native compilation, exact verification, emulator and submission path, cost sheet
executor: executor-opus   effort: high
time budget: 2 working days of executor time for Stage A, no single command above 30 min; Stage E only after the owner has a Quantinuum Nexus login and has confirmed the emulator budget   machine: laptop (0 HQC, 0 QPU seconds on every provider under this prompt; no push)

Planner survey behind this prompt: `reports/qpu_survey_2x3_20261002.md` (every vendor number with its
URL and read date 2026-10-02; every repository number with its path; planner arithmetic in
`scratch/planner/quantinuum_2x3_prototype_20261002.json`).  Read it first.  Owner's request
(2026-10-02): "search internet to find which quantum device can run 2x3 and then build the circuits
for that device".

## Why Quantinuum, in one paragraph

The signed 2x3 coarse step is 2158 two-qubit RZZ gates on 20 qubits, all-to-all, with a two-qubit
critical path 1925 gates deep (`scratch/planner/quantinuum_2x3_prototype_20261002.json counts`).
Of every device accessible or announced with measured numbers, only Quantinuum's QCCD trapped-ion
machines meet the signed error bar (mean clean-shot fraction $f \ge 0.1$, worst $\ge 0.05$) on
published measured errors: H2-2 ($\epsilon_2 = 8.3\times10^{-4}$, $\epsilon_1 = 2.8\times10^{-5}$,
SPAM $0.67$-$1.2\times10^{-3}$, memory $1.2\times10^{-4}$ per depth-1 time) gives gate-only
$f = 0.150$ and Helios-1 ($7.9\times10^{-4}$, $3\times10^{-5}$, $4.8\times10^{-4}$, memory
$5\times10^{-4}$) gives $0.164$ (survey section 3).  The transport/memory term, estimated at 5-30 %
(H2-2) and 15-80 % (Helios) of that, is the decisive unknown and is measured by the vendor
emulators, which carry the real transport schedule.  Everything else fails by 2-13 orders of
magnitude (IBM Heron ceiling $1.1\times10^{-2}$, IonQ Forte $8.6\times10^{-5}$, Willow
$\le 4\times10^{-3}$ before routing, neutral atoms $\le 10^{-4}$).  Both Quantinuum generations share
the native gate set $\{R_z, \mathrm{PhasedX}, \mathrm{ZZPhase}\}$, so **one build serves H2-2 (primary),
Helios-1 (secondary) and H1-1 (fallback, 20 qubits exactly)**; only the submission wrapper differs
(Helios takes Guppy/HUGR programs).  The cost is the second obstacle: 4.97 HQC per shot, about
$5\times10^{5}$ HQC for the full D3-type campaign and about $10^{4}$ HQC for a two-circuit device
pilot (survey section 3); the realistic access route is a QCUP allocation or a research agreement
with Quantinuum, both of which require emulator evidence first.  This prompt produces that evidence
path and the frozen circuits; it submits nothing to hardware.

## Inputs (read these before writing code; use graphify first)

- `graphify-out/graph.json` exists: orient with `graphify query "<question>"`,
  `graphify explain "<symbol>"`, `graphify path "A" "B"`, `graphify affected "<symbol>"` before grepping
  or reading whole files; after changing code run `graphify update .` (seconds, no API cost).  Start
  with `graphify explain "scripts/gate_S2D.py"` (`circuit_set`, `analyse_rzz`), `graphify explain
  "clean_shot_fraction"`, `graphify explain "statevector"` (`src/skqd/circuits_qiskit.py`),
  `graphify explain "pooled_reference_string_test"`, `graphify explain "clean_statistics"`
  (`scripts/gate_H0P.py`), `graphify explain "n4_of_sector"` (`scripts/h0_support_plan.py`),
  `graphify explain "write_counts_for_job"` (`scripts/h0_submit.py`), `graphify explain "read_token"`
  (`scripts/ibm_account.py`).
- Survey: `reports/qpu_survey_2x3_20261002.md`; prototype: `scratch/planner/quantinuum_2x3_prototype_20261002.py`
  (the transpile settings that reproduce 2158 RZZ: `basis_gates=["rz","rx","ry","rzz"]`,
  `coupling_map=None`, `optimization_level=3`, `seed_transpiler=7`, exactly as `gate_S2D.main`).
- 2x3 circuits: `gate_S2D.circuit_set(3)` -> 44 tuples `(twoB, ref, k, gates_ir)`; counts
  `data/S2D_2x3_device_requirements.json`, `validation/S2.json`.
- Clean-shot algebra: `src/skqd/device_req.py`.  Clean statistics and the reference-string test used
  by every hardware gate: `gate_H0P.clean_statistics`, `skqd.skqd.pooled_reference_string_test`,
  `skqd.skqd.yield_model` (y = 0.82 f), `poisson_lambda_star` ($\lambda^* = 6.2958$).
- D3' shot rule: `scripts/h0_support_plan.py` (margin 0.7, floor 267, round to 100, `n4_of_sector`).
  Shot-rule evidence for 2x3: `data/S2D_recall_at_f.json results.*.shot_rule_union_reading_N_sector`.
- Submission path to mirror: `scripts/h0_submit.py` (phases, `session.json`, counts files as raw data,
  `write_counts_for_job`), `scripts/ibm_account.py` (credential hygiene), `scripts/gate_H0_2x2.py`
  (`stage_plan`, `stage_predict`, `stage_prereg_md`, `stage_assemble`, K7-style completeness check).
- prompts/25 Part B, if already built by the time you start (check `git log` and `prompts/LOG.md`):
  reuse `scripts/ionq_device_table.py`'s row format and `ionq_submit.py`'s session format so the two
  providers share one shape.  If prompts/25 Part B is not built, do not build it here.
- Package pins: the `coding` env (qiskit 2.5.2, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.49.0, numpy
  2.5.2, scipy 1.18.0, Python 3.12.14) must not change.

## Conventions that must not change (CLAUDE.md rule 2)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py` (qubit $k$ = bit $k$, little-endian).
The signed term family, the signed budget, $\lambda^*$, the D3' constants, every criterion constant
of every existing gate.  The 2x3 circuit family is frozen as **the compiled native circuit that passes
Q1**, byte-identical QASM under `data/quantinuum/circuits_2x3/`; any later change needs a new prompt.

Quantinuum / pytket conventions (https://docs.quantinuum.com/tket/api-docs/optype.html, read
2026-10-02; angles in **half-turns**, $1$ half-turn $= \pi$ rad):
$$ R_z(a) = e^{-i\pi a Z/2},\quad R_x(a) = e^{-i\pi a X/2},\quad \mathrm{PhasedX}(a,b) = R_z(b)\,R_x(a)\,R_z(-b),$$
$$ \mathrm{ZZPhase}(a) = e^{-i\pi a\,(Z\otimes Z)/2},\quad \mathrm{ZZMax} = e^{-i\pi (Z\otimes Z)/4}. $$
Our IR (`src/skqd/circuits_qiskit.ir_to_qiskit`, qiskit convention): $rz(\lambda) = e^{-i\lambda Z/2}$,
$rx(\theta) = e^{-i\theta X/2}$, $rzz(\varphi) = e^{-i\varphi (Z\otimes Z)/2}$.  Hence
$rz(\lambda) \to R_z(\lambda/\pi)$, $rx(\theta) \to R_x(\theta/\pi)$, $ry \to R_y(\theta/\pi)$,
$rzz(\varphi) \to \mathrm{ZZPhase}(\varphi/\pi)$; $\mathrm{PhasedX}(a,b)$ read back as the time-ordered
IR `rz(-pi b), rx(pi a), rz(pi b)` **if** the operator product above is read right-to-left — fix the
order by the unit test (A2), never from memory.  Rz is virtual on Quantinuum and is not billed
("Rz operations excluded", https://docs.quantinuum.com/systems/trainings/helios/getting_started/costing.html).
Billing: $\mathrm{HQC} = 5 + C\,(N_{1q} + 10\,N_{2q} + 5\,N_m)/5000$ per job, $N_{1q}$ = PhasedX count,
$N_{2q}$ = ZZPhase/ZZMax count, $N_m$ = initialisations + measurements (= 40 for our circuits), $C$ = shots
(https://learn.microsoft.com/en-us/azure/quantum/provider-quantinuum, same page for the limits
10,000 shots per job, 500,000 HQC per job).

## Interface (names the gate, the tests and later prompts call)

- `src/skqd/quantinuum_native.py`
  - `ir_to_pytket(gates: list, n: int, measure: bool = True) -> pytket.Circuit` (direct writer, no
    pytket-qiskit dependency; gates `rz, rx, ry, x, h, rzz`, `measure` to bit $k$ for qubit $k$).
  - `compile_native(circ, device_name: str = "H2-2", optimisation_level: int = 2) -> pytket.Circuit`
    using `pytket.extensions.quantinuum.QuantinuumBackend(device_name, api_handler=QuantinuumAPIOffline())
    .get_compiled_circuit(circ, optimisation_level)`; fallback (documented in the manifest if used):
    `AutoRebase({Rz, PhasedX, ZZPhase})` + `FullPeepholeOptimise`.  Must raise if the result contains
    any OpType outside `{Rz, PhasedX, ZZPhase, ZZMax, Measure, Barrier}` or a non-identity
    `implicit_qubit_permutation()`.
  - `pytket_to_ir(circ) -> tuple[list, int, dict]`: independent reader of `circ.get_commands()` into
    our IR (`Rz, Rx, Ry, PhasedX, ZZPhase, ZZMax, Measure`), returning also the qubit->bit map.
  - `native_counts(circ) -> dict(n_phasedx, n_rz, n_zz, n_meas, depth, depth_2q)`.
  - `hqc_per_shot(counts) -> float` and `hqc_job(counts, shots) -> float` (the formula above).
  - `to_qasm(circ) -> str` via `pytket.qasm.circuit_to_qasm_str(circ, header="hqslib1")`;
    `to_json(circ) -> dict` via `circ.to_dict()`; `from_json(d) -> pytket.Circuit`.
- `scripts/quantinuum_build_circuits.py` -> `data/quantinuum/circuits_2x3/<id>.{qasm,json,manifest.json}`
  (ids `B0_ref<r>_k<k>` / `B1_ref<r>_k<k>`, 44 in all) + `index.json`.
- `scripts/quantinuum_device_table.py` -> `data/quantinuum/devices_20261002.json`.
- `scripts/quantinuum_account.py` (`--login`, `--check`, `--logout`, `--status`).
- `scripts/quantinuum_submit.py` (`--dry-run`, `--syntax-check`, `--emulate`, `--preflight`,
  `--submit`, `--retrieve`, `--status`; `--device`, `--max-cost`, `--prereg`, `--only`, `--shots-plan`).
- `scripts/gate_Q0P_2x3.py --stage verify|predict|prereg-md|assemble-emulator` ->
  `validation/Q0P_2x3.json`, `reports/Q0P_2x3.md`, `reports/Q0P_2x3_prereg.md`.
- tests: `tests/test_quantinuum_native.py`, `tests/test_quantinuum_submit.py`,
  `tests/test_quantinuum_device_table.py`.

## Steps

### Stage A — build, verify, cost, package (laptop; 0 HQC; about 1.5 days)

A1. Stack (30 min).  In `coding`: `pip install --dry-run pytket pytket-quantinuum pytket-qiskit qnexus`
    and save the output to `data/quantinuum/stack_check_20261002.json`.  The planner's dry run on
    2026-10-02 showed only new packages (pytket 2.18.4, pytket-quantinuum 0.59.3, pytket-qir 2.0.2,
    pyqir 0.12.6, pytket-qiskit 0.78.0, symengine 0.14.1, qnexus 0.51.0, quantinuum-schemas 7.8.2,
    hugr 0.18.6, pandas 2.3.3, websockets, rich, ...) and **no change** to the five pinned packages
    (survey section 4).  Install **only** if your dry run agrees; record `pip freeze` of the five pins
    before and after.  Do **not** install guppylang / selene-sim (llvmlite, ziglang, wasmtime) unless
    step A9 is reached and the owner wants the Helios wrapper.  Nothing in A2-A8 may depend on
    pytket-qiskit (optional cross-check only).

A2. `src/skqd/quantinuum_native.py` (3 h) with unit tests on 1- and 2-qubit circuits: every
    conversion rule checked numerically against `pytket.Circuit.get_unitary()` and our
    `circuits_qiskit.statevector`, including the PhasedX order and the half-turn factor; a random
    6-qubit `{rz, rx, ry, rzz}` circuit round-trips IR -> pytket -> compile_native -> IR with
    statevector agreement $< 10^{-12}$ after removing the global phase.  Endianness: a 3-qubit
    circuit with X on qubit 0 only must give our key 1 (`reference_sim.qiskit_key_to_bits`) through
    `pytket_to_ir` and through the reader of a pytket `BackendResult`-style counts dict (bit tuples in
    cbit order `c[0], c[1], ...`; record the convention and the documentation sentence it rests on).

A3. Build the family (1 h run).  For the 44 circuits of `circuit_set(3)`: transpile to
    `{rz, rx, ry, rzz}` as the prototype did (RZZ count must be 2158 on every circuit:
    `data/S2D_2x3_device_requirements.json counts.coarse_step.rzz`), `ir_to_pytket`, `compile_native`
    at optimisation levels 0 and 2 for `device_name="H2-2"`; keep, per circuit, the level with the
    fewest ZZ gates among those that pass A4; record both counts.  Dense statevector of the compiled
    circuit via `pytket_to_ir` + `circuits_qiskit.statevector` (20 qubits, 16 MB complex128) against
    the statevector of the pre-conversion IR: max $|\Delta\psi|$ after global-phase removal, leakage
    out of the codeword space (`Codec`).  Write QASM (`hqslib1`), JSON and a manifest per circuit
    (id, sector, ref, k, dt, counts, `hqc_per_shot`, sha256 of the QASM, residuals, pytket and
    pytket-quantinuum versions, git commit).  Also compile the same 44 for `device_name="Helios-1"`
    and `"H1-1"` and record whether the circuits are byte-identical (expected: the gate set is the
    same; if the offline handler has no Helios entry, say so and keep the H2-2 circuits).

A4. Exactness and round trip: see the Q1-Q3 criteria.  JSON -> `from_json` -> `pytket_to_ir` ->
    statevector identical to $10^{-12}$; QASM -> `pytket.qasm.circuit_from_qasm_str` -> same.

A5. Device table, `scripts/quantinuum_device_table.py` -> `data/quantinuum/devices_20261002.json`
    (2 h).  Encode verbatim with `source`, `read_on`, `verbatim` the rows of survey section 2 for
    H2-2, H2-1, H1-1, Helios-1 (performance-validation page, data sheets, paper), the memory-error
    scenario model of survey section 3 (three per-round times, the per-second rates, flagged
    `ESTIMATE`), the HQC formula and limits, the Azure plans, the QCUP route; keep the IonQ rows by
    reading `data/ionq_2x3_feasibility_20261001.json` (do not retype them).  For each device and each
    lattice (2x2 from `validation/S2.json data.2x2.coarse_step.all_to_all.ops`, 2x3 from the manifests
    of A3, 2x4 from `validation/S2_2x4.json` as in prompts/25 B5): gate-only $f$, $f_{2q}$,
    $\epsilon_2$ for mean $f = 0.1$ and worst $0.05$, the memory scenarios, D3-type shots scaled as
    $1/f$ from `data/S2D_recall_at_f.json` (2x3) and `validation/H0_2x2.json data.shot_plan` (2x2),
    HQC and USD at 12.5 USD/HQC (labelled Azure-Standard-equivalent), machine time at the mid
    scenario, qubit fit, job-limit fit (10,000 shots/job -> number of jobs).  Must reproduce the
    prototype's `devices.quantinuum_*.f_gate_only` to $10^{-12}$ at the prototype's counts
    (H2-2 0.15020, Helios-1 0.16420, H1-1 0.11129, H2-1 0.08602 — read the exact values from the JSON)
    and the IonQ rows to $10^{-12}$.

A6. Local noisy dry run (about 25 min of compute).  Aer noise model from the H2-2 row: depolarizing
    $8.3\times10^{-4}$ on `rzz`, $2.8\times10^{-5}$ on `rx`/`ry` (physical 1q; `rz` noiseless), readout
    flips $6.7\times10^{-4}$ / $1.2\times10^{-3}$, **no memory term** (label: gate-only path check).
    Run B0 and B1 `k = 1` circuits at 200 shots each (the S3 laptop calibration is about 3.2 s per
    noisy 2x3 shot; stop at 25 min and reduce shots if needed), through `clean_statistics` /
    `pooled_reference_string_test` with the exact $p_{\rm ref}$ of each circuit from its statevector;
    report $f$ with its Garwood interval and state that it must be consistent with the gate-only
    prediction 0.150 (expected clean shots about 30 of 200 per circuit).

A7. Account and submission scripts (4 h).
    - `scripts/quantinuum_account.py`: `--login` calls `qnexus.login()` (browser) or
      `qnexus.login_with_credentials()` reading the password from a hidden prompt or piped stdin,
      **never argv**; nothing of the token is printed or copied (qnexus keeps its own token store;
      record its path in the report by reading qnexus' documentation/source, not by printing the
      token); `--check` lists `qnx.devices.get_all()` and writes `data/hardware/quantinuum_devices_<stamp>.json`
      with a sha256 fingerprint of the device list (the D9 analogue is limited: Quantinuum publishes no
      per-job calibration record; say so); `--logout` calls `qnexus.logout()`.
    - `scripts/quantinuum_submit.py`, mirroring `h0_submit.py`: `--dry-run` builds every job record
      (device, shots, `QuantinuumConfig` fields `noisy_simulation`, `no_opt=True`,
      `allow_implicit_swaps=False`, `attempt_batching`, `max_cost`, `user_group`), writes
      `<out>/session.json` with `job_id: null`, runs the circuits on the A6 Aer path (few shots) and
      writes counts files in the `write_counts_for_job` raw format (refuse to overwrite);
      `--syntax-check` submits to `H2-2SC` (free; needs a login; not run under this prompt);
      `--emulate` submits to `H2-2E` (or `Helios-1E`) with `max_cost` from `--max-cost` and refuses
      without it; `--preflight`: device status, `qnx` cost estimate of every job against `--max-cost`
      and the sum against `--cap-hqc`, the preregistered prediction file present and its sha256
      recorded; `--submit` to `H2-2` requires `--prereg`, the preflight record and `--cap-hqc`, and
      refuses otherwise; `--retrieve` polls `qnx.jobs.results` and writes counts files, recording the
      bit-order convention and whether the backend returned counts or shots.
    - tests `tests/test_quantinuum_submit.py`: parser has no password/token argument; a dry run leaves
      no credential string in any written file or log (grep the output tree for the fake credential
      used in the test); session fields; counts-file decode to our little-endian keys.

A8. Gate `scripts/gate_Q0P_2x3.py --stage verify` and `--stage predict` -> `validation/Q0P_2x3.json`,
    `reports/Q0P_2x3.md` (via `skqd.report.GateResult`; never a typed number).  `predict` writes the
    preregistration block: per device, gate-only $f$ and the three memory scenarios, the pilot plan
    (Stage P below) and the full-campaign plan (D3' at $0.7 f$ for $f \in \{0.05, 0.10, 0.15\}$), HQC
    and USD; `--stage prereg-md` renders `reports/Q0P_2x3_prereg.md` from the JSON.

Pass criteria of **Q0P_2x3 Stage A** (status PASS iff Q1-Q7; the device verdicts are result fields):
- Q1 all 44 compiled native circuits exact: max $|\Delta\psi| < 10^{-10}$ after global-phase removal
  (float64 accumulation over $\sim 5\times10^{3}$ gates is $\sim10^{-12}$; the same bound as gate
  S2_2x4's C2), leakage $< 10^{-9}$, implicit permutation identity, measurement map $q_k \to c_k$;
- Q2 RZZ count 2158 before compilation on all 44; ZZ count after compilation recorded per circuit and
  per level, and the frozen level's count $\le 2158$;
- Q3 JSON and QASM round trips identical to $10^{-12}$; the endianness test decodes to key 1;
- Q4 device table reproduces the prototype's Quantinuum gate-only $f$ and the IonQ feasibility rows to
  $10^{-12}$; every spec entry carries `source`, `read_on`, `verbatim`; every estimate carries
  `ESTIMATE` and its inputs;
- Q5 `hqc_per_shot` recomputed from the manifests equals the table's value to $10^{-12}$ (planner:
  4.9666 at the mean counts 3053 / 2158 / 40), and the pilot and campaign HQC totals in the JSON
  equal the formula applied to the plan's shots;
- Q6 dry run wrote `session.json` + counts for the 2 `k = 1` circuits (+ the 2 calibration circuits:
  all-zeros, single X on qubit 0); no credential string in any output (test); every job body has
  `no_opt: true`, `allow_implicit_swaps: false` and a `max_cost`; the A6 $f$ interval is reported with
  the shots used;
- Q7 `pytest -q tests` and `python scripts/check_package.py` pass; the five pinned versions are
  unchanged after A1 (recorded in the JSON).

`what_pass_means` (verbatim): "compiled to the Quantinuum native gate set, verified exactly, costed and
packaged; PASS is NOT a statement that H2-2 or Helios-1 delivers the signed clean-shot fraction —
that is Stage E's emulator measurement, and after it Stage P's device pilot".

### Stage E — vendor emulator (needs a Nexus login; eHQC or QCUP simulation seconds; owner confirms the budget; about half a day)

Not started until the owner says the login exists and names the budget (`--max-cost` per job and
`--cap-hqc` for the stage).  Costs below are planner arithmetic at 4.97 HQC/shot.

E1. `--syntax-check` of all 44 circuits on `H2-2SC` (free): compile success, the compiler's own gate
    counts (record; if the stack changes the ZZ count, the frozen circuit must be resubmitted with
    `no_opt=True` and the counts must then agree with A3 — a criterion).
E2. `--emulate` on `H2-2E` with the noise model on: B0 and B1 `k = 1` circuits at 1000 shots each
    (about 9,900 eHQC) and `k = 4` at 200 shots each (about 2,000 eHQC).  `max_cost` per job from the
    formula + 10 %.
E3. The same on `Helios-1E` only if a submission path for pytket circuits exists for it at that time
    (see A9); otherwise record "not run".
E4. `gate_Q0P_2x3.py --stage assemble-emulator`: clean statistics by the reference-string test;
    $f_E$ per circuit with Garwood intervals; the pooled $k = 1$ value is **the prediction** for the
    device pilot; the D3' plan at $0.7 f_E$; the emulator-vs-prediction ratio against the gate-only
    value (this measures the memory term the planner could only estimate).

Criteria E1-E4 (separate `stage_E.status`): E1 44/44 compile; counts agree with A3 or the
resubmission rule applied; E2 the four jobs returned with the planned shots; E3 recorded; E4 the
pooled $f_E$ interval is reported and the GO rule evaluated: **GO to Stage P iff the 95 % lower bound
of pooled $f_E \ge 0.05$ and the point estimate $\ge 0.10$** (the signed bars applied to the emulator);
otherwise the result goes to the owner with the memory-term diagnosis (ratio $f_E / f_{\rm gate}$).

### Stage P — device pilot (not under this prompt; needs an HQC allocation and the owner's signature)

For the owner's allocation request: B0 and B1 `k = 1` circuits at 1000 shots each on H2-2, about
9,940 HQC, prediction $f_E$ preregistered (K1-style: prereg JSON committed before submission, its
sha256 in the preflight record), GO rule for the full campaign: pooled device $f$ 95 % lower bound
$\ge 0.05$ and point estimate $\ge 0.10$.  Full campaign at $f = f_{\rm device}$: D3' shots per sector
(about 51,000 each at $f = 0.14$), 11 jobs per sector at the 10,000-shot limit, about $5\times10^{5}$
HQC, 60 h of machine time at the mid scenario.

### A9 (optional, after A8; only if the owner wants Helios in the same build)

`pip install --dry-run guppylang` must show no change to the pins (planner: none, but it adds
llvmlite, ziglang, wasmtime, selene-*).  If installed: load the frozen pytket circuits into a Guppy
program by the documented route ("Pytket can be submitted to Helios by loading the user circuit into
Guppy source", https://docs.quantinuum.com/systems/user_guide/hardware_user_guide/workflow.html),
compile to HUGR, run the two `k = 1` circuits on the local Selene statevector simulator (noiseless) and
check the counts against our statevector probabilities; record the HUGR package per circuit under
`data/quantinuum/circuits_2x3_helios/`.  If the route needs an API or anything undocumented, stop
and record it.

## HQC, QPU seconds and money

0 on IBM, 0 on IonQ, 0 HQC on Quantinuum under Stage A.  Stage E spends eHQC (or QCUP simulation
seconds) only after the owner's written confirmation of the budget, with `max_cost` on every job.
Never submit to `H2-2`, `H2-1`, `H1-1` or `Helios-1` under this prompt.  Syntax checkers are free
(Azure provider page: "Syntax Checkers usage is offered free-of-charge").

## Outputs

- `src/skqd/quantinuum_native.py`; `scripts/quantinuum_build_circuits.py`,
  `scripts/quantinuum_device_table.py`, `scripts/quantinuum_account.py`,
  `scripts/quantinuum_submit.py`, `scripts/gate_Q0P_2x3.py`;
- `data/quantinuum/circuits_2x3/` (44 x {qasm, json, manifest} + index), `data/quantinuum/devices_20261002.json`,
  `data/quantinuum/stack_check_20261002.json`, `data/hardware/Q0P_2x3_dryrun/` (session + counts);
- `validation/Q0P_2x3.json`, `reports/Q0P_2x3.md`, `reports/Q0P_2x3_prereg.md`;
- tests: `tests/test_quantinuum_native.py`, `tests/test_quantinuum_submit.py`,
  `tests/test_quantinuum_device_table.py`;
- `validation/gates.md`: row for Q0P_2x3 (Stage A status; Stage E "not run" until it runs);
  `reports/PROJECT_STATUS.md`: one paragraph; `graphify update .` after the code changes;
- git: commit after Stage A (`git commit <paths>`; retry if `.git/index.lock` exists); **no push**.

## Escalation and STOP conditions

- STOP (binding) if the native conversion cannot reach $10^{-10}$ after two honest attempts: write the
  residual, the first gate at which it appears and the two candidate conventions (half-turn factor,
  PhasedX order, ZZPhase sign) into `validation/BLOCKED.md`; do not loosen Q1.
- STOP if `compile_native` at every level changes the statevector (a TKET pass that is not exact for
  this family): freeze the level-0 circuits (pure rebase) and record it.
- STOP if any step needs a package change in `coding`, a Nexus login that does not exist, a change to
  the signed family, or any hardware submission.
- STOP if the Stage E emulator gives pooled $f_E < 0.05$ on H2-2E: the planner must look (the memory
  term would be larger than the pessimistic scenario).
- After two failed attempts at any pass criterion: BLOCKED.md and stop; the planner returns.

## Do-not-touch list (binding)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py`, `device_req.py` (add nothing that
changes a value), every existing `validation/*.json`, every frozen circuit under `data/hardware/`,
the signed family, every criterion constant of every existing gate, `ci/`, `prompts/00`-`25`,
`prompts/27` (another planner's), `prompts/LOG.md` (the coordinator appends).

## What the owner must do (the executor cannot)

1. **Access.**  Apply to OLCF's QCUP (https://docs.olcf.ornl.gov/quantum/quantum_access.html;
   year-round "Project Application Form" at myOLCF; vendors IBM, Quantinuum, IonQ, IQM; default
   emulator quota "6000 seconds", hardware "0 HQCs" until a monthly allocation request "justified
   using results from an emulator" is approved — deadline the 25th of the preceding month), or write
   to Sales@Quantinuum.com for a research agreement / Nexus account, or use an Azure Quantum
   workspace (Standard plan USD 125,000/month for 10k HQC + 100k eHQC; pay-as-you-go by contact).
   Quantinuum's page says "Researchers in the United States may apply" for QCUP; confirm eligibility
   with OLCF.
2. **Budget for Stage E**: about 12,000 eHQC on H2-2E (or the QCUP simulation-seconds equivalent) and
   the written go-ahead with `--max-cost`.
3. **Allocation for Stage P**: about 10,000 HQC on H2-2 for the two-circuit pilot; for the full
   campaign about 500,000 HQC — ask Quantinuum / OLCF whether an allocation of that size is possible
   at all before planning it; if not, the owner decides whether a reduced, unsigned 2x3 run (fewer
   references, $k \le 2$) is worth a signature.
4. People: QCsupport@quantinuum.com (calendar of commercial periods, emulator discrepancies);
   OLCF QCUP help for allocations.

## LOG row (append to `prompts/LOG.md`, one row per stage; the planner's own row is already there)

| date | prompts/26_2x3_circuits_for_quantinuum_h2_helios.md Stage A / Stage E | Q0P_2x3 | executor-opus | PASS/FAIL with the numbers from the JSON (max residual; ZZ count per level; gate-only $f$ H2-2 / Helios-1 / H1-1; HQC per shot; pilot and campaign HQC; dry-run $f$ interval; stack check result; for Stage E the pooled $f_E$ interval and the GO rule) | commit | open items (owner access, Stage E budget, Stage P allocation) |

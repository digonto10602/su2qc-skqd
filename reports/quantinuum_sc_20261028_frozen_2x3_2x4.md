# H2-2SC syntax check of the frozen 2x3 and 2x4 circuits (2026-10-28)

- Date: 2026-10-28. Git commit at report time: `eef94e3`, plus the uncommitted `max_cost` fix shown in section 5.
- Request in force: the owner's words of 2026-10-28, "run the syntax checker on 2x3, 2x4 frozen and compressed" (this report covers the FROZEN circuits; the compressed exports come later).
- Related reports: `reports/quantinuum_sc_20261028_frozen_2x2.md`, `reports/quantinuum_sc_20261028_2x2_frozen_vs_compressed.md`.
- Data: `data/hardware/quantinuum_sc_20261028/frozen_2x3/` (`summary.json`, `session.json`, `counts/`, `account_before.json`, `account_after.json`) and `data/hardware/quantinuum_sc_20261028/frozen_2x4/` (`summary.json`, the two failed attempts' session files and error logs, `account_before.json`, `account_after.json`).
- Every number below is read from those files by a generator script, not typed by hand.
- Owner's thread rule followed: every heavy command ran under `taskset -c 0-9 nice -n 10` with OMP/MKL/OPENBLAS threads = 10.

## Words used here

- **H2-2SC**: the *syntax checker* of Quantinuum's H2-2 trapped-ion computer: it compiles a circuit as the machine would and returns the cost the job would have, but does not run it, so every shot comes back as all zeros. Documented as free.
- **Nexus**: Quantinuum's cloud service; `qnexus` is its Python client (0.51.0 here). A circuit is first *uploaded* to Nexus, then a *job* (circuit + shot count + device) is started on it.
- **HQC** (H-System Quantum Credit): Quantinuum's billing unit. Package formula (`skqd.quantinuum_native.hqc_job`):
$$\mathrm{HQC} = 5 + C\,\frac{N_{1q} + 10\,N_{2q} + 5\,N_m}{5000},$$
  with $C$ shots, $N_{1q}$ PhasedX (one-qubit) gates, $N_{2q}$ ZZPhase (two-qubit) gates, $N_m$ initialisations plus measurements.
- **Frozen** circuits: the stored, checksummed pytket circuits (`data/quantinuum/circuits_2x3`, `data/quantinuum/circuits_2x4`). For 2x4 only the *structured* source is frozen (`validation/QV_2x4_01.json`, `data.frozen_source = "structured"`); the 19 `*.opt3` circuits were not submitted.
- **HTTP 500**: the server's generic "internal error" reply; it says the server failed, not what was wrong with the request.

## 1. What was asked

Run the free syntax checker H2-2SC (nothing else) on the frozen 2x3 circuits (44 lattice + 2 calibration) and on the 60 frozen 2x4 structured circuits; record completion, all-zero results, checker cost vs formula, per-circuit cost range and totals; fix the script's `max_cost` defect (permitted); stop after one retry if Nexus rejects the large 2x4 circuits.

## 2. What was done

1. Fixed the `max_cost` defect in `scripts/quantinuum_submit.py` (section 5) and added a test; `tests/test_quantinuum_submit.py` 9 passed (8 fast tests + the Aer dry-run test) in the isolated venv.
2. Dry runs (`--dry-run --records-only`, no network) for both lattices: 2x3 `--all` = 46 jobs; 2x4 `--only` the 60 ids of `index.json` `sources.structured.circuits` plus CAL_zeros, CAL_x0 = 62 jobs. No change to the script was needed for the gzipped 2x4 layout: `load_frozen` already reads `.json.gz` and checks the sha256 of the uncompressed text, and `--only` selects the structured circuits.
3. Offline safety gate: every job record carries the device string `H2-2SC` and nothing else, no `opt3` id is in the 2x4 plan, every circuit loads with its manifest sha256, every `QuantinuumConfig` builds. The live device list (read-only) showed H2-2SC as system_type "syntax checker" before each run.
4. 2x3: `--syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x3 --all --max-cost 1100 --project su2qc-skqd-2x3-frozen`, then `--status` and `--retrieve`; first attempt succeeded.
5. 2x4: `--syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x4 --only <60 structured> CAL_zeros CAL_x0 --max-cost 40000 --project su2qc-skqd-2x4-frozen`; the upload of the first circuit failed twice (section 3.2); stopped after the one retry as instructed.

## 3. Results

### 3.1 Frozen 2x3: all jobs passed

| quantity | value | source (`frozen_2x3/summary.json`) |
|---|---|---|
| jobs completed / error | 46/46 / 0 | `n_completed`, `n_error` |
| all-zero results | 46/46 jobs, 200 of 200 shots each | `n_all_zero` |
| max $|\mathrm{SC} - \mathrm{formula}|$ | 1.1e-13 HQC (floating-point rounding) | `max_abs_sc_minus_formula` |
| per-circuit SC cost, 44 lattice circuits, 200 shots | 995.76 to 999.84 HQC | `jobs[].sc_cost_hqc` |
| lattice total (44 circuits), SC / formula | 43926.00 / 43926.00 HQC | `total_sc_cost_hqc_28_lattice` (the key name is inherited; it sums every non-calibration job) |
| calibration (2 circuits) | 26.04 HQC | |
| all 46 jobs, SC / formula | 43952.04 / 43952.04 HQC | `total_sc_cost_hqc` |
| HQC per shot (lattice) | 4.9538 to 4.9742; mean 4.9666 | `jobs[].formula_hqc_per_shot` |
| gate counts (lattice) | $N_{2q}$ = 2158, $N_{1q}$ = 2989 to 3091, $N_m$ = 40 | `jobs[].native_counts` |

No job reported compile error text; job ids are in `summary.json` (`jobs[].job_id`).

### 3.2 Frozen 2x4: not run -- Nexus rejected the circuit upload

Both attempts failed while uploading the FIRST circuit, `B0_ref102_k1.structured`, before any job existed:

| attempt | started | error logged by | jobs created | error |
|---|---|---|---|---|
| 1 | 19:14:58 | 19:16:16 | 0 | `Failed to create resource with status code: 500, message: {"message":"Internal Server Error - Cancelled"}` |
| 2 | 19:17:51 | 19:19:07 | 0 | `Failed to create resource with status code: 500, message: {"message":"Internal Server Error - Cancelled"}` |

The circuit is large: 28 qubits, $N_{2q}$ = 71548, $N_{1q}$ = 210994, plus 143140 Rz gates; its pytket JSON is 32.6 MB uncompressed (0.28 MB gzipped on disk). From session start to the logged error took 78 and 76 s (this includes loading and checksumming the circuit locally); each attempt failed during the upload call (`qnx.circuits.upload`). The Nexus project `su2qc-skqd-2x4-frozen` holds 0 circuits and 0 jobs afterwards (read-only listing), so nothing partial was left. **The cause is not established**: an HTTP 500 "Cancelled" reply after that long fits a server-side request-size or time limit, but Quantinuum's reply does not say which.

For scale only, the package formula (NOT a checker value) gives 37075.16 to 37075.20 HQC per 2x4 circuit at 200 shots and 2224511.84 HQC for the 60 lattice circuits (`formula_estimate_only` in `frozen_2x4/summary.json`).

## 4. Was anything charged?

`qnexus` 0.51.0 has no HQC-balance call; `qnx.quotas.get_all()` gives CPU-time and storage counters (account-wide):

| run | before (UTC) | after (UTC) | simulation s | compilation s | database_usage MB |
|---|---|---|---|---|---|
| frozen 2x3 | 19:12:03 | 19:20:13 | 0.000 / 0.000 | 0.000 / 0.000 | 1.190 / 4.562 |
| frozen 2x4 | 19:14:41 | 19:20:05 | 0.000 / 0.000 | 0.000 / 0.000 | 3.836 / 4.562 |

Simulation and compilation time stayed at zero; only stored data grew. The two windows overlap (the 2x3 results were retrieved while the 2x4 attempts ran), so the storage growth cannot be split between them. Indirect evidence that the 2x3 checker costs are estimates, not charges: H2-2SC is classed "syntax checker", `qnexus`'s own `circuits.cost` uses H2-xSC as its "dedicated cost estimation device", and all shots came back zero. The 2x4 run created no job at all. **Not established:** a direct reading of the HQC balance (the Nexus web portal's usage page shows it).

## 5. Script fix (permitted item (a)); item (b) needed no code

```diff
diff --git i/scripts/quantinuum_submit.py w/scripts/quantinuum_submit.py
index 11ec358..6b93239 100644
--- i/scripts/quantinuum_submit.py
+++ w/scripts/quantinuum_submit.py
@@ -145,7 +145,8 @@ def backend_config_fields(device, args, max_cost):
             "noisy_simulation": (True if device.endswith("E") else None),
             "no_opt": True, "allow_implicit_swaps": False,
             "attempt_batching": bool(args.attempt_batching), "user_group": args.user_group,
-            "max_cost": max_cost}
+            # QuantinuumConfig.max_cost is an int field (quantinuum-schemas 7.8.2): round the cap UP
+            "max_cost": (None if max_cost is None else int(math.ceil(max_cost)))}
 
 
 def plan_jobs(args, cdir, index, device):
```

Test added in `tests/test_quantinuum_submit.py`: `test_job_records_carry_the_required_config_fields` now also asserts that the config cap is an integer $\ge$ the job's cap, and the new `test_backend_config_builds_a_quantinuum_config` builds a `QuantinuumConfig` from every default (formula x 1.10, decimal) 2x3 job record, the case that failed on 2026-10-28 for 2x2 attempt 1. Result: 9 passed. The 2x3 run used the fixed script; the cap passed to Nexus was the integer `--max-cost`.

## 6. What the result means

- The 44 frozen 2x3 circuits (and the 2 calibration circuits) compile on H2-2 as submitted (`no_opt=True`, no implicit swaps), and Quantinuum's cost equals the package formula, as for 2x2. The formula can set the 2x3 shot budget.
- The frozen 2x4 circuits could not be checked: Nexus did not accept the upload of a circuit of this size through `qnx.circuits.upload`. This is a transport problem, not a compile verdict; H2-2SC never saw the circuit.
- Nothing here is a physics result.

## 7. Problems and options

1. **2x4 upload rejected twice** (HTTP 500 "Internal Server Error - Cancelled"); stopped after the one retry, no circuit split or modified. Options for the owner/planner, none tried: ask Quantinuum support for the upload size/time limit and a supported route for circuits of this size; try a newer `qnexus` (0.51.0 already warns of a deprecated endpoint) in a separate venv; or submit a smaller-footprint encoding of the same circuit (that would be a new frozen artefact, so it needs a plan).
2. 2x4 calibration circuits (CAL_zeros, CAL_x0) were included in the plan for consistency with `--all`; they never ran.
3. Quota windows of the two runs overlap (section 4).
4. `cost_confidence` is -1.0 on every 2x3 job (`qnexus`'s placeholder when no value is sent); the quotas endpoint prints a deprecation warning for qnexus 0.51.0.
5. The summary key `total_sc_cost_hqc_28_lattice` is a name inherited from the 2x2 collector; for 2x3 it sums the 44 lattice circuits.

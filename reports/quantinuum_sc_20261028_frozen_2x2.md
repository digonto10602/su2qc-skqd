# H2-2SC syntax check of the frozen 2x2 circuits (2026-10-28)

- Date: 2026-10-28 (jobs submitted 2026-10-28 18:17:40 to 2026-10-28 18:18:23 UTC)
- Git commit: `261222c` (working tree; nothing committed by this run)
- Request in force: the owner's words of 2026-10-28, "run the syntax checker on both frozen and compressed circuit A and B test on H2-sc first"; this report covers the FROZEN 2x2 circuits only (the compressed ones are a separate request).
- Data: `data/hardware/quantinuum_sc_20261028/frozen_2x2/` (`session.json`, `counts/*.json`, `summary.json`, `account_before.json`, `account_after.json`, `attempt1_session_maxcost_type_error.json`).
- Every number below is read from `summary.json` / `account_*.json` by a generator script, not typed by hand.

## Words used here

- **Nexus**: Quantinuum's cloud service through which jobs are sent; `qnexus` is its Python client (version 0.51.0 here).
- **H2-2SC**: the *syntax checker* of Quantinuum's H2-2 trapped-ion computer. It compiles a circuit exactly as the real machine would and reports the cost, but does not run it: every shot comes back as all zeros. Quantinuum documents it as free.
- **HQC** (H-System Quantum Credit): Quantinuum's billing unit. The package's formula (`skqd.quantinuum_native.hqc_job`, from the Azure Quantinuum provider page) is
$$\mathrm{HQC} = 5 + C\,\frac{N_{1q} + 10\,N_{2q} + 5\,N_m}{5000},$$
  where $C$ is the number of shots, $N_{1q}$ the PhasedX (one-qubit) gate count, $N_{2q}$ the ZZPhase/ZZMax (two-qubit) gate count and $N_m$ the qubit initialisations plus measurements.
- **Shot**: one run of the circuit ending in one measured bit string. **Job**: one circuit with its shot count sent to a device.
- **Frozen circuit**: the stored, checksummed pytket circuit of `data/quantinuum/circuits_2x2/` (built 2026-10-13, prompts/35); the script refuses to send one whose sha256 differs from its manifest.

## 1. What was asked

Send every frozen 2x2 circuit to the free syntax checker H2-2SC (nothing else), retrieve the results, and record per circuit the job id, status, the checker's cost estimate, whether the results are all zeros, and any compile error; compare each cost with the package formula; show that no HQC was charged.

## 2. What was done

1. Read `scripts/quantinuum_submit.py` in full. Findings: `--syntax-check` uses `--device` or the default `H2-2SC` and refuses any device outside `SYNTAX_CHECKERS = (H2-2SC, H2-1SC, H1-1SC, Helios-1SC)`; it cannot reach the hardware or emulator branches, which are separate flags (`--submit` additionally needs a preregistration, a preflight record, `--cap-hqc` and `--max-cost`). Shots: default `--shots 200` and `--cal-shots 200`. It writes `<out>/session.json` (job records, saved after every submission so a job id survives a crash) and, on `--retrieve`, one `counts/<id>.json` per job (never overwritten). `--all` takes the 28 lattice circuits plus the 2 calibration circuits (CAL_zeros, CAL_x0) of `index.json`, i.e. 30 jobs.
2. Dry run (local, no network) with `--dry-run --circuits data/quantinuum/circuits_2x2 --all` into a scratch directory: all 30 frozen circuits loaded with matching sha256 and ran on the local simulator Aer (200 shots each).
3. Safety gate before any network call: replayed the script's device choice and job plan offline; every job record carries the device string `H2-2SC` and only that. Then the live device list (read-only) gave: `H2-2SC` system_type "syntax checker"; `H2-2` system_type "hardware"; `H2-2E` system_type "emulator"; `Helios-1SC` system_type "emulator". The hardware row H2-2 names `H2-2SC` as its syntax checker.
4. Attempt 1 (`--syntax-check --device H2-2SC ... --all`) stopped before any job was started: the script's default per-job cap `max_cost` = formula x 1.10 (e.g. 140.05) is a decimal, and `QuantinuumConfig.max_cost` accepts only an integer (pydantic error `int_from_float`). One circuit (B0_ref06_k1) had already been uploaded to the Nexus project; no job exists for it. Its session file is kept as `attempt1_session_maxcost_type_error.json`.
5. Attempt 2 (the one retry), adapted only by command-line options: `--max-cost 141` (an integer above the largest formula estimate, 127.60 HQC), `--project su2qc-skqd-2x2`. 30 jobs were submitted, then `--status` and `--retrieve`.
6. Read-only collection of each job's status, message, error detail and cost (`qnx.jobs.status`, `qnx.jobs.cost_confidence`), and of the account quotas before and after.

Command: `~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x2 --all --max-cost 141 --project su2qc-skqd-2x2 --out data/hardware/quantinuum_sc_20261028/frozen_2x2`, then `--retrieve --circuits data/quantinuum/circuits_2x2 --out data/hardware/quantinuum_sc_20261028/frozen_2x2`.

## 3. Results

30 of 30 jobs COMPLETED, 0 ERROR, no compile error text on any job (message "The job is completed.", error_detail empty). 30 of 30 jobs returned only the all-zero string, 200 times out of 200 shots, as the documentation says a syntax checker does.

| circuit | Nexus job id | status | shots | SC cost (HQC) | formula (HQC) | SC - formula | all zeros |
|---|---|---|---|---|---|---|---|
| B0_ref06_k1 | `7c4b5aed-a579-4bd4-b92b-d0df54169af8` | COMPLETED | 200 | 127.32 | 127.32 | -1.4e-14 | yes |
| B0_ref06_k2 | `1cedf48c-7e6b-4cd7-90ef-6e3dd4378844` | COMPLETED | 200 | 127.40 | 127.40 | 1.4e-14 | yes |
| B0_ref06_k3 | `567b48c7-2ec1-446a-9897-e95a27b65abc` | COMPLETED | 200 | 127.20 | 127.20 | 0.0e+00 | yes |
| B0_ref06_k4 | `655235e4-9473-4da9-a0ec-f2db977422d7` | COMPLETED | 200 | 126.88 | 126.88 | -1.4e-14 | yes |
| B0_ref43_k1 | `207be805-131a-438a-8767-0ff8a8a8a4f5` | COMPLETED | 200 | 127.40 | 127.40 | 1.4e-14 | yes |
| B0_ref43_k2 | `e0ed3698-c8a4-403e-aa3f-be3111b27850` | COMPLETED | 200 | 127.44 | 127.44 | 0.0e+00 | yes |
| B0_ref43_k3 | `004e6316-4416-4377-978b-63b3eb665e02` | COMPLETED | 200 | 127.24 | 127.24 | 0.0e+00 | yes |
| B0_ref43_k4 | `5ab1d04f-f104-4caf-a6cd-f84c3be6e8d9` | COMPLETED | 200 | 126.92 | 126.92 | 0.0e+00 | yes |
| B0_ref30_k1 | `81ad7bb4-7c89-43d9-91f8-643adbf4e2d7` | COMPLETED | 200 | 127.36 | 127.36 | 0.0e+00 | yes |
| B0_ref30_k2 | `d8c89c81-d97f-46fa-91cf-8c9d26ec83c7` | COMPLETED | 200 | 127.52 | 127.52 | -1.4e-14 | yes |
| B0_ref30_k3 | `97771662-3d48-46f7-927e-b27c8f26f670` | COMPLETED | 200 | 127.28 | 127.28 | -1.4e-14 | yes |
| B0_ref30_k4 | `5247eb4c-dccf-44ba-860e-eb197327347d` | COMPLETED | 200 | 127.04 | 127.04 | 1.4e-14 | yes |
| B0_ref21_k1 | `63b305cb-ff2c-4608-84c6-2e0f96660b8a` | COMPLETED | 200 | 127.40 | 127.40 | 1.4e-14 | yes |
| B0_ref21_k2 | `59bf4fbb-1d38-480a-90f3-6117f56a3a16` | COMPLETED | 200 | 127.56 | 127.56 | 0.0e+00 | yes |
| B0_ref21_k3 | `8acbb34a-5d4e-409d-ad8a-5e2732db9ece` | COMPLETED | 200 | 127.16 | 127.16 | 0.0e+00 | yes |
| B0_ref21_k4 | `dc4a00c7-5f49-4f71-8e2c-f190698495e8` | COMPLETED | 200 | 127.04 | 127.04 | 1.4e-14 | yes |
| B0_ref17_k1 | `165baf9d-f642-46f5-9f3a-4c756e24f7b1` | COMPLETED | 200 | 127.52 | 127.52 | -1.4e-14 | yes |
| B0_ref17_k2 | `c99480b5-1e29-4104-9168-c31476cde7fe` | COMPLETED | 200 | 127.60 | 127.60 | 0.0e+00 | yes |
| B0_ref17_k3 | `afdfac28-dd71-412e-8f3d-36ccdb7fc460` | COMPLETED | 200 | 127.16 | 127.16 | 0.0e+00 | yes |
| B0_ref17_k4 | `750ef406-240f-49ef-a5aa-d744c9781d37` | COMPLETED | 200 | 126.96 | 126.96 | -1.4e-14 | yes |
| B1_ref14_k1 | `c857e59e-c670-46a1-a9b7-88800af50129` | COMPLETED | 200 | 127.04 | 127.04 | 1.4e-14 | yes |
| B1_ref14_k2 | `7339508f-80db-4c08-a210-ac378ccf48c0` | COMPLETED | 200 | 126.96 | 126.96 | -1.4e-14 | yes |
| B1_ref14_k3 | `b0f901de-6be8-4dd0-a8c9-f44edb5c628e` | COMPLETED | 200 | 127.16 | 127.16 | 0.0e+00 | yes |
| B1_ref14_k4 | `14504632-5545-4c48-97be-d4fa2e326cbd` | COMPLETED | 200 | 126.80 | 126.80 | 0.0e+00 | yes |
| B1_ref07_k1 | `98d62d9f-3bca-45aa-a1e3-ed7dc360a478` | COMPLETED | 200 | 126.88 | 126.88 | -1.4e-14 | yes |
| B1_ref07_k2 | `8d7cbaca-efd6-44f1-8dea-05f23a01cc1a` | COMPLETED | 200 | 126.92 | 126.92 | 0.0e+00 | yes |
| B1_ref07_k3 | `744647c6-c12e-461f-b988-8e7ac7e6bb5a` | COMPLETED | 200 | 127.12 | 127.12 | 0.0e+00 | yes |
| B1_ref07_k4 | `7908613e-edf3-45da-96ee-d4e282c1d80e` | COMPLETED | 200 | 126.84 | 126.84 | 1.4e-14 | yes |
| CAL_zeros | `93a32d27-3d9c-4e8b-a76e-01f477b9e005` | COMPLETED | 200 | 9.80 | 9.80 | 0.0e+00 | yes |
| CAL_x0 | `2b3e30e7-52eb-466b-9de6-090d181f19ca` | COMPLETED | 200 | 9.84 | 9.84 | 0.0e+00 | yes |

**Totals** (200 shots per job): all 30 jobs 3580.76 HQC from the checker against 3580.76 HQC from the formula; the 28 lattice circuits alone 3561.12 vs 3561.12 HQC. Largest per-job difference $|\Delta| = 1.4e-14$ HQC, which is floating-point rounding: the checker counts the same $N_{1q}, N_{2q}, N_m$ as the package. Source: `summary.json` keys `total_sc_cost_hqc`, `total_formula_hqc`, `max_abs_sc_minus_formula`.

**Meaning.** All 28 frozen 2x2 lattice circuits (and the 2 calibration circuits) pass H2-2's compiler unchanged with `no_opt=True` and no implicit swaps, and the package's cost formula reproduces Quantinuum's own estimate exactly. The SC cost is the price these jobs WOULD have on H2-2 hardware at 200 shots; it scales linearly in the shot count (per-shot cost $0.609$ to $0.613$ HQC for the lattice circuits, `formula_hqc_per_shot`). This check says nothing about the physics: the results are zeros by design.

## 4. Was anything charged?

- What `qnexus` 0.51.0 exposes about the account: `qnx.quotas.get_all()` lists CPU-time and storage quotas only; there is no HQC balance or HQC-usage call in this client. Before / after this run:

| quota | before | after | unit |
|---|---|---|---|
| simulation | 0.000 | 0.000 | s |
| compilation | 0.000 | 0.000 | s |
| database_usage | 0.000 | 0.468 | MB |
| jupyterhub | 3600.000 | 3600.000 | s |

  (before 2026-10-28 18:16:46 UTC, after 2026-10-28 18:21:23 UTC; `account_before.json`, `account_after.json`). Simulation and compilation time stayed at zero; only the stored-data counter grew (the uploaded circuits and results).
- The "cost" each job reports is the hardware estimate, not a charge: `qnexus`'s own `circuits.cost` routes cost estimation to the H2-xSC device as "a dedicated cost estimation device" (`qnexus/client/circuits.py`), and the device list classifies H2-2SC as "syntax checker". The all-zero results confirm that nothing ran on the ion trap.
- **Not established here:** a direct reading of the account's HQC balance before and after. If the owner wants that proof, the Nexus web portal's usage page is the place to read it; this client cannot.

## 5. Problems and assumptions

1. **Script defect (not edited):** `plan_jobs` sets `max_cost` = formula x 1.10 rounded to 2 decimals, but `QuantinuumConfig.max_cost` (quantinuum-schemas, marked deprecated in favour of the per-job `max_cost` of `start_execute_job`) is an integer field. Every `--syntax-check`, `--emulate` or `--submit` run without an integer `--max-cost` fails at the first job. Fix for the builder: round the cap up to an integer, or drop `max_cost` from the config and keep only the per-job argument.
2. Attempt 1 left one uploaded circuit (B0_ref06_k1) in the Nexus project `su2qc-skqd-2x2` with no job; the project now holds 31 circuits and 30 jobs (read-only listing).
3. `--all` includes the 2 calibration circuits, so 30 jobs ran, not 28; their rows are listed separately in the totals.
4. Per-job `max_cost` was 141 HQC instead of the script's 1.10 x formula; on a syntax checker this cap has no effect.
5. The venv `~/.local/share/su2qc-quantinuum/venv` is built with `include-system-site-packages = true` on top of the `coding` conda env, so packages such as pydantic are imported from `coding`. Nothing was installed. The quotas endpoint printed a deprecation warning (qnexus 0.51.0 uses `/api/quotas/v1beta`); it still answered.
6. `cost_confidence` is -1.0 on every job, which is `qnexus`'s placeholder when the service sends no confidence value.

# H2-2SC syntax check of every frozen and compressed circuit family, 2x2 / 2x3 / 2x4 (2026-10-28)

- Date: 2026-10-28. Git commit at report time: `a66c35a`.
- Requests in force: the owner's words of 2026-10-28, "run the syntax checker on both frozen and compressed circuit A and B test on H2-sc first" and "run the syntax checker on 2x3, 2x4 frozen and compressed".
- Related reports: `reports/quantinuum_sc_20261028_frozen_2x2.md`, `reports/quantinuum_sc_20261028_2x2_frozen_vs_compressed.md`, `reports/quantinuum_sc_20261028_frozen_2x3_2x4.md`.
- Data: one directory per family (listed in section 3), each with `summary.json` (and `session.json`, `counts/`, `account_before.json`, `account_after.json` where jobs ran). Every number below is read from those files by a generator script, not typed by hand.
- Owner's thread rule: every heavy command ran under `taskset -c 0-9 nice -n 10` with OMP/MKL/OPENBLAS threads = 10; families ran one after another.

## Words used here

- **H2-2SC**: the *syntax checker* of Quantinuum's H2-2 trapped-ion computer. It compiles a circuit as the machine would and returns the cost the job would have, but does not run it: every shot comes back as all zeros. Documented as free.
- **Nexus**: Quantinuum's cloud service (`qnexus` 0.51.0 is its Python client). **Job**: one circuit + shot count on one device. **Shot**: one run ending in one bit string.
- **HQC** (H-System Quantum Credit): Quantinuum's billing unit. Package formula (`skqd.quantinuum_native.hqc_job`):
$$\mathrm{HQC} = 5 + C\,\frac{N_{1q} + 10\,N_{2q} + 5\,N_m}{5000},$$
  $C$ shots, $N_{1q}$ PhasedX (one-qubit) gates, $N_{2q}$ ZZPhase (two-qubit) gates, $N_m$ initialisations + measurements. "HQC per shot" is $(N_{1q} + 10 N_{2q} + 5 N_m)/5000$.
- **Frozen**: the package's stored, checksummed circuits (`data/quantinuum/circuits_2x<L>`; for 2x4 the *structured* source frozen by `validation/QV_2x4_01.json`).
- **Class A** (compressed): *operator-exact* -- equal to the exact product of term exponentials on every valid lattice state. **Class B** (compressed): *input-specific* -- exact only on its own reference state, for one coarse step (see each family's `index.json` fields `contract` and `valid_use`). **v1 / v2**: two versions of the 2x4 compressed families.
- **Lattice circuits**: the time-evolution circuits (one per reference state and step $k$); the 2 calibration circuits (CAL_zeros, CAL_x0) of each family are excluded from the per-circuit columns and counted only in "all jobs".
- **Max |SC - formula|**: the largest difference, over all jobs of a family, between the checker's cost and the package formula.

## 1. What was asked

Run the free H2-2SC syntax checker -- nothing else -- on the frozen and compressed (class A, class B; v1 and v2 for 2x4) circuit families of the 2x2, 2x3 and 2x4 lattices at 200 shots per job, and compare per lattice: completed/errors, all-zero results, checker cost vs formula, per-circuit cost range, totals, HQC per shot.

## 2. What was done

For every family: a records-only dry run (no network); an offline safety gate (every job record carries the device string `H2-2SC` and nothing else, every circuit loads with its manifest sha256, every job configuration builds); a read-only device-list check (H2-2SC system_type "syntax checker") with an account-quota snapshot; then `scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits <family export> --all --max-cost <whole number above the largest per-job formula cost> --project <one Nexus project per family>`, `--retrieve`, `--status`, a read-only collection of each job's status, error text and cost, and a second quota snapshot. The exact command of each family is the `produced_by` field of its `summary.json`.

## 3. All-lattice comparison (200 shots per job)

| lattice | family | jobs completed / error | all-zero results | max \|SC - formula\| (HQC) | lattice circuits | per-circuit SC cost (HQC) | lattice total SC (HQC) | lattice total formula (HQC) | all jobs SC (HQC) | HQC per shot, min to max (mean) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2x2 | frozen | 30/30 / 0 | 30/30 | 1.4e-14 | 28 | 126.80 to 127.60 | 3561.12 | 3561.12 | 3580.76 | 0.6090 to 0.6130 (0.6109) |
| 2x2 | class A | 30/30 / 0 | 30/30 | 2.8e-14 | 28 | 132.68 to 132.72 | 3716.00 | 3716.00 | 3735.64 | 0.6384 to 0.6386 (0.6386) |
| 2x2 | class B | 30/30 / 0 | 30/30 | 1.4e-14 | 28 | 37.28 to 91.12 | 1949.28 | 1949.28 | 1968.92 | 0.1614 to 0.4306 (0.3231) |
| 2x3 | frozen | 46/46 / 0 | 46/46 | 1.1e-13 | 44 | 995.76 to 999.84 | 43926.00 | 43926.00 | 43952.04 | 4.9538 to 4.9742 (4.9666) |
| 2x3 | class A | 46/46 / 0 | 46/46 | 0.0e+00 | 44 | 458.00 to 458.04 | 20153.60 | 20153.60 | 20179.64 | 2.2650 to 2.2652 (2.2652) |
| 2x3 | class B | 46/46 / 0 | 46/46 | 2.8e-14 | 44 | 169.48 to 248.84 | 9197.12 | 9197.12 | 9223.16 | 0.8224 to 1.2192 (1.0201) |
| 2x4 | frozen (structured) | **BLOCKED**: upload HTTP 500, 0 jobs created (2 attempts) | -- | -- | 60 | -- (formula only: 37075.16 to 37075.20) | -- | 2224511.84 | -- | -- |
| 2x4 | class A v1 | 77/77 / 0 | 77/77 | 1.1e-13 | 75 | 903.84 to 906.08 | 67923.08 | 67923.08 | 67955.52 | 4.4942 to 4.5054 (4.5032) |
| 2x4 | class B v1 | 77/77 / 0 | 77/77 | 5.7e-14 | 75 | 311.56 to 422.92 | 27223.96 | 27223.96 | 27256.40 | 1.5328 to 2.0896 (1.7899) |
| 2x4 | class A v2 | 77/77 / 0 | 77/77 | 3.6e-15 | 75 | 779.56 to 779.60 | 58469.80 | 58469.80 | 58502.24 | 3.8728 to 3.8730 (3.8730) |
| 2x4 | class B v2 | 77/77 / 0 | 77/77 | 5.7e-14 | 75 | 310.20 to 403.48 | 26865.00 | 26865.00 | 26897.44 | 1.5260 to 1.9924 (1.7660) |

Source of each cell: `summary.json` keys `n_completed`, `n_jobs`, `n_error`, `n_all_zero`, `max_abs_sc_minus_formula`, `jobs[].sc_cost_hqc`, `total_sc_cost_hqc_28_lattice` (an inherited key name: it sums every non-calibration job, whatever their number), `total_formula_hqc_28_lattice`, `total_sc_cost_hqc`, `jobs[].formula_hqc_per_shot`; for the blocked frozen 2x4 row, `formula_estimate_only` (formula, not a checker value).

### 3.1 Ratios to the frozen family of the same lattice (lattice totals, same circuits)

The 2x4 compressed families also carry 15 circuits at $k = 5$, which the frozen 2x4 set does not have; the 2x4 ratios use the $k \le 4$ subset of each compressed family (60 circuits) against the frozen 2x4 *formula* total (no checker value exists for it).

| lattice | family | compared circuits | family total (HQC) | frozen total (HQC) | ratio |
|---|---|---|---|---|---|
| 2x2 | class A | 28 | 3716.00 (SC) | 3561.12 (SC, 28 circuits) | 1.0435 |
| 2x2 | class B | 28 | 1949.28 (SC) | 3561.12 (SC, 28 circuits) | 0.5474 |
| 2x3 | class A | 44 | 20153.60 (SC) | 43926.00 (SC, 44 circuits) | 0.4588 |
| 2x3 | class B | 44 | 9197.12 (SC) | 43926.00 (SC, 44 circuits) | 0.2094 |
| 2x4 | class A v1 | 60 (k <= 4) | 54343.36 (SC) | 2224511.84 (formula, 60 circuits) | 0.0244 |
| 2x4 | class B v1 | 60 (k <= 4) | 21778.56 (SC) | 2224511.84 (formula, 60 circuits) | 0.0098 |
| 2x4 | class A v2 | 60 (k <= 4) | 46775.84 (SC) | 2224511.84 (formula, 60 circuits) | 0.0210 |
| 2x4 | class B v2 | 60 (k <= 4) | 21492.00 (SC) | 2224511.84 (formula, 60 circuits) | 0.0097 |

### 3.2 Native gate counts of the lattice circuits (from each job's manifest `native_counts`)

| lattice | family | $N_{2q}$ (ZZ) | $N_{1q}$ (PhasedX) | $N_m$ |
|---|---|---|---|---|
| 2x2 | frozen | 252 | 405 to 425 | 24 |
| 2x2 | class A | 245 | 622 to 623 | 24 |
| 2x2 | class B | 55 to 162 | 137 to 413 | 24 |
| 2x3 | frozen | 2158 | 2989 to 3091 | 40 |
| 2x3 | class A | 871 | 2415 to 2416 | 40 |
| 2x3 | class B | 309 to 465 | 822 to 1246 | 40 |
| 2x4 | frozen (structured) | 71548 (first circuit) | 210994 (first circuit) | 56 |
| 2x4 | class A v1 | 1736 to 1740 | 4831 to 4847 | 56 |
| 2x4 | class B v1 | 582 to 800 | 1564 to 2168 | 56 |
| 2x4 | class A v2 | 1492 | 4164 to 4165 | 56 |
| 2x4 | class B v2 | 580 to 763 | 1550 to 2052 | 56 |

### 3.3 Where each family's files are

- 2x2 frozen: `data/hardware/quantinuum_sc_20261028/frozen_2x2/` (Nexus project in `produced_by`; circuits `data/quantinuum/circuits_2x2`)
- 2x2 class A: `2x2_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classA/` (Nexus project in `produced_by`; circuits `2x4_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classA`)
- 2x2 class B: `2x2_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classB/` (Nexus project in `produced_by`; circuits `2x4_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classB`)
- 2x3 frozen: `data/hardware/quantinuum_sc_20261028/frozen_2x3/` (Nexus project in `produced_by`; circuits `data/quantinuum/circuits_2x3`)
- 2x3 class A: `2x3_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x3_classA/` (Nexus project in `produced_by`; circuits `2x3_compression_using_ai_v1/data/families/native_2x3/compressed_circuit_llm_2x3_classA`)
- 2x3 class B: `2x3_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x3_classB/` (Nexus project in `produced_by`; circuits `2x3_compression_using_ai_v1/data/families/native_2x3/compressed_circuit_llm_2x3_classB`)
- 2x4 frozen (structured): `data/hardware/quantinuum_sc_20261028/frozen_2x4/`
- 2x4 class A v1: `2x4_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x4_classA/` (Nexus project in `produced_by`; circuits `2x4_compression_using_ai_v1/data/families/native_2x4/compressed_circuit_llm_2x4_classA`)
- 2x4 class B v1: `2x4_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x4_classB/` (Nexus project in `produced_by`; circuits `2x4_compression_using_ai_v1/data/families/native_2x4/compressed_circuit_llm_2x4_classB`)
- 2x4 class A v2: `2x4_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x4_classA_v2/` (Nexus project in `produced_by`; circuits `2x4_compression_using_ai_v1/data/families/native_2x4/compressed_circuit_llm_2x4_classA_v2`)
- 2x4 class B v2: `2x4_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x4_classB_v2/` (Nexus project in `produced_by`; circuits `2x4_compression_using_ai_v1/data/families/native_2x4/compressed_circuit_llm_2x4_classB_v2`)

## 4. Was anything charged?

`qnexus` 0.51.0 has no HQC-balance call. `qnx.quotas.get_all()` gives account-wide CPU-time and storage counters; the snapshots around each family:

| lattice | family | before (UTC) | after (UTC) | simulation s | compilation s | database_usage MB |
|---|---|---|---|---|---|---|
| 2x2 | frozen | 18:16:46 | 18:21:23 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.468 |
| 2x2 | class A | 18:29:07 | 18:34:17 | 0.000 / 0.000 | 0.000 / 0.000 | 0.468 / 1.190 |
| 2x2 | class B | 18:30:01 | 18:34:52 | 0.000 / 0.000 | 0.000 / 0.000 | 0.905 / 1.190 |
| 2x3 | frozen | 19:12:03 | 19:20:13 | 0.000 / 0.000 | 0.000 / 0.000 | 1.190 / 4.562 |
| 2x3 | class A | 20:53:45 | 21:00:38 | 0.000 / 0.000 | 0.000 / 0.000 | 4.562 / 6.618 |
| 2x3 | class B | 21:00:55 | 21:04:26 | 0.000 / 0.000 | 0.000 / 0.000 | 6.618 / 7.690 |
| 2x4 | frozen (structured) | 19:14:41 | 19:20:05 | 0.000 / 0.000 | 0.000 / 0.000 | 3.836 / 4.562 |
| 2x4 | class A v1 | 21:04:54 | 21:13:02 | 0.000 / 0.000 | 0.000 / 0.000 | 7.690 / 13.436 |
| 2x4 | class B v1 | 21:13:18 | 21:20:21 | 0.000 / 0.000 | 0.000 / 0.000 | 13.436 / 16.581 |
| 2x4 | class A v2 | 21:20:47 | 21:29:39 | 0.000 / 0.000 | 0.000 / 0.000 | 16.581 / 22.691 |
| 2x4 | class B v2 | 21:29:55 | 21:37:21 | 0.000 / 0.000 | 0.000 / 0.000 | 22.691 / 25.809 |

Simulation and compilation time stayed at zero in every snapshot; only stored data grew (uploaded circuits and results). Some windows overlap (2x2 class A/B, frozen 2x3/2x4). Indirect evidence that the checker costs are estimates and not charges: H2-2SC is classed "syntax checker", `qnexus`'s own `circuits.cost` uses H2-xSC as its "dedicated cost estimation device", and every returned shot is all zeros. **Not established:** a direct reading of the HQC balance (the Nexus web portal's usage page shows it).

## 5. What the result means

- 536 of 536 submitted jobs completed across 10 families, with 0 errors and 536 all-zero results: every submitted frozen and compressed circuit compiles on H2-2 as submitted (`no_opt=True`, no implicit swaps).
- In every family the checker's cost equals the package formula to floating-point rounding (largest difference 1.1e-13 HQC), so the formula can set the shot budget of any of these families.
- The frozen 2x4 set is the exception: Nexus refused its 32.6 MB circuit upload (HTTP 500 "Internal Server Error - Cancelled", twice), so H2-2SC never saw it. Its row carries formula numbers only.
- This is a syntax and cost check. It says nothing about the physics: the results are zeros by design.

## 6. Problems and assumptions

1. Frozen 2x4 blocked by the upload error (`reports/quantinuum_sc_20261028_frozen_2x3_2x4.md` section 3.2); not retried again.
2. The summary key `total_sc_cost_hqc_28_lattice` is a name inherited from the 2x2 collector; it sums all lattice circuits (28 for 2x2, 44 for 2x3, 75 for the 2x4 compressed families).
3. `cost_confidence` is -1.0 on every job (`qnexus`'s placeholder when the service sends no value); the quotas endpoint prints a deprecation warning for qnexus 0.51.0.
4. The 2x2 frozen Nexus project holds one circuit uploaded without a job (the 2x2 attempt 1 before the `max_cost` fix).

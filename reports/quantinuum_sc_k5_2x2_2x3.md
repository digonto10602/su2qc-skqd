# H2-2SC syntax check of the k = 5 circuit sets, 2x2 and 2x3 (2026-10-28)

- Date: 2026-10-28. Git commit at report time: `14cc187` (k = 5 sets built in `14cc187` frozen and `5196d1f` compressed).
- Request in force: the owner's words, "yes, run the syntax checker on all six k=5 sets".
- Related reports: `reports/quantinuum_sc_20261028_all_lattices.md` (the k = 1..4 runs used for the comparison in section 3.2).
- Every number below is read from the `summary.json` / `account_*.json` files of section 3.3 by a generator script, not typed by hand.
- Owner's thread rule: every heavy command ran under `taskset -c 0-9 nice -n 10` with OMP/MKL/OPENBLAS threads = 10; sets ran one after another.

## Words used here

- **H2-2SC**: the *syntax checker* of Quantinuum's H2-2 trapped-ion computer: it compiles a circuit as the machine would and returns the cost the job would have, but does not run it (every shot comes back all zeros). Documented as free.
- **HQC** (H-System Quantum Credit): Quantinuum's billing unit. Package formula (`skqd.quantinuum_native.hqc_job`):
$$\mathrm{HQC} = 5 + C\,\frac{N_{1q} + 10\,N_{2q} + 5\,N_m}{5000},$$
  $C$ shots, $N_{1q}$ PhasedX (one-qubit) gates, $N_{2q}$ ZZPhase (two-qubit) gates, $N_m$ initialisations + measurements; "HQC per shot" is the fraction.
- **k**: the number of coarse time steps in a circuit's time-evolution angle ($\theta = k\,\delta t$). The k = 5 sets add one circuit per reference state (7 for 2x2, 11 for 2x3) to the existing k = 1..4 sets, plus the 2 calibration circuits.
- **Frozen / class A / class B**: the package's stored circuits / the operator-exact compressed family / the input-specific compressed family (valid only for its own reference and one coarse step).

## 1. What was asked

Run the free H2-2SC checker (nothing else) on the six k = 5 sets at 200 shots per job and compare, per lattice, frozen vs class A vs class B: completion, all-zero results, checker vs formula cost, per-circuit cost range, totals, HQC per shot, and whether each k = 5 cost equals the k = 1..4 cost of the same reference.

## 2. What was done

Per set: an offline safety gate (every job carries the device string `H2-2SC` and nothing else, every circuit loads with its manifest sha256, every job configuration builds, the whole-number `--max-cost` lies above the largest per-job formula cost); a read-only device-list check (H2-2SC system_type "syntax checker") and quota snapshot; `scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits <set> --all --max-cost <cap> --project <one Nexus project per set>`; `--retrieve`, `--status`; read-only collection of status, error text and cost; a second quota snapshot. Each set's exact command is the `produced_by` field of its `summary.json`. (The local `--dry-run --records-only` of each set was run by the builder before this step, per the request.)

## 3. Results (200 shots per job)

| lattice | set (k = 5) | jobs completed / error | all-zero results | max \|SC - formula\| (HQC) | k = 5 circuits | per-circuit SC cost (HQC) | k = 5 total SC = formula (HQC) | all jobs incl. calibration (HQC) | HQC per shot, min to max (mean) |
|---|---|---|---|---|---|---|---|---|---|
| 2x2 | frozen | 9/9 / 0 | 9/9 | 1.4e-14 | 7 | 127.04 to 127.40 | 890.00 / 890.00 | 909.64 | 0.6102 to 0.6120 (0.6107) |
| 2x2 | class A | 9/9 / 0 | 9/9 | 2.8e-14 | 7 | 132.68 to 132.72 | 929.00 / 929.00 | 948.64 | 0.6384 to 0.6386 (0.6386) |
| 2x2 | class B | 9/9 / 0 | 9/9 | 1.4e-14 | 7 | 37.28 to 91.12 | 487.32 / 487.32 | 506.96 | 0.1614 to 0.4306 (0.3231) |
| 2x3 | frozen | 13/13 / 0 | 13/13 | 1.1e-13 | 11 | 990.44 to 997.20 | 10948.20 / 10948.20 | 10974.24 | 4.9272 to 4.9610 (4.9515) |
| 2x3 | class A | 13/13 / 0 | 13/13 | 0.0e+00 | 11 | 458.00 to 458.04 | 5038.40 / 5038.40 | 5064.44 | 2.2650 to 2.2652 (2.2652) |
| 2x3 | class B | 13/13 / 0 | 13/13 | 2.8e-14 | 11 | 169.48 to 248.84 | 2299.28 / 2299.28 | 2325.32 | 0.8224 to 1.2192 (1.0201) |

Sources: `summary.json` keys `n_completed`, `n_jobs`, `n_error`, `n_all_zero`, `max_abs_sc_minus_formula`, `jobs[].sc_cost_hqc`, `total_sc_cost_hqc_28_lattice` (inherited key name: the sum over all non-calibration jobs), `total_formula_hqc_28_lattice`, `total_sc_cost_hqc`, `jobs[].formula_hqc_per_shot`.

### 3.2 Is the k = 5 cost the same as the k = 1..4 cost of the same reference?

Each k = 5 circuit's checker cost against the checker costs of k = 1, 2, 3, 4 for the same reference state (from the k = 1..4 runs of the same family):

| lattice | set | references with k = 5 cost equal to all of k = 1..4 | max \|cost(k=5) - cost(k)\| over references and k (HQC) | $N_{2q}$ identical for k = 1..5 |
|---|---|---|---|---|
| 2x2 | frozen | 0/7 | 0.56 | yes |
| 2x2 | class A | 7/7 | 0.00 | yes |
| 2x2 | class B | 7/7 | 0.00 | yes |
| 2x3 | frozen | 0/11 | 8.44 | yes |
| 2x3 | class A | 11/11 | 0.00 | yes |
| 2x3 | class B | 11/11 | 0.00 | yes |

Per reference (checker cost in HQC at 200 shots; $N_{1q}$ in brackets):

**2x2 frozen**

| reference | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|
| B0_ref06 | 127.32 [418] | 127.40 [420] | 127.20 [415] | 126.88 [407] | 127.16 [414] |
| B0_ref43 | 127.40 [420] | 127.44 [421] | 127.24 [416] | 126.92 [408] | 127.08 [412] |
| B0_ref30 | 127.36 [419] | 127.52 [423] | 127.28 [417] | 127.04 [411] | 127.40 [420] |
| B0_ref21 | 127.40 [420] | 127.56 [424] | 127.16 [414] | 127.04 [411] | 127.20 [415] |
| B0_ref17 | 127.52 [423] | 127.60 [425] | 127.16 [414] | 126.96 [409] | 127.04 [411] |
| B1_ref14 | 127.04 [411] | 126.96 [409] | 127.16 [414] | 126.80 [405] | 127.04 [411] |
| B1_ref07 | 126.88 [407] | 126.92 [408] | 127.12 [413] | 126.84 [406] | 127.08 [412] |

**2x2 class A**

| reference | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|
| B0_ref06 | 132.68 [622] | 132.68 [622] | 132.68 [622] | 132.68 [622] | 132.68 [622] |
| B0_ref43 | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] |
| B0_ref30 | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] |
| B0_ref21 | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] |
| B0_ref17 | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] |
| B1_ref14 | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] |
| B1_ref07 | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] | 132.72 [623] |

**2x2 class B**

| reference | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|
| B0_ref06 | 74.44 [326] | 74.44 [326] | 74.44 [326] | 74.44 [326] | 74.44 [326] |
| B0_ref43 | 74.48 [327] | 74.48 [327] | 74.48 [327] | 74.48 [327] | 74.48 [327] |
| B0_ref30 | 68.36 [294] | 68.36 [294] | 68.36 [294] | 68.36 [294] | 68.36 [294] |
| B0_ref21 | 91.12 [413] | 91.12 [413] | 91.12 [413] | 91.12 [413] | 91.12 [413] |
| B0_ref17 | 74.52 [328] | 74.52 [328] | 74.52 [328] | 74.52 [328] | 74.52 [328] |
| B1_ref14 | 37.28 [137] | 37.28 [137] | 37.28 [137] | 37.28 [137] | 37.28 [137] |
| B1_ref07 | 67.12 [283] | 67.12 [283] | 67.12 [283] | 67.12 [283] | 67.12 [283] |

**2x3 frozen**

| reference | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|
| B0_ref25 | 999.84 [3091] | 997.24 [3026] | 998.88 [3067] | 998.72 [3063] | 997.00 [3020] |
| B0_ref795 | 999.60 [3085] | 997.24 [3026] | 998.96 [3069] | 998.80 [3065] | 997.00 [3020] |
| B0_ref525 | 999.68 [3087] | 997.16 [3024] | 999.00 [3070] | 998.80 [3065] | 997.16 [3024] |
| B0_ref333 | 999.64 [3086] | 997.12 [3023] | 998.80 [3065] | 998.68 [3062] | 997.12 [3023] |
| B0_ref169 | 999.84 [3091] | 997.16 [3024] | 998.92 [3068] | 998.68 [3062] | 997.08 [3022] |
| B0_ref117 | 999.76 [3089] | 997.28 [3027] | 999.00 [3070] | 998.84 [3066] | 997.08 [3022] |
| B0_ref86 | 999.80 [3090] | 997.20 [3025] | 999.00 [3070] | 998.76 [3064] | 997.20 [3025] |
| B0_ref70 | 999.80 [3090] | 997.24 [3026] | 998.92 [3068] | 998.76 [3064] | 997.12 [3023] |
| B1_ref57 | 995.76 [2989] | 998.80 [3065] | 996.12 [2998] | 998.80 [3065] | 990.48 [2857] |
| B1_ref29 | 995.80 [2990] | 998.84 [3066] | 996.16 [2999] | 998.84 [3066] | 990.52 [2858] |
| B1_ref27 | 995.84 [2991] | 998.88 [3067] | 996.20 [3000] | 998.84 [3066] | 990.44 [2856] |

**2x3 class A**

| reference | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|
| B0_ref25 | 458.00 [2415] | 458.00 [2415] | 458.00 [2415] | 458.00 [2415] | 458.00 [2415] |
| B0_ref795 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B0_ref525 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B0_ref333 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B0_ref169 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B0_ref117 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B0_ref86 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B0_ref70 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B1_ref57 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B1_ref29 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |
| B1_ref27 | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] | 458.04 [2416] |

**2x3 class B**

| reference | k=1 | k=2 | k=3 | k=4 | k=5 |
|---|---|---|---|---|---|
| B0_ref25 | 207.56 [1014] | 207.56 [1014] | 207.56 [1014] | 207.56 [1014] | 207.56 [1014] |
| B0_ref795 | 207.60 [1015] | 207.60 [1015] | 207.60 [1015] | 207.60 [1015] | 207.60 [1015] |
| B0_ref525 | 202.36 [984] | 202.36 [984] | 202.36 [984] | 202.36 [984] | 202.36 [984] |
| B0_ref333 | 224.24 [1101] | 224.24 [1101] | 224.24 [1101] | 224.24 [1101] | 224.24 [1101] |
| B0_ref169 | 200.44 [976] | 200.44 [976] | 200.44 [976] | 200.44 [976] | 200.44 [976] |
| B0_ref117 | 190.36 [924] | 190.36 [924] | 190.36 [924] | 190.36 [924] | 190.36 [924] |
| B0_ref86 | 248.84 [1246] | 248.84 [1246] | 248.84 [1246] | 248.84 [1246] | 248.84 [1246] |
| B0_ref70 | 233.84 [1161] | 233.84 [1161] | 233.84 [1161] | 233.84 [1161] | 233.84 [1161] |
| B1_ref57 | 169.48 [822] | 169.48 [822] | 169.48 [822] | 169.48 [822] | 169.48 [822] |
| B1_ref29 | 206.00 [1005] | 206.00 [1005] | 206.00 [1005] | 206.00 [1005] | 206.00 [1005] |
| B1_ref27 | 208.56 [1019] | 208.56 [1019] | 208.56 [1019] | 208.56 [1019] | 208.56 [1019] |

### 3.3 Files

- 2x2 frozen k = 5: `data/hardware/quantinuum_sc_20261028/frozen_2x2_k5/` (k = 1..4 comparison: `data/hardware/quantinuum_sc_20261028/frozen_2x2/summary.json`)
- 2x2 class A k = 5: `2x2_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classA_k5/` (k = 1..4 comparison: `2x2_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classA/summary.json`)
- 2x2 class B k = 5: `2x2_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classB_k5/` (k = 1..4 comparison: `2x2_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classB/summary.json`)
- 2x3 frozen k = 5: `data/hardware/quantinuum_sc_20261028/frozen_2x3_k5/` (k = 1..4 comparison: `data/hardware/quantinuum_sc_20261028/frozen_2x3/summary.json`)
- 2x3 class A k = 5: `2x3_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x3_classA_k5/` (k = 1..4 comparison: `2x3_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x3_classA/summary.json`)
- 2x3 class B k = 5: `2x3_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x3_classB_k5/` (k = 1..4 comparison: `2x3_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x3_classB/summary.json`)

## 4. Was anything charged?

`qnexus` 0.51.0 has no HQC-balance call; `qnx.quotas.get_all()` gives account-wide CPU-time and storage counters:

| lattice | set | before (UTC) | after (UTC) | simulation s | compilation s | database_usage MB |
|---|---|---|---|---|---|---|
| 2x2 | frozen | 22:51:21 | 22:52:22 | 0.000 / 0.000 | 0.000 / 0.000 | 25.809 / 25.927 |
| 2x2 | class A | 23:21:11 | 23:22:12 | 0.000 / 0.000 | 0.000 / 0.000 | 26.766 / 26.882 |
| 2x2 | class B | 23:22:23 | 23:23:56 | 0.000 / 0.000 | 0.000 / 0.000 | 26.882 / 26.955 |
| 2x3 | frozen | 22:52:34 | 23:29:32 | 0.000 / 0.000 | 0.000 / 0.000 | 25.927 / 27.975 |
| 2x3 | class A | 23:24:07 | 23:26:02 | 0.000 / 0.000 | 0.000 / 0.000 | 26.955 / 27.476 |
| 2x3 | class B | 23:26:13 | 23:27:25 | 0.000 / 0.000 | 0.000 / 0.000 | 27.476 / 27.748 |

Simulation and compilation time stayed at zero; only stored data grew. H2-2SC is classed "syntax checker", `qnexus`'s own `circuits.cost` uses H2-xSC as its "dedicated cost estimation device", and every shot came back all zeros. **Not established:** a direct reading of the HQC balance (Nexus web portal).

## 5. What the result means

- 66 of 66 jobs completed with 0 errors and 66 all-zero results across 6 sets: every k = 5 circuit compiles on H2-2 as submitted.
- The checker cost equals the package formula in every set (largest difference 1.1e-13 HQC).
- 2x2 frozen: two-qubit count identical for k = 1..5; k = 5 cost equal to all k = 1..4 costs for 0 of 7 references, largest difference 0.56 HQC (from the PhasedX count, which the compiler sets per angle).
- 2x2 class A: two-qubit count identical for k = 1..5; k = 5 cost equal to every k = 1..4 cost of the same reference.
- 2x2 class B: two-qubit count identical for k = 1..5; k = 5 cost equal to every k = 1..4 cost of the same reference.
- 2x3 frozen: two-qubit count identical for k = 1..5; k = 5 cost equal to all k = 1..4 costs for 0 of 11 references, largest difference 8.44 HQC (from the PhasedX count, which the compiler sets per angle).
- 2x3 class A: two-qubit count identical for k = 1..5; k = 5 cost equal to every k = 1..4 cost of the same reference.
- 2x3 class B: two-qubit count identical for k = 1..5; k = 5 cost equal to every k = 1..4 cost of the same reference.
- This is a syntax and cost check, not a physics result.

## 6. Problems and assumptions

1. 2x3 frozen: first pass had 3 ERROR jobs (B0_ref117_k5, B0_ref795_k5, B1_ref29_k5), all with error_detail `'Submission error: {"error":{"code":"INTEGRATION_TIMEOUT", "text": "Endpoint request timed out"}} (code: 1)'` -- a Quantinuum service timeout, not a compile error (the other circuits of the set, of the same size, passed). One retry of those circuits (`retry1/`, same Nexus project) completed all of them; `summary.json` merges both passes (each job carries `attempt` and, for the retried ones, `first_attempt`), `summary_first_pass.json` keeps the first pass, and the quota window runs from the first pass's `account_before.json` to the retry's `account_after.json`.
2. The output folder carries today's date, `quantinuum_sc_20261028`, the same date as the k = 1..4 runs; the k = 5 sets sit in their own subfolders (`*_k5`).
3. `cost_confidence` is -1.0 on every job (`qnexus` placeholder); the quotas endpoint prints a deprecation warning for qnexus 0.51.0.

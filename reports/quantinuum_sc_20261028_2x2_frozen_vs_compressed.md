# H2-2SC syntax check: frozen vs compressed 2x2 circuits (2026-10-28)

- Date: 2026-10-28. Git commit at report time: `bd2b8e5` (frozen run summary records `261222c`, compressed runs `bd2b8e5`; the compressed families were committed in `bd2b8e5`). Nothing committed by these runs.
- Request in force: the owner's words of 2026-10-28, "run the syntax checker on both frozen and compressed circuit A and B test on H2-sc first".
- Related report: `reports/quantinuum_sc_20261028_frozen_2x2.md` (the frozen run in detail, including the `max_cost` defect).
- Data (each directory: `summary.json`, `session.json`, `counts/`, `account_before.json`, `account_after.json`):
  - frozen: `data/hardware/quantinuum_sc_20261028/frozen_2x2/` (circuits `data/quantinuum/circuits_2x2/`, Nexus project `su2qc-skqd-2x2`)
  - classA: `2x4_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classA/` (circuits `2x4_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classA/`, Nexus project `su2qc-skqd-2x2-classA`)
  - classB: `2x4_compression_using_ai_v1/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classB/` (circuits `2x4_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classB/`, Nexus project `su2qc-skqd-2x2-classB`)
- Every number below is read from those files by a generator script, not typed by hand.

## Words used here

- **H2-2SC**: the *syntax checker* of Quantinuum's H2-2 trapped-ion computer: it compiles a circuit as the machine would and returns the cost the job would have, but does not run it, so every shot comes back as all zeros. Quantinuum documents it as free.
- **HQC** (H-System Quantum Credit): Quantinuum's billing unit. Package formula (`skqd.quantinuum_native.hqc_job`):
$$\mathrm{HQC} = 5 + C\,\frac{N_{1q} + 10\,N_{2q} + 5\,N_m}{5000},$$
  with $C$ shots, $N_{1q}$ PhasedX (one-qubit) gates, $N_{2q}$ ZZPhase/ZZMax (two-qubit) gates, $N_m$ initialisations plus measurements. "HQC per shot" below is the fraction $(N_{1q} + 10 N_{2q} + 5 N_m)/5000$.
- **Frozen** family: the checksummed circuits of `data/quantinuum/circuits_2x2` (one coarse time step $k$ of the 2x2 lattice, $k = 1..4$, from 7 reference states in two sectors B0/B1).
- **Class A** (compressed): the same 28 time-evolution circuits rebuilt to be *operator-exact* -- equal to the exact product of term exponentials on every valid lattice state (`index.json` field `contract`).
- **Class B** (compressed): *input-specific* -- exact only on its own reference state (up to a global phase); valid ONLY for "prepare own reference, one coarse step, measure" (`index.json` field `valid_use`).
- **Job**: one circuit with its shot count sent to a device. **Shot**: one run ending in one measured bit string.

## 1. What was asked

Run the free syntax checker H2-2SC on the frozen 2x2 circuits and on the compressed class A and class B 2x2 circuits (nothing else), and compare the three families: jobs completed / errors, all-zero results, checker cost vs package formula, per-circuit cost range at 200 shots, the 28-circuit total, HQC per shot, and the account quotas before/after.

## 2. What was done

1. For each family, an offline safety gate (no network): the job plan of `scripts/quantinuum_submit.py --syntax-check --device H2-2SC --all` carries the device string `H2-2SC` and nothing else; all 30 circuits (28 lattice + CAL_zeros, CAL_x0) load with their manifest sha256; every job's `QuantinuumConfig` builds. The live device list then showed H2-2SC with system_type "syntax checker" before each run.
2. Submission, one run per family, venv `~/.local/share/su2qc-quantinuum/venv`, shots = script default 200, `--max-cost` a whole number (frozen 141, compressed 150: works around the script's decimal-`max_cost` defect), then `--status` and `--retrieve`. The compressed runs succeeded at the first attempt; the frozen run needed its one retry.
3. Per-job status, error text and cost read with `qnx.jobs.status` / `qnx.jobs.cost_confidence`; quotas read with `qnx.quotas.get_all()` before and after each run.

- frozen: `scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x2 --all --max-cost 141 --project su2qc-skqd-2x2 (shots: script default 200)`
- classA: `scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits 2x4_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classA --all --max-cost 150 --project su2qc-skqd-2x2-classA (shots: script default 200)`
- classB: `scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits 2x4_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classB --all --max-cost 150 --project su2qc-skqd-2x2-classB (shots: script default 200)`

## 3. Comparison

| family | jobs completed / error | all-zero results | max $|\mathrm{SC}-\mathrm{formula}|$ (HQC) | per-circuit cost at 200 shots (HQC, 28 lattice) | 28-circuit total SC (HQC) | 28-circuit total formula (HQC) | HQC per shot (min to max; mean) |
|---|---|---|---|---|---|---|---|
| frozen | 30/30 / 0 | 30/30 | 1.4e-14 | 126.80 to 127.60 | 3561.12 | 3561.12 | 0.6090 to 0.6130; 0.6109 |
| classA | 30/30 / 0 | 30/30 | 2.8e-14 | 132.68 to 132.72 | 3716.00 | 3716.00 | 0.6384 to 0.6386; 0.6386 |
| classB | 30/30 / 0 | 30/30 | 1.4e-14 | 37.28 to 91.12 | 1949.28 | 1949.28 | 0.1614 to 0.4306; 0.3231 |

Ratios of the 28-circuit totals to the frozen family: classA 1.043, classB 0.547. All 30 jobs of every family (including the 2 calibration circuits, frozen 19.64 HQC, classA 19.64 HQC, classB 19.64 HQC) are in `summary.json` key `total_sc_cost_hqc`: frozen 3580.76, classA 3735.64, classB 1968.92 HQC.

Native gate counts of the 28 lattice circuits (from each manifest, `native_counts`), which set the cost:

| family | $N_{2q}$ (ZZ) | $N_{1q}$ (PhasedX) | $N_m$ (12 init + 12 meas) |
|---|---|---|---|
| frozen | 252 | 405 to 425 | 24 |
| classA | 245 | 622 to 623 | 24 |
| classB | 55 to 162 | 137 to 413 | 24 |

Per-circuit checker cost at 200 shots (HQC); job ids are in each `summary.json`:

| circuit | frozen | classA | classB |
|---|---|---|---|
| B0_ref06_k1 | 127.32 | 132.68 | 74.44 |
| B0_ref06_k2 | 127.40 | 132.68 | 74.44 |
| B0_ref06_k3 | 127.20 | 132.68 | 74.44 |
| B0_ref06_k4 | 126.88 | 132.68 | 74.44 |
| B0_ref43_k1 | 127.40 | 132.72 | 74.48 |
| B0_ref43_k2 | 127.44 | 132.72 | 74.48 |
| B0_ref43_k3 | 127.24 | 132.72 | 74.48 |
| B0_ref43_k4 | 126.92 | 132.72 | 74.48 |
| B0_ref30_k1 | 127.36 | 132.72 | 68.36 |
| B0_ref30_k2 | 127.52 | 132.72 | 68.36 |
| B0_ref30_k3 | 127.28 | 132.72 | 68.36 |
| B0_ref30_k4 | 127.04 | 132.72 | 68.36 |
| B0_ref21_k1 | 127.40 | 132.72 | 91.12 |
| B0_ref21_k2 | 127.56 | 132.72 | 91.12 |
| B0_ref21_k3 | 127.16 | 132.72 | 91.12 |
| B0_ref21_k4 | 127.04 | 132.72 | 91.12 |
| B0_ref17_k1 | 127.52 | 132.72 | 74.52 |
| B0_ref17_k2 | 127.60 | 132.72 | 74.52 |
| B0_ref17_k3 | 127.16 | 132.72 | 74.52 |
| B0_ref17_k4 | 126.96 | 132.72 | 74.52 |
| B1_ref14_k1 | 127.04 | 132.72 | 37.28 |
| B1_ref14_k2 | 126.96 | 132.72 | 37.28 |
| B1_ref14_k3 | 127.16 | 132.72 | 37.28 |
| B1_ref14_k4 | 126.80 | 132.72 | 37.28 |
| B1_ref07_k1 | 126.88 | 132.72 | 67.12 |
| B1_ref07_k2 | 126.92 | 132.72 | 67.12 |
| B1_ref07_k3 | 127.12 | 132.72 | 67.12 |
| B1_ref07_k4 | 126.84 | 132.72 | 67.12 |
| CAL_zeros | 9.80 | 9.80 | 9.80 |
| CAL_x0 | 9.84 | 9.84 | 9.84 |

## 4. Was anything charged?

`qnexus` 0.51.0 has no HQC-balance call; `qnx.quotas.get_all()` gives CPU-time and storage counters (account-wide, not per project). Snapshots around each run:

| family | before (UTC) | after (UTC) | simulation s before/after | compilation s before/after | database_usage MB before/after |
|---|---|---|---|---|---|
| frozen | 18:16:46 | 18:21:23 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.468 |
| classA | 18:29:07 | 18:34:17 | 0.000 / 0.000 | 0.000 / 0.000 | 0.468 / 1.190 |
| classB | 18:30:01 | 18:34:52 | 0.000 / 0.000 | 0.000 / 0.000 | 0.905 / 1.190 |

Simulation and compilation time stayed at zero through all three runs; only stored data grew (uploaded circuits and results). The classA "after" snapshot was taken after the classB run had also finished (the counters are account-wide), so the classA and classB windows overlap. Indirect evidence that the checker cost is an estimate and not a charge: the device list classes H2-2SC as "syntax checker", `qnexus`'s own `circuits.cost` uses H2-xSC as its "dedicated cost estimation device", and every shot of all 90 jobs came back all zeros. **Not established here:** a direct reading of the HQC balance; the Nexus web portal's usage page is where to read it.

## 5. What the result means

- All three families compile on H2-2 as submitted (`no_opt=True`, no implicit swaps): 90 of 90 jobs completed, no compile error text, all results all-zero as a syntax checker returns them.
- In every family Quantinuum's estimate equals the package formula to floating-point rounding, so the formula can be used for the shot budget of any of the three families without a further checker run.
- Class A costs slightly more than frozen (ratio 1.043): it has a few fewer two-qubit gates but many more PhasedX gates, and both enter the formula. Class B is the cheapest (ratio 0.547) because it drops two-qubit gates, but it is valid only for its own reference state and one coarse step (see its `valid_use`).
- This is a syntax and cost check only. It says nothing about the physics: whether the compressed circuits give the right samples is tested elsewhere, not by H2-2SC.

## 6. Problems and assumptions

1. The script's per-job `max_cost` defect (decimal value into an integer field) is still in `scripts/quantinuum_submit.py`; these runs worked around it with a whole-number `--max-cost`. Not edited.
2. Each family ran as 30 jobs (28 lattice + 2 calibration), as `--all` prescribes; the comparison uses the 28.
3. The frozen Nexus project `su2qc-skqd-2x2` also holds one circuit uploaded without a job (the frozen attempt 1).
4. Quota counters are account-wide; per-family before/after windows overlap (section 4).
5. `cost_confidence` is -1.0 on every job (`qnexus`'s placeholder when the service sends no value); the quotas endpoint prints a deprecation warning for qnexus 0.51.0 but still answers.

# qiskit-aer 0.15.1: GPU statevector with Kraus noise instructions samples a different distribution than the CPU statevector

Bundle assembled by `scripts/campaign33_aer_report.py` (prompts/33f R5) at commit 5763933, 2026-10-18 19:20:59 UTC.
Every number below is read from a committed JSON of the su2qc-skqd repository (listed per row) and stored in
`summary.json`; nothing is typed by hand.  Not filed yet: the owner reads it first.

## Claim

On qiskit-aer-gpu 0.15.1 (qiskit 1.4.3, numpy 2.5.3, python 3.12.14), `AerSimulator(method="statevector",
precision="double", device="GPU")` running a scheduled circuit on the 156-qubit device layout
(21 active qubits, 20 measured; 5659 cz,
8004 delays) with a `NoiseModel.from_backend`-style thermal-relaxation model that contains Kraus
instructions returns a measured distribution that (1) changes with `fusion_enable` and with `cuStateVec_enable` (it
should not: these are execution options), (2) differs from the CPU statevector of the same aer version and the same
model, on two independent CPU installations that agree with each other, and (3) is the only outlier: the same channel
written without Kraus instructions (`T2 := min(T2, T1)` on the qubits with $T_2 > T_1$: 4 of the
21 active qubits, [59, 69, 92, 95], so that Aer's
`thermal_relaxation_error` takes its reset-mixture branch; identical super-operators everywhere else) agrees with CPU
Kraus on both CPU installations.  The GPU Kraus arms all show a lower mean Hamming weight than the CPU, i.e. more
population in $|0\rangle$ (the direction of excess relaxation).  Observable: the mean Hamming weight $\bar w$ of the 20
measured bits (with its standard error from the per-shot spread) and the 20 per-clbit marginals.

## Every arm

| arm | job | source JSON | engine | representation | shots | $\bar w \pm$ se | s/shot | raw counts |
|---|---|---|---|---|---|---|---|---|
| `C2_KCHK_run1:kraus_gpu_cusv` | 59780907 | `validation/archive/C2_KCHK_job59780907.json` | GPU custatevec | kraus | 256 | 2.996 $\pm$ 0.235 | 1.92 | yes |
| `C2_KCHK_run1:kraus_gpu_native` | 59780907 | `validation/archive/C2_KCHK_job59780907.json` | GPU native | kraus | 256 | 3.566 $\pm$ 0.247 | 2.22 | yes |
| `C2_KCHK_run1:kraus_gpu_cusv_nofusion` | 59780907 | `validation/archive/C2_KCHK_job59780907.json` | GPU custatevec_nofusion | kraus | 128 | 1.141 $\pm$ 0.219 | 5.05 | yes |
| `C2_KCHK_run1:rm_gpu_cusv` | 59780907 | `validation/archive/C2_KCHK_job59780907.json` | GPU custatevec | rm | 512 | 7.434 $\pm$ 0.100 | 0.42 | yes |
| `C2_KCHK_run2:rm_gpu_cusv_anchor` | 59828887 | `validation/C2_KCHK.json` | GPU custatevec | rm | 128 | 7.062 $\pm$ 0.205 | 0.43 | yes |
| `C2_KCHK_run2:kraus_cpu` | 59828887 | `validation/C2_KCHK.json` | CPU statevector (separate process) (qiskit-aer-gpu wheel, CPU path) | kraus | 7 | 8.429 $\pm$ 0.782 | 213.68 | yes |
| `C2_KCHK_run2:rm_cpu` | 59828887 | `validation/C2_KCHK.json` | CPU statevector (separate process) (qiskit-aer-gpu wheel, CPU path) | rm | 12 | 6.667 $\pm$ 0.414 | 93.90 | yes |
| `C2_CAL_run3:kraus` | 59736871 | `validation/C2_CAL.json` | GPU custatevec | kraus | 640 | 2.398 $\pm$ 0.136 | 1.84 | no |
| `C2_CAL_run3:rm` | 59736871 | `validation/C2_CAL.json` | GPU custatevec | rm | 1024 | 7.420 $\pm$ 0.077 | 0.35 | no |
| `C2_CAL_run3:pta` | 59736871 | `validation/C2_CAL.json` | GPU custatevec | pta | 512 | 9.957 $\pm$ 0.102 | 0.29 | no |
| `laptop:cpu_kraus` | laptop | `data/campaign33/c33c_diag/summary.json` | CPU statevector, laptop (qiskit-aer CPU wheel) | kraus | 67 | 7.463 $\pm$ 0.269 | 236.42 | yes |
| `laptop:cpu_rm` | laptop | `data/campaign33/c33c_diag/summary.json` | CPU statevector, laptop (qiskit-aer CPU wheel) | rm | 78 | 7.269 $\pm$ 0.274 | 90.40 | yes |

## Statistics

$z_w = (\bar w_A - \bar w_B)/\sqrt{\mathrm{se}_A^2 + \mathrm{se}_B^2}$; per clbit, Fisher's exact test on the $2\times2$ table
(two-sided, `scipy.stats.fisher_exact`), flagged at $P(|Z|>3) = 0.0027$ per test (Bonferroni over 20 clbits: 0.054).
Marginal counts are recovered exactly as $p_k N$ from the stored structures.

**Exhibit 1_gpu_vs_gpu (same channel, fusion on/off and kernel choice)**

| arm A | arm B | $\bar w_A$ | $\bar w_B$ | $z_w$ | Fisher min $p$ (clbit) | clbits with $p<0.0027$ |
|---|---|---|---|---|---|---|
| `C2_KCHK_run1:kraus_gpu_cusv_nofusion` | `C2_KCHK_run1:kraus_gpu_cusv` | 1.141 | 2.996 | -5.78 | 1.71e-05 (4) | [4, 9, 10, 12, 13, 15, 18] |
| `C2_KCHK_run1:kraus_gpu_native` | `C2_KCHK_run1:kraus_gpu_cusv` | 3.566 | 2.996 | +1.67 | 0.0136 (14) | [] |
| `C2_KCHK_run1:kraus_gpu_native` | `C2_KCHK_run1:kraus_gpu_cusv_nofusion` | 3.566 | 1.141 | +7.36 | 1.22e-06 (10) | [0, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 19] |

**Exhibit 2_gpu_kraus_vs_cpu_kraus (identical software versions)**

| arm A | arm B | $\bar w_A$ | $\bar w_B$ | $z_w$ | Fisher min $p$ (clbit) | clbits with $p<0.0027$ |
|---|---|---|---|---|---|---|
| `C2_KCHK_run1:kraus_gpu_cusv` | `C2_KCHK_run2:kraus_cpu` | 2.996 | 8.429 | -6.65 | 5.49e-05 (8) | [8, 9, 17] |
| `C2_KCHK_run1:kraus_gpu_cusv` | `laptop:cpu_kraus` | 2.996 | 7.463 | -12.49 | 2.88e-11 (16) | [4, 6, 7, 8, 9, 11, 12, 13, 14, 16, 18, 19] |
| `C2_CAL_run3:kraus` | `laptop:cpu_kraus` | 2.398 | 7.463 | -16.79 | 4.64e-14 (13) | [0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19] |
| `C2_KCHK_run2:kraus_cpu` | `laptop:cpu_kraus` | 8.429 | 7.463 | +1.17 | 0.0103 (8) | [] |

**Exhibit 3_same_channel_without_kraus_instructions (RM) vs CPU Kraus**

| arm A | arm B | $\bar w_A$ | $\bar w_B$ | $z_w$ | Fisher min $p$ (clbit) | clbits with $p<0.0027$ |
|---|---|---|---|---|---|---|
| `C2_KCHK_run1:rm_gpu_cusv` | `C2_KCHK_run2:kraus_cpu` | 7.434 | 8.429 | -1.26 | 0.0453 (8) | [] |
| `C2_KCHK_run1:rm_gpu_cusv` | `laptop:cpu_kraus` | 7.434 | 7.463 | -0.10 | 0.0189 (16) | [] |
| `C2_KCHK_run1:rm_gpu_cusv` | `C2_KCHK_run2:rm_cpu` | 7.434 | 6.667 | +1.80 | 0.0745 (19) | [] |
| `C2_KCHK_run1:rm_gpu_cusv` | `laptop:cpu_rm` | 7.434 | 7.269 | +0.56 | 0.0602 (11) | [] |
| `C2_KCHK_run2:rm_gpu_cusv_anchor` | `C2_KCHK_run1:rm_gpu_cusv` | 7.062 | 7.434 | -1.63 | 0.0582 (19) | [] |

## Files

- `circuit_IBM-T0_B0_ref117_k1.qpy.gz` (QPY version 13, sha256 `55d36665b79eb9c50b122032bcd1c5417a9b1970191bcc2a6654e99fa8150ea7`); `circuit.qasm3`:
  present, sha256 `ca4370e31a0508549f184dd93ca8b4fe65803fcaa5797a30628f0727457622a9`.
- `noise_model_kraus.json.gz`, `noise_model_rm.json.gz`: `NoiseModel.to_dict(serializable=True)`, gzipped (13-17 MB each as plain JSON) (aer 0.15.1);
  Kraus instructions in `to_dict`: 6580 (Kraus model), 0 (RM model);
  inserted by the delay pass into this circuit: 445 / 0 of
  8004 sites.  `NoiseModel.from_dict` applied directly to this serializable export fails in
  aer 0.15.1 (`ValueError: too many values to unpack (expected 2)`: complex entries are
  written as `[re, im]` and not read back); `reproduce.py` decodes them first.  Its loader rebuilds the models the CI
  built: 664 gate errors, super-operator max difference
  3.3e-15 (Kraus) /
  3.3e-15 (RM), readout and delay pass identical: check
  True / True.
- `relaxation_pass.json`: the `RelaxationNoisePass` on `Delay` (per-qubit $T_1$, $T_2$, excited-state populations, `dt`),
  which `to_dict` does not carry; RM differs from Kraus on qubits [0, 1, 3, 13, 14, 21, 22, 28, 31, 32, 33, 34, 35, 47, 57, 59, 66, 69, 82, 92, 95, 99, 104, 105, 106, 107, 112, 116, 117, 121, 122, 125, 127, 130, 132, 135, 136, 140, 141, 144, 149, 150] of the
  record (active in this circuit: [59, 69, 92, 95]).
- `reproduce.py`: self-contained (qiskit + qiskit-aer only): loads the QPY, rebuilds both models from the dictionaries,
  appends the relaxation pass, runs the CPU arm and the GPU arms (cuStateVec on/off, fusion on/off) with the recorded
  seeds and prints $\bar w$ per arm.  `python reproduce.py --help`.
- `counts/`: the raw counts of every arm that stored them (`.json` with chunk seeds and shots, `.npz` with the same rows).
- `logs/`: the CI job logs, the C2_KCHK JSONs (run 1 archive, run 2), the laptop CPU segments and summary, the 1-qubit
  and delay-site checks, the release-note reading.
- `environment/`: `pip freeze` of the laptop twin; `ci_environment.json` with the versions the CI jobs recorded and what
  is missing (below).

## Versions

CI (both jobs, from the JSONs): {"qiskit": "1.4.3", "qiskit_aer": "0.15.1", "numpy": "2.5.3", "scipy": "1.18.1", "threadpoolctl": "3.7.0", "python": "3.12.14"}; CPU arm wheel on the CI: {'distributions': ['qiskit-aer-gpu'], 'versions': {'qiskit-aer-gpu': '0.15.1'}}.
Laptop twin: {"python": "3.12.14", "qiskit": "1.4.3", "qiskit_aer": "0.15.1", "numpy": "2.5.3"} (CPU wheel `qiskit-aer`).
**Not recorded by the jobs (the owner adds them before filing):** the CUDA, cuStateVec and driver versions and the GPU
model; a `pip freeze` of the CI env.

## Small-scale checks (negative results)

- `data/campaign33/c33c_diag/oneq_q53_qiskit1.4.3.json`: CPU, qiskit 1.4.3 / aer 0.15.1: x, delay(400 us), measure on physical qubit 53 (T1 292.7 us), 20000 shots: P(1) Kraus 0.2510 (z -1.32), RM 0.2614 (z +2.07) vs e^(-t/T1) = 0.2550
- `data/campaign33/c33c_diag/oneq_q53_qiskit2.5.2.json`: CPU, qiskit 2.5.2 / aer 0.17.2: x, delay(400 us), measure on physical qubit 53 (T1 292.7 us), 20000 shots: P(1) Kraus 0.2510 (z -1.32), RM 0.2614 (z +2.07) vs e^(-t/T1) = 0.2550
- `data/campaign33/c33c_diag/delays_q53_qiskit1.4.3.json`: qiskit 1.4.3 / aer 0.15.1: the Kraus and RM models attach 55 / 55 delay errors to physical qubit 53 of this circuit (407.3 us in total); super-operator max |difference| 0.0
- `data/campaign33/c33c_diag/delays_q53_qiskit2.5.2.json`: qiskit 2.5.2 / aer 0.17.2: the Kraus and RM models attach 55 / 55 delay errors to physical qubit 53 of this circuit (407.3 us in total); super-operator max |difference| 0.0
- The 2- and 8-qubit statevector-vs-density-matrix checks mentioned in prompts/33d R4 have no committed record in
  this repository; they are not quoted here.  No small-scale **GPU** check was run (the CI runs one job at a time).

## Reproducer smoke test (laptop CPU)

`smoke/reproduce_laptop_cpu_2shots.json` (`python reproduce.py --arms kraus_cpu rm_cpu kraus_gpu_cusv kraus_gpu_native kraus_gpu_cusv_nofusion rm_gpu_cusv --shots 2 --threads 10 --out reproduce_laptop_cpu_2shots.json`; qiskit 1.4.3, aer 0.15.1, laptop CPU, Aer devices ['CPU']):

- `kraus_cpu`: 2 shots, $\bar w$ = 8.000 $\pm$ 2.000, 144.7 s/shot; seeds of `counts/C2_KCHK_run2__kraus_cpu.json`: counts identical to the recorded chunks in 2 of 2 calls
- `rm_cpu`: 2 shots, $\bar w$ = 5.500 $\pm$ 1.500, 64.4 s/shot; seeds of `counts/C2_KCHK_run2__rm_cpu.json`: counts identical to the recorded chunks in 2 of 2 calls
- `kraus_gpu_cusv`: skipped (no GPU)
- `kraus_gpu_native`: skipped (no GPU)
- `kraus_gpu_cusv_nofusion`: skipped (no GPU)
- `rm_gpu_cusv`: skipped (no GPU)

The CPU arms recorded on the CI (job 59828887, qiskit-aer-gpu wheel, CPU path) are reproduced bit for bit by `reproduce.py` from the bundle files alone on a different installation, which also checks that the exported models and the relaxation pass are the ones the CI ran.

## Upstream status

Release notes read 2026-10-13 (UTC-6 afternoon), by the executor on branch c33c (https://api.github.com/repos/Qiskit/qiskit-aer/releases?per_page=30, https://qiskit.github.io/qiskit-aer/release_notes.html, https://api.github.com/search/issues?q=repo:Qiskit/qiskit-aer+kraus+custatevec): No release note of 0.16.x or 0.17.x names a fix to Kraus channels, non-unitary noise sampling or the cuStateVec execution path; 0.16-0.17.2 are compatibility and build releases. A newer qiskit-aer-gpu is therefore not expected to change the C2_CAL GPU Kraus result, and nothing upstream documents the defect: if C2_KCHK confirms it (K1), it is a new report for Qiskit/qiskit-aer (prompts/33d R4).
Re-checked 2026-10-18 (GitHub releases API; 0.17.2 published 2025-09-17): latest release 0.17.2 -- **no fix found**.

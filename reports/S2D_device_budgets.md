# Gate S2D — device-resolved budgets for the exact circuits (2x2 Heron, 2x3 all-to-all RZZ)

**Status: FAIL** — `scripts/gate_S2D.py`, optimization level 3,
seed 7.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 89102d2, 2026-09-16 07:02:12 MDT.  Runtime 213 s.

Owner decision of 2026-09-16 (prompts/12, options (b) + (c) of prompts/11): the circuit family stays the
**exact structured circuits of gate S2** (`exact structured circuits, CircuitFactory default (validation/S2.json)`); 2x2 runs on a Heron-class device
(heavy-hex, native CZ) and 2x3 on an all-to-all trapped-ion device with native RZZ.  The fixed CZ numbers of
manual Step 4.3 (250 / 500) are replaced by the physical condition of Step 4.4 they were derived from:
the clean-shot fraction f of one coarse-step circuit must be >= 0.1 (worst circuit >= 0.05),
the condition under which gate S1 established recall >= 0.9 with the production shot budget.
Gate S2 keeps its recorded FAIL; `validation/S2.json` is untouched.

## Declared inputs (NOT measurements)

| symbol | value | what it is |
|---|---|---|
| eps2 | 0.001 | two-qubit (RZZ) error of the all-to-all device — vendor-class specification |
| eps1 | 0.0001 | one-qubit error of the all-to-all device — vendor-class specification |
| eps_ro | 0.002 | readout error per qubit of the all-to-all device — vendor-class specification |
| p | 0.001 | ideal probability of the configuration that must be seen (gate S1's 99.9 % support threshold) |
| k | 3 | minimum number of times it must be seen (manual Step 4.4) |
| confidence | 0.95 | probability with which that must happen (manual Step 4.4) |
| lambda* | 6.295794 | smallest Poisson mean with P(X >= k) >= confidence (skqd.skqd.poisson_lambda_star) |
| yield model | y = 0.82 f (manual Step 4.4) | accepted-shot yield of manual Step 4.4 |

The 2x2/Heron numbers below are **not** in this list: they are computed from the per-edge CZ errors and
per-qubit readout errors of the calibration snapshots qiskit_ibm_runtime.fake_provider FakeFez (Heron r2), FakeTorino (Heron r1).

## 2a. 2x2 on a Heron-class device (12 qubits, 28 circuits = references x k = 1..4)

`transpile(qc, backend=<snapshot>, optimization_level=3, seed_transpiler=7)`; f is the
product of (1 - error) over the CZ gates actually executed on their physical edges and over the readout of
the measured physical qubits.

| snapshot | device qubits | circuits | CZ mean | CZ min | CZ max | f mean | f worst | f best | mean error of the used edges | snapshot median CZ error | mean readout error of the patch | f mean incl. 1q errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FakeFez | 156 | 28 | 663 | 663.0 | 663.0 | 0.1248 | 0.1166 | 0.1261 | 3.05e-03 | 3.90e-03 | 7.46e-03 | 0.0967 |
| FakeTorino | 133 | 28 | 636 | 636.0 | 639.0 | 0.0735 | 0.0569 | 0.0763 | 4.08e-03 | 4.19e-03 | 3.51e-02 | 0.0537 |

Best snapshot: **FakeFez** (mean f 0.1248).  The last column is a *diagnostic*, not the
criterion: the criterion's f follows manual Step 4.4 and counts CZ and readout only, while the transpiled
circuits also contain 2026 one-qubit gates on average, whose snapshot errors reduce f further.

### The patch the transpiler chose

| snapshot | distinct patches over the circuit set | physical qubits (first circuit) | mean error over the used edges | same, weighted by CZ count | snapshot median CZ error | mean readout error of the patch | snapshot median readout error |
|---|---|---|---|---|---|---|---|
| FakeFez | 2 | [117, 122, 123, 124, 125, 136, 141, 142, 143, 144, 145, 146] | 3.047e-03 | 3.000e-03 | 3.903e-03 | 7.455e-03 | 7.568e-03 |
| FakeTorino | 2 | [9, 10, 11, 12, 13, 14, 18, 29, 30, 31, 32, 33] | 4.079e-03 | 3.412e-03 | 4.190e-03 | 3.508e-02 | 2.295e-02 |

Reproduction check: the k = 1 coarse step routed on the **ideal** heavy-hex d = 3 coupling map gives
618 CZ, against 618 in `validation/S2.json`.  The real
snapshots cost 663 CZ on average because their heavy-hex patch is not the ideal d = 3 tile.

## 2b. 2x3 on the all-to-all trapped-ion device (20 qubits, 44 circuits)

`transpile(qc, basis_gates=['rz','rx','ry','rzz'], coupling_map=None, optimization_level=3)`.

| circuit set | circuits | RZZ mean | 1q mean | depth mean | f mean | f worst | f factor: 2q (k=1) | f factor: 1q (k=1) | f factor: readout (k=1) | f mean if rz are virtual |
|---|---|---|---|---|---|---|---|---|---|---|
| 2x3 coarse step, RZZ basis, all-to-all | 44 | 2158 | 7310 | 5655 | 0.0534 | 0.0532 | 0.1154 | 0.4797 | 0.9608 | 0.0817 |

The last column is a *diagnostic*: on trapped-ion hardware the 4255 rz of the k = 1 circuit (of 7346 one-qubit gates) are frame
changes with no physical error; the criterion's f charges eps1 to every one-qubit gate, as declared.
Reproduction check: the same k = 1 circuit in the CZ basis all-to-all gives 2164 CZ,
against 2164 in `validation/S2.json`.
Two-qubit error that would be needed for mean f = 0.1 at these counts (derived, holding eps1 and eps_ro):
**7.09e-04** instead of the declared 1e-03.

## 3. Shot budget (manual Step 4.4 / eq. 5, `skqd.skqd.shot_rule`)

N_circuit = ceil(lambda* / (p y)) with y = 0.82 f; N_sector = N_circuit x (number of circuits).

| circuit set / device | sector | circuits | mean f | yield y = 0.82 f | N_circuit | N_sector | manual Step 9.2 | within budget |
|---|---|---|---|---|---|---|---|---|
| 2x3 / all-to-all | B=0 | 32 | 0.0533 | 0.0437 | 143921 | 4.605e+06 | 2e+05 | NO |
| 2x3 / all-to-all | B=1 | 12 | 0.0535 | 0.0439 | 143508 | 1.722e+06 | 2e+05 | NO |
| 2x2 / Heron FakeFez | B=0 | 20 | 0.1261 | 0.1034 | 60872 | 1.217e+06 | 2e+05 | NO |
| 2x2 / Heron FakeFez | B=1 | 8 | 0.1214 | 0.0995 | 63270 | 5.062e+05 | 2e+05 | NO |
| manual design point f = 0.2 (manual eq. 5) | any sector | 44 | 0.2000 | 0.1640 | 38389 | 1.689e+06 | 2e+05 | NO |

The last block is the manual's own design point (f = 0.2): eq. (5) already asks for
38389 shots per circuit there, i.e.
1.69e+06 per sector over
44 circuits — so the 2x10^5 per-sector quota of Step 9.2 and eq. (5) at
p = 1e-03 are inconsistent *in the manual itself*, independently of any device.  Neither p nor the
confidence was lowered here.

### Device time (ILLUSTRATIVE — the throughputs are round numbers, not device specifications)

device time [min] = N_sector / throughput [shots per minute]

| throughput (shots/min) | B=0 (min) | B=1 (min) |
|---|---|---|
| 100 | 46055 | 17221 |
| 300 | 15352 | 5740 |
| 1000 | 4606 | 1722 |

## 5. Cost of the 2x3 noisy simulation (fixes the S3 desktop job)

10 noisy shots of one 2x3 coarse-step circuit (2158 RZZ,
7346 one-qubit gates, 20 qubits) took 32 s on this
laptop CPU: **3.20 s per shot** (AerSimulator(method='statevector', CPU), depolarizing model of the declared inputs applied to rzz, rz, rx, ry plus readout flips).  At the shot budget above, one
sector of the S3 device-model simulation is
| sector | hours on this laptop CPU (measured cost x N_sector) |
|---|---|
| B=0 | 4.092e+03 |
| B=1 | 1.530e+03 |
single-shot trajectory sampling on this laptop CPU; the intended executor is Aer GPU with batched shots on the RTX 3070 desktop (the GTX 1060 Max-Q of this laptop is compute capability 6.1 and no compatible qiskit-aer-gpu wheel exists for qiskit 2.5.2, see prompts/LOG.md).

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| 2x2/Heron (FakeFez snapshot): mean clean-shot fraction f over the 28-circuit set | 0.1248 | >= 0.1 | PASS |
| 2x2/Heron (FakeFez snapshot): worst-circuit f | 0.1166 | >= 0.05 | PASS |
| 2x3/all-to-all at the declared eps2 = 0.001: mean f over the 44-circuit set | 0.0534 | >= 0.1 | FAIL |
| 2x3/all-to-all: worst-circuit f | 0.0532 | >= 0.05 | PASS |
| 2x2: CZ of the k = 1 coarse step routed on the ideal heavy-hex d=3 map | 618 | = 618 (validation/S2.json) | PASS |
| 2x3: CZ of the k = 1 coarse step, all-to-all CZ basis | 2164 | = 2164 (validation/S2.json) | PASS |
| 2x3: shots per sector from the shot rule (worst sector) | 4605472 | <= 2e+05 (manual Step 9.2) | FAIL |
| pytest -q tests | 25 passed in 86.90s (0:01:26) | all pass | PASS |

## Scope

Every number above is computed by `scripts/gate_S2D.py` and stored in `validation/S2D.json`; the reports and
`proposal/amendment_01_devices_and_budgets.md` are generated from that file.  The 2x2 numbers use two public
calibration snapshots, not a reservation on a specific device; the 2x3 numbers use declared vendor-class
inputs.  Nothing here changes the circuit family, `validation/S2.json`, or any preregistered threshold.

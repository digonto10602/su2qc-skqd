# Gate H0_diag_dryrun — the H0 diagnostic session on AerSimulator.from_backend(FakeFez) [local testing mode]

**Status: FAIL** — `scripts/gate_H0_diag.py --prereg data/hardware/H0_diag_dryrun/idle_model_fakefez.json --out H0_diag_dryrun`.
Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 9cfe3ec, 2026-09-22 14:16:46 MDT.  Runtime 1 s.  Total QPU usage of the session
**0.0 s** (cap 40 s).

Preregistration `data/hardware/H0_diag_dryrun/idle_model_fakefez.json` (written 2026-09-22 14:05:07 MDT at commit `9cfe3ec`) on the
calibration fingerprint **`d4ea676171b6a08487fab79c78bcb9780b31d34d7842f49fc3e516a42498c1fb`**
(fake_fez, 2025-02-26T15:16:25-05:00).  The decision rule and
both predictions were fixed before any of these counts existed.

## 1. The decision

| | value |
|---|---|
| J1 accepted N1 of 2000 | **328** |
| preregistered H_A (idle relaxation, options off) | 23.2 +- 4.8 |
| preregistered H_B (the options were the cause) | 374.5 +- 17.4 |
| garbage floor (a = 0.00928) | 18.6 |
| rule | N1 = accepted shots of the canary pub of J1: N1 <= 100 rejects H_B, N1 >= 250 confirms H_B, 100 < N1 < 250 is inconclusive (prompts/19 D5 C3) |
| **outcome** | **H_B confirmed (the sampler options were the cause)** |

Ratios between the cells of the factorial: only J1 was run.

## 2. The four canary pubs

| job | DD | twirling | shots | accepted | yield | f from yield | distinct strings | distinct states | reference string seen | rejections | mixture c | chi-square (2 dof) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J1 | XY4 | on (active-accum) | 2000 | 328 | 0.1640 | 0.1908 | 939 | 25 | 178 | {'flag': 994, 'link': 558, 'sector': 120, 'unknown': 0} | 0.1562 | 601.21 |

## 3. Jobs

| job | job id(s) | status | usage (s) | calibration fingerprint | prereg match |
|---|---|---|---|---|---|
| J1 | 8271cfd3-1cad-4de2-a069-72514383b80a | DONE | 0.0 | None | None |

## 4. Windowed T1 test (`diag_patch1_t1w`)

| job | physical qubit | raw P(1) | P(1) readout-corrected | P(1) predicted | T1 measured (us) | T1 record (us) | rate ratio | in band |
|---|---|---|---|---|---|---|---|---|
| J1 | 117 | 0.7610 | 0.7652 | 0.7822 | 162.7 | 177.1 | 1.09 | yes |
| J1 | 122 | 0.7410 | 0.7435 | 0.7386 | 146.9 | 143.6 | 0.98 | yes |
| J1 | 123 | 0.7445 | 0.7470 | 0.7558 | 149.2 | 155.4 | 1.04 | yes |
| J1 | 124 | 0.6435 | 0.6448 | 0.6490 | 99.2 | 100.7 | 1.02 | yes |
| J1 | 125 | 0.7810 | 0.7867 | 0.7691 | 181.4 | 165.8 | 0.91 | yes |
| J1 | 136 | 0.6300 | 0.6303 | 0.6344 | 94.3 | 95.6 | 1.01 | yes |
| J1 | 141 | 0.7645 | 0.7695 | 0.7721 | 166.1 | 168.2 | 1.01 | yes |
| J1 | 142 | 0.7655 | 0.7699 | 0.7694 | 166.5 | 166.0 | 1.00 | yes |
| J1 | 143 | 0.7310 | 0.7330 | 0.7480 | 140.1 | 149.9 | 1.07 | yes |
| J1 | 144 | 0.6305 | 0.6325 | 0.6407 | 95.0 | 97.8 | 1.03 | yes |
| J1 | 145 | 0.7235 | 0.7296 | 0.7517 | 138.0 | 152.5 | 1.10 | yes |
| J1 | 146 | 0.5020 | 0.5015 | 0.5015 | 63.1 | 63.1 | 1.00 | yes |

## 5. Windowed Ramsey test (`diag_patch1_ramw`)

| job | physical qubit | raw P(0) | P(0) readout-corrected | P(0) bound from the record | T2* measured (us) | T2* upper bound (us) | T2 record (us) | under the bound |
|---|---|---|---|---|---|---|---|---|
| J1 | 117 | 0.8130 | 0.8181 | 0.8132 | 96.2 | 117.0 | 93.0 | yes |
| J1 | 122 | 0.7740 | 0.7785 | 0.7721 | 74.4 | 89.2 | 71.5 | yes |
| J1 | 123 | 0.8375 | 0.8421 | 0.8407 | 114.7 | 140.9 | 113.4 | yes |
| J1 | 124 | 0.8210 | 0.8232 | 0.8271 | 99.7 | 121.1 | 102.6 | yes |
| J1 | 125 | 0.7055 | 0.7110 | 0.7064 | 50.4 | 60.1 | 49.2 | yes |
| J1 | 136 | 0.8095 | 0.8136 | 0.8141 | 93.3 | 113.1 | 93.6 | yes |
| J1 | 141 | 0.8020 | 0.8045 | 0.8107 | 87.7 | 105.9 | 91.4 | yes |
| J1 | 142 | 0.8745 | 0.8801 | 0.8702 | 158.8 | 201.1 | 144.8 | yes |
| J1 | 143 | 0.8425 | 0.8448 | 0.8505 | 117.1 | 143.8 | 122.5 | yes |
| J1 | 144 | 0.8285 | 0.8373 | 0.8386 | 110.5 | 136.1 | 111.7 | yes |
| J1 | 145 | 0.8390 | 0.8488 | 0.8646 | 120.9 | 150.2 | 137.8 | yes |
| J1 | 146 | 0.5680 | 0.5693 | 0.5796 | 22.0 | 27.5 | 23.7 | yes |

## 6. Idle-aware post-diction with the measured coherence times

| job | S_T1 | S_T2 | f predicted | yield predicted | yield measured | measured/predicted clean yield | within a factor 3 |
|---|---|---|---|---|---|---|---|
| J1 | 0.917 | 2.930 | 2.694e-03 | 0.01146 | 0.16400 | 70.833 | no |

## 7. Readout

Smallest confusion diagonal of patch 1 in J1: 0.9860
(criterion >= 0.9).
Qubit 123: measured error 0.00600 against the record 0.00635, ratio 0.95 (information, not a criterion).

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| C1 every job DONE with usage recorded, each <= 30 s, total <= 40 s (1 job directory/ies: J1 0.0 s) | 0 | per job <= 30, total <= 40 | PASS |
| C2 decoder round trip over the accepted strings of 1 canary pub(s) (25 distinct strings) | 0 mismatch(es) | 0 | PASS |
| C3 decisive J1 count: N1 = 328 of 2000 against the preregistered 23 (H_A) and 374 (H_B) -- H_B confirmed (the sampler options were the cause) | 328 | <= 100 or >= 250 | PASS |
| C4a t1w (J1): per-qubit decay rate 1/T1_measured within [0.5, 2.0] x 1/T1_record | 12 of 12 | >= 10 of 12 | PASS |
| C4b ramw (J1): P(0) <= (1 + e^-T/T2_record)/2 + 3 sigma_binomial | 12 of 12 | >= 10 of 12 | PASS |
| C5 J1: the idle-aware post-diction with the measured T1/T2 predicts a clean yield 0.00218 against the measured 0.15472 | 70.833 | within a factor 3 | FAIL |
| C6 readout confusion of patch 1 at 2000 shots (J1): smallest diagonal element | 0.986 | >= 0.9 | PASS |

Every number above is computed by `scripts/gate_H0_diag.py` from the raw counts of the job directories
and from `data/hardware/H0_diag_dryrun/idle_model_fakefez.json`, and is stored in `validation/H0_diag_dryrun.json`.  The counts files are never modified.

# Device survey for the 2x2 H0 patch (prompts/20 part E)

`scripts/h0_device_survey.py`, 2026-09-30 14:46:41 MDT.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit 6180c6a, 2026-09-30 14:47:28 MDT.
**0 QPU seconds**: a calibration record is target / properties / status
metadata, and an offline snapshot needs no account at all.  Runtime 375 s.
Every number below is in `data/H0_device_survey_20260922.json` or in the per-device records under
`data/hardware/device_survey_20260922`.  The patch searches are `scripts/h0_patch_select.py` run unmodified; each
device for which it produced a result has its own JSON and report, and the `method` field of
every entry says which route was taken.

Requested devices: FakeFez, FakeMarrakesh, FakeKingston.

## Devices that could not be surveyed

| device | attempted | reason |
|---|---|---|
| ibm_fez | no | the live target could not be read in this session: outbound access to the IBM Quantum service is denied in this sandbox, so no live full-device record was written.  The offline fake-provider snapshot of the same device family was surveyed instead; part E1's li |
| ibm_marrakesh | no | the live target could not be read in this session: outbound access to the IBM Quantum service is denied in this sandbox, so no live full-device record was written.  The offline fake-provider snapshot of the same device family was surveyed instead; part E1's li |
| ibm_kingston | no | the live target could not be read in this session: outbound access to the IBM Quantum service is denied in this sandbox, so no live full-device record was written.  The offline fake-provider snapshot of the same device family was surveyed instead; part E1's li |

## 1. T2 geography (part E2)

| device | record | calibration | qubits | edges | T2 p10 (us) | T2 p25 (us) | T2 p50 (us) | T2 p75 (us) | T2 p90 (us) | T2 >= 50 us | T2 >= 100 us | T2 >= 150 us | missing errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fake_fez | offline fake-provider snapshot | 2025-02-26T15:16:25-05:00 | 156 | 176 | 22.6 | 48.1 | 88.0 | 122.9 | 158.0 | 73 % | 41 % | 12 % | 0 |
| fake_marrakesh | offline fake-provider snapshot | 2025-02-26T14:52:45-05:00 | 156 | 176 | 31.7 | 68.9 | 118.4 | 205.6 | 301.0 | 81 % | 59 % | 41 % | 0 |
| fake_kingston | offline fake-provider snapshot | 2026-04-15T09:15:15+02:00 | 156 | 176 | 43.6 | 79.9 | 144.2 | 262.9 | 336.8 | 89 % | 67 % | 46 % | 0 |

## 2. Where a twelve-qubit tree can live (part E2)

Connected components of the subgraph with readout error <=
3 %, CZ error <=
1 % and T2 above the stated
floor.  The frozen coarse step needs a connected 12-qubit region, so the last column is the
one that decides whether a floor is reachable at all.

| device | T2 floor (us) | good qubits | components | four largest | components >= 12 | four largest, readout filter only | >= 12, readout filter only |
|---|---|---|---|---|---|---|---|
| fake_fez | 40 | 116 | 29 | [25, 17, 16, 10] | 3 | [41, 33, 19, 4] | 3 |
| fake_fez | 60 | 94 | 37 | [17, 10, 7, 6] | 1 | [21, 11, 11, 11] | 1 |
| fake_fez | 80 | 76 | 36 | [13, 8, 6, 5] | 1 | [17, 8, 7, 5] | 1 |
| fake_fez | 100 | 58 | 36 | [5, 5, 4, 4] | 0 | [6, 5, 4, 4] | 0 |
| fake_fez | 120 | 38 | 27 | [5, 4, 3, 2] | 0 | [5, 4, 4, 2] | 0 |
| fake_fez | 150 | 16 | 11 | [3, 3, 2, 1] | 0 | [3, 3, 2, 1] | 0 |
| fake_marrakesh | 40 | 108 | 28 | [24, 19, 10, 8] | 2 | [38, 24, 10, 8] | 2 |
| fake_marrakesh | 60 | 98 | 28 | [23, 19, 7, 7] | 2 | [31, 23, 7, 7] | 2 |
| fake_marrakesh | 80 | 89 | 34 | [16, 7, 6, 6] | 1 | [16, 13, 8, 7] | 2 |
| fake_marrakesh | 100 | 77 | 35 | [15, 5, 4, 4] | 1 | [15, 7, 5, 4] | 1 |
| fake_marrakesh | 120 | 62 | 34 | [7, 6, 4, 4] | 0 | [7, 6, 5, 4] | 0 |
| fake_marrakesh | 150 | 52 | 31 | [6, 5, 3, 3] | 0 | [6, 5, 3, 3] | 0 |
| fake_kingston | 40 | 114 | 19 | [28, 20, 12, 11] | 3 | [29, 20, 12, 11] | 3 |
| fake_kingston | 60 | 104 | 23 | [17, 16, 11, 10] | 2 | [17, 17, 11, 10] | 2 |
| fake_kingston | 80 | 93 | 27 | [13, 11, 10, 7] | 1 | [13, 11, 10, 7] | 1 |
| fake_kingston | 100 | 82 | 32 | [12, 9, 5, 4] | 1 | [12, 9, 5, 4] | 1 |
| fake_kingston | 120 | 74 | 32 | [12, 5, 5, 4] | 1 | [12, 5, 5, 4] | 1 |
| fake_kingston | 150 | 52 | 34 | [4, 4, 4, 3] | 0 | [4, 4, 4, 3] | 0 |

The last two columns drop the CZ ceiling and keep only the readout and T2 filters: that is the
variant P12 of `reports/H0_replan_planner_analysis_20260922.md` reported, and reproducing it
([41, 33, 19] at 40 us on the FakeFez snapshot, [21, 11, 11, 11] at 60, [17, 8, 7] at 80,
[6, 5, 4] at 100, [5, 4, 4] at 120, [3, 3, 2] at 150) is the check that the search is the same
one.  The columns before them are the prompt's stricter criteria.

## 3. The winning patch per device (part E3)

The exhaustive embedding search of `scripts/h0_patch_select.py`: every injective map of the
frozen coarse step's 12-node CZ interaction tree into the device coupling graph, scored by
f_gates x exp(-S_T1 - S_T2) on the record's T1 and Hahn-echo T2.  Same circuit, different
qubits: no re-routing and no second transpiler solution.

* `fake_fez`: scripts/h0_patch_select.py, run unmodified as a subprocess
* `fake_marrakesh`: scripts/h0_patch_select.py, run unmodified as a subprocess
* `fake_kingston`: scripts/h0_patch_select.py's own enumerate_embeddings / score_patch / rank_key called directly, because search() refused on this record (see patch_select_error): the identity embedding cannot be scored, so the incumbent comparison and the h0_idle_model consistency check are NOT available  Refusal: `the identity embedding (the transpiler's own patch [117, 122, 123, 124, 125, 136, 141, 142, 143, 144, 145, 146]) is not among the candidates -- the enumeration is wrong`

| device | candidates | winning qubits | f_gates | PTA clean f | S_T1 | S_T2 | S_idle | duration (us) | weakest three qubits by T2 (us) |
|---|---|---|---|---|---|---|---|---|---|
| fake_fez | 1494 | [3, 4, 16, 21, 22, 23, 24, 25, 26, 37, 44, 45] | 1.1012e-01 | 9.4001e-03 | 0.745 | 1.716 | 2.461 | 52.55 | 22 (74.2), 24 (93.7), 26 (95.9) |
| fake_marrakesh | 1494 | [77, 85, 86, 87, 88, 89, 97, 106, 107, 108, 109, 110] | 8.7822e-02 | 1.3776e-02 | 0.486 | 1.366 | 1.852 | 52.68 | 86 (66.0), 97 (77.5), 109 (124.2) |
| fake_kingston | 1454 | [59, 72, 73, 74, 75, 79, 90, 91, 92, 93, 94, 95] | 3.0215e-01 | 6.5294e-02 | 0.365 | 1.167 | 1.532 | 50.24 | 79 (78.4), 91 (120.2), 75 (133.0) |

## 4. The two budgets at the winner's f (part E3)

| device | PTA clean f (winner) | PTA clean f (transpiler's patch) | gain | D3' N4 per sector | D3' coarse shots | D3' execution (s) | D3' execution, P11 interpolated (s) | D3''-H0 shots per k = 1 circuit | D3''-H0 coarse shots | D3''-H0 execution (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| fake_fez | 9.4001e-03 | 2.8430e-03 | 3.31x | {'B=0': 160000, 'B=1': 380000} | 1571823 | 490 | 479 | 14894 | 116081 | 50 |
| fake_marrakesh | 1.3776e-02 | 7.2201e-04 | 19.08x | {'B=0': 109100, 'B=1': 259200} | 1075723 | 340 | 332 | 10163 | 82964 | 40 |
| fake_kingston | 6.5294e-02 | - | - | {'B=0': 22800, 'B=1': 54500} | 234823 | 85 | 84 | 2145 | 26838 | 23 |

The "P11 interpolated" column is the planner's own table of
`reports/H0_replan_planner_analysis_20260922.md` interpolated linearly in 1/f; the column
before it is computed here from the rule itself (`h0_support_plan.n4_of_sector`, floor
267, margin 0.7,
lambda* 6.2958) on this record's own durations.
The two agreeing is the check that neither is a typing error.

## 5. What the owner needs in one paragraph

**The best patch of the surveyed records is `fake_kingston` [59, 72, 73, 74, 75, 79, 90, 91, 92, 93, 94, 95]**, with an echo-end PTA clean f of **6.5294e-02** (S_idle 1.53, with no incumbent comparison available on that record).  At that f the plan costs **85 s** of execution under rule D3' as it stands and **23 s** under the owner's D3''-H0 sizing (2145 shots per k = 1 circuit).  Both figures are the ECHO-T2 end.  On the patch that flew, the measured in-circuit error budget was **1.73x** the echo-PTA value (S_eff 5.76 against S_echo 3.32, `reports/H0_replan_planner_analysis_20260922.md` section 2), and the free-induction T2* of any of these patches is **unknown until the pilot** measures it.  Nothing here narrows that: T2* need not scale with the echo T2.

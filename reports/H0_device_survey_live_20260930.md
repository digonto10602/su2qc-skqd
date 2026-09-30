# Device survey for the 2x2 H0 patch (prompts/20 part E)

`scripts/h0_device_survey.py`, 2026-09-30 17:21:40 MDT.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit de8e57b, 2026-09-30 17:21:40 MDT.
**0 QPU seconds**: a calibration record is target / properties / status
metadata, and an offline snapshot needs no account at all.  Runtime 336 s.
Every number below is in `H0_device_survey_live_20260930` or in the per-device records under
`data/hardware/device_survey_20260922`.  The patch searches are `scripts/h0_patch_select.py` run unmodified; each
device for which it produced a result has its own JSON and report, and the `method` field of
every entry says which route was taken.

Requested devices: ibm_fez, ibm_marrakesh, ibm_kingston.


## 1. T2 geography (part E2)

| device | record | calibration | qubits | edges | T2 p10 (us) | T2 p25 (us) | T2 p50 (us) | T2 p75 (us) | T2 p90 (us) | T2 >= 50 us | T2 >= 100 us | T2 >= 150 us | missing errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ibm_fez | live device target, read-only metadata | 2026-09-30T16:57:15-06:00 | 156 | 176 | 24.8 | 48.7 | 92.2 | 131.1 | 169.1 | 74 % | 45 % | 15 % | 0 |
| ibm_marrakesh | live device target, read-only metadata | 2026-09-30T16:53:40-06:00 | 156 | 176 | 19.9 | 43.4 | 78.1 | 121.3 | 176.2 | 67 % | 37 % | 14 % | 0 |
| ibm_kingston | live device target, read-only metadata | 2026-09-30T16:55:44-06:00 | 156 | 176 | 40.2 | 76.4 | 141.2 | 235.4 | 342.1 | 84 % | 66 % | 46 % | 0 |

## 2. Where a twelve-qubit tree can live (part E2)

Connected components of the subgraph with readout error <=
3 %, CZ error <=
1 % and T2 above the stated
floor.  The frozen coarse step needs a connected 12-qubit region, so the last column is the
one that decides whether a floor is reachable at all.

| device | T2 floor (us) | good qubits | components | four largest | components >= 12 | four largest, readout filter only | >= 12, readout filter only |
|---|---|---|---|---|---|---|---|
| ibm_fez | 40 | 107 | 44 | [11, 11, 7, 6] | 0 | [17, 13, 7, 6] | 2 |
| ibm_fez | 60 | 91 | 43 | [10, 7, 6, 5] | 0 | [16, 7, 6, 6] | 1 |
| ibm_fez | 80 | 75 | 43 | [8, 7, 4, 4] | 0 | [13, 7, 5, 4] | 1 |
| ibm_fez | 100 | 59 | 36 | [8, 7, 4, 3] | 0 | [10, 7, 5, 3] | 0 |
| ibm_fez | 120 | 43 | 32 | [3, 3, 3, 2] | 0 | [3, 3, 3, 2] | 0 |
| ibm_fez | 150 | 21 | 17 | [3, 2, 2, 1] | 0 | [3, 2, 2, 1] | 0 |
| ibm_marrakesh | 40 | 98 | 28 | [11, 10, 10, 9] | 0 | [14, 12, 11, 11] | 2 |
| ibm_marrakesh | 60 | 77 | 38 | [7, 5, 4, 4] | 0 | [7, 6, 6, 5] | 0 |
| ibm_marrakesh | 80 | 62 | 36 | [6, 4, 4, 3] | 0 | [6, 6, 6, 4] | 0 |
| ibm_marrakesh | 100 | 47 | 34 | [3, 3, 2, 2] | 0 | [5, 3, 3, 2] | 0 |
| ibm_marrakesh | 120 | 33 | 26 | [3, 3, 2, 2] | 0 | [3, 3, 3, 2] | 0 |
| ibm_marrakesh | 150 | 16 | 15 | [2, 1, 1, 1] | 0 | [2, 2, 1, 1] | 0 |
| ibm_kingston | 40 | 128 | 12 | [57, 32, 10, 10] | 2 | [89, 10, 10, 7] | 1 |
| ibm_kingston | 60 | 113 | 20 | [26, 20, 13, 10] | 3 | [39, 21, 10, 10] | 2 |
| ibm_kingston | 80 | 107 | 24 | [25, 15, 13, 10] | 3 | [25, 15, 13, 10] | 3 |
| ibm_kingston | 100 | 94 | 27 | [24, 10, 10, 6] | 1 | [24, 10, 10, 6] | 1 |
| ibm_kingston | 120 | 79 | 24 | [22, 9, 6, 5] | 1 | [22, 9, 6, 5] | 1 |
| ibm_kingston | 150 | 65 | 28 | [6, 5, 5, 5] | 0 | [6, 5, 5, 5] | 0 |

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

* `ibm_fez`: scripts/h0_patch_select.py, run unmodified as a subprocess
* `ibm_marrakesh`: scripts/h0_patch_select.py, run unmodified as a subprocess
* `ibm_kingston`: scripts/h0_patch_select.py's own enumerate_embeddings / score_patch / rank_key called directly, because search() refused on this record (see patch_select_error): the identity embedding cannot be scored, so the incumbent comparison and the h0_idle_model consistency check are NOT available  Refusal: `the identity embedding (the transpiler's own patch [117, 122, 123, 124, 125, 136, 141, 142, 143, 144, 145, 146]) is not among the candidates -- the enumeration is wrong`

| device | candidates | winning qubits | f_gates | PTA clean f | S_T1 | S_T2 | S_idle | duration (us) | weakest three qubits by T2 (us) |
|---|---|---|---|---|---|---|---|---|---|
| ibm_fez | 1350 | [120, 121, 122, 123, 124, 136, 140, 141, 142, 143, 144, 145] | 2.0305e-01 | 1.9950e-02 | 0.778 | 1.543 | 2.320 | 45.37 | 122 (60.6), 123 (80.6), 124 (101.1) |
| ibm_marrakesh | 1084 | [9, 10, 11, 12, 13, 14, 18, 30, 31, 32, 33, 34] | 1.3734e-01 | 4.6269e-03 | 0.696 | 2.694 | 3.391 | 53.24 | 32 (46.7), 30 (49.3), 31 (52.6) |
| ibm_kingston | 1454 | [82, 83, 96, 102, 103, 104, 105, 106, 107, 117, 125, 126] | 2.4930e-01 | 5.6220e-02 | 0.494 | 0.995 | 1.489 | 50.14 | 103 (131.8), 106 (143.6), 96 (158.1) |

## 4. The two budgets at the winner's f (part E3)

| device | PTA clean f (winner) | PTA clean f (transpiler's patch) | gain | D3' N4 per sector | D3' coarse shots | D3' execution (s) | D3' execution, P11 interpolated (s) | D3''-H0 shots per k = 1 circuit | D3''-H0 coarse shots | D3''-H0 execution (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| ibm_fez | 1.9950e-02 | 5.7718e-03 | 3.46x | {'B=0': 75300, 'B=1': 178900} | 746123 | 235 | 235 | 7018 | 60949 | 32 |
| ibm_marrakesh | 4.6269e-03 | 1.9773e-07 | 23399.97x | {'B=0': 325400, 'B=1': 772200} | 3183223 | 979 | 955 | 30258 | 223629 | 82 |
| ibm_kingston | 5.6220e-02 | - | - | {'B=0': 26500, 'B=1': 63300} | 270923 | 96 | 95 | 2491 | 29260 | 23 |

The "P11 interpolated" column is the planner's own table of
`reports/H0_replan_planner_analysis_20260922.md` interpolated linearly in 1/f; the column
before it is computed here from the rule itself (`h0_support_plan.n4_of_sector`, floor
267, margin 0.7,
lambda* 6.2958) on this record's own durations.
The two agreeing is the check that neither is a typing error.

## 5. What the owner needs in one paragraph

**The best patch of the surveyed records is `ibm_kingston` [82, 83, 96, 102, 103, 104, 105, 106, 107, 117, 125, 126]**, with an echo-end PTA clean f of **5.6220e-02** (S_idle 1.49, with no incumbent comparison available on that record).  At that f the plan costs **96 s** of execution under rule D3' as it stands and **23 s** under the owner's D3''-H0 sizing (2491 shots per k = 1 circuit).  Both figures are the ECHO-T2 end.  On the patch that flew, the measured in-circuit error budget was **1.73x** the echo-PTA value (S_eff 5.76 against S_echo 3.32, `reports/H0_replan_planner_analysis_20260922.md` section 2), and the free-induction T2* of any of these patches is **unknown until the pilot** measures it.  Nothing here narrows that: T2* need not scale with the echo T2.

# 33a — Campaign 33, addendum after the first CI wave: threadpoolctl, the C2_CAL ladder, Kraus vs PTA, re-sizing

executor: executor-opus   effort: high
time budget: laptop code + tests about 1 executor day (0 QPU s, 0 HQC); Perlmutter: 1 smoke (15 min) + the
re-requests of section 6 (every job 1 GPU, <= 60 min; about 24 jobs of the campaign are re-sized, none is dropped)
machine: laptop (code, dry runs, commit) + Perlmutter CI (every sampling job)
date: 2026-10-07   planner: Fable 5.1 (high)   prompt number: 33a (addendum to `prompts/33`; prompts/33 stays in
force for everything not re-ruled here)

Trigger: the first four jobs of `prompts/33` came back (origin/master, CI commits 0dedf6a, fc1b4b9, 15e9406,
744702c): `C1_IDEAL` (job 59491455), `C3_AER` (59491462) and `C4_FCELLS_A` (59491480) died after 15-21 s with
`ModuleNotFoundError: No module named 'threadpoolctl'` raised from `scripts/gate_CV.py:114` inside
`campaign33/analysis.py:53` (`Physics()` builds `gate_CV.Sector`); `C2_CAL` (59491475) ran 779 s and wrote
`validation/C2_CAL.json` with `status: FAIL` on **P5 only** (ladder points per mode 2 / 1 / 4 / 3 against >= 2);
P4 resolved to `kraus_only` because no Kraus point reached 512 shots.  Planner arithmetic for every derived number
below: `scratch/planner/campaign33a_resize_20261007.{py,json}` (inputs: the job-59491475 JSON copied to
`scratch/planner/C2_CAL_job59491475.json`, `validation/S3.json`, `validation/K1_2x3_fpilot.json`,
`data/hardware/K1_2x3_ibm_kingston/counts/*.json`, the kingston record of 2026-10-06).

**Rule 1 is binding** (every number in a report from a JSON; "planner arithmetic" is labelled and is re-computed in
code before it is used).  **Rule 2:** no convention changes; the tree of `prompts/34` (`src/skqd/codec*`,
`circuits_ir`, `reference_sim`) is not touched.  **0 QPU s, 0 HQC.**  Local commits only; the coordinator pushes
the request commits as `prompts/33` 7e step 4.

**Code orientation (mandatory):** `graphify-out/graph.json` exists.  Use `graphify query "<question>"`,
`graphify explain "<symbol>"`, `graphify path "A" "B"`, `graphify affected "<symbol>"` BEFORE grepping or reading
files; grep only to edit specific lines; `graphify update .` after every code change.  Start with
`graphify explain "run_c2_cal"`, `graphify explain "run_c2_cell"`, `graphify explain "run_frun"`,
`graphify explain "Sampler"`, `graphify affected "Physics"`, `graphify explain "ibm_spec"`.

---

## 0. The rulings (what changed and why)

Measured facts (job 59491475, `validation/C2_CAL.json` on origin, I-ECHO on IBM-T0 `B0_ref117_k1`, 21 qubits,
double precision, one A100):

| representation \| mode | 8 shots | 32 | 128 | 512 | per-call set-up / per-shot (planner fit) |
|---|---|---|---|---|---|
| kraus \| custatevec | 6.88 s/shot | 3.18 | skipped | skipped | 10.8 s / 1.49 s (two points only) |
| kraus \| batched | 10.53 | skipped | skipped | skipped | — |
| pta \| custatevec | 1.84 | 0.794 | 0.374 | 0.270 | 3.46 s / 0.236 s |
| pta \| batched | 2.29 | 1.45 | 1.11 | skipped | 2.73 s / 1.00 s |

Accepted strings: Kraus 1 of 32, PTA 1 of 512 (`cells.*.ladder[].accepted`); reference hits 0 everywhere.

**R1 — P5 and the C2_CAL record.**  P5 ("$\ge2$ ladder points per (representation, mode)") is attainable inside the
45-min walltime with unequal budget shares (the one missing point, `kraus|batched` at 32 shots, was predicted at
337 s), but it would buy nothing: `batched_shots_gpu` is slower than cuStateVec at **every** measured point
(10.53 vs 6.88, 2.29 vs 1.84, 1.45 vs 0.794, 1.11 vs 0.374 s/shot), so the **mode decision is taken from the recorded
data: cuStateVec for both representations; the batched arm is closed** (do-not-retry).  The record of job 59491475
is **kept** (archived as `validation/archive/C2_CAL_job59491475.json`, identical bytes; never edited) and a **second
calibration run** is made under the same token with a re-designed content (section 2), because the one physics
question the calibration exists for — whether a cheap representation of thermal relaxation reproduces the Kraus
channel — was **not answered**: P4 compared *accepted fractions* at 512 shots, and at the accepted rate the device
showed ($58/10^5$, `validation/K1_2x3_fpilot.json data.circuits.B0_ref117_k1.accepted`) 512 shots carry an
expectation of 0.30 accepted strings — the test had no power even if the Kraus point had existed.

**R2 — Kraus vs PTA for class 2 (physics).**  Aer builds `thermal_relaxation_error(T1, T2, t)` as a **Kraus**
channel only when $T_2>T_1$; for $T_2\le T_1$ it is a mixture of {identity, $Z$, reset-to-0, reset-to-1} which the
statevector sampler applies per shot as cheaply as a Pauli.  On the 21 physical qubits of the K1 circuits the record
of 2026-10-06 has $T_2>T_1$ on **4 qubits only** (59, 69, 92, 95; planner arithmetic from the record), so the whole
Kraus cost of 1.49-3.18 s/shot comes from the relaxation sites on four qubits.  The Pauli-twirled form (PTA) is
**unital**: it keeps the no-fault probability (hence $f$) exactly but replaces energy relaxation towards $|0\rangle$
by symmetric $X$/$Y$ flips.  The quantity class 2 can actually compare with the device is the **structure of the
garbage** (the K1 strings are 99.94 % garbage), and the device's garbage is *not* unital: the measured mean Hamming
weight is $9.771\pm0.007$ ($B=0$) and $9.769\pm0.007$ ($B=1$) of 20 against the unital limit 10 (planner arithmetic
from `data/hardware/K1_2x3_ibm_kingston/counts`), of which readout asymmetry (mean $P(0|0)=0.9863$, $P(1|1)=0.9800$,
K1 readout block) explains 0.063 bits and the remaining $\approx0.17$ bits are relaxation-type.  PTA cannot produce
this deficit; the Kraus/reset channel can.  **Ruling: the non-unital channel is required for every class-2 number
that is compared with the device.**  The cheap representation that *keeps* the non-unital physics is **RM** ("reset
mixture", my label): the same model with $T_2:=\min(T_2,T_1)$ on the four qubits where $T_2>T_1$ (432.5→351.4,
140.1→131.1, 338.2→329.2, 299.2→247.4 $\mu$s), which makes every relaxation site a reset mixture (no Kraus
instruction anywhere) at PTA speed, and only *overstates dephasing* on four qubits by at most a factor 1.2 in
$T_2$.  C2_CAL run 2 tests RM and PTA against Kraus on the observables that have power at $\sim10^3$ shots
(mean Hamming weight, 21 per-clbit marginals); RM is expected to agree, PTA is expected to fail.  **PTA stays
in the campaign as an information cell** (it is exactly `idle.py`'s channel, so it reports what the project's
analytic model assumed), never as the production channel.

**R3 — what the IBM class can deliver in 60 min on 1 GPU.**  Sampling window per job: budget 50 min, about 120 s
of set-up, 75 % share → 2 160 s.  Kraus: 1 445 shots per job at the fitted 1.49 s/shot, 679 at the flat 3.18
(i.e. 340-720 per circuit for the 2-run cells, 170-360 for C2_XY4's 4 runs).  RM / PTA at 0.270 s/shot: 8 000 per
job (4 000 per circuit, 2 000 for XY4).  The $10^5$-per-circuit target of `prompts/33` is **unreachable** (it would
need 7.5 h per circuit even with RM).  What the five cells can and will state: (a) the simulated garbage structure
(mean Hamming weight to $\pm0.035$ at 4 000 shots, per-clbit marginals to $\pm0.008$) against the measured K1
strings — a device-vs-model comparison with real power, like-for-like only in C2_XY4 (the device flew the T3
circuits); (b) accepted counts and hits with the two-sided Poisson probability of the measured 58 / 45 and 0 / 0
scaled to the realised $N$ — **labelled underpowered** (expected 2.3 accepted at 4 000 shots at the measured rate);
(c) the analytic $f_0$ per cell (free); (d) the per-cell Kraus reference arm (20 % of the window) checking RM
in situ.  No $f$ point value (unchanged).

**R4 — the 0.0199 s/shot basis of classes 1/3/4.**  Classes 1 and 3 are statevector + noiseless sampling (cost
independent of shots; `C1_IDEAL` dry run 0.39 s/shot on the laptop CPU is overhead) — **not affected**.  Class 4
*was* sized on `validation/S3.json data.cost.seconds_per_shot_best_ladder` = 0.0199 (20-qubit native-type circuit,
E8 depolarizing, 476-shot calls).  The IBM PTA point (0.270) does **not** invalidate it: IBM-T0 has
$5659+11401+5596+20$ noise sites on 21 qubits against $2158+3053+20$ on 20 for NAT-O0, a factor 8.7 in sites × state
size (planner arithmetic) against the measured 13.6 — same order, so the native rate is still expected near 0.02.
What the original sizing **did** miss is the per-call set-up: S3's own mean rate at 100-shot calls was 0.0468
s/shot, which implies 2.7 s per `run()` call; at 476-shot chunks the effective rate is 0.0255 s/shot, and
the driver reserves 25 % (40 % for plan runs) of the window for analysis.  With those two facts (`class4_fit` in the
scratch JSON): the $10^5$-shot quota halves (C4_F4/F8 a/b) need **2 parts each**; the $B=1$ plan runs at 67 600
shots (F1/F2/F3/F6/F7) and F5_B1 at 99 000 need **2 parts**; the $B=0$ plan runs fit in one; C4_FCELLS_A/B are
borderline (max 67 707 shots at 0.0255 against 80 000 / 73 200 — the driver would drop cells and record it).  The
first measurement of the native rate at 476/952/1428-shot chunks is C4_FCELLS_A's own ladder, so **no C4_F* job is
requested before C4_FCELLS_A has reported**, and the parts are computed from its ladder by a script, not by hand
(section 4).  `C4_CF` (statevector trajectories, checkpointed, self-budgeting) is unchanged.

**R5 — threadpoolctl.**  No code is needed for the three dead jobs once the owner installs the package in the
`skqd` env (`pip install threadpoolctl`; pure Python, no pin).  Should `gate_CV` fall back when it is missing?
**No silent fallback**: `threadpool_limits(1)` around `model.reference` / `eigh` and `threadpool_limits(blas_threads)`
in `oracle_width` fix the BLAS thread count *mid-process* to reproduce a recorded eigenvector round-off order;
environment variables (`jobs/gate.sbatch` sets `OMP/MKL/OPENBLAS_NUM_THREADS` to 32 for the whole job) cannot
switch counts per call, so an env-var fallback would change numerics silently.  The right protection is to
**fail in the first 5 s, before any GPU or QPY work**, with the package name and the install line: a preflight in
`scripts/campaign33.py` (section 1), the package named in `scripts/check_package.py`, `SKQD-CI-SETUP.md` and
`scripts/ci_smoke.py` (so the 15-min `smoke` token catches an env drift before four 60-min jobs do), and the
version recorded in every token JSON (`run.versions.threadpoolctl`).

---

## 1. Step A — preflight and dependency declaration (laptop, 1 h; needed before any re-request)

1. `scripts/campaign33.py`: a `preflight(token)` called first in `main()` (before `ci_context`, before loading any
   QPY, before `AerSimulator`): import `threadpoolctl`, `qiskit`, `qiskit_aer`, `numpy`, `scipy`, `skqd.campaign33.*`,
   `gate_CV`; on failure print `preflight: missing <module>; install: pip install <package> (env skqd)` and
   `sys.exit(3)`; record `run.versions.threadpoolctl`.  The gate JSON is still written (`status: FAIL`, criterion
   `S0 preflight imports`) so the CI harvest has a record instead of `status UNKNOWN`.
2. `scripts/check_package.py`: add `threadpoolctl` to the import list.  `SKQD-CI-SETUP.md` line 107: add
   `threadpoolctl` to the pip line.  `scripts/ci_smoke.py`: import `threadpoolctl` and print its version.
3. Done-check: `tests/test_campaign33_preflight.py` — a stub `sys.modules` without `threadpoolctl` makes
   `preflight` exit 3 with the message; with it present every token passes preflight on the laptop in < 5 s.

## 2. Step B — C2_CAL run 2 (laptop code 3 h; one 45-min CI job)

Content of `run_c2_cal` (same token, `run: 2`, `supersedes: {"job": "59491475", "archived":
"validation/archive/C2_CAL_job59491475.json"}`), custatevec only, circuit IBM-T0 `B0_ref117_k1`, model I-ECHO:

| arm | representation | shots | chunk | order | expected time (planner arithmetic) |
|---|---|---|---|---|---|
| 1 | **PTA** (as run 1) | 512 fixed | 128 | first | 4 × 3.5 + 512 × 0.236 ≈ 135 s |
| 2 | **RM**: `ibm_spec(..., representation="rm")` = the Kraus builder with `T2 := min(T2, T1)` per qubit; assert `noise_model.to_dict()` contains **no** `kraus` instruction and that the 17 qubits with $T_2\le T_1$ have errors identical to run 1's Kraus model to $10^{-12}$ | 1024 fixed | 128 | second | ≈ 270 s (PTA speed; **measured here**) |
| 3 | **Kraus** (as run 1) | target 1024, **minimum 384**, deadline-stopped at a chunk boundary | 128 | last, share 0.9 of what is left | 808 s for 512 at the fit, 1 627 s at the flat rate |

Set-up ≈ 120 s; the budget is 35 min; at the flat Kraus rate arms 1-3 give 512 / 1024 / ≥ 390 shots, at the fitted
rate ≥ 830 Kraus shots.  Observables per arm, computed from the raw counts of all chunks: mean Hamming weight
$\bar w$ with its standard error, the 21 per-clbit marginals $p_k=P(\text{bit}_k=1)$ (string position $k$ ↔ clbit
$19-k$ ↔ physical qubit through the manifest's `measurement_map_clbit_to_physical`), accepted count, distinct
accepted strings, reference hits, s/shot and calls.  Also read the K1 hardware counts of the same circuit
(`data/hardware/K1_2x3_ibm_kingston/counts/B0_ref117_k1.json`) through the same function (information: the device
flew T3, not T0).

Criteria of run 2 (replace P4/P5 of `prompts/33` for this token; the structural S1-S6 stay):
- **P4a** RM vs Kraus: $|\bar w_{RM}-\bar w_{K}|\le3\,\sigma$ (two-sample, $\sigma^2=s_{RM}^2/N_{RM}+s_K^2/N_K$ from the
  per-shot Hamming-weight variances) **and** every $|p_{k,RM}-p_{k,K}|\le3\,\sigma_k$ (21 tests; family-wise
  false-alarm $\le21\times0.0027=5.7\,\%$, stated in the JSON).  PASS/FAIL → `decision.production_representation`
  = `rm` / `kraus`.
- **P4b** PTA vs Kraus, same statistic — **information** (expected FAIL; its value is the size of the twirling error
  on the garbage structure).
- **P5'** $\ge2$ ladder points per representation in custatevec (each arm records its chunks as points; satisfied by
  construction) and Kraus `shots_done` $\ge384$.
- **P4c** (information, no threshold): each arm's $\bar w$ and marginals against the K1 measurement, with $z$ and the
  readout-asymmetry share of the deficit computed from the K1 readout block (the formula of the scratch file,
  section 9).
- `decision.seconds_per_shot` per representation at the largest point; the C2 cells read `rm` or `kraus`.

Laptop dry run (`--shots-scale 0.01`, CPU) must exercise all three arms with 4 / 8 / 4 shots and write
`validation/dryrun/C2_CAL.json` with `run: 2`.  **Before the request**, copy origin's `validation/C2_CAL.json`
byte-identically to `validation/archive/C2_CAL_job59491475.json` and commit it (`sha256` recorded in the run-2 JSON).

## 3. Step C — the five production cells (laptop code 3 h; five 60-min CI jobs after run 2)

`run_c2_cell` changes:
1. Representation from run 2: `rm` if P4a PASS, else `kraus`; `pta` never for production.
2. Window split per job: **Kraus reference arm first, 20 % of the sampling window** (both circuits, equal shots,
   chunk 128; its only purpose is the in-cell RM-vs-Kraus check, information), then the production arm (RM, or
   Kraus if P4a failed) for the rest, **both K1 circuits with equal shots**, chunk `C2_CHUNK` as now.  C2_XY4 has 4
   runs (echo/star × 2 circuits): same rule, equal shots per run.  Record `shots_per_circuit` per arm and the rule.
3. Minimum (criterion S6 of this token): production arm $\ge1\,000$ shots per circuit when RM, $\ge256$ when Kraus
   (below that the garbage statistics are meaningless; the job records `shots_reduced_to` and FAILs S6 rather
   than pretending).
4. Observables per run and per arm, exactly as run 2 (Hamming weight, 21 marginals, accepted, distinct, hits,
   rejections, round trip P6), plus:
   - **P7'** the measured K1 values for the same circuit (58 / 45 accepted, 0 / 0 hits at $10^5$; its $\bar w$ and
     marginals from the counts file) with the two-sided Poisson probability of the measured counts under the
     simulated rate scaled to $10^5$, **and** the $z$ of $\bar w$ and of each marginal between simulation and device.
     The JSON field `comparison_power` says `underpowered` for the accepted/hits comparison whenever the simulated
     arm's expected accepted count at the device's rate is $<5$ (it will be), and `like_for_like` only for C2_XY4
     (T3 circuits); the other cells say `different_circuit_variant` (T0 / U: the device flew T3).
   - $f_0$ analytic per cell (unchanged) and the K0 / prereg numbers (unchanged).
   - The **RM-vs-Kraus in-cell check** (P4a statistic on the two arms; information).
5. No `f` point estimate (unchanged).  The dry run keeps PTA 1-shot path checks but labels them as such.

## 4. Step D — class-4 re-sizing by measurement, and generic part slots (laptop code 1 day)

1. **Generic slots.** Add 20 tokens `C4_PART_01` … `C4_PART_20` to `scripts/gate_tokens.json` (class 4, walltime
   01:00:00, 1 GPU, env `skqd`, script `scripts/campaign33.py --token C4_PART_NN`).  A slot's content is the file
   `ci/parts/C4_PART_NN.json` in the requested commit: `{"content": "frun" | "fcells" | "cv3", "scenario", "sector",
   "family", "part": i, "parts": n, "shots_by_circuit": {...}, "seed_token_index": <the slot's own index>,
   "cells": [...] (fcells only), "written_by": "scripts/campaign33_resize.py", "from": "validation/C4_FCELLS_A.json
   job <id>"}`.  The job writes `validation/C4_PART_NN.json` **and** the content-named copy
   `validation/C33_<scenario>_<sector>_part<i>of<n>.json`; `results/campaign33/C33_<...>_part<i>/`.  Rule: never
   two pending requests on the same slot.  `ci/allowed_jobs.campaign33a` = the 20 lines
   `C4_PART_NN  01:00:00 1`, generated from the token table (test: identical).
2. **Existing F tokens become part 1.** `C4_F*_B0`, `C4_F*_B1`, `C4_F4_*`, `C4_F8_*` keep their names and run **part
   1 of n** of their content, with `n` and the per-circuit shots read from `data/campaign33/sizing_33a.json`
   (written by the resize script, committed with the request); absent that file they run as `prompts/33` sized
   them (n = 1) and say so.
3. **`scripts/campaign33_resize.py`** reads `validation/C4_FCELLS_A.json` (`data.ladder.points`: one `run()` call
   per point at chunks 476 / 952 / 1428), fits $t=c+b\cdot\text{chunk}$ (least squares, record both and the
   residual), takes the chunk the F runs will use (476 unless the 952/1428 points succeeded at
   `--gpu-memory-bytes` ≥ 1.6e10, then the largest successful), and sizes every class-4 job with
   $N_{\max}=\text{share}\times(3000-120)\,/\,(1.25\,r_{\rm eff})$, $r_{\rm eff}=b+c/\text{chunk}$, share 0.75 for
   quota / f-cell jobs and 0.6 for plan runs (the driver's shares; do not change them), parts
   $n=\lceil N/N_{\max}\rceil$, equal per-circuit shots per part rounded **up** to chunk boundaries so that every
   `gate_CV` prefix point ($\phi\in\{1/16,1/8,1/4,1/2,1\}$ of the per-circuit plan shots) is a chunk boundary of the
   concatenated parts.  Output: `data/campaign33/sizing_33a.json` (every input number named with its JSON path)
   and the `ci/parts/*.json` files for the parts $\ge2$, assigned to slots in order.  Also the f-cells: if
   C4_FCELLS_A's JSON lists `cells_dropped`, the dropped cells (and C4_FCELLS_B's, once it has run) become
   `fcells` slot contents.
4. **Assembly merges parts**: `--stage assemble` concatenates the parts of a run in order (part 1 first; seeds are
   disjoint by the slot index), rebuilds the order-kept prefixes, and evaluates on the laptop what `run_frun` did
   in-job: CV0-CV5 (`cv_reading`), the certificates (ruling 2 of prompts/31), recall, bootstrap, P13 / P14 / P15 —
   writing `validation/C33_<scenario>_<sector>.json` with the same criteria names and the list of part JSONs it
   came from.  The in-job analysis of part 1 is kept (information: "part 1 of n").  The CV3 equal-shots sample is
   its own slot content (`cv3`) when the parts do not leave room; `not_evaluated` otherwise, as now.
5. Done-checks: `tests/test_campaign33_parts.py` — the 20 slots in the table and the allowlist text; a dry
   `C4_PART_01` with a synthetic `ci/parts` file runs on the laptop; the resize script on a synthetic FCELLS_A JSON
   with $b=0.02$, $c=2.7$ gives $n=2$ for 100 000 shots at share 0.75 and $n=1$ for 27 309 at 0.6; assembly of two
   dry-run parts reproduces the prefix boundaries of the unsplit dry run (same `bounds`) and the same `E_tol`.

## 5. Pass criteria (machine-checkable)

- A: `python scripts/check_package.py` PASS; `pytest -q tests` PASS (pins unchanged, recorded); every token's
  preflight < 5 s on the laptop.
- B: `validation/C2_CAL.json` (run 2, CI) `status: PASS` with P4a decided (PASS or FAIL, both are a decision),
  P5' PASS, Kraus `shots_done >= 384`, RM `shots_done == 1024`, PTA `shots_done == 512`, `supersedes` present,
  archive sha256 recorded; S1-S6 PASS.
- C: each `validation/C2_<cell>.json` `status: PASS`: S6 at the token's minimum, P6 0 mismatches, P7' fields present
  with `comparison_power` and the $z$ table, the Kraus arm present.
- D: `data/campaign33/sizing_33a.json` exists and names `validation/C4_FCELLS_A.json`'s job id; every F part JSON
  `full: true` (S6); every assembled `validation/C33_<scenario>_<sector>.json` has the P13-P15 criteria and
  `parts` listed.
- Nothing in `src/skqd/{su2,lattice,codec*,reference_sim,circuits_ir}.py` changes (`git diff --stat` shows none).

## 6. The re-request list (exact; `scripts/ci_request.sh` one commit per wave; the poller takes 4 at a time)

| wave | tokens | code that must land first | gate to open the wave |
|---|---|---|---|
| 0 | `smoke` | A (ci_smoke imports threadpoolctl) | owner confirms `pip install threadpoolctl` in `skqd` |
| 1 | `C1_IDEAL`, `C3_AER`, `C4_FCELLS_A`, `C2_CAL` | A for the first three (no other change needed); A + B + the archive commit for `C2_CAL` | `smoke` PASS with `threadpoolctl` printed |
| 2 | `C2_GATE`, `C2_ECHO`, `C2_STAR`, `C2_XY4`, `C2_COH` | C | `validation/C2_CAL.json` run 2 harvested with P4a decided |
| 3 | `C4_FCELLS_B`, `C4_CF`, `C3_LE` (if `data/campaign33/engines.json` keeps it; `C3_SEL` is dropped there) | none (FCELLS_B: the driver already records dropped cells) | after wave 1 (`C4_FCELLS_A` gives the GPU mode) |
| 4 | `C4_F1_B0`, `C4_F2_B0`, `C4_F3_B0`, `C4_F5_B0`, `C4_F6_B0`, `C4_F7_B0` (part 1 of n, n from sizing_33a) | D | `C4_FCELLS_A` harvested; `sizing_33a.json` committed |
| 5 | `C4_F1_B1`, `C4_F2_B1`, `C4_F3_B1`, `C4_F5_B1`, `C4_F6_B1`, `C4_F7_B1`, `C4_F4_B0a/b`, `C4_F4_B1a/b`, `C4_F8_B0a/b`, `C4_F8_B1a/b` (part 1) **and** their parts $\ge2$ in `C4_PART_NN` slots | D + the owner's allowlist append | same as wave 4 + the 20 slot lines installed |

Expected slot use at the inferred rate 0.0255 s/shot: 14 of 20 (planner arithmetic; the script decides).
Daily cap 24: waves 0-3 fit in one UTC day, 4-5 in the next.

## 7. What needs the owner

1. `conda activate skqd && pip install threadpoolctl` on Perlmutter, then tell the coordinator (wave 0 verifies).
2. `cat $SCRATCH/su2qc-skqd/ci/allowed_jobs.campaign33a >> ~/skqd-ci/allowed_jobs` (20 generic class-4 slot lines,
   60 min, 1 GPU each) after the push of step D — before wave 5 only.
3. Note for the record: the class-2 target of $10^5$ shots per circuit is withdrawn by this addendum (R3); the IBM
   class reports garbage structure and underpowered count comparisons, as stated above.  No decision is needed
   unless the owner wants class 2 dropped instead.

## 8. Escalation

- P4a FAIL (RM disagrees with Kraus): production on Kraus at $\ge256$ per circuit, report it; no retry of RM.
- Kraus `shots_done < 384` in run 2 (rate worse than 3.18 s/shot): re-request once with PTA 256 / RM 512 / Kraus
  minimum 256; a second miss → `prompts/BLOCKED_C33.md`.
- A C4_FCELLS_A ladder with a failed 476-shot point (OOM at 8e9 bytes): STOP, planner (the S3 memory bound would
  have moved).
- Any part JSON with `full: false`: re-size that run's remaining parts with the script (never hand-edit shots),
  max 2 re-requests per run, then BLOCKED.
- `E_R < E_0 - 10^{-9}` anywhere, or P11 FAIL: STOP as in `prompts/33` section 8.
- Three CI failures in a row on one token → `prompts/BLOCKED_C33.md`.

## 9. Outputs

`scripts/campaign33.py` (preflight, run-2 C2_CAL, cells, parts), `src/skqd/campaign33/{noise,tokens_run,sampling,
assemble}.py`, `scripts/campaign33_resize.py`, `scripts/{check_package,ci_smoke}.py`, `SKQD-CI-SETUP.md`,
`scripts/gate_tokens.json` (+20 slots), `ci/allowed_jobs.campaign33a`, `ci/parts/README.md`,
`validation/archive/C2_CAL_job59491475.json`, `tests/test_campaign33_{preflight,parts}.py`, dry-run JSONs,
`data/campaign33/sizing_33a.json` (after wave 1), LOG rows, `graphify update .`.  Local commits; pushes only with
the request commits per `prompts/33` 7e.

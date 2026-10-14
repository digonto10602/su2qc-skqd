# 33c — Campaign 33, addendum 3 (after wave 1 of 33b): the class-2 representation, the RM arm as a bug, C4_CF accepted as recorded, the next requests

executor: executor-opus   effort: high
time budget: laptop code + tests about 0.5 executor day (0 QPU s, 0 HQC); Perlmutter: the requests of section 4
machine: laptop (code, CPU tests, commit) + Perlmutter CI
date: 2026-10-13   planner: Fable 5.1 (high)   prompt number: 33c (addendum to `prompts/33`, `33a`, `33b`, which stay
in force for everything not re-ruled here)

Trigger (origin/master, harvested 2026-10-13): `C4_F5_B0` PASS 8/8 (the first full noisy 2x3 SKQD run; CV3 evaluated
in-job at $N_{\rm eq}=1100$), `C4_FCELLS_B` PASS 8/8 (P12 inside its band: 656 accepted against S3's 695, band
[650, 741]; no cell dropped), `C2_CAL` run 3 PASS 12/12 with `production_representation: kraus` (P4a FAIL: RM vs
Kraus $z_w = 32.2$; P4c vs the K1 strings: PTA $z_w = +1.82$, RM $-30.6$, Kraus $-54.2$), `C4_CF` FAIL 7/8 on S6
only (1232-1262 trajectories per arm of 2000; P16/P17 PASS).  Planner arithmetic: the per-qubit relaxation
expectation of section 1 is computed from `data/campaign33/circuits/IBM-T0/B0_ref117_k1.qpy.gz` (delay sum per
physical qubit) and `data/hardware/K0_prep/ibm_kingston_full_20261006T0652Z.json` (`qubits.<q>.T1_s`); it is
orientation, labelled, and the executor's test of section 2 recomputes it in code.

**Rule 1 binding; no criterion, tolerance, bar or convention changes; 0 QPU s.**  Code orientation: `graphify explain
"ibm_spec"`, `graphify explain "run_c2_cell"`, `graphify affected "C2_CELLS"`, `graphify explain "cf_gpu"` first.

---

## 0. The rulings

**R1 — the 54 sigma is the circuit, not the channel.**  C2_CAL sampled IBM-T0 (the ALAP-scheduled circuit with every
XY4 pulse replaced by a delay: 8 004 delays, 248 `x`) while the device flew IBM-T3 (5 596 delays, 2 656 `x`).  On
T0 each physical qubit idles 143-410 $\mu$s against $T_1$ of 131-351 $\mu$s, so amplitude damping drives the
populations towards $|0\rangle$: the zeroth-order expectation $\sum_q \tfrac12 e^{-t_{{\rm idle},q}/T_{1,q}}$ over
the 20 measured qubits is **2.64 bits** of 20 (planner arithmetic), and the Kraus arm measured **2.40 $\pm$ 0.14**.
On T3 the XY4 train flips every qubit about every 70 ns (5 596 windows in 411 $\mu$s), far faster than $T_1$, so
the same amplitude damping acts alternately on $|0\rangle$ and $|1\rangle$ and its fixed point is the maximally
mixed population — a *unital* net effect on the populations that a Markovian Aer model reproduces as soon as the
pulses are present as gates.  That is why the device shows $\bar w = 9.771\pm0.007$ (unital limit 10, readout
share 0.063 bits, the remaining 0.17 bits from the un-symmetrised gate-time windows and the last window before
measurement), and why PTA — unital by construction — lands at $z_w=1.8$ without being the right channel.  Neither
leakage (not modelled; cannot add 7 bits of weight) nor the measurement-error model (0.06 bits) is involved.
**Consequence:** the Kraus decision of C2_CAL stands for the *channel*; the like-for-like cell is `C2_XY4` on
IBM-T3 with the Kraus channel, and it is promoted from information to the **primary class-2 cell**.  Preregistered
expectation (planner, information — P7' keeps no threshold): its Kraus arm gives $\bar w$ within about 0.2 bits of
the device's 9.771, i.e. $|z_w|$ of order 1-3 at 300-500 shots, against 54 for T0.  If the XY4 arm does not
reproduce the device's weight, the residual is the one number class 2 has to report.

**R2 — the RM arm is a bug until proven otherwise.**  RM changes $T_2$ on four qubits only (P4r: 17 qubits with
identical super-operators on every gate site), yet its marginals differ from Kraus on all 20 clbits ($z$ 4.5-18)
and its weight 7.42 is three times the relaxation expectation of R1; on physical qubit 53 ($T_1 = 293\ \mu$s, idle
407 $\mu$s, expectation $\tfrac12 e^{-1.39}=0.12$) RM gives $P(1)=0.52$ — no relaxation at all on an *unchanged*
qubit.  P4r compared gate sites and the $T_1/T_2$ *inputs* of the delay pass, never the delay errors themselves
(their probabilities or durations).  So the RM delay pass does not apply the relaxation it claims (a duration
unit, an op-type filter or a per-qubit lookup is the likely place: `ibm_spec(..., representation="rm")` in
`src/skqd/campaign33/noise.py`).  Until fixed, RM is not a candidate; after the fix it re-enters only through the
in-cell P4a of R3 (33a's rule: production = RM iff P4a passes).  Kraus (1.84 s/shot at the largest point, 3.2 mean
over the arm) is the production channel for every class-2 cell requested before the maintenance.

**R3 — what the five cells run.**  `C2_XY4`: IBM-T3, **echo half only** (`("echo",)`; the star half is dropped from
this token: the population argument of R1 does not depend on $T_2^*$ and the Kraus budget does not carry four
runs), both K1 circuits, **production Kraus at 80 % of the window** and the 20 % arm becomes the **RM arm** (the
fixed RM, for the in-cell P4a; when production is Kraus a Kraus reference arm is a duplicate) — S6 minimum 256
production shots per circuit (unchanged constant; expected 290-470 at 1.8-3 s/shot).  `C2_ECHO` (IBM-T0, Kraus,
both circuits: adds the $B=1$ circuit to C2_CAL's Kraus arm) is *should-run*; `C2_GATE`, `C2_STAR`, `C2_COH` are
*may slip* — they sample circuits the device did not fly, their count comparisons are underpowered by 33a R3, and
each costs a GPU-hour the F runs need.  If the RM arm of `C2_XY4` passes P4a in-cell, the three deferred cells run
on RM (5x the shots) after the maintenance.

**R4 — C4_CF is accepted as recorded.**  Its first failure is S6 only (0.475 s per trajectory on the GPU against
the 0.3 the prompt sized; 4 977 trajectories in 2 400 s); P16 and P17 PASS with intervals: $r(10^{-3})$ = 1.061
[1.035, 1.090] / 1.048 [1.016, 1.082] / **1.172 [1.128, 1.217]** / 1.052 [1.030, 1.075], pooled 1.055 [1.033, 1.078],
`r_nc_new` 1.078.  No re-request before the maintenance: one more GPU-hour would narrow the pooled interval from
$\pm0.022$ to about $\pm0.016$ and change no decision.  **Consequences for $r_{nc}$:** (a) every campaign number
keeps $r_{nc}=1.115$ (`data/cf_trajectories/r_nc.json`) — it is *larger* than the new pooled upper end 1.078, so
$\hat f_{\rm ideal}$ and the tiers are conservative, and `prompts/33` section 6 makes the replacement an owner
item; (b) the new pooled 95 % interval [1.033, 1.078] excludes 1.115, so that owner item **fires** — the JSON field
`owner_item_r_nc_outside_old_interval` says `false`; the executor checks its rule against the section-6 text and
corrects the field's logic if it compared something else (no number is edited); (c) the $k=4$ arm's interval
[1.128, 1.217] lies entirely above both 1.078 and 1.115: $r_{nc}$ bounds the $k=1$ excess only, which is all the
campaign's pooled-$k=1$ statistic uses, and the report must say so where $k=4$ circuits are discussed.  A
re-request as 2 parts (K about 1 240 each, disjoint seeds, merged at assembly) is listed after the maintenance for
the owner.

**R5 — the E8 rate is now measured twice below E1.**  `C4_FCELLS_B.data.s3_redo`: 3 200 shots in 141.0 s at 14-shot
calls (0.044 s/shot, overhead-dominated) and gate S3's 0.0199 at 476-shot calls; the resize keeps $\rho_{E8}=\rho_{E1}$
with the label `upper bound (S3 and FCELLS_B s3_redo)`; F8 stays at 2 parts per half.  FCELLS_B dropped no cell and
its E6/E7 cells cost 43-58 s per 2 000 shots (E1-like, as assumed in 33b R2): the 33b f-cell slots are unchanged.

## 1. Orientation table (planner arithmetic; the executor's test recomputes it)

| clbit | qubit | $T_1$ ($\mu$s) | idle on T0 ($\mu$s) | $\tfrac12 e^{-t/T_1}$ | Kraus | RM | PTA | device (T3) |
|---|---|---|---|---|---|---|---|---|
| 1 | 69 | 131 | 393 | 0.025 | 0.042 | 0.145 | 0.527 | 0.499 |
| 4 | 53 | 293 | 407 | 0.124 | 0.142 | 0.519 | 0.512 | 0.498 |
| 9 | 72 | 256 | 208 | 0.222 | 0.184 | 0.505 | 0.516 | 0.492 |
| 19 | 59 | 351 | 405 | 0.158 | 0.139 | 0.438 | 0.562 | 0.502 |
| sum over 20 | | | | **2.64** | **2.40** | **7.42** | **9.96** | **9.77** |

## 2. Executor steps (laptop, about 0.5 day)

1. **RM delay pass.**  `tests/test_campaign33_noise.py`: (a) for the T0 circuit and the record, walk every `delay` of
   physical qubit 53 and compare the QuantumError the RM pass and the Kraus pass attach (probabilities of the
   reset / $Z$ / identity terms vs the Kraus channel's super-operator, to $10^{-12}$; durations in seconds); (b) a
   one-qubit Aer CPU test: `x`, `delay(400 µs)`, `measure` with $T_1=293\ \mu$s under the RM builder and under the
   Kraus builder, 20 000 shots each, both $P(1)$ within $4\sigma$ (binomial) of $e^{-400/293}=0.255$.  Fix what (a)
   finds in `noise.ibm_spec` (the convention and the function named in the LOG row); extend P4r so that the
   delay-pass errors themselves are compared on the unchanged qubits (this is a stronger version of the existing
   check, not a loosening).  Record in the LOG row the cause in one sentence.
2. **C2 cells.**  `C2_CELLS["C2_XY4"] = ("I-XY4", "IBM-T3", ("echo",))`; when `prod == "kraus"` the 20 % arm runs
   `rm` (label `rm_arm`, the in-cell P4a statistic against the production arm; `representation_decision_for_later_cells`
   = `rm` iff it passes); `like_for_like` stays `C2_XY4`-only; the dry run exercises the new arm layout.
3. **C4_CF field.**  Check `owner_item_r_nc_outside_old_interval` against `prompts/33` section 6 ("the new pooled
   interval excludes 1.115's derivation"); if the rule is wrong, fix the rule and record that the harvested JSON is
   not rewritten (the assembled report evaluates it from the stored intervals).  Add the `cf` part content
   (K per part, disjoint seeds by the slot rule of 33b R4, merged by assembly) for the post-maintenance re-request;
   not requested now.
4. `pytest -q tests` (laptop) and the campaign33 tests on the 1.4.3 twin; `graphify update .`; LOG row; commit.

## 3. Pass criteria

- Step 1(a) and 1(b) tests exist and PASS after the fix; before the fix 1(a) FAILs on at least one delay of qubit 53
  (the test's own assertion message names the site) — the LOG row quotes it.
- `validation/dryrun/C2_XY4.json` shows 2 runs (`B0_ref117_k1|echo`, `B1_ref29_k1|echo`), arms `rm_arm` and
  `production` (kraus).
- `validation/C2_XY4.json` (CI): `status: PASS`, S6 $\ge256$ production shots per circuit, P7' fields present with
  `comparison_power == like_for_like`, the RM-vs-Kraus in-cell statistic present.
- `git diff --stat` shows nothing under `src/skqd/{su2,lattice,codec*,reference_sim,circuits_ir}.py`.

## 4. The next requests (coordinator; `scripts/ci_request.sh`, one commit per line)

Running: wave 2 (`C4_F1_B0`, `C4_F7_B0`, `C4_F5_B1`, `C4_PART_01`, jobs 59739276-82); requested: wave 4
(`C4_F4_B0a`, `C4_PART_02`, `C4_F4_B1a`, `C4_PART_03`).  Then, in this order:

| when | tokens |
|---|---|
| now (no code needed) | `C4_F4_B0b`, `C4_PART_04`, `C4_F4_B1b`, `C4_PART_05` |
| after step 2 is pushed | `C2_XY4`, `C4_F8_B0a`, `C4_PART_06`, `C4_F8_B1a`, `C4_PART_07` |
| after one PASS of the batch above | `C4_F8_B0b`, `C4_PART_08`, `C4_F8_B1b`, `C4_PART_09` |
| next | `C4_F1_B1`, `C4_PART_10`, `C4_F7_B1`, `C4_PART_11` |
| if the queue still allows before 2026-10-21 06:00 UTC | `C2_ECHO`, `C4_F2_B0`, `C4_F2_B1`, `C4_PART_12` |
| after the maintenance | `C2_GATE`, `C2_STAR`, `C2_COH` (RM if the in-cell P4a passed, else Kraus), the C4_CF 2-part re-request if the owner wants K = 2000, then the 33b deferred list |

Must-run before the maintenance is unchanged in size (24): the four class-2 cells of 33b wave 3 are replaced by
`C2_XY4` plus three F jobs.  A `full: false` part or an S6 failure of `C2_XY4` follows the 33a/33b re-size rule
(at most 2 re-requests, then `prompts/BLOCKED_C33.md`).

## 5. What needs the owner

1. $r_{nc}$: the new pooled $r(10^{-3})$ interval [1.033, 1.078] excludes 1.115 (section 6 of `prompts/33`): decide
   whether `data/cf_trajectories/r_nc.json` is replaced by 1.078 (every $\hat f_{\rm ideal}$ rises by 3.4 %, no tier
   changes: the 33a tiers were read on the lower ends, which move up) or kept at 1.115 for the campaign report
   with both stated.  Nothing is changed until then.
2. Note: the $k=4$ arm's $r=1.172$ [1.128, 1.217] is above both; $r_{nc}$ is a $k=1$ quantity in this project.
3. Note: class 2 before the maintenance is `C2_XY4` (+ `C2_ECHO` if the queue allows); the three other cells wait.

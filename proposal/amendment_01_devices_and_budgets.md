# Amendment 01 — devices and budgets (items 1-3 signed 2026-09-23; items 4 and 5 open)

Status: **items 1, 2 and 3 signed by the owner on 2026-09-23** on the evidence named in section 5;
**items 4 and 5 remain open.**  Prepared by the executor from `validation/S2D.json` (gate S2D, status
**FAIL**), `validation/S2.json`, `validation/S2D_idle.json` (gate S2D_idle, status
**FAIL**), `validation/L4_fez.json`, `data/H0_patch_select.json` and
`data/S2_duration_compare.json`; every number is cited in the provenance table at the end and
re-checked against the JSON by `scripts/make_amendment.py`.  This amendment changes the *device
assignment*, the *budget criterion* and the *figure of merit* of the preregistration.  It does **not**
change the circuit family, any physics convention, any decoder, any frozen circuit, or any statistical
threshold.

What signing did and did not settle, in one line: item 2 fixes the **bar** (the clean-shot fraction is
read on the scheduled circuit, thresholds unchanged), and on that bar the present 2x2/Heron leg
**fails** — signing a criterion is not a claim that the device meets it.

## 1. What is amended

**(a) Device per lattice.**  The preregistration assumed one Heron-class superconducting device for both
lattices.  The amendment assigns:

| lattice | device | two-qubit gates per coarse step | mean f (gate-only) | worst-circuit f (gate-only) | f computed from | meets f >= 0.1 (gate-only) |
|---|---|---|---|---|---|---|
| 2x2 (12 qubits) | Heron-class superconducting, heavy-hex, native CZ | 663 CZ | 0.1248 | 0.1166 | calibration snapshot FakeFez | yes |
| 2x3 (20 qubits) | all-to-all trapped ion, native RZZ | 2158 RZZ | 0.0534 | 0.0532 | declared eps2 = 0.001 | **no** |

The two f columns of that table are the **gate-and-readout** f of the original draft, i.e. the
S_idle = 0 limit of the criterion the owner signed as item 2.  Read on the scheduled circuit, the 2x2
row does not meet the criterion either (section 2, item 2 of section 5); the row is kept because it is
what gate S2D computed and because the device assignment itself is unchanged.

**(b) Circuit family: unchanged.**  The exact structured circuits of gate S2 (`validation/S2.json`,
`skqd.circuits_ir.structured_term_gates`, `angle_mode="exact"`) remain the preregistered family.  The
fixed-angle alternative measured in `validation/S2_fixed.json` is *not* adopted (re-measured under the
corrected figure of merit: item 3 of section 5).  Reproduction checks in gate S2D: the **2x2** k = 1
coarse step gives 618 CZ routed on the ideal heavy-hex d = 3 map,
identical to the 618 routed CZ of `validation/S2.json`, whose
all-to-all count for that same 2x2 step is 256 CZ; the **2x3**
k = 1 coarse step gives 2164 CZ all-to-all in the CZ basis, identical to
the 2164 recorded in `validation/S2.json`.  (Errata, 2026-09-23: until
this revision the 2x2 sentence quoted the 2x3 all-to-all count for the 2x2 step.  No criterion, gate
count or JSON record changed; the sentence now cites `validation/S2.json` -> `data.2x2.coarse_step`.)

**(c) The budget criterion.**  Manual Step 4.3 fixed the budget as "<= 250 CZ at 2x2 and <= 500 CZ at
2x3".  Those numbers were derived in Step 4.4 from a physical condition: with per-CZ error eps the
clean-shot fraction is f = (1 - eps)^N_CZ, and the circuits must keep f high enough for the shot budget
to find a configuration of ideal probability p = 0.001.
The amendment replaces the gate-count proxy by the condition itself, evaluated on the device that will
actually run the circuits:

> **Budget criterion (amended, as drafted).**  For the production circuit set of a lattice, the
> clean-shot fraction
> f = prod over executed two-qubit gates (1 - eps_gate) x prod over measured qubits (1 - eps_readout),
> computed from the calibration of the device that will run them, must satisfy
> mean f >= 0.1 and worst-circuit f >= 0.05.

**As signed on 2026-09-23 (item 2 of section 5), f is read on the *scheduled* circuit:**

> **Budget criterion (as signed).**  f = f_gates x exp(-S_idle), with f_gates the gate-and-readout
> product above and S_idle = S_T1 + S_T2 the relaxation budget of the idle windows of the circuit's own
> ASAP schedule on that device (`skqd.idle`),
> S_T1 = sum_q sum_w (1 - e^(-w/T1_q))/4, S_T2 = sum_q sum_w (1 - e^(-w/T2_q))/2.
> The thresholds are unchanged: **mean f >= 0.1 and worst-circuit f >= 0.05**.  The T2 convention
> (Hahn-echo T2 of the record, or measured free-induction T2*) must be named wherever an f is quoted,
> and a device is assessable only if it declares **gate durations and T1/T2 alongside its error rates**.

f >= 0.1 is the operating point at which gate S1 established recall >= 0.9 of the 99.9 % support with the
production shot budget (`validation/S1.json`); it is therefore the condition the CZ numbers stood for.
The criterion is *not* weaker than the old one: at 2x2 the routed count 618
CZ is still far above 250, and on the FakeFez calibration its *gate-only* f is
0.1248 — which is what the draft reported as clearing the
requirement, and what the signed form of the criterion no longer accepts: on the scheduled circuit the
same set gives mean f = 6.71e-03 on the live ibm_fez record with the
Hahn-echo T2 and DD off (section 2, gate S2D_idle).

## 2. Evidence (gate S2D, status FAIL; gate S2D_idle, status FAIL)

### 2x2 on a Heron-class device — the gate-only computation

| snapshot | device qubits | circuits | CZ per circuit | mean f | worst f | mean error of the edges used | snapshot median CZ error | mean readout error of the patch |
|---|---|---|---|---|---|---|---|---|
| FakeFez | 156 | 28 | 663 | 0.1248 | 0.1166 | 3.05e-03 | 3.90e-03 | 7.46e-03 |
| FakeTorino | 133 | 28 | 636 | 0.0735 | 0.0569 | 4.08e-03 | 4.19e-03 | 3.51e-02 |

The transpiler's calibration-aware layout is what makes the difference: on FakeFez it places the
12 qubits on a patch whose edges average 3.05e-03 against a
snapshot median of 3.90e-03.  On FakeTorino the
same construction only reaches mean f = 0.0735, mostly through a
readout error of 3.51e-02 per qubit.  **The 2x2 run
must therefore be scheduled on a device of the FakeFez class, and the patch must be chosen from the
calibration of the day, not fixed in advance.**  How it is chosen is item 1 of section 5: a
calibration-aware layout is not enough, because the transpiler's layout maximises exactly the
gate-and-readout f of this table and is blind to the idle term that dominates.

### 2x2 — withdrawn as a hardware statement (2026-09-23)

Read on the scheduled circuit, as the signed criterion requires, the same
28 circuits fail at **every** point of the T2 x DD bracket (gate
S2D_idle, `validation/S2D_idle.json`, status FAIL):

| record / T2 convention | f_gates mean | S_T1 mean | S_T2 mean | idle-aware f mean (DD off) | worst | mean f at the most favourable corner (perfect DD refocusing) | criterion |
|---|---|---|---|---|---|---|---|
| live ibm_fez at the canary submission / Hahn-echo T2 | 0.2023 | 0.801 | 2.706 | 6.71e-03 | 1.54e-03 | 0.0623 | **FAIL** |
| live ibm_fez at the canary submission / measured T2* | 0.2023 | 0.801 | 9.239 | 1.30e-05 | 3.40e-07 | 0.0472 | **FAIL** |

The bars are 0.1 (mean) and
0.05 (worst).  **Gate S2D's 2x2 PASS is therefore withdrawn as a
statement about the hardware**; it stands as the gate-only computation it was, i.e. the S_idle = 0 limit
of the signed criterion, which gate S2D_idle reproduces to a maximum absolute difference of
0.0e+00 (criterion V1; `validation/S2D.json` is not rewritten).  Nothing here is a
model artefact: those 28 circuits are the r = 1 subset of the frozen H0
set — the circuits that flew — and their measured f is
0.0101 (J1),
0.0052 (J2),
0.0040 (J3),
-0.0010 (J4) and
0.0255 in the canary job itself, every one
below the worst-circuit bar with no model at all.

### 2x3 on an all-to-all trapped-ion device — the amendment is NOT yet supported

Declared inputs (vendor-class specifications, **not** measurements):
eps2 = 0.001 (two-qubit),
eps1 = 0.0001 (one-qubit),
eps_ro = 0.002 (readout).

| circuit set | circuits | RZZ | one-qubit gates | f (2q factor) | f (1q factor) | f (readout factor) | mean f | required |
|---|---|---|---|---|---|---|---|---|
| 2x3 coarse step, RZZ basis, all-to-all | 44 | 2158 | 7310 | 0.1154 | 0.4797 | 0.9608 | 0.0534 | >= 0.1 |

Even with all-to-all connectivity (no routing overhead at all: 2158 RZZ against
2164 CZ for the same circuit) the exact coarse step reaches only
f = 0.0534, about half of what the criterion requires.  Two-qubit error that would be
needed at these gate counts, holding eps1 and eps_ro: **7.09e-04**.
Note that a quarter of the loss (in log terms) is not the two-qubit error at all: the one-qubit factor alone is
0.4797.  If the platform implements rz as a virtual frame change (no
physical error), f rises to 0.0817 -- still below 0.1.  **This is a
decision the owner has to make; the amendment cannot be signed for 2x3 as it stands.**

**Necessary but no longer sufficient (2026-09-23).**  Everything above is the gate-and-readout f.  Under
the criterion as signed, the two-qubit requirement is the S_idle = 0 row of a table, not a number: the
sheet's requirement is recomputed at the shifted target `f_target e^(S_idle)`
(`skqd.device_req.target_with_idle`) over the same
44 circuits and the same declared inputs
(`reports/S2D_2x3_device_requirements.md`, `reports/S2D_idle_device_budgets.md` section 5):

| S_idle of the 2x3 schedule | shifted mean target | eps2 for mean f >= 0.1 | eps2 for worst f >= 0.05 | mean f at the declared eps2 |
|---|---|---|---|---|
| 0.000 | 0.1000 | 7.094e-04 | 1.029e-03 | 0.0534 |
| 0.100 | 0.1105 | 6.631e-04 | 9.824e-04 | 0.0483 |
| 0.300 | 0.1350 | 5.705e-04 | 8.898e-04 | 0.0396 |
| 1.000 | 0.2718 | 2.463e-04 | 5.656e-04 | 0.0196 |
| 3.507 | unreachable | - | - | - |

S_idle for the 2x3 device is **not computed anywhere in this repository and no number is asserted for
it**: the all-to-all device has no declared gate durations and no declared T1/T2, so its schedule cannot
be built.  The last row is the 2x2/Heron idle budget measured on the live record, shown only for scale:
at that S_idle the criterion is unreachable at any gate error.

## 3. Shot budget (manual Step 4.4, eq. 5)

N_circuit = ceil(lambda*/(p y)), lambda* = 6.295794 for
k = 3 counts at confidence
0.95, y = 0.82 f, p = 0.001;
N_sector = N_circuit x (number of circuits).  Implementation: `skqd.skqd.shot_rule`.

| circuit set / device | sector | circuits | mean f | yield y | N_circuit | N_sector | within the 2e5 of Step 9.2 |
|---|---|---|---|---|---|---|---|
| 2x3 / all-to-all | B=0 | 32 | 0.0533 | 0.0437 | 143921 | 4.605e+06 | no |
| 2x3 / all-to-all | B=1 | 12 | 0.0535 | 0.0439 | 143508 | 1.722e+06 | no |
| 2x2 / Heron FakeFez | B=0 | 20 | 0.1261 | 0.1034 | 60872 | 1.217e+06 | no |
| 2x2 / Heron FakeFez | B=1 | 8 | 0.1214 | 0.0995 | 63270 | 5.062e+05 | no |
| manual design point f = 0.2 (manual eq. 5) | any sector | 44 | 0.2000 | 0.1640 | 38389 | 1.689e+06 | no |

Two findings, neither of which is repaired by lowering p or the confidence (they are preregistered and
were left untouched):

1. At the measured f the 2x3 production run needs
   4.605e+06 shots in B = 0 and
   1.722e+06 in B = 1.
2. The 2x10^5-per-sector quota of Step 9.2 is inconsistent with eq. (5) *in the manual itself*: at the
   manual's own design point f = 0.2 eq. (5) asks
   38389 shots per circuit,
   i.e. 1.689e+06 per sector
   over 44 circuits.
   The owner must either raise the quota, reduce the circuit set, or accept a larger p (a weaker support
   claim).  **Nothing in this amendment chooses for him.**

Both findings are computed on the gate-only f, and every N_circuit and N_sector in the table above scales
as 1/f: when f is re-read on the scheduled circuit (the criterion as signed), these shot numbers move by
the same factor as f.  That is why item 5 stays open — see section 5 and
`reports/S2D_shot_quota_decision_20260922.md`.

Device time is N_sector / throughput; the throughput of the chosen device is not known here, so the
amendment states the formula and leaves the number to the owner
(`validation/S2D.json` -> `data.device_time_illustrative` holds an illustrative table for 100, 300 and
1000 shots per minute; those are round numbers, not device specifications).

## 4. The H0 role split

The 2x2 lattice cannot test SKQD accuracy (its sectors saturate at 38 and 20 states, manual Step 9.1), so
the amendment fixes what each lattice is *for*:

| lattice / device | what it establishes | gate |
|---|---|---|
| 2x2 on FakeFez-class Heron | decoder validity, bit order, link-parity checks, sector filter, readout confusion, measured f versus the model | H0 |
| 2x3 on the all-to-all device | yield versus two-qubit-gate count, support recall, certified energies | H1, H2 |

Rehearsal of H0 on the calibration snapshot (`validation/L4_fez.json`, `scripts/laptop_L4_aer_noise.py
--backend FakeFez`: full `NoiseModel.from_backend`, circuits transpiled onto the snapshot's qubits):

| sector | circuits | shots/circuit | CZ | f (FakeFez) | predicted yield 0.82 f | measured yield | measured / predicted | \|B\| | recall of the 99.9 % support |
|---|---|---|---|---|---|---|---|---|---|
| B=0 | 20 | 258 | 663 | 0.1261 | 0.1115 | 0.1467 | 1.32 | 38 | 1.000 |
| B=1 | 8 | 722 | 663 | 0.1214 | 0.1038 | 0.1356 | 1.31 | 20 | 1.000 |

Status of that run: **PASS** (450 s on the laptop CPU, criterion: measured
yield within a factor 3 of the manual's 0.82 f).  Both sectors keep the exact E_0 inside the Weinstein
interval, so bit order, decoder and sector filter survive a full calibration-snapshot noise model --
which is exactly what gate H0 has to confirm on hardware.

Two things the owner should note before H0.  (i) The manual's yield model is **conservative**: the measured
yield is a factor 1.32 (B = 0) and
1.31 (B = 1) above 0.82 f, in the same direction in both
sectors.  The manual's uniform-garbage term (0.15 % of random bitstrings decode) is far too small to explain
that; the excess is corrupted shots that still decode as a valid configuration of the right sector, because
the errors are local and leave most of the string intact.  (ii) Gate H0's preregistered criterion is
"measured f within 30 % of the model"; a systematic factor
1.32 sits just outside that window, so either the yield
model gains a calibrated acceptance term before H0 or H0's tolerance is revisited.  This amendment flags the
question and does not decide it.

**Note added 2026-09-23.**  The rehearsal above compares a gate-only model with a gate-only noise
simulation, and in that setting the model is conservative.  On hardware the ordering is the other way
round: the gate-only f predicts
359.6 accepted shots of
2000 against the
35 that gate H0_diag measured (a factor
0.097),
while the same prediction with the idle term and the Hahn-echo T2 is
30.8 against
35 (factor
1.13).  What was missing was
idle-time relaxation, not the acceptance term; that is what item 2 of section 5 fixes.

## 5. What the owner has signed, and what stays open

Items 1, 2 and 3 are **signed, 2026-09-23**, in the wording below, on the evidence named under each.
Items 4 and 5 remain open.

### 1. The 2x2 qubit patch, and the rule that selects it — SIGNED 2026-09-23

> The 2x2 circuits run on a Heron-class device, and the physical qubit patch is **not** fixed in
> advance: it is selected on the day of the run by the following rule.
>
>   * **Candidates.**  A candidate patch is an embedding of the routed circuit's CZ interaction graph
>     (12 nodes,
>     11 edges for the 2x2 r = 1 circuit) into the device
>     coupling graph.  Relabelling the frozen circuit along an embedding changes no gate, no angle, no
>     CZ count and no classical-bit mapping — only which physical qubit plays which role.  The
>     enumeration is exhaustive and deterministic.
>   * **Objective.**  `f_dd_off = f_gates x exp(-S_T1 - S_T2)` on the calibration record — the
>     idle-aware clean-shot fraction of item 2, not the gate-and-readout product alone.
>   * **Tie-breaks.**  1. larger f_dd_off; 2. larger f_gates; 3. smaller max_q S_T2; 4. lexicographically smallest tuple of physical qubits.
>   * **When it runs.**  On the calibration read of the day, on the **full device** (a target query:
>     free, no QPU time).  The H0 calibration records cover only the
>     30 qubits the frozen set already uses, so a search
>     restricted to them is a lower bound on what the rule finds.
>   * **Recording and freezing.**  The selected patch, the calibration record it was selected from with
>     its fingerprint, and the relabelled circuits are written to the run's prep directory and frozen
>     before submission, exactly as the present frozen set is.  Implementation and evidence:
>     `scripts/h0_patch_select.py`, `data/H0_patch_select.json`, `reports/H0_patch_select.md`.
>
> Why the rule is needed: the level-3 transpiler's calibration-aware layout is the **exact maximiser of
> gate-plus-readout f on every record tested** — a T2-blind objective returns the transpiler's own patch,
> a gain of 1.00x, on all
> 7 committed records and on the full device.  The
> layout pass was not mis-solving its problem; it was solving the wrong one.  Scored with the idle term
> the winner is the same patch with qubit 146
> (T2 16.0 us, carrying
> 0.857 of the patch's
> 2.568 S_T2 units) replaced by qubit
> 140
> (T2 36.0 us):
> **[117, 122, 123, 124, 125, 136, 140, 141, 142, 143, 144, 145]**.  It is worth
> **1.41x** in f on the record the canary
> actually flew (7.583e-03 ->
> 1.069e-02, the transpiler's patch ranking
> 3 of 10 candidates),
> 2.09x to
> 2.11x on the four earlier ibm_fez
> records, and **3.31x** on the full
> 156-qubit device, where the transpiler's patch ranks
> 57 of 1494.  Over the
> 7 committed records the rule returns
> **1** distinct winner.
>
> **This is a factor, not a rescue.**  At 1.069e-02 the 2x2
> r = 1 circuit remains far below the f >= 0.1 of item 2: of
> 2000 shots the predicted accepted count moves from
> 30.8 to
> 35.9 over a garbage floor of
> 18.6.  Signing item 1 fixes how the patch is
> chosen; it does not make the 2x2 leg meet the criterion.

Evidence: `reports/H0_patch_select.md`, `data/H0_patch_select.json`
(commit 2c6edb6, 2026-09-22 16:12:29 MDT, no QPU time).

### 2. The budget criterion: the idle-aware clean-shot fraction of the scheduled circuit — SIGNED 2026-09-23

> The fixed CZ numbers of manual Step 4.3 are replaced by the criterion of section 1(c), with the
> clean-shot fraction read on the **scheduled** circuit:
> f = f_gates x exp(-S_idle), f_gates the gate-and-readout product and S_idle = S_T1 + S_T2 the
> relaxation budget of the idle windows of the circuit's own ASAP schedule (`skqd.idle`).
>
>   * the thresholds are **unchanged**: mean f >= 0.1,
>     worst-circuit f >= 0.05;
>   * the **T2 convention must be named wherever an f is quoted**.  The two ends in use here are the
>     record's Hahn-echo T2 and the measured free-induction T2* (gate H0_diag's windowed Ramsey; median
>     ratio T2*/T2_echo 0.1740), and on the same 2x2
>     circuits they give mean f 6.71e-03 and
>     1.30e-05 respectively;
>   * a device is **assessable only if it declares gate durations and T1/T2 alongside its error rates**.
>     Without a schedule there is no S_idle and therefore no f: error rates alone are not an answer to
>     this criterion (item 4).
>
> **Signing this fixes the bar; the present 2x2/Heron leg fails it.**  On the idle-aware f that leg does
> not meet the criterion **at any point of the T2 x DD bracket** (gate S2D_idle,
> `validation/S2D_idle.json`, status FAIL): on the live ibm_fez record at the canary
> submission, echo T2, DD off, mean f = 6.71e-03 and worst
> 1.54e-03; and at the most favourable corner of the whole bracket (live
> record, echo T2, perfect DD refocusing — which the hardware contradicts, the canary having run XY4 DD
> on and measured a lower yield than with it off) mean f =
> 0.0623 and worst
> 0.0349.  Every T1 and T2 of the patch would have to
> be a factor
> 5.5
> longer to reach the mean bar.  The verdict does not depend on the model: the
> 28 circuits of the 2x2 set are the r = 1 subset of the frozen H0 set —
> the circuits that flew — and their measured f is
> 0.0101 (J1),
> 0.0052 (J2),
> 0.0040 (J3),
> -0.0010 (J4) and
> 0.0255 in the canary job, every one below
> the worst-circuit bar with no model at all.
>
> **Gate S2D's 2x2 PASS is therefore withdrawn as a hardware statement.**  It stands as the gate-only
> computation it was — the S_idle = 0 limit of the criterion above, reproduced by gate S2D_idle to
> 0.0e+00 — and `validation/S2D.json` is not rewritten.

Evidence: `reports/S2D_idle_device_budgets.md`, `validation/S2D_idle.json`
(commit 2c6edb6, 2026-09-22 16:36:34 MDT, no QPU time).

### 3. The circuit family, and the figure of merit by which a family is chosen — SIGNED 2026-09-23

> The circuit family stays the exact structured circuits of gate S2 (`validation/S2.json`,
> `skqd.circuits_ir.structured_term_gates`, `angle_mode="exact"`).  The criterion on which that choice
> rests is amended: a circuit family is judged not by its two-qubit gate count but by the
> **ASAP-scheduled duration and per-qubit idle budget** of its circuits on the calibration of the device
> that will run them —
>
>   * `T` = the ASAP critical path before the measure layer, and the idle window list of every active
>     qubit (`skqd.idle` / `scripts/h0_idle_model.py`);
>   * `S_T1 = sum_q sum_w (1 - e^(-w/T1_q))/4`, `S_T2 = sum_q sum_w (1 - e^(-w/T2_q))/2`;
>   * the idle-aware clean-shot fraction `f = f_gates x exp(-S_T1 - S_T2)` of item 2.
>
> Gate H0_diag (`validation/H0_diag.json`,
> 15.0 s of QPU time on ibm_fez; J1 gave
> N1 = 35 accepted of
> 2000) established the reason: at 2x2 the dominant loss is
> idle-time decoherence over the circuit's wall-clock duration, not the gate count.  The frozen canary
> runs 43.71 us at
> depth 1328 for only
> 663 CZ
> (1.46 CZ per CZ
> layer, qubit-time utilisation
> 0.233), and its idle budget
> is S_T1 = 0.755 plus S_T2 =
> 2.568 error units, which is what
> separates the gate-only prediction from the device.  A family with fewer gates at the same or greater
> duration therefore buys nothing, and a shallower-in-time family wins even at equal gate count.
>
> Re-evaluated on that criterion (`data/S2_duration_compare.json`,
> `reports/S2_duration_and_idle_2x2.md`, 89 circuits, no QPU time),
> the fixed-angle generator of `validation/S2_fixed.json` is **not adopted** — and now for the right
> reason.  With both families on the canary's own 12 physical qubits and the same ibm_fez calibration
> record (20 paired circuits), the fixed-angle
> circuits are
> -2.2 % in DAG
> depth but
> **+3.7 %
> in duration**,
> +3.5 % in
> summed idle time and
> +5.3 % in CZ,
> reaching 0.748x
> the exact family's idle-aware f: the exact family wins by
> **1.34x**.  They are not shallower
> in time, so the earlier rejection on routed CZ count is confirmed rather than reversed, and their known
> cost (a different generator: worst per-term deviation
> 0.132 at 2x2 against
> 1.9e-14 for the exact family, with gate-S1 recall
> 1.000 /
> 0.937) is not incurred.  For the record,
> the gate counts on which item 3 was originally decided are
> 256 all-to-all /
> 618 routed CZ per 2x2 coarse step for the exact family
> and 240 /
> 671 for the fixed-angle one.
>
> This item does **not** claim that the exact family is adequate at 2x2 on the present device: at the
> production point it reaches an idle-aware f of
> 6.11e-03 (mean over
> 20 circuits) against the f >= 0.1 of
> item 2.  What moves that number is duration and patch quality, not the family — see 3(b) and item 1.
>
> **3(b).  Re-scheduling headroom (measured, no new decomposition).**  On the same gates and the same
> layout no qubit can finish before its own busy time, so the duration cannot fall below
> `T_min = max_q busy_q` =
> 24.74 us against the
> 43.71 us the ASAP schedule takes:
> a perfect re-schedule is worth at most
> **1.77x** in duration (S_T1
> 0.755 ->
> 0.307, S_T2
> 2.568 ->
> 1.066) and
> **7.03x** in f — which reaches
> 0.0533, still short of f >= 0.1.  That
> bound is not attainable: only
> **1 of the
> 15** pairs of Hamiltonian terms have
> disjoint support, and the diagonal and plaquette terms touch
> 12 and
> 8 of the
> 12 logical qubits, so no
> term-level re-ordering can put either in parallel with anything else.  Reaching the bound would require
> a different codeword layout (`skqd.codec`), which re-opens E1-E3 — not a re-ordering of the present
> one.  Qubit 146 alone
> (T2 16.0 us)
> carries 0.857 of the
> 2.568 S_T2 units, so patch selection on
> T2 is the larger lever and is covered by item 1.

Evidence: `reports/S2_duration_and_idle_2x2.md`, `data/S2_duration_compare.json`
(commit 2c6edb6,
2026-09-22 16:22:01 MDT, no QPU time).

### 4. OPEN — the 2x3 device

At the declared eps2 = 0.001 the criterion is
missed by a factor of about two; a device with two-qubit error
7.09e-04 or better satisfies it at the present gate counts
**on the gate-and-readout f alone**.  What today's measurement adds: that requirement
(`eps2 <= 7.094e-04`, which is the
row `S_idle = 0.000` of the table in section 2)
is **necessary but no longer sufficient**.  Under item 2 the requirement is
`n_2q eps2~ + n_1q eps1~ + n_meas eps_ro~ <= ln(1/f_target) - S_idle`
(`skqd.device_req.target_with_idle`), so a vendor must additionally declare

  * two-qubit and one-qubit **gate durations**,
  * **T1 and T2** per qubit (and which T2 convention),
  * whether the device **idles qubits serially** (a trapped-ion device that executes one gate at a time
    idles every other qubit for the whole circuit),

because without them S_idle, and hence f, cannot be computed at all.  **No S_idle is asserted here for a
device that has no schedule in this repository**; section 2 gives the requirement as a function of it.
Sources: `reports/S2D_2x3_device_requirements.md`, `src/skqd/device_req.py`
(`target_with_idle`), `validation/S2D_idle.json` -> `data.implication_2x3`.

### 5. OPEN — the shot quota of Step 9.2

The analysis and the recommendation are in `reports/S2D_shot_quota_decision_20260922.md` (section 3 of
this document is the arithmetic).  Its per-sector shot figures are computed at the gate-only 2x3 f and
scale as 1/f; they are not to be signed until the corrected, idle-aware f of item 2 is available for the
2x3 device (which requires item 4 first).

Until 4 and 5 are settled, gate S2D stays **FAIL** and the 2x3 hardware claim of the plan is not
supported by measurement.  The 2x3 numbers can still be delivered from the certified emulation
(`validation/S1.json`) and from the S3 device-model simulation, whose cost is now measured:
3.20 s per shot on this laptop CPU for one 20-qubit
coarse-step circuit in the RZZ basis
(10 shots timed), i.e.
4.092e+03 CPU-hours for one B = 0 sector
at the budget of section 3 -- a GPU job with batched shots (RTX 3070 desktop or the Slurm cluster), not a
laptop job.

## Provenance of every number above

| value in this document | source (JSON path) | value in the JSON |
|---|---|---|
| `12` | `validation/S2D.json` -> `data.2x2.n_qubits` | `12` |
| `663` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.cz.mean` | `663.0` |
| `0.1248` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.f.mean` | `0.1247654303377872` |
| `0.1166` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.f.min` | `0.11656917621461786` |
| `20` | `validation/S2D.json` -> `data.2x3.n_qubits` | `20` |
| `2158` | `validation/S2D.json` -> `data.2x3.rzz.mean` | `2158.0` |
| `0.0534` | `validation/S2D.json` -> `data.2x3.f.mean` | `0.05338942314406832` |
| `0.0532` | `validation/S2D.json` -> `data.2x3.f.min` | `0.053191508462773214` |
| `0.001` | `validation/S2D.json` -> `data.assumed_inputs.eps2_two_qubit_all_to_all` | `0.001` |
| `32` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=0.n_circuits` | `32` |
| `0.0533` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=0.mean_f` | `0.05334763471362451` |
| `0.0437` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=0.yield` | `0.0437450604651721` |
| `143921` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=0.N_circuit` | `143921` |
| `4.605e+06` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=0.N_sector` | `4605472` |
| `12` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=1.n_circuits` | `12` |
| `0.0535` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=1.mean_f` | `0.053500858958585196` |
| `0.0439` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=1.yield` | `0.04387070434603986` |
| `143508` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=1.N_circuit` | `143508` |
| `1.722e+06` | `validation/S2D.json` -> `data.shot_budget.2x3 / all-to-all.B=1.N_sector` | `1722096` |
| `20` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=0.n_circuits` | `20` |
| `0.1261` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=0.mean_f` | `0.12613147269164876` |
| `0.1034` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=0.yield` | `0.10342780760715198` |
| `60872` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=0.N_circuit` | `60872` |
| `1.217e+06` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=0.N_sector` | `1217440` |
| `8` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=1.n_circuits` | `8` |
| `0.1214` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=1.mean_f` | `0.12135032445313329` |
| `0.0995` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=1.yield` | `0.09950726605156929` |
| `63270` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=1.N_circuit` | `63270` |
| `5.062e+05` | `validation/S2D.json` -> `data.shot_budget.2x2 / Heron FakeFez.B=1.N_sector` | `506160` |
| `44` | `validation/S2D.json` -> `data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.n_circuits` | `44` |
| `0.2000` | `validation/S2D.json` -> `data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.mean_f` | `0.2` |
| `0.1640` | `validation/S2D.json` -> `data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.yield` | `0.164` |
| `38389` | `validation/S2D.json` -> `data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.N_circuit` | `38389` |
| `1.689e+06` | `validation/S2D.json` -> `data.shot_budget.manual design point f = 0.2 (manual eq. 5).any sector.N_sector` | `1689116` |
| `20` | `validation/L4_fez.json` -> `data.B=0.circuits` | `20` |
| `258` | `validation/L4_fez.json` -> `data.B=0.shots` | `258` |
| `663` | `validation/L4_fez.json` -> `data.B=0.cz` | `663.0` |
| `0.1261` | `validation/L4_fez.json` -> `data.B=0.f_model` | `0.12613147269164876` |
| `0.1115` | `validation/L4_fez.json` -> `data.B=0.predicted_yield` | `0.11153498632729782` |
| `0.1467` | `validation/L4_fez.json` -> `data.B=0.yield_` | `0.14670542635658915` |
| `1.32` | `validation/L4_fez.json` -> `data.B=0.ratio_measured_over_predicted` | `1.3153310112585137` |
| `38` | `validation/L4_fez.json` -> `data.B=0.size` | `38` |
| `1.000` | `validation/L4_fez.json` -> `data.B=0.recall` | `1.0` |
| `8` | `validation/L4_fez.json` -> `data.B=1.circuits` | `8` |
| `722` | `validation/L4_fez.json` -> `data.B=1.shots` | `722` |
| `663` | `validation/L4_fez.json` -> `data.B=1.cz` | `663.0` |
| `0.1214` | `validation/L4_fez.json` -> `data.B=1.f_model` | `0.12135032445313329` |
| `0.1038` | `validation/L4_fez.json` -> `data.B=1.predicted_yield` | `0.10379754767045048` |
| `0.1356` | `validation/L4_fez.json` -> `data.B=1.yield_` | `0.13556094182825484` |
| `1.31` | `validation/L4_fez.json` -> `data.B=1.ratio_measured_over_predicted` | `1.3060129537804765` |
| `20` | `validation/L4_fez.json` -> `data.B=1.size` | `20` |
| `1.000` | `validation/L4_fez.json` -> `data.B=1.recall` | `1.0` |
| `PASS` | `validation/L4_fez.json` -> `status` | `PASS` |
| `450` | `validation/L4_fez.json` -> `runtime_s` | `449.8135039806366` |
| `FAIL` | `validation/S2D_idle.json` -> `status` | `FAIL` |
| `618` | `validation/S2D.json` -> `data.2x2.ideal_heavy_hex_cz_k1` | `618` |
| `618` | `validation/S2.json` -> `data.2x2.coarse_step.routed.cz` | `618` |
| `256` | `validation/S2.json` -> `data.2x2.coarse_step.all_to_all.cz` | `256` |
| `2164` | `validation/S2D.json` -> `data.2x3.all_to_all_cz_k1` | `2164` |
| `2164` | `validation/S2D.json` -> `data.2x3.S2_all_to_all_cz_k1` | `2164` |
| `0.001` | `validation/S2D.json` -> `data.assumed_inputs.p_configuration_probability` | `0.001` |
| `618` | `validation/S2D.json` -> `data.2x2.S2_heavy_hex_cz_k1` | `618` |
| `6.71e-03` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.f_dd_off.mean` | `0.006708679108014621` |
| `156` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.backend_qubits` | `156` |
| `28` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.n_circuits` | `28` |
| `3.05e-03` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.patch_mean_edge_error` | `0.0030469027261051823` |
| `3.90e-03` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.snapshot_median_cz_error` | `0.0039033828523107883` |
| `7.46e-03` | `validation/S2D.json` -> `data.2x2.snapshots.FakeFez.patch_mean_readout_error` | `0.007455008370535714` |
| `133` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.backend_qubits` | `133` |
| `28` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.n_circuits` | `28` |
| `636` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.cz.mean` | `636.4285714285714` |
| `0.0735` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.f.mean` | `0.07349130372839997` |
| `0.0569` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.f.min` | `0.05686424856214271` |
| `4.08e-03` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.patch_mean_edge_error` | `0.004078531496888499` |
| `4.19e-03` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.snapshot_median_cz_error` | `0.004190160309680474` |
| `3.51e-02` | `validation/S2D.json` -> `data.2x2.snapshots.FakeTorino.patch_mean_readout_error` | `0.035083589099702384` |
| `28` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.n_circuits` | `28` |
| `0.2023` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.f_gates.mean` | `0.20230713463719793` |
| `0.801` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.S_T1.mean` | `0.8008782581952315` |
| `2.706` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.S_T2.mean` | `2.70649379792917` |
| `1.54e-03` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.f_dd_off.min` | `0.0015417675136907636` |
| `0.0623` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.criterion_best_of_bracket.mean_f` | `0.06231484738784631` |
| `0.801` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.star.S_T1.mean` | `0.8008782581952315` |
| `9.239` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.star.S_T2.mean` | `9.238770436679925` |
| `1.30e-05` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.star.f_dd_off.mean` | `1.2983220313851827e-05` |
| `3.40e-07` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.star.f_dd_off.min` | `3.401620537389005e-07` |
| `0.0472` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.star.criterion_best_of_bracket.mean_f` | `0.047245033282735875` |
| `0.1` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.criterion_dd_off.mean_f_min` | `0.1` |
| `0.05` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.criterion_dd_off.worst_f_min` | `0.05` |
| `0.0e+00` | `validation/S2D_idle.json` -> `criteria.0.value` | `0.0` |
| `0.0101` | `validation/S2D_idle.json` -> `data.hardware_anchor.measured_f_by_cell.J1` | `0.010142378761232506` |
| `0.0052` | `validation/S2D_idle.json` -> `data.hardware_anchor.measured_f_by_cell.J2` | `0.005208508998048616` |
| `0.0040` | `validation/S2D_idle.json` -> `data.hardware_anchor.measured_f_by_cell.J3` | `0.003975041557252645` |
| `-0.0010` | `validation/S2D_idle.json` -> `data.hardware_anchor.measured_f_by_cell.J4` | `-0.0009588282059312431` |
| `0.0255` | `validation/S2D_idle.json` -> `data.hardware_anchor.measured_f_H0_canary` | `0.02551452448875534` |
| `0.0001` | `validation/S2D.json` -> `data.assumed_inputs.eps1_one_qubit_all_to_all` | `0.0001` |
| `0.002` | `validation/S2D.json` -> `data.assumed_inputs.eps_ro_readout_all_to_all` | `0.002` |
| `44` | `validation/S2D.json` -> `data.2x3.n_circuits` | `44` |
| `7310` | `validation/S2D.json` -> `data.2x3.n_1q.mean` | `7309.909090909091` |
| `0.1154` | `validation/S2D.json` -> `data.2x3.f_factors_k1.f_2q` | `0.11543130130536802` |
| `0.4797` | `validation/S2D.json` -> `data.2x3.f_factors_k1.f_1q` | `0.4796796793911737` |
| `0.9608` | `validation/S2D.json` -> `data.2x3.f_factors_k1.f_ro` | `0.9607509570263427` |
| `7.09e-04` | `validation/S2D.json` -> `data.2x3.eps2_required_for_f_0.1` | `0.000709441266619093` |
| `0.0817` | `validation/S2D.json` -> `data.2x3.f_virtual_rz.mean` | `0.08172250657676296` |
| `44` | `validation/S2D_idle.json` -> `data.implication_2x3.n_circuits` | `44` |
| `0.000` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.0.S_idle` | `0.0` |
| `0.1000` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.0.f_target_mean_shifted` | `0.1` |
| `7.094e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.0.eps2_for_mean` | `0.0007094434028515578` |
| `1.029e-03` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.0.eps2_for_worst` | `0.0010286436519356444` |
| `0.0534` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.0.mean_f_at_declared` | `0.05338942314406414` |
| `0.100` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.1.S_idle` | `0.1` |
| `0.1105` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.1.f_target_mean_shifted` | `0.11051709180756478` |
| `6.631e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.1.eps2_for_mean` | `0.0006631360020119495` |
| `9.824e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.1.eps2_for_worst` | `0.0009823510429238832` |
| `0.0483` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.1.mean_f_at_declared` | `0.048308747788104296` |
| `0.300` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.2.S_idle` | `0.3` |
| `0.1350` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.2.f_target_mean_shifted` | `0.13498588075760032` |
| `5.705e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.2.eps2_for_mean` | `0.0005705147625399947` |
| `8.898e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.2.eps2_for_worst` | `0.0008897593891640268` |
| `0.0396` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.2.mean_f_at_declared` | `0.03955185745680893` |
| `1.000` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.3.S_idle` | `1.0` |
| `0.2718` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.3.f_target_mean_shifted` | `0.27182818284590454` |
| `2.463e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.3.eps2_for_mean` | `0.0002462728171220783` |
| `5.656e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.3.eps2_for_worst` | `0.0005656210153340309` |
| `0.0196` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.3.mean_f_at_declared` | `0.019640871150703985` |
| `3.507` | `validation/S2D_idle.json` -> `data.implication_2x3.rows.4.S_idle` | `3.507` |
| `6.295794` | `validation/S2D.json` -> `data.assumed_inputs.lambda_star` | `6.295793621871989` |
| `3` | `validation/S2D.json` -> `data.assumed_inputs.k_min_counts` | `3` |
| `0.95` | `validation/S2D.json` -> `data.assumed_inputs.confidence` | `0.95` |
| `359.6` | `validation/S2D_idle.json` -> `data.hardware_anchor.gate_only_for_comparison.expected_accepted` | `359.6170293646223` |
| `2000` | `validation/S2D_idle.json` -> `data.hardware_anchor.echo.shots` | `2000` |
| `35` | `validation/S2D_idle.json` -> `data.hardware_anchor.echo.measured_accepted` | `35` |
| `0.097` | `validation/S2D_idle.json` -> `data.hardware_anchor.gate_only_for_comparison.factor_measured_over_predicted` | `0.0973257580761362` |
| `30.8` | `validation/S2D_idle.json` -> `data.hardware_anchor.echo.expected_accepted` | `30.849455594717572` |
| `1.13` | `validation/S2D_idle.json` -> `data.hardware_anchor.echo.factor_measured_over_predicted` | `1.1345419011541045` |
| `12` | `data/H0_patch_select.json` -> `sources.0.result.pattern.n_nodes` | `12` |
| `11` | `data/H0_patch_select.json` -> `sources.0.result.pattern.n_edges` | `11` |
| `30` | `data/H0_patch_select.json` -> `sources.0.result.host.n_qubits` | `30` |
| `1.00` | `data/H0_patch_select.json` -> `sources.0.result.gain.f_dd_off_gate_only_over_incumbent` | `1.0` |
| `7` | `data/H0_patch_select.json` -> `stability.n_committed_records` | `7` |
| `146` | `data/H0_patch_select.json` -> `sources.0.result.incumbent.worst_qubit` | `146` |
| `16.0` | `data/H0_patch_select.json` -> `sources.0.result.incumbent.worst_qubit_T2_s`, rendered in us (x 1e6) | `1.6015796811329427e-05` |
| `0.857` | `data/H0_patch_select.json` -> `sources.0.result.incumbent.worst_qubit_S_T2` | `0.8565443771207583` |
| `2.568` | `data/H0_patch_select.json` -> `sources.0.result.incumbent.S_T2` | `2.5675961961706695` |
| `140` | `data/H0_patch_select.json` -> `sources.0.result.best.worst_qubit` | `140` |
| `36.0` | `data/H0_patch_select.json` -> `sources.0.result.best.worst_qubit_T2_s`, rendered in us (x 1e6) | `3.600422109206929e-05` |
| `[117, 122, 123, 124, 125, 136, 140, 141, 142, 143, 144, 145]` | `data/H0_patch_select.json` -> `stability.winners.0` | `[117, 122, 123, 124, 125, 136, 140, 141, 142, 143, 144, 145]` |
| `1.41` | `data/H0_patch_select.json` -> `sources.0.result.gain.f_dd_off_best_over_incumbent` | `1.4098021899688278` |
| `7.583e-03` | `data/H0_patch_select.json` -> `sources.0.result.incumbent.f_dd_off` | `0.0075825980684856254` |
| `1.069e-02` | `data/H0_patch_select.json` -> `sources.0.result.best.f_dd_off` | `0.010689963362604438` |
| `3` | `data/H0_patch_select.json` -> `sources.0.result.incumbent.rank` | `3` |
| `10` | `data/H0_patch_select.json` -> `sources.0.result.n_candidates` | `10` |
| `2.09` | `data/H0_patch_select.json` -> `sources.3.result.gain.f_dd_off_best_over_incumbent` | `2.0917134565901048` |
| `2.11` | `data/H0_patch_select.json` -> `sources.4.result.gain.f_dd_off_best_over_incumbent` | `2.1079939168120445` |
| `3.31` | `data/H0_patch_select.json` -> `sources.7.result.gain.f_dd_off_best_over_incumbent` | `3.3064392837315864` |
| `156` | `data/H0_patch_select.json` -> `sources.7.result.host.n_qubits` | `156` |
| `57` | `data/H0_patch_select.json` -> `sources.7.result.incumbent.rank` | `57` |
| `1494` | `data/H0_patch_select.json` -> `sources.7.result.n_candidates` | `1494` |
| `1` | `data/H0_patch_select.json` -> `stability.n_distinct_winners` | `1` |
| `2000` | `data/H0_patch_select.json` -> `sources.0.result.gain.shots_reference` | `2000` |
| `30.8` | `data/H0_patch_select.json` -> `sources.0.result.gain.accepted_of_reference_incumbent` | `30.849455594717572` |
| `35.9` | `data/H0_patch_select.json` -> `sources.0.result.gain.accepted_of_reference_best` | `35.887878485091704` |
| `18.6` | `data/H0_patch_select.json` -> `sources.0.result.gain.garbage_floor_of_reference` | `18.5546875` |
| `2c6edb6` | `data/H0_patch_select.json` -> `commit` | `2c6edb6` |
| `2026-09-22 16:12:29 MDT` | `data/H0_patch_select.json` -> `created` | `2026-09-22 16:12:29 MDT` |
| `0.1740` | `validation/S2D_idle.json` -> `data.t2_bracket.fallback_ratio` | `0.17402491607893011` |
| `0.0349` | `validation/S2D_idle.json` -> `data.records.live ibm_fez at the canary submission.by_convention.echo.criterion_best_of_bracket.worst_f` | `0.034904036487405074` |
| `5.5` | `validation/S2D_idle.json` -> `data.device_requirement.live ibm_fez at the canary submission.echo.coherence_scale_for_mean_0.1` | `5.513049795515682` |
| `2c6edb6` | `validation/S2D_idle.json` -> `environment.git_commit` | `2c6edb6` |
| `2026-09-22 16:36:34 MDT` | `validation/S2D_idle.json` -> `environment.timestamp` | `2026-09-22 16:36:34 MDT` |
| `15.0` | `data/S2_duration_compare.json` -> `context.H0_diag.total_usage_s` | `15.0` |
| `35` | `data/S2_duration_compare.json` -> `context.H0_diag.N1` | `35` |
| `43.71` | `data/S2_duration_compare.json` -> `circuits.exact|frozen|B0_ref06_k1_rep1.T_s`, rendered in us (x 1e6) | `4.370799999999948e-05` |
| `1328` | `data/S2_duration_compare.json` -> `circuits.exact|frozen|B0_ref06_k1_rep1.depth` | `1328` |
| `663` | `data/S2_duration_compare.json` -> `circuits.exact|frozen|B0_ref06_k1_rep1.n_cz` | `663` |
| `1.46` | `data/S2_duration_compare.json` -> `circuits.exact|frozen|B0_ref06_k1_rep1.cz_per_cz_layer` | `1.457142857142857` |
| `0.233` | `data/S2_duration_compare.json` -> `rescheduling_headroom.qubit_time_utilisation` | `0.2331838565022444` |
| `0.755` | `data/S2_duration_compare.json` -> `rescheduling_headroom.S_T1_now` | `0.7552952713856562` |
| `2.568` | `data/S2_duration_compare.json` -> `rescheduling_headroom.S_T2_now` | `2.5675961961706695` |
| `89` | `data/S2_duration_compare.json` -> `n_circuits` | `89` |
| `20` | `data/S2_duration_compare.json` -> `verdict.pinned / ibm_fez.n_pairs` | `20` |
| `-2.2` | `data/S2_duration_compare.json` -> `verdict.pinned / ibm_fez.depth_ratio.mean`, rendered as the percentage change (v - 1) x 100 | `0.9781803776415187` |
| `+3.7` | `data/S2_duration_compare.json` -> `verdict.pinned / ibm_fez.T_ratio_fixed_over_exact.mean`, rendered as the percentage change (v - 1) x 100 | `1.0371312642018775` |
| `+3.5` | `data/S2_duration_compare.json` -> `verdict.pinned / ibm_fez.idle_ratio.mean`, rendered as the percentage change (v - 1) x 100 | `1.034972627290634` |
| `+5.3` | `data/S2_duration_compare.json` -> `verdict.pinned / ibm_fez.cz_ratio.mean`, rendered as the percentage change (v - 1) x 100 | `1.0531609195402296` |
| `0.748` | `data/S2_duration_compare.json` -> `verdict.pinned / ibm_fez.f_idle_ratio_fixed_over_exact.mean` | `0.7477220171015517` |
| `1.34` | `data/S2_duration_compare.json` -> `verdict.pinned / ibm_fez.win_margin_f` | `1.3374020894311824` |
| `0.132` | `data/S2_duration_compare.json` -> `context.S2_fixed.max_per_term_deviation_2x2` | `0.13161542140337218` |
| `1.9e-14` | `data/S2_duration_compare.json` -> `context.S2.max_deviation` | `1.8744776847271545e-14` |
| `1.000` | `data/S2_duration_compare.json` -> `context.S2_fixed.recall_2x3_B0` | `1.0` |
| `0.937` | `data/S2_duration_compare.json` -> `context.S2_fixed.recall_2x3_B1` | `0.937` |
| `256` | `data/S2_duration_compare.json` -> `context.S2.cz_all_to_all_2x2` | `256` |
| `618` | `data/S2_duration_compare.json` -> `context.S2.cz_routed_2x2` | `618` |
| `240` | `data/S2_duration_compare.json` -> `context.S2_fixed.cz_all_to_all_2x2` | `240` |
| `671` | `data/S2_duration_compare.json` -> `context.S2_fixed.cz_routed_2x2` | `671` |
| `6.11e-03` | `data/S2_duration_compare.json` -> `summary.exact|pinned|ibm_fez.f_idle_dd_off.mean` | `0.006108455661542971` |
| `20` | `data/S2_duration_compare.json` -> `summary.exact|pinned|ibm_fez.n_circuits` | `20` |
| `24.74` | `data/S2_duration_compare.json` -> `rescheduling_headroom.T_min_s`, rendered in us (x 1e6) | `2.473999999999983e-05` |
| `43.71` | `data/S2_duration_compare.json` -> `rescheduling_headroom.T_s`, rendered in us (x 1e6) | `4.370799999999948e-05` |
| `1.77` | `data/S2_duration_compare.json` -> `rescheduling_headroom.speedup_available` | `1.766693613581236` |
| `0.307` | `data/S2_duration_compare.json` -> `rescheduling_headroom.S_T1` | `0.30654086013996484` |
| `1.066` | `data/S2_duration_compare.json` -> `rescheduling_headroom.S_T2` | `1.0662276292010806` |
| `7.03` | `data/S2_duration_compare.json` -> `rescheduling_headroom.f_gain` | `7.0295520091955686` |
| `0.0533` | `data/S2_duration_compare.json` -> `rescheduling_headroom.f_idle_dd_off` | `0.053302267487245564` |
| `1` | `data/S2_duration_compare.json` -> `rescheduling_headroom.terms.n_disjoint_pairs` | `1` |
| `15` | `data/S2_duration_compare.json` -> `rescheduling_headroom.terms.n_pairs` | `15` |
| `12` | `data/S2_duration_compare.json` -> `rescheduling_headroom.terms.support_sizes.diag` | `12` |
| `8` | `data/S2_duration_compare.json` -> `rescheduling_headroom.terms.support_sizes.plaq0` | `8` |
| `12` | `data/S2_duration_compare.json` -> `circuits.exact|frozen|B0_ref06_k1_rep1.n_active` | `12` |
| `16.0` | `data/S2_duration_compare.json` -> `rescheduling_headroom.per_qubit.146.T2_s`, rendered in us (x 1e6) | `1.6015796811329427e-05` |
| `0.857` | `data/S2_duration_compare.json` -> `rescheduling_headroom.per_qubit.146.S_T2` | `0.8565443771207583` |
| `2c6edb6` | `data/S2_duration_compare.json` -> `environment.git_commit` | `2c6edb6` |
| `2026-09-22 16:22:01 MDT` | `data/S2_duration_compare.json` -> `environment.timestamp` | `2026-09-22 16:22:01 MDT` |
| `7.094e-04` | `validation/S2D_idle.json` -> `data.implication_2x3.eps2_of_the_sheet_at_S_idle_0` | `0.0007094434028515578` |
| `3.20` | `validation/S2D.json` -> `data.per_shot_cost_2x3.seconds_per_shot` | `3.198385763168335` |
| `10` | `validation/S2D.json` -> `data.per_shot_cost_2x3.shots_timed` | `10` |
| `4.092e+03` | `validation/S2D.json` -> `data.per_shot_cost_2x3.desktop_job_hours_per_sector_this_cpu.B=0` | `4091.6877992973327` |

Generated by `scripts/make_amendment.py` from `validation/S2D.json`
(commit 89102d2, 2026-09-16 07:02:12 MDT), `validation/S2.json`,
`validation/S2D_idle.json` (commit 2c6edb6), `data/H0_patch_select.json`
and `data/S2_duration_compare.json` (commit 2c6edb6) and `validation/L4_fez.json`
(commit 3722018, 2026-09-16 12:28:26 MDT).

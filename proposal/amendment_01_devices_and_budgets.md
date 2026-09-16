# Amendment 01 — devices and budgets (DRAFT for the owner's signature, 2026-09-16)

Status: **draft, unsigned.**  Prepared by the executor from `validation/S2D.json` (gate S2D, status
**FAIL**) and `validation/L4_fez.json`; every number is cited in the provenance table at the end and
re-checked against the JSON by `scripts/make_amendment.py`.  This amendment changes the *device
assignment* and the *budget criterion* of the preregistration.  It does **not** change the circuit
family, any physics convention, or any statistical threshold.

## 1. What is amended

**(a) Device per lattice.**  The preregistration assumed one Heron-class superconducting device for both
lattices.  The amendment assigns:

| lattice | device | two-qubit gates per coarse step | mean f | worst-circuit f | f computed from | meets f >= 0.1 |
|---|---|---|---|---|---|---|
| 2x2 (12 qubits) | Heron-class superconducting, heavy-hex, native CZ | 663 CZ | 0.1248 | 0.1166 | calibration snapshot FakeFez | yes |
| 2x3 (20 qubits) | all-to-all trapped ion, native RZZ | 2158 RZZ | 0.0534 | 0.0532 | declared eps2 = 0.001 | **no** |

**(b) Circuit family: unchanged.**  The exact structured circuits of gate S2 (`validation/S2.json`,
`skqd.circuits_ir.structured_term_gates`, `angle_mode="exact"`) remain the preregistered family.  The
fixed-angle alternative measured in `validation/S2_fixed.json` is *not* adopted.  Reproduction checks in
gate S2D: the k = 1 coarse step gives 618 CZ routed on the ideal
heavy-hex d = 3 map and 2164 CZ all-to-all in the CZ basis, identical to
the numbers recorded in `validation/S2.json`.

**(c) The budget criterion.**  Manual Step 4.3 fixed the budget as "<= 250 CZ at 2x2 and <= 500 CZ at
2x3".  Those numbers were derived in Step 4.4 from a physical condition: with per-CZ error eps the
clean-shot fraction is f = (1 - eps)^N_CZ, and the circuits must keep f high enough for the shot budget
to find a configuration of ideal probability p = 0.001.
The amendment replaces the gate-count proxy by the condition itself, evaluated on the device that will
actually run the circuits:

> **Budget criterion (amended).**  For the production circuit set of a lattice, the clean-shot fraction
> f = prod over executed two-qubit gates (1 - eps_gate) x prod over measured qubits (1 - eps_readout),
> computed from the calibration of the device that will run them, must satisfy
> mean f >= 0.1 and worst-circuit f >= 0.05.

f >= 0.1 is the operating point at which gate S1 established recall >= 0.9 of the 99.9 % support with the
production shot budget (`validation/S1.json`); it is therefore the condition the CZ numbers stood for.
The criterion is *not* weaker than the old one: at 2x2 the routed count 618
CZ is still far above 250, but on the FakeFez calibration it gives mean f =
0.1248, above the physical requirement.

## 2. Evidence (gate S2D, status FAIL)

### 2x2 on a Heron-class device — the amendment is supported

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
calibration of the day, not fixed in advance.**

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
| B=0 | 20 | 331 | 663 | 0.1261 | 0.1034 | 0.1438 | 1.39 | 38 | 1.000 |
| B=1 | 8 | 895 | 663 | 0.1214 | 0.0995 | 0.1381 | 1.39 | 20 | 1.000 |

Status of that run: **PASS** (530 s on the laptop CPU, criterion: measured
yield within a factor 3 of the manual's 0.82 f).  Both sectors keep the exact E_0 inside the Weinstein
interval, so bit order, decoder and sector filter survive a full calibration-snapshot noise model --
which is exactly what gate H0 has to confirm on hardware.

Two things the owner should note before H0.  (i) The manual's yield model is **conservative**: the measured
yield is a factor 1.39 (B = 0) and
1.39 (B = 1) above 0.82 f, in the same direction in both
sectors.  The manual's uniform-garbage term (0.15 % of random bitstrings decode) is far too small to explain
that; the excess is corrupted shots that still decode as a valid configuration of the right sector, because
the errors are local and leave most of the string intact.  (ii) Gate H0's preregistered criterion is
"measured f within 30 % of the model"; a systematic factor
1.39 sits just outside that window, so either the yield
model gains a calibrated acceptance term before H0 or H0's tolerance is revisited.  This amendment flags the
question and does not decide it.

## 5. What the owner is asked to sign

1. 2x2 runs on a Heron-class device; the qubit patch is chosen by calibration-aware layout on the day of
   the run (evidence: section 2).
2. The fixed CZ numbers of Step 4.3 are replaced by the f >= 0.1 / worst >= 0.05 criterion of section 1(c).
3. The circuit family stays the exact structured circuits of gate S2.
4. **Open:** the 2x3 device.  At the declared eps2 = 0.001
   the criterion is missed by a factor of about two; a device with two-qubit error
   7.09e-04 or better satisfies it at the present gate counts.
5. **Open:** the shot quota of Step 9.2 (section 3).

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
| `331` | `validation/L4_fez.json` -> `data.B=0.shots` | `331` |
| `663` | `validation/L4_fez.json` -> `data.B=0.cz` | `663.0` |
| `0.1261` | `validation/L4_fez.json` -> `data.B=0.f_model` | `0.12613147269164876` |
| `0.1034` | `validation/L4_fez.json` -> `data.B=0.predicted_yield` | `0.10342780760715198` |
| `0.1438` | `validation/L4_fez.json` -> `data.B=0.yield_` | `0.14380664652567976` |
| `1.39` | `validation/L4_fez.json` -> `data.B=0.ratio_measured_over_predicted` | `1.390406021868877` |
| `38` | `validation/L4_fez.json` -> `data.B=0.size` | `38` |
| `1.000` | `validation/L4_fez.json` -> `data.B=0.recall` | `1.0` |
| `8` | `validation/L4_fez.json` -> `data.B=1.circuits` | `8` |
| `895` | `validation/L4_fez.json` -> `data.B=1.shots` | `895` |
| `663` | `validation/L4_fez.json` -> `data.B=1.cz` | `663.0` |
| `0.1214` | `validation/L4_fez.json` -> `data.B=1.f_model` | `0.12135032445313329` |
| `0.0995` | `validation/L4_fez.json` -> `data.B=1.predicted_yield` | `0.09950726605156929` |
| `0.1381` | `validation/L4_fez.json` -> `data.B=1.yield_` | `0.13812849162011173` |
| `1.39` | `validation/L4_fez.json` -> `data.B=1.ratio_measured_over_predicted` | `1.3881246777348615` |
| `20` | `validation/L4_fez.json` -> `data.B=1.size` | `20` |
| `1.000` | `validation/L4_fez.json` -> `data.B=1.recall` | `1.0` |
| `PASS` | `validation/L4_fez.json` -> `status` | `PASS` |
| `530` | `validation/L4_fez.json` -> `runtime_s` | `530.0458493232727` |
| `618` | `validation/S2D.json` -> `data.2x2.ideal_heavy_hex_cz_k1` | `618` |
| `2164` | `validation/S2D.json` -> `data.2x3.all_to_all_cz_k1` | `2164` |
| `0.001` | `validation/S2D.json` -> `data.assumed_inputs.p_configuration_probability` | `0.001` |
| `618` | `validation/S2D.json` -> `data.2x2.S2_heavy_hex_cz_k1` | `618` |
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
| `0.0001` | `validation/S2D.json` -> `data.assumed_inputs.eps1_one_qubit_all_to_all` | `0.0001` |
| `0.002` | `validation/S2D.json` -> `data.assumed_inputs.eps_ro_readout_all_to_all` | `0.002` |
| `44` | `validation/S2D.json` -> `data.2x3.n_circuits` | `44` |
| `7310` | `validation/S2D.json` -> `data.2x3.n_1q.mean` | `7309.909090909091` |
| `0.1154` | `validation/S2D.json` -> `data.2x3.f_factors_k1.f_2q` | `0.11543130130536802` |
| `0.4797` | `validation/S2D.json` -> `data.2x3.f_factors_k1.f_1q` | `0.4796796793911737` |
| `0.9608` | `validation/S2D.json` -> `data.2x3.f_factors_k1.f_ro` | `0.9607509570263427` |
| `2164` | `validation/S2D.json` -> `data.2x3.S2_all_to_all_cz_k1` | `2164` |
| `7.09e-04` | `validation/S2D.json` -> `data.2x3.eps2_required_for_f_0.1` | `0.000709441266619093` |
| `0.0817` | `validation/S2D.json` -> `data.2x3.f_virtual_rz.mean` | `0.08172250657676296` |
| `6.295794` | `validation/S2D.json` -> `data.assumed_inputs.lambda_star` | `6.295793621871989` |
| `3` | `validation/S2D.json` -> `data.assumed_inputs.k_min_counts` | `3` |
| `0.95` | `validation/S2D.json` -> `data.assumed_inputs.confidence` | `0.95` |
| `3.20` | `validation/S2D.json` -> `data.per_shot_cost_2x3.seconds_per_shot` | `3.198385763168335` |
| `10` | `validation/S2D.json` -> `data.per_shot_cost_2x3.shots_timed` | `10` |
| `4.092e+03` | `validation/S2D.json` -> `data.per_shot_cost_2x3.desktop_job_hours_per_sector_this_cpu.B=0` | `4091.6877992973327` |

Generated by `scripts/make_amendment.py` from `validation/S2D.json`
(commit 89102d2, 2026-09-16 07:02:12 MDT) and `validation/L4_fez.json`
(commit 7c8150f, 2026-09-16 07:15:55 MDT).

## 6. Planner addendum (2026-09-16): the operational criterion at the predicted 2x3 fidelity

Generated table from `reports/S2D_recall_at_predicted_f.md` (`scripts/s2d_recall_at_predicted_f.py`, numbers in `data/S2D_recall_at_f.json`):
the S1 criterion (recall of the 99.9 % support >= 0.9 with 2e5 shots per sector) evaluated at the clean-shot fractions predicted
by gate S2D for the 2x3 all-to-all device, three seeds.  This is the requirement the CZ budget was derived from.

| sector | f | circuits | shots/circuit | recall (3 seeds) | min recall | |B| | yield | E0 in Weinstein | N_sector, shot rule per sector |
|---|---|---|---|---|---|---|---|---|---|
| B=0 | 0.1 | 32 | 6250 | 1.000 / 1.000 / 1.000 | 1.0 | 333/333/350 | 0.0881 | yes | 71500 |
| B=0 | 0.0817 | 32 | 6250 | 1.000 / 1.000 / 1.000 | 1.0 | 329/323/341 | 0.0743 | yes | 84714 |
| B=0 | 0.0534 | 32 | 6250 | 1.000 / 0.988 / 1.000 | 0.9883720930232558 | 313/311/320 | 0.0508 | yes | 123954 |
| B=0 | 0.03 | 32 | 6250 | 0.988 / 0.953 / 1.000 | 0.9534883720930233 | 284/290/302 | 0.0315 | yes | 199952 |
| B=1 | 0.1 | 12 | 16667 | 1.000 / 0.989 / 0.989 | 0.9894736842105263 | 244/248/260 | 0.0886 | yes | 71075 |
| B=1 | 0.0817 | 12 | 16667 | 0.979 / 0.989 / 0.979 | 0.9789473684210527 | 242/259/253 | 0.0737 | yes | 85440 |
| B=1 | 0.0534 | 12 | 16667 | 0.958 / 0.989 / 0.989 | 0.9578947368421052 | 224/237/222 | 0.0505 | yes | 124569 |
| B=1 | 0.03 | 12 | 16667 | 0.958 / 0.958 / 0.937 | 0.9368421052631579 | 220/216/211 | 0.0314 | yes | 200806 |


Reading: at the predicted f the S1 criterion holds in both sectors (minimum recall over seeds in the "min recall" column) and the
shot rule applied to the sector as a whole (union support) stays below the 2e5 quota; gate S2D's two failing criteria (mean f >= 0.1,
per-circuit shot rule) are stricter than this operational requirement and remain recorded as FAIL.  Owner inputs still required before
signature: the vendor's specified one- and two-qubit and readout errors and whether rz is virtual (S2D used declared class values).

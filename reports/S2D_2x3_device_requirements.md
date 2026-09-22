# Device requirements for the 2x3 coarse-step circuits (20 qubits, all-to-all)

Open item 4 of `proposal/amendment_01_devices_and_budgets.md`.  Produced by
`scripts/s2d_2x3_device_requirements.py`; every number below is read from
`data/S2D_2x3_device_requirements.json`, which the same script wrote.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44, 12 CPUs, commit d5e357d, 2026-09-22 00:57:40 MDT.
Runtime 97 s.  `pytest -q tests`: 80 passed, 5 warnings in 105.53s (0:01:45).

**What this sheet is.**  A *requirement*: the region of device error rates in which the
preregistered 2x3 circuit set satisfies the amended budget criterion.  It names no vendor and
asserts no vendor specification -- there is no verified source for any product's error rates in
this repository, and an unsourced claim in a preregistration amendment would be worse than no
claim.  The owner matches a device to the region.

**What it replaces.**  The amendment currently states one number, "two-qubit error
7.094e-04 or better", which holds
eps1 and eps_ro at their declared values.  That number is reproduced below
(7.094e-04, computed from the 44-circuit
set rather than from the mean gate counts) and is one point on a boundary, not the requirement.

## 0. The criterion and the model

Criterion (amendment 01 section 1(c), gate S2D): over the production circuit set of the lattice,

> mean f >= 0.1 and worst-circuit f >= 0.05,
> f = (1 - eps2)^n_2q x (1 - eps1)^n_1q x (1 - eps_ro)^n_meas.

The f model is gate S2D's (`gate_S2D.analyse_rzz`); this sheet only inverts it
(`skqd.device_req`, tested in `tests/test_device_req.py` against the recorded S2D numbers).
The circuit family is unchanged: the exact structured circuits of gate S2
(`skqd.circuits_ir.CircuitFactory`, `angle_mode="exact"`), coarse steps k = 1..4 of every
reference of both sectors -- 44 circuits.

## 1. What the circuits need from the device

Per term of the coarse step (theta = dt of the B = 0 reference, all-to-all, no routing):

| term | RZZ | 1q gates | of which rz | depth | CZ basis (all-to-all) | CZ in validation/S2.json |
|---|---|---|---|---|---|---|
| diag | 14 | 51 | 31 | 17 | 20 | 20 |
| hop0 | 194 | 667 | 385 | 531 | 194 | 194 |
| hop1 | 48 | 173 | 91 | 110 | 48 | 48 |
| hop2 | 182 | 633 | 359 | 485 | 182 | 182 |
| hop3 | 184 | 640 | 358 | 479 | 184 | 184 |
| hop4 | 358 | 1255 | 710 | 968 | 358 | 358 |
| hop5 | 156 | 538 | 305 | 444 | 156 | 156 |
| hop6 | 44 | 161 | 79 | 109 | 44 | 44 |
| plaq0 | 214 | 743 | 431 | 594 | 214 | 214 |
| plaq1 | 764 | 2523 | 1531 | 2079 | 764 | 764 |

The CZ column reproduces `validation/S2.json` `data.2x3.per_term_cz` exactly
(match), which is the
check that this sheet is priced on the preregistered circuits.  The two plaquette terms and
`hop4` dominate; the diagonal term is negligible.  The per-term RZZ counts sum to
2158 against 2158 for the compiled step, so the two-qubit
cost is additive over terms: **removing a term removes its RZZ count, one for one** -- which is what
makes the ablation lever of section 4 priceable.

Per compiled circuit, over the 44 circuits of the production set:

| quantity | mean | min | max |
|---|---|---|---|
| RZZ (native two-qubit) | 2158 | 2158 | 2158 |
| one-qubit gates (physical rz) | 7310 | 7247 | 7347 |
| of which rz | 4257 | 4255 | 4261 |
| one-qubit gates (virtual rz) | 3053 | - | - |
| depth | 5655 | 5641 | 5677 |
| measured qubits | 20 | 20 | 20 |

Reproduction checks: the k = 1 coarse step compiles to
2158 RZZ and
7346 one-qubit gates, identical to
`validation/S2D.json` `data.2x3.per_circuit[0]`
(match); in the CZ basis the
same step is 2164 CZ, identical to `validation/S2.json`
(match).  The RZZ
count is the same, 2158, for every circuit of the set: k and the reference change
the angles, not the structure.  Only the one-qubit count moves
(7247..7347), which is why the per-circuit spread of f is
0.37 % (section 3).

## 2. The feasible region

Take -log of the f model: the criterion `mean f >= 0.1` is, at the mean
gate counts, the half-space

> 2158 x (-ln(1 - eps2)) + 7310 x (-ln(1 - eps1)) + 20 x (-ln(1 - eps_ro)) <= ln(1/0.1) = 2.302585

or, to first order in the errors,
2158 eps2 + 7310 eps1 + 20 eps_ro <= 2.3026.
With a virtual-rz frame change the one-qubit weight drops to
3053.  **This single inequality is the requirement**; everything
below is a slice of it.  A vendor can answer it with three numbers.

How the declared triple (eps2 = 1e-03, eps1 =
1e-04, eps_ro = 2e-03) spends that budget:

| channel | gates per circuit | log-error spent | share of the ln(1/0.1) budget | share of the total loss |
|---|---|---|---|---|
| 2q | 2158 | 2.1591 | 93.8 % | 73.7 % |
| 1q | 7310 | 0.7310 | 31.7 % | 24.9 % |
| ro | 20 | 0.0400 | 1.7 % | 1.4 % |

Total spent 2.9302 against a budget of 2.3026: over by
0.6276 in log terms, i.e. f is a factor
1.87 too small.  The two-qubit channel alone spends
93.8 % of the budget and the one-qubit channel
31.7 %; readout spends
1.7 %.

### 2a. Required two-qubit error as a function of the other two channels

The eps2 that makes the criterion hold exactly, at each (eps1, eps_ro).  The mean and worst
columns are the two halves of the criterion; the binding one is the smaller.

| eps_ro | eps1 | eps2 for mean f >= 0.1 | eps2 for worst f >= 0.05 | eps2 for mean f >= 0.1, virtual rz |
|---|---|---|---|---|
| 1e-03 | 0 (virtual/ideal) | 1.057e-03 | 1.378e-03 | 1.057e-03 |
| 1e-03 | 1e-05 | 1.023e-03 | 1.344e-03 | 1.043e-03 |
| 1e-03 | 2e-05 | 9.895e-04 | 1.310e-03 | 1.029e-03 |
| 1e-03 | 5e-05 | 8.880e-04 | 1.208e-03 | 9.865e-04 |
| 1e-03 | 1e-04 | 7.187e-04 | 1.038e-03 | 9.158e-04 |
| 1e-03 | 2e-04 | 3.801e-04 | 6.977e-04 | 7.745e-04 |
| 1e-03 | 5e-04 | not reachable | not reachable | 3.502e-04 |
| 2e-03 | 0 (virtual/ideal) | 1.048e-03 | 1.369e-03 | 1.048e-03 |
| 2e-03 | 1e-05 | 1.014e-03 | 1.335e-03 | 1.034e-03 |
| 2e-03 | 2e-05 | 9.802e-04 | 1.301e-03 | 1.020e-03 |
| 2e-03 | 5e-05 | 8.787e-04 | 1.199e-03 | 9.772e-04 |
| 2e-03 | 1e-04 | 7.094e-04 | 1.029e-03 | 9.066e-04 |
| 2e-03 | 2e-04 | 3.708e-04 | 6.884e-04 | 7.652e-04 |
| 2e-03 | 5e-04 | not reachable | not reachable | 3.409e-04 |
| 5e-03 | 0 (virtual/ideal) | 1.020e-03 | 1.341e-03 | 1.020e-03 |
| 5e-03 | 1e-05 | 9.862e-04 | 1.307e-03 | 1.006e-03 |
| 5e-03 | 2e-05 | 9.523e-04 | 1.273e-03 | 9.918e-04 |
| 5e-03 | 5e-05 | 8.508e-04 | 1.171e-03 | 9.494e-04 |
| 5e-03 | 1e-04 | 6.816e-04 | 1.001e-03 | 8.787e-04 |
| 5e-03 | 2e-04 | 3.430e-04 | 6.605e-04 | 7.373e-04 |
| 5e-03 | 5e-04 | not reachable | not reachable | 3.130e-04 |
| 1e-02 | 0 (virtual/ideal) | 9.734e-04 | 1.294e-03 | 9.734e-04 |
| 1e-02 | 1e-05 | 9.395e-04 | 1.260e-03 | 9.592e-04 |
| 1e-02 | 2e-05 | 9.057e-04 | 1.226e-03 | 9.451e-04 |
| 1e-02 | 5e-05 | 8.042e-04 | 1.124e-03 | 9.027e-04 |
| 1e-02 | 1e-04 | 6.349e-04 | 9.541e-04 | 8.320e-04 |
| 1e-02 | 2e-04 | 2.963e-04 | 6.139e-04 | 6.907e-04 |
| 1e-02 | 5e-04 | not reachable | not reachable | 2.663e-04 |

Reading: eps_ro barely moves the requirement (20 measured qubits against
2158 two-qubit gates), eps1 moves it strongly (there are
7310 one-qubit gates, 4255..4261 of
them rz), and the mean criterion is always the binding half -- the worst-circuit column is looser
by construction, because the spread over the set is
0.37 %.

### 2b. Marginal requirement on each channel

Each channel at the criterion with the other two held at the declared values:

| channel | gates per circuit | declared | required for mean f >= 0.1 | required for worst f >= 0.05 | improvement needed | gates (virtual rz) | required, virtual rz |
|---|---|---|---|---|---|---|---|
| two-qubit error eps2 | 2158 | 1e-03 | 7.094e-04 | 1.029e-03 | 1.41x | 2158 | 9.066e-04 |
| one-qubit error eps1 | 7310 | 1e-04 | 1.415e-05 | 1.084e-04 | 7.07x | 3053 | 3.389e-05 |
| readout error eps_ro | 20 | 2e-03 | not reachable | 5.083e-03 | - | 20 | not reachable |

Three facts a vendor should read off this table.

1. **Readout alone cannot satisfy the criterion.**  At the declared eps2 and eps1 the two-qubit
   and one-qubit factors already multiply to below 0.1, so no readout
   error, not even zero, reaches the criterion.  Readout is a constraint only once the other two
   channels are inside the region (section 2a).
2. **The one-qubit channel is a real requirement, not a rounding error.**  Holding eps2 at the
   declared 1e-03, the criterion needs eps1 <=
   1.415e-05 -- a factor
   7.1 below the declared value.
   With virtual rz that relaxes to 3.389e-05.
3. **A uniform improvement of all three channels by a factor
   1.272** also satisfies the criterion (candidate R3 below); with virtual rz the factor is
   1.088.

### 2c. Tolerable routing overhead

If the device is not all-to-all, the same step executes rho x
2158 two-qubit gates.  Holding the one-qubit count fixed (optimistic
-- routing adds one-qubit gates too, see the measured row):

| routing overhead rho | two-qubit gates | eps2 required (physical rz) | eps2 required (virtual rz) |
|---|---|---|---|
| 1.00x | 2158 | 7.094e-04 | 9.066e-04 |
| 1.25x | 2698 | 5.675e-04 | 7.252e-04 |
| 1.50x | 3237 | 4.730e-04 | 6.045e-04 |
| 1.75x | 3776 | 4.055e-04 | 5.182e-04 |
| 2.00x | 4316 | 3.548e-04 | 4.534e-04 |
| 2.50x | 5395 | 2.838e-04 | 3.627e-04 |
| 2.53x (measured, heavy-hex d = 5) | 5477 | 9.420e-05 | - |

The last row is the fully measured heavy-hex point of `validation/S2.json`
(5477 CZ and 17465 one-qubit gates after routing on a d = 5 map): a heavy-hex device
would need eps2 <= 9.420e-05.  **Routing overhead is the most expensive
single property in this table.**  The pure two-qubit effect is the rho = 2.50 row above
(2.838e-04),
but routing also multiplies the one-qubit count by
2.39x, so the measured requirement is a factor
7.5 tighter than at all-to-all, not a factor
2.5.  **All-to-all connectivity is worth a factor
7.5 in two-qubit error** for this circuit.

## 3. Candidate error sets: mean and worst f over the 44 circuits

Both halves of the criterion, for every candidate, with the shot rule of manual Step 4.4
(p = 1e-03, k = 3, confidence
0.95, y = 0.82 f (clean shots, manual Step 4.4)) in the B = 0 sector:

| error set | eps2 | eps1 | eps_ro | virtual rz | mean f | worst f | criterion | N per circuit (B=0) | N per sector (B=0) |
|---|---|---|---|---|---|---|---|---|---|
| D0: declared inputs of gate S2D | 1.000e-03 | 1.000e-04 | 2.000e-03 | no | 0.0534 | 0.0532 | FAIL | 143921 | 4.605e+06 |
| D0v: declared inputs, virtual rz | 1.000e-03 | 1.000e-04 | 2.000e-03 | yes | 0.0817 | 0.0814 | FAIL | 94031 | 3.009e+06 |
| R1: the amendment's eps2, declared eps1/eps_ro | 7.094e-04 | 1.000e-04 | 2.000e-03 | no | 0.1000 | 0.0996 | PASS | 76839 | 2.459e+06 |
| R1v: minimum eps2 with virtual rz | 9.066e-04 | 1.000e-04 | 2.000e-03 | yes | 0.1000 | 0.0996 | PASS | 76844 | 2.459e+06 |
| R2: declared eps2, minimum eps1 | 1.000e-03 | 1.415e-05 | 2.000e-03 | no | 0.1000 | 0.0999 | PASS | 76787 | 2.457e+06 |
| R3: all three declared errors scaled by the same factor | 7.859e-04 | 7.859e-05 | 1.572e-03 | no | 0.1000 | 0.0997 | PASS | 76826 | 2.458e+06 |
| R4: round vendor point eps2 = 5e-4 | 5.000e-04 | 1.000e-04 | 2.000e-03 | no | 0.1572 | 0.1566 | PASS | 48884 | 1.564e+06 |
| R5: round vendor point eps2 = 5e-4, eps_ro = 5e-3, virtual rz | 5.000e-04 | 1.000e-04 | 5.000e-03 | yes | 0.2265 | 0.2257 | PASS | 33921 | 1.085e+06 |
| H1: today's Heron (live ibm_fez patch) AS IF all-to-all | 2.348e-03 | 0.000e+00 | 9.583e-03 | no | 0.0052 | 0.0052 | FAIL | 1486448 | 4.757e+07 |
| H2: FakeFez snapshot patch AS IF all-to-all | 3.047e-03 | 0.000e+00 | 7.455e-03 | no | 0.0012 | 0.0012 | FAIL | 6459098 | 2.067e+08 |
| H3: today's Heron on the ROUTED 2x3 circuit (what it would run) | 2.348e-03 | 0.000e+00 | 9.583e-03 | no | 2.111e-06 | 2.111e-06 | FAIL | 3637376980 | 1.164e+11 |

The worst circuit is the same one throughout (B=0 ref169 k1) and sits
0.37 % below the mean, so the
worst >= 0.05 half of the criterion is never the binding one at 2x3; at
the declared inputs it is in fact already satisfied (worst f = 0.0532) while the mean
half fails.  The spread is small because every circuit of the set has the same
2158 RZZ gates; it is reported here because the criterion constrains it, not
because it is at risk.  What a single number *does* hide is the trade-off: rows R1, R1v, R2 and R3
all satisfy the criterion on four devices with different two-qubit errors
(7.094e-04, 9.066e-04, 1.000e-03, 7.859e-04).

The last three rows are the gap to today's hardware, from this repository's own measurements.
Row H3 is the honest one: a heavy-hex Heron must route, so it executes 5477 two-qubit
gates, and at the live edge error measured on ibm_fez it reaches mean f =
2.111e-06 -- 47375 times below the criterion.
Rows H1 and H2 grant a Heron all-to-all connectivity it does not have and set eps1 = 0, and even
then reach only 0.0052
and 0.0012.

## 4. What would relax the requirement, and what is already spent

| lever | what it changes | f at the declared inputs | eps2 requirement for mean f >= 0.1 | status |
|---|---|---|---|---|
| virtual rz (platform property) | 4257 of the 7310 one-qubit gates per circuit carry no error | 0.0534 -> 0.0817 | 7.094e-04 -> 9.066e-04 | UNSPENT |
| fixed-angle generator (validation/S2_fixed.json) | 1626 CZ / 1620 RZZ against 2164 CZ / 2158 RZZ exact | 0.1105 (virtual rz 0.1525) | 1.062e-03 (virtual rz 1.260e-03) | UNSPENT on an all-to-all device |
| term ablation: no plaq1 (interior-corner plaquette) | 1400 CZ / 1394 RZZ | 0.1469 (virtual rz 0.1930) | 1.276e-03 | UNSPENT (recall at f = 0.1: B=0 0.977, B=1 0.937 against the S1 criterion 0.9) |
| term ablation: no plaquettes | 1186 CZ / 1180 RZZ | 0.1958 (virtual rz 0.2465) | 1.569e-03 | SPENT (recall at f = 0.1: B=0 0.930, B=1 0.895 against the S1 criterion 0.9) |
| connectivity | all-to-all 2164 CZ, grid best 4026, heavy-hex best 5401, line 7052 | - | - | SPENT (all-to-all is the floor) |
| fixed angles + no plaq1 + virtual rz (combined) | 1218 RZZ | 0.2397 | 1.717e-03 | UNSPENT but the recall of the combination is UNMEASURED |

The f column is the 44-circuit mean in the virtual-rz row and the
single k = 1 circuit of the first B = 0 reference in the generator and ablation rows; the RZZ count
is identical across the set, so the two readings differ by under
0.37 %.  Plainly:

* **Connectivity: SPENT.**  The requirement in section 2 is already quoted at all-to-all,
  which is the floor (2164 CZ against
  4026 on the best of 8 grid seeds,
  5401 heavy-hex, 7052 on a line;
  `data/S2_escalation_experiments.json`).  There is nothing left to win here -- only to lose, by
  choosing a device that routes.
* **Virtual rz: UNSPENT, and cheap.**  It is a property of the platform, not of the circuits:
  4255..4261 of the 7247..7347
  one-qubit gates are rz.  It moves mean f from 0.0534 to
  0.0817 and the two-qubit requirement from
  7.094e-04 to 9.066e-04 -- a
  28 %
  relaxation for free.  **It should be a line item in the specification.**
* **The fixed-angle generator: UNSPENT on an all-to-all device.**  Gate S2_fixed was stopped on
  cost, but the cost that stopped it was the *routed* heavy-hex count
  (3736 CZ against the old 500-CZ budget of manual Step 4.3).
  On an all-to-all device there is no routing: it compiles to
  1620 RZZ against 2158 for the exact
  generator, i.e. 25 % fewer
  two-qubit gates, which relaxes the two-qubit requirement to
  1.062e-03 (1.260e-03 with virtual rz).
  Its price is that it is a *different generator*: per-term deviation from exp(-i theta H) is about
  1e-1 instead of 1e-14, and it is justified only by the S1 recall criterion, which it meets
  (2x3 B=0 1.0, 2x3 B=1 0.937).
  Amendment 01 section 1(b) does not adopt it; this is an owner decision, and it is the single
  largest device-side relaxation available.
* **Term ablation: partly unspent.**  Dropping the interior-corner plaquette `plaq1` leaves
  1394 RZZ and relaxes the
  requirement to
  1.276e-03,
  at a measured recall of
  0.977 (B = 0) and
  0.937 (B = 1) against the S1
  criterion of 0.9 -- so it is still available.  Dropping *both* plaquettes gives
  1180 RZZ but recall
  0.895 in B = 1, **below the S1 criterion**: that
  lever is spent.
* **Combined (fixed angles + no plaq1 + virtual rz): unmeasured.**  It would need only eps2 <=
  1.717e-03 at 1218 RZZ, but the recall
  of that *combination* has never been emulated -- each lever was measured alone.  Nothing may be
  claimed for it until that emulation is run (one S1-style run, about the cost of
  `scripts/s2_escalation_experiments.py`).
* **The shot quota is not a device lever.**  It is open item 5 of the amendment and is being
  decided separately; it changes what f the run can afford, not what f the device delivers.

## 5. Vendor-facing summary

| what the device must deliver | requirement | at these circuit counts | what this repository measures on today's Heron |
|---|---|---|---|
| qubits | 20 | - | 30 frozen-set qubits on ibm_fez |
| connectivity | all-to-all preferred; the requirement below is quoted at zero routing overhead, and the tolerable overhead is tabulated | - | heavy-hex: 2.53x routing overhead measured (5477 CZ) |
| native two-qubit gate | RZZ(theta), continuous angle | 2158 per circuit | CZ only: 2164 per circuit all-to-all |
| two-qubit error eps2 | 7.094e-04 | declared 1e-03 | 2.348e-03 (live ibm_fez, 3.31x too high) |
| two-qubit error eps2, virtual rz | 9.066e-04 | - | 2.59x too high |
| one-qubit error eps1 (physical rz) | 1.415e-05 | declared 1e-04, 7310 gates per circuit | not resolved per gate in this repository's Heron measurements |
| one-qubit error eps1 (virtual rz) | no requirement on rz | 3053 error-carrying gates per circuit | - |
| readout error eps_ro | 2.431e-02 once eps2 = 5e-4 (at eps1 = 1e-04) | declared 2e-03, 20 measured qubits | 9.583e-03 (live ibm_fez) |
| mid-circuit measurement / reset | not required: the circuits measure once, at the end | 20 measurements and 1 barrier per circuit, at the end | - |
| circuit depth | 5655 (mean), 5677 (max) | - | - |

Requirement in one paragraph, for a vendor who reads nothing else:

> 20 qubits; all-to-all connectivity (or a routing overhead of at most
> 1.42x if the two-qubit error is 5e-4, i.e.
> at most 3062 two-qubit gates in the circuit);
> a native two-qubit RZZ(theta) with a continuous angle; one
> circuit of 2158 two-qubit gates, 7310 one-qubit gates
> and depth 5655, measured once at the end on all 20 qubits (no mid-circuit
> measurement, no reset).  Two-qubit error at most 7.094e-04
> (9.066e-04 if rz is a virtual frame change);
> one-qubit error at most 1.415e-05 if the
> two-qubit error only reaches 1e-3, and no requirement on rz at all if rz is virtual; readout
> error at most 2.431e-02 once the two-qubit error is
> 5e-4.  Any triple satisfying
> 2158 eps2 + 7310 eps1 + 20 eps_ro
> <= 2.303 qualifies.

The gap to today's hardware, from this repository's measurements only: the live ibm_fez
target of 2026-09-21T14:53:59-06:00 (frozen patch, 54 directed edges) gives a
mean CZ edge error of 2.348e-03 and a mean readout error of
9.583e-03 on the patch its own layout preferred, against the
FakeFez snapshot values 3.047e-03 and
7.455e-03 that the 2x2 row of the
amendment is built on.  The two-qubit error must therefore come down by a factor
3.31
(2.59 with virtual rz) *and*
the routing overhead of 2.53x must disappear, before a
Heron-class device meets the 2x3 requirement.  That is the whole content of the 2x3 device
question: it is not a marginal calibration improvement.

## 6. What this does not decide

* It does not adopt the fixed-angle generator or any term ablation (amendment 01 section 1(b);
  owner decision).  It prices them.
* It does not name a device, a vendor or a product, and asserts no vendor specification.
* It does not change gate S2D's status: S2D stays **FAIL** while the 2x3 device is unspecified,
  and `validation/S2.json`, `validation/S2D.json` and `validation/S2_fixed.json` are untouched.
* It does not touch open item 5 (the shot quota of manual Step 9.2).

## Provenance

Inputs read (values in `data/S2D_2x3_device_requirements.json` -> `sources`):
`validation/S2.json` (2x3 per-term and coarse-step CZ counts),
`validation/S2D.json` (declared inputs, the 44-circuit RZZ counts, the recorded f and the 2x2
FakeFez patch errors), `validation/S2_fixed.json` (the fixed-angle cost and recall),
`data/S2_escalation_experiments.json` (coupling-map and term ablations),
`validation/H0P_ibm_fez.json` (the live ibm_fez calibration of 20260921T2053Z, produced
by `gate_S2D.analyse_on_backend`).  The f model and the counts come from
`gate_S2D.analyse_rzz`; the inversion from `skqd.device_req`
(80 passed, 5 warnings in 105.53s (0:01:45)).  Counts used for the region:
recomputed here.

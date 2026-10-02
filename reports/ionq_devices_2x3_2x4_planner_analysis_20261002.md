# 2x3 and 2x4 on ibm_kingston, and on IonQ — planner analysis (2026-10-02)

- date: 2026-10-02
- git commit at writing: 8ec5db8 (`git rev-parse --short HEAD`)
- prompt in force: `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` (H0_2x2 PASS); this analysis
  backs `prompts/25_2x3_2x4_kingston_check_and_ionq_prep.md`
- related: `reports/S2D_2x3_device_requirements.md`, `reports/S2_2x4_compilation_and_device_requirement.md`,
  `reports/S2D_levers_2x2_kingston.md`, `reports/ibm_decoherence_literature_20261002.md`,
  `data/ionq_2x3_feasibility_20261001.json`, `validation/H0_ddtest.json`, `validation/H0_2x2.json`
- QPU seconds spent by this analysis: 0.  Nothing was submitted anywhere.

Every number below is either read from a file of this repository (path given), from a vendor or
literature page fetched on 2026-10-02 (URL given, quoted verbatim where it matters), or is marked
**planner arithmetic** / **ESTIMATE** with the inputs it was computed from.  The planner arithmetic was
run once in `scratch/planner/ionq_feasibility_prototype_20261002.json` and
`scratch/planner/ionq_cost_rows_20261002.json` (committed with this report); the executor recomputes
all of it in scripts under prompts/25 and the gate JSONs replace these scratch numbers.

Jargon used below, defined once: **clean-shot fraction f** = the probability that one shot of a circuit
suffers no error at all (manual Step 4.4; `src/skqd/device_req.py`): $f = (1-\epsilon_2)^{n_{2q}}
(1-\epsilon_1)^{n_{1q}} (1-\epsilon_{ro})^{n_{meas}} \times e^{-S_{\rm idle}}$, where $\epsilon_2,
\epsilon_1, \epsilon_{ro}$ are the two-qubit, one-qubit and readout error rates, $n$ the gate counts and
$S_{\rm idle}$ the idle-time (decoherence) budget in nats.  **Signed budget** = amendment 01 item 2: mean
$f \ge 0.1$ over the circuit family and worst $f \ge 0.05$.  **Virtual rz** = a Z rotation done by
bookkeeping of the phase of later pulses, so it carries no error (IonQ: "phase propagation").
**DRB** = direct randomized benchmarking, the method IonQ uses to quote two-qubit fidelity.
**SPAM** = state preparation and measurement error.  **ALAP** = as-late-as-possible scheduling.
**XY4** = the four-pulse dynamical-decoupling sequence X-Y-X-Y that refocuses slow dephasing in idle
windows.

---

## 1. What was asked

The owner (2026-10-02): "check 2x3 is ready to run on ibm kingston machine using the techniques we used
for 2x2 case, if not prepare it for ionq devices and let me know, i will try to get access to ionq qpus.
same for 2x4."

The 2x2 techniques (validation/H0_2x2.json, H0_ddtest.json, prompts/24): the signed term family with
ALAP scheduling, client-side XY4 in idle windows $\ge 1.024\,\mu$s (cell T3, gain $R = 2.819$
[95 %: 2.495, 3.185] on the pilot baseline, `validation/H0_ddtest.json data.decision.cells.T3`),
idle-aware patch selection, D3' shot planning, the D9 fingerprint guard.  Result: pooled $k = 1$
$f = 0.1271$ [0.1084, 0.1479] (`validation/H0_2x2.json data.clean_fraction`), 102 of 600 s used.

## 2. Verdict for ibm_kingston: 2x3 and 2x4 are NOT ready, and no 2x2 technique can make them ready

### 2.1 The bound that settles it

Dynamical decoupling, scheduling and patch selection act only on the idle term $e^{-S_{\rm idle}}$ and on
*which* edges are used.  They cannot reduce the number of two-qubit gates, and every CZ carries at
least the error of the best edge on the device.  So, with zero one-qubit error, zero readout error and
zero idle time (the most favourable case any technique can reach),

$$ f \;\le\; (1-\epsilon_{2,\min})^{\,n_{\rm CZ}} . $$

If this ceiling is below 0.05 the signed budget fails for every patch, every schedule and every DD
sequence.

### 2.2 Inputs (all from repository files)

| quantity | value | source |
|---|---|---|
| 2x3 CZ per coarse step, all-to-all (unroutable on heavy-hex; a lower bound on any IBM count) | 2164 | `validation/S2.json data.2x3.coarse_step.all_to_all.cz` |
| 2x3 CZ per coarse step, routed on heavy-hex d = 5 (57 physical qubits) | 5477 | `validation/S2.json data.2x3.coarse_step.routed.cz` (best of 8 seeds 5401: `data/S2D_2x3_device_requirements.json levers.connectivity.heavy_hex_best_cz`) |
| 2x3 one-qubit gates in the routed circuit | 17465 (sx 11350 + rz 5513 + x 602) | `validation/S2.json data.2x3.coarse_step.routed.ops`; `data/S2D_2x3_device_requirements.json feasible_region.measured_routed_heavy_hex_point.n_1q` |
| 2x4 CZ per coarse step, all-to-all | 69688 | `validation/S2_2x4.json data.compile_4_exact_perterm.structure_identity.all_to_all` |
| 2x4 CZ per coarse step, routed on FakeFez (Heron r2) | 148726 | `validation/S2_2x4.json data.schedule_4_exact.rows["2x4\|B0_ref0_k1\|fakefez"].n_cz` |
| ibm_kingston record of the H0_2x2 day: CZ error over the 342 calibrated edges (10 edges carry the uncalibrated marker 1.0) — minimum / 10th percentile / median | $8.164\times10^{-4}$ / $1.146\times10^{-3}$ / $1.804\times10^{-3}$ | `data/hardware/H0_ddtest_prep/ibm_kingston_full_20261002T1906Z.json edges.*.cz_error` (planner arithmetic over the file; the executor reproduces it in gate K0) |
| same record: sx error median, readout error median, $T_2$ median, CZ duration | $2.44\times10^{-4}$, $8.97\times10^{-3}$, $147\,\mu$s, 68 ns (80 and 108 ns on some edges) | same file, `qubits.*` and `edges.*` |
| 2x3 on the 2026-10-01 kingston record, gate-only f at the device median CZ error, 5477 CZ | $2.14\times10^{-5}$ | `validation/S2D_levers.json data.information.2x3_on_ibm.f_gates_median` |

### 2.3 The ceilings (planner arithmetic, $f \le (1-\epsilon_{2,\min})^{n_{\rm CZ}}$ with the record's best edge)

| circuit | $n_{\rm CZ}$ | ceiling at $\epsilon_{2,\min} = 8.164\times10^{-4}$ | at the 10th percentile | at the median | $\epsilon_2$ that would be needed for $f = 0.05$ with nothing else wrong | signed bar |
|---|---|---|---|---|---|---|
| 2x3 routed (5477) | 5477 | $1.14\times10^{-2}$ | $1.87\times10^{-3}$ | $5.07\times10^{-5}$ | $5.47\times10^{-4}$ ($4.20\times10^{-4}$ for $f = 0.1$) | **FAIL** by 4.4x even at the ceiling |
| 2x3 all-to-all (2164; not routable on heavy-hex, shown as the absolute floor) | 2164 | $1.71\times10^{-1}$ | $8.4\times10^{-2}$ | $2.0\times10^{-2}$ | $1.38\times10^{-3}$ | would pass only if every one of 2164 CZ sat on the single best edge, which routing on a heavy-hex lattice cannot do (the routed count is 2.53x higher: `measured_routed_heavy_hex_point.routing_overhead_vs_all_to_all`) |
| 2x4 routed on Heron (148726) | 148726 | $1.8\times10^{-53}$ | $8.8\times10^{-75}$ | $2.3\times10^{-117}$ | $2.0\times10^{-5}$ | **FAIL** by 53 orders of magnitude |
| 2x4 all-to-all (69688) | 69688 | $1.9\times10^{-25}$ | — | — | $4.3\times10^{-5}$ | FAIL |

Adding the one-qubit gates of the routed 2x3 circuit at the record's median sx error multiplies the
ceiling by $(1-2.44\times10^{-4})^{17465} = e^{-4.26} = 0.014$, and the 20 readouts at the median by
$0.835$: the 2x3 gate-only f on the best imaginable patch is about $1.3\times10^{-4}$, and with the
realistic edge mix (median) about $5\times10^{-5}$, consistent with the $2.1\times10^{-5}$ recorded in
`validation/S2D_levers.json` on the previous day's record.

Idle time on top: the routed 2x3 circuit has depth 11540 (`validation/S2.json data.2x3.coarse_step.routed.depth`)
against the 2x2 canary's 455 CZ-depth and 46.4 $\mu$s (`validation/S2D_levers.json data.rows.L1_seed_alap`);
the 2x2 ran at $S_{T2} \approx 1.0$ nat (`data.anchor_i.computed.S_T2 = 0.995`) and XY4 bought a factor
2.8.  A 2x3 circuit of 25x the CZ depth on qubits with median $T_2 = 147\,\mu$s is far outside the
regime where a factor 2.8 matters.  The 2x4 report already states the coherence requirement for 2x4
on Heron: $T_2/t_{2q} \ge 6.3874\times10^{5}$ for the all-to-all circuit (69688 CZ, Heron timings,
$f = 0.1$, $T_1 \to \infty$) and $8.5853\times10^{5}$ for the FakeFez-routed one (148726 CZ)
(`reports/S2_2x4_compilation_and_device_requirement.md`, table "T2/t_2q measured", rows
`2x4 / exact / B0_ref0_k1 / all_to_all` and `/ fakefez`), against the record's $T_2/t_{\rm CZ}$
harmonic mean of 1038 (same report, "What a real device has").

### 2.4 Verdict

- **2x3 on ibm_kingston: NO-GO.**  Decisive number: the gate-only ceiling $f \le 1.14\times10^{-2}$
  (5477 routed CZ at the record's best edge error $8.164\times10^{-4}$), below the signed worst-case
  bar 0.05 by 4.4x before one-qubit, readout and idle errors, which lower it to $\sim 10^{-4}$.  The 2x2
  techniques (DD, ALAP, patch selection) act on terms that are already set to zero in the ceiling.
- **2x4 on ibm_kingston: NO-GO.**  Decisive number: 148726 routed CZ need $\epsilon_2 \le 2.0\times10^{-5}$
  for $f = 0.05$; the best edge is 41x worse.  Ceiling $f \le 10^{-53}$.
- What a kingston run of 2x3 **could** still test, if the owner wanted one anyway: nothing about the
  2x3 physics; a 2x3 job at $f \sim 10^{-4}$ returns the garbage distribution (prompts/20: garbage
  saturation).  It is not recommended.

No 2x2 technique changes this, and no circuit-cost lever available without the owner's signature does
either: the fixed-angle 2x3 generator (1626 all-to-all CZ, 3736 routed; `validation/S2_fixed.json`)
has a ceiling $(1-8.164\times10^{-4})^{3736} = 0.047 < 0.05$ at the best edge alone.

## 3. IonQ: devices accessible today, with sources

Pages fetched 2026-10-02.  Quotes are verbatim.

| device | status today | qubits | 2q error | 1q error | SPAM | $T_1$, $T_2$ | gate times | native gates | source |
|---|---|---|---|---|---|---|---|---|---|
| **Forte** (`qpu.forte-1`) | "Operational" on status.ionq.co (maintenance completed 2026-09-29) | 36 | "0.4%" ("Direct Randomized Benchmarking") | "0.02%" | "0.5%" | "10–100s, ~1s" | not on the page; literature: "around 950 microseconds for the two-qubit ZZ gates and around 130 microseconds for single-qubit gates" | GPi, GPi2, ZZ (virtual Z by phase propagation) | https://ionq.com/quantum-systems/forte ; https://status.ionq.co/ ; arXiv:2506.07866v2 Sec. IV.1 (https://arxiv.org/html/2506.07866v2) ; https://docs.ionq.com/guides/getting-started-with-native-gates |
| **Forte Enterprise** (`qpu.forte-enterprise-1`) | "Operational" (job-processing outage resolved 2026-09-30) | 36 | "0.4%" | "0.02%" | "0.5%" | "10–100s, ~1s" | same class; literature as Forte | GPi, GPi2, ZZ | https://ionq.com/quantum-systems/forte-enterprise ; Azure: "The base quantum computing hardware and performance are the same" (https://learn.microsoft.com/en-us/azure/quantum/provider-ionq, updated 2026-08-29) |
| Forte / Forte Enterprise, **measured on a day** | — | 36 | "median direct randomized benchmarking (DRB) fidelities for these entangling gates were 99.3% on Forte and 99.5% on Forte Enterprise" | "around 99.98%" | — | — | 950 $\mu$s / 130 $\mu$s | ZZ | arXiv:2506.07866v2 Sec. IV.1 (IonQ authors) |
| Aria (`qpu.aria-1`, `-2`) | **"Retired in 2026"** on ionq.com; "qpu.aria-1 – 25 qubits (Retired)" in the backends manual; still listed on the Azure page of 2026-08-29 (stale) | 25 | "0.6%" (ionq.com) / "99.6% (not SPAM corrected)" (Azure) | "0.06%" / "99.95% (SPAM corrected)" | "0.39%" / "99.61%" | "10-100 s", "1 s" | "135 µs" 1q, "600 µs" 2q (Azure) | GPi, GPi2, MS | https://www.ionq.com/quantum-systems/aria ; https://docs.ionq.com/user-manual/backends ; Azure page above |
| Tempo | "Late 2026 (projected)"; "Inquire about IonQ Tempo"; **targets, not specifications** | 100 (target) | "99.9%" (target) | "99.99%" (target) | not published | not published | "faster gate speeds" (no number) | not published; "Many-to-many" connectivity | https://www.ionq.com/quantum-systems/compare ; https://ionq.com/quantum-systems/tempo |

Native-gate definitions (https://docs.ionq.com/guides/getting-started-with-native-gates, parameters in
**turns**, 1 turn $= 2\pi$):
$\mathrm{GPi}(\phi) = \begin{pmatrix} 0 & e^{-2\pi i\phi} \\ e^{2\pi i\phi} & 0 \end{pmatrix}$,
$\mathrm{GPi2}(\phi) = \tfrac{1}{\sqrt2}\begin{pmatrix} 1 & -i e^{-2\pi i\phi} \\ -i e^{2\pi i\phi} & 1 \end{pmatrix}$,
$\mathrm{ZZ}(\theta) = \exp(-i\pi\theta\, Z\otimes Z) = \mathrm{diag}(e^{-i\pi\theta}, e^{i\pi\theta}, e^{i\pi\theta}, e^{-i\pi\theta})$
("Parameter range stated as any floating-point value. No explicit precision statement given"; for the
Aria MS partial angle the page says "the physical hardware is limited to around three decimal places of
precision" — the executor must check whether the same applies to ZZ by a dry run on IonQ's own
simulator, see prompts/25 step B6).  In our convention $\mathrm{RZZ}(\varphi) = \exp(-i\tfrac{\varphi}{2} Z\otimes Z)$,
so $\theta = \varphi / 2\pi$.  Z rotations: "we do not expose or implement a 'true' Z gate" — they are
absorbed into the $\phi$ of later GPi/GPi2 (virtual rz).

Access routes and prices (fetched 2026-10-02):

| route | devices | price | notes | source |
|---|---|---|---|---|
| IonQ Quantum Cloud (direct REST, `POST https://api.ionq.co/v0.4/jobs`, header `Authorization: apiKey <key>`) | `qpu.forte-1`, `qpu.forte-enterprise-1`, `simulator` (noise models `forte-1`, `forte-enterprise-1`, up to 29 qubits) | "Your particular rates, credit units, and cost model may vary depending on your access agreement with IonQ"; `GET /jobs/estimate` returns the cost for your key; "Debiasing is enabled by default for jobs with 500 or more shots" | API: `shots` 1–1,000,000; `input.gateset` "qis" or "native"; `settings.error_mitigation.debiasing` boolean; `dry_run` boolean; multi-circuit jobs "max 5,000 circuits, 150,000 total gates", body 10 MB | https://docs.ionq.com/api-reference/v0.4/jobs/create-job ; https://docs.ionq.com/guides/job-cost-and-usage ; https://docs.ionq.com/guides/direct-api-submission ; https://docs.ionq.com/features/simulation-with-noise-models |
| Amazon Braket | "IonQ Forte": "$0.30000" per task, "$0.08000" per shot; Forte Enterprise on Braket since 2025-03-31 (us-east-1) | flat per shot, independent of circuit depth; "IonQ QPUs require a minimum of 2,500 shots per task when using error mitigation"; reservation "$7,000.00" per hour | the Braket page lists only "IonQ Forte" in its table; the Forte Enterprise rate is not on the page (ask AWS/IonQ) | https://aws.amazon.com/braket/pricing/ ; https://aws.amazon.com/about-aws/whats-new/2025/03/ionq-forte-enterprise-amazon-braket |
| Azure Quantum (pay-as-you-go) | Forte 1, Forte Enterprise 1: "USD0.0001645 / 1-qubit-gate shot", "USD0.001121 / 2-qubit-gate shot", minimum per program "USD168.195 - default setting, error mitigation is on", "USD25.7899 if error mitigation is off"; Aria 1 still listed at USD0.000220 / USD0.000975, min USD97.50 / USD12.4166 | per gate-shot: cost scales with circuit depth; subscription "USD25,000/Month" | https://learn.microsoft.com/en-us/azure/quantum/pricing (updated 2026-04-23) |
| qBraid | Forte-1, Forte-Enterprise-1: "30 credits" per task, "8 credits" per shot, "Each qBraid credit is worth $0.01 USD" (= $0.30 / $0.08, the Braket rates) | | https://docs.qbraid.com/v2/home/pricing |

## 4. Feasibility of 2x3 and 2x4 on IonQ

### 4.1 Gate counts used (repository files)

| lattice | qubits | 2q gates (RZZ/ZZ, all-to-all) | 1q with virtual rz | 1q with physical rz | measured | source |
|---|---|---|---|---|---|---|
| 2x2 (information) | 12 | 256 | 541 | 920 | 12 | `validation/S2.json data.2x2.coarse_step.all_to_all.ops` |
| 2x3 | 20 | 2158 | 3053 | 7310 | 20 | `data/S2D_2x3_device_requirements.json counts.coarse_step` (RZZ basis) |
| 2x4 (CZ count used as the ZZ proxy; the executor compiles the real one) | 28 | 69688 | 138711 (sx 136996 + x 1715) | 209395 (+ rz 70684) | 28 | `validation/S2_2x4.json data.schedule_4_exact.rows["2x4\|exact\|B0_ref0_k1\|all_to_all"].ops` |
| 2x3 fixed-angle, no plaq1 (unsigned lever) | 20 | 1218 | 1699 | 4111 | 20 | `data/S2D_2x3_device_requirements.json levers.combined_fixed_angle_no_plaq1_virtual_rz.counts_rzz_recomputed` |
| 2x4 fixed-angle (unsigned lever) | 28 | 14048 | 28492 | 42794 | 28 | `validation/S2_2x4.json data.schedule_4_fixed.rows["2x4\|fixed\|B0_ref0_k1\|all_to_all"].ops` |

### 4.2 Gate-only f and the idle estimate (planner arithmetic with `skqd.device_req.clean_shot_fraction`; `scratch/planner/ionq_feasibility_prototype_20261002.json`)

Idle **ESTIMATE** (same assumption as `scripts/ionq_2x3_feasibility.py`: gates executed serially, each
qubit idle whenever it is not in a gate, linear small-window dephasing $S = \sum_q t_{{\rm idle},q}/(2T_2)$,
$T_1 \gg$ duration, $T_2 = 1$ s, 950 $\mu$s / 130 $\mu$s gate times from arXiv:2506.07866v2).  IonQ does
not publish its scheduling, so this column is an order-of-magnitude statement only.

| lattice | error set | gate-only f (virtual rz) | gate-only f (physical rz) | $\epsilon_2$ needed for mean $f = 0.1$ at the set's $\epsilon_1, \epsilon_{ro}$ (virtual rz) | serial duration (ESTIMATE) | $S_{\rm idle}$ (ESTIMATE) | f with idle (ESTIMATE) | signed bar |
|---|---|---|---|---|---|---|---|---|
| 2x3 | Forte / Forte Enterprise spec (0.4 %, 0.02 %, 0.5 %) | $8.61\times10^{-5}$ | $3.67\times10^{-5}$ | $7.37\times10^{-4}$ | 2.45 s | 22.2 | $2\times10^{-14}$ | FAIL (gate-only alone fails by 1160x) |
| 2x3 | Forte Enterprise measured DRB 99.5 % (arXiv:2506.07866) | $9.85\times10^{-6}$ | $4.20\times10^{-6}$ | same | 2.45 s | 22.2 | $2\times10^{-15}$ | FAIL |
| 2x3 | Forte measured DRB 99.3 % (arXiv:2506.07866) | $1.28\times10^{-7}$ | $5.47\times10^{-8}$ | same | 2.45 s | 22.2 | $3\times10^{-17}$ | FAIL |
| 2x3 | Tempo targets (99.9 %, 99.99 %, SPAM 0.5 % assumed) | $7.70\times10^{-2}$ | $5.03\times10^{-2}$ | $8.79\times10^{-4}$ | 2.45 s at today's gate times | 22.2 | $2\times10^{-11}$ | FAIL on the mean bar even gate-only; needs $\epsilon_2 \le 8.8\times10^{-4}$ **and** gates $\gtrsim 20$x faster or $T_2 \gg 1$ s |
| 2x3 | Aria spec (retired) | $3.39\times10^{-7}$ | $2.63\times10^{-8}$ | $1.8\times10^{-4}$ | 1.71 s | 15.6 | $8\times10^{-17}$ | FAIL, and not accessible |
| 2x4 | Forte spec | $3.9\times10^{-134}$ | — | none ($\epsilon_2 = 0$ does not reach 0.1: the 1q and readout errors alone give $f < 0.1$) | 84 s | 1104 | 0 | FAIL |
| 2x4 | Tempo targets | $4.3\times10^{-37}$ | — | none | 84 s | 1104 | 0 | FAIL |
| 2x4 | pure two-qubit requirement, nothing else wrong | — | — | $3.30\times10^{-5}$ ($f = 0.1$), $4.30\times10^{-5}$ ($f = 0.05$) | — | — | — | no roadmap device (the 99.99 % lab record, https://thequantuminsider.com/2025/10/21/ionq-achieves-99-99-two-qubit-gate-performance/, is $10^{-4}$: $f = e^{-6.97} = 9\times10^{-4}$) |
| 2x2 (information) | Forte spec | 0.303 | 0.281 | $8.3\times10^{-3}$ | 0.31 s | 1.60 | 0.061 | gate-only PASS; with the serial idle estimate below 0.1 |
| 2x2 (information) | Forte Enterprise DRB 99.5 % | 0.234 | — | — | 0.31 s | 1.60 | 0.047 | gate-only PASS |
| 2x2 (information) | Forte DRB 99.3 % | 0.140 | — | — | 0.31 s | 1.60 | 0.028 | gate-only PASS on the mean bar only |

Scenario rows of `data/ionq_2x3_feasibility_20261001.json scenario_eps2_for_2x3` (2x3, virtual rz,
$\epsilon_1 = 2\times10^{-4}$, $\epsilon_{ro} = 5\times10^{-3}$): $\epsilon_2 = 4\times10^{-3} \to f = 8.6\times10^{-5}$;
$10^{-3} \to 0.0567$; $5\times10^{-4} \to 0.167$; $10^{-4} \to 0.396$.  The S2D record's 2x3 $f = 0.0534$
at $\epsilon_2 = 10^{-3}$, $\epsilon_1 = 10^{-4}$, $\epsilon_{ro} = 2\times10^{-3}$ (physical rz;
`validation/S2D.json`) and 0.0817 with virtual rz are reproduced by the same function.

### 4.3 Qubit count and API limits

- 2x3: 20 qubits $\le$ 36 (Forte, Forte Enterprise).  Fits.  Native gates per circuit 5211 (virtual rz),
  below the "150,000 total gates" job limit.
- 2x4: 28 qubits $\le$ 36.  Fits on qubits.  **But** the exact 2x4 coarse step is 208,399 native gates
  (69688 ZZ + 138711 1q), above the "150,000 total gates" limit of the create-job API
  (https://docs.ionq.com/api-reference/v0.4/jobs/create-job, read 2026-10-02; whether the limit is per
  job or per circuit is not stated — the executor's dry run on the IonQ simulator settles it).  The
  2x4 fixed-angle family (42,540 native gates) fits.  The 2x4 noisy-simulator check on IonQ's cloud is
  not possible either: "Forte-class systems: Up to 29 qubits" but a 2x4 circuit is 28 qubits with
  $2\times10^5$ gates, far beyond what that simulator is documented for.

### 4.4 Shot plan and dollar cost

Shot numbers come from the repository's own shot rule: the D3-type per-sector shot count of
`data/S2D_recall_at_f.json results.*.shot_rule_union_reading_N_sector` for 2x3 (71,500 at $f = 0.1$;
84,714 at 0.0817; 123,954 at 0.0534; 199,952 at 0.03; $N f \approx 6000$–7150, i.e. the rule scales as
$1/f$), and for 2x2 the executed plan 133,907 coarse shots at $f = 0.1129$ (`validation/H0_2x2.json
data.shot_plan`).  Per-shot cost (planner arithmetic from the published rates, virtual rz counts;
`scratch/planner/ionq_cost_rows_20261002.json`): Azure 2x2 $0.376/shot, 2x3 $2.92/shot, 2x4 $100.9/shot;
Braket $0.08/shot flat.

| run | f used | shots | Braket cost (planner arithmetic) | Azure cost (planner arithmetic) | QPU wall time (ESTIMATE, serial durations) |
|---|---|---|---|---|---|
| 2x3, both sectors, Forte spec gate-only $f = 8.6\times10^{-5}$ | $8.6\times10^{-5}$ | $7.7\times10^{7}$ per sector ($123{,}954 \times 0.0534 / 8.6\times10^{-5}$) | $6.2\times10^{6}$ USD per sector | $2.2\times10^{8}$ USD per sector | 6 years per sector |
| 2x3 at the signed $f = 0.1$ (a device that does not exist) | 0.1 | 71,500 per sector | 5,720 USD per sector + tasks | 209,000 USD per sector | 49 h per sector |
| 2x4 | 0 | not computable (no clean shots at any budget) | — | — | — |
| 2x2 (information), Forte Enterprise DRB 99.5 % gate-only $f = 0.234$ | 0.234 | 64,600 total | 5,170 USD + 30 tasks x 0.30 | 24,300 USD + minimum per program | 5.6 h |
| 2x2 (information), Forte spec with the serial idle estimate $f = 0.061$ | 0.061 | 248,000 total | 19,800 USD | 93,000 USD | 22 h |

Conclusion of this section: **2x3 and 2x4 are infeasible on every IonQ device that exists today**, on
gate errors alone (2x3 misses the mean bar by 1160x at the spec, by $10^4$–$10^6$ at the measured DRB
values; 2x4 by more than 130 orders of magnitude), before idle time and before cost.  Access to Forte
or Forte Enterprise would not change that.  The only IonQ hardware for which the signed family is
within reach on gate errors is 2x2 (already run on IBM), where a Forte run would be a cross-platform
check at 5–20 kUSD on Braket rates, with the idle term uncertain (ESTIMATE 0.03–0.06 after idle).

## 5. What the preparation (prompts/25) still buys

1. The 2x3 and 2x4 circuit families compiled to IonQ native gates (GPi, GPi2, ZZ with virtual Z),
   verified exactly against the statevector / sparse path, stored as `ionq.circuit.v1` JSON plus QPY —
   ready for any future all-to-all device with a ZZ native gate (Tempo-class, or a 2027 device).
2. A requirement table per device that the owner can hand to IonQ: 2x3 signed family needs
   $\epsilon_2 \le 7.4\times10^{-4}$ (virtual rz, at $\epsilon_1 = 2\times10^{-4}$, $\epsilon_{ro} = 5\times10^{-3}$)
   **and** an idle budget $S \lesssim 1$, i.e. $n_{\rm 2q}\, t_{2q} \ll T_2$: with 2158 gates and $T_2 = 1$ s,
   $t_{2q} \lesssim 50\,\mu$s if the gates are serial (19x faster than today's 950 $\mu$s), or a
   scheduler that parallelizes gates across the chain.  2x4 exact: $\epsilon_2 \le 3.3\times10^{-5}$ —
   no device class; 2x4 fixed-angle (14,048 ZZ): $\epsilon_2 \le 1.6\times10^{-4}$ and $t_{2q} \lesssim 7\,\mu$s
   serial — the 99.99 % lab class with a gate speed that does not exist.
3. A submission path (dry run, preflight, preregistration, key handling) that mirrors the IBM one, so
   that an IonQ 2x2 cross-check or a future Tempo 2x3 run needs no new tooling.
4. The device class that would work for 2x3: **two-qubit error $\le 7\times10^{-4}$ (99.93 %+), one-qubit
   $\le 2\times10^{-4}$, SPAM $\le 0.5$ %, with the 2158-gate circuit executed well inside $T_2$** —
   IonQ's published Tempo targets (99.9 %) meet the gate-error part only marginally ($f = 0.077$ mean,
   below 0.1) and publish no gate time.

Circuit-cost reductions the planner can offer, each a change of the signed family and therefore an
**owner decision** (none is adopted here):

| lever | 2x3 2q gates | gate-only f at Forte spec (virtual rz) | $\epsilon_2$ for $f = 0.1$ | evidence | price |
|---|---|---|---|---|---|
| signed exact family | 2158 | $8.6\times10^{-5}$ | $7.4\times10^{-4}$ | this report | — |
| fixed-angle generator | 1620 (1q with virtual rz 2199) | $8.8\times10^{-4}$ (planner arithmetic, `clean_shot_fraction(1620, 2199, 20, 0.004, 0.0002, 0.005)`) | $1.09\times10^{-3}$ at Forte's $\epsilon_1, \epsilon_{ro}$ ($1.26\times10^{-3}$ at the S2D declared inputs, `levers.fixed_angle_generator.eps2_required_virtual_rz`) | `data/S2D_2x3_device_requirements.json levers.fixed_angle_generator` | per-term deviation $\sim 10^{-1}$ from $e^{-i\theta H}$; S1 recall 1.0 / 0.937 at $f = 0.1$ |
| drop plaq1 | 1394 (1q 2103) | $2.2\times10^{-3}$ (planner arithmetic) | $1.28\times10^{-3}$ | `levers.term_ablation` | S1 recall 0.977 / 0.937 |
| fixed-angle + no plaq1 | 1218 (1q 1699) | $4.9\times10^{-3}$ (planner arithmetic) | $1.53\times10^{-3}$ at Forte's $\epsilon_1, \epsilon_{ro}$ ($1.72\times10^{-3}$ at the S2D inputs) | `levers.combined_fixed_angle_no_plaq1_virtual_rz` | combination's recall not emulated |

Even the cheapest unsigned 2x3 variant is 20x below the mean bar on Forte's spec, and its serial
duration (1.38 s, ESTIMATE) still exceeds $T_2$.  No reduction makes 2x3 run on Forte-class hardware.

## 6. Software stack (checked 2026-10-02 against the pinned `coding` env: qiskit 2.5.2, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.49.0, Python 3.12.14)

Package metadata read from the wheels downloaded with `pip download --no-deps` (not installed):

| package | version | Requires-Dist | compatible with qiskit 2.5.2 by metadata? |
|---|---|---|---|
| qiskit-ionq | 1.1.1 | `qiskit>=2.0.0`, decorator>=5.1.0, requests>=2.24.0, importlib-metadata>=4.11.4, python-dotenv>=1.0.1; Requires-Python >=3.10 | yes; no pin on numpy, aer or runtime |
| qiskit-braket-provider | 0.25.0 | `qiskit<3.0.0,>=2.2.0`, `qiskit-ionq<2.0.0,>=1.0.0`, amazon-braket-sdk>=1.123.0, amazon-braket-default-simulator>=1.40.1 | yes by metadata, but pulls the Braket SDK |
| amazon-braket-sdk | 1.127.3.post0 | boto3>=1.28.53, `cloudpickle==2.2.1`, `oqpy~=0.3.7`, openqasm3, openpulse, sympy, networkx, numpy | the exact `cloudpickle==2.2.1` pin is the one risk for the `coding` env |

Recommendation (binding for prompts/25): **do not rely on either provider for correctness.**  The
native-gate conversion is a 40-line deterministic rewrite of the `{rz, sx, x, rzz}` basis
(virtual-Z frame tracking: $rz(\lambda)$ shifts the phase of every later GPi/GPi2 on that qubit by
$-\lambda/2\pi$ turns, ZZ commutes with Z, measurement is in Z), implemented in `src/skqd/ionq_native.py`
with the matrices above and verified exactly in the `coding` env.  Submission uses a plain REST client
(`requests`, already a dependency of qiskit-ibm-runtime) against the documented v0.4 endpoints, with the
API key read exactly as `scripts/ibm_account.py` reads IBM's (token file, `$IONQ_API_KEY`, hidden
prompt or piped stdin; never argv).  qiskit-ionq 1.1.1 may be installed as an optional cross-check only
after `pip install --dry-run qiskit-ionq==1.1.1` shows no change to qiskit, qiskit-aer,
qiskit-ibm-runtime, numpy or scipy; the Braket SDK goes into a separate conda env (`su2qc-ionq`) if the
owner chooses the Braket route.

## 7. What the owner must ask IonQ for, and the decisions only the owner can make

Ask IonQ (or AWS):
1. Which device: Forte Enterprise 1 (`qpu.forte-enterprise-1`) — the better measured DRB (99.5 %) in
   arXiv:2506.07866 and the newer noise model; Forte 1 as fallback.  Tempo: early-access terms,
   *measured* two-qubit error, gate time, $T_2$ and the scheduler's parallelism — the four numbers that
   decide 2x3.
2. Access route: Amazon Braket (flat $0.08/shot: 36x cheaper than Azure's per-gate-shot rate for a 2x3
   circuit) or IonQ Quantum Cloud direct (rates per agreement; ask for the per-shot rate and whether
   `gateset: native` and `debiasing: false` are permitted on the account — SKQD needs raw bit strings,
   so debiasing/sharpening must be off, which also removes the 500-shot minimum).
3. Credits: for a 2x2 cross-check 5–20 kUSD at Braket rates (section 4.4); for 2x3 on today's devices
   no amount of credit helps (section 4.2).
4. The published noise-model documentation for `forte-enterprise-1` ("Additional documentation on the
   new models is in preparation", docs.ionq.com, read 2026-10-02) and the characterization endpoint's
   current values (`GET /v0.4/backends/{backend}/characterizations`), so that a prediction can be
   preregistered the way D9 does on IBM.

Owner decisions:
- D1. Whether to run 2x2 on Forte Enterprise as a cross-platform check (not asked for; information).
- D2. Whether any unsigned circuit-cost lever (fixed-angle generator, plaq1 ablation) may be adopted
  for a future 2x3 device run — none helps on today's devices.
- D3. Whether to add a Perlmutter CI token for the 2x4 native-gate verification (the sparse laptop
  path may not complete the 69,688-gate circuit; `validation/S2_2x4.json
  data.compiled_probe.probe_4_exact.circuits["B0_ref0_k1|all_to_all"]` recorded `completed: false` after
  711 s on the laptop, and the committed C6 came from the Perlmutter GPU job 59162991,
  `data.gpu.gpu_4_GPU`, qiskit 1.4.3 / aer 0.15.1).

## 8. Problems, assumptions, and what is NOT established

- The kingston ceilings use the 2026-10-02T19:06Z record; edges change daily, but the best edge would
  have to improve 1.5x (2x3) or 41x (2x4) for the ceiling alone to reach 0.05.  The executor reads the
  day's record in gate K0.
- The Forte gate durations (950 / 130 $\mu$s) are from one IonQ-authored paper, not from a spec page;
  the idle column is an ESTIMATE under serial execution, and IonQ may schedule gates in parallel.  The
  gate-only column does not depend on it, and it alone settles 2x3 and 2x4.
- IonQ's spec pages quote "0.4%" two-qubit error; the same company's paper measured 0.7 % / 0.5 % on
  the day.  Both are shown.  Tempo numbers are targets.
- The 2x4 ZZ count is proxied by the CZ count of the all-to-all compile (69,688); the RZZ compile of 2x3
  gave 2158 against 2164 CZ, so the proxy is within 0.3 % there.
- The "150,000 total gates" limit is quoted from the multi-circuit job documentation; whether a single
  208,399-gate circuit is accepted is unknown until a dry run on IonQ's simulator (needs a key).
- Prices are list prices read 2026-10-02; IonQ states that direct rates depend on the agreement.
- Nothing here is a hardware measurement on IonQ.  The Azure page still lists Aria 1 (page dated
  2026-08-29) while ionq.com and docs.ionq.com call Aria retired; Aria is treated as not accessible.

# 2x3 on quantum hardware: can error correction, error detection or an "amplifier" give a substantial result? (planner analysis, 2026-10-02)

- date: 2026-10-02
- git commit at writing: 86a9bd6 (`git rev-parse --short HEAD`)
- prompt in force: `prompts/25_2x3_2x4_kingston_check_and_ionq_prep.md`; this analysis backs
  `prompts/27_2x3_substantial_result_strategy.md` (prompts/26 is being written in parallel by another
  planner and is not referenced here)
- related: `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md`,
  `reports/H0_2x2_full_hardware_report_20261002.md`, `reports/SESSION_HANDOVER_20260925_1002.md` section 7,
  `prompts/low_clean_fraction_techniques.md` (the owner's literature catalogue; its entry labels B13, C3,
  D27 etc. are used below), `proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md`,
  `proposal/amendment_01_devices_and_budgets.md`
- QPU seconds spent by this analysis: 0 on every provider.  Nothing was submitted anywhere.

Rule 1 of `CLAUDE.md` applies: every project number below is read from a named `validation/*.json` or
`data/*.json` key; every literature number comes from an arXiv abstract page or vendor page fetched on
2026-10-02 (listed in section 9); everything I computed is marked **(planner arithmetic)** and, where
it rests on an assumption, **ESTIMATE**.  Two scratch prototypes were run for this report and are
committed with it: `scratch/planner/helios_2x3_feasibility_20261002.{py,json}` (device/cost table) and
`scratch/planner/lowf_counting_amplifier_20261002.{py,json,log}` plus `lowf_tiers_20261002.{py,log}`
(the shot-versus-clean-fraction emulation).  Scratch numbers are planner estimates until an executor
turns them into a gate JSON (prompts/27 stage 0).

---

## 0. Vocabulary (each term once, plain words)

- **Clean fraction $f$**: probability that one shot (one circuit run plus one readout) has no error at all.
  The repository computes the gate-only part as $f = (1-\epsilon_2)^{n_{2q}}(1-\epsilon_1)^{n_{1q}}(1-\epsilon_{ro})^{n_{\rm meas}}$
  (`src/skqd/device_req.py`); idle-time dephasing multiplies it by $e^{-S_{\rm idle}}$ (`src/skqd/idle.py`).
- **Signed budget** (amendment 01 item 2): mean $f \ge 0.1$ over the circuit family, worst circuit $\ge 0.05$.
- **Signed family**: the exact coarse-step circuits $\prod_\gamma e^{-iH_\gamma k\Delta t}$ in the term
  order `diag, hop0..hop6, plaq0, plaq1`; 2164 CZ all-to-all, 5477 CZ routed on heavy-hex
  (`validation/S2.json data.2x3.coarse_step`), 2158 RZZ + 3053 non-$R_z$ one-qubit gates in the
  RZZ basis with virtual $R_z$ (`data/S2D_2x3_device_requirements.json counts`, `levers.virtual_rz`).
- **Decoder**: the classical per-shot check of manual Step 2.5 (vertex flags, link consistency, sector).
  **Garbage acceptance**: the fraction of uniformly random 20-bit strings it accepts, 0.146 %
  (`validation/E2.json`, 1727/2^20); per state it is $2^{-20} = 9.5\times10^{-7}$ per garbage shot
  **(planner arithmetic)**.  **Near-clean string**: a string with a few errors that still passes every
  check (rule M4.4 of amendment 01).
- **$B_{\rm all}$ / $B_{\rm sig}$** (project labels, prompts/24 P9): all accepted states; the states whose
  count exceeds the uniform-noise expectation at the one-sided $3\sigma$ Poisson level.
- **Counting amplifier** (my label for this report, not a standard term): the plain fact that a state's
  signal count grows as $N f p$ with the shot number $N$ while the uniform-noise count per state grows as
  $N\,2^{-20}$ and fluctuates as its square root.  It is the only "amplifier" that exists for sampling.
- **Error detection code**: an encoding in which any single error moves the state out of the code space and
  is caught by a check; the shot is discarded, not corrected.  **Iceberg code** $[[k+2,k,2]]$: $k$ logical
  qubits in $k+2$ physical ones (arXiv:2211.06703).  **Error correction (QEC)**: the error is identified
  and undone; **surface code**, **colour code**, **qLDPC** (quantum low-density parity-check) are families.
  **Logical qubit**: one error-protected qubit made of many physical ones.  **Magic state / T gate**:
  the non-Clifford resource that fault-tolerant codes need for arbitrary rotation angles; **Clifford+T
  synthesis**: writing a rotation $R_z(\theta)$ as a sequence of Clifford gates and $T$ gates to precision
  $\epsilon$ (arXiv:1403.2975: about $3\log_2(1/\epsilon)$ $T$ gates).
- **Data-processing inequality**: no physical operation (completely positive map) can increase the
  distinguishability of two states; a textbook fact (Nielsen and Chuang, Theorem 9.2, trace-distance
  contractivity), used here without an arXiv source.
- **Virtual distillation (VD) / error suppression by derangement (ESD)**: estimate observables in the state
  $\rho^M/\mathrm{Tr}\rho^M$ from $M$ copies (arXiv:2011.07064, arXiv:2011.05942).
- **HQC**: Quantinuum's Hardware Quantum Credit, $\mathrm{HQC} = 5 + C\,(N_{1q} + 10N_{2q} + 5N_m)/5000$ per job
  with $C$ shots (Azure pricing page, read 2026-10-02).

---

## 1. What was asked

Owner, 2026-10-02 (verbatim): "use planner to figure out if quantum error correction techniques can help
with the 2x3 case or not, can we build an amplifier which can amplify the signals and leaves noise, try to
come up with a plan in which way we can get something substantial from 2x3 runs on quantum computers, may
be use large number of qubits which also do error corrections etc."

Short answers (details follow):

1. **QEC**: not on any 2026 device.  A fault-tolerant 2x3 needs about $10^5$ $T$ gates per shot on
   $\gtrsim 20$ logical qubits; that is a 2029-class machine (IBM Starling "200 qubits running 100 million
   gates", Quantinuum Apollo "hundreds of logical qubits", both vendor roadmaps).  **Error detection**
   (Iceberg) does not raise $f$ and costs 4-5x more two-qubit gates than the unencoded circuit; our
   Gauss-law decoder already is a distance-2 detection code at zero gate cost.
2. **Amplifier**: there is no quantum amplifier for an unknown noisy state (data processing; noiseless
   amplification is heralded and probabilistic).  Virtual distillation costs $\sim f^{-4}$ shots and $2\times$
   the qubits for expectation values and is useless for samples.  **What does act like an amplifier is
   shots**: the counting statistic plus the Gauss-law decoder plus $B_{\rm sig}$ gives the same result at
   $f = 0.01$ with $10^6$ shots as at $f = 0.17$ with $2\times10^5$ (proxy emulation, section 2.3).  Its cost
   is $\propto 1/f$ up to about $2\times10^6$ shots per sector and $\propto 1/f^2$ beyond, because uniform
   garbage then starts to saturate the per-state counts.  The practical floor at 2x3 is $f \approx 10^{-3}$,
   not $0.1$.
3. **Substantial result**: the manual's primary endpoint P1 (device support versus CIPSI at equal $|B|$
   with bootstrap bands, manual Step 6.3) on 2x3 hardware data, with the honest expectation "device between
   BFS and CIPSI".  The one device class that reaches the signed $f \ge 0.1$ for the signed family today is
   Quantinuum Helios ($f_{\rm gates} = 0.167$, planner arithmetic on the vendor's published infidelities);
   its idle term is unknown and its list price is prohibitive (about USD 62 per shot), so the route runs
   through the Helios emulator and a DOE QCUP allocation.  The cheapest *measurement* available now is a
   2x3 clean-fraction pilot on ibm_kingston ($\le 300$ s), which decides whether the IBM route is dead
   ($f < 3\times10^{-4}$) or a ten-hour run ($f \ge 10^{-3}$).

---

## 2. The arithmetic that frames every technique

### 2.1 Gate-only clean fractions of the 2x3 families on the devices that exist (planner arithmetic)

`scratch/planner/helios_2x3_feasibility_20261002.json`, computed with `skqd.device_req.clean_shot_fraction`
on the repository's counts.  Device inputs: Helios two-qubit infidelity $7.9(2)\times10^{-4}$, one-qubit
$2.5(1)\times10^{-5}$, SPAM $4.8(6)\times10^{-4}$ (arXiv:2511.05465, Table 2, abstract fetched);
H2 "two-qubit gate fidelity > 99.9 %" (Quantinuum H2 page; I take $\epsilon_2 = 10^{-3}$, $\epsilon_1 = 10^{-4}$,
$\epsilon_{ro} = 2\times10^{-3}$, the S2D declared set); IonQ Forte spec (0.4 %, 0.02 %, 0.5 %; `reports/ionq_devices_...`).

| family (owner-signed = first row) | $n_{2q}$ | $n_{1q}$ (virtual $R_z$) | $f$ Helios | $f$ H2 ($\epsilon_2 = 10^{-3}$) | $f$ IonQ Forte | HQC / shot | USD / shot at 12.5 / HQC | shots per sector (D3 rule, $\propto 1/f$) |
|---|---|---|---|---|---|---|---|---|
| signed exact | 2158 | 3053 | **0.167** | 0.082 | $8.6\times10^{-5}$ | 4.95 | 61.8 | 42,900 |
| fixed-angle generator (`levers.fixed_angle_generator`) | 1620 | 2199 | 0.261 | 0.152 | $8.8\times10^{-4}$ | 3.70 | 46.2 | 27,400 |
| no plaq1 (`levers.term_ablation`) | 1394 | 2103 | 0.312 | 0.193 | $2.2\times10^{-3}$ | 3.23 | 40.4 | 22,900 |
| fixed-angle + no plaq1 (`levers.combined_...`) | 1218 | 1699 | 0.363 | 0.240 | $4.9\times10^{-3}$ | 2.80 | 34.9 | 19,700 |

The shot column scales the repository's union-reading D3 count 71,500 per sector at $f = 0.1$
(`data/S2D_recall_at_f.json results."B=0|f=0.1".shot_rule_union_reading_N_sector`) as $1/f$.  The HQC
column is the Azure formula with the 20 measurements; USD 12.5 per HQC is the Standard plan
(USD 125,000 per month for 10k HQC, Azure pricing page) **(planner arithmetic)**; pay-as-you-go rates are
"contact sales".  Every Helios job is capped at 10,000 shots and 500,000 HQC (Quantinuum Helios user guide).

Two consequences.  (i) **Helios is the only device whose published gate errors put the signed family above
the signed budget** (0.167 gate-only; Forte misses by 1160x, kingston's best-edge ceiling is $1.14\times10^{-2}$
at 5477 routed CZ, `reports/ionq_devices_...` section 2).  (ii) At list price a full P1 run is
$2 \times 42{,}900 \times 4.95 \approx 4.2\times10^5$ HQC, about USD 5.3 M **(planner arithmetic)** -- forty
Standard-plan months.  Commercial access cannot pay for 2x3 SKQD; the DOE Quantum Computing User Program
(QCUP, ORNL: "Quantinuum N $\ge$ 56 qubit trapped-ion", merit-reviewed, no price stated) or a vendor
research agreement is the only route.

### 2.2 The idle term on Helios is unknown and decisive

The signed 2x3 circuit is almost serial: one $k = 1$ circuit compiled to `{rz, rx, ry, rzz}` at optimization
level 1 has 2568 RZZ and a **two-qubit depth of 2302** (`scratch/planner/two_qubit_depth_2x3_20261002.json`,
every $k = 1$ circuit of both sectors gives 2302), i.e. almost one two-qubit gate per layer.  Helios
reports a memory error of $5(1)\times10^{-4}$ per qubit per "depth-1 transport" (randomly pairing all 98
qubits, transporting and cooling, no gates; arXiv:2511.05465 Sec. III.2.4) and 55 ms per depth-1 layer at
98 qubits (Sec. II.3).  If every one of our ~2300 layers cost that memory error on all 20 qubits the idle
budget would be $S_{\rm idle} = 20 \times 2300 \times 5\times10^{-4} = 23$ nats and $f \to 10^{-10}$; if a
20-qubit, one-gate-per-layer circuit moves only the two gated ions the cost is far smaller.  **Neither number
is a prediction**: the memory error per layer of a 20-qubit serial program is a property of Quantinuum's
scheduler that only their emulator or a measurement can give.  This is amendment item 4 again ("the
vendor must additionally declare gate durations, $T_1$, $T_2$ and whether qubits idle serially") and it is
why prompts/27 puts the Helios emulator run before any hardware discussion.  The 2x2 lesson stands: the
gate-only model was 15-50x optimistic on Heron (`validation/H0_model.json`).

### 2.3 The counting amplifier: what shots buy at low $f$ (proxy emulation, prototype)

`scratch/planner/lowf_counting_amplifier_20261002.py` runs the manual's Step-8.2 proxy emulator
(`gate_S1.emulate`: a shot is clean with probability $f$, otherwise uniform garbage or a clean sample with
Poisson(2) flips, plus readout flips) on the 2x3 $B = 0$ sector (677 states, 99.9 % support 86 states,
99 % support 31 states; `validation/E3.json`) with all 8 references and coarse steps $k = 1..4$
(32 circuits), seed 20261002, and evaluates $B_{\rm sig}$ against the manual's controls at equal size.
**These are proxy numbers, not device numbers** (the proxy has no near-clean structure beyond Poisson
flips; rule M4.4).

| $f$ | $N$ per sector | accepted | $\mu$ uniform per state | $|B_{\rm all}|$ | $|B_{\rm sig}|$ | $E_R(B_{\rm sig}) - E_0$ | recall 99.9 % / 99 % ($B_{\rm sig}$) | false pos. ($B_{\rm sig}$) | random at equal size: mean / best of 100 | CIPSI at equal size | BFS at equal size |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.17 | $2\times10^4$ | 2,912 | 0.008 | 163 | 100 | $1.6\times10^{-2}$ | 0.85 / 0.97 | 0 | 0.181 / 0.154 | $4.3\times10^{-3}$ | $1.4\times10^{-2}$ |
| 0.17 | $5\times10^4$ | 7,229 | 0.020 | 218 | 142 | $3.2\times10^{-3}$ | 0.98 / 1.00 | 2 | 0.173 / 0.123 | $1.6\times10^{-3}$ | $9.6\times10^{-3}$ |
| 0.17 | $2\times10^5$ | 29,021 | 0.079 | 340 | 200 | $1.5\times10^{-3}$ | 0.99 / 1.00 | 0 | 0.156 / 0.110 | $5.8\times10^{-4}$ | $1.3\times10^{-3}$ |
| 0.17 | $10^6$ | 145,886 | 0.40 | 537 | 318 | $1.7\times10^{-4}$ | 1.00 / 1.00 | 6 | 0.122 / 0.079 | $6.7\times10^{-5}$ | $7.2\times10^{-4}$ |
| 0.36 | $2\times10^4$ | 5,920 | 0.006 | 193 | 126 | $3.0\times10^{-3}$ | 0.99 / 1.00 | 0 | 0.174 / 0.143 | $2.0\times10^{-3}$ | $1.3\times10^{-2}$ |
| 0.05 | $10^6$ | 47,743 | 0.45 | 502 | 271 | $5.2\times10^{-4}$ | 1.00 / 1.00 | 11 | 0.137 / 0.087 | $1.3\times10^{-4}$ | $9.6\times10^{-4}$ |
| 0.01 | $10^6$ | 15,399 | 0.47 | 502 | 197 | $1.5\times10^{-3}$ | 1.00 / 1.00 | 5 | 0.155 / 0.120 | $6.2\times10^{-4}$ | $1.3\times10^{-3}$ |
| 0.36 | $5\times10^4$ | 15,187 | 0.015 | 268 | 179 | $1.6\times10^{-3}$ | 1.00 / 1.00 | 0 | 0.161 / 0.127 | $8.8\times10^{-4}$ | $3.4\times10^{-3}$ |
| 0.05 | $2\times10^5$ | 9,430 | 0.091 | 322 | 164 | $3.0\times10^{-3}$ | 0.97 / 1.00 | 1 | 0.161 / 0.117 | $1.1\times10^{-3}$ | $6.8\times10^{-3}$ |
| 0.02 | $10^6$ | 23,545 | 0.47 | 503 | 211 | $1.2\times10^{-3}$ | 1.00 / 1.00 | 5 | 0.151 / 0.112 | $4.5\times10^{-4}$ | $1.2\times10^{-3}$ |
| 0.01 | $4\times10^6$ | 61,223 | 1.9 | 654 | 288 | $5.0\times10^{-4}$ | 1.00 / 1.00 | 9 | 0.130 / 0.096 | $1.0\times10^{-4}$ | $8.8\times10^{-4}$ |
| 0.003 | $4\times10^6$ | 38,660 | 1.9 | 650 | 262 | $8.6\times10^{-4}$ | 1.00 / 1.00 | 11 | 0.140 / 0.107 | $1.5\times10^{-4}$ | $9.8\times10^{-4}$ |
| 0.001 | $4\times10^6$ | 31,881 | 1.9 | 638 | 262 | $8.0\times10^{-4}$ | 1.00 / 1.00 | 9 | 0.140 / 0.107 | $1.5\times10^{-4}$ | $9.8\times10^{-4}$ |

**A caveat that matters at $f \le 0.01$.**  The accepted shots are not mostly clean there.  With the proxy's
rates the clean accepted count is $0.82 f N$ and the $B = 0$ garbage count is about $(1-f)N/2 \times 0.00146 \times 677/1727$;
the rest are *near-clean* strings (a clean sample with Poisson(2) flips that still decodes) **(planner
arithmetic)**: at $f = 0.17$, $N = 2\times10^5$ they are 4 % of the accepted shots; at $f = 0.01$, $N = 10^6$
about 45 %; at $f = 10^{-3}$, $N = 4\times10^6$ about 86 %.  In the proxy a near-clean string that passes the
decoder is a few-bit variant of a true sample, i.e. usually a Hamiltonian neighbour of a support state, so
it behaves like a BFS proposal and keeps $B_{\rm sig}$ good.  **On hardware the near-clean strings' structure
is exactly what rule M4.4 says is unmeasured** (at 2x2 they were about 20 % of the accepted shots at
$f = 0.127$, section 8).  So the rows at $f \le 0.01$ are the proxy's optimistic reading; the uniform-garbage
derivation below is the pessimistic one; the truth on a device lies between and is what stage 1 (device
model) and stage 0b (the kingston pilot) are for.

Reading: (a) $B_{\rm sig}$ beats random equal-size bases by two orders of magnitude in every cell (the
hardware value sits at the 0th percentile of 100 random draws); at 2x3 "beats random" is therefore a
*necessary* check, not a result.  (b) The informative comparison is BFS (blind neighbour growth, the
classically trivial support) and CIPSI: the device support ties BFS in about half the cells and beats it
by 2-4x in the others (the ratio drifts with $|B_{\rm sig}|$, not monotonically with $N$), and CIPSI beats the
device by 2-5x everywhere -- exactly the manual's preregistered expectation (Step 6.2, "characterized
null").  A preregistered Tier-A bar of "device error $\le 1.5\times$ BFS at equal size" is therefore
realistic; "device $\le 0.5\times$ BFS" is a stretch reached only in the $10^6$-shot cells.  (c) **$f = 0.01$ with $10^6$ shots gives the
same $|B_{\rm sig}|$, recall and energy as $f = 0.17$ with $2\times10^5$**: the cost is $1/f$ as long as the
uniform-noise count per state $\mu = N(1-f)/2^{21}$ stays below about 1, and $B_{\rm all}$ (502 states, 95 false
positives at $f = 0.01$) is already noise-filled while $B_{\rm sig}$ is not.

Beyond $\mu \gtrsim 1$ the per-state noise fluctuates as $\sqrt{\mu}$ and the condition for a state of ideal
probability $p$ to stand $z$ sigma above it becomes **(planner derivation, proxy noise)**

$$ N \;\gtrsim\; \frac{z^2\,(1-f)\,2^{-21}}{(0.82\,f\,p)^2}\,, \qquad\text{against the discovery condition}\quad N \gtrsim \frac{3}{0.82\,f\,p}\ \text{for}\ \mu \ll 1 . $$

The crossover is at $N \approx 2\times10^6$ shots per sector.  At $z = 5$, $p = 10^{-3}$: $N \approx 1.8\times10^7$
for $f = 10^{-3}$ and $1.8\times10^9$ for $f = 10^{-4}$.  So the counting amplifier takes a device from the
signed 0.1 down to about $10^{-3}$ at 2x3 (ten-hour runs at $10^3$ shots per second), and no further; the
proxy rows at $f = 0.003$ and $0.001$ above look better than this bound only because of the near-clean
mechanism of the caveat, which the bound ignores and the device may or may not have.
At 2x2 the same arithmetic saturated at $N \approx 2\times10^4$ because the garbage acceptance per state is
$2^{-12}$, which is why 2x2 could never be a device test (`validation/H0_2x2.json data.C22`).

---

## 3. Question 1: quantum error correction and error detection

### 3.1 What a fault-tolerant 2x3 would need (planner arithmetic, order of magnitude)

The signed coarse step has, in the IR, 2588 CNOT, 2164 $R_y$, 144 one-qubit unitaries, 29 phase gates and
2 controlled phases (`validation/S2.json data.2x3.ir_gate_counts_coarse_step`): about **2,600 arbitrary-angle
rotations per shot**, all non-Clifford.  In a Clifford+T code each costs about $3\log_2(1/\epsilon)$ $T$ gates
(arXiv:1403.2975).  For the sampled distribution to be right to about 10 % the synthesis errors must sum to
$\lesssim 0.1$, so $\epsilon \approx 4\times10^{-5}$ and about 44 $T$ per rotation: **$\approx 1.1\times10^5$ $T$ gates
per shot** plus 2,600 Clifford CNOTs.  Magic-state cultivation reaches $2\times10^{-9}$ per $T$ state at
$10^{-3}$ physical noise (arXiv:2409.17595), so the $T$ states contribute $2\times10^{-4}$ error per shot --
negligible.  The memory must then survive $\sim 10^5 \times d$ code cycles per shot on 20 logical qubits plus
routing.  With Google's measured surface-code scaling (distance-7 memory at $0.143$ % error per cycle,
suppression $\Lambda = 2.14$ per two distance steps at their physical error, arXiv:2408.13687) a per-cycle
logical error of $\sim 10^{-9}$ needs $d \approx 40$ and $\sim 10^5$ physical qubits; at a physical error of
$10^{-4}$ the same target needs $d \approx 15$-$20$ and $\sim 3\times10^4$ physical qubits **(ESTIMATE,
assumes $\Lambda$ scales with physical error as in the paper's model)**.  The IBM gross code reduces the
memory part 10x (12 logical qubits in 288 physical at 0.1 % error, arXiv:2308.07915) but has no
demonstrated logical non-Clifford gates.  Per-shot time $\approx 1.1\times10^5 \times d \times 1.1\,\mu$s
$\approx 2$ s on a superconducting cycle (Google's cycle time), 43k shots $\approx 24$ h per sector; ions are
$\sim 100$x slower per cycle.

**Which machine:** IBM Starling, "available in 2029 with 200 qubits running 100 million gates"
(IBM roadmap page); Quantinuum Apollo, "by the end of the decade ... millions of operations on hundreds
of logical qubits" (Quantinuum roadmap, via HPCwire 2025-11-05 and computerweekly).  Both fit $10^5$ $T$ per
shot on 20-40 logical qubits.  **Nothing in 2026 does**: the demonstrated logical computations are
4-48 logical qubits with hundreds of logical gates and no arbitrary-angle rotations at our count
(Quantinuum/Microsoft $[[7,1,3]]$ and $[[12,2,4]]$, logical error 9.8-800x below physical,
arXiv:2404.02280; Harvard/QuEra 48 logical qubits, 228 logical two-qubit gates and 48 logical CCZ on 280
atoms, arXiv:2312.03982; 2025: 448 atoms, "dozens of logical qubits and hundreds of logical
teleportations", arbitrary-angle synthesis "with logarithmic overhead" by transversal teleportation with
$[[15,1,3]]$, arXiv:2506.20661; Helios 48-94 logical qubits with the $[[k+2,k,2]]$ and concatenated iceberg
codes, arXiv:2602.22211).  Our 2,600 rotations per shot are 10-30x beyond "hundreds of teleportations".

**Partially fault-tolerant (STAR) architecture** (arXiv:2303.13181): error-corrected Clifford gates plus
non-corrected analog rotations; "for early-FTQC devices that consist of $10^4$ physical qubits with
physical error probability $p = 10^{-4}$ ... roughly $1.72\times10^7$ Clifford operations and $3.75\times10^4$
arbitrary rotations on 64 logical qubits".  Our 2,600 rotations and 2,600 Cliffords per shot sit inside
that budget with margin, so a STAR-class machine ($10^4$ physical qubits at $10^{-4}$) would give
$f \approx e^{-2600\,c\,10^{-4}}$ with $c$ of order 1-3, i.e. $f \approx 0.5$-$0.8$ **(ESTIMATE)**.  That is
the earliest fault-tolerance-assisted route and it is the same 2029 device class.

**Verdict on QEC: not a 2026-2028 option for 2x3; a 2029+ option on Starling/Apollo/STAR-class hardware,
at $\sim 10^5$ $T$ gates per shot and $10^4$-$10^5$ physical qubits.**

### 3.2 Error detection with post-selection

**Iceberg $[[k+2,k,2]]$ on ions.**  Logical operators are weight-2 (arXiv:2211.06703: "a universal set of
local and global logical rotations that have physical support on only two qubits"), so a logical
$R_{ZZ}(\theta)$ costs one physical $R_{ZZ}$ but **every logical one-qubit rotation costs one physical two-qubit
gate** ($R_z$ on logical $i$ is $e^{-i\theta Z_tZ_i/2}$ on the top ancilla; $R_x$ is $e^{-i\theta X_bX_i/2}$ on the
bottom one).  Our signed circuit in the RZZ basis has 2158 RZZ, 3053 $X$-type one-qubit gates and 4257 $R_z$
that are virtual on bare hardware but become physical $Z_tZ_i$ gates in the code: **about 9,500 physical
two-qubit gates plus syndrome rounds** ($2(k+2) = 44$ CNOT per round) **(planner arithmetic)**.  The
co-compiled QAOA demonstration confirms the ratio: 330 algorithmic two-qubit gates became 744 physical ones
(2.25x) for a circuit that has only $ZZ$ and $X$ rotations, with a post-selection rate of 33 % at 22 qubits
on H2-1 (arXiv:2504.21172); QAOA on 20 logical qubits improved over unencoded (arXiv:2409.12104).  For us the
encoded circuit has 4.4x the two-qubit count, so the acceptance rate -- which for a detection code is close
to the probability of no error at all -- would be about $0.167^{4.4} \approx 4\times10^{-4}$ on Helios
**(planner arithmetic)**, against $f = 0.167$ unencoded.  Discard rate $\approx 99.96$ %; residual error among
kept shots: the undetected two-error events, of order $(\lambda_{\rm enc}^2/2)e^{-\lambda_{\rm enc}}$ relative to
the kept clean ones, i.e. a few per cent **(ESTIMATE)**.

**Why that is a bad trade for SKQD specifically.**  Our codewords already form a detection code at zero
gate cost: every link's flux bit is stored twice (once at each end vertex, manual Step 2.4), so the seven
link-consistency checks $Z_aZ_b = +1$ are stabilisers of the code space, the vertex flags catch the
remaining single flips except an intertwiner-bit flip (which maps a valid state to another valid state of
the same sector), and the sector count catches single matter-bit flips.  Any single $X$-type error during
the circuit leaves the code space, and because every term gate is an exact unitary that maps codewords to
codewords (`src/skqd/circuits_ir.py`, control minimisation note; leakage $3.4\times10^{-14}$,
`validation/S2.json data.2x3.compiled_leakage`) it maps the orthogonal complement to itself too, so a
string that has left the code space stays out and the final decoder rejects it.  Exactly as for Iceberg,
what gets through are two-error events, $Z$ (phase) errors, and errors inside a term's CNOT frame that are
transformed into multi-qubit flips.  Yao's construction makes the same point formally: for truncated SU(2)
at $j_{\max} = 1/2$ "the first code converts Gauss's law at each vertex into a stabilizer" and corrects
single-qubit errors (arXiv:2511.13721).  The literature's 55 % systematic-error reduction with Iceberg on
the Schwinger model (arXiv:2608.02944) is for *observables* measured on an unencoded-fermion register that
has no such redundancy; it does not transfer to a register that is already Gauss-law encoded.

**Mid-circuit Gauss-law checks (gauge-symmetry error detection).**  The seven $Z_aZ_b$ link parities can be
measured between terms with one reused ancilla (two CNOT + measure-and-reset each; Helios supports
measure-and-reset, user guide), i.e. 14 two-qubit gates and 7 mid-circuit measurements per round, ten
rounds per circuit = 140 gates (+6.5 % of 2158) **(planner arithmetic)**.  This is "dynamical post-selection"
in the language of the non-Abelian symmetry-verification paper (arXiv:2412.07844: "dynamical post-selection
(DPS), based on mid-circuit measurements without active feedback, and post-processed symmetry verification
(PSV)", demonstrated for $D_3$ in 2+1D) and the Abelian Gauss-law oracles of arXiv:1812.01617; the vertex
syndrome with recovery ("gauge cooling", arXiv:2603.26819) is the correcting version, which the author shows
fails the Knill-Laflamme conditions "when singlet multiplicity exceeds one" -- our interior vertices have
multiplicity 2, so recovery is out, detection is in.  What the checks buy over the end-of-circuit decoder is
only the within-term propagation class (an $X$ error between a term's compressing CNOTs becomes a
multi-flip that may land back in the code space); the size of that class is not known for our circuits and
must be measured on the simulator before it is worth 140 gates.  Expected gain: a reduction of the near-clean
false-positive rate, not of $f$ **(ESTIMATE: tens of per cent of the false positives at best)**.

**Verdict on error detection: Iceberg is a net loss (4.4x gates for no gain in $f$); the Gauss-law code we
already have is the right detection code; mid-circuit link-parity checks are a cheap, testable add-on
whose value is an open simulator question (prompts/27 stage 1).**

---

## 4. Question 2: can the signal be amplified while the noise is left behind?

### 4.1 The limits (why the honest answer is "no, except by repetition")

- The noisy output is $\rho = f\,|\psi\rangle\langle\psi| + (1-f)\,\sigma$ with $\sigma$ the error branches.  Any
  physical post-processing is a completely positive map, and the data-processing inequality says no such
  map increases the distinguishability of $\rho$ from $\sigma$ (textbook).  Noiseless amplification exists only
  as a heralded, probabilistic operation (Ralph and Lund, "non-deterministic noiseless linear
  amplification", arXiv:0809.0326), which is just another form of post-selection.
- Unbiased error mitigation of expectation values costs samples that grow exponentially with depth
  (Tsubouchi-Sagawa-Yoshioka, arXiv:2208.09385: "unbiased estimation of an observable encounters an
  exponential growth with the circuit depth in the lower bound on the measurement cost", saturated by
  rescaling under global depolarising noise; Quek et al., arXiv:2210.11505: "a superpolynomial number of
  samples is needed in the worst case").  Sampling-based methods are not exempt: the kept fraction is
  $\le f$ plus undetected errors, and we showed above that the cost is $1/f$ then $1/f^2$.
- Grover-type amplitude amplification of the gauge-invariant component needs a coherent reflection about
  the physical subspace (a Gauss-law oracle) applied to a *clean* state; each round costs about three
  circuits ($U$, oracle, $U^\dagger$, reflection, $U$), so at $f$ per circuit one round leaves $f^3$.  It would
  help only against *coherent* leakage, e.g. Trotter error, which our exact block unitaries do not have
  ($3.4\times10^{-14}$).  Not applicable.

### 4.2 What does act like an amplifier for our purpose, with cost and gain

| technique | what it does for samples | qubits | shots | gain at 2x3 | verdict |
|---|---|---|---|---|---|
| **Shots + Gauss-law decoder + $B_{\rm sig}$** (the counting amplifier, section 2.3) | signal $\propto Nfp$, uniform noise $\propto N2^{-20}$ | 20 | $\propto 1/f$ to $2\times10^6$ per sector, then $\propto 1/f^2$ | $f = 0.01$ with $10^6$ shots equals $f = 0.17$ with $2\times10^5$ (proxy) | **the amplifier we have**; floor $f \sim 10^{-3}$ |
| Symmetry post-selection (catalogue C2, D24; arXiv:1807.10050, arXiv:1807.02467 "detection of up to 60-80 % of depolarising errors") | already in the decoder (flags, link parity, sector) | 20 | $1/f_{\rm keep}$ | built in | done; mid-circuit variant above |
| Virtual distillation / ESD (arXiv:2011.07064: "$\rho^M/\mathrm{Tr}(\rho^M)$ ... approaches the closest pure state to $\rho$ exponentially quickly"; arXiv:2011.05942: error "suppressed exponentially as $Q^n$") | estimates *expectation values* in the purified state; a bitstring probability $\mathrm{Tr}[\rho^2|x\rangle\langle x|]$ is a sum over coherences and needs the derangement gadget, variance $\propto \mathrm{Tr}[\rho^2]^{-2} \lesssim f^{-4}$ (catalogue D27) | $2\times20$ + 20 controlled swaps | to resolve $p = 10^{-3}$: $\gtrsim 1/(p^2 f^4) = 10^{6} f^{-4}$: $10^9$ at $f = 0.17$, $10^{14}$ at $f = 0.01$ **(planner arithmetic)** | none; the gadget's own 20 Fredkins add $\sim 140$ two-qubit gates per copy pair | **no**: post-selection costs $e^{\lambda}$, VD $e^{4\lambda}$, for the same purified information |
| Dominant-eigenvector principle (arXiv:2011.07064; Koczor) | says the information *is* there: with $\lambda \approx 4.6$ ($f = 0.01$) the single-error branches each carry $\sim \lambda e^{-\lambda}/(2158 \times 15) \approx 1.4\times10^{-6}$, far below $f$, so $|\psi\rangle$ dominates $\rho$ | -- | -- | explains why counting works at $f = 0.01$ | principle, not a method |
| Purification-based / subspace-expansion sampling (arXiv:2406.11533, shadows + regularised expansion) | expectation values from shadows; no sample output | 20 | $f^{-2}$ | not applicable to SKQD's support discovery | no |
| Configuration recovery, S-CORE (arXiv:2405.05068) and code-space recovery (arXiv:2607.10227: dual-rail violations as "local recovery signals") | repairs rejected strings using occupations of the current Ritz vector; the critiques show "classical uniform random sampling can reproduce SQD benchmarks" (arXiv:2608.11569) and "recovery alone (starting from randomly generated configurations) can efficiently construct accurate CI spaces" (arXiv:2605.23697) | 20 | none extra | raises usable fraction by $\sum_{k\le k^*}\lambda^k/k!$ (catalogue J4, optimistic) | **only under the manual's seven-protocol rule** (Step 7.5): report with and without; never as the device result |
| Classical ML denoising (manual Step 7; ridge Spearman 0.862 / 0.888 at 2x3, `validation/S1.json`; generative GenKSR learns Krylov sample distributions on 20 IBM qubits, arXiv:2512.19420; PIGen-SQD, arXiv:2512.06858) | re-ranks accepted strings and proposes neighbours; a generative model replaces the device | 20 | none extra | at 2x3 ML-alone already beats the device proxy at equal $|B|$ (Table 3: $3.5\times10^{-3}$ vs $8.6\times10^{-3}$ at 160) | **it re-ranks and extends; it cannot extract more device information than the counts carry**; credit only by rule 7.5 |
| Reference-string / near-clean filtering (rule M4.4; mixture estimator `skqd.clean_fraction_mixture`) | measures $f$ and the near-clean term; a per-string clean posterior needs the ideal $p(x)$, which is what we are looking for | 20 | none | diagnostic | keep as the $f$ measurement |
| ZNE / PEC / PEA / TEM (catalogue D1-D8) | for expectation values measured on the device | 20 (PEC $f^{-4}$) | $f^{-2}$-$f^{-4}$ | **not applicable**: SKQD's $H_B$ matrix elements are computed classically and exactly; the device only chooses $B$ (manual Step 5.1) | no |
| Fewer gates (section 5) | raises $f$ itself | 20 | $1/f$ | $0.167 \to 0.36$ on Helios | yes, owner decision |

**Verdict on the amplifier: physically there is none; operationally the amplifier is shots, and it is
already built (decoder + $B_{\rm sig}$).  With it the 2x3 bar is $f \gtrsim 10^{-3}$, which turns the device
question from "which device reaches 0.1" into "which device reaches $10^{-3}$ and how many shots per second
it gives".**  "A large number of qubits" helps only as logical qubits in 2029 (section 3.1); as copies for
distillation it hurts.

---

## 5. Question 3: changing what we ask the hardware to do

Every item that alters the signed family or its order is an **owner decision** (amendment 01 item 3); none
is adopted here.  Gate counts are from the repository where it has them; the rest is marked.

| change | 2x3 two-qubit gates | effect on $f$ (Helios, planner arithmetic) | what is lost | status / evidence |
|---|---|---|---|---|
| Shorter Krylov time or fewer Trotter steps | **no change**: the coarse-step family has one block per term for every $k$; only the angles change (`validation/S2.json per_term_cz` is $k$-independent); the Trotterised family (a) is $k$x deeper | -- | -- | nothing to gain |
| Drop plaq1 (the interior-corner plaquette, 764 CZ) | 1394 | $0.167 \to 0.312$ | S1 recall at $f = 0.1$: 0.977 ($B = 0$), 0.937 ($B = 1$), still $\ge 0.9$ (`data/S2D_2x3_device_requirements.json levers.term_ablation`) | unsigned lever |
| Fixed-angle generator | 1620 | $\to 0.261$ | per-term deviation from $e^{-i\theta H}$ $\sim 10^{-1}$; recall 1.0 / 0.937 (`levers.fixed_angle_generator`) | unsigned lever |
| Both combined | 1218 | $\to 0.363$ | combination's recall "UNMEASURED" (`levers.combined_...`) | needs an S1-type emulation |
| Drop both plaquettes | 1186 | $\to 0.38$ **(planner arithmetic)** | recall 0.930 / **0.895 < 0.9** in $B = 1$ | fails S1 |
| Truncate the multiplexed rotations to $\le 4$ controls (my proposal: keep the term's structure, drop the branches whose angle depends on 5-7 environment bits) | $\approx 320$ CZ **(ESTIMATE from `validation/S2.json per_term_structure`, scaling each term's CZ by the $2^c$-weighted share of its rotations with $c \le 4$; the actual decomposition minimises controls, so the true count differs)** | $\to 0.8$ (ESTIMATE) | the dropped branches are the hops at interior vertices with three flux ends -- precisely the intertwiner physics that makes 2x3 different from 2x2; the circuit stays an exact codeword-to-codeword unitary (it is a product of fewer multiplexed rotations) so leakage stays zero, but recall is unknown | the highest-leverage unsigned idea; must be emulated (prompts/27 stage 0c) before it is taken seriously |
| Per-term or per-plaquette circuits | 20-764 each | $\ge 0.55$ each | **a single term exponential from a product state only populates that term's Hamiltonian neighbours: it reproduces BFS, the classically trivial support (Table 3 BFS row).  The quantum content of a Krylov state is the interference between terms** | not worth doing |
| Reorder commuting terms for parallelism (hops on disjoint links commute) | no change in count; two-qubit depth 2302 $\to$ roughly 2302/2-3 **(ESTIMATE: at most 2-3 terms of 6-10 qubits fit in 20 qubits)** | idle term and wall time down 2-3x on a device with parallel gate zones (Helios has 4) | changes the signed order (prompts/24 P2 declined a reorder at 2x2) | owner decision; only matters if the Helios idle term turns out to dominate |
| Circuit cutting / knitting | the ladder's two halves share $\sim 8$ qubits of interface and plaq1 spans them; wire cuts cost $O(16^n)$ without and $O(4^n)$ with classical communication (arXiv:2302.03366), $4^8 = 65{,}536$ | -- | cutting reconstructs *expectation values* from signed sub-circuit results; a sampled bitstring from a quasi-probability mixture is not a sample of the full circuit, and the decoder needs single shots | no |
| Sample 2x2 sub-ladders and stitch configurations | 588 CZ per sub-ladder (2x2 on kingston) | $f \approx 0.13$ per piece (`validation/H0_2x2.json`) | the 2x2 Krylov distribution over 38 states is classically trivial, and stitching two of them is a classical proposal generator; the stitched support carries no 2x3 interference | not worth doing as a device result; fine as a *classical* control |
| Cheaper gauge-invariant ansatz (LUCJ-like, one layer) | the fixed-angle generator *is* the one-layer gauge-invariant ansatz of this encoding (one rotation per flip pattern) | as above | as above | same row |
| SqDRIFT: Krylov states by qDRIFT randomised compilation (arXiv:2508.02578: "combines SKQD with a qDRIFT randomized compilation of the Hamiltonian propagator ... while preserving the convergence guarantees") | each circuit is a random product of $M$ term exponentials, $M$ chosen; per-circuit cost $\approx M \times 216$ CZ (mean term cost) **(planner arithmetic)** | $M = 3$: $\approx 650$ CZ, $f \approx 0.6$ on Helios, $\approx 0.5$ on kingston's best edges routed **(ESTIMATE)** | many more circuits; convergence is in expectation over the random products; support coverage per circuit is BFS-like for small $M$ | the one depth-for-breadth trade with a published convergence statement; emulate (stage 0c) |
| Hardware proposes, classical diagonalises | that is SKQD; the union support of manual Step 6.4 is already the production mode; device-seeded CIPSI was emulated and did not help ($1.7\times10^{-3}$ vs $1.2\times10^{-3}$, manual 6.2) | -- | -- | nothing new |
| IBM fractional $R_{ZZ}$ gates | none: our two-qubit gates are CNOTs inside multiplexed rotations, not small-angle $ZZ$; a CNOT is one $R_{ZZ}(\pi/2)$ plus one-qubit gates | -- | -- | no gain (catalogue B3 applies to $ZZ$-type circuits) |

---

## 6. Ranked table (gain on $f$ or on the endpoint, overhead, readiness, source)

| rank | technique | gain | overhead | readiness | source |
|---|---|---|---|---|---|
| 1 | **Shots: counting amplifier with $B_{\rm sig}$** | lowers the usable $f$ from 0.1 to $\sim 10^{-3}$ at 2x3 | $1/f$ shots to $2\times10^6$ per sector, $1/f^2$ beyond; 0 qubits | today (built) | section 2.3 prototype; manual Steps 4.4, 6.3; prompts/24 P9 |
| 2 | **A device with $\epsilon_2 \lesssim 8\times10^{-4}$ and a non-serial idle budget** (Helios class) | $f_{\rm gates} = 0.167$ for the signed family | USD 62 per shot at list; idle unknown | today for the gates; access and idle open | arXiv:2511.05465; Azure pricing; Helios user guide |
| 3 | **Fewer gates in the family** (no plaq1; fixed-angle; both) | $f$ 0.167 $\to$ 0.31-0.36 on Helios; shots halved | owner signature; recall re-emulated | today | `data/S2D_2x3_device_requirements.json levers` |
| 4 | **Truncated multiplexed rotations** ($\le 4$ controls) | $f \to \sim 0.8$ if recall survives (ESTIMATE) | unknown recall loss; owner signature | needs emulation | `validation/S2.json per_term_structure` |
| 5 | **SqDRIFT** (random short products of terms) | $f \approx 0.5$-$0.6$ per circuit | many circuits; BFS-like per circuit | needs emulation | arXiv:2508.02578 |
| 6 | **Mid-circuit Gauss-law parity checks** (DPS) | fewer near-clean false positives (tens of per cent, ESTIMATE); no gain in $f$ | +140 two-qubit gates, 70 MCMR per circuit | today on ions (MCMR) | arXiv:2412.07844, arXiv:1812.01617, arXiv:2511.13721 |
| 7 | **Configuration recovery / ML re-ranking** | raises usable fraction, re-ranks tail | 0 qubits; must pass rule 7.5 against ML-alone and random | today | arXiv:2405.05068, 2607.10227, 2608.11569, 2605.23697, 2512.19420 |
| 8 | **Parallel term ordering** | idle and wall time 2-3x (only if idle dominates) | signed order changes | today | prompts/24 P2 |
| 9 | **STAR / early-FT analog rotations** | $f \approx 0.5$-$0.8$ (ESTIMATE) | $10^4$ physical qubits at $p = 10^{-4}$ | 2029 class | arXiv:2303.13181 |
| 10 | **Full QEC (surface / qLDPC / colour) with Clifford+T** | $f \to 1 - 10^{-3}$ | $10^5$ $T$ per shot, $10^4$-$10^5$ physical qubits | 2029+ (Starling, Apollo) | arXiv:2408.13687, 2308.07915, 2409.17595, 1403.2975, roadmaps |
| 11 | **Iceberg error detection** | none in $f$; cleaner kept shots | 4.4x two-qubit gates, acceptance $\sim 4\times10^{-4}$ | today | arXiv:2211.06703, 2504.21172, 2409.12104, 2602.22211 |
| 12 | **Virtual distillation / ESD** | none for samples | 2x qubits, $f^{-4}$ shots | -- | arXiv:2011.07064, 2011.05942 |
| 13 | **ZNE / PEC / TEM / cutting** | not applicable to SKQD's subspace step | -- | -- | arXiv:2208.09385, 2210.11505, 2302.03366 |

---

## 7. What "substantial" means and the route to it (summary; the plan is prompts/27)

**The claim** (preregistered, manual Step 6.3 / gate P1): on 2x3 hardware data, the curves $E_R - E_0$ and
recall versus $|B|$ for $B_{\rm sig}$ and for CIPSI, BFS, random and ML-alone at equal $|B|$, with bootstrap
bands over circuits, plus the certified intervals of Step 5 (H1/H2).  Three tiers, each a complete claim:

- **Tier A** ($|B| \le 100$): $B_{\rm sig}$ beats random with non-overlapping bands and matches BFS; $E_0$
  inside the Weinstein interval.  Proxy cost $2\times10^4$ shots per sector at $f = 0.17$.
- **Tier B** ($|B| \approx 200$, recall of the 99.9 % support $\ge 0.9$): the manual's H1/H2 criteria
  (interval width $\le 0.1$, recall $\ge 0.8$) and the P1 curve to $|B| = 200$.  Proxy cost $2\times10^5$ per
  sector at $f = 0.17$, $10^6$ at $f = 0.01$.
- **Tier C** ($|B| \approx 320$, device beats BFS 4x, CIPSI still 2.5x better): $10^6$ per sector at
  $f = 0.17$.

**Cheapest route today, in order:** (0) the simulator stage (0 QPU s): make the tier arithmetic a gate on
the proxy and on a Helios-class Aer device model, and emulate the three unsigned levers; (0b, optional,
$\le 300$ s of the 498 s left) measure $f$ of two signed $k = 1$ 2x3 circuits on ibm_kingston with the
reference-string statistic -- at $f \sim 10^{-4}$ the expected reference hits are $\approx 8$ in $10^5$ shots
against 0.1 from garbage **(planner arithmetic: $N f p_{\rm ref}\,0.82$ with $p_{\rm ref} \approx 0.5$)**, so the
number is measurable, and it decides whether IBM is dead or a ten-hour Tier-B run; (1) the Helios emulator
(eHQC or Nexus seconds, no QPU) for the idle term; (2) a QCUP proposal for Helios/H2 time; (3) a 4,000-shot
pilot ($\approx 2\times10^4$ HQC) then Tier A/B.

**Medium-term route (1-3 years):** Helios-class ions with the unsigned cheaper family ($f \approx 0.36$),
mid-circuit Gauss-law checks if the simulator shows they cut false positives, 2x4 only if a device reaches
$\epsilon_2 \le 3.3\times10^{-5}$ or the truncated/SqDRIFT families pass recall at 2x4.

**Fault-tolerant route (2029+):** section 3.1.

**Not worth doing:** Iceberg encoding of this register; virtual distillation; ZNE/PEC on SKQD; per-term
circuits; stitched 2x2 sub-ladders as a device result; any 2x3 run on IonQ Forte/Forte Enterprise
($f = 8.6\times10^{-5}$ on the spec and $10^{-5}$-$10^{-7}$ on the day-measured values, 6 years per sector at
$10^3$ shots per second); 2x4 on anything that exists.

---

## 8. Problems, assumptions, and what is NOT established

- The Helios $f = 0.167$ is gate-only on the vendor's Table-2 infidelities; the memory/idle term for a
  20-qubit serial program is unknown (section 2.2).  The 2x2 campaign showed the idle term can be 15-50x.
- The counting-amplifier scan is the Step-8.2 proxy, whose near-clean structure is Poisson flips; on fez
  and kingston the near-clean term was about 20 % of accepted shots **(planner arithmetic from
  `validation/H0_2x2.json data.support."B=0"`: 9454 accepted, 0.82 x 0.127 x 69505 = 7238 clean,
  0.0093 x 0.873 x 69505 = 564 garbage)**.  The $1/f$ then $1/f^2$ law is a derivation under uniform garbage;
  below $f = 0.01$ the proxy's accepted set is dominated by near-clean strings (section 2.3 caveat), so
  the proxy rows there are optimistic and the "floor $f \approx 10^{-3}$" is the planner's reading of the two
  limits, not a measurement.
- HQC price per unit is inferred from the Standard plan (USD 125k for 10k HQC); pay-as-you-go and QCUP
  terms are not public.  The HQC formula counts one-qubit gates; Quantinuum's native $R_z$ is a frame change,
  and whether it is billed was not checked.
- The FT numbers (section 3.1) are order-of-magnitude: the $T$ count assumes Ross-Selinger synthesis of
  every $R_y$ separately; the distance estimate extrapolates Google's $\Lambda$; no lattice-surgery routing
  overhead was counted.
- The truncated-rotation lever (section 5) is an estimate from the S2 structure record; the real
  decomposition minimises controls (`_multiplexed_two_level`), so the CZ count after truncation must be
  compiled, and the recall must be emulated, before the number means anything.
- The 2x3 kingston $f$ pilot is proposed, not run; its prediction bracket comes from gate K0's three $f$'s
  (prompts/25 Part A) once that gate exists.
- No abstract I fetched gives a post-selection *rate* for the Iceberg code at our depth; the $4\times10^{-4}$
  is my scaling of the unencoded $f$ by the physical gate ratio, cross-checked only against the 33 % at 744
  gates of arXiv:2504.21172.
- The ORNL QCUP page lists Quantinuum "N $\ge$ 56 qubits" (H2 class); whether Helios is in the program is
  not stated.

---

## 9. Sources fetched on 2026-10-02 (abstract or page read; quotes in the text are verbatim from them)

arXiv:2511.05465 (Helios, Table 2 and Secs. II.3, III.2.4 via the HTML version); arXiv:2404.02280
(Quantinuum/Microsoft logical qubits); arXiv:2408.13687 (Google below-threshold surface code);
arXiv:2308.07915 (IBM gross code); arXiv:2312.03982 and arXiv:2506.20661 (Harvard/QuEra logical
processors); arXiv:2303.13181 (STAR); arXiv:2211.06703 (Iceberg); arXiv:2602.22211 (Helios 48-94 logical
qubits); arXiv:2504.21172 (Iceberg co-compilation, 744 physical gates, 33 %); arXiv:2409.12104 (QAOA with
Iceberg, 20 logical qubits); arXiv:2409.17595 (magic-state cultivation); arXiv:1403.2975 (Ross-Selinger);
arXiv:2011.07064 (virtual distillation); arXiv:2011.05942 (ESD); arXiv:2405.05068 (SQD); arXiv:2608.11569
and arXiv:2605.23697 (random-sampling critiques); arXiv:2608.05314 (SQD review); arXiv:2501.07231 (QSCI
limitations); arXiv:2607.10227 (code-space recovery); arXiv:2312.00733 (CVaR bounds); arXiv:2406.11533
(shadow subspace expansion); arXiv:1807.10050 and arXiv:1807.02467 (symmetry verification);
arXiv:1812.01617 (Gauss-law oracles); arXiv:2412.07844 (non-Abelian symmetry verification, DPS/PSV);
arXiv:2511.13721 (SU(2) gauge-redundancy codes); arXiv:2608.02944 (sparse error detection for LGT);
arXiv:2603.26819 (gauge cooling); arXiv:2508.02578 (SqDRIFT); arXiv:2501.09702 (SKQD); arXiv:2510.26951
(SKQD Schwinger); arXiv:2602.18080 (SU(2) hadron dynamics, 156 qubits); arXiv:2208.09385 and
arXiv:2210.11505 (mitigation cost bounds); arXiv:2210.00921 (mitigation review); arXiv:0809.0326 (noiseless
linear amplification); arXiv:1904.00102 and arXiv:2302.03366 (circuit cutting); arXiv:2512.19420 (GenKSR);
arXiv:2512.06858 (PIGen-SQD); arXiv:2511.02125 (Helios Fermi-Hubbard).  Vendor pages: Quantinuum H2 and
Helios product pages, Helios user guide (docs.quantinuum.com, job limits, MCMR), emulator page (H2-1E 32
state-vector qubits, noise model with memory and leakage), parameterised-angle gate page ($R_{zz}$ in
half-turns; error grows with angle); Azure Quantum pricing (HQC formula, plans); IBM roadmap (Starling 2029);
ORNL QCUP page; HPCwire 2025-11-05 and computerweekly (Quantinuum roadmap quotes).

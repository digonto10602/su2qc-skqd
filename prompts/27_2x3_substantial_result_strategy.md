# 27 — A substantial 2x3 result: the staged plan (simulator stages first, then the device question)
executor: executor-opus   effort: high
time budget: stage 0 about 2 executor days of laptop time (no command above 30 min); stage 1 one or two Perlmutter CI tokens (owner must allowlist them); stages 2-4 are owner actions and QPU decisions, not executor work   machine: laptop; Perlmutter GPU (stage 1); QPU only after an explicit owner decision

Planner analysis behind this prompt: `reports/2x3_qec_amplification_strategy_20261002.md` (every
literature number with its arXiv ID, every repository number with its file and key, every estimate
labelled).  Read it first.  prompts/26 is being written in parallel by another planner; nothing here depends
on it and nothing here may edit it.

## Goal

The owner asked (2026-10-02): "figure out if quantum error correction techniques can help with the 2x3 case
or not, can we build an amplifier which can amplify the signals and leaves noise, try to come up with a plan
in which way we can get something substantial from 2x3 runs on quantum computers, may be use large number of
qubits which also do error corrections etc."

The analysis answers: QEC is a 2029-class option ($\sim 10^5$ $T$ gates per shot); error detection by an
Iceberg code is a net loss because the Gauss-law codewords already are a distance-2 detection code; there
is no quantum amplifier, but **shots are one**: with the decoder and $B_{\rm sig}$ the usable clean fraction
at 2x3 drops from the signed 0.1 to about $10^{-3}$ (cost $\propto 1/f$ up to $2\times10^6$ shots per sector,
$\propto 1/f^2$ beyond).  The substantial result is the manual's primary endpoint P1 on 2x3 hardware data
(device support versus CIPSI/BFS/random/ML at equal $|B|$ with bootstrap bands; expected: device between BFS
and CIPSI).  This prompt turns the planner's prototypes into gates, so that every later device decision is
made on a JSON, and lists the owner decisions in the order they are needed.

**Nothing in this prompt spends QPU seconds.**  Stage 0b (a 2x3 clean-fraction pilot on ibm_kingston) is
written as a preregistration the owner can sign; it is not executed by this prompt.

## Inputs (read these before writing code; use graphify first)

- `graphify-out/graph.json` exists: orient with `graphify query "<question>"`, `graphify explain "<symbol>"`,
  `graphify path "A" "B"`, `graphify affected "<symbol>"` before grepping or reading whole files; after
  changing code run `graphify update .` (seconds, no API cost).  Start with
  `graphify explain "emulate"` (scripts/gate_S1.py), `graphify explain "measure_and_decode"`,
  `graphify explain "controls.py"`, `graphify explain "clean_shot_fraction"`,
  `graphify explain "structured_term_gates"`, `graphify explain "_multiplexed_two_level"`,
  `graphify explain "coarse_states"`, `graphify explain "reference_string_test"`.
- Planner prototypes (reproduce, then supersede): `scratch/planner/lowf_counting_amplifier_20261002.py`
  (+ `.json`, `.log`), `scratch/planner/lowf_tiers_20261002.py` (+ `.log`),
  `scratch/planner/helios_2x3_feasibility_20261002.py` (+ `.json`),
  `scratch/planner/two_qubit_depth_2x3_20261002.json`.
- Emulation path: `scripts/gate_S1.py` (`emulate`, `P_RO`), `scripts/s2d_recall_at_predicted_f.py`,
  `src/skqd/noise.py`, `src/skqd/controls.py` (`cipsi`, `bfs`, `random_support`, `oracle`, `top_by_count`),
  `src/skqd/skqd.py` (`ritz`, `certify`, `support_metrics`, `exact_support`, `poisson_lambda_star`,
  `reference_string_test`, `clean_fraction_mixture`), `src/skqd/ml.py` (`RidgeRanker`, `features`).
- The $B_{\rm sig}$ definition and the random/garbage baselines as implemented for 2x2:
  `scripts/gate_H0_2x2.py` (`stage_assemble`; keys `data.support.*.B_sig`, `data.baselines.*`),
  prompts/24 decision P9.
- Circuits and counts: `validation/S2.json` (`data.2x3.per_term_structure`, `per_term_cz`,
  `ir_gate_counts_coarse_step`, `compiled_leakage`), `data/S2D_2x3_device_requirements.json`
  (`counts`, `levers`), `scripts/gate_S2D.py` (`circuit_set(3)`, `analyse_rzz`),
  `src/skqd/circuits_ir.py` (`CircuitFactory`, `structured_term_gates`, `angle_mode`),
  `src/skqd/device_req.py`.
- Device model path for stage 1: `scripts/s3_device_model.py`, `slurm/s3_2x3.sbatch`, `validation/S3.json`
  (`data.seconds_per_shot_used_for_projection` = 0.0199 s per shot at 20 qubits on the Perlmutter GPU, job
  58771538), `RUNBOOK.md` ("Engine and HPC policy": Aer-GPU on qiskit 1.4.3 for hardware-matching gates;
  record wall time, per-phase timings, GPUs, s/shot, peak GPU memory, utilisation), `ci/README` and
  `scripts/ci_request.sh` / `ci_check.sh`.
- The 2x2 clean-fraction measurement machinery to be reused for stage 0b: `scripts/gate_H0_kpilot.py`
  (`decode_counts`, the reference-string statistic), `scripts/h0_submit.py`, `scripts/h0_backends.py`
  (`calibration_fingerprint`), `validation/H0_kpilot.json` (`data.decision`), `validation/H0_2x2.json`
  (`data.clean_fraction.pooled`), prompts/21 and prompts/24 (preregistration format).
- Package pins: the `coding` env (qiskit 2.5.2, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.49.0, numpy 2.5.2,
  scipy 1.18.0, Python 3.12.14) must not change; Perlmutter CI code must also run on qiskit 1.4.3.

## Conventions that must not change (CLAUDE.md rule 2)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py` (qubit $k$ = bit $k$, little-endian).  The
signed family and its term order, the signed budget (mean $f \ge 0.1$, worst $\ge 0.05$), $\lambda^* = 6.2958$,
the D3' rule (margin 0.7, floor 267, round to 100), $B_{\rm sig}$ (one-sided $3\sigma$ Poisson above the
uniform-noise expectation $\mu_s = N a/\dim$ with $a$ the exhaustive sector acceptance) are unchanged.  No
tolerance of any existing gate changes.  Every unsigned circuit variant is emulated and reported as a
*candidate*; adopting one is an owner signature (amendment 01 item 3).

## Definitions used by the gates below

- **Claim tiers** (planner, section 7 of the analysis), each evaluated per sector on $B_{\rm sig}$ with the
  references always included:
  - **Tier A**: $|B_{\rm sig}| \ge 40$; $E_R(B_{\rm sig}) - E_0$ below the 2.5th percentile of 200 random
    equal-size bases (bootstrap over circuits gives the device band; the two bands must not overlap);
    $E_R(B_{\rm sig}) \le 1.5 \times$ the BFS error at equal size; $E_0$ inside the Weinstein interval.
  - **Tier B**: Tier A plus recall of the 99.9 % support $\ge 0.8$ (manual gate H1) and the gap-assumed
    certified interval of width $\le 0.1$ containing $E_0$ (H1), cluster energy certified to
    $\pm r_H \le 0.15$ at $B = 1$ (H2); the P1 curve reported to $|B| = |B_{\rm sig}|$.
  - **Tier C**: Tier B plus $|B_{\rm sig}| \ge 300$ and device error $\le 0.5 \times$ BFS at equal size.
- **Shot-versus-$f$ curve**: for each $f$ the smallest $N$ per sector (on a fixed grid) at which each tier
  holds in $\ge 2$ of 3 seeds.
- **Noise proxies**: (P) the manual Step-8.2 proxy (`skqd.noise`); (D) an Aer device model (stage 1).

## Steps

### Stage 0 — laptop, 0 QPU s: make the tier arithmetic a gate (gate T0_2x3_tiers; about 1 executor day)

Script `scripts/gate_T0_2x3_tiers.py`, output `validation/T0_2x3_tiers.json` + `reports/T0_2x3_tiers.md`
(via `skqd.report.GateResult`; never a typed number).  `--quick` runs one seed and the two smallest budgets.

T0.1 Reproduce the planner's prototype exactly: with seed 20261002, proxy (P), $B = 0$, all 8 references,
    $k = 1..4$ (32 circuits), $f = 0.17$, $N = 2\times10^5$: $|B_{\rm all}| = 340$, $|B_{\rm sig}| = 200$,
    $E_R(B_{\rm sig}) - E_0 = 1.5037\times10^{-3}$, recall(99.9 %) $= 0.98837$, CIPSI at 200 $= 5.835\times10^{-4}$,
    BFS at 200 $= 1.285\times10^{-3}$ (`scratch/planner/lowf_counting_amplifier_20261002.json cells[0]`).
    Tolerance: exact integers, energies to $10^{-9}$ (same code path, same seed).  If the executor's
    implementation differs from the prototype's (e.g. a vectorised decoder), reproduce to $10^{-9}$ first with
    the prototype's loop, then switch.

T0.2 Grid: $f \in \{0.36, 0.17, 0.10, 0.05, 0.02, 0.01, 0.003, 0.001\}$, $N \in \{2, 5, 20, 50, 100, 400\}\times10^4$
    per sector, seeds $\{20261002, 1, 2\}$, both sectors ($B = 1$: 3 references, 12 circuits).  Per cell record:
    accepted, $\mu_s$, $c_{\rm sig}$, $|B_{\rm all}|$, $|B_{\rm sig}|$, false positives (weight $< 10^{-8}$) in both,
    recall of the 99.9 % and 99 % supports, $E_R - E_0$ for both bases, $r_H$, Weinstein and Kato-Temple
    intervals and whether $E_0$ is inside, random-equal-size (200 seeds) mean / 2.5th percentile / percentile
    of the device value, CIPSI, BFS and ML-alone (`skqd.ml.RidgeRanker`, leakage-safe training as in gate
    S1) at $|B_{\rm sig}|$, and the **bootstrap band**: resample the 32 (12) circuits with replacement 200
    times, recompute $B_{\rm sig}$ and $E_R$, report the 2.5-97.5 % band.  Skip cells with
    $N > 4\times10^6$ if the 30-minute rule bites; record `completed: false` with the reason.

T0.3 Tier evaluation per cell and the shot-versus-$f$ curve per tier and sector (the result; no criterion).
    Fit $\log N_{\min}$ against $\log f$ on the $\mu_s < 1$ cells and on the $\mu_s > 1$ cells separately and
    report both slopes (planner expects about $-1$ and about $-2$).

T0.4 Thresholds for the tier definitions are the ones above; they are **preregistered here** and may not be
    tuned to the outcome.  If a tier is never reached at any $f$ on the grid, that is the result.

Pass criteria of T0 (PASS iff all hold; the curves carry no criterion):
- T0.a the reproduction of T0.1 holds to the stated tolerances;
- T0.b CIPSI and oracle at $|B| = 160$ and $320$ reproduce `validation/S1.json data.table3` ("B=0|CIPSI|160"
  $= 1.2012\times10^{-3}$, "B=0|oracle|320" $= 6.7208\times10^{-5}$) to $10^{-9}$ (same code path);
- T0.c for every cell $E_R(B_{\rm sig}) \ge E_0 - 10^{-9}$ and $E_R(B_{\rm all}) \le E_R(B_{\rm sig}) + 10^{-9}$
  (variational, and the larger basis is never worse);
- T0.d every random-equal-size baseline includes the references (as `controls.random_support` does);
- T0.e `pytest -q tests` and `python scripts/check_package.py` pass; add `tests/test_t0_tiers.py` (the
  $c_{\rm sig}$ threshold on synthetic Poisson counts; the bootstrap band on a synthetic 3-circuit set; the tier
  predicate on hand-built inputs).

### Stage 0c — laptop, 0 QPU s: the three unsigned levers emulated the same way (gate T0c_levers; about half a day)

For each candidate family build the circuits with the existing factory and sample them through proxy (P) at
$f$ taken from the Helios gate-only table (`scratch/planner/helios_2x3_feasibility_20261002.json rows`) and
at $f = 0.1$, $N = 2\times10^5$, three seeds, both sectors; report recall of the 99.9 % support, $|B_{\rm sig}|$,
tier reached, CZ count (all-to-all compile) and the leakage check:

1. **no plaq1** (existing: `levers.term_ablation`; drop the `plaq1` block) -- must reproduce
   `levers.term_ablation.recall_at_f_0.1` (0.9767 / 0.9368) to $10^{-9}$ with the S2 escalation seeds;
2. **fixed-angle + no plaq1** (`CircuitFactory(..., angle_mode="fixed")` without `plaq1`): the combination
   `levers.combined_fixed_angle_no_plaq1_virtual_rz` lists as "UNMEASURED";
3. **truncated multiplexed rotations**: add an *optional* keyword to `structured_term_gates` /
   `_multiplexed_two_level` (default off, no change to any default path) that drops every multiplexed
   rotation whose minimised control count exceeds $c_{\max} \in \{3, 4\}$; verify on the full-space simulator
   that the truncated term unitary still maps every codeword to a codeword (leakage $\le 10^{-12}$, the
   S2 check) and record its CZ count; then emulate.  Planner's estimate: about 320 CZ at $c_{\max} = 4$ (from
   `validation/S2.json per_term_structure`); the executor's compiled count replaces it.
4. **SqDRIFT-style random products** (arXiv:2508.02578): circuits that apply $M \in \{2, 3, 5\}$ terms drawn
   with probability $\propto \|H_\gamma\|$ (use the term coefficients' 1-norms from `term_groups`), each for
   time $\tau = \lambda t/M$ with $\lambda = \sum_\gamma \|H_\gamma\|$, $t = k\Delta t$; 32 random circuits per
   reference-$k$ pair at $N$ shots in total equal to the signed family's budget; report the same metrics and
   the mean CZ per circuit.

Pass criteria of T0c: (a) item 1 reproduces the recorded recalls; (b) leakage $\le 10^{-12}$ for every
truncated circuit; (c) the SqDRIFT sampler's term frequencies match the target probabilities to within
$3\sigma$ binomial over the generated circuits; (d) pytest + check_package with `tests/test_t0c_levers.py`.
The tier results are the output, not a criterion.  **Do not adopt any variant**: the report ends with a table
"family / CZ / $f$ Helios / $f$ kingston-best-patch / recall / tier at $N$" for the owner.

### Stage 0b — written, not run: the 2x3 clean-fraction pilot on ibm_kingston (preregistration only; owner decision D1)

Produce `reports/K1_2x3_fpilot_prereg_draft.md` and `scripts/gate_K1_2x3_fpilot.py --dry-run` (no
submission path is called without `--live`, and `--live` is refused unless the file
`data/owner_decision_<date>_k1_2x3_fpilot.md` exists):
- circuits: the two signed $k = 1$ circuits with the largest ideal reference-string probability
  $p_{\rm ref}$ (one per sector), routed on the day's record exactly as gate K0 does (prompts/25 Part A), ALAP
  with explicit delays, client-side XY4 in windows $\ge 1.024\,\mu$s (the adopted 2x2 cell T3);
  plus the two readout pubs;
- shots: $10^5$ per circuit (planner: at $f = 10^{-4}$ and $p_{\rm ref} \approx 0.5$ the expected reference
  hits are $N f p_{\rm ref}\,0.82 \approx 8$ against $N 2^{-20} \approx 0.1$ from garbage);
- prediction bracket from gate K0's `f_gates_layout`, `f_idle_aware` (echo and transferred 0.174) and
  `f_idle_aware_xy4`; decision rule on the pooled reference-string $f$ with its 95 % interval:
  **GO-B** if $f \ge 10^{-3}$ (a Tier-B run costs $\le 2\times10^7$ shots per sector, about 6 h at the 2x2 run's
  2,700 shots per second, `validation/H0_2x2.json data.live` 141,907 shots in 53 s -- the executor
  recomputes the rate), **GO-A** if $3\times10^{-4} \le f < 10^{-3}$ (Tier A only), **NO-GO** below;
- QPU estimate by `scripts/h0_qpu_time.py` (planner: $\le 300$ s of the 498 s left); fingerprint guard D9.

This stage has no pass criterion beyond the dry run passing; it is a document for decision D1.

### Stage 1 — Perlmutter GPU, 0 QPU s: the device-model version (gate S3H_2x3; needs a CI token, owner decision D2)

Under the RUNBOOK engine policy (Aer-GPU, qiskit 1.4.3 on the CI), extend `scripts/s3_device_model.py` with
a **Helios-class noise model**: depolarising $7.9\times10^{-4}$ on every RZZ, $2.5\times10^{-5}$ on every
one-qubit gate, readout $4.8\times10^{-4}$, and a per-layer memory channel of $5\times10^{-4}$ per qubit per
two-qubit layer **as the pessimistic end** and $0$ as the optimistic end (arXiv:2511.05465 Table 2 and
Sec. III.2.4; the true per-layer value for a 20-qubit serial program is unknown -- this is the bracket the
Helios emulator will later settle).  Sample the signed family and the no-plaq1 family, both sectors,
$N = 5\times10^4$ per sector per family per end (the S1 multi-reference budget; recall 0.97 at $f = 0.1$),
and evaluate the tier predicate and the shot-versus-$f$ point exactly as T0 does, with the measured
reference-string $f$ per circuit.  Also run the **mid-circuit link-parity variant** on the signed family at
the optimistic end: after each term block, for each of the 7 links, CNOT both flux bits into one reused
ancilla, measure, reset; discard the shot if any parity is 1; report the near-clean false-positive count of
$B_{\rm sig}$ with and without the checks at equal shots.  Budget: $0.0199$ s per shot at 20 qubits
(`validation/S3.json`) gives $5\times10^4 \times 2 \times 2 \times 2 \approx 4\times10^5$ shots $\approx 2.2$ h plus the
check variant $\approx 0.6$ h: **two CI tokens of 60 min each plus one for the variant**, or three days of the
"one job per hour" loop; parallelise only along sector / family / shot batch as the policy says; record
wall time, per-phase timings, GPUs, s/shot, peak GPU memory and utilisation in the JSON.

Pass criteria of S3H: (a) noiseless run of each family reproduces the exact Krylov sampling distribution of
`skqd.krylov.coarse_states` to total-variation $\le 3\sqrt{2^{20}/N}$ on the accepted strings (the L2/L5
style identity check); (b) the measured reference-string $f$ of each circuit at the optimistic end lies
within the 95 % interval of the gate-only prediction `clean_shot_fraction` on the circuit's own counts
(0.167 for the signed family at $k = 1$; note the $k$-independence); (c) the link-parity variant changes no
accepted-string count in the noiseless run (the checks are stabilisers of the code space: a PASS here is the
proof that the construction is right); (d) GPU bookkeeping fields present; (e) pytest + check_package.  The
tier table, the pessimistic/optimistic $f$ bracket and the false-positive reduction are the outputs.

### Stage 2 — owner actions (0 QPU s): access and the vendor numbers

- D3: apply to ORNL QCUP for Quantinuum time (H2 "N $\ge$ 56 qubits" is listed; ask whether Helios is), or
  open a Quantinuum research conversation; ask for: the measured two-qubit infidelity and memory error per
  layer for a 20-qubit serial program, the scheduler's parallelism, whether $R_z$ is billed, the HQC
  pay-as-you-go rate, and emulator access (H2-1E: 32 state-vector qubits with memory and leakage in the
  noise model).
- Executor work once an emulator key exists (gate Q0P_2x3, mirrors prompts/25 I0P): native-gate
  conversion to `{Rz, PhasedX, ZZPhase}` with ZZPhase in half-turns ($R_{ZZ}(\varphi) = e^{-i\varphi ZZ/2}$ is
  ZZPhase($\varphi/\pi$)), verified to $10^{-10}$ against the statevector; HQC per circuit; a 4,000-shot emulator
  run of the two $k = 1$ circuits, the reference-string $f$ and its 95 % interval, and the tier predicate
  from T0 at that $f$.  This is the gate that replaces the stage-1 bracket by the vendor's own number.

### Stage 3 — QPU (owner decision D4, only after Q0P): the Helios/H2 pilot and the run

- Pilot: the two $k = 1$ circuits, 2,000 shots each, plus readout; GO if the pooled reference-string
  $f \ge 0.1$ (signed) or, under an explicit waiver like the 2x2 one, $\ge 10^{-2}$ (Tier B at $10^6$ shots).
- Run: D3' shot plan at the measured $f$, both sectors, Tier A then B as the budget allows; the P1 analysis
  of T0 on the hardware counts; H1/H2/P1/M1 rows filled from `validation/`.

## QPU seconds and money

0 on IBM, 0 on IonQ, 0 on Quantinuum, 0 on Braket/Azure by this prompt.  Stage 0b spends $\le 300$ s only if
the owner signs D1.  Stage 3 at Helios list price is USD 62 per shot for the signed family (planner
arithmetic from the Azure HQC formula and the Standard plan); a Tier-B run of $2\times10^5$ shots per sector
is about $2\times10^6$ HQC, which only an allocation can pay.  The executor must put the HQC and USD figures
of every proposed run in the gate JSON next to the shot count.

## Outputs

- `scripts/gate_T0_2x3_tiers.py`, `validation/T0_2x3_tiers.json`, `reports/T0_2x3_tiers.md`,
  `tests/test_t0_tiers.py`;
- `scripts/gate_T0c_levers.py`, `validation/T0c_levers.json`, `reports/T0c_levers.md`,
  `tests/test_t0c_levers.py`; the optional truncation keyword in `src/skqd/circuits_ir.py` with its default
  off and a test that the default path is byte-identical (same IR) to before;
- `scripts/gate_K1_2x3_fpilot.py` (dry run only), `reports/K1_2x3_fpilot_prereg_draft.md`;
- stage 1: `scripts/s3_device_model.py` extension (`--noise helios-pessimistic|helios-optimistic`,
  `--link-parity-checks`), `validation/S3H_2x3.json`, `reports/S3H_2x3.md`, the sbatch under `slurm/`,
  `tests/test_s3h_noise.py`;
- `validation/gates.md` rows for T0_2x3_tiers, T0c_levers, S3H_2x3 (K1 appears as "prereg draft, not
  run"); `reports/PROJECT_STATUS.md`: one paragraph; `graphify update .` after code changes;
- git: `git commit <paths>` after each gate (retry if `.git/index.lock` exists); **no push**.

## Escalation and STOP conditions

- STOP (binding) if T0.1 cannot reproduce the prototype to $10^{-9}$ after two attempts: the planner's
  numbers would be wrong; write `validation/BLOCKED.md` with the first differing quantity.
- STOP if any tier threshold would have to change to make a cell pass; thresholds are preregistered.
- STOP if the truncated-rotation variant leaks ($> 10^{-12}$): report the first leaking term and stop; do not
  "fix" it by projecting.
- STOP if a stage needs a QPU key, a CI token not in the allowlist, a package change in `coding`, a change
  to the signed family, or a change to any existing criterion constant.
- Retry rule: one re-run per cell on a seed failure; after two failed attempts at any pass criterion,
  BLOCKED.md and the planner returns.

## Do-not-touch list (binding)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py`, `device_req.py` (add nothing that changes a
value), every existing `validation/*.json`, every frozen circuit under `data/hardware/`, the signed family
and its order, every criterion constant of every existing gate, `ci/`, `prompts/00`-`26`, `prompts/LOG.md`
rows of others.

## Owner decisions (in the order they are needed)

| # | decision | needed for | planner's recommendation |
|---|---|---|---|
| D1 | run the 2x3 clean-fraction pilot on ibm_kingston ($\le 300$ s of the 498 s left; preregistered GO-B / GO-A / NO-GO rule) | the only cheap measurement that decides whether any IBM 2x3 run exists | yes: it is the first measured 2x3 number of the project and costs under 300 s |
| D2 | allowlist Perlmutter CI tokens `S3H` (two or three 60-min jobs) | stage 1 | yes |
| D3 | apply for Quantinuum time (ORNL QCUP) and/or an emulator key; ask the vendor the five questions of stage 2 | stages 2-3 | yes; nothing else reaches the signed budget at 2x3 today |
| D4 | whether an unsigned cheaper family (no plaq1 $f = 0.31$; fixed-angle + no plaq1 $f = 0.36$ on Helios) may be adopted for a device run if T0c keeps recall $\ge 0.9$ | halves the HQC cost | decide after T0c, not before |
| D5 | whether the signed term order may be re-ordered for parallelism (only if S3H's pessimistic end dominates) | Helios idle term | decide after S3H |
| D6 | whether Tier A or Tier B is the preregistered claim for the first 2x3 hardware run | prereg | Tier B if $f \ge 10^{-2}$ on the device, Tier A otherwise |
| D7 | 2x4: no action (every path needs $\epsilon_2 \le 3.3\times10^{-5}$ or a family that T0c has not yet shown to keep recall) | -- | defer |

## LOG row (append to `prompts/LOG.md`, one row per gate; the planner's own row is added by the coordinator)

| date | prompts/27_2x3_substantial_result_strategy.md stage 0 / 0c / 0b / 1 | T0_2x3_tiers / T0c_levers / K1 (draft) / S3H_2x3 | executor-opus | PASS/FAIL with the verdict numbers from the JSON (shot-versus-$f$ slopes; tier table per family; $f$ bracket and false-positive reduction from S3H) | commit | open owner decisions D1-D7 |

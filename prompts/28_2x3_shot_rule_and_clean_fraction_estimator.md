# 28 — The 2x3 shot rule (D3'-R) and the clean-fraction estimator: decisive trajectory test, tail-class statistic, Stage E / P GO rule, 2x2 information block
executor: executor-opus   effort: high
time budget: Part A about 3 h of laptop wall time in background chunks of <= 25 min each (no single foreground command above 30 min); Part B about one executor day   machine: laptop (0 QPU seconds, 0 HQC, 0 eHQC on every provider; no push)

Planner analysis behind this prompt: `reports/2x3_shot_rule_estimator_ruling_20261003.md` (read it first; every
number there is traced to `validation/*.json`, `data/*.json`, or the planner prototype
`scratch/planner/d3s_2x3_shot_rule_20261003.{py,json}`, which Part B must reproduce in a gate).  Owner's
instruction (2026-10-03): "Send problem 1 and 2 to planner now" — the two problems of the Stage A run of
prompts/26 (`reports/Q0P_2x3.md`).

## Goal

Two rulings are to be implemented and one physics question settled offline, before any emulator or device
shot is spent on Quantinuum:

1. **Problem 1 (shot rule).**  Rule D3' (every sector state at $\lambda^* = 6.2958$ expected clean counts) is
   unreachable at 2x3 ($N_4 \sim 10^{36}$, `validation/Q0P_2x3.json data.stage_A.predict.campaign`).  The
   planner's ruling is rule **D3'-R**: the clean-shot budget is derived from the preregistered targets the shots
   exist for — S1/H1 recall of the exact $10^{-3}$ support $S_{999}$ and the certified energy — not from every
   state of the sector.  Precisely: (a) every state of the $10^{-2}$ support $S_{99}$ (31 states in $B=0$, 42 in
   $B=1$) gets $\ge \lambda^*$ expected clean counts (3 hits with 95 % probability, manual eq. 5 applied to the
   state's actual circuit probabilities), the allocation over the 44 circuits being the linear programme of
   minimum total shots with every circuit $\ge 267$; (b) then the $k = 4$ circuits are topped up (multiples of
   100) until the probability that the clean shots alone recall $\ge 0.9$ of $S_{999}$ is $\ge 0.95$
   (Poisson-binomial, exact).  Clean yield per shot $y = 0.82 \times 0.7 \times f$ as in D3' (constants unchanged).
   Planner prototype at $f = 0.10$: $B=0$ 34,909 shots / 173,614 HQC, $B=1$ 49,203 / 244,553; total 84,112 shots,
   418,166 HQC (table in the report).  Part B turns this into gate **Q0P_2x3_plan** and re-renders the
   preregistration block.
2. **Problem 2 (estimator).**  The reference-string estimator (`skqd.skqd.pooled_reference_string_test`) gave
   $f = 0.2502$ [0.1927, 0.3195] on the A6 Aer dry run against a fault-free fraction of 0.1722 (Aer channel)
   / 0.1502 (gate-only model).  The planner's reading: this is the near-clean term of M4.4/C3' — shots carrying
   $Z$-type errors at positions where the state is close to a computational basis state still land on the
   reference string — and not a bug; but that reading must be *proved* by a trajectory decomposition
   (Part A, gate **CF_traj**), and one Aer-path bug candidate (merged two-qubit gates lowering the number of
   error events) must be excluded by a counting control.  Ruling on the statistic (Part B): the quantity the
   budget criterion $f \ge 0.1$ refers to is the **fault-free fraction** $f_0$ (the manual's definition); the
   quantity that sizes the campaign is the per-state effective sampling rate on the target support, of which
   $f_0$ is a floor and the reference-hit fraction $f_{\rm hit}$ an upper end; the device-side statistic for
   both the GO rules and the sizing becomes the **tail-class fraction** $f_T$ — the same excess-count
   construction on the class $T_c$ of states with ideal probability $\ge 10^{-3}$ other than the circuit's
   reference — with the reference count kept as the C3' bit-order test and $\rho_{\rm hit} = f_{\rm hit}/f_T$
   reported as the near-clean index.  The Stage E and Stage P plans are rebalanced to $k = 1$ / $k = 4$ shots so
   that $f_T$ has the precision the GO rule needs.  The 2x2 records are not rewritten; an information block
   states which recorded $f$ values are $f_{\rm hit}$.

Definitions used throughout (the planner's labels, not manual terms): $f_0$ = fraction of shots with no error
event anywhere (fault-free); $f_{\rm hit}$ = (reference-string count minus garbage expectation) / ($N\,p_{\rm ref}$),
the recorded estimator; $f_T$ = the same construction on the tail class $T_c$; $f_{\rm eff}(s)$ = (expected count
of state $s$ minus garbage) / ($N\,p_c(s)$), the per-state effective rate; near-clean = a shot with $\ge 1$ error
whose measured string is nevertheless a correct-looking sample.

## Inputs (read these first; use graphify before grepping)

- `graphify-out/graph.json` exists: orient with `graphify query "<question>"`, `graphify explain "<symbol>"`,
  `graphify path "A" "B"`, `graphify affected "<symbol>"` before grepping or reading whole files; after changing
  code run `graphify update .` (seconds, no API cost).  Start with `graphify explain "pooled_reference_string_test"`,
  `graphify explain "clean_fraction_mixture"`, `graphify explain "n4_of_sector"`, `graphify explain "analyse_dryrun"`
  (`scripts/gate_Q0P_2x3.py`), `graphify explain "statevector_aer"` (`src/skqd/circuits_qiskit.py`),
  `graphify explain "pytket_to_ir"`, `graphify affected "d3_plan"`, `graphify explain "support_metrics"`.
- The ruling: `reports/2x3_shot_rule_estimator_ruling_20261003.md`; the prototype
  `scratch/planner/d3s_2x3_shot_rule_20261003.py` and its JSON (Part B2 must reproduce its numbers).
- Problem statements: `reports/Q0P_2x3.md`, `validation/Q0P_2x3.json` (`data.stage_A.predict.dryrun`,
  `.campaign`, `.campaign_d3type`), `data/quantinuum/q0p_stages/predict.json`, `data/quantinuum/a6_phase_error_check.json`,
  `data/hardware/Q0P_2x3_dryrun/` and `data/hardware/Q0P_2x3_dryrun_pilots/`.
- Frozen circuits and their sector distributions: `data/quantinuum/circuits_2x3/` (manifests: `reference`,
  `reference_int`, `p_reference`, `counts`, `hqc_per_shot`), `data/quantinuum/q0p_stages/verify.json
  per_circuit.<id>.p_sector` (the Aer statevector of the frozen native circuit, normalised to the sector).
- Noise channel of A6: `scripts/quantinuum_submit.py A6_NOISE` and the dry-run sampler path in the same file
  (the exact `AerSimulator` construction, transpile call and options it used — record them).
- Exact ground states: `skqd.exact.Model(3).reference(4.0, twoB, k=4)` (`ground`, `indices`, `support99`,
  `support999`); 2x2: `Model(2)`.
- Shot-rule code: `scripts/h0_support_plan.py` (`clean_rate`, `lambda_of_plan`, `n4_of_sector`, floor 267,
  round 100, margin 0.7), `scripts/gate_Q0P_2x3.py` (`d3_plan`, `d3type_plan`, `cost_of_plan`, `GO_RULE`,
  `stage_predict`, `stage_prereg_md`), `scripts/s2d_recall_at_predicted_f.py` (the emulated recall machinery).
- Estimators: `src/skqd/skqd.py` (`reference_string_test`, `pooled_reference_string_test`,
  `clean_fraction_mixture`, `near_clean_yield`, `poisson_lambda_star`, `support_metrics`), `tests/test_clean_yield.py`.
- 2x2 records to be *cited, never edited*: `validation/H0_kpilot.json`, `validation/H0_ddtest.json`,
  `validation/H0_2x2.json` (`data.clean_fraction`, `data.adopted_configuration`, `data.support`), `validation/H0_model.json`.
- 2x2 idle model for the optional arm A4: `scripts/h0_idle_model.py` (`schedule`, `budgets`, `f_on_record`),
  the H0_2x2 patch record and circuits under `data/hardware/H0_2x2_prep/`.
- Device table and billing: `data/quantinuum/devices_20261002.json` (`billing`, `rows.2x3|quantinuum_h2_2`).
- Package pins (coding env: qiskit 2.5.2, qiskit-aer 0.17.2, qiskit-ibm-runtime 0.49.0, numpy 2.5.2, scipy
  1.18.0, Python 3.12.14) must not change; pytket lives in `~/.local/share/su2qc-quantinuum/venv` as in prompts/26.

## Conventions that must not change (CLAUDE.md rule 2)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py` (qubit $k$ = bit $k$, little-endian), the signed
term family, the 44 frozen native circuits (byte-identical), $\lambda^* = 6.2958$, the margin 0.7, the floor 267,
the rounding 100, the readout factor 0.82 (kept as recorded even though the Quantinuum $f_0$ already contains the
readout survival — it is a conservative double count, see the report section 2.4; do not remove it here), every
criterion constant of every existing gate, the signed bars 0.1 (mean) and 0.05 (worst).  The A6 noise channel
(`A6_NOISE`) is frozen for Part A: the same numbers, the same Aer channel definitions.

## Part A — the decisive trajectory test (gate CF_traj; laptop; no HQC)

Purpose: decide whether the 64 reference hits of A6 against 44.06 expected from fault-free shots (Poisson
$P = 0.0028$, `predict.json dryrun`) are the near-clean term (physics) or an Aer-path defect (bug).  The test
decomposes the noisy output by **Pauli-error trajectories**: the fault-free shots are known analytically (their
fraction $f_0' = \prod (1 - \tfrac{15}{16} p_2)^{n_{ZZ}} (1 - \tfrac{3}{4} p_1)^{n_{PhX}} \times$ readout survival
$= 0.17209$ for `B0_ref25_k1`, $0.17236$ for `B1_ref57_k1`, `predict.json dryrun.predictions.*.aer_channel_no_error_probability`),
so only *faulty* trajectories are simulated, and for each the **exact** output distribution is computed (one
statevector per trajectory), which gives $p_\tau(s)$ for every sector state at once instead of one sampled bit
string.  That is why a few hundred trajectories give the $\pm 0.02$ precision the owner asked for.

A0. Orientation and timing pilot (20 min).  `graphify` as above.  Measure the wall time of one
    `circuits_qiskit.statevector_aer` evaluation of `B0_ref25_k1` (native IR from
    `quantinuum_native.from_json` + `pytket_to_ir`) on 1 thread and with 6 worker processes in parallel
    (planner's reading of `verify.json`: 903 s for 176 statevectors on 6 workers, about 31 s per statevector
    per core; confirm).  Set the chunk size so that one background chunk is $\le 25$ min.  Record in the JSON.

A1. `scripts/cf_trajectories.py` (3 h).  Inputs: `--id` (frozen circuit id), `--K` (faulty trajectories),
    `--seed`, `--chunk`, `--workers`.  Channel = `A6_NOISE` read from `quantinuum_submit`, reproduced
    *exactly as Aer defines it*: `depolarizing_error(p, 2)` = identity with probability $1 - \tfrac{15}{16}p$,
    each of the 15 non-identity two-qubit Paulis with $p/16$; `depolarizing_error(p, 1)` = identity with
    $1 - \tfrac{3}{4}p$, each of $X, Y, Z$ with $p/4$; applied **after** the gate it is attached to (confirm Aer's
    convention from the qiskit-aer source or documentation and cite the sentence in the JSON); `Rz` noiseless;
    readout flips `readout_p1_given_0` / `readout_p0_given_1` applied **exactly** to the final distribution by
    the per-qubit convolution on the $2^{20}$ vector (20 passes).  Sampling: for every ZZPhase draw
    Bernoulli($\tfrac{15}{16}p_2$), for every PhasedX (one physical 1q rotation each; the IR carries it as
    `rz, rx, rz` — the error attaches to the `rx`) Bernoulli($\tfrac{3}{4}p_1$); reject the all-identity draw
    (probability $f_0'$; no simulation needed); insert the drawn Paulis as `x`/`y`/`z` IR gates after the gate;
    evaluate the statevector; record per trajectory: the event list (position, gate type, Pauli), $n_{2q}$,
    $n_{1q}$, whether all Paulis are $Z$-type (`Z` on 1q; `ZI, IZ, ZZ` on 2q), the sector mass, $p_\tau(\mathrm{ref})$,
    $p_\tau(s)$ for every $s \in S_{999}$ of the sector (positions as in `Model(3).reference`), the total
    variation distance of the sector-normalised $p_\tau$ from the ideal $p_c$, and the tail-class probability
    $\sum_{s \in T_c} p_\tau(s)$ with $T_c = \{s : p_c(s) \ge 10^{-3},\ s \ne \mathrm{ref}\}$.  Output one JSON per
    chunk under `data/cf_trajectories/<id>/chunk<n>.json` (raw data, never overwritten) and a combined file.

A2. Arms and sizes (background chunks, each $\le 25$ min; run them one after another, never in parallel with
    each other beyond the 6 workers):
    - `B0_ref25_k1`: $K = 720$ (three chunks of 240, seeds 101-103);
    - `B1_ref57_k1`: $K = 240$ (seed 201);
    - `B0_ref25_k4`: $K = 240$ (seed 301) — the production circuit family, $p_{\rm ref} = 0.236$.
    Expected precision (planner arithmetic): with the per-trajectory standard deviation of $p_\tau(\mathrm{ref})$
    at most 0.3, $K = 720$ gives a standard error $\le 0.011$ on $\bar h_{\rm ref}$ and $\le 0.011$ on $f_{\rm hit}$,
    i.e. about $\pm 0.02$ at 95 %.  If A0's timing makes this exceed 3 h of wall time, reduce $K$ for
    `B0_ref25_k1` to 480 and say so.

A3. Analysis (`scripts/gate_CF_traj.py` → `validation/CF_traj.json`, `reports/CF_traj.md`; via
    `skqd.report.GateResult`, no typed numbers).  For each arm, with $f_0'$ from `predict.json` (recomputed from
    the counts and the channel and checked to $10^{-12}$):
    - $\bar h_{\rm ref} = \langle p_\tau(\mathrm{ref})\rangle_\tau \pm$ s.e.; the trajectory prediction of the
      reference-hit fraction $f_{\rm hit}^{\rm traj} = f_0' + (1 - f_0')\,\bar h_{\rm ref}/p_{\rm ref}$ and
      $\rho_{\rm ref} = f_{\rm hit}^{\rm traj}/f_0'$;
    - the predicted A6 hit count for the two $k = 1$ circuits, $140\,[f_0' p_{\rm ref} + (1 - f_0')\bar h_{\rm ref}]$
      each, summed, with its uncertainty (s.e. propagated) against the observed 64; two-sided Poisson $P$;
    - the $Z$-only stratum: $\langle p_\tau(\mathrm{ref})\rangle$ over trajectories whose Paulis are all $Z$-type,
      and the prediction for the phase-only check of `data/quantinuum/a6_phase_error_check.json`
      ($40\,[0.17469 \times 0.91502 + 0.82531\,\bar h_Z]$) against its 11 hits;
    - the benign fraction $b$ = fraction of faulty trajectories with TV distance $< 10^{-3}$ from the ideal;
    - $f_T^{\rm traj} = f_0' + (1 - f_0')\,\langle \sum_{T_c} p_\tau \rangle / \sum_{T_c} p_c$ and
      $\rho_T = f_T^{\rm traj}/f_0'$;
    - per state $s \in S_{999}$: $f_{\rm eff}(s)/f_0'$, its minimum, median and maximum over $S_{99}$ and over
      $S_{999}$, and the number of $S_{99}$ states with $f_{\rm eff}(s) < 0.7\,f_T^{\rm traj}$ (the margin check
      of rule D3'-R); the Hamming-distance histogram (in the codeword space) of where the faulty trajectories'
      weight goes, for the report.
    - A6-path audit, written into the JSON: the `AerSimulator` method and options used by the dry-run sampler,
      `noise_model.noise_instructions`, `noise_model.basis_gates`, and the operation counts of the circuit object
      actually handed to `run` (must contain 2158 `rzz` and one noisy 1q rotation per PhasedX; any merging of
      consecutive `rzz` on the same pair by a transpile step would lower the number of error events and is a
      bug candidate).

A4. Counting control on the Aer path (25 min background, independent of the trajectory code).  Re-run the A6
    sampler on `B0_ref25_k1` with the **same event probabilities but bit-flipping errors only**: 2q channel
    $\{XX : \tfrac{15}{16}p_2\}$, 1q channel $\{X : \tfrac{3}{4}p_1\}$ (`pauli_error`), readout unchanged, 280
    shots, seed 23.  Prediction from a 120-trajectory arm of A1 with the same channel (`--channel xx`):
    $280\,[f_0' p_{\rm ref} + (1 - f_0')\bar h_{\rm ref}^{XX}]$ — the planner expects $\bar h^{XX}_{\rm ref}$ near
    zero (a bit flip early in the circuit leaves the reference and returns only through the dynamics), so about
    $44 \pm 6.6$ hits.  Pass: observed within the Poisson 95 % band of the prediction.  If the control gives
    about 64 again, the Aer path applies fewer error events than the model says: **STOP** (bug), write
    `validation/BLOCKED.md`.

A5. Optional 2x2 information arm (<= 15 min; 12 qubits).  The H0_2x2 adopted $k = 1$ circuit `B0_ref06_k1`
    (the T3 circuit under `data/hardware/H0_2x2_prep/`) with: depolarizing `cz` errors at the patch's recorded
    per-edge $\epsilon_{cz}$, 1q errors at the recorded `sx` errors, readout at the recorded values, and the idle
    dephasing of `h0_idle_model.budgets` as a Pauli-twirling approximation ($Z$ with probability
    $\tfrac12 (1 - e^{-t/T_2^*})$ per scheduled idle window at the pilot's measured $T_2^*$ per qubit — state the
    exact window list used).  $K = 2000$ trajectories.  Report $\rho_{\rm ref}$ and $\rho_T$ at 2x2 under this
    model as **information** for the 2x2 records (section B4).  If the H0_2x2 preparation files do not expose
    the scheduled windows in a usable form within 30 min of work, record "not run" and move on.

Pass criteria of **CF_traj** (status PASS iff C1-C6; the physics verdict is a result field):
- C1 A0 timing recorded; the planned $K$ per arm reached (or the documented reduction applied); every chunk
  file present with its seed and git commit;
- C2 the trajectory prediction of the A6 reference hits (both circuits, 280 shots) is consistent with the
  observed 64 at two-sided Poisson $P \ge 0.05$ **and** the counting control A4 passes.  If C2 fails with the
  prediction *below* 64 by more than 3 standard errors, the status is FAIL and the executor STOPs (bug
  candidate); if the prediction is *above* 64, record it and continue (the near-clean term would be larger in
  the trajectory model than in Aer's sampling — a model question, not a bug);
- C3 the $Z$-only stratum reproduces the phase-only check (11 hits in 40) within its Poisson 95 % band;
- C4 $\rho_{\rm ref}$, $\rho_T$, $b$, $\min_{S_{99}} f_{\rm eff}/f_0'$, $\min_{S_{999}} f_{\rm eff}/f_0'$ and the
  number of $S_{99}$ states with $f_{\rm eff} < 0.7 f_T$ are reported with intervals for all three arms;
- C5 the A6-path audit shows 2158 `rzz` and 3053 noisy 1q rotations in the executed circuit and the four noise
  instructions attached (`rzz`, `rx`/`ry` as the IR emits them, `measure`);
- C6 `pytest -q tests` and `python scripts/check_package.py` pass; the pins are unchanged.

`what_pass_means`: "the excess of reference-string hits over the fault-free expectation in the A6 Aer run is
reproduced by an independent Pauli-trajectory decomposition of the same channel on the same circuit, and a
bit-flip-only control gives the fault-free count; the reference-string estimator therefore measures the
clean-plus-near-clean fraction, not the fault-free fraction.  PASS says nothing about any device."

STOP (Part A): C2 fails on the low side; A4 reproduces about 64; any change to `A6_NOISE`; any need to touch
`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py`; two failed attempts at any criterion →
`validation/BLOCKED.md`, the planner returns.  **Also STOP and return to the planner (without BLOCKED) if
$\rho_T > 1.5$ on any arm**: then $f_T$ sits too far above $f_0$ for the 0.7 margin to cover and the GO rule's
bar must be re-derived before Part B3 fixes it in the preregistration.

## Part B — implement the rulings (after CF_traj PASS; laptop; no HQC)

B1. The tail-class statistic (3 h).  In `src/skqd/skqd.py`:
    - `tail_class(p_sector, reference_pos, p_min=1e-3) -> np.ndarray` of sector positions
      ($p \ge p_{\min}$, reference excluded);
    - `tail_class_test(n_tail, n_shots, p_tail, n_tail_states, acceptance, dim, readout_factor, conf)` and
      `pooled_tail_class_test(rows, ...)`: the construction of `reference_string_test` with the garbage
      expectation $N a |T_c| / \mathrm{dim}$ and the clean denominator $N p_{T_c}$ with $p_{T_c} = \sum_{T_c} p_c$;
      Garwood intervals at `conf`; keys `f_tail`, `f_tail_68`/`_95`, plus `near_clean_index` when a reference
      row is supplied ($\rho_{\rm hit} = f_{\rm hit}/f_T$ with the log-ratio interval of `H0_ddtest`'s rule);
    - docstrings stating what each statistic measures ($f_{\rm hit} \ge f_T \ge f_0$ in expectation under the
      trajectory model of CF_traj, with the measured $\rho$ values cited from `validation/CF_traj.json`).
    Tests (`tests/test_clean_yield.py` additions): synthetic samples $w\,p_c + (1 - w)/\mathrm{dim}$ at
    $w \in \{0.05, 0.1, 0.5\}$ recover $f_T$ within the 95 % interval in $\ge 95$ of 100 seeds; on a mixture
    built from CF_traj's recorded trajectories (fault-free $\times f_0'$ + faulty $\times (1 - f_0')$) the
    estimator's expectation equals $f_T^{\rm traj}$ to $10^{-9}$; a flat histogram gives $f_T = 0$.
    `analyse_dryrun` in `gate_Q0P_2x3.py`: fix the shadowed variable (`a` is overwritten by the timing-pilot
    loop, so `dryrun.garbage_acceptance` in `predict.json` holds a pilot record instead of the acceptance —
    the computed rows are right, the JSON field is wrong); report $f_T$ beside $f_{\rm hit}$ for the A6 run
    (information: at 280 shots the tail count is about 4, so the interval is wide).

B2. Rule D3'-R (4 h).  In `scripts/h0_support_plan.py`: `d3r_plan(p_by_circuit, f_by_circuit, ids, k4_ids,
    S99, S999, floor=267, round_to=100, margin=0.7, readout_factor=0.82, recall_target=0.9, prob_target=0.95,
    lambda_star=poisson_lambda_star())`: (i) `scipy.optimize.linprog(method="highs")`: minimise
    $\sum_c N_c$ subject to $\sum_c N_c\, y_c\, p_c(s) \ge \lambda^*$ for all $s \in S_{99}$, $N_c \ge$ floor, with
    $y_c = 0.82 \times 0.7 \times f_c$; circuits at the floor stay at exactly 267, the others are rounded up to
    100; (ii) `recall_tail_prob` (exact Poisson-binomial DP over $S_{999}$) and the smallest extra (multiple of
    100) added to every $k = 4$ circuit until $P(\text{recall} \ge 0.9) \ge 0.95$; returns the plan, $\lambda_{\min}$
    on $S_{99}$ and $S_{999}$, the recall floor, $P(\text{recall} \ge 0.9)$, $P(\text{all } S_{99} \text{ seen})$.
    Unit test: on the frozen inputs (verify.json `p_sector`, `Model(3)`) at $f = 0.10$ the plan reproduces the
    planner prototype to the shot: $B=0$ 34,909 shots (extra 1100 on the $k = 4$ circuits; `B0_ref25_k4` 17,600,
    `B0_ref25_k3` 1,000), $B=1$ 49,203 shots (extra 0; `B1_ref27_k4` 14,800, `B1_ref29_k4` 11,400,
    `B1_ref57_k4` 20,600); the prototype's LP used `ceil100(267) = 300` for the floor circuits — the gate uses
    267 exactly, so compare the scaled circuits to the shot and the totals after replacing 300 by 267
    (prototype totals 34,909 / 49,203 already use 267 in the D3R block; see the JSON).  Also the 2x2 check:
    `Model(2)` sectors, the H0_2x2 circuit distributions (`data/hardware/H0_2x2_prep`), $f = 0.1129$: the
    recorded plan (`N_4$ 13,100 / 31,400`) satisfies both conditions of D3'-R (planner reading of
    `validation/H0_2x2.json data.support`: $\lambda_{\min}$ over $S_{999}$ at the margin $f$ is 30.15 / 32.76
    against $\lambda^* = 6.30$; $|S_{999}|$ = 16 of 38 and 13 of 20) — a test that `d3r_plan` at 2x2 returns a plan
    with sector totals $\le$ the recorded ones.

B3. Gate **Q0P_2x3_plan** (`scripts/gate_Q0P_2x3.py --stage plan28`; 4 h) → `validation/Q0P_2x3_plan.json`,
    `reports/Q0P_2x3_plan.md`, and `reports/Q0P_2x3_prereg.md` re-rendered as **preregistration block v2**
    (first line: "v2 replaces v1 of 2026-10-03 03:22 UTC before any Stage E/P shot; v1 is in git history at
    a2e6060"; `validation/Q0P_2x3.json` is not rewritten).  Contents:
    - the target sets: $|S_{99}|$, $|S_{999}|$ per sector, the reachability table (min over $S_{999}$ of
      $\sum_c p_c(s)$, of $\sum_{k=4} p_c(s)$, of $\max_c p_c(s)$ — planner prototype: $B=0$ 5.89e-3 / 2.41e-3 /
      1.64e-3; $B=1$ 1.10e-3 / 6.20e-4 / 6.19e-4), and the 32 / 11 states outside $S_{999}$ that D3' could not
      reach (their largest ground-state weight);
    - the D3'-R plan at $f \in \{0.05, 0.10, 0.15\}$: shots per circuit, per sector, jobs, HQC (formula of
      `data/quantinuum/devices_20261002.json billing`, 5 HQC per job, $\le 10{,}000$ shots per job), USD at the
      ESTIMATE rate, machine hours at the mid scenario, $\lambda_{\min}$ on $S_{99}$ / $S_{999}$, recall floor,
      $P(\text{recall} \ge 0.9)$; plus the two calibration circuits at 1,000 shots each;
    - comparison columns (information): D3'-S (λ* on every $S_{999}$ state, LP), the D3-type union plan of
      the Stage A record, with the same guarantee numbers;
    - the emulated check of the plan (the machinery of `scripts/s2d_recall_at_predicted_f.py`, 3 seeds, clean
      fraction $0.7 f$ at $f = 0.10$, garbage at gate E2's acceptance, per-circuit shots of the plan): recall of
      $S_{999}$, $|B|$, $E_R - E_0$, $r_H$, Weinstein interval and width, for both sectors;
    - the Stage E plan v2: `B0_ref25_k1` 600, `B1_ref57_k1` 600, `B0_ref25_k4` 400, `B1_ref57_k4` 400 on
      `H2-2E` (planner arithmetic: 2,000 shots, about 9,950 eHQC; expected tail hits at $f_0 = 0.10$: 69, at
      0.15: 104, from the tail weights 0.0823 / 0.0852 / 0.7189 / 0.7555 of the prototype); `max_cost` = formula
      + 10 %;
    - the Stage P pilot v2: the same four circuits at 500 shots each on `H2-2` (about 9,950 HQC);
    - the GO rule v2 for both stages: statistic = $f_T$ pooled over the stage's circuits
      (`pooled_tail_class_test`, Garwood 95 %); **GO iff $f_{T,\rm lo95} \ge 0.05$ and $f_T \ge 0.10$; NO-GO iff
      $f_{T,\rm hi95} < 0.10$; AMBIGUOUS otherwise**, with the top-up rule of `H0_kpilot` (Poisson scaling of the
      measured counts, one top-up at most, equal size); C3' kept: every $k = 1$ circuit's reference count
      $\ge 3\sigma$ above garbage (bit-order test); $\rho_{\rm hit}$ with interval reported as the near-clean index
      and compared with CF_traj's Aer value (information);
    - the campaign sizing rule: $f_{\rm size} = f_T$ (point estimate) of Stage P; D3'-R at $0.7 f_{\rm size}$;
      mid-campaign check preregistered: after the first half of each sector's $k = 4$ shots, the pooled
      observed/expected ratio on $S_{99}$ (expected $= \lambda_s/2$ at the plan's $y$) is computed; if it is
      $< 0.7$ the second half is re-sized by that ratio once (HQC cap: the owner's);
    - the HQC/USD/machine-hour table and the floor-circuit share (33 of 44 circuits at 267 shots).
    Criteria P1-P6: P1 `d3r_plan` reproduces the prototype at $f = 0.10$ to the shot (B2's test) and the 2x2
    consistency test passes; P2 every $S_{99}$ state has $\lambda_s \ge \lambda^*$ and $P(\text{recall} \ge 0.9)
    \ge 0.95$ in both sectors at all three $f$; P3 the emulated check gives recall $\ge 0.9$ in every seed and
    $E_0$ inside the Weinstein interval (width reported against H1's 0.1 as information); P4 HQC totals equal
    the formula applied job by job to $10^{-12}$ relative; P5 the prereg v2 renders from the JSON only (no typed
    number; a test greps the markdown numbers against the JSON); P6 tests and `check_package.py` pass.

B4. The 2x2 information block (2 h).  `scripts/cf_estimator_information.py` →
    `validation/CF_estimator_2x2_info.json` + `reports/CF_estimator_2x2_information_20261003.md`: a table of
    every recorded clean-fraction value with its statistic name, read from the records (never edited):
    `H0_kpilot data.decision.f_pool` (0.0413 [0.0361, 0.0470]), `H0_ddtest data.decision.cells.T0/T1/T2/T3.f_pool`,
    `H0_2x2 data.clean_fraction.pooled` and `data.adopted_configuration.f_pool` (0.1129 [0.1058, 0.1203]),
    `H0_model` C1-C3 — each labelled "$f_{\rm hit}$ (reference-hit fraction): an upper end of the fault-free
    fraction $f_0$; the near-clean factor on ibm_kingston is not measured (CF_traj's Aer value and, if A5 ran,
    the 2x2 PTA value are cited as the only model estimates)"; the statements that **do not change**: every
    H0_* criterion (same statistic on both sides, or $f$-independent), the H0_kpilot NO-GO (strengthened:
    $f_0 \le f_{\rm hit} = 0.041$), the H0_ddtest adoption of T3 ($R$ is a ratio of hit statistics; information
    that DD changes the error composition so $R$ is not exactly the ratio of $f_0$), the H0_2x2 energies
    (sector saturation; $f$-independent) and recall (1.0 from the observed per-state counts, min 59 / 80 on
    $S_{999}$); the statement that **is qualified**: "signed bar GO on $f_{\rm pool} \ge 0.1$" in `H0_ddtest`
    and `H0_2x2` is a GO on $f_{\rm hit}$, and the bar on $f_0$ is not established at 2x2.  Add the rows to
    `validation/gates.md` (CF_traj, Q0P_2x3_plan, the information file as a note under H0_2x2) and one
    paragraph to `reports/PROJECT_STATUS.md`.

B5. Bookkeeping: `graphify update .`; LOG rows (one per gate); commit `git commit <paths>` (retry on
    `.git/index.lock`); **no push**.

STOP (Part B): the LP is infeasible at any $f$ (a state of $S_{99}$ with zero probability in every circuit —
report it, do not drop it); any criterion constant would have to change; any edit to an existing
`validation/*.json` or frozen circuit; two failed attempts at any criterion → `validation/BLOCKED.md`.

## Outputs

- Part A: `scripts/cf_trajectories.py`, `scripts/gate_CF_traj.py`, `data/cf_trajectories/<id>/chunk*.json`,
  `data/cf_trajectories/control_xx/` (A4 counts in the `write_counts_for_job` raw format),
  `validation/CF_traj.json`, `reports/CF_traj.md`; tests `tests/test_cf_trajectories.py`.
- Part B: `src/skqd/skqd.py` (tail-class statistic), `scripts/h0_support_plan.py` (`d3r_plan`),
  `scripts/gate_Q0P_2x3.py` (`--stage plan28`, the `analyse_dryrun` fix), `validation/Q0P_2x3_plan.json`,
  `reports/Q0P_2x3_plan.md`, `reports/Q0P_2x3_prereg.md` (v2), `scripts/cf_estimator_information.py`,
  `validation/CF_estimator_2x2_info.json`, `reports/CF_estimator_2x2_information_20261003.md`, tests,
  `validation/gates.md`, `reports/PROJECT_STATUS.md`, `prompts/LOG.md`; git commit, no push.

## Escalation

Retry rule: a failing criterion may be retried once with the same constants after the cause is written into
the report; a second failure is BLOCKED.  The planner returns on: C2 low-side failure, the A4 control at about
64, $\rho_T > 1.5$, an infeasible LP, or any result that would require a criterion constant, the readout factor,
the margin, $\lambda^*$ or a signed bar to change.

## Do-not-touch list (binding)

`src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py`, `device_req.py`; every existing
`validation/*.json`; every frozen circuit under `data/hardware/` and `data/quantinuum/circuits_2x3/`;
`A6_NOISE`; every criterion constant of every existing gate; `ci/`; `prompts/00`-`27`; the planner's row in
`prompts/LOG.md` (append only).

## What the owner must do (the executor cannot)

1. Confirm rule D3'-R as the 2x3 shot rule (amendment 01 item 5) — or choose D3'-S (every $S_{999}$ state at
   $\lambda^*$: 2.78e6 HQC at $f = 0.10$, planner prototype) if the all-states guarantee is wanted at that price.
2. Confirm the GO-rule statistic $f_T$ and the rebalanced Stage E / P plans before any emulator or device job.
3. Decide whether the 2x2 "signed bar GO" statements are to be cited with the qualification of B4 in any
   external text.
4. Access and budgets as in prompts/26 (Nexus login, eHQC for Stage E, HQC for Stage P) — unchanged.

## LOG rows (append to `prompts/LOG.md`)

| date | prompts/28_2x3_shot_rule_and_clean_fraction_estimator.md Part A / Part B | CF_traj / Q0P_2x3_plan | executor-opus | PASS/FAIL with the numbers from the JSON ($\rho_{\rm ref}$, $\rho_T$, $b$, the A6 hit prediction vs 64, the control's hits, $\min f_{\rm eff}/f_T$ on $S_{99}$; the D3'-R shots and HQC at the three $f$, the emulated recall and width, the Stage E/P v2 plans) | commit | open items |

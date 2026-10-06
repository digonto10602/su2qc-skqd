# 33 — The 2x3 four-class simulation campaign on Perlmutter (ideal / IBM noise / Quantinuum-based ideal / Quantinuum-based with errors and optimisations)

executor: executor-opus   effort: high
time budget: laptop build + freeze about 1.5 executor days (0 QPU s, 0 HQC); Perlmutter about 20 GPU-hours of
1-GPU jobs over 2-3 UTC days once the owner has installed the concurrency change; analysis + report 1 day
machine: laptop (build, freeze, tests, assemble, report) + Perlmutter CI (every sampling job)
date: 2026-10-06   planner: Fable 5.1 (high)   prompt number: 33

Trigger: the owner's request of 2026-10-06 (verbatim in `reports/2x3_four_class_campaign_plan_20261006.md`,
section 1): four classes of 2x3 runs "on qiskit" — (1) no noise, no optimisation; (2) IBM noise; (3) Quantinuum-
based simulators, no error, no optimisation; (4) Quantinuum-based with varied errors and optimisations — every
earlier 2x3 simulation redone and the difference computed, and everything laid out so the jobs run on Perlmutter
**simultaneously**.  Reports read: `reports/PACKAGE_FULL_REPORT_20261006.md`, `prompts/18`, `prompts/26`,
`prompts/27` (stage S3H), `prompts/28`-`31`, `validation/{S1,S3,S3_smoke,L4,L4_p2_*,Q0P_2x3,Q0P_2x3_plan,
CV_2x3_plan,CF_traj,K0_2x3_2x4,K1_2x3_fpilot,S2_2x4_gpu}.json`.  Planner arithmetic (sizing, matched-$f$ rates):
`scratch/planner/campaign33_sizing_20261006.{py,json}`.

**Rule 1 is binding.** Every number in a report comes from `validation/*.json` or `data/*.json`; the campaign
report is generated, never typed.  **Rule 2:** no convention changes.  **0 QPU s, 0 HQC** by this prompt.
**No push and no CI request by this prompt**: the executor commits locally with `git commit <paths>`; the owner
decides the single push that makes the poller change and the request files visible to Perlmutter (section 7).

**Code orientation (mandatory):** `graphify-out/graph.json` exists.  Use `graphify query "<question>"`,
`graphify explain "<symbol>"`, `graphify path "A" "B"` and `graphify affected "<symbol>"` BEFORE grepping or
reading files; grep only to edit specific lines.  Run `graphify update .` after every code change.  Start
with: `graphify explain "sample_many"`, `graphify explain "pytket_to_ir"`, `graphify explain "schedule_circuit"`,
`graphify explain "chunk_2x3"`, `graphify explain "backend_from_record"`, `graphify affected "run_gate.py"`.

---

## Goal

Produce, with 0 QPU s, the first complete simulator picture of the signed 2x3 family: the ideal reference
(class 1), what IBM Heron noise does to the routed circuits (class 2, the model behind the measured K1 NO-GO),
what the Quantinuum-native circuits do with no error (class 3), and what they do under the Quantinuum error
classes and under exact circuit optimisations (class 4) — each with the project's full statistics ($f_{\rm hit}$,
$\hat f_{\rm ideal}$, $f_0$, accepted fraction, decoded support, recall of $S_{99}$ / $S_{999}$, $E_R$ with the
Kato-Temple / Weinstein certificates, the CV0-CV5 convergence criteria) — and a generated comparison of every
earlier 2x3 simulation (S1, S3, S3_smoke, the A6 dry run, CF_traj, CV_2x3_plan / Q0P_2x3_plan P3, the K0 / K1
predictions) with its redo, difference and uncertainty.  All sampling runs on Perlmutter as independent 1-GPU
jobs that can be submitted at the same time, after the owner installs the concurrency change of section 7.

What this is NOT: no device measurement, no change to any signed circuit, bar, criterion constant or convention;
the Quantinuum vendor emulator (H2-2E on Nexus) is NOT run (no account); the class-3/4 "Quantinuum-based" engine
is Qiskit Aer on the Quantinuum-native circuits (the owner said "on qiskit"), cross-checked by the one Quantinuum
emulator that runs locally without an account (pytket-pecos `H2-1LE`, noiseless) and, optionally, Selene.

---

## 1. The campaign matrix (what runs)

### 1.1 Circuit families (all 20 logical qubits; the IBM-routed ones 21 physical)

| id | family | source | gates | exactness check |
|---|---|---|---|---|
| IR-L0 | signed family, IR as built, **no transpilation at all** (`ir_to_qiskit` keeps `unitary`, `cx`, `ry`, `p`, `cp`, `x`; Aer executes them natively) | `gate_S2D.circuit_set(3)` via `h0_build_circuits.repeated_coarse_step`, 44 circuits (32 at $B=0$, 12 at $B=1$) | per manifest: cx 2588, unitary 144, ry 2164, p 29, cp 2, x 3 | vs `skqd.krylov.coarse_states` |
| NAT-O0 | the frozen Quantinuum-native family (pytket level 0 = **no optimisation**), converted by `skqd.quantinuum_native.pytket_to_ir` (PhasedX -> rz, rx, rz; ZZPhase -> rzz) | `data/quantinuum/circuits_2x3/*.json` (gate Q0P_2x3, sha256 in `index.json`) | ZZPhase 2158, PhasedX 2989-3091, Rz 4255 | Q1 bar re-verified on the converted circuit |
| NAT-O1..O4, O6 | optimisation variants of NAT-O0 (section 1.4) | built here | measured | bar per variant |
| IR-L3-RZZ | the circuits gate S3 sampled: `transpile(ir, basis=[rz,rx,ry,rzz], coupling_map=None, optimization_level=3, seed_transpiler=7)` | `scripts/s3_device_model.py` (the S3 path) | rzz 2162 (S3 JSON) | **never checked before — check it now** (K0 found qiskit level 3 inexact at $4.9\times10^{-5}$ on the CZ-basis circuit) |
| IBM-T3 | the two K1 circuits as flown: routed on the 2026-10-06 `ibm_kingston` record, ALAP delays, client XY4 (cell T3) | `data/hardware/K1_2x3_prep/circuits/{B0_ref117_k1,B1_ref29_k1}.qpy.gz` | 5659 CZ, 2408 / 2404 XY4 pulses, 411.2 / 410.8 $\mu$s | K5 bar ($1.6\times10^{-12}$ / $2.3\times10^{-12}$ recorded) |
| IBM-T0 | the same two circuits, ALAP delays, **no** DD pulses | rebuilt from the same record with `gate_K1_2x3_fpilot` build path minus the XY4 insertion (byte-identical routing: same seed rule, same record) | 5659 CZ | bar |
| IBM-U | the same two circuits, routed, **unscheduled** (no delays) | same | 5659 CZ | bar |

Every family is frozen on the laptop as **QPY format version 13** (`qiskit.qpy.dump(..., version=13)`; the CI
runs qiskit 1.4.3, which loads QPY $\le13$ — `quantum.cloud.ibm.com/docs/api/qiskit/1.4/qpy`, read 2026-10-06;
the laptop writes v17 by default, which 1.4.3 cannot read: the S2_2x4 lesson, recipe `data/S2_2x4/qpy13_3.json`)
under `data/campaign33/circuits/<family>/<id>.qpy.gz` with `<id>.json` manifests (ops, depth, sha256 of the gz,
exactness numbers, source file and its sha256, qiskit version that wrote it) and a `data/campaign33/circuits/index.json`.
**Check the header of the two K1 QPY files** (`data/hardware/K1_2x3_prep/circuits/*.qpy.gz`, written by
qiskit 2.5.2; the manifest records no QPY version): if it is not 13, re-write at 13 and record an exact round trip
(instruction-by-instruction equality, including delays and durations) as `data/S2_2x4/qpy13_3.json` does.

### 1.2 Noise scenarios

Notation: $\epsilon_2, \epsilon_1, \epsilon_{ro}$ per-gate / per-readout error probabilities; Aer's
`depolarizing_error(p, n)` is $\mathcal E(\rho)=(1-p)\rho+p\,I/2^n$, whose no-fault probability is
$1-p\,(4^n-1)/4^n$ (so $15p_2/16$ and $3p_1/4$ are the fault probabilities per site; this is what CF_traj
already uses).  "Rz virtual" = noiseless `rz`.

| id | class | noise model (Aer) | parameters | source |
|---|---|---|---|---|
| E0 | none | ideal statevector sampling | — | — |
| E1 | depolarizing (2q on `rzz`, 1q on `rx`/`ry`), asymmetric readout; Rz virtual | $\epsilon_2=8.3\times10^{-4}$, $\epsilon_1=2.8\times10^{-5}$, $p(1\|0)=6.7\times10^{-4}$, $p(0\|1)=1.2\times10^{-3}$ | `quantinuum_submit.A6_NOISE` (= the Q0P A6 dry run; H2-2 performance-validation page read 2026-10-02, `data/quantinuum/devices_20261002.json specs.quantinuum_h2_2`) |
| E2 | same channel classes | Helios-1: $\epsilon_2=7.9\times10^{-4}$, $\epsilon_1=3.0\times10^{-5}$, $\epsilon_{ro}=4.8\times10^{-4}$ symmetric | `data/quantinuum/devices_20261002.json rows.2x3|quantinuum_helios_1` |
| E3 | **emulator parameter set H2-2E (2025-07-16)**: depolarizing with **angle-dependent** 2q error $p_2(\theta)=(a\,|\theta|/\pi+b)\,p_2$, $a=1.518$, $b=0.241$ (power 1); 1q $p_1$; readout $p_{\rm meas}$; initialisation flip $p_{\rm init}$ (X with prob. $p_{\rm init}$ after reset) | $p_2=1.29\times10^{-3}$, $p_1=7.3\times10^{-5}$, $p_{\rm meas}=(9\times10^{-4},1.8\times10^{-3})$, $p_{\rm init}=4\times10^{-5}$ | `docs.quantinuum.com/systems/user_guide/emulator_user_guide/emulators/h2_emulators.html` and `.../noise_model.html` (read 2026-10-06). The emission ratios (0.32 / 0.59), crosstalk ($8.8\times10^{-6}$ / $9.6\times10^{-6}$) and the coherent quadratic dephasing are **not** modelled; say so in the JSON (`not_modelled`) |
| E4 | emulator set **Helios-1E (2025-11-18)**, same channel classes as E3 | $p_2=8\times10^{-4}$, $p_1=2.5\times10^{-5}$, $p_{\rm meas}=(10^{-6},10^{-6})$, $p_{\rm init}=5\times10^{-4}$; leakage ($p_{\rm prep\,leak}$ 0.75 of $p_{\rm init}$, seepage 1/3) **not representable in Aer** -> `not_modelled`; `leak2depolar=False` on the vendor side | `.../helios_emulators.html` (read 2026-10-06) |
| E5a/b/c | E1 + **memory (transport/idle) dephasing**: after every two-qubit layer, on every qubit, Pauli $Z$ with probability $p_{\rm mem}=r_{\rm lin}\,t_{\rm round}$ (the emulator's `linear_dephasing_rate` convention: "Pauli-Z with probability rate x duration") | $r_{\rm lin}=0.0028\ {\rm s^{-1}}$ (H2 emulator value), $t_{\rm round}\in\{0.5, 1.1, 4.4\}$ ms (the project's low / mid / high scenarios), 1925 two-qubit layers (`depth_2q` of the manifests) -> $S_{\rm idle}=0.054\,/\,0.119\,/\,0.474$ nats over 20 qubits (planner arithmetic; equals `memory_ESTIMATE` of the H2-1 row) | `data/quantinuum/devices_20261002.json memory_model`; emulator `noise_model.html`. The quadratic (coherent) term $\sin^2(\tfrac12 f d)$, $f=0.043$, is **not** modelled (`not_modelled`) |
| E6a/b/c | E1 with every error probability scaled by $s\in\{0.5, 2, 4\}$ (the emulator's `scale` parameter) | — | emulator `noise_model.html` (`scale`) |
| E7(f) | **matched-$f$**: E1 with $\epsilon_2$ chosen so that the mean gate-only clean fraction $f_{\rm gate}=(1-\epsilon_2)^{n_{2q}}(1-\epsilon_1)^{n_{1q}}(1-\epsilon_{ro})^{n_m}$ equals $f$ at the mean counts (2158, 3053, 20), $\epsilon_1,\epsilon_{ro}$ at the H2-2 values | $f=0.05$: $\epsilon_2=1.3390\times10^{-3}$; $0.07$: $1.1833\times10^{-3}$; $0.10$: $1.0182\times10^{-3}$ (= the device table's `eps2_for_mean_f_0.1` to $7.6\times10^{-10}$); $0.15$: $8.3048\times10^{-4}$ | `scratch/planner/campaign33_sizing_20261006.json matched_f` — **recompute in code**, assert the 0.10 value against `data/quantinuum/devices_20261002.json` to $10^{-9}$ |
| E8 | the gate-S3 declared model: depolarizing on `rzz` AND on `rz`,`rx`,`ry` (rz NOT virtual), symmetric readout | $\epsilon_2=10^{-3}$, $\epsilon_1=10^{-4}$, $\epsilon_{ro}=2\times10^{-3}$ | `validation/S3.json data.declared_inputs`, `scripts/s3_device_model.py` |
| I-GATE | IBM, **gate-only**: depolarizing + thermal relaxation on every gate for its duration + readout, from the 2026-10-06 `ibm_kingston` record (what `NoiseModel.from_backend` builds), unscheduled circuit (IBM-U) | record `data/hardware/K0_prep/ibm_kingston_full_20261006T0652Z.json` (fingerprint `b948ddc8…`) | `qiskit_aer.noise.NoiseModel.from_backend` docs (read 2026-10-06): "depolarizing gate errors, thermal relaxation, readout errors" |
| I-ECHO | IBM, **idle-aware**: IBM-T0 (ALAP delays) with thermal relaxation on every `delay` at the record's Hahn-echo $T_2$ | same record | the H0_model / H0_kpilot scheduled-Aer path (`gate_H0P.schedule_circuit`: Aer "charges" delays with relaxation) |
| I-STAR | I-ECHO with $T_2^*=0.174\,T_2^{\rm echo}$ per qubit (the measured ratio, `validation/H0_diag.json`, rule M-T2 of prompts/20) | | `scripts/h0_t2_override.py` convention |
| I-XY4 | IBM-T3 (the XY4 pulses present as `x`/`y`… gates in the delays) at both $T_2$ ends | | **information only**: Aer's relaxation on a delay is Markovian, so no DD gain can appear (the H0_ddrep dry run showed ratios at the null) |
| I-COH | I-ECHO + a **coherent over-rotation** $R_x(\epsilon_q)$ after every `x` pulse, $\epsilon_q$ = the per-qubit value of `validation/H0_ddrep.json` where the qubit is in the 12-qubit patch, else the median of the 12 (0.0148-0.0204 rad measured) | `coherent_unitary_error` | the pulse-train measurement of H0_ddrep (2026-10-06) |

Class 2 **channel classes, stated**: depolarizing (gate error), thermal relaxation $T_1$/$T_2$ on gates and (idle-
aware cells) on delays, readout confusion, coherent over-rotation (I-COH only).  **Not modelled**: ZZ crosstalk
and measurement crosstalk (no data in the record and no Aer channel for it), leakage, non-Markovian dephasing.
The XY4 cell is included as I-XY4 and labelled information.

**Relaxation representation (class 2, decided here).** Aer's `thermal_relaxation_error(t1, t2, t)` is a Kraus
channel when $T_1<T_2\le2T_1$ (Aer docs, read 2026-10-06) and that is why one noisy 21-qubit shot cost 140.6 s
on the laptop CPU in the K1 dry run.  C2_CAL measures BOTH representations on the GPU and the production cells use
the faster one if they agree: (a) **Kraus**, exactly `from_backend` / `RelaxationNoisePass(t1s, t2s, dt,
op_types=[Delay])`; (b) **Pauli-twirled** (PTA), the stochastic-Pauli channel with
$p_X=p_Y=\tfrac14(1-e^{-t/T_1})$, $p_Z=\tfrac12(1-e^{-t/T_2})-\tfrac14(1-e^{-t/T_1})$ (non-negative iff $T_2\le2T_1$),
whose total error $\tfrac14(1-e^{-t/T_1})+\tfrac12(1-e^{-t/T_2})$ is exactly the per-window term of
`src/skqd/idle.py` (Geller & Zhou, Phys. Rev. A 88, 012314 (2013), arXiv:1305.2021, the Pauli twirling
approximation).  Agreement test: accepted fractions of the two at $\ge512$ shots of the same circuit within
$3\sigma$ (binomial); if they disagree, production uses Kraus only and the JSON says so.  Build the PTA model with
`qiskit_aer.noise.LocalNoisePass(func, op_types=[Delay])` applied on the CI node at run time (the QPY carries the
scheduled circuit with delays; the pass is pure Python).  Record in every class-2 JSON: representation,
`t2_convention` (`echo` / `star_0.174`), $T_1$/$T_2$ per active qubit, `dt`, the record fingerprint.

### 1.3 Shot plans and sequences

- **f-cell** (clean-fraction cell, the cheap unit): the four Stage-E v3 circuits `B0_ref117_k1`, `B1_ref29_k1`
  (800 shots each) and `B0_ref117_k4`, `B1_ref29_k4` (200 each) = 2 000 shots (`validation/Q0P_2x3_plan.json
  data.stage_E_v3`).  Outputs: $f_{\rm hit}$ with the Garwood interval, $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$,
  $f_0$ (analytic), accepted fraction (Wilson 95 %), GO rule v3 reading (information).
- **plan-of-record run** (the full SKQD unit): per-circuit shots from `validation/CV_2x3_plan.json
  data.plan.<f>.<sector>.final_shots_by_circuit` ($B=0$ at $s=1$, $B=1$ at $s=2$).  The plan tier is chosen per
  scenario by the campaign rule: the largest $f\in\{0.05,0.10,0.15\}$ not above the f-cell's lower 95 % end of
  $\hat f_{\rm ideal}$ for that scenario (read from C4_FCELLS, which therefore runs first), default $0.15$ for E1/E2/E3/E6
  and recorded in the JSON (`plan_tier`, `plan_tier_reason`).  F5 is fixed at the $f=0.10$ plan by design.
- **S3-quota run**: $2\times10^5$ shots per sector, uniform over the sector's circuits (6 250 per $B=0$ circuit,
  16 667 per $B=1$ circuit; `s3_device_model.py` convention `shots_per_sector // n_circuits`), in two jobs of
  $10^5$ per sector (seeds disjoint, section 2.3), merged at assembly; the plan-of-record prefix is read from the
  same sequences where per-circuit plan shots $\le$ the uniform count, else the cell says `prefix_not_covered`
  (at $f=0.10$: $B=0$ max 17 600 > 6 250 for the $k=4$ circuits, so the $B=0$ CV reading of F4 comes from F5/F1-type
  runs, not from F4; record this instead of extrapolating).
- **Order-kept sequences**: every noisy run records, per circuit, the counts of every sequential chunk (chunk
  size $\le\min(476,\lceil N_c/16\rceil)$) so that prefixes at $\phi\in\{1/16,1/8,1/4,1/2,1\}$ are nested exactly
  as in `gate_CV` (`skqd.noise.measure_and_decode_sequence`); `memory=True` (per-shot list) may be used in addition
  only if a laptop test shows Aer 0.15.1-compatible behaviour and C4_FCELLS_A confirms it on the GPU.  Store as
  `results/campaign33/<token>/<circuit>.npz` (chunk counts as int arrays over decoded indices + raw-string
  dictionaries for the accepted strings) with the seed of every chunk.

### 1.4 Optimisation variants (class 4), and which are allowed

The exactness bars are the project's: after global-phase removal $\max|\Delta\psi|<10^{-10}$ against the exact
Krylov state and leakage $<10^{-9}$, measured exactly as Q0P's Q1 / K0's K5 (`skqd.circuits_qiskit.statevector_aer`
with fusion, cross-checked on one circuit per variant with `quantum_info.Statevector`).  **Allowed** = passes the
bar on all 44 circuits; otherwise **information only** (its $f$ and $E_R$ shifts are reported, never used for a
campaign number).  Build on the laptop (pytket in the isolated venv `~/.local/share/su2qc-quantinuum/venv`,
qiskit in `coding`); freeze as QPY v13.

| id | technique (class of optimisation) | tool | expected | status rule |
|---|---|---|---|---|
| O0 | none (pytket level 0) | frozen | 2158 ZZPhase | allowed by construction |
| O1 | **peephole resynthesis + 1q squashing** (exact): `FullPeepholeOptimise(allow_swaps=False, target_2qb_gate=TK2)` -> `AutoRebase({Rz, PhasedX, ZZPhase})` -> `RemoveRedundancies` -> `SquashRzPhasedX`, applied to the **measurement-free** circuit, measurements re-appended (avoids TKET's removal of the Rz before each Measure that made level 2 state-inexact, Q0P: $\max|\Delta\psi|=0.585$) | pytket 2.18.4 | $\le2158$ ZZ, fewer PhasedX | bar |
| O2 | **adjacent inverse cancellation** (qiskit preset level 1, "light optimization by simple adjacent gate collapsing") in basis `[rz, rx, ry, rzz]`, no coupling map, `seed_transpiler=7` | qiskit 2.5.2 (laptop) | small 1q reduction | bar |
| O3 | **commutation-based cancellation** (qiskit preset level 2, "gate cancellation using commutativity rules") | qiskit | | bar |
| O4 | **two-qubit peephole / unitary resynthesis** (qiskit preset level 3, `approximation_degree=1.0`) | qiskit | expected to **fail** the bar (K0: $4.9\times10^{-5}$ on the CZ-basis circuit) | bar; likely information |
| O6 | **approximate synthesis**: pytket `KAKDecomposition(cx_fidelity=0.999)` on the 2q blocks, rebased as O1 | pytket | inexact by construction | information only |
| — | gate-order / term-order re-ordering for parallelism | — | — | **not built**: owner decision D5 of prompts/27 pending (the signed term order is a signature item) |
| — | dynamical decoupling | — | — | **not applicable** to classes 3/4 (no idle term except E5, whose Z-flips are incoherent and cannot be refocused); the IBM XY4 cell is I-XY4 in class 2 |

The variant used by C4_F7 is the allowed one with the fewest two-qubit gates, ties broken by fewer one-qubit gates,
then the lower id (Q0P's selection rule); record `chosen_variant` and the counts of every variant in the index.

### 1.5 The tokens (one Perlmutter job each; walltimes are the allowlist lines of section 7a)

Sizing basis: `validation/S3.json data.cost.seconds_per_shot_best_ladder` = 0.0198663 s/shot at 20 qubits on one
A100 (job 58771538, cuStateVec path, 476 shots per `run` call), a 1.25 contingency and 5 min fixed per job
(planner arithmetic, `scratch/planner/campaign33_sizing_20261006.json jobs`).  `run_gate.py` kills a gate at
3 600 s, so every job self-budgets to finish in $\le50$ min and records what it dropped.

| token | class | content | shots | estimate | walltime |
|---|---|---|---|---|---|
| `C1_IDEAL` | 1 | IR-L0 (44), NAT-O0 (44), IBM-U/T0/T3 (6): exactness vs exact Krylov states; noiseless sampling at the $f=0.10$ plan and at $2\times10^5$ per sector; the $f=1$ SKQD reference (support, recall, $E_R$, certificates) | n/a (statevector) | 12 min | 00:30 |
| `C2_CAL` | 2 | 21-qubit timing ladder {8, 32, 128, 512} shots on `B0_ref117_k1` (IBM-T0) for Kraus vs PTA, cuStateVec vs `batched_shots_gpu` (with `batched_shots_gpu_max_qubits=21`), agreement tests; writes `s_per_shot` per mode; sizes C2_* | $\le 2\times4\times680$ | 30 min | 00:45 |
| `C2_GATE` | 2 | I-GATE on IBM-U, both K1 circuits, target $10^5$ each, reduced to the C2_CAL rate × 50 min | sized | 50 min | 01:00 |
| `C2_ECHO` | 2 | I-ECHO on IBM-T0 | sized | 50 min | 01:00 |
| `C2_STAR` | 2 | I-STAR on IBM-T0 | sized | 50 min | 01:00 |
| `C2_XY4` | 2 | I-XY4 on IBM-T3, echo and star halves (information) | sized | 50 min | 01:00 |
| `C2_COH` | 2 | I-COH on IBM-T0 | sized | 50 min | 01:00 |
| `C3_AER` | 3 | NAT-O0 noiseless on Aer GPU (the qiskit path): per-state agreement with the exact distribution; $f=1$ SKQD reference of the native family at the $f=0.10$ plan and $2\times10^5$ | n/a | 12 min | 00:30 |
| `C3_LE` | 3 | pytket-pecos **H2-1LE local emulator** (noiseless, CPU, env `skqd-pecos`): ladder {2, 8, 32} then fill to 50 min on the 4 Stage-E circuits; per-state agreement with C3_AER | ladder-sized | 50 min | 01:00 |
| `C3_SEL` | 3 | **optional**: Selene (QuEST statevector, `IdealErrorModel`) on the QIR export of the 4 Stage-E circuits, env `skqd-selene`; only if the laptop pre-check of section 3.4 passes | ladder-sized | 50 min | 01:00 |
| `C4_FCELLS_A` | 4 | 10-min ladder (chunk sizes 476 / 952 / 1 428 at `--gpu-memory-bytes` 8e9 / 1.6e10 / 2.4e10; cuStateVec vs batched) then f-cells: scenarios E1, E2, E3, E4, E5a/b/c × variants O0-O4 (+O6 info) = 40 cells × 2 000 | 80 000 | 38 min | 01:00 |
| `C4_FCELLS_B` | 4 | f-cells E6a/b/c, E7(0.05/0.07/0.10/0.15) × O0-O4 = 35 cells; + the **faithful S3 redo**: IR-L3-RZZ, E8, 32 circuits × 100 shots, `seed_simulator=11`, `seed_transpiler=7` | 73 200 | 36 min | 01:00 |
| `C4_F1_B0`, `C4_F1_B1` | 4 | E1 × O0, plan-of-record run (tier by rule, default 0.15) | 27 309 / 67 600 | 16 / 33 min | 01:00 |
| `C4_F2_B0`, `C4_F2_B1` | 4 | E2 × O0 | same | 16 / 33 | 01:00 |
| `C4_F3_B0`, `C4_F3_B1` | 4 | E3 × O0 | same | 16 / 33 | 01:00 |
| `C4_F4_B0a/b`, `C4_F4_B1a/b` | 4 | E7(0.10) × O0, **S3-quota** $2\times10^5$ per sector in 2 × $10^5$ (the S1 redo; CV prefix where covered) | 4 × 100 000 | 4 × 46 | 01:00 |
| `C4_F5_B0`, `C4_F5_B1` | 4 | E7(0.07) × O0 at the $f=0.10$ plan (like-for-like with CV_2x3_plan, which sampled at $0.7f$) | 34 909 / 99 000 | 19 / 46 | 01:00 |
| `C4_F6_B0`, `C4_F6_B1` | 4 | E5b (memory mid) × O0 | 27 309 / 67 600 | 16 / 33 | 01:00 |
| `C4_F7_B0`, `C4_F7_B1` | 4 | E1 × chosen exact variant | same | 16 / 33 | 01:00 |
| `C4_F8_B0a/b`, `C4_F8_B1a/b` | 4 | E8 × O0 (exact family), S3-quota $2\times10^5$ per sector: **the S3 recall criterion, evaluated for the first time** | 4 × 100 000 | 4 × 46 | 01:00 |
| `C4_CF` | 4 | CF_traj redo on the GPU: $K=2\,000$ faulty Pauli trajectories per arm (`B0_ref25_k1`, `B1_ref57_k1`, `B0_ref25_k4`, `B0_ref25_k1__xx`), checkpointed statevectors as `cf_trajectories.py`; $f_{\rm hit}$, $b$, $f_{\rm ideal}$, $r$ per arm, pooled $r$, $r_{nc}$ | 8 000 statevector runs | 45 min | 01:00 |

33 jobs; sum of estimates 20.1 h of 1-GPU walltime = **5.0 GPU node-hours** at $C=\tfrac{G}{4}t$ ($G=1$); cap
from the walltimes 31.75 h = 7.9 node-hours.  Every job is independent of every other except: C2_* read
`validation/C2_CAL.json` (sizing) if present, else fall back to 20 000 shots per circuit and say so; C4_F* read the
plan tier from `validation/C4_FCELLS_A.json` if present, else default 0.15 and say so.  Nothing waits.

---

## 2. Method (equations, conventions, statistics)

### 2.1 Clean-fraction statistics (unchanged project definitions)

- Reference-hit fraction of a circuit with $N$ shots, ideal reference probability $p_{\rm ref}$, sector garbage
  acceptance $a$, dimension $\dim$: $f_{\rm hit}=\dfrac{n_{\rm ref}-N a/\dim}{N\,p_{\rm ref}\,\kappa}$ with
  $\kappa=1$ on the Quantinuum path (the model already contains readout survival; `readout_factor_note` of the A6
  dry run) and $\kappa=0.82$ only where the project's hardware convention is being compared (class 2, as K1);
  interval: Garwood (Poisson) on $n_{\rm ref}$, pooled over the k = 1 circuits as `gate_K1_2x3_fpilot` does.
- $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$, $r_{nc}=1.115$ (`data/cf_trajectories/r_nc.json`), interval divided
  through; GO rule v3 (`gate_Q0P_2x3.go_rule_v3`) reported as information in every f-cell.
- Fault-free fraction $f_0$ (analytic, per circuit and scenario): the product of the channel's no-fault
  probabilities over all noisy sites, times the readout survival $(1-p(1|0))^{n_0}(1-p(0|1))^{n_1}$ of the
  reference string; for E1 at the mean counts this is $g_0=(1-\tfrac{15}{16}p_2)^{2158}(1-\tfrac34 p_1)^{3053}=0.1748$
  before readout (planner arithmetic; CF_traj's per-circuit $f_0'$ 0.17209 includes readout).  Record both.
- Accepted fraction with a Wilson 95 % interval; garbage acceptance $a$ from the exhaustive per-sector decoder
  acceptance (`gate_CV.acceptance_2x3`).

### 2.2 Energies, certificates, convergence

- $B_{\rm all}$ = references $\cup$ decoded accepted strings; Ritz energy $E_R$ from `skqd.skqd.ritz` (dense
  eigh); residual $r_H$; Weinstein $[E_R-r_H, E_R]$; Kato-Temple with the exact $E_1$: $E_0\ge E_R-\dfrac{r_H^2}{E_1-E_R}$
  (`certify(...).kt_rigorous`), read at $B=0$ (owner decision `data/owner_decision_20261005_kt_certificate.md`),
  Weinstein at $B=1$ — exactly prompts/31 ruling 2.  Variational check $E_R\ge E_0-10^{-9}$ everywhere.
- Support metrics: $|B_{\rm all}|$, recall of $S_{99}$ and $S_{999}$ (`support_metrics`), captured weight $W$,
  false positives.
- CV0-CV5 as `gate_CV` (import its functions: `Sector`, `evaluate`, `resize_points`, `h1_energy_tolerance`,
  the 200 random equal-size baselines with `gate_H0_2x2.RANDOM_SEEDS`), with $E_{\rm tol}$ recomputed and asserted
  equal to `validation/CV_2x3_plan.json data.E_tol` to $10^{-12}$.  CV3 ($k=4\to5$) needs the $k=5$ circuits:
  build NAT-O0 $k=5$ circuits of every reference on the laptop (same pytket level-0 compile, verified to the bar),
  freeze them, and sample them in the F-runs at the equal-shots count `gate_CV` uses (`cv3_at_2Nc_information`
  convention); if the extra shots do not fit the budget, CV3 is `not_evaluated` with the reason, never estimated.
- Bootstrap: 2 000 resamples over shots within each circuit (seed 33), percentile 95 % intervals on $E_R-E_0$,
  recall, $W$, $f_{\rm hit}$; the random-basis percentiles as in CV4.

### 2.3 Seeds and chunking

`sample_many` strides seeds by the chunk size (consecutive Aer seeds overlap).  Base seed per token:
$s_0=33\,000\,000+10^5\times(\text{token index in } `scripts/gate_tokens.json`)$; chunk $i$ of circuit $c$ uses
$s_0+10^3 c+i\cdot{\rm stride}$ with stride $\ge$ chunk size; the two halves `a`/`b` of a $2\times10^5$ run have
token indices that differ, so their streams are disjoint by construction.  Every seed is in the JSON.

### 2.4 Noiseless-sampling agreement (classes 1 and 3)

For every circuit, every state $s$ with exact probability $p_s\ge10^{-3}$ must satisfy
$|n_s/N-p_s|\le5\sqrt{p_s(1-p_s)/N}$; with at most ~100 tested states per circuit and 90 circuits the
Bonferroni false-alarm probability at $5\sigma$ is below $10^{-2}$ in total ($9\,000\times5.7\times10^{-7}$),
so a failure is a bug, not noise.  Also $\max|\Delta\psi|<10^{-10}$, leakage $<10^{-9}$ (the project bars).
For C3_LE / C3_SEL (different engines, small $N$): the same test at $3\sigma$ with $N$ from the ladder, plus a
two-sample total-variation distance against C3_AER with its multinomial expectation.

### 2.5 The comparison statistic (every "redo")

$\Delta=x_{\rm new}-x_{\rm old}$; $\sigma=\sqrt{\sigma_{\rm new}^2+\sigma_{\rm old}^2}$ with
$\sigma=$ (95 % half-width)/1.96 where an interval exists, else `none`; verdict `consistent` if $|\Delta|\le2\sigma$,
`tension` if $2\sigma<|\Delta|\le4\sigma$, `inconsistent` beyond, `no_old_uncertainty` when the old value has no
interval (then report $\Delta$ and $\sigma_{\rm new}$ only).  For counts (hits, accepted) use the two-sided
Poisson / binomial probability of the observed value under the new estimate.

---

## 3. Inputs the executor must read first

`CLAUDE.md`; `RUNBOOK.md` "Engine and HPC policy"; `SKQD-CI-SETUP.md`; `ci/poll.sh`, `ci/install_skqd_ci.sh`,
`jobs/gate.sbatch`, `scripts/run_gate.py`, `scripts/ci_request.sh`, `scripts/ci_check.sh`; `scripts/s3_device_model.py`
(CI self-detection, ladder, telemetry, budget — the template for every token); `src/skqd/circuits_qiskit.py`
(`sample_many`, `shot_chunk_for`, `_aer_options`); `src/skqd/hpc.py`; `src/skqd/quantinuum_native.py`
(`pytket_to_ir`); `scripts/gate_CV.py`; `scripts/gate_K1_2x3_fpilot.py` (f statistics, build path);
`scripts/gate_H0P.py` (`schedule_circuit`, `load_t2_override`); `scripts/h0_backends.py` (`backend_from_record`,
`calibration_record`); `src/skqd/idle.py`; `scripts/cf_trajectories.py`; `scripts/quantinuum_submit.py` (A6);
`data/S2_2x4/qpy13_3.json` (the QPY v13 recipe); `tests/test_s3_ci_mode.py`, `tests/test_ci_gpu_mode.py`,
`tests/test_s2_2x4_ci_mode.py` (how GPU-only paths are pinned on the laptop); the JSONs listed in the trigger;
`scratch/planner/campaign33_sizing_20261006.json`.

### 3.1 Environment facts (verified 2026-10-06)

- CI env `skqd`: qiskit 1.4.3, qiskit-aer-gpu 0.15.1 (requires `qiskit>=1.1.0`, cp312 manylinux wheel; PyPI
  metadata read 2026-10-06), numpy 2.5.3, scipy 1.18.1, python 3.12.14 (`validation/S3.json environment`).  **No
  pytket on the CI**: all pytket work happens on the laptop and only QPY v13 is committed.  `qiskit-ibm-runtime`'s
  fake provider is NOT relied on in any job: class-2 noise models are built from the committed calibration record.
- Laptop: `coding` (qiskit 2.5.2, aer 0.17.2, runtime 0.49.0) untouched; the isolated venv has pytket 2.18.4,
  pytket-quantinuum 0.59.3, pytket-qir 2.0.2 (`validation/Q0P_2x3.json data.frozen.versions`; pytket-qir checked
  2026-10-06).
- pytket-qiskit is NOT installable into the CI env (its last qiskit-1.x release 0.66.0 needs `qiskit<2,>=1.4.2`
  but `qiskit-aer>=0.15.1` and `pytket>=2.1.0`; the current 0.78.0 needs qiskit>=2.3) and is not needed.
- `batched_shots_gpu_max_qubits` defaults to 16 (Aer docs, read 2026-10-06): the S3 run at 20 active qubits
  therefore used the cuStateVec per-shot path, not shot batching.  C2_CAL / C4_FCELLS_A measure both.

---

## 4. Steps

Milestone A (laptop, no GPU, 0 QPU s) builds and freezes; milestone B is the owner's installation (section 7);
milestone C is the Perlmutter campaign; milestone D assembles and reports.  Each step names its done-check.

### A1. Token table and runner hook (laptop, 1 h)
- `scripts/gate_tokens.json`: `{token: {"script": "scripts/campaign33.py", "args": ["--token", token], "class": n,
  "walltime": "HH:MM:SS", "gpus": 1, "env": "skqd"|"skqd-pecos"|"skqd-selene"}}` for the 33 tokens of 1.5.
- `scripts/run_gate.py`: when no `scripts/gate_<G>.py` / `laptop_<G>_*.py` exists, look the token up in
  `scripts/gate_tokens.json` and run its script+args; everything else (JSON read, BLOCKED.md, `--push`) unchanged.
- `ci/allowed_jobs.campaign33`: the 33 lines `TOKEN  MAX_WALLTIME  GPUS` generated FROM `gate_tokens.json`
  (test: identical content), for the owner to append (section 7a).
- `jobs/gate.sbatch`: choose the conda env from `jobs/env/<CI_GATE>` if that file exists (one line, the env name),
  else `skqd`; nothing else changes (resources stay on the poller's sbatch line).
- Done-check: `tests/test_campaign33_tokens.py` (table complete, walltimes $\le$ 01:00:00, every token's class/env
  valid, `run_gate.py` resolves every token on a dry `--help`).

### A2. Circuit freeze (laptop, ~4 h wall, background allowed)
- `scripts/campaign33.py --stage freeze` builds every family of 1.1 and every variant of 1.4 (and the NAT-O0 $k=5$
  circuits), verifies each to the bars, writes QPY v13 + manifests + `index.json` under `data/campaign33/circuits/`.
  The IBM families come from the K1 build path on the committed record (reuse `gate_K1_2x3_fpilot` stages, no
  re-routing: load the K1 QPY, derive T0 by replacing every XY4 pulse by a delay of its duration — the
  `h0_ddrep_circuits.strip_pulses_on` operation on all qubits — and U by `transpile(optimization_level=0)` without
  scheduling; assert the per-qubit non-delay operation order is identical across T3/T0/U).
- IR-L3-RZZ: transpile exactly as `s3_device_model.py` does; record its exactness; if it fails the bar, say so in
  the manifest (`exact: false`) — it is still frozen for the faithful S3 redo and labelled information.
- Done-check: `tests/test_campaign33_freeze.py`: every QPY header is version 13; every manifest sha256 matches;
  round trip of one circuit per family equals the source instruction by instruction; the O0 conversion reproduces
  Q0P's Q1 numbers (ZZ 2158 on all 44, $\max|\Delta\psi|<10^{-10}$); the variant table lists counts and `allowed`.

### A3. Noise models and statistics modules (laptop, 1 day)
- `src/skqd/campaign33/noise.py`: builders for E1-E8 and I-* returning Aer `NoiseModel`s (plus the `LocalNoisePass`
  for the angle-dependent E3/E4 term and for delays); every builder returns alongside a JSON-able `description`
  with channel classes, parameters, sources, `not_modelled`.  Angle-dependent 2q error: `LocalNoisePass(lambda inst,
  qubits: depolarizing_error(p2 * (a*abs(theta)/pi + b), 2), op_types=[RZZGate])` with `theta = inst.params[0]`.
  Memory E5: a Pauli-Z error with probability $p_{\rm mem}$ on every qubit after every two-qubit layer (layers by
  ASAP depth over `rzz`; implemented as a `LocalNoisePass` on `rzz` whose error acts on both qubits is NOT the same
  thing — do it as explicit `pauli_error` instructions inserted after each layer on the laptop-built circuit variant
  `NAT-O0-mem` or as a Pauli channel attached to a labelled barrier; document the choice and test that the number of
  inserted sites is $20\times1925$ per circuit).
- Record noise (class 2): `record_noise_model(record, patch, representation, t2_convention)` building per-qubit /
  per-edge depolarizing + relaxation + readout from the committed record **without** the fake provider; laptop test:
  for the Kraus representation, each gate's `QuantumError` equals `NoiseModel.from_backend(backend_from_record(...))`'s
  to $10^{-12}$ in the Kraus matrices / probabilities (the laptop has runtime 0.49.0 for this test only).
- `src/skqd/campaign33/stats.py`: $f_{\rm hit}$ (Garwood), $\hat f_{\rm ideal}$, $f_0$ analytic, Wilson, bootstrap,
  the comparison statistic of 2.5, the matched-$f$ inversion (assert the 0.10 value to $10^{-9}$).
- Done-check: `tests/test_campaign33_noise.py` (no-fault probabilities, PTA non-negativity for $T_2\le2T_1$ and the
  equality of the PTA total to `idle.py`'s per-window term, angle scaling at $\theta=0,\pi$, E5 site count, matched-$f$
  values, the record model equality) and `tests/test_campaign33_stats.py`.

### A4. The job driver (laptop, 1 day)
- `scripts/campaign33.py --token <T>`: CI self-detection as `s3_device_model` (`skqd.hpc.ci_context`), GPU per policy
  (`AerSimulator(method="statevector", device="GPU", cuStateVec_enable=True, batched_shots_gpu=True)` through
  `sample_many`, double precision), one chunked `run([...])` call set per circuit set, per-chunk counts kept,
  self-budget (ladder-sized shots, 25 % of the remaining time reserved for decoding/Ritz/report), telemetry via
  `jobs/gate.sbatch`'s sampler (`skqd.hpc.gpu_telemetry`), `run` block as S3 (engine, device, GPUs, tasks, wall,
  phases, s/shot, peak GPU memory, mean utilisation, versions, seeds, batching, E(p) null with the note).  Output:
  `validation/<TOKEN>.json` (`status` PASS/FAIL on the token's criteria of section 5), `reports/<TOKEN>.md`
  (generated), `results/campaign33/<TOKEN>/*.npz`.
- Laptop mode: the same driver on the CPU with `--shots-scale 0.01` and `--max-shots-per-run 16` (forced chunking)
  must run every token end to end in $\le$ 10 min each (the dry run of the whole campaign); its JSON is tagged
  `dry_run: true` and written to `validation/dryrun/<TOKEN>.json`.
- Done-check: the 33 dry runs PASS their structural criteria; `tests/test_campaign33_driver.py` pins the CI
  defaults per token (as `test_s3_ci_mode.py`), that explicit arguments win, and that a budget overrun reduces
  shots rather than exceeding the walltime.

### A5. The poller change (laptop, 0.5 day) — section 7c; done-check `tests/test_ci_poller_sim.py`.

### A6. Class-3 engines pre-check (laptop, 2 h)
- Create `~/.local/share/su2qc-pecos/venv` (python 3.12, `pip install "numpy<2" "pytket~=2.17"
  "pytket-quantinuum[pecos]==0.59.3"`; the `pecos` extra pins `quantum-pecos==0.8.0.dev8`, a prerelease that pip
  installs because the pin is exact — PyPI metadata read 2026-10-06).  Run `QuantinuumBackend(device_name="H2-1LE",
  api_handler=QuantinuumAPIOffline())` (no credentials needed: pytket-quantinuum API docs, read 2026-10-06) on
  `B0_ref117_k1` at 2 shots with `simulator="state-vector"`, `noisy_simulation=False`; measure s/shot.  If the
  install fails or s/shot $>60$ s (fewer than 50 shots in a job), drop `C3_LE` (record the reason in
  `data/campaign33/engines.json`); the token stays in the table but its job is not requested.
- Selene: `pip install selene-sim==0.3.4` in a third venv (needs `numpy~=2.0`, so it cannot share the pecos env);
  export the 4 Stage-E circuits to QIR with pytket-qir 2.0.2 (`pytket.qir.pytket_to_qir`, Quantinuum profile);
  if Selene's `Quest` simulator runs the QIR with `IdealErrorModel` at 2 shots and the counts decode, keep `C3_SEL`,
  else drop it with the reason.  (Selene: `docs.quantinuum.com/selene`, GitHub `Quantinuum/selene`, read
  2026-10-06: inputs HUGR/Guppy and QIR; simulators QuEST / Stim; error models Ideal, Depolarizing, SimpleLeakage.)
- Done-check: `data/campaign33/engines.json` with versions, s/shot, keep/drop and the reason.

### A7. Assembly and report generator (laptop, 0.5 day; runs after milestone C too)
- `scripts/campaign33.py --stage assemble` reads every `validation/C*.json` present, merges the a/b halves, builds
  the **campaign matrix** (class × scenario × variant → $f_{\rm hit}$, $\hat f_{\rm ideal}$, $f_0$, accepted,
  $|B|$, recall, $E_R-E_0$, certificate widths, CV flags, GPU s/shot, node-hours) and the **comparison table**
  (section 6) into `validation/C33_campaign.json` and `reports/C33_campaign_report.md`; every number from JSON.
- Done-check: assembly on the laptop dry-run JSONs produces the full report skeleton with `dry_run` banners.

### A8. Commit (laptop): `git add` only the files of this prompt; `git commit` with the attribution lines; **no push**.
Append the LOG row.  Hand the owner the section-7 list.

### B. Owner installs (section 7).  Then the owner tells the coordinator to push and request.

### C1. Requests: after the owner's go, `scripts/ci_request.sh C1_IDEAL C3_AER C2_CAL C4_FCELLS_A` first (the
calibrations and the ideal references), the rest the same day in the order of 1.5 (one commit with one request file
per token; the poller takes up to MAX_CONCURRENT at a time).  Check with `scripts/ci_check.sh` no more than hourly.

### C2. On each harvest: read `validation/ci_gate_<TOKEN>.json` and `validation/<TOKEN>.json`; a FAIL on a
structural criterion -> fix, commit, re-request (max 3 per token, then `prompts/BLOCKED_C33.md`); a FAIL on a
physics criterion -> STOP (section 8).

### D. Assemble, generate the report, update `validation/gates.md` (`update_status.py` rows for the 33 tokens +
`C33_campaign`), `reports/PROJECT_STATUS.md` paragraph, LOG row, `graphify update .`, commit, no push.

---

## 5. Pass criteria (machine-checkable, per token; written as `criteria` in `validation/<TOKEN>.json`)

Structural (every token): S1 the run happened on the requested device (GPU under the CI for classes 1/2/4 and
C3_AER); S2 wall time $\le$ the walltime budget; S3 telemetry and `run` block present (policy fields non-null on
the CI); S4 every seed and every chunk recorded; S5 no OOM retry left unrecorded; S6 shots $\ge$ the token's
minimum (C4_F*: the plan of record in full, else `FAIL` with `shots_reduced_to`).

Physics (by class):
- C1 / C3_AER: P1 $\max|\Delta\psi|<10^{-10}$ and leakage $<10^{-9}$ on every circuit of every family marked
  `allowed`; P2 the $5\sigma$ per-state test of 2.4 on every circuit; P3 the noiseless SKQD at the $f=0.10$ plan:
  recall of $S_{999}\ge0.9$ in both sectors, $E_0$ inside the KT ($B=0$) / Weinstein ($B=1$) interval, $E_R\ge E_0-10^{-9}$
  (these reproduce S1's $f=1$ rows: `validation/S1.json data.table4["f=1.0|shots=10000"].recall = 1.0` at
  10 000 shots is the reference point).
- C2_CAL: P4 Kraus vs PTA accepted fractions within $3\sigma$ at $\ge512$ shots (else `representation: kraus_only`,
  still PASS: it is a calibration); P5 ladder $\ge2$ points per mode.  C2_*: P6 decoder round trip on every accepted
  string (0 mismatches, as K4); P7 the simulated accepted count and reference hits are reported with the two-sided
  Poisson probability of the **measured** K1 values (58 / 45 accepted, 0 / 0 hits at $10^5$) under the model — no
  threshold (a measurement-vs-model statement, like H0_model's C5), the PASS criterion is that the fields exist.
- C3_LE / C3_SEL: P8 per-state agreement with C3_AER at $3\sigma$; P9 every accepted string decodes.
- C4_FCELLS_*: P10 every variant marked `allowed` reproduces, cell by cell, the O0 cell's $f_{\rm hit}$ within
  $2\sigma$ of the pooled difference (an exact optimisation changes the gate count, so $f$ MAY move — this is a
  reported comparison, PASS = fields present); P11 the E1 × O0 cell's hit count is inside the Poisson 95 % band of
  the CF_traj trajectory prediction scaled to 1 600 k = 1 shots ($63.46\pm2.254$ per 280 shots -> $362.6\pm12.9$;
  `validation/CF_traj.json` C2) — **a physics criterion**: the trajectory decomposition predicts the direct Aer
  sampling of the same channel; P12 the faithful S3 redo at 3 200 shots, seed 11: accepted count inside the binomial
  95 % band of S3's 695 of 3 200 (the GPU RNG of aer 0.15.1 under the same seed may or may not reproduce the same
  stream: equality is reported, the band is the criterion).
- C4_F*: P13 $E_R\ge E_0-10^{-9}$, prefixes nested (CV0), $E_0$ inside the certificate of ruling 2 at $N$;
  P14 recall of $S_{999}\ge0.9$ on $B_{\rm all}$ at $N$ for scenarios whose $\hat f_{\rm ideal}$ lower end
  $\ge$ the plan tier (the plan was sized for it; a FAIL here is a finding about the plan, reported, not a STOP);
  CV1-CV5 reported with their own `ok` flags (information: the plan-of-record check is `CV_2x3_plan`).
- C4_F8: P15 the gate-S3 criterion itself: recall of the 99.9 % support $\ge0.9$ with $2\times10^5$ shots per sector
  and $E_0$ inside the Weinstein interval, both sectors (`s3_device_model.RECALL_MIN`, `EPS_SUPPORT`), on the exact
  family under the declared model.
- C4_CF: P16 $r$ per arm with 95 % bootstrap intervals; pooled $r$; new $r_{nc}$ = its upper end; P17 the floor
  theorem (CF_traj C4') holds on every arm.

Tolerance justifications: the exactness bars are the signed project bars; $5\sigma$ / $3\sigma$ bands are
false-alarm bounds computed above; nothing is tuned to pass.

---

## 6. The old results and what "redo and compute the difference" means for each

| old result | what it was | redo (token) | difference computed (section 2.5), with uncertainty |
|---|---|---|---|
| **S1** (`validation/S1.json`, 2026-09-14): bit-string proxy noise (`skqd.noise.corrupt_shots`: clean with prob. $f$, else half uniform garbage, half Poisson(2) flips; $p_{ro}=0.01$) at $f=0.1$, $2\times10^5$ shots per sector; recall 1.0 / 0.989; Weinstein $[-5.6565,-5.6023]$ / $[-3.9088,-3.8251]$; $M_B\in[1.6935,1.8314]$ | not a circuit simulation | `C4_F4_*` (E7(0.10), $2\times10^5$ per sector, circuit-level noise) | $\Delta$recall, $\Delta|B|$, $\Delta(E_R-E_0)$, $\Delta$ widths (Weinstein and KT), $\Delta M_B$ interval ends; new: bootstrap; old: `no_old_uncertainty` (one seed) |
| **S3** (`validation/S3.json`, job 58771538): E8 on IR-L3-RZZ, $B=0$, 32 × 100 shots, seed 11; yield 0.2172 (695/3200), recall 0.523, 0.01987 s/shot, util 30.0 %, peak 1 783 MiB; criterion NOT evaluated | GPU throughput calibration | `C4_FCELLS_B` (faithful 3 200-shot redo) and `C4_F8_*` (criterion at $2\times10^5$) | yield (binomial band), recall, s/shot per ladder point, utilisation, peak memory; then the criterion verdict itself (new) |
| **S3_smoke** (`validation/S3_smoke.json`): $B=1$, 12 × 2 shots, laptop CPU, recall 0.0737 | pipeline smoke | `C4_F8_B1*` | superseded: report the $2\times10^5$ criterion; the 24-shot number has no comparison value (say so) |
| **L4_p2_1e-3 / L4_p2_3e-3** (`validation/L4_p2_*.json`) | **2x2** dense circuits (35 670 CZ), not 2x3 (`title`: "Aer noise-model sampling at 2x2") | **not redone** | state in the report that they are 2x2 |
| **Q0P_2x3 A6 dry run** (`data/quantinuum/q0p_stages/predict.json dryrun`, `validation/Q0P_2x3.json` Q6): E1 on NAT-O0, `B0_ref25_k1` + `B1_ref57_k1`, 140 shots each, laptop CPU; 64 hits / 280; $f_{\rm hit}=0.2502$ [0.1927, 0.3195]; $P(\ge64\,|\,{\rm fault\text{-}free\ only})=0.0028$ | gate-only path check | `C4_FCELLS_A` cell E1 × O0 (the Stage-E circuits) **plus** the two A6 circuits at 800 shots each in the same cell | $\Delta f_{\rm hit}$ with both intervals; GPU vs CPU Aer of the same model (statistical agreement only: different RNG streams); hits vs the CF_traj prediction (P11) |
| **CF_traj** (`validation/CF_traj.json`, `data/cf_trajectories/r_nc.json`): $r(10^{-3})$ 1.089 [1.050, 1.136] / 1.052 [0.987, 1.126] / 1.115 [1.036, 1.220] / 1.042 [1.001, 1.122]; pooled 1.069 [1.029, 1.115]; $r_{nc}=1.115$; K = 720/240/240/120 | CPU trajectories | `C4_CF` (K = 2 000 per arm) | $\Delta r$ per arm and pooled with both intervals; new $r_{nc}$; **owner item** if the new pooled interval excludes 1.115's derivation (the campaign statistic depends on it; no verdict is edited) |
| **CV_2x3_plan** (`validation/CV_2x3_plan.json`): proxy at $0.7f$, seeds 20260914/1/2, $f=0.05/0.10/0.15$; CV1-CV5 values per seed (Block (q) of the full report) | proxy emulation of the plan | `C4_F5_*` (E7(0.07), $f=0.10$ plan: like-for-like) and `C4_F1_*`/`F4_*` (device-rate / matched 0.10) | per criterion: $\Delta(E_R(N)-E_0)$, $\Delta$ width at $N/2$ and $N$, $\Delta W$, $\Delta$ CV4 margin, CV3 $\Delta E_{4\to5}$; old uncertainty = the spread over the 3 seeds (half-range/1.96 as $\sigma$, labelled `seed_spread`) |
| **Q0P_2x3_plan P3** (`validation/Q0P_2x3_plan.json`): emulated recall of $S_{999}$ at $f=0.10$, clean fraction $0.7f$: 0.953/0.977/0.953 ($B=0$), 0.947/0.958/0.958 ($B=1$) | proxy | `C4_F5_*` | $\Delta$recall vs the 3-seed spread |
| **K0** (`validation/K0_2x3_2x4.json data.2x3.live`): $f_{\rm gates,layout}=1.671\times10^{-5}$, idle-aware $1.66\times10^{-15}$ (echo) / $5.20\times10^{-35}$ ($T_2^*$); **K1 prereg** (`data/hardware/K1_2x3_prep/prereg_99035ef05c36019e.json`): 1.37 expected hits per circuit at $10^5$ (no idle) / 0.0954 (idle-aware ends); **K1 measured** (`validation/K1_2x3_fpilot.json`): 0 / 0 hits, 58 / 45 accepted of $10^5$ | analytic model + hardware | `C2_GATE`, `C2_ECHO`, `C2_STAR`, `C2_XY4`, `C2_COH` | simulated hits and accepted counts (scaled to $10^5$) vs the analytic K0/K1 numbers (Poisson bands) and vs the measured 0/0 and 58/45 (two-sided Poisson probabilities); the "acceptance structure" (distinct strings, rejection reasons) vs K1's; no $f$ point estimate is claimed from class 2 (an upper bound only: at $f\sim10^{-5}$, $10^5$ shots give $\sim1$ expected hit) |
| **S2D 2x3 declared-model $f$** (`validation/S2D.json data.2x3`): mean $f=0.0534$ (0.0817 with virtual Rz) at $\epsilon_2=10^{-3}$ | analytic | `C4_FCELLS_B` E8 cell and E7 cells | $f_{\rm hit}$ vs the analytic $f$ (the near-clean excess, expected $r\approx1.07$) |

The comparison table in `reports/C33_campaign_report.md` has one row per line above, generated from the JSONs
named here and the new ones, with $\Delta$, $\sigma$, verdict.

---

## 7. "What to add where" — the owner's part (exact lines)

The jobs can run simultaneously only after these three things exist on Perlmutter.  Facts: the NERSC policy table
(`docs.nersc.gov/jobs/policy/`, read 2026-10-06) gives the GPU `shared` QOS "Max nodes 0.5, max time 48 h, submit
limit 5000, **run limit –**" and "GPU jobs in the shared QOS may request 1 or 2 GPUs"; i.e. NERSC imposes **no
per-user running-job cap** on shared-QOS GPU jobs — the one-job-at-a-time limit is the project's own poller.
Charge $C=\tfrac{G}{4}\,t$ node-hours per job ($G=1$).

### 7a. `~/skqd-ci/allowed_jobs` — append these 33 lines (file `ci/allowed_jobs.campaign33` in the repo is identical)

```
C1_IDEAL     00:30:00 1
C2_CAL       00:45:00 1
C2_GATE      01:00:00 1
C2_ECHO      01:00:00 1
C2_STAR      01:00:00 1
C2_XY4       01:00:00 1
C2_COH       01:00:00 1
C3_AER       00:30:00 1
C3_LE        01:00:00 1
C3_SEL       01:00:00 1
C4_FCELLS_A  01:00:00 1
C4_FCELLS_B  01:00:00 1
C4_F1_B0     01:00:00 1
C4_F1_B1     01:00:00 1
C4_F2_B0     01:00:00 1
C4_F2_B1     01:00:00 1
C4_F3_B0     01:00:00 1
C4_F3_B1     01:00:00 1
C4_F4_B0a    01:00:00 1
C4_F4_B0b    01:00:00 1
C4_F4_B1a    01:00:00 1
C4_F4_B1b    01:00:00 1
C4_F5_B0     01:00:00 1
C4_F5_B1     01:00:00 1
C4_F6_B0     01:00:00 1
C4_F6_B1     01:00:00 1
C4_F7_B0     01:00:00 1
C4_F7_B1     01:00:00 1
C4_F8_B0a    01:00:00 1
C4_F8_B0b    01:00:00 1
C4_F8_B1a    01:00:00 1
C4_F8_B1b    01:00:00 1
C4_CF        01:00:00 1
```

Command on Perlmutter (after the pull of 7c): `cat $SCRATCH/su2qc-skqd/ci/allowed_jobs.campaign33 >> ~/skqd-ci/allowed_jobs`.
No 2-GPU line: S3 measured 30 % mean GPU utilisation and L4 15 %, so E(p) $\ge0.7$ cannot be expected and has
not been measured (RUNBOOK "Measure before scaling").

### 7b. `~/skqd-ci/ci.conf` — two values

```
MAX_JOBS_PER_DAY=24
MAX_CONCURRENT=4
```

(24 per UTC day lets the 33 jobs finish in 2 days; 4 concurrent keeps the worst-case charge at
$4\times\tfrac14\times1$ h $=1$ node-hour per hour and the daily cap at $24\times\tfrac14\times1$ h $=6$ node-hours.)
The installer is changed (7c) to create `ci.conf` only if it does not exist and to print any key it would have
added, so a re-install never resets these; if the owner prefers to keep the installer as is, edit the two lines
after running it.

### 7c. The poller change (the agents commit it; the owner reviews and installs)

Specification of the new `ci/poll.sh` (same file, same hourly scrontab, every existing safety property kept):

1. **Requests** are files `ci/requests/<NNN>-<TOKEN>.txt` (first non-comment line = the token; the rest a nonce
   comment), written by `scripts/ci_request.sh TOKEN [TOKEN ...]` in ONE commit; the legacy single
   `ci/request.txt` is still honoured as one more request.  A request is identified by `<path>@<commit that last
   touched it>`; consumed identities are appended to `~/skqd-ci/consumed` — **each request runs once**; re-requesting
   = a new commit touching the file (the nonce line), as today.
2. **Concurrency**: `~/skqd-ci/running/<jobid>` holds the 5 fields the old `current` held; harvest loops over all
   of them (copy `validation/` and `reports/` of each snapshot, one commit per harvested job, `ci/status/<TOKEN>.json`
   + the legacy `ci/status.json` updated with the latest event); submit while `count(running) < MAX_CONCURRENT`
   (default 1 when the variable is absent, i.e. today's behaviour) and the daily cap holds, in file-name order.
3. **Allowlist**: exact token match as today (`awk '$1==t'`), unknown tokens refused and reported in
   `ci/status/<TOKEN>.json`; resources from the allowlist line only; GPUS forced to 1 unless the line says 2.
4. **Daily cap**: `MAX_JOBS_PER_DAY` counted in `submitted.log` as today.
5. **Snapshot**: `git archive <commit>` per job as today; the job file is `jobs/gate.sbatch` (or `smoke.sbatch`).
6. **Harvest safety**: harvests happen before submissions; a rebase conflict aborts the run with the same message.
7. `scripts/ci_check.sh` lists every request file's state (pending / submitted / done / refused) from `ci/status/`.

`tests/test_ci_poller_sim.py` runs the real `ci/poll.sh` in a temp dir with stub `sbatch` / `squeue` / `sacct` /
`git`-remote (a bare repo) and asserts: unknown token refused; 5 requests with MAX_CONCURRENT=2 -> 2 submitted,
then the next 2 after harvest; daily cap stops submission; the same request is never submitted twice; the snapshot
commit is the requested one; the legacy `ci/request.txt` path still works with MAX_CONCURRENT absent.

Owner's review-and-install (on Perlmutter, after the single push):

```bash
cd $SCRATCH/su2qc-skqd && git pull
git log --oneline -3 -- ci/poll.sh ci/install_skqd_ci.sh jobs/gate.sbatch
git diff HEAD~1 -- ci/poll.sh ci/install_skqd_ci.sh jobs/gate.sbatch      # review (the diff of the campaign commit)
bash ci/install_skqd_ci.sh                                                 # backs up the old poll.sh; ci.conf kept if present
cat ci/allowed_jobs.campaign33 >> ~/skqd-ci/allowed_jobs
nano ~/skqd-ci/ci.conf                                                     # MAX_JOBS_PER_DAY=24, MAX_CONCURRENT=4
~/skqd-ci/poll.sh; echo "exit=$?"                                          # no request: prints nothing, exit 0
```

### 7d. Conda packages on Perlmutter

- **None for classes 1, 2, 4 and C3_AER.**  Everything runs on the existing `skqd` env (qiskit 1.4.3 + qiskit-aer-gpu
  0.15.1); pytket is never imported on the CI (QPY v13 artefacts are committed).
- **`C3_LE` only** (a separate env; it must not touch `skqd` because `quantum-pecos` 0.8.0.dev8 requires `numpy<2.0`
  while `skqd` has numpy 2.5.3 — PyPI metadata read 2026-10-06):
  ```bash
  module load python
  conda create -n skqd-pecos python=3.12 -y
  conda activate skqd-pecos
  pip install "numpy<2" "pytket~=2.17" "pytket-quantinuum[pecos]==0.59.3"
  python -c "from pytket.extensions.quantinuum import QuantinuumBackend; from pytket.extensions.quantinuum.backends.api_wrappers import QuantinuumAPIOffline; print(QuantinuumBackend(device_name='H2-1LE', api_handler=QuantinuumAPIOffline()))"
  ```
  The executor's laptop pre-check (A6) decides whether `C3_LE` is requested at all; the owner creates the env only
  if `data/campaign33/engines.json` says `keep`.
- **`C3_SEL` only** (optional, third env, `numpy~=2.0`): `conda create -n skqd-selene python=3.12 -y && conda
  activate skqd-selene && pip install "selene-sim==0.3.4"`; the QIR files are committed by the executor, so no
  pytket is needed here either.  Same keep/drop rule.
- `jobs/env/C3_LE` contains `skqd-pecos`, `jobs/env/C3_SEL` contains `skqd-selene` (A1); every other token uses `skqd`.

### 7e. Order

1. Agents (this prompt, milestone A): build, freeze, test, commit locally; LOG row.  **Nothing is pushed.**
2. Owner: approves ONE push of that commit (coordinator pushes).
3. Owner on Perlmutter: 7c (pull, review, install), 7a (append allowlist), 7b (ci.conf), 7d (envs, only if kept).
   Run `~/skqd-ci/poll.sh` once by hand (exit 0).  Tell the coordinator.
4. Agents: `scripts/ci_request.sh C1_IDEAL C3_AER C2_CAL C4_FCELLS_A` (one commit, one push), then the remaining
   tokens in the order of 1.5 (the poller takes 4 at a time; 24 per UTC day).
5. Harvests arrive as CI commits; agents pull, read, assemble, report (milestone D), commit, no push without the owner.

---

## 8. Escalation and STOPs

- Any frozen base family (IR-L0, NAT-O0, IBM-T3) failing the exactness bar on the laptop: **STOP**, write
  `validation/BLOCKED.md` (a signed circuit would be wrong — rule 3).
- C1/C3_AER P1/P2 FAIL on the CI (laptop exact, CI not): a qiskit-1.4.3 QPY/`unitary` issue — fix the freeze
  (e.g. decompose `unitary` to the basis at level 0 on the laptop and re-verify), max 3 attempts, then BLOCKED.
- $E_R<E_0-10^{-9}$ anywhere: STOP (variational violation = decoder or basis bug).
- P11 FAIL (the CF_traj prediction misses the direct Aer sampling by more than the Poisson band): STOP and report —
  it contradicts a PASSed gate.
- New $r_{nc}$ outside the old pooled interval: owner item in the report (no criterion changes by this prompt).
- C2 Kraus vs PTA disagreement: production on Kraus only; if Kraus is too slow for $\ge10^4$ shots per circuit in
  50 min, run what fits and report the shot count — never extrapolate.
- Installation failures for `skqd-pecos` / `skqd-selene` on the laptop: drop the token, record the pip output in
  `data/campaign33/engines.json`; never fake a result (rule 7).
- Three CI failures in a row on one token -> `prompts/BLOCKED_C33.md`.
- Walltime overruns: the job self-reduces shots; a token whose production shots had to fall below the plan of
  record is re-split into a/b halves in a follow-up prompt — not silently accepted.

## 9. Do-not-retry (already known)

- qiskit level 3 on these circuits as an "exact" variant (K0: $4.9\times10^{-5}$) — information only unless it passes.
- pytket level 2 with measurements in the circuit (Q0P: Rz-before-measure removed, $\max|\Delta\psi|=0.585$).
- Extrapolating L4's 12-qubit 19.8x speed-up to 20 qubits (prompts/18; S3 measured the 20-qubit rate instead).
- `batched_shots_gpu` alone at 20 qubits (ignored above `batched_shots_gpu_max_qubits=16`); raise the option
  explicitly and measure.
- Writing QPY at the laptop's default version (v17 is unreadable by qiskit 1.4.3).
- Requesting 2 GPUs or a whole node (no E(p) measurement exists).
- Kraus thermal relaxation on the laptop CPU at 21 qubits for production (140.6 s/shot).

## 10. Outputs

- Code: `scripts/campaign33.py`, `src/skqd/campaign33/{noise,stats,circuits,cv}.py`, `scripts/gate_tokens.json`,
  `scripts/run_gate.py` (token hook), `jobs/gate.sbatch` (env hook), `jobs/env/*`, `ci/poll.sh`, `ci/install_skqd_ci.sh`,
  `scripts/ci_request.sh`, `scripts/ci_check.sh`, `ci/allowed_jobs.campaign33`, `ci/requests/` (empty, with a README).
- Tests: `tests/test_campaign33_{tokens,freeze,noise,stats,driver}.py`, `tests/test_ci_poller_sim.py`; `pytest -q
  tests` and `python scripts/check_package.py` pass; pins unchanged (record them).
- Artefacts: `data/campaign33/circuits/**` (QPY v13 + manifests + index), `data/campaign33/engines.json`,
  `data/campaign33/qir/*.ll` (if Selene kept).
- Results (after milestone C): `validation/<TOKEN>.json` × 33, `reports/<TOKEN>.md` × 33, `results/campaign33/**`
  (npz; compact), `validation/C33_campaign.json`, `reports/C33_campaign_report.md`, `validation/gates.md` rows,
  `reports/PROJECT_STATUS.md` paragraph, LOG rows, `graphify update .`.
- Git: local commits only; push only on the owner's word; 0 QPU s, 0 HQC.

# The 2x3 four-class simulation campaign on Perlmutter — plan for the owner (2026-10-06)

Planner: Fable 5.1 (high).  Git commit at writing: `b25f03f` (the report of 2026-10-06).  Prompt in force for
the executor: `prompts/33_2x3_four_class_perlmutter_campaign.md`.  Planner arithmetic:
`scratch/planner/campaign33_sizing_20261006.{py,json}` (every number labelled "planner arithmetic" below comes from
that file; every other number names its JSON or the web page and the date it was read).  QPU seconds and HQC spent
by this plan: 0 and 0.

## 1. What was asked

Verbatim (owner, 2026-10-06): "I want you to do a couple of things and make me a report based on that: 1. 2x3 runs
on qiskit without any noise error or optimization 2. 2x3 runs on qiskit with ibm noise 3. 2x3 runs on qiskit with
quantinuum based simulators, no error or optimization 4. 2x3 runs on qiskit with quantinuum based simulators with
varied errors and optimizations — optimizations can be qiskit side or not, you decide, mention which class of noise,
errors and optimizations are used. Use different techniques of optimizations. If any of this runs are already done,
redo them and calculate the difference you get for your old results that have already been done. All of this runs
can be done on perlmutter, give me what to add where first so that all these runs can be simultaneously parallely
submitted to perlmutter for results."

Jargon used below, defined once: a **shot** is one run of a circuit ending in one measured 20-bit string; the
**clean fraction** $f$ is the probability that a shot carries no error at all; $f_{\rm hit}$ (reference-hit
fraction) is the project's estimator of the fraction of shots that sample the ideal output, read off the count of
the circuit's most probable ideal string; $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ with the near-clean correction
$r_{nc}=1.115$ (`data/cf_trajectories/r_nc.json`); the **decoder** accepts a measured string only if it is a valid
gauge-invariant configuration of the right sector; $B_{\rm all}$ is the set of accepted configurations plus the
reference configurations; the **Ritz energy** $E_R$ is the lowest energy of the Hamiltonian restricted to
$B_{\rm all}$ (never below the true $E_0$); the **Weinstein** and **Kato-Temple** certificates are rigorous error
bars on $E_R$; **recall of $S_{999}$** is the fraction of the states carrying 99.9 % of the exact ground state that
$B_{\rm all}$ contains; **CV0-CV5** are the convergence-and-coverage criteria of `prompts/30`/`31`; **QPY** is
Qiskit's binary circuit file format (version 13 is the newest that Perlmutter's qiskit 1.4.3 can read);
**Aer** is Qiskit's simulator; a **statevector** simulation stores all $2^{20}$ amplitudes; **depolarizing** noise
replaces the state by the fully mixed state with probability $p$; **thermal relaxation** is the loss of energy
($T_1$) and phase ($T_2$) of an idle or gated qubit; **Pauli twirling** replaces a general channel by a random
Pauli error with matched probabilities; the **shared QOS** is the Perlmutter queue that gives one or two GPUs of a
four-GPU node, charged as $G/4$ of a node per hour; a **token** is one allow-listed job name in the project's
CI poller (the hourly script on Perlmutter that pulls this repository and submits jobs).

## 2. What I did (planner actions)

1. Read the CI files (`ci/poll.sh`, `ci/install_skqd_ci.sh`, `jobs/gate.sbatch`, `scripts/run_gate.py`),
   `RUNBOOK.md`'s engine policy, `SKQD-CI-SETUP.md`, the full report of 2026-10-06 and the gate JSONs of every
   earlier 2x3 simulation; oriented in the code with `graphify` (sampling path `sample_many`, the S3 gate, the
   CV gate, the K1 build, the Quantinuum conversion `pytket_to_ir`, the scheduled-Aer path).
2. Fetched and read (2026-10-06): the NERSC queue policy page; the Qiskit 1.4 QPY and preset-pass-manager pages;
   the Aer pages for `NoiseModel.from_backend`, `RelaxationNoisePass`, `thermal_relaxation_error` and the
   `AerSimulator` GPU options; the Quantinuum emulator noise-model page and the H2 / Helios emulator parameter
   pages; the pytket-quantinuum API and changelog (local emulator `H2-1LE`, `QuantinuumAPIOffline`); the Selene
   overview, GitHub README and PyPI metadata; PyPI metadata of `qiskit-aer-gpu` 0.15.1, `pytket-qiskit` (0.66.0 and
   0.78.0), `pytket-quantinuum` 0.59.3, `pytket-pecos` 0.3.3, `quantum-pecos` 0.8.0.dev8; the Geller-Zhou Pauli
   twirling paper (Phys. Rev. A 88, 012314, arXiv:1305.2021).
3. Did the sizing arithmetic and the matched-$f$ error rates in `scratch/planner/campaign33_sizing_20261006.py`
   (it reproduces the device table's $f_{\rm gate}$ for H2-2 to $2.5\times10^{-7}$ and its $\epsilon_2$ for $f=0.1$
   to $7.6\times10^{-10}$).
4. Wrote `prompts/33_2x3_four_class_perlmutter_campaign.md` for `executor-opus` (high): code, frozen circuit
   artefacts, the 33 job tokens, the noise models with their sources, the statistics, the comparison table, the
   poller change and its test, the STOPs, "no push without the owner".

## 3. The campaign (what will run), in plain words

Everything runs on Qiskit Aer on one A100 GPU per job, using the **same signed 2x3 circuit family** (44 circuits,
20 qubits, 2 158 two-qubit gates each, `data/quantinuum/circuits_2x3/`, gate `Q0P_2x3`) and, for the IBM class, the
two circuits that actually flew on `ibm_kingston` on 2026-10-06 (5 659 routed CZ each, `data/hardware/K1_2x3_prep/`).
No circuit, bar, criterion constant or convention changes.

### 3.1 Class 1 — no noise, no optimisation (token `C1_IDEAL`)

The circuits exactly as built (no transpiler pass at all: Aer executes the structured gates natively), the
Quantinuum-native frozen circuits (pytket "level 0" = no optimisation), and the IBM-routed circuits, each checked
against the exact Krylov state to the project's bars ($\max|\Delta\psi|<10^{-10}$, leakage $<10^{-9}$), then sampled
without noise at the plan-of-record shots and at $2\times10^5$ shots per sector.  This gives the **$f=1$ reference**
for every statistic (support, recall, $E_R$, certificates) and a per-state check that the sampled frequencies agree
with the exact probabilities (a $5\sigma$ band: at most ~9 000 tested states, so a failure is a bug, not chance).

### 3.2 Class 2 — IBM noise (tokens `C2_CAL`, `C2_GATE`, `C2_ECHO`, `C2_STAR`, `C2_XY4`, `C2_COH`)

The noise is built from the **recorded `ibm_kingston` calibration of 2026-10-06** (`data/hardware/K0_prep/
ibm_kingston_full_20261006T0652Z.json`, the record the K1 job was preregistered on) — not from a stock fake
backend.  Noise classes, stated: **depolarizing** gate error on every CZ / one-qubit gate; **thermal relaxation**
($T_1$, $T_2$) during every gate (`C2_GATE`, the unscheduled "gate-only" model) and, in the idle-aware cells, during
every explicit idle window of the scheduled circuit (`C2_ECHO` at the record's Hahn-echo $T_2$; `C2_STAR` at the
free-induction $T_2^*=0.174\,T_2^{\rm echo}$ measured by gate H0_diag); **readout confusion** per qubit;
**coherent over-rotation** of every $x$ pulse by the $\epsilon_q\approx0.015$-$0.020$ rad that the H0_ddrep pulse
trains measured (`C2_COH`).  The XY4 dynamical-decoupling cell **is included** (`C2_XY4`: the T3 circuits exactly as
flown, with their 2 408 / 2 404 pulses) but is labelled information: Aer's relaxation on an idle window is
memoryless, so a simulator cannot show a decoupling gain (the H0_ddrep dry run saw ratios at the null value).
**Not modelled** (and said so in every JSON): ZZ crosstalk, measurement crosstalk, leakage.

Why a calibration job first: Aer represents thermal relaxation as a Kraus channel when $T_2>T_1$, which is why one
noisy 21-qubit shot cost 140.6 s on the laptop CPU in the K1 dry run.  `C2_CAL` measures, on the GPU, the Kraus
representation against its Pauli-twirled version (the stochastic-Pauli form with
$p_X=p_Y=\tfrac14(1-e^{-t/T_1})$, $p_Z=\tfrac12(1-e^{-t/T_2})-\tfrac14(1-e^{-t/T_1})$, exactly the per-window error of
`src/skqd/idle.py`; Geller & Zhou 2013) and sizes the five production cells to 50 min each.  What class 2 can and
cannot say: the model's own prediction is $f\approx1.7\times10^{-5}$ without idle time and $\sim10^{-15}$ with it
(`validation/K0_2x3_2x4.json data.2x3.live`), so $10^5$ shots give about one expected reference hit; the runs test
**consistency** with the measured K1 result (0 and 0 hits, 58 and 45 accepted of $10^5$) and with the K0/K1
analytic predictions through Poisson probabilities — they do not measure a point value of $f$.

### 3.3 Class 3 — Quantinuum-based, no error, no optimisation (tokens `C3_AER`, `C3_LE`, optional `C3_SEL`)

Honest statement of what exists locally: Quantinuum's vendor emulators (H2-2E, Helios-1E) run only on Nexus with an
account, which the project does not have.  What runs without an account: (i) **the Quantinuum-native circuits on
Qiskit Aer** (`C3_AER`, the "on qiskit" path the owner asked for; noiseless; same checks as class 1); (ii) the
**pytket-pecos local emulator `H2-1LE`** (`pip install pytket-quantinuum[pecos]`, `QuantinuumAPIOffline`, "no
credentials required", "currently this emulation is noiseless" — pytket-quantinuum docs read 2026-10-06), a CPU
engine in its own conda env, used as a cross-check on the four Stage-E circuits (`C3_LE`); (iii) optionally
**Selene** (Quantinuum's open-source emulator, `pip install selene-sim`, inputs Guppy/HUGR and QIR, QuEST
statevector, `IdealErrorModel` — docs and GitHub read 2026-10-06) on the QIR export of the same four circuits
(`C3_SEL`).  Both (ii) and (iii) are kept only if a laptop pre-check installs them and shows a usable speed; the
result is recorded either way (`data/campaign33/engines.json`).

### 3.4 Class 4 — Quantinuum-based with varied errors and optimisations

**Errors** (all on Aer, all gate-level depolarizing with asymmetric readout and virtual noiseless $R_z$ unless stated):

| scenario | parameters | source |
|---|---|---|
| E1 H2-2 (performance-validation rates; = the project's A6 model) | $\epsilon_2=8.3\times10^{-4}$, $\epsilon_1=2.8\times10^{-5}$, readout $6.7\times10^{-4}/1.2\times10^{-3}$ | `data/quantinuum/devices_20261002.json`, `scripts/quantinuum_submit.py A6_NOISE` |
| E2 Helios-1 (PV rates) | $\epsilon_2=7.9\times10^{-4}$, $\epsilon_1=3.0\times10^{-5}$, readout $4.8\times10^{-4}$ | same file |
| E3 **H2-2E emulator parameter set (2025-07-16)** with the emulator's **angle-dependent** two-qubit error $p_2(\theta)=(1.518\,|\theta|/\pi+0.241)\,p_2$ | $p_2=1.29\times10^{-3}$, $p_1=7.3\times10^{-5}$, readout $9\times10^{-4}/1.8\times10^{-3}$, init $4\times10^{-5}$ | docs.quantinuum.com emulator pages, read 2026-10-06 |
| E4 **Helios-1E emulator set (2025-11-18)** | $p_2=8\times10^{-4}$, $p_1=2.5\times10^{-5}$, readout $10^{-6}$, init $5\times10^{-4}$; its **leakage** terms cannot be represented in Aer (recorded as not modelled) | same |
| E5a/b/c memory (transport/idle) dephasing | Pauli-$Z$ per qubit per two-qubit layer with probability $0.0028\ {\rm s^{-1}}\times t_{\rm round}$, $t_{\rm round}=0.5/1.1/4.4$ ms (the project's low/mid/high scenarios; 1 925 layers) | emulator `linear_dephasing_rate`; `data/quantinuum/devices_20261002.json memory_model` |
| E6a/b/c scaled | E1 with every probability $\times0.5$, $\times2$, $\times4$ | the emulator's `scale` parameter |
| E7 matched-$f$ | E1 with $\epsilon_2$ set so the gate-only clean fraction is $0.05/0.07/0.10/0.15$: $\epsilon_2=1.3390\times10^{-3}/1.1833\times10^{-3}/1.0182\times10^{-3}/8.3048\times10^{-4}$ | planner arithmetic (checked against the device table) |
| E8 the gate-S3 declared model (noisy $R_z$) | $\epsilon_2=10^{-3}$, $\epsilon_1=10^{-4}$, readout $2\times10^{-3}$ | `validation/S3.json` |

**Optimisations** (distinct techniques; a variant is **allowed** only if all 44 optimised circuits still meet the
exactness bars, otherwise it is "information only"):

| id | technique | tool |
|---|---|---|
| O0 | none (frozen level 0) | — |
| O1 | peephole resynthesis of two-qubit blocks + one-qubit squashing, applied before the measurements are appended (`FullPeepholeOptimise` to TK2, rebase to {Rz, PhasedX, ZZPhase}, `RemoveRedundancies`, `SquashRzPhasedX`) | pytket |
| O2 | adjacent inverse-gate cancellation (qiskit preset level 1) | qiskit |
| O3 | commutation-based gate cancellation (qiskit preset level 2) | qiskit |
| O4 | two-qubit peephole / unitary resynthesis (qiskit preset level 3) — expected to fail the bar (K0 found $4.9\times10^{-5}$) | qiskit, information unless exact |
| O6 | approximate synthesis (`KAKDecomposition(cx_fidelity=0.999)`) — inexact by construction | pytket, information only |

Not built: re-ordering the signed term order for parallelism (owner decision D5 of `prompts/27` is pending) and
dynamical decoupling (no idle term in the trapped-ion gate model; the memory term is an incoherent $Z$ flip that
decoupling cannot refocus).

**How class 4 is organised so it stays affordable.** Cheap **f-cells** (the four Stage-E circuits at
800/800/200/200 shots = 2 000 shots, about 40 GPU-seconds each) cover the whole error × optimisation grid
(75 cells in two jobs, `C4_FCELLS_A/B`) and give $f_{\rm hit}$, $\hat f_{\rm ideal}$, $f_0$ and the accepted
fraction everywhere.  Full **SKQD runs** at the plan-of-record shots (`validation/CV_2x3_plan.json`: $B=0$ at
$s=1$, $B=1$ at $s=2$) — with order-kept shot sequences so the CV criteria can be read on nested prefixes — are
done for the main scenarios only: `F1` H2-2, `F2` Helios-1, `F3` H2-2E set, `F4` matched $f=0.10$ at $2\times10^5$
shots per sector (the S1 redo), `F5` matched $f=0.07$ at the $f=0.10$ plan (like-for-like with the CV_2x3_plan
emulation, which sampled at $0.7f$), `F6` memory mid, `F7` the best exact optimisation, `F8` the gate-S3 model
at $2\times10^5$ per sector (the S3 recall criterion, evaluated for the first time).  `C4_CF` redoes the
trajectory decomposition on the GPU with 2 000 trajectories per arm (the CPU run had 720/240/240/120).

Outputs for every run: $f_{\rm hit}$ (Garwood interval), $\hat f_{\rm ideal}$, analytic $f_0$, accepted fraction
(Wilson), $|B_{\rm all}|$, recall of $S_{99}$ and $S_{999}$, $E_R-E_0$ with the Kato-Temple ($B=0$, exact $E_1$) and
Weinstein ($B=1$) certificates, CV0-CV5, bootstrap intervals (2 000 resamples, seed 33), the GPU telemetry the
RUNBOOK requires, and — for every earlier result — the difference $\Delta=x_{\rm new}-x_{\rm old}$ with
$\sigma=\sqrt{\sigma_{\rm new}^2+\sigma_{\rm old}^2}$ and a verdict (consistent / tension / inconsistent / no old
uncertainty).

## 4. The old 2x3 results that get redone, and what each comparison is

| old result (file) | what it was | redo | the difference that is computed |
|---|---|---|---|
| S1 (`validation/S1.json`): bit-string proxy noise at $f=0.1$, $2\times10^5$ shots per sector; recall 1.0 / 0.989; Weinstein $[-5.6565,-5.6023]$ / $[-3.9088,-3.8251]$; $M_B\in[1.6935,1.8314]$ | not a circuit simulation | `C4_F4_*` (matched $f=0.10$, circuit-level noise, $2\times10^5$) | $\Delta$ recall, $\Delta|B|$, $\Delta(E_R-E_0)$, $\Delta$ certificate widths, $\Delta M_B$ ends; old value has no interval (one seed) |
| S3 (`validation/S3.json`, Perlmutter job 58771538): $B=0$, 32 × 100 shots, yield 0.2172, recall 0.523 at 3 200 shots, 0.01987 s/shot, criterion not evaluated | throughput calibration | faithful 3 200-shot redo (same seed) inside `C4_FCELLS_B`; the criterion at $2\times10^5$ in `C4_F8_*` | yield and recall (binomial bands), s/shot per ladder point, utilisation, peak memory; then the S3 verdict itself (new) |
| S3_smoke (`validation/S3_smoke.json`): $B=1$, 24 shots, recall 0.0737 | pipeline test | `C4_F8_B1*` | superseded; the 24-shot number has no comparison value (stated) |
| L4_p2_1e-3 / L4_p2_3e-3 | **2x2**, not 2x3 (`title`: "Aer noise-model sampling at 2x2") | not redone | stated in the report |
| Q0P A6 dry run (`data/quantinuum/q0p_stages/predict.json`): 2 circuits × 140 shots on the laptop CPU, 64 hits, $f_{\rm hit}=0.2502$ [0.1927, 0.3195] | gate-only path check | the same cell at 800 shots per circuit in `C4_FCELLS_A` | $\Delta f_{\rm hit}$ with both intervals; CPU-vs-GPU agreement of the same model (statistical); the hit count against the CF_traj trajectory prediction (a physics pass criterion) |
| CF_traj (`validation/CF_traj.json`): $r$ per arm 1.089 / 1.052 / 1.115 / 1.042, pooled 1.069 [1.029, 1.115], $r_{nc}=1.115$ | CPU trajectories | `C4_CF` (2 000 per arm) | $\Delta r$ per arm and pooled; new $r_{nc}$; an owner item if it moves outside the old interval (nothing is edited) |
| CV_2x3_plan (`validation/CV_2x3_plan.json`): proxy at $0.7f$, 3 seeds, CV1-CV5 | proxy emulation | `C4_F5_*` (like-for-like) and `C4_F1_*` / `F4_*` | per criterion: $\Delta(E_R-E_0)$, $\Delta$ widths, $\Delta W$, $\Delta$ CV4 margin, CV3 $\Delta E_{4\to5}$; old uncertainty = the 3-seed spread |
| Q0P_2x3_plan P3: emulated recall at $f=0.10$: 0.953/0.977/0.953 and 0.947/0.958/0.958 | proxy | `C4_F5_*` | $\Delta$ recall vs the seed spread |
| K0 / K1 predictions (`validation/K0_2x3_2x4.json`, the K1 preregistration) and the K1 measurement (0/0 hits, 58/45 accepted) | analytic model + hardware | `C2_*` | simulated hits and accepted counts vs the analytic numbers and vs the measured ones (Poisson probabilities); the acceptance structure |
| S2D 2x3 declared-model $f=0.0534$ (0.0817 with virtual $R_z$) | analytic | E8 and E7 f-cells | $f_{\rm hit}$ vs the analytic $f$ (the near-clean excess) |

## 5. Size and cost (planner arithmetic from measured throughputs)

Throughput basis: 0.0198663 s per noisy 20-qubit shot on one A100 (`validation/S3.json data.cost.
seconds_per_shot_best_ladder`, job 58771538; mean GPU utilisation 30.0 %, peak memory 1 783 MiB), with a 1.25
contingency and 5 min fixed per job; the IBM class is sized by its own calibration job because its channel is
different (Kraus).  Shot totals of the noisy GPU runs: 1 561 654.  **33 jobs**, each one GPU and at most 60 min;
sum of the estimates **20.1 h** of 1-GPU walltime = **5.0 GPU node-hours** at $C=\tfrac{G}{4}t$; the allow-listed
walltimes cap it at 31.75 h = 7.9 node-hours.  Longest planned job: 46 min (a $10^5$-shot batch).  With the
proposed caps (4 concurrent, 24 per UTC day) the campaign takes **2 UTC days** of calendar time; with today's
caps (1 job at a time, 6 per day) it would take 6 days.  The two largest classes of cost are the four
$2\times10^5$-shot runs (F4 and F8: 8 jobs, 6.2 h) and the IBM cells (5 jobs, 4.2 h).

Independence: no job waits for another.  Two soft dependencies are read if present and defaulted otherwise
(the IBM production cells read `C2_CAL`'s rate; the full runs read the plan tier from the f-cells, default 0.15).

## 6. What to add where — the owner's list (exact)

Fact from NERSC (`docs.nersc.gov/jobs/policy/`, read 2026-10-06): the GPU `shared` QOS has "Max nodes 0.5, max time
48 h, submit limit 5000, **run limit –**", and "GPU jobs in the shared QOS may request 1 or 2 GPUs".  NERSC imposes
no per-user cap on the number of running shared-QOS jobs; the one-at-a-time limit is our own poller.

**(a) `~/skqd-ci/allowed_jobs` — append the 33 lines** of `ci/allowed_jobs.campaign33` (listed in full in
`prompts/33`, section 7a; format `TOKEN  MAX_WALLTIME  GPUS`, all 1 GPU, walltimes 00:30 / 00:45 / 01:00):
`cat $SCRATCH/su2qc-skqd/ci/allowed_jobs.campaign33 >> ~/skqd-ci/allowed_jobs`.

**(b) `~/skqd-ci/ci.conf`:** `MAX_JOBS_PER_DAY=24` and the new line `MAX_CONCURRENT=4`.  Worst-case charge
$4\times\tfrac14\times1$ h = 1 node-hour per hour, $24\times\tfrac14\times1$ h = 6 node-hours per day.

**(c) `ci/poll.sh` (the agents commit it; you review and install):** requests become files
`ci/requests/<NNN>-<TOKEN>.txt` (one per job, written by `scripts/ci_request.sh TOKEN [TOKEN ...]`; the old
`ci/request.txt` still works); the poller harvests every finished job, then submits up to `MAX_CONCURRENT`
pending requests per hour; unknown tokens are refused; the daily cap, the once-only rule (consumed requests are
logged by file-and-commit) and the frozen `git archive` snapshot per job are unchanged; a simulation test with stub
`sbatch`/`squeue`/`sacct` is committed.  Install:
```bash
cd $SCRATCH/su2qc-skqd && git pull
git diff HEAD~1 -- ci/poll.sh ci/install_skqd_ci.sh jobs/gate.sbatch   # review
bash ci/install_skqd_ci.sh                                              # backs up the old poller
cat ci/allowed_jobs.campaign33 >> ~/skqd-ci/allowed_jobs
nano ~/skqd-ci/ci.conf                                                  # the two values of (b)
~/skqd-ci/poll.sh; echo "exit=$?"                                       # no request: silent, exit 0
```

**(d) Packages on Perlmutter:** **none** for classes 1, 2, 4 and the Aer part of class 3 — everything runs on the
existing `skqd` env (qiskit 1.4.3 + qiskit-aer-gpu 0.15.1, whose wheel requires `qiskit>=1.1.0`; PyPI read
2026-10-06); pytket never runs on Perlmutter because the circuits are converted on the laptop and committed as QPY
v13.  Only if the laptop pre-check keeps the local Quantinuum emulator: a **separate** env (quantum-pecos
0.8.0.dev8 needs `numpy<2`, so it must not share `skqd`):
```bash
module load python && conda create -n skqd-pecos python=3.12 -y && conda activate skqd-pecos
pip install "numpy<2" "pytket~=2.17" "pytket-quantinuum[pecos]==0.59.3"
```
and, only if Selene is kept, a third env: `conda create -n skqd-selene python=3.12 -y && conda activate
skqd-selene && pip install "selene-sim==0.3.4"` (needs `numpy~=2.0`).  The job script picks the env from
`jobs/env/<TOKEN>`.

**(e) Order:** 1. agents build, freeze, test and commit locally (nothing pushed); 2. you approve one push;
3. you do (c), (a), (b), (d) on Perlmutter and run the poller once by hand; 4. agents push the request files
(`C1_IDEAL C3_AER C2_CAL C4_FCELLS_A` first, then the rest); 5. results arrive as CI commits within about two
days; the agents assemble `reports/C33_campaign_report.md` from the JSONs.

## 7. What the result will mean, and what it cannot mean

- Class 1 and 3 establish that every frozen circuit family is exact on Perlmutter's qiskit 1.4.3 and give the
  $f=1$ baselines; class 3's local emulators check that an independent Quantinuum engine agrees with Aer.
- Class 2 can only confirm or contradict the model behind the measured 2x3 NO-GO on IBM; it cannot change that
  verdict (the model predicts about one hit in $10^5$ shots; the device gave none).
- Class 4 gives, for the first time, circuit-level (not bit-string-proxy) answers to the S1, S3 and CV_2x3_plan
  questions, the sensitivity of the clean fraction to each error class and scale, and whether any exact
  optimisation reduces the two-qubit count at all (the expectation from Q0P is that it does not: pytket level 2
  also gave 2 158 ZZ).  The angle-dependent and memory terms are the emulator's published forms; the coherent
  quadratic dephasing, emission ratios, crosstalk and leakage of the vendor models are **not** reproduced and are
  listed as such — the vendor emulator (Stage E) remains the first informative number for 2x3 on Quantinuum.
- Nothing here is a device measurement; every "f" is a model value.

## 8. Decisions needed from the owner

1. Approve the one push, then do section 6 (a)-(e).  The caps `MAX_CONCURRENT=4` / `MAX_JOBS_PER_DAY=24` are my
   proposal; any smaller values only lengthen the calendar time.
2. Whether `C3_LE` (pytket-pecos local emulator) and `C3_SEL` (Selene) are wanted at all, given that they need one
   or two extra conda envs on Perlmutter; the laptop pre-check decides feasibility, you decide the effort.
3. Term-order re-ordering as an optimisation technique needs decision D5 of `prompts/27` (it touches the signed
   term order); it is excluded until decided.
4. If `C4_CF` moves $r_{nc}$ outside its old interval, whether the campaign statistic is re-signed (no verdict is
   edited by this prompt).

## 9. Problems and assumptions

- The throughput basis is a single measurement at 20 qubits on the cuStateVec per-shot path; the first job of each
  class re-measures it (ladder) and the jobs self-reduce their shots to the walltime rather than overrun, so a
  shortfall shows up as a recorded `shots_reduced_to`, never as a silent truncation.
- The IBM class may be slow in the Kraus representation; the Pauli-twirled form is used only after it agrees with
  Kraus at the calibration shots (within $3\sigma$).
- `quantum-pecos` 0.8.0.dev8 is a pre-release with a pure-Python wheel; whether its state-vector simulator is fast
  enough for 20 qubits is unknown until the laptop pre-check.
- The K1 QPY files were written by qiskit 2.5.2 and record no QPY version; they are re-written at version 13 with an
  exact round-trip check before any job uses them.
- Sources for every vendor number are the pages named above with the date read; none was measured by this
  project.

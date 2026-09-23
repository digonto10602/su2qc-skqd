# su2qc-skqd — agent operating manual

Neural-enhanced sample-based Krylov quantum diagonalization (SKQD) for SU(2) lattice gauge theory with
staggered quarks on 2×Lx ladders.  Reference document: `proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md`
(SU2QC Project 2, rev. 2, 10 Sept 2026).  Owner: Digonto (digonto10602).

## Commands

- Package check (run first on any fresh checkout): `python scripts/check_package.py`
- Tests: `pytest -q tests` (or `python scripts/run_tests_no_pytest.py` if pytest is missing)
- Cloud-verifiable gates: `python scripts/run_gate.py E1 | E2 | E3 | S1 [--quick]`
- Laptop gates: `python scripts/run_gate.py L2 | L3 | L4 | L5 [--push]` (scripts/laptop_*.py)
- Structure report for S2: `python scripts/report_circuit_structure.py`
- Everything a gate computes goes to `validation/<GATE>.json` (machine-readable) and `reports/<GATE>_*.md`
  (human-readable, generated from the same numbers).  Never type a number into a report by hand.

## Layout

- `src/skqd/` physics core (`su2, fermions, lattice, vertex, basis, hamiltonian, fullspace, codec, exact`),
  SKQD workflow (`krylov, noise, skqd, controls, ml, certification in skqd.py`), circuit layer
  (`reference_sim, circuits_ir, circuits_qiskit, circuits_cudaq`), bookkeeping (`report`).
- `scripts/` gate scripts; `tests/` pytest; `validation/` gate JSON + `gates.md` (the gate table);
  `reports/` gate reports; `data/` reference numbers; `prompts/` every prompt the planner writes;
  `proposal/` the project document; `.claude/agents/` model/effort-routed agents; `.claude/skills/gate/`.

## graphify

This package has a knowledge graph at `graphify-out/` (895 nodes, 1645 edges, 83 communities over the 116
indexed files; AST extraction only, no LLM, no API cost).  `graphify` is on the PATH
(`~/.local/share/graphify/venv`, version 0.9.53, isolated from the `coding` conda env so that the pinned
qiskit 2.5.2 / aer 0.17.2 stack is never touched).  The graph is gitignored: it is regenerated, not archived.

- For any question about where something lives or what depends on what, query the graph before grepping:
  `graphify query "<question>"` returns a scoped subgraph, usually far smaller than raw grep output.
  `graphify path "A" "B"` gives the relationship between two nodes, `graphify explain "X"` a focused
  concept, `graphify affected "X"` what a change to X reaches, `graphify god-nodes` the architectural hubs
  (currently `Model`, `Codec`, `CircuitFactory`, `Ladder`, `Basis`, `run_ir`).
- `graphify-out/GRAPH_REPORT.md` is for broad architecture review only, when query/path/explain do not
  surface enough; `graphify-out/graph.html` is the interactive view for a human.
- After changing code, run `graphify update .` to keep the graph current.  It takes seconds and costs nothing.
- `.graphifyignore` keeps the measured numbers out of the index: `data/hardware/`, the QPY circuit bundles
  and `validation/*.json` are excluded, `validation/gates.md` is not.
- **The graph is navigation, never evidence.**  It carries no gate status and no physics value.  Rule 1
  below is unchanged: every number in prose comes from `validation/*.json` or `data/*.json`.

## Rules for every agent

1. Physics first.  A gate passes only when its script writes `"status": "PASS"` — not when the prose says so.
   Numbers in prose must come from `validation/*.json` or `data/*.json`.  If a number cannot be computed
   here, say so; never estimate a value and present it as computed.
2. Conventions are fixed in `src/skqd/su2.py` (link generators `L_a = -J_a^T`, `R_a = +J_a`, matter charge
   `Q_a = psi^dag sigma_a/2 psi`, `[L_a,U] = -(T_a U)`, `[R_a,U] = +(U T_a)`), `lattice.py` (site index
   `x1*Ly + x2`, links +x/+y, `eta = i` on x-links, `(-1)^{x1+x2}` on y-links), `codec.py` (qubit layout) and
   `reference_sim.py` (qubit k = bit k, little-endian).  Do not change a convention without re-running E1–E3.
3. The manual's numbers (Tables 1–4) are reproduced by this package; any new disagreement is a bug until proven
   otherwise — stop and escalate.
4. The 30-minute rule on the laptop (i7-8750H, GTX 1060 Max-Q, 6 GB): if a run exceeds 30 minutes,
   re-parametrize (fewer shots, `--quick`, smaller sector) and record in the report what the laptop can do and
   what needs the RTX 3070 desktop, the Slurm GPU cluster, or the QPU.
5. Git: commit after every gate; `scripts/run_gate.py <G> --push` pushes on PASS.  The remote is
   `origin` = `https://github.com/digonto10602/su2qc-skqd`.
6. Model routing (see `prompts/ROUTING.md`): the planner (Fable 5.1) writes prompts and decides; executors
   (Opus) implement; runners/reviewers (Sonnet/Opus at lower effort) run gates, tests and reviews; the
   scribe (Haiku) formats reports.  Fable is invoked at `max` effort only for blocked gates or physics
   decisions, never for repetitive runs.
7. Every new step starts with a prompt file `prompts/NN_<slug>.md` written by the planner (template:
   `prompts/ESCALATION_TEMPLATE.md` for blocked gates, `prompts/README.md` for the format).  Executors
   follow the newest prompt for their step and append their outcome to `prompts/LOG.md`.

## Current status (see reports/PROJECT_STATUS.md for the full table)

Cloud-verified and reproduced on the laptop (2026-09-14): E1, E2, E3, S1 (all PASS; E1-E3 identical to the cloud
values).  Laptop gates done: L2 PASS (Qiskit = reference to 3.7e-15), L5 PASS (CUDA-Q on `qpp-cpu`; the `nvidia`
target needs compute capability >= 7.0), L3 FAIL as expected (35606 CZ per coarse step all-to-all, 55459 routed,
budget 250), L4 FAIL as expected (yield at the random-acceptance level because f = (1-p2)^35670 is zero; Weinstein
criteria PASS; noisy Aer costs 2-3.3 s per shot on this CPU, so 2x3 noisy runs need the desktop or cluster).
No GPU path on the laptop: qiskit-aer-gpu 0.15.1 is incompatible with qiskit 2.5.2.  Gate S2 (2026-09-15): exact structured circuits verified (1.9e-14); 256/618 CZ at 2x2 and 2164/5477 at 2x3 against
250/500 routed (FAIL on cost only; the controls are validity controls of the encoding, `prompts/11`).  Owner decision
(2026-09-16): combined plan, 2x2 on Heron + 2x3 exact circuits on an all-to-all ion-trap device (`prompts/12`).  Gate S2D:
2x2/Heron f = 0.125 with a FakeFez calibration (PASS; L4_fez pilot yield 0.14 vs model 0.10); 2x3 f = 0.053 at declared
eps2 = 1e-3, eps1 = 1e-4 (0.082 with virtual rz) -> S2D FAIL on f >= 0.1 and on the per-circuit shot rule, but the
operational S1 criterion holds at that f (recall >= 0.958 with 2e5 shots per sector, `data/S2D_recall_at_f.json`).
H0 preparation (prompts 13-14): gate H0P PASS (84 frozen circuits on the FakeFez patch leak-free, decoder and E0
consistency, yield model 0.82 f + (1-f) a per manual Step 4.4 within 1.3-1.75x of the simulation for r = 1, 2, 3,
confusion diagonal >= 0.977, dry-run submission + gate_H0.py PASS 9/9); S3 job packaged (`scripts/s3_device_model.py`,
`slurm/s3_2x3.sbatch`; 2x3 at 2e5 shots per sector is 180-580 CPU-hours -> RTX 3070 / cluster).  H0 session day
(prompts/15 part B, 2026-09-21): `validation/H0P_ibm_fez.json` **FAIL** 15/16 on the live calibration
20260921T2053Z -- the B=1 support came out 19 of 20, held at STOP A.  Cause and decision:
`reports/H0P_ibm_fez_escalation_20260921.md` -- the frozen plan (267/130/92) saturates B=0 from clean shots with
probability 0.0043 and B=1 with 0.0762, so criterion 3's premise was a coin flip, not a measurement.  prompts/16
part A' (2026-09-21) replaces the r = 1 shot counts by **rule D3'** (new `scripts/h0_support_plan.py`: the k = 4
circuits of each sector get N4 = the smallest multiple of 100 that gives every sector state an expected clean
count >= lambda* = 6.2958 in the r = 1 circuits alone at 0.7 x f_cal): N4 8200/19700 on the live calibration,
11700/28100 on FakeFez; gate H0P gains two shot-plan criteria (18 in all); `analyse_records` writes
`support_states_decoded` / `missing_states` / the per-state predicted-vs-observed table; the session becomes 6 jobs
(21/5/2/28/28/42 pubs) at 69.9 s of QPU execution (cap 120).  **`validation/H0P_rehearsal.json` PASS 18/18** on
FakeFez through the new sampling cache, supports 38/38 and 20/20, `missing_states == []`.  No criterion constant,
tolerance, convention or frozen circuit changed.  Session day (prompts/16 part B' and prompts/17, 2026-09-22):
`validation/H0P_ibm_fez.json` **PASS 18/18** twice, first on the calibration 20260922T0711Z and again on
20260922T1400Z after ibm_fez recalibrated (N4 6900/16800, r = 1 shots 38505/35202, supports 38/38 and 20/20,
execution estimate 66.3 s).  prompts/17 replaces the stamp guard of the preflight by **rule D9**: submission
requires identity of the calibration *content* of the frozen patch (`h0_backends.calibration_fingerprint`, the
sha256 of the 30 x 9 qubit and 54 x 4 edge leaves the prediction actually reads) and of the 84 live clean-shot
fractions to 1e-9; `scripts/h0_calwatch.py` logs the windows.  The fingerprint stayed constant through three
stamp-only updates and fired on the one real recalibration.  **Canary (2026-09-22, the only QPU spend so far:
2.0 s):** job `dapbusac505c73chv0og`, 3 pubs x 267 shots, DONE, preflight `fingerprint_match` true and the
retrieval-time record identical to the prediction's -- but **8 accepted of 267 against the preregistered >= 10
and the simulated 71**, measured f 0.0255 vs predicted 0.2195: **canary NO-GO**, the main 6-job submission is not
run (`validation/BLOCKED.md`, prompts/07 clause (b) / prompts/15 escalation B5).  **Diagnostic H0_diag
(2026-09-22, 15.0 s of QPU, 17.0 s spent in total):** the cause is idle-time relaxation, which neither
`gate_S2D.analyse_on_backend` nor the unscheduled Aer path contains -- J1 (both options off) gave 35 accepted of
2000 against a preregistered 30.8 +- 5.5 for idle relaxation and 374.5 +- 17.4 for the options hypothesis, so the
options are exonerated and D8's set is the worst of the four cells.  The re-plan (`prompts/20`) then found that the
accepted shots are mostly near-clean strings, not clean ones: 6 reference-string hits in 8267 shots against 2.02
from garbage give f_clean = 6.7e-4, so the yield inversion overstates the clean fraction 15x and "31 vs 35" did not
validate the echo-T2 model (S_eff 5.76 sits between the echo 3.32 and the T2* 7.52).  Criterion 3 is void as a
device test (garbage saturation reaches it at every planned budget).  r = 1 only at 2x2 on this device class; 2x3
on any superconducting device is dead.  **Amendment 01 items 1-3 are SIGNED (2026-09-23, commit 336a60b):** patch
selection by the idle-aware objective (`scripts/h0_patch_select.py`, worth 1.41x on the day's record and 3.31x
device-wide, a factor and not a rescue), the budget criterion read on the *scheduled* circuit with the 0.1/0.05
thresholds unchanged, and the exact circuit family kept but judged on duration.  **Gate S2D's 2x2 PASS is withdrawn
as a hardware statement** (idle-aware mean f 6.71e-03 against 0.1; `validation/S2D_idle.json` FAIL, not registered
in the gate table); `validation/S2D.json` is not rewritten and stands as the gate-only computation it was.  **L4
PASSES on the GPU** (job 58741899, 19.8x over this laptop) and the **S3 GPU calibration PASSES** (job 58771538,
0.0199 s/shot at 20 qubits, 161x over the laptop's 3.198: a 2e5-shot sector is 1.1 h instead of 178 h).  Open:
amendment items 4 (the 2x3 device -- now also needs the vendor's gate durations and T1/T2, not only error rates)
and 5 (the shot quota, whose figures scale as 1/f); the owner's nine named changes in `prompts/20`; whether H0 can
be made to fit the 583 s left on this device class.


# skqd-ci: how to run tests on Perlmutter (rules for Claude / any agent)

You have NO login to Perlmutter and must not try to get one (no ssh, sshproxy, SF API).
Perlmutter pulls this repo every hour at :07 UTC and runs at most one allowlisted job.

**Which engine a gate may use, how a GPU job is laid out, and what it must measure** are fixed by the
owner's engine and HPC policy in `RUNBOOK.md` ("Engine and HPC policy for Perlmutter runs"): exact
numpy/scipy for E1-E3 and S1, Aer-GPU for the hardware-matching gates (code must run on qiskit 1.4.3),
CUDA-Q for gate-level validation; parallelise only along k, sector, g2, lattice, shot batch, seed or
resample; every GPU job records wall time, per-phase timings, GPUs, s/shot, peak GPU memory and mean
GPU utilization in its validation JSON; more GPUs are proposed only with measured E(p) >= 0.7.

## Loop
1. Make your change, run the fast CPU tests locally, commit, push to master.
2. `scripts/ci_request.sh <TOKEN>`  - TOKEN is one of: smoke E1 E2 E3 S1 L1 L2 L3 L4 L5
3. Wait. Check with `scripts/ci_check.sh`  (exit 0 done, 2 pending, 3 refused).
   Check no more often than every 15 minutes; a job usually needs 1-3 hours round trip
   (poll interval + GPU queue). Between checks, do useful local work.
4. Read `validation/ci_gate_<TOKEN>.json` (or `validation/ci_smoke.json`) and `reports/ci-<jobid>.out`.
   Fix, push, request again.

## Limits (enforced on Perlmutter, not changeable from the repo)
- one job at a time; max 6 jobs per UTC day; walltime per token 15-60 min; 1 GPU (shared QOS)
- a request made while a job is running is picked up after that job finishes
- only the first non-comment line of ci/request.txt counts; unknown tokens are refused

## Never
- edit `ci/status.json`, `ci/poll.sh`, `reports/ci-*.out`, `validation/ci_*.json` (the CI writes them)
- request the same token again while its previous request is still pending
- request more than 3 jobs in a row without a passing result in between: stop and write
  prompts/BLOCKED_<gate>.md for the planner / the user instead
- run anything long on the laptop to "save queue time"; 30-minute rule from the package still holds

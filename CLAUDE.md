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
No GPU path on the laptop: qiskit-aer-gpu 0.15.1 is incompatible with qiskit 2.5.2.  Blocking hardware: S2-b
(structured hopping and interior-corner plaquette gates within the CZ budget, prompts/06), then S3 with a real
calibration, then H0 hardware calibration at 2x2.

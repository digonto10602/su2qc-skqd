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
`slurm/s3_2x3.sbatch`; 2x3 at 2e5 shots per sector is 180-580 CPU-hours -> RTX 3070 / cluster).  Open: owner signs
`proposal/amendment_01_devices_and_budgets.md` with the vendor's error specs for the 2x3 device; IBM backend access
for H0 (`scripts/h0_submit.py --backend <name>`); S3 production run on the desktop GPU.

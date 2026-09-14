# 01 — L1: reproduce the cloud-verified gates on the laptop
executor: runner-sonnet   effort: low
time budget: 30 min   machine: laptop (CPU only)

## Goal
Show that the laptop reproduces every number of the cloud gates E1, E2, E3 and S1 (Tables 1–4 of the manual)
before any circuit work starts.  This is the "proof of concept on the laptop" step: the whole physics core
(basis with intertwiners, dressed-site Hamiltonian, exact references, decoder, emulation, certification,
controls) runs on the CPU in minutes.

## Inputs
- `validation/E1.json, E2.json, E3.json, S1.json` and `data/references.json` from the cloud run (keep copies:
  `mkdir -p validation/cloud && cp validation/*.json validation/cloud/`)
- `reports/laptop_vs_hpc_plan.md` (expected runtimes)

## Steps
1. `python scripts/run_gate.py E1` (~2–4 min: the 160 000-dimensional kernel blocks dominate)
2. `python scripts/run_gate.py E2` (~1 min)
3. `python scripts/run_gate.py E3` (~1 min; 2x4 build ≈ 5 s)
4. `python scripts/run_gate.py S1` (~2 min; use `--quick` if the machine is busy)
5. Compare with the cloud copies: `python - <<'EOF'` … for each gate load both JSONs and print every criterion
   whose value differs by more than 1e-9 (deterministic gates E1–E3 must agree to machine precision; S1
   uses a fixed seed, so it must agree exactly on the same numpy version and closely otherwise).
6. `git add validation reports data && git commit -m "L1: laptop reproduces E1-E3, S1"` and
   `python scripts/run_gate.py S1 --push` (pushes the whole commit).

## Pass criteria
- all four JSONs say PASS on the laptop
- E1–E3 criteria values identical to the cloud copies (|diff| < 1e-9 for floats)
- S1: the S1-criterion recall values ≥ 0.9 and CIPSI/oracle errors within 10 % of the cloud values
- total wall time < 30 min

## Outputs
validation/*.json regenerated on the laptop (cloud copies kept in validation/cloud/), reports regenerated,
prompts/LOG.md entry with the runtimes.  Push: yes.

## Escalation
A deterministic difference in E1–E3 means a library difference (numpy/scipy eigensolver ordering or a
degenerate-eigenvector phase) — record the exact values in validation/BLOCKED.md and call planner-fable at
max effort; do not "fix" tolerances.  If E1 exceeds 30 min (it needs ~100 s for the kernel step on 2 cloud
CPUs), report the time in prompts/LOG.md and continue with E2; the planner decides whether the kernel step
should be restricted to a subset of blocks on this machine.

# 03 — L3: transpiled CZ counts of the exact circuits (measurement for gate S2)
executor: runner-sonnet   effort: low
time budget: 30 min   machine: laptop (CPU)

## Goal
Measure the CZ count and depth of the exact block-unitary circuits at 2x2 per term and per coarse step,
all-to-all and routed on a heavy-hex map (Heron-like basis {rz, sx, x, cz}).  The manual's budget is ≤ 250 CZ
per first-order step at 2x2 and ≤ 500 at 2x3 (gate S2).  The generic synthesis of the 6- and 8-qubit hopping
unitaries is expected to be far above the budget: this prompt produces the honest baseline that prompt 06
must beat.  A FAIL of the S2 criterion here is expected and is not a blocker for prompts 04 and 05.

## Inputs
- `reports/circuit_structure.md`, `validation/CS.json` (flip patterns, block sizes, distinct amplitudes)
- `scripts/laptop_L3_cz_counts.py`

## Steps
1. `python scripts/run_gate.py L3 --level 3 --heavy-hex 3`
   (if an 8-qubit UnitaryGate takes > 15 min at level 3, re-run with `--level 2` and say so).
2. Read `reports/L3_cz_counts.md`; copy the per-term CZ numbers into prompts/LOG.md.
3. Commit the JSON/report (`git commit -am "L3 baseline CZ counts"`), push (`git push`), even though the
   gate status is FAIL — the numbers are the deliverable.

## Pass criteria (for the record; expected FAIL for the baseline)
- CZ per coarse step (all-to-all) ≤ 250; routed ≤ 250

## Outputs
validation/L3.json, reports/L3_cz_counts.md, prompts/LOG.md entry.  Push: yes (baseline numbers).

## Escalation
None for a FAIL of the budget criterion (expected).  Escalate to planner-fable only if transpilation itself
errors out (traceback) after one retry at `--level 1`.

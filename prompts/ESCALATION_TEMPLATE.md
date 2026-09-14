# NN — <GATE> fix (<date>)
executor: executor-opus   effort: high (xhigh on the second attempt)
time budget: <minutes>   machine: <laptop|desktop|cluster>

> Written by planner-fable at max effort after `validation/BLOCKED.md` reported the failure below.
> The planner's job in this file: state the cause, not only the symptom; give the executor a fix that a
> script can verify.

## Failure (copied from validation/BLOCKED.md and validation/<GATE>.json)
- criterion: <name>  value: <value>  criterion: <threshold>
- runtime / exit code / traceback summary

## Diagnosis
What the number means physically or numerically; which module/function produces it
(`src/skqd/<file>.py:<function>`); why it is wrong (convention, parametrization, missing term, noise model,
too few shots, environment); what evidence in the JSON/data supports this diagnosis.  If two causes are
possible, name the discriminating test first.

## Fix
Exact change: file, function, what to replace by what, and the invariants that must still hold afterwards
(E1–E3 must stay PASS whenever a convention or the builder is touched; tests/ must pass).

## Steps
1. discriminating test (command, expected output)
2. implement the fix
3. `pytest -q tests`
4. `python scripts/run_gate.py <GATE> [args]`
5. re-run the gates the fix could affect (E1–E3 if src/skqd physics changed)

## Pass criteria
- `validation/<GATE>.json` status PASS; the previously failing criterion now reads <value> (<threshold>)
- no other gate regressed (list the JSONs to check)

## Outputs
validation/<GATE>.json, reports/<GATE>_*.md regenerated, prompts/LOG.md entry, commit, push on PASS.

## Escalation
If the discriminating test contradicts the diagnosis, stop and write validation/BLOCKED.md with the new
evidence; do not try a third guess.  The planner returns at max effort.

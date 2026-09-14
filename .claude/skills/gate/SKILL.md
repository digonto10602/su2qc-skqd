---
name: gate
description: Run one SKQD project gate end to end (script -> validation JSON -> report -> commit/push) and route the outcome to the right agent. Use as /gate <GATE> [args], e.g. /gate S1 --quick or /gate L2 --push.
allowed-tools: Bash(python *) Bash(git *) Read Glob Grep
---

Run the gate `$0` with any extra arguments:

1. `python scripts/check_package.py` (must print PACKAGE OK; if not, stop and report what is missing).
2. `python scripts/run_gate.py $ARGUMENTS` with a 30-minute timeout.
3. Read `validation/$0.json`.  If status is PASS: run `python scripts/run_gate.py $0 --push` (only if not
   already pushed), then ask `scribe-haiku` to update reports/PROJECT_STATUS.md and validation/gates.md.
4. If status is FAIL or the run timed out: read `validation/BLOCKED.md`; if the failure is a parametrization
   or environment problem (missing package, timeout), ask `runner-sonnet` to retry with the reduced
   parameters named in the prompt; otherwise invoke `planner-fable` with the escalation template
   (`prompts/ESCALATION_TEMPLATE.md`) to write the fix prompt, then `executor-opus` to implement it.
5. Summarize: gate, status, runtime, commit hash, next prompt file.

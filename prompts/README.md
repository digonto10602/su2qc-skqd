# prompts/ — the prompt chain

Every step of this project is driven by a prompt file in this folder.  The planner model (Fable 5.1) writes
the prompt for the next step; an executor model (Opus, or a cheaper runner) executes it; the outcome is
appended to `LOG.md`; when a gate is blocked the planner returns at max effort, writes a fix prompt, and a
lower-effort model executes it.  This is the workflow Digonto asked for: Fable thinks, others repeat.

## File naming

`NN_<slug>.md` with a two-digit running number, e.g. `03_laptop_L3_cz_counts_S2.md`.  Fix prompts written
after a blocked gate are named `NN_<gate>_fix_<YYYYMMDD>.md`.  Never edit an executed prompt; write a new one.
`LOG.md` records who executed what, with commit hashes.

## Format of a prompt (all sections required)

```
# NN — <title>
executor: <agent name from .claude/agents/>   effort: <low|medium|high|xhigh|max>
time budget: <minutes>   machine: <laptop|desktop|cluster|QPU|cloud>
## Goal
one paragraph: the gate or deliverable, and why it matters for the project
## Inputs
files, JSON, prior reports the executor must read first
## Steps
numbered, exact commands, expected runtime of each
## Pass criteria
machine-checkable statements (which JSON key, which threshold); "the report looks fine" is not a criterion
## Outputs
which files must exist afterwards (validation/*.json, reports/*.md, data/*.json), git push yes/no
## Escalation
what to do if a step fails: retry rule (parameters), and when to stop and call the planner
```

## Model routing summary (details in ROUTING.md)

| task type | agent | model | effort |
|---|---|---|---|
| plan next step, diagnose blocked gate, physics decision | planner-fable | Fable 5.1 | max (only then) |
| implement code / decomposition / analysis | executor-opus | Opus | high |
| review a passed gate before push | reviewer-opus | Opus | medium |
| run gates, tests, benchmarks, transpilations | runner-sonnet | Sonnet | low |
| update status tables, logs, formatting | scribe-haiku | Haiku | low |

## Current chain

| # | prompt | gate | status |
|---|---|---|---|
| 00 | `00_bootstrap_and_push.md` | package check, GitHub repo, first push | to run on the laptop |
| 01 | `01_laptop_L1_reproduce_cloud_gates.md` | L1: E1–E3, S1 re-run on the laptop | pending |
| 02 | `02_laptop_L2_qiskit_check.md` | L2: Qiskit vs numpy reference | pending |
| 03 | `03_laptop_L3_cz_counts_S2.md` | L3: CZ counts (S2 measurement) | pending, FAIL expected for the baseline |
| 04 | `04_laptop_L4_aer_noise_S3.md` | L4: Aer noise (S3 preparation) | pending |
| 05 | `05_laptop_L5_cudaq_check.md` | L5: CUDA-Q on the GTX 1060 | pending |
| 06 | `06_S2b_plaquette_interior_and_hopping_decomposition.md` | S2: structured gates within budget | pending (planner + executor) |
| 07 | `07_hardware_H0_2x2_calibration.md` | H0: first QPU session | pending (needs S2, S3) |
| 08 | `08_month_plan_and_reporting.md` | weekly plan to H1/H2/P1/M1 | reference |

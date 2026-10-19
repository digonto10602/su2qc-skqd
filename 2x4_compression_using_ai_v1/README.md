# 2x4_compression_using_ai_v1

A separate study, kept apart from the main package: can the AI-driven circuit-optimisation loop
described in the owner's two reference documents
(`~/Documents/QC_Papers/circuit_optimization_through_claude/2512.22932v2.pdf`, `2610.22367v1.pdf`)
compress the 2x4 SKQD circuits beyond the package's traditional compilation?

- Agent: `genie-opus` (`.claude/agents/genie-opus.md`, Opus 5.5 at high effort) plans and executes
  itself, without planner-fable.
- Phase 1 (setup and study, no building) ends with a report in `reports/`; phase 2 (building) starts
  only on the owner's approval.
- Every mathematical formulation is proved in Lean 4 (`lean/`).
- The package (`src/skqd/`) is imported read-only; nothing outside this folder is modified.
- This folder carries no gate status of the package; its numbers are not package results.

Layout: `notes/` plans, `reports/` reports, `src/` code, `scripts/` drivers, `tests/` tests,
`lean/` Lean 4 project, `data/` computed numbers.

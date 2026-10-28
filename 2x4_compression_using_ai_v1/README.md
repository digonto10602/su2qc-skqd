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

## Three folders, one per lattice (owner 2026-10-28, `notes/012-folder-split.md`)

| folder (repository root) | holds |
|---|---|
| `2x4_compression_using_ai_v1/` (this one) | everything 2x4-specific **and all shared machinery**: `src/c2x4/`, `scripts/`, `lean/`, `tests/`, `families.py` (loader shim), `noise/src/` + `noise/scripts/` (+ `noise/data/device_specs_*`, `noise/reports/`), `MANUAL_lgt_circuit_compression.md`, `notes/`, `reviews/`, the study-wide `reports/`, the 2x4 families `data/families/compressed_circuit_llm_2x4_*`, the 2x4 noise results `noise/data/results/2x4/` and the study-wide results index `noise/data/results/index.json` |
| [`../2x3_compression_using_ai_v1/`](../2x3_compression_using_ai_v1/README.md) | 2x3 data only: `data/c2x3/`, `data/families/compressed_circuit_llm_2x3_*`, `noise/data/results/2x3/` |
| [`../2x2_compression_using_ai_v1/`](../2x2_compression_using_ai_v1/README.md) | 2x2 data only: `data/c2x2/`, `data/families/compressed_circuit_llm_2x2_*`, `data/families/native_2x2/`, `hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_*`, `examples/2x2_sandbox/` |

No code is copied into the 2x3 and 2x2 folders; the code here finds them by itself:
`src/c2x4/env.py` (`STUDY_DIRS`, `lattice_study`, `lattice_data`, `archive_path`), `src/c2x4/families.py`
(`FAMILY_DIRS`, `family_path`) and `noise/src/results.py` (`RESULTS_DIRS`, `lattice_results`).  Inside each folder the
layout is the same (`data/...`, `noise/data/results/...`, `hardware/...`).  Loading is unchanged:

```python
import sys; sys.path.insert(0, "2x4_compression_using_ai_v1")
from families import get_family                     # every family by name: 2x4 v1/v2, 2x3, 2x2
sys.path.insert(0, "2x4_compression_using_ai_v1/noise/src")
import results                                       # results.list_available() spans all three folders
```

## Phase 2 (approved 2026-10-21) — where things are

- Plans: `notes/003` (steps), `notes/004` (approximate-class tolerance), `notes/006` (certified pruned verification);
  planner request `notes/005`.  Report: `reports/002-phase2-compression-results.md`.
- Code: `src/c2x4/` (`evaluate.py` the independent evaluator, `plaqfactor.py` corner frames CF1/CF2/CFG,
  `reach.py` reachable-set restriction, `sparsemux.py` sparse-Walsh multiplexors, `hopframe.py` hop frames,
  `peephole.py`, `proposals.py` the proposal registry, `family.py` families).
- Loop: `scripts/loop_select.py` → `data/archive_it1..5.json`; verification `scripts/eval_family.py`
  (`--family arch:it5:input:pp` / `arch:it5:operator:pp`, `--prune-tau 1e-15`); tables `scripts/summarise.py`;
  native `scripts/native_check.py` (run with `~/.local/share/su2qc-quantinuum/venv/bin/python`).
- Lean: `lean/Compress2x4/*.lean` (48 statements), `cd lean && lake build`.

## C4 (second 2x4 round) and C3 (2x3) — 2026-10-21

- Plan `notes/010`; report `reports/004-c4-c3-second-round-and-2x3.md`; loader API for other agents `notes/009`
  (`from families import get_family`, frozen files in `data/families/`).
- Families: `compressed_circuit_llm_2x4_class{A,B}_v1` (it5, reviewed), `..._v2` (it6), `compressed_circuit_llm_2x3_class{A,B}`.
- New code: `src/c2x4/linsynth.py` (angle-linear synthesis, flags), `certify.py` (MILP certificates), `families.py`;
  scripts `freeze_family.py`, `certify_family.py`, `verify_aer_family.py`, `native_family.py`, `merge_archives.py`.
- 2x3 outputs: `../2x3_compression_using_ai_v1/data/c2x3/` (in `data/c2x3/` of this folder until `notes/012`).  Lean: `lean/Compress2x4/{Glue,Rounding,Conj}.lean`.

## 2x2 families — 2026-10-28

- Owner request, plan and result `notes/011-2x2-families.md`; data in `../2x2_compression_using_ai_v1/` (README there).
- Folder split into one folder per lattice: `notes/012-folder-split.md` (moves table, integrity checks
  `data/split_integrity_{before,after,compare}.json`, `data/split_dryrun_check.json`).

## Native exports of the 2x3 and 2x4 compressed families — 2026-10-28

- `notes/013-native-exports-2x3-2x4.md`: Quantinuum native exports for the H2-2SC syntax check, 2x4 in
  `data/families/native_2x4/<family>/` (gzipped like the frozen 2x4 set), 2x3 in
  `../2x3_compression_using_ai_v1/data/families/native_2x3/<family>/`; numbers `data/native_exports_2x3_2x4.json`,
  load check `data/native_exports_load_check.json`, dry-run sessions `data/dryrun_native_2x4/`.

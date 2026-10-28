# 012 — One folder per lattice (2x2, 2x3, 2x4)

- Date: 2026-10-28.  Author: genie-opus.  Base commit: `8cb3a84` (the H2-2SC syntax check, finished and committed);
  this reorganisation is the commit that adds this note.
- Request in force, the owner's words (2026-10-28): **"split into 2x2, 2x3, 2x4 folders after the syntax check
  finishes"**, with the layout agreed through the coordinator: the 2x4 folder keeps everything 2x4-specific and all
  shared machinery; the new 2x3 and 2x2 folders get that lattice's data only, with the same inside layout; no code is
  copied; history follows the files (`git mv`).
- Related: `notes/009-family-api.md` (loader contract, updated), `notes/011-2x2-families.md` (2x2 families),
  `../2x2_compression_using_ai_v1/README.md`, `../2x3_compression_using_ai_v1/README.md`, `README.md`.

## Layout after the split (all at the repository root)

| folder | holds |
|---|---|
| `2x4_compression_using_ai_v1/` | 2x4 data **and all shared machinery**: `src/c2x4/`, `scripts/`, `lean/`, `tests/`, `families.py`, `noise/src/`, `noise/scripts/`, `noise/reports/`, `noise/data/device_specs_*`, `MANUAL_lgt_circuit_compression.md`, `notes/` (this note and `notes/011` included), `reviews/`, the study-wide `reports/`, `noise/data/results/2x4/` and the study-wide `noise/data/results/index.json`; the shared regenerable cache `data/cache/` (gitignored) |
| `2x3_compression_using_ai_v1/` | `data/c2x3/`, `data/families/compressed_circuit_llm_2x3_*`, `noise/data/results/2x3/`, `README.md` |
| `2x2_compression_using_ai_v1/` | `data/c2x2/`, `data/families/compressed_circuit_llm_2x2_*`, `data/families/native_2x2/`, `hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_*`, `examples/2x2_sandbox/`, `README.md` |

Choice for the notes: every note stays in `2x4_compression_using_ai_v1/notes/` (one numbered sequence for the whole
study); the 2x2 and 2x3 READMEs point to the notes that concern them.  The study-wide reports (001-004, the noise
reports 001-003) stay in the 2x4 folder; there were no 2x3-only or 2x2-only reports or figures to move.  2x3 has no
separate native-export folder (its native counts are `data/c2x3/native_*.json`, moved with `data/c2x3/`).

## Moves table (all `git mv`; file counts are git-tracked files)

| from (`2x4_compression_using_ai_v1/` + ...) | to | files |
|---|---|---|
| `data/c2x3/` | `2x3_compression_using_ai_v1/data/c2x3/` | 22 |
| `data/families/compressed_circuit_llm_2x3_classA.json.gz`, `..._classB.json.gz` | `2x3_compression_using_ai_v1/data/families/` | 2 |
| `noise/data/results/2x3/` | `2x3_compression_using_ai_v1/noise/data/results/2x3/` | 935 |
| `data/c2x2/` | `2x2_compression_using_ai_v1/data/c2x2/` | 26 |
| `data/families/compressed_circuit_llm_2x2_classA.json.gz`, `..._classB.json.gz` | `2x2_compression_using_ai_v1/data/families/` | 2 |
| `data/families/native_2x2/` | `2x2_compression_using_ai_v1/data/families/native_2x2/` | 182 |
| `hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classA/`, `..._classB/` | `2x2_compression_using_ai_v1/hardware/quantinuum_sc_20261028/` | 68 |
| `examples/2x2_sandbox/` | `2x2_compression_using_ai_v1/examples/2x2_sandbox/` | 5 |
| | **total** | **1 242** |

The sandbox's gitignored `cache/` (regenerable) was moved with a plain `mv`.  The now empty
`2x4_compression_using_ai_v1/hardware/` was removed.

## How the code finds the three folders

| map | file | used by |
|---|---|---|
| `STUDY_DIRS`, `lattice_study(L)`, `lattice_data(L)` (2x4 `data/`, 2x3 `<2x3>/data/c2x3/`, 2x2 `<2x2>/data/c2x2/`) | `src/c2x4/env.py` | `archive_path` (`L3_`/`L2_` labels), `eval_family.py`, `certify_family.py`, `verify_aer_family.py`, `native_family.py`, `summarise_2x2.py`, `report004_tables.py`, `export_quantinuum_family.py` (relative `--out` resolved against the family's lattice folder) |
| `FAMILY_DIRS`, `family_lattice(name)`, `family_dir(name)`, `family_path(name)` | `src/c2x4/families.py` | `get_family`, `get_family_ir`, `available_families`, `freeze_family.py` |
| `RESULTS_DIRS`, `lattice_results(L)` | `noise/src/results.py` | `list_available`, `load`, `table`, `summary`; the writers `accuracy_sv.py`, `analytic_f.py`, `noisy_run.py`, `validate_engine.py`, `noisy_queue.py`, `accuracy_queue.sh`, `aggregate.py` (globs all folders; index paths now relative to the repository root, key `path_base`), `report_003_results.py` |

Signatures are unchanged: `get_family(name, measure=False)`, `results.load(lattice, family, device, test)`,
`results.table(test, lattice)`, `results.list_available()`.

## Integrity checks (all run on this laptop, `taskset -c 0-9 nice -n 10`, coding env unless stated)

Script `scripts/split_integrity.py` (`before` at `8cb3a84` before any move, `after` after the moves and the path
edits, then `compare`); files `data/split_integrity_before.json`, `data/split_integrity_after.json`,
`data/split_integrity_compare.json`.  Deterministic (no randomness, `seed: null`).

1. **sha256 of every moved file** (1 242 files) plus the 4 frozen 2x4 family files that stay (control): identical
   before and after for all 1 246 files except one file edited on purpose, `examples/2x2_sandbox/run_2x2_example.py`
   (its import paths now point to the shared code in `2x4_compression_using_ai_v1/src/`).  All **190 family and
   native-export files** (8 frozen families, 182 files of `native_2x2/`) are byte-identical
   (`family_and_native_export_files_identical: true`, `unexpected_differences: []`, `status: PASS`).
2. **`get_family(name)` for every registered name and alias** (10 names): same file sha256 and, per circuit, the same
   circuit id, stored `content_sha256`, recomputed IR gate-list sha256 and sha256 of the qiskit instruction list
   (`families_all_equal: true`).  Frozen file sha256 (equal to `notes/009`):

| family | circuits | new path | sha256 |
|---|---|---|---|
| `compressed_circuit_llm_2x4_classA_v1` | 75 | `2x4_compression_using_ai_v1/data/families/` (unmoved) | `7c2d0b0abf80fbca9dabe9220481f9d6bbade83314fcde0ffb7ebd09cb2b39c3` |
| `compressed_circuit_llm_2x4_classB_v1` | 75 | `2x4_compression_using_ai_v1/data/families/` (unmoved) | `cd902c9a7f295236b1f3f1b5a94fe65de41c70ca536a12c2df5d374fd345d27b` |
| `compressed_circuit_llm_2x4_classA_v2` | 75 | `2x4_compression_using_ai_v1/data/families/` (unmoved) | `2631884e1b7ab1576da2ca7217eb12351393568eca451bd4438db2371f0e846f` |
| `compressed_circuit_llm_2x4_classB_v2` | 75 | `2x4_compression_using_ai_v1/data/families/` (unmoved) | `475a06c28d0f7f519ccc3558b062f9716f77b279a737f6abbc784e1066322c35` |
| `compressed_circuit_llm_2x3_classA` | 44 | `2x3_compression_using_ai_v1/data/families/` | `ae12cff21d380b46b909d4e7892bc09fdc98241f1839954c6e7f3a53f5ff9ec6` |
| `compressed_circuit_llm_2x3_classB` | 44 | `2x3_compression_using_ai_v1/data/families/` | `0e75e43807b9086e41af77c778c0e5d32eecbdbfb953fbdb48fd17697e47ad62` |
| `compressed_circuit_llm_2x2_classA` | 28 | `2x2_compression_using_ai_v1/data/families/` | `fbdd73b1ee35b0dbde838e7e8af37d678ca910d5f0fe5ef870cdaf3b6ea19e9c` |
| `compressed_circuit_llm_2x2_classB` | 28 | `2x2_compression_using_ai_v1/data/families/` | `622f29d6829e0910565ec67d2c08308a40bff0d2703924a3b34a089476422367` |

3. **`results.list_available()`**: 189 entries before (2x4 112, 2x3 77) and the identical list, in the same order,
   after (`results_list_available_identical: true`).  The 189 paths of `noise/data/results/index.json` were rewritten
   to repository-root paths and each checked to exist and to equal the loader's own path.  The accuracy queue plan
   resolves 432 of 432 runs as done through the new `lattice_results`.
4. **Study tests**: `pytest -q 2x4_compression_using_ai_v1/tests` — 21 passed before the move and 21 passed after.
5. **Local dry run of the package's submit script** on the moved exports (isolated venv
   `~/.local/share/su2qc-quantinuum/venv`, no login, no network, output in the job tmp dir):
   `scripts/quantinuum_submit.py --dry-run --all --circuits <repo>/2x2_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_class{A,B} --out <tmp>/split_dryrun_2x2_class{A,B}`.
   Both classes: 30 jobs, 6 000 shots, the same job ids, HQC estimate and `index.json` sha256 as the pre-split dry-run
   records in `../2x2_compression_using_ai_v1/data/c2x2/dryrun/`, and the seeded local-Aer counts identical file by
   file to the pre-split dry run.  Record: `data/split_dryrun_check.json`.

## What was left alone, and why

- Provenance fields inside moved files (`family_file` in the native-export manifests and `index.json`, `produced_by`,
  `circuits` in `session.json`, the `verification` paths inside the frozen families, `git_commit` fields) still name
  `2x4_compression_using_ai_v1/...`.  They record where the file was when it was written; editing them would change
  the sha256 that the hardware sessions (`index_sha256`) and `notes/009` cite.  The READMEs say so.
- Historical commit hashes in notes and reports.
- Package files: none touched, except the path strings of `reports/quantinuum_sc_20261028_2x2_frozen_vs_compressed.md`
  (allowed exception; a dated path note was added there saying the strings were updated by hand after the run).

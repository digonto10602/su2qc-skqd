# 2x3_compression_using_ai_v1

The **2x3 data** of the compressed-circuit study (AI-driven circuit-optimisation loop, agent `genie-opus`; the 2x3
round is owner decision C3).  Split out of `2x4_compression_using_ai_v1/` on 2026-10-28 at the owner's request
("split into 2x2, 2x3, 2x4 folders after the syntax check finishes"); moves and integrity checks in
[`../2x4_compression_using_ai_v1/notes/012-folder-split.md`](../2x4_compression_using_ai_v1/notes/012-folder-split.md).

**This folder holds data only.  The code lives in `2x4_compression_using_ai_v1/`** and is not copied here:
`../2x4_compression_using_ai_v1/src/c2x4/` (builders, verification, the loader `families.py`),
`../2x4_compression_using_ai_v1/scripts/`, `../2x4_compression_using_ai_v1/noise/` (noise study code, results loader,
noise reports), `../2x4_compression_using_ai_v1/lean/`, `../2x4_compression_using_ai_v1/tests/`.  Plans:
`../2x4_compression_using_ai_v1/notes/010-c4-c3-work-plan.md`; report
`../2x4_compression_using_ai_v1/reports/004-c4-c3-second-round-and-2x3.md` (study-wide, covers 2x4 and 2x3); noise
results report `../2x4_compression_using_ai_v1/noise/reports/003-noise-results.md`; loader contract
`../2x4_compression_using_ai_v1/notes/009-family-api.md`.  These families are study circuits, not package results;
they are not substituted into any package gate or plan without the owner (`notes/008`).

## What is here

| path | what |
|---|---|
| `data/families/compressed_circuit_llm_2x3_classA.json.gz`, `..._classB.json.gz` | the frozen 2x3 families (44 circuits each; sha256 in `notes/009`) |
| `data/c2x3/` | loop archives (`archive_L3_it1*.json`), certified verification (`eval_arch_L3_it1_*_pp2_all44_pruned.json`), MILP certificates (`cert_L3_it1_*.json`), Aer checks (`aer_*.json`), native counts (`native_*.json`), run logs |
| `noise/data/results/2x3/<family>/<device>/<test>.json` | the noise study's 2x3 results (families `compressed_circuit_llm_2x3_class{A,B}` and the package's `frozen` 2x3 circuits; tests `accuracy`, `analytic_f`, `noise_behaviour`, `skqd_energy`, `engine_validation`); listed in `../2x4_compression_using_ai_v1/noise/data/results/index.json` |

There are no separate 2x3 native exports (the native counts are `data/c2x3/native_*.json`).  Provenance fields inside
the files still name the old location `2x4_compression_using_ai_v1/...`; they are left unchanged on purpose (the
sha256 of every moved file is unchanged).

## How to use (from the repository root)

```python
import sys
sys.path.insert(0, "2x4_compression_using_ai_v1")          # the loader shim lives with the code
from families import get_family, family_path
circuits = get_family("compressed_circuit_llm_2x3_classB")  # [(circuit_id, qiskit.QuantumCircuit, metadata), ...]
family_path("compressed_circuit_llm_2x3_classB")           # -> 2x3_compression_using_ai_v1/data/families/...

sys.path.insert(0, "2x4_compression_using_ai_v1/noise/src")
import results
results.load("2x3", "frozen", "quantinuum_h2_2", "noise_behaviour")   # dict, read from this folder
results.table("analytic_f", "2x3")                                     # pandas DataFrame
```

New 2x3 outputs of the study scripts land here automatically (`c2x4.env.lattice_data("2x3")` = `data/c2x3/`,
`results.lattice_results("2x3")` = `noise/data/results/2x3/`).

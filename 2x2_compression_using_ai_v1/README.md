# 2x2_compression_using_ai_v1

The **2x2 data** of the compressed-circuit study (AI-driven circuit-optimisation loop, agent `genie-opus`).  Split
out of `2x4_compression_using_ai_v1/` on 2026-10-28 at the owner's request ("split into 2x2, 2x3, 2x4 folders after
the syntax check finishes"); moves and integrity checks in
[`../2x4_compression_using_ai_v1/notes/012-folder-split.md`](../2x4_compression_using_ai_v1/notes/012-folder-split.md).

**This folder holds data only.  The code lives in `2x4_compression_using_ai_v1/`** and is not copied here:
`../2x4_compression_using_ai_v1/src/c2x4/` (builders, verification, the loader `families.py`),
`../2x4_compression_using_ai_v1/scripts/` (loop, eval, freeze, Aer, native, export, summarise),
`../2x4_compression_using_ai_v1/noise/` (noise study code and the results loader),
`../2x4_compression_using_ai_v1/lean/` (proofs), `../2x4_compression_using_ai_v1/tests/`.
Plans and decisions: `../2x4_compression_using_ai_v1/notes/` (2x2: `notes/011-2x2-families.md`; loader contract
`notes/009-family-api.md`).  These families are study circuits, not package results; they are not substituted into
any package gate or plan without the owner (`notes/008`).

## What is here

| path | what |
|---|---|
| `data/families/compressed_circuit_llm_2x2_classA.json.gz`, `..._classB.json.gz` | the frozen 2x2 families (28 circuits each; sha256 in `notes/009`) |
| `data/families/compressed_circuit_llm_2x2_classA_k5.json.gz`, `..._classB_k5.json.gz` | k = 5 add-on families (2026-10-28, `notes/014`): the k = 5 circuit of each of the 7 references, same archive choices and skeleton as the k = 1..4 families above (which are unchanged); native exports in `data/families/native_2x2/<family>_k5/` |
| `data/families/native_2x2/<family>/` | Quantinuum native exports in the on-disk format of the package's `data/quantinuum/circuits_2x2` (`index.json`, `<id>.json`, `<id>.qasm`, `<id>.manifest.json`, `CAL_*`); read by the package's `scripts/quantinuum_submit.py` |
| `data/c2x2/` | loop archive (`archive_L2_it1.json`), certified verification (`eval_arch_L2_it1_*_pp2_all28_pruned.json`), MILP certificates (`cert_L2_it1_*.json`), Aer checks (`aer_*.json`), native counts (`native_*.json`), the summary of every number (`summary_2x2.json`), the dry-run session records (`dryrun/`), run logs |
| `hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_class{A,B}/` | the H2-2SC syntax-check runs of 2026-10-28 (`session.json`, `counts/`, `summary.json`, `account_before.json`, `account_after.json`); report `../reports/quantinuum_sc_20261028_2x2_frozen_vs_compressed.md` |
| `examples/2x2_sandbox/` | the worked teaching example (not a family): `run_2x2_example.py`, `results.json`, `archive_L2_example.json`, `circuits_L2_example.json.gz` (its `cache/` is not committed) |
| `noise/data/results/2x2/` | (none yet) where the noise study writes 2x2 results |

The provenance fields inside these files (`family_file`, `produced_by`, `circuits` arguments in `session.json`, ...)
still name the old location `2x4_compression_using_ai_v1/...`: they record where the file was when it was written and
are left unchanged on purpose (the sha256 of every moved file is unchanged).

## How to use (from the repository root)

```python
import sys
sys.path.insert(0, "2x4_compression_using_ai_v1")          # the loader shim lives with the code
from families import get_family, family_path
circuits = get_family("compressed_circuit_llm_2x2_classA")  # [(circuit_id, qiskit.QuantumCircuit, metadata), ...]
family_path("compressed_circuit_llm_2x2_classA")           # -> 2x2_compression_using_ai_v1/data/families/...

sys.path.insert(0, "2x4_compression_using_ai_v1/noise/src")
import results
[x for x in results.list_available() if x[0] == "2x2"]      # noise results for 2x2 (none yet)
```

Local dry run of the package's submission script on the exports (no login, no network; isolated venv):

```bash
~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_submit.py --dry-run --all \
    --circuits 2x2_compression_using_ai_v1/data/families/native_2x2/compressed_circuit_llm_2x2_classA --out <tmp dir>
```

Worked example: `python 2x2_compression_using_ai_v1/examples/2x2_sandbox/run_2x2_example.py` (writes only inside
`examples/2x2_sandbox/`).  New 2x2 outputs of the study scripts land here automatically
(`c2x4.env.lattice_data("2x2")` = `data/c2x2/`; `export_quantinuum_family.py --out data/families/native_2x2/<family>`
is resolved against this folder).

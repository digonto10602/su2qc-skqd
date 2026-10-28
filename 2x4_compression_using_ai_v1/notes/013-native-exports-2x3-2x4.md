# 013 — Quantinuum native exports of the 2x3 and 2x4 compressed families (for the H2-2SC syntax check)

- Date: 2026-10-28.  Author: genie-opus.  Base commit: `eef94e3` (notes/012, the folder split).
- Request in force (owner, relayed by the coordinator 2026-10-28): run the H2-2SC syntax checker on the 2x3 and 2x4
  COMPRESSED families; genie-opus produces the native exports "in exactly the format you made for 2x2".  The
  submission itself is not genie-opus's job (no Nexus, no push).
- Related: `notes/011-2x2-families.md` (the 2x2 exports this repeats), `notes/012-folder-split.md`, `notes/009`.

## What is exported

| family | circuits | export folder |
|---|---|---|
| `compressed_circuit_llm_2x3_classA`, `_classB` | 44 each (= the frozen 2x3 ids, same order) | `2x3_compression_using_ai_v1/data/families/native_2x3/<family>/` |
| `compressed_circuit_llm_2x4_classA` (= `_classA_v1`), `_classB` (= `_classB_v1`) | 75 each | `2x4_compression_using_ai_v1/data/families/native_2x4/<family>/` |
| `compressed_circuit_llm_2x4_classA_v2`, `_classB_v2` | 75 each | same |

The 2x4 v1 export folders carry the alias names the coordinator gave (`compressed_circuit_llm_2x4_classA` /
`_classB`); the `family` field inside is the canonical `_v1` name.

## Route (the 2x2 route, `scripts/export_quantinuum_family.py`)

Per circuit: IR from `get_family_ir` → `cz` → `cp(π)` → `qn.ir_to_pytket(measure=True)` →
`qn.compile_native(., "H2-2", 0)` (offline backend) → Q1L `qn.local_equivalence_35a(ir, native, n, structured=True)`
with its rounding bound $B$ → `<id>.json`, `<id>.qasm`, `<id>.manifest.json`; `index.json` at the end; the calibration
circuits `CAL_zeros` / `CAL_x0` copied byte for byte from the frozen folder of the same lattice.

Differences that the lattice forces, each an option of the script (2x2 defaults unchanged):

1. **2x3** (20 qubits): identical to 2x2 — dense Aer statevector (complex128) of the native circuit against the
   package's exact coarse state (Q1 bar $\max|\Delta\psi|<10^{-10}$, leakage $<10^{-9}$), against the IR statevector,
   and JSON/QASM round trips re-simulated.  Plain files, as the frozen 2x3 set.
2. **2x4** (28 qubits):
   - ids: the frozen 2x4 set names its structured circuits `B0_ref102_k1.structured` (k = 1..4); the exports use the
     package id without the suffix (`--frozen-suffix .structured`).  The family's 15 k = 5 circuits have no frozen
     native counterpart; they are exported too (`--extra-k`), with $dt$ = the frozen index's `dt[2B]` (checked equal to
     the family metadata) and the reference integer checked against the frozen manifest of the same reference.
   - files gzipped (`--gzip`: `.json.gz` / `.qasm.gz`, level 9, mtime 0, sha256 of the uncompressed text, key
     `sha256_of`) — the on-disk convention of the frozen 2x4 set; `scripts/quantinuum_submit.py:load_frozen` reads
     it.  Plain files would be about 0.3–1 MB each (measured on one class-B circuit: 0.29 MB JSON, 0.009 MB gzipped).
   - calibration: the frozen 2x4 set has `CAL_zeros` and `CAL_x0` (28 qubits, gzipped); copied byte for byte.
   - state check: a dense $2^{28}$ statevector is out of reach on this laptop (4.3 GB per vector, several per
     circuit, 300 circuits).  Decided after a measured probe (below).  Round trips are checked by Q1L of the IR
     against each re-read circuit (JSON and QASM) plus equal counts.
3. Chunking: every run stops starting new circuits after 1 500 s; a driver re-invokes it (resume from the
   manifests already written) until `index.json` exists.  All runs `taskset -c 0-9 nice -n 10`, thread variables
   $\le 10$ (owner rule).

## Checks after the export

- `scripts/quantinuum_submit.py --dry-run --all --circuits <dir> --out <tmp>` per family (local, no network): job
  count and the formula HQC total at 200 shots ($\mathrm{HQC}_{\rm job}=5+200\,(N_{1q}+10N_{2q}+5N_m)/5000$,
  `qn.hqc_job`).  2x3 with the local Aer sampling, as for 2x2; 2x4 with `--records-only` (local Aer sampling of 28
  qubits is the same dense statevector that is out of reach).
- Numbers collected by `scripts/summarise_native_exports.py` into `data/native_exports_2x3_2x4.json`.

## Decision on the 2x4 state check (measured)

Probe `data/probes/native_2x4_sparse_probe.json`: the certified sparse simulation of the native form of the smallest
2x4 circuit (`compressed_circuit_llm_2x4_classB_v1` `B0_ref102_k1`, 660 ZZ) did **not finish in 1 700 s** (killed by
`timeout`, exit 124).  The native form breaks the codeword structure the sparse simulator relies on (each CX becomes
ZZPhase plus PhasedX on the target; same effect as the frozen 2x3 case in `noise/data/checks/native_compile_check.json`,
support 442 368 native vs 998 IR).  300 circuits are therefore out of the 30-minute rule, and the 2x4 exports use
`--state-check q1l-only`: exactly the frozen 2x4 set's own check (`statevector_engine: null`, Q1L only).  The 2x4
manifests carry `passes_Q1: null`: **Q1 is not claimed for the 2x4 native circuits.**  What holds instead (both are
computed, neither is a new proof): Q1L — the package's conversion proof — passes for every native circuit against its
IR, with rounding bound $B\le1.5\times10^{-13}$; and every IR circuit passed the certified pruned verification
against the exact state earlier (`data/eval_arch_it5_{operator,input}_pp_all75_pruned.json`,
`data/eval_arch_it6_{operator,input}_pp2_all75_pruned.json`: 75/75 each, certified $\max|\Delta\psi|\le1.8\times10^{-12}$).

## Outcome (numbers from `data/native_exports_2x3_2x4.json`, written by `scripts/summarise_native_exports.py`)

| family | circuits | ZZ (min–max) | PhasedX (min–max) | depth-2q | HQC/shot (min–max) | Q1 | Q1L | max $B$ |
|---|---|---|---|---|---|---|---|---|
| `compressed_circuit_llm_2x3_classA` | 44 | 871–871 | 2 415–2 416 | 611 | 2.2650–2.2652 | 44/44 (max $\vert\Delta\psi\vert$ $1.8\times10^{-14}$) | 44/44 | $6.3\times10^{-14}$ |
| `compressed_circuit_llm_2x3_classB` | 44 | 309–465 | 822–1 246 | 170–290 | 0.8224–1.2192 | 44/44 ($1.4\times10^{-14}$) | 44/44 | $3.1\times10^{-14}$ |
| `compressed_circuit_llm_2x4_classA` (v1) | 75 | 1 736–1 740 | 4 831–4 847 | 1 275–1 280 | 4.4942–4.5054 | not computed | 75/75 | $1.5\times10^{-13}$ |
| `compressed_circuit_llm_2x4_classB` (v1) | 75 | 582–800 | 1 564–2 168 | 292–469 | 1.5328–2.0896 | not computed | 75/75 | $4.8\times10^{-14}$ |
| `compressed_circuit_llm_2x4_classA_v2` | 75 | 1 492–1 492 | 4 164–4 165 | 948 | 3.8728–3.8730 | not computed | 75/75 | $1.1\times10^{-13}$ |
| `compressed_circuit_llm_2x4_classB_v2` | 75 | 580–763 | 1 550–2 052 | 292–429 | 1.5260–1.9924 | not computed | 75/75 | $4.7\times10^{-14}$ |

- In every family the native ZZ count equals the IR two-qubit count, as for 2x2.
- JSON and QASM round trips pass for every circuit (2x3: re-simulated with Aer; 2x4: Q1L of each re-read circuit plus equal counts).
- Each 2x4 family includes 15 circuits at $k=5$ with no frozen counterpart.
- Calibration: `CAL_zeros`, `CAL_x0` in every export, copied byte for byte (2x3 plain, 2x4 gzipped, exactly as in the frozen folders).
- Load check (`data/native_exports_load_check.json`): every circuit and calibration of the six exports (46/46/77/77/77/77) loads through the submission script's own `load_index` / `load_manifest` / `load_frozen` (sha256 check), with native counts equal to the manifest.

Dry runs (`scripts/quantinuum_submit.py --dry-run --all --records-only`, 200 shots per circuit and per calibration;
session records copied to `../2x3_compression_using_ai_v1/data/c2x3/dryrun/` and `data/dryrun_native_2x4/`):

| family | jobs | shots | formula HQC total | of which the circuits only |
|---|---|---|---|---|
| 2x3 classA | 46 | 9 200 | 20 179.64 | 20 153.60 |
| 2x3 classB | 46 | 9 200 | 9 223.16 | 9 197.12 |
| 2x4 classA (v1) | 77 | 15 400 | 67 955.52 | 67 923.08 |
| 2x4 classB (v1) | 77 | 15 400 | 27 256.40 | 27 223.96 |
| 2x4 classA_v2 | 77 | 15 400 | 58 502.24 | 58 469.80 |
| 2x4 classB_v2 | 77 | 15 400 | 26 897.44 | 26 865.00 |

`--records-only` for all six: the dry run with local sampling uses the A6 *noise model*, i.e. noisy Aer trajectories.
At 20 qubits it did not finish within 30 min (class A on 1 core) or within 16 min (class B on 8 cores, stopped);
record `data/probes/dryrun_2x3_aer_aborted.json`.  At 28 qubits it is out of reach.  The job records, shots and
formula HQC are the same with or without sampling.

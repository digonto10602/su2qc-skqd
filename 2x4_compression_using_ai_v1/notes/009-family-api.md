# 009 — Family loader API for the noise agent (C5) and later users

- Date: 2026-10-21 (updated the same day with v2 and 2x3).  Author: genie-opus.  API commit: **`f0b2363`**
  (code + frozen v1 files); v2 and 2x3 families added at **`390629e`** with no change to the signature.
- Plan in force: owner decisions `notes/008` (naming and separation rule; C3/C4 signed); C4/C3 work plan `notes/010`.
- This note is the contract between genie-opus (producer) and the noise agent in `2x4_compression_using_ai_v1/noise/`
  (consumer).  genie-opus never writes into `noise/`.

## Signature

```python
import sys; sys.path.insert(0, "/home/digimonk/Projects/su2qc-skqd/2x4_compression_using_ai_v1")
from families import get_family            # shim; the implementation is src/c2x4/families.py

get_family(name: str, measure: bool = False) -> list[tuple[str, qiskit.QuantumCircuit, dict]]
#            -> [(circuit_id, circuit, metadata), ...] in the fixed order (twoB, reference, k)
```

Other functions in the same module:

| function | returns |
|---|---|
| `available_families()` | names whose frozen file exists now |
| `get_family_ir(name)` | `[(circuit_id, IR gate list, metadata)]` — the package's IR tuples `(name, qubits, param)` |
| `family_header(name)` | family-level record (provenance, contract, count ranges, verification files) |
| `exact_target(metadata)` | `(codeword ints, amplitudes)`: the package's exact coarse state (`krylov.apply_groups`, complex128); imports `skqd` lazily |
| `ir_to_qiskit(gates, n, measure=False)` | the converter used by `get_family` |

- The loader needs only numpy and the caller's qiskit (it uses `x, h, ry, rz, rx, p, cx, cz, cp, rzz, unitary(1q)`
  only, so qiskit 1.4.3 and 2.5.2 both work).  It imports nothing from the construction code.
- Every family is a **frozen file** `data/families/<name>.json.gz`, written once by `scripts/freeze_family.py`.  The
  loader re-checks the sha256 of every circuit's gate list against the stored `content_sha256` and raises on a
  mismatch.  A family that is not frozen yet raises `FileNotFoundError`.
- `measure=True` appends `measure(range(n), range(n))`; qiskit's counts keys then have qubit 0 at the right end
  (`skqd.reference_sim.qiskit_key_to_bits` converts them to the package's bit tuples).

## Names (owner rule, notes/008)

| name | status | circuits | contract | 2q gates (min–max) |
|---|---|---|---|---|
| `compressed_circuit_llm_2x4_classA_v1` (alias `compressed_circuit_llm_2x4_classA`) | frozen at `f0b2363` | 75 (15 references × $k=1..5$), 28 qubits | operator-exact | 1 736–1 740 |
| `compressed_circuit_llm_2x4_classB_v1` (alias `compressed_circuit_llm_2x4_classB`) | frozen at `f0b2363` | 75, 28 qubits | exact on own reference only | 582–800 |
| `compressed_circuit_llm_2x4_classA_v2` | frozen at `390629e` (C4 round) | 75, 28 qubits | operator-exact | 1 492–1 492 |
| `compressed_circuit_llm_2x4_classB_v2` | frozen at `390629e` (C4 round) | 75, 28 qubits | exact on own reference only | 580–763 |
| `compressed_circuit_llm_2x3_classA` | frozen at `390629e` (C3) | 44 (8 references at $B=0$, 3 at $B=1$, $k=1..4$ — the frozen 2x3 list), 20 qubits | operator-exact | 871–871 |
| `compressed_circuit_llm_2x3_classB` | frozen at `390629e` (C3) | 44, 20 qubits | exact on own reference only | 309–465 |

The aliases without a version keep pointing to v1 (the reviewed it5 families); the owner decides when (if) they move.
The 2x4 v2 and 2x3 counts come from `data/eval_arch_it6_*_pp2_all75_pruned.json` and
`data/c2x3/eval_arch_L3_it1_*_pp2_all44_pruned.json` (summary `n_2q_range`).

v1 is exactly the it5 family the reviewer verified (`reviews/001`); its frozen file is built from the same builders
(`arch:it5:<operator|input>:pp`), and `freeze_family.py` refuses to write unless every circuit's two-qubit count and
two-qubit depth equal the verification record.  File sha256 (the v1 files are unchanged since `f0b2363`):

- `compressed_circuit_llm_2x4_classA_v1.json.gz`: `7c2d0b0abf80fbca9dabe9220481f9d6bbade83314fcde0ffb7ebd09cb2b39c3`
- `compressed_circuit_llm_2x4_classB_v1.json.gz`: `cd902c9a7f295236b1f3f1b5a94fe65de41c70ca536a12c2df5d374fd345d27b`
- `compressed_circuit_llm_2x4_classA_v2.json.gz`: `2631884e1b7ab1576da2ca7217eb12351393568eca451bd4438db2371f0e846f`
- `compressed_circuit_llm_2x4_classB_v2.json.gz`: `475a06c28d0f7f519ccc3558b062f9716f77b279a737f6abbc784e1066322c35`
- `compressed_circuit_llm_2x3_classA.json.gz`: `ae12cff21d380b46b909d4e7892bc09fdc98241f1839954c6e7f3a53f5ff9ec6`
- `compressed_circuit_llm_2x3_classB.json.gz`: `0e75e43807b9086e41af77c778c0e5d32eecbdbfb953fbdb48fd17697e47ad62`

Gate set of v2 and 2x3: as v1 plus `cz` (the JW conjugation) and `h` (the relative-phase ANDs of the flags); all are
in the loader's converter.  The package's `ir_to_pytket` has no `cz`; `scripts/native_family.py` rewrites it as
`cp(pi)` (identical matrix) before compiling.

## Metadata keys (per circuit)

`circuit_id` (e.g. `B0_ref102_k1`), `lattice` (`2x4`/`2x3`), `family`, `class` (`A`/`B`), `version`, `twoB`,
`reference` (dressed-basis index), `reference_bits` (the qubit integer the X-gate preparation writes), `k`, `dt`,
`theta` $=k\,dt$, `n_qubits`, `n_2q`, `n_1q`, `depth_2q`, `ops`, `contract`, `valid_use`, `global_phase_vs_target`,
`content_sha256`, `source`, `verification` (file and the bar numbers of that circuit).

- `global_phase_vs_target` $\varphi$: the noiseless output equals $e^{i\varphi}$ times the package's exact coarse
  state.  Class A: $\varphi=0$.  Class B: $\varphi=\theta\,(H_{\rm diag})_{rr}$, the dropped diagonal group (Lean
  `diagonal_mulVec_single`; measured by the reviewer to $2.8\times10^{-14}$ rad).  Irrelevant for sampling.
- **`valid_use` of class B is binding** (reviews/001 note 1): prepare own reference with X gates, one coarse step,
  measure in the computational basis.  Not valid for another input, $r>1$ repetitions, Hadamard tests or controlled
  versions.  Noise tests that inject errors mid-circuit are fine (they model this use), but a comparison of class B
  "as an operator" is not.

## Stability promise

Frozen files are never rewritten.  A changed family gets a new version name (v2, v3, ...) and a new line in this
note's table, with its commit and file hash.  The loader's signature does not change.

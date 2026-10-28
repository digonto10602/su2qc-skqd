# 014 — k = 5 add-on families for the compressed 2x2 and 2x3 families

- Date: 2026-10-28.  Author: genie-opus.  Base commit: `7b9bf32`; this note is part of the commit that adds the
  families.
- Request in force (owner, 2026-10-28, relayed by the coordinator): **"build k=5 circuits for 2x2 and 2x3, frozen and
  compressed"**.  Another agent builds the package's frozen k = 5 circuits (`data/quantinuum/circuits_2x{2,3}_k5/`); genie-opus
  builds the compressed ones and touches nothing of the other agent's work (read-only cross-check only).
- Related: `notes/009-family-api.md` (loader contract, updated), `notes/011-2x2-families.md`, `notes/013-native-exports-2x3-2x4.md`.
- All numbers below come from `data/k5_addons_2x2_2x3.json` (written by `scripts/summarise_k5_addons.py` from the files
  the production scripts wrote).  Every run used `taskset -c 5-9 nice -n 10` with thread variables $\le 5$ (the
  coordinator's 5-thread budget for this task, inside the owner's 10-thread rule).

## Plan

1. The base families `compressed_circuit_llm_2x{2,3}_class{A,B}` (k = 1..4) stay frozen and untouched.  The $k=5$
   circuit of each reference (2x2: 7, 2x3: 11) goes into a separate add-on family `<base>_k5`, built from the base
   family's own spec (`arch:L{2,3}_it1:<operator|input>:pp2`, i.e. the same loop-archive choices and the same `pp2`
   finishing pass) at $\theta = 5\,dt$, with $dt$ from the frozen k = 1..4 manifests (`Problem(lx)`, as before).
2. Verify at the package bar ($\max|\Delta\psi| < 10^{-10}$, leakage $< 10^{-9}$): certified pruned evaluation with the
   rounding term; independent Aer statevector; random-superposition operator test (seeds 11, 12); class-B global-phase
   check.  Confirm skeleton and counts equal the base k = 1..4 circuits of the same reference.
3. Native exports (same route as notes/011/013) and a local dry run of the package's submission script.

## Code changes (study folder only)

| file | change |
|---|---|
| `src/c2x4/families.py` | four new names in `FAMILY_NAMES`; nothing else |
| `scripts/freeze_family.py` | `--kmin`, `--addon-of <base>`: refuses unless spec, lattice, class and $dt$ equal the base header and every circuit's gate skeleton (names + qubits, angles ignored) and counts (`n_2q`, `n_1q`, `depth_2q`, `ops`) equal those of **all four** k = 1..4 circuits of the same reference; records `addon_of` (base file + sha256) and per-circuit `addon`; refuses to overwrite an existing family file |
| `scripts/eval_family.py` | `--kmin` |
| `scripts/export_quantinuum_family.py` | `--addon`: a family with no frozen counterpart at all; $dt$ and `reference_int` checked against the frozen k = 1..4 manifest of the same $(2B, r)$ when the frozen index has no `dt` key (2x2/2x3); 2x4 path unchanged |
| `scripts/summarise_k5_addons.py` | new: collects every number into `data/k5_addons_2x2_2x3.json` |
| `tests/test_families.py` | new `test_k5_addon_matches_base` (ids, $k$, $\theta=5\,dt$, $dt$, counts, skeleton, one certified state); the 2x2 id test excludes the add-ons |

One slip, caught by the freeze check itself: the first class-A freeze refused because my skeleton hash used `repr` of
the qubit lists, which differ between numpy integers (fresh build) and plain integers (frozen file); the hash now casts
qubits to `int`.  The two class-B files written in that first pass were deleted (uncommitted, seconds old) and all four
families re-frozen with the same hash definition.

## Families (frozen files)

| family | circuits | file | sha256 |
|---|---|---|---|
| `compressed_circuit_llm_2x2_classA_k5` | 7 | `2x2_compression_using_ai_v1/data/families/` | `1b1e8a7742e533f008c1906b3449ca6e9c8508312971d9ad9ef04384bfd085c4` |
| `compressed_circuit_llm_2x2_classB_k5` | 7 | same | `5425dd4a52b792ef55f4d5798c81e00be4ece5fce36b8f71eac775f629775084` |
| `compressed_circuit_llm_2x3_classA_k5` | 11 | `2x3_compression_using_ai_v1/data/families/` | `a89333b2c1458e09b728c1a14d6ad4899c8a9021f241634480c0eb647396efb3` |
| `compressed_circuit_llm_2x3_classB_k5` | 11 | same | `6d1f880e608427f3c64c3ac0ccbfbdb4fd27dd53518dc5307e1a027dfbf4d8dc` |

Ids: `B0_ref06_k5`, `B0_ref43_k5`, `B0_ref30_k5`, `B0_ref21_k5`, `B0_ref17_k5`, `B1_ref14_k5`, `B1_ref07_k5` (2x2);
`B0_ref25_k5`, `B0_ref795_k5`, `B0_ref525_k5`, `B0_ref333_k5`, `B0_ref169_k5`, `B0_ref117_k5`, `B0_ref86_k5`,
`B0_ref70_k5`, `B1_ref57_k5`, `B1_ref29_k5`, `B1_ref27_k5` (2x3).  $dt$: 2x2 $0.24501194722475933$ ($2B=0$),
$0.33194310785049674$ ($2B=2$); 2x3 $0.15644331744992473$, $0.1869734214853983$ — equal to the base headers, and
$\theta = 5\,dt$ exactly for every circuit.  The base files' sha256 equal the values recorded at their native export
(`base_file_unchanged: true` for all four).

## Verification (all computed; nothing in this round is a new Lean statement)

| family | IR 2q (min–max) | equal to base k=1..4 (counts, skeleton) | certified eval: pass, max certified $\lvert\Delta\psi\rvert$, max certified leakage | Aer: pass, max $\lvert\Delta\psi\rvert$, max leakage | superposition seeds 11, 12 | class-B phase: max $\lvert\varphi_{\rm meas}-\varphi_{\rm pred}\rvert$ |
|---|---|---|---|---|---|---|
| 2x2 A k5 | 245–245 | 7/7, 7/7 | 7/7, $2.0\times10^{-13}$, $3.6\times10^{-26}$ | 7/7, $4.3\times10^{-15}$, $6.5\times10^{-32}$ | 14/14 pass, max $\lvert\Delta\psi\rvert$ $4.3\times10^{-15}$ | (class A: $\varphi=0$) $3.9\times10^{-15}$ rad |
| 2x2 B k5 | 55–162 | 7/7, 7/7 | 7/7, $1.3\times10^{-13}$, $1.7\times10^{-26}$ | 7/7, $3.2\times10^{-15}$, $2.0\times10^{-31}$ | 0/14 (expected-failure control; min $\ell_2$ error 0.93) | $3.6\times10^{-15}$ rad |
| 2x3 A k5 | 871–871 | 11/11, 11/11 | 11/11, $9.2\times10^{-13}$, $8.3\times10^{-25}$ | 11/11, $8.4\times10^{-15}$, $1.3\times10^{-30}$ | 22/22 pass, $2.8\times10^{-15}$ | (class A) $5.9\times10^{-14}$ rad |
| 2x3 B k5 | 309–465 | 11/11, 11/11 | 11/11, $4.2\times10^{-13}$, $1.7\times10^{-25}$ | 11/11, $7.2\times10^{-15}$, $1.7\times10^{-31}$ | 0/22 (expected-failure control; min $\ell_2$ error 1.23) | $5.6\times10^{-14}$ rad |

- Certified eval = `eval_family.py --kmin 5 --kmax 5 --prune-tau 1e-15` (certified pruned simulation, rounding and
  pruning bounds included, notes/006) plus the term-level operator check at $\theta=5\,dt$; files
  `<lattice>/data/c2x<L>/eval_arch_L<L>_it1_<operator|input>_pp2_k5_pruned.json`.
- Aer = `verify_aer_family.py --superposition-seeds 11,12` through the loader (`get_family`), qiskit 2.5.2 /
  qiskit-aer 0.17.2, statevector double precision, fusion off, $dt$ from `Model(L).reference(4, 2B).dt` (independent of
  the manifests; `dt_consistent: true`); files `<lattice>/data/c2x<L>/aer_<family>.json`.  The superposition test is an
  operator test: class A passes it; class B is valid only on its own reference (notes/009) and fails it, as designed.
- Per-reference skeleton/count equality was enforced by `freeze_family.py` and re-checked independently by the
  summariser and by `test_k5_addon_matches_base`.  Study tests: 29 passed (`pytest -q 2x4_compression_using_ai_v1/tests`).

## Native exports (route of notes/011/013: `cz` -> `cp(pi)`, pytket level 0 for H2-2, Q1 + Q1L)

`export_quantinuum_family.py --addon --frozen-dir data/quantinuum/circuits_2x{2,3}` (pytket venv
`~/.local/share/su2qc-quantinuum/venv`), into `2x2_compression_using_ai_v1/data/families/native_2x2/<family>/` and
`2x3_compression_using_ai_v1/data/families/native_2x3/<family>/`.  Q1 = dense Aer statevector of the native circuit
against the package's exact coarse state (bar $10^{-10}$ / $10^{-9}$), plus native vs IR state and JSON/QASM round trips;
Q1L = the package's conversion proof with its rounding bound $B$.  `CAL_zeros` / `CAL_x0` copied byte for byte from the
frozen k = 1..4 folder of the same lattice (checked).

| family | ZZ | PhasedX | depth-2q | HQC/shot | Q1 (max $\lvert\Delta\psi\rvert$ vs exact) | Q1L (max $B$) | $f$ gate-only H2-2 |
|---|---|---|---|---|---|---|---|
| 2x2 A k5 | 245 | 622–623 | 188 | 0.6384–0.6386 | 7/7 ($5.9\times10^{-15}$) | 7/7 ($0$) | 0.79286–0.79289 |
| 2x2 B k5 | 55–162 | 137–413 | 45–137 | 0.1614–0.4306 | 7/7 ($7.4\times10^{-15}$) | 7/7 ($9.8\times10^{-15}$) | 0.854–0.941 |
| 2x3 A k5 | 871 | 2 415–2 416 | 611 | 2.2650–2.2652 | 11/11 ($1.1\times10^{-14}$) | 11/11 ($2.7\times10^{-14}$) | 0.44504–0.44505 |
| 2x3 B k5 | 309–465 | 822–1 246 | 170–290 | 0.8224–1.2192 | 11/11 ($7.7\times10^{-15}$) | 11/11 ($1.7\times10^{-14}$) | 0.644–0.742 |

- Native ZZ = IR two-qubit count in every circuit; native ZZ and PhasedX counts equal the base export's k = 1..4
  circuits of the same reference (`native_counts_equal_base_k1_4: true`, all four families).
- $B = 0$ for 2x2 class A is a computed value, not a missing one: the Q1L record compares 136 angle gates and 42
  one-qubit unitaries and finds no angle changed by the half-turn conversion (`n_rounded_gates: 0`); the base family's
  `B0_ref06_k4` export has the same zero.
- Read-only cross-check against the other agent's frozen k = 5 folders (state at 2026-10-28 22:39 UTC): for all 7 (2x2)
  and 11 (2x3) ids a frozen manifest exists, with equal $dt$, $k$, $2B$, reference and `reference_int`.

## Dry runs (`scripts/quantinuum_submit.py --dry-run --all --records-only --circuits <export dir> --out /tmp/...`, local, offline)

200 shots per circuit and per calibration circuit; session records copied to `<lattice>/data/c2x<L>/dryrun/session_class<A|B>_k5.json`;
formula $\mathrm{HQC}_{\rm job} = 5 + 200\,(N_{1q}+10N_{2q}+5N_m)/5000$.

| family | jobs (circuits + CAL) | shots | formula HQC total | circuits only |
|---|---|---|---|---|
| 2x2 A k5 | 9 (7 + 2) | 1 800 | 948.64 | 929.00 |
| 2x2 B k5 | 9 (7 + 2) | 1 800 | 506.96 | 487.32 |
| 2x3 A k5 | 13 (11 + 2) | 2 600 | 5 064.44 | 5 038.40 |
| 2x3 B k5 | 13 (11 + 2) | 2 600 | 2 325.32 | 2 299.28 |

All jobs `RECORD ONLY (not executed)`; each session's `index_sha256` equals the export's `index.json`.

## Wall time

Certified evaluation: 1.0–18.9 s per family (construction cache); freezing: seconds.  Aer (incl. the superposition test): 2x2 2.6–2.9 s, 2x3 class B 116 s, class A 240 s.  Native export: 2x2 19–28 s per
family; 2x3 class B 772 s, class A 1 466 s (24.4 min, under the 30-minute rule, on 2 threads while the class-B export
and another agent's jobs ran).

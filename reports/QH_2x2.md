# Gate QH_2x2 — 2x2 native circuits as Helios Guppy/HUGR programs on Selene (Quest, IdealErrorModel), offline (prompts/35 T6)

Status: **FAIL**.  Generated from `validation/QH_2x2.json`.

What PASS means: "the frozen native circuits survive the Helios Guppy/HUGR route offline and reproduce their exact distributions on Selene; not a Helios device or Helios-1E statement".

Route: frozen pytket JSON -> guppy.load_pytket inside a @guppy main that allocates the qubits, calls it, records result('c', bits) and discards the qubits -> main.compile() (HUGR package) -> selene_sim.build -> run_shots(Quest, IdealErrorModel).  guppylang 0.21.16 `main.compile()` lists only the extensions it resolves itself; load_pytket (tket 0.13.2 CompilationState.from_tket1) emits PhasedX and ZZPhase as ops of `tket.qsystem.helios`, which neither selene-hugr-qis-compiler 0.2.11 nor tket's own registry carry, so the package is written with that extension embedded (tket_exts 0.12.4 `qsystem_helios()`), the way tket's CircBuild.finish_package packages it; the raw compile() output is recorded by its sha256.

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| H1 28/28 HUGR packages written with sha256 | {'written': 9, 'of': 28} | 28 | FAIL |
| H2 Selene counts: per-state 5 sigma test 0 failures and fraction outside the exact support 0 on every circuit; bit order fixed by CAL_x0 (X on qubit 0 -> key 1) | {'ran': 9, 'of': 28, 'failures': 0, 'max_outside': 0.0, 'max_z': 2.805713919849029, 'CAL_x0_counts': {'1': 10}, 'errors': {}} | 0; 0; key 1 | FAIL |
| H3 the HUGR -> pytket round-trip field present (either form) | {'B0_ref06_k1': 'not available in tket 0.13.2 (package route: to_tket1() of the package returns a 0-qubit circuit with 0 commands (the entry point allocates its qubits; the loaded pytket function is not extracted); circuit route: RuntimeError:     1: OpaqueOp:tket.qsystem.helios.ZZPhase in Node(10) requires extension tket.qsystem.helios, but it could not be found in the extension list used during resolution. The available extensions are: arithmetic.conversions, arithmetic.float, arithmetic.float.types, arithmetic.int, arithmetic.int.types)', 'B0_ref06_k2': 'not available in tket 0.13.2 (package route: to_tket1() of the package returns a 0-qubit circuit with 0 commands (the entry point allocates its qubits; the loaded pytket function is not extracted); circuit route: RuntimeError:     1: OpaqueOp:tket.qsystem.helios.ZZPhase in Node(10) requires extension tket.qsystem.helios, but it could not be found in the extension list used during resolution. The available extensions are: arithmetic.conversions, arithmetic.float, arithmetic.float.types, arithmetic.int, arithmetic.int.types)', 'B0_ref06_k3': 'not available in tket 0.13.2 (package route: to_tket1() of the package returns a 0-qubit circuit with 0 commands (the entry point allocates its qubits; the loaded pytket function is not extracted); circuit route: RuntimeError:     1: OpaqueOp:tket.qsystem.helios.ZZPhase in Node(10) requires extension tket.qsystem.helios, but it could not be found in the extension list used during resolution. The available extensions are: arithmetic.conversions, arithmetic.float, arithmetic.float.types, arithmetic.int, arithmetic.int.types)', 'B0_ref06_k4': 'not available in tket 0.13.2 (package route: to_tket1() of the package returns a 0-qubit circuit with 0 commands (the entry point allocates its qubits; the loaded pytket function is not extracted); circuit route: RuntimeError:     1: OpaqueOp:tket.qsystem.helios.ZZPhase in Node(10) requires extension tket.qsystem.helios, but it could not be found in the extension list used during resolution. The available extensions are: arithmetic.conversions, arithmetic.float, arithmetic.float.types, arithmetic.int, arithmetic.int.types)'} | present | FAIL |
| H4 hqc == 0 | 0 | 0 | PASS |

| circuit | shots | s/shot | max z | outside | reference hits | round trip |
|---|---|---|---|---|---|---|
| B0_ref06_k1 | 1599 | 0.09214 | 0.9841 | 0.0 | 1407 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref06_k2 | 1599 | 0.1024 | 2.759 | 0.0 | 981 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref06_k3 | 1599 | 0.07555 | 2.122 | 0.0 | 480 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref06_k4 | 1599 | 0.07792 | 2.806 | 0.0 | 194 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref17_k1 | 1599 | 0.1144 | 1.699 | 0.0 | 1413 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref17_k2 | 1599 | 0.1271 | 2.071 | 0.0 | 955 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref17_k3 | 1599 | 0.1098 | 1.749 | 0.0 | 500 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref17_k4 | 1599 | 0.0912 | 2.24 | 0.0 | 170 | not available in tket 0.13.2 (package route: to_tket1() of t |
| B0_ref21_k1 | 1599 | 0.1269 | 0.9177 | 0.0 | 1404 | not available in tket 0.13.2 (package route: to_tket1() of t |

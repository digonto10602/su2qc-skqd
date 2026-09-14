# Execution log

| date | prompt | gate | agent / model | result | commit | notes |
|---|---|---|---|---|---|---|
| 2026-09-14 | (package assembly, cloud sandbox) | E1, E2, E3, S1, CS | Claude Fable 5.1 (cloud session) | all PASS | see git log | Qiskit/CUDA-Q not installable in the sandbox (PyPI blocked): circuit translators written, numpy reference verified; laptop gates L2–L5 pending |
| 2026-09-14 | (independent audit, cloud session) | E1–S1, circuits | reviewer (Opus, independent rebuild of 2x2 in the 160 000-dim space) | physics confirmed; fixes applied: CUDA-Q kernel via real source file + endianness test, Table-3 device-row saturation now marked with the realised |B|, Kato–Temple denominator guard, CIPSI denominator magnitude, locality check in `localize`, static counts computed in E3, CI runs E1, README numbers sourced | see git log | audit findings recorded here for the record |

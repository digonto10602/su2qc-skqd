# 35b — Ruling on the 2x4 STOP: the state bar is measured, not bounded; a second (structured) source for 2x4; the k >= 2 builds wait for one GPU job

executor: executor-opus   effort: high
time budget: laptop about half a day (the structured-source k = 1 build and the 2x3 cross-check); no new compute
on the opt-3 k >= 2 builds until section 4's decision; 0 QPU s, 0 HQC, no push, no CI request
machine: laptop + one Perlmutter GPU job (`QV_2x4_01`, requested by the coordinator after the campaign-33
must-run set / the maintenance, prompts/35 R4)
date: 2026-10-13   planner: Fable 5.1 (high)   prompt number: 35b (addendum to prompts/35 and 35a; re-rules
35a R2 (iii) and 35 R2 for 2x4 only)

Trigger: `validation/BLOCKED.md` and `validation/Q0P_2x4.json data.Q1L` on branch `q35` (d5ccb68): on all 19
built 2x4 circuits, (i) skeleton identical to 4.4e-15 half-turns and (ii) one-qubit products to 8.0e-15
**PASS**; (iii) the linear bound $B = \tfrac{\pi}{2}\sum_g|\Delta a_g|$ is 4.96e-9 to 4.98e-9 against 1e-10
**FAIL**, from 66 925 to 67 236 angles per circuit that qiskit opt-3 leaves at a multiple of $1/4$ half-turn
plus a residue of 1e-14 to 1e-12 and pytket snaps to the multiple (largest single difference 8.0e-13).  The
planner's 35a expectation of 1e-16 residues was wrong; the bound was never going to settle a 5e5-gate circuit.

## 1. The physics fact the ruling rests on (from the files, not from the STOP)

The 1e-10 state bar at 2x4 was **never met by any compiled 2x4 circuit, before any Quantinuum conversion**:
`validation/S2_2x4.json data.gpu_validation.compiled["B0_ref0_k1|all_to_all"]` gives, for the qiskit opt-3
all-to-all circuit (279 083 instructions, 69 688 CZ) on the Perlmutter GPU, `max_abs_difference_vs_coarse_states`
5.80e-9 raw and **1.528e-9 phase-aligned** (leakage 1.1e-12), while the structured IR of the same step is
1.07e-13 from the exact state on the sparse path (`data.circuits.circuits_4_exact.coarse_steps.B0_ref0_k1.
max_deviation_vs_coarse_states`).  Gate S2_2x4's C6 checked leakage only; no amplitude bar was ever applied
to a 2x4 compiled circuit.  So the 2x4 native family's distance to the exact state is expected to be of order
1e-9 whatever pytket does — the snapping ($B \le 5\times10^{-9}$ on top of the source's own 1.5e-9) is the
smaller of two effects, and the larger one is qiskit opt-3's one-qubit resynthesis (the same mechanism K0
measured at 4.9e-5 on the CZ-basis 2x3 circuit, prompts/33 section 1.1) plus float accumulation over 5e5 gates.
At 2x3 (5e3 gates) both effects stay at 2e-13 (`validation/Q0P_2x3.json` Q1, `validation/C3_AER.json` P1).

## 2. Rulings

**R1 — the bar stays and is measured.**  Candidate (a).  The physics bar for every lattice is the one of
prompts/26: the frozen native circuit's state against `krylov.coarse_states`, $\max|\Delta\psi| < 10^{-10}$
after global-phase removal, leakage $< 10^{-9}$.  At 2x4 it is measured on the Aer GPU (section 4), as the
2x3 one was measured dense on the laptop.  No bound replaces a measurement; no probabilistic bound (candidate
(c)) is a criterion — the incoherent estimate $\tfrac{\pi}{2}\sqrt{\sum_g \Delta a_g^2}$ may be recorded as
information, labelled "estimate, not a bound".

**R2 — Q1L is the conversion proof, (i) + (ii) only.**  35a's (iii) is withdrawn as a criterion.  Q1L PASSES
on the 19 built circuits (4.4e-15 / 8.0e-15): the pytket circuit **is** the opt-3 source with its angles
canonicalised, and nothing else — that is what a local proof can show.  $B$ stays in the JSON as
`rounding.state_bound_B` and becomes a **falsifiable consistency criterion of the GPU job** (section 4): the
measured distance between the native circuit and its own source circuit must be $\le B + 10^{-12}$; if it is
not, the conversion or the bound is wrong and the job STOPs.  Candidate (b) (snapping the source first) is
not adopted as a second convention: substituting the read-back angles in (ii) already is that comparison.

**R3 — `validation/Q0P_2x4.json` is honest until the measurement exists.**  prompts/35 R2's sentence "Q0P_2x4
can PASS on Q1L" is **reversed**: a local proof that cannot place the state inside the bar is not a PASS.
Status `FAIL` with `status_reason: "Q1 (state vs coarse_states) not measured on the laptop; deferred to
QV_2x4_01 (GPU); Q1L conversion proof PASS 19/19"`; `what_pass_means` says so; the LOG row says FAIL.
`validation/BLOCKED.md` is closed with a pointer to this prompt (the STOP was correct and is resolved by a
ruling, not by a fix).

**R4 — a second source for 2x4: the structured IR, no qiskit opt-3.**  Because the source itself is 1.5e-9
from exact, a Quantinuum-native 2x4 family that can meet 1e-10 must not pass through qiskit opt-3.  Build
`--source structured`: the exact structured IR of `circuit_set(4)` (gates at $k=1$: cx 71 544, ry 70 308,
unitary1q 388, p 40, cp 4, x 4 — `S2_2x4.json data.compile.compile_4_exact_a2a_k1.circuits.B0_ref0_k1.ir_gate_counts`)
fed to `ir_to_pytket` extended with `cx` -> `CX`, `p` -> `U1`, `cp` -> `CU1`, `unitary` (1q) -> `Unitary1qBox`
(tests: each new rule against `Circuit.get_unitary()` and `circuits_qiskit.statevector` on 1-2 qubits,
1e-12, including the half-turn factor and the control/target order of `CU1`), then `compile_native` at level 0
(DecomposeBoxes + rebase + squash; pytket's TK1 decomposition of a 1q unitary is float-exact, and the structured
IR's Clifford angles are exact multiples of $1/4$, so `rounding.n_rounded_gates` is expected far below 67 000 —
record it).  Q1L (i)+(ii) against the structured IR (the skeleton is now the `cx`/`cp` sequence as ZZPhase
plus the rebase's fixed one-qubit frame; (i) compares the two-qubit pairs and order, (ii) the per-qubit
products between them, as before).  Files under `data/quantinuum/circuits_2x4/` with `source` in the id
suffix (`<id>.opt3.*`, `<id>.structured.*`) and in the manifest; counts and HQC per shot for both.  Expected
ZZ count about 71 548 (cx + cp) against 69 688 (planner arithmetic; measured by the build).  The **frozen 2x4
family is chosen by the measurement** (section 4), not now.

**R5 — the 2x3 cross-check of the structured source (laptop, 20 qubits, cheap).**  Before any 2x4 build:
`B0_ref25_k1` from the structured 2x3 IR (`cx 2588, unitary 144, ry 2164, p 29, cp 2, x 3`, prompts/33 IR-L0)
through the new path, dense statevector against `krylov.coarse_states` and against the frozen opt-3 native
circuit; record max abs(dpsi) (expected 1e-13-class for both), ZZ count (expected 2590 vs 2158) and the
rounding block.  This validates the new `ir_to_pytket` rules on a lattice where the dense check exists.
**The 2x3 frozen family does not change** (prompts/26 convention): this is a cross-check, written to
`validation/Q0P_2x4.json data.structured_source_check_2x3`.

**R6 — the k >= 2 builds.**  Opt-3 source: **paused** (not resumed) — 45 circuits of 6-h laptop work for a
source that may not be frozen.  Structured source: build $k=1$ only (15 circuits + 2 calibration) now.  Both
sources' $k \ge 2$ resume **after `QV_2x4_01`** has chosen the source (section 4); if the owner wants the
laptop idle time used earlier, the structured $k \ge 2$ build may go first (it is the one expected to pass),
with the opt-3 $k \ge 2$ build dropped unless the measurement favours opt-3.  Record the pause in the index
(`built_k`, `paused_by: "prompts/35b R6"`).

## 3. The 2x2 and 2x3 tiers are untouched

The 2x2 Q1 is the dense measurement on every circuit (prompts/35 3.2) and already contains any snapping; the
2x2 bound was 2.7e-13 (executor).  Nothing in 35 / 35a changes for 2x2 and 2x3, and the executor continues them.

## 4. The GPU job that decides: `QV_2x4_01` (generic slots `QV_2x4_01..08`)

Replace the four `QV_2x4_K*` tokens of 35a R1 by **eight generic slots** `QV_2x4_01..08` (class 3, `01:00:00`,
1 GPU, env `skqd`, script `scripts/quantinuum_lattice_tests.py --lattice 4 --tier gpu-verify --slot NN`),
content in `ci/parts/QV_2x4_NN.json` (the C4_PART pattern; `ci/allowed_jobs.q35` with eight lines; the
campaign-33 token indices unchanged — criterion kept).  Each slot holds the statevector runs its content
lists, sized from the manifests at $2.32\times10^{-4}$ s per instruction (`S2_2x4.json data.gpu_validation.
telemetry_summary.s_per_instruction`) under the 0.75 share of 60 min; `qpy13` bundles of every circuit it runs
are committed (the native circuits via `pytket_to_ir` -> `ir_to_qiskit`; the structured IR source via
`ir_to_qiskit` as IR-L0 is frozen in campaign 33; the opt-3 source is the existing prototype transpile).

**Slot 01 — the decision job** (6 statevector runs, planner arithmetic about 13 min): for `B0_ref0_k1` and
`B1_ref0_k1`, (1) the opt-3-source native circuit, (2) its opt-3 source circuit (for `B0_ref0_k1` this must
reproduce `S2_2x4.json`'s 1.528e-9 phase-aligned to 1e-12: same qiskit 1.4.3 / Aer 0.15.1, a reproducibility
criterion), (3) the structured-source native circuit, (4) the structured IR itself — each against
`krylov.coarse_states` (max abs(dpsi) up to phase, leakage), plus native-vs-own-source distances against $B$
(R2).  Per circuit the JSON records the four numbers; criteria of slot 01: V1 every run completed on the GPU
with the policy telemetry; V2 the S2_2x4 reproduction; V3 native-vs-source $\le B + 10^{-12}$ for both
sources (else STOP, conversion or bound wrong); V4 (the physics bar) **the frozen source is the one whose
native circuits satisfy $\max|\Delta\psi| < 10^{-10}$ and leakage $< 10^{-9}$ on both circuits; if both do,
the one with the smaller maximum; if neither does, STOP: the planner rules on the 2x4 bar in writing with the
four measured numbers (never the executor).**  Slots 02-08 then carry the chosen source's remaining $k=1$
circuits and, if built, $k \ge 2$, with the per-state noiseless test of prompts/35 3.1(g) on each.

Prediction on record (planner arithmetic, to be falsified by slot 01): opt-3-source native between 1e-9 and
6.5e-9 (source 1.5e-9 plus up to $B$); structured-source native of order the 2x3 value, 1e-13 to 1e-12, if
float accumulation over 1.4e5 IR gates stays linear in the per-gate 1e-16 — and this is exactly what the
measurement will tell.

## 5. Pass criteria (machine-checkable)

- `validation/Q0P_2x4.json`: `status == "FAIL"` with the `status_reason` of R3 until slot 01 is harvested;
  `data.Q1L` PASS on every built circuit of both sources with `rounding` recorded; `data.structured_source_check_2x3`
  present with its three numbers; `data.index.built_k` and `paused_by` as in R6; tokens `QV_2x4_01..08` in
  `scripts/gate_tokens.json`, `ci/parts/QV_2x4_01.json` listing the six runs of slot 01, campaign-33 token
  indices unchanged, `pytest -q tests` and `check_package.py` PASS, pins unchanged.
- `validation/BLOCKED.md`: the 2x4 entry closed with "resolved by prompts/35b (ruling)".
- After slot 01 (later, coordinator): `validation/QV_2x4_01.json` V1-V4; then `Q0P_2x4.json` is re-assembled
  with the measured Q1 of the chosen source and may PASS.

## 6. STOP conditions

- Any new `ir_to_pytket` rule failing its 1-2-qubit unit test after two attempts: BLOCKED.md, planner.
- R5's 2x3 cross-check giving max abs(dpsi) $> 10^{-10}$ for the structured path: STOP before any 2x4 build
  (the new rules, not 2x4, would be wrong).
- Slot 01's V3 or V4 failing: STOP as written in section 4.

## LOG row

| 2026-10-13 | prompts/35b_2x4_exactness_ruling.md | Q0P_2x4 (Q1 / Q1L), QV_2x4_01..08 | planner-fable (Fable 5.1, high) | ruling, no gate run | commit | — |

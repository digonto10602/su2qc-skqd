# 35a — Addendum to prompts/35: Q2 corrected, the pytket angle rounding, the 2x2 T3 cap, level-0-only at 2x4

executor: executor-opus   effort: high
time budget: inside the prompts/35 budget; no new compute beyond the re-derivations below
machine: laptop (0 QPU s, 0 HQC, no push, no CI request)
date: 2026-10-13   planner: Fable 5.1 (high)   prompt number: 35a (addendum; prompts/35 stays in force for
everything not re-ruled here)

Trigger: the executor's three findings on branch `q35` (WIP e5503b8).  Rule 1 and rule 2 unchanged; no bar
of prompts/35 is loosened — one bar (Q1L) is restated so that it measures what it was meant to measure.

## R1 — Q2 is corrected: the coarse-step gate count does not depend on $k$

`circuit_set(Lx)` calls `CircuitFactory.coarse_step(r, k, dt)`, which builds **one** step at the angle
$k\,dt$ (`circuits_ir.coarse_step`, L898); the $k$ repetitions in prompts/35 Q2 confused this with the
H0 repetition $U^r$ of `h0_build_circuits.repeated_coarse_step` — the planner's error.  The 2x3 record already
says so (`validation/Q0P_2x3.json` Q2: 2158 on all 44).  **Q2 (every lattice):** `rzz_before` recorded per
circuit and **equal to the family's $k=1$ value on every circuit** (per reference and across references, as
at 2x3); the frozen ZZ count $\le$ `rzz_before`.  The executor's implementation is the ruling; delete the
"$k\times$" field from the JSON, do not keep a relation that holds on 7 of 28 by accident.

Consequence for `QV_2x4`: every 2x4 circuit has the same instruction count, so the GPU cost per circuit is
the same for every $k$.  Re-derive the prediction from the **manifests** (instruction count of the
`pytket_to_ir` -> `ir_to_qiskit` circuit) times the measured $2.32\times10^{-4}$ s per instruction
(`validation/S2_2x4.json data.gpu_validation.telemetry_summary.s_per_instruction`) and write it into
`scripts/gate_tokens.json estimate_minutes`.  Planner arithmetic at the prompts/35 estimate of about 130 s
per circuit: 15 circuits per token = about 33 min; the 45 circuits with $k \ge 2$ = about 1.6 GPU-h, **not 4.9**.
Define four tokens `QV_2x4_K1`, `QV_2x4_K2`, `QV_2x4_K3`, `QV_2x4_K4` (15 circuits each, same script with
`--k`), `ci/allowed_jobs.q35` with four lines; `QV_2x4` of prompts/35 is renamed `QV_2x4_K1`.  Owner item 4
of prompts/35 section 6 now reads "about 1.6 GPU-h for K2-K4".

## R2 — pytket's angle canonicalisation: the Q1 bar stays, Q1L is restated with a rigorous bound

Finding: pytket stores any angle within $10^{-11}$ half-turns of a multiple of $1/4$ as that multiple
(`Rz(0.5 + 3\times10^{-12})` reads back as 0.5).  This is a **perturbation of known size**, not a conversion
error, and it is already inside the 2x3 Q1 result (2.09e-13 was measured on the read-back circuits).

Effect on the state, exactly: for one rotation $R(\theta) = e^{-i\theta P/2}$ with $\theta$ in radians,
$\|R(\theta+\delta) - R(\theta)\|_{\rm op} = 2|\sin(\delta/4)| \le |\delta|/2$; with $\delta = \pi\,\Delta a$
($\Delta a$ in half-turns) this is $\le \tfrac{\pi}{2}|\Delta a|$.  For $\mathrm{PhasedX}(a,b) = R_z(b)R_x(a)R_z(-b)$
the bound is $\tfrac{\pi}{2}(|\Delta a| + 2|\Delta b|)$; for ZZPhase and Rz, $\tfrac{\pi}{2}|\Delta a|$.  Products
of unitaries obey the triangle inequality, $\|U - U'\|_{\rm op} \le \sum_g \|U_g - U'_g\|_{\rm op}$, hence
$$\max_s|\Delta\psi_s| \le \|\Delta\psi\|_2 \le B := \frac{\pi}{2}\sum_{g}\big(|\Delta a_g| + 2|\Delta b_g|\big),$$
with $\Delta a_g, \Delta b_g$ the **observed** per-gate differences between the IR angle (in half-turns) and the
angle read back by `pytket_to_ir`.  Worst case per rounded gate $\tfrac{\pi}{2}\times10^{-11} = 1.6\times10^{-11}$;
in practice the differences are the float residue of the transpiler ($\sim10^{-16}$), so $B$ is expected many
orders below the bar — **compute it, do not assume it**.

**Q1L (restated, every lattice; binding):**
- (i) the two-qubit skeleton (ordered qubit pairs, gate order) is identical and every two-qubit angle agrees
  with the IR to $|\Delta a| \le 10^{-11}$ half-turns (pytket's own canonicalisation tolerance, recorded as such);
- (ii) between consecutive two-qubit gates the per-qubit one-qubit products agree to $10^{-12}$ **with the
  read-back angles substituted into the IR reference** (this isolates the conversion: PhasedX order, half-turn
  factor, ZZ sign, gate order — what Q1L exists to prove);
- (iii) the rounding bound $B$ of the circuit, computed from the observed differences, satisfies
  $B < 10^{-10}$ — the Q1 state bar, unchanged; record per circuit `rounding: {n_rounded_gates, max_abs_delta,
  sum_abs_delta, state_bound_B}`, and also the raw segment residual of prompts/35 (the 8.3e-13 figure) as
  `segment_residual_raw`, information.
Q1L passes iff (i), (ii), (iii).  Where Q1S (statevector) is also available, (iii) is confirmed by the measured
$\max|\Delta\psi|$, which must be $\le B + 10^{-12}$ — a consistency criterion, recorded.  At 2x2, where the
dense Q1 statevector check runs on every circuit, Q1 stays exactly as in prompts/35 (bar $10^{-10}$) and the
`rounding` block is added for information.

## R3 — the 2x2 T3 plan: f-cells on everything, plan-of-record on four scenarios

Measured rate about 25 ms per shot (executor, `s_per_shot`).  Planner arithmetic on it: f-cells
$28\times2000\times11 = 616\,000$ shots = 4.3 h; one plan-of-record run $133\,907$ shots = 0.93 h; eleven of
them 10.2 h; total 14.5 h against the 8-h cap.  Ruling:
- **f-cells: keep all 28 circuits x 11 scenarios** (this is the "all circuits" content of the owner's request).
- **plan-of-record SKQD: E1, E3, E4, E5b, in that order** (the H2-2 spec, the H2-2E emulator set, the Helios-1E
  set, memory mid) — the cap for T3 becomes **10 h** in background chunks of $\le 30$ min (the 8 h was planner
  arithmetic from an upper-bound rate; the measured rate decides; 4.3 + 4 x 0.93 = 8.0 h predicted, 10 h
  allows the E5b rate to differ from E1's as it does on the GPU, 5.5x at 2x3 per prompts/33b R1 — if the
  measured E5b rate puts the run past 10 h, E5b is dropped and recorded).
- **dropped (plan-of-record only): E7(0.10; 2x2 counts), E2, E6a, E6b, E6c, E5a, E5c**, each recorded in
  `validation/QN_2x2.json data.plan_of_record.<sid>.status = "dropped by prompts/35a: <predicted h>"`.  E2 and
  E6 are E1 with scaled parameters and E5a/c bracket E5b; their f-cells carry the per-circuit information.
- N4 of prompts/35 applies to the runs that ran; `scenarios_run` lists them.

## R4 — level 0 only at 2x4, scripted

pytket level 2 did not finish inside 30 min on a 2x4 circuit; the 2x3 frozen level was 0 anyway and level 2
gave the same ZZ count there (`validation/Q0P_2x3.json data.frozen.frozen_levels = [0]`, Q2 "level 2 [2158]").
Ruling: `quantinuum_build_circuits.py --levels 0` for `--lattice 4` (default for 4; `0,2` for 2 and 3); the
manifest records `levels_attempted: {"0": {...counts...}, "2": "capped at 1800 s on <id> (prompts/35a R4)"}`
with the measured seconds of the capped attempt on the one circuit where it was tried; `index.json
frozen_levels = [0]`; the selection rule text gains "level 2 not attempted at 2x4 (R4)".  No hand-written
note anywhere.

## R5 — the smaller items

- Selene rate 0.139 s/shot under load vs 0.085 sized: size QH_2x2 on the rate measured **immediately before**
  the run, shots per circuit $= \min(2000, \lfloor 3600/(28\,s_{\rm shot})\rfloor)$, floor 500; record
  `load_average_before`, the rate and the shots achieved (the per-state 5 sigma test is valid at any $N$).
- The E7 test may be skipped in the pecos venv with the reason string ("E7 needs the Aer noise builder of
  `coding`"); it must run in `coding`.
- The HUGR packaging fix (`tket.qsystem.helios` extension): allowed **in the pecos venv only**, recorded as a
  stack-check block (`pip freeze` of the pecos venv before and after, the package and version added, the error
  it fixed) in `validation/QH_2x2.json data.stack`; nothing in `coding`, nothing in the quantinuum venv.

## LOG row

| 2026-10-13 | prompts/35a_quantinuum_tests_rulings.md | Q0P_2x2/2x4 Q2 + Q1L, QN_2x2 T3 plan, QV_2x4_K1..K4, QH_2x2 | planner-fable (Fable 5.1, high) | rulings, no gate run | commit | — |

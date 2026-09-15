# 11 — S2 planner decision (2026-09-15): the exact coarse step cannot meet the CZ budget in this encoding; measure the floor, then the owner decides
executor: executor-opus   effort: high (xhigh on the second attempt)   planner: planner-fable (max)
time budget: 1 day; each run < 30 min   machine: laptop (CPU)

> Written by planner-fable at max effort after gate S2 (prompt 06) returned FAIL on the budget criteria only
> (`validation/S2.json`, commits 5d60461, e6275bb).  Diagnostics: `reports/S2_escalation_analysis.md`,
> `data/S2_escalation_experiments.json` (script `scripts/s2_escalation_experiments.py`).

## Failure (validation/S2.json)
- 2x2: CZ per coarse step routed on heavy-hex d=3: 618 (all-to-all 256), criterion <= 250
- 2x3: CZ per coarse step routed on heavy-hex d=5: 5477 (all-to-all 2164), criterion <= 500
- correctness criteria PASS: max deviation 1.87e-14, leakage 4.5e-14, 20 tests

## Diagnosis
The structured circuits are exact and already 90x (routed) / 139x (all-to-all) cheaper than the L3 baseline.
What remains is intrinsic to exact block unitaries in the local encoding: every term is a product of
multiplexed rotations, one per (schedule round x flip pattern), and a multiplexed rotation with c controls
costs 2^c CNOT.  The angle of a hopping rotation depends on the SU(2) recoupling data of both vertices
(other flux bits, intertwiner label) and on the Jordan-Wigner parity, so c = 2-4 at 2x2 and 4-7 at 2x3
(`per_term_structure` in S2.json); the interior-corner plaquette needs 17 rotations with c up to 7.
Three levers were measured (`reports/S2_escalation_analysis.md`):
1. Compilation: heavy-hex routing costs 2.4-2.5x all-to-all and a seed sweep recovers < 5 %; a square
   lattice costs 1.8x (2x2: 454, 2x3: 4026).  Even all-to-all (2164 at 2x3) is 4.3x the budget.
2. Term ablation at 2x3 (S1 production budget, emulated): dropping the diagonal terms saves 20 CZ and
   changes nothing; dropping only plaq1 keeps recall >= 0.937 at f = 0.1 in both sectors but leaves
   ~3800 routed CZ; dropping both plaquettes fails the S1 criterion in B = 1 (0.895).
3. Budget with the yield rule: f = (1 - eps)^N: 618 CZ gives f = 0.29 / 0.16 at eps = 2e-3 / 3e-3 (a 2x2
   calibration run H0 is feasible on a Heron-class device as is); 2164 CZ gives f = 0.115 only at eps = 1e-3
   on an all-to-all device; 5477 CZ gives f = 0 on any device.
Conclusion: no combination of compilation and term ablation brings the exact 2x3 coarse step within 500
routed CZ on heavy-hex.  Option (ii) of prompt 06 (a different vertex layout) cannot remove the physical
dependence of the angle on both vertices' flux, so it can at best save one control per rotation (2x).

## What is decided now (no owner input needed)
A. Gate S2 stays FAIL with its criteria unchanged; `validation/S2.json` is the record of the exact circuits.
B. The one remaining technical lever is to give up exactness of the local exponential while keeping exact
   gauge invariance: SKQD needs the circuits only to generate the support (the classical step diagonalizes
   the exact H on it, and E_R >= E_0 holds for any support), so a rotation between the *same* pairs of
   codewords with a *fixed* angle per (round, flip pattern) is a legitimate generator provided the recall
   criterion of S1 is re-established for it by emulation.  Its cost floor must be measured before the owner
   chooses among the options below.

## Steps (executor)
1. In `src/skqd/circuits_ir.py` add `angle_mode` to `structured_term_gates` / `CircuitFactory`
   (`"exact"` = current behaviour and default; `"fixed"` = the same two-level rotations and the same
   validity/pair-selection controls, but the angle-selecting controls removed and one angle per
   (round, flip pattern), theta_eff = theta x mean of the distinct |elements| merged into that rotation;
   record the merged elements).  The circuit must still map codewords to codewords exactly: verify leakage
   of `run_ir` statevectors on 20 random physical states < 1e-12 for every term at 2x2 and 2x3.
2. Count: `python scripts/gate_S2.py --angle-mode fixed --out S2_fixed` writing `validation/S2_fixed.json` and
   `reports/S2_fixed_angle_circuits.md` with the same tables as S2 (per term and per step, all-to-all and
   heavy-hex, plus the square grid from `scripts/s2_escalation_experiments.py`).  Do not touch S2.json.
3. Recall re-emulation for the fixed-angle generator: at 2x3, build the coarse-step states of every
   reference and k = 1..4 with `run_ir` on the 2^20 statevector (about 10 s per circuit; run sector by
   sector inside 30 min), project onto the dressed basis with `CodewordEmbedding`, and run the S1
   production-budget emulation (`gate_S1.emulate`, 2e5 shots per sector, f = 0.2 and 0.1) exactly as
   `scripts/s2_escalation_experiments.py` does for the ablations.  Add the recall rows to S2_fixed.json.
4. CUDA-Q: add `ry`, `rx`, `gphase`, `mcu` to `src/skqd/circuits_cudaq.py` (controlled registered operation
   via `.ctrl`) so that `python scripts/run_gate.py L5 --target qpp-cpu` passes again with the structured
   circuits as default; re-run L2 as well.
5. `pytest -q tests`; commit; push (these are measurements, not a gate PASS; say so in the message).

## Pass criteria (of this measurement step, not of gate S2)
- `validation/S2_fixed.json` exists with per-term and per-step CZ at 2x2 and 2x3 (all-to-all, heavy-hex,
  grid), leakage < 1e-12 for every term, and the emulated recall at f = 0.1 for both 2x3 sectors
- L2 and L5 PASS with the structured (exact) circuits as default; tests pass

## Decision required from the owner (Digonto) after step 2-3 — the planner will write prompt 12 accordingly
(a) Amend the preregistered budget to the measured floor of the fixed-angle circuits (if <= ~1000 routed on
    heavy-hex, f = 0.135 at eps = 2e-3) with the shot budget recomputed from eq. (5) — keeps Heron and the
    2x3 hardware program, changes the circuit family in the preregistration (gauge-invariant but not exact).
(b) Keep the exact circuits and move the 2x3 hardware target to an all-to-all device with eps <= 1e-3
    (2164 CZ, f = 0.115) — keeps the preregistered family, changes the device and the shot rate assumptions.
(c) Descope hardware to 2x2 (H0 at 618 routed CZ, f = 0.29 at eps = 2e-3) and deliver the 2x3 numbers from
    the certified emulation plus S3 device-model simulation — changes the hardware claim of the plan.
Doing nothing is not an option: at 5477 CZ the preregistered 2x3 run has zero yield on every device.

## Escalation
If the fixed-angle step is still > 1500 routed CZ at 2x3 or its emulated recall < 0.9 at f = 0.1 in either
sector, stop after step 3 and report; the owner then chooses between (b) and (c).

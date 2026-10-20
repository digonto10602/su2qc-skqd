# BLOCKED — CV_2x4_plan (prompts/36 Part A), 2026-10-19, executor-opus

Gate `validation/CV_2x4_plan.json` is **FAIL** and its STOP fired (`data.stop`).  Nothing was requested on the CI;
`ci/parts/QV_2x4_02..07.json` are left as the prompts/35b placeholders because there is no final plan to write them
from (prompts/36 section 9).  Every number below is in `validation/CV_2x4_plan.json`, `data/cv/2x4/*.json`,
`data/cv/acceptance_2x4.json` or `data/quantinuum/circuits_2x4_qpy/index.json`.

## STOP 1 — CV3 fails in the emulation at B=1 (prompts/36 A4: "STOP otherwise")

CV3 = E_R(k <= 4, equal shots) - E_R(k <= 5, equal shots) at N_eq = 1600 shots per circuit (B=1), against
E_tol(B=1) = 0.012534 (`data/cv/2x4/etol.json`):

| seed | B=1 CV3 dE / E_tol | at 2 N_eq (information) | B=0 CV3 / E_tol |
|---|---|---|---|
| 20260914 | 0.01119 / 0.89 | 0.54 | 0.27 |
| 1 | 0.01515 / **1.21** | 0.62 | 0.19 |
| 2 | 0.01052 / 0.84 | 0.54 | 0.24 |

(`data/cv/2x4/chunk_<seed>.json sectors["B=1"].seed_result.criteria_1x.CV3`).  Not a code fault as far as I can
find: CV0 holds in every seed (nested prefixes, the k = 5 stream replay reproduces the cache, the sequence
histogram equals measure_and_decode), and the k = 5 term IR synthesised for this prompt is exact on the sparse path
(1.0e-13 / 1.4e-13 vs coarse_states, `index.json irl0_sparse_check_k5`).  Reading: adding the four k = 5 circuits
(25 % more shots) lowers E_R(B=1) by 0.84-1.21 E_tol while doubling the shots (CV1, N/2 -> N) lowers it by 0.43-0.74 E_tol (CV1 in the three seeds) —
the B=1 Krylov direction is not converged at this budget.  Planner question per section 9: references, k = 5 in the
signed family, or CV3 read at 2 N_eq.

## STOP 2 — re-sizing to s = 8 still fails CV2 at B=1 (prompts/31 fix (g), prompts/36 R3 (iii))

B=0 passes CV1-CV5 at 1x in all seeds.  B=1 fails only CV2 (Weinstein r_H <= 0.15 at N/2 AND N) at every s:

| s | B=1 shots | max r_H(sN/2) | max r_H(sN) |
|---|---|---|---|
| 1 | 24 404 | 0.352 | 0.255 |
| 4 | 98 000 | 0.200 | 0.167 |
| 8 | 196 000 | 0.167 | 0.131 |

(`data/cv/2x4/resize_s<s>.json`; at s = 8 the 12 floor circuits are evaluated at the 2 136 sampled shots instead of
2 200, conservative.)  r_H(N) passes from s = 6 on; r_H(N/2) never does inside the grid.  Information (executor's
scratch, not a gate number: `scratch/executor36/oracle_b1.json`): the oracle support of the same size (|B| = 1229 to
1266, the B_all size at s = 8, N/2) has r_H 0.090-0.095, so the width is reachable at that |B| — the sampled family
misses tail states the oracle has; more shots (s > 8) or more references would be the levers.  Planner's call.

## Criterion that looks wrong as written — A7 "n_instructions == k x 142288"

The IR-L0 circuit of Krylov index k is ONE coarse step at angle k dt (`CircuitFactory.coarse_step`;
`krylov.coarse_states` and `ideal_sector_distribution` agree), so its size does not grow with k: the 75 bundles
have n_unitary_instructions 142288 (B=0) / 142289 (B=1) at every k = 1..5 (`index.json irl0`; S2_2x4's own record
already had B0_ref0_k4 at 142288 IR gates).  The criterion is evaluated as written and FAILS; it was not edited.
The same arithmetic makes R6's units wrong (the family is 60 units, not 150; the k = 5 set 15, not 75): every slot
is far below 2700 s (provisional tables below).

## What is ready (so the slots can run once the planner rules)

- A1 PASS: factorised acceptance = exhaustive at 2x2 and 2x3; 2x4 accepted 12843 / 8934 = the dimensions; Monte
  Carlo 1e7 strings (seed 36) z = 0.57 / 0.89.  `Phys` reads `data/cv/acceptance_2x4.json`.
- A2 PASS (E_tol 0.014495 / 0.012534), A3 PASS (D3'-R at y = 1: 14 547 / 24 404 shots, LP optimal), A4.0 CV0 PASS,
  A9 PASS.
- 75 IR-L0 bundles, 8.0 MB, round trip on qiskit 1.4.3 ok, the slot-01 structured sources gate-for-gate identical.
- The 13 native structured k = 1 bundles exported (QV_2x4_01 froze `structured`, stop false), for slots 06/07.
- `--tier slots-2x4` writes the parts from `data.plan.final`; it refuses while that is empty.  Provisional parts
  for information: `data/cv/2x4/provisional_parts_s1/`, `..._s8/` (status PROVISIONAL, never requested).
- Sampling run kind, `--tier assemble-2x4` (SKQD_2x4, K1-K7, S1-S6): dry runs PASS on the qiskit 1.4.3 / Aer
  0.15.1 twin (`validation/dryrun/QV_2x4_02..07.json`, `validation/dryrun/SKQD_2x4.json`).

re-planned by prompts/36a; owner items OD1-OD4 open (data/owner_decision_2x4_cv_plan_DRAFT.md, UNSIGNED).

Correction (executor, 2026-10-19, prompts/36a run): the A7 paragraph above says "142288 (B=0) / 142289 (B=1)". That attribution is wrong. The count is per reference, not per sector: 142288 for the Dirac-sea reference 102 (4 x gates) and 142289 for every other reference (5 x gates), at every k; the coarse-step body is 142284 for all 75 bundles (validation/CV_2x4_plan.json data.bundles.information_*). R12 as written (n_unit per sector from slot 01) therefore fails on the 50 bundles of the 10 B=0 references other than 102.

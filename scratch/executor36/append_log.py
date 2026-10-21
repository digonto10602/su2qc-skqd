import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
with open(os.path.join(ROOT, ".gitignore"), "a") as fh:
    fh.write("# prompts/36: executor scratch logs (the numbers that matter are in validation/*.json and data/cv/2x4/)\n"
             "scratch/executor36/*.log\n")
row = (
    "| 2026-10-19 | prompts/36_2x4_full_pipeline.md Part A (+ coordinator: QV_2x4_01 harvested PASS, frozen source "
    "structured, stop false) | CV_2x4_plan (A1-A9), SKQD_2x4 code, QV_2x4_02..07 parts | executor-opus (Opus 5.5, high) | "
    "**CV_2x4_plan FAIL, STOP fired (prompts/36 section 9); nothing requested.** PASS: A1 (factorised acceptance = "
    "exhaustive at 2x2 and 2x3; 2x4 accepted 12843 / 8934 = the sector dimensions; Monte Carlo 1e7 strings seed 36 z 0.57 "
    "/ 0.89; Phys reads data/cv/acceptance_2x4.json), A2 (E_tol 0.014495 / 0.012534), A3 (D3'-R at y = 1: 14547 / 24404 "
    "shots, LP optimal, P(recall S999 >= 0.9) 0.971 / 0.957), A4.0 CV0, A8 (pytest coding 678 passed / 50 skipped, "
    "quantinuum venv 707 / 21, qiskit 1.4.3 twin 323 / 18, PACKAGE OK, Q0P_2x3 reproduced in memory, 2x3 / 2x2 records "
    "unchanged, dry runs 02-07 PASS on the 1.4.3 twin), A9 (no noisy cell). FAIL: A4 -- CV3 (k = 4 -> 5 at equal shots) "
    "B=1 seed 1 = 1.21 E_tol (STOP), and re-sizing to s = 8 still fails CV2 at B=1 (Weinstein r_H(sN/2) up to 0.167 > "
    "0.15; r_H(sN) 0.131 passes) -> no final plan, so A5 / A6 cannot be evaluated and ci/parts/QV_2x4_02..07 stay "
    "placeholders (provisional parts at s = 1 and 8 in data/cv/2x4/provisional_parts_s*, information); A7 fails only on "
    "the criterion as written (n_instructions == k x 142288): the k-th circuit is one coarse step at angle k dt, every "
    "bundle has 142288 / 142289 unitary instructions at k = 1..5 -- the criterion looks wrong and was not edited. 75 IR-L0 "
    "bundles 8.0 MB, round trip ok on qiskit 1.4.3, slot-01 sources gate-for-gate identical, k = 5 term IR exact on the "
    "sparse path (1.0e-13 / 1.4e-13); 13 native structured k = 1 bundles exported for slots 06/07. Sampling run kind "
    "(save_amplitudes before the measurements, measure_sampling true), --tier slots-2x4 / assemble-2x4, the campaign-33 "
    "analysis generalised (Physics(lat), e_tol, cv_reading k_of) with 2x3 unchanged. predicted_s at the S2_2x4 rate (A6 as "
    "written); slot 01's measured 1.5357e-4 s/instruction recorded beside it. | (this commit) | Planner: "
    "prompts/BLOCKED_CV_2x4_plan.md (CV3 at B=1; CV2 at B=1 beyond s = 8; the A7 / R6 k-unit arithmetic). Coordinator: no "
    "QV_2x4_02+ request until the planner rules. |\n")
with open(os.path.join(ROOT, "prompts", "LOG.md"), "a") as fh:
    fh.write(row)
print("ok")

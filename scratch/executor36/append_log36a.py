import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
row = (
    "| 2026-10-19 | prompts/36a_CV_2x4_plan_fix_20261019.md sections 3.1-3.8 (coordinator: OD1-OD4 not signed, gate stays FAIL, "
    "nothing in ci/parts) | CV_2x4_plan (re-assembly), provisional slots QV_2x4_02..05, owner draft | executor-opus (Opus 5.5, "
    "high) | **CV_2x4_plan FAIL as written (OD1-OD4 UNSIGNED); conditions_under_proposed_rules: none.** E1 PASS (32 N "
    "extension starts with the cached 8 N; ladder s = 1.5..8 recomputed, max abs diff 0.0). E2 12N/2 vs 6N PASS (r_H 0.14370 = "
    "0.14370; 16N/2 vs 8N not evaluated, lazy ladder stopped at 12). E3 PASS (0 <= CV3 <= bound at every reading). "
    "s_star_information = 12 (B=1 294 000 shots; r_H(sN/2) / r_H(sN) 0.1396 / 0.1019, 0.1362 / 0.1023, 0.1437 / 0.1064). "
    "CV3 B=1 / E_tol: 1x 0.89 / 1.21 / 0.84, final N_eq 18 400 0.182 / 0.172 / 0.154, 2 N_eq 0.106 / 0.099 / 0.105. Cluster "
    "D1 overlap rank 3 (amplitude rank 4), D2 supports the cluster-projection reading (W1+W2+W3 on B minus O 2.8e-4 vs W0 "
    "8e-6 to 9e-6); oracle r_H reproduced to 1e-9 on 2 of 3 seeds (tie order of the non-bit-reproducible reference "
    "eigensolve, 1.7e-7 on seed 1). Cost fit 50.61 s + 3.428e-5 s/instr, rms 2.79 s. Provisional R14 slots 02-05: 1314 / 1851 "
    "/ 1542 / 2629 s, all fit (at 1e-3 s/shot 2217 / 2124 / 1764 / 2629). A7: R12's corrected rule also fails (50 bundles): "
    "the count is per reference (142 288 for ref 102 with 4 x gates, 142 289 for the others), body 142 284 everywhere -- my "
    "Part A note misattributed it per sector. Tests: coding 685 passed / 50 skipped, quantinuum venv 714 / 21, qiskit 1.4.3 "
    "twin 330 / 18, PACKAGE OK, Q0P_2x3 reproduced. | (this commit) | Owner: OD1-OD4 (data/owner_decision_2x4_cv_plan_DRAFT.md); "
    "planner: the OD3 wording (per-reference count). No CI request. |\n")
with open(os.path.join(ROOT, "prompts", "LOG.md"), "a") as fh:
    fh.write(row)
print("ok")

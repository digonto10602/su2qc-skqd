import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
row = (
    "| 2026-10-21 | prompts/36a (owner signed OD1-OD4 on 2026-10-21, verbatim \"signed OD1-OD4.\", decision file "
    "data/owner_decision_20261021_2x4_cv_plan.md written by the coordinator) | CV_2x4_plan, ci/parts/QV_2x4_02..08 | "
    "executor-opus (Opus 5.5, high) | **CV_2x4_plan PASS 10/10 under the signed set; STOP not fired.** Parser reads OD1-OD4 "
    "SIGNED. A4: resized_by B=0 1 / B=1 12, CV3 read at the final N_eq (0.18 / 0.17 / 0.15 E_tol); A5 certificates at the "
    "final plan hold; A6 ci/parts/QV_2x4_02..05 written by --tier slots-2x4 from the s* = 12 plan (02: 20 runs 1 003 200 "
    "shots 1314 s / 2217 s at 1e-3 s/shot; 03: 30, 303 304, 1851 / 2124; 04: 25, 247 170, 1542 / 1764; 05: 13 natives, "
    "2629 s), 06-08 reserve, slot 01 byte-identical to 6b8f8fc, token indices unchanged; A7 under the corrected rule (C = "
    "142 284 + n_x, popcount identity). Final plan 308 547 emulated shots (14 547 / 294 000), GPU shots 1 411 324. Parts "
    "check on the qiskit 1.4.3 twin PASS (every bundle loads with its sha256, count, q[k] -> c[k], seeds, prefixes); dry "
    "runs 02-05 and the dry SKQD_2x4 assembly PASS on the twin. Tests: coding 688 passed / 50 skipped, quantinuum venv 717 "
    "/ 21, 1.4.3 twin 333 / 18; PACKAGE OK; Q0P_2x3 reproduced. origin/master merge: already up to date (c1fc785). | "
    "(this commit) | Coordinator: request QV_2x4_02 (the sampling calibration) after the maintenance, per prompts/36 "
    "section 5; no request made here. |\n")
with open(os.path.join(ROOT, "prompts", "LOG.md"), "a") as fh:
    fh.write(row)
print("ok")

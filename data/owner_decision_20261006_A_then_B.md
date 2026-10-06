# Owner decision, 2026-10-06: option A first, then option B (2x3 on ibm_kingston, and the remaining IBM seconds)

Verbatim: "I want you to do A first, then when that is finished, do B because by that time it might be online"

Context (coordinator's options after the K1 precondition STOP, commit 4227a94): gate K0_2x3_2x4 PASS 6/6
(validation/K0_2x3_2x4.json) predicts the 2x3 clean fraction on ibm_kingston at f_gates = 6.07e-6 on the
routed layout and ~1e-16 or below with idle dephasing, i.e. reference hits at the garbage level (0.095 per
circuit at 1e5 shots).

A. Record 2x3 on IBM Heron as NO-GO on the K0 analysis (a model verdict, not a measurement), and use the
   remaining IBM seconds first for the 2x2 work: the XY4 dynamical-decoupling replication and the test of
   the context-aware DD (cell T1) collapse (about 32 s planned; planner to specify, preregistered).
B. Afterwards, when ibm_kingston again publishes two-qubit calibration, run the K1 2x3 clean-fraction pilot
   as built (one job, cap 300 s billed, every precondition of gate_K1_2x3_fpilot.py), as a measured upper
   limit.  If the seconds left after A do not cover K1's estimate x 1.3, STOP to the owner.

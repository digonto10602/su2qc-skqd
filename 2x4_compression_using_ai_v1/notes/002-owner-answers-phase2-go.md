# 002 — Owner answers to the phase-1 questions; phase 2 approved (2026-10-21)

Recorded by the coordinator from the session.  Owner's words quoted verbatim where given.

- **Phase 2 (building) is approved.**
- **O1 (second paper):** "the paper is the decoded quantum interferometry, use it if you need it. Gauge
  Symmetry in Quantum Simulation is another paper, download and use it if you need, but the correct paper is
  already inside the folder."  → The DQI paper (arXiv:2408.08292, file `2512.22932v2.pdf`) is the intended
  second document.  arXiv:2512.22932 (Hanada et al.) may be downloaded and used if useful.
- **O2 (failure budget / don't-cares):** "yes check by dropping near zero part of the amplitude and compare
  with the final result if they match under some certain tolerance, read the other paper to learn about the
  technique of the loop to execute circuit compression"  → Approximate class allowed: drop near-zero-amplitude
  parts, then compare with the exact final result under a stated tolerance (genie-opus states and justifies the
  tolerance before using it; the error bound is proved in Lean, lemma L6).  The loop technique is the one of
  arXiv:2610.22367.
- **O7 (go/no-go):** "try to come up with mathematical techniques that can prove you to reduce the circuits
  further, try the loop multiple times to find a compressed version of the circuits that gives you the same
  result under certain tolerances."  → No hard stop at 20 000 CX; keep developing provable reduction techniques
  and run the loop repeatedly.  (The 30-minute rule per laptop run still holds.)
- **O8 (adoption):** "you can submit it to the planner to check if this is the ultimate compressed version of
  the circuit and genie-opus can get help from the planner"  → genie-opus may ask planner-fable for help and
  submits its best family to the planner for review; requests go through the coordinator.
- **O3, O4, O5, O6, O9:** "For others choose recommended options" →
  O3 both classes (operator-exact; exact on own reference input), excluding circuits that directly prepare the
  classically computed output; O4 judged on the state (package bar); O5 genie-opus proposes turn by turn (no
  API loop); O6 score = ZZ count, then two-qubit depth; O9 rewrite identities proved in Lean, full 28-qubit
  circuits checked numerically.

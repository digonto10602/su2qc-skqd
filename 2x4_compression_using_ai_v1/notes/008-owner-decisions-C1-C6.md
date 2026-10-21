# 008 — Owner decisions C1–C6 on the compressed circuits (2026-10-21)

Recorded by the coordinator from the session.  Owner's words quoted verbatim.

## In force now (owner directive, not pending)

**Naming and separation (C1/C2).**  "keep the frozen circuits that have already been tested separate from
Class A and Class B, these will be known as compressed_circuit_llm_2x4_class[A,B] from now on. I will tell you
what to test when, remember this, write it in a file so that you can remind yourself later on."
"like i said, keep them separate and I will tell you what to use where."

- `compressed_circuit_llm_2x4_classA` = genie-opus family `arch:it5:operator:pp` (operator-exact, 1 736–1 740 ZZ).
- `compressed_circuit_llm_2x4_classB` = genie-opus family `arch:it5:input:pp` (exact on own reference input,
  582–800 ZZ).
- The 2x3 analogues (C3) will be `compressed_circuit_llm_2x3_classA` / `..._classB`.
- The package's frozen, tested circuits (2x2/2x3/2x4, incl. the 2x4 "structured" source frozen by QV_2x4_01)
  stay as they are.  The compressed families are NOT substituted anywhere — not in prompts/36, the GPU slots,
  Q0P/QN gates, preregistrations or hardware plans — until the owner says which to use where and when.
- Results of the compressed families are kept in separate, clearly named files (never mixed into the package's
  `validation/` gate JSONs).

## Pending the owner's signature (after the full compression report)

The owner asked for the full report first: "Before signing all of this, write the full report …".

- **C3:** "extend it to 2x3 as well, keep them separate like before. test with noise, without noise, all in qiskit,
  use cpu or gpu whichever gets the work done fastest without errors in run or compile."
- **C4:** "yes, one more genie run to check if it can be further compressed."
- **C5:** "yes, check circuit accuracy on the laptop, as well as check its behaviour under noise models, ibm,
  quantinuum, ionq. keep the results separate and easily callable."
- **C6:** "don't have access to quantinuum, you need to get information from the internet about quantinuum
  devices, when i get access I will tell you."

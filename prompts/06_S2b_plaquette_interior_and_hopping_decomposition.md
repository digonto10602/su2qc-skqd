# 06 — S2-b: structured hopping gates and interior-corner plaquette gates within the CZ budget
executor: executor-opus   effort: high (xhigh on the second attempt)   planner: planner-fable (max) wrote this prompt
time budget: 2 days of work; each verification run < 30 min   machine: laptop (CPU) — no GPU needed

## Goal
Gate S2 requires routed CZ ≤ 250 per coarse step at 2x2 and ≤ 500 at 2x3, with noiseless compiled circuits
leak-free.  The exact block unitaries are already available and verified (`skqd.circuits_ir`); the generic
synthesis of the hopping unitaries (6–11 qubits) is far above budget (baseline in `validation/L3.json`).
Build structured, exact, basic-gate decompositions of (a) the hopping terms and (b) the 2x3 plaquettes with
interior corners, verify them against the numpy reference to 1e-10, and measure the CZ counts.

## Inputs (read all)
- `reports/circuit_structure.md`, `validation/CS.json`: per term, the flipped qubits, the number of flip patterns
  (4 per hopping link), the largest block (3 at 2x2, 4 at 2x3), the distinct |element| values (3–6), and the
  proof that the 2x2 plaquette is `exp(+i θ/(2g²) D X^{⊗8})` with D a function of the four corner parities.
- `src/skqd/circuits_ir.py`: `ucrz_gray` (Gray-code uniformly controlled Rz, verified), `plaq_gates` (the
  structured 2x2 plaquette), `hop_gates` (dense baseline), `run_ir` (numpy executor of the IR).
- `src/skqd/reference_sim.py`: `localize` (term restricted to its support with a locality assertion),
  `local_unitary`, `apply_local`.
- `src/skqd/hamiltonian.py`: `hopping_element`, `plaquette_element` (the matrix elements by local labels).

## What the structure says (facts computed in this repo, not guesses)
1. A hopping term on link ℓ = (x → y) flips at most four qubits: the flux bit of ℓ at x and at y, and the
   occupation/intertwiner bit of x and of y.  Its off-diagonal blocks are chains of ≤ 3 (2x2) or ≤ 4 (2x3)
   configurations; the angle depends on the other flux bits of x and y (they fix the local singlet tensors)
   and on the Jordan–Wigner parity of the sites between x and y (XOR of their flux bits) — a sign.
2. The 2x2 plaquette is a single pair rotation with 4 distinct angles keyed by the corner parities (done).
3. A 2x3 plaquette with interior corners connects a configuration to up to 4 partners (the two intertwiner
   labels of each interior corner), with 2–4 flip patterns and ≤ 9 distinct |amplitudes|.

## Steps
1. **Hopping as controlled Givens chains.**  For each link build, from `localize`, the list of connected
   blocks {(states s₁…s_k, h_block)} and group blocks by (flip pattern, control-bit values).  Implement
   `exp(-iθ h_block)` for k ≤ 4 as a product of two-level rotations between computational basis states
   (each = a CNOT "compression" mapping the pair to a single differing qubit + a multi-controlled
   U(2) on that qubit + uncompute; use `qiskit.circuit.library.MCXGate`/`mcry`-style multi-controlled
   rotations or explicit Gray-code multi-controlled gates).  Merge blocks that share the flip pattern and the
   angle (at most 3–6 distinct |elements| per link, so the number of distinct controlled rotations is small).
   Emit IR gates only from {x, h, rz, p, cp, cx} plus a new IR gate `('mcu', controls+[target], (U2, ctrl_state))`
   that `run_ir` and `ir_to_qiskit` must support (Qiskit: `UnitaryGate(U2).control(len(controls), ctrl_state=...)`).
2. **Verify exactly.**  For every link and θ ∈ {dt, 2dt, 4dt}: `run_ir(new gates)` versus `apply_local(local_unitary)`
   on 20 random physical states embedded in 2^n — max |diff| < 1e-10.  Add the test to `tests/test_circuits_ir.py`.
3. **Plaquettes with interior corners (2x3).**  Generalize `plaq_gates`: after the parity CNOTs on each corner,
   the plaquette becomes a uniformly controlled unitary acting on the flux-flip qubits of the four corners
   plus the intertwiner bits of the two interior corners (q4 of the interior codeword; ι flips are part of the
   flip patterns).  Use `localize` on the 14-qubit support to get the exact blocks, then the same Givens-chain
   machinery as step 1.  Verify as in step 2 against the dressed-basis emulation (`krylov.coarse_states`) —
   the 2x3 dense 14-qubit unitary is NOT to be built (4 GB).
4. **Count.**  Extend `scripts/laptop_L3_cz_counts.py` with `--structured` to transpile the new circuits at
   2x2 and 2x3 (all-to-all and heavy-hex d = 3/5), optimization level 3; write validation/S2.json with the
   per-step CZ, the leak-free check (`CodewordEmbedding.leakage` of the noiseless transpiled circuit's
   statevector < 1e-9) and the pass criteria.
5. `pytest -q tests`; commit; `python scripts/run_gate.py S2 --push` on PASS.

## Pass criteria (gate S2)
- 2x2: CZ per coarse step ≤ 250 routed on heavy-hex; 2x3: ≤ 500 routed
- max |structured circuit − reference| < 1e-10 for all links, all plaquettes, θ ∈ {dt, 2dt, 4dt}
- leakage of every noiseless compiled circuit < 1e-9
- tests pass

## Outputs
`src/skqd/circuits_ir.py` (structured gates), `src/skqd/circuits_qiskit.py` (`mcu` support), validation/S2.json,
reports/S2_structured_circuits.md (counts table per term and per step, 2x2 and 2x3), prompts/LOG.md.  Push on PASS.

## Escalation
If after the Givens-chain construction the 2x3 step is still > 500 CZ, do NOT relax the budget: report the
count per term, identify the dominant term, and stop; planner-fable decides between (i) dropping the diagonal
terms from the generator (manual Step 4.3 ablation), (ii) a different vertex qubit layout that shortens the
flip patterns, (iii) raising the budget in the preregistration with the yield consequence computed from
eq. (5) of the manual.

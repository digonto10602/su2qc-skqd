# 12 — Combined plan: 2x2 on Heron, 2x3 exact circuits on an all-to-all device — device-resolved budgets, shot rule, S3 preparation
executor: executor-opus   effort: high   planner: planner-fable (max)
time budget: 1 day; each run < 30 min   machine: laptop (CPU); the full 2x3 noisy simulation is a desktop/cluster job

> Owner decision (2026-09-16, Digonto): pursue options (b) and (c) of prompt 11 together.  The circuit family
> stays the exact structured circuits of gate S2 (`validation/S2.json`).  2x2 runs on a Heron-class device
> (heavy-hex, CZ); 2x3 runs on an all-to-all trapped-ion device with two-qubit error <= 1e-3 (native RZZ).
> The fixed CZ numbers of manual Step 4.3 (250 / 500) are replaced by the physical condition they were derived
> from (Step 4.4): the clean-shot fraction f = prod_gates (1 - eps_gate) of one coarse-step circuit on the
> chosen device must be >= 0.1, the condition under which gate S1 established recall >= 0.9 with the production
> shot budget.  Gate S2 keeps its recorded FAIL; the new device-resolved gate is S2D.

## Goal
Produce every number the preregistration amendment needs: per (lattice, device) the two-qubit gate count of the
exact coarse step after transpilation to that device's connectivity and native gates, the clean-shot fraction
computed from that device's calibration (Heron: the per-edge CZ errors of a real calibration snapshot; ion trap:
the vendor-specified error as a declared input), the resulting yield prediction, the shot budget from the manual's
shot rule, a 2x2 noisy pilot with the Heron calibration model (H0 preparation), and the measured per-shot cost of the
2x3 noisy simulation that fixes the desktop/cluster job for S3.

## Inputs
- `validation/S2.json`, `validation/S2_fixed.json`, `reports/S2_escalation_analysis.md`, `data/S2_escalation_experiments.json`
- `scripts/gate_S2.py`, `scripts/laptop_L4_aer_noise.py`, `src/skqd/circuits_qiskit.py` (transpile_counts, generic_noise_model, sample)
- `qiskit_ibm_runtime.fake_provider.FakeTorino` (Heron r1, 133 qubits) and `FakeFez` (Heron r2, 156 qubits): calibration
  snapshots with per-edge CZ errors (medians 4.2e-3 and 3.9e-3 over all edges; the transpiler's layout must pick the
  best 12-qubit patch and f must be computed from the errors of the edges actually used)
- manual Step 4.4 (yield ~ 0.82 f plus 0.15 % garbage that decodes; shot rule: a configuration of ideal probability p is
  seen at least three times with 95 % probability) and Step 9.2 (32-44 circuits per sector, 2e5 shots per sector)

## Steps
1. **Shot rule.**  Implement `shot_rule(p, y, k=3, conf=0.95)` in `src/skqd/skqd.py`: the smallest N such that a
   Poisson(N p y) count is >= k with probability >= conf (solve for lambda* numerically, N = ceil(lambda*/(p y)));
   unit test with k = 3, conf = 0.95 (lambda* = 6.296) and a Monte-Carlo check.
2. **Gate S2D (`scripts/gate_S2D.py` -> `validation/S2D.json`, `reports/S2D_device_budgets.md`).**  For the exact
   circuits (`CircuitFactory` default), coarse steps k = 1..4 of every reference in both sectors:
   a. 2x2 on Heron: `transpile(qc, backend=FakeFez(), optimization_level=3, seed_transpiler=7)` (and FakeTorino);
      record the physical qubits chosen, the CZ count, and f = prod over executed CZ of (1 - eps_edge) times
      prod over measured qubits of (1 - readout_error) from `backend.target`; report the mean and the worst circuit.
      Also report the routed count on the ideal heavy-hex map (must reproduce the 618 of S2.json for k = 1).
   b. 2x3 on the all-to-all device: `transpile(qc, basis_gates=['rz','rx','ry','rzz'], coupling_map=None,
      optimization_level=3)`; record the RZZ count (this is the two-qubit gate count), and f = (1 - eps2)^N_RZZ
      x (1 - eps1)^N_1q x (1 - eps_ro)^n with declared inputs `--eps2 1e-3 --eps1 1e-4 --eps-ro 2e-3` recorded in
      the JSON under `assumed_inputs` and printed as such in the report (they are vendor-class specifications, not
      measurements).  Also record the CZ-basis all-to-all count (must reproduce 2164 for k = 1).
   c. Criteria: for each (lattice, device): mean f over the circuit set >= 0.1 and worst-circuit f >= 0.05; the
      k = 1 reproduction checks above; and the shot budget of step 3 <= 2e5 per sector at 2x3.
3. **Shot budget.**  For each 2x3 sector: predicted yield y = 0.82 f (mean f from 2b); p = 1e-3 (the 99.9 % support
   threshold of gate S1); N_circuit = shot_rule(1e-3, y); N_sector = N_circuit x number of circuits.  Record both and
   the manual's 2e5; also the same for 2x2 on Heron with the H0 circuit set.  Device time is
   N_sector / throughput with `throughput` left as an owner-supplied parameter: print the formula and a table for
   throughput in {100, 300, 1000} shots per minute clearly labelled as illustrative, not as a device number.
4. **S3 preparation at 2x2 (H0 rehearsal).**  Extend `scripts/laptop_L4_aer_noise.py` with `--backend FakeFez|FakeTorino`
   (NoiseModel.from_backend, transpile onto the backend so that the calibration's edges are the ones simulated)
   and `--out`; run `python scripts/run_gate.py L4 --timeout 1800 --backend FakeFez --budget-minutes 25 --pilot-shots 50
   --min-shots 1 --out L4_fez` writing `validation/L4_fez.json`; compare the measured yield with the S2D prediction
   0.82 f of step 2a (record the ratio; the L4 criterion factor 3 applies).
5. **2x3 per-shot cost.**  Time 10 noisy shots of one 2x3 coarse-step circuit in the RZZ basis with the depolarizing
   model of 2b on Aer statevector (CPU); record seconds per shot in S2D.json; state the desktop job:
   N_sector shots x per-shot cost, and that Aer GPU with batched shots is the intended executor (RTX 3070).
6. **Amendment draft.**  Write `proposal/amendment_01_devices_and_budgets.md` for the owner's signature: device per
   lattice, circuit family unchanged (exact structured circuits, S2.json), the f >= 0.1 condition replacing the fixed
   CZ numbers, the S2D numbers (cited from validation/S2D.json by name), the shot budget, and the H0 role split
   (decoder/bit-order/parity validation on Heron; yield-vs-CZ on the production device).  No number typed by hand:
   generate the numeric table with a small script section in gate_S2D.py or copy exact JSON values by reference.
7. `pytest -q tests`; `python scripts/update_status.py`; commit; `python scripts/run_gate.py S2D --push` on PASS,
   plain commit + push otherwise.  LOG row.

## Pass criteria (gate S2D)
- `validation/S2D.json` status PASS: 2x2/Heron mean f >= 0.1 (worst >= 0.05) with the best of FakeFez/FakeTorino;
  2x3/all-to-all mean f >= 0.1 (worst >= 0.05) at the declared eps2 = 1e-3; k = 1 counts reproduce 618 and 2164;
  2x3 shot budget <= 2e5 per sector.
- `validation/L4_fez.json` exists (its yield criterion is informative for H0; a FAIL there is a finding, not a blocker).
- tests pass (shot rule added).

## Outputs
validation/S2D.json, validation/L4_fez.json, reports/S2D_device_budgets.md, reports/L4_aer_noise.md (fez run),
proposal/amendment_01_devices_and_budgets.md, prompts/LOG.md.  Push: yes.

## Escalation
If 2x2/Heron mean f < 0.1 on both snapshots even with calibration-aware layout, report the best patch's f and CZ count
and stop: the planner decides between a smaller H0 circuit set (k = 1, 2 only) and a device with lower CZ error.
If the 2x3 shot budget exceeds 2e5 per sector at eps2 = 1e-3, report N_sector and stop; do not lower p or conf.

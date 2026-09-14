# 08 — One-month plan to H1/H2 (2x3 hardware spectroscopy) with the gate table
executor: planner-fable (max) revises weekly; scribe-haiku keeps the tables   machine: all

## Where the project stands (14 Sept 2026)
Cloud-verified in this package: E1, E2, E3, S1 (Tables 1–4 of the manual reproduced by an independent
implementation), the exact circuit layer at 2x2 with a 30-CNOT plaquette gate, and the structural analysis
for S2.  Open: S2 (structured hopping/interior-plaquette gates within budget), S3 (device-model simulation),
H0/H1/H2 (hardware), P1 (primary endpoint), M1 (ML credit).

## Week 1 (laptop) — prompts 00–05
- Day 1: 00 bootstrap + push; 01 L1 reproduce; 02 L2 Qiskit check.
- Day 2: 03 L3 baseline CZ counts; 04 L4 Aer noise at 2x2; 05 L5 CUDA-Q.
- Day 3–5: 06 S2-b structured gates (executor-opus), reviewed by reviewer-opus; S2 JSON.
Exit: S2 PASS or a quantified decision by the planner (budget vs. yield).

## Week 2 (laptop + desktop RTX 3070) — S3 and preregistration
- Aer device-model simulation with a real calibration (`NoiseModel.from_backend`) of the 2x3 production set
  (32–44 circuits per sector; 20–21 qubits).  Laptop: 2x2 only and 2x3 pilots (≤ 30 min); desktop: full 2x3
  set at 2e5 shots per sector (statevector 2^20 fits in the 8 GB GPU; noisy simulation cost is per-shot).
- Shot budget from eq. (5) with the measured f; gate S3: recall ≥ 0.9 of the 99.9 % support.
- Preregistration signed: controls, endpoints, gates (Step 6/10 of the manual) — `reports/preregistration.md`.
- ML model v1 beyond ridge (message-passing network on the lattice graph) trained leakage-safely on the desktop
  GPU; credit rule of Step 7.5.

## Week 3 — hardware H0 (prompt 07) and 2x3 pilot
- 2x2 calibration session; readout confusion; measured f.
- 2x3 pilot: 1e4 shots per circuit on one sector; decode; yield check.

## Week 4 — H1/H2 production and analysis
- 2x3 production, four sectors (B = 0, B = 1, static r = 1, r = 2), two calibration windows if quota permits.
- Certified intervals (Weinstein / Kato–Temple, gap-assumed labelled), seven-protocol tables at equal |B|,
  primary-endpoint curves with bootstrap bands (P1), ML credit table (M1).
- Research note with the claim table; release bundle (builder, decoder, circuits, raw bit strings).

## Standing rules
- Every gate: script → JSON → report → review → push.  No number in prose without a JSON source.
- 30-minute rule on the laptop; overflow goes to the desktop (RTX 3070, 32 GB) or the Slurm GPU cluster
  (2x4 noisy simulation, ML training at scale, bootstrap analyses).
- Fable at max effort only for blocked gates and the weekly re-plan; Opus implements; Sonnet/Haiku run and format.

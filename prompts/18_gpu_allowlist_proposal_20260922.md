# 18 — Proposed GPU allowlist lines for S3 and H0P (owner action on Perlmutter)

Requested by the owner after the L4 GPU calibration.  The allowlist is enforced on Perlmutter and
cannot be changed from this repository, so this note proposes lines and states the measurement that
justifies each one.  **No line is proposed without a measured number, and the one number I do not
have is named as missing rather than extrapolated.**

Everything below comes from `validation/L4.json` (job 58741899, `data.run`), `validation/S2D.json`,
`reports/S2D_shot_quota_decision_20260922.md` and `validation/H0P_ibm_fez.json`.

## 1. What the L4 calibration measured

| quantity | value | source |
|---|---|---|
| engine | Qiskit Aer statevector, GPU, cuStateVec + batched shots | `data.run.engine` |
| stack | qiskit 1.4.3, qiskit-aer 0.15.1 | `data.run.versions` |
| device | 1 A100-SXM4-80GB, node nid008257 | job 58741899 |
| **GPU cost per shot** | **0.00103 s** (2000-shot ladder point; 0.00106 at 1000, 0.00129 at 500) | `data.run.timing_ladder` |
| laptop CPU cost per shot | 0.02037 s (8-shot ladder point, same circuits) | laptop run 2026-09-22 |
| **measured speed-up** | **19.8x** | the two above |
| wall time | 677 s for 560 000 shots (20x20000 + 8x20000) | `runtime_s`, `data.run.shots_per_circuit` |
| **peak GPU memory** | **27 915 MiB** | `data.run.gpu_telemetry` |
| **mean GPU utilization** | **15.3 %** (max 27 %, 68 samples) | `data.run.gpu_telemetry` |
| batching | B=0 4 `run` calls at 20x6103, B=1 2 at 8x15258, 0 OOM retries | `data.run.batching` |
| CZ per circuit | 288 (the structured circuits of gate S2, not the 35 670 of 2026-09-14) | `data["B=0"].cz` |

Two consequences that shape the proposal:

**(a) 15.3 % mean utilization means these jobs are not GPU-bound.**  A second GPU would therefore
buy far less than a factor 2, so **no line below asks for 2 GPUs**, and the policy's E(p) >= 0.7
test would almost certainly fail if one were requested.  The bottleneck is elsewhere (noise
sampling and the per-call set-up on the host); finding it is worth more than another card.

**(b) My allocation model underestimates by a factor 3.5.**  `shot_chunk_for` predicted 8.0 GB for
the 20x6103 chunk; the measured peak was 27.9 GB.  That is exactly why the first attempt (job
58737320) died: 20x20000 was 26 GB by the model and therefore about 92 GB in reality, against 80 GB
available.  The default `--gpu-memory-bytes 8e9` is consequently a ~28 GB real budget and is
*correctly* conservative, but the factor should be documented rather than rediscovered.

## 2. Proposed allowlist lines

| token | walltime | GPUs | what it runs | justification |
|---|---|---|---|---|
| `S3` | **04:00:00** | **1** | `scripts/s3_device_model.py`, one lattice/sector/repetition per call | see 2.1 |
| `H0P` | **01:00:00** | **1** | `scripts/gate_H0P.py --backend <live> --shots-plan ...` | see 2.2 |

### 2.1 S3 — 4 hours, 1 GPU

S3 is the gate that cannot run here at all: `validation/S2D.json` measures **3.198 s per shot** for
one 20-qubit coarse-step circuit in the RZZ basis on this laptop CPU, so

| shot budget | laptop CPU | if the GPU gave L4's 19.8x |
|---|---|---|
| the current Step 9.2 quota (2e5 per sector, both) = 400 000 shots | **355 h** | 18 h |
| the item-5 recommendation (556 000 + 808 104) = 1 364 104 shots | **1 212 h** | 61 h |

**The right-hand column is not a measurement and must not be quoted as one.**  L4 is 12 qubits;
S3 is 20, so each statevector is 256x larger, and at the measured 3.5x model factor a single
20-qubit circuit needs about 476 shots per `run` call inside a 28 GB real budget — S3 will be
chunk-dominated in a way L4 was not.  The first S3 job must therefore be **a reduced-size
calibration, not production**: one sector, one repetition, a few thousand shots, with the timing
ladder and the telemetry, from which the production walltime is then sized.  4 hours is proposed as
enough for that calibration plus a first useful production slice, not as enough for the full run —
the full run is sized from the calibration, per the policy.

### 2.2 H0P — 1 hour, 1 GPU

H0P's Aer prediction is the step that made the H0 session day unworkable: the critical path
measured in `prompts/LOG.md` (part B') is **28m40s**, of which **23m39s** is Aer simulated-yield
sampling of the frozen 2x2 circuits, and `ibm_fez`'s calibration content is only guaranteed stable
for the windows measured in `prompts/17` (one content-stable window of >= 143 min is on record, but
timestamp windows as short as 30m17s).  At L4's 19.8x that sampling would be minutes, which turns
the prediction from the thing that loses the window into something that fits inside it comfortably.

This is the one place where L4's speed-up transfers with confidence: H0P samples **the same
12-qubit frozen circuits on the same noise-model path** as L4, differing only in using
`NoiseModel.from_backend(live ibm_fez)` rather than the generic model and 17 physical qubits rather
than 12 logical.  1 hour is the current H0P budget (`--budget-minutes 28` twice over) with margin.

## 3. What is deliberately not proposed

- **No 2-GPU line, and no whole-node line.**  15.3 % utilization is the reason; the policy's
  E(p) >= 0.7 bar has not been measured and on this evidence would not be met.  When a workload is
  found that saturates one card, T_1 and T_2 get measured first and the proposal comes after.
- **No `L4` walltime increase.**  L4 now PASSES at 20 000 shots per circuit inside 677 s of its
  existing 60-minute line; it needs nothing more.
- **No line for E1-E3 or S1.**  The policy keeps them in the exact gauge-invariant basis on CPU.

## 4. If the owner adds these lines

The first two requests would be `scripts/ci_request.sh S3` (the reduced-size calibration described
in 2.1, which needs `s3_device_model.py` to grow the same CI self-detection, `--shots-plan`,
timing ladder and telemetry that L4 has) and `scripts/ci_request.sh H0P` (which needs the same, plus
the live-backend path already built in part A'').  Neither script has those hooks yet; that is
executor work for a later prompt and is not assumed here.

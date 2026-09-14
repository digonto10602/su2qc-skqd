# 05 — L5: CUDA-Q version of the 2x2 circuits on the GTX 1060 Max-Q
executor: runner-sonnet   effort: low   (executor-opus high if the convention tests disagree)
time budget: 30 min   machine: laptop (GPU)

## Goal
Run the same IR circuits through CUDA-Q (`skqd.circuits_cudaq`, generated kernel source with registered
custom unitaries) on the `nvidia` target and show the sampled distribution matches the numpy reference.
Two conventions are unknown until this runs: the order of the result strings and the qubit order of
`cudaq.register_operation` for multi-qubit matrices — the script tests both first with a CNOT.

## Inputs
- `src/skqd/circuits_cudaq.py`, `scripts/laptop_L5_cudaq_check.py`
- CUDA-Q: `pip install cudaq` (CUDA 12 build; the confirmed-working alternative is the container
  `nvcr.io/nvidia/quantum/cuda-quantum:cu13-0.15.1` with the repo mounted at /workspace)

## Steps
1. `python scripts/laptop_L5_cudaq_check.py --target nvidia --shots 10000`
   (fallback `--target qpp-cpu` if the GPU target is unavailable; say which one was used)
2. If the register_operation convention test reports big-endian, the script sets `BIG_ENDIAN = True` for the
   run; make that permanent in `src/skqd/circuits_cudaq.py` (executor-opus) and re-run.
3. Record GPU vs CPU sampling time in prompts/LOG.md; push on PASS.

## Pass criteria
- both convention tests determined (documented in the report)
- 100 % of noiseless shots decode; TVD below the shot-noise bound

## Outputs
validation/L5.json, reports/L5_cudaq_check.md, prompts/LOG.md.  Push: yes.

## Escalation
If `cudaq.register_operation` rejects the 256x256 matrices (8-qubit custom ops), split: use the structured
plaquette (already basic gates) and register only the hopping unitaries; if those are also rejected, report
and let planner-fable decide between the CUDA-Q container and a Givens decomposition (prompt 06 produces
basic-gate hopping circuits anyway).

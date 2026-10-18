#!/bin/bash
# prompts/33f coordinator check: run a command in the jobs/gate.sbatch thread/binding environment on the laptop,
# with the qiskit 1.4.3 / aer 0.15.1 twin first on PATH.  BIND=0 drops OMP_PROC_BIND / OMP_PLACES (the R4 variant).
# CI=1 additionally sets the variables that make skqd.hpc.ci_context() see a CI job (CI_GATE from $1 of the
# command is not inferred: pass CI_GATE yourself), with SLURM_CPUS_PER_TASK = this machine's CPUs.
set -uo pipefail
cd "$(dirname "$0")/../.."
TWIN="${SKQD_TWIN_PYTHON:-$HOME/.local/share/su2qc-qiskit143/venv/bin}"
export PATH="$TWIN:$PATH"
NCPU=$(nproc)
export SLURM_CPU_BIND=cores
if [ "${BIND:-1}" = "1" ]; then
  export OMP_PROC_BIND=spread
  export OMP_PLACES=threads
else
  unset OMP_PROC_BIND OMP_PLACES
fi
export OMP_NUM_THREADS="$NCPU" MKL_NUM_THREADS="$NCPU" OPENBLAS_NUM_THREADS="$NCPU"
unset SKQD_STEP_CPUS
if [ "${CI:-0}" = "1" ]; then
  export SLURM_CPUS_PER_TASK="$NCPU" SLURM_JOB_ID="${SLURM_JOB_ID:-laptop-sim}" SLURM_NTASKS=1 SLURM_PROCID=0
  export CUDA_VISIBLE_DEVICES=0
  : "${CI_GATE:?set CI_GATE}"
  export CI_GATE
  if [ -n "${FAKE_TELEMETRY:-}" ]; then
    export SKQD_GPU_TELEMETRY="$FAKE_TELEMETRY"
  fi
fi
echo "sbatch_env: python $(command -v python), BIND=${BIND:-1}, CI=${CI:-0}, OMP_PROC_BIND=${OMP_PROC_BIND:-unset}, OMP_PLACES=${OMP_PLACES:-unset}, OMP_NUM_THREADS=$OMP_NUM_THREADS"
exec "$@"

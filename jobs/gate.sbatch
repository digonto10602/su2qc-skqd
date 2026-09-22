#!/bin/bash
# Runs one package gate: python scripts/run_gate.py $CI_GATE  (resources set by poll.sh)
#
# Environment and telemetry follow the owner's engine and HPC policy (RUNBOOK.md, "Engine and HPC
# policy for Perlmutter runs").  The resource request itself is NOT made here: ci/poll.sh submits
# -n 1 -c $((32*GPUS)) --gpus-per-task=$GPUS and exports CI_GATE, CI_CODE_SHA, CI_REQUEST_SHA.
set -uo pipefail
module load python
conda activate skqd

# --- CPU binding and threading: one threaded process per task, never oversubscribed -----------
export SLURM_CPU_BIND=cores
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export OPENBLAS_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"

# --- GPU telemetry: utilization and memory every 10 s, in the job's working directory ---------
# Policy: "sample nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv every 10 s in
# the background".  One line per GPU per sample, prefixed with the unix time:
#   <seconds>,<utilization %>,<memory MiB>
# The gate reads the file back (scripts/laptop_L4_aer_noise.py: gpu_telemetry) and folds peak
# memory and mean utilization into its validation JSON.  When nvidia-smi is missing (a CPU-only
# job, or any laptop run) no file is written and every telemetry field stays null.
# $PWD is the CI snapshot on $SCRATCH: ci/poll.sh submits with -D "$SNAP", so the job script
# runs there while SLURM_SUBMIT_DIR still points at the poller's own directory.  The policy
# says outputs go relative to the job's working directory, so use $PWD, not SLURM_SUBMIT_DIR.
export SKQD_GPU_TELEMETRY="$PWD/gpu_telemetry.csv"
SMI_PID=""
if command -v nvidia-smi > /dev/null 2>&1; then
  ( while true; do
      nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits \
        | sed "s/^/$(date +%s),/"
      sleep 10
    done ) > "$SKQD_GPU_TELEMETRY" 2>/dev/null &
  SMI_PID=$!
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv > \
    "$PWD/gpu_device.csv" 2>/dev/null
fi

START=$(date +%s)
srun python scripts/run_gate.py "$CI_GATE"
RC=$?
[ -n "$SMI_PID" ] && { pkill -P "$SMI_PID" 2> /dev/null; kill "$SMI_PID" 2> /dev/null; }

mkdir -p validation
printf '{\n "gate": "%s",\n "exit_code": %d,\n "pass": %s,\n "seconds": %d,\n "jobid": "%s",\n "code_sha": "%s",\n "request_sha": "%s"\n}\n' \
  "$CI_GATE" "$RC" "$([ $RC -eq 0 ] && echo true || echo false)" "$(( $(date +%s) - START ))" \
  "$SLURM_JOB_ID" "$CI_CODE_SHA" "$CI_REQUEST_SHA" > "validation/ci_gate_${CI_GATE}.json"
exit $RC

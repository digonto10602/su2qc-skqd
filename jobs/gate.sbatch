#!/bin/bash
# Runs one package gate: python scripts/run_gate.py $CI_GATE  (resources set by poll.sh)
#
# Environment and telemetry follow the owner's engine and HPC policy (RUNBOOK.md, "Engine and HPC
# policy for Perlmutter runs").  The resource request itself is NOT made here: ci/poll.sh submits
# -n 1 -c $((32*GPUS)) --gpus-per-task=$GPUS and exports CI_GATE, CI_CODE_SHA, CI_REQUEST_SHA.
set -uo pipefail
module load python
# Conda env per token (prompts/33 A1): jobs/env/<CI_GATE> holds one line, the env name (C3_LE ->
# skqd-pecos, C3_SEL -> skqd-selene); every other token uses skqd.  Resources are unchanged: they
# stay on the poller's sbatch line.
CI_ENV=skqd
if [ -f "jobs/env/${CI_GATE:-}" ]; then
  CI_ENV=$(head -1 "jobs/env/${CI_GATE}" | tr -cd 'A-Za-z0-9_.-')
  [ -n "$CI_ENV" ] || CI_ENV=skqd
fi
echo "conda env: $CI_ENV"
conda activate "$CI_ENV"

# --- CPU binding and threading: one threaded process per task, never oversubscribed -----------
# prompts/33f R4 (owner policy amended in RUNBOOK.md): no OpenMP binding.  Under OMP_PROC_BIND=spread +
# OMP_PLACES=threads, qiskit_aer's OpenMP runtime binds the initial thread to the first place when it is imported,
# so the driver's main thread and every subprocess it starts ran on one CPU (C2_KCHK job 59828887).  The arithmetic
# depends on the thread COUNT, fixed by the exports below and threadpool_limits, not on placement.
export SLURM_CPU_BIND=cores
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
# prompts/33e R1: Slurm >= 22.05 no longer lets a job step inherit the allocation's --cpus-per-task, so a bare
# `srun` bound the step to one CPU (C2_KCHK job 59780907: the CPU arm ran on 1 thread while the allocation had 32).
# The step asks for the allocation's CPUs explicitly; every campaign-33 token JSON records run.cpu_affinity and
# its structural criterion S3 FAILs on the CI when that differs from SLURM_CPUS_PER_TASK.
srun --cpus-per-task="${SLURM_CPUS_PER_TASK:-1}" python scripts/run_gate.py "$CI_GATE"
RC=$?
[ -n "$SMI_PID" ] && { pkill -P "$SMI_PID" 2> /dev/null; kill "$SMI_PID" 2> /dev/null; }

mkdir -p validation
printf '{\n "gate": "%s",\n "exit_code": %d,\n "pass": %s,\n "seconds": %d,\n "jobid": "%s",\n "code_sha": "%s",\n "request_sha": "%s"\n}\n' \
  "$CI_GATE" "$RC" "$([ $RC -eq 0 ] && echo true || echo false)" "$(( $(date +%s) - START ))" \
  "$SLURM_JOB_ID" "$CI_CODE_SHA" "$CI_REQUEST_SHA" > "validation/ci_gate_${CI_GATE}.json"
exit $RC

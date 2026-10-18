#!/bin/bash
# prompts/33f coordinator check: a campaign token's dry run through the CI's own chain (run_gate.py -> campaign33.py
# subprocess) in the jobs/gate.sbatch environment, with the variables that make the driver believe it is on the CI
# (CI_GATE, SLURM_JOB_ID, SLURM_CPUS_PER_TASK = this machine's CPUs, CUDA_VISIBLE_DEVICES, a fake GPU telemetry file).
#   usage: cisim.sh TOKEN BIND   (BIND=1: OMP_PROC_BIND=spread + OMP_PLACES=threads as now; BIND=0: R4's variant)
# Output: scratch/c33f/logs/cisim_<TOKEN>_bind<BIND>.log and a copy of validation/dryrun/<TOKEN>.json beside it.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../.."
TOKEN="$1"
export BIND="$2"
export CI=1 CI_GATE="$TOKEN" FAKE_TELEMETRY="$HERE/fake_gpu_telemetry.csv"
LOG="$HERE/logs/cisim_${TOKEN}_bind${BIND}.log"
START=$(date +%s)
bash "$HERE/sbatch_env.sh" python scripts/run_gate.py "$TOKEN" --dry-run --device CPU --budget-minutes 8 \
  --max-shots-per-run 16 --bootstrap 20 > "$LOG" 2>&1
RC=$?
echo "cisim: exit $RC, $(( $(date +%s) - START )) s" >> "$LOG"
cp "validation/dryrun/${TOKEN}.json" "$HERE/logs/cisim_${TOKEN}_bind${BIND}.json"
exit 0

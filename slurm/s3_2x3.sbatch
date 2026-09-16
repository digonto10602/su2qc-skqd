#!/bin/bash
#SBATCH --job-name=skqd-s3-2x3
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --output=slurm/logs/s3_2x3_%j.out
#SBATCH --error=slurm/logs/s3_2x3_%j.err
#
# Gate S3 at 2x3: the four production jobs of manual Step 9.2 on the all-to-all
# trapped-ion device model (prompts/12, prompts/13 step 4) -- B = 0 and B = 1, each with
# r = 1 and r = 2 repetitions of the coarse step, 2e5 shots per sector.
#
#   sbatch slurm/s3_2x3.sbatch
#   sbatch --export=ALL,SHOTS=50000 slurm/s3_2x3.sbatch     # smaller budget
#
# The script picks Aer's GPU with batched shots when `AerSimulator().available_devices()`
# contains 'GPU' and falls back to the CPU otherwise, so the same file runs on the RTX 3070
# desktop (drop the #SBATCH lines and run it as a shell script).  The laptop of this project
# cannot run it: measured CPU cost is recorded in validation/S3_smoke.json and
# validation/S2D.json (per_shot_cost_2x3).
#
# Requires qiskit-aer with GPU support (qiskit-aer-gpu matching the installed qiskit).

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")/..}"
mkdir -p slurm/logs

SHOTS="${SHOTS:-200000}"
EPS2="${EPS2:-1e-3}"
EPS1="${EPS1:-1e-4}"
EPSRO="${EPSRO:-2e-3}"
PY="${PY:-python}"

echo "host $(hostname), $(date)"
${PY} -c "from qiskit_aer import AerSimulator; print('Aer devices:', AerSimulator().available_devices())"

for SECTOR in 0 1; do
  for REPS in 1 2; do
    TAG="2x3_B${SECTOR}_r${REPS}"
    echo "=== ${TAG}: ${SHOTS} shots per sector ==="
    ${PY} scripts/s3_device_model.py \
        --lattice 3 --sector "${SECTOR}" --reps "${REPS}" \
        --shots-per-sector "${SHOTS}" \
        --eps2 "${EPS2}" --eps1 "${EPS1}" --eps-ro "${EPSRO}" \
        --device auto --tag "${TAG}"
  done
done

echo "done $(date); results in validation/S3_2x3_B*_r*.json and reports/S3_2x3_B*_r*_device_model.md"

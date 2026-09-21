#!/bin/bash
# Resources (account, QOS, GPUs, walltime) are set by ~/skqd-ci/poll.sh on the sbatch
# command line; any #SBATCH lines added here are overridden by those flags.
set -uo pipefail
module load python
conda activate skqd
export SLURM_CPU_BIND=cores
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
srun python scripts/ci_smoke.py

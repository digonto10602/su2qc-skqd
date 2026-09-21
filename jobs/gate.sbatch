#!/bin/bash
# Runs one package gate: python scripts/run_gate.py $CI_GATE  (resources set by poll.sh)
set -uo pipefail
module load python
conda activate skqd
export SLURM_CPU_BIND=cores
START=$(date +%s)
srun python scripts/run_gate.py "$CI_GATE"
RC=$?
mkdir -p validation
printf '{\n "gate": "%s",\n "exit_code": %d,\n "pass": %s,\n "seconds": %d,\n "jobid": "%s",\n "code_sha": "%s",\n "request_sha": "%s"\n}\n' \
  "$CI_GATE" "$RC" "$([ $RC -eq 0 ] && echo true || echo false)" "$(( $(date +%s) - START ))" \
  "$SLURM_JOB_ID" "$CI_CODE_SHA" "$CI_REQUEST_SHA" > "validation/ci_gate_${CI_GATE}.json"
exit $RC

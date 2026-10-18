#!/bin/bash
# prompts/33f R3: the campaign assembly in chunks under the 30-minute rule -- one split run per process, each killed
# at 1800 s (timeout), then the final pass that reuses every merge whose inputs are unchanged.
#   usage: assemble_chunks.sh RUN [RUN ...]      (merge these runs, one process each)
#          assemble_chunks.sh --final            (the campaign JSON + report, --reuse-merged)
# Threads: ASM_THREADS (default 1) for OMP / MKL / OPENBLAS.  The first attempt at Aer's default (12 BLAS threads on
# this laptop) had not finished F1_B1 after 792 s; the in-job analysis of the same size took 50 s on one CPU.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../.."
LOG="$HERE/logs/assemble_chunks.log"
T="${ASM_THREADS:-1}"
export OMP_NUM_THREADS="$T" MKL_NUM_THREADS="$T" OPENBLAS_NUM_THREADS="$T"
if [ "${1:-}" = "--final" ]; then
  S=$(date +%s)
  timeout 1800 python scripts/campaign33.py --stage assemble --reuse-merged >> "$LOG" 2>&1
  echo "chunk FINAL: exit $?, $(( $(date +%s) - S )) s, threads $T" >> "$LOG"
  exit 0
fi
for RUN in "$@"; do
  S=$(date +%s)
  timeout 1800 python scripts/campaign33.py --stage assemble --runs "$RUN" >> "$LOG" 2>&1
  echo "chunk $RUN: exit $?, $(( $(date +%s) - S )) s, threads $T" >> "$LOG"
done

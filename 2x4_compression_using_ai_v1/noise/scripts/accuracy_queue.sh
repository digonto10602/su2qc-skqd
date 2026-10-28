#!/bin/bash
# C5 test 1 background queue: noiseless Aer statevector (complex128) accuracy, resumable, 30-min cap per run.
# The plan (scripts/queue_plan.py: accuracy_jobs) is re-read before every run, so new families join without restart.
# Usage: nohup nice -n 10 bash scripts/accuracy_queue.sh >> logs/accuracy_queue.log 2>&1 &
cd "$(dirname "$0")/.."
export AER_THREADS=${AER_THREADS:-10}
PY=${PY:-python}
SKIP=""
while true; do
  next=$($PY - "$SKIP" <<'PYEOF'
import os, sys
sys.path.insert(0, "scripts")
sys.path.insert(0, "src")
import queue_plan
from results import lattice_results   # one folder per lattice (notes/012)
skip = set(sys.argv[1].split(",")) if sys.argv[1] else set()
for lat, fam, tag in queue_plan.accuracy_jobs():
    if f"{lat}/{fam}/{tag}" in skip:
        continue
    if not os.path.exists(os.path.join(lattice_results(lat), fam, "noiseless", "accuracy_runs", f"{tag}.json")):
        print(lat, fam, tag); break
PYEOF
)
  [ -z "$next" ] && break
  set -- $next
  echo "START $(date -u +%FT%TZ) $1 $2 $3"
  timeout 1800 $PY scripts/accuracy_sv.py $1 $2 $3 || { echo "FAILED_OR_TIMEOUT $1 $2 $3 rc=$?"; SKIP="$SKIP,$1/$2/$3"; }
done
echo "QUEUE_DONE $(date -u +%FT%TZ) skipped: $SKIP"

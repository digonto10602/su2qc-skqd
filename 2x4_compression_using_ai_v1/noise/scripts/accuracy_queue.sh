#!/bin/bash
# C5 test 1 background queue: noiseless Aer statevector (complex128) accuracy, resumable.
# Each run is capped at 30 min (timeout 1800); finished runs are skipped (result JSON exists).
# Usage: nohup nice -n 10 bash scripts/accuracy_queue.sh > logs/accuracy_queue.log 2>&1 &
cd "$(dirname "$0")/.."
export AER_THREADS=${AER_THREADS:-10}
PY=${PY:-python}
list() {
  $PY - <<'PYEOF'
import sys; sys.path.insert(0, "src")
import circuits
for t in circuits.frozen_2x3_ids(): print("2x3 frozen", t)
for fam in ("compressed_circuit_llm_2x4_classB", "compressed_circuit_llm_2x4_classA"):
    for (b, r, k) in circuits.v1_ids(): print("2x4", fam, circuits.tag(b, r, k))
PYEOF
}
list | while read lat fam tag; do
  out=data/results/$lat/$fam/noiseless/accuracy_runs/$tag.json
  [ -f "$out" ] && continue
  echo "START $(date -u +%FT%TZ) $lat $fam $tag"
  timeout 1800 $PY scripts/accuracy_sv.py $lat $fam $tag || echo "FAILED_OR_TIMEOUT $lat $fam $tag rc=$?"
done
echo "QUEUE_DONE $(date -u +%FT%TZ)"

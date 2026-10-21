#!/bin/bash
# Review 001 run queue (sequential; each run < 30 min)
cd "$(dirname "$0")"
export AER_THREADS=12
for args in "B 0 102 1" "B 0 102 5" "B 2 230 5" "A 0 102 1" "A 0 102 5" "A 2 230 1" "A 2 230 5" \
            "A 0 102 1 11" "A 0 102 1 12" "A 0 102 5 11" "A 0 102 5 12" "A 2 230 1 11" "A 2 230 1 12" \
            "A 2 230 5 11" "A 2 230 5 12" "B 0 345 4" "B 0 102 1 11"; do
  timeout 1800 python 001_verify_aer.py $args >> 001_queue.log 2>&1 || echo "FAILED/TIMEOUT: $args" >> 001_queue.log
done
echo QUEUE_DONE >> 001_queue.log

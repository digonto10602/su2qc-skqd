#!/bin/bash
# prompts/33e R3: the laptop CPU reference of C2_KCHK run 2, in background segments under the 30-minute rule.
#
# Runs scripts/c33c_diag_full.py in the qiskit 1.4.3 / aer 0.15.1 twin (the CI's versions), one segment after the
# other, each capped at --max-seconds 1700 (no call is started whose predicted time would pass the cap), Kraus first
# until the pooled Kraus arm (every full_IBM-T0_B0_ref117_k1_kraus_cpu*.json) has >= 64 shots, then RM to >= 64.
# Segment k writes full_IBM-T0_B0_ref117_k1_<rep>_cpu_seg<k>.json with seed0 = 33033000 + 100000 x k (disjoint from
# the 33c segments, which used k = 0, 1, 2; c33c_diag_full.py --summarize refuses shared shot seeds).
#
#   nohup setsid bash scripts/c33e_diag_segments.sh [threads] [shots_per_call] > scratch/c33e/segments.log 2>&1 &
#
# Each finished segment is committed by the executor (one commit per segment); this script never commits.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TWIN="${SKQD_TWIN_PYTHON:-$HOME/.local/share/su2qc-qiskit143/venv/bin/python}"
THREADS="${1:-10}"
SPC="${2:-2}"
TARGET="${C33E_TARGET_SHOTS:-64}"
DIAG="$ROOT/data/campaign33/c33c_diag"
cd "$ROOT" || exit 2

pooled() {   # pooled shots of one representation over every segment file present
  "$TWIN" - "$DIAG" "$1" <<'EOF'
import glob, json, os, sys
d, rep = sys.argv[1], sys.argv[2]
n = 0
for p in glob.glob(os.path.join(d, f"full_IBM-T0_B0_ref117_k1_{rep}_cpu*.json")):
    n += sum(int(c["shots"]) for c in json.load(open(p))["calls"])
print(n)
EOF
}

next_seg() {   # the smallest k >= 3 with no seg<k> file of either representation (k = 0..2 belong to 33c)
  local k=3
  while ls "$DIAG"/full_IBM-T0_B0_ref117_k1_*_cpu_seg${k}.json > /dev/null 2>&1; do k=$((k + 1)); done
  echo "$k"
}

for REP in kraus rm; do
  while true; do
    N=$(pooled "$REP")
    if [ "$N" -ge "$TARGET" ]; then
      echo "$(date -u +%FT%TZ) $REP: pooled $N >= $TARGET shots, done"
      break
    fi
    K=$(next_seg)
    SEED=$((33033000 + 100000 * K))
    OUT="$DIAG/full_IBM-T0_B0_ref117_k1_${REP}_cpu_seg${K}.json"
    echo "$(date -u +%FT%TZ) $REP: pooled $N shots; segment $K (seed0 $SEED, $SPC shots per call, $THREADS threads)"
    "$TWIN" scripts/c33c_diag_full.py --rep "$REP" --shots-per-call "$SPC" --max-shots 1000 --max-seconds 1700 \
      --threads "$THREADS" --seed "$SEED" --out "data/campaign33/c33c_diag/full_IBM-T0_B0_ref117_k1_${REP}_cpu_seg${K}.json"
    RC=$?
    echo "$(date -u +%FT%TZ) $REP: segment $K exit $RC"
    [ "$RC" -eq 0 ] || exit "$RC"
    [ -f "$OUT" ] || exit 4
  done
done

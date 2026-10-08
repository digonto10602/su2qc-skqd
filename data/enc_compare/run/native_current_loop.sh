#!/bin/bash
# prompts/34 native stage, current codec, in single-round chunks of 6 circuits; each invocation capped at 30 min
cd /home/digimonk/Projects/su2qc-skqd-v0.1.0
PY=~/.local/share/su2qc-quantinuum/venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
for i in 1 2 3 4 5 6 7; do
  left=$(python -c "import json; d=json.load(open('data/enc_compare/native.json')); print(44-sum(1 for k in d['circuits'] if k.startswith('current|')))")
  echo "chunk $i: $left current circuits left $(date +%T)"
  [ "$left" -le 0 ] && break
  s=$(date +%s)
  timeout 1800 $PY scripts/gate_ENC_compare.py --stage native --codec current --max-circuits 6 --workers 6 2>&1 | grep -v Warn
  echo "chunk $i rc ${PIPESTATUS[0]} wall $(( $(date +%s) - s )) s"
done
echo LOOPDONE

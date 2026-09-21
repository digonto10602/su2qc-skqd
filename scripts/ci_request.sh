#!/bin/bash
# Ask Perlmutter to run one allowlisted job on the current master.  Usage: scripts/ci_request.sh L2
set -euo pipefail
TOKEN="${1:?usage: ci_request.sh <smoke|E1|E2|E3|S1|L1..L5>}"
cd "$(git rev-parse --show-toplevel)"
git pull -q --rebase --autostash origin master
mkdir -p ci
printf '%s\n# requested %s from %s nonce %s\n' "$TOKEN" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(hostname)" "$(date +%s%N)$RANDOM" > ci/request.txt
git add ci/request.txt
git commit -qm "ci: request $TOKEN"
git push -q origin HEAD:master
echo "request $(git log -1 --format=%H -- ci/request.txt) ($TOKEN) pushed; picked up at :07 past the hour (UTC)"

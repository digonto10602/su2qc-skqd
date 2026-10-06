#!/bin/bash
# Ask Perlmutter to run allowlisted jobs on the current master.
#
#   scripts/ci_request.sh C1_IDEAL C3_AER C2_CAL C4_FCELLS_A   # one request file per token, ONE commit
#   scripts/ci_request.sh --legacy L2                          # the one-job poller's ci/request.txt
#
# Each token becomes ci/requests/<NNN>-<TOKEN>.txt (first line the token, then a nonce comment);
# the poller (ci/poll_concurrent.sh, prompts/33 section 7c) runs every request once, up to
# MAX_CONCURRENT at a time and MAX_JOBS_PER_DAY per UTC day.  The one-job poller (ci/poll.sh as
# installed before prompts/33) reads ONLY ci/request.txt: use --legacy until the owner has
# installed the concurrent poller.
set -euo pipefail
LEGACY=0
if [ "${1:-}" = "--legacy" ]; then LEGACY=1; shift; fi
[ "$#" -ge 1 ] || { echo "usage: ci_request.sh [--legacy] TOKEN [TOKEN ...]" >&2; exit 64; }
for t in "$@"; do
  [ "$t" = "$(printf '%s' "$t" | tr -cd 'A-Za-z0-9_')" ] || { echo "bad token '$t'" >&2; exit 64; }
done
cd "$(git rev-parse --show-toplevel)"
git pull -q --rebase --autostash origin master
mkdir -p ci/requests
NONCE() { printf '# requested %s from %s nonce %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(hostname)" "$(date +%s%N)$RANDOM"; }
if [ "$LEGACY" = "1" ]; then
  [ "$#" -eq 1 ] || { echo "--legacy takes exactly one token (ci/request.txt holds one)" >&2; exit 64; }
  { printf '%s\n' "$1"; NONCE; } > ci/request.txt
  git add ci/request.txt
  git commit -qm "ci: request $1"
  git push -q origin HEAD:master
  echo "request $(git log -1 --format=%H -- ci/request.txt) ($1) pushed; picked up at :07 past the hour (UTC)"
  exit 0
fi
LAST=$( { ls ci/requests/ 2>/dev/null || true; } | sed -n 's/^\([0-9][0-9]*\)-.*\.txt$/\1/p' | sort -n | tail -1)
N=$((10#${LAST:-0}))
FILES=()
for t in "$@"; do
  N=$((N + 1))
  f=$(printf 'ci/requests/%03d-%s.txt' "$N" "$t")
  { printf '%s\n' "$t"; NONCE; } > "$f"
  FILES+=("$f")
done
git add "${FILES[@]}"
git commit -qm "ci: request $*"
git push -q origin HEAD:master
echo "requests pushed in $(git log -1 --format=%h): ${FILES[*]}; picked up at :07 past the hour (UTC)"

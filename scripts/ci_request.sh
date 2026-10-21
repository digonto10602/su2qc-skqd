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
# Sync by MERGE, never rebase: the Perlmutter CI pushes merge commits to master, and
# `git pull --rebase` on top of them left the tree mid-rebase (2026-10 incidents).
GITDIR=$(git rev-parse --git-dir)
if [ -d "$GITDIR/rebase-merge" ] || [ -d "$GITDIR/rebase-apply" ] || [ -f "$GITDIR/MERGE_HEAD" ]; then
  echo "a rebase or merge is in progress; finish or abort it first" >&2; exit 65
fi
[ "$(git rev-parse --abbrev-ref HEAD)" = "master" ] || { echo "not on master" >&2; exit 65; }
sync_master() {
  git fetch -q origin master
  git merge -q --no-edit origin/master || { git merge --abort 2>/dev/null || true;
    echo "merge with origin/master failed; resolve by hand" >&2; exit 66; }
}
# push with up to 3 attempts: if the CI pushed in between, merge again and retry
push_master() {
  local i
  for i in 1 2 3; do
    git push -q origin HEAD:master && return 0
    echo "push rejected (attempt $i); merging origin/master and retrying" >&2
    sync_master
  done
  echo "push failed 3 times" >&2; exit 67
}
sync_master
mkdir -p ci/requests
NONCE() { printf '# requested %s from %s nonce %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(hostname)" "$(date +%s%N)$RANDOM"; }
if [ "$LEGACY" = "1" ]; then
  [ "$#" -eq 1 ] || { echo "--legacy takes exactly one token (ci/request.txt holds one)" >&2; exit 64; }
  { printf '%s\n' "$1"; NONCE; } > ci/request.txt
  git add ci/request.txt
  git commit -qm "ci: request $1"
  push_master
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
push_master
echo "requests pushed in $(git log -1 --format=%h): ${FILES[*]}; picked up at :07 past the hour (UTC)"

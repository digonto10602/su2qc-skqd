#!/bin/bash
# skqd-ci poller. Runs hourly from scrontab on the Perlmutter login-node pool.
# Slurm never starts a new scrontab instance while the previous one is still running.
#  1. if the CI job finished: copy its outputs into the repo, commit, push
#  2. if ci/request.txt changed in a new commit: check allowlist + daily cap, snapshot the code,
#     submit ONE GPU job with resources fixed here (not in the repo), record status, push
set -euo pipefail
CI="$HOME/skqd-ci"
source "$CI/ci.conf"
cd "$REPO"
unset SLURM_MEM_PER_CPU          # set by scrontab; breaks sbatch (NERSC docs)
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(now)] $*"; }

status() {   # state token jobid req_sha code_sha note
  mkdir -p ci
  printf '{\n "state": "%s",\n "token": "%s",\n "jobid": "%s",\n "request_sha": "%s",\n "code_sha": "%s",\n "note": "%s",\n "updated_utc": "%s"\n}\n' \
    "$1" "$2" "$3" "$4" "$5" "$6" "$(now)" > ci/status.json
}
sync_remote() {
  if ! git pull -q --rebase origin "$BRANCH"; then
    git rebase --abort 2>/dev/null || true
    log "ERROR: rebase conflict; fix by hand in $REPO"; exit 1
  fi
  git push -q origin "HEAD:$BRANCH" || log "WARN: push failed, will retry next hour"
}

# ---- 1. harvest a finished job ------------------------------------------------------
if [ -s "$CI/current" ]; then
  read -r JID TOKEN REQ CODE SNAP < "$CI/current"
  if squeue -h -j "$JID" -o %T 2>/dev/null | grep -q .; then
    log "job $JID ($TOKEN) still queued/running"
  else
    STATE=$(sacct -n -X -P -j "$JID" -o State 2>/dev/null | head -1 || true)
    STATE=${STATE:-UNKNOWN}
    mkdir -p reports validation
    [ -d "$SNAP/validation" ] && cp -r "$SNAP/validation/." validation/
    [ -d "$SNAP/reports" ]    && cp -r "$SNAP/reports/."    reports/
    status "done" "$TOKEN" "$JID" "$REQ" "$CODE" "slurm state: $STATE"
    git add -A -- reports validation ci/status.json
    git commit -qm "ci: results job $JID ($TOKEN, $STATE) for request $REQ" || true
    : > "$CI/current"
    log "harvested job $JID ($STATE)"
  fi
fi

sync_remote
[ -s "$CI/current" ] && exit 0            # one CI job at a time

# ---- 2. new request? -------------------------------------------------------------------
[ -f ci/request.txt ] || exit 0
REQ=$(git log -1 --format=%H -- ci/request.txt)
[ "$REQ" = "$(cat "$CI/last_request" 2>/dev/null || true)" ] && exit 0

TODAY=$(grep -c "^$(date -u +%F)" "$CI/submitted.log" 2>/dev/null || true)
if [ "${TODAY:-0}" -ge "$MAX_JOBS_PER_DAY" ]; then
  log "daily cap reached; request $REQ waits for tomorrow (UTC)"; exit 0
fi
echo "$REQ" > "$CI/last_request"          # consumed, whatever happens next

TOKEN=$( (grep -v '^#' ci/request.txt || true) | head -1 | tr -cd 'A-Za-z0-9_')
LINE=$(awk -v t="$TOKEN" '$1==t {print; exit}' "$CI/allowed_jobs")
CODE=$(git rev-parse HEAD)
if [ -z "$TOKEN" ] || [ -z "$LINE" ]; then
  status "refused" "$TOKEN" "" "$REQ" "$CODE" "token not in allowlist"
  git add ci/status.json && git commit -qm "ci: refused '$TOKEN' for request $REQ"
  sync_remote; log "refused '$TOKEN'"; exit 0
fi
read -r _ WALL GPUS <<< "$LINE"
[ "$GPUS" = "2" ] || GPUS=1

# Snapshot the exact commit, so later pulls cannot change code under a running job.
SNAP="$RUNS/${CODE:0:12}-$(date -u +%Y%m%d%H%M%S)"
mkdir -p "$SNAP"
git archive "$CODE" | tar -x -C "$SNAP"
mkdir -p "$SNAP/validation" "$SNAP/reports"
JOBFILE="$SNAP/jobs/gate.sbatch"; [ "$TOKEN" = "smoke" ] && JOBFILE="$SNAP/jobs/smoke.sbatch"

JID=$(sbatch --parsable -J skqd-ci -A "$ACCOUNT_GPU" -C gpu -q shared \
        -n 1 -c $((32 * GPUS)) --gpus-per-task="$GPUS" -t "$WALL" -D "$SNAP" \
        -o "$SNAP/reports/ci-%j.out" \
        --export=ALL,CI_GATE="$TOKEN",CI_CODE_SHA="$CODE",CI_REQUEST_SHA="$REQ" \
        "$JOBFILE")
echo "$JID $TOKEN $REQ $CODE $SNAP" > "$CI/current"
echo "$(date -u +%F) $(now) $JID $TOKEN $REQ $CODE" >> "$CI/submitted.log"
status "submitted" "$TOKEN" "$JID" "$REQ" "$CODE" "walltime $WALL, gpus $GPUS"
git add ci/status.json && git commit -qm "ci: submitted job $JID ($TOKEN) for request $REQ"
sync_remote
log "submitted job $JID ($TOKEN, $WALL, $GPUS GPU)"

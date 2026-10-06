#!/bin/bash
# skqd-ci poller with concurrent jobs (prompts/33 section 7c).  Runs hourly from scrontab on the
# Perlmutter login-node pool; Slurm never starts a new scrontab instance while the previous one runs.
#
# PROPOSED REPLACEMENT of ci/poll.sh.  The agents may not edit ci/poll.sh (the owner's permission
# rule), so this file sits beside it; the owner reviews it and either moves it over ci/poll.sh
# (`git mv -f ci/poll_concurrent.sh ci/poll.sh`) or installs it directly
# (`POLLER=ci/poll_concurrent.sh bash ci/install_skqd_ci.sh`).  tests/test_ci_poller_sim.py runs it.
#
#  1. harvest EVERY finished CI job: copy the files it wrote into the repo, one commit per job
#  2. sync with GitHub (pull --rebase, push); a rebase conflict aborts the run
#  3. submit pending requests -- ci/requests/*.txt in file-name order, then the legacy
#     ci/request.txt -- while fewer than MAX_CONCURRENT jobs run and the daily cap holds.
#     Allowlist and resources come from ~/skqd-ci (never from the repo); each request runs once.
#
# A request is the identity <path>@<commit that last touched the file>; consumed identities are
# appended to ~/skqd-ci/consumed, so a request runs once and re-requesting is a new commit that
# touches a request file (a new file or a new nonce line).  The snapshot of a job is
# `git archive <that commit>`, so later commits never change the code under a running job.
# MAX_CONCURRENT absent from ci.conf = 1 = the behaviour of the one-job poller this replaces.
set -euo pipefail
CI="$HOME/skqd-ci"
source "$CI/ci.conf"
MAX_CONCURRENT="${MAX_CONCURRENT:-1}"
cd "$REPO"
unset SLURM_MEM_PER_CPU          # set by scrontab; breaks sbatch (NERSC docs)
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(now)] $*"; }
RUNNING="$CI/running"            # one file per submitted job: "JID TOKEN REQUEST CODE SNAP"
CONSUMED="$CI/consumed"          # one request identity per line
mkdir -p "$RUNNING"
touch "$CONSUMED"

status() {   # state token jobid request(path@sha) code_sha note -> ci/status/<TOKEN>.json + ci/status.json
  mkdir -p ci/status
  local tok="${2:-_invalid}" req="$4" body
  [ -n "$tok" ] || tok="_invalid"
  body=$(printf '{\n "state": "%s",\n "token": "%s",\n "jobid": "%s",\n "request": "%s",\n "request_sha": "%s",\n "code_sha": "%s",\n "note": "%s",\n "updated_utc": "%s"\n}' \
    "$1" "$2" "$3" "$req" "${req##*@}" "$5" "$6" "$(now)")
  printf '%s\n' "$body" > "ci/status/${tok}.json"
  printf '%s\n' "$body" > ci/status.json          # legacy: the latest event
}
sync_remote() {
  if ! git pull -q --rebase origin "$BRANCH"; then
    git rebase --abort 2>/dev/null || true
    log "ERROR: rebase conflict; fix by hand in $REPO"; exit 1
  fi
  git push -q origin "HEAD:$BRANCH" || log "WARN: push failed, will retry next hour"
}
harvest_copy() {   # snapshot -> repo: only files the job created or changed (never revert others)
  local snap="$1" rel sum
  if [ ! -f "$snap/.ci_manifest" ]; then   # a snapshot of the one-job poller: copy as it did
    if [ -d "$snap/validation" ]; then cp -r "$snap/validation/." validation/; fi
    if [ -d "$snap/reports" ]; then cp -r "$snap/reports/." reports/; fi
    return 0
  fi
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    sum=$(cd "$snap" && sha256sum -- "$rel" | cut -d' ' -f1)
    if ! grep -qxF -- "$sum  $rel" "$snap/.ci_manifest"; then
      mkdir -p "$(dirname -- "$rel")"
      cp -- "$snap/$rel" "$rel"
    fi
  done < <(cd "$snap" && { find validation reports -type f 2>/dev/null || true; } | LC_ALL=C sort)
}

# ---- 0. migrate the one-job poller's state (idempotent) -----------------------------------
if [ -s "$CI/current" ]; then
  read -r JID _ < "$CI/current"
  cp "$CI/current" "$RUNNING/$JID"
  : > "$CI/current"
  log "migrated running job $JID from $CI/current"
fi

# ---- 1. harvest every finished job (always before any submission) --------------------------
for f in "$RUNNING"/*; do
  [ -e "$f" ] || continue
  read -r JID TOKEN REQ CODE SNAP < "$f"
  if squeue -h -j "$JID" -o %T 2>/dev/null | grep -q .; then
    log "job $JID ($TOKEN) still queued/running"
    continue
  fi
  STATE=$(sacct -n -X -P -j "$JID" -o State 2>/dev/null | head -1 || true)
  STATE=${STATE:-UNKNOWN}
  mkdir -p reports validation
  harvest_copy "$SNAP"
  status "done" "$TOKEN" "$JID" "$REQ" "$CODE" "slurm state: $STATE"
  git add -A -- reports validation ci/status.json ci/status
  git commit -qm "ci: results job $JID ($TOKEN, $STATE) for request $REQ" || true
  rm -f "$f"
  log "harvested job $JID ($TOKEN, $STATE)"
done

sync_remote

# ---- 2. submit pending requests -------------------------------------------------------------
requests() {   # file-name order, then the legacy single request file
  { ls ci/requests/*.txt 2>/dev/null || true; } | LC_ALL=C sort
  if [ -f ci/request.txt ]; then echo ci/request.txt; fi
}
CHANGED=0
for RQ in $(requests); do
  SHA=$(git log -1 --format=%H -- "$RQ" 2>/dev/null || true)
  [ -n "$SHA" ] || continue                       # not committed: not a request
  ID="$RQ@$SHA"
  if grep -qxF -- "$ID" "$CONSUMED"; then continue; fi
  if [ "$RQ" = "ci/request.txt" ] && [ "$SHA" = "$(cat "$CI/last_request" 2>/dev/null || true)" ]; then
    echo "$ID" >> "$CONSUMED"                     # consumed by the one-job poller already
    continue
  fi
  NRUN=$(find "$RUNNING" -mindepth 1 -maxdepth 1 -type f | wc -l)
  if [ "$NRUN" -ge "$MAX_CONCURRENT" ]; then
    log "$NRUN job(s) running (MAX_CONCURRENT=$MAX_CONCURRENT); $ID waits"; break
  fi
  TODAY=$(grep -c "^$(date -u +%F)" "$CI/submitted.log" 2>/dev/null || true)
  if [ "${TODAY:-0}" -ge "$MAX_JOBS_PER_DAY" ]; then
    log "daily cap reached; request $ID waits for tomorrow (UTC)"; break
  fi
  echo "$ID" >> "$CONSUMED"                       # consumed, whatever happens next
  if [ "$RQ" = "ci/request.txt" ]; then echo "$SHA" > "$CI/last_request"; fi
  CHANGED=1

  TOKEN=$( (grep -v '^#' "$RQ" || true) | head -1 | tr -cd 'A-Za-z0-9_')
  LINE=""
  if [ -n "$TOKEN" ]; then LINE=$(awk -v t="$TOKEN" '$1==t {print; exit}' "$CI/allowed_jobs"); fi
  CODE="$SHA"                                      # the snapshot is the requested commit
  if [ -z "$TOKEN" ] || [ -z "$LINE" ]; then
    status "refused" "$TOKEN" "" "$ID" "$CODE" "token not in allowlist"
    git add -A -- ci/status.json ci/status
    git commit -qm "ci: refused '$TOKEN' for request $ID" || true
    log "refused '$TOKEN' ($ID)"; continue
  fi
  read -r _ WALL GPUS <<< "$LINE"
  [ "$GPUS" = "2" ] || GPUS=1

  # Snapshot the exact commit, so later pulls cannot change code under a running job.
  SNAP="$RUNS/${CODE:0:12}-$(date -u +%Y%m%d%H%M%S)-$TOKEN"
  while [ -e "$SNAP" ]; do SNAP="$SNAP.x"; done
  mkdir -p "$SNAP"
  git archive "$CODE" | tar -x -C "$SNAP"
  mkdir -p "$SNAP/validation" "$SNAP/reports"
  # what the snapshot held before the job: the harvest copies back only what the job wrote
  (cd "$SNAP" && { find validation reports -type f -print0 2>/dev/null || true; } | LC_ALL=C sort -z \
     | xargs -0 -r sha256sum --) > "$SNAP/.ci_manifest"
  JOBFILE="$SNAP/jobs/gate.sbatch"; [ "$TOKEN" = "smoke" ] && JOBFILE="$SNAP/jobs/smoke.sbatch"

  if ! JID=$(sbatch --parsable -J skqd-ci -A "$ACCOUNT_GPU" -C gpu -q shared \
          -n 1 -c $((32 * GPUS)) --gpus-per-task="$GPUS" -t "$WALL" -D "$SNAP" \
          -o "$SNAP/reports/ci-%j.out" \
          --export=ALL,CI_GATE="$TOKEN",CI_CODE_SHA="$CODE",CI_REQUEST_SHA="$SHA" \
          "$JOBFILE"); then
    status "error" "$TOKEN" "" "$ID" "$CODE" "sbatch failed"
    git add -A -- ci/status.json ci/status
    git commit -qm "ci: sbatch failed for '$TOKEN' ($ID)" || true
    log "ERROR: sbatch failed for $TOKEN ($ID)"; continue
  fi
  JID=${JID%%;*}
  echo "$JID $TOKEN $ID $CODE $SNAP" > "$RUNNING/$JID"
  echo "$(date -u +%F) $(now) $JID $TOKEN $SHA $CODE $RQ" >> "$CI/submitted.log"
  status "submitted" "$TOKEN" "$JID" "$ID" "$CODE" "walltime $WALL, gpus $GPUS"
  git add -A -- ci/status.json ci/status
  git commit -qm "ci: submitted job $JID ($TOKEN) for request $ID" || true
  log "submitted job $JID ($TOKEN, $WALL, $GPUS GPU) for $ID"
done
if [ "$CHANGED" = "1" ]; then sync_remote; fi
exit 0

#!/bin/bash
# Run ONCE on a Perlmutter login node, from the repo root:   bash ci/install_skqd_ci.sh
# Copies the CI driver OUT of the repo into ~/skqd-ci, so commits (by you or an agent)
# can never change what the driver does, which jobs are allowed, or how much they may use.
set -euo pipefail

ACCOUNT_GPU="m4135_g"          # GPU jobs are charged here
ACCOUNT_CRON="m4135"           # the hourly scrontab poller (login-node pool)
REPO="$(git rev-parse --show-toplevel)"
CI="$HOME/skqd-ci"
RUNS="$SCRATCH/skqd-ci-runs"

mkdir -p "$CI" "$RUNS"
[ -e "$CI/poll.sh" ] && cp "$CI/poll.sh" "$CI/poll.sh.bak.$(date +%s)"
cp "$REPO/ci/poll.sh" "$CI/poll.sh"
chmod 700 "$CI/poll.sh"

# Absolute paths resolved now: scrontab jobs may not have $SCRATCH set.
cat > "$CI/ci.conf" <<CONF
REPO="$REPO"
RUNS="$RUNS"
ACCOUNT_GPU="$ACCOUNT_GPU"
BRANCH="master"
MAX_JOBS_PER_DAY=6
CONF

# Allowlist: TOKEN  MAX_WALLTIME  GPUS(1 or 2, shared QOS)  -- edit only here, never in the repo
if [ ! -e "$CI/allowed_jobs" ]; then
cat > "$CI/allowed_jobs" <<'ALLOW'
smoke 00:15:00 1
E1    00:30:00 1
E2    00:30:00 1
E3    00:30:00 1
S1    01:00:00 1
L1    00:30:00 1
L2    00:30:00 1
L3    00:30:00 1
L4    01:00:00 1
L5    00:30:00 1
ALLOW
fi

cat > "$CI/scrontab.txt" <<CRON
#SCRON -q cron
#SCRON -C cron
#SCRON -A $ACCOUNT_CRON
#SCRON -t 00:10:00
#SCRON -J skqd-ci-poll
#SCRON -o $CI/poll.log
#SCRON --open-mode=append
7 * * * * $CI/poll.sh
CRON

git -C "$REPO" config user.name  "skqd-ci (perlmutter)"
git -C "$REPO" config user.email "skqd-ci@users.noreply.github.com"

echo "Installed to $CI:"
ls -l "$CI"
echo
echo "Next: review $CI/allowed_jobs, run $CI/poll.sh once by hand, then install the schedule with"
echo "      scrontab $CI/scrontab.txt     (or: scrontab -e  and paste the file)"

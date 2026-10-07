# skqd-ci: how to run tests on Perlmutter (rules for Claude / any agent)

You have NO login to Perlmutter and must not try to get one (no ssh, sshproxy, SF API).
Perlmutter pulls this repo every hour at :07 UTC and runs at most one allowlisted job.

## Loop
1. Make your change, run the fast CPU tests locally, commit, push to master.
2. `scripts/ci_request.sh <TOKEN>`  - TOKEN is one of: smoke E1 E2 E3 S1 L1 L2 L3 L4 L5
3. Wait. Check with `scripts/ci_check.sh`  (exit 0 done, 2 pending, 3 refused).
   Check no more often than every 15 minutes; a job usually needs 1-3 hours round trip
   (poll interval + GPU queue). Between checks, do useful local work.
4. Read `validation/ci_gate_<TOKEN>.json` (or `validation/ci_smoke.json`) and `reports/ci-<jobid>.out`.
   Fix, push, request again.

## Limits (enforced on Perlmutter, not changeable from the repo)
- one job at a time; max 6 jobs per UTC day; walltime per token 15-60 min; 1 GPU (shared QOS)
- a request made while a job is running is picked up after that job finishes
- only the first non-comment line of ci/request.txt counts; unknown tokens are refused

## Never
- edit `ci/status.json`, `ci/poll.sh`, `reports/ci-*.out`, `validation/ci_*.json` (the CI writes them)
- request the same token again while its previous request is still pending
- request more than 3 jobs in a row without a passing result in between: stop and write
  prompts/BLOCKED_<gate>.md for the planner / the user instead
- run anything long on the laptop to "save queue time"; 30-minute rule from the package still holds

## After the owner installs the concurrent poller (prompts/33 section 7c)
The new poller is `ci/poll_concurrent.sh` (agents may not edit `ci/poll.sh`; the owner moves it over or installs
it with `POLLER=ci/poll_concurrent.sh bash ci/install_skqd_ci.sh`).  Until the owner says it is installed, use
`scripts/ci_request.sh --legacy TOKEN` (the one-job `ci/request.txt` path).  Afterwards:
- `scripts/ci_request.sh T1 T2 ...` writes one `ci/requests/<NNN>-<TOKEN>.txt` per token in ONE commit and pushes;
  each request runs once, up to `MAX_CONCURRENT` at a time and `MAX_JOBS_PER_DAY` per UTC day (`~/skqd-ci/ci.conf`).
- `scripts/ci_check.sh` lists every request (pending / submitted / done / refused / error);
  `scripts/ci_check.sh TOKEN` shows the latest request of one token in full.  Per-token states are in
  `ci/status/<TOKEN>.json` (written by the CI only, like `ci/status.json`).
- The prompts/33 campaign tokens are listed in `scripts/gate_tokens.json` and `ci/allowed_jobs.campaign33`.

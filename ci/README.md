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

## The `skqd-pecos` env for token C3_LE (prompts/35 section 3.6 and owner action 1)
Token `C3_LE` (2x3 f-cell circuits on pytket-quantinuum's local H2-1LE emulator) runs in its own conda env:
`jobs/gate.sbatch` reads `jobs/env/C3_LE` (one line: `skqd-pecos`) and does `conda activate skqd-pecos` before
`python scripts/run_gate.py C3_LE`.  The env does not exist on Perlmutter yet.  The package needs no install:
`scripts/campaign33.py` puts `src/` and `scripts/` on `sys.path` itself (the same way the `skqd` env runs every
other token), so the env needs only the engine and the modules of the `engine` preflight set
(`scripts/campaign33.py PREFLIGHT_MODULES["engine"]`: numpy, skqd.report, skqd.campaign33.{tokens,stats,engines}).
Paste on a Perlmutter login node (the command of `data/campaign33/engines.json C3_LE.perlmutter_env_if_kept`,
**without** a `numpy<2` pin, which `engines.json C3_LE.attempts[0]` shows unsatisfiable):
```
module load python
conda create -n skqd-pecos python=3.12 -y
conda activate skqd-pecos
pip install "pytket~=2.17" "pytket-quantinuum[pecos]==0.59.3" scipy threadpoolctl
python -c "import pytket, pytket.extensions.quantinuum, pytket_pecos, scipy; print('skqd-pecos ok')"
cd $SCRATCH/su2qc-skqd && CI_GATE=C3_LE python scripts/campaign33.py --token C3_LE --dry-run   # path check, CPU
```
No `PYTHONPATH` line is needed.  Tell the coordinator when the env exists; `C3_LE` is requested only after the
last campaign-33 must-run request (prompts/35 R4).  The laptop smoke of the same engine path is
`validation/QEMU_2x3_laptop_smoke.json`.

## Token QV_2x4 (prompts/35 section 4; owner action 2)
`scripts/gate_tokens.json` carries `QV_2x4` (class 3, 01:00:00, 1 GPU, env `skqd`; appended after the campaign-33
tokens, whose indices and seeds are unchanged).  Its allowlist line is `ci/allowed_jobs.q35`; after the maintenance:
`cat $SCRATCH/su2qc-skqd/ci/allowed_jobs.q35 >> ~/skqd-ci/allowed_jobs`.

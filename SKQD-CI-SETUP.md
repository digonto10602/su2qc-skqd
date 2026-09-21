# skqd-ci: automatic GPU testing on Perlmutter, step by step

Project account `m4135_g` · repo `digonto10602/su2qc-skqd` (branch `master`) · written 21 Sept 2026

## How it works

```
 laptop / Claude                      GitHub                         Perlmutter
 ───────────────                      ──────                         ──────────
 edit, commit, push ───────────────►  master  ◄────── git pull ───── scrontab, every hour at :07 UTC
 scripts/ci_request.sh L2 ─────────►  ci/request.txt                 ~/skqd-ci/poll.sh
                                                                        │ allowlist + caps (in $HOME, not in repo)
                                                                        │ snapshot commit → sbatch 1 GPU, shared QOS
                                                                        ▼
 scripts/ci_check.sh ◄─────────────  ci/status.json  ◄──── git push ─ results: validation/ci_*.json,
 reads results                        reports/ci-<job>.out              reports/ci-<job>.out
```

Your laptop and Claude never hold a NERSC credential. Perlmutter holds one secret: a GitHub
deploy key that can write to this repository only. You log in to NERSC by hand (password + OTP)
only for the one-time setup below.

Every round trip takes up to 1 hour of polling plus the GPU queue wait, so expect results in
roughly 1 to 3 hours. This is for re-testing gates without you. For live debugging, keep using an
interactive `salloc` session.

## What is in the bundle

| file | lives | what it does |
|---|---|---|
| `ci/install_skqd_ci.sh` | repo | one-time installer run on Perlmutter; copies the poller out of the repo into `~/skqd-ci` |
| `ci/poll.sh` | repo → copied to `~/skqd-ci/poll.sh` | the hourly driver (harvest finished job, submit new request) |
| `ci/README.md` | repo | the rules for Claude / any agent (paste into `CLAUDE.md`) |
| `jobs/smoke.sbatch`, `scripts/ci_smoke.py` | repo | GPU smoke test: Qiskit Aer GPU, CUDA-Q `nvidia`, 28-qubit memory check |
| `jobs/gate.sbatch` | repo | runs `python scripts/run_gate.py <GATE>` and records exit code in `validation/ci_gate_<GATE>.json` |
| `scripts/ci_request.sh`, `scripts/ci_check.sh` | repo | laptop side: request a run / read its result |

Created by the installer on Perlmutter, and never touched by a commit:
`~/skqd-ci/{poll.sh, ci.conf, allowed_jobs, scrontab.txt, submitted.log, current, last_request, poll.log}`.

---

## Step 1 — Laptop: add the bundle to the repo

```bash
cd ~/path/to/su2qc-skqd
git pull
tar -xzkf ~/Downloads/skqd-ci-bundle.tar.gz      # -k: never overwrite files you already have
git status                                       # expect ci/, jobs/*.sbatch, scripts/ci_*.{sh,py}
cat ci/README.md >> CLAUDE.md                    # the agent rules
git add ci jobs scripts CLAUDE.md
git commit -m "Add skqd-ci: hourly Perlmutter GPU testing"
git push origin master
```

Do **not** create `ci/request.txt` yet. Any commit that changes that file triggers a job.

## Step 2 — Perlmutter: log in (the only step that needs your OTP)

```bash
ssh <user>@perlmutter.nersc.gov        # password + OTP
```

## Step 3 — Perlmutter: a deploy key for this one repo

```bash
ssh-keygen -t ed25519 -f ~/.ssh/skqd_deploy -N "" -C "skqd-ci perlmutter"
cat >> ~/.ssh/config <<'CFG'

Host github-skqd
    HostName github.com
    User git
    IdentityFile ~/.ssh/skqd_deploy
    IdentitiesOnly yes
CFG
chmod 600 ~/.ssh/config
cat ~/.ssh/skqd_deploy.pub
```

On GitHub go to **su2qc-skqd → Settings → Deploy keys → Add deploy key**. Paste the public key,
title it `perlmutter-ci` and tick **Allow write access**. Then test from Perlmutter:

```bash
ssh -T git@github-skqd           # "Hi digonto10602/su2qc-skqd! You've successfully authenticated..."
```

If port 22 is blocked, change the two lines in `~/.ssh/config` to `HostName ssh.github.com` and
`Port 443`, then test again.

## Step 4 — Perlmutter: clone the repo

```bash
cd $SCRATCH
git clone git@github-skqd:digonto10602/su2qc-skqd.git
cd su2qc-skqd && git log --oneline -1
```

`$SCRATCH` is purged only for files unused for weeks. A clone that is pulled every hour stays in
use, and GitHub keeps the master copy anyway.

## Step 5 — Perlmutter: the Python environment

```bash
module load python
conda create -n skqd python=3.12 -y
conda activate skqd
pip install numpy scipy pytest qiskit qiskit-aer-gpu cudaq
python -c "import qiskit, qiskit_aer; print(qiskit.__version__, qiskit_aer.__version__)"
```

Also install whatever else `scripts/run_gate.py` imports. Do not `module load cudatoolkit` on top
of this environment (NERSC's advice). There is no GPU on the login node, so GPU problems only
show up in Step 8's smoke test. That is what the smoke test is for.

## Step 6 — Perlmutter: install the CI driver

```bash
cd $SCRATCH/su2qc-skqd
bash ci/install_skqd_ci.sh
cat ~/skqd-ci/allowed_jobs
```

`allowed_jobs` is the whole list of what the CI will ever run: `TOKEN  MAX_WALLTIME  GPUS`.
Edit it here (for example `nano ~/skqd-ci/allowed_jobs`) to add or remove gates or change their
walltime. GPUS may be 1 or 2, because the shared QOS takes 1 or 2 GPUs. Other limits are in
`~/skqd-ci/ci.conf` (`MAX_JOBS_PER_DAY=6`).

Run the poller once by hand. With no request it should print nothing and exit 0:

```bash
~/skqd-ci/poll.sh; echo "exit=$?"
```

## Step 7 — Perlmutter: start the hourly schedule

```bash
cat ~/skqd-ci/scrontab.txt
scrontab ~/skqd-ci/scrontab.txt       # if your scrontab refuses a file: scrontab -e, paste it, save
scrontab -l                           # shows the entry
squeue --me                           # a job named skqd-ci-poll in the cron QOS
```

The file looks like this. `m4135` is the CPU side of your project; if Slurm rejects it, use
`m4135_g`:

```
#SCRON -q cron
#SCRON -C cron
#SCRON -A m4135
#SCRON -t 00:10:00
#SCRON -J skqd-ci-poll
#SCRON -o /global/homes/<x>/<user>/skqd-ci/poll.log
#SCRON --open-mode=append
7 * * * * /global/homes/<x>/<user>/skqd-ci/poll.sh
```

Scrontab times are UTC. `7 * * * *` means 7 minutes past every hour.

## Step 8 — First end-to-end test (the smoke test)

On the laptop:

```bash
scripts/ci_request.sh smoke
```

To skip waiting for :07, run `~/skqd-ci/poll.sh` once by hand on Perlmutter. It prints
`submitted job <id> (smoke, 00:15:00, 1 GPU)`. When `squeue --me` no longer lists that job, run
`~/skqd-ci/poll.sh` again (or wait for the next hour). It prints `harvested job <id> (COMPLETED)`
and pushes. Then, on the laptop:

```bash
scripts/ci_check.sh        # exit 0 done · 2 pending · 3 refused
```

A pass looks like `"pass": true` for `qiskit_aer_gpu`, `cudaq_nvidia` and `aer_28q_memory` in
`validation/ci_smoke.json`. The core of that test:

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
qc = QuantumCircuit(12); qc.h(0)
for i in range(11): qc.cx(i, i + 1)
for i in range(12): qc.rz(2 * 0.245, i)          # diagonal phases: support must stay {0…0, 1…1}
qc.measure_all()
sim = AerSimulator(method="statevector", device="GPU")
counts = sim.run(transpile(qc, sim), shots=4000).result().get_counts()
assert set(counts) <= {"0" * 12, "1" * 12}
```

```python
import cudaq
@cudaq.kernel
def ghz_phases(n: int, t: float):
    q = cudaq.qvector(n); h(q[0])
    for i in range(n - 1): x.ctrl(q[i], q[i + 1])
    for i in range(n): rz(2.0 * t, q[i])
cudaq.set_target("nvidia")
print(cudaq.sample(ghz_phases, 12, 0.245, shots_count=4000))
```

If `cudaq_nvidia` fails and the error mentions CUDA, the `cudaq` build does not match the node's
driver. Reinstall it for the CUDA major version shown by `nvidia-smi` on a GPU node. Your
known-good container (`podman-hpc pull nvcr.io/nvidia/quantum/cuda-quantum:<tag>`) is the fallback.

## Step 9 — Hand it to Claude

With `ci/README.md` in `CLAUDE.md`, start Claude Code (or Hermes) in the repo on the laptop:

```text
Read CLAUDE.md, STATE.md and ci/README.md. Continue the next open gate. For anything that needs a
GPU, push and use scripts/ci_request.sh <GATE>, then scripts/ci_check.sh no more than every 15
minutes, doing local CPU work in between. Record every CI result in STATE.md and the gate report.
Stop and write prompts/BLOCKED_<gate>.md after 3 failed GPU runs in a row.
```

Claude needs only `git`, `scripts/ci_request.sh` and `scripts/ci_check.sh`. It never touches NERSC.

## Cost and limits

A shared-QOS job with $G$ GPUs is charged as a fraction $G/4$ of a GPU node:

$$C = \frac{G}{4}\, t\, f ,$$

where $C$ is the charge in GPU node-hours, $G \in \{1,2\}$ is the number of GPUs, $t$ is the
elapsed wall time in hours, and $f = 1$ is the QOS charge factor. With the defaults
($G=1$, at most 6 jobs per UTC day, walltime at most 1 h) the worst case is

$$C_{\text{day}} \le 6 \times \tfrac{1}{4} \times 1\ \text{h} = 1.5\ \text{GPU node-hours per day}.$$

The hourly poller itself runs in the `cron` QOS on login nodes.

Safety properties (checked in a local simulation with a fake Slurm and a fake GitHub remote):
unknown tokens are refused and reported; resources come from `sbatch` flags in `~/skqd-ci`, which
override anything in the repo's job files; one job at a time; a request is never run twice; the
daily cap holds; jobs run on a frozen snapshot of the requested commit; results are pushed from
the login node, so compute nodes need no internet access.

## Day to day

| task | command (Perlmutter) |
|---|---|
| see what the CI did | `tail -50 ~/skqd-ci/poll.log` · `cat ~/skqd-ci/submitted.log` |
| pause | `scrontab -e`, put `#` before the `7 * * * *` line |
| stop for good | `scrontab -r` (removes all your scrontab entries) |
| allow a new gate | add a line to `~/skqd-ci/allowed_jobs` |
| update the poller | review `git diff` of `ci/poll.sh`, then `bash ci/install_skqd_ci.sh` again (it backs up the old one) |
| kill a runaway job | `scancel <jobid>`; the next poll harvests it as CANCELLED |

Two things live outside the repo on purpose: the allowlist and the poller. An agent can propose a
change to `ci/poll.sh` in a commit, but it only takes effect when you re-run the installer.

## Troubleshooting

`poll.log` says `rebase conflict`: someone edited a CI-owned file (`ci/status.json`,
`reports/ci-*`, `validation/ci_*`). In `$SCRATCH/su2qc-skqd`, run `git status`, resolve it and
push. The CI resumes on the next hour.

`sbatch: error: invalid account or QOS`: check `sacctmgr show assoc user=$USER format=account,qos%60`
and fix `ACCOUNT_GPU` in `~/skqd-ci/ci.conf`.

The job fails immediately with a conda error: in `jobs/*.sbatch`, replace `conda activate skqd`
with the environment's python path (`conda env list` shows it).

`ci_check.sh` says pending for many hours: look at `squeue --me` and `poll.log`. The daily cap
also delays requests to the next UTC day and logs it.

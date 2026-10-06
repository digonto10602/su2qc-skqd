"""
The concurrent CI poller (prompts/33 section 7c) run for real in a sandbox: the actual poller
script, a bare git repository as "GitHub", a poller clone as "$SCRATCH/su2qc-skqd", an agent clone
that pushes request files, and stub `sbatch` / `squeue` / `sacct` that keep job state in files.

Nothing here touches the real repository's remote, Slurm or Perlmutter: every git command runs in
the temp directory and HOME points into it, so ~/skqd-ci is the sandbox's.

What is asserted (the safety properties of the one-job poller, kept, plus the new ones):
unknown token refused; 5 requests at MAX_CONCURRENT=2 -> 2 submitted, the next 2 after harvest;
the daily cap stops submission; no request is ever submitted twice; the snapshot is the requested
commit; the legacy ci/request.txt path still works with MAX_CONCURRENT absent (one job at a time);
the one-job poller's `current` / `last_request` state is migrated without re-running anything;
a harvest copies only what the job wrote (never reverts a newer repo file); a rebase conflict
aborts before any submission; a failed sbatch is recorded and not retried.
"""
import datetime
import json
import os
import shutil
import subprocess
import textwrap

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CAND = [os.path.join(ROOT, "ci", "poll_concurrent.sh"), os.path.join(ROOT, "ci", "poll.sh")]
POLLER = next(p for p in _CAND if os.path.exists(p))

pytestmark = pytest.mark.skipif(shutil.which("git") is None or shutil.which("bash") is None,
                                reason="needs git and bash")

STUB_SBATCH = r"""#!/bin/bash
# stub sbatch: records its arguments, assigns a job id, marks the job RUNNING
S="$SIM_SLURM"; mkdir -p "$S/jobs"
[ -f "$S/fail_next" ] && { rm -f "$S/fail_next"; echo "sbatch: error: stub failure" >&2; exit 1; }
N=$(( $(cat "$S/counter" 2>/dev/null || echo 1000) + 1 )); echo "$N" > "$S/counter"
D=""; EXPORT=""; prev=""
for a in "$@"; do
  [ "$prev" = "-D" ] && D="$a"
  case "$a" in --export=*) EXPORT="${a#--export=}";; esac
  prev="$a"
done
echo RUNNING > "$S/jobs/$N"
printf '%s\t%s\t%s\t%s\n' "$N" "$D" "$EXPORT" "${@: -1}" >> "$S/sbatch.log"
echo "$N"
"""
STUB_SQUEUE = r"""#!/bin/bash
# stub squeue -h -j JID -o %T : prints the state while the job file exists
S="$SIM_SLURM"; JID=""; prev=""
for a in "$@"; do [ "$prev" = "-j" ] && JID="$a"; prev="$a"; done
[ -n "$JID" ] && [ -f "$S/jobs/$JID" ] && cat "$S/jobs/$JID"
exit 0
"""
STUB_SACCT = "#!/bin/bash\necho COMPLETED\n"

ALLOWED = """smoke 00:15:00 1
L2    00:30:00 1
T1    01:00:00 1
T2    01:00:00 1
T3    01:00:00 1
T4    01:00:00 1
T5    01:00:00 1
TWO   01:00:00 2
"""


class Sim:
    def __init__(self, tmp, max_concurrent=None, max_per_day=24):
        self.tmp = str(tmp)
        self.remote = os.path.join(self.tmp, "remote.git")
        self.agent = os.path.join(self.tmp, "agent")
        self.repo = os.path.join(self.tmp, "perl")
        self.home = os.path.join(self.tmp, "home")
        self.ci = os.path.join(self.home, "skqd-ci")
        self.runs = os.path.join(self.tmp, "runs")
        self.slurm = os.path.join(self.tmp, "slurm")
        self.bin = os.path.join(self.tmp, "bin")
        for d in (self.home, self.ci, self.runs, self.slurm, self.bin):
            os.makedirs(d, exist_ok=True)
        for name, body in (("sbatch", STUB_SBATCH), ("squeue", STUB_SQUEUE), ("sacct", STUB_SACCT)):
            p = os.path.join(self.bin, name)
            with open(p, "w") as fh:
                fh.write(body)
            os.chmod(p, 0o755)
        self.env = dict(os.environ)
        self.env.update({"HOME": self.home, "PATH": self.bin + os.pathsep + os.environ["PATH"],
                         "SIM_SLURM": self.slurm, "GIT_CONFIG_NOSYSTEM": "1",
                         "GIT_AUTHOR_NAME": "sim", "GIT_AUTHOR_EMAIL": "sim@x",
                         "GIT_COMMITTER_NAME": "sim", "GIT_COMMITTER_EMAIL": "sim@x"})
        for k in ("CI_GATE", "SLURM_JOB_ID", "GIT_DIR", "GIT_WORK_TREE"):
            self.env.pop(k, None)
        self.git(self.tmp, "init", "-q", "--bare", "-b", "master", self.remote)
        self.git(self.tmp, "clone", "-q", self.remote, self.agent)
        self.git(self.agent, "checkout", "-q", "-b", "master")
        self.write(self.agent, "jobs/gate.sbatch", "#!/bin/bash\necho gate\n")
        self.write(self.agent, "jobs/smoke.sbatch", "#!/bin/bash\necho smoke\n")
        self.write(self.agent, "validation/old.json", '{"v": 1}\n')
        self.write(self.agent, "reports/old.md", "old\n")
        self.write(self.agent, "marker.txt", "A\n")
        self.git(self.agent, "add", "-A")
        self.git(self.agent, "commit", "-qm", "seed")
        self.git(self.agent, "push", "-q", "origin", "master")
        self.git(self.tmp, "clone", "-q", self.remote, self.repo)
        conf = (f'REPO="{self.repo}"\nRUNS="{self.runs}"\nACCOUNT_GPU="m0000_g"\nBRANCH="master"\n'
                f"MAX_JOBS_PER_DAY={max_per_day}\n")
        if max_concurrent is not None:
            conf += f"MAX_CONCURRENT={max_concurrent}\n"
        self.write(self.ci, "ci.conf", conf)
        self.write(self.ci, "allowed_jobs", ALLOWED)
        self.nreq = 0

    # -- helpers ---------------------------------------------------------------------------
    def git(self, cwd, *args, check=True):
        r = subprocess.run(["git", *args], cwd=cwd, env=self.env, capture_output=True, text=True)
        if check and r.returncode:
            raise AssertionError(f"git {args} failed: {r.stderr}")
        return r.stdout.strip()

    @staticmethod
    def write(base, rel, text):
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)

    def agent_commit(self, files, msg):
        self.git(self.agent, "pull", "-q", "--rebase", "origin", "master")
        for rel, text in files.items():
            self.write(self.agent, rel, text)
        self.git(self.agent, "add", "-A")
        self.git(self.agent, "commit", "-qm", msg)
        self.git(self.agent, "push", "-q", "origin", "master")
        return self.git(self.agent, "rev-parse", "HEAD")

    def request(self, *tokens):
        """What scripts/ci_request.sh writes: one file per token, ONE commit."""
        files = {}
        for t in tokens:
            self.nreq += 1
            files[f"ci/requests/{self.nreq:03d}-{t}.txt"] = f"{t}\n# requested by the sim nonce {self.nreq}\n"
        return self.agent_commit(files, "ci: request " + " ".join(tokens)), list(files)

    def legacy_request(self, token):
        self.nreq += 1
        return self.agent_commit({"ci/request.txt": f"{token}\n# legacy nonce {self.nreq}\n"},
                                 f"ci: request {token}")

    def poll(self, expect_rc=0):
        r = subprocess.run(["bash", POLLER], cwd=self.repo, env=self.env, capture_output=True, text=True)
        assert r.returncode == expect_rc, f"poller rc {r.returncode}\n{r.stdout}\n{r.stderr}"
        return r.stdout + r.stderr

    def submissions(self):
        p = os.path.join(self.slurm, "sbatch.log")
        if not os.path.exists(p):
            return []
        out = []
        for line in open(p):
            jid, d, export, jobfile = line.rstrip("\n").split("\t")
            ex = dict(kv.split("=", 1) for kv in export.split(",") if "=" in kv)
            out.append({"jid": jid, "snap": d, "export": ex, "jobfile": jobfile})
        return out

    def running(self):
        d = os.path.join(self.ci, "running")
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def finish(self, jid, outputs=None):
        """The job writes its outputs into its snapshot and leaves the queue."""
        sub = next(s for s in self.submissions() if s["jid"] == str(jid))
        for rel, text in (outputs or {}).items():
            self.write(sub["snap"], rel, text)
        os.remove(os.path.join(self.slurm, "jobs", str(jid)))

    def status(self, token):
        self.git(self.agent, "pull", "-q", "--rebase", "origin", "master")
        p = os.path.join(self.agent, "ci", "status", f"{token}.json")
        return json.load(open(p)) if os.path.exists(p) else None

    def consumed(self):
        p = os.path.join(self.ci, "consumed")
        return open(p).read().split() if os.path.exists(p) else []


def tokens_of(subs):
    return [s["export"]["CI_GATE"] for s in subs]


# ---------------------------------------------------------------------------------------------
def test_the_poller_under_test_is_the_concurrent_one():
    txt = open(POLLER).read()
    assert "MAX_CONCURRENT" in txt and "ci/requests" in txt and ".ci_manifest" in txt


def test_no_request_is_silent_and_exit_0(tmp_path):
    s = Sim(tmp_path, max_concurrent=4)
    out = s.poll()
    assert s.submissions() == [] and "submitted" not in out


def test_unknown_token_is_refused_and_never_submitted(tmp_path):
    s = Sim(tmp_path, max_concurrent=4)
    sha, files = s.request("NOPE")
    s.poll()
    assert s.submissions() == []
    st = s.status("NOPE")
    assert st["state"] == "refused" and st["request"] == f"{files[0]}@{sha}"
    assert f"{files[0]}@{sha}" in s.consumed()
    s.poll()
    assert s.submissions() == [], "a refused request is consumed, not retried"


def test_five_requests_two_at_a_time_and_each_exactly_once(tmp_path):
    s = Sim(tmp_path, max_concurrent=2)
    sha, files = s.request("T1", "T2", "T3", "T4", "T5")
    s.poll()
    subs = s.submissions()
    assert tokens_of(subs) == ["T1", "T2"], "file-name order, MAX_CONCURRENT=2"
    s.poll()
    assert len(s.submissions()) == 2, "nothing new while both run"
    s.finish(subs[0]["jid"], {"validation/T1.json": '{"status": "PASS"}\n'})
    s.finish(subs[1]["jid"], {"validation/T2.json": '{"status": "PASS"}\n'})
    s.poll()
    subs = s.submissions()
    assert tokens_of(subs) == ["T1", "T2", "T3", "T4"], "the next 2 after the harvest"
    assert s.status("T1")["state"] == "done" and s.status("T3")["state"] == "submitted"
    assert os.path.exists(os.path.join(s.agent, "validation", "T1.json")), "harvest pushed to the remote"
    for j in subs[2:]:
        s.finish(j["jid"])
    s.poll()
    s.finish(s.submissions()[-1]["jid"])
    s.poll()
    s.poll()
    subs = s.submissions()
    assert tokens_of(subs) == ["T1", "T2", "T3", "T4", "T5"], "every request exactly once"
    assert s.running() == []
    ids = [f"{f}@{sha}" for f in files]
    assert sorted(set(s.consumed()) & set(ids)) == sorted(ids)
    # one commit per harvested job, all pushed to the remote
    s.git(s.agent, "pull", "-q", "--rebase", "origin", "master")
    log = s.git(s.agent, "log", "--format=%s")
    assert sum(1 for line in log.splitlines() if line.startswith("ci: results job")) == 5


def test_daily_cap_stops_submission_and_requests_wait(tmp_path):
    s = Sim(tmp_path, max_concurrent=5, max_per_day=3)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    with open(os.path.join(s.ci, "submitted.log"), "w") as fh:
        fh.write(f"{yesterday} x 1 OLD a b\n" * 7)        # yesterday's jobs do not count
        fh.write(f"{today} x 2 OLD a b\n")                 # one already today
    s.request("T1", "T2", "T3", "T4")
    out = s.poll()
    assert tokens_of(s.submissions()) == ["T1", "T2"], "3 per day, 1 already used"
    assert "daily cap reached" in out
    pend = [i for i in s.consumed() if "T3" in i or "T4" in i]
    assert pend == [], "requests beyond the cap are not consumed: they wait"
    s.poll()
    assert len(s.submissions()) == 2


def test_snapshot_is_the_requested_commit_not_a_later_one(tmp_path):
    s = Sim(tmp_path, max_concurrent=2)
    sha, _ = s.request("T1")
    s.agent_commit({"marker.txt": "B\n"}, "a later commit")
    s.poll()
    (sub,) = s.submissions()
    assert sub["export"]["CI_CODE_SHA"] == sha and sub["export"]["CI_REQUEST_SHA"] == sha
    assert open(os.path.join(sub["snap"], "marker.txt")).read() == "A\n"
    assert sub["jobfile"] == os.path.join(sub["snap"], "jobs", "gate.sbatch")


def test_never_twice_and_re_request_is_a_new_commit(tmp_path):
    s = Sim(tmp_path, max_concurrent=3)
    _sha, files = s.request("T1")
    s.poll()
    s.finish(s.submissions()[0]["jid"])
    for _ in range(3):
        s.poll()
    s.agent_commit({"marker.txt": "C\n"}, "unrelated commit")
    s.poll()
    assert tokens_of(s.submissions()) == ["T1"], "the same identity never runs twice"
    s.agent_commit({files[0]: "T1\n# re-requested nonce 2\n"}, "re-request")
    s.poll()
    assert tokens_of(s.submissions()) == ["T1", "T1"], "a new commit touching the file is a new request"


def test_harvest_copies_only_what_the_job_wrote(tmp_path):
    s = Sim(tmp_path, max_concurrent=2)
    s.request("T1")
    s.poll()
    (sub,) = s.submissions()
    # after the snapshot, the repo moves on: a newer validation/old.json lands on master
    s.agent_commit({"validation/old.json": '{"v": 2}\n'}, "newer old.json")
    s.finish(sub["jid"], {"validation/T1.json": '{"status": "PASS"}\n',
                          "reports/ci-%s.out" % sub["jid"]: "log\n"})
    s.poll()
    s.git(s.agent, "pull", "-q", "--rebase", "origin", "master")
    assert json.load(open(os.path.join(s.agent, "validation", "old.json")))["v"] == 2, \
        "a file the job did not write is never reverted to the snapshot's copy"
    assert os.path.exists(os.path.join(s.agent, "validation", "T1.json"))
    assert os.path.exists(os.path.join(s.agent, "reports", f"ci-{sub['jid']}.out"))


def test_legacy_request_txt_with_max_concurrent_absent(tmp_path):
    s = Sim(tmp_path, max_concurrent=None)
    s.legacy_request("L2")
    s.poll()
    assert tokens_of(s.submissions()) == ["L2"]
    st = json.load(open(os.path.join(s.repo, "ci", "status.json")))
    assert st["state"] == "submitted" and st["token"] == "L2", "the legacy status file is kept"
    s.request("T1")
    s.poll()
    assert tokens_of(s.submissions()) == ["L2"], "MAX_CONCURRENT absent = one job at a time"
    s.finish(s.submissions()[0]["jid"])
    s.poll()
    assert tokens_of(s.submissions()) == ["L2", "T1"]


def test_migration_of_the_one_job_poller_state(tmp_path):
    s = Sim(tmp_path, max_concurrent=None)
    sha = s.legacy_request("L2")
    # the one-job poller had consumed this request and was running its job 77
    with open(os.path.join(s.ci, "last_request"), "w") as fh:
        fh.write(sha + "\n")
    snap = os.path.join(s.runs, "oldsnap")
    os.makedirs(os.path.join(snap, "validation"))
    with open(os.path.join(snap, "validation", "L2.json"), "w") as fh:
        fh.write('{"status": "PASS"}\n')
    with open(os.path.join(s.ci, "current"), "w") as fh:
        fh.write(f"77 L2 {sha} {sha} {snap}\n")
    os.makedirs(os.path.join(s.slurm, "jobs"), exist_ok=True)
    with open(os.path.join(s.slurm, "jobs", "77"), "w") as fh:
        fh.write("RUNNING\n")
    out = s.poll()
    assert "migrated running job 77" in out and s.running() == ["77"]
    assert s.submissions() == [], "the consumed legacy request is not run again"
    os.remove(os.path.join(s.slurm, "jobs", "77"))
    s.poll()
    assert s.running() == [] and s.submissions() == []
    s.git(s.agent, "pull", "-q", "--rebase", "origin", "master")
    assert os.path.exists(os.path.join(s.agent, "validation", "L2.json")), "old snapshot harvested as before"


def test_rebase_conflict_aborts_before_any_submission(tmp_path):
    s = Sim(tmp_path, max_concurrent=2)
    s.request("T1")
    s.poll()
    (sub,) = s.submissions()
    s.finish(sub["jid"])
    s.request("T2")
    # an agent breaks the rule and edits a CI-owned file: the harvest commit cannot rebase
    s.agent_commit({"ci/status.json": '{"state": "hand-edited"}\n'}, "bad edit")
    out = s.poll(expect_rc=1)
    assert "rebase conflict" in out
    assert tokens_of(s.submissions()) == ["T1"], "no submission after an aborted sync"


def test_failed_sbatch_is_recorded_and_not_retried(tmp_path):
    s = Sim(tmp_path, max_concurrent=2)
    open(os.path.join(s.slurm, "fail_next"), "w").close()
    s.request("T1", "T2")
    s.poll()
    assert tokens_of(s.submissions()) == ["T2"]
    assert s.status("T1")["state"] == "error"
    s.poll()
    assert tokens_of(s.submissions()) == ["T2"]


def test_two_gpu_line_and_resources_come_from_the_allowlist(tmp_path):
    s = Sim(tmp_path, max_concurrent=2)
    s.request("TWO", "smoke")
    s.poll()
    log = open(os.path.join(s.slurm, "sbatch.log")).read()
    subs = s.submissions()
    assert tokens_of(subs) == ["TWO", "smoke"]
    assert subs[1]["jobfile"].endswith("jobs/smoke.sbatch")
    assert len(log.splitlines()) == 2


def test_installer_keeps_an_existing_ci_conf(tmp_path):
    """bash ci/install_skqd_ci.sh never overwrites ~/skqd-ci/ci.conf (prompts/33 7b)."""
    home = tmp_path / "h"
    (home / "skqd-ci").mkdir(parents=True)
    conf = home / "skqd-ci" / "ci.conf"
    conf.write_text("MAX_JOBS_PER_DAY=24\nMAX_CONCURRENT=4\n")
    repo = tmp_path / "r"
    shutil.copytree(os.path.join(ROOT, "ci"), repo / "ci")
    env = dict(os.environ, HOME=str(home), SCRATCH=str(tmp_path / "scratch"), GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=str(tmp_path / "gitconfig"))
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
    r = subprocess.run(["bash", "ci/install_skqd_ci.sh"], cwd=repo, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert conf.read_text() == "MAX_JOBS_PER_DAY=24\nMAX_CONCURRENT=4\n"
    assert "ci.conf has no REPO" in r.stdout and "kept the existing" in r.stdout
    assert (home / "skqd-ci" / "running").is_dir()
    r2 = subprocess.run(["bash", "ci/install_skqd_ci.sh"], cwd=repo, capture_output=True, text=True,
                        env=dict(env, POLLER="ci/poll_concurrent.sh"))
    assert r2.returncode == 0
    assert open(home / "skqd-ci" / "poll.sh").read() == open(os.path.join(ROOT, "ci", "poll_concurrent.sh")).read()


def test_request_and_check_scripts_parse():
    for f in ("scripts/ci_request.sh", "scripts/ci_check.sh", "ci/install_skqd_ci.sh", POLLER):
        r = subprocess.run(["bash", "-n", os.path.join(ROOT, f)], capture_output=True, text=True)
        assert r.returncode == 0, (f, r.stderr)
    txt = open(os.path.join(ROOT, "scripts", "ci_request.sh")).read()
    assert "ci/requests/%03d-%s.txt" in txt and "--legacy" in txt
    assert textwrap.dedent("git commit -qm \"ci: request $*\"") in txt, "one commit for all tokens"

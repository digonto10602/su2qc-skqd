#!/bin/bash
# Report the CI state of every request (prompts/33 section 7c, item 7).
#
#   scripts/ci_check.sh            # one line per request file: pending / submitted / done / refused / error
#   scripts/ci_check.sh C2_CAL     # the latest request of one token in full (status, ci_gate JSON, log tail)
#
# Exit 0 = everything listed is done, 2 = something is still pending or running, 3 = refused/error
# (and nothing pending).  States come from ci/status/<TOKEN>.json (written by the concurrent poller)
# and, for the legacy ci/request.txt, also from ci/status.json (the one-job poller).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git pull -q --rebase --autostash origin master
python3 - "$@" <<'PY'
import json, os, subprocess, sys, glob

def sha_of(path):
    r = subprocess.run(["git", "log", "-1", "--format=%H", "--", path], capture_output=True, text=True)
    return r.stdout.strip()

def token_of(path):
    for line in open(path):
        if not line.startswith("#"):
            return "".join(ch for ch in line if ch.isalnum() or ch == "_")
    return ""

def load(p):
    return json.load(open(p)) if os.path.exists(p) else {}

reqs = sorted(glob.glob("ci/requests/*.txt"))
if os.path.exists("ci/request.txt"):
    reqs.append("ci/request.txt")
rows = []
for path in reqs:
    sha = sha_of(path)
    if not sha:
        continue
    tok = token_of(path)
    ident = f"{path}@{sha}"
    st = load(f"ci/status/{tok or '_invalid'}.json")
    state = None
    if st.get("request") == ident:
        state = st.get("state")
    elif path == "ci/request.txt":
        legacy = load("ci/status.json")
        if legacy.get("request_sha") == sha and not legacy.get("request", "").startswith("ci/requests/"):
            state, st = legacy.get("state"), legacy
    rows.append({"path": path, "sha": sha, "token": tok, "state": state or "pending", "status": st if state else {}})

want = sys.argv[1] if len(sys.argv) > 1 else None
if want:
    mine = [r for r in rows if r["token"] == want]
    if not mine:
        print(f"no request for {want}"); sys.exit(2)
    r = mine[-1]
    print(json.dumps(r, indent=1))
    if r["state"] in ("refused", "error"): sys.exit(3)
    if r["state"] != "done": print("PENDING:", r["path"], r["state"]); sys.exit(2)
    res = "validation/ci_smoke.json" if want == "smoke" else f"validation/ci_gate_{want}.json"
    if os.path.exists(res):
        print(open(res).read())
    log = f"reports/ci-{r['status'].get('jobid')}.out"
    if os.path.exists(log):
        print("---- tail", log); print("".join(open(log).readlines()[-40:]))
    sys.exit(0)

for r in rows:
    j = r["status"].get("jobid") or ""
    print(f"{r['state']:<9} {r['token']:<14} job {j:<10} {r['path']}@{r['sha'][:12]}  {r['status'].get('note', '')}")
states = {r["state"] for r in rows}
if states & {"pending", "submitted"}: sys.exit(2)
if states & {"refused", "error"}: sys.exit(3)
sys.exit(0)
PY

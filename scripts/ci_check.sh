#!/bin/bash
# Report the CI state for the latest request.  Exit 0 = done, 2 = still pending, 3 = refused.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git pull -q --rebase --autostash origin master
REQ=$(git log -1 --format=%H -- ci/request.txt)
python3 - "$REQ" <<'PY'
import json, sys, glob, os
req = sys.argv[1]
st = json.load(open("ci/status.json")) if os.path.exists("ci/status.json") else {}
if st.get("request_sha") != req:
    print(f"PENDING: request {req[:12]} not picked up yet (poller runs at :07 UTC each hour)"); sys.exit(2)
print(json.dumps(st, indent=1))
if st["state"] == "refused": sys.exit(3)
if st["state"] != "done": print("PENDING: job", st["jobid"], "is", st["state"]); sys.exit(2)
tok = st["token"]
res = "validation/ci_smoke.json" if tok == "smoke" else f"validation/ci_gate_{tok}.json"
if os.path.exists(res):
    print(open(res).read())
log = f"reports/ci-{st['jobid']}.out"
if os.path.exists(log):
    print("---- tail", log); print("".join(open(log).readlines()[-40:]))
sys.exit(0)
PY

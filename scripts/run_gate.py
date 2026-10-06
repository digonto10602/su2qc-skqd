#!/usr/bin/env python3
"""
Gate runner used by the agents (and by hand):

    python scripts/run_gate.py E1            # run scripts/gate_E1.py, print status
    python scripts/run_gate.py S1 --quick    # extra args are passed through
    python scripts/run_gate.py L2 --push     # laptop gate; on PASS commit + push

A gate G is defined by scripts/gate_G.py (cloud-verifiable gates) or
scripts/laptop_G_*.py (laptop gates), else by its entry in scripts/gate_tokens.json
(script + args; the prompts/33 campaign tokens).  Every gate script writes
validation/G.json with "status": "PASS"|"FAIL" and a report in reports/.
On PASS with --push the runner commits reports/, validation/, data/ and pushes
to the current branch's upstream (creating it on origin if needed).  On FAIL the
runner writes validation/BLOCKED.md with the failing criteria so that the
planner (Fable 5.1, max effort) can be invoked with prompts/ESCALATION_TEMPLATE.md.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


TOKENS_FILE = os.path.join(ROOT, "scripts", "gate_tokens.json")


def find_script(gate: str) -> str:
    cands = [os.path.join(ROOT, "scripts", f"gate_{gate}.py")] + glob.glob(os.path.join(ROOT, "scripts", f"laptop_{gate}_*.py"))
    for c in cands:
        if os.path.exists(c):
            return c
    raise SystemExit(f"no script for gate {gate}: looked for {cands} and {TOKENS_FILE}")


def resolve(gate: str):
    """(script, args) for token `gate`: scripts/gate_<G>.py or scripts/laptop_<G>_*.py with no
    args, else the entry of scripts/gate_tokens.json (prompts/33 A1: the campaign tokens run one
    driver with `--token <G>`).  Everything after resolution is unchanged."""
    try:
        return find_script(gate), []
    except SystemExit:
        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE) as fh:
                table = json.load(fh)
            ent = table.get(gate)
            if gate and not gate.startswith("_") and isinstance(ent, dict):
                return os.path.join(ROOT, ent["script"]), [str(a) for a in ent.get("args", [])]
        raise


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gate")
    ap.add_argument("--push", action="store_true", help="commit and push on PASS")
    ap.add_argument("--timeout", type=int, default=3600, help="seconds (30-minute laptop rule = 1800)")
    ap.add_argument("--resolve", action="store_true",
                    help="print the command the token resolves to and exit (nothing is run)")
    args, extra = ap.parse_known_args()
    script, token_args = resolve(args.gate)
    if args.resolve:
        print(" ".join([os.path.relpath(script, ROOT), *token_args, *extra]))
        return 0
    t0 = time.time()
    try:
        proc = subprocess.run([sys.executable, script, *token_args, *extra], cwd=ROOT, timeout=args.timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        code = 124
        print(f"gate {args.gate} exceeded {args.timeout} s: re-parametrize (fewer shots / --quick) and record it in the report")
    dt = time.time() - t0
    jpath = os.path.join(ROOT, "validation", f"{args.gate}.json")
    status = "UNKNOWN"
    if os.path.exists(jpath):
        with open(jpath) as fh:
            js = json.load(fh)
        status = js.get("status", "UNKNOWN")
        failing = [c for c in js.get("criteria", []) if not c.get("passed")]
    else:
        failing = []
    print(f"gate {args.gate}: status {status}, exit code {code}, {dt:.0f} s")
    if status == "PASS" and code == 0:
        if args.push:
            git("add", "-A")
            msg = f"Gate {args.gate} PASS ({dt:.0f} s)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
            r = git("commit", "-m", msg, check=False)
            print(r.stdout.strip() or r.stderr.strip())
            branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            r = git("push", "-u", "origin", branch, check=False)
            print(r.stdout.strip() or r.stderr.strip())
        return 0
    with open(os.path.join(ROOT, "validation", "BLOCKED.md"), "w") as fh:
        fh.write(f"# Gate {args.gate} did not pass ({time.strftime('%Y-%m-%d %H:%M')})\n\n")
        fh.write(f"exit code {code}, runtime {dt:.0f} s, status {status}\n\n")
        for c in failing:
            fh.write(f"- {c['name']}: value {c['value']}, criterion {c['threshold']}\n")
        fh.write("\nNext step: the planner writes prompts/<NN>_<gate>_fix_<date>.md using prompts/ESCALATION_TEMPLATE.md.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

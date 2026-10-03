#!/usr/bin/env python3
"""
prompts/26 A1 (with the coordinator's ruling of 2026-10-02): the Quantinuum stack lives in an
ISOLATED venv, never in the pinned `coding` env -> data/quantinuum/stack_check_20261002.json.

Records
  * `pip install --dry-run pytket pytket-quantinuum pytket-qiskit qnexus` in `coding` (nothing is
    installed there): the packages it would add and what it says about the five pins;
  * the five pins of `coding` (python -c "import ...; __version__"), now and as recorded before the
    venv was created (--pins-before), and the `pip freeze` of `coding` before (--coding-freeze-before)
    and now: they must be identical;
  * the venv (path, python, how it was made) and its `pip freeze` diff against `coding` (what the venv
    adds or shadows; nothing is written into `coding`).

Usage: python scripts/quantinuum_stack_check.py --coding-freeze-before F --pins-before P
         [--venv-freeze-before F2] [--no-dry-run]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODING_PY = "/home/digimonk/anaconda3/envs/coding/bin/python"
VENV = os.path.join(os.path.expanduser("~"), ".local", "share", "su2qc-quantinuum", "venv")
VENV_PY = os.path.join(VENV, "bin", "python")
PACKAGES = ["pytket", "pytket-quantinuum", "pytket-qiskit", "qnexus"]
PINS_EXPECTED = {"python": "3.12.14", "qiskit": "2.5.2", "qiskit-aer": "0.17.2",
                 "qiskit-ibm-runtime": "0.49.0", "numpy": "2.5.2", "scipy": "1.18.0"}
PINS_CODE = ("import sys,json,qiskit,qiskit_aer,qiskit_ibm_runtime,numpy,scipy;"
             "print(json.dumps({'python':sys.version.split()[0],'qiskit':qiskit.__version__,"
             "'qiskit-aer':qiskit_aer.__version__,'qiskit-ibm-runtime':qiskit_ibm_runtime.__version__,"
             "'numpy':numpy.__version__,'scipy':scipy.__version__}))")


def run(cmd, timeout=600):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def pins(py):
    rc, out, err = run([py, "-c", PINS_CODE])
    if rc != 0:
        raise SystemExit(f"{py}: cannot import the pinned stack: {err[-500:]}")
    return json.loads(out.strip().splitlines()[-1])


def freeze(py):
    rc, out, err = run([py, "-m", "pip", "freeze"])
    if rc != 0:
        raise SystemExit(err)
    return sorted(line for line in out.splitlines() if line.strip())


def parse_freeze(lines):
    d = {}
    for line in lines:
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:==|@)\s*(.+)$", line)
        if m:
            d[m.group(1).lower().replace("_", "-")] = m.group(2).strip()
    return d


def dry_run():
    rc, out, err = run([CODING_PY, "-m", "pip", "install", "--dry-run"] + PACKAGES, timeout=900)
    would = re.findall(r"^Would install (.+)$", out, re.M)
    pinned = [line for line in out.splitlines() if line.startswith("Requirement already satisfied")
              and re.search(r"\b(qiskit|qiskit-aer|qiskit-ibm-runtime|numpy|scipy)[ <>=!]", line.split("in /")[0])]
    return {"command": f"{CODING_PY} -m pip install --dry-run " + " ".join(PACKAGES),
            "returncode": rc, "would_install": (would[0].split() if would else []),
            "pinned_lines": pinned, "stderr_tail": err[-1000:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coding-freeze-before", required=True)
    ap.add_argument("--pins-before", required=True)
    ap.add_argument("--venv-freeze-before", default=None)
    ap.add_argument("--no-dry-run", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "quantinuum", "stack_check_20261002.json"))
    args = ap.parse_args()
    fb = sorted(line for line in open(args.coding_freeze_before).read().splitlines() if line.strip())
    pins_before = json.load(open(args.pins_before))
    pins_now = pins(CODING_PY)
    fn = freeze(CODING_PY)
    vf = freeze(VENV_PY)
    cpar, vpar = parse_freeze(fn), parse_freeze(vf)
    venv_added = {k: v for k, v in vpar.items() if k not in cpar}
    venv_shadowed = {k: {"coding": cpar[k], "venv": v} for k, v in vpar.items() if k in cpar and cpar[k] != v}
    venv_pins = pins(VENV_PY)
    dr = None if args.no_dry_run else dry_run()
    would = set((dr or {}).get("would_install", []))
    pin_names = {"qiskit", "qiskit-aer", "qiskit-ibm-runtime", "numpy", "scipy"}
    rec = {
        "produced_by": "scripts/quantinuum_stack_check.py", "prompt": "prompts/26 A1",
        "ruling": ("coordinator 2026-10-02: nothing is installed into `coding`; pytket, pytket-quantinuum, "
                   "pytket-qiskit and qnexus go into an isolated venv created with --system-site-packages "
                   "from the coding env's python"),
        "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "coding_python": CODING_PY,
        "pins_expected": PINS_EXPECTED, "pins_before": pins_before, "pins_now": pins_now,
        "pins_unchanged": pins_before == pins_now == PINS_EXPECTED,
        "coding_freeze_before_n": len(fb), "coding_freeze_now_n": len(fn),
        "coding_freeze_identical": fb == fn,
        "coding_freeze_diff": {"removed": sorted(set(fb) - set(fn)), "added": sorted(set(fn) - set(fb))},
        "dry_run_in_coding": dr,
        "dry_run_touches_pins": (None if dr is None else
                                 any(w.rsplit("-", 1)[0].lower() in pin_names for w in would)),
        "venv": {"path": VENV, "python": VENV_PY,
                 "created_with": f"{CODING_PY} -m venv --system-site-packages {VENV}",
                 "install_command": (f"{VENV_PY} -m pip install pytket==2.18.4 pytket-quantinuum==0.59.3 "
                                     "pytket-qiskit==0.78.0 qnexus==0.51.0"),
                 "versions": {k: vpar.get(k) for k in ("pytket", "pytket-quantinuum", "pytket-qiskit",
                                                       "qnexus", "quantinuum-schemas", "pytket-qir", "pyqir",
                                                       "hugr", "symengine", "pandas")},
                 "pins_seen_from_venv": venv_pins,
                 "pip_freeze_diff_vs_coding": {"added_in_venv": venv_added, "shadowed_in_venv": venv_shadowed},
                 "venv_freeze_before_install": (sorted(open(args.venv_freeze_before).read().split())
                                                if args.venv_freeze_before else None)},
        "not_installed": "guppylang / selene-sim (prompts/26 A9 not reached)",
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rec, fh, indent=1)
    print(f"pins unchanged: {rec['pins_unchanged']}; coding freeze identical: {rec['coding_freeze_identical']}; "
          f"dry run touches pins: {rec['dry_run_touches_pins']}; venv adds {sorted(venv_added)}; "
          f"shadows {sorted(venv_shadowed)}")
    return 0 if (rec["pins_unchanged"] and rec["coding_freeze_identical"]) else 1


if __name__ == "__main__":
    sys.exit(main())

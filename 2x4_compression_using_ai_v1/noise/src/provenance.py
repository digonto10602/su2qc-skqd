"""Provenance block for every result JSON (commit, machine, engine versions, spec-file hashes)."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time

import numpy as np

from circuits import ROOT, NOISE


def git_commit() -> str:
    try:
        h = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", ROOT, "diff", "--quiet", "--", os.path.relpath(NOISE, ROOT)])
        return h + ("+dirty(noise/)" if dirty else "")
    except Exception as exc:  # recorded, not swallowed
        return f"unavailable: {exc}"


def machine() -> dict:
    import scipy
    d = {"platform": platform.platform(), "node": platform.node(), "python": platform.python_version(),
         "executable": sys.executable, "numpy": np.__version__, "scipy": scipy.__version__,
         "cpu_count": os.cpu_count()}
    try:
        import qiskit, qiskit_aer
        d["qiskit"] = qiskit.__version__
        d["qiskit_aer"] = qiskit_aer.__version__
    except Exception as exc:
        d["qiskit_import_error"] = str(exc)
    return d


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def provenance(**extra) -> dict:
    d = {"git_commit": git_commit(), "machine": machine(),
         "created_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
         "command": " ".join([os.path.basename(sys.executable)] + sys.argv)}
    d.update(extra)
    return d


def _default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


def dump(obj, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=1, default=_default)
    os.replace(tmp, path)

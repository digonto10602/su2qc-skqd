"""Paths, provenance and JSON output for the study (every number written carries its provenance)."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time

import numpy as np

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # .../2x4_compression_using_ai_v1/src
STUDY = os.path.dirname(SRC)                                            # .../2x4_compression_using_ai_v1
ROOT = os.path.dirname(STUDY)                                           # the package repository
DATA = os.path.join(STUDY, "data")
CACHE = os.path.join(DATA, "cache")                                     # gitignored, regenerable

if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))


def git_commit() -> str:
    try:
        h = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", ROOT, "diff", "--quiet", "--", "2x4_compression_using_ai_v1"])
        return h + ("+dirty(study folder)" if dirty else "")
    except Exception as exc:                       # recorded, not swallowed silently
        return f"unavailable: {exc}"


def machine() -> dict:
    import scipy
    return {"platform": platform.platform(), "python": platform.python_version(),
            "executable": sys.executable, "numpy": np.__version__, "scipy": scipy.__version__,
            "cpu_count": os.cpu_count(), "node": platform.node()}


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (complex, np.complexfloating)):
        return [float(np.real(o)), float(np.imag(o))]
    raise TypeError(f"not JSON serialisable: {type(o)}")


def write_json(path: str, payload: dict, produced_by: str, parameters: dict, seed=None,
               t_start: float | None = None) -> str:
    """Write `payload` with the provenance block the study's rules require."""
    out = {"produced_by": produced_by, "git_commit": git_commit(), "machine": machine(),
           "parameters": parameters, "seed": seed,
           "written_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    if t_start is not None:
        out["wall_s"] = time.time() - t_start
    out.update(payload)
    path = path if os.path.isabs(path) else os.path.join(STUDY, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=_default)
    return path


def archive_path(label: str) -> str:
    """data/archive_<label>.json for 2x4; data/c2x3/archive_<label>.json for 2x3 labels (prefix 'L3_'), so that the
    2x3 outputs stay in their own folder (C3, notes/010)."""
    if label.startswith("L3_"):
        return os.path.join(DATA, "c2x3", f"archive_{label}.json")
    if label.startswith("L2_"):                     # 2x2 families (notes/011): their own folder data/c2x2/
        return os.path.join(DATA, "c2x2", f"archive_{label}.json")
    return os.path.join(DATA, f"archive_{label}.json")

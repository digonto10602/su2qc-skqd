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
CACHE = os.path.join(DATA, "cache")                                     # gitignored, regenerable (shared by all lattices)

# One folder per lattice (owner 2026-10-28, notes/012).  The code, Lean, tests, notes and study-wide reports live
# only in this folder (2x4_compression_using_ai_v1/); the 2x3 and 2x2 folders hold that lattice's data only, with
# the same internal layout (data/..., noise/data/results/..., hardware/...).
STUDY_DIRS = {"2x4": STUDY,
              "2x3": os.path.join(ROOT, "2x3_compression_using_ai_v1"),
              "2x2": os.path.join(ROOT, "2x2_compression_using_ai_v1")}


def _lattice_key(lattice) -> str:
    """'2x3', 3 or '3' -> '2x3'."""
    s = str(lattice)
    return s if s.startswith("2x") else f"2x{int(s)}"


def lattice_study(lattice) -> str:
    """The study folder that holds this lattice's data (2x4 -> this folder)."""
    return STUDY_DIRS[_lattice_key(lattice)]


def lattice_data(lattice) -> str:
    """Folder for a lattice's loop/verification outputs: data/ for 2x4, <2x3 folder>/data/c2x3/ for 2x3,
    <2x2 folder>/data/c2x2/ for 2x2."""
    key = _lattice_key(lattice)
    return DATA if key == "2x4" else os.path.join(STUDY_DIRS[key], "data", "c" + key)

if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))


def git_commit() -> str:
    try:
        h = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
        dirty = subprocess.call(["git", "-C", ROOT, "diff", "--quiet", "--", "2x4_compression_using_ai_v1",
                                 "2x3_compression_using_ai_v1", "2x2_compression_using_ai_v1"])
        return h + ("+dirty(study folders)" if dirty else "")
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
    """data/archive_<label>.json for 2x4; 2x3_compression_using_ai_v1/data/c2x3/archive_<label>.json for 2x3 labels
    (prefix 'L3_', C3, notes/010) and 2x2_compression_using_ai_v1/data/c2x2/archive_<label>.json for 2x2 labels
    (prefix 'L2_', notes/011); one folder per lattice since notes/012."""
    if label.startswith("L3_"):
        return os.path.join(lattice_data("2x3"), f"archive_{label}.json")
    if label.startswith("L2_"):
        return os.path.join(lattice_data("2x2"), f"archive_{label}.json")
    return os.path.join(DATA, f"archive_{label}.json")

"""Loader for the C5 noise-study results (noise/data/results/<lattice>/<family>/<device>/<test>.json).

    import sys; sys.path.insert(0, "2x4_compression_using_ai_v1/noise/src")
    import results
    results.list_available()                      # [(lattice, family, device, test), ...]
    d = results.load("2x3", "frozen", "quantinuum_h2_2", "noise_behaviour")   # the dict
    df = results.table("noise_behaviour", "2x3")  # pandas DataFrame, one row per (family, device, circuit)
    df = results.table("accuracy", "2x4")         # device column is "noiseless"
    results.summary("noise_behaviour", "2x3")     # one row per (family, device): the JSON "summary" blocks

Tests: accuracy (device "noiseless"), analytic_f, noise_behaviour, skqd_energy.
Every JSON carries "provenance" (git commit, machine, command), and the noisy ones the noise-spec file and its sha256.
"""
from __future__ import annotations

import glob
import json
import os

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "results")
TESTS = ("accuracy", "analytic_f", "noise_behaviour", "skqd_energy", "engine_validation")


def _path(lattice, family, device, test):
    return os.path.join(RESULTS, lattice, family, device, test + ".json")


def list_available() -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(RESULTS, "*", "*", "*", "*.json"))):
        rel = os.path.relpath(p, RESULTS).split(os.sep)
        if len(rel) == 4 and rel[3][:-5] in TESTS:
            out.append((rel[0], rel[1], rel[2], rel[3][:-5]))
    return out


def load(lattice: str, family: str, device: str, test: str) -> dict:
    p = _path(lattice, family, device, test)
    if not os.path.exists(p):
        avail = [x for x in list_available() if x[0] == lattice and x[3] == test]
        raise FileNotFoundError(f"{p} not found; available for ({lattice}, {test}): {avail}")
    with open(p) as fh:
        return json.load(fh)


def _flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict) and k not in ("accepted_counts", "native_counts", "ops"):
            out.update(_flat(v, prefix + k + "."))
        elif not isinstance(v, (list, dict)):
            out[prefix + k] = v
    return out


def table(test: str, lattice: str):
    """One row per (family, device, circuit) for the test at the lattice (pandas DataFrame)."""
    import pandas as pd
    rows = []
    for lat, fam, dev, t in list_available():
        if lat != lattice or t != test:
            continue
        d = load(lat, fam, dev, t)
        for circ, r in d.get("rows", {}).items():
            row = {"lattice": lat, "family": fam, "device": dev, "circuit": circ}
            row.update(_flat(r))
            rows.append(row)
    return pd.DataFrame(rows)


def summary(test: str, lattice: str):
    """One row per (family, device): the 'summary' block of each result JSON."""
    import pandas as pd
    rows = []
    for lat, fam, dev, t in list_available():
        if lat != lattice or t != test:
            continue
        d = load(lat, fam, dev, t)
        row = {"lattice": lat, "family": fam, "device": dev}
        row.update(_flat(d.get("summary", {})))
        rows.append(row)
    return pd.DataFrame(rows)


def index() -> dict:
    p = os.path.join(RESULTS, "index.json")
    with open(p) as fh:
        return json.load(fh)

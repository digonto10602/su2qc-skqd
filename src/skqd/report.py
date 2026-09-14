"""
Gate-result bookkeeping: every gate script records its criteria and the numbers
it actually computed in validation/<GATE>.json and writes reports/<GATE>_*.md
from those same numbers.  Nothing in a report is typed by hand.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field

import numpy as np
import scipy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def environment() -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                         stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        commit = "n/a"
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "git_commit": commit,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }


@dataclass
class Criterion:
    name: str
    value: float | int | str
    threshold: str
    passed: bool


@dataclass
class GateResult:
    gate: str
    title: str
    criteria: list = field(default_factory=list)
    data: dict = field(default_factory=dict)
    runtime_s: float = 0.0

    def add(self, name, value, threshold, passed):
        self.criteria.append(Criterion(name, value, threshold, bool(passed)))

    @property
    def passed(self):
        return all(c.passed for c in self.criteria)

    def save(self):
        os.makedirs(os.path.join(ROOT, "validation"), exist_ok=True)
        out = {
            "gate": self.gate, "title": self.title, "status": "PASS" if self.passed else "FAIL",
            "criteria": [c.__dict__ for c in self.criteria], "data": _jsonable(self.data),
            "runtime_s": self.runtime_s, "environment": environment(),
        }
        path = os.path.join(ROOT, "validation", f"{self.gate}.json")
        with open(path, "w") as fh:
            json.dump(out, fh, indent=1)
        return path

    def criteria_table(self) -> str:
        lines = ["| check | value | criterion | result |", "|---|---|---|---|"]
        for c in self.criteria:
            v = c.value
            if isinstance(v, float):
                v = f"{v:.3e}" if (abs(v) < 1e-3 or abs(v) > 1e4) and v != 0 else f"{v:.6g}"
            lines.append(f"| {c.name} | {v} | {c.threshold} | {'PASS' if c.passed else 'FAIL'} |")
        return "\n".join(lines)


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, complex):
        return [x.real, x.imag]
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def write_report(name: str, text: str) -> str:
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    path = os.path.join(ROOT, "reports", name)
    with open(path, "w") as fh:
        fh.write(text)
    return path


def md_table(header: list, rows: list) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(lines)


def env_block() -> str:
    e = environment()
    return (f"Environment: Python {e['python']}, numpy {e['numpy']}, scipy {e['scipy']}, "
            f"{e['platform']}, {e['cpu_count']} CPUs, commit {e['git_commit']}, {e['timestamp']}.")

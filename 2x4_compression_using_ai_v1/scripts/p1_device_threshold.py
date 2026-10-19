"""Phase-1 arithmetic: how small must a 2x4 circuit be before any Quantinuum device row of the
package gives a gate-only clean fraction f >= 0.1 (mean criterion) or >= 0.05 (worst criterion)?

Uses only the package's own formula, skqd.device_req.clean_shot_fraction
(f = (1-eps2)^n_2q (1-eps1)^n_1q (1-eps_ro)^n_meas), the package's device table
(data/quantinuum/devices_20261002.json, eps_ro = mean of the two SPAM values as the package does)
and the frozen 2x4 manifests for the baseline counts.  The one-qubit count is modelled as
r x n_2q with r taken from the baseline families (opt3, structured) and from the frozen 2x3
family; n_meas = 28.  Writes data/p1_device_threshold.json.  No noise model beyond the package's.
"""
from __future__ import annotations

import glob
import json
import math
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(ROOT, "src"))

from skqd.device_req import clean_shot_fraction  # noqa: E402

N_MEAS = 28


def git_commit():
    return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()


def max_n2(target, eps2, eps1, eps_ro, ratio):
    """Largest integer n_2q with f(n_2q, round(ratio n_2q), 28) >= target (None if even 0 fails)."""
    if clean_shot_fraction(0, 0, N_MEAS, eps2, eps1, eps_ro) < target:
        return None
    lo, hi = 0, 10 ** 7
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if clean_shot_fraction(mid, int(round(ratio * mid)), N_MEAS, eps2, eps1, eps_ro) >= target:
            lo = mid
        else:
            hi = mid
    return lo


def main():
    dev = json.load(open(os.path.join(ROOT, "data", "quantinuum", "devices_20261002.json")))
    specs = dev["specs"]
    base = {}
    for src in ("opt3", "structured"):
        mans = sorted(glob.glob(os.path.join(ROOT, "data", "quantinuum", "circuits_2x4",
                                             f"B*_ref*_k*.{src}.manifest.json")))
        zz, px = [], []
        for p in mans:
            m = json.load(open(p))
            c = m["levels"]["0"]["counts"] if "0" in m["levels"] else list(m["levels"].values())[0]["counts"]
            zz.append(c["n_zz"])
            px.append(c["n_phasedx"])
        base[src] = {"n_manifests": len(mans), "n_zz_mean": sum(zz) / len(zz),
                     "n_phasedx_mean": sum(px) / len(px),
                     "ratio_1q_per_2q": (sum(px) / len(px)) / (sum(zz) / len(zz))}
    c23 = dev["counts"]["2x3"]
    ratios = {"opt3_2x4": base["opt3"]["ratio_1q_per_2q"],
              "structured_2x4": base["structured"]["ratio_1q_per_2q"],
              "frozen_2x3": c23["n_1q_mean"] / c23["n_2q_mean"], "no_1q": 0.0}
    rows = {}
    for key, s in specs.items():
        if "eps2" not in s:
            continue
        e2, e1, ero = s["eps2"], s["eps1"], 0.5 * (s["eps_ro_0"] + s["eps_ro_1"])
        r = {"device": s.get("device_name", key), "eps2": e2, "eps1": e1, "eps_ro": ero,
             "qubits": s.get("qubits"),
             "f_baseline": {src: clean_shot_fraction(int(round(b["n_zz_mean"])),
                                                     int(round(b["n_phasedx_mean"])), N_MEAS, e2, e1, ero)
                            for src, b in base.items()},
             "max_n2q": {}}
        for tgt in (0.1, 0.05):
            for rk, rv in ratios.items():
                n = max_n2(tgt, e2, e1, ero, rv)
                r["max_n2q"][f"f>={tgt}|1q_ratio={rk}"] = {
                    "n_2q": n, "ratio_used": rv,
                    "compression_needed_vs_structured": (base["structured"]["n_zz_mean"] / n) if n else None}
        rows[key] = r
    out = {"produced_by": "2x4_compression_using_ai_v1/scripts/p1_device_threshold.py",
           "git_commit": git_commit(), "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
           "machine": {"platform": platform.platform(), "python": platform.python_version()},
           "formula": "skqd.device_req.clean_shot_fraction; eps_ro = mean(eps_ro_0, eps_ro_1); n_meas = 28; "
                      "memory/transport error NOT included (the package's gate-only f)",
           "baseline": base, "ratios": ratios, "rows": rows,
           "note": "a model of the one-qubit count as ratio x n_2q is an assumption of this arithmetic"}
    with open(os.path.join(STUDY, "data", "p1_device_threshold.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    for k, r in rows.items():
        print(r["device"], {kk: (v["n_2q"], None if v["compression_needed_vs_structured"] is None
                                  else round(v["compression_needed_vs_structured"], 1))
                            for kk, v in r["max_n2q"].items()},
              {s: f"{v:.3e}" for s, v in r["f_baseline"].items()})


if __name__ == "__main__":
    main()

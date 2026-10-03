"""prompts/26 A5 / Q4-Q5: data/quantinuum/devices_20261002.json (scripts/quantinuum_device_table.py).

Runs in `coding` (no pytket).  Skips when the frozen circuits (prompts/26 A3) are not built, since the
2x3 counts of the table are read from their manifests.
"""
import glob
import json
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import quantinuum_device_table as qt  # noqa: E402
from skqd import quantinuum_native as qn  # noqa: E402

CIRC = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
HAVE_FROZEN = len(glob.glob(os.path.join(CIRC, "B*_ref*_k*.manifest.json"))) == 44
frozen = pytest.mark.skipif(not HAVE_FROZEN, reason="the 44 frozen circuits of prompts/26 A3 are not built")


def test_prototype_quantinuum_f_reproduced_to_1e_12():
    for name, v in qt.reproduce_prototype().items():
        assert v["abs_diff"] <= 1e-12, (name, v)


def test_ionq_rows_reproduced_to_1e_12():
    rep, rows = qt.reproduce_ionq()
    assert rep and all(v["abs_diff"] <= 1e-12 for v in rep.values())
    assert "2x3|ionq_forte|virtual_rz" in rows["results"]


def test_every_spec_has_source_read_on_verbatim():
    for name, s in qt.SPECS.items():
        assert s["source"] and s["read_on"] == "2026-10-02" and s["verbatim"], name
        assert all(isinstance(v, str) for v in s["verbatim"].values()), name
    assert qt.MEMORY_MODEL["flag"] == "ESTIMATE"
    assert qt.BILLING["usd_per_hqc_ESTIMATE"]["flag"] == "ESTIMATE"


def test_solve_eps2_matches_required_error_on_one_circuit():
    from skqd.device_req import clean_shot_fraction, required_error

    other = clean_shot_fraction(0, 3000, 20, 0.0, 3e-5, 5e-4)
    a = qt.solve_eps2(lambda x: clean_shot_fraction(2158, 3000, 20, x, 3e-5, 5e-4), 0.1)
    b = required_error(2158, 0.1, other)
    assert abs(a - b) < 1e-12


@frozen
def test_table_rows_and_hqc_consistency():
    c = qt.counts_2x3()
    assert len(c["per_circuit"]) == 44 and all(p["n_2q"] <= 2158 for p in c["per_circuit"])
    for p in c["per_circuit"]:
        recomputed = qn.hqc_per_shot({"n_phasedx": p["n_1q"], "n_zz": p["n_2q"],
                                      "n_qubits": p["n_qubits"], "n_meas": p["n_meas"]})
        assert abs(recomputed - p["hqc_per_shot"]) <= 1e-12
    r = qt.row("quantinuum_h2_2", qt.SPECS["quantinuum_h2_2"], "2x3", c)
    assert abs(r["hqc_per_shot_mean"] - np.mean([p["hqc_per_shot"] for p in c["per_circuit"]])) <= 1e-12
    assert r["f_gate_only_worst"] <= r["f_gate_only_mean"]
    assert set(r["memory_ESTIMATE"]["scenarios"]) == {"low", "mid", "high"}

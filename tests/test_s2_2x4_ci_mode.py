"""Gate S2_2x4 under the Perlmutter CI (part F, criterion C6), checked without a GPU.

* the CI runs `run_gate.py S2_2x4` with no arguments, so the CI defaults must select the GPU
  job of C6 and a following assemble; explicit flags still win; the laptop default is unchanged;
* the gate module imports no qiskit at load time (the CI runs qiskit 1.4.3, the laptop 2.5.2);
* the shipped circuit is QPY version 13 (readable by qiskit 1.x), round-trips identically and
  carries the 69688-CZ count the compile stage reported;
* a circuit file that does not match its manifest makes the C6 job fail LOUDLY -- there is no
  re-transpilation fallback.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "gate_S2_2x4.py")


def _gate():
    spec = importlib.util.spec_from_file_location("gate_S2_2x4_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ci_defaults_select_the_gpu_job_and_explicit_flags_win():
    g = _gate()
    a = g.build_parser({"CI_GATE": "S2_2x4"}).parse_args([])
    assert (a.stage, a.device, a.lattice, a.gpu_jobs) == ("gpu", "GPU", 4, "transpiled")
    assert a.then_assemble is True and a.tests_from_record is True
    b = g.build_parser({"CI_GATE": "S2_2x4"}).parse_args(["--stage", "assemble",
                                                           "--device", "CPU"])
    assert (b.stage, b.device) == ("assemble", "CPU")
    c = g.build_parser({}).parse_args([])
    assert (c.stage, c.device) == ("assemble", "CPU")
    assert c.then_assemble is False and c.tests_from_record is False


def test_gate_module_imports_no_qiskit_at_load():
    code = (f"import importlib.util, sys; spec = importlib.util.spec_from_file_location('g', "
            f"{SCRIPT!r}); m = importlib.util.module_from_spec(spec); "
            f"spec.loader.exec_module(m); print('qiskit' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().splitlines()[-1] == "False"


def test_map_to_physical():
    g = _gate()
    ints = np.array([0b001, 0b010, 0b110], dtype=np.int64)
    assert np.array_equal(g.map_to_physical(ints, None), ints)
    assert np.array_equal(g.map_to_physical(ints, [0, 1, 2]), ints)
    # virtual 0 -> physical 2, 1 -> 0, 2 -> 1
    assert list(g.map_to_physical(ints, [2, 0, 1])) == [0b100, 0b001, 0b011]


def test_shipped_circuit_is_qpy13_and_matches_its_manifest():
    g = _gate()
    path, mpath = g.transpiled_v13_path(4), g.transpiled_manifest_path(4)
    if not (os.path.exists(path) and os.path.exists(mpath)):
        pytest.skip("the 2x4 v13 circuit is not in this checkout")
    with open(mpath) as fh:
        man = json.load(fh)
    assert g._qpy_header(path) == {"magic": "QISKIT", "qpy_version": 13}
    assert g._sha256_file(path) == man["sha256"]
    assert man["roundtrip_identical"] is True
    assert man["n_2q"] == man["n_2q_reported_by_compile"] == 69688
    assert man["final_layout_is_identity"] is True


def test_a_mismatched_circuit_file_fails_loudly(tmp_path, monkeypatch):
    g = _gate()
    src = g.transpiled_v13_path(2)
    if not os.path.exists(src):
        pytest.skip("the 2x2 v13 circuit is not in this checkout")
    bad = tmp_path / "c.qpy.gz"
    shutil.copy(src, bad)
    with open(g.transpiled_manifest_path(2)) as fh:
        man = json.load(fh)
    man["sha256"] = "0" * 64
    mp = tmp_path / "c.json"
    mp.write_text(json.dumps(man))
    monkeypatch.setattr(g, "transpiled_v13_path", lambda lat: str(bad))
    monkeypatch.setattr(g, "transpiled_manifest_path", lambda lat: str(mp))
    e = g.transpiled_job(SimpleNamespace(device="CPU"), 2, None, None)
    assert e["complete"] is False
    assert "sha256" in e["error"]
    assert "leakage" not in e


def test_assemble_reads_c6_from_the_gpu_file_only_when_complete(tmp_path):
    """A synthetic part-F file (a test fixture, not a result): a completed 2x4 entry is taken,
    an incomplete one is reported with its error, other lattices are ignored."""
    g = _gate()
    assert g.gpu_c6_entries(str(tmp_path / "absent.json")) == ({}, [], None)
    f = tmp_path / "gpu.json"
    f.write_text(json.dumps({"lattice": 4, "angle_mode": "exact", "device": "GPU",
                             "compiled": {"B0_ref0_k1|all_to_all":
                                          {"complete": True, "leakage": 1e-14}},
                             "amplitudes_on_codewords": {"x": [1]}}))
    ok, fail, summ = g.gpu_c6_entries(str(f))
    assert list(ok) == ["B0_ref0_k1|all_to_all|aer_GPU"] and fail == []
    assert "amplitudes_on_codewords" not in summ
    f.write_text(json.dumps({"lattice": 4, "angle_mode": "exact", "device": "GPU",
                             "compiled": {"B0_ref0_k1|all_to_all":
                                          {"complete": False, "error": "QpyError: v13"}}}))
    ok, fail, _ = g.gpu_c6_entries(str(f))
    assert ok == {} and "QpyError" in fail[0]
    f.write_text(json.dumps({"lattice": 2, "angle_mode": "exact", "compiled": {}}))
    assert g.gpu_c6_entries(str(f)) == ({}, [], None)

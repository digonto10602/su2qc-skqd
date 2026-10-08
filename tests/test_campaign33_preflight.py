"""
prompts/33a step A: the campaign driver's preflight.  The first CI wave of prompts/33 died after 15-21 s on
`ModuleNotFoundError: threadpoolctl` (jobs 59491455 / 59491462 / 59491480).  The preflight imports every module
a token needs before ci_context, QPY or AerSimulator; a missing one prints the package and the install line,
writes the token JSON (status FAIL, criterion `S0 preflight imports`) and exits 3.  No silent fallback (R5).
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import campaign33 as C33  # noqa: E402
from skqd.campaign33 import tokens as TK  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_missing_threadpoolctl_exits_3_with_the_install_line(monkeypatch, capsys, tmp_path):
    monkeypatch.setitem(sys.modules, "threadpoolctl", None)       # a stub sys.modules without threadpoolctl
    with pytest.raises(SystemExit) as e:
        C33.preflight("C1_IDEAL", root=str(tmp_path))
    assert e.value.code == 3 == C33.PREFLIGHT_EXIT
    out = capsys.readouterr().out
    assert "preflight: missing threadpoolctl; install: pip install threadpoolctl (env skqd)" in out
    d = json.load(open(tmp_path / "validation" / "C1_IDEAL.json"))
    assert d["status"] == "FAIL" and d["criteria"][0]["name"] == "S0 preflight imports"
    assert d["data"]["preflight"]["missing"] == "threadpoolctl" and not d["criteria"][0]["passed"]
    assert d["data"]["run"]["versions"]["threadpoolctl"].startswith("unavailable")


def test_missing_module_in_a_dry_run_writes_the_dryrun_json(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "threadpoolctl", None)
    with pytest.raises(SystemExit):
        C33.preflight("C4_F1_B0", dry=True, root=str(tmp_path))
    assert (tmp_path / "validation" / "dryrun" / "C4_F1_B0.json").exists()


def test_main_runs_the_preflight_before_anything(monkeypatch, tmp_path):
    """main() calls preflight first: with threadpoolctl missing it exits 3 before ci_context / argparse."""
    monkeypatch.setitem(sys.modules, "threadpoolctl", None)
    called = []
    monkeypatch.setattr(C33, "ci_context", lambda: called.append(1) or {})
    monkeypatch.setattr(C33, "ROOT", str(tmp_path))
    with pytest.raises(SystemExit) as e:
        C33.main(["--token", "C2_CAL", "--dry-run"])
    assert e.value.code == 3 and not called


@pytest.mark.parametrize("tok", list(TK.load_tokens()))
def test_every_token_passes_preflight_quickly(tok):
    t0 = time.time()
    r = C33.preflight(tok, write=False)
    assert time.time() - t0 < 5.0 and r["seconds"] < 5.0
    assert r["versions"]["threadpoolctl"] and not r["versions"]["threadpoolctl"].startswith("unavailable")
    mods, env = C33.preflight_modules(tok)
    assert "threadpoolctl" in mods if env == "skqd" else "numpy" in mods


def test_versions_record_threadpoolctl():
    assert "threadpoolctl" in C33.versions()


def test_package_check_smoke_and_setup_name_threadpoolctl():
    assert '"threadpoolctl"' in open(os.path.join(ROOT, "scripts", "check_package.py")).read()
    assert "import threadpoolctl" in open(os.path.join(ROOT, "scripts", "ci_smoke.py")).read()
    s = open(os.path.join(ROOT, "SKQD-CI-SETUP.md")).read()
    assert "pip install numpy scipy threadpoolctl pytest qiskit qiskit-aer-gpu cudaq" in s

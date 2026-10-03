"""prompts/26 A7: scripts/quantinuum_submit.py and scripts/quantinuum_account.py.

No test here contacts Quantinuum: the parser, the job records, the refusals, the dry run on the
local Aer path and the counts-file decoding.  The dry-run test needs pytket (the isolated venv) and
the frozen circuits of prompts/26 A3, and skips with that reason otherwise.
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import quantinuum_account as qa  # noqa: E402
import quantinuum_submit as qs  # noqa: E402
from skqd.reference_sim import bits_to_int, qiskit_key_to_bits  # noqa: E402

CIRC = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
HAVE_PYTKET = importlib.util.find_spec("pytket") is not None
HAVE_FROZEN = os.path.exists(os.path.join(CIRC, "index.json"))
FAKE = "FAKE-NEXUS-CREDENTIAL-7f3a9c"
SECRET_WORDS = ("password", "passwd", "token", "secret", "apikey", "api-key", "api_key")


def option_strings(parser):
    return [(s, a) for a in parser._actions for s in a.option_strings]


@pytest.mark.parametrize("parser", [qs.build_parser(), qa.build_parser()])
def test_parsers_take_no_secret(parser):
    for s, action in option_strings(parser):
        assert not any(w in s.lower() for w in SECRET_WORDS), s
        if "cred" in s.lower():                 # --credentials is a flag, never a value
            assert action.nargs == 0, s


def test_bits_to_qiskit_key_round_trip():
    for bits in [(1, 0, 0), (0, 1, 1, 0, 1), (0,) * 20]:
        assert qiskit_key_to_bits(qs.bits_to_qiskit_key(bits)) == bits
    assert bits_to_int(qiskit_key_to_bits(qs.bits_to_qiskit_key((1, 0, 0)))) == 1


def test_offline_preflight_record_lists_every_missing_guard():
    class A:
        max_cost = None
        cap_hqc = None
        prereg = None
    rec = qs.preflight_record(A(), [{"circuit_id": "x", "chunk": 0, "n_shots": 10, "device_name": "H2-2",
                                     "qasm_sha256": "0", "max_cost": 1.0, "hqc_estimate": 0.5}])
    assert not rec["ok"]
    assert {"--max-cost missing", "--cap-hqc missing", "--prereg missing"} <= set(rec["problems"])
    assert "no per-job calibration record" in rec["calibration_record_note"]


def test_token_store_status_reads_names_only(tmp_path, monkeypatch):
    d = tmp_path / ".qnx" / "auth"
    d.mkdir(parents=True)
    (d / "refresh_token").write_text(FAKE)
    monkeypatch.setattr(qa, "TOKEN_DIR", str(d))
    st = qa.token_store_status()
    assert st["exists"] and st["files"] == ["refresh_token"]
    assert FAKE not in json.dumps(st)


@pytest.mark.skipif(not HAVE_FROZEN, reason="frozen circuits of prompts/26 A3 not built")
def test_remote_phases_refuse_without_their_guards(tmp_path):
    with pytest.raises(SystemExit, match="max-cost"):
        qs.main(["--emulate", "--out", str(tmp_path / "e")])
    with pytest.raises(SystemExit, match="refuses"):
        qs.main(["--submit", "--out", str(tmp_path / "s")])
    with pytest.raises(SystemExit, match="Guppy"):
        qs.main(["--emulate", "--device", "Helios-1E", "--max-cost", "100", "--out", str(tmp_path / "h")])
    with pytest.raises(SystemExit, match="emulator"):
        qs.main(["--emulate", "--device", "H2-2", "--max-cost", "100", "--out", str(tmp_path / "x")])


@pytest.mark.skipif(not HAVE_FROZEN, reason="frozen circuits of prompts/26 A3 not built")
def test_job_records_carry_the_required_config_fields():
    args = qs.build_parser().parse_args(["--dry-run", "--shots", "12000"])
    jobs = qs.plan_jobs(args, CIRC, qs.load_index(CIRC), "H2-2")
    k1 = [j for j in jobs if j["circuit_id"].endswith("_k1")]
    assert len({j["circuit_id"] for j in k1}) == 2
    assert sorted(j["n_shots"] for j in k1 if j["circuit_id"] == k1[0]["circuit_id"]) == [2000, 10000]
    for j in jobs:
        bc = j["backend_config"]
        assert bc["no_opt"] is True and bc["allow_implicit_swaps"] is False
        assert bc["max_cost"] is not None and j["max_cost"] >= j["hqc_estimate"]
        assert j["job_id"] is None and j["n_shots"] <= 10000


@pytest.mark.skipif(not (HAVE_PYTKET and HAVE_FROZEN),
                    reason="needs pytket (isolated venv ~/.local/share/su2qc-quantinuum/venv) and the "
                           "frozen circuits of prompts/26 A3")
def test_dry_run_writes_session_and_counts_and_leaks_no_credential(tmp_path):
    out = tmp_path / "dry"
    env = dict(os.environ, NEXUS_PASSWORD=FAKE, QNX_TOKEN=FAKE)
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "quantinuum_submit.py"), "--dry-run",
           "--only", "CAL_zeros", "CAL_x0", "--cal-shots", "50", "--out", str(out), "--threads", "2"]
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert p.returncode == 0, p.stderr[-2000:]
    assert FAKE not in p.stdout + p.stderr
    for dirpath, _d, files in os.walk(out):
        for f in files:
            assert FAKE not in open(os.path.join(dirpath, f)).read(), f
    sess = json.load(open(out / "session.json"))
    assert sess["dry_run"] is True and len(sess["jobs"]) == 2
    for j in sess["jobs"]:
        assert j["job_id"] is None and j["backend_config"]["no_opt"] is True
        assert j["backend_config"]["allow_implicit_swaps"] is False and j["max_cost"] is not None
    rec = json.load(open(out / "counts" / "CAL_x0.json"))
    counts = {bits_to_int(qiskit_key_to_bits(k)): v for k, v in rec["counts"].items()}
    assert max(counts, key=counts.get) == 1 and sum(counts.values()) == 50
    rec0 = json.load(open(out / "counts" / "CAL_zeros.json"))
    c0 = {bits_to_int(qiskit_key_to_bits(k)): v for k, v in rec0["counts"].items()}
    assert max(c0, key=c0.get) == 0
    # raw data are never overwritten
    p2 = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    assert p2.returncode != 0 and "never overwritten" in (p2.stdout + p2.stderr)

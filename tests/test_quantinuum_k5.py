"""The k = 5 extension of the frozen 2x2 / 2x3 Quantinuum sets (owner request 2026-10-28).

Code: gate_S2D.circuit_set(Lx, ks, dts) (defaults unchanged) and quantinuum_build_circuits.frozen_dts /
copy_calibration.  Data: data/quantinuum/circuits_2x{2,3}_k5 against the frozen folders (ids, dt bit for bit,
calibration bytes, file hashes, verify.json status).  No pytket needed: runs in `coding`.
"""
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gate_S2D  # noqa: E402
import quantinuum_build_circuits as B  # noqa: E402

QD = os.path.join(ROOT, "data", "quantinuum")


def _load(p):
    with open(p) as fh:
        return json.load(fh)


def _sha_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def test_circuit_set_default_is_k1_to_4_at_the_model_dt():
    M, _F, cset = gate_S2D.circuit_set(2)
    assert sorted({c[2] for c in cset}) == [1, 2, 3, 4]
    assert len(cset) == 28
    ids = sorted(B.circuit_id(*c[:3]) for c in cset)
    assert ids == sorted(_load(os.path.join(QD, "circuits_2x2", "index.json"))["circuits"])


def test_circuit_set_k5_with_pinned_dt_equals_the_factory_step():
    dts = B.frozen_dts(os.path.join(QD, "circuits_2x2"))
    M, F, cset = gate_S2D.circuit_set(2, ks=(5,), dts=dts)
    assert len(cset) == 7 and {c[2] for c in cset} == {5}
    for twoB, r, k, gates in cset:
        assert gates == F.coarse_step(r, 5, dts[twoB])


@pytest.mark.parametrize("lat", [2, 3])
def test_frozen_dts_are_the_manifest_values(lat):
    d = os.path.join(QD, f"circuits_2x{lat}")
    dts = B.frozen_dts(d)
    idx = _load(os.path.join(d, "index.json"))
    for c in idx["circuits"]:
        m = _load(os.path.join(d, c + ".manifest.json"))
        assert m["dt"] == dts[m["twoB"]]


def test_frozen_dts_refuses_two_values_in_one_sector(tmp_path):
    ids = ["B0_ref01_k1", "B0_ref01_k2", "B1_ref02_k1"]
    for c, dt, tb in zip(ids, (0.1, 0.1000000001, 0.2), (0, 0, 2)):
        (tmp_path / (c + ".manifest.json")).write_text(json.dumps({"twoB": tb, "dt": dt}))
    (tmp_path / "index.json").write_text(json.dumps({"circuits": ids}))
    with pytest.raises(SystemExit):
        B.frozen_dts(str(tmp_path))


def test_copy_calibration_is_byte_identical(tmp_path, monkeypatch):
    src = os.path.join(QD, "circuits_2x2")
    monkeypatch.setattr(B, "OUT", str(tmp_path))
    mans = B.copy_calibration(src)
    assert [m["id"] for m in mans] == _load(os.path.join(src, "index.json"))["calibration"]
    for m in mans:
        for nm in (m["id"] + ".manifest.json", m["files"]["qasm"], m["files"]["json"]):
            assert _sha_file(os.path.join(tmp_path, nm)) == _sha_file(os.path.join(src, nm))


@pytest.mark.parametrize("lat,n_refs", [(2, 7), (3, 11)])
def test_k5_folder_against_the_frozen_set(lat, n_refs):
    d, fz = os.path.join(QD, f"circuits_2x{lat}_k5"), os.path.join(QD, f"circuits_2x{lat}")
    if not os.path.exists(os.path.join(d, "index.json")):
        pytest.skip(f"{d} not built")
    idx, fidx = _load(os.path.join(d, "index.json")), _load(os.path.join(fz, "index.json"))
    refs = sorted(c.rsplit("_k", 1)[0] for c in fidx["circuits"] if c.endswith("_k1"))
    assert len(refs) == n_refs
    assert sorted(idx["circuits"]) == [r + "_k5" for r in refs]
    assert idx["calibration"] == fidx["calibration"]
    for key in ("device_name_compiled_for", "transpile", "levels", "selection_rule", "versions"):
        assert idx[key] == fidx[key], key
    assert set(fidx) <= set(idx)                                  # same format (+ the k-extension provenance)
    dts = B.frozen_dts(fz)
    for c in idx["circuits"]:
        m = _load(os.path.join(d, c + ".manifest.json"))
        assert m["k"] == 5 and m["dt"] == dts[m["twoB"]] and m["frozen_level"] == 0
        with open(os.path.join(d, m["files"]["qasm"])) as fh:
            assert hashlib.sha256(fh.read().encode()).hexdigest() == m["qasm_sha256"] == idx["files"][c]["qasm_sha256"]
        with open(os.path.join(d, m["files"]["json"])) as fh:
            assert hashlib.sha256(fh.read().encode()).hexdigest() == m["json_sha256"] == idx["files"][c]["json_sha256"]
    for c in idx["calibration"]:
        m = _load(os.path.join(fz, c + ".manifest.json"))
        for nm in (c + ".manifest.json", m["files"]["qasm"], m["files"]["json"]):
            assert _sha_file(os.path.join(d, nm)) == _sha_file(os.path.join(fz, nm))
    vp = os.path.join(d, "verify.json")
    if os.path.exists(vp):
        v = _load(vp)
        assert v["status"] == "PASS"
        assert v["index_sha256"] == _sha_file(os.path.join(d, "index.json"))

"""
prompts/33a steps B, C, D: the driver paths of C2_CAL run 2, a C2 production cell, a C4_PART slot and the
assembly of a split run, end to end with a stub simulator (seeded random strings) instead of Aer.

Why a stub: a 21-qubit noisy shot costs 1-5 minutes on the laptop CPU (the C2_CAL dry run of prompts/33a, 4 / 8
/ 4 shots, did not finish inside the 30-minute rule; the reduced 2 / 2 / 2 run reached the Kraus arm only), so
the bookkeeping -- arms, P4a / P4b / P4c / P5', the decision block, S6, the slot content check, the content-named
copy, the parts' chunk ranges and their merge -- is pinned here without the physics cost.  The channels
themselves are tested in tests/test_campaign33_noise.py (RM vs Kraus on the real record).
"""
import json
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import campaign33 as C33  # noqa: E402
from skqd.campaign33 import noise as N  # noqa: E402
from skqd.campaign33 import sampling as SM  # noqa: E402
from skqd.campaign33 import tokens as TK  # noqa: E402
from skqd.campaign33 import tokens_run as TR  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class FakeResult:
    def __init__(self, counts):
        self.success, self._c = True, counts

    def get_counts(self, i=0):
        return self._c


class FakeSim:
    """Seeded strings: half random 20-bit garbage, half codewords (so that decoding has something to accept)."""

    def __init__(self, codewords, n_bits=20):
        self.cw, self.n = list(codewords), n_bits

    def run(self, circ, shots, seed_simulator):
        rng = np.random.default_rng(int(seed_simulator) % (2 ** 32))
        out = {}
        for _ in range(int(shots)):
            x = int(rng.choice(self.cw)) if rng.random() < 0.5 else int(rng.integers(0, 2 ** self.n))
            k = format(x, f"0{self.n}b")
            out[k] = out.get(k, 0) + 1
        return SimpleNamespace(result=lambda: FakeResult(out))


def fake_spec(rep):
    return SimpleNamespace(noise_model=None, apply=lambda c: c, local_errors={}, t1s=[], t2s=[], dt=1e-9,
                           readout_per_qubit={}, description={"representation": rep, "t2_convention": "echo",
                                                               "id": "stub"})


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Outputs (validation/, reports/, results/) go to tmp_path; inputs stay the repository's."""
    import skqd.report as REP
    for sub in ("validation/dryrun", "validation/archive", "reports/dryrun"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    arch = os.path.join(ROOT, TR.C2_CAL_ARCHIVE)
    (tmp_path / TR.C2_CAL_ARCHIVE).write_bytes(open(arch, "rb").read())
    monkeypatch.setattr(REP, "ROOT", str(tmp_path))
    monkeypatch.setattr(C33, "ROOT", str(tmp_path))
    real_vp = TR.validation_path
    monkeypatch.setattr(TR, "validation_path",
                        lambda ctx, tok: os.path.join(str(tmp_path), "validation", "dryrun" if ctx.dry else "", tok + ".json"))
    from skqd.campaign33.analysis import Physics
    P = Physics(with_sectors=False)
    cws = [int(x) for x in P.emb.ints]
    monkeypatch.setattr(TR, "simulator", lambda ctx, nm, mode: (FakeSim(cws), {"stub": True}))
    monkeypatch.setattr(TR, "ROOT", TR.ROOT)
    return tmp_path, real_vp


def run_dry(token, extra=()):
    args = C33.apply_dry_defaults(C33.build_parser({}).parse_args(["--token", token, "--dry-run"] + list(extra)))
    return C33.run_token(args, {})


def test_c2_cal_run2_and_a_c2_cell(sandbox, monkeypatch):
    tmp, _ = sandbox
    monkeypatch.setattr(N, "ibm_spec", lambda rec, cell, rep, conv="echo", *a, **k: fake_spec(rep))
    monkeypatch.setattr(N, "rm_vs_kraus_check", lambda *a, **k: {
        "ok": True, "changed_qubits": {"59": {}}, "n_unchanged": 17, "max_superop_diff_unchanged": 0.0,
        "kraus_in_rm": {"to_dict": 0, "custom_pass_sites": 0}})
    rc = run_dry("C2_CAL")
    d = json.load(open(tmp / "validation" / "dryrun" / "C2_CAL.json"))
    assert rc == 0 and d["status"] == "PASS", [c for c in d["criteria"] if not c["passed"]]
    D = d["data"]
    assert D["calibration_run"] == 2 == D["run"]["calibration_run"] and D["supersedes"]["job"] == "59491475"
    assert D["supersedes"]["sha256"] == "54b77474065486eaa0f43b5e1c7403ed521ddafcd1d3abd58d6b85fca1022ac7"
    assert [D["arms"][r]["shots_done"] for r in ("pta", "rm", "kraus")] == [4, 8, 4], "the prompt's 4 / 8 / 4"
    assert all(len(D["arms"][r]["points"]) >= 2 for r in D["arms"])
    assert D["decision"]["production_representation"] in ("rm", "kraus")
    assert D["decision"]["production_representation"] == ("rm" if D["comparisons"]["P4a_rm_vs_kraus"]["pass"] else "kraus")
    assert D["comparisons"]["P4a_rm_vs_kraus"]["n_marginal_tests"] == 20, "20 clbits (the prompt says 21)"
    assert D["K1_device_structure"]["shots"] == 100000 and D["K1_device_structure"]["map_matches_circuit"]
    assert set(D["comparisons"]["P4c_vs_K1"]) == {"pta", "rm", "kraus", "K1_device"}
    names = [c["name"] for c in d["criteria"]]
    assert any(n.startswith("P0 ") for n in names) and any(n.startswith("P4r ") for n in names)
    # ---- a production cell reads the run-2 decision
    monkeypatch.setattr(N, "f0_ibm", lambda *a, **k: {"g0": None, "f0": None, "stub": True})
    for tok in ("C2_ECHO", "C2_XY4"):
        rc = run_dry(tok)
        c = json.load(open(tmp / "validation" / "dryrun" / f"{tok}.json"))
        assert rc == 0 and c["status"] == "PASS", [x for x in c["criteria"] if not x["passed"]]
        C = c["data"]
        assert C["representation_used"] == D["decision"]["production_representation"]
        assert set(C["arms"]) == {"kraus_reference", "production"}
        for v in C["per_run"].values():
            cp = v["comparison_power"]
            assert cp["counts"] == "underpowered" and cp["circuit"] == ("like_for_like" if tok == "C2_XY4"
                                                                         else "different_circuit_variant")
            assert v["z_vs_K1"]["evaluated"] and v["measured_K1"]["accepted"] in (58, 45)
        assert C["arms"]["production"]["equal_shots"]


def test_c2_cell_falls_back_to_kraus_on_the_run1_record(sandbox):
    tmp, _ = sandbox
    ctx = SimpleNamespace(dry=False, device="GPU")
    (tmp / "validation" / "C2_CAL.json").write_bytes(open(os.path.join(ROOT, TR.C2_CAL_ARCHIVE), "rb").read())
    rep, mode, _r, src = TR.c2_cal_decision(ctx)
    assert rep == "kraus" and mode == "custatevec" and "run-1 record" in src


def test_part_slot_and_assembly(sandbox, monkeypatch):
    """A split dry F run: part 1 in its F token (from the dry sizing), part 2 in C4_PART_01 (from its ci/parts
    file), then the assembly merges them into C33_<run>.json with the unsplit bounds."""
    tmp, _ = sandbox
    import campaign33_resize as RS
    from skqd.campaign33 import assemble as AS
    fa = tmp / "C4_FCELLS_A.json"
    json.dump({"data": {"ladder": {"points": [{"mode": "cpu", "chunk": 16, "seconds": 16.0, "success": True,
                                               "gpu_memory_bytes_model": 2.7e8}], "fastest_mode": "cpu"},
                        "cells_dropped": [], "run": {"ci": {}}}}, open(fa, "w"))
    out = RS.build(str(fa), str(tmp / "none.json"), dry=True, force_parts=2, runs_only=["F4_B0a"])
    sizing = tmp / "sizing_33a.json"
    RS.write(out, str(sizing), str(tmp / "parts"))
    monkeypatch.setattr(TR, "sizing_path", lambda dry: str(sizing))
    monkeypatch.setattr(AS, "ROOT", str(tmp))
    assert out["runs"]["F4_B0a"]["parts"] == 2 and out["slots"]["C4_PART_01"]["run"] == "F4_B0a"
    rc1 = run_dry("C4_F4_B0a")
    p1 = json.load(open(tmp / "validation" / "dryrun" / "C4_F4_B0a.json"))
    assert rc1 == 0 and p1["data"]["frun"]["part"]["part"] == 1 and p1["data"]["frun"]["full"]
    rc2 = run_dry("C4_PART_01", ["--parts-file", str(tmp / "parts" / "C4_PART_01.json")])
    p2 = json.load(open(tmp / "validation" / "dryrun" / "C4_PART_01.json"))
    copy = json.load(open(tmp / "validation" / "dryrun" / "C33_F4_B0a_part2of2.json"))
    assert rc2 == 0 and p2["status"] == "PASS" and copy == p2, [c for c in p2["criteria"] if not c["passed"]]
    assert p2["data"]["frun"]["part"]["part"] == 2
    split, _P = AS.assemble_split_runs(True)
    assert split["F4_B0a"]["status"] == "PASS", split
    m = json.load(open(tmp / "validation" / "dryrun" / "C33_F4_B0a.json"))
    plan = m["data"]["plan_shots_by_circuit"]
    ch = out["runs"]["F4_B0a"]["part_descriptors"][0]["chunk"]
    for c, n in plan.items():
        assert m["data"]["bounds"][c] == [0] + [int(x) for x in np.cumsum([s for _a, s in SM.chunk_plan(n, ch)])]
    assert m["data"]["frun"]["E_tol"]["value"] == p1["data"]["frun"]["E_tol"]["value"]
    assert len(m["data"]["parts"]) == 2 and any(c["name"].startswith("P13") for c in m["criteria"])


def test_slot_without_content_fails_honestly(sandbox):
    tmp, _ = sandbox
    rc = run_dry("C4_PART_20", ["--parts-file", str(tmp / "absent.json")])
    d = json.load(open(tmp / "validation" / "dryrun" / "C4_PART_20.json"))
    assert rc == 1 and d["status"] == "FAIL"
    assert any(c["name"].startswith("P0 slot content present") and not c["passed"] for c in d["criteria"])
    assert TK.is_slot("C4_PART_20")

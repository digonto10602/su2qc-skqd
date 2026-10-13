"""prompts/35: the lattice driver scripts/quantinuum_lattice_tests.py (tiers T2-T6, QV_2x4) -- structure, the
2x2 sizes and rules, the E7 matched-f scenario at the 2x2 counts, the Pecos engine with circuit_dir / ids and the
Guppy/HUGR route.  The pecos and HUGR tests run only in ~/.local/share/su2qc-pecos/venv and skip elsewhere with
that reason; the frozen 2x2 family (data/quantinuum/circuits_2x2) must exist."""
import importlib.util
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import quantinuum_lattice_tests as Q  # noqa: E402

HAVE_FAMILY = os.path.exists(os.path.join(ROOT, "data", "quantinuum", "circuits_2x2", "index.json"))
needs_family = pytest.mark.skipif(not HAVE_FAMILY, reason="the frozen 2x2 family is not built (prompts/35 3.2)")
HAVE_PECOS = importlib.util.find_spec("pytket_pecos") is not None
HAVE_GUPPY = importlib.util.find_spec("guppylang") is not None and importlib.util.find_spec("selene_sim") is not None
VENV_REASON = ("needs the isolated venv ~/.local/share/su2qc-pecos/venv (pytket-pecos, guppylang, selene-sim; "
               "prompts/35: nothing is installed into `coding`)")


def test_driver_tiers_scenarios_and_seed_rules():
    ap_tiers = ("export", "noiseless", "noise", "pecos", "hugr", "gpu-verify", "assemble")
    with pytest.raises(SystemExit):
        Q.main(["--lattice", "2", "--tier", "nonsense"])
    for t in ap_tiers:
        assert t in open(Q.__file__).read()
    assert len(Q.SCENARIOS) == 11 and sorted(Q.POR_ORDER) == sorted(Q.SCENARIOS)
    assert Q.POR_ORDER[:5] == ("E1", "E3", "E4", "E5b", "E7_0.10_lat")          # prompts/35 3.5 order
    seeds = {Q.SEED_T2, Q.SEED_T4, Q.SEED_FC, Q.SEED_POR, Q.SEED_QV, Q.SEED_T6}
    assert len(seeds) == 6 and Q.SEED_T2 == 35_000_000 and Q.SEED_T4 == 35_100_000
    # seed ranges never overlap: T2 uses 1000 c + chunk for c < 28, T3 uses 1000 s + c for s < 11, c < 28
    assert Q.SEED_T2 + 1000 * 27 + 999 < Q.SEED_T4 and Q.SEED_FC + 1000 * 10 + 27 < Q.SEED_POR < Q.SEED_QV
    assert (Q.N_T2, Q.N_FCELL, Q.N_SIGMA, Q.P_MIN, Q.QV_SHOTS) == (20000, 2000, 5.0, 1e-3, 6250)


@needs_family
def test_2x2_family_plan_of_record_and_sector_sizes():
    idx, mans, cals = Q.family(2)
    assert len(idx["circuits"]) == 28 and sorted(cals) == ["CAL_x0", "CAL_zeros"]
    plan = Q.plan_of_record()
    assert sorted(plan) == sorted(idx["circuits"]) and sum(plan.values()) == 133907
    P = Q.Phys(2)
    assert P.n == 12 and P.sector[0]["dim"] == 38 and P.sector[2]["dim"] == 20
    import gate_H0_2x2 as H
    assert P.sector[0]["a"] == H.E2_ACCEPTANCE[0] and P.sector[2]["a"] == H.E2_ACCEPTANCE[2]
    for cid in ("B0_ref06_k1", "B1_ref14_k4"):
        m = mans[cid]
        p = P.exact(m)
        assert abs(sum(p.values()) - 1.0) < 1e-12 and set(p) <= P.sector[int(m["twoB"])]["ints"]
        assert abs(p[int(m["reference_int"])] - m["p_reference"]) < 1e-12
    acc, rej = P.decode({int(mans["B0_ref06_k1"]["reference_int"]): 3, 1: 2}, 0)
    assert sum(acc.values()) == 3 and rej == 2


@needs_family
def test_e7_matched_f_uses_the_2x2_counts():
    from skqd.campaign33 import noise as N
    _idx, mans, _ = Q.family(2)
    spec = Q.spec_of("E7_0.10_lat", 12, mans, 2)
    mc = Q.mean_counts(mans)
    f = N.f_gate(spec.description["parameters"]["p2"], n2=mc["n2"], n1=mc["n1"], nm=mc["nm"])
    assert abs(f - 0.10) < 1e-12 and spec.description["id"] == "E7(0.10; 2x2 counts)"
    assert spec.description["parameters"]["p2"] > N.matched_f_eps2(0.10)      # fewer gates at 2x2 -> larger eps2


def test_hugr_shot_rule_stays_inside_the_cap():
    rt = {"seconds_per_shot": 0.085, "compile_s": 8.7, "selene_build_s": 8.3}
    n = Q.hugr_shots(rt, 2)
    assert n % 100 == 0 and 20 <= n <= 2000
    assert 28 * n * 0.085 + 29 * 17.0 <= 3600.0
    assert Q.hugr_shots({"seconds_per_shot": 1e-4, "compile_s": 1.0, "selene_build_s": 1.0}, 2) == 2000
    assert Q.hugr_shots({"seconds_per_shot": 100.0, "compile_s": 1.0, "selene_build_s": 1.0}, 3) == 20
    with pytest.raises(SystemExit):
        Q.hugr_shots(None, 2)


@needs_family
@pytest.mark.skipif(not HAVE_PECOS, reason=VENV_REASON)
def test_pecos_engine_takes_a_circuit_dir_and_ids():
    from skqd.campaign33 import engines as EN
    eng = EN.Pecos(circuit_dir=Q.circ_dir(2), ids=["CAL_x0", "B0_ref06_k1"])
    assert sorted(eng.circ) == ["B0_ref06_k1", "CAL_x0"]
    assert eng.run("CAL_x0", 3, 35) == {1: 3}                       # X on qubit 0 -> key 1 (bit k = c[k])
    _idx, mans, _ = Q.family(2)
    cnt = eng.run("B0_ref06_k1", 4, 36)
    assert sum(cnt.values()) == 4 and set(cnt) <= set(Q.Phys(2).exact(mans["B0_ref06_k1"]))
    default = EN.Pecos.__init__.__defaults__
    assert default == (None, None), "the C3_LE default (2x3 family, FCELL_SHOTS ids) is unchanged"


@needs_family
@pytest.mark.skipif(not HAVE_GUPPY, reason=VENV_REASON)
def test_guppy_hugr_selene_route_on_the_calibration_circuit(tmp_path):
    rec = Q.hugr_one(2, "CAL_x0", str(tmp_path), 4, 7)
    assert rec["ok"] and rec["counts"] == {"1": 4}, rec.get("selene_error")
    assert "tket.qsystem.helios" in rec["package_extensions"] and len(rec["hugr_sha256"]) == 64
    assert "status" in rec["hugr_to_pytket"]

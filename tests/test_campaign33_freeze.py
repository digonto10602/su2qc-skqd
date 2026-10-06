"""
prompts/33 A2: the frozen circuit families (data/campaign33/circuits/).

Every QPY header is version 13 (what qiskit 1.4.3 on the CI reads); every manifest's sha256 matches its
file; a round trip of one circuit per family equals the source instruction by instruction; the NAT-O0
conversion reproduces Q0P's Q1 numbers (ZZ 2158 on all 44, max |dpsi| < 1e-10, leakage < 1e-9); the
variant table lists counts and `allowed`; the base families are exact; the IBM families keep the per-qubit
operation order and T3 reproduces the flown K1 circuit; the qiskit 1.4.3 load check is recorded.
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from skqd.campaign33 import circuits as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
Q143 = os.path.expanduser("~/.local/share/su2qc-qiskit143/venv/bin/python")

pytestmark = pytest.mark.skipif(not os.path.exists(C.INDEX), reason="the freeze has not been run")


@pytest.fixture(scope="module")
def index():
    return C.load_index()


def test_every_family_is_complete(index):
    want = {"IR-L0": 44, "NAT-O0": 44, "NAT-O0-k5": 11, "NAT-O1": 44, "NAT-O2": 44, "NAT-O3": 44, "NAT-O4": 44,
            "NAT-O6": 44, "IR-L3-RZZ": 44, "IBM-T3": 2, "IBM-T0": 2, "IBM-U": 2}
    for fam, n in want.items():
        assert fam in index["families"], fam
        assert index["families"][fam]["n_circuits"] == n and index["families"][fam]["complete"], fam


def test_qpy_headers_and_sha256(index):
    for fam, f in index["families"].items():
        assert f["qpy_versions"] == [13], fam
        assert f["sha256_match"] and f["all_roundtrips_identical"], fam
        for cid in f["circuits"]:
            man = C.load_manifest(fam, cid)
            assert C.qpy_header(C.qpy_path(fam, cid))["qpy_version"] == 13
            assert C.sha256_file(C.qpy_path(fam, cid)) == man["qpy"]["gz_sha256"]


def test_round_trip_of_one_circuit_per_family_is_instruction_exact(index):
    for fam, f in index["families"].items():
        cid = f["circuits"][0]
        man = C.load_manifest(fam, cid)
        circ = C.load_circuit(fam, cid)
        assert C.ops_digest(circ) == man["ops_digest"], fam
        assert man["roundtrip"]["checks"]["instruction_by_instruction"] is True


def test_nat_o0_reproduces_q0p_q1(index):
    f = index["families"]["NAT-O0"]
    assert f["n_2q"] == {"min": 2158, "max": 2158, "mean": 2158.0}
    assert f["all_exact"] and f["max_abs_dpsi_max"] < 1e-10 and f["leakage_max"] < 1e-9
    for cid in f["circuits"]:
        man = C.load_manifest("NAT-O0", cid)
        q0p = json.load(open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x3", cid + ".manifest.json")))
        assert man["n_zz"] == q0p["counts"]["n_zz"] == 2158
        assert man["n_phasedx"] == q0p["counts"]["n_phasedx"]
        assert man["source_sha256"] == q0p["json_sha256"]


def test_base_families_are_exact(index):
    for fam in C.BASE_FAMILIES:
        assert index["base_families_exact"][fam] is True, fam
    for fam in ("IR-L0", "NAT-O0", "NAT-O0-k5", "IBM-T3", "IBM-T0", "IBM-U"):
        f = index["families"][fam]
        assert f["all_exact"] and f["max_abs_dpsi_max"] < 1e-10 and f["leakage_max"] < 1e-9, fam


def test_variant_table_lists_counts_and_allowed(index):
    v = index["variants"]
    assert set(v) == {"NAT-O0", "NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4", "NAT-O6"}
    for k, x in v.items():
        assert set(x) >= {"allowed", "status", "reason", "n_2q", "n_1q"}
        assert x["allowed"] == (index["families"][k]["all_exact"] and index["families"][k]["complete"]
                                and k != "NAT-O6")
    assert v["NAT-O0"]["allowed"] and not v["NAT-O6"]["allowed"]
    allowed = [k for k, x in v.items() if x["allowed"]]
    best = sorted(allowed, key=lambda k: (v[k]["n_2q"]["mean"], v[k]["n_1q"]["mean"], k))[0]
    assert index["chosen_variant"] == best


def test_ibm_families_keep_the_operation_order_and_reproduce_t3():
    for cid in ("B0_ref117_k1", "B1_ref29_k1"):
        for fam in ("IBM-T3", "IBM-T0", "IBM-U"):
            man = C.load_manifest(fam, cid)
            assert all(man["per_qubit_order_checks"].values()), (fam, cid)
            assert man["rebuild"]["dd_variant_reproduces_T3"] is True
            assert man["source_qpy_header"]["qpy_version"] == 17, "the K1 files were QPY 17 (unreadable by 1.4.3)"
            assert man["qpy"]["header"]["qpy_version"] == 13
        t0 = C.load_manifest("IBM-T0", cid)
        assert abs(t0["durations_s"]["T0"] - t0["durations_s"]["T3"]) < 1e-12, "pulses replaced by equal delays"
        assert "delay" not in C.load_manifest("IBM-U", cid)["counts"]["ops"]


def test_ir_l3_rzz_exactness_is_recorded(index):
    f = index["families"]["IR-L3-RZZ"]
    assert f["n_circuits"] == 44 and isinstance(f["all_exact"], bool)
    for cid in f["circuits"][:3]:
        man = C.load_manifest("IR-L3-RZZ", cid)
        assert man["transpile"] == {"basis_gates": ["rz", "rx", "ry", "rzz"], "coupling_map": None,
                                    "optimization_level": 3, "seed_transpiler": 7}


def test_quantum_info_cross_check_per_family(index):
    for fam in ("IR-L0", "NAT-O0", "NAT-O1", "NAT-O2", "NAT-O3", "NAT-O4", "IR-L3-RZZ"):
        qi = index["families"][fam]["quantum_info_cross_check"]
        assert qi is not None, fam
        assert qi["max_abs_diff_aer_vs_quantum_info"] < 1e-10, fam


def test_qiskit_143_load_check_recorded():
    p = os.path.join(C.CIRC_DIR, "check_qiskit143.json")
    assert os.path.exists(p), "run the check143 stage under qiskit 1.4.3"
    d = json.load(open(p))
    assert d["qiskit"] == "1.4.3" and d["qiskit_aer"] == "0.15.1" and d["all_ok"]
    assert set(d["families"]) == set(C.load_index()["families"])


@pytest.mark.skipif(not os.path.exists(Q143), reason="no qiskit 1.4.3 venv on this machine")
def test_qiskit_143_loads_a_frozen_circuit_live():
    code = ("import sys; sys.path.insert(0, 'src'); from skqd.campaign33 import circuits as C; "
            "c = C.load_circuit('IBM-T0', 'B0_ref117_k1'); m = C.load_manifest('IBM-T0', 'B0_ref117_k1'); "
            "import qiskit; assert qiskit.__version__ == '1.4.3'; assert C.ops_digest(c) == m['ops_digest']; print('ok')")
    r = subprocess.run([Q143, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and r.stdout.strip() == "ok", r.stderr[-2000:]

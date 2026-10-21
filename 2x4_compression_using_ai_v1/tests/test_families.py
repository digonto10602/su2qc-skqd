"""The family loader API (notes/009): frozen files load, hashes re-check, qiskit conversion preserves the gate list,
and one class-B circuit per frozen 2x4 family reproduces the package's exact coarse state through the loaded IR."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from c2x4.families import (ALIASES, available_families, exact_target, family_header, get_family,   # noqa: E402
                           get_family_ir)


def test_aliases_point_to_v1():
    for a, n in ALIASES.items():
        assert n.endswith("_v1") and n.startswith(a)


@pytest.mark.parametrize("name", available_families())
def test_family_loads_and_counts_match(name):
    hdr = family_header(name)
    fam = get_family(name)
    assert len(fam) == hdr["n_circuits"]
    for cid, qc, md in fam:
        n2 = sum(1 for ins in qc.data if ins.operation.num_qubits == 2)
        assert n2 == md["n_2q"], cid
        assert all(ins.operation.num_qubits <= 2 for ins in qc.data)
        assert qc.num_qubits == md["n_qubits"]
        assert md["verification"]["pass"]


@pytest.mark.parametrize("name", [n for n in available_families() if "2x4" in n])
def test_one_circuit_state(name):
    from c2x4.evaluate import certified_state_check
    rows = get_family_ir(name)
    cid, g, md = [r for r in rows if r[0] == "B1_ref230_k1"][0]
    ints, tgt = exact_target(md)
    r = certified_state_check(g, md["n_qubits"], ints, tgt * np.exp(1j * md["global_phase_vs_target"]))
    assert r["pass"], r

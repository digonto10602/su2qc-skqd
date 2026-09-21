"""Unit tests for the H0 session scripts (prompts/15 part A).

Nothing here touches a QPU or an IBM account: the live path of `resolve_backend` is
exercised with a stubbed `open_service`, everything else runs on the FakeFez
calibration snapshot that ships with qiskit-ibm-runtime.
"""
import os
import sys

import pytest

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import h0_backends  # noqa: E402
import h0_qpu_time  # noqa: E402


# --------------------------------------------------------------------- name routing
def test_is_fake_names():
    assert h0_backends.is_fake("FakeFez")
    assert h0_backends.is_fake("FakeTorino")
    assert not h0_backends.is_fake("ibm_fez")
    assert not h0_backends.is_fake("ibm_marrakesh")


def test_resolve_backend_fake_names_need_no_account():
    b = h0_backends.resolve_backend("FakeFez")
    assert b.num_qubits == 156
    assert "cz" in b.target.operation_names


def test_resolve_backend_live_name_goes_through_the_service(monkeypatch):
    """Any name that is not a snapshot must be looked up on the account, not guessed."""
    calls = {}

    class _Service:
        def backend(self, name):
            calls["name"] = name
            return f"live backend {name}"

        def backends(self):
            return []

    import ibm_account
    monkeypatch.setattr(ibm_account, "open_service", lambda: _Service())
    assert h0_backends.resolve_backend("ibm_fez") == "live backend ibm_fez"
    assert calls["name"] == "ibm_fez"


def test_resolve_backend_unreachable_name_is_a_clean_exit(monkeypatch):
    class _Service:
        def backend(self, name):
            raise ValueError("no such backend")

        def backends(self):
            return []

    import ibm_account
    monkeypatch.setattr(ibm_account, "open_service", lambda: _Service())
    with pytest.raises(SystemExit):
        h0_backends.resolve_backend("ibm_nonexistent")


# --------------------------------------------------------------------- calibration record
def test_calibration_stamp_is_utc():
    assert h0_backends.calibration_stamp("2025-02-26T15:16:25-05:00") == "20250226T2016Z"
    assert h0_backends.calibration_stamp("2026-09-21T14:23:42+00:00") == "20260921T1423Z"


def test_calibration_record_on_the_snapshot_has_no_missing_errors():
    b = h0_backends.resolve_backend("FakeFez")
    edges = [e for e in b.coupling_map][:6]
    qubits = sorted({q for e in edges for q in e})
    rec = h0_backends.calibration_record(b, qubits, edges)
    assert rec["missing_errors"] == []
    assert rec["n_qubits_frozen_set"] == len(qubits)
    assert rec["last_update_date"] is not None
    assert rec["stamp"] == h0_backends.calibration_stamp(rec["last_update_date"])
    for q in qubits:
        e = rec["qubits"][str(q)]
        assert 0.0 <= e["measure_error"] <= 1.0
        assert e["measure_duration_s"] > 0
        assert e["T1_s"] > 0 and e["T2_s"] > 0
    for v in rec["edges"].values():
        assert 0.0 <= v["cz_error"] <= 1.0
        assert v["cz_duration_s"] > 0


def test_calibration_record_reports_a_none_error_instead_of_defaulting():
    """A None error must be listed in missing_errors: gate_H0P turns that into a stop."""
    b = h0_backends.resolve_backend("FakeFez")
    edge = tuple(next(iter(b.coupling_map)))
    key = h0_backends._cz_key(b.target, edge)
    props = b.target["cz"][key]
    saved = props.error
    try:
        props.error = None
        rec = h0_backends.calibration_record(b, list(edge), [edge])
        assert {"instruction": "cz", "qubits": [int(edge[0]), int(edge[1])]} in rec["missing_errors"]
        assert rec["edges"][f"{min(edge)}-{max(edge)}"]["cz_error"] is None
    finally:
        props.error = saved


# --------------------------------------------------------------------- ASAP schedule
def test_circuit_duration_is_the_asap_critical_path():
    from qiskit import QuantumCircuit

    b = h0_backends.resolve_backend("FakeFez")
    t = b.target
    d = t.durations()
    qc = QuantumCircuit(3, 3)
    qc.sx(0)
    qc.sx(1)          # parallel with the first: does not add to the critical path
    qc.sx(0)          # in series on qubit 0
    qc.measure([0, 1, 2], [0, 1, 2])
    sx0 = t["sx"][(0,)].duration
    sx1 = t["sx"][(1,)].duration
    m = max(t["measure"][(q,)].duration for q in (0, 1, 2))
    got = h0_qpu_time.circuit_duration_s(qc, d, t)
    assert got == pytest.approx(max(2 * sx0 + t["measure"][(0,)].duration,
                                    sx1 + t["measure"][(1,)].duration,
                                    m), rel=1e-12)


def test_rz_and_barrier_cost_no_time():
    from qiskit import QuantumCircuit

    b = h0_backends.resolve_backend("FakeFez")
    t, d = b.target, b.target.durations()
    qc = QuantumCircuit(1, 1)
    qc.rz(0.3, 0)
    qc.barrier()
    qc.rz(0.7, 0)
    assert h0_qpu_time.circuit_duration_s(qc, d, t) == 0.0


# --------------------------------------------------------------------- gate_H0 guards
def test_error_ratios_guard_a_zero_measured_error():
    import gate_H0

    ratio, worst, zeros = gate_H0.error_ratios([0.0, 0.02, 0.005], [0.01, 0.01, 0.01])
    assert zeros == [0]                       # no error event on that qubit
    assert ratio[0] is None                   # 1/0 is not a drift factor
    assert worst == pytest.approx(2.0)        # max(2.0, 1/0.5)
    assert ratio[1] == pytest.approx(2.0)


def test_error_ratios_without_any_event_has_no_worst_ratio():
    import gate_H0

    ratio, worst, zeros = gate_H0.error_ratios([0.0, 0.0], [0.01, 0.01])
    assert worst is None and zeros == [0, 1] and ratio == [None, None]


def test_error_ratios_ignores_a_zero_reference():
    import gate_H0

    ratio, worst, zeros = gate_H0.error_ratios([0.02, 0.01], [0.0, 0.01])
    assert ratio[0] is None and zeros == []
    assert worst == pytest.approx(1.0)

"""
The Perlmutter CI passes only a gate token and runs `python scripts/run_gate.py L4` with no
arguments, so gate L4 has to recognise the CI itself and switch to the GPU.  These tests pin that
detection and check that the CPU path is bit-for-bit unchanged when the GPU option is requested on
a machine without one (the laptop: qiskit 2.5.2 + aer 0.17.2, CPU only).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from laptop_L4_aer_noise import ci_context, qiskit_versions  # noqa: E402


def _env(monkeypatch, **kw):
    for k in ("CI_GATE", "SLURM_JOB_ID", "SLURM_JOB_NODELIST"):
        monkeypatch.delenv(k, raising=False)
    for k, v in kw.items():
        monkeypatch.setenv(k, v)


def test_ci_context_empty_on_a_laptop(monkeypatch):
    _env(monkeypatch)
    assert ci_context() == {}


def test_ci_context_detects_the_poller_and_slurm(monkeypatch):
    _env(monkeypatch, CI_GATE="L4")
    assert ci_context() == {"CI_GATE": "L4"}
    _env(monkeypatch, SLURM_JOB_ID="58717267")
    assert ci_context() == {"SLURM_JOB_ID": "58717267"}
    # the nodelist alone is not a CI run: it is recorded, never used as the trigger
    _env(monkeypatch, SLURM_JOB_NODELIST="nid001234")
    assert ci_context() == {}


def test_ci_context_records_the_nodelist_when_present(monkeypatch):
    _env(monkeypatch, CI_GATE="L4", SLURM_JOB_ID="58717267", SLURM_JOB_NODELIST="nid001234")
    assert ci_context() == {"CI_GATE": "L4", "SLURM_JOB_ID": "58717267",
                            "SLURM_JOB_NODELIST": "nid001234"}


def test_qiskit_versions_are_recorded():
    v = qiskit_versions()
    assert set(v) == {"qiskit", "qiskit_aer"}
    # the CI runs qiskit 1.4.3, the laptop 2.5.2; both must be reported, not guessed
    assert all(isinstance(x, str) and x for x in v.values())


def test_batched_shots_gpu_is_ignored_on_the_cpu():
    """The option reaches AerSimulator only when device='GPU', so a CPU run is unchanged."""
    from skqd.circuits_ir import CircuitFactory
    from skqd.codec import Codec
    from skqd.exact import Model
    from skqd import circuits_qiskit as cq

    M = Model(2)
    g2 = 4.0
    F = CircuitFactory(M, g2)
    n = Codec(M.basis).n_qubits
    ref = M.reference(g2, 0)
    from skqd.krylov import references

    g = F.coarse_step(references(M.basis, 0)[0], 1, ref.dt)
    nm = cq.generic_noise_model(3e-4, 3e-3, 1e-2)
    a = cq.sample(g, n, 64, noise_model=nm, device="CPU", batched_shots_gpu=False)
    b = cq.sample(g, n, 64, noise_model=nm, device="CPU", batched_shots_gpu=True)
    assert a == b, "the CPU path must not see batched_shots_gpu"

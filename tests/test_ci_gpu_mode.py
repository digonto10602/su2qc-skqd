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


# ---------------------------------------------------------------------------------------------
# sample_many: one AerSimulator.run([...]) call for many circuits (RUNBOOK.md HPC policy).
# The refactor is safe only if the batched call executes the same circuits and puts each
# circuit's counts in its own slot, so that is what these tests pin.
# ---------------------------------------------------------------------------------------------
def _sector_circuits(k_list=(1, 2), n_refs=2):
    from skqd.circuits_ir import CircuitFactory
    from skqd.codec import Codec
    from skqd.exact import Model
    from skqd.krylov import references

    M = Model(2)
    g2 = 4.0
    F = CircuitFactory(M, g2)
    n = Codec(M.basis).n_qubits
    ref = M.reference(g2, 0)
    refs = references(M.basis, 0)[:n_refs]
    return [F.coarse_step(r, k, ref.dt) for r in refs for k in k_list], n, M


def test_sample_many_of_one_circuit_equals_sample():
    """Exact equality, with the noise model on: a batch of one is a single run of one."""
    from skqd import circuits_qiskit as cq

    gs, n, _ = _sector_circuits(k_list=(1, 2), n_refs=1)
    nm = cq.generic_noise_model(3e-4, 3e-3, 1e-2)
    for g in gs:
        a = cq.sample(g, n, 48, noise_model=nm, seed=11)
        b = cq.sample_many([g], n, 48, noise_model=nm, seed=11)[0]
        assert a == b, "sample_many([g]) must reproduce sample(g) bit-for-bit"


def test_sample_many_matches_a_sample_loop_for_deterministic_circuits():
    """Many circuits in one run() call: same counts as the per-circuit loop, in the same order.

    Circuits whose outcome is deterministic (X preparations on different qubits, no noise) make
    the comparison exact and would expose any mis-ordering of the batched results.  For a NOISY
    batch bit-for-bit equality is impossible: Aer derives a separate RNG stream per experiment
    from the single seed_simulator, so only the first experiment reproduces a lone sample() call
    (measured on the laptop, aer 0.17.2).  That is a sampling-seed difference, not a physics
    difference; the statistical check below covers it."""
    from skqd import circuits_qiskit as cq

    _, n, _ = _sector_circuits()
    dets = [[("x", (q,), None)] for q in (0, 3, 7, 11)]
    loop = [cq.sample(d, n, 16, seed=11) for d in dets]
    batched = cq.sample_many(dets, n, 16, seed=11)
    assert loop == batched
    for q, counts in zip((0, 3, 7, 11), batched):
        bits = list(counts)[0]
        assert counts == {bits: 16} and bits[q] == 1 and sum(bits) == 1


def test_sample_many_is_reproducible_and_statistically_matches_the_loop():
    """Same seed twice -> same counts; and the decoded yield of the batched call agrees with the
    per-circuit loop within the binomial spread of the shot count used here."""
    from skqd.codec import Codec
    from skqd import circuits_qiskit as cq

    gs, n, M = _sector_circuits(k_list=(1, 2), n_refs=2)
    codec = Codec(M.basis)
    nm = cq.generic_noise_model(3e-4, 3e-3, 1e-2)
    shots = 96
    b1 = cq.sample_many(gs, n, shots, noise_model=nm, seed=11)
    b2 = cq.sample_many(gs, n, shots, noise_model=nm, seed=11)
    assert b1 == b2, "sample_many must be reproducible at a fixed seed"
    assert all(sum(c.values()) == shots for c in b1)
    assert len(b1) == len(gs)
    loop = [cq.sample(g, n, shots, noise_model=nm, seed=11) for g in gs]

    def yield_of(counts_list):
        acc = tot = 0
        for c in counts_list:
            a, _ = codec.decode_counts(c, target_twoB=0)
            acc += sum(a.values())
            tot += sum(c.values())
        return acc / tot

    yb, yl = yield_of(b1), yield_of(loop)
    # 4 x 96 = 384 shots per path: 1 sigma on a yield near 0.9 is about 0.015, so 0.15 is ~10 sigma
    assert abs(yb - yl) < 0.15, f"batched yield {yb} vs loop {yl}"


def test_gpu_telemetry_is_null_without_a_file_and_parses_the_sampler_output(tmp_path):
    """The nvidia-smi sampler of jobs/gate.sbatch, read back by the gate."""
    from laptop_L4_aer_noise import gpu_telemetry

    missing = gpu_telemetry(str(tmp_path / "nothing.csv"))
    assert missing["samples"] == 0
    assert missing["peak_memory_mib"] is None and missing["mean_utilization_pct"] is None

    p = tmp_path / "gpu_telemetry.csv"
    p.write_text("1758000000,30,1000\n1758000010,70,2500\n")
    t = gpu_telemetry(str(p))
    assert t["samples"] == 2 and t["peak_memory_mib"] == 2500.0
    assert t["mean_utilization_pct"] == 50.0 and t["max_utilization_pct"] == 70.0

    # nvidia-smi with its header and units (--format=csv without noheader,nounits)
    p2 = tmp_path / "with_units.csv"
    p2.write_text("utilization.gpu [%], memory.used [MiB]\n40 %, 1024 MiB\n60 %, 2048 MiB\n")
    t2 = gpu_telemetry(str(p2))
    assert t2["samples"] == 2 and t2["peak_memory_mib"] == 2048.0
    assert t2["mean_utilization_pct"] == 50.0


def test_slurm_layout_reads_the_job_environment(monkeypatch):
    from laptop_L4_aer_noise import slurm_layout

    for k in ("SLURM_GPUS_PER_TASK", "SLURM_NTASKS", "SLURM_PROCID", "SLURM_CPUS_PER_TASK",
              "SLURM_JOB_NODELIST"):
        monkeypatch.delenv(k, raising=False)
    empty = slurm_layout()
    assert all(v is None for v in empty.values())
    monkeypatch.setenv("SLURM_GPUS_PER_TASK", "1")
    monkeypatch.setenv("SLURM_NTASKS", "1")
    monkeypatch.setenv("SLURM_PROCID", "0")
    monkeypatch.setenv("SLURM_CPUS_PER_TASK", "32")
    monkeypatch.setenv("SLURM_JOB_NODELIST", "nid001234")
    assert slurm_layout() == {"gpus_per_task": 1, "tasks": 1, "rank": 0, "cpus_per_task": 32,
                              "nodelist": "nid001234"}


def test_gpu_only_options_never_reach_a_cpu_simulator():
    """cuStateVec_enable, batched_shots_gpu, precision and the policy's method="statevector" are
    GPU-only: on the CPU the simulator must be exactly what it was before the policy change."""
    from skqd import circuits_qiskit as cq

    cpu = cq._aer_simulator(device="CPU", batched_shots_gpu=True, cu_statevec_enable=True,
                            precision="single", seed=11)
    assert cpu.options.device == "CPU"
    assert cpu.options.method == "automatic"
    assert cpu.options.batched_shots_gpu is False
    assert cpu.options.cuStateVec_enable is False
    assert cpu.options.precision == "double"


def test_s2d_shot_quota_is_read_from_the_data_file():
    """The full-size extrapolation in the report uses the quota in data/S2D_recall_at_f.json,
    never a hard-coded shot count."""
    import json
    import os

    from laptop_L4_aer_noise import s2d_shots_per_sector

    q = s2d_shots_per_sector()
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "data", "S2D_recall_at_f.json")) as fh:
        e = next(iter(json.load(fh)["results"].values()))
    assert q == e["circuits"] * e["shots_per_circuit"]


def test_gpu_option_set_is_the_policy_one():
    """The policy fixes AerSimulator(method="statevector", device="GPU", cuStateVec_enable=True,
    batched_shots_gpu=True) for noisy shot sampling (RUNBOOK.md).  There is no GPU on this
    laptop, so the option set itself is what is checked here -- `_aer_options` builds it without
    touching qiskit; the simulator that consumes it is only exercised on Perlmutter."""
    from skqd import circuits_qiskit as cq

    gpu = cq._aer_options(device="GPU", batched_shots_gpu=True, seed=11)
    assert gpu == {"method": "statevector", "device": "GPU", "seed_simulator": 11,
                   "batched_shots_gpu": True, "cuStateVec_enable": True}
    # precision stays double unless a tolerance check justifies single, and is then explicit
    assert "precision" not in gpu
    assert cq._aer_options(device="GPU", precision="single")["precision"] == "single"
    # an explicit method is never overridden by the policy default
    assert cq._aer_options(device="GPU", method="density_matrix")["method"] == "density_matrix"
    # the CPU path carries none of it
    assert cq._aer_options(device="CPU", batched_shots_gpu=True, cu_statevec_enable=True,
                           precision="single", seed=11) == {"method": "automatic",
                                                            "device": "CPU",
                                                            "seed_simulator": 11}

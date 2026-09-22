"""
Gate S3 on the Perlmutter CI: the self-detection, the 20-qubit timing ladder, the memory-aware
batching and the calibration criteria of `scripts/s3_device_model.py`.

The CI passes only the gate token (`srun python scripts/run_gate.py S3`, jobs/gate.sbatch), so the
script has to recognise the CI itself and size a reduced-size THROUGHPUT calibration; these tests
pin that, and pin that a calibration run can never be read as the S3 physics criterion.

What is NOT covered here: every GPU line.  This laptop has no usable qiskit-aer-gpu (aer-gpu 0.15.1
is incompatible with the pinned qiskit 2.5.2), so `device='GPU'`, `batched_shots_gpu`, the
cuStateVec options and the OOM-retry path of `sample_many` run only on Perlmutter.  The CPU tests
below exercise the same code with the chunking forced by `--max-shots-per-run`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import s3_device_model as s3  # noqa: E402
from skqd.circuits_qiskit import shot_chunk_for  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------------------------
# CI self-detection and the calibration defaults
# ---------------------------------------------------------------------------------------------
def test_laptop_defaults_are_unchanged_without_the_ci():
    a = s3.build_parser({}).parse_args([])
    assert a.calibration is False and a.ladder_auto is False
    assert a.timing_ladder == [] and a.budget_minutes == 0.0 and a.walltime_budget_s == 0.0
    assert a.tag == "run" and a.min_shots == 1 and a.device == "auto"
    assert a.shots_per_sector == s3.PRODUCTION_SHOTS_PER_SECTOR
    assert a.max_shots_per_run == 0, "no chunking is imposed off the GPU"


def test_ci_switches_to_the_reduced_size_calibration():
    """`python scripts/run_gate.py S3` with no arguments must be the calibration of prompts/18."""
    a = s3.build_parser({"CI_GATE": "S3"}).parse_args([])
    assert a.calibration is True and a.ladder_auto is True
    assert (a.lattice, a.sector, a.reps, a.kmax) == (3, 0, 1, 4), "one sector, one repetition"
    assert a.shots_per_sector == 3200.0, "a few thousand shots, not the 2e5 production quota"
    # run_gate.py kills a gate at its default --timeout 3600 s, so the budget has to be well
    # inside one hour even though the allowlist line is 04:00:00
    assert 0 < a.budget_minutes <= 45 and a.budget_minutes * 60 < 3600
    assert 0 < a.ladder_budget_minutes < a.budget_minutes
    assert 0 < a.walltime_budget_s < 3600
    assert a.tag == "", "the CI reads validation/S3.json, so the gate slot is the untagged one"


def test_explicit_arguments_win_over_the_ci_defaults():
    a = s3.build_parser({"SLURM_JOB_ID": "58741899"}).parse_args(
        ["--lattice", "2", "--shots-per-sector", "500", "--tag", "byhand"])
    assert (a.lattice, a.shots_per_sector, a.tag) == (2, 500.0, "byhand")
    assert a.calibration is True, "the rest of the CI defaults still apply"


def test_the_gate_slot_follows_the_tag():
    assert s3.gate_name_for("") == "S3", "what run_gate.py S3 reads"
    assert s3.gate_name_for("smoke") == "S3_smoke" and s3.gate_name_for("B0_r1") == "S3_B0_r1"


def test_run_gate_resolves_the_S3_token_to_this_job():
    """run_gate.py maps a token G to scripts/gate_G.py; scripts/gate_S3.py forwards to the job."""
    from run_gate import find_script

    assert os.path.basename(find_script("S3")) == "gate_S3.py"
    import gate_S3

    assert gate_S3.main is s3.main


# ---------------------------------------------------------------------------------------------
# The 20-qubit ladder and the memory model
# ---------------------------------------------------------------------------------------------
def test_the_chunk_at_20_qubits_is_the_reason_for_a_new_ladder():
    """476 shots per run() call for one 2x3 circuit inside the 8 GB model budget, against 122 070
    for one 2x2 circuit: gate L4's ladder cannot be reused."""
    assert shot_chunk_for(20, 1, 8e9) == 476
    assert shot_chunk_for(12, 1, 8e9) == 122070
    # the whole B=0 circuit set at 2x3 in one call is 14 shots per call -- the run is
    # chunk-dominated, which is what the calibration has to measure
    assert shot_chunk_for(20, 32, 8e9) == 14


def test_default_ladder_straddles_the_chunk_bound():
    c = shot_chunk_for(20, 1, 8e9)
    lad = s3.default_ladder(20, 8e9)
    assert lad == [c // 10, c // 2, c, 3 * c] == [47, 238, 476, 1428]
    assert sum(lad) < 2500, "the ladder itself must stay a small part of the calibration"
    assert lad[-1] > c and lad[0] < c, "points on both sides of the one-call bound"
    # it follows --gpu-memory-bytes rather than being written down
    assert s3.default_ladder(20, 2e9)[2] == shot_chunk_for(20, 1, 2e9)


def test_the_memory_model_factor_is_the_measured_one():
    """L4 job 58741899: 8.0 GB predicted for the 20 x 6103 chunk, 27915 MiB measured."""
    assert s3.MEASURED_MEMORY_MODEL_FACTOR == 3.5
    assert "must NOT be extrapolated" in s3.L4_SPEEDUP_NOTE


# ---------------------------------------------------------------------------------------------
# sample_many with pre-transpiled circuits (how the job hands its level-3 circuits to Aer)
# ---------------------------------------------------------------------------------------------
def test_sample_many_accepts_pre_transpiled_circuits():
    """The gate transpiles once at optimization level 3, counts the two-qubit gates and samples
    the SAME circuits; passing them in must give what transpiling inside sample_many gives."""
    from qiskit import transpile

    from skqd import circuits_qiskit as cq
    from skqd.circuits_ir import CircuitFactory
    from skqd.codec import Codec
    from skqd.exact import Model
    from skqd.krylov import references

    M = Model(2)
    g2 = 4.0
    F = CircuitFactory(M, g2)
    n = Codec(M.basis).n_qubits
    ref = M.reference(g2, 0)
    gs = [F.coarse_step(r, 1, ref.dt) for r in references(M.basis, 0)[:2]]
    basis = ["rz", "sx", "x", "cz"]
    tqs = [transpile(cq.ir_to_qiskit(g, n, measure=True), basis_gates=basis, coupling_map=None,
                     optimization_level=1, seed_transpiler=11) for g in gs]
    nm = cq.generic_noise_model(3e-4, 3e-3, 1e-2)
    a = cq.sample_many(gs, n, 32, noise_model=nm, seed=11, basis=basis)
    b = cq.sample_many(None, n, 32, noise_model=nm, seed=11, transpiled=tqs)
    assert a == b


def test_chunking_splits_the_run_calls_and_conserves_the_shots():
    """The chunked path (GPU on Perlmutter) forced on the CPU with max_shots_per_run."""
    from skqd import circuits_qiskit as cq

    dets = [[("x", (q,), None)] for q in (0, 3)]
    one, info1 = cq.sample_many(dets, 6, 24, seed=11, return_info=True)
    many, info2 = cq.sample_many(dets, 6, 24, seed=11, max_shots_per_run=5, return_info=True)
    assert info1["run_calls"] == 1 and info2["run_calls"] == 5   # ceil(24/5)
    assert all(sum(c.values()) == 24 for c in many)
    assert one == many, "deterministic circuits: chunking changes nothing but the seeds used"
    assert info2["seeds"] == [11, 12, 13, 14, 15], "base_seed + chunk index (HPC policy)"


# ---------------------------------------------------------------------------------------------
# A calibration run end to end (CPU, tiny): the criteria, the run block, the report
# ---------------------------------------------------------------------------------------------
def test_a_calibration_run_records_the_policy_block_and_never_claims_gate_S3(monkeypatch):
    tag = "pytest_tmp"
    jpath = os.path.join(ROOT, "validation", f"S3_{tag}.json")
    rpath = os.path.join(ROOT, "reports", f"S3_{tag}_device_model.md")
    argv = ["s3_device_model.py", "--lattice", "2", "--sector", "0", "--kmax", "1",
            "--shots-per-sector", "10", "--calibration", "--timing-ladder", "4", "8",
            "--max-shots-per-run", "3", "--min-shots", "1", "--walltime-budget-s", "100000",
            "--tag", tag]
    monkeypatch.setattr(sys, "argv", argv)
    try:
        assert s3.main() == 0
        d = json.load(open(jpath))
        data = d["data"]
        assert data["calibration"] is True
        assert "NOT EVALUATED" in data["gate_S3_criterion"]
        assert data["run_kind"].startswith("CALIBRATION")
        names = [c["name"] for c in d["criteria"]]
        assert all(nm.startswith("calibration:") for nm in names), names
        assert not any("recall" in nm for nm in names), "the S3 criterion must not be evaluated"
        run = data["run"]
        for key in ("engine", "device", "gpus", "tasks", "rank", "wall_seconds", "phases_s",
                    "gpu_telemetry", "versions", "seeds", "timing_ladder", "batching",
                    "gpu_node_hours", "parallel_efficiency_Ep", "shot_chunk_one_circuit"):
            assert key in run, key
        assert run["parallel_efficiency_Ep"] is None, "E(p) needs two task counts; never estimated"
        assert run["gpu_telemetry"]["peak_memory_mib"] is None, "no sampler file on a laptop"
        assert len(run["timing_ladder"]) == 2
        assert run["batching"]["run_calls"] == 1 and run["batching"]["max_shots_per_run"] == 3
        assert set(run["phases_s"]) == {"transpile_s", "ladder_s", "sampling_s", "analysis_s"}
        txt = open(rpath).read()
        assert "THROUGHPUT CALIBRATION, not gate S3" in txt
        assert "calibration criteria only" in txt

        # and the gate table can never present it as the physics gate
        from update_status import calibration_note

        assert "NOT evaluated" in calibration_note(d)
        assert calibration_note({"data": {"calibration": False}}) == ""
    finally:
        for p in (jpath, rpath):
            if os.path.exists(p):
                os.remove(p)


def test_a_tight_budget_degrades_instead_of_overrunning(monkeypatch):
    """Nothing in the job may run past its budget: the transpilation stops after half of it, the
    ladder skips points it cannot afford, and the shots fall back to --min-shots.  The CI budget
    is 40 minutes against run_gate.py's 3600 s timeout, so this is the safety net, not the plan."""
    tag = "pytest_tmp_budget"
    jpath = os.path.join(ROOT, "validation", f"S3_{tag}.json")
    rpath = os.path.join(ROOT, "reports", f"S3_{tag}_device_model.md")
    argv = ["s3_device_model.py", "--lattice", "2", "--sector", "0", "--kmax", "2",
            "--shots-per-sector", "100000", "--calibration", "--timing-ladder", "4",
            "--budget-minutes", "0.01", "--min-shots", "1", "--tag", tag]
    monkeypatch.setattr(sys, "argv", argv)
    try:
        s3.main()          # criteria may fail (no GPU, a one-point ladder); it must not overrun
        data = json.load(open(jpath))["data"]
        assert data["circuits_dropped_for_budget"] > 0
        assert data["n_circuits"] == len(data["per_circuit"]) < 10
        # how many shots survive depends on the machine's load, so pin the behaviour, not a
        # number: a request of 100 000 per sector must collapse to a handful
        assert data["shots_per_circuit"] >= 1
        assert data["shots_per_circuit"] < 100 < data["shots_per_circuit_requested"]
        assert "reduced from" in data["shots_per_circuit_reason"]
        assert data["run"]["timing_ladder_skipped_for_budget"] == [4]
        assert data["run"]["wall_seconds"] < 120
    finally:
        for p in (jpath, rpath):
            if os.path.exists(p):
                os.remove(p)

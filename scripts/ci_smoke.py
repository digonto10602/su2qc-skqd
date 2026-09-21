"""GPU smoke test for skqd-ci: is this node usable as the 'QPU' for SKQD sampling?

Checks, each recorded separately in validation/ci_smoke.json:
  qiskit_aer_gpu : 12-qubit GHZ + diagonal phases sampled on AerSimulator(device="GPU")
  cudaq_nvidia   : the same circuit on CUDA-Q's "nvidia" (cuStateVec) target
  aer_28q_memory : a 28-qubit state vector (2x4 ladder size) fits on one GPU
Diagonal RZ phases cannot move the computational-basis support, so only the two GHZ
bitstrings may appear; anything else means a broken simulator or wrong qubit order.
Usage: python scripts/ci_smoke.py [--cpu]   (--cpu lets you dry-run it on a laptop)
"""
import json, os, sys, time, traceback

N = 12                 # 2x2 plaquette register
SHOTS = 4000
T = 0.245              # pi/W for the 2x2 model (manual Table 1), used as a stand-in angle
GHZ = {"0" * N, "1" * N}
DEVICE = "CPU" if "--cpu" in sys.argv else "GPU"
out = {"jobid": os.environ.get("SLURM_JOB_ID"), "code_sha": os.environ.get("CI_CODE_SHA"),
       "request_sha": os.environ.get("CI_REQUEST_SHA"), "device": DEVICE, "checks": {}}


def check(name, fn):
    t0 = time.time()
    try:
        info = fn()
        out["checks"][name] = {"pass": True, **info}
    except Exception as exc:  # record, keep going
        out["checks"][name] = {"pass": False, "error": repr(exc),
                               "trace": traceback.format_exc()[-800:]}
    out["checks"][name]["seconds"] = round(time.time() - t0, 2)
    print(name, out["checks"][name]["pass"], flush=True)


def qiskit_aer():
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    qc = QuantumCircuit(N)
    qc.h(0)
    for i in range(N - 1):
        qc.cx(i, i + 1)
    for i in range(N):
        qc.rz(2 * T, i)
    qc.measure_all()
    sim = AerSimulator(method="statevector", device=DEVICE)
    counts = sim.run(transpile(qc, sim), shots=SHOTS).result().get_counts()
    assert set(counts) <= GHZ, f"unexpected bitstrings {sorted(set(counts) - GHZ)[:5]}"
    assert sum(counts.values()) == SHOTS
    return {"counts": counts, "devices": list(sim.available_devices())}


def cudaq_nvidia():
    import cudaq

    @cudaq.kernel
    def ghz_phases(n: int, t: float):
        q = cudaq.qvector(n)
        h(q[0])
        for i in range(n - 1):
            x.ctrl(q[i], q[i + 1])
        for i in range(n):
            rz(2.0 * t, q[i])

    cudaq.set_target("nvidia" if DEVICE == "GPU" else "qpp-cpu")
    res = cudaq.sample(ghz_phases, N, T, shots_count=SHOTS)
    counts = {k: v for k, v in res.items()}
    assert set(counts) <= GHZ, f"unexpected bitstrings {sorted(set(counts) - GHZ)[:5]}"
    assert sum(counts.values()) == SHOTS
    return {"counts": counts, "version": cudaq.__version__,
            "gpus": cudaq.num_available_gpus()}


def aer_28q():
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    n = 28 if DEVICE == "GPU" else 20
    qc = QuantumCircuit(n)
    qc.h(range(n))
    qc.measure_all()
    sim = AerSimulator(method="statevector", device=DEVICE)
    counts = sim.run(transpile(qc, sim), shots=1000).result().get_counts()
    return {"qubits": n, "distinct": len(counts)}


check("qiskit_aer_gpu", qiskit_aer)
check("cudaq_nvidia", cudaq_nvidia)
check("aer_28q_memory", aer_28q)
out["pass"] = all(c["pass"] for c in out["checks"].values())
os.makedirs("validation", exist_ok=True)
with open("validation/ci_smoke.json", "w") as f:
    json.dump(out, f, indent=1)
print("SMOKE", "PASS" if out["pass"] else "FAIL")
sys.exit(0 if out["pass"] else 1)

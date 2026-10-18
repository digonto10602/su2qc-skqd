#!/usr/bin/env python3
"""
Reproducer for the qiskit-aer GPU Kraus report (su2qc-skqd prompts/33f R5).  Self-contained: qiskit, qiskit-aer and
numpy only (written for qiskit 1.4.3 + qiskit-aer(-gpu) 0.15.1, the versions of the recorded jobs).

It loads the scheduled circuit (QPY), rebuilds the two noise models from their `NoiseModel.to_dict()` exports, appends
the thermal-relaxation pass on `Delay` that `to_dict()` does not carry (relaxation_pass.json; exactly what
`NoiseModel.from_backend` appends in aer 0.15.1), runs every requested arm with the seeds recorded in counts/ and prints
the mean Hamming weight of the measured bits per arm.  Where the recorded run used the same seed and chunk size, it
also says whether the counts are identical.

    python reproduce.py                                  # every arm, 64 shots each (GPU arms skipped without a GPU)
    python reproduce.py --arms kraus_cpu rm_cpu --shots 2 --threads 8      # the CPU smoke test (minutes per shot)
    python reproduce.py --arms kraus_gpu_cusv kraus_gpu_cusv_nofusion kraus_gpu_native rm_gpu_cusv --shots 256

Arms (the options are those of the recorded jobs):
    kraus_cpu / rm_cpu                 AerSimulator(method="statevector", precision="double", max_parallel_threads=T)
    kraus_gpu_cusv / rm_gpu_cusv       ... device="GPU", cuStateVec_enable=True,  batched_shots_gpu=False
    kraus_gpu_native                   ... device="GPU", cuStateVec_enable=False, batched_shots_gpu=False
    kraus_gpu_cusv_nofusion            ... device="GPU", cuStateVec_enable=True,  batched_shots_gpu=False, fusion_enable=False
Expected (recorded, see README.md): every *_cpu arm and rm_gpu_cusv near the same mean weight; the three kraus_gpu_*
arms lower than the CPU and different from each other.
"""
import argparse
import gzip
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CIRCUIT = "circuit_IBM-T0_B0_ref117_k1.qpy.gz"
ARMS = {
    "kraus_cpu": ("kraus", "CPU", {}),
    "rm_cpu": ("rm", "CPU", {}),
    "kraus_gpu_cusv": ("kraus", "GPU", {"cuStateVec_enable": True, "batched_shots_gpu": False}),
    "rm_gpu_cusv": ("rm", "GPU", {"cuStateVec_enable": True, "batched_shots_gpu": False}),
    "kraus_gpu_native": ("kraus", "GPU", {"cuStateVec_enable": False, "batched_shots_gpu": False}),
    "kraus_gpu_cusv_nofusion": ("kraus", "GPU", {"cuStateVec_enable": True, "batched_shots_gpu": False,
                                                 "fusion_enable": False}),
}
# the recorded run whose chunk seeds each arm reuses (counts/<file>.json)
RECORDED = {
    "kraus_cpu": "C2_KCHK_run2__kraus_cpu.json",
    "rm_cpu": "C2_KCHK_run2__rm_cpu.json",
    "kraus_gpu_cusv": "C2_KCHK_run1__kraus_gpu_cusv.json",
    "rm_gpu_cusv": "C2_KCHK_run1__rm_gpu_cusv.json",
    "kraus_gpu_native": "C2_KCHK_run1__kraus_gpu_native.json",
    "kraus_gpu_cusv_nofusion": "C2_KCHK_run1__kraus_gpu_cusv_nofusion.json",
}


def load_circuit():
    from qiskit import qpy
    with gzip.open(os.path.join(HERE, CIRCUIT), "rb") as fh:
        return qpy.load(fh)[0]


def _complex(x):
    """Invert AerJSONEncoder: a complex number was written as [re, im], so a matrix of them has a trailing axis of 2."""
    import numpy as np
    a = np.asarray(x, dtype=float)
    return a[..., 0] + 1j * a[..., 1]


def decode(noise_dict):
    """NoiseModel.to_dict(serializable=True) -> the form NoiseModel.from_dict reads (aer 0.15.1 does not invert its own
    serializable export: complex Kraus / unitary matrices come back with an extra axis and from_dict raises)."""
    for err in noise_dict.get("errors", []):
        if err.get("type") != "qerror":
            continue
        for circ in err.get("instructions", []):
            for inst in circ:
                if inst.get("name") == "kraus":
                    inst["params"] = [_complex(m) for m in inst["params"]]
                elif inst.get("name") == "unitary":
                    inst["params"] = [_complex(inst["params"][0])]
    return noise_dict


def load_model(rep):
    """NoiseModel.from_dict of the export plus the RelaxationNoisePass on Delay (custom passes are not in to_dict),
    and the original model's basis gates."""
    import warnings

    from qiskit.circuit import Delay
    from qiskit_aer.noise import NoiseModel
    from qiskit_aer.noise.passes import RelaxationNoisePass
    with gzip.open(os.path.join(HERE, f"noise_model_{rep}.json.gz"), "rt") as fh:
        d = decode(json.load(fh))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)      # from_dict is deprecated in 0.15 but still the loader
        nm = NoiseModel.from_dict(d)
    with open(os.path.join(HERE, "relaxation_pass.json")) as fh:
        p = json.load(fh)[rep]
    # the original model's basis gates (from_dict substitutes its defaults, and add_basis_gates ignores delay / measure;
    # there is no public setter in aer 0.15.1)
    nm._basis_gates = set(p["noise_model_basis_gates"])
    delay_pass = RelaxationNoisePass(t1s=p["t1_s"], t2s=p["t2_s"], dt=p["dt_s"], op_types=Delay,
                                     excited_state_populations=p["excited_state_populations"])
    nm._custom_noise_passes.append(delay_pass)       # what NoiseModel.from_backend does in aer 0.15.1
    return nm


def recorded_chunks(arm):
    path = os.path.join(HERE, "counts", RECORDED[arm])
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def weight_stats(counts, n_bits):
    """Mean Hamming weight of the measured bits with its standard error (per-shot spread), from {int: count}."""
    n = sum(counts.values())
    if n == 0:
        return {"shots": 0}
    w = {k: bin(k & ((1 << n_bits) - 1)).count("1") for k in counts}
    mean = sum(w[k] * v for k, v in counts.items()) / n
    var = sum(v * (w[k] - mean) ** 2 for k, v in counts.items()) / (n - 1) if n > 1 else 0.0
    return {"shots": n, "mean_hamming_weight": mean, "se": math.sqrt(var / n)}


def to_int(counts):
    out = {}
    for k, v in counts.items():
        s = str(k).replace(" ", "")
        x = int(s, 16) if s.startswith("0x") else int(s, 2)
        out[x] = out.get(x, 0) + int(v)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS))
    ap.add_argument("--shots", type=int, default=64, help="shots per arm")
    ap.add_argument("--chunk", type=int, default=0,
                    help="shots per run() call (0 = the recorded chunk size of the arm, which reuses its seeds)")
    ap.add_argument("--seed", type=int, default=None, help="base seed (default: the recorded chunk seeds)")
    ap.add_argument("--threads", type=int, default=0, help="CPU arms: max_parallel_threads (0 = Aer's default)")
    ap.add_argument("--out", default=None, help="write the per-arm results as JSON here")
    a = ap.parse_args(argv)

    import qiskit
    import qiskit_aer
    from qiskit_aer import AerSimulator
    print(f"qiskit {qiskit.__version__}, qiskit-aer {qiskit_aer.__version__}, python {sys.version.split()[0]}")
    devices = list(AerSimulator().available_devices())
    print(f"Aer devices: {devices}")
    circ = load_circuit()
    n_bits = circ.num_clbits
    print(f"circuit: {circ.num_qubits} qubits, {n_bits} clbits, {len(circ.data)} instructions")
    models = {}
    results = {}
    for arm in a.arms:
        rep, dev, opts = ARMS[arm]
        if dev == "GPU" and "GPU" not in devices:
            print(f"{arm}: SKIPPED -- no GPU device in this Aer build ({devices}); needs qiskit-aer-gpu and a GPU")
            results[arm] = {"skipped": "no GPU"}
            continue
        if rep not in models:
            t_b = time.time()
            models[rep] = load_model(rep)
            print(f"noise model {rep}: rebuilt from noise_model_{rep}.json.gz + relaxation_pass.json in "
                  f"{time.time() - t_b:.1f} s")
        kw = dict(method="statevector", precision="double", noise_model=models[rep])
        if dev == "GPU":
            kw.update(device="GPU", **opts)
        elif a.threads:
            kw["max_parallel_threads"] = a.threads
        sim = AerSimulator(**kw)
        rec = recorded_chunks(arm)
        rchunks = (rec or {}).get("chunks") or []
        chunk = a.chunk or (int(rchunks[0]["shots"]) if rchunks else 16)
        total, calls, identical = {}, [], []
        done, j = 0, 0
        t0 = time.time()
        while done < a.shots:
            k = min(chunk, a.shots - done)
            if a.seed is not None:
                seed = a.seed + done
            elif j < len(rchunks):
                seed = int(rchunks[j]["seed"])
            else:
                seed = int(rchunks[-1]["seed"]) + (j - len(rchunks) + 1) * chunk if rchunks else 12345 + done
            t_c = time.time()
            res = sim.run(circ, shots=k, seed_simulator=seed).result()
            if not res.success:
                raise RuntimeError(str(getattr(res, "status", "")))
            cnt = to_int(res.get_counts(0))
            for x, v in cnt.items():
                total[x] = total.get(x, 0) + v
            calls.append({"seed": seed, "shots": k, "seconds": time.time() - t_c,
                          "counts": {str(x): v for x, v in sorted(cnt.items())}})
            if a.seed is None and j < len(rchunks) and int(rchunks[j]["shots"]) == k:
                identical.append({str(x): int(v) for x, v in cnt.items()} ==
                                 {str(x): int(v) for x, v in rchunks[j]["counts"].items()})
            done += k
            j += 1
            print(f"  {arm}: call {j}, {k} shots, seed {seed}, {calls[-1]['seconds']:.1f} s", flush=True)
        st = weight_stats(total, n_bits)
        st.update({"seconds_per_shot": (time.time() - t0) / max(1, done), "calls": calls, "simulator_options":
                   {k: v for k, v in kw.items() if k != "noise_model"},
                   "identical_to_recorded_chunks": identical or None,
                   "recorded_source": RECORDED[arm] if rec else None,
                   "recorded_mean_hamming_weight_all_chunks": (rec or {}).get("mean_hamming_weight")})
        results[arm] = st
        same = ("; same seeds as the recorded run: counts identical in " + f"{sum(identical)} of {len(identical)} calls"
                if identical else "")
        print(f"{arm}: {st['shots']} shots, mean Hamming weight {st['mean_hamming_weight']:.3f} +- {st['se']:.3f}, "
              f"{st['seconds_per_shot']:.2f} s/shot{same}", flush=True)
    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"versions": {"qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
                                    "python": sys.version.split()[0]}, "devices": devices, "args": vars(a),
                       "arms": results}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

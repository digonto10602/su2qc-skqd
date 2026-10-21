"""C5: analytic clean-shot fraction f of every circuit under every device model (no sampling).

Usage: python analytic_f.py LATTICE FAMILY [DEVICE ...]   (FAMILY 'frozen' at 2x4 uses the committed native files)
Writes noise/data/results/<LATTICE>/<FAMILY>/<DEVICE>/analytic_f.json (rows per circuit + summary).

f       = P(no gate, idle or memory fault in the model) * (1 - mean readout error)^n      (the model's clean fraction)
f_gate  = P(no gate fault) only (1q and 2q gate channels; no idle/memory, no readout)
f_pkg   = (1 - r_2q)^N_2q (1 - r_1q)^N_1q (1 - eps_ro)^n  : the package's convention (skqd.device_req.clean_shot_fraction:
          published average infidelities used directly as fault probabilities, no angle scaling, no idle), kept so the
          numbers can be compared with reviews/001 (f = 0.5751 / 0.2006 on H2-2 with TKET counts).
"""
import os as _os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")   # one BLAS thread per job: the queue runs several jobs in parallel

import gzip
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits  # noqa: E402
import noise_models as nm  # noqa: E402
from provenance import provenance, dump  # noqa: E402

RES = os.path.join(circuits.NOISE, "data", "results")
ALL_DEVICES = list(nm.DEVICES)


def tags_of(lattice, family):
    if lattice == "2x4" and family in circuits.FAMILY_V1:
        return [circuits.tag(*x) for x in circuits.v1_ids()]
    if lattice == "2x3" and family == "frozen":
        return circuits.frozen_2x3_ids()
    raise KeyError((lattice, family))


def frozen_2x4_native(tag_source):
    """Frozen 2x4 native circuit from the committed Quantinuum-native QASM (gzip), as a qiskit circuit."""
    from qiskit import qasm2
    from qiskit.circuit.library import RGate, RZZGate
    import re
    p = os.path.join(circuits.ROOT, "data", "quantinuum", "circuits_2x4", tag_source + ".qasm.gz")
    src = gzip.open(p, "rt").read()
    src = src.replace('include "hqslib1.inc";', 'include "qelib1.inc";')
    src = re.sub(r"\bU1q\(", "rgate(", src)
    src = re.sub(r"\bRZZ\(", "rzzgate(", src)
    custom = list(qasm2.LEGACY_CUSTOM_INSTRUCTIONS) + [
        qasm2.CustomInstruction("rgate", 2, 1, RGate, builtin=True),
        qasm2.CustomInstruction("rzzgate", 1, 2, RZZGate, builtin=True)]
    qc = qasm2.loads(src, custom_instructions=custom)
    return qc.remove_final_measurements(inplace=False)


def f_pkg(bud, device, n):
    P = nm.params(device)
    p10, p01 = nm.readout_probs(device)
    n1 = bud["n_1q_pulses"]
    return (1 - P["p2"]) ** bud["n_2q"] * (1 - P["p1"]) ** n1 * (1 - 0.5 * (p10 + p01)) ** n


def row_for(nat, device, n, lay=None):
    a = nm.analytic_f(nat, device, n)
    b = a["budget"]
    r = {"f": a["f"], "f_gate_only": b["f_parts"]["gate_1q"] * b["f_parts"]["gate_2q"],
         "f_with_idle_no_readout": a["f_gate"], "f_readout_mean": a["f_readout"],
         "f_parts": b["f_parts"], "f_pkg": f_pkg(b, device, n),
         "n_2q": b["n_2q"], "n_1q_native": b["n_1q_native"], "n_1q_pulses": b["n_1q_pulses"],
         "n_rz_virtual": b["n_rz_virtual"], "n_events": b["n_events"],
         "n_active_qubits": b["n_active_qubits"], "duration_s": b.get("duration_s"),
         "depth1_equivalent_layers": b.get("depth1_equivalent_layers"),
         "depth_2q": nat.depth(filter_function=lambda ins: ins.operation.num_qubits == 2)}
    if lay is not None:
        r["n_physical_qubits"] = lay.get("n_physical")
    return r


def main():
    lattice, family = sys.argv[1], sys.argv[2]
    devices = sys.argv[3:] or ALL_DEVICES
    t0 = time.time()
    if lattice == "2x4" and family == "frozen":
        idx = json.load(open(os.path.join(circuits.ROOT, "data", "quantinuum", "circuits_2x4", "index.json")))
        tags = idx["circuits"]
        rows = {d: {} for d in devices}
        for t in tags:
            nat = frozen_2x4_native(t)
            for d in devices:
                kind = nm.params(d)["kind"]
                if kind == "ibm":
                    # no routing of a ~70 000-gate circuit: an upper bound with 2 CZ per RZZ, no SWAP, gate-only
                    P = nm.params(d)
                    n2 = sum(1 for ins in nat.data if ins.operation.num_qubits == 2)
                    n1 = sum(1 for ins in nat.data if ins.operation.name == "r")
                    fb = (1 - 1.25 * P["p2"]) ** (2 * n2) * (1 - 1.5 * P["p1"]) ** (2 * n1)
                    rows[d][t] = {"f_upper_bound_gate_only": fb, "assumption": "2 CZ per RZZ, 2 sx per PhasedX, no "
                                  "routing SWAPs, no idle, no readout: an upper bound on f", "n_rzz": n2, "n_phasedx": n1}
                else:
                    rows[d][t] = row_for(nat, d, nat.num_qubits)
            print(t, {d: rows[d][t].get("f", rows[d][t].get("f_upper_bound_gate_only")) for d in devices}, flush=True)
    else:
        tags = tags_of(lattice, family)
        rows = {d: {} for d in devices}
        for t in tags:
            qc = circuits.circuit(lattice, family, t)
            for d in devices:
                kind = nm.params(d)["kind"]
                nat, lay = nm.native_circuit(qc, kind, cache_key=f"{lattice}__{family}__{t}")
                rows[d][t] = row_for(nat, d, qc.num_qubits, lay)
            print(t, {d: round(rows[d][t]["f"], 5) for d in devices}, flush=True)
    for d in devices:
        R = rows[d]
        fs = [r["f"] for r in R.values() if "f" in r]
        summ = {"n_circuits": len(R)}
        if fs:
            summ.update({"f_min": min(fs), "f_max": max(fs), "f_mean": sum(fs) / len(fs),
                         "f_gate_only_mean": sum(r["f_gate_only"] for r in R.values()) / len(R),
                         "f_pkg_mean": sum(r["f_pkg"] for r in R.values()) / len(R),
                         "n_2q_min": min(r["n_2q"] for r in R.values()), "n_2q_max": max(r["n_2q"] for r in R.values()),
                         "n_2q_mean": sum(r["n_2q"] for r in R.values()) / len(R)})
        else:
            fb = [r["f_upper_bound_gate_only"] for r in R.values()]
            summ.update({"f_upper_bound_max": max(fb)})
        rec = {"test": "analytic_f", "lattice": lattice, "family": family, "device": d, "rows": R, "summary": summ,
               "definitions": __doc__, "noise_spec_file": os.path.relpath(nm.spec_path(d), circuits.NOISE),
               "noise_spec_sha256": nm.spec_sha256(d), "noise_model_params": nm.params(d),
               "runtime_s": time.time() - t0, "provenance": provenance()}
        dump(rec, os.path.join(RES, lattice, family, d, "analytic_f.json"))
    print("DONE", lattice, family, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

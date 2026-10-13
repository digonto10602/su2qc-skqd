#!/usr/bin/env python
"""
prompts/33c step 1(a) diagnostic: walk every `delay` of a physical qubit in the IBM-T0 circuit B0_ref117_k1 and
compare the QuantumError the RM model's relaxation pass attaches with the one the Kraus model's pass attaches
(SuperOp max |diff|, the error's probabilities, the delay duration in seconds), plus the closed-form
thermal-relaxation probabilities of each window.  Writes data/campaign33/c33c_diag/delays_q<q>_<stack>.json.

    python scripts/c33c_diag_delays.py --qubit 53
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")]
from c33c_diag_full import CID, OUT_DIR, provenance  # noqa: E402


def delay_errors(spec, circ, q):
    """[(delay seconds, QuantumError)] the spec's custom passes insert after every delay of physical qubit q."""
    from qiskit_aer.noise import QuantumError
    from skqd.campaign33 import noise as N
    qc = spec.noise_model._pass_manager().run(circ)
    out, prev = [], None
    for inst in qc.data:
        qs = [qc.find_bit(x).index for x in inst.qubits]
        if qs != [q]:
            continue
        op = inst.operation
        if op.name == "delay":
            prev = N.delay_seconds(inst, spec.dt)
            continue
        err = op if isinstance(op, QuantumError) else getattr(op, "_quantum_error", None)
        if err is not None:
            out.append((prev, err))
            prev = None
    return out


def error_probs(err) -> dict:
    d = err.to_dict()
    names = ["+".join(i["name"] for i in circ) for circ in d["instructions"]]
    return {n: float(p) for n, p in zip(names, d["probabilities"])}


def compare(rec, circ, q, reps=("kraus", "rm")):
    from qiskit.quantum_info import SuperOp
    from skqd.campaign33 import noise as N
    specs = {r: N.ibm_spec(rec, "I-ECHO", r, "echo") for r in reps}
    errs = {r: delay_errors(specs[r], circ, q) for r in reps}
    a, b = errs[reps[0]], errs[reps[1]]
    t1 = specs["kraus"].t1s[q]
    t2 = {r: specs[r].t2s[q] for r in reps}
    sites, worst, worst_site = [], 0.0, None
    for i, ((ta, ea), (tb, eb)) in enumerate(zip(a, b)):
        d = float(np.max(np.abs(SuperOp(ea.to_quantumchannel()).data - SuperOp(eb.to_quantumchannel()).data)))
        pr = 1.0 - math.exp(-ta / t1)
        sites.append({"index": i, "delay_s": {reps[0]: ta, reps[1]: tb},
                      "probabilities": {reps[0]: error_probs(ea), reps[1]: error_probs(eb)},
                      "closed_form_reset_probability": pr, "superop_max_abs_diff": d})
        if d > worst:
            worst, worst_site = d, i
    return {"qubit": q, "T1_s": t1, "T2_s_by_representation": t2, "n_delay_errors": {r: len(errs[r]) for r in reps},
            "total_delay_s": {r: float(sum(t for t, _e in errs[r] if t)) for r in reps},
            "max_superop_diff": worst, "max_at_site": worst_site, "identical_to_1e-12": worst <= 1e-12,
            "durations_identical": all(s["delay_s"][reps[0]] == s["delay_s"][reps[1]] for s in sites),
            "sites": sites}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser()
    ap.add_argument("--qubit", type=int, default=53)
    a = ap.parse_args(argv)
    import qiskit
    from skqd.campaign33 import circuits as C
    from skqd.campaign33 import tokens_run as TR
    rec = TR.load_record()
    circ = C.load_circuit("IBM-T0", CID)
    res = compare(rec, circ, a.qubit)
    stack = "qiskit" + qiskit.__version__
    doc = {"title": f"prompts/33c step 1(a): RM vs Kraus delay errors on physical qubit {a.qubit}, IBM-T0 {CID}",
           **provenance(argv), "record": {"path": os.path.relpath(TR.RECORD, ROOT), "fingerprint": rec["fingerprint"]},
           "rule": "SuperOp max |diff| <= 1e-12 at every delay site of the qubit; durations in seconds identical",
           **res}
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, f"delays_q{a.qubit}_{stack}.json")
    with open(p, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"{res['n_delay_errors']} errors, total {res['total_delay_s']}, max diff {res['max_superop_diff']}")
    print(f"wrote {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main()

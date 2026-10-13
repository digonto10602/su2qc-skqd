#!/usr/bin/env python
"""
prompts/33c step 1(b) diagnostic (CPU): `x`, `delay(400 us)`, `measure` on one physical qubit of the record under
the class-2 builders (`noise.ibm_spec(record, "I-ECHO", rep)`, rep = rm, kraus, pta), 20 000 shots each; P(1)
against e^{-400 us / T1} with the binomial z.  Writes data/campaign33/c33c_diag/oneq_q<q>_<stack>.json.

    python scripts/c33c_diag_oneq.py --qubit 53
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")]
from c33c_diag_full import OUT_DIR, provenance  # noqa: E402

DELAY_S = 400e-6
SHOTS = 20000
SEED = 7


def one_qubit_circuit(rec, q, delay_s=DELAY_S):
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(int(rec["num_qubits"]), 1)
    qc.x(q)
    qc.delay(int(round(delay_s / float(rec["dt_s"]))), q, unit="dt")
    qc.measure(q, 0)
    return qc


def p1_under(rec, q, rep, shots=SHOTS, seed=SEED, delay_s=DELAY_S):
    from skqd.campaign33 import noise as N
    from skqd.campaign33 import sampling as SM
    spec = N.ibm_spec(rec, "I-ECHO", rep, "echo")
    sim, _kw = SM.make_simulator("CPU", "policy", spec.noise_model)
    c = sim.run(spec.apply(one_qubit_circuit(rec, q, delay_s)), shots=shots, seed_simulator=seed).result().get_counts()
    return c.get("1", 0) / shots


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser()
    ap.add_argument("--qubit", type=int, default=53)
    a = ap.parse_args(argv)
    from skqd.campaign33 import tokens_run as TR
    import qiskit
    rec = TR.load_record()
    q = a.qubit
    t1 = float(rec["qubits"][str(q)]["T1_s"])
    expect = math.exp(-DELAY_S / t1)
    sig = math.sqrt(expect * (1 - expect) / SHOTS)
    rows = {}
    for rep in ("rm", "kraus", "pta"):
        p = p1_under(rec, q, rep)
        rows[rep] = {"P1": p, "z_vs_exp": (p - expect) / sig, "within_4_sigma": abs(p - expect) <= 4 * sig}
        print(rep, p, rows[rep]["z_vs_exp"])
    stack = "qiskit" + qiskit.__version__
    doc = {"title": f"prompts/33c step 1(b): one-qubit relaxation on physical qubit {q} (CPU)", **provenance(argv),
           "qubit": q, "T1_s": t1, "T2_s": float(rec["qubits"][str(q)]["T2_s"]), "delay_s": DELAY_S, "shots": SHOTS,
           "seed": SEED, "expected_P1": expect, "binomial_sigma": sig,
           "rule": "x, delay(400 us), measure; P(1) within 4 sigma (binomial at the expectation) of e^{-t/T1}; the "
                   "measured P(1) also contains the x gate error and the readout error of this qubit",
           "record": {"path": os.path.relpath(TR.RECORD, ROOT), "fingerprint": rec["fingerprint"]},
           "by_representation": rows,
           "note": "pta is unital by construction (information): it is not expected to reproduce relaxation"}
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, f"oneq_q{q}_{stack}.json")
    with open(p, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"wrote {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
prompts/26 A6 diagnostic: does a Z-type (phase) error leave a k = 1 shot on the reference string?

The A6 dry run (gate-only H2-2 depolarizing model) estimates f by the reference-string test, i.e. from
the number of shots that end on the reference string.  A k = 1 circuit puts ~91 % of its output on that
one string, so an error that only changes PHASES of a near-basis state may still end there; such a shot
is counted as clean although an error occurred.  This script measures that directly on one frozen k = 1
circuit with a channel that has the SAME error-event probability per gate as the A6 depolarizing model
(15/16 p2 per rzz, 3/4 p1 per rx/ry) but puts every event on Z-type Paulis only
({ZI, IZ, ZZ} for rzz, {Z} for rx/ry), and no readout error.  Its error-free fraction is therefore the
A6 model's error-free fraction (without readout), and any excess of reference-string hits over
`no_error_probability x p_ref` is the near-clean contribution of phase errors.

Output: data/quantinuum/a6_phase_error_check.json.  Runs in the isolated venv (pytket).
Usage: ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/q0p_a6_phase_error_check.py [--shots 40]
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from skqd import circuits_qiskit as cq  # noqa: E402
from skqd import quantinuum_native as qn  # noqa: E402
from skqd.reference_sim import bits_to_int, qiskit_key_to_bits  # noqa: E402

from quantinuum_submit import A6_NOISE, load_frozen, load_index, load_manifest, pilot_ids  # noqa: E402

CIRC = os.path.join(ROOT, "data", "quantinuum", "circuits_2x3")
OUT = os.path.join(ROOT, "data", "quantinuum", "a6_phase_error_check.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=40)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--id", default=None, help="default: the B0 pilot k = 1 circuit")
    args = ap.parse_args()
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, pauli_error
    from scipy.stats import chi2

    cid = args.id or pilot_ids(load_index(CIRC))[0]
    man = load_manifest(CIRC, cid)
    ir, n, _ = qn.pytket_to_ir(load_frozen(CIRC, man))
    qc = cq.ir_to_qiskit(ir, n, measure=True)
    p2, p1 = A6_NOISE["depolarizing_2q_rzz"], A6_NOISE["depolarizing_1q_rx_ry"]
    e2, e1 = 15.0 / 16.0 * p2, 0.75 * p1          # error-event probability of the A6 depolarizing channels
    nm = NoiseModel(basis_gates=["rz", "rx", "ry", "rzz"])
    nm.add_all_qubit_quantum_error(pauli_error([("II", 1 - e2), ("ZI", e2 / 3), ("IZ", e2 / 3), ("ZZ", e2 / 3)]), ["rzz"])
    nm.add_all_qubit_quantum_error(pauli_error([("I", 1 - e1), ("Z", e1)]), ["rx", "ry"])
    t0 = time.time()
    res = AerSimulator(noise_model=nm, method="statevector", seed_simulator=args.seed).run(qc, shots=args.shots).result()
    wall = time.time() - t0
    counts = {bits_to_int(qiskit_key_to_bits(k)): int(v) for k, v in res.get_counts().items()}
    hits = counts.get(int(man["reference_int"]), 0)
    c = man["counts"]
    no_err = (1 - e2) ** c["n_zz"] * (1 - e1) ** c["n_phasedx"]
    lo = 0.0 if hits == 0 else chi2.ppf(0.025, 2 * hits) / 2
    hi = chi2.ppf(0.975, 2 * hits + 2) / 2
    rec = {"produced_by": "scripts/q0p_a6_phase_error_check.py", "circuit": cid, "shots": args.shots,
           "seed": args.seed, "channel": ("Z-type Pauli channel with the A6 error-event probabilities: rzz "
                                          "{ZI, IZ, ZZ} total 15/16 p2; rx/ry {Z} 3/4 p1; no readout error"),
           "p2": p2, "p1": p1, "event_probability_2q": e2, "event_probability_1q": e1,
           "no_error_probability": no_err, "p_reference": man["p_reference"],
           "expected_hits_if_phase_errors_leave_the_reference": args.shots * man["p_reference"],
           "expected_hits_if_only_error_free_shots_hit": args.shots * no_err * man["p_reference"],
           "reference_hits": hits, "reference_hits_95": [lo, hi],
           "hit_fraction": hits / args.shots, "wall_s": wall,
           "created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    with open(OUT, "w") as fh:
        json.dump(rec, fh, indent=1)
    print(json.dumps({k: rec[k] for k in ("circuit", "shots", "no_error_probability", "reference_hits",
                                          "expected_hits_if_only_error_free_shots_hit",
                                          "expected_hits_if_phase_errors_leave_the_reference", "wall_s")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Job plans for the background queues (re-read by the queues before every job, so new families join without a
restart).  Priorities: cheap and decisive first."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits  # noqa: E402

S2X4 = ["B0_ref102_k1", "B0_ref102_k3", "B0_ref102_k5", "B0_ref345_k1", "B0_ref345_k4", "B0_ref345_k5",
        "B0_ref16833_k1", "B0_ref1338_k1", "B1_ref230_k1", "B1_ref230_k3", "B1_ref230_k5", "B1_ref103_k1"]
A1, B1 = "compressed_circuit_llm_2x4_classA", "compressed_circuit_llm_2x4_classB"
A2, B2 = "compressed_circuit_llm_2x4_classA_v2", "compressed_circuit_llm_2x4_classB_v2"
A3, B3 = "compressed_circuit_llm_2x3_classA", "compressed_circuit_llm_2x3_classB"


def available():
    F = circuits.genie_family_api()
    return set(F.available_families()) if F else set()


def accuracy_jobs():
    """Coordinator priority (2026-10-21): 2x3 families (cheap), then 2x4 v2 (all 150; genie ran 2 at 28 qubits),
    then 2x4 v1 (all 150)."""
    av = available()
    J = [("2x3", "frozen", t) for t in circuits.frozen_2x3_ids()]
    for fam in (B3, A3):
        if fam in av:
            J += [("2x3", fam, t) for t in circuits.genie_ir(fam)]
    for fam in (B2, A2):
        if fam in av:
            J += [("2x4", fam, t) for t in circuits.genie_ir(fam)]
    v1 = [circuits.tag(*x) for x in circuits.v1_ids()]
    J += [("2x4", B1, t) for t in v1] + [("2x4", A1, t) for t in v1]
    return J


def noisy_jobs():
    av = available()
    F23 = circuits.frozen_2x3_ids()
    fam23 = [f for f in (B3, A3) if f in av] + ["frozen"]
    v2 = [f for f in (B2, A2) if f in av]
    J = []
    for dev, sh24, sh23 in (("quantinuum_h2_2", 300, 400), ("quantinuum_helios_1", 300, 400)):
        J += [("2x4", f, dev, t, sh24) for t in S2X4 for f in (B1, A1)]
        J += [("2x3", f, dev, t, sh23) for t in F23 for f in fam23]          # interleaved by circuit
        J += [("2x4", f, dev, t, sh24) for t in S2X4 for f in v2]
    for dev in ("quantinuum_h2_2_nomem", "ionq_tempo_noidle", "ionq_forte_noidle"):
        J += [("2x3", f, dev, t, 300) for t in F23 for f in fam23]
        J += [("2x4", f, dev, t, 300) for t in S2X4 for f in [B1, A1] + v2]
    for dev in ("ionq_forte", "ionq_tempo"):
        J += [("2x3", f, dev, t, 200) for t in F23 if t.endswith("_k1") for f in fam23]
        J += [("2x4", f, dev, t, 200) for t in S2X4 if t.endswith("_k1") for f in [B1, A1] + v2]
    return J


if __name__ == "__main__":
    print(len(accuracy_jobs()), len(noisy_jobs()))

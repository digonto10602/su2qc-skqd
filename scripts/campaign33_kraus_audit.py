#!/usr/bin/env python
"""
prompts/33d R2: the Kraus audit of every campaign-33 noise builder -> data/campaign33/kraus_audit.json.

For each builder the instruction classes Aer executes, read from the BUILT model (noise.instruction_classes:
`to_dict` errors, the run-time transform's and the custom passes' inserted errors on a frozen circuit of the
family the tokens run): E0-E8 (quantinuum_spec, NAT-O0 B0_ref117_k1; E8 on IR-L3-RZZ), I-GATE / ECHO / STAR / XY4 /
COH x (kraus, rm, pta) (ibm_spec on the record, the cell's family, B0_ref117_k1), and CF (cf_gpu: a noiseless
statevector with explicit Pauli gates in the IR; no noise model).  Which harvested tokens ran a Kraus instruction
on the GPU follows from the table.

    python scripts/campaign33_kraus_audit.py [--out data/campaign33/kraus_audit.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")]

CID = "B0_ref117_k1"
IBM_CELLS = {"I-GATE": "IBM-U", "I-ECHO": "IBM-T0", "I-STAR": "IBM-T0", "I-XY4": "IBM-T3", "I-COH": "IBM-T0"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "campaign33", "kraus_audit.json"))
    a = ap.parse_args(argv)
    from c33c_diag_full import provenance
    from skqd.campaign33 import cf_gpu as CFG
    from skqd.campaign33 import circuits as C
    from skqd.campaign33 import noise as N
    from skqd.campaign33 import tokens_run as TR
    t0 = time.time()
    out = {"title": "prompts/33d R2: Kraus audit of every campaign-33 noise builder", **provenance(argv),
           "rule": ("instruction classes read from the built models: to_dict errors (gate + readout), plus the errors "
                    "the run-time transform and the custom passes insert into a frozen circuit of the family"),
           "builders": {}}
    for sid in N.QUANTINUUM_SCENARIOS:
        fam = "IR-L3-RZZ" if sid == "E8" else "NAT-O0"
        spec = N.quantinuum_spec(sid)
        ic = N.instruction_classes(spec, C.load_circuit(fam, CID))
        out["builders"][sid] = {"builder": "noise.quantinuum_spec", "circuit": f"{fam} {CID}", **ic,
                                "used_by": "class 4 (C4_FCELLS_*, C4_F*, C4_PART_*)" if sid != "E0" else "noiseless"}
        print(sid, ic["kraus_total"], sorted(ic["to_dict"]), sorted(ic["inserted"]), flush=True)
    rec = TR.load_record()
    ratio = N.t2_star_ratio()
    for cell, fam in IBM_CELLS.items():
        circ = C.load_circuit(fam, CID)
        eps = None
        if cell == "I-COH":
            eps, _info = N.coherent_eps_for(C.load_manifest(fam, CID)["physical_qubits"])
        conv = "star" if cell == "I-STAR" else "echo"
        for rep in ("kraus", "rm", "pta"):
            spec = N.ibm_spec(rec, cell, rep, conv, ratio, eps)
            ic = N.instruction_classes(spec, circ)
            out["builders"][f"{cell}|{rep}"] = {"builder": "noise.ibm_spec", "circuit": f"{fam} {CID}", **ic,
                                                "used_by": ("C2_CAL arms; C2 cells / C2_KCHK" if cell == "I-ECHO"
                                                            else "C2 cells")}
            print(cell, rep, ic["kraus_total"], ic["kraus_to_dict"], ic["kraus_inserted"], flush=True)
    sim = CFG._sim("CPU", 1)
    out["builders"]["CF"] = {"builder": "cf_gpu (C4_CF and the cf parts)", "noise_model": sim.options.noise_model,
                             "to_dict": {}, "inserted": {}, "kraus_total": 0, "circuit_checked": False,
                             "note": ("cf_gpu._sim builds AerSimulator without a noise model: the trajectories insert "
                                      "explicit Pauli gates into the IR (cf_trajectories.insert_paulis) and evolve "
                                      "noiseless statevectors")}
    out["noiseless"] = {"C1_IDEAL": "statevector, no noise model", "C3_AER": "statevector, no noise model"}
    kr = {k: v["kraus_total"] for k, v in out["builders"].items() if v["kraus_total"]}
    out["summary"] = {"builders_with_kraus": kr,
                      "e_scenarios_kraus_free": all(out["builders"][s]["kraus_total"] == 0 for s in N.QUANTINUUM_SCENARIOS),
                      "harvested_gpu_tokens_with_kraus": ["C2_CAL runs 1-3 (the kraus arms only)"],
                      "conclusion": ("Kraus instructions appear only in the ibm_spec 'kraus' representation (gates and "
                                     "delays of the T2 > T1 qubits): of the harvested GPU tokens only C2_CAL's Kraus arms "
                                     "executed a Kraus channel; classes 1, 3, 4 and C4_CF did not")}
    out["runtime_s"] = time.time() - t0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"wrote {os.path.relpath(a.out, ROOT)}; Kraus in: {kr}")


if __name__ == "__main__":
    main()

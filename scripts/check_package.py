#!/usr/bin/env python3
"""
Package integrity check — the FIRST thing to run on a fresh checkout (the first
prompt, prompts/00_bootstrap_and_push.md, starts here).

Verifies that every expected file is present, that the validation JSONs of the
cloud-verified gates say PASS, that the reports quote the same numbers as the
JSONs (spot check), and that the import of the package works.  Exit code 0 only
if everything is in place.
"""
import importlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

EXPECTED = [
    "README.md", "RUNBOOK.md", "CLAUDE.md", "LICENSE", "pyproject.toml", "requirements.txt", "requirements-laptop.txt",
    "proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md", "proposal/README.md",
    "prompts/README.md", "prompts/ROUTING.md", "prompts/ESCALATION_TEMPLATE.md", "prompts/00_bootstrap_and_push.md",
    "prompts/01_laptop_L1_reproduce_cloud_gates.md", "prompts/02_laptop_L2_qiskit_check.md",
    "prompts/03_laptop_L3_cz_counts_S2.md", "prompts/04_laptop_L4_aer_noise_S3.md", "prompts/05_laptop_L5_cudaq_check.md",
    "prompts/06_S2b_plaquette_interior_and_hopping_decomposition.md", "prompts/07_hardware_H0_2x2_calibration.md",
    "prompts/08_month_plan_and_reporting.md",
    "reports/E1_gauss_law_two_builders.md", "reports/E2_counts_codewords_decoder.md", "reports/E3_exact_references.md",
    "reports/S1_support_emulation_controls.md", "reports/circuit_structure.md", "reports/laptop_vs_hpc_plan.md",
    "reports/PROJECT_STATUS.md",
    "validation/E1.json", "validation/E2.json", "validation/E3.json", "validation/S1.json", "validation/gates.md",
    "data/references.json", "data/S1_emulation.json",
    "src/skqd/__init__.py", "src/skqd/su2.py", "src/skqd/fermions.py", "src/skqd/lattice.py", "src/skqd/vertex.py",
    "src/skqd/basis.py", "src/skqd/hamiltonian.py", "src/skqd/fullspace.py", "src/skqd/codec.py", "src/skqd/exact.py",
    "src/skqd/krylov.py", "src/skqd/noise.py", "src/skqd/skqd.py", "src/skqd/controls.py", "src/skqd/ml.py",
    "src/skqd/report.py", "src/skqd/reference_sim.py", "src/skqd/circuits_ir.py", "src/skqd/circuits_qiskit.py",
    "src/skqd/circuits_cudaq.py",
    "scripts/gate_E1.py", "scripts/gate_E2.py", "scripts/gate_E3.py", "scripts/gate_S1.py", "scripts/run_gate.py",
    "scripts/laptop_L2_qiskit_check.py", "scripts/laptop_L3_cz_counts.py", "scripts/laptop_L4_aer_noise.py",
    "scripts/laptop_L5_cudaq_check.py", "scripts/check_package.py",
    "tests/test_su2.py", "tests/test_builder.py", "tests/test_codec.py", "tests/test_skqd.py", "tests/test_circuits_ir.py",
    ".claude/agents/planner-fable.md", ".claude/agents/executor-opus.md", ".claude/agents/reviewer-opus.md",
    ".claude/agents/runner-sonnet.md", ".claude/agents/scribe-haiku.md", ".claude/skills/gate/SKILL.md",
    ".claude/settings.json", ".github/workflows/ci.yml",
]
CLOUD_GATES = ["E1", "E2", "E3", "S1"]


def main():
    missing = [p for p in EXPECTED if not os.path.exists(os.path.join(ROOT, p))]
    ok = True
    if missing:
        ok = False
        print("MISSING files:")
        for p in missing:
            print("  ", p)
    else:
        print(f"all {len(EXPECTED)} expected files present")
    for g in CLOUD_GATES:
        p = os.path.join(ROOT, "validation", f"{g}.json")
        if os.path.exists(p):
            with open(p) as fh:
                js = json.load(fh)
            n_fail = sum(1 for c in js["criteria"] if not c["passed"])
            print(f"gate {g}: {js['status']} ({len(js['criteria'])} criteria, {n_fail} failing), computed {js['environment']['timestamp']}")
            ok = ok and js["status"] == "PASS"
    # spot check: E3 report quotes the E0 values of data/references.json
    try:
        refs = json.load(open(os.path.join(ROOT, "data", "references.json")))["references"]
        e0 = refs["2x3|g2=4.0|2B=0"]["energies"][0]
        txt = open(os.path.join(ROOT, "reports", "E3_exact_references.md")).read()
        if f"{e0:.4f}" in txt:
            print(f"report/data consistency: E0(2x3, g2=4, B=0) = {e0:.4f} appears in reports/E3_exact_references.md")
        else:
            ok = False
            print("report/data MISMATCH for E0(2x3)")
    except Exception as e:
        ok = False
        print("could not spot-check references:", e)
    for mod in ("skqd.su2", "skqd.hamiltonian", "skqd.codec", "skqd.skqd", "skqd.circuits_ir",
                "skqd.hardware"):
        try:
            importlib.import_module(mod)
        except Exception as e:
            ok = False
            print("import failed:", mod, e)
    print("PACKAGE OK" if ok else "PACKAGE INCOMPLETE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Review 001: collect every number of the review into 001-independent-verification.json."""
import glob, json, os, platform, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
def sh(c):
    return subprocess.check_output(c, shell=True, text=True, cwd=ROOT).strip()
runs = {}
for p in sorted(glob.glob(os.path.join(HERE, "001_runs", "*.json"))):
    runs[os.path.basename(p)[:-5]] = json.load(open(p))
G = {"A": json.load(open(os.path.join(HERE, "..", "data", "eval_arch_it5_operator_pp_all75_pruned.json"))),
     "B": json.load(open(os.path.join(HERE, "..", "data", "eval_arch_it5_input_pp_all75_pruned.json")))}
table = []
for tag, r in runs.items():
    gtag = f"B{r['twoB']//2}_ref{r['reference']}_k{r['k']}"
    gv = G[r["class"]]["circuits"][gtag]["verification"] if r["input"].get("seed") is None else None
    table.append({"run": tag, "class": r["class"], "circuit": gtag, "input": r["input"].get("seed", "own reference"),
                  "n_qubits": r["counts_recount_from_qiskit_circuit"]["n_qubits_circuit"],
                  "n_qubits_touched": r["counts_recount_from_qiskit_circuit"]["n_qubits_touched"],
                  "n_2q": r["counts_recount_from_qiskit_circuit"]["n_2q"],
                  "depth_2q": r["counts_recount_from_qiskit_circuit"]["depth_2q"],
                  "max_abs_dpsi_phase_aligned": r["max_abs_dpsi_phase_aligned"],
                  "max_abs_dpsi_raw": r["max_abs_dpsi_raw"], "l2_dpsi_phase_aligned_incl_leak": r["l2_dpsi_phase_aligned_incl_leak"], "abs_overlap": r["abs_overlap"], "global_phase_rad": r["global_phase_rad"],
                  "leakage_noncodeword": r["leakage_noncodeword"],
                  "leakage_other_sector_codewords": r["leakage_other_sector_codewords"],
                  "leakage_outside_sector": r["leakage_outside_sector"], "pass_bar": r["pass_bar"],
                  "aer_s": r["timing_s"]["aer"],
                  "dropped_diag": r.get("dropped_diag"),
                  "genie_max_dev_phase_aligned": gv and gv["max_dev_phase_aligned"],
                  "genie_certified_max_dev": gv and gv.get("certified_max_dev")})
out = {"review_started_at_commit": "6eb4528", "produced_by": "2x4_compression_using_ai_v1/reviews/001_*.py (reviewer-opus, independent check)",
       "git_commit": sh("git rev-parse --short HEAD"),
       "git_status_study_folder": sh("git status --short 2x4_compression_using_ai_v1 | head -20"),
       "machine": {"platform": platform.platform(), "node": platform.node(), "cpu_count": os.cpu_count(),
                   "python": platform.python_version()},
       "written_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
       "parameters": {"lattice": "2x4", "g2": 4.0, "m": "mass_default(4.0)", "dt_source": "validation/E3.json",
                      "bar": {"max_abs_dpsi": 1e-10, "leakage": 1e-9},
                      "circuits_source": "genie builders c2x4.family.archive_family('it5', cls, peephole=True), cache redirected to reviews/001_cache (genie data/cache not read)",
                      "engine": "qiskit-aer statevector, precision double, fusion on, 12 threads, CPU",
                      "target": "skqd.krylov.coarse_states / apply_groups with skqd.krylov.term_groups; Codec codewords (CodewordEmbedding.ints)"},
       "seeds": {"operator_test_states": "numpy.random.default_rng(seed), seeds 11 and 12; aer seed_simulator 1"},
       "runs": table,
       "counts_all_150": json.load(open(os.path.join(HERE, "001_counts_all.json")))["summary"],
       "counts_mismatches_vs_genie": json.load(open(os.path.join(HERE, "001_counts_all.json")))["mismatches"],
       "native_f": json.load(open(os.path.join(HERE, "001_native_f.json"))),
       "lean": {"build_log": "reviews/001_lake_build.log", "axioms_log": "reviews/001_lean_axioms.log",
                "build_ok": "Build completed successfully" in open(os.path.join(HERE, "001_lake_build.log")).read(),
                "axioms": [l for l in open(os.path.join(HERE, "001_lean_axioms.log")).read().splitlines() if "axioms" in l]}}
json.dump(out, open(os.path.join(HERE, "001-independent-verification.json"), "w"), indent=1, default=str)
for t in table:
    print(t["run"], t["n_2q"], t["depth_2q"], f"{t['max_abs_dpsi_phase_aligned']:.2e}", f"{t['leakage_outside_sector']:.1e}", t["pass_bar"])

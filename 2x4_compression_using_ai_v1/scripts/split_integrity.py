"""Integrity snapshot for the folder split (notes/012): run once BEFORE and once AFTER the `git mv`, then compare.

    python 2x4_compression_using_ai_v1/scripts/split_integrity.py before   -> data/split_integrity_before.json
    python 2x4_compression_using_ai_v1/scripts/split_integrity.py after    -> data/split_integrity_after.json
    python 2x4_compression_using_ai_v1/scripts/split_integrity.py compare  -> data/split_integrity_compare.json

Recorded per snapshot:
  files      sha256 of every git-tracked file in the moved trees, keyed by its NEW repository-relative path (the
             before-snapshot maps old -> new through MOVES), so the two snapshots compare key by key;
  families   for every registered family name (and alias): get_family(name) -> per circuit (circuit_id, the metadata
             content_sha256, the recomputed IR gate-list sha256, and the sha256 of the qiskit circuit's instruction
             list (gate name, qubit indices, parameters as repr floats));
  results    noise/src/results.list_available() as a sorted list of 4-tuples.
Imports the loaders lazily from wherever they are at the time of the run; no other side effect.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
S4, S3, S2 = "2x4_compression_using_ai_v1", "2x3_compression_using_ai_v1", "2x2_compression_using_ai_v1"

# old repository-relative prefix -> new repository-relative prefix (the moves table of notes/012)
MOVES = [
    (f"{S4}/data/c2x3/", f"{S3}/data/c2x3/"),
    (f"{S4}/data/families/compressed_circuit_llm_2x3_classA.json.gz",
     f"{S3}/data/families/compressed_circuit_llm_2x3_classA.json.gz"),
    (f"{S4}/data/families/compressed_circuit_llm_2x3_classB.json.gz",
     f"{S3}/data/families/compressed_circuit_llm_2x3_classB.json.gz"),
    (f"{S4}/noise/data/results/2x3/", f"{S3}/noise/data/results/2x3/"),
    (f"{S4}/data/c2x2/", f"{S2}/data/c2x2/"),
    (f"{S4}/data/families/compressed_circuit_llm_2x2_classA.json.gz",
     f"{S2}/data/families/compressed_circuit_llm_2x2_classA.json.gz"),
    (f"{S4}/data/families/compressed_circuit_llm_2x2_classB.json.gz",
     f"{S2}/data/families/compressed_circuit_llm_2x2_classB.json.gz"),
    (f"{S4}/data/families/native_2x2/", f"{S2}/data/families/native_2x2/"),
    (f"{S4}/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classA/",
     f"{S2}/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classA/"),
    (f"{S4}/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classB/",
     f"{S2}/hardware/quantinuum_sc_20261028/compressed_circuit_llm_2x2_classB/"),
    (f"{S4}/examples/2x2_sandbox/", f"{S2}/examples/2x2_sandbox/"),
]
# moved files whose CONTENT was edited on purpose in the split (path fixes in code); every other moved file -- all
# frozen families, native exports, hardware records, results and data -- must be byte-identical
EDITED_ON_PURPOSE = {f"{S2}/examples/2x2_sandbox/run_2x2_example.py"}
# the 2x4 families stay where they are; they are hashed too (control: unchanged by the split)
STAY = [f"{S4}/data/families/compressed_circuit_llm_2x4_class{c}_v{v}.json.gz" for c in "AB" for v in (1, 2)]


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked(prefix: str) -> list:
    out = subprocess.check_output(["git", "-C", ROOT, "ls-files", "--", prefix.rstrip("/")], text=True)
    return [x for x in out.splitlines() if x]


def files_snapshot(mode: str) -> dict:
    res = {}
    for old, new in MOVES:
        src = old if mode == "before" else new
        for rel in tracked(src):
            key = new + rel[len(src):] if src.endswith("/") else new
            res[key] = sha256_file(os.path.join(ROOT, rel))
    for rel in STAY:
        res[rel] = sha256_file(os.path.join(ROOT, rel))
    return dict(sorted(res.items()))


def families_snapshot() -> dict:
    sys.path.insert(0, os.path.join(STUDY, "src"))
    from c2x4 import families as F
    names = list(F.FAMILY_NAMES) + sorted(F.ALIASES)
    out = {"family_names": list(F.FAMILY_NAMES), "aliases": dict(F.ALIASES),
           "available_families": F.available_families(), "per_family": {}}
    for name in names:
        rows = []
        ir = {cid: g for cid, g, _ in F.get_family_ir(name)}
        for cid, qc, md in F.get_family(name):
            ins = [[ci.operation.name, [qc.find_bit(q).index for q in ci.qubits],
                    [repr(float(p)) if not hasattr(p, "shape") else repr(p.tolist()) for p in ci.operation.params]]
                   for ci in qc.data]
            qhash = hashlib.sha256(json.dumps([repr(float(qc.global_phase)), ins]).encode()).hexdigest()
            rows.append({"circuit_id": cid, "content_sha256": md["content_sha256"],
                         "ir_sha256": F.gates_sha256(F.encode_gates(ir[cid])), "qiskit_sha256": qhash,
                         "n_qubits": md["n_qubits"], "n_2q": md["n_2q"]})
        out["per_family"][name] = {"path": os.path.relpath(F.family_path(name), ROOT),
                                   "file_sha256": sha256_file(F.family_path(name)), "n_circuits": len(rows),
                                   "circuits": rows}
    return out


def results_snapshot() -> list:
    sys.path.insert(0, os.path.join(STUDY, "noise", "src"))
    import results
    return sorted(list(x) for x in results.list_available())


def git_head() -> str:
    return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()


def main():
    mode = sys.argv[1]
    data = os.path.join(STUDY, "data")
    if mode in ("before", "after"):
        rec = {"produced_by": f"{S4}/scripts/split_integrity.py {mode}", "git_commit": git_head(),
               "written_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
               "machine": {"node": os.uname().nodename, "python": sys.executable}, "seed": None,
               "moves": MOVES, "files": files_snapshot(mode), "families": families_snapshot(),
               "results_list_available": results_snapshot()}
        p = os.path.join(data, f"split_integrity_{mode}.json")
        with open(p, "w") as fh:
            json.dump(rec, fh, indent=1)
        print(p, len(rec["files"]), "files,", len(rec["families"]["per_family"]), "family names,",
              len(rec["results_list_available"]), "results")
        return
    assert mode == "compare"
    b = json.load(open(os.path.join(data, "split_integrity_before.json")))
    a = json.load(open(os.path.join(data, "split_integrity_after.json")))
    fam_b, fam_a = b["families"]["per_family"], a["families"]["per_family"]
    strip = lambda d: {k: v for k, v in d.items() if k != "path"}                          # noqa: E731
    fam_cmp = {n: {"before_path": fam_b[n]["path"], "after_path": fam_a.get(n, {}).get("path"),
                   "file_sha256_equal": fam_b[n]["file_sha256"] == fam_a.get(n, {}).get("file_sha256"),
                   "circuits_equal": strip(fam_b[n]) == strip(fam_a.get(n, {})),
                   "n_circuits": fam_b[n]["n_circuits"]} for n in fam_b}
    diff = sorted(set(b["files"]) ^ set(a["files"])) + sorted(k for k in b["files"] if k in a["files"]
                                                                 and b["files"][k] != a["files"][k])
    unexpected = [k for k in diff if k not in EDITED_ON_PURPOSE]
    files_equal = set(b["files"]) == set(a["files"]) and not unexpected
    fam_files = [k for k in b["files"] if "/data/families/" in k]
    res_equal = b["results_list_available"] == a["results_list_available"]
    out = {"produced_by": f"{S4}/scripts/split_integrity.py compare", "git_commit": git_head(),
           "written_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "seed": None,
           "n_files": len(b["files"]), "n_family_and_native_export_files": len(fam_files),
           "family_and_native_export_files_identical": all(b["files"][k] == a["files"].get(k) for k in fam_files),
           "files_sha256_identical_except_edited_on_purpose": files_equal, "files_differing": diff,
           "edited_on_purpose": sorted(EDITED_ON_PURPOSE), "unexpected_differences": unexpected,
           "families": fam_cmp, "families_all_equal": all(v["file_sha256_equal"] and v["circuits_equal"]
                                                            for v in fam_cmp.values()),
           "family_names_equal": b["families"]["family_names"] == a["families"]["family_names"],
           "available_families_equal": b["families"]["available_families"] == a["families"]["available_families"],
           "results_n": len(b["results_list_available"]), "results_list_available_identical": res_equal}
    out["status"] = "PASS" if (files_equal and out["families_all_equal"] and out["family_names_equal"]
                               and out["available_families_equal"] and res_equal) else "FAIL"
    with open(os.path.join(data, "split_integrity_compare.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "families"}, indent=1))


if __name__ == "__main__":
    main()

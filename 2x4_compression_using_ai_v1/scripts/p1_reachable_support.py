"""Phase-1 diagnostic (no optimisation): how much of each term's local codeword space does a
2x4 coarse-step circuit actually touch, starting from its reference basis state?

The signed 2x4 circuit is prepare(ref) followed by prod_gamma exp(-i k dt H_gamma) in the
package's group order (diag, hop0..hop9, plaq0..plaq2; skqd.krylov.coarse_states).  Its input is
ONE computational-basis state, so before term gamma the state is supported on a known set of
codewords.  This script records, per (sector, reference, k) and per term:

  * the structural support before the term (union of the connected components of every
    earlier group's generator reached from the reference: an exact UPPER bound on the set of
    codewords that can carry amplitude, independent of angles),
  * the numerical support of the exact coarse state (|amp|^2 > 1e-24) for comparison,
  * on the term's own qubit support: how many local codewords and how many connected blocks of
    the local generator the incoming state touches, against the totals the structured
    synthesis (circuits_ir.structured_term_gates) pays for.

Only package functions are imported (read-only).  Writes data/p1_reachable_support.json.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as csgraph
import scipy.sparse.linalg as spl

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(ROOT, "src"))

from skqd.exact import Model, mass_default            # noqa: E402
from skqd.codec import Codec                            # noqa: E402
from skqd.krylov import references                      # noqa: E402
from skqd.reference_sim import term_support, localize   # noqa: E402

G2 = 4.0
KMAX = 5
NUM_THRESHOLD = 1e-24


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception as exc:  # recorded, not swallowed silently
        return f"unavailable: {exc}"


def components(H) -> np.ndarray:
    A = (abs(H) > 1e-12).astype(np.int8).tocsr()
    A.setdiag(0)
    A.eliminate_zeros()
    _n, lab = csgraph.connected_components(A, directed=False)
    return lab


def main():
    t0 = time.time()
    with open(os.path.join(ROOT, "data", "quantinuum", "circuits_2x4", "index.json")) as fh:
        dts = json.load(fh)["dt"]                     # the frozen manifests' dt per 2B
    M = Model(4)
    m = mass_default(G2)
    groups = M.terms.groups(G2, m)                    # ordered dict: diag, hop0.., plaq0..
    names = list(groups)
    mats = [sp.csr_matrix(groups[nm]) for nm in names]
    labs = [components(H) for H in mats]
    codec = Codec(M.basis)
    cw = codec.all_codewords()                        # (dim, 28) int8, qubit q = column q
    t_model = time.time() - t0

    # per-term local data: support, local state of every global codeword, local blocks
    term_info = {}
    for nm in names:
        if nm == "diag":
            term_info[nm] = {"support": list(range(codec.n_qubits))}
            continue
        kind, idx = ("hop", int(nm[3:])) if nm.startswith("hop") else ("plaq", int(nm[4:]))
        sup = term_support(M, kind, idx)
        states, h, pos = localize(M, groups[nm], sup)
        A = np.abs(h) > 1e-12
        np.fill_diagonal(A, False)
        nb, lab = csgraph.connected_components(sp.csr_matrix(A), directed=False)
        sizes = np.bincount(lab, minlength=nb)
        weights = 1 << np.arange(len(sup))
        loc_of_global = (cw[:, sup].astype(np.int64) * weights).sum(axis=1)
        term_info[nm] = {"support": [int(q) for q in sup], "n_local_states": len(states),
                         "n_blocks": int(nb), "n_nontrivial_blocks": int((sizes > 1).sum()),
                         "_pos": pos, "_lab": lab, "_loc": loc_of_global, "_sizes": sizes}

    rows = []
    for twoB in (0, 2):
        dt = float(dts[str(twoB)])
        for ref in references(M.basis, twoB):
            # structural support is angle-independent: compute once per reference
            struct = np.zeros(M.basis.dim, dtype=bool)
            struct[ref] = True
            per_term = []
            for nm, H, lab in zip(names, mats, labs):
                before = np.flatnonzero(struct)
                entry = {"term": nm, "structural_support_before": int(len(before))}
                if nm != "diag":
                    ti = term_info[nm]
                    loc = np.unique(ti["_loc"][before])
                    blocks = np.unique(ti["_lab"][[ti["_pos"][int(s)] for s in loc]])
                    nontriv = int((ti["_sizes"][blocks] > 1).sum())
                    entry.update(local_states_touched=int(len(loc)),
                                 local_states_total=ti["n_local_states"],
                                 blocks_touched=int(len(blocks)),
                                 nontrivial_blocks_touched=nontriv,
                                 nontrivial_blocks_total=ti["n_nontrivial_blocks"])
                hit = np.unique(lab[before])
                struct = np.isin(lab, hit)
                per_term.append(entry)
            numeric = {}
            for k in range(1, KMAX + 1):
                psi = np.zeros(M.basis.dim, dtype=complex)
                psi[ref] = 1.0
                for H in mats:
                    psi = spl.expm_multiply(-1j * k * dt * H, psi)
                p = np.abs(psi) ** 2
                numeric[str(k)] = {"support_gt_1e-24": int((p > NUM_THRESHOLD).sum()),
                                   "support_gt_1e-12": int((p > 1e-12).sum()),
                                   "outside_structural": float(p[~struct].sum()),
                                   "norm": float(p.sum())}
            rows.append({"twoB": twoB, "reference": int(ref), "dt": dt,
                         "structural_support_final": int(struct.sum()),
                         "per_term": per_term, "numeric_by_k": numeric})
            print(f"2B={twoB} ref={ref}: final structural support {int(struct.sum())}; "
                  f"plaq1 blocks touched "
                  f"{[e for e in per_term if e['term'] == 'plaq1'][0]['nontrivial_blocks_touched']}",
                  flush=True)

    out = {
        "produced_by": "2x4_compression_using_ai_v1/scripts/p1_reachable_support.py",
        "purpose": "phase-1 diagnostic: reachable codewords per term of the 2x4 coarse step",
        "git_commit": git_commit(),
        "machine": {"platform": platform.platform(), "python": platform.python_version(),
                    "numpy": np.__version__, "cpu_count": os.cpu_count()},
        "parameters": {"lattice": "2x4", "g2": G2, "m": m, "kmax": KMAX,
                       "dt_source": "data/quantinuum/circuits_2x4/index.json dt", "dt": dts,
                       "numeric_threshold_prob": NUM_THRESHOLD, "seed": None,
                       "term_order": names},
        "dim": int(M.basis.dim), "n_qubits": int(codec.n_qubits),
        "terms": {nm: {k: v for k, v in ti.items() if not k.startswith("_")}
                  for nm, ti in term_info.items()},
        "rows": rows,
        "runtime_s": {"model_and_groups": t_model, "total": time.time() - t0},
        "created": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    os.makedirs(os.path.join(STUDY, "data"), exist_ok=True)
    with open(os.path.join(STUDY, "data", "p1_reachable_support.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote data/p1_reachable_support.json in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()

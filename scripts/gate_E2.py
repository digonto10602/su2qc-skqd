#!/usr/bin/env python3
"""
Gate E2 — state counts of Table 2, vertex-type state tables, codewords and the
per-shot decoder: encode–decode round trip on every state of every lattice used
in the project, exhaustive acceptance at 12 qubits, random-bit-string acceptance
at 20 and 28 qubits (Steps 2.1–2.5 of the manual).

Runtime: ~1 minute.
"""
import itertools
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from skqd.basis import enumerate_basis, count_labels_without_intertwiner  # noqa: E402
from skqd.codec import Codec, Reject  # noqa: E402
from skqd.lattice import Ladder  # noqa: E402
from skqd.report import GateResult, env_block, md_table, write_report  # noqa: E402
from skqd.vertex import kernel_dim  # noqa: E402

# Table 2 of the manual: (Lx, static sites) -> (states, labels, {2B: dim} or None)
TABLE2 = {
    (2, ()): (82, 82, {0: 38, 2: 20, -2: 20, 4: 2, -4: 2}),
    (3, ()): (1727, 1460, {0: 677, 2: 426, -2: 426, 4: 95, -4: 95, 6: 4, -6: 4}),
    (4, ()): (37165, 26248, {0: 12843, 2: 8934, -2: 8934, 4: 2869, -4: 2869, 6: 350, -6: 350, 8: 8, -8: 8}),
    (2, (0, 2)): (113, 82, None),      # static pair r = 1 (bottom row)
    (2, (0, 3)): (112, 82, None),      # static pair on the diagonal
    (3, (0, 2)): (2729, None, {0: 1089}),
    (3, (0, 4)): (2418, None, {0: 978}),
}
QUBITS = {(2, ()): 12, (3, ()): 20, (4, ()): 28, (3, (0, 2)): 21, (3, (0, 4)): 20, (2, (0, 2)): 12, (2, (0, 3)): 12}


def main():
    t0 = time.time()
    R = GateResult("E2", "State counts (Table 2), vertex tables, codewords and decoder")
    rng = np.random.default_rng(20260914)

    # vertex-type tables (manual Step 2.1)
    def vt(k_ends, static):
        roles = ["out", "out", "in"][:k_ends]
        combos, states = 0, 0
        for js in itertools.product((0, 0.5), repeat=k_ends):
            for n in (0, 1, 2):
                kd = kernel_dim(tuple(zip(js, roles)), n, static)
                combos += kd > 0
                states += kd
        return combos, states

    vrows = []
    for name, k, st, exp_c, exp_s in (("corner", 2, False, 6, 6), ("interior", 3, False, 12, 13),
                                       ("corner + static 1/2", 2, True, 6, 7), ("interior + static 1/2", 3, True, 12, 17)):
        c, s = vt(k, st)
        vrows.append([name, c, s, exp_c, exp_s])
        R.add(f"vertex table: {name} (combinations, states)", f"({c}, {s})", f"= ({exp_c}, {exp_s})", (c, s) == (exp_c, exp_s))
    k13 = kernel_dim(((0.5, "out"), (0.5, "out"), (0.5, "in")), 1)
    R.add("interior vertex, three flux ends, n=1: singlet multiplicity (13th state)", k13, "= 2", k13 == 2)
    k_static = kernel_dim(((0.5, "out"), (0.5, "out")), 1, True)
    R.add("charged corner, two flux ends, n=1: multiplicity", k_static, "= 2", k_static == 2)

    crows, drows = [], []
    for (Lx, st), (n_states, n_labels, sectors) in TABLE2.items():
        lat = Ladder(Lx, static_sites=st)
        B = enumerate_basis(lat)
        nl = count_labels_without_intertwiner(B)
        R.add(f"2x{Lx} static={list(st)}: states", B.dim, f"= {n_states}", B.dim == n_states)
        if n_labels is not None:
            R.add(f"2x{Lx} static={list(st)}: distinct ({{j}},{{n}}) labels", nl, f"= {n_labels}", nl == n_labels)
        sd = B.sector_dims()
        if sectors is not None:
            ok = all(sd.get(k, 0) == v for k, v in sectors.items())
            R.add(f"2x{Lx} static={list(st)}: sector dims", str({k: sd.get(k) for k in sorted(sectors)}),
                  f"= {dict(sorted(sectors.items()))}", ok)
        crows.append([f"2x{Lx}", list(st) or "-", B.dim, nl, str(dict(sorted(sd.items())))])
        # codec
        C = Codec(B)
        R.add(f"2x{Lx} static={list(st)}: qubits", C.n_qubits, f"= {QUBITS[(Lx, st)]}", C.n_qubits == QUBITS[(Lx, st)])
        ok = 0
        cws = set()
        for k, b in enumerate(B.labels):
            bits = C.encode(b)
            cws.add(bits)
            kk, _ = C.decode(bits)
            ok += kk == k
        R.add(f"2x{Lx} static={list(st)}: encode-decode round trip", f"{ok}/{B.dim}", "all states", ok == B.dim)
        R.add(f"2x{Lx} static={list(st)}: codewords distinct", len(cws), f"= {B.dim}", len(cws) == B.dim)
        if C.n_qubits <= 12:
            acc, reasons = 0, {}
            for bits in itertools.product((0, 1), repeat=C.n_qubits):
                try:
                    C.decode(bits)
                    acc += 1
                except Reject as r:
                    reasons[str(r)] = reasons.get(str(r), 0) + 1
            R.add(f"2x{Lx} static={list(st)}: exhaustive acceptance", f"{acc} of {2 ** C.n_qubits}", f"= {B.dim}", acc == B.dim)
            drows.append([f"2x{Lx}", list(st) or "-", C.n_qubits, f"exhaustive: {acc}/{2 ** C.n_qubits}",
                          f"{100 * acc / 2 ** C.n_qubits:.3f}%", f"{100 * B.dim / 2 ** C.n_qubits:.3f}%", str(reasons)])
        else:
            N = 200000
            Rb = rng.integers(0, 2, size=(N, C.n_qubits))
            acc, reasons = 0, {}
            for row in Rb:
                try:
                    C.decode(tuple(int(x) for x in row))
                    acc += 1
                except Reject as r:
                    reasons[str(r)] = reasons.get(str(r), 0) + 1
            frac = acc / N
            expect = B.dim / 2 ** C.n_qubits
            # binomial 4-sigma band
            sig = np.sqrt(expect * (1 - expect) / N)
            R.add(f"2x{Lx} static={list(st)}: random-string acceptance", f"{100 * frac:.3f}%",
                  f"= dim/2^n = {100 * expect:.3f}% within 4 sigma ({100 * 4 * sig:.3f}%)", abs(frac - expect) <= 4 * sig + 1e-12)
            drows.append([f"2x{Lx}", list(st) or "-", C.n_qubits, f"random: {acc}/{N}", f"{100 * frac:.3f}%",
                          f"{100 * expect:.3f}%", str(reasons)])
    R.runtime_s = time.time() - t0
    path = R.save()
    report = f"""# Gate E2 — state counts, vertex tables, codewords and decoder

**Status: {'PASS' if R.passed else 'FAIL'}** — produced by `scripts/gate_E2.py`; numbers stored in `validation/E2.json`.
{env_block()}  Runtime {R.runtime_s:.0f} s.

## Vertex-type tables (Step 2.1 of the manual)

{md_table(["vertex type", "allowed ({j_e}, n) combinations", "physical states", "manual: combinations", "manual: states"], vrows)}

The 13th interior state is the second singlet of $(\\tfrac12)^{{\\otimes 4}} = 2(0)\\oplus 3(1)\\oplus(2)$
(three flux ends and one quark); the fusion-tree label $\\iota_x \\in \\{{0,1\\}}$ is the intermediate spin
$J_{{12}}$ of the first two link ends.  A charged corner with two flux ends and one quark also has two states.

## State counts (Table 2 of the manual)

{md_table(["lattice", "static sites", "states", "distinct ({j},{n}) labels", "sectors {2B: dim}"], crows)}

Every count of Table 2 is reproduced: 82 / 1 727 / 37 165 states versus 82 / 1 460 / 26 248 labels, 113 and 112
with a static pair at 2x2, 2 729 ($B=0$: 1 089) and 2 418 ($B=0$: 978) with a static pair at 2x3.

## Codewords and decoder (Steps 2.4–2.5)

{md_table(["lattice", "static", "qubits", "test", "accepted", "dim / 2^n", "rejection reasons"], drows)}

The decoder accepts exactly the codewords (exhaustively verified at 12 qubits: 82 of 4 096, and 113 of 4 096 with
a static pair); the fraction of uniformly random strings accepted equals $\\dim/2^n$ within statistics
(manual: 0.15 % at 20 qubits, $1727/2^{{20}} = 0.16\\%$), so uncorrelated garbage is almost always rejected and the
residual acceptances are valid but unrelated configurations (false positives that enlarge $B$ without biasing the
variational energy).

## All checks

{R.criteria_table()}

## Reproduce

```
python scripts/gate_E2.py
```
"""
    write_report("E2_counts_codewords_decoder.md", report)
    print(R.criteria_table())
    print("STATUS", "PASS" if R.passed else "FAIL", "->", path)
    return 0 if R.passed else 1


if __name__ == "__main__":
    sys.exit(main())

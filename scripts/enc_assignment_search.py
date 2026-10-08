#!/usr/bin/env python3
"""
E5' (prompts/34 step 8): the codeword-assignment search inside the CURRENT codec widths, flux bits fixed.

The current codec (`skqd.codec.Codec`) stores the flux bits of a vertex's link ends, then one extra bit
(corner: q3; interior: q4).  The flux bits carry the link check and are not touched.  What is free is the
meaning of the extra bit given the flux pattern:

  interior vertex (3 ends), 8 binary choices = 256 assignments, the same at every interior vertex:
    bits 0-3  for the even-parity flux patterns (000, 110, 101, 011): q4 = n/2 XOR e  (which pattern is n = 0)
    bits 4-6  for the one-flux patterns (100, 010, 001): the valid (n = 1) value of q4 is v, the flag is 1 - v
    bit  7    for the three-flux pattern 111: q4 = iota XOR p
  corner vertex (2 ends), 3 binary choices = 8 assignments, the same at every corner:
    bit 0     flux 00: q3 = n/2 XOR c0;   bit 1  flux 11: q3 = n/2 XOR c1
    bit 2     unequal flux (01, 10): the valid (n = 1) value of q3 is c2, the flag is 1 - c2
  Assignment 0 is the current codec (checked: identical codewords).

Score = all-to-all CZ count (qiskit level 3, seed 7, basis rz/sx/x/cz) of the 2x3 terms compiled by
`structured_term_gates` with the variant codec: the interior assignment on {hop4, plaq1} (corner = current),
the corner assignment on {hop0, hop1, plaq0} (interior = current).  The best of each (ties: the lower id,
so the current codec wins ties) is combined and the nine-term coarse step (without diag, whose gate is written
for the current polarities) is compiled for the ratio `best_step_cz_ratio`.  The single-flip detection
fractions of the best variant are compared with the current ones (`detection_unchanged`).

No production code is changed: `VariantCodec` lives here.  Called by `gate_ENC_compare.py --stage assign`.
"""
import os
import sys
import time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from skqd.codec import Codec, Reject  # noqa: E402

G2 = 4.0
EVEN = ((0, 0, 0), (1, 1, 0), (1, 0, 1), (0, 1, 1))
ONE = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
INTERIOR_TERMS = ("hop4", "plaq1")
CORNER_TERMS = ("hop0", "hop1", "plaq0")
STEP_TERMS = tuple([f"hop{l}" for l in range(7)] + ["plaq0", "plaq1"])


class VariantCodec(Codec):
    """Codec with the extra-bit assignment (interior id 0..255, corner id 0..7); id 0/0 = Codec."""

    def __init__(self, basis, interior: int = 0, corner: int = 0):
        self.interior = int(interior)
        self.corner = int(corner)
        super().__init__(basis)

    def _ib(self, i):
        return (self.interior >> i) & 1

    def _cb(self, i):
        return (self.corner >> i) & 1

    def encode_vertex(self, s, flux, n, iota):
        if self.basis.lat.is_static(s):
            return super().encode_vertex(s, flux, n, iota)
        flux = tuple(int(x) for x in flux)
        k, f = len(flux), sum(flux)
        if k == 2:
            if flux[0] == flux[1]:
                assert n in (0, 2) and iota == 0
                return (*flux, (n // 2) ^ self._cb(0 if flux == (0, 0) else 1))
            assert n == 1 and iota == 0
            return (*flux, self._cb(2))
        if f % 2 == 0:
            assert n in (0, 2) and iota == 0
            return (*flux, (n // 2) ^ self._ib(EVEN.index(flux)))
        if f == 1:
            assert n == 1 and iota == 0
            return (*flux, self._ib(4 + ONE.index(flux)))
        assert n == 1
        return (*flux, int(iota) ^ self._ib(7))

    def decode_vertex(self, s, bits):
        if self.basis.lat.is_static(s):
            return super().decode_vertex(s, bits)
        k = len(self.ends[s])
        flux = tuple(int(x) for x in bits[:k])
        f = sum(flux)
        b = int(bits[k])
        if k == 2:
            if flux[0] == flux[1]:
                return flux, 2 * (b ^ self._cb(0 if flux == (0, 0) else 1)), 0
            if b != self._cb(2):
                raise Reject("flag")
            return flux, 1, 0
        if f % 2 == 0:
            return flux, 2 * (b ^ self._ib(EVEN.index(flux))), 0
        if f == 1:
            if b != self._ib(4 + ONE.index(flux)):
                raise Reject("flag")
            return flux, 1, 0
        return flux, 1, b ^ self._ib(7)


_G = {}


def _setup():
    if not _G:
        from skqd.exact import Model
        M = Model(3)
        _G["M"] = M
        _G["dt"] = float(M.reference(G2, 0).dt)
    return _G


def term_op_support(M, codec, term):
    from skqd.reference_sim import term_support
    if term.startswith("hop"):
        l = int(term[3:])
        return M.terms.hop[l], term_support(M, "hop", l, codec=codec)
    P = int(term[4:])
    return -M.terms.plaq[P] / (2 * G2), term_support(M, "plaq", P, codec=codec)


def term_ir(M, codec, term, dt):
    from skqd.circuits_ir import structured_term_gates
    O, sup = term_op_support(M, codec, term)
    return structured_term_gates(M, O, sup, dt, codec=codec)


def cz_of(gates, n, seed=7):
    from skqd import circuits_qiskit as cq
    return int(cq.transpile_counts(gates, n, seed=seed)["cz"])


def score(job):
    kind, aid, terms = job
    G = _setup()
    M, dt = G["M"], G["dt"]
    c = VariantCodec(M.basis, interior=aid if kind == "interior" else 0, corner=aid if kind == "corner" else 0)
    per = {}
    for t in terms:
        per[t] = cz_of(term_ir(M, c, t, dt), c.n_qubits)
    return kind, aid, per


def detection(codec, basis):
    from skqd.codec import Reject as Rj
    out = {}
    for twoB in (0, 2):
        idx = basis.sector(twoB)
        tot = det = 0
        for k in idx:
            c = codec.encode(basis.labels[k])
            for q in range(codec.n_qubits):
                cc = list(c)
                cc[q] ^= 1
                tot += 1
                try:
                    codec.decode(tuple(cc), twoB)
                except Rj:
                    det += 1
        out[f"B={twoB // 2}"] = {"single_flips": tot, "detected": det, "detected_fraction": det / tot}
    return out


def run(quick=False, workers=6, log=print):
    import multiprocessing as mp
    t0 = time.time()
    G = _setup()
    M, dt = G["M"], G["dt"]
    base = Codec(M.basis)
    v0 = VariantCodec(M.basis, 0, 0)
    same = bool(np.array_equal(base.all_codewords(), v0.all_codewords()))
    if not same:
        raise SystemExit("VariantCodec(0, 0) does not reproduce the current codewords")
    interior_ids = list(range(256))
    corner_ids = list(range(8))
    if quick:
        rng = np.random.default_rng(7)
        interior_ids = sorted({0} | set(int(x) for x in rng.choice(np.arange(1, 256), 23, replace=False)))
    jobs = [("interior", a, INTERIOR_TERMS) for a in interior_ids] + [("corner", a, CORNER_TERMS) for a in corner_ids]
    log(f"assign: {len(jobs)} assignments on {workers} workers")
    res = {"interior": {}, "corner": {}}
    ctx = mp.get_context("fork")
    with ctx.Pool(workers) as pool:
        for i, (kind, aid, per) in enumerate(pool.imap_unordered(score, jobs)):
            res[kind][aid] = per
            if (i + 1) % 20 == 0 or i + 1 == len(jobs):
                log(f"  assign {i + 1}/{len(jobs)}")
    tot = {kind: {a: sum(v.values()) for a, v in res[kind].items()} for kind in res}
    best_i = min(tot["interior"], key=lambda a: (tot["interior"][a], a))
    best_c = min(tot["corner"], key=lambda a: (tot["corner"][a], a))
    # the nine-term coarse step (no diag), current and best
    step = {}
    for lab, (ai, ac) in (("current", (0, 0)), ("best", (best_i, best_c))):
        c = VariantCodec(M.basis, ai, ac)
        gates = []
        for t in STEP_TERMS:
            gates += term_ir(M, c, t, dt)
        step[lab] = {"interior": ai, "corner": ac, "cz_a2a_seed7": cz_of(gates, c.n_qubits),
                     "per_term": {t: cz_of(term_ir(M, c, t, dt), c.n_qubits) for t in STEP_TERMS}}
        log(f"assign step {lab}: {step[lab]['cz_a2a_seed7']} CZ")
    best = VariantCodec(M.basis, best_i, best_c)
    rt = all(best.decode(best.encode(lab))[0] == k for k, lab in enumerate(M.basis.labels))
    det_cur, det_best = detection(base, M.basis), detection(best, M.basis)
    unchanged = all(det_cur[s]["detected_fraction"] == det_best[s]["detected_fraction"] for s in det_cur)
    return {"what": "E5' codeword-assignment search inside the current widths (flux bits fixed)",
            "assignment_encoding": __doc__.split("Score =")[0].strip(), "quick": bool(quick),
            "n_interior_scored": len(res["interior"]), "n_corner_scored": len(res["corner"]),
            "interior_terms": list(INTERIOR_TERMS), "corner_terms": list(CORNER_TERMS),
            "transpile": "skqd.circuits_qiskit.transpile_counts: basis rz/sx/x/cz, level 3, seed 7, all-to-all",
            "dt": dt, "current_reproduced_by_variant_0_0": same,
            "scores_interior": {str(a): {"per_term": res["interior"][a], "total": tot["interior"][a]} for a in sorted(res["interior"])},
            "scores_corner": {str(a): {"per_term": res["corner"][a], "total": tot["corner"][a]} for a in sorted(res["corner"])},
            "current_interior_score": tot["interior"][0], "current_corner_score": tot["corner"][0],
            "best_interior": best_i, "best_interior_score": tot["interior"][best_i],
            "best_corner": best_c, "best_corner_score": tot["corner"][best_c],
            "interior_score_range": [min(tot["interior"].values()), max(tot["interior"].values())],
            "corner_score_range": [min(tot["corner"].values()), max(tot["corner"].values())],
            "step": step, "current_step_cz": step["current"]["cz_a2a_seed7"], "best_step_cz": step["best"]["cz_a2a_seed7"],
            "best_step_cz_ratio": step["best"]["cz_a2a_seed7"] / step["current"]["cz_a2a_seed7"],
            "best_round_trip": bool(rt), "detection_current": det_cur, "detection_best": det_best,
            "detection_unchanged": bool(unchanged), "runtime_s": time.time() - t0,
            "diag_note": "diag excluded on both sides: CircuitFactory.diag_gates is written for the current polarities"}


if __name__ == "__main__":
    import json
    r = run(quick="--quick" in sys.argv)
    print(json.dumps({k: r[k] for k in ("best_interior", "best_corner", "current_step_cz", "best_step_cz",
                                        "best_step_cz_ratio", "detection_unchanged")}, indent=1))

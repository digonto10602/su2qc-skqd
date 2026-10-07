"""
Planner prototype (2026-10-07, prompts/34): qubit counts of candidate encodings, the
single-fault detection of the present codec versus a de-duplicated ("dedup") codec, the
random decoder acceptance of both, and a structured compile of the dedup codec through the
package's own `structured_term_gates` (monkey-patched codec) at 2x2 and 2x3.

Everything here is PLANNER ARITHMETIC / PROTOTYPE: not a gate, not a validation JSON.
Output: scratch/planner/encodings_prototype_20261007.json  (+ .log via tee).

Dedup codec layout (uncharged vertices only):
    qubits 0 .. n_links-1      : flux bit of link l  (j = 1/2 <=> 1)         -- stored ONCE
    qubits n_links + s         : one bit per vertex s
        corner:   flux equal   -> bit = n/2 ;  flux unequal -> n = 1, bit must be 0 (1 = flag)
        interior: f even       -> bit = n/2 ;  f = 1 -> n = 1, bit 0 (1 = flag) ;  f = 3 -> n = 1, bit = iota
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, "src")
from skqd.basis import Basis, enumerate_basis  # noqa: E402
from skqd.codec import Codec, Reject  # noqa: E402
from skqd.lattice import Ladder  # noqa: E402

OUT = "scratch/planner/encodings_prototype_20261007.json"
T0 = time.time()
R = {"produced_by": "scratch/planner/encodings_prototype_20261007.py", "date": "2026-10-07",
     "status": "PLANNER PROTOTYPE (not a gate)", "sections": {}}


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


# ----------------------------------------------------------------------------- A. counts
def counts_section():
    out = {}
    for Lx in (2, 3, 4):
        lat = Ladder(Lx)
        basis = enumerate_basis(lat)
        ends = lat.ends()
        n_corner = sum(1 for s in range(lat.n_sites) if len(ends[s]) == 2)
        n_int = sum(1 for s in range(lat.n_sites) if len(ends[s]) == 3)
        dims = basis.sector_dims()
        d0, d1 = dims[0], dims[2]
        nl, ns, nP = lat.n_links, lat.n_sites, len(lat.plaquettes)
        row = {
            "n_sites": ns, "n_links": nl, "n_plaquettes": nP, "corners": n_corner, "interior": n_int,
            "dim_total": basis.dim, "dim_B0": d0, "dim_B1": d1,
            "E1_current_2nl_plus_ns": 2 * nl + ns,
            "E1_check_codec": Codec(basis).n_qubits,
            "E2_dedup_nl_plus_ns": nl + ns,
            "E3_dedup_plus_vertex_parity_nl_plus_2ns": nl + 2 * ns,
            "E4_dense_sector_B0_ceil_log2": math.ceil(math.log2(d0)),
            "E4_dense_sector_B1_ceil_log2": math.ceil(math.log2(d1)),
            "E4_dense_full_ceil_log2": math.ceil(math.log2(basis.dim)),
            "E5_vertex_dense_no_link_dup_note": "identical to E2 (the vertex block is already dense: 6/13 states in 3/4 bits)",
            "E6_LSH_unary_loops_3corner_5interior": 3 * n_corner + 5 * n_int,
            "E6_LSH_dense_interior_equals_E1": 3 * n_corner + 4 * n_int,
            "E7_schwinger_boson_4nl_plus_2ns": 4 * nl + 2 * ns,
            "E7b_kogut_susskind_jmL_mR_3nl_plus_2ns": 3 * nl + 2 * ns,
            "E8_fermion_plus_loop_links_2ns_plus_3nP": 2 * ns + 3 * nP,
            "E8_tree_links_eliminated": nl - (ns - 1),
            "E10_qudit_levels_corner_interior": [6, 13],
            "random_acceptance_E1_B0": d0 / 2 ** (2 * nl + ns),
            "random_acceptance_E2_B0": d0 / 2 ** (nl + ns),
            "random_acceptance_E4_B0": d0 / 2 ** math.ceil(math.log2(d0)),
            "C22_saturation_shots_E1_B0_(5x2^n)": 5 * 2 ** (2 * nl + ns),
            "C22_saturation_shots_E2_B0_(5x2^n)": 5 * 2 ** (nl + ns),
            "C22_saturation_shots_E4_B0_(5x2^n)": 5 * 2 ** math.ceil(math.log2(d0)),
        }
        out[f"2x{Lx}"] = row
        log(f"counts 2x{Lx}: {row}")
    return out


# ----------------------------------------------------------------------- B. dedup codec
@dataclass
class DedupCodec:
    basis: Basis

    def __post_init__(self):
        lat = self.basis.lat
        self.ends = lat.ends()
        for s in range(lat.n_sites):
            if lat.is_static(s):
                raise NotImplementedError("dedup prototype: uncharged vertices only")
        self.nl = lat.n_links
        self.n_qubits = lat.n_links + lat.n_sites
        # attributes some package code reads (term_support reads offsets/widths; we do not use it)
        self.offsets = np.array([self.nl + s for s in range(lat.n_sites)])
        self.widths = [1] * lat.n_sites

    def _vbit(self, s, flux, n, iota):
        k = len(flux)
        f = sum(flux)
        if k == 2:
            if flux[0] == flux[1]:
                assert n in (0, 2) and iota == 0
                return n // 2
            assert n == 1 and iota == 0
            return 0
        if f % 2 == 0:
            assert n in (0, 2) and iota == 0
            return n // 2
        if f == 1:
            assert n == 1 and iota == 0
            return 0
        assert n == 1
        return iota

    def encode(self, label):
        j2, n, iota = label
        bits = list(j2)
        for s in range(self.basis.lat.n_sites):
            flux = tuple(j2[l] for l, _ in self.ends[s])
            bits.append(self._vbit(s, flux, n[s], iota[s]))
        return tuple(bits)

    def decode(self, bits, target_twoB=None):
        lat = self.basis.lat
        j2 = tuple(int(b) for b in bits[:self.nl])
        n, iota = [], []
        for s in range(lat.n_sites):
            flux = tuple(j2[l] for l, _ in self.ends[s])
            b = int(bits[self.nl + s])
            k, f = len(flux), sum(flux)
            if k == 2:
                if flux[0] == flux[1]:
                    n.append(2 * b); iota.append(0)
                else:
                    if b:
                        raise Reject("flag")
                    n.append(1); iota.append(0)
            else:
                if f % 2 == 0:
                    n.append(2 * b); iota.append(0)
                elif f == 1:
                    if b:
                        raise Reject("flag")
                    n.append(1); iota.append(0)
                else:
                    n.append(1); iota.append(b)
        label = (j2, tuple(n), tuple(iota))
        if target_twoB is not None:
            twoB = sum(n[s] - lat.n_vac(s) for s in range(lat.n_sites))
            if twoB != target_twoB:
                raise Reject("sector")
        try:
            return self.basis.index[label], label
        except KeyError:
            raise Reject("unknown")

    def all_codewords(self):
        return np.array([self.encode(b) for b in self.basis.labels], dtype=np.int8)

    # qubits a term may act on (all link bits and vertex bits of the touched vertices, plus the
    # link bits of the sites strictly between x and y for the Jordan-Wigner parity)
    def support(self, kind, index):
        lat = self.basis.lat
        q = set()
        if kind == "hop":
            x, y, _ = lat.links[index]
            for s in (x, y):
                q.update(l for l, _ in self.ends[s]); q.add(self.nl + s)
            for z in range(x + 1, y):
                q.update(l for l, _ in self.ends[z])
        elif kind == "plaq":
            pl = lat.plaquettes[index]
            for s in (pl["c00"], pl["c10"], pl["c11"], pl["c01"]):
                q.update(l for l, _ in self.ends[s]); q.add(self.nl + s)
        else:
            q = set(range(self.n_qubits))
        return sorted(q)


# ---------------------------------------------------------------- C. fault detection
def detection_section(Lx, codec, name, max_pairs=True):
    basis = codec.basis
    n = codec.n_qubits
    out = {}
    for twoB in (0, 2):
        idx = basis.sector(twoB)
        cw = [codec.encode(basis.labels[k]) for k in idx]
        # round trip
        for k, c in zip(idx, cw):
            kk, _ = codec.decode(c, twoB)
            assert kk == k
        det = {"flag": 0, "link": 0, "sector": 0, "unknown": 0}
        silent_same = 0      # accepted as a DIFFERENT valid state of the same sector
        silent_self = 0
        total = 0
        for k, c in zip(idx, cw):
            for q in range(n):
                cc = list(c); cc[q] ^= 1
                total += 1
                try:
                    kk, _ = codec.decode(tuple(cc), twoB)
                    if kk == k:
                        silent_self += 1
                    else:
                        silent_same += 1
                except Reject as r:
                    det[str(r)] += 1
        row = {"n_qubits": n, "dim": len(idx), "single_flips": total,
               "detected": sum(det.values()), "detected_by": det,
               "silent_accepted": silent_same, "silent_self": silent_self,
               "detected_fraction": sum(det.values()) / total,
               "random_acceptance": len(idx) / 2 ** n}
        if max_pairs:
            det2 = 0; sil2 = 0; tot2 = 0
            for k, c in zip(idx, cw):
                for q1 in range(n):
                    for q2 in range(q1 + 1, n):
                        cc = list(c); cc[q1] ^= 1; cc[q2] ^= 1
                        tot2 += 1
                        try:
                            codec.decode(tuple(cc), twoB); sil2 += 1
                        except Reject:
                            det2 += 1
            row.update(double_flips=tot2, double_detected=det2, double_silent=sil2,
                       double_detected_fraction=det2 / tot2)
        out[f"B={twoB // 2}"] = row
        log(f"detection 2x{Lx} {name} 2B={twoB}: {row}")
    return out


# ------------------------------------------------------------- D. structured compile
def compile_section(Lx, g2=4.0, heavy_hex=None, do_route=True):
    import skqd.reference_sim as rs
    import skqd.circuits_ir as ci
    from skqd.exact import Model
    from skqd.circuits_ir import structured_term_gates, run_ir, gate_counts
    from skqd import circuits_qiskit as cq
    from qiskit.transpiler import CouplingMap
    import scipy.sparse.linalg as spl

    M = Model(Lx)
    dt = M.reference(g2, 0).dt
    out = {"dt_B0": dt, "terms": {}}
    rng = np.random.default_rng(7)
    terms = [(f"hop{l}", M.terms.hop[l], "hop", l) for l in range(M.lat.n_links)]
    terms += [(f"plaq{P}", -M.terms.plaq[P] / (2 * g2), "plaq", P) for P in range(len(M.lat.plaquettes))]

    for enc in ("current", "dedup"):
        if enc == "current":
            rs.Codec = Codec; ci.Codec = Codec
            codec = Codec(M.basis)
            sup_of = lambda kind, i: rs.term_support(M, kind, i)
        else:
            rs.Codec = DedupCodec; ci.Codec = DedupCodec
            codec = DedupCodec(M.basis)
            sup_of = codec.support
        n = codec.n_qubits
        cw = codec.all_codewords()
        ints = np.array([int("".join(str(b) for b in c[::-1]), 2) for c in cw])  # qubit k = bit k
        step = []
        rows = {}
        for name, O, kind, i in terms:
            sup = sup_of(kind, i)
            t1 = time.time()
            st = []
            gates = structured_term_gates(M, O, sup, dt, stats=st)
            tcomp = time.time() - t1
            # verify on 3 random superpositions of all codewords
            worst = 0.0
            for _ in range(3):
                c = rng.normal(size=M.basis.dim) + 1j * rng.normal(size=M.basis.dim)
                c /= np.linalg.norm(c)
                psi = np.zeros(2 ** n, dtype=complex); psi[ints] = c
                ref = spl.expm_multiply(-1j * dt * O, c)
                got = run_ir(gates, n, psi)
                full = np.zeros(2 ** n, dtype=complex); full[ints] = ref
                worst = max(worst, float(np.linalg.norm(got - full)))
            gc = gate_counts(gates)
            a2a = cq.transpile_counts(gates, n)
            row = {"support": len(sup), "ir_cx": int(gc.get("cx", 0)), "n_multiplexed": len(st),
                   "controls": [e["n_controls"] for e in st], "verify_max_dev": worst,
                   "cz_all_to_all": a2a["cz"], "depth_all_to_all": a2a["depth"], "compile_s": tcomp}
            if do_route and heavy_hex:
                rr = cq.transpile_counts(gates, n, coupling_map=CouplingMap.from_heavy_hex(heavy_hex))
                row.update(cz_routed=rr["cz"], depth_routed=rr["depth"])
            rows[name] = row
            step += gates
            log(f"compile 2x{Lx} {enc} {name}: {row}")
        tot = cq.transpile_counts(step, n)
        rows["_step_without_diag"] = {"cz_all_to_all": tot["cz"], "depth_all_to_all": tot["depth"],
                                      "ops": tot["ops"], "n_qubits": n}
        if do_route and heavy_hex:
            rr = cq.transpile_counts(step, n, coupling_map=CouplingMap.from_heavy_hex(heavy_hex))
            rows["_step_without_diag"].update(cz_routed=rr["cz"], depth_routed=rr["depth"],
                                              n_qubits_routed=rr["n_qubits"])
        log(f"compile 2x{Lx} {enc} STEP(no diag): {rows['_step_without_diag']}")
        out["terms"][enc] = rows
    rs.Codec = Codec; ci.Codec = Codec
    return out


# ------------------------------------------------------ E. dense-sector synthesis (2x2)
def dense_section():
    from skqd.exact import Model
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import UnitaryGate
    import scipy.linalg as sla
    M = Model(2)
    g2 = 4.0
    out = {}
    for twoB in (0, 2):
        ref = M.reference(g2, twoB)
        H = M.H(g2)[ref.indices][:, ref.indices].toarray()
        d = H.shape[0]
        nq = math.ceil(math.log2(d))
        U = np.eye(2 ** nq, dtype=complex)
        U[:d, :d] = sla.expm(-1j * ref.dt * H)
        qc = QuantumCircuit(nq)
        qc.append(UnitaryGate(U), list(range(nq)))
        tq = transpile(qc, basis_gates=["rz", "sx", "x", "cz"], optimization_level=3, seed_transpiler=7)
        ops = dict(tq.count_ops())
        out[f"B={twoB // 2}"] = {"dim": d, "n_qubits": nq, "cz": int(ops.get("cz", 0)), "depth": tq.depth(),
                            "qsd_bound_23_48_4n": 23 / 48 * 4 ** nq}
        log(f"dense 2x2 2B={twoB}: {out[f'B={twoB // 2}']}")
    for nq in (10, 14):
        out[f"qsd_bound_n{nq}"] = 23 / 48 * 4 ** nq
    return out


if __name__ == "__main__":
    R["sections"]["A_counts"] = counts_section()
    det = {}
    for Lx in (2, 3):
        basis = enumerate_basis(Ladder(Lx))
        det[f"2x{Lx}"] = {"current": detection_section(Lx, Codec(basis), "current", max_pairs=(Lx == 2)),
                          "dedup": detection_section(Lx, DedupCodec(basis), "dedup", max_pairs=(Lx == 2))}
    R["sections"]["C_detection"] = det
    R["sections"]["E_dense_2x2"] = dense_section()
    comp = {"2x2": compile_section(2, heavy_hex=3)}
    json.dump(R | {"sections": R["sections"] | {"D_compile": comp}}, open(OUT, "w"), indent=1, default=float)
    if "--2x3" in sys.argv:
        comp["2x3"] = compile_section(3, heavy_hex=5, do_route=("--route" in sys.argv))
    R["sections"]["D_compile"] = comp
    R["runtime_s"] = time.time() - T0
    json.dump(R, open(OUT, "w"), indent=1, default=float)
    log("written", OUT)

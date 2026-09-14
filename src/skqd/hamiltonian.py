"""
Dressed-site Hamiltonian builder — Step 3 / Algorithm 2 of the SKQD manual.

H = -1/2 sum_{l=(x->y)} [ eta_l psi^dag_{x,i} U_ij(l) psi_{y,j} + h.c. ]
    + m sum_x (-1)^{x1+x2} n_x
    + g^2/2 sum_l E_l^2
    - 1/(2 g^2) sum_P (W_P + W_P^dag),
W_P = sum_{ijkl} U_ij(l_b) U_jk(l_r) (U_lk(l_t))^dag (U_il(l_l))^dag  (counter-clockwise
from the lower-left corner), links truncated at jmax in the electric basis.

Matrix elements between dressed-site states are obtained by local contraction
(eq. 4 of the manual): the local singlet tensors of the touched vertices, the
link operator blocks, the site Fock operators, and the Jordan-Wigner sign
s_JW = prod_{x<z<y} (-1)^{n_z} for a hopping term psi^dag_x psi_y with the
intra-site signs absorbed into F_x = psi^loc_dag_{x,i} P_x and F_y = psi^loc_{y,j}
(x < y, which always holds for the ladder's link orientation).

The builder returns the term matrices separately:
    terms['mass']      : diag  sum_x (-1)^{x1+x2} n_x
    terms['electric']  : diag  sum_l j_l (j_l + 1)
    terms['hop'][l]    : -(eta_l/2) sum_ij psi^dag_x U_ij psi_y + h.c.   (one per link)
    terms['plaq'][P]   : W_P + W_P^dag                                    (one per plaquette)
and  H(g^2, m) = m*mass + (g^2/2)*electric + sum_l hop[l] - 1/(2 g^2) sum_P plaq[P].

Symbols: g^2 = gauge coupling, m = staggered quark mass, eta_l = staggered
hopping phase, E_l^2 = j_l(j_l+1) electric Casimir, n_x = quark occupation.
"""
from __future__ import annotations

import itertools
import string
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

from .basis import Basis
from .fermions import PARITY, PSI
from .su2 import LinkSpace
from .vertex import vertex_tensors

_LETTERS = string.ascii_letters


class _Letters:
    def __init__(self):
        self.k = 0

    def new(self):
        c = _LETTERS[self.k]
        self.k += 1
        return c


@dataclass
class Terms:
    mass: sp.csr_matrix
    electric: sp.csr_matrix
    hop: list
    plaq: list

    def H(self, g2: float, m: float) -> sp.csr_matrix:
        H = m * self.mass + 0.5 * g2 * self.electric
        for h in self.hop:
            H = H + h
        for w in self.plaq:
            H = H - w / (2.0 * g2)
        return sp.csr_matrix(H)

    def groups(self, g2: float, m: float) -> dict:
        """Term groups gamma used by the coarse single-step circuits."""
        out = {"diag": m * self.mass + 0.5 * g2 * self.electric}
        for l, h in enumerate(self.hop):
            out[f"hop{l}"] = h
        for p, w in enumerate(self.plaq):
            out[f"plaq{p}"] = -w / (2.0 * g2)
        return out


class HamiltonianBuilder:
    def __init__(self, basis: Basis):
        self.basis = basis
        self.lat = basis.lat
        self.link = LinkSpace(basis.jmax)
        self.ends = self.lat.ends()
        U = self.link.U()
        self._U = U
        self._Udag = [[U[a][b].conj().T for b in range(2)] for a in range(2)]
        self._cache_hop = {}
        self._cache_plaq = {}
        # site operators for hopping: F_x[i] = psi_dag_i P, F_y[j] = psi_j
        self.Fx = np.array([PSI[i].conj().T @ PARITY for i in range(2)])  # [i, c', c]
        self.Fy = np.array([PSI[j] for j in range(2)])                     # [j, c', c]

    # ------------------------------------------------------------------ helpers
    def _block(self, M, jp, j):
        """Block <j' .| M |j .> reshaped to [d', d', d, d] (mL', mR', mL, mR)."""
        a0, a1 = self.link.block(jp)
        b0, b1 = self.link.block(j)
        dp, d = int(round(2 * jp + 1)), int(round(2 * j + 1))
        return M[a0:a1, b0:b1].reshape(dp, dp, d, d)

    def local_label(self, b, s):
        j2, n, iota = b
        return (tuple(j2[l] for l, _ in self.ends[s]), n[s], iota[s])

    def tensor(self, s, loc):
        js, n, iota = loc
        sig = tuple((jj / 2, role) for jj, (_, role) in zip(js, self.ends[s]))
        return vertex_tensors(sig, n, self.lat.is_static(s))[iota]

    def _vertex_axes(self, s, touched_links, letters, bra, ket, matter_bra=None, matter_ket=None):
        """Assign einsum letters to the axes of the bra and ket tensors of vertex s.
        Returns (bra_subscript, ket_subscript, dict link -> (bra letter, ket letter))."""
        bsub, ksub, lk = [], [], {}
        for l, role in self.ends[s]:
            if l in touched_links:
                lb, lkk = letters.new(), letters.new()
                lk[l] = (lb, lkk)
                bsub.append(lb)
                ksub.append(lkk)
            else:
                c = letters.new()
                bsub.append(c)
                ksub.append(c)
        if matter_bra is None:
            c = letters.new()
            bsub.append(c)
            ksub.append(c)
        else:
            bsub.append(matter_bra)
            ksub.append(matter_ket)
        if self.lat.is_static(s):
            c = letters.new()
            bsub.append(c)
            ksub.append(c)
        return "".join(bsub), "".join(ksub), lk

    # ------------------------------------------------------------ hopping term
    def hopping_element(self, l, loc_bra_x, loc_bra_y, loc_ket_x, loc_ket_y):
        """<b'| sum_ij psi^dag_{x,i} U_ij(l) psi_{y,j} |b>  without eta, 1/2 and JW sign."""
        key = (l, loc_bra_x, loc_bra_y, loc_ket_x, loc_ket_y)
        if key in self._cache_hop:
            return self._cache_hop[key]
        x, y, _ = self.lat.links[l]
        letters = _Letters()
        ci, cj = letters.new(), letters.new()           # colour indices
        cxb, cxk, cyb, cyk = (letters.new() for _ in range(4))
        bx, kx, lkx = self._vertex_axes(x, {l}, letters, None, None, cxb, cxk)
        by, ky, lky = self._vertex_axes(y, {l}, letters, None, None, cyb, cyk)
        mLp, mL = lkx[l]
        mRp, mR = lky[l]
        jp = loc_bra_x[0][[ll for ll, _ in self.ends[x]].index(l)] / 2
        j = loc_ket_x[0][[ll for ll, _ in self.ends[x]].index(l)] / 2
        Ublk = np.array([[self._block(self._U[a][b], jp, j) for b in range(2)] for a in range(2)])
        sub = (
            f"{bx},{by},{ci}{cj}{mLp}{mRp}{mL}{mR},{ci}{cxb}{cxk},{cj}{cyb}{cyk},{kx},{ky}->"
        )
        val = np.einsum(
            sub,
            self.tensor(x, loc_bra_x).conj(), self.tensor(y, loc_bra_y).conj(),
            Ublk, self.Fx, self.Fy,
            self.tensor(x, loc_ket_x), self.tensor(y, loc_ket_y),
            optimize=True,
        )
        val = complex(val)
        self._cache_hop[key] = val
        return val

    # ---------------------------------------------------------- plaquette term
    def plaquette_element(self, P, loc_bra: tuple, loc_ket: tuple):
        """<b'| W_P |b> for the local labels of the four corners (c00, c10, c11, c01)."""
        key = (P, loc_bra, loc_ket)
        if key in self._cache_plaq:
            return self._cache_plaq[key]
        pl = self.lat.plaquettes[P]
        corners = [pl["c00"], pl["c10"], pl["c11"], pl["c01"]]
        links = {"b": pl["b"], "r": pl["r"], "t": pl["t"], "l": pl["l"]}
        touched = set(links.values())
        letters = _Letters()
        ci, cj, ck, cl = (letters.new() for _ in range(4))
        subs_bra, subs_ket, lk = [], [], {}
        for s, lb, lkt in zip(corners, loc_bra, loc_ket):
            bs, ks, lks = self._vertex_axes(s, touched, letters, None, None)
            subs_bra.append(bs)
            subs_ket.append(ks)
            for l, pair in lks.items():
                lk.setdefault(l, {})
                role = dict(self.ends[s])[l]
                lk[l][role] = pair  # (bra letter, ket letter) of the mL ('out') or mR ('in') index

        def jpair(l):
            # (j', j) on link l from the corner that owns its 'out' end
            for s, lb, lkt in zip(corners, loc_bra, loc_ket):
                ends_s = [ll for ll, _ in self.ends[s]]
                if l in ends_s:
                    k = ends_s.index(l)
                    return lb[0][k] / 2, lkt[0][k] / 2
            raise KeyError

        ops, subs = [], []
        # U_ij on b, U_jk on r, (U_lk)^dag on t, (U_il)^dag on l
        for name, colours, M in (("b", ci + cj, self._U), ("r", cj + ck, self._U),
                                 ("t", cl + ck, self._Udag), ("l", ci + cl, self._Udag)):
            l = links[name]
            jp, j = jpair(l)
            blk = np.array([[self._block(M[a][b], jp, j) for b in range(2)] for a in range(2)])
            (mLp, mL), (mRp, mR) = lk[l]["out"], lk[l]["in"]
            ops.append(blk)
            subs.append(f"{colours}{mLp}{mRp}{mL}{mR}")
        operands = [self.tensor(s, lb).conj() for s, lb in zip(corners, loc_bra)] + ops + \
                   [self.tensor(s, lkt) for s, lkt in zip(corners, loc_ket)]
        sub = ",".join(subs_bra + subs + subs_ket) + "->"
        val = complex(np.einsum(sub, *operands, optimize=True))
        self._cache_plaq[key] = val
        return val

    # ------------------------------------------------------------------ build
    def build(self, verbose=False) -> Terms:
        basis = self.basis
        lat = self.lat
        N = basis.dim
        spins2 = list(range(int(round(2 * basis.jmax)) + 1))
        # diagonal terms
        mass = np.array([sum((1 if lat.parity(s) == 0 else -1) * n[s] for s in range(lat.n_sites))
                         for (_, n, _) in basis.labels], dtype=float)
        elec = np.array([sum((jj / 2) * (jj / 2 + 1) for jj in j2) for (j2, _, _) in basis.labels])
        # hopping
        hop = []
        for l, (x, y, _) in enumerate(lat.links):
            rows, cols, vals = [], [], []
            eta = lat.eta(l)
            for kb, b in enumerate(basis.labels):
                j2, n, iota = b
                if n[x] >= 2 or n[y] <= 0:
                    continue
                s_jw = (-1) ** sum(n[z] for z in range(x + 1, y))
                for j2p in (j2[l] - 1, j2[l] + 1):
                    if j2p not in spins2:
                        continue
                    j2n = list(j2)
                    j2n[l] = j2p
                    nn = list(n)
                    nn[x] += 1
                    nn[y] -= 1
                    j2n, nn = tuple(j2n), tuple(nn)
                    kx = self._kdim(x, j2n, nn[x])
                    ky = self._kdim(y, j2n, nn[y])
                    for ix in range(kx):
                        for iy in range(ky):
                            io = list(iota)
                            io[x], io[y] = ix, iy
                            bp = (j2n, nn, tuple(io))
                            kbp = basis.index[bp]
                            v = self.hopping_element(
                                l,
                                self.local_label(bp, x), self.local_label(bp, y),
                                self.local_label(b, x), self.local_label(b, y),
                            )
                            v = -0.5 * eta * s_jw * v
                            if abs(v) > 1e-14:
                                rows.append(kbp); cols.append(kb); vals.append(v)
            T = sp.coo_matrix((vals, (rows, cols)), shape=(N, N), dtype=complex).tocsr()
            hop.append(sp.csr_matrix(T + T.conj().T))
            if verbose:
                print(f"  hop link {l}: {T.nnz} elements, cache {len(self._cache_hop)}")
        # plaquettes
        plaq = []
        for P, pl in enumerate(lat.plaquettes):
            corners = [pl["c00"], pl["c10"], pl["c11"], pl["c01"]]
            plinks = [pl["b"], pl["r"], pl["t"], pl["l"]]
            rows, cols, vals = [], [], []
            for kb, b in enumerate(basis.labels):
                j2, n, iota = b
                choices = []
                for l in plinks:
                    choices.append([jp for jp in (j2[l] - 1, j2[l] + 1) if jp in spins2])
                for jps in itertools.product(*choices):
                    j2n = list(j2)
                    for l, jp in zip(plinks, jps):
                        j2n[l] = jp
                    j2n = tuple(j2n)
                    kd = [self._kdim(s, j2n, n[s]) for s in corners]
                    if min(kd) == 0:
                        continue
                    for ios in itertools.product(*[range(k) for k in kd]):
                        io = list(iota)
                        for s, i_ in zip(corners, ios):
                            io[s] = i_
                        bp = (j2n, n, tuple(io))
                        kbp = basis.index[bp]
                        v = self.plaquette_element(
                            P,
                            tuple(self.local_label(bp, s) for s in corners),
                            tuple(self.local_label(b, s) for s in corners),
                        )
                        if abs(v) > 1e-14:
                            rows.append(kbp); cols.append(kb); vals.append(v)
            W = sp.coo_matrix((vals, (rows, cols)), shape=(N, N), dtype=complex).tocsr()
            plaq.append(sp.csr_matrix(W + W.conj().T))
            if verbose:
                print(f"  plaquette {P}: {W.nnz} elements, cache {len(self._cache_plaq)}")
        return Terms(mass=sp.diags(mass).tocsr(), electric=sp.diags(elec).tocsr(), hop=hop, plaq=plaq)

    def _kdim(self, s, j2, n):
        sig = tuple((j2[l] / 2, role) for l, role in self.ends[s])
        return len(vertex_tensors(sig, n, self.lat.is_static(s)))


def neighbours(H: sp.csr_matrix, B) -> np.ndarray:
    """Hamiltonian neighbours N(B): column support of H restricted to rows B, minus B."""
    B = np.asarray(sorted(set(int(b) for b in B)))
    sub = H[B, :]
    cols = np.unique(sub.indices)
    return np.setdiff1d(cols, B)

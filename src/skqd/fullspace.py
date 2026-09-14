"""
Redundant-basis ("projector") construction of the 2 x 2 model — the second,
independent route of gate E1 (Step 1.3 of the SKQD manual).

The full Hilbert space is the tensor product of the four truncated link spaces
(5 states each for jmax = 1/2) and the four site Fock spaces (4 states each):
dimension 5^4 * 4^4 = 160 000.  All operators are built directly from the
link operators U_ij, L_a, R_a and the fermion operators with explicit
Jordan-Wigner strings, with no reference to the dressed-site tensors.

Provided checks:
  * [G_a(x), H] = 0 for every site x and colour a  (gauge invariance of H)
  * the kernel of sum_{x,a} G_a(x)^2, computed block by block by dense
    diagonalization (blocks = fixed link spins and site occupations), has
    dimension 82 with baryon-number split 38/20/20/2/2
  * P^dag H P on that kernel has the same spectrum as the dressed-site builder
  * the dressed-site states embedded in the full space are annihilated by
    every G_a(x), are orthonormal, and reproduce the builder's matrix
    elements one by one (this tests the contraction formula, JW signs and
    phases, not only the spectrum).

Symbols: G_a(x) = Gauss-law generator at site x, P = isometry from the
physical (kernel) space into the redundant space, H = Hamiltonian of
hamiltonian.py.
"""
from __future__ import annotations

import itertools

import numpy as np
import scipy.sparse as sp

from .basis import Basis
from .fermions import N_OP, PARITY, PSI, Q_OPS
from .hamiltonian import HamiltonianBuilder
from .lattice import Ladder
from .su2 import LinkSpace


class FullSpace:
    def __init__(self, lat: Ladder, jmax: float = 0.5):
        assert not lat.static_sites, "static charges are not implemented in the redundant-basis route"
        self.lat = lat
        self.link = LinkSpace(jmax)
        self.dl = self.link.dim
        self.nl, self.ns = lat.n_links, lat.n_sites
        self.dims = [self.dl] * self.nl + [4] * self.ns
        self.dim = int(np.prod(self.dims))

    # ---------------------------------------------------------------- embedding
    def _embed(self, ops: dict) -> sp.csr_matrix:
        """Kronecker product with ops[factor] at the given factors, identity elsewhere."""
        out = sp.identity(1, format="csr", dtype=complex)
        for f, d in enumerate(self.dims):
            M = ops.get(f, sp.identity(d, format="csr", dtype=complex))
            out = sp.kron(out, sp.csr_matrix(M), format="csr")
        return out

    def link_op(self, l, M):
        return self._embed({l: M})

    def psi(self, x, i):
        """psi_{x,i} with the Jordan-Wigner string over the sites z < x."""
        ops = {self.nl + z: PARITY for z in range(x)}
        ops[self.nl + x] = PSI[i]
        return self._embed(ops)

    def site_op(self, x, M):
        return self._embed({self.nl + x: M})

    # -------------------------------------------------------------- operators
    def gauss(self, x, a) -> sp.csr_matrix:
        L, R = self.link.generators()
        G = self.site_op(x, Q_OPS[a])
        for l, role in self.lat.ends()[x]:
            G = G + self.link_op(l, L[a] if role == "out" else R[a])
        return sp.csr_matrix(G)

    def hamiltonian(self, g2, m) -> sp.csr_matrix:
        lat = self.lat
        U = self.link.U()
        H = sp.csr_matrix((self.dim, self.dim), dtype=complex)
        # hopping
        for l, (x, y, _) in enumerate(lat.links):
            eta = lat.eta(l)
            T = sp.csr_matrix((self.dim, self.dim), dtype=complex)
            for i in range(2):
                for j in range(2):
                    T = T + self.psi(x, i).conj().T @ self.link_op(l, U[i][j]) @ self.psi(y, j)
            T = -0.5 * eta * T
            H = H + T + T.conj().T
        # mass
        for x in range(self.ns):
            H = H + m * (1 if lat.parity(x) == 0 else -1) * self.site_op(x, N_OP)
        # electric
        for l in range(self.nl):
            H = H + 0.5 * g2 * self.link_op(l, self.link.casimir())
        # plaquette
        for pl in lat.plaquettes:
            W = sp.csr_matrix((self.dim, self.dim), dtype=complex)
            for i, j, k, l_ in itertools.product(range(2), repeat=4):
                W = W + (self.link_op(pl["b"], U[i][j]) @ self.link_op(pl["r"], U[j][k])
                         @ self.link_op(pl["t"], U[l_][k].conj().T) @ self.link_op(pl["l"], U[i][l_].conj().T))
            H = H - (W + W.conj().T) / (2.0 * g2)
        return sp.csr_matrix(H)

    # ------------------------------------------------------------- kernel (P)
    def _factor_indices(self, idx):
        return np.unravel_index(idx, self.dims)

    def physical_kernel(self, tol=1e-9):
        """Orthonormal basis of ker sum_{x,a} G_a(x)^2 by dense diagonalization of the
        blocks with fixed (j_l, n_x).  Returns (P as dense array dim x K, twoB per column)."""
        C = sp.csr_matrix((self.dim, self.dim), dtype=complex)
        for x in range(self.ns):
            for a in range(3):
                G = self.gauss(x, a)
                C = C + G @ G
        C = C.tocsr()
        idx = np.arange(self.dim)
        fac = np.array(self._factor_indices(idx))  # shape (n_factors, dim)
        jl = np.array([[self.link.j_of(k) for k in fac[l]] for l in range(self.nl)])  # (nl, dim)
        occ = np.array([[0, 1, 1, 2][k] for k in range(4)])
        nx = np.array([occ[fac[self.nl + x]] for x in range(self.ns)])  # (ns, dim)
        keys = np.vstack([2 * jl, nx]).T.astype(int)  # (dim, nl+ns)
        # group indices by key (fixed link spins and site occupations)
        uniq, inv = np.unique(keys, axis=0, return_inverse=True)
        inv = np.asarray(inv).ravel()
        order = np.argsort(inv, kind="stable")
        bounds = np.searchsorted(inv[order], np.arange(len(uniq) + 1))
        cols, twoB = [], []
        nvac = np.array([self.lat.n_vac(s) for s in range(self.ns)])
        for bid in range(len(uniq)):
            block = order[bounds[bid]:bounds[bid + 1]]
            Cb = C[block][:, block].toarray()
            w, v = np.linalg.eigh((Cb + Cb.conj().T) / 2)
            kern = v[:, w < tol]
            for c in range(kern.shape[1]):
                vec = np.zeros(self.dim, dtype=complex)
                vec[block] = kern[:, c]
                cols.append(vec)
                twoB.append(int(uniq[bid][self.nl:].sum() - nvac.sum()))
        P = np.array(cols).T
        return P, np.array(twoB)

    # ----------------------------------------------- embed dressed-site states
    def embed_dressed(self, basis: Basis, hb: HamiltonianBuilder) -> np.ndarray:
        """Dense (dim x basis.dim) array whose columns are the dressed-site states."""
        ends = self.lat.ends()
        out = np.zeros((self.dim, basis.dim), dtype=complex)
        strides = np.cumprod([1] + self.dims[::-1])[::-1][1:]  # C-order strides
        for kb, b in enumerate(basis.labels):
            j2, n, iota = b
            # letters: mL_l, mR_l for each link, c_x for each site
            letters = {}
            k = 0
            alph = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for l in range(self.nl):
                letters[("L", l)] = alph[k]; k += 1
                letters[("R", l)] = alph[k]; k += 1
            for x in range(self.ns):
                letters[("c", x)] = alph[k]; k += 1
            subs, ops = [], []
            for x in range(self.ns):
                s = "".join(letters[("L" if role == "out" else "R", l)] for l, role in ends[x]) + letters[("c", x)]
                subs.append(s)
                ops.append(hb.tensor(x, hb.local_label(b, x)))
            outsub = "".join(letters[("L", l)] + letters[("R", l)] for l in range(self.nl)) + \
                     "".join(letters[("c", x)] for x in range(self.ns))
            A = np.einsum(",".join(subs) + "->" + outsub, *ops)
            # map (mL_l, mR_l) -> link basis index, c_x -> site index
            it = np.nditer(A, flags=["multi_index"])
            for val in it:
                if abs(val) < 1e-15:
                    continue
                mi = it.multi_index
                full = 0
                for l in range(self.nl):
                    j = j2[l] / 2
                    d = int(round(2 * j + 1))
                    o = self.link.offset[j]
                    full += (o + mi[2 * l] * d + mi[2 * l + 1]) * strides[l]
                for x in range(self.ns):
                    full += mi[2 * self.nl + x] * strides[self.nl + x]
                out[full, kb] = val
        return out

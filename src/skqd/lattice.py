"""
Open 2 x Lx ladder (Ly = 2 rows), the geometry of the SKQD manual (Step 1.1).

Sites x = (x1, x2), x1 = 0..Lx-1 (column), x2 = 0..Ly-1 (row), site index
x1*Ly + x2.  Links are oriented in +x and +y and are listed in the order of their
start site (x-link before y-link at the same site).  Every link goes from a
lower site index to a higher one, which is what the Jordan-Wigner sign rule
of the builder assumes.

eta_l = i on x-links, (-1)^{x1+x2} of the start site on y-links (staggered
hopping phases; the product of phases around a plaquette is -1).

A plaquette P with lower-left corner (x1, x2) is described by its four links
(bottom, right, top, left) counter-clockwise from the lower-left corner:
    bottom = (x1,x2) -> (x1+1,x2)      traversed forward
    right  = (x1+1,x2) -> (x1+1,x2+1)  traversed forward
    top    = (x1,x2+1) -> (x1+1,x2+1)  traversed backward (U^dag)
    left   = (x1,x2) -> (x1,x2+1)      traversed backward (U^dag)

Static charges: a set of site indices that carry an extra static spin-1/2 in
Gauss's law (Step 1.3, Table 2 of the manual).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ladder:
    Lx: int
    Ly: int = 2
    static_sites: tuple = field(default_factory=tuple)

    # ---- derived geometry ----------------------------------------------------
    @property
    def sites(self):
        return [(x1, x2) for x1 in range(self.Lx) for x2 in range(self.Ly)]

    @property
    def n_sites(self):
        return self.Lx * self.Ly

    def site_index(self, x1, x2):
        return x1 * self.Ly + x2

    def coords(self, s):
        return divmod(s, self.Ly)

    def parity(self, s):
        x1, x2 = self.coords(s)
        return (x1 + x2) % 2  # 0 = even site (empty in the Dirac sea), 1 = odd (doubly occupied)

    def n_vac(self, s):
        return 0 if self.parity(s) == 0 else 2

    @property
    def links(self):
        """List of (start, end, direction) with direction 'x' or 'y'."""
        out = []
        for (x1, x2) in self.sites:
            s = self.site_index(x1, x2)
            if x1 + 1 < self.Lx:
                out.append((s, self.site_index(x1 + 1, x2), "x"))
            if x2 + 1 < self.Ly:
                out.append((s, self.site_index(x1, x2 + 1), "y"))
        return out

    @property
    def n_links(self):
        return len(self.links)

    def link_index(self, a, b):
        for k, (s, t, _) in enumerate(self.links):
            if (s, t) == (a, b):
                return k
        raise KeyError((a, b))

    def eta(self, l):
        s, t, d = self.links[l]
        if d == "x":
            return 1j
        return float((-1) ** sum(self.coords(s)))

    @property
    def plaquettes(self):
        """List of dicts with link indices 'b','r','t','l' and corner sites 'c00','c10','c11','c01'."""
        out = []
        for x1 in range(self.Lx - 1):
            for x2 in range(self.Ly - 1):
                c00 = self.site_index(x1, x2)
                c10 = self.site_index(x1 + 1, x2)
                c01 = self.site_index(x1, x2 + 1)
                c11 = self.site_index(x1 + 1, x2 + 1)
                out.append(
                    dict(
                        b=self.link_index(c00, c10),
                        r=self.link_index(c10, c11),
                        t=self.link_index(c01, c11),
                        l=self.link_index(c00, c01),
                        c00=c00, c10=c10, c11=c11, c01=c01,
                    )
                )
        return out

    def ends(self):
        """ends[s] = list of (link index, role) in canonical order (= link index order);
        role 'out' if the link starts at s (mL index), 'in' if it ends at s (mR index)."""
        e = {s: [] for s in range(self.n_sites)}
        for l, (a, b, _) in enumerate(self.links):
            e[a].append((l, "out"))
            e[b].append((l, "in"))
        return e

    def is_static(self, s):
        return s in self.static_sites

    def describe(self):
        return f"{self.Ly}x{self.Lx} ladder: {self.n_sites} sites, {self.n_links} links, " \
               f"{len(self.plaquettes)} plaquettes, static charges at {list(self.static_sites)}"

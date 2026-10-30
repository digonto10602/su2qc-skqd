"""Catalogue of the physical (gauge-invariant) states of the 2x2, 2x3, 2x4 ladders, by baryon sector, with the
lowest energy eigenstates and their dominant configurations, plus examples of unphysical configurations.

Everything is computed from the package: skqd.exact.Model(Lx) (basis, Hamiltonian, g^2 = 4, m = 3 g^2/16),
skqd.codec.Codec (bit strings), skqd.vertex.kernel_dim (Gauss-law check of the invalid examples).
"""
import os, sys, csv, json, subprocess, datetime, textwrap
import numpy as np
import scipy.sparse.linalg as spl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Wedge, Rectangle, FancyArrowPatch

ROOT = "/home/digimonk/Projects/su2qc-skqd"
sys.path.insert(0, os.path.join(ROOT, "src"))
from skqd.exact import Model, mass_default
from skqd.codec import Codec, Reject
from skqd.vertex import kernel_dim

G2 = 4.0
M_Q = mass_default(G2)
KLEV = 4                      # ground state + 3 excited states per sector
MAXCFG, CUMW = 6, 0.95        # configurations drawn per eigenstate
OUT_PDF = f"{ROOT}/reports/physical_states_catalogue.pdf"
OUT_CSV = f"{ROOT}/reports/physical_states_catalogue_all_states.csv"
COMMIT = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
A4 = (8.27, 11.69)
ON, OFFC = "#d62728", "#a8a8a8"
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans"})


# ------------------------------------------------------------------ physics data
def lattice_data(Lx):
    M = Model(Lx)
    C = Codec(M.basis)
    lat = M.lat
    H = M.H(G2).tocsr()
    diag = np.real(H.diagonal())
    cw = C.all_codewords()
    sectors = {}
    for tb in sorted(M.basis.sector_dims()):
        idx = M.basis.sector(tb)
        h = H[idx][:, idx]
        dim = len(idx)
        if dim <= 3000:
            w, v = np.linalg.eigh(h.toarray())
        else:
            w, v = spl.eigsh(h, k=KLEV + 2, which="SA", tol=1e-12)
            o = np.argsort(w); w, v = w[o], v[:, o]
        lev = []
        for k in range(min(KLEV, dim)):
            vec = v[:, k]
            p = int(np.argmax(np.abs(vec)))
            vec = vec * np.exp(-1j * np.angle(vec[p]))
            prob = np.abs(vec) ** 2
            order = np.argsort(-prob)
            cfg, cum = [], 0.0
            for j in order:
                if len(cfg) >= MAXCFG or cum >= CUMW:
                    break
                cfg.append((int(idx[j]), complex(vec[j]), float(prob[j])))
                cum += prob[j]
            deg = [kk for kk in range(len(w)) if kk != k and abs(w[kk] - w[k]) < 1e-8]
            lev.append(dict(E=float(w[k]), cfg=cfg, cum=float(cum), deg=deg,
                            pr=float(1 / np.sum(prob ** 2))))
        sectors[tb] = dict(idx=idx, dim=dim, levels=lev, all_E=[float(x) for x in w[:min(len(w), 8)]])
    return dict(Lx=Lx, M=M, C=C, lat=lat, diag=diag, cw=cw, sectors=sectors)


def site_info(lat, s, n):
    nv = lat.n_vac(s)
    exc = n - nv
    sym = {0: "", 1: "q", 2: "2q", -1: r"$\bar{q}$", -2: r"$2\bar{q}$"}[exc]
    return nv, exc, sym


# ------------------------------------------------------------------ drawing
def draw_config(ax, D, label, scale=1.0, fs=6.5, show_j=True, bad_sites=(), bad_links=()):
    lat = D["lat"] if isinstance(D, dict) else D
    j2, n, iota = label
    P = lambda s: (lat.coords(s)[0] * 1.0, lat.coords(s)[1] * 1.0)
    for l, (a, b, d) in enumerate(lat.links):
        pa, pb = P(a), P(b)
        on = j2[l] > 0
        col = ON if on else OFFC
        bad = l in bad_links
        if bad:
            col = "#9467bd"
        ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color=col, lw=(2.6 if on else 0.9) * scale,
                ls="-" if on else (0, (2, 2)), zorder=1, solid_capstyle="round")
        if show_j:
            mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
            ax.text(mx, my, "½" if on else "0", fontsize=fs - 1, ha="center", va="center",
                    color=col, bbox=dict(fc="white", ec="none", pad=0.15), zorder=2)
    r = 0.15
    for s in range(lat.n_sites):
        x, y = P(s)
        ns = n[s]
        odd = lat.parity(s) == 1
        ec = "r" if s in bad_sites else "k"
        lw = 1.6 if odd else 0.8
        if ns == 1:
            ax.add_patch(Circle((x, y), r, fc="white", ec=ec, lw=lw, zorder=4))
            ax.add_patch(Wedge((x, y), r, 90, 270, fc="#9ecae1", ec=ec, lw=lw, zorder=5))
        else:
            ax.add_patch(Circle((x, y), r, fc={0: "white", 2: "#08519c"}[ns], ec=ec, lw=lw, zorder=4))
        ax.text(x, y, str(ns), ha="center", va="center", fontsize=fs, weight="bold",
                color="white" if ns == 2 else "k", zorder=6)
        _, exc, sym = site_info(lat, s, ns)
        dy = -1 if lat.coords(s)[1] == 0 else 1
        if sym:
            ax.text(x + 0.17, y + dy * 0.2, sym, fontsize=fs, color="#b15928", weight="bold",
                    ha="left", va="center", zorder=6)
        if iota[s] and ns == 1 and sum(j2[l] for l, _ in lat.ends()[s]) == 3:
            pass
        nflux = sum(j2[l] for l, _ in lat.ends()[s])
        if len(lat.ends()[s]) == 3 and nflux == 3 and ns == 1:
            ax.text(x - 0.17, y + dy * 0.2, f"ι={iota[s]}", fontsize=fs - 0.5, color="#6a3d9a",
                    weight="bold", ha="right", va="center", zorder=6)
        if s in bad_sites:
            ax.text(x, y + dy * 0.32, "✗", fontsize=fs + 4, color="r", ha="center", va="center", zorder=7)
    ax.set_xlim(-0.35, lat.Lx - 1 + 0.35)
    ax.set_ylim(-0.42, 1.42)
    ax.set_aspect("equal")
    ax.axis("off")


def bitgroups(D, bits):
    C = D["C"]
    return " ".join("".join(str(int(b)) for b in bits[o:o + w]) for o, w in zip(C.offsets, C.widths))


def fit_texts(fig, margin=0.012):
    fig.canvas.draw(); r = fig.canvas.get_renderer(); W, H = fig.bbox.width, fig.bbox.height
    ts = list(fig.texts)
    for ax in fig.axes:
        ts += list(ax.texts) + ([ax.title] if ax.title.get_text() else [])
    for t in ts:
        if not t.get_text().strip():
            continue
        for _ in range(40):
            bb = t.get_window_extent(r)
            if bb.x1 <= W * (1 - margin) and bb.x0 >= W * margin and bb.y1 <= H and bb.y0 >= 0:
                break
            t.set_fontsize(t.get_fontsize() * 0.95)


class FitPdf(PdfPages):
    def savefig(self, fig=None, **kw):
        fit_texts(fig)
        return super().savefig(fig, **kw)


def text_block(fig, x, y, lines, fs=8.4, dy=0.0195):
    for ln in lines:
        bold = ln.startswith("##")
        mono = ln.startswith("    ")
        fig.text(x, y, ln.lstrip("#").strip() if bold else ln, fontsize=fs + (1.2 if bold else 0),
                 weight="bold" if bold else "normal", family="DejaVu Sans Mono" if mono else "DejaVu Sans")
        y -= dy
    return y


# ------------------------------------------------------------------ cards
GRID = {2: (4, 6), 3: (3, 6), 4: (2, 6)}


def card(fig, D, gidx, x, y, w, h, extra=None, bg="white"):
    lab = D["M"].basis.labels[gidx]
    bg_ax = fig.add_axes([x, y, w, h]); bg_ax.axis("off")
    bg_ax.add_patch(Rectangle((0, 0), 1, 1, transform=bg_ax.transAxes, fc=bg, ec="0.75", lw=0.5))
    ax = fig.add_axes([x + 0.004, y + 0.36 * h, w - 0.008, 0.62 * h])
    draw_config(ax, D, lab, fs=6.2)
    tb = int(D["M"].basis.twoB[gidx])
    sec_idx = int(np.searchsorted(D["sectors"][tb]["idx"], gidx))
    lines = [f"#{gidx}  (B={tb // 2}, #{sec_idx} in sector)   E_diag = {D['diag'][gidx]:+.3f}"]
    if extra:
        lines.append(extra)
    lines.append("bits " + bitgroups(D, D["cw"][gidx]))
    lines.append("n=(" + " ".join(str(v) for v in lab[1]) + ")   j=(" + " ".join("½" if v else "0" for v in lab[0]) + ")")
    yy = y + 0.33 * h
    for k, t in enumerate(lines):
        fig.text(x + 0.006, yy, t, fontsize=5.7 if k else 6.0, va="top",
                 family="DejaVu Sans Mono" if t.startswith(("bits", "n=")) else "DejaVu Sans",
                 weight="bold" if k == 0 else "normal")
        yy -= 0.075 * h


def cards_pages(pdf, D, gidx_list, title, extras=None, bgs=None):
    nc, nr = GRID[D["Lx"]]
    W, Hh = 0.95 / nc, 0.86 / nr
    per = nc * nr
    npg = max(1, (len(gidx_list) + per - 1) // per)
    for pg in range(npg):
        fig = plt.figure(figsize=A4)
        fig.text(0.5, 0.975, f"{title}   (page {pg + 1}/{npg})", ha="center", fontsize=9.5, weight="bold")
        for k, g in enumerate(gidx_list[pg * per:(pg + 1) * per]):
            r, c = divmod(k, nc)
            i = pg * per + k
            card(fig, D, g, 0.025 + c * W, 0.83 - r * (Hh + 0.01), W - 0.006, Hh,
                 extra=(extras[i] if extras else None), bg=(bgs[i] if bgs else "white"))
        pdf.savefig(fig); plt.close(fig)


# ------------------------------------------------------------------ pages
def page_title(pdf, DATA):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.95, "Catalogue of the physical states", ha="center", fontsize=18, weight="bold")
    fig.text(0.5, 0.925, "SU(2) lattice gauge theory with staggered quarks on 2x2, 2x3 and 2x4 ladders", ha="center",
             fontsize=10.5)
    rows = ["## Contents",
            "  1. How to read the pictures and the labels (pages 2-3)",
            "  2. Why a configuration can be unphysical: examples (page 4)",
            "  3. Energy levels of every sector, all three lattices (page 5)",
            "  4. Per lattice and baryon sector B: the ground state and excited states 1-3, each drawn as its",
            "     dominant configurations with their weights",
            "  5. Every physical state of 2x2 (82) and 2x3 (1,727), drawn one by one, sector by sector",
            "  The 2x4 lattice has 37,165 physical states (about 2,000 pages if drawn); they are all listed with labels,",
            f"  bit strings and diagonal energies in the companion file reports/{os.path.basename(OUT_CSV)}.",
            "",
            "## Number of physical states (gauge-invariant basis states) per baryon sector B"]
    for D in DATA:
        dims = {tb // 2: s["dim"] for tb, s in D["sectors"].items()}
        rows.append(f"    2x{D['Lx']}: total {D['M'].basis.dim:>6,}   " + "  ".join(f"B={b:+d}:{d}" for b, d in dims.items()))
    rows += ["",
             "## Model and parameters (src/skqd/hamiltonian.py)",
             "    H = sum_l hop_l  +  m sum_x (-1)^(x1+x2) n_x  +  (g^2/2) sum_l j_l(j_l+1)  -  1/(2 g^2) sum_P (W_P + W_P^dag)",
             f"    g^2 = {G2:g},  m = 3 g^2/16 = {M_Q:g}  (the package's standard line; the energies below are for these values),",
             "    links truncated at j_max = 1/2 (each link has j = 0 or j = 1/2).",
             "",
             "## Where everything comes from",
             "  skqd.exact.Model(Lx) builds the gauge-invariant basis and the Hamiltonian; energies and eigenvectors are exact",
             "  diagonalisations of each sector (numpy eigh, or scipy eigsh for the two large 2x4 sectors).  Ground-state",
             "  energies equal the stored references in validation/E3.json (checked on page 5).  Bit strings: skqd.codec.Codec.",
             f"  Repository commit {COMMIT}; generated {datetime.date.today().isoformat()}."]
    text_block(fig, 0.06, 0.88, rows, fs=8.4)
    pdf.savefig(fig); plt.close(fig)


def page_legend(pdf, DATA):
    D4 = DATA[2]; lat = D4["lat"]
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "How to read the pictures", ha="center", fontsize=14, weight="bold")
    ax = fig.add_axes([0.06, 0.67, 0.88, 0.25]); ax.axis("off"); ax.set_aspect("equal")
    for l, (a, b, d) in enumerate(lat.links):
        pa, pb = lat.coords(a), lat.coords(b)
        ax.add_patch(FancyArrowPatch(pa, pb, arrowstyle="-|>", mutation_scale=9, lw=1.0, color="0.3", shrinkA=11,
                                     shrinkB=11))
        ax.text((pa[0] + pb[0]) / 2 + (0 if d == "x" else 0.09), (pa[1] + pb[1]) / 2 + (0.08 if d == "x" else 0),
                f"link {l}", fontsize=7, color="#7f2704", ha="center" if d == "x" else "left")
    for s in range(lat.n_sites):
        x, y = lat.coords(s)
        odd = lat.parity(s) == 1
        ax.add_patch(Circle((x, y), 0.12, fc="white", ec="k", lw=1.6 if odd else 0.8, zorder=3))
        ax.text(x, y, str(s), ha="center", va="center", fontsize=8, weight="bold", zorder=4)
        ax.text(x, y + (-0.27 if y == 0 else 0.27), f"site {s} ({x},{y})\n{'odd' if odd else 'even'}, vacuum n={lat.n_vac(s)}",
                ha="center", va="center", fontsize=6.5)
    ax.set_xlim(-0.5, 3.5); ax.set_ylim(-0.55, 1.55)
    ax.set_title("2x4 ladder (2x2 and 2x3 are its first 2 or 3 columns): site numbers, coordinates (x1, x2), link numbers and directions",
                 fontsize=8)
    rows = ["## Sites and quarks (staggered fermions)",
            "* Each site holds a quark field with two colours, so its occupation is n = 0, 1 or 2 (number in the circle;",
            "  white = 0, half-filled = 1, dark = 2).",
            "* Staggered fermions: the 'empty' vacuum (Dirac sea) has n = 0 on EVEN sites (x1+x2 even, thin circle) and",
            "  n = 2 on ODD sites (thick circle).  Physical particles are deviations from that vacuum (brown label):",
            "    even site: n=0 -> nothing,  n=1 -> 'q' (one quark),       n=2 -> '2q' (two quarks)",
            "    odd site:  n=2 -> nothing,  n=1 -> 'q̄' (one hole = antiquark), n=0 -> '2q̄' (two holes)",
            "* Mass term m sum (-1)^(x1+x2) n: every quark or antiquark costs energy m relative to the vacuum.",
            "",
            "## Links (colour-electric flux)",
            "* Each link carries spin j = 0 (grey dashed, '0', no flux) or j = 1/2 (red, '½', one unit of flux).",
            "  Electric energy (g^2/2) j(j+1) = 3/8 g^2 per flux link.",
            "",
            "## Gauss's law and the intertwiner iota",
            "* At every site the spins arriving there (each flux link brings 1/2, n = 1 brings 1/2; n = 0, 2 bring 0) must",
            "  combine to total colour spin 0.  So the number of spin-1/2 objects at a site must be even.",
            "* At an interior site with flux on all three links and n = 1 there are TWO ways to do this, labelled",
            "  iota = 0, 1 (purple 'ι='); it is shown only there.",
            "",
            "## Baryon number B and sectors",
            "* B = 1/2 sum_x (n_x - n_vac,x).  In SU(2) a 'baryon' is two quarks, so B = 1 means two extra quarks;",
            "  quark-antiquark pairs (mesons) have B = 0.  The Hamiltonian never changes B, so each B is a separate sector.",
            "* The SKQD work of this project uses B = 0 (2B = 0) and B = 1 (2B = 2).",
            "",
            "## The text under each picture",
            "* #k = position in the package's basis list (skqd.basis); '#i in sector' = position inside its B sector.",
            "* E_diag = diagonal energy of that configuration alone (mass + electric terms) -- not an eigenvalue.",
            "* bits = how the state is stored on qubits (skqd.codec): one group per site 0, 1, 2, ...; in each group the flux",
            "  bits of the site's links (link-number order), then the matter bit (n/2, or iota at a three-flux n = 1 site).",
            "* n=(...) per site, j=(...) per link in link-number order.",
            "* In the eigenstate sections: c = amplitude of that configuration in the eigenstate (global phase fixed so the",
            "  largest amplitude is real and positive) and |c|^2 = its weight (probability)."]
    text_block(fig, 0.06, 0.64, rows, fs=8.0, dy=0.0178)
    pdf.savefig(fig); plt.close(fig)


def page_invalid(pdf, DATA):
    D2 = DATA[0]; lat = D2["lat"]; B = D2["M"].basis; C = D2["C"]
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.96, "Examples of unphysical configurations (2x2 ladder)", ha="center", fontsize=13, weight="bold")
    fig.text(0.06, 0.93, "A configuration is physical only if Gauss's law holds at EVERY site: the spin-1/2 objects there (flux links and an",
             fontsize=8.2)
    fig.text(0.06, 0.915, "n = 1 quark) must combine to total spin 0.  Each example below is checked against the package: it is not in the basis,",
             fontsize=8.2)
    fig.text(0.06, 0.90, "and skqd.vertex.kernel_dim = 0 (no singlet) at the marked site.", fontsize=8.2)
    ends = lat.ends()

    def vertex_ok(lab, s):
        j2, n, _ = lab
        spins = tuple((j2[l] / 2, role) for l, role in ends[s])
        return kernel_dim(spins, n[s]) > 0 if True else None

    nl = lat.n_links
    examples = []
    # (a) open flux string: link 0 alone, all sites at vacuum occupation
    j2 = [0] * nl; j2[0] = 1
    examples.append(("Open flux string", (tuple(j2), (0, 2, 2, 0), (0, 0, 0, 0)),
                     "One flux link with nothing at its ends: each end site has a single spin-1/2 and no partner, so no singlet exists.  Flux must close into a loop or end on a quark."))
    # (b) lone quark, no flux
    examples.append(("Lone quark", (tuple([0] * nl), (1, 2, 2, 0), (0, 0, 0, 0)),
                     "One quark (n=1) on site 0 with no flux: an isolated colour charge.  Its spin-1/2 has nothing to pair with."))
    # (c) closed loop + one quark at a corner
    j2 = [1] * nl
    examples.append(("Flux loop with a stray quark", (tuple(j2), (1, 2, 2, 0), (0, 0, 0, 0)),
                     "A closed flux loop is fine by itself, but site 0 also has one quark: two flux links + one quark = three spin-1/2 objects, an odd number, so no spin 0."))
    # (d) string ending on a quark at one end only
    j2 = [0] * nl; j2[0] = 1
    examples.append(("String with only one end on a quark", (tuple(j2), (1, 2, 2, 0), (0, 0, 0, 0)),
                     "Site 0 is fine (flux + quark pair up), but the other end of the string, site 2, has nothing to pair with. A string must end on charges at BOTH ends (compare a valid meson: also n = 1 at site 2)."))
    rows = []
    for i, (name, lab, why) in enumerate(examples):
        bad = [s for s in range(lat.n_sites) if not vertex_ok(lab, s)]
        assert lab not in B.index and bad, name
        ax = fig.add_axes([0.06 + (i % 2) * 0.46, 0.68 - (i // 2) * 0.24, 0.38, 0.15])
        draw_config(ax, D2, lab, fs=7, bad_sites=bad)
        ax.set_title(f"({chr(97 + i)}) {name}", fontsize=9, loc="left")
        fig.text(0.06 + (i % 2) * 0.46, 0.665 - (i // 2) * 0.24, "\n".join(textwrap.wrap(why, 60)), fontsize=6.9, va="top")
    # encoding-level rejections
    good = B.labels[int(B.sector(0)[0])]
    cwg = list(C.encode(good))
    rows = ["## Bit strings that are not states (rejected by the decoder, skqd.codec.Codec.decode)",
            "The qubit encoding can also produce strings that describe no state at all; the decoder rejects them:"]
    # link mismatch: flip one copy of link 0
    bad1 = list(cwg); q0 = C.offsets[0]; bad1[q0] ^= 1
    # flag: corner with one flux and matter bit 1 -> pick a state with exactly one flux at a corner
    flagbits = None
    for lab in B.labels:
        j2, n, io = lab
        f0 = [j2[l] for l, _ in ends[0]]
        if sum(f0) == 1:
            b = list(C.encode(lab)); b[C.offsets[0] + 2] = 1; flagbits = (lab, b); break
    def reason(bits):
        try:
            C.decode(tuple(bits)); return "accepted"
        except Reject as r:
            return str(r)
    rows += [f"    good  {''.join(map(str, cwg[:3]))} {''.join(map(str, cwg[3:6]))} {''.join(map(str, cwg[6:9]))} {''.join(map(str, cwg[9:12]))}   = state #{int(B.sector(0)[0])}: decoder '{reason(cwg)}'",
             f"    link  {''.join(map(str, bad1[:3]))} {''.join(map(str, bad1[3:6]))} {''.join(map(str, bad1[6:9]))} {''.join(map(str, bad1[9:12]))}   one copy of link 0 changed: the two ends disagree -> '{reason(bad1)}'",
             f"    flag  {''.join(map(str, flagbits[1][:3]))} {''.join(map(str, flagbits[1][3:6]))} {''.join(map(str, flagbits[1][6:9]))} {''.join(map(str, flagbits[1][9:12]))}   corner with one flux must have n = 1, matter bit 1 is a flag -> '{reason(flagbits[1])}'",
             "",
             "* 'link': every link is stored at both of its ends; a physical state has equal copies.",
             "* 'flag': a matter-bit value that the site's flux pattern does not allow (n is already forced).",
             "* 'sector': a perfectly physical state, rejected only because its baryon number B is not the one being studied.",
             "  It is NOT unphysical -- it belongs to another sector of this catalogue.",
             "Unphysical configurations like (a)-(d) cannot even be written in this encoding: the encoding stores only",
             "Gauss-law-respecting site states (6 per corner site, 13 per interior site), which is why bit-level errors show up",
             "as 'link' or 'flag' rejections instead."]
    text_block(fig, 0.06, 0.27, rows, fs=7.9, dy=0.0168)
    pdf.savefig(fig); plt.close(fig)


E3REF = json.load(open(f"{ROOT}/validation/E3.json"))["data"]["references"]


def page_spectra(pdf, DATA):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.96, "Energy levels of every sector (g^2 = 4, m = 0.75)", ha="center", fontsize=13, weight="bold")
    rows = ["E_0 = ground state, E_1, E_2, E_3 = first three excited states.  '=' marks a degenerate level (same energy",
            "as its neighbour); inside a degenerate level the choice of individual eigenvectors is arbitrary.",
            "Check: stored references validation/E3.json (key 2xL|g2=4.0|2B=...) vs this computation."]
    y = text_block(fig, 0.06, 0.93, rows, fs=8.2)
    for D in DATA:
        y -= 0.01
        fig.text(0.06, y, f"2x{D['Lx']}", fontsize=10.5, weight="bold"); y -= 0.02
        fig.text(0.06, y, "      B     dim        E_0          E_1          E_2          E_3      check vs E3.json",
                 fontsize=7.6, family="DejaVu Sans Mono"); y -= 0.017
        for tb, s in D["sectors"].items():
            Es = [lv["E"] for lv in s["levels"]]
            cells = []
            for k, e in enumerate(Es):
                mark = "=" if s["levels"][k]["deg"] else " "
                cells.append(f"{e:+10.5f}{mark}")
            key = f"2x{D['Lx']}|g2={G2}|2B={tb}"
            chk = ""
            if key in E3REF:
                ref = E3REF[key]["energies"][:len(Es)]
                chk = f"max|diff| {max(abs(a - b) for a, b in zip(ref, Es)):.1e}"
            fig.text(0.06, y, f"    {tb // 2:+3d}  {s['dim']:>6}  " + "  ".join(cells) + "   " + chk, fontsize=7.6,
                     family="DejaVu Sans Mono"); y -= 0.0165
    pdf.savefig(fig); plt.close(fig)


def eigen_section(pdf, D):
    Lx = D["Lx"]
    for tb, s in D["sectors"].items():
        g_list, extras, bgs = [], [], []
        cols = ["#fff7ec", "#eef6fb", "#f3f9ee", "#fbf0f7"]
        head = []
        for k, lv in enumerate(s["levels"]):
            name = "ground state" if k == 0 else f"excited state {k}"
            degtxt = f", degenerate with E_{','.join(map(str, lv['deg']))}" if lv["deg"] else ""
            head.append(f"E_{k} = {lv['E']:+.6f}  ({name}{degtxt}):  {len(lv['cfg'])} configurations drawn carry "
                        f"{lv['cum']:.1%} of the weight; participation ratio {lv['pr']:.1f}")
            for (g, c, p) in lv["cfg"]:
                g_list.append(g)
                cs = f"{c.real:+.4f}" if abs(c.imag) < 1e-10 else (f"{c.imag:+.4f}i" if abs(c.real) < 1e-10 else f"{c.real:+.3f}{c.imag:+.3f}i")
                extras.append(f"E_{k} ({name}):  c = {cs},  |c|² = {p:.4f}")
                bgs.append(cols[k % 4])
        # header page for the sector
        fig = plt.figure(figsize=A4)
        fig.text(0.5, 0.95, f"2x{Lx}, sector B = {tb // 2:+d}   ({s['dim']:,} physical states)", ha="center", fontsize=14,
                 weight="bold")
        rows = ["## Lowest energy levels and how each one is drawn on the following pages"] + head + [
            "",
            "Each eigenstate is a superposition of many configurations.  The following pages draw its most important",
            f"configurations (largest weight first, up to {MAXCFG} or until {CUMW:.0%} of the weight is covered), one card each,",
            "with the amplitude c and the weight |c|^2.  Cards of the same level share a background colour.",
            "Participation ratio = 1/sum|c|^4 = roughly how many configurations the state is spread over."]
        text_block(fig, 0.06, 0.9, rows, fs=8.2)
        pdf.savefig(fig); plt.close(fig)
        cards_pages(pdf, D, g_list, f"2x{Lx}, B = {tb // 2:+d}: lowest eigenstates, dominant configurations", extras, bgs)


def basis_section(pdf, D):
    Lx = D["Lx"]
    for tb, s in D["sectors"].items():
        idx = list(s["idx"])
        idx.sort(key=lambda g: (D["diag"][g], g))
        cards_pages(pdf, D, idx, f"2x{Lx}: all physical states of sector B = {tb // 2:+d} ({s['dim']}), lowest E_diag first")


def write_csv(DATA):
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["lattice", "global_index", "B", "index_in_sector", "E_diag", "bits_by_site", "n_per_site",
                    "j_per_link", "iota_per_site", "particles"])
        for D in DATA:
            lat = D["lat"]
            for tb, s in D["sectors"].items():
                for si, g in enumerate(s["idx"]):
                    j2, n, io = D["M"].basis.labels[g]
                    parts = []
                    for st in range(lat.n_sites):
                        sym = site_info(lat, st, n[st])[2]
                        if sym:
                            parts.append(f"{sym.replace(chr(36), '').replace(chr(92) + 'bar{q}', 'qbar')}@{st}")
                    w.writerow([f"2x{D['Lx']}", int(g), tb // 2, si, f"{D['diag'][g]:.6f}", bitgroups(D, D["cw"][g]),
                                " ".join(map(str, n)), " ".join("1/2" if v else "0" for v in j2),
                                " ".join(map(str, io)), " ".join(parts)])


def main():
    DATA = [lattice_data(L) for L in (2, 3, 4)]
    write_csv(DATA)
    with FitPdf(OUT_PDF) as pdf:
        page_title(pdf, DATA); page_legend(pdf, DATA); page_invalid(pdf, DATA); page_spectra(pdf, DATA)
        for D in DATA:
            eigen_section(pdf, D)
            print("eigen", D["Lx"], flush=True)
        for D in DATA[:2]:
            basis_section(pdf, D)
            print("basis", D["Lx"], flush=True)
        pdf.infodict()["Title"] = "Catalogue of the physical states, 2x2 / 2x3 / 2x4"
    print(OUT_PDF, OUT_CSV)


if __name__ == "__main__":
    main()

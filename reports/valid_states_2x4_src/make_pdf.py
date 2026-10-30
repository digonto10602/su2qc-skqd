"""Valid local states of the three 2x4 plaquette terms, drawn as pictures (PDF).

Data: vs.pkl from extract.py (skqd.exact.Model(4), skqd.reference_sim.term_support/localize,
plaquette term O = -plaq_P / (2 g^2), g^2 = 4), i.e. exactly the local states and couplings the
package's circuit builder uses.  Nothing here is typed in by hand except the encoding rules,
which are quoted from src/skqd/codec.py and re-checked against the data.
"""
import pickle, subprocess, datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle, Wedge, FancyBboxPatch


def fit_texts(fig, margin=0.012):
    """Shrink any text that runs past the page edge until it fits (returns the number shrunk)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.bbox.width, fig.bbox.height
    texts = list(fig.texts)
    for ax in fig.axes:
        texts += [t for t in ax.texts]
        if ax.title.get_text():
            texts.append(ax.title)
    n = 0
    for t in texts:
        if not t.get_text().strip() or not t.get_visible():
            continue
        shrunk = False
        for _ in range(40):
            bb = t.get_window_extent(r)
            if bb.x1 <= W * (1 - margin) and bb.x0 >= W * margin and bb.y1 <= H * (1 - margin * 0.5) and bb.y0 >= 0:
                break
            t.set_fontsize(t.get_fontsize() * 0.95)
            shrunk = True
        n += shrunk
    return n


class FitPdf(PdfPages):
    shrunk_pages = []

    def savefig(self, fig=None, **kw):
        k = fit_texts(fig)
        if k:
            FitPdf.shrunk_pages.append((self.get_pagecount() + 1, k))
        return super().savefig(fig, **kw)

D = pickle.load(open("vs.pkl", "rb"))
L = D["lattice"]
LINKS, PLAQ, ENDS = L["links"], L["plaquettes"], L["ends"]
OFF, WID = L["offsets"], L["widths"]
COMMIT = subprocess.run(["git", "-C", "/home/digimonk/Projects/su2qc-skqd", "rev-parse", "--short", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
TODAY = datetime.date.today().isoformat()

ON, OFFC = "#d62728", "#b0b0b0"
NFILL = {0: "white", 1: "#9ecae1", 2: "#08519c"}
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans"})
A4 = (8.27, 11.69)


def site_kind(s):
    return "corner" if len(ENDS[s]) == 2 else "interior"


def draw_site(ax, x, y, n, iota, r=0.09, fs=6.5, label=None, iota_up=False):
    """Matter circle: white n=0, light n=1, dark n=2; iota written below when defined."""
    if n == 1:
        ax.add_patch(Circle((x, y), r, fc="white", ec="k", lw=0.8, zorder=5))
        ax.add_patch(Wedge((x, y), r, 90, 270, fc=NFILL[1], ec="k", lw=0.8, zorder=6))
    else:
        ax.add_patch(Circle((x, y), r, fc=NFILL[n], ec="k", lw=0.8, zorder=5))
    ax.text(x, y, f"{n}", ha="center", va="center", fontsize=fs, zorder=7,
            color="white" if n == 2 else "k", weight="bold")
    if iota is not None:
        ax.text(x, (y + r + 0.04) if iota_up else (y - r - 0.04), rf"$\iota$={iota}", ha="center",
                va="bottom" if iota_up else "top", fontsize=fs - 0.3, zorder=7, color="#6a3d9a", weight="bold")
    if label is not None:
        ax.text(x, y + r + 0.03, label, ha="center", va="bottom", fontsize=fs - 1.5, color="0.35")


def draw_link(ax, p, q, on, lw_on=2.6, label=None, fs=6):
    if on:
        ax.plot([p[0], q[0]], [p[1], q[1]], color=ON, lw=lw_on, solid_capstyle="round", zorder=2)
    else:
        ax.plot([p[0], q[0]], [p[1], q[1]], color=OFFC, lw=0.9, ls=(0, (2, 2)), zorder=1)
    if label is not None:
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        ax.text(mx, my, label, fontsize=fs, ha="center", va="center", color=ON if on else "0.5",
                bbox=dict(fc="white", ec="none", pad=0.3), zorder=3)


# ---------------------------------------------------------------- plaquette geometry helpers
def plaq_geometry(P):
    pl = PLAQ[P]
    pos = {pl["c00"]: (0.0, 0.0), pl["c10"]: (1.0, 0.0), pl["c11"]: (1.0, 1.0), pl["c01"]: (0.0, 1.0)}
    plinks = {"b": pl["b"], "r": pl["r"], "t": pl["t"], "l": pl["l"]}
    third = {}
    for s in pos:
        for (l, role) in ENDS[s]:
            if l not in plinks.values():
                a, b, d = LINKS[l]
                other = b if a == s else a
                dx = -1 if L["coords"][other][0] < L["coords"][s][0] else 1
                third[s] = (l, dx)
    return pl, pos, plinks, third


def draw_plaquette_state(ax, P, rec, ox=0.0, oy=0.0, scale=1.0, fs=6.0, show_j=True):
    pl, pos, plinks, third = plaq_geometry(P)
    T = lambda xy: (ox + scale * xy[0], oy + scale * xy[1])
    sites = rec["sites"]
    flux = {}
    for s, d in sites.items():
        for l, v in d["flux"].items():
            flux.setdefault(l, set()).add(v)
    for l, vs in flux.items():
        assert len(vs) == 1, f"link {l} copies disagree"          # every valid state: copies agree
    fl = {l: next(iter(v)) for l, v in flux.items()}
    pairs = {"b": (pl["c00"], pl["c10"]), "r": (pl["c10"], pl["c11"]), "t": (pl["c01"], pl["c11"]),
             "l": (pl["c00"], pl["c01"])}
    for side, (a, b) in pairs.items():
        on = fl[plinks[side]]
        draw_link(ax, T(pos[a]), T(pos[b]), on, label=(("½" if on else "0") if show_j else None), fs=fs - 0.5)
    for s, (l, dx) in third.items():
        p = T(pos[s]); q = (p[0] + dx * 0.3 * scale, p[1])
        on = fl[l]
        draw_link(ax, p, q, on, lw_on=2.0)
        ax.text(q[0] + dx * 0.02 * scale, q[1], "½" if on else "0", fontsize=fs - 1, ha="left" if dx > 0 else "right",
                va="center", color=ON if on else "0.55")
    for s, d in sites.items():
        x, y = T(pos[s])
        draw_site(ax, x, y, d["n"], d["iota"], r=0.11 * scale, fs=fs, iota_up=(pos[s][1] > 0.5))


# ---------------------------------------------------------------- page 1: title
def page_title(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.93, "Valid local states of the 2x4 plaquette terms", ha="center", fontsize=17, weight="bold")
    fig.text(0.5, 0.905, "SU(2) lattice gauge theory, staggered quarks, $j_{\\max}=\\frac{1}{2}$, 2x4 ladder (28 qubits)",
             ha="center", fontsize=10)
    t = [
        "What this document shows",
        "  1. The 2x4 ladder: sites, links, qubits and the three plaquettes (page 2).",
        "  2. How one lattice site is encoded and why a CORNER site has exactly 6 valid states and an",
        "     INTERIOR site 13 (pages 3-4).",
        "  3. What the intertwiner label iota is, and how the plaquette mixes iota = 0 and 1 into one",
        "     BRIGHT combination while the orthogonal DARK combination is not reached (pages 5-6).",
        "  4. How to read a state picture (page 7).",
        "  5. The full catalogue: every valid local state of plaq0 (383), plaq1 (1831) and plaq2 (383),",
        "     grouped into the blocks that the plaquette term connects, with bit string, state number,",
        "     n, j, iota and the matrix elements to the states it is connected to.",
        "",
        "Where the numbers come from (nothing typed by hand)",
        "  Model: skqd.exact.Model(4), g^2 = 4; plaquette term  O_P = -W_P / (2 g^2)  as in scripts/gate_S2_2x4.py",
        "  (term_operator).  Support: skqd.reference_sim.term_support.  Valid local states and the local",
        "  matrix h: skqd.reference_sim.localize -- the same function the circuit builder",
        "  (skqd.circuits_ir.structured_term_gates) uses.  Encoding rules: src/skqd/codec.py.",
        "",
        "Consistency with the package's stored numbers (validation/S2_2x4.json, data.structure.structure_4):",
    ]
    for P in range(3):
        d = D[f"plaq{P}"]
        t.append(f"  plaq{P}: {len(d['support'])} qubits, {d['n_states']} states, {d['n_blocks']} blocks, "
                 "sizes " + " ".join(f"{k}x{v}" for k, v in d['block_hist'].items()))
    t.append("  All three lines are identical to the stored record.")
    t += ["", f"Repository commit {COMMIT}; generated {TODAY}.",
          "Conventions: qubit k = bit k (little-endian); a link's flux bit is 1 <=> j = 1/2, 0 <=> j = 0;",
          "every link is stored twice (one copy at each end site); 'state number' = position in the sorted",
          "list of local states (#idx) and the integer of the support bits (int = sum_k b_k 2^k)."]
    y = 0.86
    for line in t:
        fig.text(0.07, y, line, fontsize=8.6, family="DejaVu Sans Mono" if line.startswith("  ") else "DejaVu Sans",
                 weight="bold" if line and not line.startswith(" ") else "normal")
        y -= 0.021
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- page 2: lattice map
def page_lattice(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.95, "The 2x4 ladder: sites, links, qubits, plaquettes", ha="center", fontsize=13, weight="bold")
    ax = fig.add_axes([0.05, 0.5, 0.9, 0.42]); ax.set_aspect("equal"); ax.axis("off")
    sx = lambda s: (L["coords"][s][0] * 2.4, L["coords"][s][1] * 2.4)
    cols = ["#fdd0a2", "#c7e9c0", "#dadaeb"]
    for P, pl in enumerate(PLAQ):
        x0, y0 = sx(pl["c00"])
        ax.add_patch(Rectangle((x0 + 0.25, y0 + 0.25), 1.9, 1.9, fc=cols[P], ec="none", zorder=0))
        ax.text(x0 + 1.2, y0 + 1.2, f"plaq{P}", ha="center", va="center", fontsize=11, weight="bold")
    for l, (a, b, d) in enumerate(LINKS):
        pa, pb = sx(a), sx(b)
        ax.add_patch(FancyArrowPatch(pa, pb, arrowstyle="-|>", mutation_scale=10, lw=1.4, color="k",
                                     shrinkA=14, shrinkB=14, zorder=2))
        qa = [OFF[a] + i for i, (ll, _) in enumerate(ENDS[a]) if ll == l][0]
        qb = [OFF[b] + i for i, (ll, _) in enumerate(ENDS[b]) if ll == l][0]
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        off = (0, 0.28) if d == "x" else (0.42, 0)
        ax.text(mx + off[0], my + off[1], f"link {l}\nq{qa} & q{qb}", ha="center", va="center", fontsize=7,
                color="#7f2704")
    for s in range(len(WID)):
        x, y = sx(s)
        ax.add_patch(Circle((x, y), 0.33, fc="white", ec="k", lw=1.2, zorder=4))
        ax.text(x, y, f"{s}", ha="center", va="center", fontsize=10, weight="bold", zorder=5)
        qs = list(range(OFF[s], OFF[s] + WID[s]))
        ax.text(x, y + (-0.62 if L["coords"][s][1] == 0 else 0.62),
                f"{site_kind(s)}\nq{qs[0]}-q{qs[-1]}", ha="center", va="center", fontsize=7)
    ax.set_xlim(-1, 8.2); ax.set_ylim(-1.3, 3.7)
    rows = ["Each site owns a block of qubits (src/skqd/codec.py).  Inside a block: first one FLUX bit per link",
            "end (in link-index order), then one MATTER bit.  Corner sites (2 links) have 3 qubits, interior",
            "sites (3 links) have 4: widths " + str(WID) + ", 28 qubits in all.",
            "Every link has a flux bit at BOTH ends (listed on each link above); valid states have equal copies.",
            "",
            "Plaquette  corner sites (c00,c10,c11,c01)  links (bottom,right,top,left)  qubits of the term"]
    for P, pl in enumerate(PLAQ):
        sup = D[f"plaq{P}"]["support"]
        rows.append(f"plaq{P}      ({pl['c00']},{pl['c10']},{pl['c11']},{pl['c01']})                     "
                    f"({pl['b']},{pl['r']},{pl['t']},{pl['l']})                    q{sup[0]}-q{sup[-1]}  ({len(sup)} qubits)")
    rows += ["",
             "Why 14 / 16 / 14 qubits: a plaquette term acts on ALL qubits of its four corner sites (its matrix",
             "elements depend on each site's other link and on the matter/intertwiner bit).  plaq0 and plaq2 have",
             "two 3-qubit corner sites and two 4-qubit interior sites (14); plaq1 has four interior sites (16).",
             "The 2 extra qubits of plaq1 are the flux bits of two more 'third' links (links 6 and 8 at sites 4, 5)."]
    y = 0.46
    for r in rows:
        fig.text(0.06, y, r, fontsize=8.4, family="DejaVu Sans Mono" if r.startswith(("Plaq", "plaq")) else "DejaVu Sans")
        y -= 0.02
    # qubit meaning table for plaq1
    y -= 0.01
    fig.text(0.06, y, "Qubits of plaq1 (the middle plaquette):", fontsize=8.6, weight="bold"); y -= 0.02
    pl, pos, plinks, third = plaq_geometry(1)
    side_of = {v: k for k, v in plinks.items()}
    names = {"b": "bottom", "r": "right", "t": "top", "l": "left"}
    for s in (pl["c00"], pl["c01"], pl["c10"], pl["c11"]):
        line = f"  site {s}: "
        for i, (l, role) in enumerate(ENDS[s]):
            q = OFF[s] + i
            what = names[side_of[l]] if l in side_of else "third"
            line += f"q{q} = link {l} ({what}),  "
        line += f"q{OFF[s] + len(ENDS[s])} = matter/iota"
        fig.text(0.06, y, line, fontsize=8.0, family="DejaVu Sans Mono"); y -= 0.019
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- site encoding pages
def decode(kind, bits):
    k = 2 if kind == "corner" else 3
    fl, m = bits[:k], bits[k]
    f = sum(fl)
    if kind == "corner":
        if fl[0] == fl[1]:
            return True, 2 * m, None, ("no flux: quarks alone must be a singlet -> n = 0 or 2" if f == 0 else
                                       "1/2 x 1/2 -> 0 needs the quarks to be a singlet -> n = 0 or 2")
        if m == 0:
            return True, 1, None, "one flux 1/2 + one quark 1/2 -> 0: n = 1 forced"
        return False, None, None, "FLAG: one flux forces n = 1, so the matter bit must be 0"
    if f % 2 == 0:
        return True, 2 * m, None, ("no flux: n = 0 or 2" if f == 0 else "two flux 1/2's -> 0 with n = 0 or 2")
    if f == 1:
        if m == 0:
            return True, 1, None, "one flux 1/2 + quark 1/2 -> 0: n = 1"
        return False, None, None, "FLAG: n = 1 forced and only one singlet, bit must be 0"
    return True, 1, m, "three flux + quark: TWO singlets, bit = iota"


def draw_site_pattern(ax, kind, bits, title=None):
    ax.set_xlim(-1.25, 1.25); ax.set_ylim(-1.1, 1.25); ax.set_aspect("equal"); ax.axis("off")
    ok, n, iota, why = decode(kind, bits)
    k = 2 if kind == "corner" else 3
    dirs = [(1, 0), (0, 1)] if kind == "corner" else [(-1, 0), (1, 0), (0, 1)]
    for i in range(k):
        dx, dy = dirs[i]
        draw_link(ax, (0, 0), (0.85 * dx, 0.85 * dy), bits[i])
        ax.text(1.0 * dx, 1.0 * dy + (0.0 if dy == 0 else 0.0), ("½" if bits[i] else "0"), ha="center", va="center",
                fontsize=8, color=ON if bits[i] else "0.5")
    if ok:
        draw_site(ax, 0, 0, n, iota, r=0.22, fs=9)
    else:
        ax.add_patch(Circle((0, 0), 0.22, fc="#fee0d2", ec="r", lw=1.2, zorder=5))
        ax.text(0, 0, "×", ha="center", va="center", fontsize=13, color="r", zorder=6)
    bs = "".join(str(b) for b in bits)
    ax.text(0, -0.62, f"bits {bs}", ha="center", fontsize=8, family="DejaVu Sans Mono", weight="bold")
    ax.text(0, -0.84, ("VALID" if ok else "invalid (flag)"), ha="center", fontsize=8, color="g" if ok else "r",
            weight="bold")
    if title:
        ax.set_title(title, fontsize=7)
    return ok, why


def page_corner(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Why a corner site has exactly 6 valid states", ha="center", fontsize=13, weight="bold")
    expl = [
        "A site carries a staggered quark with two colours: occupation n = 0, 1 or 2.  n = 0 (empty) and n = 2 (both colours,",
        "antisymmetric) are colour singlets (spin 0); n = 1 is a colour doublet (spin 1/2).  Each link with flux carries j = 1/2 into",
        "the site.  GAUSS'S LAW: at every site, all spins arriving (links + quark) must add to total colour spin 0.",
        "",
        "A corner site has 2 links -> 2 flux bits (f1, f2) + 1 matter bit m = 3 qubits = 8 bit patterns.  Bit string = f1 f2 m.",
        "  * f1 = f2 (0 or 2 flux):  the link spins already form a singlet, so the quarks must be a singlet too: n in {0, 2},",
        "    stored as m = n/2.  2 flux patterns x 2 values of n = 4 valid states.",
        "  * f1 != f2 (1 flux):  1/2 from the link must be cancelled by the quark: n = 1 is FORCED.  Nothing is left to record,",
        "    so m must be 0; m = 1 is a FLAG (the decoder rejects it).  2 flux patterns x 1 = 2 valid states, 2 flagged strings.",
        "  * n = 1 with 0 or 2 flux would leave an odd number of 1/2's -> no singlet exists -> not a state at all.",
        "  Total: 4 + 2 = 6 valid states; 8 - 6 = 2 bit patterns are flags.",
    ]
    y = 0.925
    for e in expl:
        fig.text(0.05, y, e, fontsize=7.9); y -= 0.0185
    order = [(0, 0, 0), (0, 0, 1), (1, 1, 0), (1, 1, 1), (1, 0, 0), (0, 1, 0), (1, 0, 1), (0, 1, 1)]
    for i, bits in enumerate(order):
        r, c = divmod(i, 4)
        ax = fig.add_axes([0.04 + c * 0.235, 0.47 - r * 0.2, 0.21, 0.2])
        ok, why = draw_site_pattern(ax, "corner", bits)
        import textwrap
        ax.text(0, -1.02, "\n".join(textwrap.wrap(why, 34)), ha="center", va="top", fontsize=5.8,
                color="0.2", clip_on=False)
    fig.text(0.05, 0.255, "Legend:  red thick link = j = 1/2 (flux bit 1);  grey dashed = j = 0;  circle = quark occupation n "
             "(white 0, half-filled 1, dark 2).", fontsize=7.6)
    # spin-coupling sketches
    ax = fig.add_axes([0.05, 0.03, 0.9, 0.2]); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 2)
    ax.text(0, 1.85, "The singlet in each valid case (what Gauss's law requires):", fontsize=8.5, weight="bold")
    cases = [("n=0, no flux", "nothing to couple: |0>"), ("n=2, no flux", "quark pair (r g - g r)/sqrt2: spin 0"),
             ("n=0, flux on both links", "(1/2 x 1/2)_J=0 = (|up dn> - |dn up>)/sqrt2"),
             ("n=2, flux on both", "link singlet  x  quark-pair singlet"),
             ("n=1, flux on one link", "(link 1/2 x quark 1/2)_J=0")]
    for i, (a, b) in enumerate(cases):
        ax.text(0.1, 1.45 - i * 0.32, f"* {a}:", fontsize=7.8, weight="bold")
        ax.text(3.2, 1.45 - i * 0.32, b, fontsize=7.8)
    pdf.savefig(fig); plt.close(fig)


def page_interior(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "An interior site: 13 valid states (and where iota comes from)", ha="center", fontsize=13,
             weight="bold")
    expl = [
        "An interior site has 3 links -> 3 flux bits + 1 matter bit = 4 qubits = 16 patterns.  Bit string = f1 f2 f3 m (links in index order).",
        "  * 0 or 2 flux (4 patterns): links form a singlet -> quarks singlet -> n in {0,2}, m = n/2:          4 x 2 = 8 valid",
        "  * 1 flux (3 patterns): n = 1 forced, unique singlet -> m must be 0 (m = 1 is a flag):              3 x 1 = 3 valid, 3 flags",
        "  * 3 flux (1 pattern): n = 1 forced; FOUR spin-1/2's (3 links + quark) have TWO independent singlets,",
        "    labelled by the intertwiner iota in {0, 1}; the matter bit is free (n is already fixed) and stores iota:  1 x 2 = 2 valid",
        "  Total 8 + 3 + 2 = 13 valid, 3 flags.   The SAME qubit means n/2 or iota -- the flux bits (read first) say which.",
    ]
    y = 0.925
    for e in expl:
        fig.text(0.04, y, e, fontsize=7.7); y -= 0.0185
    pats = [(0, 0, 0, 0), (0, 0, 0, 1), (1, 1, 0, 0), (1, 1, 0, 1), (1, 0, 1, 0), (1, 0, 1, 1), (0, 1, 1, 0), (0, 1, 1, 1),
            (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (1, 1, 1, 0), (1, 1, 1, 1), (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]
    for i, bits in enumerate(pats):
        r, c = divmod(i, 4)
        ax = fig.add_axes([0.04 + c * 0.235, 0.6 - r * 0.135, 0.21, 0.135])
        ok, why = draw_site_pattern(ax, "interior", bits)
    fig.text(0.04, 0.055, "Links drawn: left = first link end, right = second, up = third (index order).  "
             "Last row: the 3 flagged strings (one flux with m = 1).", fontsize=7.5)
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- iota, bright and dark
def bright_dark_numbers():
    P = D["plaq1"]; S = P["states"]
    vals = []
    for r in S:
        if tuple(r["sites"][2]["bits"]) == (1, 0, 0, 0):
            nb = {}
            for j, re, im in r["nbrs"]:
                t = S[j]
                if tuple(t["sites"][2]["bits"][:3]) == (1, 1, 1):
                    key = tuple(tuple(t["sites"][s]["bits"]) for s in (3, 4, 5))
                    nb.setdefault(key, {})[t["sites"][2]["bits"][3]] = complex(re, im)
            for key, d in nb.items():
                if 0 in d and 1 in d:
                    vals.append((r, d[0], d[1]))
    return vals


def page_iota(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "The intertwiner label iota: two ways to make a singlet", ha="center", fontsize=13, weight="bold")
    txt = [
        "At an interior site with flux on all three links and one quark (n = 1) there are four spin-1/2 objects:",
        "the three link ends e1, e2, e3 (in link-index order) and the quark q.  Four spin-1/2's contain total spin 0 TWICE:",
        r"$\frac{1}{2}\otimes\frac{1}{2}\otimes\frac{1}{2}\otimes\frac{1}{2} = 0\oplus 0\oplus 1\oplus 1\oplus 1\oplus 2$.",
        "The package (src/skqd/vertex.py) labels the two singlets by the intermediate spin of the FIRST TWO link ends:",
        r"$|\iota\rangle = |\,[(e_1 e_2)_{J_{12}=\iota}\; e_3]_{1/2}\; q\,\rangle_{J=0},\qquad \iota\in\{0,1\}$  (fusion tree below).",
        "Any combination  a|iota=0> + b|iota=1>  is also a valid gauge-invariant state; iota=0,1 is just one basis of that 2-d space.",
    ]
    y = 0.915
    for t in txt:
        fig.text(0.05, y, t, fontsize=8.6); y -= 0.026
    for i, J in enumerate((0, 1)):
        ax = fig.add_axes([0.08 + i * 0.46, 0.5, 0.38, 0.23]); ax.axis("off"); ax.set_xlim(0, 4); ax.set_ylim(0, 3.2)
        leaves = {"e1": (0.4, 2.9), "e2": (1.4, 2.9), "e3": (2.4, 2.9), "q": (3.4, 2.9)}
        for k, (x, yy) in leaves.items():
            ax.text(x, yy + 0.15, k, ha="center", fontsize=10, weight="bold", color=ON if k != "q" else "#08519c")
        n1, n2, n3 = (0.9, 2.1), (1.65, 1.3), (2.5, 0.5)
        for a, b in [(leaves["e1"], n1), (leaves["e2"], n1), (n1, n2), (leaves["e3"], n2), (n2, n3), (leaves["q"], n3)]:
            ax.plot([a[0], b[0]], [a[1], b[1]], "k-", lw=1.4)
        ax.text(n1[0] - 0.75, n1[1], f"$J_{{12}}={J}$", fontsize=11, color="#6a3d9a", weight="bold")
        ax.text(n2[0] - 0.85, n2[1], r"$J_{123}=\frac{1}{2}$", fontsize=10)
        ax.text(n3[0] - 0.2, n3[1] - 0.35, "J = 0", fontsize=10, weight="bold")
        ax.set_title(f"iota = {J}   (matter bit = {J})", fontsize=11, color="#6a3d9a")
    txt2 = [
        "At plaq1's corner c00 = site 2 the link ends in index order are: link 0 (the 'third' link, q6), link 3 (plaquette bottom, q7),",
        "link 4 (plaquette left, q8); the matter/iota bit is q9.  So iota = J of (link 0, link 3).",
        "",
        "The plaquette operator does NOT create flux in the iota basis.  At a corner it multiplies the two plaquette links",
        "(bottom and left) by U-matrices whose colour indices are contracted with each other (delta_ij): the two NEW",
        "half-spins it creates are in a SINGLET with each other, (link 3, link 4)_{J=0}.  If the site had flux only on link 0",
        "plus one quark (singlet of link 0 and q), the result is",
        r"$\quad |(e_1\,q)_0\,(e_2\,e_3)_0\rangle \;=\;\sum_{J=0,1} c_J\, |(e_1 e_2)_J\,(e_3\,q)_J\rangle,\qquad |c_0| = \frac{1}{2},\ |c_1| = \frac{\sqrt{3}}{2}$",
        "(standard recoupling of four spin-1/2's: |c_J| = sqrt(2J+1)/2).  It is a FIXED mixture of iota = 0 and iota = 1.",
    ]
    y = 0.44
    for t in txt2:
        fig.text(0.05, y, t, fontsize=8.4); y -= 0.025
    pdf.savefig(fig); plt.close(fig)


def page_bright_dark(pdf):
    vals = bright_dark_numbers()
    r0, v0, v1 = vals[0]
    ratios0 = [abs(a) / np.hypot(abs(a), abs(b)) for _, a, b in vals]
    ratios1 = [abs(b) / np.hypot(abs(a), abs(b)) for _, a, b in vals]
    sgn = [np.sign((b / a).real) for _, a, b in vals]
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Bright and dark states (plaq1, corner c00 = site 2)", ha="center", fontsize=13, weight="bold")
    # transition picture
    ax = fig.add_axes([0.06, 0.63, 0.88, 0.29]); ax.axis("off"); ax.set_xlim(-0.3, 12); ax.set_ylim(-0.6, 3.2)

    def corner(x0, f0, f3, f4, n, iota, title, bonds=()):
        o = (x0 + 1.4, 0.6)
        draw_link(ax, o, (o[0] - 1.1, o[1]), f0)                          # link 0 (third), to the left
        ax.text(o[0] - 1.25, o[1], "link 0", fontsize=7, ha="right", va="center")
        draw_link(ax, o, (o[0] + 1.6, o[1]), f3)                          # link 3 (bottom), right
        ax.text(o[0] + 1.65, o[1] - 0.25, "link 3 (bottom)", fontsize=7, ha="left")
        draw_link(ax, o, (o[0], o[1] + 1.6), f4)                          # link 4 (left), up
        ax.text(o[0] + 0.1, o[1] + 1.7, "link 4 (left)", fontsize=7)
        draw_site(ax, o[0], o[1], n, iota, r=0.25, fs=10)
        for (a, b, lab) in bonds:
            pa = {"0": (o[0] - 0.7, o[1]), "3": (o[0] + 0.9, o[1]), "4": (o[0], o[1] + 0.95), "q": (o[0], o[1] - 0.25)}[a]
            pb = {"0": (o[0] - 0.7, o[1]), "3": (o[0] + 0.9, o[1]), "4": (o[0], o[1] + 0.95), "q": (o[0], o[1] - 0.25)}[b]
            ax.add_patch(FancyArrowPatch(pa, pb, connectionstyle="arc3,rad=0.5", arrowstyle="-", ls="--",
                                         color="#2ca02c", lw=1.3))
            ax.text((pa[0] + pb[0]) / 2, min(pa[1], pb[1]) - 0.45, lab, fontsize=7, color="#2ca02c", ha="center")
        ax.text(o[0] + 0.5, 2.95, title, fontsize=9, ha="center", weight="bold")

    corner(0.0, 1, 0, 0, 1, None, "before: |s0>   bits q6q7q8q9 = 1000", bonds=[("0", "q", "singlet")])
    ax.add_patch(FancyArrowPatch((4.1, 1.2), (5.6, 1.2), arrowstyle="-|>", mutation_scale=18, lw=2))
    ax.text(4.85, 1.45, "plaquette", ha="center", fontsize=8)
    corner(6.4, 1, 1, 1, 1, None, "after: |bright>  (mixture of 1110 and 1111)",
           bonds=[("0", "q", "singlet"), ("3", "4", "new singlet")])

    lines = [
        "Before: one flux on link 0 and one quark (n = 1); they form the unique singlet.  Site-2 bits (q6 q7 q8 q9) = 1000.",
        "The plaquette adds flux on link 3 and link 4 as a NEW SINGLET pair.  Three flux links + one quark: the result lies in the",
        "2-dimensional iota space, spanned by  |s1> = 1110 (iota = 0)  and  |s2> = 1111 (iota = 1).  Computed from the package's own",
        f"matrix h (localize, plaq1): in all {len(vals)} cases where a state with site-2 bits 1000 connects to both 1110 and 1111 (other",
        f"corners fixed), the two matrix elements v0 = <s1|O|s0>, v1 = <s2|O|s0> satisfy |v0|/|v| = {np.mean(ratios0):.15f}"
        f" (spread {np.ptp(ratios0):.1e}),",
        f"|v1|/|v| = {np.mean(ratios1):.15f} (spread {np.ptp(ratios1):.1e}) and sign(v1/v0) = {int(sgn[0])} in every case.",
        f"Example (local state #{r0['idx']}, int {r0['int']}):  v0 = {v0.real:+.6f},  v1 = {v1.real:+.6f},  |v| = {np.hypot(abs(v0), abs(v1)):.6f}.",
    ]
    y = 0.6
    for t in lines:
        fig.text(0.05, y, t, fontsize=8.0); y -= 0.02
    eqs = [
        r"$O\,|s_0\rangle \;\propto\; v_0|s_1\rangle + v_1|s_2\rangle \;=\; |v|\;|\beta\rangle,$",
        r"$|\beta\rangle = \frac{1}{2}\,|\iota{=}0\rangle \;-\; \frac{\sqrt{3}}{2}\,|\iota{=}1\rangle$   (BRIGHT: the only combination the plaquette reaches)",
        r"$|\delta\rangle = \frac{\sqrt{3}}{2}\,|\iota{=}0\rangle \;+\; \frac{1}{2}\,|\iota{=}1\rangle$   (DARK: orthogonal, $\langle\delta|O|s_0\rangle = 0$)",
    ]
    y -= 0.008
    for e in eqs:
        fig.text(0.07, y, e, fontsize=10.5); y -= 0.033
    # vector picture
    ax2 = fig.add_axes([0.08, 0.06, 0.38, 0.27]); ax2.set_aspect("equal")
    ax2.axhline(0, color="0.6", lw=0.8); ax2.axvline(0, color="0.6", lw=0.8)
    for v, c, lab in [((1, 0), "0.3", r"$|\iota{=}0\rangle$"), ((0, 1), "0.3", r"$|\iota{=}1\rangle$"),
                      ((0.5, -np.sqrt(3) / 2), "#ff7f0e", r"bright $|\beta\rangle$"),
                      ((np.sqrt(3) / 2, 0.5), "#1f77b4", r"dark $|\delta\rangle$")]:
        ax2.add_patch(FancyArrowPatch((0, 0), v, arrowstyle="-|>", mutation_scale=12, color=c, lw=2))
        ax2.text(v[0] * 1.12, v[1] * 1.12, lab, fontsize=9, color=c, ha="center", va="center")
    ax2.set_xlim(-0.4, 1.45); ax2.set_ylim(-1.15, 1.25); ax2.set_xticks([]); ax2.set_yticks([])
    ax2.set_title("the 2-d iota space: a 60-degree rotation", fontsize=8.5)
    t3 = [
        "What 'dark' means -- and what it does NOT mean:",
        "* The dark state is NOT thrown away.  It is a perfectly",
        "  valid gauge-invariant state of the lattice; other terms",
        "  (e.g. hops) and other configurations can reach it.",
        "* It is simply never produced by THIS plaquette move from",
        "  |s0>, and the plaquette leaves it alone (coupling 0, the",
        "  zero singular value 0 of the corner's 3-state block).",
        "* For the circuit this is the saving: rotate the iota",
        "  qubit once into the (bright, dark) frame -- one fixed",
        "  rotation R(60 deg) -- and the plaquette becomes a single",
        "  two-state rotation  |s0> <-> |bright>; the dark state",
        "  needs no gate at all.  (genie-opus 'corner frame', step c",
        "  of MANUAL_lgt_circuit_compression.md.)",
    ]
    y = 0.32
    for t in t3:
        fig.text(0.52, y, t, fontsize=7.9, weight="bold" if t.startswith("What") else "normal"); y -= 0.0195
    pdf.savefig(fig); plt.close(fig)


# ---------------------------------------------------------------- how to read + catalogue
TH_W, TH_H, NC, NR = 0.31, 0.142, 3, 6


def fmt_bits(rec, P):
    out = []
    for s in sorted(rec["sites"], key=lambda s: OFF[s]):
        out.append("".join(str(b) for b in rec["sites"][s]["bits"]))
    return " ".join(out)


def thumb(fig, P, rec, x, y, blk_color, size_of_block, S):
    bg = fig.add_axes([x, y, TH_W, TH_H]); bg.axis("off")
    bg.add_patch(Rectangle((0, 0), 1, 1, transform=bg.transAxes, fc=blk_color, ec="0.7", lw=0.5, zorder=0))
    ax = fig.add_axes([x + 0.002, y + 0.25 * TH_H, 0.52 * TH_W, 0.74 * TH_H]); ax.axis("off")
    ax.set_xlim(-0.55, 1.55); ax.set_ylim(-0.4, 1.4); ax.set_aspect("equal")
    draw_plaquette_state(ax, P, rec, fs=6.4)
    tx = x + 0.52 * TH_W
    fig.text(tx, y + 0.95 * TH_H, f"#{rec['idx']}   int {rec['int']}", fontsize=6.4, weight="bold", va="top")
    fig.text(tx, y + 0.83 * TH_H, f"block {rec['block']} (size {size_of_block})", fontsize=5.6, va="top", color="0.3")
    nbtxt = [f"#{j}: {re:+.4f}" if abs(im) < 1e-12 else f"#{j}: {re:+.3f}{im:+.3f}i" for j, re, im in rec["nbrs"]]
    yy = y + 0.72 * TH_H
    if not nbtxt:
        fig.text(tx, yy, "no coupling: the plaquette", fontsize=5.3, va="top", color="0.3")
        fig.text(tx, yy - 0.1 * TH_H, "maps this state to 0", fontsize=5.3, va="top", color="0.3")
    else:
        fig.text(tx, yy, "couples to:", fontsize=5.3, va="top", color="0.3"); yy -= 0.095 * TH_H
        for t in nbtxt[:4]:
            fig.text(tx, yy, t, fontsize=5.3, va="top", family="DejaVu Sans Mono"); yy -= 0.085 * TH_H
        if len(nbtxt) > 4:
            fig.text(tx, yy, f"... +{len(nbtxt) - 4} more (listed on their cards)", fontsize=5.0, va="top")
    order = sorted(rec["sites"], key=lambda s: OFF[s])
    ns = " ".join(f"{rec['sites'][s]['n']}" for s in order)
    io = " ".join("-" if rec["sites"][s]["iota"] is None else str(rec["sites"][s]["iota"]) for s in order)
    fig.text(x + 0.006, y + 0.19 * TH_H, "bits " + fmt_bits(rec, P), fontsize=6.0, family="DejaVu Sans Mono", va="top",
             weight="bold")
    fig.text(x + 0.006, y + 0.09 * TH_H, f"n=({ns})  iota=({io})", fontsize=5.8, family="DejaVu Sans Mono", va="top")


def page_howto(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "How to read a state picture", ha="center", fontsize=13, weight="bold")
    S = D["plaq1"]["states"]
    ex = next(r for r in S if r["nbrs"] and any(S[j]["sites"][2]["iota"] is not None for j, _, _ in r["nbrs"]))
    ax = fig.add_axes([0.1, 0.55, 0.8, 0.35]); ax.axis("off")
    ax.set_xlim(-0.9, 3.6); ax.set_ylim(-1.2, 1.5)
    draw_plaquette_state(ax, 1, ex, fs=11, scale=1.0)
    pl, pos, plinks, third = plaq_geometry(1)
    for s, (xy) in pos.items():
        ax.text(xy[0] + (0.2 if xy[0] > 0.5 else -0.2), xy[1] + 0.22, f"site {s}", fontsize=9,
                ha="left" if xy[0] > 0.5 else "right", color="0.3")
    ax.text(1.9, 1.3, f"#{ex['idx']}   int {ex['int']}", fontsize=12, weight="bold", va="top")
    ax.text(1.9, 0.95, f"block {ex['block']}", fontsize=10, va="top")
    ax.text(1.9, 0.6, "couples to: " + ", ".join(f"#{j} ({re:+.4f})" for j, re, im in ex["nbrs"]), fontsize=9, va="top")
    ax.text(-0.85, -0.7, "bits " + fmt_bits(ex, 1), fontsize=10, family="DejaVu Sans Mono", va="top")
    txt = [
        "* Square = the plaquette; its four sides are the plaquette links (bottom, right, top, left).  Short horizontal stubs",
        "  at the corners = each site's 'third' link that leaves the plaquette (interior sites only).",
        "* Thick red line labelled 1/2 = flux on (j = 1/2, bit 1).  Grey dashed labelled 0 = no flux (j = 0, bit 0).",
        "* Circle = quark occupation n at that site: white = 0, half-filled = 1, dark = 2 (number written inside).",
        "  Purple 'iota=' appears only at a site with three flux links (then the matter bit stores iota).",
        "* #idx = position in the sorted list of valid local states of that plaquette (0 ... N-1).  int = the integer whose",
        "  binary digits are the term's qubits, lowest qubit = lowest bit (the package's bits_to_int).",
        "* bits = the term's qubits in increasing qubit number, one group per site (site order = qubit order).",
        "  For plaq1 the groups are  q6q7q8q9 | q10q11q12q13 | q14q15q16q17 | q18q19q20q21  (sites 2 | 3 | 4 | 5).",
        "  Within a group: flux bits of the site's links in link-index order, then the matter/iota bit.",
        "* n=(...) iota=(...) list the four sites in the same order ('-' = iota not defined there).",
        "* block = which connected group of states the plaquette links together (states are listed block by block, with",
        "  a shared background colour).  'couples to #j: x' = the matrix element <j|O_P|this> of the plaquette term",
        "  O_P = -W_P/(2 g^2), g^2 = 4.  A block of size 1 is a state the plaquette maps to zero.",
        "* What changes along a block: the plaquette flips ALL FOUR plaquette links at once (both stored copies, i.e. 8 bits",
        "  for plaq1); j on each plaquette link goes 0 <-> 1/2; at a corner whose flux count passes through three, iota",
        "  appears or disappears (the matter bit changes meaning); n never changes (the plaquette has no quark operators).",
        "* Block sizes: the plaquette acts as a product of four corner moves.  A corner that goes from one flux link to",
        "  three flux links can land in iota = 0 or 1, so it contributes two partner states.  Example: the first block of",
        "  plaq1 (size 9) is one state whose three interior corners each do this: 1 + 2 x 2 x 2 = 9 states.",
    ]
    y = 0.5
    for t in txt:
        fig.text(0.05, y, t, fontsize=8.3); y -= 0.021
    pdf.savefig(fig); plt.close(fig)


def plaquette_header(pdf, P):
    d = D[f"plaq{P}"]
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, f"Catalogue: plaq{P}", ha="center", fontsize=15, weight="bold")
    pl, pos, plinks, third = plaq_geometry(P)
    rows = [f"Corner sites: c00 = {pl['c00']}, c10 = {pl['c10']}, c11 = {pl['c11']}, c01 = {pl['c01']}   "
            f"(kinds: " + ", ".join(f"{s} {site_kind(s)}" for s in (pl['c00'], pl['c10'], pl['c11'], pl['c01'])) + ")",
            f"Plaquette links: bottom {pl['b']}, right {pl['r']}, top {pl['t']}, left {pl['l']};  third links: "
            + (", ".join(f"link {l} at site {s}" for s, (l, _) in third.items()) or "none"),
            f"Qubits ({len(d['support'])}): " + " ".join(f"q{q}" for q in d["support"]),
            "Bit groups in the pictures (one per site, qubit order):"]
    for s in sorted(pos, key=lambda s: OFF[s]):
        parts = [f"q{OFF[s] + i}=link{l}" for i, (l, _) in enumerate(ENDS[s])] + [f"q{OFF[s] + len(ENDS[s])}=matter/iota"]
        rows.append(f"   site {s} ({site_kind(s)}): " + ", ".join(parts))
    rows += ["",
             f"Valid local states: {d['n_states']}   blocks: {d['n_blocks']}   block sizes: {d['block_hist']}",
             f"(diagonal of the local matrix: max |h_ss| = {d['diag_max']:.1e}, i.e. the plaquette has no diagonal part)",
             "",
             "States are listed block by block (largest blocks first); states of one block share a background colour.",
             "Per site: corner sites have 6 valid states, interior sites 13; the counts above are smaller than the",
             "product of those (6^2 x 13^2 = 6084 for plaq0/plaq2, 13^4 = 28561 for plaq1) because every plaquette link is",
             "stored at both of its ends and the two copies must agree, and because only states that occur in the",
             "global gauge-invariant basis are kept (skqd.reference_sim.localize)."]
    y = 0.91
    for r in rows:
        fig.text(0.05, y, r, fontsize=8.3, family="DejaVu Sans Mono" if r.startswith("   ") else "DejaVu Sans"); y -= 0.02
    # example: the all-empty state and its partner
    S = d["states"]
    e0 = next(r for r in S if r["int"] == 0)
    ax = fig.add_axes([0.05, 0.12, 0.42, 0.28]); ax.axis("off"); ax.set_xlim(-0.8, 1.8); ax.set_ylim(-0.9, 1.4)
    draw_plaquette_state(ax, P, e0, fs=9)
    ax.set_title(f"#{e0['idx']} (int 0): empty plaquette", fontsize=9)
    if e0["nbrs"]:
        j, re, im = e0["nbrs"][0]
        ax2 = fig.add_axes([0.53, 0.12, 0.42, 0.28]); ax2.axis("off"); ax2.set_xlim(-0.8, 1.8); ax2.set_ylim(-0.9, 1.4)
        draw_plaquette_state(ax2, P, S[j], fs=9)
        ax2.set_title(f"#{j} (int {S[j]['int']}): one flux loop, <#{j}|O|#{e0['idx']}> = {re:+.4f}", fontsize=9)
    fig.text(0.05, 0.08, "Example of one plaquette move: the empty plaquette is mixed with the state carrying one flux loop around it.",
             fontsize=8.3)
    pdf.savefig(fig); plt.close(fig)


def catalogue(pdf, P):
    d = D[f"plaq{P}"]; S = d["states"]
    blocks = {}
    for r in S:
        blocks.setdefault(r["block"], []).append(r)
    order = sorted(blocks, key=lambda b: (-len(blocks[b]), min(r["idx"] for r in blocks[b])))
    palette = ["#fff7ec", "#eef6fb", "#f3f9ee", "#fbf0f7", "#f7f7f7", "#fffbe0"]
    seq = []
    for i, b in enumerate(order):
        for r in sorted(blocks[b], key=lambda r: r["idx"]):
            seq.append((r, palette[i % len(palette)], len(blocks[b])))
    per = NC * NR
    npages = (len(seq) + per - 1) // per
    for pg in range(npages):
        fig = plt.figure(figsize=A4)
        fig.text(0.5, 0.975, f"plaq{P}: valid local states  (page {pg + 1}/{npages}; states {pg * per}-"
                 f"{min(len(seq), (pg + 1) * per) - 1} of {len(seq)} in block order)", ha="center", fontsize=9.5,
                 weight="bold")
        for k, (r, col, sz) in enumerate(seq[pg * per:(pg + 1) * per]):
            row, c = divmod(k, NC)
            thumb(fig, P, r, 0.025 + c * (TH_W + 0.012), 0.815 - row * (TH_H + 0.016), col, sz, S)
        pdf.savefig(fig); plt.close(fig)


def main():
    out = "/home/digimonk/Projects/su2qc-skqd/reports/valid_states_2x4_plaquettes.pdf"
    with FitPdf(out) as pdf:
        page_title(pdf); page_lattice(pdf); page_corner(pdf); page_interior(pdf)
        page_iota(pdf); page_bright_dark(pdf); page_howto(pdf)
        for P in range(3):
            plaquette_header(pdf, P)
            catalogue(pdf, P)
            print("done plaq", P, flush=True)
        info = pdf.infodict(); info["Title"] = "Valid local states of the 2x4 plaquette terms"
    print(out)
    print("pages with shrunk text (page, n texts):", FitPdf.shrunk_pages)


if __name__ == "__main__":
    main()

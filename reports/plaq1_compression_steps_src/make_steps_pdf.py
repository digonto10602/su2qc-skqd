"""PDF: how the 2x4 plaq1 term was compressed, step by step, with circuit diagrams.

Numbers: plaq1_steps.pkl (analyse.py: every step rebuilt in a sandbox with genie-opus's code, counted with
c2x4.evaluate.counts and checked with c2x4.evaluate.verify_term_operator against the exact term) and
cf2_gates.pkl (gates.py: the actual CF2 gate list).  Stored values quoted with their file:
validation/S2_2x4.json (frozen synthesis), data/cert_it6_operator_plaq1_long.json (MILP), data/archive_it*.json.
"""
import json, pickle, subprocess, datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch, FancyBboxPatch

STUDY = "/home/digimonk/Projects/su2qc-skqd/2x4_compression_using_ai_v1"
ROOT = "/home/digimonk/Projects/su2qc-skqd"
O = pickle.load(open("plaq1_steps.pkl", "rb"))
G = pickle.load(open("cf2_gates.pkl", "rb"))
S2 = json.load(open(f"{ROOT}/validation/S2_2x4.json"))["data"]
SYN = S2["synth"]["2x4|exact"]["plaq1"]["per_theta"]["dt"]
STRUCT = S2["structure"]["structure_4"]["terms"]["plaq1"]
CERT = json.load(open(f"{STUDY}/data/cert_it6_operator_plaq1_long.json"))
P21 = json.load(open(f"{STUDY}/data/p2_1_structure.json"))["plaquettes"]["plaq1"]
COMMIT = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
A4 = (8.27, 11.69)
plt.rcParams.update({"font.size": 8.5, "font.family": "DejaVu Sans"})
STEPS = [("frozen", "frozen (package)"), ("cf1", "1-3: corner frames +\nladder + one rotation"),
         ("cf2", "4: clean qubits +\ndark-state flags"), ("cf2_sw", "5: sparse Walsh\nmultiplexor"),
         ("cf2_lin_milp", "6: exact-minimum\n(MILP) support")]
COL = ["#7f7f7f", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]


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


def text_block(fig, x, y, lines, fs=8.6, dy=0.0205, mono=False):
    for ln in lines:
        bold = ln.startswith("##")
        fig.text(x, y, ln.lstrip("#").strip() if bold else ln, fontsize=fs + (1 if bold else 0),
                 weight="bold" if bold else "normal", family="DejaVu Sans Mono" if mono else "DejaVu Sans")
        y -= dy
    return y


# ------------------------------------------------------------------ circuit drawing
def layer(gates, qubits):
    """Greedy as-soon-as-possible columns; a gate occupies the wire range between its qubits."""
    row = {q: i for i, q in enumerate(qubits)}
    free = {q: 0 for q in qubits}
    cols = []
    for g in gates:
        nm, qs = g[0], g[1]
        lo, hi = min(row[q] for q in qs), max(row[q] for q in qs)
        span = [q for q in qubits if lo <= row[q] <= hi]
        c = max(free[q] for q in span)
        cols.append(c)
        for q in span:
            free[q] = c + 1
    return cols


def draw_circuit(ax, gates, qubits, qlabels=None, title=None, hl=None, colw=1.0, fs=7):
    row = {q: i for i, q in enumerate(qubits)}
    cols = layer(gates, qubits)
    ncol = (max(cols) + 1) if cols else 1
    ny = len(qubits)
    Y = lambda q: ny - 1 - row[q]
    for q in qubits:
        ax.plot([-0.6, ncol * colw - 0.4], [Y(q), Y(q)], color="0.25", lw=0.8, zorder=1)
        ax.text(-0.75, Y(q), (qlabels or {}).get(q, f"q{q}"), ha="right", va="center", fontsize=fs)
    for g, c in zip(gates, cols):
        nm, qs, par = g[0], g[1], g[2]
        x = c * colw
        col = (hl or {}).get(id(g), "k")
        if nm == "cx":
            a, b = qs
            ax.plot([x, x], [Y(a), Y(b)], color=col, lw=1.0, zorder=2)
            ax.add_patch(Circle((x, Y(a)), 0.09, color=col, zorder=3))
            ax.add_patch(Circle((x, Y(b)), 0.2, fc="white", ec=col, lw=1.0, zorder=3))
            ax.plot([x - 0.2, x + 0.2], [Y(b), Y(b)], color=col, lw=1.0, zorder=4)
            ax.plot([x, x], [Y(b) - 0.2, Y(b) + 0.2], color=col, lw=1.0, zorder=4)
        elif nm in ("cp", "cz"):
            a, b = qs
            ax.plot([x, x], [Y(a), Y(b)], color=col, lw=1.0, zorder=2)
            for q in qs:
                ax.add_patch(Circle((x, Y(q)), 0.09, color=col, zorder=3))
            lab = "Z" if nm == "cz" or abs(abs(par) - np.pi) < 1e-9 else f"P({par / np.pi:+.2g}π)"
            ax.text(x + 0.12, (Y(a) + Y(b)) / 2, lab, fontsize=fs - 1.5, color=col, va="center")
        elif nm == "mux":
            tq, ctrls, lab = qs[0], qs[1:], par
            ys = [Y(q) for q in qs]
            ax.add_patch(FancyBboxPatch((x - 0.45, min(ys) - 0.32), 0.9 + colw * 1.6, max(ys) - min(ys) + 0.64,
                                        boxstyle="round,pad=0.02", fc="#fde0dd", ec="#c51b8a", lw=1.2, zorder=3))
            for q in ctrls:
                ax.add_patch(Circle((x - 0.25, Y(q)), 0.09, color="#c51b8a", zorder=4))
            ax.add_patch(Rectangle((x + 0.2, Y(tq) - 0.25), 0.9, 0.5, fc="white", ec="#c51b8a", zorder=4))
            ax.text(x + 0.65, Y(tq), "Ry", fontsize=fs, ha="center", va="center", zorder=5)
            ax.text(x + 0.55, max(ys) + 0.5, lab, fontsize=fs - 0.5, ha="center", color="#c51b8a")
        elif nm == "box":
            ys = [Y(q) for q in qs]
            ax.add_patch(FancyBboxPatch((x - 0.4, min(ys) - 0.3), 0.8 + colw * 0.8, max(ys) - min(ys) + 0.6,
                                        boxstyle="round,pad=0.02", fc=par[1], ec="k", lw=0.8, zorder=3))
            ax.text(x + colw * 0.4, (min(ys) + max(ys)) / 2, par[0], fontsize=fs - 0.5, ha="center", va="center",
                    zorder=4, rotation=90 if len(qs) > 2 else 0)
        else:
            q = qs[0]
            lab = {"ry": "Ry", "rz": "Rz", "x": "X", "unitary": "U", "h": "H"}.get(nm, nm)
            fc = {"unitary": "#efedf5", "x": "#fff7bc"}.get(nm, "white")
            ax.add_patch(Rectangle((x - 0.3, Y(q) - 0.25), 0.6, 0.5, fc=fc, ec=col, lw=0.9, zorder=3))
            ax.text(x, Y(q), lab, ha="center", va="center", fontsize=fs - 1, zorder=4)
            if nm == "ry" and par is not None:
                ax.text(x, Y(q) + 0.33, f"{par / np.pi:+.3g}π" if abs(par) > 1e-3 else f"{par:+.1e}", fontsize=fs - 2.5,
                        ha="center", va="bottom", color="0.35")
    ax.set_xlim(-2.2, ncol * colw + 0.4 + (1.6 if any(g[0] == "mux" for g in gates) else 0))
    ax.set_ylim(-0.8, ny + 0.4)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=fs + 1.5, loc="left")
    return ncol


def block_diagram(ax, slots, qubits, qlabels, title=None, fs=6.8):
    """slots: list of (width, [(label, [qubits], colour), ...]); boxes in one slot are side by side in time."""
    row = {q: i for i, q in enumerate(qubits)}
    ny = len(qubits)
    Y = lambda q: ny - 1 - row[q]
    xtot = sum(w for w, _ in slots) + 0.4 * len(slots)
    for q in qubits:
        ax.plot([-0.3, xtot], [Y(q), Y(q)], color="0.3", lw=0.7, zorder=1)
        ax.text(-0.45, Y(q), qlabels.get(q, f"q{q}"), ha="right", va="center", fontsize=fs - 0.5)
    x = 0.2
    for w, boxes in slots:
        for lab, qs, colr in boxes:
            ys = [Y(q) for q in qs]
            lo, hi = min(ys) - 0.38, max(ys) + 0.38
            ax.add_patch(FancyBboxPatch((x, lo), w, hi - lo, boxstyle="round,pad=0.02,rounding_size=0.15",
                                        fc=colr, ec="0.2", lw=0.8, zorder=3))
            ax.text(x + w / 2, (lo + hi) / 2, lab, ha="center", va="center", fontsize=fs, zorder=4,
                    rotation=0 if w >= 1.6 or (hi - lo) < 2.2 else 90)
        x += w + 0.4
    ax.set_xlim(-3.2, xtot + 0.1); ax.set_ylim(-0.9, ny + 0.2); ax.axis("off")
    if title:
        ax.set_title(title, fontsize=fs + 2, loc="left")


GATES = G["gates"]
CORN = G["corners"]
QL = {}
for c in CORN:
    QL[c["third"]] = f"q{c['third']} 3rd lk"
    QL[c["plinks"][0]] = f"q{c['plinks'][0]} lk{c['plink_ids'][0]}"
    QL[c["plinks"][1]] = f"q{c['plinks'][1]} lk{c['plink_ids'][1]}"
    QL[c["q"]] = f"q{c['q']} n/ι"


# ------------------------------------------------------------------ pages
def p_title(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.95, "Compressing the 2x4 plaq1 circuit, step by step", ha="center", fontsize=16, weight="bold")
    fig.text(0.5, 0.925, "from 66,468 to 202 two-qubit gates, exact at every step", ha="center", fontsize=11)
    ax = fig.add_axes([0.12, 0.58, 0.8, 0.31])
    vals = [O[k]["n_2q"] for k, _ in STEPS]
    ax.bar(range(len(STEPS)), vals, color=COL)
    ax.set_yscale("log"); ax.set_ylim(80, 2e5)
    for i, v in enumerate(vals):
        ax.text(i, v * 1.15, f"{v:,}", ha="center", fontsize=10, weight="bold")
        ax.text(i, 95, f"depth {O[STEPS[i][0]]['depth_2q']:,}", ha="center", fontsize=7, color="white" if i else "k",
                rotation=90, va="bottom")
    ax.set_xticks(range(len(STEPS))); ax.set_xticklabels([s[1] for s in STEPS], fontsize=7.5)
    ax.set_ylabel("two-qubit gates (CX + controlled phase), log scale")
    ax.set_title("plaq1 term, class A (exact for every input), one coarse step at theta = dt", fontsize=9)
    rows = ["## What this PDF shows",
            "plaq1 is the middle plaquette of the 2x4 ladder: the term  exp(-i theta O_plaq1)  on 16 qubits (q6-q21), where",
            "O_plaq1 = -W_plaq1/(2 g^2) is the magnetic (Wilson-loop) energy of the middle square.  In the frozen circuits it",
            f"cost {O['frozen']['n_2q']:,} CNOTs, {SYN['counts']['cx'] / 71520:.1%} of all 71,520 term CNOTs of a 2x4 circuit.  genie-opus brought it to "
            f"{O['cf2_lin_milp']['n_2q']} in six steps.",
            "Each step is drawn with an example from the real circuit, its equation, its gate count and its accuracy.",
            "",
            "## Every step is exact (largest error of the term, all 1,831 valid input states, bar 1e-10):"]
    for k, lab in STEPS:
        d = O[k]
        rows.append(f"   {lab.replace(chr(10), ' '):48s} {d['n_2q']:>7,} 2q gates   depth {d['depth_2q']:>6,}   "
                    f"max error {d['max_dev']:.1e}")
    rows += ["",
             "## Where the numbers come from",
             "Every count and error above was recomputed for this PDF: each step was rebuilt with genie-opus's code",
             "(2x4_compression_using_ai_v1/src/c2x4: plaqfactor.cf1_gates / cf2_gates, sparsemux, linsynth, proposals) in a",
             "sandbox, counted with c2x4.evaluate.counts and checked against the exact term with verify_term_operator.",
             "They equal the stored archive values (data/archive_it1..6.json: 2110, 238, 220, 202) and the frozen synthesis",
             f"in validation/S2_2x4.json (cx {SYN['counts']['cx']:,}, ry {SYN['counts']['ry']:,}).",
             f"Repository commit {COMMIT}; generated {datetime.date.today().isoformat()}."]
    text_block(fig, 0.07, 0.52, rows, fs=8.2, dy=0.0195)
    pdf.savefig(fig); plt.close(fig)


def p_frozen(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Step 0 - the frozen circuit: why plaq1 cost 66,468 CNOTs", ha="center", fontsize=13, weight="bold")
    rows = ["## How the package builds the term (src/skqd/circuits_ir.py, structured_term_gates)",
            f"1. Keep the {STRUCT['local_states']:,} valid local states of the 16 qubits; the term splits them into {STRUCT['blocks']} connected blocks",
            f"   (sizes {STRUCT['block_size_histogram']}).",
            "2. Inside each block write exp(theta A) as rounds of two-state (Givens) rotations between basis states.",
            "3. All rotations of one round that flip the same 8 plaquette bits are merged into one MULTIPLEXED rotation:",
            "   CNOTs squeeze the 8-bit flip onto one target qubit; the other 15 qubits select the angle; controls that do",
            "   not change the angle are dropped.",
            f"4. Result: {SYN['n_multiplexed_rotations']} multiplexed rotations with {SYN['controls_min']}-{SYN['controls_max']} controls "
            f"(median {SYN['controls_median']}).",
            "",
            "## A multiplexed rotation and its Gray-code circuit (here m = 3 controls)",
            r"$\sum_c |c\rangle\langle c| \otimes R_y(\theta_c)$ = 2^m rotations alternating with 2^m CNOTs (src/skqd/circuits_ir.py ucr_gray).",
            "The cost doubles with every control: 2^m CNOTs and 2^m Ry."]
    y = text_block(fig, 0.06, 0.92, rows, fs=8.4)
    ax = fig.add_axes([0.04, y - 0.2, 0.92, 0.19])
    m = 3
    gates = []
    order = [0, 1, 0, 2, 0, 1, 0, 2]
    for j in range(8):
        gates.append(("ry", [3], None)); gates.append(("cx", [order[j], 3], None))
    draw_circuit(ax, gates, [0, 1, 2, 3], {0: "c1", 1: "c2", 2: "c3", 3: "target"}, colw=0.85, fs=8,
                 title="ucr_gray, m = 3: 8 Ry + 8 CNOT (one control changes between consecutive angles)")
    ax2 = fig.add_axes([0.1, y - 0.5, 0.45, 0.25])
    h = {int(k): v for k, v in SYN["controls_histogram"].items()}
    ks = sorted(h)
    ax2.bar(ks, [h[k] for k in ks], color="#7f7f7f")
    for k in ks:
        ax2.text(k, h[k] + 0.5, f"{h[k]}\n(2^{k}={2 ** k})", ha="center", fontsize=7)
    ax2.set_xlabel("controls m per multiplexed rotation"); ax2.set_ylabel("number of rotations")
    ax2.set_ylim(0, max(h.values()) * 1.35)
    ax2.set_title(f"the {SYN['n_multiplexed_rotations']} multiplexed rotations of plaq1", fontsize=8.5)
    tot = sum(h[k] * 2 ** k for k in ks)
    fr = SYN["frame_cnots"]
    rows = [f"Ry = sum 2^m = " + " + ".join(f"{h[k]}x{2 ** k}" for k in ks) + f" = {tot:,}  (stored ry {SYN['counts']['ry']:,})",
            f"CX = {tot:,} (Gray cores) + 2 x {fr} (control-reduction frames) + {SYN['counts']['cx'] - tot - 2 * fr} (squeeze CNOTs)",
            f"   = {SYN['counts']['cx']:,}  (validation/S2_2x4.json, data.synth['2x4|exact'].plaq1).",
            "",
            "Why so many controls: the angle of a rotation depends on what is happening at ALL FOUR corners at once",
            "(third-link flux, quark number, intertwiner).  The general method cannot see that this dependence is a",
            "PRODUCT of four small corner pieces, so it keeps 7-11 qubits as controls and pays 2^m for each."]
    cost = ["## Cost", "Ry = sum over rotations of 2^m:"] + [f"   {h[k]} x 2^{k} = {h[k] * 2 ** k:,}" for k in ks] + [
            f"   total {tot:,}  (stored {SYN['counts']['ry']:,})", "",
            "CX = Gray cores + frames + squeeze:", f"   {tot:,} + 2 x {fr} + {SYN['counts']['cx'] - tot - 2 * fr}",
            f"   = {SYN['counts']['cx']:,}  (stored {SYN['counts']['cx']:,})"]
    text_block(fig, 0.6, y - 0.26, cost, fs=8.2)
    why = ["## Why so many controls",
           "The angle of a rotation depends on what happens at ALL FOUR corners at once (third-link flux, quark",
           "number, intertwiner).  The general method cannot see that this dependence is a PRODUCT of four small",
           "corner pieces, so it keeps 7-11 qubits as controls and pays 2^m for each rotation.",
           "Source: validation/S2_2x4.json, data.synth['2x4|exact'].plaq1 (counts, controls histogram, frame_cnots)."]
    text_block(fig, 0.06, y - 0.565, why, fs=8.3)
    pdf.savefig(fig); plt.close(fig)


def p_factor(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "The key discovery: the plaquette is a product of four corner pieces", ha="center", fontsize=13,
             weight="bold")
    rows = ["## Structure test (genie-opus, scripts/p2_1_structure.py -> data/p2_1_structure.json)",
            "On the valid states the 16-qubit plaquette matrix factorises EXACTLY over its four corner sites:",
            r"$h_{P}|_{\rm valid} \;=\; A_{c00}\otimes A_{c10}\otimes A_{c11}\otimes A_{c01}$,   each $A_c$ a small 4-qubit matrix of one corner site.",
            f"Checked on every row: residual {P21['product_residual_all_rows']:.1e} ({P21['n_elements']:,} nonzero elements, {P21['n_local_codewords']:,} states).",
            "Physics reading (genie-opus; the reviewer calls it plausible, not needed for correctness): the Wilson loop is a",
            "trace of four link matrices; its colour indices are contracted at the corners, and gauge invariance makes each",
            "corner an SU(2)-invariant map of that corner's own state.",
            "",
            "## The corner pieces (plaq1, from data/p2_1_structure.json; bits written in increasing qubit order)"]
    y = text_block(fig, 0.06, 0.92, rows, fs=8.4)
    y -= 0.01
    for c in P21["corners"]:
        fig.text(0.06, y, f"corner {c['key']} = site {c['site']}  (qubits q{c['qubits'][0]}-q{c['qubits'][-1]}; last bit = n/iota q{c['q']})",
                 fontsize=8.2, weight="bold"); y -= 0.0165
        parts = []
        for b in c["blocks"]:
            st = [s_[::-1] for s_ in b["states"]]
            sv = sorted({round(v, 4) for v in b["singular_values"]}, reverse=True)
            parts.append(" <-> ".join(st) + "  [" + ", ".join(f"{v:.4f}" for v in sv) + "]")
        for j in range(0, len(parts), 3):
            fig.text(0.075, y, "    ".join(parts[j:j + 3]), fontsize=7.0, family="DejaVu Sans Mono"); y -= 0.0155
        y -= 0.006
    fig.text(0.06, y, "[...] = coupling strengths (singular values) of that block; 0 = the dark combination.", fontsize=7.6)
    y -= 0.03
    rows = ["## What follows from it",
            "* Two magnitudes per corner, always in the ratio 1/sqrt2 (0.52424/0.74139 = 0.70711): the angle table is",
            r"   $\theta(x) = \pm\,\theta_0\,A\,\prod_{c}\left(-\frac{1}{\sqrt{2}}\right)^{x_c}$,  with $x_c = 1$ if the two plaquette links at corner c differ.",
            "   A product of four one-bit functions has only 2^4 = 16 Walsh terms -- not 2^11.",
            "* Three corners have a three-state block {one flux, three flux with iota = 0 or 1}: the plaquette reaches only",
            "  the BRIGHT combination of the two iota states (see the valid-states PDF, page 6).  Corner c11 has none.",
            "* So each corner can be 'straightened' separately by a few gates (step 1), after which the whole term is a",
            "  single flip of one qubit times a diagonal angle (steps 2-3)."]
    text_block(fig, 0.06, y, rows, fs=8.4)
    pdf.savefig(fig); plt.close(fig)


def p_corner_frame(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Step 1 - corner frames: make each corner flip ONE qubit", ha="center", fontsize=13, weight="bold")
    rows = ["At a corner the plaquette flips BOTH plaquette-link qubits p_a, p_b (bottom and left at c00 = q7, q8).",
            "(a) One CNOT p_a -> p_b stores x = p_a XOR p_b in p_b.  The plaquette keeps x fixed (it flips both), so after",
            r"    the CNOT it flips only $p_a$:   $\mathrm{CX}_{ab}\,(X_a X_b)\,\mathrm{CX}_{ab} = X_a$.",
            "(b) For the three-state block, one two-level rotation of the iota qubit maps the BRIGHT combination onto one",
            r"    basis state and the dark one onto the other:  R = (1/|v|) [[v1, v2], [-v2, v1]]  (bright -> s1, dark -> s2).",
            "    It acts only on states of that block, so it is a multiplexed Ry on q9 with 3 controls (q6, q7, q8): 8 CNOTs.",
            r"Now the corner piece is $A_c = X_{p_a}\otimes D_c(\ell)$: one bit flip times a diagonal in the corner's labels.",
            "",
            "## The real gates at corner c00 (site 2), first 19 gates of the compressed circuit:"]
    y = text_block(fig, 0.06, 0.92, rows, fs=8.4)
    ax = fig.add_axes([0.03, y - 0.2, 0.94, 0.18])
    g0 = GATES[0:19]
    hl = {id(GATES[0]): "#d62728"}
    draw_circuit(ax, g0, [6, 7, 8, 9], QL, hl=hl, colw=0.9, fs=7.5,
                 title="red: CX(q7 -> q8) = step (a);  then U - [Ry, CX] x 8 - U = the bright rotation on q9 (step b)")
    rows = ["The angles +-pi/12 are the Walsh coefficients of the 60-degree bright rotation (bright weight 1/2 on iota=0,",
            "sqrt3/2 on iota=1); U, U^dag rotate the target axis.  Corners c10 and c01 get the same pattern (q14,q16 | q17 and",
            "q11,q12 | q13).  Corner c11 has no three-state block, so it gets only its CNOT (q18 -> q19).",
            "",
            "## Sign corrections (also part of step 1)",
            "After the frames, some label-dependent signs of the corner pieces remain.  genie-opus fits them over F2 and",
            "absorbs each with the cheapest available gate: a free 2*pi in a bright rotation (sign flip at no cost,",
            "used at c00), a CZ (1 two-qubit gate, used at c01: CZ(q10,q11)), or a doubly-controlled Z built from",
            "3 controlled phases + 2 CNOTs (used at c11).  The c11 correction, as built:"]
    y = text_block(fig, 0.06, y - 0.23, rows, fs=8.4)
    ax = fig.add_axes([0.03, y - 0.15, 0.94, 0.13])
    draw_circuit(ax, GATES[38:46], [18, 19, 20], QL, colw=0.9, fs=7.5,
                 title="corner c11: CX(q18 -> q19), then X - CP - CX - CP - CX - CP - X  =  CCZ on (q18, NOT q19, q20)")
    i = O["cf2"]["info"]
    text_block(fig, 0.06, y - 0.19,
               [f"Chosen corrections (cf2_gates return_info): bright_sign {i['bright_sign']}, cz on (third, p_a) {i['cz_c']}, "
                f"ccz {i['ccz_xc']}.",
                "Lean: CX conjugation of a flip (xorLinear_conj_flip), ccz_phase / ccz_circuit, ry_add_two_pi (free sign)."],
               fs=8.2)
    pdf.savefig(fig); plt.close(fig)


def p_ladder(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Steps 2-3 - one CNOT ladder, then ONE rotation (construction CF1)", ha="center", fontsize=13,
             weight="bold")
    rows = ["After step 1 the plaquette flips one qubit at each corner: p_a = q7, q14, q18, q11 together.  The product",
            "of four X's is turned into a single X by a ladder of three CNOTs from p_1 = q7 (proved in Lean,",
            r"xorLinear_conj_flip):   $L\,(X_{7}X_{14}X_{18}X_{11})\,L^{-1} = X_{7}$,   $L = \mathrm{CX}(7\to14)\,\mathrm{CX}(7\to18)\,\mathrm{CX}(7\to11)$."]
    y = text_block(fig, 0.06, 0.92, rows, fs=8.5)
    ax = fig.add_axes([0.2, y - 0.17, 0.6, 0.15])
    draw_circuit(ax, GATES[66:69], [7, 14, 18, 11], QL, colw=1.0, fs=8, title="the ladder in the real circuit")
    rows = ["Now the whole frame-transformed generator is a flip of q7 times a diagonal angle F(s) of the other bits:",
            r"$F\,h\,F^\dagger = X_{7}\otimes \mathrm{diag}(F)$   so   $e^{-i\theta X_7\,\mathrm{diag}(F)} = H_7\,\mathrm{diag}\left(e^{-i\theta(-1)^{s_7}F(s)}\right)H_7$",
            "(Lean exp_xt_diag): ONE multiplexed rotation on q7 replaces the frozen circuit's 82.  The term is",
            r"$e^{-i\theta h} = F^{-1}\,\cdot\,[\mathrm{one\ multiplexed\ rotation}]\,\cdot\,F$   (Lean exp_conj_frame).",
            "",
            "## CF1 in numbers (rebuilt for this PDF)"]
    y = text_block(fig, 0.06, y - 0.2, rows, fs=8.5)
    i = O["cf1"]["info"]
    mx = i["multiplexer"][0]
    rows = [f"* all {i['n_rotations']} two-state rotations merge into ONE multiplexed rotation on q{i['p1']}",
            f"* it still has {mx['n_controls']} controls -> 2^{mx['n_controls']} = {2 ** mx['n_controls']:,} CNOTs",
            f"* frame (4 corner CNOTs + 3 bright rotations x 8 + 3 ladder) = {i['frame_2q']} two-qubit gates, applied and undone",
            f"* total {2 ** mx['n_controls']:,} + 2 x {i['frame_2q']} = {O['cf1']['n_2q']:,} two-qubit gates  "
            f"(was {O['frozen']['n_2q']:,}),  max error {O['cf1']['max_dev']:.1e}"]
    y = text_block(fig, 0.08, y, rows, fs=8.5)
    ax = fig.add_axes([0.03, y - 0.24, 0.94, 0.22])
    FR = "#deebf7"
    block_diagram(ax, [(1.3, [("c00\nframe", [6, 9], FR), ("c01\nframe", [10, 13], FR), ("c10\nframe", [14, 17], FR),
                              ("c11\nframe", [18, 21], FR)]),
                       (1.0, [("ladder", [7, 18], "#e5f5e0")]),
                       (4.2, [("ONE multiplexed Ry on q7\n11 controls\n2^11 = 2,048 CX", [6, 21], "#fde0dd")]),
                       (1.0, [("ladder\nundone", [7, 18], "#e5f5e0")]),
                       (1.3, [("frames\nundone", [6, 21], FR)])],
                  list(range(6, 22)), QL, title="CF1 schematic (16 qubits of plaq1; time runs left to right)")
    rows = ["Why still 11 controls: the angle depends on x_c (4 bits) AND on whether each corner sits on its dark",
            "state, which is spread over the corner's third-link bit and n/iota bit (2 bits per corner).  Step 4 packs each",
            "corner's 'dark' condition into ONE bit."]
    text_block(fig, 0.06, y - 0.27, rows, fs=8.5)
    pdf.savefig(fig); plt.close(fig)


def p_flags(pdf):
    i = O["cf2"]["info"]
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Step 4 - free qubits and dark-state flags (construction CF2)", ha="center", fontsize=13,
             weight="bold")
    rows = ["## (a) Clean qubits for free",
            "Every plaquette link is stored twice.  After the frames and the ladder, the qubits p_a of corners c10, c11, c01",
            "(and one more) hold fixed parities of the x labels on every valid state, so a few CNOTs reset them to |0>:",
            f"{i['clear_2q']} CNOTs give four clean qubits: {i['ancillas']} (found by F2 linear algebra, plaqfactor.f2_relations)."]
    y = text_block(fig, 0.06, 0.92, rows, fs=8.4)
    ax = fig.add_axes([0.1, y - 0.19, 0.8, 0.17])
    draw_circuit(ax, GATES[69:75], [8, 11, 12, 16, 18, 19], QL, colw=1.0, fs=7.5, title="clearing CNOTs (real circuit)")
    rows = ["## (b) A flag per corner: g_c = (third-link bit) AND (n/iota bit)",
            "A corner is on its dark state exactly when both bits are 1.  A relative-phase Toffoli (Margolus, 3 CNOTs)",
            "writes g_c into a clean qubit; its stray phase cancels when the same gates are undone (Lean relphase_cancel)."]
    y = text_block(fig, 0.06, y - 0.22, rows, fs=8.4)
    ax = fig.add_axes([0.1, y - 0.17, 0.8, 0.15])
    draw_circuit(ax, GATES[75:82], [6, 9, 14], QL, colw=0.85, fs=7.5,
                 title="flag of corner c00 into clean q14:  g = q6 AND q9  (Ry(pi/4) - CX - Ry - CX - Ry - CX - Ry)")
    rows = ["## (c) The angle now depends on 8 bits only",
            r"$F(x,g) = \theta\,M(x)\,\prod_{c}\left(1-\bar x_c\,g_c\right)$:  x_c (4 bits) and g_c (4 flags).  The package's control",
            "reduction removes one more, leaving 7 controls: 2^7 = 128 CNOTs instead of 2,048.",
            "",
            "## CF2 in numbers (rebuilt for this PDF)",
            f"frame per side = 4 corner CNOTs + 3 x 8 bright + 1 CZ + 5 (CCZ) + 3 ladder + {i['clear_2q']} clear + 4 x 3 flags = {i['frame_2q']}",
            f"total = 128 + 2 x {i['frame_2q']} = {O['cf2']['n_2q']}  (CF1 had {O['cf1']['n_2q']:,});  depth {O['cf2']['depth_2q']},  max error {O['cf2']['max_dev']:.1e}",
            "",
            "Two failed attempts on the way (report 003 section 2.3.4): the first CF2 build had 8 controls (356 gates)",
            "because the package's greedy control reduction dropped corner c11's flag and kept its two source bits (fixed by",
            "re-ordering the bits); the second because a 'free' sign flip was assumed at c11, which has no bright rotation",
            "to absorb it (fixed by offering the CCZ as a costed correction)."]
    text_block(fig, 0.06, y - 0.2, rows, fs=8.3)
    pdf.savefig(fig); plt.close(fig)


def p_sparse(pdf):
    i = O["cf2_sw"]["info"]["multiplexer"][0]
    rt = i["reduced_table"]
    m = rt["m"]; N = 1 << m
    th = np.zeros(N); fixed = np.zeros(N, bool)
    th[rt["fixed_idx"]] = rt["fixed_val"]; fixed[rt["fixed_idx"]] = True
    W = np.array([[(-1) ** bin(s & c).count("1") for s in range(N)] for c in range(N)], float)
    a_zero = np.linalg.solve(W, th)                      # free slots set to 0
    nz_zero = int((np.abs(a_zero) > 1e-12).sum())
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Steps 5-6 - fewer terms in the one rotation (sparse Walsh, then MILP)", ha="center",
             fontsize=13, weight="bold")
    rows = ["## A multiplexed rotation is a product of 'Walsh' factors",
            r"$\sum_c |c\rangle\langle c|\otimes R_y(\theta_c) = \prod_{S}\exp\left(-\frac{i}{2}\,a_S\,Z_S\,Y_t\right)$,   $\theta_c = \sum_S a_S\,(-1)^{|S\cap c|}$",
            "Each factor with a_S != 0 costs one Ry plus the CNOTs needed to move from one mask S to the next.  The",
            "Gray-code circuit simply uses ALL 2^m masks.  But some table entries theta_c are 'don't care' (the control",
            "pattern c never occurs on a valid state), and their values can be chosen freely.",
            "",
            f"## The CF2 rotation: m = {m} controls, {N} table entries, {int(fixed.sum())} fixed, {N - int(fixed.sum())} free"]
    y = text_block(fig, 0.06, 0.92, rows, fs=8.4)
    ax = fig.add_axes([0.08, y - 0.17, 0.86, 0.14])
    ax.bar(np.where(fixed)[0], th[fixed], color="#2ca02c", width=0.8, label="fixed angle")
    ax.bar(np.where(~fixed)[0], np.zeros((~fixed).sum()) + 0.004, color="#ff7f0e", width=0.8, label="free (don't care)")
    ax.set_xlim(-1, N); ax.set_xlabel("control pattern c"); ax.set_ylabel(r"$\theta_c$ / rad")
    ax.legend(fontsize=7); ax.set_title("angle table of the single rotation (from cf2 with sparse multiplexor)", fontsize=8.5)
    rows = [f"With the free entries set to 0 the Walsh transform has {nz_zero} nonzero terms.  sparsemux.sparse_walsh chooses",
            f"the free entries by a linear programme (minimise sum |a_S|), prunes, and re-solves exactly: {i['support_used']} terms used,",
            f"walked in an order that needs {i['walk_cnots']} CNOTs (Gray code: {N}).  Total {O['cf2_sw']['n_2q']} two-qubit gates "
            f"(= 2 x 55 frame + {i['walk_cnots']}), max error {O['cf2_sw']['max_dev']:.1e}."]
    y = text_block(fig, 0.06, y - 0.235, rows, fs=8.4)
    ax2 = fig.add_axes([0.3, y - 0.2, 0.62, 0.16])
    labs = ["Gray code (all masks)", "Walsh, free = 0", "sparse (LP), step 5", "MILP, step 6", "MILP lower bound"]
    vals = [N, nz_zero, i["support_used"], CERT["support_used"], CERT["support_lb"]]
    cols = ["#7f7f7f", "#bdbdbd", "#ff7f0e", "#d62728", "#fdd0a2"]
    ax2.barh(range(5), vals, color=cols)
    for k, v in enumerate(vals):
        ax2.text(v + 1, k, f"{v}", va="center", fontsize=8)
    ax2.set_yticks(range(5)); ax2.set_yticklabels(labs, fontsize=8); ax2.invert_yaxis(); ax2.set_xlim(0, N + 18)
    ax2.set_xlabel("number of Walsh masks (one Ry each) in the single rotation")
    rows = ["## Step 6: exact minimum by MILP (data/cert_it6_operator_plaq1_long.json)",
            "Choosing the free entries to minimise the NUMBER of nonzero a_S is a mixed-integer linear programme",
            "(certify.min_walsh_support, solver HiGHS, one binary per mask).  For this rotation:",
            f"   masks used {CERT['support_used']},  walk CNOTs {CERT['walk_cnots']},  proven lower bound {CERT['support_lb']} masks after "
            f"{CERT['milp_wall_s']:.0f} s ({CERT['status']}).",
            f"   Total {O['cf2_lin_milp']['n_2q']} = 2 x 55 frame + {CERT['walk_cnots']};  depth {O['cf2_lin_milp']['depth_2q']};  "
            f"max error {O['cf2_lin_milp']['max_dev']:.1e}.",
            "So at most 7 more masks could be saved inside this construction; the gap is not closed.",
            "The same build also makes every structural choice from angle-free tables (linsynth), so the gate pattern",
            "is identical for every Krylov step k; only the angles scale with theta = k dt.",
            "Lean: cx_conj_yt (a CNOT maps Y_t to Z_c Y_t), exp_sum_commuting / walk_factors_comm (the factors commute),",
            "exp_agree_mulVec (don't-care entries do not change the action on valid states)."]
    text_block(fig, 0.06, y - 0.26, rows, fs=8.3)
    pdf.savefig(fig); plt.close(fig)


def p_summary(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.5, 0.955, "Summary: the whole plaq1 term after compression", ha="center", fontsize=13, weight="bold")
    ax = fig.add_axes([0.03, 0.62, 0.94, 0.3])
    FR = "#deebf7"
    block_diagram(ax, [(1.4, [("c00 frame", [6, 9], FR), ("c01 frame\n+CZ", [10, 13], FR),
                              ("c10 frame", [14, 17], FR), ("c11 frame\n+CCZ", [18, 21], FR)]),
                       (0.8, [("ladder", [7, 18], "#e5f5e0")]),
                       (0.8, [("clear", [8, 19], "#fff7bc")]),
                       (1.0, [("4 flags", [6, 21], "#fdd0a2")]),
                       (3.4, [(f"ONE multiplexed Ry\non q7, 7 controls\n(q8 q11 q12 q14\n q16 q18 q19)\n{CERT['walk_cnots']} CX (MILP)",
                               [7, 19], "#fde0dd")]),
                       (1.4, [("everything\nundone", [6, 21], "#f0f0f0")])],
                  list(range(6, 22)), QL,
                  title="plaq1 (class A, v2):  frame 55  +  one rotation 92  +  frame undone 55  =  202 two-qubit gates")
    rows = ["## The steps and what each one exploited",
            "  step                          gates   exploited structure",
            f"  0   frozen package synthesis {O['frozen']['n_2q']:>7,}    none (82 multiplexed rotations, 7-11 controls)",
            f"  1-3 corner frames + ladder   {O['cf1']['n_2q']:>7,}    product over corners; bright/dark; one flip for all four corners",
            f"  4   clean qubits + flags     {O['cf2']['n_2q']:>7,}    duplicated link bits are free scratch; dark condition = 1 bit",
            f"  5   sparse Walsh             {O['cf2_sw']['n_2q']:>7,}    don't-care table entries (LP)",
            f"  6   MILP minimum             {O['cf2_lin_milp']['n_2q']:>7,}    exact minimum mask count (lower bound {CERT['support_lb']})",
            "",
            "## Accuracy at every step",
            "Each rebuilt term was compared with the exact exp(-i theta O_plaq1) on all 1,831 valid states (columns); the",
            "largest deviations are on page 1 (all below 4.1e-13, bar 1e-10).  The full 28-qubit circuits containing the",
            "final term were verified separately (75/75; reviewer-opus's independent Aer check for v1, report 004 for v2).",
            "",
            "## Proved vs checked",
            "Proved in Lean (general identities): CX conjugation of flips and of Y (xorLinear_conj_flip, cx_conj_yt),",
            "frame conjugation of an exponential (exp_conj_frame), the flip-times-diagonal exponential (exp_xt_diag), the",
            "relative-phase Toffoli cancellation (relphase_cancel), the CCZ construction (ccz_circuit), commuting Walsh",
            "factors (exp_sum_commuting), don't-care entries (exp_agree_mulVec).  Checked numerically, not proved: the",
            "factorisation of this particular term, the fitted signs, every specific table and gate list.",
            "",
            "## Class B (exact only on each circuit's own starting state)",
            "On top of these steps, class B restricts the term to the blocks reachable from the starting state",
            "(reach.py); plaq1 then costs 152-208 two-qubit gates depending on the reference (report 003, it5).",
            "",
            "Sources: 2x4_compression_using_ai_v1/reports/003 (sections 2.3-2.4), report 004, MANUAL steps (c)-(f);",
            "code src/c2x4/plaqfactor.py, sparsemux.py, linsynth.py, certify.py."]
    y = text_block(fig, 0.06, 0.58, rows[:1], fs=8.2, dy=0.0192)
    y = text_block(fig, 0.06, y, rows[1:8], fs=7.6, dy=0.0192, mono=True)
    text_block(fig, 0.06, y, rows[8:], fs=8.2, dy=0.0192)
    pdf.savefig(fig); plt.close(fig)


def main():
    out = f"{ROOT}/reports/plaq1_compression_steps_2x4.pdf"
    with FitPdf(out) as pdf:
        p_title(pdf); p_frozen(pdf); p_factor(pdf); p_corner_frame(pdf); p_ladder(pdf); p_flags(pdf)
        p_sparse(pdf); p_summary(pdf)
        pdf.infodict()["Title"] = "Compressing the 2x4 plaq1 circuit, step by step"
    print(out)


if __name__ == "__main__":
    main()

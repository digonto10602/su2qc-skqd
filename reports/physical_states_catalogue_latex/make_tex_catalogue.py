"""LaTeX/TikZ version of the physical-states catalogue (same data as make_catalogue.py)."""
import os, sys, json, subprocess, datetime, textwrap
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/digimonk/.claude/jobs/9a585e99/tmp/cat")
import make_catalogue as mc                      # noqa: E402  (data + conventions, nothing runs on import)
from skqd.vertex import kernel_dim                # noqa: E402
from skqd.codec import Reject                     # noqa: E402

ROOT = mc.ROOT
OUT_TEX = os.path.join(HERE, "physical_states_catalogue.tex")
UNIT = {2: 1.55, 3: 1.75, 4: 2.05}               # cm per lattice spacing
NCOL = {2: 4, 3: 3, 4: 2}
LEVCOL = ["orange!8", "cyan!7", "green!7", "magenta!6"]


def tex_escape(s):
    return s.replace("#", r"\#").replace("_", r"\_").replace("%", r"\%")


def site_label(lat, s, n):
    exc = n - lat.n_vac(s)
    return {0: "", 1: "$q$", 2: "$2q$", -1: r"$\bar q$", -2: r"$2\bar q$"}[exc]


def lattice_tikz(lat, label, bad_sites=(), unit=1.6, jlabels=True):
    j2, n, iota = label
    o = [rf"\begin{{tikzpicture}}[x={unit}cm,y={unit}cm,baseline=(current bounding box.center)]"]
    for l, (a, b, d) in enumerate(lat.links):
        (xa, ya), (xb, yb) = lat.coords(a), lat.coords(b)
        if j2[l]:
            o.append(rf"\draw[fluxon] ({xa},{ya}) -- ({xb},{yb}) node[midway,jlab,text=fluxred] {{$\tfrac12$}};"
                     if jlabels else rf"\draw[fluxon] ({xa},{ya}) -- ({xb},{yb});")
        else:
            o.append(rf"\draw[fluxoff] ({xa},{ya}) -- ({xb},{yb}) node[midway,jlab,text=gray] {{$0$}};"
                     if jlabels else rf"\draw[fluxoff] ({xa},{ya}) -- ({xb},{yb});")
    ends = lat.ends()
    for s in range(lat.n_sites):
        x, y = lat.coords(s)
        odd = lat.parity(s) == 1
        bad = s in bad_sites
        sty = ("oddsite" if odd else "evensite") + (",draw=red" if bad else "")
        ns = n[s]
        if ns == 0:
            o.append(rf"\node[site,{sty},fill=white] at ({x},{y}) {{\textbf{{0}}}};")
        elif ns == 2:
            o.append(rf"\node[site,{sty},fill=occ2] at ({x},{y}) {{\textcolor{{white}}{{\textbf{{2}}}}}};")
        else:
            o.append(rf"\fill[white] ({x},{y}) circle[radius=0.15cm];")
            o.append(rf"\fill[occ1] ({x},{y}) ++(90:0.15cm) arc[start angle=90,end angle=270,radius=0.15cm] -- cycle;")
            o.append(rf"\node[site,{sty},fill=none] at ({x},{y}) {{\textbf{{1}}}};")
        dy = -1 if y == 0 else 1
        sl = site_label(lat, s, ns)
        if sl:
            o.append(rf"\node[part] at ({x}+0.17,{y}+{dy}*0.21) {{{sl}}};")
        nflux = sum(j2[l] for l, _ in ends[s])
        if len(ends[s]) == 3 and nflux == 3 and ns == 1:
            o.append(rf"\node[iot] at ({x}-0.17,{y}+{dy}*0.21) {{$\iota{{=}}{iota[s]}$}};")
        if bad:
            o.append(rf"\node[text=red,font=\large] at ({x},{y}+{dy}*0.34) {{\ding{{55}}}};")
    o.append(rf"\useasboundingbox ({-0.35},{-0.42}) rectangle ({lat.Lx - 1 + 0.35},{1.42});")
    o.append(r"\end{tikzpicture}")
    return "\n".join(o)


def bits_str(D, g):
    return mc.bitgroups(D, D["cw"][g])


def card(D, g, extra=None, bg="white"):
    lat = D["lat"]; Lx = D["Lx"]
    lab = D["M"].basis.labels[g]
    tb = int(D["M"].basis.twoB[g])
    si = int(np.searchsorted(D["sectors"][tb]["idx"], g))
    w = {2: 0.235, 3: 0.315, 4: 0.48}[Lx]
    lines = [rf"\textbf{{\#{g}}} ($B{{=}}{tb // 2}$, \#{si} in sector)\ \ $E_{{\rm diag}}={D['diag'][g]:+.3f}$"]
    if extra:
        lines.append(extra)
    lines.append(r"\texttt{" + bits_str(D, g) + "}")
    lines.append(r"$n=(" + r"\,".join(str(v) for v in lab[1]) + r")$\ \ $j=(" +
                 r"\,".join(r"\frac12" if v else "0" for v in lab[0]) + ")$")
    pic = lattice_tikz(lat, lab, unit=UNIT[Lx])
    return (rf"\fcolorbox{{gray!45}}{{{bg}}}{{\begin{{minipage}}[t][\cardh{Lx}][t]{{{w}\textwidth}}\centering" "\n"
            + pic + "\n" + r"\par\vspace{1pt}\raggedright\tiny " + r"\\ ".join(lines) + r"\end{minipage}}")


def cards(D, glist, extras=None, bgs=None):
    n = NCOL[D["Lx"]]
    out = []
    for i, g in enumerate(glist):
        out.append(card(D, g, extras[i] if extras else None, bgs[i] if bgs else "white"))
        out.append(r"\hfill" if (i + 1) % n else r"\par\vspace{3pt}\noindent")
    if len(glist) % n:
        out.append(r"\par\vspace{3pt}\noindent")
    return r"\noindent" + "\n".join(out)


def preamble():
    return r"""\documentclass[10pt]{article}
\usepackage[a4paper,margin=1.3cm,top=1.5cm,bottom=1.5cm]{geometry}
\usepackage{amsmath,amssymb,booktabs,longtable,array,xcolor,pifont,enumitem}
\usepackage{tikz}
\usepackage[hidelinks,bookmarksnumbered]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\fboxsep}{2pt}
\definecolor{fluxred}{HTML}{D62728}
\definecolor{occ1}{HTML}{9ECAE1}
\definecolor{occ2}{HTML}{08519C}
\definecolor{partc}{HTML}{B15928}
\definecolor{iotac}{HTML}{6A3D9A}
\newcommand{\rs}{0.15}
\tikzset{
  fluxon/.style={line width=2.2pt,draw=fluxred,line cap=round},
  fluxoff/.style={line width=0.5pt,draw=gray!70,dash pattern=on 1.5pt off 1.5pt},
  jlab/.style={fill=white,inner sep=0.4pt,font=\tiny},
  site/.style={circle,minimum size=0.3cm,inner sep=0pt,font=\scriptsize},
  evensite/.style={draw=black,line width=0.5pt},
  oddsite/.style={draw=black,line width=1.3pt},
  part/.style={text=partc,font=\scriptsize\bfseries,inner sep=0.5pt},
  iot/.style={text=iotac,font=\tiny\bfseries,inner sep=0.5pt},
}
\newlength{\cardhii}\setlength{\cardhii}{4.25cm}
\newlength{\cardhiii}\setlength{\cardhiii}{4.25cm}
\newlength{\cardhiv}\setlength{\cardhiv}{4.85cm}
\newcommand{\cardh}[1]{\ifcase#1\or\or\cardhii\or\cardhiii\or\cardhiv\fi}
\begin{document}
"""


def intro(DATA):
    o = []
    o.append(r"""\begin{center}{\LARGE\bfseries Catalogue of the physical states}\\[4pt]
{\large SU(2) lattice gauge theory with staggered quarks on $2\times2$, $2\times3$ and $2\times4$ ladders}\\[2pt]
{\small generated """ + datetime.date.today().isoformat() + r""" from repository commit \texttt{""" + mc.COMMIT + r"""}}\end{center}
\tableofcontents
\section{What is in this catalogue}
\begin{itemize}[leftmargin=*,itemsep=1pt]
\item How to read the pictures and labels (section~\ref{sec:legend}).
\item Why a configuration can be unphysical, with checked examples (section~\ref{sec:invalid}).
\item The lowest energy levels of every baryon sector of every lattice (section~\ref{sec:spectra}).
\item For each lattice and sector $B$: the ground state and excited states 1--3, each drawn as its dominant
configurations with amplitude and weight (sections~\ref{sec:eig2}--\ref{sec:eig4}).
\item Every physical state of $2\times2$ (82) and $2\times3$ (1\,727), one picture each, sector by sector
(sections~\ref{sec:all2}--\ref{sec:all3}).  The $2\times4$ ladder has 37\,165 physical states (about 2\,000 pages if
drawn); all of them are listed in the companion file\\
\texttt{reports/physical\_states\_catalogue\_all\_states.csv}.
\end{itemize}
\subsection*{Number of physical (gauge-invariant) states per baryon sector}
\begin{center}\begin{tabular}{l r l}\toprule lattice & total & per sector $B$\\\midrule""")
    for D in DATA:
        per = ", ".join(rf"${tb // 2:+d}$:\,{s['dim']}" for tb, s in D["sectors"].items())
        tot = f"{D['M'].basis.dim:,}".replace(",", "{,}")
        o.append(rf"$2\times{D['Lx']}$ & {tot} & {per}\\")
    o.append(r"""\bottomrule\end{tabular}\end{center}
\subsection*{Model and parameters}
Hamiltonian (\texttt{src/skqd/hamiltonian.py}), links truncated at $j_{\max}=\tfrac12$:
\[ H=\sum_{l}H^{\rm hop}_l+m\sum_x(-1)^{x_1+x_2}n_x+\frac{g^2}{2}\sum_l j_l(j_l+1)-\frac{1}{2g^2}\sum_P\big(W_P+W_P^\dagger\big),\qquad
g^2=4,\ \ m=\tfrac{3}{16}g^2=0.75 . \]
Energies and eigenvectors are exact diagonalisations of each sector (\texttt{numpy eigh}, or \texttt{scipy eigsh} for
the two largest $2\times4$ sectors) of the package's own Hamiltonian (\texttt{skqd.exact.Model}); the ground-state
energies equal the stored references \texttt{validation/E3.json} (section~\ref{sec:spectra}).  Bit strings come from
\texttt{skqd.codec.Codec}.
""")
    return "\n".join(o)


def legend(DATA):
    lat = DATA[2]["lat"]
    o = [r"\clearpage\section{How to read the pictures}\label{sec:legend}", r"\begin{center}",
         r"\begin{tikzpicture}[x=3.4cm,y=2.6cm]"]
    for l, (a, b, d) in enumerate(lat.links):
        (xa, ya), (xb, yb) = lat.coords(a), lat.coords(b)
        pos = "above" if d == "x" else "right"
        o.append(rf"\draw[-latex,gray!70!black,shorten >=8pt,shorten <=8pt] ({xa},{ya}) -- ({xb},{yb}) "
                 rf"node[midway,{pos},font=\scriptsize,text=partc] {{link {l}}};")
    for s in range(lat.n_sites):
        x, y = lat.coords(s)
        odd = lat.parity(s) == 1
        o.append(rf"\node[site,{'oddsite' if odd else 'evensite'},fill=white,minimum size=0.5cm] at ({x},{y}) {{\textbf{{{s}}}}};")
        where = "below" if y == 0 else "above"
        o.append(rf"\node[{where}=7pt,font=\scriptsize,align=center] at ({x},{y}) {{site {s}, $({x},{y})$\\"
                 rf"{'odd' if odd else 'even'}, vacuum $n={lat.n_vac(s)}$}};")
    o.append(r"\end{tikzpicture}\\[2pt]{\small The $2\times4$ ladder; $2\times2$ and $2\times3$ are its first two or three columns.}\end{center}")
    o.append(r"""
\paragraph{Sites and quarks (staggered fermions).}  Each site holds a quark field with two colours, so its occupation is
$n=0,1,2$: the number in the circle (white $=0$, half-filled $=1$, dark $=2$).  In the staggered (Dirac-sea) vacuum
$n=0$ on \emph{even} sites ($x_1+x_2$ even, thin circle) and $n=2$ on \emph{odd} sites (thick circle).  Particles are
deviations from that vacuum, written next to the site in brown:
\begin{center}\begin{tabular}{lccc}\toprule & $n=0$ & $n=1$ & $n=2$\\\midrule
even site & vacuum & $q$ (one quark) & $2q$ (two quarks)\\
odd site & $2\bar q$ (two holes) & $\bar q$ (one hole = antiquark) & vacuum\\\bottomrule\end{tabular}\end{center}
The mass term $m\sum_x(-1)^{x_1+x_2}n_x$ makes every quark or antiquark cost energy $m$ relative to the vacuum.

\paragraph{Links (colour-electric flux).}  Each link carries $j=0$ (grey dashed, ``$0$'': no flux) or $j=\tfrac12$ (red,
``$\tfrac12$'': one unit of flux), with electric energy $\frac{g^2}{2}j(j+1)=\frac38 g^2$ per flux link.

\paragraph{Gauss's law and the intertwiner $\iota$.}  At every site the colour spins arriving there (each flux link
brings $\tfrac12$; $n=1$ brings $\tfrac12$; $n=0,2$ bring $0$) must add up to total spin $0$, so their number must be
even.  At an interior site with flux on all three links and $n=1$ there are two ways to do this, labelled $\iota=0,1$
(purple, shown only there).

\paragraph{Baryon number $B$.}  $B=\tfrac12\sum_x\big(n_x-n^{\rm vac}_x\big)$.  In SU(2) a baryon is two quarks, so $B=1$
means two extra quarks, while quark--antiquark pairs (mesons) have $B=0$.  The Hamiltonian conserves $B$, so each $B$
is a separate sector; the SKQD work of this project uses $B=0$ ($2B=0$) and $B=1$ ($2B=2$).

\paragraph{The text under each picture.}
\begin{itemize}[leftmargin=*,itemsep=0pt]
\item \#$k$: position in the package's basis list (\texttt{skqd.basis}); ``\#$i$ in sector'': position inside its sector.
\item $E_{\rm diag}$: diagonal energy of that configuration alone (mass $+$ electric terms) -- not an eigenvalue.
\item bits: the qubit encoding (\texttt{skqd.codec}), one group per site $0,1,2,\dots$; in each group the flux bits of the
site's links in link-number order, then the matter bit ($n/2$, or $\iota$ at a three-flux $n=1$ site).
\item $n=(\dots)$ per site, $j=(\dots)$ per link in link-number order.
\item In the eigenstate sections: $c$ = amplitude of the configuration in the eigenstate (global phase fixed so the
largest amplitude is real and positive) and $|c|^2$ its weight.
\end{itemize}
""")
    return "\n".join(o)


def invalid(DATA):
    D2 = DATA[0]; lat = D2["lat"]; B = D2["M"].basis; C = D2["C"]; ends = lat.ends(); nl = lat.n_links

    def bad_sites(lab):
        j2, n, _ = lab
        return [s for s in range(lat.n_sites)
                if kernel_dim(tuple((j2[l] / 2, role) for l, role in ends[s]), n[s]) == 0]
    ex = []
    j = [0] * nl; j[0] = 1
    ex.append(("Open flux string", (tuple(j), (0, 2, 2, 0), (0,) * 4),
               r"One flux link with nothing at its ends: each end site has a single spin-$\tfrac12$ and no partner. Flux must close into a loop or end on charges."))
    ex.append(("Lone quark", (tuple([0] * nl), (1, 2, 2, 0), (0,) * 4),
               r"One quark ($n=1$) on site 0 with no flux: an isolated colour charge whose spin-$\tfrac12$ has nothing to pair with."))
    ex.append(("Flux loop with a stray quark", (tuple([1] * nl), (1, 2, 2, 0), (0,) * 4),
               r"The closed loop alone is fine, but site 0 also has a quark: two flux links $+$ one quark $=$ three spin-$\tfrac12$ objects, so no spin 0."))
    j = [0] * nl; j[0] = 1
    ex.append(("String with only one end on a quark", (tuple(j), (1, 2, 2, 0), (0,) * 4),
               r"Site 0 is fine (flux $+$ quark pair up), but site 2 at the other end has nothing to pair with. A valid meson would also have $n=1$ at site 2."))
    o = [r"\clearpage\section{Unphysical configurations: examples}\label{sec:invalid}",
         r"A configuration is physical only if Gauss's law holds at \emph{every} site.  Each example below was checked "
         r"against the package: it is not in the basis, and \texttt{skqd.vertex.kernel\_dim} $=0$ (no singlet) at the "
         r"sites marked \textcolor{red}{\ding{55}}.\par\medskip", r"\noindent"]
    for i, (name, lab, why) in enumerate(ex):
        bad = bad_sites(lab)
        assert lab not in B.index and bad, name
        o.append(r"\begin{minipage}[t]{0.48\textwidth}\centering\textbf{(" + chr(97 + i) + ") " + name + r"}\\[2pt]"
                 + lattice_tikz(lat, lab, bad_sites=bad, unit=2.3) + r"\\[2pt]\raggedright\small " + why + r"\end{minipage}"
                 + (r"\hfill" if i % 2 == 0 else r"\par\bigskip\noindent"))

    def reason(bits):
        try:
            C.decode(tuple(bits)); return "accepted"
        except Reject as r:
            return str(r)
    g0 = int(B.sector(0)[0]); good = list(C.encode(B.labels[g0]))
    bad1 = list(good); bad1[C.offsets[0]] ^= 1
    flag = None
    for lab in B.labels:
        if sum(lab[0][l] for l, _ in ends[0]) == 1:
            flag = list(C.encode(lab)); flag[C.offsets[0] + 2] = 1; break
    grp = lambda b: " ".join("".join(map(str, b[o:o + w])) for o, w in zip(C.offsets, C.widths))
    o.append(r"""\subsection*{Bit strings that are not states}
The qubit encoding can also produce strings that describe no state; the decoder (\texttt{skqd.codec.Codec.decode}) rejects them:
\begin{center}\begin{tabular}{l l l}\toprule & bits (sites 0,1,2,3) & decoder\\\midrule""")
    o.append(rf"physical state \#{g0} & \texttt{{{grp(good)}}} & \texttt{{{reason(good)}}}\\")
    o.append(rf"one copy of link 0 changed & \texttt{{{grp(bad1)}}} & \texttt{{{reason(bad1)}}}\\")
    o.append(rf"corner with one flux, matter bit 1 & \texttt{{{grp(flag)}}} & \texttt{{{reason(flag)}}}\\")
    o.append(r"""\bottomrule\end{tabular}\end{center}
\begin{itemize}[leftmargin=*,itemsep=0pt]
\item \texttt{link}: every link is stored at both of its end sites; a physical state has equal copies.
\item \texttt{flag}: a matter-bit value the site's flux pattern does not allow ($n$ is already forced).
\item \texttt{sector}: a perfectly physical state, rejected only because its $B$ is not the one being studied -- it belongs to another sector of this catalogue.
\end{itemize}
Configurations like (a)--(d) cannot even be written in this encoding: it stores only Gauss-law-respecting site states
(6 per corner site, 13 per interior site), which is why bit-level errors appear as \texttt{link} or \texttt{flag}
rejections instead.""")
    return "\n".join(o)


def spectra(DATA):
    o = [r"\clearpage\section{Energy levels of every sector}\label{sec:spectra}",
         r"$E_0$ is the ground state, $E_1,E_2,E_3$ the first three excited states ($g^2=4$, $m=0.75$).  "
         r"An asterisk marks a degenerate level; inside a degenerate level the individual eigenvectors are not unique.  "
         r"Last column: largest difference from the stored references \texttt{validation/E3.json}.\par\medskip"]
    for D in DATA:
        o.append(rf"\subsection*{{$2\times{D['Lx']}$}}\begin{{center}}\begin{{tabular}}{{r r r r r r l}}\toprule"
                 r"$B$ & dim & $E_0$ & $E_1$ & $E_2$ & $E_3$ & check vs E3.json\\\midrule")
        for tb, s in D["sectors"].items():
            Es = [lv["E"] for lv in s["levels"]]
            cells = [f"${e:+.5f}$" + ("$^*$" if s["levels"][k]["deg"] else "") for k, e in enumerate(Es)]
            cells += [""] * (4 - len(cells))
            key = f"2x{D['Lx']}|g2={mc.G2}|2B={tb}"
            chk = ""
            if key in mc.E3REF:
                ref = mc.E3REF[key]["energies"][:len(Es)]
                chk = f"${max(abs(a - b) for a, b in zip(ref, Es)):.1e}$"
            o.append(rf"${tb // 2:+d}$ & {s['dim']} & " + " & ".join(cells) + rf" & {chk}\\")
        o.append(r"\bottomrule\end{tabular}\end{center}")
    return "\n".join(o)


def eigen_sections(DATA):
    o = []
    for D in DATA:
        Lx = D["Lx"]
        o.append(rf"\clearpage\section{{Eigenstates of the $2\times{Lx}$ ladder}}\label{{sec:eig{Lx}}}")
        for tb, s in D["sectors"].items():
            o.append(rf"\subsection{{$2\times{Lx}$, sector $B={tb // 2:+d}$ ({s['dim']:,} physical states)}}".replace(",", "{,}"))
            rows, glist, extras, bgs = [], [], [], []
            for k, lv in enumerate(s["levels"]):
                name = "ground state" if k == 0 else f"excited state {k}"
                deg = (r", degenerate with $E_{" + ",".join(map(str, lv["deg"])) + "}$") if lv["deg"] else ""
                rows.append(rf"\colorbox{{{LEVCOL[k % 4]}}}{{$E_{k}={lv['E']:+.6f}$}} & {name}{deg} & {len(lv['cfg'])} "
                            rf"& {lv['cum'] * 100:.1f}\% & {lv['pr']:.1f}\\")
                for (g, c, p) in lv["cfg"]:
                    glist.append(g)
                    if abs(c.imag) < 1e-10:
                        cs = f"{c.real:+.4f}"
                    elif abs(c.real) < 1e-10:
                        cs = f"{c.imag:+.4f}i"
                    else:
                        cs = f"{c.real:+.3f}{c.imag:+.3f}i"
                    extras.append(rf"$E_{k}$ ({name}): $c={cs}$, $|c|^2={p:.4f}$")
                    bgs.append(LEVCOL[k % 4])
            o.append(r"\begin{center}\small\begin{tabular}{l l r r r}\toprule level & & configs drawn & weight covered & "
                     r"participation ratio\\\midrule" + "\n".join(rows) + r"\bottomrule\end{tabular}\end{center}")
            o.append(rf"\small Most important configurations of each level (largest weight first, up to {mc.MAXCFG} or "
                     rf"until {mc.CUMW * 100:.0f}\% of the weight is covered); cards of one level share a colour.  "
                     r"Participation ratio $=1/\sum|c|^4$ $\approx$ number of configurations the state is spread over.\par\smallskip")
            o.append(cards(D, glist, extras, bgs).replace("%", r"\%"))
            o.append(r"\clearpage")
    return "\n".join(o)


def basis_sections(DATA):
    o = []
    for D in DATA[:2]:
        Lx = D["Lx"]
        o.append(rf"\clearpage\section{{All physical states of the $2\times{Lx}$ ladder}}\label{{sec:all{Lx}}}")
        o.append(r"Sorted by sector, then by diagonal energy $E_{\rm diag}$ (lowest first).")
        for tb, s in D["sectors"].items():
            idx = sorted(s["idx"], key=lambda g: (D["diag"][g], g))
            o.append(rf"\subsection{{$2\times{Lx}$, sector $B={tb // 2:+d}$: all {s['dim']} states}}")
            o.append(cards(D, [int(g) for g in idx]))
            o.append(r"\clearpage")
    return "\n".join(o)


def main():
    DATA = [mc.lattice_data(L) for L in (2, 3, 4)]
    tex = preamble() + intro(DATA) + legend(DATA) + invalid(DATA) + spectra(DATA) + eigen_sections(DATA) \
        + basis_sections(DATA) + "\n\\end{document}\n"
    open(OUT_TEX, "w").write(tex)
    print(OUT_TEX, len(tex))


if __name__ == "__main__":
    main()

# su2qc-skqd: full package report (2026-10-05)

## 0. How to read this file

**What this file is.** One self-contained description of the whole `su2qc-skqd` package (a research code base owned by Digonto, repository `https://github.com/digonto10602/su2qc-skqd`, local path `/home/digimonk/Projects/su2qc-skqd-v0.1.0`), written on 2026-10-05 from the repository's own files, so that it can be uploaded on its own to another assistant that has no access to the repository. It carries the numbers, the history, the open decisions and machine-readable data blocks (Section 11) that can be plotted directly.

**Repository facts (from `git log`).** `git log --oneline | wc -l` gave 173 commits on branch `master`; the first commit is dated 2026-09-14 (`5e3fe61`) and the newest committed one at the time of writing is dated 2026-10-05 (`c29a402`). The 173 commits span the 22 calendar days 2026-09-14 to 2026-10-05 inclusive (sum of sourced dates).

**Rules this file follows (the owner's reporting rules).**

1. *Plain English.* Every technical word is defined the first time it appears, and Section 12 is a glossary of all of them.
2. *Project labels.* Names such as "B_all", "B_sig", "rule D3'", "rule D3'-R", "gate H0_2x2", "C22", "f_hit", "f_ideal", "r_nc", "stage E / stage P" are **the project's own labels** (invented inside this project, mostly by its planner agent), not standard physics or computer-science terms. Each is explained where first used.
3. *Math* is written in LaTeX: $\ldots$ inline, $$\ldots$$ displayed.
4. *Numbers.* Every number carries its units where it has any, its uncertainty or interval where one exists, and the source file (and JSON key where useful) in which it was found. The notation `validation/H0_2x2.json -> data.clean_fraction.pooled.f` means "open that file, go to `data`, then `clean_fraction`, then `pooled`, then key `f`". "95 %" intervals are the intervals the source file states; I did not recompute any.
5. *Never invented.* If a number is not in a repository file I say so. Where the only source is the project planner's own arithmetic I label it **(planner arithmetic)**; where an input is a guess I label it **ESTIMATE**. Where I did a trivial sum or ratio myself from sourced numbers I label it **(sum of sourced numbers)**.
6. *"PASS" does not mean "the result is good".* The project has two kinds of gates (Section 4.3): *validation gates* (PASS = the code reproduces a known answer) and *measurement gates* (PASS = "preregistered, measured, verified, consistent", never "the number is good"). Each row in Section 5 says which.

**Units used.** Energies are in the lattice units of the Hamiltonian ($a_0 = 1$, dimensionless numbers; the project quotes them as bare numbers such as $-3.6408$). Times on the quantum device are in microseconds ($\mu$s) or nanoseconds (ns); QPU time is in seconds (s) as billed by the IBM service; Quantinuum cost is in HQC (hardware quantum credits, defined in the glossary).

**Date and status caveat.** "Today" is 2026-10-05. Two other agents were working in the repository while this file was written: one runs the **K1 pilot** (a 2x3 clean-fraction pilot on the IBM device `ibm_kingston`), the other works on `prompts/29` Part B' and `prompts/30` (a re-sizing and convergence check of the 2x3 plan). Their files are uncommitted and may change after this file was written; where I cite them I say so.

**File map for the reader.** Section 1 summary; 2 physics and method from scratch; 3 the intended plan; 4 package layout; 5 gate table; 6 history; 7 QPU ledger; 8 lessons; 9 present state and open decisions; 10 progress measure; 11 data blocks; 12 glossary.

## 1. Executive summary

*(section still to be written)*

## 2. The physics and the method, explained from scratch

Source of this whole section unless a file is named: `proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md` ("the manual", SU2QC Project 2 rev. 2, 10 Sept 2026), `README.md`, `CLAUDE.md`, `data/references.json`, and the gate JSONs named in the text.

### 2.1 What problem is being solved

**Lattice gauge theory.** The strong force binds quarks into protons, neutrons and similar particles. Its mathematical core is a *gauge theory* with the symmetry group SU(2) in the simplified two-colour version used here (the real strong force uses SU(3)). To calculate on a computer, space is replaced by a grid (a *lattice*); quark fields live on the grid points (*sites*), and the force-carrying (gauge) field lives on the segments joining neighbouring sites (*links*). The model here is the *Kogut-Susskind Hamiltonian* with *staggered quarks* (a standard way of putting quarks on a lattice in which one quark component sits on each site and the parity of the site, $(-1)^{x_1+x_2}$, tells whether it behaves as a particle or an antiparticle slot). The **Hamiltonian** $H$ is the operator whose lowest eigenvalue $E_0$ (the *ground-state energy*, "vacuum energy") and next levels are the physics output; an *eigenvalue* of a matrix $H$ is a number $E$ with $H\psi = E\psi$ for some vector $\psi$ (the *eigenvector*, i.e. the quantum state).

**The ladder lattices.** The package works on open "$2\times L_x$ ladders": two rows and $L_x$ columns. $L_x = 2, 3, 4$ gives the **2x2**, **2x3** and **2x4** lattices (the project's own short names).

**Hamiltonian** (manual eq. (1); `README.md`):

$$
H = -\frac12\sum_{\ell=(x\to y)}\Big[\eta_\ell\,\psi^\dagger_{x,i}U_{ij}(\ell)\,\psi_{y,j}+\text{h.c.}\Big]
\;+\; m\sum_x(-1)^{x_1+x_2}\,n_x
\;+\; \frac{g^2}{2}\sum_\ell j_\ell(j_\ell+1)
\;-\; \frac{1}{2g^2}\sum_P\big(W_P+W_P^\dagger\big).
$$

Symbols: $g^2$ gauge coupling (the reference value is $g^2=4$; $g^2=2$ and $1$ are also tabulated), $m=3g^2/16$ the quark mass (so $m=0.75$ at $g^2=4$), $\eta_\ell$ the staggered phases ($i$ on links in the $x$ direction, $(-1)^{x_1+x_2}$ on links in the $y$ direction), $\psi_{x,i}$ the quark field at site $x$ with colour index $i$, $U_{ij}(\ell)$ the link operator (the gauge field's "parallel transporter" along link $\ell$), $n_x$ the quark number at site $x$, $j_\ell$ the *link spin*, $W_P$ the *plaquette* (the product of four $U$ around one square of the lattice). Four physics terms therefore exist: **hopping** (a quark moves along a link and flips its flux), **mass** (diagonal), **electric** (diagonal, costs $\tfrac{g^2}{2}\cdot\tfrac34$ for each link that carries flux), and **plaquette** (flips the flux on all four links of a square).

**Truncation.** The gauge field on each link is cut off at spin $j_{\max}=\tfrac12$, so each link carries either no flux ($j=0$) or a spin-$\tfrac12$ flux ($j=\tfrac12$). The cost of this truncation on the 2x2 lattice is computed exactly in `data/references.json -> truncation_2x2`: raising the cut-off to $j_{\max}=1$ lowers $E_0$ by $0.0019205$ at $g^2=4$ (74 instead of 38 states in the $B=0$ sector).

### 2.2 Conventions (fixed; changing one forces a re-run of gates E1-E3)

From `CLAUDE.md` rule 2 and `README.md`:

- **Link generators**: $L_a=-J_a^{\top}$ acting on the left magnetic index, $R_a=+J_a$ on the right one; commutators $[L_a,U]=-(T_aU)$, $[R_a,U]=+(UT_a)$ (file `src/skqd/su2.py`). $J_a$ are the standard spin matrices.
- **Matter charge** $Q_a=\psi^\dagger\tfrac{\sigma_a}{2}\psi$ ($\sigma_a$ the Pauli matrices).
- **Site index** $x_1L_y+x_2$; links oriented in $+x$ and $+y$; Jordan-Wigner order equals site order (`src/skqd/lattice.py`). (Jordan-Wigner is the textbook trick that turns fermions into qubit operators by attaching a sign string.)
- **Qubit order**: qubit $k$ is bit $k$ of an integer, little-endian (`src/skqd/reference_sim.py`, Qiskit's convention); the codeword layout is in `src/skqd/codec.py`.

### 2.3 Gauss's law, physical states and the sectors

**Gauss's law.** A gauge theory has redundant degrees of freedom; only states that satisfy a local constraint, *Gauss's law*, are physical. At every site $x$ the colour charge carried by the outgoing links, the incoming links and the quarks must cancel:

$$
G_a(x)=\sum_{\ell\ \mathrm{out}}L_a(\ell)+\sum_{\ell\ \mathrm{in}}R_a(\ell)+Q_a(x)\ \Big(+\tfrac{\sigma_a}{2}\Big|_{\rm static}\Big),\qquad G_a(x)|\text{phys}\rangle=0 .
$$

($a=1,2,3$ labels the three SU(2) directions; the optional last term is a *static charge*, an infinitely heavy quark used to probe the potential $V(r)$ between charges.) Gate E1 verified $[G_a(x),H]=0$ with maximum residual $0.0$ in the 160 000-dimensional redundant space of the 2x2 lattice (`validation/E1.json`, criterion "max |[G_a(x), H]|"; the manual quotes $2\times10^{-15}$).

**Dressed-site basis.** The package does not work in the redundant space. It uses the *dressed-site* (spin-network) basis of the manual's Step 2: a basis state is
$|b\rangle=|\{j_\ell\},\{n_x\},\{\iota_x\}\rangle$, i.e. the link spins, the quark occupations $n_x\in\{0,1,2\}$ and, at vertices where the Gauss singlet is not unique, an **intertwiner label** $\iota_x$ (the label of which of the two possible gauge-singlet combinations is meant; the manual fixes it by a fusion-tree convention). The number of physical states, the manual's Table 2, reproduced by gate E2 (`validation/E2.json`, 51 criteria PASS):

| lattice | qubits | physical states | distinct $(\{j\},\{n\})$ labels without $\iota$ |
|---|---|---|---|
| 2x2 | 12 | 82 | 82 |
| 2x3 | 20 | 1 727 | 1 460 |
| 2x4 | 28 | 37 165 | 26 248 |

(Earlier versions of the plan used the labels without $\iota$ and thereby miscounted; the manual's Table 2 and gate E2 fix this.)

**Sectors.** $H$ conserves *baryon number* $B=\tfrac12\sum_x(n_x-n_x^{\rm vac})$ with $n^{\rm vac}_x=1-(-1)^{x_1+x_2}$ (a count of quarks minus antiquarks, divided by the number of colours). The project also uses the integer $2B$ ("twoB") as a key. Charge conjugation maps $B\to -B$, so only $B\ge 0$ is computed. Sector sizes (the manual's Table 2, gate E2): 

| lattice | $B=0$ | $B=\pm1$ | $B=\pm2$ | $B=\pm3$ | $B=\pm4$ |
|---|---|---|---|---|---|
| 2x2 | 38 | 20 | 2 | | |
| 2x3 | 677 | 426 | 95 | 4 | |
| 2x4 | 12 843 | 8 934 | 2 869 | 350 | 8 |

With a static pair at distance $r$: 2x3 with static pair $r=1$ has 2 729 states ($B=0$: 1 089), $r=2$ has 2 418 ($B=0$: 978) (manual Table 2; `data/references.json` keys `2x3+static r=1|...`).

The project calls the three experimentally relevant sectors **$B=0$** (the vacuum sector), **$B=1$** (one baryon, here a "diquark", a pair of quarks; the lowest levels there form a near-degenerate cluster of $L_x$ states) and the **static** sectors. Project key `2B=2` means $B=1$ and `2B=4` means $B=2$.

### 2.4 The exact reference energies ("exact $E_0$")

Because the sectors are small enough (up to 12 843 states), the Hamiltonian can be diagonalized exactly on a classical computer. These exact values are the *reference* against which every later approximate method is judged. They come from the **dressed-site builder** (`src/skqd/hamiltonian.py`, `exact.py`), which was validated against an independent route (the redundant-space "projector" construction, `src/skqd/fullspace.py`): all 82 eigenvalues agree to $2.3\times10^{-14}$ (`validation/H0_2x2.json` provenance row; `validation/E1.json`, 23 criteria PASS).

Key reference numbers at $g^2=4$, $m=0.75$ (`data/references.json -> references`; `validation/E3.json`, 85 criteria PASS):

| lattice, sector | dim | $E_0$ | next levels | $\Delta t=\pi/W$ | support$_{99}$ / support$_{99.9}$ | participation ratio |
|---|---|---|---|---|---|---|
| 2x2, $B=0$ | 38 | $-3.6407665507$ | $-0.9622448$, $-0.8505667$ | 0.24501195 | 9 / 16 | 1.4744 |
| 2x2, $B=1$ | 20 | $-1.8615880345$ | $-1.8197453$, $+0.2082291$ | 0.33194311 | 8 / 13 | 2.5924 |
| 2x3, $B=0$ | 677 | $-5.6026004579$ | $-2.8886027$, $-2.8651784$ | 0.15644332 | 31 / 86 | 1.9138 |
| 2x3, $B=1$ | 426 | $-3.8260844431$ | $-3.8017280$, $-3.6686561$, $-1.6528839$ | 0.18697342 | 42 / 95 | 3.5609 |
| 2x3, $B=2$ | 95 | $-2.0118247869$ | $-1.8622427$, $-1.8438853$ | 0.23360023 | 15 / 22 | 1.5043 |
| 2x4, $B=0$ | 12 843 | $-7.5652140739$ | $-4.8435986$, $-4.8374654$ | 0.11469820 | 76 / 305 | 2.4883 |
| 2x4, $B=1$ | 8 934 | $-5.7801629009$ | $-5.7741284$, $-5.6540876$ | 0.13031277 | 127 / 470 | 4.7849 |

Here "support$_{99}$" ($S_{99}$) is the smallest set of configurations that together carry 99 % of the ground-state *weight* $|\langle b|\Omega\rangle|^2$ ($\Omega$ = exact ground state), support$_{99.9}$ ($S_{999}$) the same for 99.9 %, and the *participation ratio* is the effective number of configurations that matter. Small supports are what makes the whole sampling method viable ("sparse ground state"). Further rows (other $g^2$, static pairs, units, the derived physical quantities) are in Appendix block (k). Derived 2x3 quantities at $g^2=4$ (`data/references.json -> derived`): meson-like gap $\Delta_0=2.7139978$, baryon mass $M_B=E_0^{B=1}-E_0^{B=0}=1.7765160$, static potentials $V(1)=1.3871769$, $V(2)=2.5898457$, binding $0.0377436$; at $g^2=2$: $\Delta_0=1.4980195$, $M_B=1.1350016$, $V(1)=0.7819829$, $V(2)=1.3740250$; 2x4 at $g^2=4$: $\Delta_0=2.7216155$, $M_B=1.7850512$.

### 2.5 The qubit encoding (the "codec") and the Gauss-law decoder

**Encoding.** A quantum computer holds states as bit strings in superposition. The project assigns each physical basis state a short bit string, a **codeword** (`src/skqd/codec.py`; manual Step 2.4):

- A *corner* vertex (two link ends) uses 3 qubits: two *flux bits* (one per link end; $j=\tfrac12\Leftrightarrow 1$) and one more bit that either gives the quark occupation ($n=0$ or $2$) or is a *flag* meaning "not a valid state".
- An *interior* vertex (three link ends) uses 4 qubits: three flux bits and one more bit (occupation, intertwiner label $\iota$, or flag).
- Totals: 2x2 has four corner vertices, so 12 qubits; 2x3 has four corners and two interior vertices, so 20; 2x4 has four corners and four interior vertices, so 28. A static charge at an interior vertex needs 5 qubits, so a static pair at $r=1$ on 2x3 costs 21 qubits.

Only 82 of the $2^{12}=4096$ strings at 2x2 are valid codewords; at 2x3, 1 727 of $2^{20}$.

**Decoder.** Every measured bit string (a *shot*) is passed through a classical checker (manual Step 2.5): (i) split it into vertex codewords; (ii) reject if any vertex carries a flag; (iii) reject if the two ends of any link disagree about the flux on that link (*link consistency*, the check Gauss's law implies); (iv) read the label; (v) reject if the baryon number is not the target sector's; (vi) look the label up in the basis. A string that survives is *accepted*. Gate E2 verified that encode-then-decode returns every one of the 82 (2x2) and 1 727 (2x3) states, and the **random acceptance** $a$: the fraction of uniformly random bit strings that the decoder accepts. At 2x2 this is exactly $a_{B=0}=38/4096=0.00927734375$ and $a_{B=1}=20/4096=0.0048828125$ (exhaustive over all 4096 strings, `validation/E2.json`, `validation/H0P.json`), at 2x3 it is $0.146\,\%$ ($1727/2^{20}$, `validation/E2.json`). Because $a$ is not zero, noise that happens to land on a valid-looking string is silently accepted; this single fact drives much of Sections 6 and 8.

### 2.6 Krylov time evolution and the "coarse step"

**Krylov idea.** Starting from a simple **reference configuration** $|b_0\rangle$ (e.g. the Dirac-sea vacuum: odd sites doubly occupied, even sites empty, no flux), apply the time-evolution operator $e^{-iH\,t}$. The states $e^{-ik\Delta t\,H}|b_0\rangle$, $k=0,1,2,\ldots$ span the *Krylov space*; they spread the reference over exactly those configurations that the Hamiltonian couples it to, which are the ones the ground state needs. A quantum computer can prepare such states naturally, and then *measure* them in the configuration basis to learn which configurations appear. That list is the support.

**Time step.** To avoid aliasing the step is $\Delta t=\pi/W$ with $W=E_{\max}-E_{\min}$ the spectral width of the sector (manual Step 1.4). Values at $g^2=4$: 0.245 (2x2, $B=0$), 0.156 (2x3, $B=0$), 0.115 (2x4, $B=0$) (`data/references.json`, table above; gate E3 verified $\Delta t$ per sector).

**Coarse step.** Rather than approximating $e^{-iHt}$ by many small Trotter steps (which makes circuits deep), the project uses *one* product of exact term evolutions per circuit,
$$
|\psi_{r,k}\rangle=\prod_{\gamma}e^{-iH_\gamma\,k\Delta t}\,|r\rangle,\qquad k=1,\dots,4,
$$
where $H=\sum_\gamma H_\gamma$ splits into the term groups $\gamma$ (diagonal part, each hopping link, each plaquette) and $r$ is a reference configuration. This is the "coarse step of order $k$" (manual Step 4.3, family (b)). The state is then *not* the exact Krylov state, but it is gauge invariant by construction (each factor is an exact unitary on the Gauss-law-obeying codewords) and covers more of the support at a quarter of the depth (manual: 62 vs 41 of 86 configurations at 2x3).

**Circuit family sizes.** One circuit per (reference, $k$) pair. 2x2: 5 references in $B=0$ (the Dirac sea plus four one-meson configurations) and 2 in $B=1$ (the diquark on either even site), times $k=1..4$: 28 circuits. 2x3: 8 references in $B=0$ and 3 in $B=1$, times 4: 32 + 12 = 44 circuits (`validation/S2D.json`; `data/quantinuum/devices_20261002.json -> counts.2x3.per_circuit`: 32 circuits labelled `B0_ref...`, 12 labelled `B1_ref...`). Term groups: 2x2 has 6 (diagonal, 4 hoppings `hop0..hop3`, 1 plaquette `plaq0`), 2x3 has 10 (diagonal, 7 hoppings, 2 plaquettes `plaq0, plaq1`), 2x4 has 14 (`validation/S2_2x4.json`, prompts/22).

**Exact circuits ("structured gates").** Gate S2 compiled every term to basic gates *exactly* (no approximation of the term unitary): hopping blocks are bipartite, so $e^{-i\theta h}$ is built from Givens-rotation chains; verified to $1.87\times10^{-14}$ against the reference (`validation/S2.json`, criterion "max |structured circuit - reference|"), leakage out of the codeword space $4.5\times10^{-14}$ (<$10^{-9}$ required). Gate counts per coarse step: 2x2 256 CZ all-to-all, 618 routed on a heavy-hex device; 2x3 2 164 CZ all-to-all (2 158 RZZ gates in the RZZ basis), 5 477 routed; 2x4 69 688 CZ all-to-all (`validation/S2.json`, `validation/S2_2x4.json`; Appendix block (j)).

### 2.7 SKQD: sample, build the subspace, Ritz energy, certificates

**SKQD** = *sample-based Krylov quantum diagonalization* (Yu et al. arXiv:2501.09702; Rosanowski et al. arXiv:2510.26951; Robledo-Moreno et al. arXiv:2405.05068). The recipe in the manual (Steps 4-5):

1. **Sample.** Run each coarse-step circuit on the device many times, measuring all qubits in the configuration basis.
2. **Decode** each shot; the union of accepted configurations over all circuits of a sector (always including the references) is the **support** $B$. (The project uses $B$ both for baryon number and, in "$|B|$", for the support; context makes it clear. The project's own labels for two versions of the support are **$B_{\rm all}$** = every accepted state of the sector, and **$B_{\rm sig}$** = "signal support" = only states whose counts exceed the uniform-noise expectation $\mu_s=Na/\dim$ at the one-sided $3\sigma$ Poisson level, with $N$ the shots of that sector; both defined in `prompts/24`, decision P9.)
3. **Project.** Build $H_B=P_BHP_B$, the Hamiltonian restricted to the span of $B$, with the *exact* matrix elements from the classical builder (the quantum device only chooses $B$, it never supplies matrix elements). Diagonalize it: the lowest eigenvalue is the **Ritz energy** $E_R$ ("Ritz" is the name for a variational estimate from a subspace). **Variational bound:** $E_R\ge E_0$ for any $B$; with $\varepsilon_B=\|(1-P_B)\Omega\|^2$ the weight of the ground state outside $B$,
$$
0\le E_R-E_0\le\frac{\varepsilon_B\,(E_{\max}-E_0)}{1-\varepsilon_B}\quad\text{(manual eq. (6))}.
$$
4. **Certify.** Apply the exact $H$ to the Ritz vector $\psi_R$ and form the **Hamiltonian residual** $r_H=\|(H-E_R)\psi_R\|$ (manual eq. (7)). Two rigorous facts hold for any $B$: $E_R\ge E_0$, and (**Weinstein**) *some* exact eigenvalue lies in $[E_R-r_H,\,E_R+r_H]$. To turn this into an interval for $E_0$ one needs a *gap assumption* (that the exact level nearest to $E_R$ is the ground state, guaranteed if $r_H<E_1-E_R$ with $E_1$ the first excited exact level). Then:
$$
\textbf{Weinstein:}\ E_0\in[E_R-r_H,\,E_R];\qquad
\textbf{Kato--Temple:}\ E_0\ge E_R-\frac{r_H^2}{\alpha-E_R}\ \ \text{with } \alpha\le E_1,\ \alpha>E_R .
$$
The project uses the second Ritz value as $\alpha$ (an upper bound on $E_1$, not a lower bound), so both intervals are labelled **gap-assumed**. A near-degenerate cluster (as in $B=1$) is certified as a whole. Differences such as $M_B$ are reported by interval arithmetic.
5. **Support quality.** *Recall* of the exact support: $R_\varepsilon=|B\cap S_\varepsilon|/|S_\varepsilon|$; the count of *false positives* (accepted states carrying exact weight $<10^{-8}$); the *yield* (accepted shots over shots); and the error $E_R-E_0$.

**What is rigorous and what is heuristic** (manual Step 4.1): the energy bound and the intervals are rigorous for any $B$. The claim that the device finds a good $B$ is heuristic on real hardware, because the SKQD convergence theorem assumes exact Krylov states and a sparse ground state, neither of which a noisy coarse-step circuit satisfies.

### 2.8 Classical controls

Because the diagonalization is variational for any $B$, the only quantum content is *which* $B$ is chosen. The manual (Step 6) therefore preregisters classical supports of equal size $|B|$: **CIPSI** (selected configuration interaction: grow $B$ by repeatedly adding the Hamiltonian-neighbour configurations with the largest score $|\langle c|H|\psi_R\rangle|^2/(H_{cc}-E_R)$), **BFS** (breadth-first neighbour growth, truncated), **random** configurations, the **oracle** (top-$|B|$ by exact weight, simulator only), **ML-alone**, and device-seeded CIPSI. The manual's emulation (Table 3) and gate S1 find that CIPSI tracks the oracle at 2x3 and beats the device proxy at equal $|B|$: at $|B|=160$ the errors are $1.2\times10^{-3}$ (CIPSI) and $1.2\times10^{-3}$ (oracle) against $8.6\times10^{-3}$ for the device proxy at $f=0.1$. The plan therefore does **not** expect a device advantage; the primary endpoint P1 is a "characterized null" (manual Step 6.3). Gate S1's controls rows, from `validation/S1.json`: CIPSI vs oracle at $|B|=160$ is $1.2\times10^{-3}$ vs $1.2\times10^{-3}$ ($B=0$) and $1.0\times10^{-3}$ vs $9.8\times10^{-4}$ ($B=1$); at $|B|=320$, $6.5\times10^{-5}$ vs $6.7\times10^{-5}$ and $6.7\times10^{-6}$ vs $6.5\times10^{-6}$.

### 2.9 The neural / ML step

The manual's Step 7 specifies a *gauge-invariant neural importance model* $f_\theta(b;\lambda)\approx\log|\langle b|\Omega_\lambda\rangle|$ (a message-passing network on the lattice graph, conditioned on $\lambda=(g^2,m,B,L_x,\text{static placement})$, trained with a pairwise ranking loss, eq. (8), and *leakage-safe* splits: test points never in training), for four uses: recovery of flagged bit strings (eq. (9)), size-constrained extension of $B$, ML-alone support proposal, and transfer from small to large lattices. The learned model is classical, so the project is "ML-assisted quantum simulation", not quantum machine learning.

**What actually exists in the package (important).** Only the manual's Step 7.4 *minimal model*: `src/skqd/ml.py` holds hand-built features (16 gauge-invariant numbers such as numbers of flux links by direction, quarks on even sites, holes on odd sites, $\sum\iota$, the diagonal energy relative to the Dirac sea), `design`, `RidgeRanker` (a ridge regression, i.e. linear regression with an $L_2$ penalty) and `spearman` (Spearman rank correlation). It is trained leakage-safely and scored **only in gate S1 on exact 2x3 and 2x4 amplitudes**: Spearman $0.862$ ($B=0$) and $0.888$ ($B=1$) at 2x3, $0.763$ on the 2x4 transfer (`validation/S1.json -> data.ml_spearman|B=0`, `data.ml_spearman|B=1`, `data.2x4_ml_spearman`; the manual's own numbers are 0.85 / 0.89). No graph network is implemented, no recovery routine (eq. (9)) exists in `src/skqd/`, and **no learned model has ever touched hardware data** (`reports/H0_2x2_full_hardware_report_20261002.md`, plan rows 7.1-7.5). "Neural-enhanced" is therefore, as of today, a plan rather than a result.

### 2.10 Noise, the clean fraction, and the statistics of the hardware runs

A real quantum computer makes errors. For this project the key concepts are (all defined in the manual Step 4.4 and Step 8 and refined by later amendments):

- **Clean fraction $f$** ("fidelity proxy"): the probability that a single shot of a circuit carries *no error at all*. The manual's model is $f\simeq(1-\epsilon)^{N_{CZ}}$ for per-CZ error $\epsilon$ and $N_{CZ}$ CZ gates, times a readout factor 0.82 for 12-20 qubits at 1 % readout error each. The **signed budget** (amendment 01 item 2): mean $f\ge0.1$ over the circuit family and worst circuit $f\ge0.05$, read on the *scheduled* circuit (the circuit as it is actually timed on the device).
- **Idle-time error.** A qubit that waits while others are gated decoheres (loses its phase, "dephasing", time constant $T_2$; loses energy, time constant $T_1$). Including it: $f=f_{\rm gates}\,e^{-S_{\rm idle}}$ with $S_{\rm idle}=S_{T_1}+S_{T_2}$ the idle-window relaxation budget in nats (`src/skqd/idle.py`). $T_2^{\rm echo}$ is the dephasing time measured with one refocusing pulse (the number in IBM's calibration records); $T_2^*$ is the dephasing time of free evolution (what an idle qubit in a circuit actually feels). The project found $T_2^*/T_2^{\rm echo}\approx0.17$ on its devices (Section 6).
- **Yield model** (manual Step 4.4, amended by rule M4.4): accepted fraction $y=0.82f+(1-f)a+(\text{near-clean term})$, where $a$ is the random acceptance of 2.5 and the *near-clean* term counts shots with a few errors that still decode as valid (the project's own concept). Consequence: the accepted-shot count overstates the clean fraction (by a factor 15 on `ibm_fez`, Section 6).
- **Clean-fraction estimators** (all the project's own labels): $f_{\rm hit}$, the *reference-string hit fraction*: (count of the circuit's most probable ideal output string minus the accidental hits expected from uniform noise) divided by (shots $\times$ the ideal probability of that string $\times$ 0.82). The **mixture estimator** fits one weight separating the ideal distribution from uniform noise over all accepted strings. $f_0$ (or $f_0'$): the *fault-free fraction* (no gate fault at all). $f_{\rm ideal}$: the *ideal-sample fraction*, shots that sample the ideal output distribution exactly (fault-free shots plus shots whose faults are *benign*, e.g. a phase error that does not change the measured string); $f_{\rm hit}$ turns out to estimate $f_{\rm ideal}$, not $f_0$; their ratio $r_{nc}=f_{\rm hit}/f_{\rm ideal}$ is the *near-clean correction* (Section 6.17: $r_{nc}=1.115$).
- **Saturation (project rule C22).** At 2x2, once $Na/\dim\gtrsim5$ (with $N$ the shots in a sector), every sector state is hit about five or more times by accidentally valid noise alone, so $B_{\rm all}$ is the whole sector whether or not the processor worked. The full 2x2 hardware run has $Na/\dim=16.97$ ($B=0$) and $15.72$ ($B=1$) (`validation/H0_2x2.json -> data.C22`). Therefore the energy from the whole accepted support is not a device result; the signal support $B_{\rm sig}$ and the controls are.
- **Shot rule** (manual eq. (5)): shots per circuit $S\ge\lambda^*/(0.82\,f\,p)$, where $p$ is the ideal probability of a configuration and $\lambda^*=6.295794$ is the Poisson mean that gives three expected observations with 95 % probability (`skqd.skqd.poisson_lambda_star(3,0.95)`). The project's rule **D3'** (2x2 sizing: every sector state must reach $\lambda^*$ expected clean counts from the $k=4$ circuits at $0.7f$) and the 2x3 replacement **D3'-R** are described in Section 6.

### 2.11 Summary table of the three lattices

| item | 2x2 | 2x3 | 2x4 |
|---|---|---|---|
| sites / links / plaquettes (lattice geometry) | 4 / 4 / 1 | 6 / 7 / 2 | 8 / 10 / 3 |
| qubits | 12 | 20 | 28 |
| physical states | 82 | 1 727 | 37 165 |
| sector dimensions $B=0$ / $B=1$ | 38 / 20 | 677 / 426 | 12 843 / 8 934 |
| exact $E_0$ at $g^2=4$, $B=0$ / $B=1$ | $-3.6407665507$ / $-1.8615880345$ | $-5.6026004579$ / $-3.8260844431$ | $-7.5652140739$ / $-5.7801629009$ |
| $\Delta t$ at $g^2=4$, $B=0$ / $B=1$ | 0.24501 / 0.33194 | 0.15644 / 0.18697 | 0.11470 / 0.13031 |
| 99.9 % support $B=0$ / $B=1$ | 16 / 13 | 86 / 95 | 305 / 470 |
| random acceptance $a$ | 0.00928 ($B=0$), 0.00488 ($B=1$) | 0.00146 (any sector, upper bound) | not tabulated in the sources read |
| exact coarse step, CZ all-to-all / routed heavy-hex | 256 / 618 | 2 164 / 5 477 | 69 688 / 148 726 |
| role in the plan | decoder / yield calibration only (manual Step 0, 9.1) | the SKQD test (H1, H2, P1) | simulator-only transfer test; hardware only if 2x3 passes |

Sources: `data/references.json`, `validation/E2.json`, `validation/S2.json`, `validation/S2_2x4.json`, `validation/K0_2x3_2x4.json -> data.2x4` (148 726 routed on the FakeFez map), manual Step 0.

## 3. The intended plan

Source: `proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md` (Steps 0-11, Appendix A), `validation/gates.md`, `prompts/08_month_plan_and_reporting.md`, `proposal/amendment_01_devices_and_budgets.md`.

### 3.1 What the project set out to do

**Title of the manual:** "Neural-enhanced sample-based Krylov diagonalization for SU(2) with dynamical quarks in 2+1D" (SU2QC Project 2, revision 2, corrected specification of 10 Sept 2026, prepared for D. Digonto). The first version of the plan was reviewed by two referees ("Claude" and "Codex") who both rebuilt the 2x2 Hamiltonian and reproduced every number but found the same problems beyond 2x2: non-unique labels (fixed by adding the intertwiner label), a 2x2 hardware run that cannot test SKQD because its sectors saturate (re-scoped as a calibration), a missing classical control (added: CIPSI, BFS, random, oracle), an optimistic noise model, a one-sided variational bound (replaced by two-sided certified intervals), and an under-specified ML model. The revised manual concludes that, at these small sizes, a classical selected-CI support of equal size is at least as good as the device-generated support; so the experiment is specified as a **workflow validation with certified spectra and a measured device-support quality, not as an advantage demonstration**.

**Roles of the three lattices (manual Step 0).**
- 2x2 (12 qubits, 82 states): *pipeline calibration only* (decoder validity, yield versus circuit depth, readout confusion, sector filter); not an accuracy test, because any run of about $10^3$ shots saturates its sectors (38 and 20 states).
- 2x3 (20 qubits, 1 727 states, sectors 677 and 426): *the SKQD test*, with exact references from the Step-3 builder.
- 2x4 (28 qubits, 37 165 states): simulator-only transfer and scaling test with exact Lanczos references; hardware only if the 2x3 gates pass with margin.

**Claims if all gates pass (manual Step 0):** (i) first quantum-centric spectroscopy of a non-Abelian gauge theory with dynamical matter in two spatial dimensions (vacuum energy, diquark-baryon cluster, meson-like gap, static potential $V(1),V(2)$ on 2x3, with two-sided certified intervals); (ii) a validated Gauss-law-aware pipeline; (iii) a measured curve of device-support quality (recall, false positives) versus circuit depth and shots with the classical controls at equal $|B|$. **Not claimed:** quantum advantage; the continuum limit; string breaking.

### 3.2 The ten steps of the manual

| step | content | gate(s) |
|---|---|---|
| 1 | Hamiltonian, sectors, symmetries, exact references; $\Delta t=\pi/W$ per sector | E1, E3 |
| 2 | gauge-invariant basis with intertwiner labels; codewords; decoder | E2 |
| 3 | dressed-site Hamiltonian builder, validated against the projector construction | E1 |
| 4 | support generation on the QPU: reference sets, coarse circuits (family b: exact coarse steps $k=1..4$; family a: Trotterized ablation), $\le250$ CZ per step at 2x2 and $\le500$ at 2x3, fidelity/yield model, shot rule eq. (5) | S2, S3 |
| 5 | HPC post-processing: projected diagonalization, residual $r_H$, Weinstein and Kato-Temple intervals, support metrics | S1, H1, H2 |
| 6 | classical controls (CIPSI, BFS, random, oracle, ML-alone, device-seeded CIPSI) and the primary endpoint P1 | S1, P1 |
| 7 | gauge-invariant neural importance model; leakage-safe splits; four uses; the "seven protocols" comparison | M1 |
| 8 | noise simulation before hardware (the Step 8.2 proxy; transpiled device-model simulation; gate S3 recall $\ge0.9$) | S3 |
| 9 | hardware: 9.1 the 2x2 calibration run; 9.2 the 2x3 production (4 sectors: $B=0$, $B=1$, static $r=1$, static $r=2$; 32-44 circuits per sector; $2\times10^5$ shots per sector; two calibration windows); 9.3 optional 2x4 | H0, H1, H2 |
| 10 | analysis, gates, error budget, reporting (raw bit strings, calibration snapshots, circuits and decoder released) | all |
| 11 | six-week timeline and Plan B | -- |

### 3.3 The manual's gate table (Step 10) and its endpoints

| gate | check | criterion in the manual | manual's expected timing |
|---|---|---|---|
| E1 | $[G_a(x),H]=0$; 82-dim kernel; sector split; two builders agree to $10^{-12}$ | done ($8\times10^{-15}$) | done |
| E2 | counts of Table 2; codec round trip on all 2x3 states; random-bitstring acceptance $\approx0.15\,\%$ | done | done |
| E3 | 2x3 and 2x4 references (Table 1); static sectors; $\Delta t=\pi/W$ per sector | done | done |
| S1 | emulated support recall $\ge0.9$ at $f\ge0.1$ with the production budget; controls table | done (Tables 3, 4) | done |
| S2 | routed CZ per coarse step $\le500$ on the target map; noiseless compiled circuits leak-free | -- | week 2 |
| S3 | Aer device-model recall $\ge0.9$ for the production set; shot budget fixed | -- | week 2 |
| H0 | 2x2: decoder validity, bit order, parity checks; **measured $f$ within 30 % of the model** | -- | week 3 |
| H1 | 2x3 $B=0$: certified interval $I_0$ of width $\le0.1$ containing the exact $E_0$; recall $\ge0.8$ | -- | week 4 |
| H2 | 2x3 $B=1$: cluster energy certified to $\pm r_H\le0.15$; $V(1),V(2)$ intervals containing the exact values | -- | week 4 |
| P1 | **primary endpoint**: curves $E_R-E_0$ and $R_{10^{-3}}$ versus $|B|$ for device and CIPSI at equal $|B|$, bootstrap bands; "advantage" declared only if the device curve lies below CIPSI everywhere with non-overlapping bands | -- | week 5 |
| M1 | ML uses credited only under Step 7.5 (must beat the baseline at equal $|B|$ on 2x3 hardware data and on held-out couplings) | -- | week 5 |

**Primary endpoint P1** (manual Step 6.3): the pair of curves $E_R-E_0$ and $R_{10^{-3}}$ versus $|B|$, device versus CIPSI at equal $|B|$, on 2x3 hardware data. The manual's own expectation is a characterized null (device between BFS and CIPSI) and says it is publishable as "the first measured support-quality curve for a non-Abelian theory".

**Manual timeline (Step 11):** week 1 E1-E3, S1; week 2 S2, S3; week 3 H0 (2x2 hardware, plus a 2x3 pilot of $10^4$ shots per circuit); week 4 H1, H2 (2x3 production, four sectors, two calibration windows); week 5 P1, M1, 2x4 transfer on the simulator; week 6 research note and release bundle. **Plan B:** if S3 fails reduce to $k=1,2$ and raise shots; if H1 fails use the union support of device + CIPSI and report the hardware as the measured support-quality curve alone.

### 3.4 Amendments and decisions that changed the plan (in order)

| date | document | what it changed |
|---|---|---|
| 2026-09-15 | `prompts/11` (planner decision), owner decision | the CZ-count budget cannot be met in this encoding (S2 FAIL on cost only); measure the cost floor first |
| 2026-09-16 | `prompts/12`; `proposal/amendment_01_devices_and_budgets.md` (draft) | combined plan: 2x2 on a Heron-class IBM device, 2x3 exact circuits on an all-to-all ion-trap device; replace the gate-count budget by the device-resolved budget "mean $f\ge0.1$, worst $\ge0.05$" (gate S2D) |
| 2026-09-23 | amendment 01 items 1-3 **signed** | item 1: the 2x2 patch is chosen by the idle-aware objective; item 2: $f$ is read on the *scheduled* circuit (thresholds 0.1 / 0.05 unchanged); item 3: the exact family is kept and judged on duration. Items 4 (the 2x3 device) and 5 (the shot quota) **remain open** |
| 2026-09-30 | `data/H0_replan_owner_decisions.md` | nine owner decisions D8', D1', D3'-f, D3''-H0, D5', C2', C3', H0P-Y', M4.4 (all approved), see Section 6.11 |
| 2026-10-02 | `data/owner_decision_20261002_run_below_signed_budget.md` | run the full 2x2 SKQD on `ibm_kingston` using the 600 s budget even if the signed budget is not met |
| 2026-10-05 | `data/owner_decision_20261005_partB.md`, `data/owner_decision_20261005_k1_2x3_fpilot.md` | decisions 1a, 2a, 3a on `prompts/29` Part B' and the K1 2x3 pilot (Section 9) |

### 3.5 What the manual asked for that has not been done

The manual's steps that need 2x3 hardware (Step 9.2, H1, H2, P1, M1, the seven-protocol table) and the neural step on hardware data are all **open** as of today; the status of each of the 51 plan rows is in Section 10.

## 4. The package layout

Source: `CLAUDE.md`, `README.md`, `RUNBOOK.md`, `SKQD-CI-SETUP.md`, `prompts/ROUTING.md`, `.claude/agents/*.md`, directory listings made on 2026-10-05, and `graphify god-nodes`. The package is a Python code base (`src/skqd/`, 27 modules, 6 132 lines by `wc -l`), 64 scripts in `scripts/`, 28 test files in `tests/`; code facts below are from module docstrings.

### 4.1 `src/skqd/`: the modules

**Physics core** (exact numerics, numpy/scipy only; no quantum software needed):

| module | what it does |
|---|---|
| `su2.py` | spin matrices, Clebsch-Gordan coefficients, the truncated electric-basis link operators ($j_{\max}=\tfrac12$); fixes the generator convention $L_a=-J_a^T$, $R_a=+J_a$ |
| `fermions.py` | the two-colour staggered-fermion site (Fock space, Jordan-Wigner pieces) |
| `lattice.py` | the open $2\times L_x$ ladder: site index $x_1L_y+x_2$, links, plaquettes, staggered phases $\eta$ |
| `vertex.py` | local singlet (intertwiner) tensors of one dressed vertex (manual Algorithm 1) |
| `basis.py` | the gauge-invariant configuration basis $|\{j\},\{n\},\{\iota\}\rangle$ with baryon-number sectors (Step 2) |
| `hamiltonian.py` | the dressed-site Hamiltonian builder (Step 3, Algorithm 2) and the Hamiltonian-neighbour query |
| `fullspace.py` | the second, independent route: the redundant-basis "projector" construction of the 2x2 model (gate E1) |
| `exact.py` | exact sector references (Table 1): class `Model` (central object: 86 edges in the graph), sector energies, $\Delta t$, supports |
| `codec.py` | hardware codewords and the per-shot decoder (Steps 2.4 and 2.5); class `Codec` (69 edges) |

**SKQD workflow**:

| module | what it does |
|---|---|
| `krylov.py` | support-generating states emulated exactly in the gauge-invariant basis (Step 4): exact Krylov states, coarse-step states `coarse_states`, reference sets `references` |
| `noise.py` | the device-proxy noise model on bit strings (Step 8.2): clean with probability $f$, otherwise uniform garbage or Poisson-corrupted, plus readout flips; `measure_and_decode` |
| `skqd.py` | HPC post-processing (Step 5): `ritz`, `certify` (Weinstein, Kato-Temple), `support_metrics`, `exact_support`, `shot_rule`, `poisson_lambda_star`, `yield_model`, `clean_fraction_from_yield`, `reference_string_test`, `clean_fraction_mixture`, `near_clean_yield` |
| `controls.py` | classical-support controls at prescribed size (Step 6): `cipsi`, `bfs`, `random_support`, `oracle`, `top_by_count` |
| `ml.py` | the minimal gauge-invariant ridge ranker (Step 7.4) |

**Circuit layer** (translates the exact term evolutions into gates):

| module | what it does |
|---|---|
| `reference_sim.py` | numpy reference: codeword embedding into the $2^n$ space, exact block unitaries, a plain statevector simulator; qubit $k$ = bit $k$ |
| `circuits_ir.py` | backend-independent circuit description ("IR", a list of gates); class `CircuitFactory` (48 edges); `structured_term_gates` (Givens-chain / Gray-code multiplexed-rotation synthesis) with `angle_mode` exact or fixed |
| `circuits_qiskit.py` | IR to Qiskit; statevector check; transpiled CZ counts (gate S2); Aer noise sampling (`sample_many` with memory-aware chunking `shot_chunk_for`, adaptive halving on GPU out-of-memory) |
| `circuits_cudaq.py` | IR to CUDA-Q (generated kernel source, registered custom unitaries) |
| `sparse_sim.py` | exact sparse statevector simulation of IR and transpiled circuits (used for 2x4 verification) |
| `quantinuum_native.py` | IR to the Quantinuum native gate set $\{R_z,\ \mathrm{PhasedX},\ \mathrm{ZZPhase}\}$ (gate Q0P_2x3) |

**Device-model and hardware bookkeeping:**

| module | what it does |
|---|---|
| `idle.py` | idle-time relaxation in $f$: ASAP schedule, per-window relaxation, `f_idle_aware`; the $T_2$ convention is an argument and a recorded field |
| `coherence.py` | the coherence ($T_2$ vs gate time) a compiled circuit requires of a device |
| `device_req.py` | device-requirement algebra: `clean_shot_fraction`, `target_with_idle`; inverts the $f$ model |
| `hardware.py` | hardware-session helpers: readout confusion matrix, inverse, transpiled layout, `logical_statevector`, link-consistency checks |
| `hpc.py` | CI / Slurm / GPU telemetry helpers shared by gate scripts that may run on Perlmutter |
| `report.py` | gate-result bookkeeping: each gate script records its criteria and the numbers it computed in `validation/<GATE>.json` and writes `reports/<GATE>_*.md` from the same numbers; nothing in a report is typed by hand |

`graphify god-nodes` (the code knowledge graph, 895 nodes at the last full build, AST-only, no API cost; navigation aid, never evidence) lists as the most connected nodes: `Model` (86 edges), `Codec` (69), `load_manifests()` (52), `CircuitFactory` (48), `resolve_backend()` (48), `stage_assemble()` (45), `references()` (44), `load_circuit()` (43), `md_table()` (42), `CodewordEmbedding` (38).

### 4.2 `scripts/`

- **Gate scripts**, one per gate: `gate_E1.py`, `gate_E2.py`, `gate_E3.py`, `gate_S1.py`, `gate_S2.py`, `gate_S2D.py`, `gate_S2D_idle.py`, `gate_S2D_levers.py`, `gate_S2_2x4.py`, `gate_S3.py`, `gate_H0.py` (analyses any counts directory), `gate_H0P.py`, `gate_H0_diag.py`, `gate_H0_model.py`, `gate_H0_kpilot.py`, `gate_H0_ddtest.py`, `gate_H0_2x2.py`, `gate_Q0P_2x3.py`, `gate_CF_traj.py`, `gate_K0_2x3_2x4.py` (the last one uncommitted). The laptop gates are `laptop_L2_qiskit_check.py` ... `laptop_L5_cudaq_check.py`.
- **Runner and status:** `run_gate.py` (runs a gate script, prints the status, on FAIL writes `validation/BLOCKED.md` listing the failing criteria, with `--push` commits and pushes on PASS), `check_package.py` (prints PACKAGE OK when everything is present), `update_status.py` (regenerates `validation/gates.md` and `reports/PROJECT_STATUS.md` from the JSON), `run_tests_no_pytest.py`, `make_amendment.py` (generates amendment 01 from the JSON; `--check-only` re-verifies every cited value).
- **IBM hardware tooling:** `ibm_account.py` (checks the stored key, never prints it), `h0_backends.py` (`resolve_backend`, `calibration_record`, `calibration_fingerprint` = rule D9), `h0_submit.py` (submit / retrieve split, dry run on `AerSimulator.from_backend(FakeFez)`, preflight, per-job `session.json`), `h0_qpu_time.py` (execution-time estimate from the target's durations), `h0_support_plan.py` (rule D3'), `h0_patch_select.py` (exhaustive embedding search scored by the idle-aware $f$), `h0_calwatch.py`, `h0_idle_model.py`, `h0_t2_override.py`, `h0_build_circuits.py`, `h0_compare_prep.py`, `h0_device_survey.py`, plus circuit builders `h0_diag_circuits.py`, `h0_kpilot_circuits.py`, `h0_ddtest_circuits.py`, `h0_2x2_circuits.py`.
- **Quantinuum tooling:** `quantinuum_account.py` (login via the Nexus token store; tokens never on a command line), `quantinuum_build_circuits.py`, `quantinuum_device_table.py` (device and cost table), `quantinuum_submit.py` (dry run, job bodies with `max_cost`), `quantinuum_stack_check.py`, `q0p_a6_phase_error_check.py`. Isolated virtual environment `~/.local/share/su2qc-quantinuum/venv` so the pinned qiskit stack in the `coding` conda environment is never touched (`data/quantinuum/stack_check_20261002.json` and `_after.json` show identical pins).
- **IonQ tooling:** only `ionq_2x3_feasibility.py` (published-specification arithmetic -> `data/ionq_2x3_feasibility_20261001.json`). The submission scripts and gates `I0P_2x3`, `I0P_2x4` named in `prompts/25` Part B have no script and no validation JSON in the repository today (not built; the Quantinuum route of `prompts/26` came first).
- **Other:** `cf_traj_2x2_arm.py`, `cf_trajectories.py` (Pauli-trajectory decomposition, gate CF_traj), `s2d_2x3_device_requirements.py`, `s2d_recall_at_predicted_f.py`, `s2_duration_compare.py`, `s2_duration_report.py`, `s2_escalation_experiments.py`, `s2_fixed_recall.py`, `s3_device_model.py`, `report_circuit_structure.py`, `ionq_2x3_feasibility.py`, `ci_request.sh`, `ci_check.sh`, `ci_smoke.py`.

### 4.3 The gate system

A **gate** is a script whose result is written to `validation/<GATE>.json` with `"status": "PASS"|"FAIL"` and a list of criteria (`name`, `value`, `threshold`, `passed`), plus a generated report `reports/<GATE>_*.md`. Rule 1 of `CLAUDE.md`: "a gate passes only when its script writes status PASS, not when the prose says so"; every number in prose must come from `validation/*.json` or `data/*.json`. The 43 JSON files in `validation/` were enumerated with a short python snippet; 38 of them are gate results with a criteria list, 4 are CI result files (`ci_gate_L4`, `ci_gate_S3`, `ci_gate_S2_2x4`, `ci_smoke`) and 1 is the GPU stage record `S2_2x4_gpu.json` (Section 5).

Two kinds of gate (the project's wording):
- **Validation gates** (E1-E3, S1, CS, L2, L5, ...): PASS means the code reproduces an independently known answer.
- **Measurement gates** (S2_2x4, S2D_levers, H0_kpilot, H0_ddtest, H0_2x2, Q0P_2x3, CF_traj, ...): PASS means "preregistered, measured, verified, consistent", never "the number is good". The measured number is reported as the result.

**Preregistration**: the circuits, shot counts, decision rule and prediction are written to a committed file *before* the device data exist. **Calibration fingerprint (rule D9)**: a sha256 over the calibration-record content the prediction actually reads (30 qubit and 54 edge blocks on the IBM patch); submission is allowed only when the live fingerprint equals the preregistered one, and it is recorded again at retrieval. **Dry runs** on a simulator precede every hardware submission (`H0_dryrun`, `H0_kpilot_dryrun`, `H0_ddtest_dryrun`, `H0_2x2_dryrun`, `H0_diag_dryrun`). **Rules that make the record honest**: preregistered records are never rewritten (a correction is a new gate); no tolerance is changed after the fact; the 30-minute rule (below); QPU spend only with the owner's explicit go.

**The 30-minute rule** (`CLAUDE.md` rule 4): on the laptop (Intel i7-8750H, 6 cores / 12 threads, 62 GiB RAM since 2026-09-30, GTX 1060 Max-Q 6 GB with no usable local GPU because CUDA-Q's `nvidia` target needs compute capability $\ge7.0$ and the GPU has 6.1, and `qiskit-aer-gpu` 0.15.1 is incompatible with qiskit 2.5.2), any run that exceeds 30 minutes must be re-parametrized (fewer shots, `--quick`, smaller sector) with the report stating what the laptop can do and what needs the RTX 3070 desktop, the Slurm GPU cluster or the QPU.

### 4.4 Agents and model routing

From `prompts/ROUTING.md` and `.claude/agents/*.md` (Claude models; names are the project's):

| agent | model / effort | job |
|---|---|---|
| `planner-fable` | Fable 5.1, `high` (raised to `max` only for a blocked gate or a hard physics decision; owner decision 2026-10-01) | writes `prompts/NN_*.md`, decides, diagnoses blocked gates, owns the numerical plans and preregistrations |
| `executor-opus` | Opus 5.5, `high` | implements the current prompt, runs the gate, appends the outcome to `prompts/LOG.md` |
| `reviewer-opus` | Opus, `medium` | independent audit of JSON vs report vs code (never re-derives the physics) |
| `runner-sonnet` | Sonnet, `low` | runs gates, tests, transpilations; never edits source |
| `scribe-haiku` | Haiku, `low` | formats reports, updates `reports/PROJECT_STATUS.md` and `validation/gates.md`; never changes numbers |

The loop: planner writes a prompt, runner executes the gate, reviewer audits, `run_gate.py --push` on PASS; on FAIL the planner is invoked with `prompts/ESCALATION_TEMPLATE.md`. `prompts/LOG.md` is the execution log (126 lines; all outcomes with commit hashes). The numbered prompts 00-30 are listed in Section 6 with their titles. The coordinator session (the main Claude session) briefs agents, never writes production code, and is the only one that commits; there is also an auto-memory and a `gate` skill (`/gate <GATE> [--push]`).

### 4.5 The Perlmutter GPU CI loop

Source: `CLAUDE.md` ("skqd-ci" section), `SKQD-CI-SETUP.md`, `ci/README.md`, `RUNBOOK.md` ("Engine and HPC policy", owner 2026-09-21).

Perlmutter (the NERSC supercomputer, account `m4135_g`) **has no login from this project** (no ssh). It pulls the repository every hour at 07 minutes UTC, reads `ci/request.txt`, and runs *at most one allowlisted job*, then pushes the result back (`ci/status.json`, `validation/ci_gate_<TOKEN>.json`, `reports/ci-<jobid>.out`). Loop: commit and push, `scripts/ci_request.sh <TOKEN>`, poll `scripts/ci_check.sh` (not more than every 15 minutes; exit 0 done, 2 pending, 3 refused), read the JSON. Tokens: `smoke E1 E2 E3 S1 L1 L2 L3 L4 L5` originally, with `S3 04:00:00 1`, `H0P 01:00:00 1` and `S2_2x4` added by the owner on the Perlmutter side. Limits (enforced there, not changeable from the repository): one job at a time, at most 6 jobs per UTC day, 15-60 minutes walltime per token (S3 up to 4 hours), 1 GPU (an A100-SXM4-80GB, 81 920 MiB), at most 3 requests in a row without a pass before a `BLOCKED_<gate>` note. **Never** edit `ci/status.json`, `ci/poll.sh`, `reports/ci-*.out`, `validation/ci_*.json`.

**Engine policy** (`RUNBOOK.md`): exact numpy/scipy for E1-E3 and S1; Qiskit + Aer-GPU for the hardware-matching gates (L2, L3, L4, S2/S2D, S3, H0/H0P), with the code required to run on qiskit 1.4.3 and qiskit-aer-gpu 0.15.1 (the laptop has qiskit 2.5.2, aer 0.17.2, so gate modules are kept free of qiskit imports at load time); CUDA-Q 0.16 (target `nvidia`) for gate-level validation. Parallelise only along $k$, sector, $g^2$, lattice, shot batch, seed or resample; every GPU job records wall time, per-phase timings, GPUs, s/shot, peak GPU memory and mean GPU utilization in its JSON; more GPUs are proposed only with measured parallel efficiency $E(p)=T_1/(pT_p)\ge0.7$.

**CI jobs actually run** (from `validation/ci_*.json` and `prompts/LOG.md`): smoke job 58717267 (pass; A100 and `qiskit_aer_gpu` True); L4 job 58737320 (FAIL, GPU out-of-memory crash, 608 s; fixed by `shot_chunk_for` plus adaptive halving), L4 job 58741899 (PASS, 686 s, code sha `79f4dae`), S3 calibration job 58771538 (PASS, 255 s, code sha `ea600be`), S2_2x4 job 59162991 (PASS, 99 s, code sha `870d0c4`). Details in Section 6.

### 4.6 Repository bookkeeping directories

`validation/` (gate JSONs, `gates.md`, ignored `BLOCKED.md`), `reports/` (generated gate reports and the planner's analyses), `data/` (reference numbers, hardware raw counts under `data/hardware/`, calibration records, frozen circuits as QPY files, owner decisions), `prompts/` (every plan, numbered; `LOG.md`), `proposal/` (the manual, amendment 01, the Quantinuum access draft), `tests/` (pytest; last recorded totals: `coding` environment 270 passed / 19 skipped and the Quantinuum venv 287 passed / 2 skipped, `validation/Q0P_2x3.json` criterion Q7, with 287 passed / 19 skipped recorded in `prompts/LOG.md` row 2026-10-05 for commit 749fe3c), `scratch/planner/` (the planner's prototypes whose numbers are "planner arithmetic" until a gate reproduces them), `slurm/`, `jobs/`, `ci/`.

## 5. The full gate table

Source: every `validation/*.json` (enumerated with a python snippet that reads `status`, `criteria[*].passed`, `environment.timestamp`, `environment.git_commit`, `runtime_s`), `validation/gates.md` (generated 2026-10-03; it does not yet contain the rows `CF_traj`, `K0_2x3_2x4`, `H0P_repro`, `H0_*_dryrun`, `L4_p2_*`, `S2_fixed`, `S2D_idle`; they are added here from their JSON files). Column "kind": *validation* = PASS means a known answer is reproduced; *measurement* = PASS means "preregistered, measured, verified, consistent" and the measured number is the result (Section 4.3). The date/time is the string recorded in the JSON `environment.timestamp` in whatever time zone the run used (MDT, PDT or UTC). "Criteria" is passed/total. The commit is the repository commit at the time the gate ran (`n/a` where the run was on the Perlmutter CI snapshot).

### 5.1 Gate results (38 gate JSON files with criteria lists)

| gate | file | date, time as recorded | status | criteria | kind | runtime | commit | one-line meaning | key numbers (source in the file named) |
|---|---|---|---|---|---|---|---|---|---|
| `E1` | `validation/E1.json` | 2026-09-14 16:43:44 MDT | PASS | 23/23 | validation | 427 s | 57b3bff | Gauss law and the two independent Hamiltonian builders (2x2) | $\max|[G_a(x),H]|=0.0$ in the 160 000-dim redundant space; kernel dimension 82; sector split $\{2B:\dim\}=\{-4{:}2,-2{:}20,0{:}38,2{:}20,4{:}2\}$; $\max|{\rm eig}(P^\dagger HP)-{\rm eig}(H_{\rm dressed})|=2.309\times10^{-14}$ over 82 levels (threshold $10^{-12}$); element-wise $3.55\times10^{-15}$; link covariance $1.1\times10^{-16}$ |
| `E2` | `validation/E2.json` | 2026-09-14 16:44:00 MDT | PASS | 51/51 | validation | 15 s | 57b3bff | State counts (Table 2), vertex tables, codewords, decoder | 82 / 1 727 / 37 165 states at 2x2 / 2x3 / 2x4; 82/82 round trip at 2x2 (113/113 with a static pair); 2x3 sector dims $\{0{:}677,\pm2{:}426,\pm4{:}95,\pm6{:}4\}$ in the $2B$ key; random-string acceptance 0.15 % at 2x3 (0.242 % for static $[0,4]$) |
| `E3` | `validation/E3.json` | 2026-09-14 16:44:36 MDT | PASS | 85/85 | validation | 36 s | 57b3bff | Exact references (Table 1), static sectors, derived quantities, $\Delta t$ per sector | all Table 1 rows to 4 decimals (e.g. 2x2 $B{=}0$ $E_0=-3.6408$, $\pi/W=0.245$); 2x3 $V(2)=2.5898$; 2x4 $M_B=1.7851$; 2x2 $j_{\max}=1$ gives 152 states |
| `S1` | `validation/S1.json` | 2026-09-14 16:48:20 MDT | PASS | 12/12 | validation | 223 s | 57b3bff | Emulated support recall, certification and size-matched controls (2x3, 2x4) | 2x3 $B{=}0$ recall of the 99.9 % support $=1.0$ and $B{=}1$ $0.989$ at $f=0.1$, $2\times10^5$ shots (threshold 0.9); $E_0$ inside the Weinstein interval; $M_B$ interval $[1.6935,1.8314]\ni1.7765$; ridge Spearman 0.862 / 0.888; CIPSI within 3x of the oracle at $|B|=160,320$; 2x4 proxy recall $0.934$ (threshold 0.85) |
| `CS` | `validation/CS.json` | 2026-09-14 21:37:07 UTC | PASS | 4/4 | validation | 4 s | 3c32216 | Structure of the Hamiltonian terms in codeword space (input to S2) | 2x2 plaquette: one partner per state; 4 distinct pair amplitudes; structured plaquette gate vs dense exponential $3.97\times10^{-16}$; 30 CNOT (8 parity + 6 ladder + 16 UCRz) |
| `S2` | `validation/S2.json` | 2026-09-15 15:12:59 MDT | FAIL | 3/5 | measurement | 436 s | 5d60461 | Structured basic-gate circuits (hopping chains, interior-corner plaquettes) and their CZ cost | FAIL on the cost criteria only: 2x2 routed 618 CZ (budget $\le250$), 2x3 routed 5 477 (budget $\le500$); exactness $1.87\times10^{-14}$ and leakage $4.5\times10^{-14}$ pass |
| `S2_fixed` | `validation/S2_fixed.json` | 2026-09-15 20:18:31 MDT | FAIL | 5/9 | measurement | 301 s | 2fbcf29 | Fixed-angle generator (same codeword pairs, one angle per flip pattern): cost floor, leakage, recall | FAIL: 2x2 671 routed (heavy-hex) / 474 (square grid), 2x3 3 736 / 2 803, all above budget; recall kept (B=0 1.000, B=1 0.937 at $f=0.1$, `data/S2_fixed_recall.json`); not adopted |
| `S2D` | `validation/S2D.json` | 2026-09-16 07:02:12 MDT | FAIL | 6/8 | measurement | 213 s | 89102d2 | Device-resolved budget: 2x2 on Heron (FakeFez snapshot) and 2x3 on an all-to-all RZZ device at declared $\epsilon_2=10^{-3}$ | FAIL 6/8: 2x2 mean $f=0.1248$, worst $0.1166$ (pass); 2x3 mean $f=0.0534$ (needs $\ge0.1$: fail), worst $0.0532$; 2x3 shots per sector 4 605 472 vs quota $2\times10^5$ (fail); reproduces 618 routed and 2 164 all-to-all CZ |
| `S2D_idle` | `validation/S2D_idle.json` | 2026-09-22 16:36:34 MDT | FAIL | 6/15 | measurement | 406 s | 2c6edb6 | S2D re-evaluated on the idle-aware $f$ (scheduled circuit) at both ends of the $T_2$ bracket | FAIL 6/15: live ibm_fez, echo $T_2$: mean $f=6.708\times10^{-3}$, worst $1.542\times10^{-3}$; measured $T_2^*$: mean $1.298\times10^{-5}$; most favourable point of the bracket (DD perfect) mean $0.0623<0.1$. **Withdraws the 2x2/Heron S2D PASS as a hardware statement.** Hardware anchor V5: predicted 30.8 vs measured 35 accepted of 2 000 (ratio 1.135) |
| `S2D_levers` | `validation/S2D_levers.json` | 2026-10-02 11:13:55 MDT | PASS | 9/9 | measurement | 489 s | 782580c | 2x2 duration levers on ibm_kingston: compile/schedule levers, $f$ predicted at both $T_2$ ends, $r_{\rm crit}$ | PASS 9/9: best row duration 0.710x the as-is canary; Aer $f_{\rm clean}$ 0.2170 (echo end) and 0.0312 (ratio 0.174) for the signed family with ALAP; $r_{\rm crit}(0.1)\approx0.329$ (C6 scoped to $p_{\rm ref}\ge0.5$ by planner ruling) |
| `S2_2x4` | `validation/S2_2x4.json` | 2026-10-01 09:15:29 PDT | PASS | 12/12 | measurement | 0 s | n/a | 2x4 coarse step compiled to exact circuits, verified, measured (counts, duration, idle budget, $T_2/t_{2q}$) | PASS 12/12: exactness $3.4\times10^{-14}$; leakage of the transpiled 28-qubit circuit $1.10\times10^{-12}$ (GPU job 59162991); 69 688 CZ all-to-all, 148 726 routed; $T_2/t_{2q}=638\,742$ required vs Heron harmonic mean 1 038 (`reports/S2_2x4_compilation_and_device_requirement.md`) |
| `S3_smoke` | `validation/S3_smoke.json` | 2026-09-16 11:46:01 MDT | FAIL | 1/2 | measurement | 295 s | 1223e92 | S3 pipeline smoke test at 2x3 $B{=}1$ (2 shots per circuit) | FAIL by construction: recall 0.0737 at 24 shots (criterion $\ge0.9$); 295 s on laptop CPU; shows 10.42 s per shot at 2 shots per call |
| `S3` | `validation/S3.json` | 2026-09-22 18:01:22 PDT | PASS | 4/4 | measurement | 248 s | n/a | GPU throughput calibration of the 2x3 $B{=}0$ set (reduced size; recall criterion NOT evaluated) | PASS 4/4 as a calibration: 0.01987 s/shot at 20 qubits on one A100 (job 58771538) vs 3.198 s/shot on the laptop (161x); projected 1.10 h per $2\times10^5$-shot sector (4.41 h for four sectors) |
| `L2` | `validation/L2.json` | 2026-09-15 20:20:11 MDT | PASS | 4/4 | validation | 8 s | 0420211 | Qiskit circuits reproduce the numpy reference at 2x2 | max $|\text{Qiskit}-\text{reference}|=2.69\times10^{-14}$ over 35 circuits; 10 000/10 000 noiseless shots decode; TVD 0.0103 |
| `L3` | `validation/L3.json` | 2026-09-15 15:04:26 MDT | FAIL | 0/2 | measurement | 14 s | 5d60461 | Transpiled CZ counts of the dense 2x2 circuits (S2 baseline) | FAIL as expected: 35 606 CZ all-to-all, 55 459 routed (budget 250); led to the structured-gate work of S2 |
| `L4` | `validation/L4.json` | 2026-09-22 01:22:38 PDT | PASS | 4/4 | validation | 677 s | n/a | Aer noise-model sampling at 2x2 (S3 preparation); the current record is the GPU run | PASS 4/4 on the GPU at full production shots (job 58741899): yields 0.458 / 0.441 vs model 0.378 / 0.376 (ratios 1.21 / 1.17); $|B|=38/38$ and $20/20$; recall 1.000; 19.8x faster than the laptop. The two earlier laptop records are in `L4_p2_*.json` |
| `L4_p2_1e-3` | `validation/L4_p2_1e-3.json` | 2026-09-14 18:24:06 MDT | FAIL | 2/4 | validation | 1012 s | 30684f2 | L4 laptop record at $p_2=10^{-3}$ (reduced shots, 2026-09-14) | FAIL 2/4: yield criterion only ($f=(1-p_2)^{35670}\approx0$); Weinstein criteria pass; 1 012 s |
| `L4_p2_3e-3` | `validation/L4_p2_3e-3.json` | 2026-09-14 18:00:36 MDT | FAIL | 2/4 | validation | 1376 s | 30684f2 | L4 laptop record at $p_2=3\times10^{-3}$ (reduced shots, 2026-09-14) | FAIL 2/4: same cause; 1 376 s |
| `L4_fez` | `validation/L4_fez.json` | 2026-09-16 12:28:26 MDT | PASS | 4/4 | validation | 450 s | 3722018 | L4 with `NoiseModel.from_backend(FakeFez)` (H0 rehearsal) | PASS 4/4: measured yield 0.147 / 0.136 vs model 0.112 / 0.104 (ratios 1.32 / 1.31); recall 1.000; $E_0$ inside both Weinstein intervals |
| `L5` | `validation/L5.json` | 2026-09-15 20:19:58 MDT | PASS | 6/6 | validation | 3 s | 0420211 | CUDA-Q circuits vs the numpy reference at 2x2 (CPU target `qpp-cpu`) | PASS 6/6: TVD 0.0091; endianness test; IR gate coverage TVD 0.019; the `nvidia` target needs compute capability $\ge7.0$ |
| `H0P` | `validation/H0P.json` | 2026-09-16 13:15:46 MDT | PASS | 16/16 | validation | 1179 s | 2392fb3 | H0 preparation on the FakeFez snapshot: 84 frozen circuits, yield by repetition, confusion, Ritz consistency | PASS 16/16 after the yield model gained the term $(1-f)a$: leakage $1.49\times10^{-14}$ over 84 circuits; simulated/model yield ratios 1.34 / 1.75 / 1.53 ($B{=}0$, $r{=}1,2,3$) and 1.30 / 1.54 / 1.59 ($B{=}1$); confusion min diagonal 0.9768 |
| `H0P_rehearsal` | `validation/H0P_rehearsal.json` | 2026-09-21 17:57:49 MDT | PASS | 18/18 | validation | 175 s | 1e5c03b | H0P on FakeFez with the D3' shot plan through the sampling cache | PASS 18/18: supports 38/38 and 20/20, `missing_states==[]`, r=1 yields 0.1489 / 0.1371 |
| `H0P_repro` | `validation/H0P_repro.json` | 2026-09-30 15:28:44 MDT | PASS | 15/15 | validation | 1741 s | 6180c6a | H0P reproducibility run (15 criteria, identical to H0P) | PASS 15/15; "H0P_repro identical" |
| `H0P_ibm_fez` | `validation/H0P_ibm_fez.json` | 2026-09-22 11:46:55 MDT | PASS | 18/18 | validation | 319 s | 1e6d7d3 | H0P re-predicted on the live ibm_fez calibration (D3' plan; last PASS at stamp 20260922T1400Z) | PASS 18/18 (calibration run, throughput only): supports 38/38 and 20/20; $N_4=6900$ ($B{=}0$) / 16 800 ($B{=}1$); first attempt on 2026-09-21 FAILED 15/16 (criterion 3 premise was a coin flip, `reports/H0P_ibm_fez_escalation_20260921.md`) |
| `H0_dryrun` | `validation/H0_dryrun.json` | 2026-09-30 15:41:37 MDT | PASS | 9/9 | validation | 10 s | 6180c6a | Gate H0 run on SamplerV2 dry-run counts (FakeFez) | PASS 9/9: 58/58 accepted strings re-encode; measured $f$ 0.1710 vs predicted 0.1727 ($B{=}0$) |
| `H0_canary` | `validation/H0_canary.json` | 2026-09-30 15:41:49 MDT | FAIL | 3/6 | measurement | 11 s | 6180c6a | The 3-pub canary on ibm_fez (go rule before the main submission) | FAIL 3/6 = canary NO-GO: 8 accepted of 267 vs the preregistered $\ge10$ and simulated 71; yield-inverted $f=0.0255$ vs predicted 0.2195; $B{=}0$ energy not reproduced (support 8 of 38); readout drift ratio 3.516 (limit 3) |
| `H0_diag_dryrun` | `validation/H0_diag_dryrun.json` | 2026-09-22 14:16:46 MDT | FAIL | 6/7 | measurement | 1 s | 9cfe3ec | H0_diag on the simulator (path check) | FAIL 6/7: C5 only (post-diction vs simulator sample); path check |
| `H0_diag` | `validation/H0_diag.json` | 2026-09-22 14:46:44 MDT | FAIL | 6/8 | measurement | 1 s | 4d1e8f6 | Diagnostic session on ibm_fez: DD x twirling factorial and windowed $T_1$ / Ramsey | FAIL 6/8 but decisive on its question: J1 (both options off) 35 accepted of 2 000 vs preregistered 30.8 $\pm$ 5.5 (idle relaxation) and 374.5 $\pm$ 17.4 (options hypothesis): options exonerated; C5 post-diction misses by 88.6x / 12.0x (the bound over-charges); 15.0 s of QPU time |
| `H0_model` | `validation/H0_model.json` | 2026-09-30 15:31:18 MDT | PASS | 5/5 | measurement | 2 s | 6180c6a | Post-diction of the fez counts by scheduled Aer at both ends of the $T_2$ bracket; clean-yield statistic | PASS 5/5: 6 reference hits vs 2.018 from garbage ($P=0.0172$); at the measured $T_2^*$ predicted/measured clean count 1.0503, at the echo $T_2$ 49.58; acceptance structure ratio 0.8643 |
| `H0_kpilot_dryrun` | `validation/H0_kpilot_dryrun.json` | 2026-10-02 12:04:30 MDT | PASS | 9/9 | measurement | 49 s | 761369f | Kingston pilot dry run on FakeKingston | PASS 9/9 after the K3 ruling (`prompts/21a`) |
| `H0_kpilot` | `validation/H0_kpilot.json` | 2026-10-02 12:31:53 MDT | FAIL | 8/9 | measurement | 450 s | fc3a5a2 | ibm_kingston pilot: windowed Ramsey, $T_1$, direct $f_{\rm clean}$ of the signed $k{=}1$ circuits; GO/NO-GO | FAIL 8/9 (K5: $T_2^*$ resolved on 9/12 qubits, 10 required), **decision NO-GO**: pooled $f=0.0413$, 95 % [0.0361, 0.0470]; $r_{\rm eff}=0.0974$ vs $r_{\rm crit}=0.3285$; 12.0 s QPU |
| `H0_ddtest_dryrun` | `validation/H0_ddtest_dryrun.json` | 2026-10-02 14:10:22 MDT | PASS | 8/8 | measurement | 15 s | aa4da1e | DD A/B test dry run | PASS 8/8 (path check; simulator cannot predict DD gains) |
| `H0_ddtest` | `validation/H0_ddtest.json` | 2026-10-02 14:37:48 MDT | PASS | 8/8 | measurement | 601 s | d4b3855 | One-job A/B test of client-side DD vs no DD on the pilot's two $k{=}1$ circuits; adoption by preregistered ratio rule | PASS 8/8: T0 (no DD) $f=0.0400$ [0.0358, 0.0446]; T1 context-aware 0.0005 ($R=0.012$); T2 XY4 everywhere 0.1118 ($R=2.793$); **T3 XY4 in windows $\ge1\,\mu$s adopted: $f=0.1129$ [0.1058, 0.1203], $R=2.819$ [2.495, 3.185]**; 20.0 s QPU |
| `H0_2x2_dryrun` | `validation/H0_2x2_dryrun.json` | 2026-10-02 15:04:52 MDT | PASS | 8/8 | measurement | 17 s | 4e979a0 | Full 2x2 run dry run | PASS 8/8 |
| `H0_2x2` | `validation/H0_2x2.json` | 2026-10-02 16:04:51 MDT | PASS | 8/8 | measurement | 444 s | da715fc | The full 2x2 SKQD run on ibm_kingston below the signed budget (owner decision 2026-10-02) | PASS 8/8: pooled $f$ (7 $k{=}1$ circuits) 0.1271 [0.1084, 0.1479]; 133 907 coarse shots; $B_{\rm sig}$ 35/38 and 19/20; $E_R-E_0=5.48\times10^{-4}$ ($B{=}0$) and $5.75\times10^{-6}$ ($B{=}1$); garbage-only reproduces $E_0$ in 100/100 seeds; 53.0 s QPU |
| `Q0P_2x3` | `validation/Q0P_2x3.json` | 2026-10-02 21:36:57 MDT | PASS | 7/7 | measurement | 926 s | 8072b8d | Signed 2x3 circuits compiled to the Quantinuum native gate set, verified, costed, packaged (Stage A; Stage E/P not run) | PASS 7/7: 44 frozen circuits, max $|\Delta\psi|=2.09\times10^{-13}$, 2 158 ZZPhase on all 44, mean 4.9666 HQC/shot; H2-2 gate-only $f=0.1502$, Helios-1 0.1642; Stage E 11 936 eHQC, pilot 9 938 HQC (later re-planned); 0 HQC spent |
| `CF_traj` | `validation/CF_traj.json` | 2026-10-05 13:47:33 MDT | PASS | 7/7 | measurement | 1201 s | a8ebbaa | Pauli-trajectory decomposition of the reference-hit excess and the near-clean correction $r_{nc}$ | PASS 7/7: trajectory prediction 63.46 $\pm$ 2.254 vs 64 observed hits ($P=0.9794$); $r_{nc}=1.115$; floor theorem holds on all four arms; $k{=}4$ mixture bias 1.274 [1.170, 1.402] |
| `K0_2x3_2x4` | `validation/K0_2x3_2x4.json` | 2026-10-05 15:47:54 MDT | FAIL | 5/6 | measurement | 23 s | c29a402 | ibm_kingston readiness of 2x3 and 2x4 on the day's record (prompts/25 Part A) -- UNCOMMITTED, written by the K1 agent | FAIL 5/6 only because tests were skipped (`--skip-tests`); 2x3 routed 5 527 CZ (seed 6), $f_{\rm ceiling,2q}=1.095\times10^{-2}$, $f_{\rm gates,layout}=5.542\times10^{-6}$; $\epsilon_2$ needed for $f=0.05$ is $5.420\times10^{-4}$ vs best edge $8.164\times10^{-4}$; 2x4 ceiling $\log_{10}f=-52.8$; verdict: no record meets 0.1 / 0.05 |

**Reading the failures.** The FAIL rows are of four kinds and none is a hidden defect: (1) *cost gates that were deliberately re-defined* (S2, S2_fixed, S2D, L3): the manual's gate-count budget was replaced by the amended device-resolved budget; (2) *calibration/measurement gates whose FAIL records an honest negative physics result* (H0_canary, H0_kpilot, S2D_idle): the canary gave 8 accepted shots against a simulated 71; the pilot measured $f=0.0413$ against the bar 0.1; (3) *diagnostic gates failing one prediction-comparison criterion while answering their own question* (H0_diag); (4) *by-construction* or *tests-skipped* failures (S3_smoke at 2 shots per circuit, K0_2x3_2x4 with `--skip-tests`, the two early laptop L4 records). Records are never rewritten; a corrected analysis is a new gate (e.g. S2D_idle supersedes the 2x2 reading of S2D, H0_model supersedes the reading of H0_canary).

### 5.2 Gates that are still open (no JSON; from `validation/gates.md`)

| gate | check (manual Step 10) | runs on | status today |
|---|---|---|---|
| H0 | 2x2 hardware: decoder validity, bit order, parity checks; measured $f$ within 30 % of the model | QPU | open as a gate; its role was realised by the measurement gates `H0_canary`, `H0_diag`, `H0_kpilot`, `H0_ddtest`, `H0_2x2` (the "within 30 % of the model" criterion was read measurement-to-measurement, because the model was 5.1x off in the pilot) |
| H1 | 2x3 $B{=}0$: certified interval of width $\le0.1$ containing the exact $E_0$; recall $\ge0.8$ | QPU | open (no 2x3 hardware data exist) |
| H2 | 2x3 $B{=}1$: cluster energy certified to $\pm r_H\le0.15$; $V(1)$, $V(2)$ intervals containing exact values | QPU | open |
| P1 | primary-endpoint curves with bootstrap bands | laptop | open (needs 2x3 hardware data) |
| M1 | ML uses credited only under Step 7.5 | desktop GPU | open |

### 5.3 Other result files in `validation/`

| file | content | key numbers |
|---|---|---|
| `validation/S2_2x4_gpu.json` | the GPU stage of gate S2_2x4 on Perlmutter (no `status` field) | job 59162991, leakage of the transpiled 2x4 circuit $1.10\times10^{-12}$; Aer statevector 64.9 s of an 88 s stage, 99 s for the whole job; peak GPU memory 4 557 MiB, mean utilisation 60 % (`prompts/LOG.md`) |
| `validation/ci_gate_L4.json` | CI wrapper for L4 | exit 0, pass True, 686 s, job 58741899, code sha `79f4dae` |
| `validation/ci_gate_S3.json` | CI wrapper for S3 | exit 0, pass True, 255 s, job 58771538, code sha `ea600be` |
| `validation/ci_gate_S2_2x4.json` | CI wrapper for S2_2x4 | exit 0, pass True, 99 s, job 59162991, code sha `870d0c4` |
| `validation/ci_smoke.json` | CI smoke job | job 58717267, device GPU, pass True |
| `validation/BLOCKED.md` | local (gitignored) list of the open STOP questions | not read as evidence |

### 5.4 Totals

Counting the 38 gate JSON files above: PASS 25, FAIL 13 **(sum of sourced statuses; counted by the python snippet)**. A machine-readable version of the table with dates is Appendix block (a).

## 6. The chronological history

*(section still to be written)*

## 7. Hardware ledger

*(section still to be written)*

## 8. What was learnt

*(section still to be written)*

## 9. Where we are now and where we are heading

*(section still to be written)*

## 10. Progress measure

*(section still to be written)*

## 11. DATA APPENDIX for plotting

*(section still to be written)*

## 12. Glossary

*(section still to be written)*

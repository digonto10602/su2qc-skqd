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

Sources: `prompts/LOG.md` (the execution log, every row cited with its commit), `reports/SESSION_HANDOVER_20260921_24.md`, `reports/SESSION_HANDOVER_20260925_1002.md`, `CLAUDE.md` ("Current status"), `reports/H0_2x2_full_hardware_report_20261002.md`, the gate JSONs named in each item. Each item gives: date, what was done, numbers, verdict, QPU seconds. "QPU s = 0" means no quantum computer was used.

### 6.0 The prompts (the plans in force), by number and title

The project's own scheme: the planner agent writes numbered prompt files `prompts/NN_slug.md`; the executor follows the newest prompt for its step. Titles (first line of each file):

| no. | title |
|---|---|
| 00 | Bootstrap: check the package, create the public GitHub repository, push |
| 01 | L1: reproduce the cloud-verified gates on the laptop |
| 02 | L2: Qiskit circuits reproduce the numpy reference (2x2, 12 qubits) |
| 03 | L3: transpiled CZ counts of the exact circuits (measurement for gate S2) |
| 04 | L4: Aer noise-model sampling at 2x2 (gate S3 preparation) |
| 05 | L5: CUDA-Q version of the 2x2 circuits on the GTX 1060 Max-Q |
| 06 | S2-b: structured hopping gates and interior-corner plaquette gates within the CZ budget |
| 07 | H0: first QPU session, 2x2 calibration run (12 qubits) |
| 08 | One-month plan to H1/H2 (2x3 hardware spectroscopy) with the gate table |
| 09 | L4 fix (2026-09-14): honour the 30-minute rule when the circuits carry about 35 000 CZ |
| 10 | L5 fix (2026-09-14): CUDA-Q 0.15.1 `SampleResult` API in the convention tests |
| 11 | S2 planner decision (2026-09-15): the exact coarse step cannot meet the CZ budget in this encoding; measure the floor, then the owner decides |
| 12 | Combined plan: 2x2 on Heron, 2x3 exact circuits on an all-to-all device; device-resolved budgets, shot rule, S3 preparation |
| 13 | H0 preparation on Heron (gate H0P) and the S3 desktop job |
| 14 | H0P fix (2026-09-16): the yield model must include the manual's garbage-acceptance term |
| 15 | H0: first QPU session on ibm_fez (2x2 calibration run, manual Step 9.1, gate H0) |
| 16 | H0P_ibm_fez fix (2026-09-21): the shot plan must guarantee the saturation that criterion 3 presupposes |
| 17 | H0 submission window (2026-09-22): the preflight must test the calibration CONTENT of the frozen patch, not its timestamp |
| 18 | Proposed GPU allowlist lines for S3 and H0P (owner action on Perlmutter) |
| 19 | H0 canary NO-GO: diagnostic session on ibm_fez (idle-time model, DD/twirling factorial) |
| 20 | H0 re-plan: the clean-yield statistic, the scheduled-Aer prediction at both ends of the $T_2$ bracket, the post-diction gate H0_model, and the free device survey |
| 21a | Ruling on the Part-D STOP of prompts/21: the dry-run K3 on the FakeKingston snapshot |
| 21 | The ibm_kingston pilot: in-circuit $T_2^*/T_2^{\rm echo}$ on the selected patch and the direct $f_{\rm clean}$ of the best schedulable signed circuit (gate H0_kpilot); part 0 applies the C6 ruling to S2D_levers |
| 22 | 2x4: compile the coarse step to exact circuits, measure its duration and idle budget, derive the device requirement |
| 23 | 2x2 on IBM: measure the duration levers and decide what the signed $f\ge0.1$ criterion needs |
| 24 | IBM 2x2 inside the 571 s: Stage T (dynamical-decoupling A/B test, gate H0_ddtest) and Stage R (the full 2x2 SKQD run, gate H0_2x2) |
| 25 | 2x3 and 2x4: the ibm_kingston readiness check (gate K0_2x3_2x4) and the IonQ preparation (gates I0P_2x3, I0P_2x4) |
| 26 | The signed 2x3 circuits for Quantinuum H2-2 / Helios-1 (gate Q0P_2x3): native compilation, exact verification, emulator and submission path, cost sheet |
| 27 | A substantial 2x3 result: the staged plan (simulator stages first, then the device question) |
| 28 | The 2x3 shot rule (D3'-R) and the clean-fraction estimator: decisive trajectory test, tail-class statistic, Stage E / P GO rule, 2x2 information block |
| 29 | Re-ruling after the CF_traj STOP ($\rho_T>1.5$): the ideal-sample fraction $f_{\rm ideal}$, the corrected reference-hit statistic, completion of CF_traj, and the amended Part B of prompts/28 |
| 30 | Energy-convergence and weighted-coverage criteria for the 2x3 plan check (owner decision 2a, 2026-10-05) |

Also in `prompts/`: `README.md` (format), `ROUTING.md` (model routing), `ESCALATION_TEMPLATE.md`, `LOG.md`, and `low_clean_fraction_techniques.md` (the owner's literature catalogue of techniques that raise the clean fraction).

### 6.1 2026-09-14: the exact references (E1, E2, E3), S1 and CS; package bootstrap

*What.* The package was assembled in a cloud sandbox (Fable 5.1 session); Qiskit and CUDA-Q could not be installed there so only the numpy gates ran. Gates E1, E2, E3, S1 and CS all PASS (criteria 23, 51, 85, 12 and 4; Section 5). An independent audit (Opus reviewer, rebuilding the 2x2 in the 160 000-dimensional space) confirmed the physics and found fixes (CUDA-Q kernel via a real source file plus an endianness test, saturation marking in Table 3, a Kato-Temple denominator guard, CIPSI denominator magnitude, a locality check). `prompts/00`: package check, the public GitHub repository created and pushed (`https://github.com/digonto10602/su2qc-skqd`), CI run green, 14 tests passed. `prompts/01` (L1): the four gates were reproduced on the laptop (runtimes E1 427 s, E2 15 s, E3 36 s, S1 223 s; cloud 104 / 8 / 13 / 75 s); E1-E3 criteria identical to the cloud copies, S1 differs in one value only (ridge Spearman $B{=}0$: 0.862 laptop vs 0.861 cloud, threshold >0.7).
*Numbers.* The manual's Tables 1-4 are reproduced from scratch (README: "it reproduces every number of the manual's Tables 1-4"); $E_0^{2\times2,B=0}=-3.6407665507$; two builders agree to $2.3\times10^{-14}$.
*Verdict.* PASS (E1, E2, E3, S1, CS). *QPU s = 0.*

### 6.2 2026-09-14/15: the circuit layer and the laptop gates L2-L5

*L2* (`prompts/02`): Qiskit circuits reproduce the numpy reference, max deviation $3.7\times10^{-15}$ over 35 circuits in the first run (the current JSON records $2.69\times10^{-14}$), 10 000/10 000 noiseless shots decode, TVD 0.0103 (limit 0.272); CPU only (qiskit 2.5.2, aer 0.17.2; the aer-gpu wheel 0.15.1 is incompatible and was rolled back). *L3* (`prompts/03`): the dense circuits cost 35 606 CZ all-to-all and 55 459 routed on heavy-hex distance 3 against the budget of 250: FAIL as expected, the baseline for the S2 work. *L5* (`prompts/10`): CUDA-Q 0.15.1 on target `qpp-cpu`, PASS (runtime 3.6 s); the `nvidia` target aborts on the GTX 1060 Max-Q (compute capability 6.1 < 7.0). *L4* (`prompts/09`): two reduced laptop runs at $p_2=3\times10^{-3}$ (1 376 s) and $10^{-3}$ (1 012 s) FAIL the yield criterion only, because $f=(1-p_2)^{35670}$ is numerically zero for the dense circuits; both Weinstein criteria pass; noisy Aer costs 2-3.3 s per shot on this laptop so a full run would take about 7-14 h here. *QPU s = 0.*

### 6.3 2026-09-15: S2, the structured exact circuits; S2_fixed; the planner's decision (`prompts/06`, `prompts/11`)

*What.* `prompts/06` stage 1-3: the executor wrote a synthesis engine (`circuits_ir.structured_term_gates`: two-level Givens rotations per block, merged per flip pattern into Gray-code uniformly controlled rotations, control sets minimised by a search over non-codeword strings; for 2x3 the SVD of the off-diagonal part, giving real Ry rotations). 2x2 coarse step: 264 CZ at first, then 256 CZ all-to-all and 618 routed; 2x3: 2 164 all-to-all and 5 477 routed. Exactness $1.9\times10^{-14}$ (<$10^{-10}$), leakage $4.5\times10^{-14}$.
*Verdict.* Gate **S2 FAIL on the CZ budget only** (2x2 routed 618 vs $\le250$; 2x3 routed 5 477 vs $\le500$); the budget was not relaxed. The planner then (`prompts/11`, Fable at `max`) ran diagnostics (`data/S2_escalation_experiments.json`: no coupling map or term ablation reaches the budget) and asked for the floor of the *fixed-angle* alternative (same codeword pairs and validity controls, one angle per flip pattern). Result (`validation/S2_fixed.json`, `data/S2_fixed_recall*.json`): 240 / 671 / 474 CZ (all-to-all / heavy-hex / square) at 2x2 and 1 626 / 3 736 / 2 803 at 2x3; recall at $f=0.1$ kept (B=0 1.000, B=1 0.937) but the cost floor is far above budget: STOPPED as the prompt required. *Owner decision (2026-09-16):* a combined plan (2x2 on a Heron superconducting device, 2x3 exact circuits on an all-to-all ion-trap device; `prompts/12`).
*QPU s = 0.*

### 6.4 2026-09-16: S2D, L4_fez, H0P, H0_dryrun, S3_smoke (`prompts/12`, `13`, `14`)

*S2D (new gate; FAIL 6/8).* Device-resolved budgets for the exact circuits: 2x2 on the FakeFez snapshot: mean $f=0.1248$, worst $0.1166$ (663 CZ; passes $\ge0.1$ / $\ge0.05$); FakeTorino 0.0735 / 0.0569. 2x3 on an all-to-all RZZ device at *declared* inputs $\epsilon_2=10^{-3}$, $\epsilon_1=10^{-4}$, $\epsilon_{ro}=2\times10^{-3}$: 2 158 RZZ + 7 310 one-qubit gates give $f=0.1154\,(2q)\times0.4797\,(1q)\times0.9608\,(\text{ro})=0.0534$, worst 0.0532; the $\epsilon_2$ needed for $f=0.1$ at these counts is $7.1\times10^{-4}$ (with virtual $R_z$, $f=0.0817$, still <0.1). Shot rule (eq. (5), $p=10^{-3}$, $y=0.82f$): 2x3 $B{=}0$ 143 921 per circuit $\times32$ = 4.61e6, $B{=}1$ 1.72e6 per sector, against the manual's quota $2\times10^5$ per sector (FAIL); the manual itself is inconsistent: at its own design point $f=0.2$ eq. (5) already asks 1.69e6 per sector. A planner follow-up (`data/S2D_recall_at_f.json`) re-evaluated the S1 criterion at the S2D $f$: min recall 0.988 ($B{=}0$) / 0.958 ($B{=}1$) at $f=0.0534$ with $2\times10^5$ shots per sector.
*L4_fez (PASS 4/4).* Aer with `NoiseModel.from_backend(FakeFez)`: measured yield 0.1467 / 0.1356 vs model 0.1115 / 0.1038 (1.32 / 1.31), $|B|$ 38 / 20, recall 1.000.
*H0P* (preparation for the first hardware session): 84 frozen circuits (references $\times k=1..4\times r=1,2,3$ repetitions of the coarse step; plus 42 readout-calibration circuits), transpiled onto FakeFez; CZ per repetition 663 / 1 305 / 1 920; leakage $1.49\times10^{-14}$. First result (`prompts/13`) FAIL 3/16: the simulated yield was 3.0x / 8.3x / 5.6x the manual's $0.82f$ for $r=2$ ($B{=}0$) and $r=3$. Diagnosis: the decoder's false-acceptance floor, since a non-clean shot is still accepted whenever its string is a codeword of the target sector, with probability $a=0.00928$ ($B=0$) / $0.00488$ ($B=1$); the manual itself names the term ("plus the 0.15 % of garbage") but the gate scripts had omitted it. `prompts/14`: the model became $y=0.82f+(1-f)a$ (`skqd.yield_model`), after which all six simulated yields lie within 1.30-1.75x of the model; **H0P PASS 16/16**. Nothing was relaxed.
*H0_dryrun PASS 9/9* (the real analysis script run on simulator counts); *S3_smoke* (the S3 job script at 2x3, 2 shots per circuit, 295 s: FAIL by construction, 10.42 s per shot at 2 shots per call). *Amendment 01 draft* generated (91 cited values).
*QPU s = 0.*

### 6.5 2026-09-21: H0P_ibm_fez FAIL 15/16, the D3' shot plan (`prompts/15`, `16`)

*What.* `prompts/15` prepared the first real QPU session on `ibm_fez` (IBM Heron r2, 156 qubits, open plan with 600 s/month): part A built the live-backend resolution, the calibration record (`calibration_record`), the submit/retrieve split (every job id written before the next submit) and the QPU-time estimator (reproduces the planner's 46.7 s for 181 692 shots); the frozen circuits were rebuilt byte-identically (126/126). Part B recomputed the prediction on the day's live calibration (stamp 20260921T2053Z): gate **H0P_ibm_fez FAIL 15/16**; the one failing criterion: the $B{=}1$ decoded support was 19 of 20 (|E_R - E_0| = $5.749\times10^{-6}$), the missing state carrying $9.3\times10^{-7}$ of the ground-state weight. The executor held at the owner's stop point.
*Planner ruling (`prompts/16`, `reports/H0P_ibm_fez_escalation_20260921.md`).* The frozen shot plan (267/130/92 shots for $r=1/2/3$) saturates $B=0$ from clean shots with probability 0.0043 and $B=1$ with 0.0762, so the preregistered criterion 3 ($E_0$ reproduced to $10^{-6}$) was "a coin flip, not a measurement". Fix, **rule D3'** (new `scripts/h0_support_plan.py`): the $k=4$ circuits of each sector get $N_4$ = the smallest multiple of 100 such that every sector state has expected clean count $\ge\lambda^*=6.2958$ from the $r=1$ circuits at $0.7f_{\rm cal}$ (0.7 = the lower edge of the 30 % tolerance of criterion 2): $N_4=8200/19700$ on that day's calibration and 11 700/28 100 on FakeFez; two shot-plan criteria added to H0P (18 in all); session = 6 jobs of 21/5/2/28/28/42 pubs, 69.9 s of QPU execution (cap 120 s). Part A' rehearsal: **H0P_rehearsal PASS 18/18** on FakeFez with the new sampling cache (supports 38/38 and 20/20, `missing_states == []`). No criterion constant, tolerance or convention changed.
*QPU s = 0.* (Only read-only live metadata calls.)

### 6.6 2026-09-22: H0P_ibm_fez PASS 18/18, rule D9, and the first Perlmutter GPU runs (`prompts/16` part B', `17`, `18`)

*H0P_ibm_fez.* Re-run with the D3' plan: PASS 18/18 at calibration stamp 20260922T0711Z ($N_4=8100/19600$, supports 38/38 and 20/20, r=1 simulated yields 0.1707 / 0.1564, 69.69 s estimate). But `ibm_fez` recalibrated twice under the session and the preflight's exact-match guard on the `last_update_date` string refused a stale stamp each time; measured windows between recalibrations: 30 min 17 s, 36 min 8 s, 51 min 4 s, then more than 52 min. *Rule D9* (`prompts/17`): the preflight now tests the calibration **content** the prediction reads (sha256 of the 30 qubit x 9 and 54 edge x 4 values; the 84 live clean fractions equal to $10^{-9}$) instead of the timestamp; three stamp-only updates changed 0 of those numbers; the fingerprint fired on the one real recalibration (a readout recalibration of all 30 qubits, ratios 0.3735 to 2.6571, which moved $f$ of the $r=1$ circuits by only -0.68 % to +0.48 %).
*GPU runs (Perlmutter A100).* L4 job 58737320 crashed (GPU out-of-memory, 608 s: 20 circuits x 20 000 shots in one `run()` call); a memory-aware chunker (`shot_chunk_for`) and adaptive halving were added. L4 job 58741899 **PASS 4/4** (686 s; full production shots, 20 000 per circuit vs 8 / 22 on the laptop; yields 0.458 / 0.441 vs model 0.378 / 0.376; $|B|$ 38/38 and 20/20; recall 1.000): timing 0.00103 s/shot against the laptop's 0.02037 s/shot, a **19.8x speed-up**; peak GPU memory 27 915 MiB; mean GPU utilisation 15.3 % (max 27 %): not GPU-bound, so no second GPU is proposed; the allocation model underestimates memory by 3.5x (8.0 GB predicted, 27.9 GB measured). S3 calibration job 58771538 **PASS 4/4** (255 s job; 245 s gate): 0.01987 s/shot at 20 qubits vs 3.198 s/shot on the laptop (**161x**): a $2\times10^5$-shot sector is 1.10 h instead of 177.7 h; recall criterion not evaluated. `prompts/18` proposed the allowlist lines `S3 04:00:00 1` and `H0P 01:00:00 1` with the measured justification.
*QPU s = 0.*

### 6.7 2026-09-22: the ibm_fez canary (first QPU job) and its NO-GO

*What.* Job `dapbusac505c73chv0og` on `ibm_fez`, 2026-09-22 17:48:32 UTC: 3 pubs x 267 shots (one frozen $r=1$ circuit `B0_ref06_k1_rep1` of 663 CZ + the two readout pubs), runtime options XY4 dynamical decoupling on and Pauli twirling on. Calibration fingerprint equal at prediction and retrieval.
*Numbers.* 8 accepted of 267 shots against the preregistered go rule $\ge10$ (`validation/H0_canary.json -> data.f_comparison`: measured yield 0.02996, predicted yield 0.18725); yield-inverted $f=0.0255$ against the gate-only prediction $0.2195$ (relative deviation 0.884 against a tolerance 0.30). Bit-order test: 2 reference-string hits vs 0.07 from garbage ($z=7.6$). Readout error drift ratio 3.516 against a limit of 3.
*Verdict.* **Canary NO-GO**: gate H0_canary FAIL 3/6; the main 6-job submission was never run (`prompts/07` clause (b), `prompts/15` escalation B5). *QPU s = 2.0* (billed, `data/hardware/H0_ibm_fez_canary/session.json -> total_usage_s`).

### 6.8 2026-09-22: H0_diag, the idle-relaxation finding (`prompts/19`)

*What.* The planner's analysis (`reports/H0_canary_planner_analysis_20260922.md`) identified the cause by computation before spending hardware: neither prediction path knew how long the circuit takes. The canary circuit runs **43.71 $\mu$s at depth 1 328 for only 663 CZ** (nearly serial), each of the 12 qubits idling 19-42 $\mu$s; thermal relaxation over those windows is **3.323 error units** (S_T1 0.755, S_T2 2.568; qubit 146 with $T_2=16.0\ \mu$s alone 0.93) against the 2.15-2.36 missing from the prediction. Four jobs on `ibm_fez`, a $2\times2$ factorial of the frozen canary circuit: J1 (DD off, twirling off) `dapegkcak42c73cierv0` 5.0 s, J2 (XY4) `dapeh3318flc739m51e0` 4.0 s, J3 (twirl) `dapeh7ac505c73ci2o60` 3.0 s, J4 (both = the canary's own options) `dapehb4ak42c73cietig` 3.0 s (2026-09-22 20:42-20:44 UTC), 2 000 shots each, plus windowed $T_1$ and Ramsey pubs.
*Numbers.* The decisive count: J1 gave 35 accepted of 2 000, against the preregistered 30.8 $\pm$ 5.5 under hypothesis A (idle relaxation) and 374.5 $\pm$ 17.4 under hypothesis B (the sampler options caused the shortfall): B rejected at about 20 sigma. Factorial accepted counts 35 / 27 / 25 / 17 (J1 / J2 / J3 / J4; garbage floor 18.6); neither option helps. Windowed Ramsey: in-circuit $T_2^*$ far below the record's echo $T_2$ (median ratio 0.174 over nine measured qubits, `validation/S2D_idle.json -> data.t2_bracket.fallback_ratio`).
*Verdict.* Gate **H0_diag FAIL 6/8** (C5, the analytic post-diction, misses by 88.6x and 12.0x because the bound over-charges) but decisive on its question (C3). *QPU s = 15.0* (5+4+3+3).

### 6.9 2026-09-22/23: the clean-yield correction and S2D_idle (`prompts/20`)

*The correction to the correction.* The re-plan found the *accepted* shots were mostly **near-clean** strings (a few errors, still decoding as valid), not clean shots. The canary circuit should give one specific reference string about 88 % of the time (ideal probability 0.8833), and J1's 16.4 accepted shots above the garbage floor should have contained 15.0 of it; they contained 2 ($P=3.9\times10^{-5}$). 13 of the 35 accepted strings were distance-2 codewords of ideal probability 0. Pooled over the five hardware pubs of that circuit: **6 reference-string hits in 8 267 shots against 2.02 expected from garbage ($z=2.80$, $P=0.0172$): $f_{\rm clean}=6.65\times10^{-4}$** (1 sigma 2.6e-4 to 1.1e-3), which is **15 times below** the yield-inverted 0.0101; the measured in-circuit error budget $S_{\rm eff}=5.76$ (5.28-6.71) lies between the echo-$T_2$ prediction 3.32 and the $T_2^*$ prediction 7.52, so "31 predicted vs 35 measured" had *not* validated the echo-$T_2$ model. Criterion 3 ($E_0$ to $10^{-6}$) is void as a device test: garbage saturation reaches it at every planned budget (it measures the decoder, gate E2). The programme statement: **r=1 only at 2x2** on this device class (r=2 and r=3 predict clean fractions about $5\times10^{-6}$ and $2\times10^{-8}$); the manual's Step 9.1 yield-versus-CZ ladder cannot be delivered; Step 9.2's premise ($f\approx0.2$ at $\le500$ CZ) never held for these circuits on any quoted device; **2x3 on any superconducting device is dead**.
*S2D_idle (new gate).* Gate S2D's 2x2 criterion re-evaluated on the idle-aware $f$ at both ends of the $T_2$ bracket, FAIL 6/15: live `ibm_fez`, echo $T_2$: mean $f=6.708\times10^{-3}$, worst $1.542\times10^{-3}$; measured $T_2^*$: mean $1.298\times10^{-5}$, worst $3.40\times10^{-7}$; the most favourable point of the whole bracket (live record, echo $T_2$, DD refocusing perfectly) gives mean $0.0623<0.1$. **The 2x2 PASS of S2D is withdrawn as a hardware statement** (`validation/S2D.json` itself is not rewritten).
*QPU s = 0.*

### 6.10 2026-09-23: amendment 01, items 1-3 signed (`proposal/amendment_01_devices_and_budgets.md`)

*What was signed (owner, commit `336a60b`).* **Item 1:** the 2x2 patch is chosen by the idle-aware objective (`scripts/h0_patch_select.py`: exhaustive embedding search scored by $f_{\rm gates}e^{-S_{T1}-S_{T2}}$), not by the transpiler's calibration-aware layout; the transpiler's patch was the exact maximiser of the *gate+readout* $f$ on every record tested (optimal for the wrong objective); the winner swaps qubit 146 ($T_2=16.0\ \mu$s) for 140 ($T_2=36.0\ \mu$s), worth **1.41x** on the day's record and **3.31x** device-wide on `ibm_fez`, "a factor, not a rescue". **Item 2:** $f$ is read on the *scheduled* circuit (thresholds 0.1 / 0.05 unchanged); a device is assessable only if it declares gate durations and $T_1/T_2$ with the error rates; the 2x2/Heron leg **fails** the signed bar (mean idle-aware $f=6.71\times10^{-3}$). **Item 3:** the exact family is kept, judged on duration rather than gate count: the fixed-angle generator is 2.2 % shallower in DAG depth but 3.7 % *longer* in time and loses 1.34x in $f$; re-scheduling headroom is bounded at 7.03x and is unattainable (1 of 15 term pairs disjoint; changing it needs a new codeword layout, re-opening E1-E3). **Items 4 (the 2x3 device) and 5 (the shot quota) remain open** (item 5's shot figures scale as $1/f$). `scripts/make_amendment.py --check-only` verified 221 distinct cited values at that time.
*QPU s = 0.*

### 6.11 2026-09-30: the nine owner decisions and gate H0_model (`prompts/20`)

*The owner's rulings* (`data/H0_replan_owner_decisions.md`; nine approved, none amended, none rejected): **D8'** runtime DD off, twirling off by default; **D1'** patch by the idle-aware objective, circuits re-frozen on one patch; **D3'-f** rule D3' unchanged but fed with the idle-aware/measured clean fraction; **D3''-H0** for gate H0 only, size the shortest-depth circuits for the clean-fraction statistic (about $140/f_{\rm clean}$ shots); **D5'** the canary becomes a measuring pilot (Ramsey at two waits, $T_1$, two Krylov depths, options off); **C2'** the criterion-2 statistic becomes the maximum-likelihood clean-shot (mixture) estimator; **C3'** every shortest-depth circuit must show its reference string at least 3 sigma above accidental acceptance (the bit-order test), criterion 3 kept but labelled "not a device test"; **H0P-Y'** the factor-3 band becomes a bracket (analytic bound $\le$ scheduled simulation $\le$ unscheduled simulation); **M4.4** the manual's Step 4.4 yield model gains the near-miss acceptance term and eq. (5) takes the clean fraction ("the second contradiction found in that document", after the shot-budget sentence that asks for 32 circuits at $2\times10^5$ shots while its own formula demands 1 228 448).
*Gate H0_model PASS 5/5.* Scheduled Aer at the *measured* free-induction $T_2^*$ post-dicts the clean count already measured on hardware: predicted 4.18 clean reference hits vs 3.98 observed (**ratio 1.0503**); at the record's echo $T_2$ it predicts 197.4 (**49.58**); distance-histogram $\chi^2$ 16.9 vs 940.0. The prediction of record for 2x2 on a Heron is therefore Aer on the *scheduled* circuit at the *measured free-induction* $T_2^*$ read with the *clean-yield* statistic; dropping any of the three gives an error of 15-50x. `h0_submit.py` defaults now off (owner instruction: "change it so that it does not default to on everytime", commit `bb5a8fd`). *Free device survey* (`reports/H0_device_survey_live_20260930.md`, 0 QPU s): $T_2$ geography on 2026-09-30: median $T_2$ 92.2 / 78.1 / 141.2 $\mu$s (fez / marrakesh / kingston); winning 12-qubit patches by echo-end PTA clean $f$: fez 0.01995, marrakesh 0.004627, **kingston 0.05622** (kingston patch `[82, 83, 96, 102, 103, 104, 105, 106, 107, 117, 125, 126]`; D3' execution 96 s at that $f$). *QPU s = 0.*

### 6.12 2026-09-30 to 2026-10-01: S2_2x4, the 2x4 compilation (`prompts/22`), Perlmutter job 59162991

*What.* The 2x4 lattice (28 qubits, 14 term groups; `plaq1` acts on 16 qubits, 1 831 local codewords) was compiled with the *unchanged* structured engine: all terms synthesised and verified, max deviation $3.40\times10^{-14}$; no non-bipartite block; no generic fallback; 71 520 IR CX gates for the coarse step of which 66 468 (93 %) are in `plaq1` alone (5.1x the whole 2x3 step in one term); 69 688 CZ all-to-all, 145 958 / 148 850 routed on heavy-hex d=5 / d=7, 148 726 routed on the FakeFez map; fixed-angle 14 048 all-to-all. Duration of the all-to-all circuit 7 920.6 $\mu$s (qubit-time utilisation 0.058) and the requirement **$T_2/t_{2q}=638\,742$** at $f=0.1$ ($T_1\to\infty$; serial-formula 423 712; FakeFez-routed 858 529) against Heron's harmonic mean of 1 038. A 28-qubit dense run is priced and rejected (hours per circuit even at 62 GiB), so verification used an exact sparse simulator regressed to $1.49\times10^{-15}$ (2x2) / $9.71\times10^{-15}$ (2x3) vs the IR path and $1.11\times10^{-16}$ vs a dense $2^{28}$ cross-check. The gate failed 11/12 on the laptop (criterion C6, the leakage of the level-3 transpiled 28-qubit circuit of 279 083 instructions, not computable there). A QPY version-13 file was written for Perlmutter's qiskit 1.4.3; CI job **59162991** (A100, 99 s job, 88 s stage; Aer statevector 64.9 s, peak 4 557 MiB, mean utilisation 60 %, about 300x the laptop; the laptop estimate was 5.4 h): C6 leakage **$1.10\times10^{-12}$** (<$10^{-9}$) and the gate became **PASS 12/12**. The planner's measured numbers corrected one of its own earlier extrapolations. *QPU s = 0.*

### 6.13 2026-10-01/02: S2D_levers and the ibm_kingston pilot H0_kpilot (`prompts/23`, `21`, `21a`)

*S2D_levers (`prompts/23`).* The question was re-framed from "halve the duration" to "what does the kingston patch's $T_2^*$ have to be". Measured offline: ALAP scheduling with explicit delays is a parameter-free 1.3-4.9x lever; the best row `L4_all` (reordered terms, fractional $r_x/r_{zz}$) has duration **0.710x** the as-is canary; Aer $f_{\rm clean}$ 0.2426 (echo end) and 0.0278 (ratio 0.174), whereas the signed default-order family scheduled ALAP (`L1_seed_alap`) gives **0.2170 / 0.0312**, so ALAP + re-seed + patch, not the family change, carries almost all of it. $r_{\rm crit}(0.1)\approx0.329$ (Aer) / 0.726 (analytic bound). First run FAIL 8/9 on criterion C6 (one information cell, a 1.65 sigma estimator deviation); the planner's ruling (`reports/S2D_levers_C6_ruling_20261002.md`) scoped C6 to cells with $p_{\rm ref}\ge0.5$ (tolerance 0.25 and the 20-hit floor unchanged); re-assembly on the same counts gives **PASS 9/9** (worst in-scope deviation 0.0987).
*Pilot (`prompts/21`; dry run K3 ruling `21a`; gate H0_kpilot).* One job, `davv8504oijs73e88fvg`, `ibm_kingston`, 2026-10-02 18:12:35 UTC, 8 pubs x 4 000 shots on the patch `[59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]` (selected by the exhaustive embedding search on the day's record), runtime DD and twirling off (D8'), fingerprint `ec74eb8bf15dde41` at preregistration, submission and retrieval; billed **12.0 s** against an estimate of 9.04 s and a 30 s cap. *Numbers:* pooled direct clean fraction of the two $k=1$ circuits **$f=0.0413$, 95 % [0.0361, 0.0470]** (242 reference hits vs 1.95 from garbage); `B0_ref06_k1` 0.0404 [0.0332, 0.0486], `B1_ref07_k1` 0.0422 [0.0349, 0.0505]; $r_{\rm eff}=0.0974$ (68 % [0.0879, 0.1022]) against $r_{\rm crit}=0.3285$ (the day's grid 0.2788); the circuit's own $f$ corresponds to an equivalent dephasing ratio of about 0.17, the same as `ibm_fez`'s 0.174. *Verdict:* **NO-GO** on the preregistered rule (upper end below 0.1; the planner had predicted NO-GO in writing); gate **FAIL 8/9 on K5 only** (the windowed Ramsey gave readout-corrected $P_0<\tfrac12$ on 9 of 12 qubits, a coherent-phase (detuning or static-ZZ) signature that this design cannot separate from decay; $T_2^*$ "measured" on 9/12 < 10 required). *QPU s = 12.0.*

### 6.14 2026-10-02: H0_ddtest, the XY4 gain (`prompts/24` Stage T)

*What.* After a literature search (`reports/ibm_decoherence_literature_20261002.md`, 25 arXiv sources: client XY4 / context-aware DD ranked first; Pauli twirling cannot raise a clean fraction because it preserves fidelity (arXiv:1512.01098); the runtime XY4 is identical on all idle qubits and cannot refocus ZZ), one preregistered job tested client-side DD against no DD on the pilot's two $k=1$ circuits: job `db01005j371s73dnmbd0`, 2026-10-02 20:11:42 UTC, 10 pubs x 6 000 shots, fingerprint `84d59cbf9b5973d1` throughout, billed **20.0 s** (estimate 17.26 s).
*Numbers (95 % intervals).* T0 (no DD) $f=0.0400$ [0.0358, 0.0446]; T1 (context-aware staggered $X$, 862 pulses) $f=0.0005$ [-0.0000, 0.0013], ratio $R=0.012$ [0.004, 0.031] against a pulse-cost null of 0.816; T2 (XY4 in every window $\ge256$ ns, 776/780 pulses) $f=0.1118$ [0.1048, 0.1192], $R=2.793$ [2.472, 3.157] (null 0.841); **T3 (XY4 only in windows $\ge1\ \mu$s, 244 pulses) $f=0.1129$ [0.1058, 0.1203], $R=2.819$ [2.495, 3.185]** (null 0.944). Readout min diagonal 0.9457.
*Verdict.* T3 adopted by the preregistered rule (largest point ratio among cells with lower interval $>1$ and $R\ge1.25$); the signed bar read **GO** on the adopted cell (on the reference-hit statistic; see the 3a qualification in Section 9); gate **PASS 8/8**. The context-aware cell **collapsed** (about 65x below its null, planner arithmetic 0.012/0.816), unexplained: its statevector and duration were verified equal to the base circuit, so the *logical* circuit is right; the planner's three untested hypotheses are in `reports/H0_2x2_full_hardware_report_20261002.md` section 3. *QPU s = 20.0.*

### 6.15 2026-10-02: H0_2x2, the full 2x2 SKQD run on ibm_kingston (`prompts/24` Stage R)

*What.* Under the owner's decision of 2026-10-02 (`data/owner_decision_20261002_run_below_signed_budget.md`: "... start preparing to send the 2x2 circuit anyway to qpus to finish run and see result all the way through to the end, meaning the skqd run for 2x2 plaquettes using 121 s of qpu time"), the 28 coarse circuits (7 references x $k=1..4$) + 2 readout pubs ran in 5 jobs on the pilot's patch with DD cell T3, DD/twirling options off, ALAP; fingerprint `84d59cbf9b5973d1` at preregistration (commit `a5e2c09` 2026-10-02T14:38:28-06:00), submission (21:05:55 UTC) and retrieval. Jobs `db01pddj371s73dnnqm0` (3.0 s), `db01pdtj371s73dnnqmg` (3.0), `db01pe04oijs73e8cl30` (4.0), `db01pelj371s73dnnqo0` (22.0), `db01peql7guc73cfndc0` (21.0).
*Numbers* (all `validation/H0_2x2.json`, detail in Appendix blocks (c)-(e)). Shot plan by rule D3' at the adopted $f$: $N_4=13\,100$ ($B{=}0$) / 31 400 ($B{=}1$), 133 907 coarse shots in all. Pooled $f$ over the seven $k=1$ circuits (267 shots each): **0.1271, 68 % [0.1174, 0.1375], 95 % [0.1084, 0.1479]** (173 reference hits vs 0.46 expected from garbage; per circuit 0.1024-0.1390). Readout min diagonal 0.9417, survival product 0.8338. Sector support: $B=0$: 69 505 shots, 9 454 accepted, $|B_{\rm all}|=38/38$, $|B_{\rm sig}|=35/38$ (exact 99.9 % support 16); $B=1$: 64 402 shots, 7 885 accepted, $20/20$, $19/20$ (13). Energies on $B_{\rm sig}$: $B=0$ $E_R=-3.6402188765$ vs exact $-3.6407665507$ ($E_R-E_0=5.48\times10^{-4}$), $r_H=0.0603$, Weinstein $[-3.700489,-3.640219]$, Kato-Temple $[-3.641574,-3.640219]$; $B=1$ $E_R=-1.8615822852$ vs $-1.8615880345$ ($5.75\times10^{-6}$), $r_H=5.95\times10^{-3}$ (below the exact gap $E_1-E_R=0.0418$, so the gap assumption holds and the lowest cluster level is certified), Weinstein $[-1.867536,-1.861582]$, Kato-Temple $[-1.862424,-1.861582]$; every interval contains the exact $E_0$. Saturation: $Na/\dim=16.97$ / 15.72. **Controls:** garbage-only (100 seeds): uniformly random strings give $|B|=38$ and 20 and $E_R=E_0$ to $4\times10^{-16}$ in every seed: **the processor could have output white noise and the $B_{\rm all}$ energies would be identical**; random-at-equal-size (200 seeds): the hardware's $B_{\rm sig}$ energy sits at the **5.0th percentile** for $B=0$ (size 35: random mean $-3.63266\pm0.00639$) and the **28.5th percentile** for $B=1$ (size 19; only 18 distinct random bases exist, so the percentile is coarse).
*Verdict.* Gate **PASS 8/8** (a measurement gate). Publishability (planner, `reports/H0_2x2_full_hardware_report_20261002.md`): **not** publishable as an SKQD physics result; publishable as a methods note (honest sampling at a noise-saturated size) and, after replication, a short note on the XY4 finding. *QPU s = 53.0* (3+3+4+22+21). Account after: **102 s consumed, 498 s remaining** of 600.

### 6.16 2026-10-02: the 2x3/2x4 device question (`prompts/25`, `26`, `27`); Q0P_2x3

*K0 verdict (planner, `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md`).* On the committed kingston record (20261002T1906Z: CZ error min $8.164\times10^{-4}$, 10th percentile $1.146\times10^{-3}$, median $1.804\times10^{-3}$; $T_2$ median 147 $\mu$s, CZ 68 ns): 2x3 routed 5 477 CZ gives a ceiling $f\le(1-\epsilon_{2,\min})^{n_{CZ}}=1.14\times10^{-2}$, below the worst-case bar 0.05 by 4.4x before one-qubit, readout and idle errors, which lower it to about $10^{-4}$: **NO-GO**; 2x4 routed 148 726 CZ needs $\epsilon_2\le2.0\times10^{-5}$ for $f=0.05$ (the best edge is 41x worse): ceiling $\sim10^{-53}$: **NO-GO**; "no 2x2 technique can change it". **IonQ** (vendor pages read 2026-10-02; `data/ionq_2x3_feasibility_20261001.json`): Forte / Forte Enterprise (36 qubits; spec 2q 0.4 %, 1q 0.02 %, SPAM 0.5 %; day-measured DRB 99.3 % / 99.5 %; T2 about 1 s; ZZ 950 $\mu$s) give 2x3 gate-only $f=8.61\times10^{-5}$ (virtual $R_z$; Aria $3.52\times10^{-5}$) with a serial-idle estimate of $e^{-22}$; Aria is retired; Tempo is a late-2026 projection whose 99.9 % target gives $f\approx0.077$, still below 0.1; 2x4 is far out of reach (and its 208 399 native gates exceed IonQ's 150 000-gate job limit). 2x2 on Forte is feasible (gate-only $f=0.303$).
*Survey and the Quantinuum route (`prompts/26`, `reports/qpu_survey_2x3_20261002.md`).* The owner asked "search internet to find which quantum device can run 2x3". Result: **only Quantinuum's QCCD trapped-ion machines** meet the signed bar on published numbers: gate-only $f$ **0.1502 (H2-2), 0.1642 (Helios-1)**, 0.1113 (H1-1), 0.0860 (H2-1); every other surveyed platform fails by 2-13 orders of magnitude (Appendix block (f)). The decisive unknown is the *memory (transport) term* of a circuit with a two-qubit critical path 1 925 gates deep; three ESTIMATE scenarios (round time 0.5 / 1.1 / 4.4 ms) give $f_{\rm mem}$ for H2-2 of 0.1454 / 0.1398 / 0.1130 and for Helios-1 0.1378 / 0.1117 / 0.0352. Cost: HQC per shot $=\;5+C(N_{1q}+10N_{2q}+5N_m)/5000$ per job; mean 4.9666 HQC per shot for the 2x3 family; an Azure Standard plan equivalent of 12.5 USD per HQC (ESTIMATE; pay-as-you-go not public).
*`prompts/27` (planner analysis `reports/2x3_qec_amplification_strategy_20261002.md`).* The owner asked whether error correction, an "amplifier" or many qubits could give a substantial 2x3 result. Answer: fault-tolerant 2x3 needs about $1.1\times10^5$ $T$ gates per shot on $10^4$-$10^5$ physical qubits (ESTIMATE): a 2029-class option (IBM Starling, Quantinuum Apollo, STAR-class), not 2026-2028; error detection by an Iceberg code is a net loss because the Gauss-law codewords are already a distance-2 detection code; there is no quantum amplifier, but *shots* are one: with the decoder and $B_{\rm sig}$ the usable clean fraction at 2x3 can drop from 0.1 to about $10^{-3}$ (cost $\propto1/f$ up to $2\times10^6$ shots per sector, $\propto1/f^2$ beyond). It defined claim tiers A/B/C (Section 9) and stages T0 (tier arithmetic), T0c (levers), 0b (a 2x3 pilot on `ibm_kingston`: the K1 pilot), S3H (Helios-class device-model GPU stage), then access and a pilot.
*Q0P_2x3 (`prompts/26` Stage A) PASS 7/7* (2026-10-02 21:36 MDT): 44 circuits compiled to $\{R_z,\mathrm{PhasedX},\mathrm{ZZPhase}\}$ with pytket and frozen with checksums, max $|\Delta\psi|=2.09\times10^{-13}$ (build $4.06\times10^{-14}$), leakage $1.29\times10^{-13}$, 2 158 ZZPhase on all 44, 2 989-3 091 PhasedX; HQC per shot 4.9538-4.9742 (mean 4.9666); **level-2 compilation is not state-exact with measurements** (max $|\Delta\psi|=0.585$ because TKET removes the $R_z$ in front of each Measure; probabilities agree to $1.6\times10^{-13}$). Stage E plan (vendor emulator): 11 936 eHQC (k=1 x1000, k=4 x200, both sectors); Stage P pilot 9 938 HQC; campaign (D3-type union reading at $0.7f$): 2.02e6 / 1.01e6 / 6.75e5 HQC at $f=0.05/0.10/0.15$. **Rule D3' is not a finite plan at 2x3**: 32 of 677 $B=0$ states and 11 of 426 $B=1$ states have total $k=4$ probability <$10^{-6}$ (min $1.2\times10^{-34}$). A local dry run of the emulator path: pooled reference-string $f=0.2502$, 95 % [0.1927, 0.3195] at 280 shots vs gate-only model 0.1502 / Aer channel 0.1722: 64 hits against 44.1 expected from error-free shots ($P=0.0028$), read as *near-clean* shots. The isolated Quantinuum venv left the `coding` pins untouched. *QPU s = 0, HQC = 0, no Nexus account.*

### 6.17 2026-10-03/05: the D3'-R ruling, CF_traj, the f_ideal re-ruling (`prompts/28`, `29`)

*`prompts/28` (planner ruling, `reports/2x3_shot_rule_estimator_ruling_20261003.md`).* Problem 1: rule D3' cannot size 2x3 ($N_4\approx8.8\times10^{35}$ at $f=0.1$); the shots exist only to put the states carrying the ground-state weight into $B$ (the manual's S1, H1, H2, P1 criteria never ask for all 677 states). **Rule D3'-R** (the project's label, "R" for recall): (a) every state of $S_{99}$ (31 of 677 in $B=0$, 42 of 426 in $B=1$) gets expected clean count $\ge\lambda^*=6.2958$ from the sector's circuits via a minimum-shot linear programme with every circuit $\ge267$ shots; (b) the $k=4$ circuits are topped up in multiples of 100 until $P(\text{clean-only recall of }S_{999}\ge0.9)\ge0.95$; yield $y=0.82\times0.7\times f$ as in D3'. Plan (planner arithmetic, prototype `scratch/planner/d3s_2x3_shot_rule_20261003.py`): $f=0.05/0.10/0.15$: 160 378 / 84 112 / 60 812 total shots, 797 157 / 418 166 / 302 382 HQC (Appendix block (g)); the D3-type union reading costs 1.01e6 HQC at $f=0.10$ with 23 / 38 $S_{999}$ states below $\lambda^*$ and $P(R\ge0.9)=0.895$ in $B=1$; D3'-S (all of $S_{999}$) 2.78e6 HQC. 2x2 is consistent and stays as recorded (min expected clean count over $S_{999}$ 30.15 / 32.76 vs $\lambda^*=6.30$; every $S_{999}$ state observed $\ge59$ / 80 times). Problem 2 (the reference-string estimator overstated $f$ in a pure gate-noise model): read as the Z-type near-clean term of M4.4, to be proved by a Pauli-trajectory decomposition (gate CF_traj) plus a bit-flip-only control to exclude a merged-gate bug.
*CF_traj, first execution (2026-10-05 Part A): FAIL (C1, C4 fail only because the STOP "$\rho_T>1.5$" truncated the run).* Physics confirmed (trajectory prediction of the A6 hits $62.58\pm2.64$ vs 64 observed, fault-free only 44.06; bit-flip control 40 hits vs predicted 45.95), but the tail-class statistic $f_T$ was inflated: $\rho_T$ up to 3.86.
*`prompts/29` (re-ruling, `Physics confirmed, f_T withdrawn`).* The returns to the reference are single Pauli events acting as a *phase* in the computational frame; most returning trajectories are at total-variation distance exactly 0 from the ideal, i.e. they are *ideal samples*. New referent: $f_{\rm ideal}(\delta)=f_0'+(1-f_0')\,b(\delta)$ (shots that sample the ideal output distribution to within TV distance $\delta$; $b$ the benign-fault fraction); $f_{\rm hit}$ is an estimator of $f_{\rm ideal}$, not of $f_0'$; $f_T$ withdrawn (noise *scattering* into low-probability states inflates it 21-39x). Budget bar refers to $f_{\rm ideal}$; the GO/sizing statistic is $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$; GO rule v3; Stage E/P v3 = 800/800/200/200 shots (about 9 950 (e)HQC). 2x2 under v3 at $r_{nc}=1.10$: the H0_2x2 "signed bar GO" reads **AMBIGUOUS** (0.103, lower 95 % 0.096).
*CF_traj completed (Part A', 2026-10-05): PASS 7/7* (`validation/CF_traj.json`, `reports/CF_traj.md`; wall 1 201 s; no STOP). Trajectories K per arm: `B0_ref25_k1` 720, `B1_ref57_k1` 240, `B0_ref25_k4` 240, `xx` arm 120; A5 (the 2x2 circuit under a twirled idle model) K=2 000 at each $T_2$ end. **$r(10^{-3})=f_{\rm hit}/f_{\rm ideal}$:** `B0_ref25_k1` 1.089 [1.050, 1.136] ($f_0'=0.17209$, $b=0.0569$ [0.0417, 0.075], $f_{\rm ideal}=0.2192$ [0.2066, 0.2342], $f_{\rm hit}=0.2387$ [0.2241, 0.2549]); `B1_ref57_k1` 1.052 [0.987, 1.126] ($f_{\rm ideal}=0.2448$ [0.2172, 0.2758]); `B0_ref25_k4` 1.115 [1.036, 1.220] ($f_0'=0.17219$, $f_{\rm ideal}=0.2205$ [0.1963, 0.2481]); `xx` 1.042 [1.001, 1.122]. **Pooled $k=1$: $r=1.069$ [1.029, 1.115] $\Rightarrow$ $r_{nc}=1.115$** (`data/cf_trajectories/r_nc.json`; commit `a8ebbaa`; the STOP $r_{nc}>1.3$ did not fire). **Floor theorem** ($f_{\rm eff}(s)\ge f_{\rm ideal}(1-2\delta/p_c)$ per state): min over $S_{99}$ of $f_{\rm eff}/f_{\rm ideal}(10^{-3})$ is 1.089 / 1.040 / 1.100 / 1.041, all $\ge0.95$. **Mixture-estimator bias at $k=4$:** 1.274 [1.170, 1.402] (inside [0.67, 1.5]). **A5 2x2:** $T_2^*$ end: $f_0'=1.64\times10^{-6}$, $f_{\rm hit}=0.0189$ [0.0139, 0.0241], $f_{\rm ideal}=0.028$ [0.021, 0.035], $r=0.674$ [0.539, 0.835]; echo end: $f_0'=0.0915$, $f_{\rm hit}=0.288$ [0.273, 0.302], $f_{\rm ideal}=0.320$ [0.301, 0.336], $r=0.902$ [0.884, 0.918] — under idle dephasing the reference-hit fraction *under*-estimates $f_{\rm ideal}$ in this model. C2: 63.46 $\pm$ 2.25 predicted vs 64 observed ($P=0.979$). *QPU s = 0, HQC = 0.*

### 6.18 2026-10-05: the owner's decisions and the Quantinuum access draft

*Decisions (`data/owner_decision_20261005_partB.md`, verbatim "1a, 2a with the convergence condition, 3a").* **1a:** the signed bar (mean $f\ge0.1$, worst $\ge0.05$) refers to $f_{\rm ideal}$, measured on a device as $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ with $r_{nc}=1.115$. **2a:** rule D3'-R is signed as the **minimum** 2x3 shot sizing (input $y=0.82\times0.7\times\hat f_{\rm ideal}$) together with the Stage E / Stage P v3 plans (800/800/200/200); condition: approval of any full 2x3 campaign additionally requires that the emulated check of the plan shows **energy convergence** (E_R and certificate width against shots and against Krylov $k$) and **weighted coverage**, under criteria the planner adds; if not met the planner re-sizes and the new cost returns to the owner; signing commits no HQC. **3a:** the 2x2 "signed bar GO" (H0_ddtest / H0_2x2) was read on $f_{\rm hit}$; under the conservative correction it may read AMBIGUOUS; external citations carry this qualification; no recorded verdict is edited. *K1 decision (`data/owner_decision_20261005_k1_2x3_fpilot.md`):* verbatim "go with step 1,2 and 3, send the 2x3 job to ibm qpu first if its ready to submit": authorises ONE preregistered K1 pilot submission on `ibm_kingston`, cap 300 s billed, under the preconditions of `prompts/27` stage 0b (gate K0 on the day's record, dry run PASS, D9 fingerprint match, QPU estimate $\le300$ s); the GO-B / GO-A / NO-GO thresholds are read on $\hat f_{\rm ideal}=f_{\rm hit}/1.115$ with $f_{\rm hit}$ reported beside it.
*`prompts/30` (planner, `CV_2x3_plan`).* Finding: coverage is checked as recall but the energy only at the final point; convergence against shots, against $k$, and weighted coverage are checked nowhere as a criterion. Defines the weighted coverage $W(B)=\sum_{s\in B}|c_s|^2$ (exact ground state of each sector; the captured weight of `support_metrics`), nested subsamples (prefixes of each circuit's shot sequence at $\phi\in\{1/16,1/8,1/4,1/2,1\}$), a Krylov curve cumulative over $k=1..4$, 200 random equal-size bases at every point, **one computed constant** $E_{\rm tol}=E_R(R\cup\text{top 80 \% of }S_{999})-E_0$ (the Ritz error H1's own recall target tolerates; planner expectation of order $10^{-2}$ from Table 3, `oracle|80` = 1.010e-2 / 1.024e-2), and **criteria CV0-CV5** (structural; shot convergence $E_R(N/2)-E_R(N)\le E_{\rm tol}$; certificate $r_H(N/2)\le0.1$ ($B=0$) / 0.15 ($B=1$) with $E_0\in[E_R-r_H,E_R]$; Krylov convergence $E_R(B^{(3)})-E_R(B^{(4)})\le E_{\rm tol}$, failure = STOP because a $k=5$ circuit is a family change; below the random 2.5th percentile with $E_{\rm rand,2.5\%}-E_R\ge E_{\rm tol}$ and weight above the random 97.5th percentile; $W(B_{\rm sig}(N))\ge0.99$) and a **re-sizing rule** (uniform multiplier $s\in\{2,4,8\}$ on D3'-R, smallest passing on prefixes of the same samples; $s=8$ failing = STOP; planner arithmetic: 418 167 HQC at $f=0.10$ becomes about 8.4e5 / 1.7e6 / 3.3e6). Stage E / P test $f$ only (two references cannot generate a support). A 2x2 information block applies the same curves to the H0_2x2 counts, labelled "not a device test (saturation)". Laptop about 1 executor day, 0 QPU s, 0 HQC. **Status today: written, not executed** (the other agent's work in progress).
*`proposal/quantinuum_access_request_draft_20261005.md`* (a draft by the coordinator for the owner to edit; nothing sent): two routes, (A) the OLCF Quantum Computing User Program (QCUP; default emulator quota "6000 seconds"; hardware credits "must be justified using results from an emulator"; eligibility to be confirmed by the owner) and (B) Sales@Quantinuum.com for a research agreement with Nexus access; ask for the emulator first (about 10 000 eHQC: two $k=1$ circuits at 800 shots and two $k=4$ circuits at 200), then, if the preregistered rule passes ($\hat f_{\rm ideal}\ge0.10$ with 95 % lower bound $\ge0.05$), a hardware pilot of the same four circuits (about 10 000 HQC); five questions to the vendor (measured 2q error; memory error per layer for a 20-qubit mostly serial 1 900-layer program; parallel gates; how $R_z$ and PhasedX enter HQC; the HQC rate and research allocations). The full-campaign scale for the owner's planning is 3.0-4.2e5 HQC at H2-2 (prompts/28/29), a minimum under the convergence condition. *QPU s = 0, HQC = 0.*

### 6.19 Other items worth a line

- **Amendment 01 item 4 prerequisite work** (`data/S2D_2x3_device_requirements.json`, `reports/S2D_2x3_device_requirements.md`): requirement stated as the exact half-space $2158\,\tilde\epsilon_2+7310\,\tilde\epsilon_1+20\,\tilde\epsilon_{ro}\le\ln10$: $\epsilon_2\le7.094\times10^{-4}$ at the declared $\epsilon_1,\epsilon_{ro}$ ($9.066\times10^{-4}$ with virtual $R_z$); levers: connectivity spent, virtual $R_z$ and the fixed-angle generator (1 620 RZZ vs 2 158) unspent; the live `ibm_fez` gap: 3.31x in $\epsilon_2$ plus 2.53x routing.
- **Literature** (`reports/ibm_decoherence_literature_20261002.md`; `prompts/low_clean_fraction_techniques.md` read): client-side XY4 / context-aware DD arXiv:2403.06852, ZZ-robust DD arXiv:2506.18010 (equivalent to plain DD on tunable-coupler devices, consistent with T2 = T3 and making the T1 collapse more surprising), the random-baseline critiques arXiv:2608.11569 and arXiv:2605.23697.
- **Environment events:** the `coding` conda environment was repaired on 2026-10-02 (pinned stack qiskit 2.5.2, aer 0.17.2, runtime 0.49.0 re-verified; it reproduced every Stage T number exactly); a power failure interrupted the 2x4 work on 2026-09-30; laptop RAM rose to 62 GiB on 2026-09-30.

## 7. Hardware ledger

Sources: `data/hardware/*/session.json -> jobs[*].{job_id,usage_s,submitted,n_pubs,group_shots}` and `total_usage_s`; `data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json -> usage`; `reports/SESSION_HANDOVER_20260921_24.md`, `reports/SESSION_HANDOVER_20260925_1002.md`; `validation/H0_*.json`. QPU seconds are the billed `usage` the IBM service reports per job. All real quantum jobs so far ran on **IBM Quantum (open plan, instance `open-instance`, 600 s of QPU time per rolling 28-day period)** on the 156-qubit Heron r2 devices `ibm_fez` and `ibm_kingston`. No job has been run on any other quantum computer.

### 7.1 Every QPU job

| # | date, UTC (submitted) | device | job id | what (pubs x shots) | purpose | billed QPU s | result |
|---|---|---|---|---|---|---|---|
| 1 | 2026-09-22 17:48:32 | ibm_fez | `dapbusac505c73chv0og` | canary: 3 pubs x 267 | first real run: one frozen 663-CZ $r=1$ circuit + 2 readout pubs; options: runtime XY4 DD on, twirling on | 2.0 | 8 accepted of 267 vs required $\ge10$; yield-inverted $f=0.0255$ vs predicted 0.2195: **NO-GO** (`validation/H0_canary.json`) |
| 2 | 2026-09-22 20:42:56 | ibm_fez | `dapegkcak42c73cierv0` (J1) | 5 pubs x 2 000 | diagnostic: both options off | 5.0 | 35 accepted of 2 000 (pre-registered 30.8 $\pm$ 5.5 idle relaxation / 374.5 $\pm$ 17.4 options hypothesis) |
| 3 | 2026-09-22 20:43:55 | ibm_fez | `dapeh3318flc739m51e0` (J2) | 3 pubs x 2 000 | diagnostic: XY4 on | 4.0 | 27 accepted |
| 4 | 2026-09-22 20:44:13 | ibm_fez | `dapeh7ac505c73ci2o60` (J3) | 1 pub x 2 000 | diagnostic: twirling on | 3.0 | 25 accepted |
| 5 | 2026-09-22 20:44:27 | ibm_fez | `dapehb4ak42c73cietig` (J4) | 1 pub x 2 000 | diagnostic: XY4 + twirling (the canary's own options) | 3.0 | 17 accepted; consistent with no clean component |
| 6 | 2026-10-02 18:12:35 | ibm_kingston | `davv8504oijs73e88fvg` | kpilot: 8 pubs x 4 000 | pilot on the selected patch: two $k=1$ circuits + one $k=4$ + Ramsey (44.03 and 22.02 $\mu$s) + $T_1$ + readout; options off | 12.0 | pooled $f=0.0413$ [0.0361, 0.0470]: **NO-GO** (`validation/H0_kpilot.json`) |
| 7 | 2026-10-02 20:11:42 | ibm_kingston | `db01005j371s73dnmbd0` | ddtest: 10 pubs x 6 000 | A/B test of client-side DD (4 cells x 2 circuits + 2 readout) | 20.0 | T0 0.0400; T2 0.1118; **T3 0.1129 [0.1058, 0.1203] adopted**; T1 0.0005 (`validation/H0_ddtest.json`) |
| 8 | 2026-10-02 21:05:55 | ibm_kingston | `db01pddj371s73dnnqm0` | H0_2x2: 14 pubs x 267 | full 2x2 run, $B=0$ $k=1..3$-type circuits at the 267 floor | 3.0 | see Section 6.15 |
| 9 | 2026-10-02 21:05:57 | ibm_kingston | `db01pdtj371s73dnnqmg` | 7 pubs x 267 | full 2x2 run: `B0_ref43_k3` and the $B=1$ circuits with $k=1,2,3$ (references 07, 14) at the floor | 3.0 | " |
| 10 | 2026-10-02 21:05:59 | ibm_kingston | `db01pe04oijs73e8cl30` | 2 pubs x 4 000 | readout calibration (all-0 / all-1) | 4.0 | min diagonal 0.9417 |
| 11 | 2026-10-02 21:06:00 | ibm_kingston | `db01pelj371s73dnnqo0` | 5 pubs x 13 100 | the five $B=0$ $k=4$ circuits (rule D3' $N_4$) | 22.0 | " |
| 12 | 2026-10-02 21:06:02 | ibm_kingston | `db01peql7guc73cfndc0` | 2 pubs x 31 400 | the two $B=1$ $k=4$ circuits (rule D3' $N_4$) | 21.0 | " |

(Circuit composition of rows 8-12 is from `data/hardware/H0_2x2_ibm_kingston/session.json -> jobs[*].circuit_ids`: 28 coarse circuits = 14 + 7 at the 267-shot floor plus 5 + 2 $k=4$ circuits at $N_4$, and 2 readout pubs at 4 000 shots.)

### 7.2 Totals and budget

| quantity | value | source |
|---|---|---|
| ibm_fez, 2026-09-22 (canary + diagnostic) | 2.0 + 15.0 = **17.0 s** | `session.json -> total_usage_s` (canary 2.0; J1-J4 5.0+4.0+3.0+3.0) |
| ibm_kingston, 2026-10-02 (pilot + DD test + full run) | 12.0 + 20.0 + 53.0 = **85.0 s** | `session.json` files (pilot 12.0; ddtest 20.0; H0_2x2 3+3+4+22+21 = 53.0) |
| **total QPU time used** | 17.0 + 85.0 = **102.0 s** (sum of sourced numbers) | the account counter after the last retrieval: `usage_consumed_seconds` 102 |
| plan allowance | 600 s per period (`usage_limit_seconds` 600); period 2026-09-04 to 2026-10-02 at the last check | `account_check_after_20261002T2157Z.json -> usage` |
| **remaining** | **498 s** (`usage_remaining_seconds` 498) | same file |
| number of real jobs | 12 (1 canary + 4 diagnostic + 1 pilot + 1 ddtest + 5 full-run) | `session.json` files |
| estimate-to-billed ratio of the full run | 41.7 s estimated vs 53.0 s billed (1.27; planner arithmetic from the report) | `reports/H0_2x2_full_hardware_report_20261002.md` section 5 |
| the 400 IBM minutes | requested allocation **not yet visible** to the account (only `open-instance` is) | `reports/SESSION_HANDOVER_20260925_1002.md` section 1 |
| authorised next spend | the K1 pilot on `ibm_kingston`: at most 300 s billed (owner decision 2026-10-05) | `data/owner_decision_20261005_k1_2x3_fpilot.md`; **no K1 job id exists in the repository at the time of writing** |

Note on the budget history: the owner's "600 second budget" and the plan numbers quoted at various times (583 s left after the fez work, 571 s after the kingston pilot, 551 s after the DD test and 498 s after the full run) are the account counter at those moments (`data/hardware/*/account_check*.json`: consumed 17, 29, 49, 102 s).

### 7.3 Everything else that cost compute (no QPU time)

| resource | job / run | cost | source |
|---|---|---|---|
| Perlmutter A100 (CI) | smoke job 58717267 | pass | `validation/ci_smoke.json` |
| Perlmutter A100 (CI) | L4 job 58737320 (crashed, OOM) | 608 s | `prompts/LOG.md` |
| Perlmutter A100 (CI) | L4 job 58741899 (PASS) | 686 s | `validation/ci_gate_L4.json` |
| Perlmutter A100 (CI) | S3 calibration job 58771538 (PASS) | 255 s | `validation/ci_gate_S3.json` |
| Perlmutter A100 (CI) | S2_2x4 job 59162991 (PASS) | 99 s | `validation/ci_gate_S2_2x4.json` |
| Quantinuum (HQC / eHQC) | none: no Nexus account, no allocation | **0 HQC, 0 eHQC** | `prompts/LOG.md` row prompts/26 Stage A |
| IonQ (Braket / Azure) | none | **$0** | `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` |
| laptop | the longest gate runs: S2 436 s; H0P 1 179 s; H0P_repro 1 741 s; CF_traj 1 201 s | within the 30-minute rule | `validation/*.json -> runtime_s` |

### 7.4 What the hardware ledger says

- 12 jobs used 102 s: 17 s on `ibm_fez` (two failures to reach the planned run: a NO-GO and a diagnosis) and 85 s on `ibm_kingston` (one NO-GO, one adopted mitigation, one full run).
- 53 of the 102 s (52 %, planner arithmetic) bought the only full SKQD run on hardware, at 2x2.
- The cost structure: the per-job billing floor is about 2-2.5 s regardless of shots (`SESSION_HANDOVER_20260921_24.md` section 4), so a session of many small jobs is job-count dominated; the 2x2 run used 133 907 coarse shots in 53 s = about 2 500 shots/s (sum of sourced numbers; the K1 stage plan quotes 2 700 shots per second for the same run).
- Next planned spend: K1 pilot (2x3 on `ibm_kingston`, cap 300 s of the 498 s left); Quantinuum emulator / pilot (about 10 000 eHQC / 10 000 HQC) pending access.

## 8. What was learnt

Every item is tied to the file that carries it. "Planner" statements are the project planner agent's conclusions, labelled as such.

### 8.1 Physics

1. **The exact references and the certification machinery work as specified.** All of the manual's Tables 1-2 and the derived quantities reproduce (gates E1-E3, Section 5); two independent Hamiltonian builders agree to $2.3\times10^{-14}$. On the hardware data, every Weinstein and Kato-Temple interval contained the exact $E_0$; at $B=1$ the residual $r_H=5.95\times10^{-3}$ is below the exact gap $0.0418$, so the lowest member of the near-degenerate cluster is certified, which the manual had listed as a stretch goal (`validation/H0_2x2.json -> data.energies.B=1.B_sig`).
2. **Ground states here are sparse.** The 99.9 % supports are 16 and 13 states at 2x2 (of 38 and 20), 86 and 95 at 2x3 (of 677 and 426) and 305 and 470 at 2x4 (of 12 843 and 8 934); participation ratios 1.5-4.8 at $g^2=4$ (`data/references.json`). At smaller coupling the support grows (2x3, $g^2=1$: 396 / 549, PR 33.8), the regime where sample-based methods get harder.
3. **At 2x2 the SKQD energy from the whole accepted support is not a device measurement.** The random decoder acceptance is $a=\dim/4096$, so once $N\gtrsim5\times4096$ shots (rule C22) the sector fills from accidentally valid noise alone. The run used 69 505 and 64 402 shots, i.e. $Na/\dim=16.97$ and $15.72$ (`validation/H0_2x2.json -> data.C22`). Uniformly random bit strings through the same decoder reproduced $E_0$ exactly in 100 of 100 seeds (`data.baselines.*.garbage_only`). The manual had anticipated it qualitatively (Step 0: "any $10^3$-shot run saturates its sectors"); the project quantified it and built the controls. The same warning is in the 2026 literature on sample-based diagonalization (arXiv:2608.11569, arXiv:2605.23697).
4. **The device-dependent reading is the signal support $B_{\rm sig}$**: 35 of 38 and 19 of 20 states above the $3\sigma$ noise line, with $E_R-E_0=5.48\times10^{-4}$ and $5.75\times10^{-6}$, at the 5.0th and 28.5th percentile of 200 random equal-size bases (the 28.5 % is coarse: only 18 distinct random bases exist for a 19-of-20 subset with both references fixed, and the omitted state carries exact weight $9.3\times10^{-7}$). A modest signal in $B=0$, no evidence in $B=1$ (`reports/H0_2x2_full_hardware_report_20261002.md` section 4).
5. **The manual itself expects no device advantage at 2x3 and 2x4**: CIPSI tracks the oracle at equal $|B|$ (S1 rows: $1.2\times10^{-3}$ vs $1.2\times10^{-3}$ at $|B|=160$), and device-seeded CIPSI does not help (manual Step 6.2). The planned primary endpoint P1 is a characterized null.
6. **Truncation matters at small coupling.** At 2x2, raising $j_{\max}$ from $\tfrac12$ to 1 shifts $E_0$ by $-0.0019$ ($g^2=4$), $-0.0385$ ($g^2=2$), $-0.341$ ($g^2=1$) (`data/references.json -> truncation_2x2`).
7. **Table 4 of the manual rests on a proxy, which later hardware showed to be badly optimistic.** The proxy treats a non-clean shot as uniform garbage or a few random bit flips; real idle-time error produces *near-clean* strings (below).

### 8.2 The device

8. **Idle-time dephasing, not gate count, is the loss that matters on Heron for this circuit family.** The gate-only model predicted $f=0.2195$ on `ibm_fez`; the clean fraction measured on the same circuit was $6.65\times10^{-4}$. The 663-CZ canary circuit runs 43.71 $\mu$s at depth 1 328 (nearly serial: 0.233 qubit-time utilisation per amendment item 3), each qubit idling 19-42 $\mu$s (`reports/SESSION_HANDOVER_20260921_24.md`). Ratio of in-circuit free-induction $T_2^*$ to the calibration record's echo $T_2$: 0.174 on `ibm_fez` (median over nine measured qubits, `validation/S2D_idle.json -> data.t2_bracket.fallback_ratio`) and about 0.17 equivalent on `ibm_kingston` (from the pilot's own $f$; the Ramsey estimate $r_{\rm eff}=0.0974$ is biased low by a coherent-phase signature). Only the *scheduled* simulation at the *measured* $T_2^*$ read with the *clean-yield* statistic post-dicts the device (ratio 1.0503; the echo end is 49.58x off; `validation/H0_model.json`).
9. **Runtime XY4 plus Pauli twirling did not help on fez; client-side XY4 restricted to windows of at least 1 $\mu$s helped by about 2.8x on kingston; staggered context-aware DD collapsed.** Same-job ratios (95 %): T2 2.793 [2.472, 3.157], T3 2.819 [2.495, 3.185], T1 0.012 [0.004, 0.031] against pulse-cost nulls 0.841 / 0.944 / 0.816 (`validation/H0_ddtest.json -> data.decision.cells`). Twirling cannot raise a clean fraction (it preserves average error, arXiv:1512.01098). The context-aware collapse is unexplained; the planner notes that arXiv:2506.18010 predicts little difference between staggered and plain DD on tunable-coupler devices, which makes the collapse more surprising. One job, one patch, one calibration content: **not a replicated result**.
10. **Patch selection and scheduling are first-order levers but not rescues**: the idle-aware patch rule was worth 1.41x on the record that flew and 3.31x device-wide on fez; ALAP with explicit delays cut the scheduled duration to 0.710x (`validation/S2D_levers.json -> data.verdict.duration_ratio_best`); the exact family is kept because the fixed-angle generator is 3.7 % *longer* in time though 2.2 % shallower in depth. Neither alone reaches the bar; with client XY4 on the kingston patch the $k=1$ circuits reached $f\approx0.11$-$0.13$ on the reference-hit statistic.
11. **Superconducting devices cannot run 2x3 or 2x4 of this family.** 2x3 routes to 5 477 CZ; even at the record's best edge error $8.164\times10^{-4}$ on every gate the ceiling is $f\le1.14\times10^{-2}$ (K0 verdict); 2x4 needs $T_2/t_{2q}=638\,742$ against Heron's 1 038. Dynamical decoupling removes only idle error, so it cannot change that.
12. **IonQ Forte-class machines cannot run 2x3 either** (gate-only $f=8.6\times10^{-5}$; the circuit is 2 158 serial two-qubit gates at 950 $\mu$s each); only Quantinuum's QCCD machines meet the signed gate-error bar on published numbers (H2-2 0.150, Helios-1 0.164, H1-1 0.111), with the transport (memory) error unknown and decisive. Error correction is a 2029-class option; detection codes are a net loss (planner, `reports/2x3_qec_amplification_strategy_20261002.md`).
13. **The calibration-content fingerprint behaves.** It stayed constant through three stamp-only updates on 2026-09-22 and fired on the one real recalibration; on kingston it was `84d59cbf9b5973d1` throughout 2026-10-02. Readout on the kingston patch: min diagonal 0.9417 against the live expectation 0.9525; survival product 0.8338 against the manual's design 0.82 (`validation/H0_2x2.json -> data.readout`).

### 8.3 Statistics and the meaning of "clean"

14. **Accepted shots are not clean shots.** The decoder accepts near-clean strings at a rate comparable to pure noise; on fez 13 of 35 accepted strings were distance-2 codewords of ideal probability 0. The yield inversion of the manual's Step 4.4 overstated the clean fraction by a factor 15 (0.0101 vs $6.65\times10^{-4}$; `validation/H0_model.json -> data.C2_pooled_device_clean_count`). Simulated Aer shows the same effect (34-42 % of accepted shots on the FakeFez snapshot), so it needed no hardware to find and was derivable from the exhaustive decoder enumeration of gate E2 (owner-approved rule M4.4).
15. **The right measurement is the reference-string statistic** ($f_{\rm hit}$), cross-checked by the mixture estimator; the C6 ruling scoped their agreement to circuits whose reference probability is at least 0.5 (at low $p_{\rm ref}$ the two estimators use nearly disjoint information, combined relative sigma 0.172).
16. **$f_{\rm hit}$ estimates the ideal-sample fraction, not the fault-free fraction.** The Pauli-trajectory decomposition (CF_traj, PASS 7/7) shows the shots that return to the reference are single phase-type events that do not change the measured string, most of them sampling the ideal distribution exactly; $r_{nc}=f_{\rm hit}/f_{\rm ideal}=1.115$ (upper 95 % end; `data/cf_trajectories/r_nc.json`). The first candidate statistic ($f_T$, tail-class fraction) was withdrawn because noise *scatters* shots into low-probability states and inflates it 21-39x. Consequence for 2x2: under the conservative correction the "signed bar GO" reads **AMBIGUOUS** (0.103 with lower 95 % bound 0.096, planner arithmetic at $r_{nc}=1.10$; owner decision 3a). Under idle dephasing at 2x2 the reference-hit fraction *under*-estimates $f_{\rm ideal}$ in the A5 model ($r=0.674$ and $0.902$ at the two $T_2$ ends), so the correction is not one-directional.
17. **The floor theorem** (CF_traj): the effective clean rate of every $S_{99}$ state is at least $f_{\rm ideal}(1-2\delta/p_c)$; measured minima 1.089 / 1.040 / 1.100 / 1.041 of $f_{\rm ideal}$ on the four arms, so sizing on $f_{\rm ideal}$ is safe by construction.
18. **At $k=4$ the mixture estimator overstates $f_{\rm ideal}$ by 27 %** (bias 1.274 [1.170, 1.402]).
19. **Rule D3' is not a finite plan at 2x3** ($N_4\sim8.8\times10^{35}$ at $f=0.1$ because 32 of 677 and 11 of 426 states have total $k=4$ probability below $10^{-6}$), and was measuring the wrong set: none of those states is in the 99.9 % support. The replacement D3'-R (31 / 42 states of $S_{99}$ at $\lambda^*$, then recall of $S_{999}\ge0.9$ with probability $\ge0.95$) costs 418 166 HQC at $f=0.10$ (planner arithmetic).
20. **Cost scales as $1/f$** (up to about $2\times10^6$ shots per sector, and $\propto1/f^2$ beyond; planner, `prompts/27` and `reports/2x3_qec_amplification_strategy_20261002.md`): the shot quota of the manual cannot be signed until the 2x3 $f$ is measured (amendment item 5).
21. **The depth ladder at 2x2 is uninformative as run**: 94 % of the shots sit at $k=4$ (65 500 of 69 505 in $B=0$, planner arithmetic), so the $k$-resolved growth of $B_{\rm sig}$ mostly tracks shot count; the clean fraction of $k=2..4$ circuits is not measurable with the present estimators at their low $p_{\rm ref}$.

### 8.4 The reference manual

22. Two internal contradictions were found in the manual: (a) Step 9.2 asks for $2\times10^5$ shots per sector for 32 circuits while its own eq. (5) demands 1 228 448 (and at its design point $f=0.2$ already 1.69e6 per sector); (b) Step 4.4's yield model has no near-clean term (rule M4.4; "a stronger claim than the other eight ... it amends the reference manual"). The manual's premise (Step 9.2) that circuits of $\le500$ CZ keep $f\gtrsim0.2$ "never held for these circuits on any quoted device" (handover).
23. The **0.82 readout factor** double-counts the readout survival on Quantinuum (its $f_0$ already contains it); it is kept for consistency with 2x2; removing it would lower every shot count by 18 % and is the owner's call (`reports/2x3_shot_rule_estimator_ruling_20261003.md` section 5).

### 8.5 Compute and process

24. **GPU speed-ups** (Perlmutter A100): 19.8x at 12 qubits (0.00103 vs 0.02037 s/shot, L4), 161x at 20 qubits (0.01987 vs 3.198 s/shot, S3), about 300x for one 28-qubit leakage check (2x4); but L4 mean GPU utilisation was 15.3 %, so more GPUs would not help; the allocation model underestimates real memory 3.5x.
25. **Measurement gates plus preregistration kept the record honest.** Every hardware step has a committed prediction and decision rule before the data, a fingerprint-guarded submission, a dry run, and a PASS that means "measured" rather than "good"; two NO-GO verdicts (canary, pilot) and one FAIL (diag) are in the record with their numbers. The one exception is positive: the full run proceeded under an explicit, scoped owner waiver of the signed bar, not under a quietly relaxed criterion.
26. **Dry runs cannot predict DD gains** (Aer's relaxation on a delay is Markovian): dry-run ratios 0.71-0.79 vs nulls 0.82-0.94 were path checks only, as `prompts/24` P10 said in advance.
27. **Mistakes recorded in the handover** (`reports/SESSION_HANDOVER_20260921_24.md` section 7): the assistant reported the corrected model as predicting the device "to 1.13x" (that anchored on the accepted-shot count, the wrong statistic); a batching change crashed the first GPU job (about 92 GB requested on an 80 GB card); the assistant repeated the amendment's own erratum (2 164 CZ quoted for 2x2: it is the 2x3 figure; 2x2 is 256 all-to-all / 618 routed); a first count of clean shots accepted bit strings in both orders and double-counted (9 instead of 6); an executor was told to preserve a file that the prompt says to overwrite.

## 9. Where we are now and where we are heading

Sources: `CLAUDE.md` status paragraph, `reports/SESSION_HANDOVER_20260925_1002.md`, `prompts/27`-`30`, `data/owner_decision_20261005_*.md`, `proposal/quantinuum_access_request_draft_20261005.md`, `reports/H0_2x2_full_hardware_report_20261002.md` section 6, `reports/qpu_survey_2x3_20261002.md`, `prompts/LOG.md`. State of the repository on 2026-10-05: branch `master`, **4 commits ahead of `origin/master`** (`git status -sb`), HEAD at the start of writing `c29a402`.

### 9.1 One-paragraph state of every track

- **Physics core (E1-E3, S1, CS):** done and reproduced on cloud and laptop (all PASS).
- **Circuit layer:** exact structured circuits verified at 2x2, 2x3 and 2x4 (S2, S2_2x4 PASS); native-gate versions of the 44 2x3 circuits frozen for Quantinuum (Q0P_2x3 PASS).
- **2x2 hardware:** the full SKQD run is done (H0_2x2 PASS, 53.0 s). The campaign is *closeable*; the report's verdict is "methods note, not an SKQD physics result".
- **2x3 hardware:** no 2x3 job has been run anywhere. The preregistered K1 pilot on `ibm_kingston` is *in preparation by another agent* (see 9.2). The only device class that meets the signed gate-error bar on published numbers is Quantinuum H2-2 / Helios-1; access is not yet requested (draft only).
- **2x4:** compiled, verified, requirement measured; no device can run it (requirement $T_2/t_{2q}=638\,742$).
- **Neural / ML step:** only the minimal ridge ranker, only on exact amplitudes (S1). Not applied to any hardware data.
- **Classical statistics machinery for the 2x3 plan:** D3'-R signed as the minimum sizing (decision 2a); $f_{\rm ideal}$ referent and $r_{nc}=1.115$ signed (1a); CF_traj PASS; the convergence/coverage criteria (CV0-CV5) written (`prompts/30`) and being executed.

### 9.2 Open work in progress (two other agents; files uncommitted at the time of writing, so everything here may change)

**(i) The K1 pilot: 2x3 clean-fraction pilot on `ibm_kingston`** (`prompts/27` Stage 0b; owner decision D1 of 2026-10-05: "go with step 1,2 and 3, send the 2x3 job to ibm qpu first if its ready to submit"). Authorised: ONE preregistered submission, cap 300 s billed of the 498 s left, under the preconditions of Stage 0b: gate K0 on the day's record, dry run PASS, D9 fingerprint match, QPU estimate $\le300$ s. Per decision 1a the thresholds are read on $\hat f_{\rm ideal}=f_{\rm hit}/1.115$ with $f_{\rm hit}$ reported beside it. Design (`prompts/27`): the two signed $k=1$ circuits with the largest ideal reference-string probability (one per sector), routed on the day's record, ALAP with explicit delays, client XY4 in windows $\ge1.024\ \mu$s (the adopted 2x2 cell T3), plus two readout pubs; $10^5$ shots per circuit (planner: at $f=10^{-4}$ and $p_{\rm ref}\approx0.5$ about 8 expected reference hits against about 0.1 from garbage); rule: **GO-B** if $f\ge10^{-3}$ (a Tier-B run then costs $\le2\times10^{7}$ shots per sector, about 6 h at 2 700 shots/s), **GO-A** if $3\times10^{-4}\le f<10^{-3}$ (Tier A only), **NO-GO** below. Progress visible in the working tree on 2026-10-05 (uncommitted): `scripts/gate_K0_2x3_2x4.py` + `validation/K0_2x3_2x4.json` (gate K0, FAIL 5/6 only because tests were skipped; on the committed 20261002T1906Z record the 2x3 routed circuit (seed 6) has 5 527 CZ, $f_{\rm ceiling,2q}=1.095\times10^{-2}$, layout gate-only $f=5.542\times10^{-6}$, idle-aware (echo) $5.6\times10^{-21}$; XY4-transfer $1.6\times10^{-20}$, verdict: no record meets the bar); `scripts/gate_K1_2x3_fpilot.py` and `data/hardware/K1_2x3_prep/select.json` (circuits chosen: **`B0_ref117_k1`** with ideal reference probability 0.92836 and **`B1_ref29_k1`** with 0.92831; random-string acceptance of the 20-qubit decoder 677/$2^{20}$ = $6.456\times10^{-4}$ ($B=0$) and 426/$2^{20}$ = $4.063\times10^{-4}$ ($B=1$), `data/K1_2x3_fpilot/garbage_acceptance_2x3.json`). **No K1 job id exists in the repository at the time of writing and no QPU time has been spent on it.** Reading of the K0 numbers (my reading, not the planner's): the preregistered thresholds start at $10^{-3}$ on $\hat f_{\rm ideal}$ while the idle-aware gate-only prediction for 2x3 on this record is many orders lower, so a NO-GO would be the expected outcome, as the planner expected in `prompts/27` ("planner: at $f=10^{-4}$").

**(ii) `prompts/29` Part B' and `prompts/30`** (the 2x3 plan check): Part B' is `prompts/28` Part B with the amendments: `skqd.skqd.corrected_clean_fraction(pooled, r_nc, r_nc_95)`; `d3r_plan` reproducing the planner's D3'-R table to the shot (gate `Q0P_2x3_plan`); the preregistration block "v2" with GO rule v3 and Stage E / P v3 plans (800 / 800 / 200 / 200 shots); the 2x2 information block with the A5 bracket. `prompts/30` adds the convergence and coverage criteria CV0-CV5 (Section 6.18) and the re-sizing rule. Uncommitted progress visible: `scripts/gate_CV.py`, `validation/CV_2x2_info.json` (**PASS**: "the CV curves on the recorded H0_2x2 ibm_kingston counts (information; not a device test (saturation))", criteria CV0 for $B=0$ and $B=1$: nested hypergeometric prefixes, variational bound, random bases contain the references, per-state counts, $E_0$ difference $0.0$), `reports/CV_2x2_information_20261005.md`, `data/cv/*` (2x3 emulated fragment at $f=0.10$, quick mode). **The CV verdict on the 2x3 plan has not been delivered**; if CV1-CV5 fail the planner re-sizes by a factor $s\in\{2,4,8\}$ and the new HQC cost returns to the owner.

**(iii) Not done although proposed in `prompts/27`:** Stage 0 (`T0_2x3_tiers`), Stage 0c (`T0c_levers`: no-plaq1, fixed-angle + no-plaq1, truncated multiplexed rotations, SqDRIFT-style random products) and Stage 1 (`S3H_2x3`, Helios-class device model on the GPU, needs a CI token): no gate JSON exists for any of them.

### 9.3 The Quantinuum route (the only device route that reaches the signed bar)

Facts (all `reports/qpu_survey_2x3_20261002.md`, `data/quantinuum/devices_20261002.json`; vendor numbers were read on 2026-10-02, none measured by this project):

| device | qubits | 2q error | gate-only $f$ (2x3) | $f$ with memory (low / mid / high, ESTIMATE) | HQC per full D3-type campaign (ESTIMATE) |
|---|---|---|---|---|---|
| H2-2 | 56 | $8.3\times10^{-4}$ | **0.1502** | 0.1454 / 0.1398 / 0.1130 | 507 144 (102 100 shots, 60.1 machine-hours at the mid scenario) |
| Helios-1 | 98 | $7.9\times10^{-4}$ | **0.1642** | 0.1378 / 0.1117 / 0.0352 | 634 299 |
| H1-1 | 20 | $9.7\times10^{-4}$ | 0.1113 | 0.1049 / 0.0977 / 0.0661 | 725 197 |
| H2-1 | 56 | $1.1\times10^{-3}$ | 0.0860 | 0.0815 / 0.0764 / 0.0535 | 927 358 |

The memory (transport) error of a 20-qubit, mostly serial, 1 925-two-qubit-layer program is *unknown* (three ESTIMATE scenarios); the vendor emulator (H2-2E) carries the real transport schedule and replaces it.

**The staged plan** (after `prompts/26`, `28`, `29`; decision 2a signs the minimum sizing, no HQC committed):
- **Stage E (emulator H2-2E):** two $k=1$ circuits at 800 shots and two $k=4$ circuits at 200 shots: about **9 950 eHQC** (planner arithmetic; v1 was 11 936 eHQC). Read $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ with GO rule v3: GO iff lower 95 % $\ge0.05$ and point $\ge0.10$; NO-GO iff upper 95 % $<0.10$; AMBIGUOUS otherwise (one top-up).
- **Stage P (hardware pilot on H2-2):** the same four circuits and shots, about **9 950 HQC**.
- **Campaign:** rule D3'-R at $\hat f_{\rm ideal}$ (Appendix block (g)); at $f=0.10$: 84 112 shots, 49 jobs, **418 166 HQC**, about 49.5 machine-hours, an Azure-Standard-equivalent 5.23e6 USD at 12.5 USD per HQC (ESTIMATE: the pay-as-you-go and research rates are not public); at $f=0.05$: 797 157 HQC; at $f=0.15$: 302 382 HQC. The convergence condition (decision 2a) may multiply these by $s\in\{2,4,8\}$ (about 8.4e5 / 1.7e6 / 3.3e6 HQC at $f=0.10$, planner arithmetic). Commercial purchase is not realistic (the only published rate is the Azure Standard plan: 125 000 USD per month for 10 000 HQC); the realistic routes are a QCUP allocation or a research agreement.
- **Access (not yet requested):** the drafted email to Sales@Quantinuum.com (route B; also the project summary for QCUP, route A). QCUP: default hardware quota 0 HQC, emulator quota 6 000 s, requests must be justified by emulator results; eligibility ("US national labs, universities, government, and industry") to be confirmed by the owner. Helios-1 needs a Guppy/HUGR program (Stage A9 not built).

### 9.4 IonQ and 2x4

- **IonQ:** no accessible IonQ device can run 2x3 (Forte / Forte Enterprise gate-only $f=8.6\times10^{-5}$; Aria retired; Tempo is a projection whose 99.9 % target gives $f\approx0.077$, below 0.1). 2x2 on Forte Enterprise is feasible (gate-only $f=0.303$), costing about 5-20 kUSD at Braket rates (`reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` section 4.4); it would be a cross-platform check only. No IonQ submission tooling exists (Section 4.2).
- **2x4:** compiled and verified; on a Heron device the gate-only ceiling is $\sim10^{-53}$; the all-to-all circuit needs 69 688 CZ and $T_2/t_{2q}=638\,742$; IonQ's job limit (150 000 gates) is below the 208 399 native gates. No action planned (`prompts/27` D7: defer).

### 9.5 Publishability

*Source: `reports/H0_2x2_full_hardware_report_20261002.md` section 6 (planner), with the field survey of arXiv abstracts fetched on 2026-10-02.*

- **Today's 2x2 result can claim:** a validated, preregistered, end-to-end SKQD pipeline for a 2+1D SU(2) gauge theory with staggered quarks on a Heron processor (intertwiner-labelled basis, Gauss-law decoder with 0 mismatches over 58 hardware strings, exact structured circuits, ALAP with client-side DD, a calibration-content guard, certified Ritz energies with their controls); a measured clean fraction on 12-qubit, 588-CZ, 44 $\mu$s circuits: 0.1271 [0.1084, 0.1479] with DD and 0.0413 [0.0361, 0.0470] without, on one patch of one device on one day (to be cited with the decision-3a qualification that these are reference-hit values and the corrected $\hat f_{\rm ideal}$ may read AMBIGUOUS: at $r_{nc}=1.115$ the adopted-cell value $0.1129/1.115=0.101$ with lower end $0.1058/1.115=0.095$; **(my arithmetic from sourced numbers, the combined interval including the uncertainty of $r_{nc}$ is wider)**); a signal support of 35/38 and 19/20 states; and a quantified statement of why the all-state energies carry no device information.
- **It cannot claim:** an SKQD accuracy result (saturation), a device-support-quality result (recall 1.0 is reached by noise alone; no CIPSI control on hardware data), a claim about the circuit family's clean fraction (the bar was read on $k=1$ circuits only), a replicated DD result, "neural-enhanced", or any physics number beyond reproduction of known exact values.
- **Verdict (planner):** publishable as (a) a methods/technical note on running sample-based diagonalization honestly at a size where noise saturates the subspace (clean-fraction estimators, near-clean term, saturation rule, signal-support definition, garbage/random baselines, the 2x2 run as worked example), and (b) possibly, after replication, a short note on client-side XY4 in long idle windows raising the clean fraction 2.8x on a Heron r2 with the context-aware variant failing. Not publishable as an SKQD result for SU(2) lattice gauge theory.
- **Context:** "first SU(2) with dynamical matter on hardware" is not available as a claim (arXiv:2102.08920, 2021; arXiv:2602.18080, 2026); the manual's own claim is the 2x3 result "first quantum-centric spectroscopy of a non-Abelian gauge theory with dynamical matter in two spatial dimensions".
- **What a publishable physics claim needs, in the plan's order:** (1) a lattice where noise cannot saturate the sector: at 2x3 the saturation parameter is $2\times10^5\times0.00146/677=0.43$ at most (planner arithmetic, upper bound), which needs a 2x3 device; (2) the primary endpoint P1, device vs CIPSI at equal $|B|$ with bootstrap bands over circuits, on that lattice; (3) the clean fraction measured on the whole circuit family ($k=2..4$); (4) repeat runs (second calibration window, patch, device); (5) the ML step credited or nulled under Step 7.5 on hardware data; (6) the release bundle (raw bit strings, calibration records, circuits, decoder).
- **Claim tiers for the first 2x3 hardware run** (`prompts/27`, evaluated per sector on $B_{\rm sig}$ with references always included): **Tier A** $|B_{\rm sig}|\ge40$; $E_R(B_{\rm sig})-E_0$ below the 2.5th percentile of 200 random equal-size bases (bands not overlapping); $\le1.5\times$ the BFS error at equal size; $E_0$ in the Weinstein interval. **Tier B** Tier A plus recall of the 99.9 % support $\ge0.8$ (gate H1), gap-assumed certified width $\le0.1$ containing $E_0$ (H1), cluster energy certified to $\pm r_H\le0.15$ at $B=1$ (H2). **Tier C** Tier B plus $|B_{\rm sig}|\ge300$ and device error $\le0.5\times$ the BFS error at equal size. Thresholds are preregistered and may not be tuned to the outcome. The planner's proxy emulation (prototype, 2026-10-02, not yet a gate) suggests that with $f\approx0.17$ and $2\times10^5$ shots per sector $|B_{\rm sig}|=200$, $E_R(B_{\rm sig})-E_0=1.5037\times10^{-3}$, recall 0.988 (`prompts/27` T0.1).

### 9.6 Open owner decisions (numbered; as of 2026-10-05)

1. **K1 pilot execution.** The pilot is authorised (cap 300 s); whether it should run at all given the K0 verdict (idle-aware gate-only $f\sim10^{-20}$ on the committed record), or be reserved for a deeper decision once Stage E exists; the rule's thresholds start at $10^{-3}$.
2. **Quantinuum access.** Whether to send the drafted email (route B) and/or apply to QCUP (route A); whether the owner is eligible for QCUP; the emulator budget (about 9 950 eHQC for Stage E v3) and the pilot budget (about 9 950 HQC for Stage P v3) as separate written decisions (signing 2a committed no HQC).
3. **Full 2x3 campaign.** Whether to approve the D3'-R campaign (418 166 HQC at $f=0.10$, minimum) once the CV (convergence/coverage) check has run; the re-sizing multiple $s\in\{2,4,8\}$ and the resulting cost return to the owner; whether a $k=5$ circuit (a family change) is allowed if CV3 fails.
4. **The 0.82 readout factor** double-counts readout survival on Quantinuum; removing it lowers every shot count by 18 % (owner's call).
5. **Amendment 01 item 4** (the 2x3 device; needs vendor gate durations and $T_1/T_2$, not only error rates) and **item 5** (the shot quota of Step 9.2, scaling as $1/f$).
6. **Whether to close the 2x2 campaign** (methods note + release bundle, 0 s) **or spend about 32 s** on a DD replication plus three one-cell tests of why context-aware DD collapsed (the planner's estimate: four cells about 20 s, three mechanism cells about 12 s).
7. **IonQ.** Whether to run 2x2 on Forte Enterprise as a cross-platform check (5-20 kUSD at Braket rates) and what to ask IonQ (measured Tempo two-qubit error, gate time, $T_2$, parallelism, raw bit strings with debiasing off).
8. **Unsigned cheaper 2x3 circuit variants** (no-plaq1 $f=0.31$, fixed-angle + no-plaq1 $f=0.36$ on Helios gate-only; `prompts/27` D4): adopt only after the unrun stage T0c shows recall $\ge0.9$; needs a signature (amendment item 3).
9. **Perlmutter CI tokens:** `S3H` for the Helios-class device-model stage (`prompts/27` D2), a token for the 2x4 native-gate verification, and the production S3 job (2x3 recall criterion; 4.4 h for four sectors, but the criterion is not a hardware criterion until the corrected model is in).
10. **The 400 IBM minutes** (allocation awaiting approval; not visible to the account) and the 498 s remaining on the open plan.
11. **Pushing:** `master` is 4 commits ahead of `origin/master`; pushes are the owner's call (`CLAUDE.md` rule 5; the gate runner pushes only on PASS with `--push`).
12. **The ML step:** whether to build the graph network of manual Step 7 and run the seven-protocol comparison once 2x3 data exist; until then the word "neural" is a plan, not a result.

## 10. Progress measure

Source: `reports/H0_2x2_full_hardware_report_20261002.md` section 2 (planner, 2026-10-02): the SKQD plan was broken into 51 rows (33 rows of the manual's Steps 0-11 and 18 rows of amendment 01, the owner decisions and the preregistration discipline) and each row was scored against the *2x2 hardware campaign* with its evidence. Status key: **F** = fulfilled; **FD** = fulfilled with a deviation (named); **ND** = not done (reason named). The tally printed by the report is: **fulfilled 31, fulfilled with deviation 12, not done 8** (I recounted the table: F 31, FD 12, ND 8). The first count in the report text reads "33 manual rows + 18 amendment/decision rows". Note on scope: this scores the plan against the 2x2 hardware run only; all 2x3/2x4 hardware rows are, by that scope, "not done".

Share of the 51 rows: F 31/51 = 60.8 %, FD 12/51 = 23.5 %, ND 8/51 = 15.7 % **(sum of sourced counts)**.

### 10.1 The 51 rows

| row | plan item | status | note on deviation or reason (planner report) |
|---|---|---|---|
| 0 | Role of $2\times2$: pipeline calibration only (decoder validity, yield vs depth, readout confusion, sector filter); not an accuracy test because any $10^3$-shot run satur | F |  |
| 1.1 | Hamiltonian eq. (1), Gauss's law eq. (2) verified: $[G_a(x), H] = 0$; two independent builders agree | F |  |
| 1.2 | Conserved quantities, sector split | F |  |
| 1.3 | Exact references (Table 1) | F |  |
| 1.4 | $\Delta t = \pi/W_B$ per sector | F |  |
| 1.5 | $B=1$ near-degenerate cluster (splitting 0.042 at 2x2); certification treats the cluster as a whole; gate tolerances tied to the splitting | F |  |
| 2.1-2.3 | Local singlet spaces, intertwiner label, basis orthonormality; Table 2 counts | F |  |
| 2.4 | Codewords: 12 qubits at 2x2 | F |  |
| 2.5 | Decoder: flag / link-consistency / sector checks; round trip; random acceptance $\approx 0.15\%$ at 2x3 | F |  |
| 3 | Dressed-site Hamiltonian builder, validated against the projector construction | F |  |
| 4.1 | State what is rigorous (variational bound) and what is heuristic (device support) | F |  |
| 4.2 | Multi-reference generation: Dirac sea + one-meson configurations ($B=0$), diquark on each even site ($B=1$) | F |  |
| 4.3 | Coarse single-step circuits $k=1..4$ (family b), gauge-invariant by construction; $\le 250$ CZ per step at 2x2 after routing | FD | the gate-count budget was not met; the criterion was amended to the one it stood for |
| 4.4 | Yield model $y = 0.82 f + (1-f)a$; shot rule eq. (5) ($S \ge 6.3/(0.82 f p)$, $2\times10^5$ shots per sector) | FD | model and shot rule both amended before the run (owner-approved 2026-09-30) |
| 5.1 | Decode every shot; $B$ = union of accepted configurations plus references; record yield and rejection reasons; build $H_B$ and diagonalize | F |  |
| 5.2 | $E_R \ge E_0$ for any $B$ | F |  |
| 5.3 | Residual $r_H$, Weinstein and Kato-Temple intervals, gap assumption stated | F |  |
| 5.4 | Support metrics: recall of the 99.9 % support, false positives, yield, $E_R - E_0$ | F | (but see row 6: at 2x2 recall 1.0 is reached by noise alone) |
| 6.1-6.2 | Size-matched classical controls at equal $\lvert B\rvert$: CIPSI, BFS, random, oracle, ML-alone, device-seeded CIPSI | FD | two of the six controls, chosen because at 2x2 the saturated sector makes CIPSI at  $\lvert B\rvert = 35$ of 38 trivially near-exact; the manual itself puts the control comparison on 2x3 |
| 6.3 | Primary endpoint P1: $E_R - E_0$ and recall vs $\lvert B\rvert$ for device vs CIPSI, with bootstrap bands, on **2x3** hardware data | ND | requires 2x3 hardware |
| 6.4 | Production mode: union of device support and CIPSI growth | ND | (moot at 2x2) |
| 7.1-7.2 | Gauge-invariant neural importance model $f_\theta(b;\lambda)$ (message-passing network), leakage-safe splits | FD | on the simulator (minimal model only); **not used on the 2x2 hardware data at all** |
| 7.3 | ML uses: (i) recovery of flagged strings by eq. (9), (ii) size-constrained extension, (iii) ML-alone proposal, (iv) transfer | ND | ML is not part of the 2x2 hardware result |
| 7.5 | Seven-protocol comparison table at equal $\lvert B\rvert$; ML credited only if it beats the baseline on 2x3 hardware data | ND |  |
| 8.1-8.2 | Noise proxy: clean with probability $f$, otherwise uniform or locally corrupted, readout flips; Table 4 | F | (simulator) |
| 8.3 | Transpiled-circuit Aer simulation with device noise models (CZ errors, $T_1$, $T_2$, readout) before hardware; gate S3 recall $\ge 0.9$ for the production set | FD | the manual's gate-only noise model was wrong by 15-50x on hardware until the idle term and $T_2^*$ were added; S3 for 2x3 is still open |
| 9.1 | 2x2 calibration run, one session: validate codewords, decoder, sector filter on real strings; yield vs CZ by repetition $r = 1,2,3$ ($N_{CZ} \approx 250, 500, 750$); per- | FD | no $r = 2,3$ depth ladder; the model comparison became a measurement-to-measurement comparison because the model (Aer at the echo $T_2$) was 5.1x off in the pilot (`validation/H0_kpilot.json` -> `data.aer_at.B0_ref06_k1.r=1` 0.2114 vs `data.decision.f_pool` 0.0413, **planner arithmetic** for the ratio) |
| 9.2 | 2x3 production, four sectors, $\le 500$ CZ, $2\times10^5$ shots per sector, two calibration windows | ND |  |
| 9.3 | Optional 2x4 hardware only if H1-H2 pass | ND | (by design) |
| 10 | Gates E1-E3, S1 (done), S2, S3, H0, H1, H2, P1, M1 | FD |  |
| 10 (error budget) | Truncation ($j_{\max}$), subspace (certified interval), device (recall, false positives, yield, CIPSI comparison), shot (bootstrap over circuits), classical | FD |  |
| 10 (reporting) | Raw bitstrings, calibration snapshots, circuits and decoder released | FD | in the repository, not yet a public release bundle |
| 11 | Six-week timeline: 2x2 in week 3, 2x3 in week 4 | FD |  |
| A1 | Patch selected on the day by the exhaustive idle-aware rule R1' on the full device; re-frozen onto that patch | F |  |
| A2 | Budget criterion: $f = f_{\rm gates}\,e^{-S_{\rm idle}}$ on the scheduled circuit, mean $\ge 0.1$, worst $\ge 0.05$; $T_2$ convention named | FD | met on $k=1$ only; family-level unknown; owner waiver in force |
| A3 | Circuit family: exact structured circuits, judged by ASAP-scheduled duration and idle budget | F |  |
| A4 | 2x3 device: must declare gate durations and $T_1/T_2$ | ND |  |
| A5 | Shot quota of Step 9.2 | ND |  |
| M4.4 | Yield model gains the near-clean term; eq. (5) takes the clean yield | F |  |
| D8' | Runtime DD off, twirling off | F |  |
| D1' | Patch by the idle-aware objective | F |  |
| D3'-f | Rule D3' fed with the measured clean fraction | F |  |
| D3''-H0 | For gate H0 only, size the $k=1$ circuits for the clean-fraction statistic | FD | struck |
| D5' | Canary becomes a measuring pilot (Ramsey at two waits, $T_1$, two depths, options off); go rule on the measured $f$ | F |  |
| C2' | Mixture clean-shot estimator reported beside the yield inversion | F |  |
| C3' | Reference string $\ge 3\sigma$ above garbage on every shortest-depth circuit; criterion 3 kept but labelled "not a device test" | F |  |
| H0P-Y' | Prediction bracket: analytic bound $\le$ scheduled simulation $\le$ unscheduled simulation | F |  |
| D9 | Submission keyed on calibration *content*; fingerprint recorded at prereg, submission, retrieval | F |  |
| prereg | Preregistration committed before submission | F |  |
| dry runs | Path check on the simulator before every submission | F |  |
| owner 2026-10-02 | Run the full 2x2 SKQD whether or not the signed bar is met; use the 600 s budget | F |  |

### 10.2 Status of the manual's gate table (Step 10) today

| manual gate | state today | evidence |
|---|---|---|
| E1 | **done** | `validation/E1.json` PASS 23/23 |
| E2 | **done** | `validation/E2.json` PASS 51/51 |
| E3 | **done** | `validation/E3.json` PASS 85/85 |
| S1 | **done** | `validation/S1.json` PASS 12/12 |
| S2 | **amended; the original budget FAILS** (2x2 618 routed vs 250; 2x3 5 477 vs 500); the amended criterion (amendment 01, signed 2026-09-23) reads $f$ on the scheduled circuit and the 2x2 leg FAILS it (idle-aware mean $6.71\times10^{-3}$) | `validation/S2.json`, `S2D.json`, `S2D_idle.json` |
| S3 | **partial**: throughput calibration PASS on the GPU (161x), the recall criterion at the production budget is **not evaluated** | `validation/S3.json`, `L4.json` (PASS) |
| H0 | **realised by measurement gates**: H0_canary (NO-GO), H0_diag, H0_kpilot (NO-GO), H0_ddtest (PASS), **H0_2x2 (PASS)**; "measured $f$ within 30 % of the model" was read measurement-to-measurement | Section 5 |
| H1 | **open** (no 2x3 hardware data) | -- |
| H2 | **open** | -- |
| P1 | **open** | -- |
| M1 | **open** (no ML on hardware data) | -- |

Of the manual's 11 Step-10 gates: 4 done (E1, E2, E3, S1), 3 partial or amended (S2, S3, H0), 4 open (H1, H2, P1, M1) **(sum of the table above)**.

### 10.3 Status per milestone

The project does not keep a separate milestone list; it tracks progress through the gate table. The twelve milestone names below are **my own grouping** of the project's work (descriptive names, not project labels), each tied to the project's own gates.

| milestone | what it means | status | evidence / remaining |
|---|---|---|---|
| physics core | Hamiltonian, basis, builder, references (Steps 1-3) | **done** | E1-E3 PASS |
| exact circuits | structured exact coarse-step circuits at 2x2, 2x3, 2x4 | **done** (verified; cost over the original budget) | S2 (cost FAIL), S2_2x4 PASS, L2, L5, Q0P_2x3 PASS |
| emulation and controls | support recall, controls, Table 3/4 reproduced | **done** | S1 PASS |
| noise model and device model | proxy replaced by scheduled Aer at measured $T_2^*$ | **done for 2x2**; 2x3 device-model run (S3 recall) open | H0_model PASS, S3 calibration PASS |
| 2x2 hardware | calibration and full run | **done** (measurement gates) | H0_2x2 PASS; 12 jobs, 102 s |
| clean-fraction statistics | estimator, near-clean term, $r_{nc}$, floor theorem | **done** | CF_traj PASS 7/7 |
| 2x3 plan check | D3'-R, convergence and coverage criteria CV0-CV5, Stage E/P plans | **in progress** | `prompts/29` Part B', `prompts/30` (uncommitted work) |
| 2x3 hardware access | a device that can run 2x3 (Quantinuum) and an allocation | **not started** (draft email only) | Section 9.3 |
| 2x3 hardware results | H1, H2, P1 | **open** | needs the 2x3 hardware access row above |
| neural step | graph network, recovery, seven-protocol comparison, M1 | **open** | only the ridge baseline exists |
| 2x4 | transfer and optional hardware | **simulator verified, hardware infeasible today** | S2_2x4 PASS |
| release | raw bit strings, calibration records, circuits, decoder, methods note | **not started** (data are in the repository) | Section 9.5 |

## 11. DATA APPENDIX for plotting

*(section still to be written)*

## 12. Glossary

*(section still to be written)*

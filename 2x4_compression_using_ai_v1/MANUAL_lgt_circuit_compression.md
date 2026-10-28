# Manual: compressing Trotterised coarse-step circuits of lattice gauge theories (the genie-opus technique)

- **Written:** 2026-10-26 by genie-opus (the study agent; Opus 5.5, high effort). **Revision 2**, same day: every
  finding of the cold-read review `reviews/002-manual-cold-read.md` (commit `6ca9520`, verdict USABLE AFTER FIXES) is
  addressed; the finding → fix table is §13.
- **Reader:** an agent in a *different* lattice-gauge-theory project (other gauge group, truncation, encoding,
  geometry or size) that has never seen this study.  It can read this repository only through the paths cited here.
- **Repository:** `su2qc-skqd` (owner Digonto), study folder `2x4_compression_using_ai_v1/`.
- **No new compression run of a frozen family** was made for this manual.  Two small runs were added for it, both in
  sandboxes under `examples/` that write nowhere else: the 2x2 worked example (§1.3, §11.0) and the structure checks
  (§3b).  Every number in this manual is quoted from a file named next to it, or explicitly marked as coming from
  report prose.

---

## 0. Conventions of this manual

### 0.1 Paths

- A path that starts with **`<root>/`** is at the repository root (the package, read-only for the study), e.g.
  `<root>/src/skqd/hamiltonian.py`, `<root>/data/quantinuum/circuits_2x3/index.json`, `<root>/validation/E3.json`.
- **Every other path** (`src/c2x4/…`, `scripts/…`, `data/…`, `lean/…`, `notes/…`, `reports/…`, `reviews/…`,
  `noise/…`, `examples/…`) is inside the study folder `2x4_compression_using_ai_v1/`.  So `data/…` is the study's data
  folder; the package's is `<root>/data/…`.
- Package code is written `skqd.<module>.<name>` (module `<root>/src/skqd/<module>.py`).

### 0.2 Claim marks

| mark | meaning |
|---|---|
| **[Lean]** | proved in Lean 4 / Mathlib in `lean/Compress2x4/*.lean`; `lake build` passes, no `sorry`, standard axioms only |
| **[num]** | checked numerically, per instance, by a script whose output file is named |
| **[prose]** | a number that exists only in a report's text (the run was interactive or its JSON does not hold it); use with care |
| **[heur]** | a heuristic, an estimate, a design suggestion or a judgement; not a computed fact |

### 0.3 Commits

The master history of this repository was rewritten after 2026-10-21; commits from that day have new hashes.  Current
hashes: family loader API `2c28e51` (was `f0b2363`), notes/009 `b676b5b` (was `a07ba6d`), C4 code + v2 and 2x3 families
`30f84af` (was `390629e`), notes/009 update `7de890a` (was `040c95d`), report 004 and evidence `5984d69` (was
`bf55f30`), first manual `ac886b2`, review 002 `6ca9520`, this revision: the commit that adds it.  Old hashes still
appear inside some files written on 2026-10-21 (for example the `git_commit` field of `data/families/*.json.gz`
headers and the text of `notes/009`); they refer to the same content.

### 0.4 Symbol table

| symbol | meaning | where |
|---|---|---|
| $L_x$, `lx` | ladder length; the lattice is $2\times L_x$ | §1.0 |
| $x=(x_1,x_2)$ | a site; index $x_1L_y+x_2$, $L_y=2$ | §1.0 |
| $l$, $(x\to y)$ | a link from site $x$ to site $y$ (oriented $+x$ or $+y$) | §1.0 |
| $j_l$ | link spin, $j_l\in\{0,\tfrac12\}$ (truncation $j_{\max}=\tfrac12$) | §1.0 |
| $n_x$ | quark occupation of site $x$, $n_x\in\{0,1,2\}$ | §1.0 |
| $\iota_x$ | intertwiner label of a vertex (fusion-tree label of its singlet) | §1.0 |
| $2B$, `twoB` | twice the baryon number, $2B=\sum_x(n_x-n_{\rm vac}(x))$; the **sector** label (0 or 2 here) | §1.0 |
| $g^2$, $m$ | gauge coupling ($g^2=4$) and staggered mass ($m=3g^2/16=0.75$) | §1.0 |
| $\eta_l$ | hopping phase: $i$ on x-links, $(-1)^{x_1+x_2}$ of the start site on y-links | §1.0 |
| $H_\gamma$ | a term group: `diag`, `hop<l>`, `plaq<p>` | §1.0 |
| $dt$, $k$, $\theta$ | $dt=\pi/W_{2B}$ ($W_{2B}$ = spectral width of the sector), step index $k$, angle $\theta=k\,dt$ | §1.0 |
| $r$, $\lvert b_0\rangle$ | reference basis state (index $r$) | §1.0 |
| $t$, $\psi$ | target (exact) state and circuit state on the codewords | §5 |
| $C$ | **local codeword set** of a term: codewords restricted to the term's support | §2.1 |
| $h$ | a term's matrix restricted to $C$ (`localize`) | §2.1 |
| $c$ | a **corner** of a plaquette, $c\in\{c_{00},c_{10},c_{11},c_{01}\}$ (counter-clockwise from the lower-left) | §3c |
| $p_{a,c},p_{b,c}$ | the two plaquette-link qubits at corner $c$ | §3c |
| $x_c$ | $p_{a,c}\oplus p_{b,c}$ after the corner CX | §3c |
| $\tau_c$, $q_c$ | the corner's third-link flux qubit (interior corners only) and its vertex bit | §3c, §3e |
| $p_\star$ | $p_{a,c_{00}}$: the ladder's control and the plaquette multiplexor's target | §3c |
| $A_c$ | corner factor matrix of a plaquette | §3b |
| $D_c(\ell)$, $\ell$ | diagonal part of $A_c$ after the corner frame; $\ell$ = the corner's label bits | §3c |
| $\Phi(s)$ | angle table of the plaquette multiplexor in the frame | §3c |
| $g_c$, $d_c$ | flag $g_c=\tau_c\wedge q_c$; dark indicator $d_c=\bar x_c\wedge\tau_c\wedge q_c$ | §3e |
| $T$, $\eta$ | raising part of a hop, $H_{\rm hop}=T+T^\dagger$; $\eta=\eta_l$ | §3g |
| $a_v$, $b_w$ | hop vertex factors at the start vertex $v$ (raises $n_v$) and end vertex $w$ (lowers $n_w$) | §3g |
| $s_{\rm JW}$ | Jordan–Wigner sign $\prod_{v<z<w}(-1)^{n_z}$ | §3g |
| $J$ | the JW qubits: support qubits outside the two end vertices | §3g |
| $N$ | $n_v+n_w$, conserved by a hop | §3g |
| $m_c$ | number of controls of a multiplexor (after reduction) | §3f |
| $W$ | Walsh–Hadamard matrix $W_{cS}=(-1)^{\lvert S\cap c\rvert}$, size $2^{m_c}$ | §3f |
| $S$, $a_S$ | a mask (subset of controls) and its Walsh coefficient | §3f |
| $Z_S$, $Y_t$, ${\rm CX}_S$ | $\prod_{i\in S}Z_i$; Pauli $Y$ on the target $t$; CNOTs from every control in $S$ to $t$ | §3f |
| $s$ (support) | number of nonzero nonempty masks | §3f |
| $\mathcal O$, $\Pi(\theta)$ | $\theta$-independent orthogonal basis change and pair-rotation round: $e^{\theta A}=\mathcal O^T\Pi(\theta)\mathcal O$ | §3h |
| $d_i$ | pair coupling ($D=U^TKV$, $d_i=D_{ii}$) | §3h |
| $V_i$, $U_i$, $v_i$ | computed step (gate + pruning + rounding), exact step, computed state before step $i$ | §5.2 |
| $G$, $G'$ | exact $2\times2$ gate matrix; the matrix the simulator uses | §5.2 |
| $u$, $\gamma_2$, $\mu$, $\gamma$ | $u=2^{-53}$; $\gamma_2=2u/(1-2u)$; $\mu=\sqrt2\gamma_2$; $\gamma=\mu+u+\mu u$ | §5.2 |
| $\epsilon_{\rm prune}$, $\epsilon_{\rm round}$ | pruned norm and rounding bound of the certified simulation | §5.2 |
| $\beta_{\rm Q1L}$ | the package's native-conversion rounding bound (Q1L) | §3k |
| $f_{\rm pkg}$, $f_{\rm full}$ | package gate-only clean-shot fraction; noise agent's full-model clean-shot fraction | Glossary, §9 |

The letter $B$ is used for nothing except the sector label $2B$.

---

## Glossary

| term | meaning |
|---|---|
| qubit, gate | a two-level memory element; an elementary operation on one or two qubits |
| ZZ count | number of two-qubit gates (CX, CZ, controlled phase, RZZ); each becomes one Quantinuum `ZZPhase` in the package's conversion |
| two-qubit depth | longest chain of two-qubit gates in the as-soon-as-possible schedule, one-qubit gates free (pytket `depth_2q`) |
| IR | the package's gate list: tuples `(name, [qubits], parameter)` (`skqd.circuits_ir`) |
| codeword | a bit string of the register that encodes a gauge-invariant basis state |
| dressed basis | the package's basis of gauge-invariant states $(\{j_l\},\{n_x\},\{\iota_x\})$; term matrices are given on it |
| intertwiner | the label $\iota$ of the independent SU(2) singlets (Gauss-law solutions) of one vertex; here only an interior vertex with three $j=\tfrac12$ ends and $n=1$ has two ($\iota\in\{0,1\}$) |
| vertex bit | the last qubit of a vertex block: $n/2$ when the flux parity is even, $\iota$ when all three ends carry flux at an interior vertex, otherwise 0 (1 = flag) |
| bright / dark state | of two intertwiner states coupled by a term to the same partner: the combination the term reaches / the orthogonal one it annihilates |
| sector | the basis states with a given $2B$ |
| term group | a summand $H_\gamma$ exponentiated as a whole in the coarse step |
| coarse step | $U_k=\prod_\gamma e^{-i\,k\,dt\,H_\gamma}$ (package order, first group first) on one reference |
| block | a connected component of the graph of a term's matrix |
| multiplexor | a uniformly controlled rotation: one target qubit rotated by an angle that depends on control qubits |
| Walsh support | number of nonzero nonempty-mask coefficients of a multiplexor's angle table |
| Gray code (chain) | an ordering of all $2^{m_c}$ masks with neighbours differing in one bit; the package's multiplexor walks it ($2^{m_c}$ CNOTs) |
| 2-opt | local search for travelling-salesman tours (reverse a segment when that shortens the tour); used to order masks |
| frame (my label) | a cheap change of basis applied before a term and undone after it |
| clean ancilla | a support qubit that is $\lvert0\rangle$ on every codeword because its information is duplicated elsewhere |
| flag (my label) | an AND of a few bits written into a clean ancilla to control a multiplexor |
| relative-phase Toffoli | a Toffoli correct up to a diagonal phase; **Margolus** form: 3 CNOTs, 2 controls; **RC3X**: 6 CNOTs, 3 controls (Maslov 2016; qiskit `RC3XGate`); used only as compute…uncompute |
| class A / class B | operator-exact (all codewords) / exact only on the circuit's own reference input |
| reachable set | codewords that can carry amplitude before a term, from the reference, computed from the Hamiltonian's graph |
| contract | the local strings a class-B term must be exact on (all strings of the touched blocks) |
| skeleton | a gate list without angles |
| MILP | mixed-integer linear programme (HiGHS via `scipy.optimize.milp`) |
| PhasedX | Quantinuum's native one-qubit gate (rotation about an axis in the XY plane) |
| Q1L | the package's conversion proof (`skqd.quantinuum_native.local_equivalence_35a`): native level-0 circuit = IR circuit (two-qubit skeleton, one-qubit segments, rounding bound $\beta_{\rm Q1L}$) |
| Q0P, Q1, Q2, Q5 | the package gate "Q0P" (Quantinuum preparation, `<root>/validation/Q0P_2x3.json`) and its criteria: **Q1** native circuits exact (state bar), **Q2** two-qubit count equal over the family (in particular equal across $k$), **Q5** HQC (Quantinuum billing units) per shot |
| $f_{\rm pkg}$ | package gate-only clean-shot fraction $(1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{\rm ro})^{n_m}$, $n_{1q}$ = PhasedX count, $n_m$ = number of qubits (`skqd.device_req.clean_shot_fraction`, numbers from `<root>/data/quantinuum/devices_20261002.json`) |
| $f_{\rm full}$ | the noise agent's full-model fault-free fraction (gate, idle/memory and readout Pauli channels from published data; `noise/reports/002-noise-models.md`); smaller than $f_{\rm pkg}$ |
| $f_{\rm hit}$, $f_{\rm ideal}$, $r_{\rm nc}$, acceptance, TV | noise-report quantities: reference-string hit fraction over its ideal probability; fraction of shots within total-variation distance $10^{-3}$ of ideal; $r_{\rm nc}=f_{\rm hit}/f_{\rm ideal}(10^{-3})$ (near-clean ratio of the package's trajectory gate **CF_traj**, `<root>/reports/CF_traj.md`); fraction decoded into the right sector; total-variation distance $\tfrac12\sum_s\lvert q_s-p_s\rvert$ |
| H2-2, H1-1, Helios-1 | Quantinuum device rows of `<root>/data/quantinuum/devices_20261002.json` (H1-1 has 20 qubits) |
| owner decisions C1–C6 | the owner's signed decisions in `notes/008` (C1/C2 naming and separation, C3 2x3, C4 one more 2x4 round, C5 noise tests, C6 no backend access) |
| genie-opus | the study agent that wrote this manual |

---

## 1. Purpose and results

### 1.0 The model being compressed

All of this is the package's fixed convention; a new project must map its own model onto it, or adapt (§2.3, §4).

**Lattice** (`<root>/src/skqd/lattice.py`, module docstring and `Ladder`): open $2\times L_x$ ladder, sites
$x=(x_1,x_2)$, $x_1=0..L_x-1$, $x_2\in\{0,1\}$, index $x_1L_y+x_2$; links oriented $+x$ and $+y$, listed by start site
(x-link before y-link); every link goes from a lower to a higher site index.  Plaquettes: corners $c_{00},c_{10},c_{11},
c_{01}$ counter-clockwise from the lower-left; bottom and right links forward, top and left backward ($U^\dagger$).
Phases $\eta_l=i$ on x-links, $(-1)^{x_1+x_2}$ of the start site on y-links.

**Hamiltonian** (Kogut–Susskind with staggered quarks; `<root>/src/skqd/hamiltonian.py` docstring lines 4–9,
`Terms.H` lines 62–68, `Terms.groups` lines 70–77):
$$H=-\tfrac12\sum_{l=(x\to y)}\bigl[\eta_l\,\psi^\dagger_{x}U(l)\psi_{y}+{\rm h.c.}\bigr]+m\sum_x(-1)^{x_1+x_2}n_x
+\frac{g^2}{2}\sum_lE_l^2-\frac1{2g^2}\sum_P\bigl(W_P+W_P^\dagger\bigr),$$
$E_l^2=j_l(j_l+1)$, $W_P$ the plaquette trace (counter-clockwise from the lower-left corner).  Hop sign
$s_{\rm JW}=\prod_{x<z<y}(-1)^{n_z}$ (docstring).  **Term groups** (`Terms.groups`):
$$H_{\rm diag}=m\,H_{\rm mass}+\tfrac{g^2}{2}H_E,\qquad H_{{\rm hop}_l}=-\tfrac{\eta_l}{2}\psi^\dagger_xU\psi_y+{\rm h.c.},\qquad
H_{{\rm plaq}_p}=-\frac{W_p+W_p^\dagger}{2g^2}.$$
Parameters: $g^2=4$ (`src/c2x4/problem.py:30`, `G2`), $m=3g^2/16=0.75$ (`skqd.exact.mass_default`,
`<root>/src/skqd/exact.py:28`).  **Truncation:** $j_{\max}=\tfrac12$ (`Model(Lx, jmax=0.5)`, `exact.py:93`;
`skqd.basis.enumerate_basis`), so every link is one bit.

**Basis and sectors** (`<root>/src/skqd/basis.py`): dressed states $(\{j_l\},\{n_x\},\{\iota_x\})$ satisfying Gauss's law at
every vertex (singlets of the vertex generators, `<root>/src/skqd/vertex.py`).  $2B=\sum_x(n_x-n_{\rm vac}(x))$ with
$n_{\rm vac}=0$ on even sites and 2 on odd sites (the Dirac sea).  Sectors used: $2B=0$ and $2B=2$.

**Vertex encoding** (`<root>/src/skqd/codec.py` docstring lines 9–14; little-endian, qubit $k$ = bit $k$; widths and
offsets from `Codec`):

| vertex | qubits | meaning |
|---|---|---|
| corner (2 link ends) | 3: $(q_1,q_2,q_3)$ | $q_1,q_2$ = flux bits of the two link ends (link-index order, $j=\tfrac12\leftrightarrow1$); $q_1=q_2\Rightarrow n\in\{0,2\}$, $q_3=n/2$; $q_1\neq q_2\Rightarrow n=1$, $q_3=0$ ($q_3=1$ is a flag = leakage) |
| interior (3 link ends) | 4: $(q_1,q_2,q_3,q_4)$ | $q_1..q_3$ flux bits; even number of fluxes $\Rightarrow q_4=n/2$; one flux $\Rightarrow n=1$, $q_4=0$ (1 = flag); three fluxes $\Rightarrow n=1$, $q_4=\iota$ (intertwiner = intermediate spin $J_{12}\in\{0,1\}$ of the first two link ends, `vertex.py` line 18) |

Every link is stored twice (once at each end); codewords have equal copies.  Registers
(`examples/structure_checks/structure_checks.json`, keys `codec_widths`, `n_qubits`, `dim`) **[num]**:

| lattice | vertex widths | qubits | basis states |
|---|---|---|---|
| 2x2 | [3, 3, 3, 3] | 12 | 82 |
| 2x3 | [3, 3, 4, 4, 3, 3] | 20 | 1 727 |
| 2x4 | [3, 3, 4, 4, 4, 4, 3, 3] | 28 | 37 165 |

**Dark and bright states, physically.**  An interior vertex in the all-flux $n=1$ state has two singlets ($\iota=0,1$).
A plaquette (or hop) changes the flux on two (or one) of that vertex's links; its corner (vertex) factor maps a fixed
partner state onto one combination of the two singlets (the *bright* state) and annihilates the orthogonal one (the
*dark* state).  The circuits rotate $\iota$ so that bright and dark become basis states, then treat the dark state as
"this term does nothing here".

**References** (`skqd.krylov.references`, `<root>/src/skqd/krylov.py:82-116,145`): at $2B=0$ the Dirac sea plus one
*one-meson* state per link (quark on the link's even end, hole on its odd end, flux $\tfrac12$ on that link, all
$\iota=0$); at $2B=2$ one *diquark* state ($n=2$) per even site, no flux.  So $1+n_{\rm links}$ references at $2B=0$ and
$n_{\rm even}$ at $2B=2$: 5+2 (2x2), 8+3 (2x3), 11+4 (2x4).

**Time step:** $dt=\pi/W_{2B}$, $W_{2B}=E_{\max}-E_0$ of $H$ in the sector (`SectorReference.dt`, `exact.py:53`).
**Circuits:** $k=1..4$ at 2x2 and 2x3 (28 and 44 circuits), $k=1..5$ at 2x4 (75 circuits).

**How to map your model:** split your Hamiltonian into (i) a diagonal part and (ii) local off-diagonal terms each on a
known support (here one hop per link and one plaquette per plaquette), in a fixed order that defines your target; your
encoding must give each term's matrix restricted to its local codewords.  If your terms are $T+T^\dagger$ with
non-Hermitian $T$ (all off-diagonal terms here are), the factorisation tests apply to $T$ (§4).

### 1.1 What problem the technique solves

The package's own circuits (the *frozen* families) are built term by term with a generic exact synthesis (block-wise SVD
rounds and Gray-code multiplexors, `skqd.circuits_ir.structured_term_gates`).  At 2x4 that gave 71 548 two-qubit gates
per circuit.  The technique exploits exact structure — vertex/corner factorisation, uniform hop couplings in a frame,
the duplicated link copies, the small reachable set of a basis state — to compress every term at the package's bar.

### 1.2 Results

**Bar** (package plan `<root>/prompts/35b_2x4_exactness_ruling.md`, item R1): for every (reference, $k$), the circuit's
state against the exact coarse state `skqd.krylov.coarse_states` (complex128): $\max_s\lvert\psi_se^{-i\varphi}-t_s\rvert<
10^{-10}$ after removing the global phase $\varphi=\arg\langle t\vert\psi\rangle$, and leakage $<10^{-9}$.

| lattice | family | circuits | ZZ (min–max, mean) | 2q depth | accuracy (max) | $f_{\rm pkg}$ H2-2 (mean) | independent checks | sources |
|---|---|---|---|---|---|---|---|---|
| 2x2 | frozen (package) | 28 | 252 | 201 | package Q1 | 0.793 | package | `<root>/data/quantinuum/circuits_2x2/index.json`, `…/B0_ref06_k1.manifest.json` (`levels.0.counts`), `<root>/validation/Q0P_2x2.json` (`data.Q5.devices.quantinuum_h2_2.f_gate_only_mean`) |
| 2x2 | **worked example** (not a family) | 28 + 28 | A 245; B 55–162 (119.4) | A 188; B 45–137 | certified A $2.02\times10^{-13}$, B $1.37\times10^{-13}$; Aer A $1.10\times10^{-14}$, B $6.93\times10^{-15}$ | not computed | own Aer + random superposition, same script (§1.3) | `examples/2x2_sandbox/results.json` |
| 2x3 | frozen (package) | 44 | 2 158 | 1 925 | package Q1 | 0.150 | package | `<root>/data/quantinuum/circuits_2x3/index.json`, `…/B0_ref25_k1.manifest.json`, `<root>/validation/Q0P_2x3.json` (`data.stage_A.predict.devices.quantinuum_h2_2`) |
| 2x3 | `compressed_circuit_llm_2x3_classA` | 44 | **871** | 611 | certified $9.41\times10^{-13}$; Aer $3.05\times10^{-14}$ (44/44) | **0.445** | noise agent own-reference Aer 44/44; **no random-superposition test** | `data/c2x3/eval_arch_L3_it1_operator_pp2_all44_pruned.json`, `data/c2x3/aer_compressed_circuit_llm_2x3_classA.json`, `data/c2x3/native_compressed_circuit_llm_2x3_classA.json`, `noise/reports/003-noise-results.md` §3.1 |
| 2x3 | `compressed_circuit_llm_2x3_classB` | 44 | **309–465 (387.6)** | 170–290 | certified $4.37\times10^{-13}$; Aer $2.10\times10^{-14}$ (44/44) | **0.692** | noise agent own-reference Aer 44/44 | same paths, `input` / `classB` |
| 2x4 | frozen (structured source) | 75 | 71 548 | 70 300 | package Q1 | $4.18\times10^{-29}$ | package | `<root>/data/quantinuum/circuits_2x4/B0_ref102_k1.structured.manifest.json`, `<root>/validation/QN_2x4.json` (`data.analytic.devices.quantinuum_h2_2.f_gate_only_mean`) |
| 2x4 | `…_2x4_classA_v1` | 75 | 1 736–1 740 (1 739.2) | 1 275–1 280 | certified incl. rounding $1.72\times10^{-12}$ | 0.2005–0.2009 (4 circ.) | reviews/001: 4 own-reference Aer + **8 random-superposition runs** | `data/eval_arch_it5_operator_pp_all75_pruned.json`, `data/rounding_v1.json`, `data/native_it5_operator.json`, `reviews/001-independent-verification.json` |
| 2x4 | `…_2x4_classB_v1` | 75 | 582–800 (683.5) | 292–469 | certified incl. rounding $7.72\times10^{-13}$ | 0.4718–0.5751 (4 circ.) | reviews/001: 5 own-reference Aer | `data/eval_arch_it5_input_pp_all75_pruned.json`, `data/rounding_v1.json`, `data/native_it5_input.json` |
| 2x4 | `…_2x4_classA_v2` | 75 | **1 492** | **948** | certified $1.75\times10^{-12}$ | **0.2512** | noise agent own-reference Aer 40/75; my sample 1; **no random-superposition test** | `data/eval_arch_it6_operator_pp2_all75_pruned.json`, `data/aer_compressed_circuit_llm_2x4_classA_v2_sample_B1_ref230_k5.json`, `data/native_compressed_circuit_llm_2x4_classA_v2.json` |
| 2x4 | `…_2x4_classB_v2` | 75 | **580–763 (675.0)** | 292–429 | certified $7.70\times10^{-13}$ | **0.5293** (0.4881–0.5763) | noise agent own-reference Aer 75/75; my sample 1 | `data/eval_arch_it6_input_pp2_all75_pruned.json`, `data/aer_compressed_circuit_llm_2x4_classB_v2_sample_B0_ref345_k1.json`, `data/native_compressed_circuit_llm_2x4_classB_v2.json` |

- "Certified" = measured deviation + pruned norm + floating-point rounding bound (§5.2).
- **Independent verification, stated plainly:** the random-superposition operator test (§5.4) was run by an
  independent agent only on **v1 class A** (`reviews/001`, 8 runs), and by me (same sandbox script) on the **2x2 worked
  example**.  It has **not** been run on `compressed_circuit_llm_2x4_classA_v2` or `compressed_circuit_llm_2x3_classA`;
  for those, class-A exactness rests on my term checks over every codeword column (§5.1) and on own-reference Aer runs.
  The noise agent's counts (40/75, 75/75, 44/44) are from `noise/reports/003-noise-results.md` §3.1 when read and may
  grow.
- $f_{\rm pkg}$ is the package's gate-only model; it is **not** the $f_{\rm full}$ of the noise report (§9).
- Ratios to the frozen circuits (from the table): 2x4 class A v2 48×, class B v2 106×; 2x3 class A 2.48×, class B 5.57×;
  2x2 example class A 1.03×.

### 1.3 2x2: a worked example, not a family

> **Update 2026-10-28:** the owner asked for 2x2 families; they now exist as `compressed_circuit_llm_2x2_classA` /
> `_classB` (built with the production scripts, `--lx 2`; `notes/011-2x2-families.md`, numbers in
> `data/c2x2/summary_2x2.json`).  The sandbox example below stays a teaching example; its circuits are not the families.

I did not make 2x2 *families*; the owner decides whether they are made.  The planner judged that 2x2 has little to gain:
"Already 252 ZZ with $f=0.79$ on H2-2 … Apply the technique only for uniformity of the hardware story; no cost case"
(`notes/007-planner-review-ultimate-compression.md` §8.3).  For this manual I ran the whole procedure on 2x2 as a
**worked example** in a sandbox: `python 2x4_compression_using_ai_v1/examples/2x2_sandbox/run_2x2_example.py`, output
`examples/2x2_sandbox/results.json` (commit `6ca9520`, parameters, seeds, machine recorded).  Its circuits are not named
`compressed_circuit_llm_2x2_*` and are not in `src/c2x4/families.py`; do not use them.

Inputs it confirms (same file): 12 qubits, 82 basis states, terms `diag, hop0..hop3, plaq0`; references
`[6, 43, 30, 21, 17]` and `[14, 7]`; $dt$ = 0.24501194722475933 and 0.33194310785049674 (identical to the frozen
manifests).  Results **[num]**:

| quantity | class A | class B | key in `results.json` |
|---|---|---|---|
| best proposal per term | hop0 `full_lin` 64, hop1 `full_lin` 52, hop2 `full_lin` 64, hop3 `full_lin` 52, plaq0 `cfg_lin` 34 | per reference | `per_term_class_A` |
| ZZ count (28 circuits) | 245 on all | 55–162, mean 119.43 | `class_A`, `class_B` |
| two-qubit depth | 188 | 45–137 | same |
| certified pruned check (incl. rounding) | 28/28, max $2.02\times10^{-13}$, leakage $\le3.6\times10^{-26}$ | 28/28, max $1.37\times10^{-13}$, leakage $\le1.7\times10^{-26}$ | same |
| skeleton identical for $k=1..4$ | yes | yes | same |
| Aer statevector, own reference, package target | 28/28, max $\lvert\Delta\psi\rvert$ $1.10\times10^{-14}$, leakage $\le8.8\times10^{-32}$ | 28/28, max $6.93\times10^{-15}$, leakage $\le1.2\times10^{-31}$ | `aer.A`, `aer.B` |
| class-B global phase − $\theta(H_{\rm diag})_{rr}$ | — | $\le6.0\times10^{-15}$ rad | `aer.B.max_abs_phase_minus_predicted` |
| random superposition ($2B=0$, 38 states, `B0_ref6_k2`, seeds 11/12): $\lVert\Delta\psi\rVert_2$ | $8.48\times10^{-15}$ / $8.20\times10^{-15}$ | 1.112 / 0.999 (expected failure) | `aer.random_superposition` |
| wall time | 27.5 s total, loop 17.5 s | | `wall_s`, `loop_wall_s` |

Class A uses 245 ZZ against the frozen 252: a small gain, as the planner expected.  $f_{\rm pkg}$ was not computed (it
needs the pytket venv and a 2x2 branch in `scripts/native_family.py`).  To make families: decide with the owner, then
make the bookkeeping edits of §2.5 and use the production scripts.

---

## 2. Prerequisites and inputs

### 2.1 What the method needs from a project

| input | what exactly | where it came from here |
|---|---|---|
| codeword set and qubit layout | codewords as integers (qubit $k$ = bit $k$), and per vertex which qubits hold which link ends and the vertex bit | `skqd.reference_sim.CodewordEmbedding(Model(Lx))` → `.ints`, `.codewords`, `.codec` (`widths`, `offsets`, `decode_vertex`); `skqd.lattice.Ladder` (`ends()`, `links`, `plaquettes`) |
| term groups | the Hamiltonian as an ordered dict of sparse matrices on the dressed basis | `Model(Lx).terms.groups(g2, m)` |
| term support and local matrix | support qubits, local codewords $C$, and $h$ = the term restricted to $C$ | `skqd.reference_sim.term_support`, `localize(model, H, support)` → `(states, h, pos)`; `src/c2x4/problem.py:Problem.local` |
| reference states | basis indices of the inputs, per sector | `skqd.krylov.references(basis, twoB)` |
| $dt$, $k$ | $\theta=k\,dt$ | 2x4: `<root>/data/quantinuum/circuits_2x4/index.json` (copied from `<root>/validation/E3.json`), $k=1..5$; 2x3 manifests, $k=1..4$; otherwise `Model(Lx).reference(g2, 2B).dt` |
| exact reference | target state of each circuit | `skqd.krylov.apply_groups(mats, basis_vector(dim, r), k*dt)` = `coarse_states(...)[k]`; `Problem.target` |
| baseline circuit | the frozen IR of each term (reproduce it first) | `skqd.circuits_ir.CircuitFactory(Model, g2)`: `hop_gates`, `plaq_gates`, `diag_gates`, `prepare`; `Problem.baseline_term_ir` |
| device numbers (optional) | $\varepsilon_2,\varepsilon_1,\varepsilon_{\rm ro}$ | `<root>/data/quantinuum/devices_20261002.json` |

### 2.2 Questions to ask in a new project

1. Which term order defines the target?  (Here fixed; only disjoint-support terms may be reordered — **[Lean]**
   `kron_disjoint_comm`, `lean/Compress2x4/Sanity.lean`.)
2. What does each qubit of a vertex mean (§1.0 table)?  Are links stored once or twice?
3. Is every term local, with matrix $h\otimes1$ on codewords?  (Here the package's `localize` guarantees it.)
4. Bit order (here little-endian)?
5. The accuracy bar: phase-aligned?  How is leakage defined?
6. Which inputs will the circuits see?  (One basis state → class B possible; anything else → class A only.)
7. Device and native gate set (here Quantinuum ZZPhase; IBM adds routing)?
8. Fermion ordering, and where do its signs sit?
9. Real matrix elements in some diagonal gauge?  (`skqd.circuits_ir._real_gauge`; here yes.)
10. What is frozen and must not change (conventions, references, $dt$)?

### 2.3 If the encoding differs

- **Links stored once:** no duplicated-link ancillas.  Compute the affine $\mathbb F_2$ relations of the occupied strings
  (`src/c2x4/plaqfactor.py:f2_relations`); each relation is a qubit a CNOT network can clear.  If there is none, flags
  need an extra qubit or must be dropped.
- **Vertex label of more than one bit:** the factorisation tests still apply; blocks get bigger; the corner frame must be
  rewritten (§4.2).
- **Other bit order:** translate at the boundary; the study code assumes qubit $k$ = bit $k$.
- **Complex matrix elements without a real gauge:** the angle-linear block rounds (§3h) refuse such blocks
  (`NotImplementedError`); replacement in §4.3.

### 2.4 Sandbox recipe (read before running anything)

**Warning 1 — evidence files are overwritten.**  The production scripts write to fixed paths inside the study:
`scripts/loop_select.py` writes `data/archive_<label>.json` through `src/c2x4/env.py:archive_path`,
`scripts/eval_family.py` writes `data/{,c2x3/}eval_*.json`, `scripts/certify_family.py` `data/cert_*.json`,
`scripts/native_family.py` `data/native_*.json`.  Re-running §12.4 *as run here* overwrites the files behind §1.2.
**Never run them in this repository with the cited labels.**

**Warning 2 — the disk cache does not know the code version.**  `src/c2x4/family.py:_cached` keys a gate list only by
(proposal tag, reference, term, $\theta$); `Problem.cpath` by name; the MILP cache (`certify.cached_min_walsh_support`) by
the table.  **If you change a proposal, delete the cache** (`data/cache/` here, `cache/` in a sandbox), or you will
silently get the old circuits.

**Sandbox, in-process** (exactly what `examples/2x2_sandbox/run_2x2_example.py` lines 37–46 do; do it before importing
any builder):

```python
import sys; sys.path.insert(0, "<root>/2x4_compression_using_ai_v1/src"); sys.path.insert(0, "<root>/src")
import c2x4.env as env
SCR = "/path/to/scratch"
env.CACHE = SCR + "/cache"
env.archive_path = lambda label: f"{SCR}/archive_{label}.json"
import c2x4.problem as problem; problem.CACHE = env.CACHE
import c2x4.family as family;   family.CACHE = env.CACHE
# then import c2x4.proposals, c2x4.family.family_from_spec, c2x4.evaluate, ...; write results with
# env.write_json(<absolute path in SCR>, payload, produced_by=..., parameters=...)
```

The loop, assembly and verification are then plain function calls (see the example script); nothing under `data/` is
written.  The production scripts have no `--out` option; if you use them, copy the study folder first.

### 2.5 Porting effort (honest list)

**(i) Package interface** (public names, §12.5): `Model`, `mass_default`, `apply_groups`, `coarse_states`, `term_groups`,
`basis_vector`, `references`, `CodewordEmbedding`, `localize`, `term_support`, `CircuitFactory`, `structured_term_gates`,
`run_ir`, `SparseState`, `apply_ir`, `run_sparse`, the `quantinuum_native` converter and proof, `clean_shot_fraction`.
Your project needs equivalents.

**(ii) Private synthesis helpers of `skqd.circuits_ir`.**  A grep of `src/c2x4/*.py` today finds 14 distinct private names
imported directly: `_FLIP2`, `_I2`, `_axis_angle`, `_basis_change_to_y`, `_bipartition`, `_block_rounds`, `_frame_cnot`,
`_gauge_gates`, `_generic_two_level`, `_multiplexed_two_level`, `_pack`, `_phase_su2`, `_real_gauge`, `_reduce_controls`.
They call further private functions (`_in_span`, `_echelon`, `_uc_u2`, `_uc_phase`, `ucr_gray`, `_zyz`, …); the review
counted 17 names in this manual's first version.  **Copy `<root>/src/skqd/circuits_ir.py` whole** rather than
re-implementing.

**(iii) Lattice-specific code in the study:**

| item | where | what to change |
|---|---|---|
| $g^2=4$ fixed | `src/c2x4/problem.py:30` (`G2`) | make it a parameter |
| sectors `twoB in (0, 2)` | `problem.py:50,57,63,68`, `reach.py:167` | your sector labels |
| $dt$ sources ($L_x\in\{3,4\}$ special-cased) | `Problem.__init__` | your $dt$ rule |
| ladder geometry | `plaqfactor.corners_of` (keys `c00..c01`, one "third" link), `hopframe.vertex_parity_frame`, `vertex_bright_frame_clean` (two ends of a link, `Ladder.ends`) | your lattice description; vertices with more links need the frames of §4 |
| 2x4 term names | `src/c2x4/proposals.py:69-90` (`pkg`, `rpkg`, `cf2`, `*_sw` list `hop0..hop9`, `plaq0/plaq2`, `plaq1`) | use the lattice-generic classes (`"hop"`, `"plaq"`, `"hop+plaq_small"`, `"plaq_interior"`) as the C4 proposals do |
| output folders and baselines only for $L_x\in\{3,4\}$ | `env.archive_path` (only `L3_` → `data/c2x3/`); `scripts/eval_family.py` (`baseline` block and `sub` folder — any other $L_x$ would be labelled with the 2x3 baseline 2 158); `certify_family.py`, `verify_aer_family.py`, `native_family.py` | add your lattice; add names to `families.FAMILY_NAMES` |
| circuit ids | `Problem.tag` writes `B0_ref6_k1`; the package's 2x2 files write `B0_ref06_k1` | keep one, record the mapping |
| block sizes | `plaqfactor.corner_frame`, `hopframe._bright_rotations` raise for blocks other than size 2 and 3 | rewrite (§4.2) |
| encoding assumptions | `hopframe` folds parity into the hop-link qubit; `codec.decode_vertex` reads $n$ | your encoding's $n$ and parity |

**Effort [heur]:** for an SU(2) $j_{\max}=\tfrac12$ ladder in this encoding, hours (the 2x2 example ran unchanged); for a
different encoding, gauge group or geometry, days, dominated by (iii) and the frame rewrites of §4.

---

## 3. The procedure, step by step

```
(a) harness ─► (b) structure tests ─► (c) plaquettes: corner frames + one rotation ─► (d) signs over F2
     ─► (e) clean ancillas + flags ─► (f) sparse-Walsh multiplexors + MILP certificates
     ─► (g) hops: vertex frames, flags, JW sign ─► (h) angle-linear synthesis (k-independent)
     ─► (i) class B restriction ─► (j) peephole + CX-run resynthesis ─► (k) native conversion
```

Every construction is a **proposal**: a function `(P, name, theta, contract_states|None, reach_local|None) -> gate list`,
registered in `src/c2x4/proposals.py:PROPOSALS` and judged only by the evaluator.

### (a) Evaluator harness — reproduce the baseline first

**Purpose.**  An evaluator that shares no construction code with any proposal and reproduces the package exactly.

**Math.**
- *Counts* (`src/c2x4/evaluate.py:counts`): ZZ count and two-qubit depth; multi-qubit `unitary` gates refused.
- *Term check (A1), all columns in one run* (`term_unitary_columns`, `verify_term_operator`): append
  $\lceil\log_2\lvert C\rvert\rceil$ index qubits, start from $\sum_{s\in C}\lvert s\rangle\lvert{\rm idx}(s)\rangle/\sqrt{\lvert C\rvert}$,
  run the exact sparse simulator; the amplitude on $\lvert o\rangle\lvert{\rm idx}(s)\rangle$ is $U_{os}/\sqrt{\lvert C\rvert}$,
  so one run yields every column of the candidate's unitary $U$; compare with $e^{-i\theta h}$.  With a contract: only
  those columns.
- *Circuit check (A2)*: `verify_circuit_pruned` (§5.2).

**Decision rule.**  Do not compress until the harness reproduces the frozen numbers.  Here: 71 548 ZZ and depth 70 300 on
`B0_ref102_k1`, state deviation $4.54\times10^{-14}$, every frozen term on all codeword columns to $\le4.1\times10^{-13}$
(`data/p2_0_harness_baseline.json`, `scripts/p2_0_harness_baseline.py`) **[num]**.

### (b) Structure tests

**Purpose.**  Find the exact structure first; everything below was found by these tests.

**Runnable for any $L_x$ of this package:** `python 2x4_compression_using_ai_v1/examples/structure_checks/run_structure_checks.py`
(sandboxed; output `examples/structure_checks/structure_checks.json`, 2x2, 2x3 and 2x4).  The older
`scripts/p2_1_structure.py` is tied to 2x4 (it calls `get_problem()` with the 2x4 default, hard-codes three plaquettes
and the references 102/345/230, and writes `data/p2_1_structure.json`); use it only as a reference.

1. **Blocks bipartite with zero diagonal** (`run_structure_checks.py:blocks`, with `src/c2x4/reach.py:components` and
   `skqd.circuits_ir._bipartition`): true for every term at 2x2, 2x3 and 2x4; largest block 3 (2x2), 5 (2x3), 9 (2x4,
   plaq1) (`terms.*.largest_block`) **[num]**.  This is what makes the block rounds of step (h) possible.
2. **Plaquette corner factorisation** $h_P\big\vert_C=A_{c_{00}}\otimes A_{c_{10}}\otimes A_{c_{11}}\otimes A_{c_{01}}$, $A_c$
   real on corner $c$'s qubits (`src/c2x4/plaqfactor.py:factorise`: least squares on $\log\lvert h\rvert$, signs over
   $\mathbb F_2$, then the product compared on every codeword column and every row of the $2^k$ local space): product
   residual $\le2.2\times10^{-16}$ (2x2), $\le2.6\times10^{-15}$ (2x3, 2x4) (`summary.max_plaq_product_residual`) **[num]**.
3. **Hop factorisation — a real product check.**  `src/c2x4/hopframe.py:hop_vertex_factors` only fits $\log\lvert T\rvert$
   and raises if the sign system is inconsistent; it never forms the product.  `run_structure_checks.py:hop_checks`
   keeps all three factors ($a_v$, $b_w$, and the factor on the qubits outside the two vertices), forms
   $\eta\,a_v\otimes b_w\otimes(\cdot)$ on every raising element and compares it with $h$: product residual
   $\le4.4\times10^{-16}$ (2x2), $\le1.1\times10^{-15}$ (2x3), $\le1.3\times10^{-15}$ (2x4) (`summary.max_hop_product_residual`);
   signs factorise for every hop **[num]**.  (The "residual $\le2.7\times10^{-15}$" of earlier reports is the log-magnitude
   fit residual of `p2_1_structure.py`, not a product residual.)
4. **Equal-step three-level chains:** for every $n=0$ state $s_0$ of a vertex with $u=Rs_0\neq0$ ($R$ = the raising factor,
   $a_v$ or $b_w^T$): $\bigl\lvert\lVert Ru\rVert/\lVert u\rVert-\lVert u\rVert\bigr\rvert\le1.3\times10^{-15}$ on every hop of
   every lattice (`summary.max_equal_step_residual`) **[num]**: each vertex factor is an equal-step chain $0\to1\to2$ (a
   spin-1 raising operator), the bright combination included.
5. **JW sign is a parity:** for every hop with JW qubits, $h_{ij}\,(-1)^{{\rm parity}(J\text{ bits})}$ is independent of
   the JW bits and the term never changes them (`summary.all_jw_signs_are_parity_times_h0`: true; the hops with JW qubits
   in `hops_with_jw_qubits`) **[num]**.
6. **Pair-magnitude ratios at corners:** at every corner of every 2x4 plaquette the two pair magnitudes have ratio
   $1/\sqrt2$ to $\le9.4\times10^{-11}$, so on non-dark labels the plaquette angle table is
   $\Phi(x)=\pm\Phi_0\prod_c(-1/\sqrt2)^{x_c}$ ($\Phi_0$ a constant per plaquette), a product of four one-bit functions
   with exactly 16 Walsh masks (`data/planner_bounds_007.json`; planner's observation, notes/007 §5.2) **[num]**.
7. **Coefficient tables of the hop multiplexors in the bright frame:** every pair coupling is $d=0.5$ or $1.0$ for all
   ten 2x4 and all seven 2x3 hops, although the raw hop elements take 3–9 distinct magnitudes between 0.177 and 0.707
   (`data/hop_coefficient_values.json`) **[num]**.  So the hop multiplexor cost comes from zero slots and signs, not
   magnitudes — the reason for the flags of step (g).
8. **Reachable support:** `plaq1` (2x4) can touch 344–578 of its 648 non-trivial blocks from one reference, each hop 0–12
   (`data/p1_reachable_support.json`, `scripts/p1_reachable_support.py`) **[num]**.

**Decision rules.**  Exact factorisation → steps (c)/(g).  Failure → §4.6.

### (c) Plaquettes: corner frames → CNOT ladder → one multiplexed rotation

**Purpose.**  Turn a plaquette (eight link bits flipped together) into one multiplexed rotation on one qubit.

**Math.**
1. *Corner frame* (`plaqfactor.corner_frame`): apply ${\rm CX}(p_{a,c}\to p_{b,c})$; now $p_{b,c}$ holds $x_c$ and every
   pair block of $A_c$ differs only in $p_{a,c}$.  For a three-state block $s_0\leftrightarrow\{s_1,s_2\}$ (interior corner,
   $A_cs_0=v_1s_1+v_2s_2$) apply $R=\frac1{\lvert v\rvert}\begin{pmatrix}v_1&v_2\\-v_2&v_1\end{pmatrix}$ on $(s_1,s_2)$:
   bright → $s_1$, dark → $s_2$.  Then $A_c=X_{p_{a,c}}\otimes D_c(\ell)$ (checked entry by entry).
2. *Ladder:* $L=\prod_{c\neq c_{00}}{\rm CX}(p_\star\to p_{a,c})$ with $p_\star=p_{a,c_{00}}$ gives $L\,(X^{\otimes4})\,L^{-1}=
   X_{p_\star}$ **[Lean]** `xorLinear_conj_flip` (`lean/Compress2x4/Bits.lean`).
3. *One rotation:* on the occupied strings the frame generator is $X_{p_\star}\otimes{\rm diag}(\Phi)$ with $\Phi(s)$
   independent of bit $p_\star$ (checked), so
   $$e^{-i\theta X_{p_\star}{\rm diag}(\Phi)}=H_{p_\star}\,{\rm diag}\bigl(e^{-i\theta(-1)^{s_{p_\star}}\Phi(s)}\bigr)\,H_{p_\star}$$
   ($s_{p_\star}$ = value of bit $p_\star$ in string $s$) **[Lean]** `exp_xt_diag` (`Pair.lean`): a multiplexed
   $R_x(2\theta\Phi)$ on $p_\star$; term = frame$^{-1}\cdot$rotation$\cdot$frame **[Lean]** `exp_conj_frame` (`Exp.lean`);
   unoccupied strings are don't-cares **[Lean]** `exp_agree_mulVec` (`Exp.lean`).

**Pseudo-code** (`plaqfactor.cf1_gates`; with flags `cfg_gates`):

```
corners = corners_of(P, p)                          # c00, c10, c11, c01: qubits, plinks, third link, vertex bit
fac = factorise(P, name, corners)                   # raise if the signs do not factorise
frame = [corner_frame(A_c) for c in corners]        # CX(p_a -> p_b) + bright rotations of three-state blocks
frame += [CX(p_star -> p_a[c]) for c != c00]        # ladder
H2, omega = frame_generator(P, name, frame)         # F h F^dag on the occupied strings omega
assert every nonzero element of H2 flips only p_star
items = [(s0, s0 | bit(p_star), exp(-i theta Phi(s0) X)) for occupied pairs with Phi != 0]
core = skqd.circuits_ir._multiplexed_two_level(1 << p_star, items, omega, k)   # step (f) replaces it
return frame + core + invert(frame)
```

**Cost.**  Frame: 4 corner CX + bright rotations + 3 ladder CX each way, plus one multiplexor.  First result: `plaq1`
(2x4) 66 468 → 2 110 two-qubit gates with 11 controls (`data/archive_it1.json`, `operator.plaq1.candidates`, `cf1`)
**[num]**; all 1 831 columns to $3.4\times10^{-14}$ **[prose]** (report 003 §2.3.4).

### (d) Sign fixing over $\mathbb F_2$

**Purpose.**  After the frames, $\Phi$ carries label-dependent signs; remove those the multiplexor cannot absorb cheaply.

**Math.**  For each sample string $s$ let $\sigma(s)\in\{0,1\}$ be the sign bit of $\Phi(s)$.  Free sources (0 ZZ): all
monomials of the four $x_c$ (inside the table), the sign of each bright rotation ($R_y(\varphi+2\pi)=-R_y(\varphi)$
**[Lean]** `ry_add_two_pi`, `Reach.lean`), each flag $g_c$.  Costed sources: ${\rm CZ}(\tau_c,p_{a,c})$ (1 ZZ),
${\rm CZ}(q_c,p_{a,c})$ (1 ZZ), and a doubly-controlled Z on bits $(\alpha,\beta,\kappa)=(p_{a,c},\bar x_c,\tau_c)$ from 3
controlled phases and 2 CX (5 ZZ), through
$$\tfrac\pi2\bigl(\beta\kappa-(\alpha\oplus\beta)\kappa+\alpha\kappa\bigr)=\pi\alpha\beta\kappa\qquad(\alpha,\beta,\kappa\in\{0,1\})$$
**[Lean]** `ccz_phase`, `ccz_circuit` (`Bits.lean`).  Put the free sources as columns of a 0/1 matrix $\Sigma_{\rm free}$
and the costed ones in $\Sigma_{\rm cost}$ (rows = samples).  For every subset `sel` of costed sources in increasing total
cost, solve $\Sigma_{\rm free}\,y\oplus\Sigma_{\rm cost}[:,{\rm sel}]\,z=\sigma$ over $\mathbb F_2$ ($y,z$ unknown bit
vectors); the first consistent subset wins (`plaqfactor.f2_solve` inside `cf2_gates`/`cfg_gates`).  None → raise.

### (e) Clean ancillas from redundant link bits; dark-state flags

**Purpose.**  Remove controls from the plaquette multiplexor.

1. *Clean ancillas:* every link is stored at both ends; after the ladder, $p_{a,c}$ ($c\neq c_{00}$) holds
   $p_{a,c}\oplus p_\star$.  The affine relations of the occupied set (`f2_relations`) say which qubits are fixed parities
   of others; a CNOT network clears them to $\lvert0\rangle$ on every codeword (up to four per plaquette; 6 CX to clear and
   6 to restore **[prose]**, report 003 §2.4.3).
2. *Dark flags:* the dark state of corner $c$ is $(x_c=0,\tau_c=1,q_c=1)$.  A Margolus relative-phase Toffoli
   (`plaqfactor.rtof`, 3 CX) writes $g_c=\tau_c\wedge q_c$ into an ancilla; the table becomes
   $\Phi(x,g)=\Phi_{\rm nd}(x)\prod_c(1-\bar x_cg_c)$ ($\Phi_{\rm nd}$ = the non-dark table of step b item 6), with 7 controls
   for plaq1.  The relative phase cancels between compute and uncompute because the multiplexor is block-diagonal in its
   controls **[Lean]** `relphase_cancel` (`Reach.lean`), `ucr_comm_ctrl_phase` (`Conj.lean`).
3. *Which corners get a flag:* those with a dark state (a three-state block, or a valid state annihilated by $A_c$;
   `cfg_gates(flag_rule="dark")`; `"triple"` is a second proposal).

**Pseudo-code** (`plaqfactor.cfg_gates`):

```
frame = corner frames with sign corrections (step d) + ladder
rel = f2_relations(occupied strings)
pivots: cleared p_a's first, then x of corner c01; one relation per pivot
frame += CNOT networks that zero the pivots ; assert the pivots are 0 on every occupied string
frame += [rtof(tau_c, q_c -> ancilla_c) for corners with a dark state]
items = rotations with angle theta * Phi ; core = multiplexor with flag source bits first in bit order (mux_relabelled)
return frame + core + invert(frame)
```

**Cost (2x4 class A, `data/report004_tables.json` `per_term_2x4`):** plaq0 88, plaq1 202 (v2; 220 in v1), plaq2 96; 2x3:
88 and 96.  plaq1 v2: multiplexor with 7 controls, support 85, walk 92 CNOTs (`data/cert_it6_operator.json`).

### (f) Sparse-Walsh multiplexors, walk ordering, MILP certificate

**Purpose.**  The package walks all $2^{m_c}$ masks (Gray code, $2^{m_c}$ CNOTs); far fewer suffice when slots are free or
the table has structure.

**Math.**  With $W_{cS}=(-1)^{\lvert S\cap c\rvert}$ ($c$ = control value, $S$ = mask),
$$\sum_c\lvert c\rangle\langle c\rvert\otimes R_y(\phi_c)=\prod_S\exp\bigl(-\tfrac i2a_SZ_SY_t\bigr),\qquad\phi_c=\sum_SW_{cS}a_S,$$
each factor ${\rm CX}_S\,R_y(a_S)\,{\rm CX}_S$ **[Lean]** `cx_conj_yt`, `exp_conj_cx_yt`, `exp_sum_commuting` (`Ucr.lean`),
`walk_factors_comm` (`Pair.lean`).  Consecutive factors share CNOTs, so the cost is the length of a closed walk from
$\emptyset$ through the nonzero masks in Hamming distance; with $s$ nonzero nonempty masks the walk has $s+1$ edges:
**walk CNOTs $\ge s+1$**.

**Algorithm** (`src/c2x4/sparsemux.py:sw_two_level`, `sparse_walsh`, `mask_walk`; angle-linear
`src/c2x4/linsynth.py:lin_two_level`, `_solve_table`):

```
for target t in the first 3 bits of the flip pattern:
    compress the pattern onto t (CX from t to the other flipped bits)
    slot table over the other bits; occupied-but-unrotated slots fixed to identity; the rest free
    control reduction (skqd.circuits_ir._reduce_controls) + CNOT frame on the controls
    LP: minimise ||a||_1 s.t. W_fixed a = phi_fixed (HiGHS); prune greedily; exact re-solve (residual <= 1e-12)
    [MILP mode: exact minimum support]
    order masks: nearest neighbour + 2-opt; cost = walk + 2*frame + 2*(|pattern| - 1)
keep the cheapest target
```

**MILP certificate** (`src/c2x4/certify.py:min_walsh_support`; `scripts/certify_family.py`): fixed slots $F$, free angles $y$
($\lvert y_i\rvert\le M_\theta=8\pi$), $a=a_0+Ky$ with $a_0=2^{-m_c}W_{:,F}\phi_F$ and $K=2^{-m_c}W_{:,{\rm free}}$; binaries
$z_S$ with $\lvert a_S\rvert\le M_Sz_S$, $M_S=\lvert a_{0,S}\rvert+\lVert K_S\rVert_1M_\theta$; minimise $\sum_{S\neq\emptyset}z_S$.
The HiGHS dual bound is a lower bound on the support of every completion in the box; upper bounds only after an exact
re-solve; `certified_optimal` := support used = lower bound.  Meaning: minimal for this target, control reduction and
frame, HiGHS trusted **[num]**.

**Results:** 2x4 class A v2 64/65 support-optimal (support 643 vs lower bound 632, walk 750 vs 697); class B v2 813/852;
2x3 class A 43/43; class B 388/396 (`data/cert_it6_{operator,input}.json`, `data/c2x3/cert_L3_it1_{operator,input}.json`).
Open: plaq1 (85 used, lower bound 78 after 1 500 s, `data/cert_it6_operator_plaq1_long.json`).  As a synthesis option the
MILP rarely beat the LP and sometimes lost on walk length (`data/loop_it6a.log`): use it mainly to certify.

### (g) Hops: vertex factorisation, parity fold, bright frames, flags, JW sign

**Purpose.**  Compress $H_{\rm hop}=T+T^\dagger$, $T=\eta\,a_v\otimes b_w\otimes s_{\rm JW}$ (verified in step b items 3–5).

1. *Parity fold* (`hopframe.vertex_parity_frame`): at each end vertex, ${\rm CX}(f\to L)$ from the other flux bits $f$
   into the hop-link qubit $L$, so $L$ = flux parity ($n$ odd iff $L=1$): $n=0\mapsto(L,q)=(0,0)$, $1\mapsto(1,0)$,
   $2\mapsto(0,1)$, dark intertwiner $\mapsto(1,1)$.
2. *Bright frame* (`vertex_bright_frame`, `_bright_rotations`): one two-level rotation of the vertex bit where the vertex
   factor reaches two intertwiner states.  The framed generator then has only pair blocks ($N=1,3$) and three-state chains
   ($N=2$: $(2,0)$–$(1,1)$–$(0,2)$ in $(n_v,n_w)$); hop3 (2x4) then needs 5 multiplexors instead of 22 **[prose]**
   (report 003 §2.4.5).
3. *Block synthesis* (`framed_gates` → `reach.synth_on`), angle-linear (step h): a chain costs a $\theta$-independent
   basis change, one pair-rotation multiplexor, and the inverse basis change.
4. *Clean ancilla and flags* (`vertex_bright_frame_clean`, `linsynth._flag_variants`, `_flag_gates`; proposals `cb0`, `cb1`,
   `cb0_jwc`, `cb1_jwc`; the digit names which end donates its link copy): fold the donor vertex's parity into its first
   *other* flux qubit, apply its bright rotations, clear its copy of the hop link by ${\rm CX}$ from the keeper vertex's
   copy (before the keeper's fold changes it), then fold and rotate at the keeper: one clean ancilla for 1 CX each way.
   For every multiplexor the synthesis also tries a flag = AND of 2–3 control literals that is 1 on every nonzero slot
   (each literal constant on the nonzero slots; candidates ranked by how many zero slots they exclude), written by a
   relative-phase AND (Margolus 3 CX / RC3X 6 CX).  Constant multiplexors use the same path (`CONST_LIN`).
5. *JW conjugation* (`jwc_framed_gates`, proposals `jwc_*`): with the framed generator $H_2=(-1)^{{\rm par}(J)}h_0$ ($h_0$
   independent of the JW bits, tested element by element), fold ${\rm par}(J)$ into one qubit $p$, synthesise
   $e^{-i\theta h_0}$ without $J$, and conjugate every $\theta$-multiplexor's target by ${\rm CZ}(p,t)$
   ($ZR_y(\varphi)Z=R_y(-\varphi)$); valid because $e^{\theta(-A)}=\mathcal O^T\Pi(-\theta)\mathcal O$ when
   $e^{\theta A}=\mathcal O^T\Pi(\theta)\mathcal O$ **[Lean]** `z_ry_z`, `cz_conj_ucr`, `neg_generator_conj` (`Conj.lean`).

**Decision rule.**  Run all hop proposals (`full_lin`, `framed_lin`, `bframed_lin`, `jwc_*`, `cb*`, `*_milp`); keep the
cheapest verified.  Winners: at 2x4 class A `cb1`/`cb1_jwc` on interior hops, `full_lin` on corner–corner y-hops,
`bframed_lin` on hop2 (`data/report004_tables.json` `per_term_2x4`); at 2x2 `full_lin` everywhere
(`examples/2x2_sandbox/results.json`).  JW conjugation alone gains little (a parity sign only shifts masks): hop3 256 → 264
with LP (`data/loop_it6a.log`).

**Cost (2x4 class A, it5 → it6):** hop0 140→130, hop3 256→168, hop4 166→130, hop5 178→134, hop6 134→124, hop7 166→130,
hop8 116→114; hop1, hop2, hop9 unchanged (52, 110, 52); sum 1 370 → 1 144 (`per_term_2x4`).

### (h) Angle-linear synthesis — the skeleton must not depend on $k$

**Purpose.**  Gate Q0P's criterion Q2 wants equal two-qubit counts over $k$.  In v1 they varied: class A 1 736–1 740 within
every reference; class B `B0_ref1338` 760, 760, 762, 760, 762 for $k=1..5$ (`data/eval_arch_it5_input_pp_all75_pruned.json`,
`circuits.B0_ref1338_k*.counts.n_2q`; the list of affected references is `data/report004_tables.json`
`2x4.*_v1.k_dependent_references_by_count`).  Cause: decisions taken on rotation *unitaries* at the circuit's angle.

**Method** (`src/c2x4/linsynth.py`):
- A $\theta$-dependent two-level op is carried as its generator: `LinRot(G, θ)` = $e^{-i\theta G}$, $G$ fixed traceless
  Hermitian.  Every decision uses the $\theta$-free coefficient table; only emitted angles are multiplied by $\theta$.
- `lin_block_rounds`: $e^{\theta A}=\mathcal O^T\Pi(\theta)\mathcal O$, $A=\begin{pmatrix}0&K\\-K^T&0\end{pmatrix}$, $K=USV^T$, $\mathcal O$
  from $U,V$, $\Pi(\theta)$ the pair rotations $e^{\theta[[0,d_i],[-d_i,0]]}$ = `LinRot(-d_i σ_y, θ)`.  **Use $D=U^TKV$,
  $d_i=D_{ii}$, not the singular values**: the gauge fix of $U,V$ flips signs (a bug I made, §8.6).  Non-bipartite blocks
  raise `NotImplementedError`.
- Switch: `with use_linear("lp" | "milp")`; proposals `*_lin`, `*_lin_milp`, `jwc_*`, `cb*`.

**Done-check.**  `scripts/eval_family.py` stores a skeleton hash per circuit; `summary.skeleton_k_independent.all` is true
in all four new families and in the 2x2 example **[num]**.  Unit tests: `tests/test_linsynth.py`.

### (i) Class B: reachable set, dropped diagonal group, input contract

- *Reachable set* (`reach.Reach.before`): $S_\gamma$ = codewords that can carry amplitude before term $\gamma$ = the union of
  the connected components of the earlier terms' graphs reached from $r$.  An exact upper bound, independent of $\theta$
  and of every amplitude.
- *Restriction* (`restricted_term_gates`, `contract_states`): exact on every local string of the blocks touched by
  $S_\gamma$ (the contract); everything else free.
- *Why exact:* induction over the terms **[Lean]** `agree_on_reachable_n` (`Reach.lean`) with the glue
  `kron_agree_of_support`, `reindex_kron_agree`, `exp_mulVec_supported`, `exp_step_maps`, `circuit_exact_on_reachable`
  (`Glue.lean`); the hypotheses for actual circuits are numerical (§6.3).
- *Dropping `diag`:* it acts first on a basis state, $e^{-i\theta H_{\rm diag}}e_r=e^{-i\theta(H_{\rm diag})_{rr}}e_r$
  **[Lean]** `diagonal_mulVec_single` (`Sanity.lean`).  **Sign convention:** the class-B output equals
  $e^{+i\theta(H_{\rm diag})_{rr}}$ times the target, i.e. $\varphi=\arg\langle t\vert\psi\rangle=+\theta(H_{\rm diag})_{rr}$;
  recorded as `global_phase_vs_target` in the frozen metadata; measured to $\le6.0\times10^{-15}$ rad at 2x2
  (`examples/2x2_sandbox/results.json` `aer.B`) and $2.8\times10^{-14}$ rad at 2x4 (reviews/001 §3.2).
- Effect: 2x4 class B v2 580–763 ZZ against class A 1 492; hops shrink a lot (hop0 mean 10.9 vs 130), plaquettes little
  (plaq1 154.7 vs 202) (`per_term_2x4`).  The input contract is binding — §9.

### (j) Peephole and CNOT-run resynthesis

- *Peephole* (`src/c2x4/peephole.py:optimise`, `cancel_cx`, `merge_1q`): cancel identical CX pairs across gates that
  commute with them — disjoint qubits **[Lean]** `kron_disjoint_comm`; diagonal gates not on the target
  `cx_comm_diagonal_of_indep`; CNOTs where neither control is the other's target `cx_comm_cx`; X-type gates on the target
  `cx_comm_flip_target`; ${\rm CX}^2=1$ `cx_involutive` — and merge equal-axis rotations.  Gain about 4–5 % **[prose]**
  (report 003 §2.4.8).
- *CNOT-run resynthesis* (`resynth_cx_runs`): replace each maximal run of CX gates by a shorter circuit with the same
  permutation (Gaussian elimination on the GF(2) matrix and on its transpose, mirrored; background: Patel–Markov–Hayes,
  §12.6); equality checked on all $2^{\lvert Q\rvert}$ labels (`_same_permutation`) and **[Lean]** `perm_eq_of_fun_eq`
  (`Conj.lean`).  On the v1 circuits: 13–14 (class A) and 2–11 (class B) CX per circuit (`data/cxr_gain_v1.json`).
- Finishing pass `pp2` = peephole → resynthesis → peephole (`src/c2x4/family.py:finish`); structural, so $k$-independent.

### (k) Native conversion

- Isolated venv `~/.local/share/su2qc-quantinuum/venv/bin/python` (never the shared `coding` env):
  `scripts/native_family.py --family <name>` → `ir_to_pytket` → `compile_native("H2-2", optimisation_level=0)` →
  `native_counts`; Q1L `local_equivalence_35a(..., structured=True)`; `clean_shot_fraction` ($n_{1q}$ = PhasedX, $n_m$ =
  qubits) gives $f_{\rm pkg}$.
- **Workaround:** the package converter has no `cz`; rewrite as `cp(π)` (same matrix; one ZZPhase) — done in
  `native_family.py`.
- Level 0 only; level 2 rewrites gates, so Q1L does not apply (§8.2).
- Results: Q1L 75/75 (each 2x4 v2 class), 44/44 (each 2x3 class), native ZZ = IR two-qubit count,
  $\beta_{\rm Q1L}\le1.13\times10^{-13}$ (`data/native_compressed_circuit_llm_2x4_class{A,B}_v2.json`,
  `data/c2x3/native_*.json`, `summary`).

---

## 4. Generalisation guide

What the method needs in every theory: (1) exact locality of each term; (2) bipartite blocks with real elements in some
diagonal gauge (or the replacement of §4.3 item 3); (3) factorisation of each off-diagonal term over its vertices/corners;
(4) redundancy in the encoding (ancillas); (5) for class B, a small reachable set.  **Test first, construct second** (§4.6).

**Background literature (each ID verified on 2026-10-26).**  The vertex/corner factorisation is the statement that, in a
basis of local gauge singlets, gauge-invariant link operators factor into vertex-local pieces; my reading of why it holds
here (Wigner–Eckart at each vertex) is **[heur]**; the reviewer called it plausible.
- J. B. Kogut and L. Susskind, *Hamiltonian formulation of Wilson's lattice gauge theories*, Phys. Rev. D 11, 395 (1975),
  doi:10.1103/PhysRevD.11.395 — the Hamiltonian of §1.0.
- I. Raychowdhury and J. R. Stryker, *Loop, string, and hadron dynamics in SU(2) Hamiltonian lattice gauge theories*,
  arXiv:1912.06133 — SU(2) with staggered quarks in gauge-singlet variables; operators factored into "normalised" ladder
  operators and diagonal matrices (the closest analogue of the vertex factorisation).
- N. Klco, J. R. Stryker and M. J. Savage, *SU(2) non-Abelian gauge field theory in one dimension on digital quantum
  computers*, Phys. Rev. D 101, 074512 (2020), arXiv:1908.06935 — a gauge-symmetry-reduced qubit mapping, controlled
  plaquette operators and gauge-variant completions in the unphysical space (the "don't-care" idea).
- A. Ciavarella, N. Klco and M. J. Savage, *A trailhead for quantum simulation of SU(3) Yang-Mills lattice gauge theory in
  the local multiplet basis*, Phys. Rev. D 103, 094501 (2021), arXiv:2101.10227 — SU(3) in a local multiplet basis with
  controlled-plaquette operators.
- T. Byrnes and Y. Yamamoto, *Simulating lattice gauge theories on a quantum computer*, Phys. Rev. A 73, 022328 (2006),
  arXiv:quant-ph/0510027 — U(1), SU(2) and SU(3) transcribed to qubits with a link cutoff.

### 4.1 U(1)

- The plaquette is $W_P+W_P^\dagger$ with $W_P=U_1U_2U_3^\dagger U_4^\dagger$ **not Hermitian**: run the factorisation on the
  raising part $T=W_P$ restricted to local codewords.  (Here every off-diagonal term is also $T+T^\dagger$; `factorise`
  works on $h$ because $T$ and $T^\dagger$ never share an element.)
- **Spin-½ quantum links** (one qubit per link, links usually stored once): each corner factor is a scalar times a flip;
  steps (c) and (f) apply — CX frame + ladder → one multiplexed rotation whose table is the indicator of flippable
  plaquettes **[heur]**.  There is **no** duplicated-link ancilla (§2.3): flags need relations or extra qubits.  No
  intertwiners → no bright frames.  I have no U(1) count: build a single plaquette first and compare with the generic
  synthesis (§4.6, fallback 1) to know what "good" looks like.
- **Higher truncations** ($E\in[-\Lambda,\Lambda]$, $\lceil\log_2(2\Lambda+1)\rceil$ qubits per link): the link raising
  operator is a cyclic shift $\lvert E\rangle\to\lvert E+1\rangle$ (truncated), **not** a single bit flip in binary or Gray
  encodings.  Procedure: (1) write each link factor as a bipartite chain $E\to E+1$; (2) test that the plaquette's $T$
  factorises over links; (3) per link, use the SVD frame of §4.2 (a chain of length $2\Lambda+1$ splits into pairs);
  (4) compare its cost with the generic synthesis before adopting **[heur]**.

### 4.2 SU(2) at $j_{\max}>\tfrac12$

**Procedure.**
1. Run `factorise` on $T$.  Expect it to hold in a vertex-singlet basis (Clebsch–Gordan / $6j$ structure) **[heur]**; if
   not, §4.6.
2. Each corner factor $A_c$ is bipartite between "flux raised" and "flux lowered" configurations, but its blocks are now
   **rectangular** $K$ ($p\times q$, $p\neq q$ possible) and may be **rank-deficient**.  Take $K=U\,{\rm diag}(d_1..d_\rho)\,V^T$
   ($\rho$ = rank).  The $\rho$ pairs $(U_{:,i},V_{:,i})$ are the bright pairs; the left and right **kernels** (dimensions
   $p-\rho$ and $q-\rho$) are the **dark states** and must be flagged as the dark intertwiner is here (§3e).
3. The corner frame becomes an orthogonal basis change on each side that maps singular vectors to basis strings, chosen
   so that each pair differs only in the corner qubit $p_{a,c}$.  **`plaqfactor.corner_frame` and `hopframe._bright_rotations`
   must be rewritten, not adapted** — they raise `NotImplementedError` for blocks other than size 2 and 3.
4. **Frame cost [heur]:** a dense basis change on a $d$-dimensional multiplicity space costs up to $d(d-1)/2$ Givens
   rotations, each a multiplexed two-level rotation controlled by the corner's other labels.  Estimate it before building:
   if $\sum_c d_c(d_c-1)$ multiplexors exceed the generic synthesis of the plaquette, skip the frame.
5. The angle table becomes a product of per-corner functions of several bits; measure its Walsh support (§3b item 6)
   before deciding on flags.

### 4.3 SU(3)

1. The plaquette is $T+T^\dagger$ with $T={\rm tr}\,U_1U_2U_3^\dagger U_4^\dagger$ non-Hermitian (as for U(1)); factorise $T$.
2. **Multiplicity labels** need more than one qubit; the one-bit "vertex bit" logic of §1.0, §3e, §3g does not carry over.
   Use the SVD frame of §4.2 on the multiplicity space; flag the kernel.
3. **Complex matrix elements:** if no diagonal gauge makes the generator real, the bipartite block rounds of §3h do not
   apply (`lin_block_rounds` raises).  Replacement **[heur]**: (a) try a diagonal gauge first (`skqd.circuits_ir._real_gauge`
   tries one); (b) otherwise decompose each block as $e^{-i\theta h}=\mathcal Q^\dagger e^{-i\theta\Lambda}\mathcal Q$ with
   $\mathcal Q$ the ($\theta$-free) eigenvector matrix, synthesise $\mathcal Q$ by Givens rotations (constant multiplexors)
   and $e^{-i\theta\Lambda}$ as multiplexed phases $R_z(\theta\lambda)$ — still angle-linear, so the skeleton stays
   $k$-independent, at the cost of one extra basis change per block compared with the bipartite case.
4. **Tractability [heur]:** local codeword counts grow fast with multiplicities; the MILP of §3f grows with the number of
   controls (a 7-control table was not closed in 1 500 s here, `data/cert_it6_operator_plaq1_long.json`); expect to rely on
   the LP heuristic and certify only small multiplexors.

### 4.4 2D lattices

1. **4-link vertices:** more intertwiners (four $j=\tfrac12$ ends already have two singlets without matter) → corner blocks
   larger than 3 → the SVD frame of §4.2 everywhere.
2. **Every bulk plaquette has four interior corners**, like plaq1 here (66 468 → 202, the most expensive 2x4 term)
   **[heur]: expect plaq1-like costs for every bulk plaquette** unless the corner multiplexor problem (the open certificate,
   §3f) is solved better.
3. **Jordan–Wigner strings:** in a snake ordering a vertical hop's string crosses a whole row, so $\lvert J\rvert\sim L_x$.
   The parity fold of §3g.5 costs $2(\lvert J\rvert-1)$ CX per hop, which dominates on long rows **[heur]**.  Alternatives:
   carry the sign inside the multiplexor (mask shift, but every mask then involves the string bits) or a local fermion
   encoding (§4.5).
4. **Parallel scheduling:** disjoint-support terms may be reordered without changing the target **[Lean]**
   `kron_disjoint_comm`; the two-qubit depth here is an as-soon-as-possible schedule, so disjoint terms placed next to each
   other already overlap.  Group the terms of a coarse step into colour classes of disjoint supports **only if** the
   project's term order allows it (it defines the target).
5. **The study code is ladder-only** (`Ladder`, `corners_of` with keys `c00..c01` and one third link, two-end hops); porting
   means rewriting these helpers (§2.5).
6. **Clean ancillas** are more plentiful when links are stored twice **[heur]**; **reachable sets** grow faster with more
   terms per step, so class B gains less after the first terms **[heur]**.

### 4.5 Other fermion encodings

- JW: sign = parity of the sites in between; carry it in the multiplexor (mask shift) or conjugate it (§3g.5).
- Other encodings (Bravyi–Kitaev, Verstraete–Cirac, gauge-fermion elimination): test whether $H_{\rm hop}=(-1)^{\lambda(s)}h_0$
  with $\lambda$ linear in bits the term does not flip (the test of §3b item 5); if yes, fold $\lambda$ into one qubit and
  conjugate; if the sign depends on flipped bits, it belongs to $h_0$.

### 4.6 Test order, failure signs, fallback order

**Test first, in this order:** (1) harness reproduces the baseline; (2) blocks bipartite, zero diagonal; (3) `factorise`
on plaquettes (product residual); (4) hop product check (`run_structure_checks.py:hop_checks`); (5) coefficient tables in
the frame; (6) reachable supports.

**Failure signs:** `factorise` raises "signs do not factorise over the corners" (basis not vertex-local, or wrong corner
assignment); product residual far above round-off (the term is not a product); `corner_frame` raises "corner block of
size …" (rewrite, §4.2); "frame generator is not X on p_1 (x) diagonal" (ladder/corner CX wrong for the encoding);
`lin_block_rounds` raises "non-bipartite block" (§4.3 item 3).

**Fallback order** (each verified): (1) package synthesis + sparse Walsh (`full_lin`; `rpkg_lin` for class B);
(2) parity/bright frames (`framed_lin`, `bframed_lin`); (3) ancilla + flags (`cb*`), JW conjugation (`jwc_*`);
(4) corner factorisation (`cfg_lin`, `cfg_t_lin`, `cf2_lin`); (5) MILP supports and the `pp2` pass.

---

## 5. Verification protocol (mandatory before claiming a result)

### 5.1 Term checks (A1)

For every winning proposal and every $\theta$ used: all codeword columns (class A) or all contract columns (class B)
against $e^{-i\theta h}$ (`evaluate.verify_term_operator`).  Loop acceptance: deviation $\le10^{-10}$, per-column leakage
$\le10^{-12}$ (`scripts/loop_select.py` `A1_DEV`, `A1_LEAK`).  v2: worst $1.03\times10^{-14}$ over 130 class-A checks and
$8.77\times10^{-15}$ over 975 class-B checks (`data/eval_arch_it6_operator_pp2_all75_pruned.json` `terms`,
`data/eval_arch_it6_input_pp2_terms.json`).

### 5.2 Certified pruned simulation with the rounding term (A2)

`evaluate.verify_circuit_pruned` (`scripts/eval_family.py --prune-tau 1e-15`): the package's exact sparse simulator; after
every 32 gates remove amplitudes $\lvert a\rvert<10^{-15}$ and add the removed norm to $\epsilon_{\rm prune}$.  With $U_i$ the
exact gate $i$, $V_i$ the computed step (the gate as the simulator applies it, then pruning) and $v_i$ the computed state
before step $i$:
$$\lVert v_N-u_N\rVert_2\le\sum_i\lVert V_i(v_i)-U_i(v_i)\rVert\le\epsilon_{\rm prune}+\epsilon_{\rm round}$$
**[Lean]** `telescoping_bound_mirror` (`Reach.lean`).  The rounding term (`evaluate.rounding_bound`) adds per
non-permutation gate
$$\delta=\gamma\lVert G'\rVert_F+\lVert G'-G\rVert_F,\qquad\gamma=\mu+u+\mu u,\quad u=2^{-53},\quad\gamma_2=\frac{2u}{1-2u},\quad\mu=\sqrt2\,\gamma_2,$$
with $G$ the exact $2\times2$ gate and $G'$ the matrix the simulator uses; $\lVert G'-G\rVert_F\le2\cdot2u$ for gates built from
an angle (each entry within one ulp — a libm assumption) and the measured distance to the unitary polar factor for stored
one-qubit `unitary` matrices; X, CX, CZ cost nothing; the sum is multiplied by $(1+10^{-9})$.  The per-pair algebra is
**[Lean]** `pair_round_bound`, `row_sq_le`, `gate_round_sq`, `entry_err_sq` (`Rounding.lean`); the constants ($u$; $\mu$ from
Higham, Lemma 3.5, §12.6; one-ulp libm) are a cited model, **not provable in Lean** (Mathlib has no IEEE-754 semantics).

Pass: $\max\lvert\Delta\psi\rvert_{\rm measured}+\epsilon_{\rm prune}+\epsilon_{\rm round}<10^{-10}$ and
$(\sqrt{L_{\rm nc}}+\epsilon_{\rm prune}+\epsilon_{\rm round})^2<10^{-9}$ ($L_{\rm nc}$ = weight on non-codeword strings, summed
directly).  Sizes: largest $\epsilon_{\rm round}$ $1.59\times10^{-12}$ and largest $\epsilon_{\rm prune}$ $1.05\times10^{-13}$
(2x4 class A v2, `data/report004_tables.json` `2x4.A_v2`).

### 5.3 Independent Aer statevector check (by a different agent and engine)

Follow `reviews/001-independent-verification.md` §2 (scripts `reviews/001_verify_aer.py`, `001_build_circuits.py`):
circuits from the proposer's builders with the proposer's cache bypassed; the reviewer's own IR → qiskit converter
(refuses multi-qubit `unitary`); `AerSimulator(method="statevector", precision="double")`; target from the **package's**
`coarse_states(term_groups(...), basis_vector(r), dt, k)[k]` with $dt$ from `<root>/validation/E3.json` (2x4) or
`Model(Lx).reference` (others); leakage summed directly on non-codewords ($L_{\rm nc}$) and on other-sector codewords
($L_{\rm sec}$); X-gate prefix = `prepare(r)`; for class B, phase $\varphi=+\theta(H_{\rm diag})_{rr}$ (§3i).  The proposer's
`scripts/verify_aer_family.py` and the example's `aer_checks` do the same but do not replace an independent agent.  Cost on
this laptop: 2x3 seconds per circuit; 2x4 750–1 310 s per circuit with fusion on (`data/aer_*_v2_sample_*.json`, `aer_s`);
2x2 all 56 circuits within the 27.5 s of the example.

### 5.4 Class A operator test on random superpositions

Load ${\rm Prep}\,\lvert\phi\rangle$ ($\phi$ a normalised complex-Gaussian superposition of all sector codewords; fixed seeds,
e.g. `numpy.random.default_rng(11)`, `(12)`) and compare with `apply_groups(groups, phi, k*dt)`.  Done on: v1 class A
(8 runs, $\lVert\Delta\psi\rVert_2\le5.03\times10^{-14}$; a class-B contrast run gives $\max\lvert\Delta\psi\rvert=2.30\times
10^{-2}$; reviews/001 §3.1) and the 2x2 example (§1.3).  **Not done** on 2x4 class A v2 or 2x3 class A (§1.2).

### 5.5 Bar and leakage

- $\max_s\lvert\psi_se^{-i\varphi}-t_s\rvert<10^{-10}$, $\varphi=\arg\langle t\vert\psi\rangle$.
- Leakage $<10^{-9}$, summed directly over strings — never as $1-\sum_{\rm codewords}\lvert\psi\rvert^2$ (§8.5).

### 5.6 What NOT to do

- **Do not use the exact (unpruned) sparse simulator on compressed circuits.**  Frames that cancel exactly leave round-off
  residues ($\sim10^{-17}$) on non-codewords that later don't-care slots scatter.  Measured on three v1 class-B circuits
  (`data/eval_arch_it5_input_pp_exact_crosscheck.json`, `sparse_max_support`, `sparse_wall_s`): `B0_ref102_k1` 16 739 916
  strings, 111.5 s; `B1_ref230_k1` 4 184 564 strings, 27.7 s; `B0_ref345_k4` 33 472 800 strings, 201.3 s; a class-A circuit
  did not finish **[prose]** (report 003 §2.3.6).  The exact deviations ($2.37$, $2.33$, $1.24\times10^{-14}$, same file)
  match the pruned ones.  Use the certified pruned simulation.
- Do not judge by counts alone; never load the classical output state into a construction; never reorder non-commuting
  terms; never type numbers into reports by hand; **clear the cache after changing a proposal** (§2.4).
- Do not simulate the native PhasedX/ZZPhase circuit with the pruned simulator (genuine superpositions; a first attempt
  timed out at 900 s and 4.3 GB **[prose]**, report 003 §2.3.7).  Native correctness comes from Q1L.

---

## 6. Lean workflow

### 6.1 Setup and acceptance

- Toolchain `leanprover/lean4:v4.35.0` (`lean/lean-toolchain`), Mathlib tag `v4.35.0` (`lean/lakefile.toml`), via `elan`
  in `~/.elan`.
- Build: `export PATH=$HOME/.elan/bin:$PATH && cd 2x4_compression_using_ai_v1/lean && lake build`; one file:
  `lake env lean Compress2x4/<File>.lean`.
- **Acceptance:** `lake build` succeeds; `grep -rn "sorry\|admit" lean/Compress2x4/` is empty; every `#print axioms` result
  lists only `propext`, `Classical.choice`, `Quot.sound` or a subset.  Last build (`data/c4_lean_build.log`): "Build
  completed successfully (9059 jobs)"; the sources contain **66** `#print axioms` commands; the log has **63** lines
  "depends on axioms", all within that set, and **3** lines "does not depend on any axioms" (`agree_on_reachable`,
  `ccz_phase`, `agree_on_reachable_n`).
- API tips: `open scoped Kronecker` for `⊗ₖ`; `(open scoped Norms.Operator in h.exp_left)` turns `Commute M P` into
  `Commute (exp M) P`; the matrix exponential is `NormedSpace.exp`, written `exp` after `open NormedSpace`;
  `Matrix.exp_conj`, `Matrix.reindex_apply`, `Matrix.submatrix_mulVec_equiv`, `blockDiagonal_mul`; put
  `set_option backward.isDefEq.respectTransparency false in` before generic Banach-algebra lemmas on matrices.

### 6.2 What exists

| file | statements | content |
|---|---|---|
| `Sanity.lean` | `CZ_mul_CZ`, `RZZ_mul_RZZ`, `RZZ_comm`, `diagonal_mulVec_single`, `kron_disjoint_comm`, `agree_on_reachable` | a diagonal acting first on a basis vector is a phase; disjoint-support gates commute; one-step reachability |
| `Exp.lean` | `exp_intertwine`, `exp_agree_of_intertwine`, `exp_agree_on_invariant`, `exp_agree_mulVec`, `exp_conj_frame`, `smul_intertwine` | exponentials agree where generators agree on an invariant subspace (don't-cares); conjugated exponential |
| `Bits.lean` (14) | `perm_*`, `perm_conj_diagonal`, `xorLinear_trans`, `xorLinear_conj_flip`, `cxFun_cxFun`, `cx_involutive`, `cx_xorLinear`, `ccz_phase`, `ccz_circuit`, … | bit-vector model: CNOT networks as xor-linear permutations; ladder; CCZ from 3 CP + 2 CX |
| `Peephole.lean` (8) | `cx_comm_diagonal_of_indep`, `cxFun_comm`, `cx_comm_cx`, `cx_comm_flip_target`, `cx_comm_lincomb_flip_target`, … | peephole commutation rules |
| `Reach.lean` | `agree_on_reachable_n`, `telescoping_bound`, `telescoping_bound_mirror`, `ry_add_two_pi`, `relphase_cancel` | n-step reachable induction; error budgets; free sign of a bright rotation; relative-phase compute/uncompute |
| `Budget.lean` | `dropped_part_bound`, `normSq_sub_le`, `tv_le_norm_sub` | approximate-class bounds; total variation ≤ $\lVert a-b\rVert$ |
| `Ucr.lean` (7) | `xt_comm_zd`, `cx_conj_zd_target`, `cx_conj_xt_target`, `cx_conj_yt`, `exp_conj_cx_yt`, `exp_sum_commuting`, … | multiplexor walk identities |
| `Pair.lean` (13) | `exp_xt_diag`, `diag_comm_xt`, `ht_diag_ht`, `walk_factors_comm`, … | frame generator $X_t{\rm diag}(D)$ → multiplexed rotation |
| `Glue.lean` | `kron_one_mulVec_apply`, `kron_agree_of_support`, `reindex_kron_agree`, `commute_proj_of_block`, `projOn_mulVec_of_support`, `exp_mulVec_supported`, `exp_step_maps`, `circuit_exact_on_reachable`, `single_supported` | local exactness on touched blocks ⇒ agreement of $W\otimes1$ on the span of reachable states; reachability map; circuit-level induction |
| `Rounding.lean` | `pair_round_bound`, `row_sq_le`, `gate_round_sq`, `entry_err_sq` | per-gate rounding bound under the standard model |
| `Conj.lean` | `z_ry_z`, `cz_conj_ucr`, `neg_generator_conj`, `ucr_comm_ctrl_phase`, `perm_eq_of_fun_eq` | JW conjugation; flags around a multiplexor; CX-run resynthesis |

### 6.3 Reuse; what remains numerical

All statements are generic (any register size or index type); copy the folder and rename the namespace.  **What remains
numerical in every project:** each term's factorisation and frame form; each Walsh solve; each term's column agreement
(A1); that the dressed-basis term equals $h\otimes1$ on codewords; the block-diagonality of each term for the actual
reachable sets; the per-term qubit relabelling; each full circuit (A2); the native conversion (Q1L); the rounding
constants; HiGHS, numpy/scipy and Aer.

---

## 7. Loop and process

### 7.1 The loop

From arXiv:2610.22367 (A. Gu, A. Kemeny, S. Yelin, M. Lukin, *Discovering state-of-the-art quantum circuits with large
language models*, 2026; ID verified on 2026-10-26): a **proposer** writes programs that build circuits, an **independent
evaluator** checks each exactly, an **archive** keeps the best verified candidate, and **families of ideas** grow.  Here I
was the proposer, turn by turn, with no automated API loop (owner decision recorded in `notes/002` as answer "O5").

- Proposals: `src/c2x4/proposals.py:PROPOSALS` (label → function, applicable term class, contract).
- One iteration: `scripts/loop_select.py --label <it> --classes operator,input --proposals a,b,… [--lx L] [--refs …]
  [--merge]`: every applicable proposal for every term (class A) and every (reference, term) (class B) at $\theta=dt$,
  A1-checked, best kept (**score: ZZ count, then two-qubit depth**); failures recorded with their error; archive
  `data/archive_<it>.json` = `{"operator": {term: {candidates, best}}, "input": {ref: {twoB, term: {candidates, best,
  n_contract_states}}}}`.
- Family: `arch:<it>:<operator|input>:<pp|pp2>` (`family.family_from_spec`) = prepare + (class A) diag + best per term in
  package order + finishing pass.
- Verify all circuits (`eval_family.py`), freeze (`freeze_family.py`, refuses on any mismatch).
- History: it1–it5 (class A term sum 4 588 → 1 774, `data/report003_tables.json`), it6 (→ 1 530,
  `data/report004_tables.json`), 2x3 `L3_it1`.

### 7.2 Stopping rule

Stop when the certificates show the remaining multiplexors are support-optimal in their class and the remaining headroom
needs a new construction, or when the time budget ends.  Freeze; never let a pipeline chase a moving family.

### 7.3 Time budgets observed (laptop i7-8750H, 6 cores/12 threads, 62 GiB, no usable GPU)

| run | wall | file |
|---|---|---|
| 2x2 worked example, everything | 27.5 s (loop 17.5 s) | `examples/2x2_sandbox/results.json` |
| class-A loop, 13 terms, 14 proposals | 916 s | `data/archive_it6a.json` `wall_s` |
| class-B loop, 5 references, 16 proposals | 1 307–1 432 s | `data/archive_it6b{0,1,2}.json` |
| 2x3 class-B loop, 5–6 references | 513–561 s | `data/c2x3/archive_L3_it1i{0,1}.json` |
| verify 75 class-A circuits + terms | 528 s | `data/eval_arch_it6_operator_pp2_all75_pruned.json` |
| class-B term checks, 15 refs × 13 terms × 5 θ | 1 298 s | `data/eval_arch_it6_input_pp2_terms.json` |
| MILP certificates, class A / class B | 433 / 370 s | `data/cert_it6_{operator,input}.json` |
| native + Q1L, 75 class-A v2 | 847 s | `data/native_compressed_circuit_llm_2x4_classA_v2.json` |
| Aer, 44 2x3 class-A circuits | 518 s | `data/c2x3/aer_compressed_circuit_llm_2x3_classA.json` |

### 7.4 Process rules

- **30-minute rule per run;** `--max-wall` guards; batch class-B loops by references and merge
  (`scripts/merge_archives.py`); write results per item when items are long.
- **CPU oversubscription:** at most ~3 heavy jobs on 12 threads; give Aer `--threads`; coordinate with other agents.
- **`pkill -f <pattern>` kills your own shell** when the pattern is in the command line (exit 144); a `pgrep -f` waiter
  can match itself; use `ps -eo pid,args | grep` and `kill <pid>` separately.
- Never install into the shared `coding` env; pytket only in its venv.
- Every JSON carries commit, machine, parameters, seed (`env.write_json`); reports read numbers from JSON.
- **Clear the cache after changing a proposal** (§2.4).

---

## 8. Dead ends and pitfalls (with evidence)

1. **The approximate class gives no gain.**  Tolerance fixed in advance ($\ell_2\le10^{-8}$ per circuit, notes/004); at
   $10^{-8}$ only 0–3 blocks can be dropped; even at $10^{-6}$ and $10^{-4}$ the counts stay 660, 582, 660
   (`data/approx_tiers.json`).  It also reads classical amplitudes (reviews/001 note 4).
2. **Native level 2 is unverified:** 1–5 % fewer ZZ, 57–62 % fewer PhasedX (`data/native_it5_*.json`), but gates are
   rewritten, so Q1L does not apply.
3. **Parity-frame-only hops:** hop3 1 548 → 1 152 IR CX (class A) and restricted hops worse, 412 → 466 on reference 102
   **[prose]** (report 003 §2.3.3, interactive).  Superseded by bright frames (it5) and flags (it6).
4. **plaq1 before 238:** CF1 2 110 (`data/archive_it1.json`); CF2 first try 356 with 8 controls (*failure 1*: the greedy
   control reduction dropped a flag and kept its source bits → fixed by putting the flag sources first, `mux_relabelled`;
   *failure 2*: a "free" sign flip at a corner with no bright rotation → fixed by offering CCZ) **[prose]**; final CF2 238
   (`data/archive_it1.json`); later 220 (it3) and 202 (it6).  The first `cfg` gave 354 by flagging only three-state corners
   **[prose]** (report 003 §2.3.4–2.3.5).
5. **The $\sqrt{\rm leakage}$ bug:** leakage computed as $1-\sum_{\rm codewords}\lvert\psi\rvert^2$ carries the $10^{-14}$
   round-off of the norm; its square root reported $\varepsilon=2.3\times10^{-7}$ **[prose]** (report 003 §2.3.8).  Sum the
   non-codeword weight directly.
6. **The $k$-dependent skeleton** (§3h) and the sign bug in my first angle-linear rounds (singular values instead of
   $D=U^TKV$), caught by a per-block reconstruction test whose deviation grew $\propto\theta$ (report 004 §2.2).
7. **No `cz` in `ir_to_pytket`:** `ValueError: ir_to_pytket: unsupported IR gate cz` → `cp(π)` (§3k).  Recommendation for
   the package: add `cz`.
8. **What did not move:** class B v1 → v2 only $-1.2$ % (plaquettes dominate); the OR'd dark flag for plaq1 was evaluated
   and not built (net $-34+2c_4$ CX, $c_4$ = the unknown cost of a 4-input relative-phase AND; ≤ 22 CX if $c_4=6$ **[heur]**;
   report 004 §2.5); the plaq1 certificate is open (85 vs 78).  The planner's targets (class A ≈ 1 000–1 200, class B
   350–450) were **[heur]** and not reached.
9. **Slow first sparse-Walsh code:** an LP over up to $2^{15}$ unknowns was stopped; run the LP only after the control
   reduction **[prose]** (report 003 §2.3.5).
10. **Stale disk cache:** the cache key has no code version; after editing a proposal, delete the cache (§2.4).

---

## 9. Usage limits (class B) and noise behaviour

**Class B is valid only for: prepare its own reference with X gates, one coarse step, measure in the computational basis.**
Not for another reference or any superposition, $r>1$ repetitions, controlled versions, Hadamard tests, or reuse inside a
longer circuit.  On a random superposition class B is off by $2.3\times10^{-2}$ in max amplitude at 2x4 (reviews/001 note
1) and by $\lVert\Delta\psi\rVert_2\approx1$ at 2x2 (`examples/2x2_sandbox/results.json`).  Any other use needs class A.

**Under noise**, near-clean statistics (in particular $r_{\rm nc}$) are properties of a circuit family and must be
re-measured for each new family (notes/007 §7 item 4).  The noise agent's results (`noise/reports/003-noise-results.md` §4;
Pauli models from published device data, no hardware).  **These are $f_{\rm full}$ values, not $f_{\rm pkg}$:**
- 2x4 v2 on H2-2 (analytic, all 75 each): $f_{\rm full}$ = 0.401 (class B), 0.136 (class A).
- 2x4 v1 on H2-2, sampled, same 12 circuits per class: acceptance 0.592 (B) vs 0.273 (A); $f_{\rm hit}$ 0.558 vs 0.191;
  $r_{\rm nc}$ 1.08 vs 1.10; TV of the accepted distribution 0.194 vs 0.374 (finite-shot floors 0.144 / 0.189).
- 2x3 on H2-2: frozen $f_{\rm full}$ 0.0552, acceptance 0.162, $r_{\rm nc}$ 1.28; class A 0.311, 0.496, 1.06; class B 0.59,
  0.732, 1.02.
- Quoted: "Under these Pauli models class B shows no sign of handling errors worse than class A: its $r_{\rm nc}$ is not
  larger and its accepted distribution is closer to the ideal one, because it has fewer gates.  (A model with coherent or
  leakage errors could behave differently; those are not modelled.)"
- Frozen 2x4: no clean shots under any published model ($f_{\rm full}$ on H2-2 $\le4.71\times10^{-41}$).

---

## 10. Rules for the parallel projects (naming and separation)

Owner's rule (`notes/008-owner-decisions-C1-C6.md`, quoted): "keep the frozen circuits that have already been tested
separate from Class A and Class B, these will be known as compressed_circuit_llm_2x4_class[A,B] from now on. I will tell
you what to test when …" and "like i said, keep them separate and I will tell you what to use where."

- Name families `compressed_circuit_llm_<lattice>_class[A,B][_vN]`; with several gauge groups in one repo, put the group
  in the lattice tag (e.g. `su3_2x2`) — my suggestion; **ask the owner first**.
- Compressed families are never substituted into frozen circuits, gates, preregistrations, GPU slots or hardware plans
  until the owner says so; results go to separate files.
- Freeze each family into an immutable hashed file with a loader (`src/c2x4/families.py`, `notes/009`); a change gets a
  new version; aliases without a version point to the reviewed version.
- **Worked examples are not families** (the 2x2 example has no `compressed_circuit_llm_*` name).
- Independent verification by another agent before anyone builds on a family.

---

## 11. Quick start

### 11.0 First five minutes (2x2, sandboxed)

```bash
cd <root>
python 2x4_compression_using_ai_v1/examples/2x2_sandbox/run_2x2_example.py            # ~30 s on this laptop
python 2x4_compression_using_ai_v1/examples/structure_checks/run_structure_checks.py   # minutes (builds the 2x4 model)
```

Expected (`examples/2x2_sandbox/results.json`): class A 245 ZZ on all 28 circuits, depth 188, 28/28 certified and 28/28
Aer; class B 55–162 ZZ, 28/28 and 28/28; skeletons $k$-independent; random superposition class A
$\lVert\Delta\psi\rVert_2\sim10^{-14}$, class B $\sim1$.  Read the script: it is the whole procedure in about 300 lines
(sandbox → structure → loop → assemble → certify → Aer).  A different commit or library version may change the counts
slightly; the passes must not change.

### 11.1 From zero to verified families

1. **Read the project's conventions** (§1.0 for this one; §2.2 questions).  *Outcome:* a plan note mapping your terms onto
   diag/hop/plaq.
2. **Wrap your project in a `Problem`** (`src/c2x4/problem.py` pattern).  *Outcome:* `Problem.target` reproduces your exact
   coarse state.
3. **Harness** (`evaluate.py`).  *Outcome:* the frozen circuits reproduce their counts and pass the bar (§3a).
4. **Structure tests** (`examples/structure_checks/run_structure_checks.py` pattern).  *Outcome:* JSON with blocks,
   factorisation residuals, equal steps, JW parity, coefficients, reachable supports; which constructions apply.
5. **Port the constructions** (§2.5; copy `circuits_ir.py`; rewrite the ladder helpers).  *Outcome:* every proposal passes
   A1 on one small term.
6. **Angle-linear synthesis** (`use_linear`).  *Outcome:* identical skeletons for all $k$ on test terms.
7. **Sandbox (§2.4), then run the loop** for class A, then class B in reference batches.  *Outcome:* archives.
8. **Assemble and verify all circuits** (`eval_family.py` or the example's calls).  *Outcome:* all pass,
   `skeleton_k_independent` true.
9. **Certify the multiplexors** (`certify_family.py`).  *Outcome:* fraction certified, open cases.
10. **Freeze** (`freeze_family.py`) and write the loader note — only for families the owner asked for.
11. **Native conversion** (`native_family.py`, pytket venv).  *Outcome:* Q1L passes; $f_{\rm pkg}$ for information.
12. **Independent check** by another agent (§5.3, §5.4).  *Outcome:* a review with a verdict.
13. **Lean** (§6).  *Outcome:* clean build; a proved-vs-numerical table.
14. **Report** with every number read from a JSON; state the class-B use limit.

---

## 12. Appendix

### 12.1 Code map `src/c2x4/`

| module | functions |
|---|---|
| `env.py` | `write_json` (provenance), `git_commit`, `machine`, `archive_path`; `STUDY`, `DATA`, `CACHE` |
| `problem.py` | `Problem(lx)`: `M`, `groups`, `names`, `mats`, `E`, `ints`, `refs`, `dt`; `circuit_ids`, `tag`, `theta`, `target`, `support`, `local`, `baseline_term_ir`, `baseline_circuit`, `diag_index`, `cpath`, `term_names`; `get_problem(lx)` |
| `evaluate.py` | `counts`; `verify_circuit` (exact; not for compressed circuits); `term_unitary_columns`; `verify_term_operator`; `verify_circuit_pruned`; `certified_state_check`; `rounding_bound` |
| `plaqfactor.py` | `corners_of`, `factorise`, `corner_blocks`, `corner_frame`, `frame_generator`, `cf1_gates`, `cf2_gates`, `cfg_gates`, `f2_solve`, `f2_relations`, `toffoli`, `ccz`, `rtof`, `invert`, `mux_relabelled`, `_rot_item`, `LINEAR` |
| `hopframe.py` | `vertex_parity_frame`, `framed_gates`, `hop_vertex_factors`, `vertex_bright_frame`, `_bright_rotations`, `vertex_bright_frame_clean`, `jwc_framed_gates`, `SOLVER_MODE` |
| `reach.py` | `components`, `Reach.before`, `Reach.local_reachable`, `restricted_term_gates`, `contract_states`, `synth_on`, `exact_trajectory`, `approx_contracts` (dead end) |
| `sparsemux.py` | `walsh_matrix`, `sparse_walsh`, `mask_walk`, `walk_cost`, `sw_two_level`, `use_sparse_mux`, `SOLVER` |
| `linsynth.py` | `LinRot`, `lin_block_rounds`, `_solve_table`, `_flag_variants`, `_flag_gates`, `lin_two_level`, `_as_const_linrot`, `two_level`, `use_linear`, `FLAG`, `CONST_LIN`, `CONJ` |
| `certify.py` | `min_walsh_support`, `cached_min_walsh_support`, `milp_walsh`, `M_THETA` |
| `peephole.py` | `commutes_with_cx`, `cancel_cx`, `merge_1q`, `optimise`, `resynth_cx_runs`, `_synth_gauss`, `_same_permutation`, `_cx_matrix` |
| `proposals.py` | `PROPOSALS`, `applicable`, `register`, `_lin`, `_jwc`, `_cb` |
| `family.py` | `_cached`, `proposal_builder`, `archive_builder`, `archive_family`, `family_from_spec`, `circuit`, `finish`, `get_reach`, `FAMILIES` |
| `families.py` | `get_family`, `get_family_ir`, `family_header`, `exact_target`, `available_families`, `ir_to_qiskit`, `FAMILY_NAMES`, `ALIASES` (shim `families.py` in the study root) |

### 12.2 Scripts and examples

`scripts/`: `p2_0_harness_baseline.py`, `p2_1_structure.py` (2x4 only), `p1_reachable_support.py`, `p1_device_threshold.py`,
`planner_bounds_007.py`, `hop_coeff_values.py`, `loop_select.py`, `merge_archives.py`, `eval_family.py`, `certify_family.py`,
`cert_long_plaq1.py`, `freeze_family.py`, `verify_aer_family.py`, `native_family.py` (pytket venv), `native_check.py` +
`dump_finalists.py` (v1 native path), `rounding_v1.py`, `cxr_gain_v1.py`, `approx_tiers.py` (dead end), `summarise.py`,
`report003_tables.py`, `report004_tables.py`.
`examples/`: `2x2_sandbox/run_2x2_example.py` (worked example), `structure_checks/run_structure_checks.py`.
Tests: `tests/test_evaluate.py`, `tests/test_families.py`, `tests/test_linsynth.py`.

### 12.3 Data files

| file | content |
|---|---|
| `data/families/*.json.gz` | frozen families (hashes in `notes/009`) |
| `data/archive_it{1..6}*.json`, `data/c2x3/archive_L3_it1*.json` | loop archives |
| `data/eval_arch_it{5,6}_*_all75_pruned.json`, `data/c2x3/eval_arch_L3_it1_*_all44_pruned.json` | full verification |
| `data/cert_it6_*.json`, `data/c2x3/cert_L3_it1_*.json` | MILP certificates |
| `data/native_*.json`, `data/c2x3/native_*.json` | native counts, Q1L, $f_{\rm pkg}$ |
| `data/aer_*.json`, `data/c2x3/aer_*.json` | Aer checks |
| `data/rounding_v1.json`, `data/cxr_gain_v1.json`, `data/hop_coefficient_values.json` | evidence for §3 |
| `data/p2_0_harness_baseline.json`, `data/p2_1_structure.json`, `data/p1_*.json`, `data/planner_bounds_007.json`, `data/approx_tiers.json` | baseline, structure (2x4), dead ends |
| `data/report004_tables.json` | tables of report 004 and §1.2 |
| `data/c4_lean_build.log` | last Lean build |
| `examples/2x2_sandbox/results.json`, `archive_L2_example.json`, `circuits_L2_example.json.gz` | worked example (its `cache/` is not committed) |
| `examples/structure_checks/structure_checks.json` | structure tests on 2x2, 2x3, 2x4 |

### 12.4 Commands as run here (**do not re-run with these labels — they overwrite §1.2's evidence; sandbox first, §2.4**)

```bash
# 'coding' conda env python (qiskit 2.5.2, qiskit-aer 0.17.2, scipy 1.18) except pytket (its venv); Lean via ~/.elan
python scripts/p2_0_harness_baseline.py
python scripts/loop_select.py --label it6a --classes operator \
   --proposals bframed_lin,framed_lin,full_lin,jwc_bframed,cfg_lin,cfg_t_lin,cf2_lin,cfg_lin_milp,cf2_lin_milp
python scripts/loop_select.py --label it6 --merge --classes operator \
   --terms hop0,hop1,hop2,hop3,hop4,hop5,hop6,hop7,hop8,hop9 \
   --proposals cb0,cb1,cb0_jwc,cb1_jwc,cb0_milp,cb1_milp,cb0_jwc_milp,cb1_jwc_milp
python scripts/loop_select.py --label it6b0 --classes input --refs 102,16833,11026,6930,3166 \
   --proposals rpkg_lin,cfg_lin,cfg_t_lin,cf2_lin,cfg_lin_milp,cf2_lin_milp,bframed_lin,framed_lin,jwc_bframed,jwc_framed,cb0,cb1,cb0_jwc,cb1_jwc,cb0p,cb1p
python scripts/merge_archives.py --out it6 --operator it6 --inputs it6b0,it6b1,it6b2
python scripts/eval_family.py --family arch:it6:operator:pp2 --circuits all --kmax 5 --prune-tau 1e-15 --label all75_pruned
python scripts/eval_family.py --family arch:it6:input:pp2 --circuits all --kmax 5 --prune-tau 1e-15 --no-terms --label all75_pruned
python scripts/eval_family.py --family arch:it6:input:pp2 --circuits all --kmax 5 --terms-only --label terms
python scripts/certify_family.py --archive it6 --cls operator --time-limit 300
python scripts/freeze_family.py --name compressed_circuit_llm_2x4_classA_v2 --spec arch:it6:operator:pp2 --lx 4 --kmax 5 \
   --verification data/eval_arch_it6_operator_pp2_all75_pruned.json --version v2 --source "..."
~/.local/share/su2qc-quantinuum/venv/bin/python scripts/native_family.py --family compressed_circuit_llm_2x4_classA_v2
python scripts/verify_aer_family.py --family compressed_circuit_llm_2x3_classA --threads 4
# 2x3: --lx 3, labels L3_it1 / L3_it1i0 / L3_it1i1, --kmax 4
export PATH=$HOME/.elan/bin:$PATH; (cd lean && lake build)
python -m pytest -q tests/
```

### 12.5 Package functions imported (read-only)

Public: `skqd.exact.Model`, `mass_default`; `skqd.krylov.apply_groups`, `coarse_states`, `term_groups`, `basis_vector`,
`references`; `skqd.reference_sim.CodewordEmbedding`, `localize`, `term_support`; `skqd.circuits_ir.CircuitFactory`,
`structured_term_gates`, `run_ir`; `skqd.sparse_sim.SparseState`, `apply_ir`, `run_sparse`;
`skqd.quantinuum_native.ir_to_pytket`, `compile_native`, `native_counts`, `local_equivalence_35a`, `pytket_to_ir`;
`skqd.device_req.clean_shot_fraction`.  Private (`skqd.circuits_ir`): the 14 names of §2.5 (ii).

### 12.6 References (verified on 2026-10-26; besides those of §4)

- A. Gu, A. Kemeny, S. Yelin, M. Lukin, *Discovering state-of-the-art quantum circuits with large language models*,
  arXiv:2610.22367.
- M. Möttönen, J. J. Vartiainen, V. Bergholm, M. M. Salomaa, *Quantum circuits for general multiqubit gates*, Phys. Rev.
  Lett. 93, 130502 (2004), arXiv:quant-ph/0404089 — uniformly controlled rotations and their Gray-code CNOT chains.
- D. Maslov, *On the advantages of using relative phase Toffolis with an application to multiple control Toffoli
  optimization*, Phys. Rev. A 93, 022311 (2016), arXiv:1508.03273 — relative-phase Toffolis (RC3X).
- A. Barenco et al., *Elementary gates for quantum computation*, Phys. Rev. A 52, 3457 (1995), arXiv:quant-ph/9503016 —
  Toffoli constructions, including the relative-phase (Margolus) form.
- K. N. Patel, I. L. Markov, J. P. Hayes, *Efficient synthesis of linear reversible circuits*, Quantum Inf. Comput. 8,
  282 (2008), arXiv:quant-ph/0302002 — CNOT-circuit synthesis (background for §3j).
- N. J. Higham, *Accuracy and Stability of Numerical Algorithms*, 2nd ed., SIAM (2002), ISBN 0-89871-521-0.

---

## 13. Review 002 findings and where they are fixed

| finding | fix |
|---|---|
| B1 model never stated | §1.0 (Hamiltonian with file:lines, truncation, vertex encoding table, intertwiner, dark/bright, $2B$, references, $dt$, how to map a model) |
| I1 overwrite / stale cache | §2.4 (two warnings + sandbox recipe), §12.4 header, §8.10, §5.6, §7.4 |
| I2 no smallest example | §1.3, §11.0; `examples/2x2_sandbox/run_2x2_example.py` → `results.json` |
| I3 wrong commit | §0.3 (current hashes, old → new map) |
| I4 path rule | §0.1 (`<root>/` prefix used throughout) |
| I5 hop check not a product check | §3b items 3–5 (real product check, equal steps, JW parity; `examples/structure_checks/`) |
| I6 bipartiteness: wrong script | §3b item 1 (`run_structure_checks.py:blocks`) |
| I7 structure script 2x4-only | §3b intro (new script for 2x2/2x3/2x4; the old one marked) |
| I8 undefined / overloaded symbols | §0.4 symbol table; $B$ only for the sector; renamed $p_\star$, $\Phi$, $\Sigma$, $\mathcal O$, $\Pi$, $\epsilon$, $\beta_{\rm Q1L}$, $\alpha\beta\kappa$; symbols defined in §3c–§3h and §5.2 |
| I9 undefined terms | Glossary (Q0P/Q1/Q2/Q5, CF_traj, C1–C6, dressed basis, intertwiner, sector, $f_{\rm hit}$, $f_{\rm ideal}$, $r_{\rm nc}$, acceptance, TV, PhasedX, Margolus, RC3X, Gray code, 2-opt, H1-1, Helios-1, genie-opus); O5 in §7.1; "prompts/35b R1" in §1.2 |
| I10 two $f$ | Glossary ($f_{\rm pkg}$, $f_{\rm full}$), §1.2, §9 |
| I11 verification scope | §1.2 (column and bullet), §5.4 |
| I12 porting effort | §2.5 |
| I13 §4 gaps, literature | §4 rewritten (procedures, [heur] marks, $T+T^\dagger$, rectangular SVD and kernels, frame cost, `corner_frame` rewrite, SU(3) complex case and multiplicity labels, 2D JW cost, scheduling, ladder-only code); verified references in §4 and §12.6 |
| m1 Lean axiom count | §6.1 (66 commands; 63 + 3) |
| m2 33 s | §5.6 (JSON values: 27.7 s etc.) |
| m3 760/762 source | §3h (eval JSON key) |
| m4 `multiplexed_two_level` | §3c pseudo-code (`skqd.circuits_ir._multiplexed_two_level`) |
| m5 phase sign | §3i, §5.3 ($\varphi=+\theta(H_{\rm diag})_{rr}$) |
| m6 prose-only numbers | marked **[prose]** (§3c, §3e, §3g.2, §3j, §5.6, §8.3–8.5, §8.9); CF1 2 110 and CF2 238 sourced to `data/archive_it1.json` |
| m7 2x2 unknown | §1.3 (worked-example numbers) |
| m8 arXiv ID | verified (§7.1, §12.6) |

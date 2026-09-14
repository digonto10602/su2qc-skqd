# Neural-enhanced sample-based Krylov diagonalization for SU(2) with dynamical quarks in 2+1D

**SU2QC Project 2, revision 2: corrected specification and step-by-step implementation manual**
(all reviewer corrections of 10 September 2026 incorporated). Prepared for D. Digonto (SU2QC), 10 September 2026.

> Text extraction of the PDF (equations lost their layout; the PDF is authoritative — see README.md in this folder).
> Symbols throughout: $g^2$ gauge coupling, $m$ staggered quark mass, $j_\ell$ link spin, $n_x$ quark occupation,
> $\iota_x$ intertwiner label, $B$ baryon number, $\Delta t$ Krylov time step, $W$ sector spectral width,
> $E_R$ Ritz value, $r_H$ Hamiltonian residual, $f$ circuit fidelity proxy, $|B|$ support size.

## Revision summary and correction checklist

The first version of Project 2 was reviewed independently by two referees ("Claude" and "Codex"). Both rebuilt the 2×2 Hamiltonian and reproduced every reference number, and both found the same class of problems in the parts of the plan that go beyond 2×2. This revision fixes every point. In doing so we built the tool the first version lacked — a dressed-site (spin-network) Hamiltonian builder with explicit intertwiner labels, validated against the projector construction at 2×2 to 10⁻¹⁴ — and used it to produce exact references and emulations at 2×3 (1 727 states) and 2×4 (37 165 states). The emulations changed one conclusion: at these sizes a classical selected-CI support of equal size is at least as good as the device-generated support (Step 6), so the experiment is specified as a workflow validation with certified spectra and a measured device-support quality, not as an advantage demonstration.

| # | reviewer point | fix in this revision | where |
|---|---|---|---|
| C1/X1 | ({jℓ},{nx}) labels are not unique beyond 2×2: 1 727 states vs 1 460 labels on 2×3, 37 165 vs 26 248 on 2×4, 113 vs 82 with a static pair; interior vertices have 13 states for 12 labels | label is now b = ({jℓ},{nx},{ιx}) with fusion-tree intertwiner labels; codewords, decoder, Hamiltonian, neighbours, ML features and recovery all use it; all counts reproduced (Table 2); Plan B "4 states" corrected | Step 2 |
| C2 | the 2×2 hardware run cannot test SKQD (sector saturates) | 2×2 is re-scoped as decoder/yield/readout calibration; the SKQD accuracy test is on 2×3 (sectors of 426–677 states, supports of 86–95) and 2×4 (simulator) | Steps 1, 9 |
| C3/X8 | no classical-support control; neighbour growth reaches the whole sector; exact training data leaks | preregistered equal-|B| controls: CIPSI, BFS, random, oracle, ML-alone, device-seeded CIPSI; leakage-safe splits; expected outcome stated from emulation | Steps 6, 7 |
| C4/X5 | noise model optimistic (uniform valid replacements add coverage); yield ≈ fidelity; compare by CZ count | fidelity-based proxy with uniform and local corruption plus readout flips; false-positive/negative support rates; CZ-count budget and shot rule; transpiled-circuit Aer models required before hardware | Steps 4, 8 |
| C4/X6 | one-sided variational bound does not cover MB, Δ0, V(r) | two-sided certified intervals per sector (Weinstein, Kato–Temple) and interval arithmetic for differences | Step 5 |
| X2 | ML model under-specified (contradictory targets across parameters); "equivariant" misnamed | model conditioned on λ = (g², m, B, Lx, charges) with intertwiner and orientation inputs; called gauge-invariant; ranking loss | Step 7 |
| X3 | Krylov residual is not a convergence certificate | renamed subspace-closure diagnostic; certification by Hamiltonian residual rH with explicit gap assumptions | Step 5 |
| X4 | SKQD theorem used outside its assumptions; "Trotter error is not systematic" | separated: rigorous variational statement vs heuristic support generation; Trotterization affects support discovery (quantified) | Step 4 |
| X7 | not QML | renamed neural-enhanced SKQD / ML-assisted quantum simulation; the learned model is classical | title |
| C-s | Δt = 0.5 contradicts π/(Emax − Emin); g² = 4 both training and test; B = 1 near-degeneracy (0.042) below gate tolerance | Δt = π/W computed per sector and used (0.245, 0.156, 0.115 for 2×2,3,4 at g² = 4); g² = 4 excluded from training; cluster-resolved observables and gates tied to level spacings | Steps 1, 5, 7 |

## 0 Scope, roles of the three lattices, and what is claimed

**Method.** Sample-based Krylov quantum diagonalization (SKQD) [1, 2]: a QPU prepares states that spread a reference configuration over the gauge-invariant configurations that matter, is measured in the configuration basis, and the HPC side diagonalizes the exact Hamiltonian in the span B of the accepted configurations. The diagonalization is variational and exact within B; the quantum device only chooses B. A classical neural model (Step 7) ranks configurations for recovery and proposal. The learned model is classical, so the project is ML-assisted quantum simulation, not quantum machine learning.

**Roles.** 2×2 (12 qubits, 82 states): pipeline calibration only — decoder validity, yield versus CZ depth, readout confusion, sector filter; not an accuracy test, because any 10³-shot run saturates its sectors (38 and 20 states). 2×3 (20 qubits, 1 727 states, sectors 677 and 426): the SKQD test; exact references from the builder of Step 3. 2×4 (28 qubits, 37 165 states): simulator-only transfer and scaling test with exact Lanczos references; hardware only if the 2×3 gates pass with margin.

**Claims if the gates pass.** (i) First quantum-centric spectroscopy of a non-Abelian gauge theory with dynamical matter in two spatial dimensions: vacuum energy, diquark-baryon cluster, meson-like gap and static potential V(1), V(2) on 2×3 from device-generated supports with two-sided certified intervals. (ii) A validated Gauss-law-aware pipeline (intertwiner-labelled dressed-site basis, decoder, builder, certification). (iii) A measured curve of device-support quality (recall of the exact support, false-positive rate) versus CZ count and shots, with the classical controls of Step 6 reported at equal |B|. Not claimed: quantum advantage; from the emulation we expect the classical CIPSI control to match or beat the device support at 2×3 and 2×4 (Fig. 1); the continuum limit; string breaking versus r.

**Logical flow.** Step 1 Hamiltonian, sectors, exact references → Step 2 basis, codewords, decoder → Step 3 builder and its validation → Step 4 support generation on the QPU with CZ and shot budgets → Step 5 HPC post-processing and certification → Step 6 classical controls and the primary endpoint → Step 7 neural importance model → Step 8 noise simulation → Step 9 hardware execution → Step 10 analysis, gates, reporting; Sec. 11 timeline.

## 1 Step 1 — Hamiltonian, sectors, symmetries, exact references

**1.1 Hamiltonian.** Eq. (1) of the Genesis proposal with a₀ = 1 on a 2×Lx open patch, sites x = (x₁, x₂) indexed x₁Ly + x₂, links oriented in +x and +y:

$$H = -\frac12\sum_{\ell=(x\to y)}\Big[\eta_\ell\,\psi^\dagger_{x,i}U_{ij}(\ell)\psi_{y,j} + \text{h.c.}\Big] + m\sum_x(-1)^{x_1+x_2}\psi^\dagger_x\psi_x + \frac{g^2}{2}\sum_\ell \hat E^2_\ell - \frac{1}{2g^2}\sum_P\big(W_P + W_P^\dagger\big), \tag{1}$$

ηℓ = i on x-links and (−1)^{x₁+x₂} (start site) on y-links, links truncated at jmax = ½ in the electric basis |j, mL, mR⟩, W_P = Σ_{ijkl} U_ij(ℓb) U_jk(ℓr) U_lk(ℓt)† U_il(ℓl)† counter-clockwise from the lower-left corner. Gauss's law with the matter charge and optional static charges,

$$G_a(x) = \sum_{\ell\,\text{out}} E^L_a(\ell) + \sum_{\ell\,\text{in}} E^R_a(\ell) + \psi^\dagger_x\tau_a\psi_x + \tfrac12\sigma^{(x)}_a\big|_{\text{static}},\quad \tau_a = -\tfrac12\sigma_a^\top,\quad [E^L_a,U] = +\tfrac12\sigma_a^\top U,\quad [E^R_a,U] = -\tfrac12 U\sigma_a^\top, \tag{2}$$

in the numerical convention in which [Ga(x), H] = 0 was verified at 2×2 (residual 2×10⁻¹⁵). **1.2 Conserved quantities.** Baryon number B = ½ Σx (nx − n^vac_x), n^vac_x = 1 − (−1)^{x₁+x₂}; charge conjugation maps B → −B (the B = ±1 spectra coincide, Table 1); the lattice reflections compatible with staggering permute configuration labels. **1.3 Exact references.** 2×2 by two independent routes (projector kernel in the redundant basis; Step-3 builder); 2×3 and 2×4 by the Step-3 builder with dense (677, 426) or Lanczos (12 843, 8 934) diagonalization per sector; static-charge sectors by adding the static spin to Eq. (2). **1.4 The Krylov time step.** Δt = π/W_B with W_B = Emax − Emin of the sector block (the anti-aliasing condition of Ref. [1]); the first version used Δt = 0.5, which violates this rule at 2×2 (π/W = 0.245). **1.5 Near-degeneracies.** In the B = 1 sector the diquark can sit on any even site, so the lowest levels form a cluster of Lx states (splittings 0.042 at 2×2, 0.024/0.13 at 2×3, 0.006/0.12 at 2×4). The baryon mass is defined as M_B = E₀^{B=1} − E₀^{B=0} with the cluster reported, gate tolerances are tied to the cluster width (Step 10), and certification treats the cluster as a whole (Step 5).

## 2 Step 2 — The gauge-invariant configuration basis with intertwiner labels

**2.1 Local singlet spaces.** A vertex x owns one index per link end (mL of outgoing links, mR of incoming links, canonical order = link index order) and its matter Fock state. Its physical states are the singlets of Ga(x) on ⊗_e V_{je} ⊗ F_{nx}, i.e. the kernel of Σa Ga(x)². Their number is the multiplicity of j = 0 in ⊗_e je ⊗ s(nx), s(0) = s(2) = 0, s(1) = ½:

| vertex type | allowed ({je}, n) combinations | physical states | max. intertwiners | qubits |
|---|---|---|---|---|
| corner (2 ends) | 6 | 6 | 1 | 3 (2 flags) |
| interior (3 ends) | 12 | 13 | 2 [(½,½,½; n=1)] | 4 (3 flags) |
| corner with static ½ | 6 | 7 | 2 [(½,½; n=1)] | 3 (1 flag) |
| interior with static ½ | 12 | 17 | 2 | 5 |

The 13th interior state is the second singlet of (½)^{⊗4} = 2(0) ⊕ 3(1) ⊕ (2); the first version's label ({jℓ},{nx}) silently dropped it.

**Table 1: Exact references from the Step-3 builder (m = 3g²/16).** Sector dimensions include intertwiner multiplicity; "support" is the number of configurations carrying 99%/99.9% of the ground-state weight; PR is the participation ratio; W the sector spectral width.

| lattice, g² | sector | dim | E0 | next levels | π/W | support | PR |
|---|---|---|---|---|---|---|---|
| 2×2, 4 | B = 0 | 38 | −3.6408 | −0.9622 | 0.245 | 9 / 16 | 1.5 |
| 2×2, 4 | B = 1 | 20 | −1.8616 | −1.8197, 0.2082 | 0.332 | 8 / 13 | 2.6 |
| 2×3, 4 | B = 0 | 677 | −5.6026 | −2.8886, −2.8652 | 0.156 | 31 / 86 | 1.9 |
| 2×3, 4 | B = ±1 | 426 | −3.8261 | −3.8017, −3.6687, −1.6529 | 0.187 | 42 / 95 | 3.6 |
| 2×3, 4 | B = 2 | 95 | −2.0118 | −1.8622, −1.8439 | 0.234 | 15 / 22 | 1.5 |
| 2×3, 2 | B = 0 | 677 | −4.2216 | −2.7236, −2.7032 | 0.257 | 137 / 326 | 5.9 |
| 2×3, 2 | B = ±1 | 426 | −3.0866 | −2.9730, −2.7940 | 0.305 | 136 / 243 | 11.9 |
| 2×3, 1 | B = 0 | 677 | −4.3918 | −3.4201 | 0.303 | 396 / 549 | 33.8 |
| 2×4, 4 | B = 0 | 12 843 | −7.5652 | −4.8436, −4.8375 | 0.115 | 76 / 305 | 2.5 |
| 2×4, 4 | B = 1 | 8 934 | −5.7802 | −5.7741, −5.6541 | — | 127 / 470 | 4.8 |

Derived quantities. 2×3, g² = 4: Δ0 = 2.7140, MB = 1.7765, E₀^{B=2} − E₀^{B=0} − 2MB = 0.038, V(1) = 1.3872, V(2) = 2.5898, V(2) − V(1) = 1.2027 (static pair on the bottom row, B = 0 matter). 2×3, g² = 2: Δ0 = 1.4980, MB = 1.1350, V(1) = 0.7820, V(2) = 1.3740. 2×4, g² = 4: Δ0 = 2.7216, MB = 1.7851; g² = 2: MB = 1.1560.

**2.2 Intertwiner (fusion-tree) label.** When the kernel has dimension > 1, define ιx by the simultaneous eigenbasis of the cumulative Casimirs Ck = (J₁ + ··· + Jk)², k = 2, ..., K − 1, over the constituents in canonical order (link ends, then matter, then static charge); for an uncharged interior vertex ιx ∈ {0, 1} is the intermediate spin J₁₂ ∈ {0, 1} of the first two link ends. Any consistent choice gives an orthonormal basis; this one is reproducible and is what the decoder returns.

**2.3 Basis and its orthonormality.**

$$|b\rangle = |\{j_\ell\},\{n_x\},\{\iota_x\}\rangle = \sum_{\{m\},\{c\}}\prod_x T^{(\iota_x)}_x[m_{e\in x}, c_x]\bigotimes_\ell|j_\ell, m^\ell_L, m^\ell_R\rangle\bigotimes_x|n_x, c_x\rangle,\qquad \langle b'|b\rangle = \prod_x\langle T'_x|T_x\rangle = \delta_{b'b}, \tag{3}$$

because every m index is owned by exactly one vertex and the local tensors are orthonormal. The count of states is the product of local singlet multiplicities summed over label assignments, which reproduces all reviewer numbers:

**Table 2: Physical states versus distinct ({jℓ},{nx}) labels** (both computed here), with the sector split for 2×3 and 2×4 given as states (labels).

| system | states | labels |
|---|---|---|
| 2×2 | 82 | 82 |
| 2×3 | 1 727 | 1 460 |
| 2×4 | 37 165 | 26 248 |
| 2×2 + static pair, r = 1 | 113 | 82 |
| 2×2 + static pair, diagonal | 112 | 82 |
| 2×3 + static pair, r = 1 | 2 729 (B=0: 1 089) | |
| 2×3 + static pair, r = 2 | 2 418 (B=0: 978) | |

| sector | B = 0 | B = ±1 | B = ±2 | B = ±3 | B = ±4 |
|---|---|---|---|---|---|
| 2×2 | 38 (38) | 20 (20) | 2 (2) | | |
| 2×3 | 677 (564) | 426 (360) | 95 (84) | 4 (4) | |
| 2×4 | 12 843 (8 856) | 8 934 (6 272) | 2 869 (2 128) | 350 (288) | 8 (8) |

**2.4 Codewords (the hardware encoding).** Corner vertex, 3 qubits (q₁,q₂,q₃): q₁,₂ are the flux bits of its two ends (j = ½ ⇔ 1); if q₁ = q₂ then n ∈ {0,2} and q₃ = n/2; if q₁ ≠ q₂ then n = 1, q₃ = 0, and q₃ = 1 is a leakage flag. Interior vertex, 4 qubits: q₁,₂,₃ flux bits of the three ends; if the number of flux ends is even, q₄ = n/2; if it is one, n = 1 and q₄ = 0 (q₄ = 1 flag); if it is three, n = 1 and q₄ = ι. Charged corner, 3 qubits: flux bits; equal bits (0,0): n = 1, q₃ = 0 (1 flag); (1,1): n = 1, q₃ = ι; unequal: n ∈ {0,2}, q₃ = n/2. Charged interior vertices need 5 qubits (17 states); a static pair at r = 1 on 2×3 therefore costs 21 qubits, at r = 2 (two corners) 20. Totals: 2×2: 12; 2×3: 20; 2×4: 28.

**2.5 Decoder (classical, per shot).** (i) Split the bitstring into vertex codewords; (ii) reject if any vertex is flagged; (iii) for every link compare the flux bit seen from its two end vertices, reject on mismatch (link consistency); (iv) read ({jℓ},{nx},{ιx}); (v) reject if Σx nx is not the target sector; (vi) look the label up in the basis index. Verification (done): encode–decode round trip on all 1 727 states; the fraction of uniformly random 20-bit strings accepted is 0.15% (1727/2²⁰ = 0.16%), so uncorrelated garbage is almost always rejected, and the residual acceptances are false positives (valid but unrelated configurations) that enlarge B without biasing the variational energy.

## 3 Step 3 — Building the Hamiltonian in the dressed-site basis

**3.1 Local tensors.** For each vertex signature (spins and roles of its ends, nx, static charge) build the local generators — J^(j)_a on an outgoing end, −J^(j)⊤_a on an incoming end (this is how E^{L,R} act on mL, mR), Qa restricted to the occupation-n block of the four-state site Fock space, σa/2 for a static charge — and take the orthonormal kernel of Σa G²_a, ordered by the fusion-tree label of 2.2. Cache by signature (a few dozen signatures in total).

**3.2 Matrix elements by local contraction.** For an operator O acting on links L_O and sites V_O,

$$\langle b'|O|b\rangle = \sum_{m,m' \text{ on } L_O;\ c,c' \text{ on } V_O}\ \prod_{x\in V(O)} T'_x[m'_{e\in L_O}, m_{e\notin L_O}, c'_x]\,T_x[m_{e\in L_O}, m_{e\notin L_O}, c_x]\ \prod_{\ell\in L_O} O_\ell\big[(j'_\ell m'_L m'_R),(j_\ell m_L m_R)\big]\ \prod_{x\in V_O}[F_x]_{c'_x c_x}\times s_{JW}, \tag{4}$$

where V(O) are the vertices touching L_O ∪ V_O, untouched link ends at those vertices are contracted between T′ and T (all other vertices give δ by orthonormality), Oℓ is the 5×5 link operator block in the electric basis, Fx the site Fock operator, and s_JW = Π_{z strictly between x,y} (−1)^{nz} the Jordan–Wigner sign of a hopping term ψ†x ψy with the intra-site signs absorbed into Fx = ψ^{loc†}_{x,i} Px (for x < y) and Fy = ψ^{loc}_{y,j} (with Py ψ^{loc}_{y,j} for x > y), P = (−1)^n. Hopping on link ℓ = (x → y) connects b to labels j′ℓ = ½ − jℓ, n′x = nx + 1, n′y = ny − 1 and every ι′ at x, y; the plaquette flips all four j's of P and every ι′ at its corners; mass and electric terms are diagonal and ι-independent.

**3.3 Validation and cost.** The builder reproduces all 82 eigenvalues of the projector construction at 2×2 (maximum difference 8×10⁻¹⁵), H = H† to 10⁻¹⁰, and gauge invariance is automatic. Runtime in plain numpy: 2×3 in 22 s (16 875 non-zeros), 2×4 in 17 min (521 391 non-zeros); charged 2×3 sectors in 1–2 min. The same routine returns the Hamiltonian neighbours of any configuration (needed in Steps 5–7).

## 4 Step 4 — Support generation on the QPU

**4.1 What is rigorous and what is heuristic.** The SKQD theorem of Ref. [1] assumes exact Krylov states e^{−ikHΔt}|b₀⟩, a reference overlap |⟨b₀|Ω⟩|² that decays at most polynomially and a sparse ground state; then sampling these states with polynomial shots yields a support in which the Ritz energy converges. On a device the states are Trotterized (or deliberately coarser, below), so the theorem does not apply and the device is an empirical support-discovery heuristic; what remains rigorous is the variational bound of Step 5, which holds for any B. Trotterization does not bias H_B, but it changes which configurations are discovered and therefore contributes to subspace-selection error — quantified below.

**4.2 Reference configurations.** Vacuum sector: the Dirac sea b₀ (odd sites doubly occupied, even sites empty, no flux; ground-state weight 0.72 at 2×3, g² = 4) plus the seven one-meson configurations (quark on the even end, hole on the odd end, flux on that link). B = 1: the diquark on each even site (Lx references; the 2×3 ground state has only 0.37 weight on a single one). Static sectors: the string along the bottom row plus its one-plaquette deformations. Multi-reference generation is essential: with a single reference and d = 5 exact Krylov states the configurations of the 99.9% support that ever reach probability > 10⁻³ number 41 of 86 (B = 0) and 35 of 95 (B = 1); with the reference sets above and coarse steps (4.3) they number 86 of 86 and 94 of 95.

**4.3 Circuits.** Two families, both gauge-invariant by construction (each factor is an exact block unitary of an electric, hopping or plaquette term): (a) Trotterized Krylov, k first-order steps of size Δt; (b) coarse single-step circuits Π_γ e^{−iH_γ kΔt} for k = 1, ..., 4 — one step per circuit. At 2×3 family (b) covers more of the support than (a) (62 vs 41 of 86 configurations from a single reference) at one quarter of the depth, so (b) is the default and (a) an ablation. Dropping the diagonal terms from the generator, as in the Schwinger runs [2], is a further ablation. CZ per first-order step in the local encoding: ≤ 250 (2×2), ≤ 500 (2×3, the nine-month plan's Gate-1 budget), to be measured after routing on the target map (gate S2).

**4.4 Fidelity, yield and the shot rule** (replaces the "5% Plan-B threshold"). With per-CZ error ε the fraction of clean shots is f ≃ (1 − ε)^{N_CZ}: for N_CZ = 250/500/1000/1500/2000, f = 0.61/0.37/0.135/0.050/0.018 at ε = 2×10⁻³, 0.47/0.22/0.050/0.011/0.002 at 3×10⁻³, and 0.37/0.135/0.018/0.002/0.0003 at 4×10⁻³; readout at 1% per qubit on 20 qubits removes another 18%. The accepted-shot yield is ≈ 0.82 f plus the 0.15% of garbage that decodes as valid, so the yield is the fidelity, as the reviewer stated, and comparing to the Schwinger runs by Trotter-step count was misleading. The design rule is therefore: circuits of one coarse step (≤ 500 CZ, f ≳ 0.2 on a Heron-class device with ε ≤ 3×10⁻³), and shots chosen so that a configuration of ideal probability p is seen at least three times with 95% probability,

$$S \ge \frac{6.3}{0.82\,f\,p} \simeq \frac{7.7}{f\,p}\quad(\text{Poisson mean } 6.3),\ \text{e.g. } f = 0.2,\ p = 10^{-3}:\ S \approx 3.9\times10^4 \text{ per circuit}, \tag{5}$$

which Nighthawk r2 (10⁵ circuits per second) executes in seconds and Heron (4×10³ per second) in a quarter of a minute. Total budgets of 2×10⁵ shots per sector are assumed below.

## 5 Step 5 — HPC post-processing: projected diagonalization and certification

**5.1 Support and projected Hamiltonian.** Decode every shot (Step 2.5); B is the union of accepted configurations over all circuits of a sector, always including the references. Record, per circuit, the yield and the rejection reasons (flag / link / sector). Build H_B = P_B H P_B with the Step-3 builder, diagonalize, and keep the Ritz pairs (E^(k)_R, ψ^(k)_R).

**5.2 What is rigorous.** E^(0)_R ≥ E₀ for any B (variational). With |Ω⟩ the exact ground state and ε_B = ‖(𝟙 − P_B)Ω‖²,

$$0 \le E^{(0)}_R - E_0 \le \frac{\varepsilon_B\,(E_{\max} - E_0)}{1 - \varepsilon_B}. \tag{6}$$

Higher Ritz values bound the corresponding exact levels from above only in the min–max sense, and differences of Ritz values (MB, Δ0, V(r), V(2) − V(1)) are differences of upper bounds with errors of either sign. They are therefore reported only with two-sided intervals from 5.3.

**5.3 Certification** (replaces the "Krylov residual"). Compute the Hamiltonian residual with the exact H applied to the Ritz vector (its support is B ∪ N(B), a cheap classical operation),

$$r_H = \|(H - E_R)\psi_R\|. \tag{7}$$

Two statements are rigorous for any B: E_R ≥ E₀, and (Weinstein) some exact eigenvalue lies in [E_R − r_H, E_R + r_H]. Turning them into a two-sided interval for E₀ needs a gap assumption: if the exact level nearest to E_R is the ground state (guaranteed when r_H < E₁ − E_R), then E₀ ∈ [E_R − r_H, E_R]; and (Kato–Temple) if α ≤ E₁ with α > E_R, then E₀ ≥ E_R − r_H²/(α − E_R). We use the second Ritz value as α, which is an upper bound of E₁ rather than a lower bound, so both intervals are labelled gap-assumed; the assumption is checked on the simulator at 2×3 and 2×4 and is stated with every hardware number. The certified interval is I₀ = [E_R − δ, E_R] with δ = r_H (Weinstein, gap-assumed) or δ = r_H²/(α − E_R) (Kato–Temple, gap-assumed). Differences are reported by interval arithmetic, MB ∈ [E_R^{B=1} − E_R^{B=0} − δ₁, E_R^{B=1} − E_R^{B=0} + δ₀]. For a near-degenerate cluster (B = 1) Weinstein certifies the cluster energy to ±r_H; resolving the splitting requires r_H below the splitting (0.024 at 2×3), which is a preregistered stretch goal, not a gate. The quantity ‖(𝟙 − P_B)e^{−iHΔt}ψ_R‖ of the first version is a subspace-closure diagnostic (it vanishes for any exact eigenstate inside B) and is kept only as a convergence monitor. Worked example (2×3, B = 0, emulated f = 0.1, 5×10⁴ shots): |B| = 123, E_R = −5.5929, exact −5.6026, r_H = 0.281, Weinstein [−5.874, −5.593], gap-assumed [−5.622, −5.593]; B = 1: |B| = 76, E_R = −3.8078, exact −3.8261, r_H = 0.189, Weinstein [−3.997, −3.808], and the gap-assumed bound is not valid because the second Ritz value (−3.454) is far above the true second level (−3.802) — exactly the near-degeneracy caveat.

**5.4 Support metrics.** With the exact support S_ε (smallest set carrying 1 − ε of the ground-state weight): recall R_ε = |B ∩ S_ε|/|S_ε|; false-positive count |{b ∈ B : |⟨b|Ω⟩|² < 10⁻⁸}|; yield; and the error E_R − E₀. At 2×4 and beyond, where |Ω⟩ is known only from Lanczos on the simulator, the same metrics are computed against the Lanczos vector; on hardware runs without an exact reference the device support is compared with the CIPSI support (Step 6) instead.

## 6 Step 6 — Classical-support controls and the primary endpoint

**6.1 The referee's question.** Because the diagonalization is variational for any B, the only quantum content of the experiment is the choice of B; the question is whether the device support beats a classical support of the same size. Four controls are preregistered, all producing supports of prescribed size |B| in the sector: (a) CIPSI selected CI: start from the references; iterate diagonalize, score the Hamiltonian neighbours b ∉ B by |⟨b|H|ψ_R⟩|²/(H_bb − E_R), add the top batch; (b) BFS neighbour growth truncated at random; (c) random configurations of the sector; (d) oracle: the top-|B| configurations by exact weight (a lower envelope, simulator only); plus (e) ML-alone (Step 7) and (f) device-seeded CIPSI. The first version's "add all neighbours" baseline is null by construction (neighbour growth reaches the whole 677-state sector in a few iterations), which is why all controls are size-matched.

**6.2 Emulated outcome (Fig. 1, Table 3).** At 2×3 CIPSI tracks the oracle at every size and beats the device support at equal |B|: at |B| = 160 the errors are 1.2×10⁻³ (CIPSI), 1.2×10⁻³ (oracle), 3.5×10⁻³ (ML-alone), 7.6×10⁻³ (BFS), 8.6×10⁻³ (device, f = 0.1). Seeding CIPSI with the device support does not help (1.7×10⁻³ vs 1.2×10⁻³ at |B| = 160). The same holds at 2×4: multi-reference coarse circuits with f = 0.1 and 2×10⁵ shots give |B| = 544, error 7.5×10⁻³, recall 0.94, while CIPSI reaches 2.7×10⁻³ at |B| = 640 (oracle 2.75×10⁻³) and ML-alone 8.4×10⁻³. The plan therefore does not expect a device advantage at these sizes, and says so in the preregistration. **6.3 Primary endpoint.** The preregistered primary endpoint is the pair of curves E_R − E₀ and R_{10⁻³} versus |B| for the device support and for CIPSI at equal |B|, on 2×3 hardware data, together with the certified intervals of Step 5. A "device advantage" would be declared only if the device curve lies below the CIPSI curve at equal |B| over the whole range with non-overlapping bootstrap bands; the expected result is a characterized null, which is publishable as the first measured support-quality curve for a non-Abelian theory. **6.4 Production mode.** For the physics numbers the union of device support and CIPSI growth is used (never worse than either), with both components' contributions reported.

**Table 3: Emulated Ritz error E_R − E₀ at equal support size, 2×3, g² = 4, m = 0.75** (means over repetitions; device proxy: single reference, d = 5 exact Krylov, f = 0.1, 10⁴ shots per circuit, top-|B| by count).

| | B = 0 (677 states) |||||  B = 1 (426 states) ||||| 
|---|---|---|---|---|---|---|---|---|---|---|
| \|B\| | 20 | 40 | 80 | 160 | 320 | 20 | 40 | 80 | 160 | 320 |
| oracle | 1.1e-1 | 2.5e-2 | 1.0e-2 | 1.2e-3 | 6.7e-5 | 1.3e-1 | 5.7e-2 | 1.0e-2 | 9.8e-4 | 6.5e-6 |
| CIPSI | 1.1e-1 | 2.5e-2 | 1.0e-2 | 1.2e-3 | 6.5e-5 | 5.1e-2 | 2.3e-2 | 1.4e-2 | 1.0e-3 | 6.7e-6 |
| ML alone (ridge) | — | 2.6e-2 | 1.5e-2 | 3.5e-3 | 3.4e-4 | — | 6.9e-2 | 1.5e-2 | 4.1e-3 | 1.2e-4 |
| BFS | 1.5e-1 | 8.4e-2 | 1.8e-2 | 7.6e-3 | 6.2e-4 | 8.9e-2 | 2.5e-2 | 2.0e-2 | 1.4e-2 | 1.2e-2 |
| random | 1.05 | 1.05 | 0.86 | 0.88 | 0.73 | 0.83 | 0.77 | 0.71 | 0.46 | 0.13 |
| device proxy | 1.6e-1 | 3.5e-2 | 1.7e-2 | 8.6e-3 | 6.3e-3 | 7.3e-2 | 2.8e-2 | 2.1e-2 | 1.7e-2 | 1.2e-2 |

## 7 Step 7 — The gauge-invariant neural importance model (classical)

**7.1 Definition.** f_θ(b; λ) ≈ log|⟨b|Ω_λ⟩| with λ = (g², m, B, Lx, static-charge placement) as explicit inputs, so that the same configuration may have different targets at different parameters. Inputs: per-vertex features (nx, sublattice parity, ιx, degree, static flag), per-link features (jℓ, direction x/y, orientation), on the lattice graph; a message-passing network with a scalar readout, invariant under the lattice symmetries that permute labels. The model is gauge-invariant (its inputs are gauge-invariant labels and its output a scalar); it is not equivariant and is not a quantum model. Loss: pairwise ranking loss on (b, b′) pairs from the same λ (what selection needs) plus a floored regression term,

$$\mathcal L = \sum_{(b,b'):|\langle b|\Omega\rangle|>|\langle b'|\Omega\rangle|}\log\big(1 + e^{f_\theta(b') - f_\theta(b)}\big) + \mu\sum_b\Big(f_\theta(b;\lambda) - \log\max\big(|\langle b|\Omega_\lambda\rangle|, 10^{-6}\big)\Big)^2. \tag{8}$$

**7.2 Leakage-safe data.** Training amplitudes come only from parameter points and lattices that are not test points: 2×2 at g² ∈ {1, 1.5, 2, 3, 6} and 2×3 at g² ∈ {1, 2, 6} for the 2×3, g² = 4 test; everything up to 2×3 (all couplings) for the 2×4 test. Hardware SKQD Ritz vectors may be added for self-training only for lattices/parameters that are themselves not test points. Splits are by (λ, lattice), never by row.

**7.3 Uses and their formulas.** (i) Recovery of a flagged or link-inconsistent bitstring y: candidate set = valid configurations within Hamming distance 2 of y in codeword space; accept b with the calibrated posterior

$$p(b\,|\,y) \propto p_{\text{noise}}(y\,|\,b)\,e^{2f_\theta(b;\lambda)},\qquad p_{\text{noise}}(y\,|\,b) = \prod_q\big[(1 - p_q)\delta_{y_q b_q} + p_q(1 - \delta_{y_q b_q})\big], \tag{9}$$

with per-qubit readout error rates p_q from the confusion calibration of Step 9; recovered samples are tagged and B is reported with and without them. Baseline: occupation-number recovery in the style of S-CORE [3]. (ii) Size-constrained extension: among the Hamiltonian neighbours of B add the top-k by f_θ; baseline: CIPSI's PT2 score. (iii) ML-alone proposal: the top-|B| configurations of the sector by f_θ (Table 3, Fig. 1); (iv) transfer: a model trained up to 2×3 proposes supports for 2×4.

**7.4 Demonstration with a minimal model.** Even a ridge regression on 16 hand-built gauge-invariant features (numbers of flux links by direction, quarks on even sites, holes on odd sites, "meson" links, flux loops, vertices with two or three flux ends, Σι, and the diagonal energy H_bb relative to the Dirac sea), trained leakage-safely as in 7.2, ranks the 2×3, g² = 4 configurations with Spearman 0.85 (B = 0) and 0.89 (B = 1) and gives near-oracle supports from |B| = 160 upward (recall 0.99; Table 3); transferred to 2×4 it reaches error 8.4×10⁻³ and recall 0.95 at |B| = 640 (oracle 2.75×10⁻³). This sets the bar the graph network must clear; it also shows that ML-alone already beats the device proxy at equal |B| at these sizes.

**7.5 Preregistered comparison table.** Every physics number is produced under seven protocols at equal |B| and shots: raw device; device + post-selection; device + classical (S-CORE-style) recovery; ML alone; device + ML recovery/extension; CIPSI; exact enumeration where feasible. The model is credited for a use only if it beats the corresponding baseline at equal |B| on 2×3 hardware data and on held-out couplings; otherwise the null is reported and the classical recovery is kept.

## 8 Step 8 — Noise simulation before hardware

**8.1 Why the first emulator was wrong.** Replacing 10% of survivors by uniformly random valid configurations is randomized basis completion, not noise: with 0% replacement the 2×2 error at d = 4, 300 shots is 8.7×10⁻³, with 10% it drops to 4.7×10⁻³ (reviewer's rerun). **8.2 Proxy used here.** Each shot is clean with probability f; otherwise it is, with equal probability, a uniformly random bitstring or a clean sample with Poisson(2) random bit flips; independent readout flips at 1% per qubit are applied to all shots; then the decoder of Step 2.5. Garbage is rejected with probability ≥ 99.8%; local corruption produces the false positives and the lost clean shots the false negatives.

**Table 4: Device-proxy emulation, 2×3, B = 0, g² = 4:** single reference, five exact Krylov states (Δt = 0.156), p_ro = 1%. Entries: Ritz error / |B| / recall of the 99.9% support / false positives; the accepted-shot yield is 0.82 f in every row. Last row: multi-reference coarse circuits at the same total budget.

| fidelity f | 10³ shots per circuit | 10⁴ shots per circuit | 3×10⁴ shots per circuit |
|---|---|---|---|
| 1.00 | 1.5e-2 / 79 / 0.74 / 0 | 1.8e-3 / 166 / 1.00 / 0 | 7.6e-4 / 228 / 1.00 / 2 |
| 0.30 | 3.0e-2 / 58 / 0.56 / 0 | 5.7e-3 / 140 / 0.93 / 5 | 1.5e-3 / 209 / 1.00 / 11 |
| 0.10 | 8.4e-2 / 41 / 0.40 / 0 | 1.1e-2 / 119 / 0.81 / 6 | 3.4e-3 / 191 / 0.97 / 15 |
| 0.03 | 1.5e-1 / 32 / 0.29 / 1 | 1.9e-2 / 101 / 0.71 / 5 | 7.9e-3 / 171 / 0.89 / 14 |
| 0.10, 8 references × 5 coarse circuits, 5×10⁴ shots in total | 2.9e-3 / 190 / 0.97 (B = 1, 3 references: 4.6e-3 / 154 / 0.94) | | |

**8.3 Required before hardware.** Transpiled-circuit simulation with Qiskit Aer device noise models built from the current calibration (CZ/ECR errors, T₁, T₂, readout confusion) of the target qubits; report yield, recall, false-positive and false-negative rates per circuit family and per sector; fix the shot budget by Eq. (5) from the measured f. Gate S3: recall of the 99.9% support ≥ 0.9 in simulation for the production circuit set.

## 9 Step 9 — Hardware execution

**9.1 2×2 calibration run (12 qubits, one session).** Purpose: validate the codewords, decoder and sector filter on real bitstrings; measure yield versus CZ count with the one-step circuits (N_CZ ≈ 250, 500, 750 by repetition); measure the per-qubit readout confusion for Step 7.3; verify the flux-bit parity checks. The Ritz energies are computed but are not an accuracy test (the sectors saturate); their agreement with the exact values is a consistency check of bit order and conventions (gate H0). **9.2 2×3 production (20 qubits; 21 for the r = 1 static sector).** Sectors: vacuum (B = 0), baryon (B = 1), static pair r = 1 and r = 2; circuit set: references of Step 4.2 × coarse steps k = 1..4 (32–44 circuits per sector) at ≤ 500 CZ each; shots from Eq. (5) with the measured f, budget 2×10⁵ per sector; mitigation limited to what helps sampling (dynamical decoupling, Pauli twirling, readout confusion calibration); everything else is post-selection. Two calibration windows if quota permits. **9.3 Optional 2×4 (28 qubits)** only if gates H1–H2 pass with recall ≥ 0.9; otherwise 2×4 stays on the simulator.

## 10 Step 10 — Analysis, gates, error budget, reporting

| gate | check | criterion / status |
|---|---|---|
| E1 | [Ga(x), H] = 0; 82-dim kernel; sector split; two builders agree to 10⁻¹² | done (8×10⁻¹⁵) |
| E2 | counts of Table 2; codec round trip on all 2×3 states; random-bitstring acceptance ≈ 0.15% | done |
| E3 | 2×3 and 2×4 references (Table 1); static sectors; Δt = π/W per sector | done |
| S1 | emulated support recall ≥ 0.9 at f ≥ 0.1 with the production budget; controls table | done (Tables 3, 4) |
| S2 | routed CZ per coarse step ≤ 500 on the target map; noiseless compiled circuits leak-free | week 2 |
| S3 | Aer device-model recall ≥ 0.9 for the production set; shot budget fixed | week 2 |
| H0 | 2×2: decoder validity, bit order, parity checks; measured f within 30% of the model | week 3 |
| H1 | 2×3 B = 0: certified interval I₀ of width ≤ 0.1 containing the exact E₀; recall ≥ 0.8 | week 4 |
| H2 | 2×3 B = 1: cluster energy certified to ±r_H ≤ 0.15; V(1), V(2) intervals containing exact values | week 4 |
| P1 | primary endpoint curves (Step 6.3) with bootstrap bands; advantage declared only under the stated rule | week 5 |
| M1 | ML uses credited only under Step 7.5; null otherwise | week 5 |

Error budget (per number): truncation (jmax = ½ → 1 at 2×2: 82 → 152 states, computed exactly); subspace (certified interval of Step 5.3); device (enters only through B: reported as recall, false-positive count and yield, and by the CIPSI comparison); shot (bootstrap over circuits); classical (none at these sizes). Reporting. Every table carries the seven protocols of Step 7.5 at equal |B|, the certified intervals, and the support-quality metrics; the raw bitstrings, calibration snapshots, circuits and decoder are released.

## 11 Timeline (six weeks) and Plan B

| week | work | exit evidence |
|---|---|---|
| 1 | port the Step-3 builder into the SU2ZX repository; reproduce Tables 1–2; static sectors; codec and decoder; Δt per sector; emulator with the proxy of Step 8.2; preregistration draft with the controls of Step 6 | E1–E3, S1 |
| 2 | circuits (coarse and Trotterized families) in the local encoding; routing and CZ counts; Aer device-model simulation; shot budget; ML model v1 with leakage-safe splits; controls implemented; preregistration signed | S2, S3 |
| 3 | hardware 2×2 calibration (Step 9.1); readout confusion; measured f; 2×3 pilot (10⁴ shots per circuit) | H0 |
| 4 | hardware 2×3 production, four sectors, two calibration windows; decoding, certification | H1, H2 |
| 5 | primary-endpoint analysis; seven-protocol tables; ML tests; 2×4 transfer on the simulator; optional 2×4 hardware | P1, M1 |
| 6 | research note with claim table; release of builder, decoder, circuits, bitstrings; hand-off to 2×5 and to string breaking in V(r) | release bundle |

**Plan B.** If gate S3 fails (recall < 0.9 at the achievable f), reduce the circuit set to k = 1, 2 coarse steps (≤ 500 CZ) and raise shots by Eq. (5); if H1 fails, the production numbers are taken from the union support of Step 6.4 and the hardware result is reported as the measured support-quality curve alone. The first version's Plan B ("the 2×3 pure-gauge static sector with 4 states") is corrected: with the intertwiner at the charged interior vertex the r = 1 sector has 5 states (r = 2: 4), and with quarks 1 089 (r = 1) and 978 (r = 2) B = 0 states; the pure-gauge sector remains the fallback for the static potential only.

## A Algorithms (pseudo-code for the implementation)

All routines below exist as validated numpy/scipy reference implementations in the release bundle (spinnet.py, skqd23.py, run_skqd23.py, ml_importance.py and count_labels.py). The SU2ZX port should reproduce Tables 1–4 before any circuit is written. *(Note for this package: that bundle was not available; `src/skqd/` is an independent implementation of Algorithms 1–3 that reproduces Tables 1–4 — see reports/.)*

**Algorithm 1 — Local singlet tensors and basis enumeration (Steps 2–3).** VERTEXTENSORS(ends = (je, role_e)_{e=1..K}, n, charge): build Ga = Σe [J^(je)_a (out), −J^(je)⊤_a (in)] + Qa|n + ½σa|charge on the local space ⊗_e ℂ^{2je+1} ⊗ Fn (⊗ ℂ²); N ← orthonormal kernel of Σa G²_a (dimension 0, 1 or 2 here); if dim N > 1 then diagonalize Σk 7^{k−2}(J₁ + ··· + Jk)² on N (k = 2..K′ − 1 over ends, matter, charge) — fusion-tree label ι; return list of tensors T^(ι) reshaped to [d_{e1}, ..., d_{eK}, d_n(, 2)]; cache by signature. ENUMERATEBASIS(lattice): for {jℓ} ∈ {0, ½}^{Nℓ}, {nx} ∈ {0,1,2}^{Nv}: kx ← |VERTEXTENSORS(ends(x), nx, charge(x))| for all x; skip if any kx = 0; emit b = ({jℓ},{nx},{ιx}) for every {ιx} ∈ Π_x{0..kx − 1}; store B(b) = ½ Σx (nx − n^vac_x).

**Algorithm 2 — Matrix elements and Hamiltonian neighbours (Step 3.2).** MATEL(b′, b, touched vertices V, link blocks {Oℓ}, site operators {Fx}): assign an index letter to every ket and bra m of each touched link end; the same letter to bra and ket for untouched ends of touched vertices and for untouched matter; operands: Oℓ[m′L, m′R, mL, mR], Fx[c′x, cx], T^(ιx)_x[...], T′^(ι′x)_x[...] for x ∈ V; return einsum of all operands to a scalar (times the JW sign Π_{z between}(−1)^{nz} for hopping). BUILDH(basis, g², m): diagonal: m Σx (−1)^{x₁+x₂} nx + (g²/2)(3/4) Σℓ jℓ (independent of ι); for each b and each link ℓ = (x → y) with nx < 2, ny > 0 (hopping): labels j′ℓ = ½ − jℓ, n′x = nx + 1, n′y = ny − 1; for every ι′ at x, y present in the index: v ← −½ηℓ Σij MATEL(·) with Oℓ = Uij block, Fx = ψ^{loc†}_{x,i} Px (if x < y), Fy = ψ^{loc}_{y,j} (or Py ψ^{loc}_{y,j} if x > y); add v and v̄; for each b and each plaquette P: flip its four j's; for every ι′ at the corners: v ← −(1/2g²) Σijkl MATEL(·) with blocks Uij, Ujk, U†lk, U†il; add v, v̄; return sparse H (assert H = H†); NEIGHBOURS(B) = column support of H restricted to rows B, minus B.

**Algorithm 3 — One SKQD sector run with certification and controls (Steps 4–6).** references R (Step 4.2); Δt = π/W_B; circuits {C_{r,k}}: one coarse step of size kΔt from r ∈ R, k = 0..4; shots S from Eq. (5); for each circuit: execute S shots; DECODE(bitstring) (Step 2.5) → accepted b or reason; log yield and reasons; B ← R ∪ {accepted b} (recovered samples tagged separately, Step 7.3); H_B ← rows/columns of H on B; Ritz pairs (E^(k)_R, ψ^(k)_R); r_H ← ‖(H − E_R)ψ_R‖ using H on B ∪ NEIGHBOURS(B); intervals: Weinstein [E_R − r_H, E_R], gap-assumed [E_R − r_H²/(E^(1)_R − E_R), E_R]; controls at |B_dev|: CIPSI(references, |B_dev|), BFS, random, ML-alone, device-seeded CIPSI; on the simulator also oracle, recall R_{10⁻³}, false positives; report the seven-protocol table (Step 7.5) and the primary-endpoint curves (Step 6.3). CIPSI(B₀, target size, batch): while |B| < target: Ritz (E_R, ψ_R) on B; score each c ∈ NEIGHBOURS(B) by |⟨c|H|ψ_R⟩|²/(H_cc − E_R); add the top batch.

**Notes on the Project 1 remarks (for the record).** Not addressed in this document, but accepted: the fuzzy–KS comparison should be made at matched physical coupling (matching the single-link electric gap) in addition to matched bare g²; the all-F = +1 sector is an exact reduction of the K1 theory but its representativeness must be shown by comparing at least the (+++−) and (+−+−) patterns; the four-cluster factorization stays a numerically verified conjecture until the algebraic proof is written; "flux-tube dynamics between static charges" is the correct wording, not "confined pair".

## References

[1] J. Yu, J. Robledo Moreno, J. T. Iosue et al., "Quantum-centric algorithm for sample-based Krylov diagonalization," arXiv:2501.09702.
[2] E. O. Rosanowski, J. Eisinger, L. Funcke et al., "Sample-based Krylov quantum diagonalization for the Schwinger model on trapped-ion and superconducting quantum processors," arXiv:2510.26951.
[3] J. Robledo-Moreno et al., "Chemistry beyond exact solutions on a quantum-centric supercomputer," arXiv:2405.05068.
[4] T. Izubuchi, "Hybrid HPC-QC strategies for lattice gauge theory," discussion draft, 18 August 2026.
[5] R. S. Sufian, P. Bedaque, T. Izubuchi, K. Yu, "AI-Accelerated Non-Abelian Gauge Dynamics on Quantum Hardware," Genesis Phase-I proposal (2026), Eq. (1), §2.0 (iii), §4.2, §7.
[6] SU2QC Nine-Month Plan (7 September 2026).

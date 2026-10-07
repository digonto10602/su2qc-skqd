# Candidate encodings for SU(2) + staggered quarks on 2xL ladders at $j_{\max}=\tfrac12$ (planner list, 2026-10-07)

**Date:** 2026-10-07   **Git commit at writing:** `6b72ac2`   **Prompt in force:** `prompts/34_encoding_comparison.md` (written with this report)
**Author:** planner-fable (Fable 5.1, high)   **Trigger:** the owner's request of 2026-10-07 (verbatim):
*"how many encodings have you tried with? make planner a list of encoding such as spin-network encoding and others, test if that shortens the required number of qubits and gate and depth numbers. first use the planner to list all the encoding we can try on these circuits"*

Related: `reports/PACKAGE_FULL_REPORT_20261006.md` (sections 2.5, 2.6, 8.3, appendix (j)), `prompts/11` (the S2
decision: "the exact coarse step cannot meet the CZ budget in this encoding"), `prompts/27` (the Gauss-law codewords
as a distance-2 detection code), `validation/S2.json`, `validation/S2_2x4.json`, `validation/E2.json`,
`validation/CV_2x3_plan.json`, `data/quantinuum/devices_20261002.json`.

**Rule 1.** Every number below is (i) from a `validation/*.json` or `data/*.json` file (named), (ii) from an arXiv
abstract I fetched on 2026-10-07 (arXiv id given), or (iii) **planner arithmetic / planner prototype**, labelled as
such and reproducible from `scratch/planner/encodings_prototype_20261007.py` (output
`scratch/planner/encodings_prototype_20261007.json`, log `*.log`, `*_2x3.log`) and
`scratch/planner/encodings_pauli_20261007.py` (output `encodings_pauli_20261007.json`).  Prototype numbers are
**not gate results**; `prompts/34` turns the ones that matter into gate `ENC_compare`.

---

## 0. Answer to "how many encodings have you tried?"

**One.** The package has exactly one qubit encoding, `src/skqd/codec.py::Codec` (graphify: the only `Codec`-type
class in `src/`; `reference_sim.CodewordEmbedding` embeds the same codewords into a statevector).  Every compiled
circuit of the project (gates S2, S2_2x4, S2D, Q0P_2x3, K0, K1, H0 family, campaign33 families) uses it.  Its
layout, verified in the code:

- one **flux bit** per *link end* ($j_\ell=\tfrac12\Leftrightarrow 1$), so every link bit is stored **twice**
  (once at each end vertex);
- one extra bit per corner vertex, one per interior vertex (occupation $n_x\in\{0,2\}$ as $n/2$, or the
  intertwiner label $\iota_x$, or a *leakage flag*);
- totals $N_q = 2N_\ell + N_s$ (planner arithmetic, equal to `Codec.n_qubits`): **12** (2x2: $N_\ell=4,N_s=4$),
  **20** (2x3: 7, 6), **28** (2x4: 10, 8).

The decoder (`Codec.decode`) rejects a measured string if any vertex is flagged, if the two copies of a link bit
disagree ("link" check), or if the baryon number is wrong ("sector" check).  `prompts/27` showed this is a
distance-2 error-*detecting* code at zero gate cost.  The prototype quantifies it (section 4): at 2x3 the decoder
catches **98.2 %** ($B=0$) / **98.3 %** ($B=1$) of all single bit flips of valid codewords, and a uniformly random
20-bit string is accepted into $B=0$ with probability $677/2^{20}=6.46\times10^{-4}$ (planner arithmetic; the
sector-summed value $1727/2^{20}$ is gate E2's).

**Jargon used below.** *Codeword*: the bit string assigned to one physical basis state.  *Pauli weight* of an
operator term: the number of qubits on which a Pauli string (product of $X,Y,Z$ on some qubits, identity elsewhere)
acts non-trivially; a Hamiltonian term written as a sum of Pauli strings costs more two-qubit gates the higher the
weight and the more strings it has.  *Support* of a term: the set of qubits its compiled block unitary touches.
*Random acceptance* $a$: the probability that a uniformly random bit string passes the decoder into the target
sector; $a=\dim(\text{sector})/2^{N_q}$ when every sector state is a codeword.  *Saturation parameter* (project rule
C22): $Na/\dim$, with $N$ the shots of a sector; above about 5 the accepted support fills the sector from noise alone.

---

## 1. Counting conventions used for (a)

Geometry (`src/skqd/lattice.py`): $N_s=2L_x$ sites, $N_\ell=3L_x-2$ links, $N_P=L_x-1$ plaquettes; 4 corner
vertices (2 link ends) and $2L_x-4$ interior vertices (3 link ends).  Sector dimensions (`data/references.json`,
manual Table 2, reproduced by `enumerate_basis` in the prototype): 2x2 38 / 20, 2x3 677 / 426, 2x4 12 843 / 8 934
($B=0$ / $B=1$); whole basis 82 / 1 727 / 37 165.  Local singlet spaces at $j_{\max}=\tfrac12$ (manual 2.1, gate E2):
corner 6 states, interior 13, charged corner 7, charged interior 17.

| encoding | formula | 2x2 | 2x3 | 2x4 |
|---|---|---|---|---|
| E1 current (vertex-local, link bits duplicated) | $2N_\ell+N_s$ | 12 | 20 | 28 |
| E2 dedup (one flux bit per link + one bit per vertex) | $N_\ell+N_s$ | 8 | 13 | 18 |
| E3 dedup + one parity bit per vertex | $N_\ell+2N_s$ | 12 | 19 | 26 |
| E4 dense sector ($B=0$ / $B=1$) | $\lceil\log_2\dim\rceil$ | 6 / 5 | 10 / 9 | 14 / 14 |
| E4' dense whole basis | $\lceil\log_2\dim\rceil$ | 7 | 11 | 16 |
| E5 unary vertex labels (information) | $6\cdot4+13\,(2L_x-4)$ | 24 | 50 | 76 |
| E6 LSH, unary loop numbers (3 / 5 bits per corner / interior) | $12+5(2L_x-4)$ | 12 | 22 | 32 |
| E6' LSH, dense interior vertex | $12+4(2L_x-4)$ | 12 | 20 | 28 |
| E7 Schwinger-boson / prepotential, gauge not solved | $4N_\ell+2N_s$ | 24 | 40 | 56 |
| E7' Kogut-Susskind $\lvert j,m_L,m_R\rangle$ (5 states/link), gauge not solved | $3N_\ell+2N_s$ | 20 | 33 | 46 |
| E8 pure-fermionic + residual loop links (maximal tree) | $2N_s+3N_P$ | 11 | 18 | 25 |
| E10 qudits | $N_s$ qudits of 6 / 13 levels | 4 | 6 | 8 |

(all planner arithmetic, `encodings_prototype_20261007.json -> sections.A_counts`; E1 checked against
`Codec.n_qubits`.)  Static-charge sectors are not in the table: the dedup prototype supports uncharged vertices only,
and the current codec needs 5 bits for a charged interior vertex (manual 2.4).

---

## 2. The candidates, one by one

For each: (a) qubits, (b) Hamiltonian terms in that encoding (ESTIMATE until compiled unless stated), (c) what
happens to the Gauss-law error detection, (d) whether the conventions / gates E1-E3 still apply and how equivalence
would be verified, (e) effort in this package, (f) source.

### E1. The current vertex-local encoding (baseline)

(a) 12 / 20 / 28.  (b) Terms are exact block unitaries on supports of 6-14 qubits (`validation/S2.json ->
data.2x3.per_term_structure`): hopping supports 6-10 qubits, plaquette supports 12 (2x2) and 14 (2x3); one coarse
step compiles to 256 CZ all-to-all / 618 routed heavy-hex at 2x2 and 2 164 / 5 477 at 2x3 (`validation/S2.json`),
2 158 ZZPhase on the Quantinuum native set (`data/quantinuum/devices_20261002.json -> counts.2x3`), 69 688 CZ
all-to-all at 2x4 (`validation/S2_2x4.json`).  If written as Pauli strings instead (prototype, `encodings_pauli`):
2x3 hopping terms have 96-512 Pauli strings of maximum weight 6-10 (e.g. `hop2`: 512 strings, weight 10); the 2x2
plaquette has 2 048 strings of weight 12.  (c) Full: single flips detected 100 % at 2x2, 98.2 / 98.3 % at 2x3; double
flips 95.9 / 98.2 % at 2x2 (prototype, exhaustive).  Random acceptance $a_{B=0}=38/4096$ (2x2, `validation/E2.json`),
$677/2^{20}$ (2x3).  (d) The reference.  (e) none.  (f) manual Step 2.4; `src/skqd/codec.py`.

### E2. The current scheme without the duplicated link bit ("dedup")

Layout: a link register ($N_\ell$ bits, one per link) and a vertex register (1 bit per uncharged vertex).  The vertex
bit means: corner with equal flux ends -> $n/2$; unequal -> $n=1$ and the bit must be 0 (1 = flag); interior with even
flux parity -> $n/2$; one flux end -> $n=1$, bit 0 (1 = flag); three flux ends -> $n=1$, bit $=\iota$.  A charged
interior vertex would need 2 bits (17 states, at most 4 per flux pattern; planner arithmetic, not prototyped).

(a) 8 / 13 / 18.  (b) **Prototyped through the package's own structured compiler** (`structured_term_gates`, codec
monkey-patched; every term verified against $e^{-i\Delta t H_\gamma}$ on random superpositions of all codewords to
$\le 7\times10^{-15}$; the current-codec path reproduces every per-term CZ count of `validation/S2.json` exactly,
which validates the harness).  Same $\Delta t=\pi/W_{B=0}$, same term family, diagonal term excluded on both sides
(it is 8 / 20 CZ in the current codec and of the same form in dedup):

| 2x3, coarse step without `diag` | current | dedup | ratio |
|---|---|---|---|
| qubits | 20 | 13 | 0.65 |
| CZ all-to-all (level 3, seed 7) | 2 144 | 1 984 | 0.925 |
| depth all-to-all | 7 312 | 6 958 | 0.952 |
| CZ routed, heavy-hex d=5 | 5 413 | 4 978 | 0.920 |
| depth routed | 11 372 | 10 288 | 0.905 |
| 2x2: CZ all-to-all / routed d=3 | 240 / 612 | 218 / 413 | 0.908 / 0.675 |

Per term at 2x3 (CZ all-to-all, current -> dedup): hop0 194 -> 188, hop1 48 -> 44, hop2 182 -> 166, hop3 184 -> 178,
hop4 358 -> 342, hop5 156 -> 152, hop6 44 -> 42, plaq0 214 -> 210, plaq1 764 -> 662.  Supports shrink (hop4 8 -> 7,
plaq1 14 -> 10) and the Pauli form gets lighter (hop2: 512 strings of weight 10 -> 128 of weight 8; 2x2 plaquette
2 048 of weight 12 -> 128 of weight 8), **but the number of multiplexed rotations and their control counts, which set
the structured cost, are unchanged** (hop4: 9 rotations with controls [6,5,3,6,5,6,5,5,3] in both).  The 7-8 %
saving is routing / cancellation, not structure.  (c) **Partly lost.** The link check disappears (it *was* the
duplication); flags and the sector check remain: single flips detected 89.5 / 100 % at 2x2 and **83.0 / 90.8 %** at 2x3
(double flips at 2x2: 78.2 / 90.0 %).  Random acceptance rises by $2^{N_\ell}$: $677/2^{13}=0.0826$ at 2x3 $B=0$
(128x the current value).  Consequence for the plan of record (`validation/CV_2x3_plan.json -> data.plan.f=0.10`,
34 909 shots at $B=0$ and 99 000 at $B=1$): the saturation parameter $N/2^{13}$ is **4.26** ($B=0$) and **12.1**
($B=1$) against 0.033 and 0.094 today (planner arithmetic) -- rule C22 says the $B=1$ sector would fill from
accidentally valid noise alone, and $B_{\rm sig}$'s $3\sigma$ line would sit at about $4.3+3\sqrt{4.3}\approx 10.5$
expected noise counts per state at $B=0$, above the $\lambda^*=6.30$ clean counts the D3'-R sizing provides.
(d) The Hamiltonian, basis and conventions are untouched (a relabelling of the same 1 727 states), so E1-E3 apply
verbatim; equivalence is verified by the S2 bars on the compiled circuits (exactness $\le10^{-10}$, leakage
$\le10^{-9}$) and a full encode-decode round trip.  (e) Medium: a second `Codec` class, a codec argument through
`term_support` / `localize` / `CircuitFactory` / `CodewordEmbedding`, dedicated `diag` gates; no change to any
signed circuit.  (f) This is "solving the Abelian Gauss law" of the LSH papers classically (arXiv:1812.07554,
abstract: "implementing gauge invariance (or Gauss's law) exactly"); the local Gauss-law solve in arbitrary
dimension is the theme of arXiv:2206.00685.

### E3. Dedup plus one parity bit per vertex

Restores a per-vertex check of the link bits (the parity bit stores the XOR of the vertex's link bits).
(a) 12 / 19 / 26 -- one qubit fewer than E1 at 2x3, with the same detection order; gates would not fall below E2.
Not worth a test (planner judgement).  (f) same as E2.

### E4. Dense (compact, $\lceil\log_2\dim\rceil$) sector encodings, binary or Gray

(a) 10 / 9 at 2x3, 6 / 5 at 2x2, 14 / 14 at 2x4.  (b) **No locality survives**: every term becomes a generic sparse
matrix on all qubits; one coarse step is a generic $2^{N_q}$ unitary.  Prototype at 2x2 (qiskit unitary synthesis,
level 3, seed 7): $B=0$ in 6 qubits costs **1 783 CZ** (depth 8 465), $B=1$ in 5 qubits 423 CZ -- against 256 CZ
for the whole 12-qubit step today.  The quantum-Shannon-decomposition bound $\tfrac{23}{48}4^{n}$ gives
$5.0\times10^{5}$ CZ at 10 qubits (2x3) and $1.3\times10^{8}$ at 14 (2x4) (planner arithmetic).  A Gray-code
assignment changes the constant, not the $4^n$ (arXiv:1909.12847 compares unary, binary and Gray for $d$-level
systems and finds the best choice "heavily dependent on the application"; here $d$ is the sector dimension).
(c) **Lost entirely** within the sector: every string is a valid state (random acceptance 0.66 at 2x3 $B=0$,
$677/1024$), saturation at $N\gtrsim 5\times1024$ shots.  (d) Equivalent by construction (same $H$), but the circuit
family would no longer be the signed one.  (e) Large (new synthesis path).  (f) arXiv:1909.12847.

### E5. Unary vs binary vs Gray for the link and vertex labels

Links are already 1 bit ($j\in\{0,\tfrac12\}$; nothing to gain).  The vertex block is already dense (6 states in 3
bits, 13 in 4); unary would cost 24 / 50 / 76 qubits (information only).  What *is* free in the current widths is the
**assignment** of the 13 interior codewords to the 16 four-bit patterns and the choice of the intertwiner tree
(manual 2.2: $\iota$ = intermediate spin of the first two ends): both change the control counts of the multiplexed
rotations and the number of non-zero matrix elements of the heavy terms (`hop4` 358 CZ, `plaq1` 764 CZ, both on
interior vertices).  ESTIMATE $\le1.3\times$ on those terms; detection unchanged; equivalence by the same spectra
(E1-E3 re-run if $\iota$ changes, because the matrix elements change).  Cheap to test (hours).  (f) arXiv:1909.12847
for the Gray-code trend; the tree choice is the package's own convention (manual 2.2).

### E6. Spin-network / loop-string-hadron (LSH) formulations

LSH (arXiv:1912.06133) rewrites SU(2) + staggered quarks in gauge-singlet loop, string and hadron variables, with
Gauss's law built in, in $d\le3$; the digitisation and qubit costs are discussed in arXiv:1812.07554 ("could save
or cost more qubits than a Kogut-Susskind-type representation basis, depending on how the bases are digitized");
1+1D algorithms in arXiv:2212.14030 (LSH "lowers the cost compared with the standard formulations"), the first
2+1D SU(2)-with-staggered-fermions LSH spin mapping in arXiv:2503.20828, and a 60-site, 156-qubit 1+1D hardware
run in arXiv:2602.18080.  Spin networks also underlie the q-deformed truncations of arXiv:2304.02527 and
arXiv:2305.05950 (2+1D SU(2)$_k$), which make a truncation *gauge-consistent* at the price of a different model.

**Planner reading for this lattice (not taken from the abstracts):** at $j_{\max}=\tfrac12$ the LSH local space of a
vertex is the same singlet space the package already enumerates (6 corner / 13 interior states); the LSH labels
(loop numbers per pair of ends, string bits) are another basis of it.  (a) a corner needs 1 loop bit + 2 string bits
= 3 qubits with 2 flagged patterns, an interior vertex 3 loop bits + 2 string bits = 5 (unary loops) or 4 (dense):
12 / 22 / 32 or 12 / 20 / 28 -- **no saving**.  LSH's "Abelian Gauss law" (the flux seen from the two ends of a link
must agree) *is* the link check of the current decoder, i.e. the current codec already is an LSH-type digitisation
with the Abelian constraint kept as a detector; solving it classically is E2.  (b) the LSH Hamiltonian is a sum of
local normalised ladder operators times diagonal factors; compiled exactly it is the same block unitary as today
(same local spaces, same matrix elements up to relabelling), so the same 2 158 ZZ; a Trotterised Pauli-string
version would be a *different*, unsigned circuit family.  (c) same as E1 (unary) or E2 (dense, Abelian law
solved).  (d) equivalence = same spectra (relabelling) plus E1-E3 if the vertex basis changes.  (e) medium-large
for a full LSH operator rewrite; zero for the count, which is the current one.  (f) arXiv:1912.06133,
1812.07554, 2212.14030, 2503.20828, 2602.18080.

### E7. Schwinger-boson / prepotential encodings (gauge not solved)

Prepotentials write each link end as an SU(2) doublet of oscillators (hep-lat/0403029: "SU(2) $\otimes$ U(1) local
gauge invariance", Gauss law solved "in terms of a set of gauge invariant integers" -- which, once solved, is LSH).
Unsolved: 2 oscillator modes per link end with total number $2j\le1$ (3 states, 2 qubits) and 2 colour modes per
site: (a) 24 / 40 / 56; the Kogut-Susskind electric basis $\lvert j,m_L,m_R\rangle$ (5 states, 3 qubits per link)
gives 20 / 33 / 46.  (b) local, low-weight Pauli terms (hopping touches one link and two sites), but the state space
is dominated by gauge-variant strings.  (c) the non-Abelian Gauss law is not diagonal in this basis, so only a partial
(e.g. $G_z$) check is possible; random acceptance of *physical* strings is tiny but the decoder cannot tell.
(d) a new builder; E1 would have to be redone in this basis.  (e) large.  **Information only.**  (f) hep-lat/0403029,
arXiv:2009.11802 ("purely bosonic" formulation analysed in 1+1D).

### E8. Purely fermionic formulations (gauge field integrated out) and maximal-tree gauge fixing

In 1+1D with open boundaries the gauge links can be eliminated exactly (arXiv:2009.11802 analyses the "purely
fermionic" formulation; arXiv:2102.08920 ran SU(2) hadrons on hardware this way; the converse, eliminating the
fermions, is arXiv:1805.05347 / 1905.00652; arXiv:2206.00685 solves Gauss's law and eliminates fermions in arbitrary
dimensions, demonstrated for $\mathbb Z_2$).  **On a ladder the plaquette loops survive:** a maximal tree has
$N_s-1$ links (3 / 5 / 7), leaving $N_\ell-(N_s-1)=N_P$ = 1 / 2 / 3 links that cannot be gauged away (planner
arithmetic).  (a) 2 colour modes per site + 3 qubits per surviving link: 11 / 18 / 25.  (b) tree-link hopping becomes a
plain fermion hop (Jordan-Wigner weight 2-4 on a ladder), the electric energy of a tree link becomes
$(\sum_{\text{subtree}}\vec Q)^2$ -- an all-to-all two-body colour-colour interaction, $O(N_s^2)$ terms of weight
about 4 -- and the plaquettes couple the loop links to the corner fermions.  (c) **lost**: Gauss's law is solved, only
the baryon-number check remains; random acceptance $=\dim/2^{N_q}$ as in E4.  (d) **Not equivalent at this
truncation.** The $j\le\tfrac12$ cut is defined on the original links; the gauge-fixing unitary mixes
representations between links, so a cut in the fixed frame is a different truncated theory and $E_0$ will not agree
to $10^{-12}$ (they agree only without truncation).  The owner would be changing the physics target, not the
encoding.  (e) large (new builder, new references).  **Declined for the comparison; listed for completeness.**
(f) arXiv:2009.11802, 2102.08920, 2206.00685, 1805.05347, 1905.00652, 2105.05870 (gauge-invariant circuit
families, U(1) and Yang-Mills).

### E9. Plaquette / dual / magnetic-basis formulations

Electric-magnetic duality and plaquette variables (arXiv:1806.08797, U(1) in 2 and 3 dimensions; arXiv:2211.10497,
2+1D U(1) with Gauss's law solved), magnetic-basis truncations for continuous groups (arXiv:2006.14160) and SU(2)
digitisations (arXiv:2201.09625, discrete subsets with a freezing analysis) all target the **weak-coupling** regime
where the electric truncation fails.  At $g^2=4$ with $j_{\max}=\tfrac12$ the electric basis is the natural one and
no magnetic digitisation reproduces the $j\le\tfrac12$ spectrum; qubit counts depend on the digitisation (one
$2^k$-point subset per loop link: $kN_P$ qubits plus the matter).  (c) no Gauss-law detector (constraints are
solved).  (d) not equivalent at this truncation.  **Information only.**

### E10. Qudit encodings

A corner vertex is a 6-level qudit, an interior vertex a 13-level one; a 2x3 ladder is 6 qudits with the link
agreement as the only constraint.  arXiv:2402.07987 runs 1+1D SU(2) with matter on 6-level ion qudits with
"a qudit encoding fulfilling gauge invariance"; arXiv:2403.14537 (qu8its, 1+1D SU(3)) reports "more than a factor of
five fewer" two-qudit entangling gates than qubits.  No qudit device is in the project's access list.
**Information only.**

### E11. Fermion-to-qubit maps for the quarks

In the dressed-site basis the quarks are absorbed into the vertex labels $(n_x,\iota_x)$; the Jordan-Wigner sign
$\prod_{x<z<y}(-1)^{n_z}$ is computed classically and enters the circuit only as a dependence of the hopping block
on the flux parity of the skipped sites (its support grows by 2-3 flux bits per skipped site, `term_support`).
With the site order $x_1L_y+x_2$ every x-link skips exactly one site (its rung partner), which is minimal for a
ladder (no linear order makes all ladder edges adjacent), and the heaviest term (`hop4`, 358 CZ) skips none: the
cost is the 13-state vertex spaces, not the string.  Bravyi-Kitaev (quant-ph/0003137), Verstraete-Cirac
(cond-mat/0508353) and compact mappings (arXiv:2003.06939) reduce Pauli weight of *fermionic* Hamiltonians; they do
not apply to block-unitary codeword circuits and would only matter in E8.  Changing the Jordan-Wigner order is a
convention change (E1-E3 re-run) with no expected gain.  **Not recommended.**

### E12. Mixed / partially gauge-fixed encodings

Fixing only the rung links (2 / 3 / 4 of them) keeps x-link flux labels but has the same truncation inconsistency as
E8 on the fixed links.  **Declined** with E8.

### E13. Encodings tailored to the architecture (all-to-all ions vs heavy-hex)

The encoding is the same; what changes is the qubit order and physical embedding.  Routing overhead today:
5 477 / 2 164 = 2.53x at 2x3 (`validation/S2.json`), 148 726 / 69 688 = 2.13x at 2x4 (`validation/S2_2x4.json`,
FakeFez map).  Fewer qubits route better (prototype: dedup 2x2 routed/all-to-all 1.89x vs 2.55x current; 2x3 2.51x
vs 2.52x).  On Quantinuum (all-to-all, `data/quantinuum/devices_20261002.json`) routing is absent and the ZZPhase
count is the only lever, which an encoding barely moves (E2: $-7.5$ %).  Patch selection (`scripts/h0_patch_select.py`)
already optimises the heavy-hex embedding; nothing new to build.

---

## 3. What the prototype says about "shortens"

Judged at fixed physics (same $\Delta t$, same signed term family, same reference set, same exactness bars):

| encoding | qubits 2x2 / 2x3 / 2x4 | two-qubit gates (2x3 coarse step) | depth | detection | status |
|---|---|---|---|---|---|
| E1 current | 12 / 20 / 28 | 2 164 CZ a2a, 5 477 routed, 2 158 ZZ | 7 325 / 11 540 | 98 % single flips; $a=6.5\times10^{-4}$ | signed |
| E2 dedup | 8 / 13 / 18 | **$-7.5$ %** a2a, $-8.0$ % routed (prototype, no diag) | $-4.8$ % / $-9.5$ % | 83-91 %; $a=0.083$ (128x); plan-of-record $B=1$ saturated ($N/2^{13}=12.1$) | test |
| E4 dense | 6 / 10 / 14 ($B=0$) | 2x2: 1 783 CZ vs 256 (7x worse); $\sim5\times10^5$ at 10 qubits (QSD bound) | worse | none | document only |
| E5' assignment / tree choice | 12 / 20 / 28 | ESTIMATE $\le1.3\times$ on hop4 + plaq1 | similar | unchanged | cheap test |
| E6 LSH | 12 / 20-22 / 28-32 | = E1 when compiled exactly | = E1 | = E1 or E2 | no count test |
| E7 bosonic / KS | 24 / 40 / 56, 20 / 33 / 46 | low weight, huge unphysical space | -- | partial | information |
| E8 fermionic + loops | 11 / 18 / 25 | nonlocal electric term | -- | none | not equivalent at $j\le\tfrac12$ |
| E9 magnetic / dual | digitisation-dependent | -- | -- | none | not equivalent, wrong regime |
| E10 qudits | 4 / 6 / 8 qudits | hardware-dependent | -- | link check only | information |
| E11 fermion maps | n/a (absorbed) | no gain | -- | -- | not recommended |

**Reading.** The two-qubit cost of the exact coarse step is set by the number of codeword pairs each term connects
and the controls needed to tell them apart -- a property of the *physics* (13-state interior vertices, 160 off-diagonal
elements in `hop2`/`hop3`, 17 rotation patterns in `plaq1`), not of how many qubits carry the labels.  No
relabelling at $j_{\max}=\tfrac12$ reaches the 500-CZ budget of `prompts/11`; the only encodings that cut qubits
substantially (E2, E4) pay with the Gauss-law detector that the whole 2x3 statistics plan rests on (near-clean
strings, $f_{\rm hit}$, $B_{\rm sig}$, rule C22).  Large gate savings can only come from *approximating the
generator* (the unsigned variants no-plaq1 / fixed-angle of `prompts/27` D4, which are not encodings) or from a
*different truncated model* (q-deformed spin networks, E6/E9), which changes the physics target.

---

## 4. Prototype numbers (planner, `scratch/planner/encodings_prototype_20261007.json`)

Error detection (exhaustive over every codeword of the sector and every single qubit flip; 2x2 also every pair):

| lattice, sector | codec | $N_q$ | single flips detected | by flag / link / sector | silently accepted as another valid state | double flips detected | $a$ |
|---|---|---|---|---|---|---|---|
| 2x2 $B=0$ | current | 12 | 456 / 456 = 100 % | 152 / 208 / 96 | 0 | 95.9 % | 0.00928 |
| 2x2 $B=1$ | current | 12 | 100 % | 120 / 64 / 56 | 0 | 98.2 % | 0.00488 |
| 2x2 $B=0$ | dedup | 8 | 272 / 304 = 89.5 % | 144 / 0 / 128 | 32 | 78.2 % | 0.148 |
| 2x2 $B=1$ | dedup | 8 | 100 % | 96 / 0 / 64 | 0 | 90.0 % | 0.078 |
| 2x3 $B=0$ | current | 20 | 13 292 / 13 540 = 98.2 % | 3 904 / 6 876 / 2 512 | 248 | -- | $6.46\times10^{-4}$ |
| 2x3 $B=1$ | current | 20 | 98.3 % | 3 354 / 3 362 / 1 660 | 144 | -- | $4.06\times10^{-4}$ |
| 2x3 $B=0$ | dedup | 13 | 7 309 / 8 801 = 83.0 % | 3 656 / 0 / 3 653 | 1 492 | -- | 0.0826 |
| 2x3 $B=1$ | dedup | 13 | 90.8 % | 2 875 / 0 / 2 151 | 512 | -- | 0.0520 |

Structured compile (2x3, CZ all-to-all / routed heavy-hex d=5, qiskit level 3 seed 7 as gate S2; the current column
equals `validation/S2.json` term by term): see section 2, E2.  Pauli form of the hopping blocks (2x3; strings / max
weight): hop0 512/9 -> 128/7, hop1 96/6 -> 48/5, hop2 512/10 -> 128/8, hop3 512/10 -> 128/8, hop4 512/8 -> 256/7,
hop5 512/9 -> 128/7, hop6 96/6 -> 48/5 (current -> dedup).

---

## 5. Ranking and recommendation

Ranked by expected reduction in (qubits, two-qubit gates, depth) against the loss of error detection and the
effort, at fixed physics:

1. **E2 dedup -- test it** (gate `ENC_compare`, `prompts/34`).  Measured prototype: $-35$ % qubits, $-7.5$ % CZ,
   $-5$ % depth at 2x3; detection falls from 98 % to 83-91 % of single flips and the random acceptance rises 128x.
   The test must report the saturation parameter at the plan-of-record shots (prototype: 4.3 and 12.1) and the
   gate-only and idle-aware $f$, so that the owner sees both sides of the trade.  Expected verdict (planner):
   "shortens qubits, does not shorten gates meaningfully, costs the decoder" -- the measurement is still worth
   having because it closes the owner's question with numbers.
2. **E5' codeword-assignment / intertwiner-tree search within the current widths -- test it** (cheap, keeps the
   detector, no qubit change).  Only hop4 and plaq1 are worth searching; gain ESTIMATE $\le1.3\times$ on those terms.
3. **E4 dense -- document, do not build**: the 2x2 synthesis number (1 783 vs 256 CZ) and the $4^n$ bound settle it.
4. **E6 LSH -- no qubit-count test** (same count); keep as the vocabulary in which E2 is "solving the Abelian Gauss
   law".  A Trotterised LSH circuit family is a separate, unsigned question.
5. **E8 / E9 / E12 -- decline** at this truncation (not equivalent to $10^{-12}$; different physics target).
6. **E7 / E10 / E11 / E13 -- information only.**

**Owner decisions needed.** (i) Is losing the link check acceptable at all for a hardware run, given that the 2x3
plan's shot sizing, $B_{\rm sig}$ and the near-clean analysis depend on $a\sim10^{-3}$?  The planner's reading is no,
unless the dedup circuits are at least 2x cheaper, which the prototype rules out.  (ii) Whether a *different
truncated model* (q-deformed SU(2)$_k$ spin networks, arXiv:2304.02527 / 2305.05950) may be opened as a new
physics target; it is not an encoding of the present one.  (iii) Whether the unsigned approximate generators of
`prompts/27` D4 (no-plaq1, fixed-angle) should be re-opened, since they are the only known route below 1 000 ZZ.

---

## 6. Sources (abstracts fetched 2026-10-07)

- arXiv:1912.06133 Raychowdhury, Stryker, *Loop, string, and hadron dynamics in SU(2) Hamiltonian lattice gauge theories*.
- arXiv:1812.07554 Raychowdhury, Stryker, *Solving Gauss's law on digital quantum computers with loop-string-hadron digitization*.
- arXiv:2009.11802 Davoudi, Raychowdhury, Shaw, *Search for efficient formulations for Hamiltonian simulation of non-Abelian lattice gauge theories*.
- arXiv:2212.14030 Davoudi, Shaw, Stryker, *General quantum algorithms for Hamiltonian simulation with applications to a non-Abelian lattice gauge theory*.
- arXiv:2503.20828 Yang, Matsuda, Huang, Kashiwa, *Quantum simulation of QC2D on a 2-dimensional small lattice* (LSH, 2+1D, staggered fermions).
- arXiv:2602.18080 Ilcic et al., *Observation of robust and coherent non-Abelian hadron dynamics on noisy quantum processors* (LSH, 60 sites, 156 qubits, 1+1D).
- hep-lat/0403029 Mathur, *Harmonic oscillator prepotentials in SU(2) lattice gauge theory*.
- arXiv:2206.00685 Pardo, Greenberg, Fortinsky, Katz, Zohar, *Resource-efficient quantum simulation of lattice gauge theories in arbitrary dimensions: solving for Gauss' law and fermion elimination*.
- arXiv:2102.08920 Atas et al., *SU(2) hadrons on a quantum computer*.
- arXiv:1805.05347 and arXiv:1905.00652 Zohar, Cirac, *Eliminating fermionic matter fields* / *Removing staggered fermionic matter in U(N) and SU(N) lattice gauge theories*.
- arXiv:1908.06935 Klco, Stryker, Savage, *SU(2) non-Abelian gauge field theory in one dimension on digital quantum computers*.
- arXiv:2101.10227 Ciavarella, Klco, Savage, *A trailhead for quantum simulation of SU(3) Yang-Mills lattice gauge theory in the local multiplet basis*.
- arXiv:2607.26445 Hidalgo, Draper, *Lattice quantum chromodynamics for quantum simulations* (representation basis with quarks, 2 and 3 spatial dimensions, up to 32 qubits).
- arXiv:1909.12847 Sawaya et al., *Resource-efficient digital quantum simulation of d-level systems* (unary / binary / Gray).
- arXiv:2304.02527 Zache, Gonzalez-Cuadra, Zoller, *Quantum and classical spin network algorithms for q-deformed Kogut-Susskind gauge theories*.
- arXiv:2305.05950 Hayata, Hidaka, *String-net formulation of Hamiltonian lattice Yang-Mills theories ...* (SU(2), 2+1D).
- arXiv:1806.08797 Kaplan, Stryker, *Gauss's law, duality, and the Hamiltonian formulation of U(1) lattice gauge theory*.
- arXiv:2006.14160 Haase et al., *A resource efficient approach for quantum and classical simulations of gauge theories in particle physics*.
- arXiv:2211.10497 Kane, Grabowska, Nachman, Bauer, *Efficient quantum implementation of 2+1 U(1) lattice gauge theories with Gauss law constraints*.
- arXiv:2201.09625 Hartung, Jakobs, Jansen, Ostmeyer, Urbach, *Digitising SU(2) gauge fields and the freezing transition*.
- arXiv:2402.07987 Calajo et al., *Digital quantum simulation of a (1+1)D SU(2) lattice gauge theory with ion qudits*.
- arXiv:2403.14537 Illa, Robin, Savage, *Qu8its for quantum simulations of lattice quantum chromodynamics*.
- quant-ph/0003137 Bravyi, Kitaev, *Fermionic quantum computation*; cond-mat/0508353 Verstraete, Cirac, *Mapping local Hamiltonians of fermions to local Hamiltonians of spins*; arXiv:2003.06939 Derby, Klassen, *A compact fermion to qubit mapping*.
- arXiv:2105.05870 Mazzola, Mathis, Mazzola, Tavernelli, *Gauge invariant quantum circuits for U(1) and Yang-Mills lattice gauge theories*.
- Project: manual `proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md` Steps 2.1-2.5, 4.3; `prompts/11`, `prompts/27`; `validation/S2.json`, `S2_2x4.json`, `E2.json`, `CV_2x3_plan.json`; `data/quantinuum/devices_20261002.json`.

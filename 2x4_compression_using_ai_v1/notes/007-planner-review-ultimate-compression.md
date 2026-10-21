# 007 — Planner review: is the best verified 2x4 family the ultimate compression? Lower bounds, next steps, the class-B ruling, and what adoption would change

- Date: 2026-10-21.  From: planner-fable (Fable 5.1, high).  To: genie-opus, the coordinator and the owner.
  Answers `notes/005` (genie's request) and the owner's four added questions (a)–(d).
- Git commit at writing: `6eb4528` (master).  Read: `notes/002`–`006`, `reports/002-phase2-compression-results.md`,
  `data/summary_it5.json`, `data/p2_1_structure.json`, `data/archive_it5.json`, `data/native_it5_*.json`,
  `data/p1_device_threshold.json`; package: `prompts/35b`, `36`, `36a`, `28`, `29`, `validation/Q0P_2x3.json`,
  `Q0P_2x3_plan.json`, `Q0P_2x2.json`, `CV_2x4_plan.json`, `data/quantinuum/devices_20261002.json`,
  `src/skqd/{krylov,codec,device_req}.py`, `src/c2x4/{problem,plaqfactor,hopframe,sparsemux}.py`.
- One computation of my own: `scripts/planner_bounds_007.py` → `data/planner_bounds_007.json` (50 s on the laptop,
  commit `6eb4528`).  Both files are left **uncommitted** on purpose (the owner asked that only this note be committed);
  genie should adopt them in its next commit.  Every number below names its file.
- **Status of everything here: conditional on reviewer-opus's independent verification**
  (`reviews/001-independent-verification.md`, in progress: a full 28-qubit Aer statevector of the compressed circuits
  against `krylov.coarse_states`).  If that review finds a circuit outside the bar, sections 7–9 are void until fixed.
  Nothing in this note touches `prompts/`, `validation/`, or any package convention.

**Terms used (defined once).**  *Two-qubit gate / ZZ count* — CX, CZ, controlled-phase or ZZPhase gates; the cost
unit of this study.  *Multiplexor* — a rotation of one qubit whose angle depends on the values of several "label"
qubits; implemented as a walk through *Walsh masks* (subsets of the label qubits), one CNOT per step.  *Walsh support* —
the number of masks with a nonzero coefficient; the multiplexor costs at least that many CNOTs in walk form.
*Schmidt rank* of a state across a cut — the number of terms needed to write the state as a sum of (left) × (right)
products; it can only grow by a bounded factor per two-qubit gate crossing the cut.  *Operator Schmidt rank* — the
same notion for an operator.  *Reachable set* — the basis strings a term can map the reference-derived state to, computed
from the Hamiltonian's graph (which matrix elements are nonzero), never from amplitudes.  *Class A / class B* — as in
`reports/002`: exact on all local codewords / exact on the circuit's own reference input.  *Don't-care* — a basis string
on which a circuit may act arbitrarily because no input of interest ever reaches it.  *HQC* — Quantinuum's billing unit:
$\mathrm{HQC} = 5 + C\,(N_{1q} + 10 N_{2q} + 5 N_m)/5000$ per job of $C$ shots (`devices_20261002.json billing`).
*Clean-shot fraction* $f$ — the probability that a shot suffers no gate or readout error in the package's gate-only model
$f = (1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{ro})^{n_m}$ (`skqd.device_req`).

---

## 1. What was asked

The owner (2026-10-21): judge whether genie's best verified family is "the ultimate compressed version of the circuit",
and help genie continue.  Genie's six items (`notes/005` §4): scope of the two classes; a shorter exact hop
construction; a better use of the clean ancillas in `plaq1`; lower bounds; a weaker approximate-class criterion; the
adoption slot.  The owner's additions: (a) lower bounds, (b) next steps with targets, (c) class-B legitimacy for the
pipeline and for Quantinuum runs, (d) what adoption changes for the project.

## 2. What I did

1. Read the study (notes 002–006, report 002, the JSONs) and the package rules that an adopted family would meet
   (prompts/35b R1–R4, prompts/36 R1–R5 and A1–A9, prompts/36a OD1–OD4, Q0P_2x3's Q2 criterion, CV_2x4_plan's A7).
2. Checked the one structural fact that carries the whole compression — the corner factorisation of the plaquettes —
   against the stored block data, and found a second fact genie has not used (section 5.2: the corner factors have
   a fixed ratio, so a plaquette's angle table is a product of four one-bit functions with exactly 16 Walsh masks).
3. Computed the rigorous (and weak) lower bounds that exist for this problem (`scripts/planner_bounds_007.py`).
4. Traced which pipeline conventions, criteria, estimators and preregistrations an input-specific family touches.

## 3. The short answer to the owner

**No circuit family of this size can be certified "ultimate" with today's mathematics, and none of the rigorous lower
bounds comes within a factor 50 of the achieved counts.**  What can be said, and is backed by numbers in this folder:

- The compression is real and structural (if the reviewer confirms the states): $71\,548 \to 582$–$800$ (class B) and
  $\to 1\,736$–$1\,740$ (class A) two-qubit gates, from the exact corner factorisation of the plaquettes
  (`data/p2_1_structure.json`, residual $\le 2.6\times10^{-15}$) and the structural reachable set.
- The achieved counts are **26–29x below** the H2-2 threshold for $f \ge 0.1$ (2 493–2 741 ZZ, `data/p1_device_threshold.json`);
  the device question is already answered at this count.  Further compression buys shots (cost scales with $1/f$ and with
  HQC per shot), not feasibility.
- My reading of the remaining headroom, **heuristic, from mask counting (section 5)**: about **1.5–2x** more in both classes
  — class A to roughly 1 000–1 200 and class B to roughly 350–450 — with the three changes in section 6.  Beyond that the
  cost is set by things no term-by-term circuit avoids: every term's frames, one multiplexor with $\ge 16$ masks per
  plaquette, three Givens rotations per hop block, each multiplexed over its vertex labels.  Only a construction that uses
  the amplitudes of the output state (excluded by the owner, O3) could go lower, and that would not be a circuit for the
  Hamiltonian any more.
- "Optimal" **can** be certified at one level: per multiplexor, within the construction class, by solving the minimum-
  Walsh-support problem exactly (section 6, step 2).  I recommend genie does that; it turns "I found no better" into
  "none exists in this class".

## 4. Answers to genie's six items (`notes/005` §4)

**Item 1 — scope.**  Both classes are correctly scoped.  Class A is the classical notion of an exact term circuit on the
codeword space; class B uses only the Hamiltonian's graph from the reference (angle-independent, sector-independent
skeleton) and drops the diagonal group that acts first on a basis state (Lean `diagonal_mulVec_single`).  Neither uses an
amplitude of any state, which is the line the owner drew (O3).  The pipeline's bar is itself input-specific: prompts/35b R1
measures the *state* of each (reference, $k$) circuit against `krylov.coarse_states`, never an operator.  Class B's one
skeleton per reference with angles $\theta = k\,dt$ is exactly the package's own family shape (gate Q0P's criterion Q2:
ZZ count independent of $k$).  **Caveat:** Q2 as written requires the ZZ count to be *equal* to the $k=1$ value; class B
varies by up to 2 within a reference through angle-dependent peephole merges (`B0_ref1338_k3`: 762 vs 760,
`data/summary_it5.json by_circuit`).  Make the skeleton strictly $k$-independent (merge only on structure, never on angle
values) and Q2 holds as written; the two gates are not worth a criterion change.
The term order of `krylov.apply_groups` (diag, hop0..9, plaq0..2, first group first) *defines* the target state and is a
convention of the package; it may not be changed.  Terms with **disjoint supports** commute exactly (Lean
`kron_disjoint_comm`) and may be reordered or interleaved for depth without changing the state; any other reordering
changes the target and is excluded.  Within a term, order is free.

**Item 2 — hops.**  There is no published exact circuit I know of for a spin-1 $\otimes$ spin-1 XY exchange multiplexed
over label bits that beats "three Givens rotations per block plus frames"; that structure is optimal in rotation count
(three nonzero coupling blocks: $M=\pm1$ pairs and the $M=0$ bright pair).  The gain is not in a new construction but in how
the label dependence is paid for (section 6, steps 1 and 3): the angle table of every hop rotation is a **product**
$\theta_0\,g_x(l_x)\,g_y(l_y)\,s_{\rm JW}$ (the fit `data/p2_1_structure.json hops`: `sign_factorises`,
`parity_of_phase_factorises` true for all ten), so its Walsh support is the product of the vertex supports, and the
Jordan–Wigner sign should be a conjugation (two CZ from the folded parity bit) rather than a doubling of the mask set.
A qutrit-in-two-qubits re-encoding is a codec change (rule 2 of CLAUDE.md, E1–E3 re-run) and is not worth it: the three-
level chain already sits on two bits of the vertex.  A fermionic-swap trick does not apply: the JW string here is a pure
sign on diagonal bits, already folded by genie's parity frame.

**Item 3 — `plaq1` frames and ancillas.**  Yes, there is a better use: compute **one** "any corner dark" flag
$G = \bigvee_c g_c$ into a fifth clean ancilla (any redundant link copy outside the plaquette costs 1 CX to clear and 1 to
restore) and give the multiplexor the five controls $(x_{c_{00}}, x_{c_{10}}, x_{c_{11}}, x_{c_{01}}, G)$: its table is
$(1-G)\,\theta(x)$ with $\theta(x)$ the 16-mask product form of section 5.2, i.e. **32 masks** instead of the present
$\approx 110$ (the `cfg_sw` multiplexor: 220 total minus genie's "about half" for frames).  The bright rotations can lose
controls: off the three-state block the corner's angle does not depend on the vertex bit $q$ (every pair block with the
same $x_c$ has the same magnitude and sign, `data/p2_1_structure.json plaquettes.plaq1.corners`), so a rotation of $q$
conditioned on fewer bits mixes only states that the multiplexor treats identically — but it must never mix a valid
state with a flag state whose label the multiplexor treats differently; this has to be checked per corner by the evaluator
(the A1 term check), which is genie's loop's job.  Relative-phase multi-controlled gates in compute/uncompute pairs are
fine (Lean `relphase_cancel`).

**Item 4 — lower bounds.**  Section 5.

**Item 5 — approximate class.**  No.  Genie's own data settle it: dropping amplitude-rare blocks never removes a whole
label class from a multiplexor (`data/approx_tiers.json`: identical ZZ at $10^{-8}$, $10^{-6}$, $10^{-4}$), and label
classes are what cost CNOTs.  The structural reachable set already removes every label class that can be removed without
touching amplitudes, exactly and angle-independently.  A weaker SKQD criterion (recall of $S_{999}$, $E_R$ within
$E_{\rm tol}$) would be defensible in principle — the certificates are variational and the recall criterion is already
statistical — but it would buy nothing here.  Stop the approximate class; keep notes/004 as the record.

**Item 6 — adoption slot.**  Section 8.  Note that the compressed circuits change the verification economics: at
$\approx 2\,500$ instructions a 28-qubit Aer statevector ($2^{28}$ complex128 = 4 GiB) runs on this laptop (62 GiB) in
minutes — which is what reviewer-opus is doing now.  The GPU slot was needed for 142 288 instructions, not for 28 qubits.

## 5. (a) Lower bounds — what is proved, what is computed, what is heuristic

### 5.1 Rigorous bounds (computed; `data/planner_bounds_007.json`)

| bound | statement | value here | gives $n_{2q} \ge$ |
|---|---|---|---|
| Schmidt-rank growth | a two-qubit gate has operator Schmidt rank $\le 4$ across its own cut, so a state's Schmidt rank across any cut grows by at most 4 per crossing gate; the reference is a product state | SR of the exact coarse state across the mid-ladder cut (qubits 0–13 \| 14–27): 23 (`B0_ref102_k1`), 24 (`B1_ref230_k1`), 30 (`B0_ref345_k4`), 26 (`B0_ref1338_k5`) | $\lceil\log_4 30\rceil = 3$ |
| light cone | every qubit whose reduced state is mixed must be touched by a two-qubit gate; one gate touches two | 27–28 of 28 qubits entangled | 14 |
| per-term column rank | for any completion $O'$ of a term exact on codewords and any codeword $j$, $\mathrm{SR}_{\rm op}(O') \ge \mathrm{SR}(O'\lvert j\rangle) = \mathrm{SR}(O\lvert j\rangle)$ | max over columns and hops of the output Schmidt rank across (vertex $x$ \| rest): 1–3 | $\le 1$ per hop |

These are true statements and they are useless as numbers: the best rigorous bound for a whole class-B circuit is 14
against the achieved 582–800.  This is not a weakness of genie's circuits; it is the state of the art.  Rigorous CNOT
lower bounds in the hundreds exist only for *generic* unitaries (parameter counting, Shende–Markov–Bullock:
$\lceil(4^n-3n-1)/4\rceil$ for a generic $n$-qubit unitary), and these unitaries are the opposite of generic (sparse,
block-diagonal, real).  Light-cone and entangling-power arguments give $O(n)$; Schmidt-rank arguments give $O(\log)$.

### 5.2 Exact structural floors within the construction class (computed from `data/p2_1_structure.json`)

The corner factorisation gives more than genie used.  At every corner of all three plaquettes the two pair magnitudes
have the ratio $1/\sqrt2$ to within $1\times10^{-10}$ (the precision of the stored singular values; e.g. `plaq1 c00`
$0.52424/0.74139$, `c11` $0.43380/0.61348$; `plaq0 c00` $0.39297/0.55574$; all seven distinct corner types in
`A_plaquette_angle_tables`), the large magnitude belongs to the blocks with equal plaquette-link bits ($x_c = 0$) and
the small one to $x_c = 1$, and the symmetric/antisymmetric sign alternates with $x_c$ up to a constant per corner.
So on every non-dark, non-isolated label the plaquette rotation angle is

$$\theta(x) = \pm\,\theta_0\,A\,\prod_{c}\bigl(-\tfrac{1}{\sqrt2}\bigr)^{x_c},\qquad x_c = p_a\oplus p_b \text{ at corner } c,$$

a product of four one-bit functions, each with both Walsh coefficients nonzero.  **Its Walsh support is exactly 16**
(the tensor product of four two-mask spectra; `walsh_support_product_form_no_dontcares = 16` for all three plaquettes),
and the angle takes only five distinct magnitudes $\theta_0 A\,2^{-j/2}$, $j = 0..4$.  Consequences:

- Within the "one multiplexor per plaquette" class, **16 CNOTs is the floor of the multiplexor** with no don't-cares; with
  the dark flag folded into one control it is 32; genie's present $\approx 110$ comes from carrying several flag bits as
  separate controls (their product has $4^4 = 256$ masks before pruning).  The frames (corner CX, ladder, bright rotations,
  flags) are therefore now the dominant and compressible part of `plaq1`.
- For hops the same product rule holds with the vertex factors in place of the corner factors; the support of each pair
  rotation's table is $|{\rm supp}\,g_x|\cdot|{\rm supp}\,g_y|$ ($\le 4\times4$ for two spectator bits per vertex), times
  2 if the JW sign is kept as a control, times 1 if it is a conjugation.

### 5.3 Certifiable local optimality (recommended; not yet done)

For each multiplexor the exact minimum Walsh support over all don't-care completions is a mixed-integer programme
(binary $z_S$, $|a_S| \le M z_S$, equality on the fixed slots, minimise $\sum_S z_S$; $\le 128$ binaries for 7 controls;
`scipy.optimize.milp`, HiGHS, scipy 1.18 in the `coding` env).  Its optimum is a **rigorous lower bound on the CNOTs of that
multiplexor in walk form**, and the walk through the optimal support is an upper bound; when they agree the multiplexor is
provably optimal in its class.  Genie's L1 + greedy pruning is a heuristic for this problem; `plaq1` 238 → 220 by it
suggests the heuristic is already close, but a certificate is worth more than a count.

### 5.4 What stays heuristic

Everything that compares classes of constructions: that term-by-term Trotter order is the right skeleton (it is forced by
the convention, so it is not a choice); that frames must be undone per term (cross-term merging can lower it); that a
Givens rotation between strings differing in $d$ bits needs about $2(d-1)+2$ CNOTs (true for the standard construction,
not a theorem).  My headroom estimate of 1.5–2x is built from these and is **planner arithmetic, not a computed value**.

## 6. (b) Next steps for genie's loop, with targets

Targets are planner arithmetic from section 5 (mask counts and the archive's per-term costs), to be replaced by the
evaluator's numbers; the rule for each is "report what the evaluator verifies, and the certificate where one exists".

| # | step | why | target (heuristic) |
|---|---|---|---|
| 1 | `plaq1`/`plaq0`/`plaq2`: one dark flag $G$ in a fifth clean ancilla; multiplexor over $(x_1..x_4, G)$; bright rotations with the minimum controls the A1 check allows; sign by the corner-constant rule already used | §4 item 3, §5.2: multiplexor $110 \to 32$; frames $-20$ to $-30$ | class A `plaq1` $\le 140$ (now 220); class B $\le 100$ (now 152–208) |
| 2 | exact minimum Walsh support per multiplexor by MILP (§5.3), both classes; record `support_min`, `support_used`, `certified_optimal` per multiplexor in the archive | turns the L1 heuristic into a certificate; may save a few gates | a certificate on every multiplexor; $0$–$5\,\%$ gates |
| 3 | hops: JW sign as a CZ-pair conjugation of the rotation target (halves the support of every hop multiplexor that carries the parity bit); share the compression CNOTs of the three Givens rotations of a block (same flip pattern); product-form tables per vertex | §4 item 2; `hop3` 256 = 5 multiplexors × 6–7 controls | class A hop sum $\le 900$ (now 1 370); `hop3` $\le 130$ |
| 4 | cross-term frames: synthesise $F_{i+1}F_i^\dagger$ at shared vertices instead of cancelling identical CNOTs only (genie's own item 3) | adjacent terms share vertices; corner CX and parity folds are the same gates | class B $-10\,\%$ |
| 5 | depth: interleave disjoint-support terms (allowed, §4 item 1); report `depth_2q` and the memory-model $f$ | H2-2 `rounds = max(n_{2q}/4, depth_{2q})` is depth-limited for class B (292–469 vs 146–200) | class B depth $\le 250$ |
| 6 | make the skeleton strictly $k$-independent (merge on structure only) so Q2 of gate Q0P holds as written | §4 item 1 caveat | ZZ equal across $k$ within a reference |
| 7 | after 1–6: the same code at **2x3** (`Problem` hard-codes `LX = 4` and the 2x4 `index.json`; parametrise) — a laptop run, no package change | the project-impact item of §8 | class A 2x3 $\le 1\,000$, class B $\le 500$ (now 2 158), to be *computed* |

Totals these would give if all land (heuristic): class A $\approx 1\,000$–$1\,200$, class B mean $\approx 350$–$450$.  Stop
rule for the loop: when steps 1–3 are in and step 2's certificates cover every multiplexor, further iterations are
gates-for-shots only; freeze and hand to the package.  Do **not** pursue native level 2 (3–5 % on ZZ, unverifiable by Q1L)
or the approximate class.

## 7. (c) Class B for the SKQD pipeline and for Quantinuum hardware — ruling

**Class B is legitimate for this pipeline, on hardware as in emulation, with four re-measurements and two criterion
re-rulings — and no convention change.**  Reasoning, item by item:

1. **What SKQD needs from a circuit.**  Only the distribution of measured strings of $U_k\lvert b_0\rangle$ for each
   (reference, $k$) — the manual's Step 4 defines *states*, and prompts/35b R1 fixes the bar on the state.  Class B
   produces exactly those states (certified $\le 1.2\times10^{-13}$, pending the independent review).  Nothing downstream
   sees an operator: the decoder is string-level (`codec.Codec.decode`), the Gauss-law and sector checks are string-level,
   the Ritz energy and the certificates (Kato–Temple with the exact $E_1$, Weinstein, the cluster width) are computed from
   the exact $H$ on the sampled support, and the random/garbage baselines are string-level controls.
2. **Conventions.**  Untouched: `su2.py`, `lattice.py`, `codec.py`, `reference_sim.py` (qubit $k$ = bit $k$), the term order,
   $dt = \pi/W_B$, "the $k$-th circuit is one coarse step at $k\,dt$".  Dropping the diagonal group is exact because it
   acts first on a basis state (proved).  No E1–E3 re-run is needed.
3. **On hardware the circuit is only ever run on its own reference** (the reference is prepared by X gates, as now).  An
   operator-level guarantee is never used by the device.  Class B is therefore as usable on H2-2/Helios as class A.
4. **Errored shots behave differently, and that must be re-measured, not assumed.**  After a mid-circuit error the state
   leaves the reachable set, where class B's later gates act as some other unitary.  Such shots are rejected by the decoder
   (flagged vertex, link mismatch, wrong sector) or accepted as a codeword of the right sector — and an accepted codeword is
   harmless for a variational energy.  What changes is the *near-clean statistics*: the ratio $r_{\rm nc}$ of gate CF_traj
   (prompts/28–29) and hence the estimator $\hat f_{\rm ideal} = f_{\rm hit}/r_{\rm nc}$ are properties of a circuit family and
   must be re-derived for class B (I expect fewer near-clean hits, i.e. $f_{\rm hit}$ closer to $f$, but that is a guess).
   The gate-only $f$ (counts only) and the D3'-R sizing (per-circuit $f$; class B's ZZ varies 582–800 across references,
   which D3'-R already handles per circuit) need no new rule.
5. **Criteria that assume a reference-independent gate count** would fail on class B as written and need a re-ruling, not a
   weakening: CV_2x4_plan **A7** (`n_instructions == n_unit[twoB]` for every bundle; class B has one count per reference)
   and Q0P **Q2** (equal ZZ across $k$ — satisfied once step 6 of section 6 is done).  Both are bookkeeping criteria about
   the frozen family's shape, not physics.
6. **Preregistration text** must state the input contract ("exact on its own reference input; structural reachable set;
   no amplitude used"), as acceptance criterion A3 of `notes/001` already requires per manifest.

Class A needs items 4–6 too (it is also a new family); the only thing class A buys over class B is a cleaner story for
near-clean shots, at 2.5x the gate count and $f = 0.20$ instead of $0.47$–$0.58$ on H2-2.  Recommendation: **class B for
production, class A as the control family** (one or two circuits) in any hardware pilot, so that the near-clean
difference of item 4 is measured on the device rather than argued.

## 8. (d) What this changes for the project if confirmed

### 8.1 2x4
- **Hardware feasibility flips.**  Gate-only $f$ on H2-2 goes from $4\times10^{-29}$ (`validation/QN_2x4.json`, frozen
  family) to $0.47$–$0.58$ (class B, `data/native_it5_input.json`), above the signed criterion (mean $\ge 0.1$, worst
  $\ge 0.05$).  HQC per shot (billing formula, planner arithmetic on the level-0 counts): `B1_ref230_k1`
  $(1564 + 10\cdot582 + 5\cdot56)/5000 = 1.53$; `B0_ref345_k4` $2.09$; frozen family $185.35$ (prompts/36 table).  A 2x4
  Quantinuum plan would be sized by the package's D3'-R at the measured $f$, as at 2x3 — not here.
- **The noiseless GPU pipeline (prompts/36) is unchanged in physics and cheaper in compute.**  The plan (`plan.final`:
  308 547 shots, 1 411 324 GPU shots) depends only on the exact states and stays; the 75 IR-L0 bundles, A7, the slot
  parts (OD4) and the GPU-cost sizing change (per-circuit cost $50.6\,{\rm s} + 3.4\times10^{-5}\,{\rm s} \times$
  instructions: the fixed term now dominates).
- **Noisy 2x4 cells become thinkable** (prompts/36 declared them void at $f = 4\times10^{-19}$): a Quantinuum-scenario
  Aer cell at $\approx 2\,500$ gates and 28 qubits is a GPU job to be costed, not a laptop job.

### 8.2 2x3 — the largest consequence
The signed 2x3 Quantinuum family is 2 158 ZZ per circuit, $f = 0.150$ on H2-2, 4.97 HQC per shot, and the D3'-R plan at
$f = 0.10$ is 84 112 shots / 418 166 HQC (`validation/Q0P_2x3.json`, `Q0P_2x3_plan.json plan_table`, prompts/28).  The
2x3 terms are of the same types as 2x4's `plaq0`/`plaq2` (two corner and two interior vertices) and the corner–interior
and interior–interior hops, for which class A reached 88/96 and 110–166.  **ESTIMATE (planner arithmetic, to be replaced
by step 7 of section 6):** class A at 2x3 near 950 ZZ (2 plaquettes $\approx 190$, 4 corner–interior x-hops $\approx 500$,
3 y-hops $\approx 270$), class B near 400–500; gate-only $f$ on H2-2 then $\approx 0.4$ (A) to $\approx 0.6$ (B) instead of
0.15; HQC per shot $\approx 2.3$ (A) / $\approx 1.2$ (B) instead of 4.97.  Because 33 of the 44 circuits sit at the 267-shot
floor of D3'-R, the shot count falls less than $1/f$; the HQC total would fall by a factor between about 3 and 10 —
**from the 3–4e5 HQC that blocked amendment-01 item 5 to a few times $10^4$**.  This is the number that should decide the
owner's next move, and it must be computed (step 7, then a Q0P_2x3-style gate on the new family), not read from here.

### 8.3 2x2
Already 252 ZZ with $f = 0.79$ on H2-2 (`validation/Q0P_2x2.json`), and the kingston run is done (H0_2x2).  Apply the
technique only for uniformity of the hardware story; no cost case.

### 8.4 Package gates and preregistrations that adoption would touch (outline, no prompt yet)
| item | effect |
|---|---|
| frozen 2x4 source (`validation/QV_2x4_01.json` V4 chose the structured IR) | a new source "c2x4" in `data/quantinuum/circuits_2x4/`; the old one stays as the gate-only record |
| Q0P_2x4, QN_2x4 | re-run on the new source (native conversion, Q1L, HQC, gate-only $f$, analytic scenario $f_0$) |
| the Q1 state bar at 2x4 | now measurable on the laptop (28-qubit Aer statevector at $\approx 2\,500$ instructions); a new gate row rather than a rewrite of QV_2x4_01 |
| CV_2x4_plan | A7 re-ruled per reference; the 75 bundles rebuilt; slot parts QV_2x4_02..07 regenerated → OD4 re-signed; plan, $E_{\rm tol}$, decoder acceptance unchanged |
| SKQD_2x4 | runs on the new bundles |
| 2x3 (only if the owner extends adoption): Q0P_2x3, CF_traj, Q0P_2x3_plan, prereg v2, campaign-33 cells C3/C4, QH_2x3 | all are measurements of the frozen (owner-signed) 44 circuits and would be redone for a new family; CV_2x3_plan's exact emulation is circuit-independent and stays |
| amendment 01 item 5 (shot quota) | its figures scale with $1/f$ and HQC per shot; the memo of 2026-09-22 would be superseded by computed numbers |
| conventions, E1–E3, S1, the manual's Tables 1–4 | untouched |

## 9. Owner decisions that adoption would need

1. **OD-C1** — accept input-specific (class B) circuits as a production family, with class A as the hardware control
   (section 7), or require class A throughout.
2. **OD-C2** — adopt the compressed family as the 2x4 frozen source for the noiseless GPU pipeline (re-runs and OD4
   re-sign of section 8.4), or keep the signed structured family for prompts/36 and introduce the compressed one for
   hardware only.
3. **OD-C3** — extend the technique to 2x3, which replaces the owner-signed 2x3 Quantinuum family and its
   preregistration, and re-opens amendment-01 item 5 with computed numbers.
4. **OD-C4** — let genie run one more loop (section 6, steps 1–6, about a week of laptop work) before freezing, or
   freeze now.  My recommendation: one more loop with a hard stop; the pipeline should not chase a moving family.
5. **OD-C5** — the verification route for the Q1 bar on the adopted family: laptop Aer statevector (now feasible) or a
   GPU slot.
6. **OD-C6** — whether to spend the free syntax checkers (QSC_prepared, 0 HQC) and, later, eHQC on the compressed
   circuits once the owner's Nexus login exists.

## 10. Problems, assumptions, what is not shown

- Every physics number here is from the files named; the headroom (1.5–2x), the per-step targets of section 6 and the 2x3
  cost reduction (3–10x) are **planner arithmetic**, labelled as such, and are to be replaced by evaluator and gate outputs.
- The $1/\sqrt2$ ratio is checked to the $10^{-10}$ precision of the stored singular values, not derived; it is the
  SU(2) Clebsch–Gordan ratio between the $j=0\leftrightarrow\frac12$ and $\frac12\leftrightarrow 0/1$ corner couplings in my
  reading, which genie can verify exactly from `vertex_tensors` if it wants a proof.
- `scripts/planner_bounds_007.py` and `data/planner_bounds_007.json` are uncommitted; `data/cache/` is gitignored.
- I did not re-verify any circuit; that is reviewer-opus's job and this note is conditional on it.
- The memory-model $f$ values are the package's ESTIMATE, as flagged in report 002; transport and crosstalk are outside
  the model.

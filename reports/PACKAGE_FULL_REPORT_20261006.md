# su2qc-skqd: full package report (2026-10-06)

## 0. How to read this file

**What this file is.** One self-contained description of the whole `su2qc-skqd` package (a research code base owned by Digonto, repository `https://github.com/digonto10602/su2qc-skqd`, local path `/home/digimonk/Projects/su2qc-skqd-v0.1.0`), written on 2026-10-06 from the repository's own files, so that it can be uploaded on its own to another assistant that has no access to the repository. It carries the numbers, the history, the open decisions and machine-readable data blocks (Section 11) that can be plotted directly. **It refreshes `reports/PACKAGE_FULL_REPORT_20261005.md`** (written at commit `408e49c`, 2026-10-05 16:18 MDT, which stays unchanged in the repository); Section 0.1 lists what changed.

**Repository facts (from `git log`).** `git log --oneline | wc -l` gave 200 commits on branch `master`; the first commit is dated 2026-09-14 (`5e3fe61`) and the newest one at the time of writing is `9444b8c`, dated 2026-10-06 02:41 -0600. The 200 commits span the 23 calendar days 2026-09-14 to 2026-10-06 inclusive (sum of sourced dates); 24 of them are newer than the previous report's commit `408e49c` (`git log --oneline 408e49c..HEAD | wc -l`). `git status -sb` showed `master...origin/master` with no ahead or behind count, so every one of those commits had been pushed; the only untracked item is the empty-counts directory `data/hardware/H0_ddrep_dryrun_prototype/` (`prompts/LOG.md` says the owner may delete it). The commit that adds this report is local and not pushed.

**Rules this file follows (the owner's reporting rules).**

1. *Plain English.* Every technical word is defined the first time it appears, and Section 12 is a glossary of all of them.
2. *Project labels.* Names such as "B_all", "B_sig", "rule D3'", "rule D3'-R", "gate H0_2x2", "C22", "f_hit", "f_ideal", "r_nc", "stage E / stage P", "K0", "K1", "H0_ddrep", "CV1-CV5", "E_tol" are **the project's own labels** (invented inside this project, mostly by its planner agent), not standard physics or computer-science terms. Each is explained where first used.
3. *Math* is written in LaTeX: $\ldots$ inline, $$\ldots$$ displayed.
4. *Numbers.* Every number carries its units where it has any, its uncertainty or interval where one exists, and the source file (and JSON key where useful) in which it was found. The notation `validation/H0_2x2.json -> data.clean_fraction.pooled.f` means "open that file, go to `data`, then `clean_fraction`, then `pooled`, then key `f`". "95 %" intervals are the intervals the source file states; I did not recompute any.
5. *Never invented.* If a number is not in a repository file I say so. Where the only source is the project planner's own arithmetic I label it **(planner arithmetic)**; where an input is a guess I label it **ESTIMATE**. Where I did a trivial sum, ratio or probability myself from sourced numbers I label it **(my arithmetic)** or **(sum of sourced numbers)**.
6. *"PASS" does not mean "the result is good".* The project has two kinds of gates (Section 4.3): *validation gates* (PASS = the code reproduces a known answer) and *measurement gates* (PASS = "preregistered, measured, verified, consistent", never "the number is good"). Each row in Section 5 says which. In particular a measurement gate that records a negative result is a PASS (gates `H0_ddrep` and `K1_2x3_fpilot` both are).

**Units used.** Energies are in the lattice units of the Hamiltonian ($a_0 = 1$, dimensionless numbers; the project quotes them as bare numbers such as $-3.6408$). Times on the quantum device are in microseconds ($\mu$s) or nanoseconds (ns); QPU time is in seconds (s) as billed by the IBM service; Quantinuum cost is in HQC (hardware quantum credits, defined in the glossary); angles are in radians (rad).

**Date and status caveat.** "Today" is 2026-10-06. At the time of writing no other agent was known to be editing the repository and every file cited is committed (the one exception is the untracked empty directory above). Two files that were work-in-progress in the previous report are now final: `validation/K0_2x3_2x4.json` (**rewritten on 2026-10-06 by the live run**; it now reads PASS 6/6, the old FAIL 5/6 row is superseded) and `validation/CV_2x2_info.json` / `validation/CF_estimator_2x2_info.json` (re-run on 2026-10-05 evening). `validation/BLOCKED.md` is a local, gitignored note that still describes the first, failed `CV_2x3_plan` run of 2026-10-05; it is stale and I do not use it as evidence.

**File map for the reader.** Section 1 summary; 2 physics and method from scratch; 3 the intended plan; 4 package layout; 5 gate table; 6 history; 7 QPU ledger; 8 lessons; 9 present state and open decisions; 10 progress measure; 11 data blocks; 12 glossary. Section 9.7 lists the numbers I could not source or reconcile.

### 0.1 What changed since the 2026-10-05 report

- **The 2x3 plan check ran and passed.** Gate `CV_2x3_plan` PASS 37/37 and gate `Q0P_2x3_plan` PASS 7/7. After the seven planner rulings of `prompts/31` and two owner decisions of 2026-10-05 (Kato-Temple at $B=0$; sector $B=1$ doubled), the shot plan of record is rule D3'-R with sector $B=1$ doubled, costing 1,279,660 / 665,605 / 471,801 HQC at $f=0.05/0.10/0.15$ (Section 6.19, block (g)).
- **2x3 on IBM was recorded as NO-GO on a model (gate `K0_2x3_2x4`, now PASS 6/6) and then measured as NO-GO.** The K1 pilot (job `db2avbe8v0ts73c2i8b0`, 188.0 s) saw **0 reference hits in $2\times10^5$ shots** against 0.191 expected from garbage; the 95 % upper bound on $\hat f_{\rm ideal}$ is $2.06\times10^{-5}$ (Section 6.22).
- **The 2x2 XY4 gain did not replicate.** Gate `H0_ddrep` (job `db29p6nr11fs7396e4ig`, 37.0 s): $R_{T3}=0.895$ [0.804, 0.996] against 2.819 on 2026-10-02; the no-DD baseline doubled (0.0818 against 0.0400) on the same frozen circuits; the context-aware collapse did not replicate either; a coherent $x$-pulse over-rotation of 0.015-0.020 rad was measured on all 12 qubits (Section 6.21).
- **QPU account:** 327 s used, **273 s left** of 600 s; 14 jobs (Section 7).
- **Owner decisions of 2026-10-05/06 are now recorded and removed from the open list** (Section 3.4, 9.6).
- **Stale wording fixed:** K1, `prompts/29` Part B' and `prompts/30` are no longer "in progress" anywhere.

## 1. Executive summary

**What the project is.** `su2qc-skqd` is a research code base and a preregistered experimental programme (owner: Digonto, digonto10602) that tests whether a quantum computer can help find the lowest energy levels of an SU(2) lattice gauge theory (a two-colour toy version of the strong force) with dynamical staggered quarks on small two-row lattices ("ladders" of 2x2, 2x3 and 2x4 sites). The method is **neural-enhanced sample-based Krylov quantum diagonalization (SKQD)**: a quantum computer prepares states that spread a starting configuration over the configurations that matter, the measured bit strings are decoded and used to pick a small subspace, and an ordinary computer finds the exact lowest energy inside that subspace together with a rigorous error bar (the Weinstein and Kato-Temple certificates). The quantum device only chooses the subspace; the energy is never below the true value. The "neural-enhanced" part (a classical learned ranking of configurations) is so far only a minimal ridge-regression baseline tested on simulated data. The plan's own expectation is a characterized null result (a classical selected-CI method is at least as good as the device at these sizes), publishable as the first measured device-support-quality curve for a non-Abelian theory.

**Where it stands today (2026-10-06).**
- *Classical machinery:* complete and validated. The exact reference energies, the gauge-invariant basis, the hardware encoding and decoder, the exact structured circuits for 2x2, 2x3 and 2x4, the certification, and now the emulated 2x3 plan check (convergence, coverage, certificate widths) all pass their gates (E1, E2, E3, S1, CS, L2, L5, S2_2x4, Q0P_2x3, CV_2x3_plan, Q0P_2x3_plan, K0_2x3_2x4). Of 46 gate result files, 34 PASS and 12 FAIL; the FAILs are either deliberately re-defined cost gates, honest negative hardware results, or by-construction records (Section 5).
- *2x2 on a real quantum computer:* the entire pipeline has been run end to end on IBM's `ibm_kingston` (the full SKQD run, 53.0 s). It is a measurement-gate PASS but, as the project's own planner states, **not an SKQD physics result**, because at this size noise alone fills every sector. The one mitigation result that had brought the clean fraction above the 0.1 bar (client-side XY4 dynamical decoupling, $\times2.8$ on 2026-10-02) **did not replicate on 2026-10-06**, and the same circuits without any decoupling were twice as clean as four days before: the day-to-day change of the device is larger than the effect being tested.
- *2x3 on a real quantum computer:* **one measurement exists and it is a firm NO-GO.** IBM's `ibm_kingston` produced no reference hit in $2\times10^5$ shots of the two signed 2x3 circuits (5 659 routed CZ, 411 $\mu$s each); the 95 % upper bound on the clean fraction is $2.06\times10^{-5}$, about 4 850 times below the signed bar 0.1 (my arithmetic). Only Quantinuum's H2-2 and Helios-1 meet the signed gate-error bar on published numbers; access has not yet been requested (an email draft exists).
- *2x4:* compiled and verified on a simulator; far out of reach of any device that exists.
- *Neural step, primary endpoint P1, gates H1/H2/M1:* open.

**The five most important numbers** (each with its source):

| # | number | meaning | source |
|---|---|---|---|
| 1 | **No-DD clean fraction 0.0400 [0.0358, 0.0446] (2026-10-02) vs 0.0818 [0.0758, 0.0881] (2026-10-06)** on the same frozen `ibm_kingston` circuits; client XY4 (cell T3) 0.1129 [0.1058, 0.1203] vs 0.0732 [0.0675, 0.0792]; ratio $R_{T3}$ **2.819 [2.495, 3.185] vs 0.895 [0.804, 0.996]** | the fraction of shots with no error is not a stable property of a device-plus-circuit: it changed by a factor 2.04 (my division) between two days, more than any same-day decoupling effect seen on 2026-10-06 (ratios 0.647 to 1.150); the earlier chain 0.2195 predicted $\Rightarrow$ $6.65\times10^{-4}$ measured on `ibm_fez` (2026-09-22) $\Rightarrow$ 0.0413 on `ibm_kingston` (2026-10-02, no DD) is in Block (b) | `validation/H0_ddtest.json`, `validation/H0_ddrep.json -> data.cells`, `data.replication`; `validation/H0_canary.json`, `H0_model.json`, `H0_kpilot.json` |
| 2 | **$E_R-E_0=5.48\times10^{-4}$ ($B{=}0$) and $5.75\times10^{-6}$ ($B{=}1$)**, with certified intervals containing the exact $E_0$; **but** uniformly random bit strings reproduce the all-state energy in **100 of 100 seeds** ($Na/\dim=16.97$ and 15.72) | what the 2x2 run shows and what it cannot show: the signal support is at the 5.0th and 28.5th percentile of random equal-size bases, so only a modest signal in one sector | `validation/H0_2x2.json -> data.energies, data.baselines, data.C22` |
| 3 | **327 s** of 600 s QPU time used, **273 s** left, 14 jobs (53.0 s bought the full 2x2 run, 37.0 s the DD replication, 188.0 s the 2x3 pilot) | the entire hardware budget so far | `data/hardware/*/session.json`, `data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json` |
| 4 | **0 reference hits in 200 000 shots** (0.191 expected from garbage); $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %) on IBM at 2x3, against **0.1502 (H2-2) and 0.1642 (Helios-1)** gate-only on Quantinuum; the re-sized 2x3 plan costs **665 605 HQC at $f=0.10$** (1 279 660 at 0.05, 471 801 at 0.15) | 2x3 on IBM is a measured NO-GO; trapped-ion machines of one vendor reach the signed bar on paper, their transport (memory) error is unmeasured | `validation/K1_2x3_fpilot.json -> data.pooled`; `data/quantinuum/devices_20261002.json`; `validation/CV_2x3_plan.json -> data.campaign_hqc` |
| 5 | **$r_{nc}=1.115$** (reference-hit fraction over ideal-sample fraction, upper 95 % end; CF_traj PASS 7/7) and plan fulfilment **31 F / 12 FD / 8 ND of 51 rows** | the statistical correction that makes the clean-fraction bar a conservative statement, and the progress measure against the manual's plan | `validation/CF_traj.json`, `data/cf_trajectories/r_nc.json`, `reports/H0_2x2_full_hardware_report_20261002.md` |

**Five lessons that changed the project.** (i) *Accepted shots are not clean shots*: the decoder accepts near-clean strings at a rate comparable to pure noise, so the manual's yield inversion overstated the clean fraction 15-fold. (ii) *Idle-time dephasing, not gate count, dominates* on current superconducting devices for this circuit family; only a scheduled simulation at the measured free-induction $T_2^*$ post-dicts the data. (iii) *At 2x2 the SKQD energy from the accepted states is not a device measurement*; the project built controls (garbage-only, random-equal-size) and a signal support to read it honestly. (iv) *Day-to-day calibration variation is larger than the dynamical-decoupling effects*: the XY4 gain and the context-aware collapse of 2026-10-02 were calibration-specific, and the one-job, one-day A/B test that adopted XY4 was not a replicated result (Section 8.2). (v) *The calibration record cannot see the $x$ pulse*: it aliases `x_error` to `sx_error`, yet pulse trains measured a coherent over-rotation of 0.015-0.020 rad on every one of the 12 patch qubits; and *2x3 on IBM Heron is now a measured NO-GO, not only a model verdict*.

**What is next (Section 9).** (1) Quantinuum access (emulator first, then a pilot of about 9 950 HQC and, if the preregistered rule passes, a campaign of at least 665 605 HQC at $f=0.10$) is the only route to 2x3 data; the access email is still an unsent draft; (2) what, if anything, to do with the 273 s left on the IBM open plan; (3) the open owner decisions listed in Section 9.6 (the Stage E / Stage P budgets, IonQ 2x2, Perlmutter tokens, the 400 IBM minutes, the publishability route).

**Honest status of publishability.** The 2x2 result still supports a methods note on running sample-based diagonalization at a noise-saturated size. **The short technical note on client-side XY4 is no longer supported as written**: the gain did not replicate, so at most it can be reported as a calibration-dependent, non-replicated observation. The 2x2 signed-bar statement carries two caveats: it was a GO on $f_{\rm hit}$ (AMBIGUOUS on $\hat f_{\rm ideal}$), and it was measured on one day only (the same circuits without decoupling were twice as clean four days later). A physics claim needs 2x3 hardware data, which IBM cannot provide (Section 9.5).

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

**Which certificate reads which width at 2x3 (owner decision 2026-10-05, `data/owner_decision_20261005_kt_certificate.md`, verbatim "keep Kato-Temple for B=0, go ahead").** The manual's gate H1 asks for a certified interval of width $\le0.1$ at $B=0$, gate H2 for $\pm r_H\le0.15$ at $B=1$. At 2x3 the project reads H1 on the **Kato-Temple** interval with $\alpha=E_1$ taken as the *exactly known* first excited level (available classically at 2x3, not on lattices beyond exact diagonalisation; this is the owner's recorded caveat), width $\delta_{\rm KT}=r_H^2/(E_1-E_R)\le0.1$ (rigorous whenever $E_R<E_1$), and H2 on **Weinstein**, because the $B=1$ cluster gap ($E_1-E_0=0.0244$, `data.oracle_width.B=1.E1` minus $E_0$ in `validation/CV_2x3_plan.json`; my subtraction) makes Kato-Temple uninformative there. The reason is quantitative: even the oracle support that holds 99.9 % of the ground-state weight has Weinstein width $r_H=0.265$ at $B=0$ (Appendix block (r)), and a Weinstein width $\le0.1$ would need a captured weight $W\ge0.9999$ (planner arithmetic, `prompts/31` D1).
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
| P1 | **primary endpoint**: curves $E_R-E_0$ and $R_{10^{-3}}$ versus $\lvert B\rvert $ for device and CIPSI at equal $\lvert B\rvert $, bootstrap bands; "advantage" declared only if the device curve lies below CIPSI everywhere with non-overlapping bands | -- | week 5 |
| M1 | ML uses credited only under Step 7.5 (must beat the baseline at equal $\lvert B\rvert $ on 2x3 hardware data and on held-out couplings) | -- | week 5 |

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
| 2026-10-05 | `data/owner_decision_20261005_partB.md`, `data/owner_decision_20261005_k1_2x3_fpilot.md` | decisions 1a (the signed bar refers to $f_{\rm ideal}$, read as $\hat f_{\rm ideal}=f_{\rm hit}/1.115$), 2a (rule D3'-R signed as the minimum 2x3 sizing, **condition:** any campaign also needs energy convergence and weighted coverage on the emulated plan; signing commits no HQC), 3a (the 2x2 "signed bar GO" is cited with the AMBIGUOUS qualification) on `prompts/29` Part B'; and ONE K1 pilot on `ibm_kingston` (cap 300 s) |
| 2026-10-05 | `data/owner_decision_20261005_kt_certificate.md` (`prompts/31` ruling 2) | verbatim "keep Kato-Temple for B=0, go ahead": the $B=0$ width criterion of H1 / CV2 is read on the Kato-Temple interval with the exact $E_1$; $B=1$ stays on Weinstein |
| 2026-10-05 | `data/owner_decision_20261005_b1_x2_plan.md` | verbatim "approve the 2x shot plan for sector B=1": the plan of record is D3'-R with $B=0$ at $s=1$ and $B=1$ at $s=2$ ($s=1.5$ fails CV2), 1 279 660 / 665 605 / 471 801 HQC at $f=0.05/0.10/0.15$; approves the plan only, commits no HQC, and the plan is re-sized at the measured $\hat f_{\rm ideal}$ before any campaign submission |
| 2026-10-06 | `data/owner_decision_20261006_A_then_B.md` (`prompts/32`) | verbatim "do A first, then ... do B": A = record 2x3 on IBM Heron as NO-GO on the K0 analysis (a model verdict) and spend the IBM seconds first on the 2x2 XY4 replication plus the context-aware-DD test (gate `H0_ddrep`, about 32 s planned); B = the K1 2x3 pilot as built, as a measured upper limit, when `ibm_kingston` publishes CZ calibration again, with a STOP to the owner if the seconds left do not cover K1's estimate $\times1.3$ |

### 3.5 What the manual asked for that has not been done

The manual's steps that need 2x3 hardware (Step 9.2, H1, H2, P1, M1, the seven-protocol table) and the neural step on hardware data are all **open** as of today (the only 2x3 hardware data are the K1 pilot's null counts, Section 6.22); the status of each of the 51 plan rows is in Section 10.

## 4. The package layout

Source: `CLAUDE.md`, `README.md`, `RUNBOOK.md`, `SKQD-CI-SETUP.md`, `prompts/ROUTING.md`, `.claude/agents/*.md`, directory listings made on 2026-10-06, and `graphify god-nodes`. The package is a Python code base (`src/skqd/`, 27 modules, 6 132 lines by `wc -l`), 74 files in `scripts/` (64 on 2026-10-05), 32 test files in `tests/` (28 on 2026-10-05); the `src/skqd/` line count is unchanged because its two edits of 2026-10-05 (below) were already in the working tree when the previous count was made; code facts below are from module docstrings.

### 4.1 `src/skqd/`: the modules

**Physics core** (exact numerics, numpy/scipy only; no quantum software needed):

| module | what it does |
|---|---|
| `su2.py` | spin matrices, Clebsch-Gordan coefficients, the truncated electric-basis link operators ($j_{\max}=\tfrac12$); fixes the generator convention $L_a=-J_a^T$, $R_a=+J_a$ |
| `fermions.py` | the two-colour staggered-fermion site (Fock space, Jordan-Wigner pieces) |
| `lattice.py` | the open $2\times L_x$ ladder: site index $x_1L_y+x_2$, links, plaquettes, staggered phases $\eta$ |
| `vertex.py` | local singlet (intertwiner) tensors of one dressed vertex (manual Algorithm 1) |
| `basis.py` | the gauge-invariant configuration basis $\lvert \{j\},\{n\},\{\iota\}\rangle$ with baryon-number sectors (Step 2) |
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

Additions of 2026-10-05, now committed: `noise.measure_and_decode_sequence` (nested shot prefixes for the convergence check; histogram-identical to `measure_and_decode`), `skqd.corrected_clean_fraction` (the $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ statistic), `skqd.h1_energy_tolerance` (the CV constant $E_{\rm tol}$), and the `h0_support_plan.py` rule D3'-R (`d3r_plan`).

`graphify god-nodes` (the code knowledge graph, `graphify-out/graph.json`, 4 266 nodes and 8 490 edges at the time of writing because it now also indexes the reports and prompts; navigation aid, never evidence) lists as the most connected nodes: `Model` (96 edges), `Codec` (77), `load_manifests()` (58), `resolve_backend()` (57), `md_table()` (54), `CircuitFactory` (49), `references()` (49), `load_circuit()` (46), `stage_assemble()` (45), `write_report()` (43). (On 2026-10-05 the list read `Model` 86, `Codec` 69, `load_manifests()` 52, ... on a 895-node graph.)

### 4.2 `scripts/`

- **Gate scripts**, one per gate: `gate_E1.py`, `gate_E2.py`, `gate_E3.py`, `gate_S1.py`, `gate_S2.py`, `gate_S2D.py`, `gate_S2D_idle.py`, `gate_S2D_levers.py`, `gate_S2_2x4.py`, `gate_S3.py`, `gate_H0.py` (analyses any counts directory), `gate_H0P.py`, `gate_H0_diag.py`, `gate_H0_model.py`, `gate_H0_kpilot.py`, `gate_H0_ddtest.py`, `gate_H0_2x2.py`, `gate_Q0P_2x3.py` (stage A, and since 2026-10-05 the `plan28` stage = gate `Q0P_2x3_plan`), `gate_CF_traj.py`, `gate_K0_2x3_2x4.py` (K0, `--live` option), `gate_CV.py` (gates `CV_2x3_plan` and `CV_2x2_info`), `gate_H0_ddrep.py` (stages reserve / predict / prereg-md / assemble), `gate_K1_2x3_fpilot.py` (stages record / build / patchcal / predict / prereg-md / assemble / submit). The laptop gates are `laptop_L2_qiskit_check.py` ... `laptop_L5_cudaq_check.py`.
- **Runner and status:** `run_gate.py` (runs a gate script, prints the status, on FAIL writes `validation/BLOCKED.md` listing the failing criteria, with `--push` commits and pushes on PASS), `check_package.py` (prints PACKAGE OK when everything is present), `update_status.py` (regenerates `validation/gates.md` and `reports/PROJECT_STATUS.md` from the JSON), `run_tests_no_pytest.py`, `make_amendment.py` (generates amendment 01 from the JSON; `--check-only` re-verifies every cited value).
- **IBM hardware tooling:** `ibm_account.py` (checks the stored key, never prints it), `h0_backends.py` (`resolve_backend`, `calibration_record`, `calibration_fingerprint` = rule D9), `h0_submit.py` (submit / retrieve split, dry run on `AerSimulator.from_backend(FakeFez)`, preflight, per-job `session.json`), `h0_qpu_time.py` (execution-time estimate from the target's durations), `h0_support_plan.py` (rule D3'), `h0_patch_select.py` (exhaustive embedding search scored by the idle-aware $f$), `h0_calwatch.py`, `h0_idle_model.py`, `h0_t2_override.py`, `h0_build_circuits.py`, `h0_compare_prep.py`, `h0_device_survey.py`, plus circuit builders `h0_diag_circuits.py`, `h0_kpilot_circuits.py`, `h0_ddtest_circuits.py`, `h0_2x2_circuits.py`.
- **Quantinuum tooling:** `quantinuum_account.py` (login via the Nexus token store; tokens never on a command line), `quantinuum_build_circuits.py`, `quantinuum_device_table.py` (device and cost table), `quantinuum_submit.py` (dry run, job bodies with `max_cost`), `quantinuum_stack_check.py`, `q0p_a6_phase_error_check.py`. Isolated virtual environment `~/.local/share/su2qc-quantinuum/venv` so the pinned qiskit stack in the `coding` conda environment is never touched (`data/quantinuum/stack_check_20261002.json` and `_after.json` show identical pins).
- **IonQ tooling:** only `ionq_2x3_feasibility.py` (published-specification arithmetic -> `data/ionq_2x3_feasibility_20261001.json`). The submission scripts and gates `I0P_2x3`, `I0P_2x4` named in `prompts/25` Part B have no script and no validation JSON in the repository today (not built; the Quantinuum route of `prompts/26` came first).
- **New on 2026-10-05/06:** `h0_ddrep_circuits.py` (builds the seven DD cells and four pulse-train pubs of H0_ddrep from the committed H0_ddtest circuits), `h0_devicewatch.py` (free metadata poll: a device counts as ready only when its status is `active` AND it publishes CZ errors; `operational` alone is not enough), `k0_nogo_note.py` (generates `reports/K0_2x3_ibm_heron_nogo.md`), `k1_ddrep_note.py` (generates the honest-limits paragraph of the K1 report from the H0_ddrep JSON), `cf_estimator_information.py` (gate `CF_estimator_2x2_info`).
- **Other:** `cf_traj_2x2_arm.py`, `cf_trajectories.py` (Pauli-trajectory decomposition, gate CF_traj), `s2d_2x3_device_requirements.py`, `s2d_recall_at_predicted_f.py`, `s2_duration_compare.py`, `s2_duration_report.py`, `s2_escalation_experiments.py`, `s2_fixed_recall.py`, `s3_device_model.py`, `report_circuit_structure.py`, `ionq_2x3_feasibility.py`, `ci_request.sh`, `ci_check.sh`, `ci_smoke.py`.

### 4.3 The gate system

A **gate** is a script whose result is written to `validation/<GATE>.json` with `"status": "PASS"|"FAIL"` and a list of criteria (`name`, `value`, `threshold`, `passed`), plus a generated report `reports/<GATE>_*.md`. Rule 1 of `CLAUDE.md`: "a gate passes only when its script writes status PASS, not when the prose says so"; every number in prose must come from `validation/*.json` or `data/*.json`. The 51 JSON files in `validation/` were enumerated with a short python snippet; 46 of them are gate results with a criteria list (38 on 2026-10-05), 4 are CI result files (`ci_gate_L4`, `ci_gate_S3`, `ci_gate_S2_2x4`, `ci_smoke`) and 1 is the GPU stage record `S2_2x4_gpu.json` (Section 5).

Two kinds of gate (the project's wording):
- **Validation gates** (E1-E3, S1, CS, L2, L5, ...): PASS means the code reproduces an independently known answer.
- **Measurement gates** (S2_2x4, S2D_levers, H0_kpilot, H0_ddtest, H0_2x2, Q0P_2x3, CF_traj, ...): PASS means "preregistered, measured, verified, consistent", never "the number is good". The measured number is reported as the result.

**Preregistration**: the circuits, shot counts, decision rule and prediction are written to a committed file *before* the device data exist. **Calibration fingerprint (rule D9)**: a sha256 over the calibration-record content the prediction actually reads (30 qubit and 54 edge blocks on the IBM patch); submission is allowed only when the live fingerprint equals the preregistered one, and it is recorded again at retrieval. **Dry runs** on a simulator precede every hardware submission (`H0_dryrun`, `H0_kpilot_dryrun`, `H0_ddtest_dryrun`, `H0_2x2_dryrun`, `H0_diag_dryrun`, `H0_ddrep_dryrun`, `K1_2x3_fpilot_dryrun`). **Device-readiness rule (2026-10-06):** a hardware submission waits for `scripts/h0_devicewatch.py` to report the device `active` with every CZ error published; the live `ibm_kingston` record of 2026-10-05/06 carried none (352 of 352 CZ keys without an error, status `maintenance` from about 01:12Z, `prompts/LOG.md` row 2026-10-05/06) and the first K1 attempt stopped there at 0 QPU s. **Rules that make the record honest**: preregistered records are never rewritten (a correction is a new gate); no tolerance is changed after the fact; the 30-minute rule (below); QPU spend only with the owner's explicit go.

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

The loop: planner writes a prompt, runner executes the gate, reviewer audits, `run_gate.py --push` on PASS; on FAIL the planner is invoked with `prompts/ESCALATION_TEMPLATE.md`. `prompts/LOG.md` is the execution log (136 lines; all outcomes with commit hashes). The numbered prompts 00-32 are listed in Section 6 with their titles. The coordinator session (the main Claude session) briefs agents, never writes production code, and is the only one that commits; there is also an auto-memory and a `gate` skill (`/gate <GATE> [--push]`).

### 4.5 The Perlmutter GPU CI loop

Source: `CLAUDE.md` ("skqd-ci" section), `SKQD-CI-SETUP.md`, `ci/README.md`, `RUNBOOK.md` ("Engine and HPC policy", owner 2026-09-21).

Perlmutter (the NERSC supercomputer, account `m4135_g`) **has no login from this project** (no ssh). It pulls the repository every hour at 07 minutes UTC, reads `ci/request.txt`, and runs *at most one allowlisted job*, then pushes the result back (`ci/status.json`, `validation/ci_gate_<TOKEN>.json`, `reports/ci-<jobid>.out`). Loop: commit and push, `scripts/ci_request.sh <TOKEN>`, poll `scripts/ci_check.sh` (not more than every 15 minutes; exit 0 done, 2 pending, 3 refused), read the JSON. Tokens: `smoke E1 E2 E3 S1 L1 L2 L3 L4 L5` originally, with `S3 04:00:00 1`, `H0P 01:00:00 1` and `S2_2x4` added by the owner on the Perlmutter side. Limits (enforced there, not changeable from the repository): one job at a time, at most 6 jobs per UTC day, 15-60 minutes walltime per token (S3 up to 4 hours), 1 GPU (an A100-SXM4-80GB, 81 920 MiB), at most 3 requests in a row without a pass before a `BLOCKED_<gate>` note. **Never** edit `ci/status.json`, `ci/poll.sh`, `reports/ci-*.out`, `validation/ci_*.json`.

**Engine policy** (`RUNBOOK.md`): exact numpy/scipy for E1-E3 and S1; Qiskit + Aer-GPU for the hardware-matching gates (L2, L3, L4, S2/S2D, S3, H0/H0P), with the code required to run on qiskit 1.4.3 and qiskit-aer-gpu 0.15.1 (the laptop has qiskit 2.5.2, aer 0.17.2, so gate modules are kept free of qiskit imports at load time); CUDA-Q 0.16 (target `nvidia`) for gate-level validation. Parallelise only along $k$, sector, $g^2$, lattice, shot batch, seed or resample; every GPU job records wall time, per-phase timings, GPUs, s/shot, peak GPU memory and mean GPU utilization in its JSON; more GPUs are proposed only with measured parallel efficiency $E(p)=T_1/(pT_p)\ge0.7$.

**CI jobs actually run** (from `validation/ci_*.json` and `prompts/LOG.md`): smoke job 58717267 (pass; A100 and `qiskit_aer_gpu` True); L4 job 58737320 (FAIL, GPU out-of-memory crash, 608 s; fixed by `shot_chunk_for` plus adaptive halving), L4 job 58741899 (PASS, 686 s, code sha `79f4dae`), S3 calibration job 58771538 (PASS, 255 s, code sha `ea600be`), S2_2x4 job 59162991 (PASS, 99 s, code sha `870d0c4`). Details in Section 6.

### 4.6 Repository bookkeeping directories

`validation/` (gate JSONs, `gates.md`, ignored `BLOCKED.md`), `reports/` (generated gate reports and the planner's analyses), `data/` (reference numbers, hardware raw counts under `data/hardware/`, calibration records, frozen circuits as QPY files, owner decisions), `prompts/` (every plan, numbered; `LOG.md`), `proposal/` (the manual, amendment 01, the Quantinuum access draft), `tests/` (pytest; last recorded totals: `coding` environment 270 passed / 19 skipped and the Quantinuum venv 287 passed / 2 skipped, `validation/Q0P_2x3.json` criterion Q7, with 287 passed / 19 skipped recorded in `prompts/LOG.md` row 2026-10-05 for commit 749fe3c; the newest recorded run is **342 passed / 19 skipped** in gates `H0_ddrep` (criterion D8), `K0_2x3_2x4` (K0.6) and `K1_2x3_fpilot` (K8), each with `scripts/check_package.py` returning PACKAGE OK; I ran no tests), `scratch/planner/` (the planner's prototypes whose numbers are "planner arithmetic" until a gate reproduces them), `slurm/`, `jobs/`, `ci/`.

## 5. The full gate table

Source: every `validation/*.json` (enumerated with a python snippet that reads `status`, `criteria[*].passed`, `environment.timestamp`, `environment.git_commit`, `runtime_s`), `validation/gates.md` (regenerated 2026-10-06 08:34 UTC; it now holds the rows `CF_traj`, `CF_estimator_2x2_info`, `CV_2x2_info`, `Q0P_2x3_plan`, `CV_2x3_plan`, `H0_ddrep` and `K1_2x3_fpilot`, but still not `K0_2x3_2x4`, `H0P_repro`, `H0_*_dryrun`, `K1_2x3_fpilot_dryrun`, `L4_p2_*`, `S2_fixed`, `S2D_idle`; those are added here from their JSON files). Column "kind": *validation* = PASS means a known answer is reproduced; *measurement* = PASS means "preregistered, measured, verified, consistent" and the measured number is the result (Section 4.3). The date/time is the string recorded in the JSON `environment.timestamp` in whatever time zone the run used (MDT, PDT or UTC). "Criteria" is passed/total. The commit is the repository commit at the time the gate ran (`n/a` where the run was on the Perlmutter CI snapshot).

### 5.1 Gate results (46 gate JSON files with criteria lists)

| gate | file | date, time as recorded | status | criteria | kind | runtime | commit | one-line meaning | key numbers (source in the file named) |
|---|---|---|---|---|---|---|---|---|---|
| `E1` | `validation/E1.json` | 2026-09-14 16:43:44 MDT | PASS | 23/23 | validation | 427 s | 57b3bff | Gauss law and the two independent Hamiltonian builders (2x2) | $\max\lvert [G_a(x),H]\rvert =0.0$ in the 160 000-dim redundant space; kernel dimension 82; sector split $\{2B:\dim\}=\{-4{:}2,-2{:}20,0{:}38,2{:}20,4{:}2\}$; $\max\lvert {\rm eig}(P^\dagger HP)-{\rm eig}(H_{\rm dressed})\rvert =2.309\times10^{-14}$ over 82 levels (threshold $10^{-12}$); element-wise $3.55\times10^{-15}$; link covariance $1.1\times10^{-16}$ |
| `E2` | `validation/E2.json` | 2026-09-14 16:44:00 MDT | PASS | 51/51 | validation | 15 s | 57b3bff | State counts (Table 2), vertex tables, codewords, decoder | 82 / 1 727 / 37 165 states at 2x2 / 2x3 / 2x4; 82/82 round trip at 2x2 (113/113 with a static pair); 2x3 sector dims $\{0{:}677,\pm2{:}426,\pm4{:}95,\pm6{:}4\}$ in the $2B$ key; random-string acceptance 0.15 % at 2x3 (0.242 % for static $[0,4]$) |
| `E3` | `validation/E3.json` | 2026-09-14 16:44:36 MDT | PASS | 85/85 | validation | 36 s | 57b3bff | Exact references (Table 1), static sectors, derived quantities, $\Delta t$ per sector | all Table 1 rows to 4 decimals (e.g. 2x2 $B{=}0$ $E_0=-3.6408$, $\pi/W=0.245$); 2x3 $V(2)=2.5898$; 2x4 $M_B=1.7851$; 2x2 $j_{\max}=1$ gives 152 states |
| `S1` | `validation/S1.json` | 2026-09-14 16:48:20 MDT | PASS | 12/12 | validation | 223 s | 57b3bff | Emulated support recall, certification and size-matched controls (2x3, 2x4) | 2x3 $B{=}0$ recall of the 99.9 % support $=1.0$ and $B{=}1$ $0.989$ at $f=0.1$, $2\times10^5$ shots (threshold 0.9); $E_0$ inside the Weinstein interval; $M_B$ interval $[1.6935,1.8314]\ni1.7765$; ridge Spearman 0.862 / 0.888; CIPSI within 3x of the oracle at $\lvert B\rvert =160,320$; 2x4 proxy recall $0.934$ (threshold 0.85) |
| `CS` | `validation/CS.json` | 2026-09-14 21:37:07 UTC | PASS | 4/4 | validation | 4 s | 3c32216 | Structure of the Hamiltonian terms in codeword space (input to S2) | 2x2 plaquette: one partner per state; 4 distinct pair amplitudes; structured plaquette gate vs dense exponential $3.97\times10^{-16}$; 30 CNOT (8 parity + 6 ladder + 16 UCRz) |
| `S2` | `validation/S2.json` | 2026-09-15 15:12:59 MDT | FAIL | 3/5 | measurement | 436 s | 5d60461 | Structured basic-gate circuits (hopping chains, interior-corner plaquettes) and their CZ cost | FAIL on the cost criteria only: 2x2 routed 618 CZ (budget $\le250$), 2x3 routed 5 477 (budget $\le500$); exactness $1.87\times10^{-14}$ and leakage $4.5\times10^{-14}$ pass |
| `S2_fixed` | `validation/S2_fixed.json` | 2026-09-15 20:18:31 MDT | FAIL | 5/9 | measurement | 301 s | 2fbcf29 | Fixed-angle generator (same codeword pairs, one angle per flip pattern): cost floor, leakage, recall | FAIL: 2x2 671 routed (heavy-hex) / 474 (square grid), 2x3 3 736 / 2 803, all above budget; recall kept (B=0 1.000, B=1 0.937 at $f=0.1$, `data/S2_fixed_recall.json`); not adopted |
| `S2D` | `validation/S2D.json` | 2026-09-16 07:02:12 MDT | FAIL | 6/8 | measurement | 213 s | 89102d2 | Device-resolved budget: 2x2 on Heron (FakeFez snapshot) and 2x3 on an all-to-all RZZ device at declared $\epsilon_2=10^{-3}$ | FAIL 6/8: 2x2 mean $f=0.1248$, worst $0.1166$ (pass); 2x3 mean $f=0.0534$ (needs $\ge0.1$: fail), worst $0.0532$; 2x3 shots per sector 4 605 472 vs quota $2\times10^5$ (fail); reproduces 618 routed and 2 164 all-to-all CZ |
| `S2D_idle` | `validation/S2D_idle.json` | 2026-09-22 16:36:34 MDT | FAIL | 6/15 | measurement | 406 s | 2c6edb6 | S2D re-evaluated on the idle-aware $f$ (scheduled circuit) at both ends of the $T_2$ bracket | FAIL 6/15: live ibm_fez, echo $T_2$: mean $f=6.708\times10^{-3}$, worst $1.542\times10^{-3}$; measured $T_2^*$: mean $1.298\times10^{-5}$; most favourable point of the bracket (DD perfect) mean $0.0623<0.1$. **Withdraws the 2x2/Heron S2D PASS as a hardware statement.** Hardware anchor V5: predicted 30.8 vs measured 35 accepted of 2 000 (ratio 1.135) |
| `S2D_levers` | `validation/S2D_levers.json` | 2026-10-02 11:13:55 MDT | PASS | 9/9 | measurement | 489 s | 782580c | 2x2 duration levers on ibm_kingston: compile/schedule levers, $f$ predicted at both $T_2$ ends, $r_{\rm crit}$ | PASS 9/9: best row duration 0.710x the as-is canary; Aer $f_{\rm clean}$ 0.2170 (echo end) and 0.0312 (ratio 0.174) for the signed family with ALAP; $r_{\rm crit}(0.1)\approx0.329$ (C6 scoped to $p_{\rm ref}\ge0.5$ by planner ruling) |
| `S2_2x4` | `validation/S2_2x4.json` | 2026-10-01 09:15:29 PDT | PASS | 12/12 | measurement | 0 s | n/a | 2x4 coarse step compiled to exact circuits, verified, measured (counts, duration, idle budget, $T_2/t_{2q}$) | PASS 12/12: exactness $3.4\times10^{-14}$; leakage of the transpiled 28-qubit circuit $1.10\times10^{-12}$ (GPU job 59162991); 69 688 CZ all-to-all, 148 726 routed; $T_2/t_{2q}=638\,742$ required vs Heron harmonic mean 1 038 (`reports/S2_2x4_compilation_and_device_requirement.md`) |
| `S3_smoke` | `validation/S3_smoke.json` | 2026-09-16 11:46:01 MDT | FAIL | 1/2 | measurement | 295 s | 1223e92 | S3 pipeline smoke test at 2x3 $B{=}1$ (2 shots per circuit) | FAIL by construction: recall 0.0737 at 24 shots (criterion $\ge0.9$); 295 s on laptop CPU; shows 10.42 s per shot at 2 shots per call |
| `S3` | `validation/S3.json` | 2026-09-22 18:01:22 PDT | PASS | 4/4 | measurement | 248 s | n/a | GPU throughput calibration of the 2x3 $B{=}0$ set (reduced size; recall criterion NOT evaluated) | PASS 4/4 as a calibration: 0.01987 s/shot at 20 qubits on one A100 (job 58771538) vs 3.198 s/shot on the laptop (161x); projected 1.10 h per $2\times10^5$-shot sector (4.41 h for four sectors) |
| `L2` | `validation/L2.json` | 2026-09-15 20:20:11 MDT | PASS | 4/4 | validation | 8 s | 0420211 | Qiskit circuits reproduce the numpy reference at 2x2 | max $\lvert \text{Qiskit}-\text{reference}\rvert =2.69\times10^{-14}$ over 35 circuits; 10 000/10 000 noiseless shots decode; TVD 0.0103 |
| `L3` | `validation/L3.json` | 2026-09-15 15:04:26 MDT | FAIL | 0/2 | measurement | 14 s | 5d60461 | Transpiled CZ counts of the dense 2x2 circuits (S2 baseline) | FAIL as expected: 35 606 CZ all-to-all, 55 459 routed (budget 250); led to the structured-gate work of S2 |
| `L4` | `validation/L4.json` | 2026-09-22 01:22:38 PDT | PASS | 4/4 | validation | 677 s | n/a | Aer noise-model sampling at 2x2 (S3 preparation); the current record is the GPU run | PASS 4/4 on the GPU at full production shots (job 58741899): yields 0.458 / 0.441 vs model 0.378 / 0.376 (ratios 1.21 / 1.17); $\lvert B\rvert =38/38$ and $20/20$; recall 1.000; 19.8x faster than the laptop. The two earlier laptop records are in `L4_p2_*.json` |
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
| `Q0P_2x3` | `validation/Q0P_2x3.json` | 2026-10-02 21:36:57 MDT | PASS | 7/7 | measurement | 926 s | 8072b8d | Signed 2x3 circuits compiled to the Quantinuum native gate set, verified, costed, packaged (Stage A; Stage E/P not run) | PASS 7/7: 44 frozen circuits, max $\lvert \Delta\psi\rvert =2.09\times10^{-13}$, 2 158 ZZPhase on all 44, mean 4.9666 HQC/shot; H2-2 gate-only $f=0.1502$, Helios-1 0.1642; Stage E 11 936 eHQC, pilot 9 938 HQC (later re-planned); 0 HQC spent |
| `CF_traj` | `validation/CF_traj.json` | 2026-10-05 13:47:33 MDT | PASS | 7/7 | measurement | 1201 s | a8ebbaa | Pauli-trajectory decomposition of the reference-hit excess and the near-clean correction $r_{nc}$ | PASS 7/7: trajectory prediction 63.46 $\pm$ 2.254 vs 64 observed hits ($P=0.9794$); $r_{nc}=1.115$; floor theorem holds on all four arms; $k{=}4$ mixture bias 1.274 [1.170, 1.402] |
| `K0_2x3_2x4` | `validation/K0_2x3_2x4.json` | 2026-10-06 01:38:10 MDT | PASS | 6/6 | measurement | 943 s | 880961d | ibm_kingston readiness of 2x3 and 2x4 (prompts/25 Part A); **rewritten on 2026-10-06 by the `--live` run (the 2026-10-05 FAIL 5/6 row, written with `--skip-tests`, is superseded)**; its verdict fields are a model result, not a criterion | PASS 6/6: all-to-all 2 164 CZ reproduced; the 2x3 circuit `B0_ref25_k1` routed on the target of each record with the exactness-gated seed rule (plain level-3 seed 6, 5 527 CZ, is NOT exact: max $\lvert\Delta\psi\rvert=4.9\times10^{-5}$) to **5 659 CZ**, 21 active qubits, ALAP 410.3 / 411.2 $\mu$s. Committed record 2026-10-02 (verdict record): $f_{\rm ceiling,2q}=9.833\times10^{-3}$, layout gate-only $6.069\times10^{-6}$, idle-aware $1.06\times10^{-16}$ (echo $T_2$) / $3.73\times10^{-38}$ ($T_2^*$ ratio 0.174), $\epsilon_2$ needed for $f=0.05$ $5.29\times10^{-4}$ vs best edge $8.16\times10^{-4}$ (misses by 1.54x). Live record 2026-10-06: $6.717\times10^{-3}$, $1.671\times10^{-5}$, $1.66\times10^{-15}$ / $5.20\times10^{-35}$, misses by 1.67x. 2x4 $\log_{10}f_{\rm ceiling}=-52.8$ (routed). No record meets 0.1 / 0.05; 0 QPU s; pytest 342 passed / 19 skipped |
| `CV_2x2_info` | `validation/CV_2x2_info.json` | 2026-10-05 17:41:27 MDT | PASS | 2/2 | measurement | 14 s | 3d5f05a | Convergence and coverage curves on the recorded H0_2x2 counts, **labelled "not a device test (saturation)"**; CV0 (structural) only | PASS 2/2: the curves are flat because the sectors saturate from garbage ($Na/\dim\ge5$, $\lvert B_{\rm all}\rvert=\dim$, garbage-only reaches $E_0$): CV4 margin at $N$ is $-1.37\times10^{-4}$ ($B=0$) and $-2.2\times10^{-15}$ ($B=1$; `data.information.<sector>.information.CV4_margin_at_N`) against $E_{\rm tol}=0.02317$ / 0.01214; no verdict on any recorded 2x2 result; this is why the 2x3 criteria exist |
| `CF_estimator_2x2_info` | `validation/CF_estimator_2x2_info.json` | 2026-10-05 17:28:05 MDT | PASS | 2/2 | measurement | 4 s | 3d5f05a | Every recorded 2x2 clean fraction labelled by statistic ($f_{\rm hit}$ or mixture), with the corrected $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$, the 2x2 signed-bar qualification, the A5 model bracket and (added by `prompts/31` ruling 6) the `qualification_ruling` text | PASS 2/2: adopted cell T3 $f_{\rm hit}=0.1129$ [0.1058, 0.1203] $\to$ $\hat f_{\rm ideal}=0.1012$ [0.0938, 0.1091]; the preregistered rule (lower 95 % end $\ge0.1$) reads **AMBIGUOUS**, the v3 rule of the 2x3 stages (lower $\ge0.05$ and point $\ge0.10$) reads GO but is not applied retroactively; A5 bracket $r=0.674$ [0.539, 0.835] ($T_2^*$ end) and 0.902 [0.884, 0.918] (echo end); no recorded verdict edited (Block (b3)) |
| `Q0P_2x3_plan` | `validation/Q0P_2x3_plan.json` | 2026-10-05 17:56:24 MDT | PASS | 7/7 | measurement | 781 s | 3d5f05a | Rule D3'-R implemented and reproduced (P1), $\lambda^*$ and recall guarantees (P2), emulated check of the plan on $B_{\rm all}$ with the owner's certificate reading (P3), HQC by the billing formula job by job (P4), preregistration v3 rendered from the JSON only (P5), tests (P6), plan identical to `CV_2x3_plan`'s final plan (P7) | PASS 7/7: D3'-R base plan (no re-sizing) 63 875 + 96 503 = 160 378 shots, 797 157 HQC at $f=0.05$; 84 112 shots, 418 166 HQC at 0.10; 60 812 shots, 302 382 HQC at 0.15; **re-sized plan 1 279 660 / 665 605 / 471 801 HQC** (Block (g)); Stage E v3 and Stage P v3 each 2 000 shots (800/800/200/200), 9 949.92 eHQC / HQC (USD 124 374 ESTIMATE for Stage P); GO rule v3 on $\hat f_{\rm ideal}$; calibration pubs 45.0 and 45.2 HQC; at $f=0.10$ recall of $S_{999}$ on $B_{\rm all}$ 0.953 / 0.977 / 0.953 ($B=0$) and 0.947 / 0.958 / 0.958 ($B=1$) in the three seeds (`prompts/LOG.md` row 2026-10-05); pytest 321 passed / 19 skipped; commits no HQC |
| `CV_2x3_plan` | `validation/CV_2x3_plan.json` | 2026-10-05 17:40:48 MDT | PASS | 37/37 | measurement | 679 s | 3d5f05a | Emulated check (S1 proxy at clean fraction $0.7f$, 3 seeds, $f=0.05/0.10/0.15$, both sectors) that the D3'-R plan converges in shots and in Krylov $k$, carries $\ge0.99$ of the ground-state weight, beats random bases, and meets the certificate widths; **an emulation of the plan, not a device statement** | PASS 37/37 on `B_all` $\cup$ references: $E_{\rm tol}=1.4225\times10^{-2}$ ($B=0$, 69 states) and $1.1040\times10^{-2}$ ($B=1$, 76 states); $B=0$ passes at $s=1$ at every $f$, $B=1$ needs $s=2$ ($s=1.5$ fails CV2); oracle-width table reproduced (196 fields, max scaled difference $3.2\times10^{-14}$); no STOP (Section 6.19, Blocks (q), (q2), (r)) |
| `H0_ddrep_dryrun` | `validation/H0_ddrep_dryrun.json` | 2026-10-06 00:59:27 MDT | PASS | 8/8 | measurement | 14 s | cd9ce12 | H0_ddrep dry run on Aer / FakeKingston (20 pubs x 6 000; the sampling itself took 1 738 s per `prompts/LOG.md`, the JSON re-assembly 14 s) | PASS 8/8: path check only; ratios sit at the null values (T3 0.830, T1 0.735 on Aer) because Aer cannot show a DD gain (its relaxation on a delay is Markovian) and the trains sit at the readout floor |
| `H0_ddrep` | `validation/H0_ddrep.json` | 2026-10-06 01:11:17 MDT | PASS | 8/8 | measurement | 422 s | 36c48a2 | One-job replication on `ibm_kingston`: the XY4 gain (T0 vs T3), the T1 collapse, four mechanism cells (M1-M4) and four pulse-train pubs; **no criterion on R1, R2, C1, the classes or the mechanism reading** | PASS 8/8, results: **R1 False, R2 False, C1 False**; $f_{T0}=0.0818$ [0.0758, 0.0881] (0.0400 on 2026-10-02), $R_{T3}=0.895$ [0.804, 0.996] (2.819 on 10-02), $R_{T1}=0.647$ [0.575, 0.727], $R_{M4}=1.150$ [1.040, 1.271] (the only INTACT cell); reading "no single hypothesis"; $x$ over-rotation $\epsilon_q=0.0148$-$0.0204$ rad on 12/12 qubits; job `db29p6nr11fs7396e4ig`, 37.0 s (Section 6.21, Blocks (o), (p)) |
| `K1_2x3_fpilot_dryrun` | `validation/K1_2x3_fpilot_dryrun.json` | 2026-10-06 02:20:48 MDT | PASS | 9/9 | measurement | 430 s | f8df126 | K1 dry run: readout pubs through the real `h0_submit --dry-run` path on FakeKingston, coarse pubs sampled noiselessly (400 shots each; one noisy 21-qubit shot cost 140.6 s) | PASS 9/9: path check; noiseless reference hits 754 of 800, $f_{\rm hit}=1.238$ [1.151, 1.330] ($0.82\,f_{\rm hit}$ 95 % [0.944, 1.090], containing 1), decision class GO-B by construction |
| `K1_2x3_fpilot` | `validation/K1_2x3_fpilot.json` | 2026-10-06 02:33:45 MDT | PASS | 8/8 | measurement | 422 s | 504d452 | The 2x3 clean-fraction pilot on `ibm_kingston`: the two signed $k=1$ circuits (`B0_ref117_k1`, `B1_ref29_k1`, 5 659 CZ, XY4 cell T3) + 2 readout pubs, one job of 4 pubs x $10^5$ shots; GO-B / GO-A / NO-GO on $\hat f_{\rm ideal}$; **no criterion on $f$ or on the decision** | PASS 8/8, decision **NO-GO (firm)**: 0 reference hits in $2\times10^5$ shots vs 0.191 from garbage; pooled $\hat f_{\rm ideal}=-1.12\times10^{-6}$, 95 % upper bound $2.06\times10^{-5}$ (GO-A needs $3\times10^{-4}$); accepted 58 / 45 of $10^5$ (garbage level); readout min diagonal 0.9358; job `db2avbe8v0ts73c2i8b0`, 188.0 s (Section 6.22, Block (s)) |

**Reading the failures.** The FAIL rows are of four kinds and none is a hidden defect: (1) *cost gates that were deliberately re-defined* (S2, S2_fixed, S2D, L3): the manual's gate-count budget was replaced by the amended device-resolved budget; (2) *calibration/measurement gates whose FAIL records an honest negative physics result* (H0_canary, H0_kpilot, S2D_idle): the canary gave 8 accepted shots against a simulated 71; the pilot measured $f=0.0413$ against the bar 0.1; (3) *diagnostic gates failing one prediction-comparison criterion while answering their own question* (H0_diag); (4) *by-construction* failures (S3_smoke at 2 shots per circuit, the two early laptop L4 records); the former tests-skipped `K0_2x3_2x4` FAIL is gone because the gate was re-run in full. Records are never rewritten; a corrected analysis is a new gate (e.g. S2D_idle supersedes the 2x2 reading of S2D, H0_model supersedes the reading of H0_canary).

### 5.2 Gates that are still open (no JSON; from `validation/gates.md`)

| gate | check (manual Step 10) | runs on | status today |
|---|---|---|---|
| H0 | 2x2 hardware: decoder validity, bit order, parity checks; measured $f$ within 30 % of the model | QPU | open as a gate; its role was realised by the measurement gates `H0_canary`, `H0_diag`, `H0_kpilot`, `H0_ddtest`, `H0_2x2` (and, since 2026-10-06, `H0_ddrep`, the replication that did not confirm the XY4 gain) (the "within 30 % of the model" criterion was read measurement-to-measurement, because the model was 5.1x off in the pilot) |
| H1 | 2x3 $B{=}0$: certified interval of width $\le0.1$ containing the exact $E_0$; recall $\ge0.8$ | QPU | open (no usable 2x3 hardware data exist: the only 2x3 job, K1, saw no reference hit; at the plan of record H1 is read on Kato-Temple with the exact $E_1$, Section 2.7) |
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

Counting the 46 gate JSON files above: PASS 34, FAIL 12 **(sum of sourced statuses; counted by the python snippet)**. On 2026-10-05 the same count over 38 files gave 25 PASS / 13 FAIL; the difference is eight new gates (`CV_2x2_info`, `CF_estimator_2x2_info`, `CV_2x3_plan`, `Q0P_2x3_plan`, `H0_ddrep_dryrun`, `H0_ddrep`, `K1_2x3_fpilot_dryrun`, `K1_2x3_fpilot`, all PASS) and one flipped row (`K0_2x3_2x4` FAIL 5/6 $\to$ PASS 6/6), i.e. $25+8+1=34$ PASS and $13-1=12$ FAIL (sum of sourced numbers). A machine-readable version of the table with dates is Appendix block (a), regenerated from the JSON files.

**Files that were interim in the previous report and are now final.** `validation/CV_2x2_info.json`, `validation/CF_estimator_2x2_info.json` and `validation/Q0P_2x3_plan.json` (then FAIL 3/7) were re-run on 2026-10-05 after the `prompts/31` rulings and are all PASS; the earlier `CV_2x3_plan` FAIL 27/36 (a planner error in the width criterion, Section 6.19) is overwritten by the PASS 37/37 record (the FAIL is preserved in `prompts/LOG.md` and in git history at `eb3f71e`).

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
| 30 | Energy-convergence and weighted-coverage criteria for the 2x3 plan check (owner decision 2a, 2026-10-05): definitions, constants, re-sizing rule; ruling in force until `prompts/31` amended it (the width criterion on $B_{\rm sig}$ and CV3 on the $3\to4$ step were planner errors) |
| 31 | CV_2x3_plan fix (2026-10-05): certificate basis $B_{\rm all}$ at 2x3, H1 width on Kato-Temple with the exact $E_1$, CV3 = the $k=4\to5$ step, the $B=1$ re-sizing, the 2x2 qualification reading (seven rulings; Section 6.19) |
| 32 | Owner decision 2026-10-06, option A then B: the 2x3 IBM NO-GO recorded on K0; one preregistered job on `ibm_kingston` replicating the XY4 gain and testing the mechanism of the context-aware DD collapse (gate H0_ddrep); then the K1 2x3 pilot as built (Sections 6.21, 6.22) |

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
*GPU runs (Perlmutter A100).* L4 job 58737320 crashed (GPU out-of-memory, 608 s: 20 circuits x 20 000 shots in one `run()` call); a memory-aware chunker (`shot_chunk_for`) and adaptive halving were added. L4 job 58741899 **PASS 4/4** (686 s; full production shots, 20 000 per circuit vs 8 / 22 on the laptop; yields 0.458 / 0.441 vs model 0.378 / 0.376; $|B|$ 38/38 and 20/20; recall 1.000): timing 0.00103 s/shot against the laptop's 0.02037 s/shot, a **19.8x speed-up**; peak GPU memory 27 915 MiB; mean GPU utilisation 15.3 % (max 27 %): not GPU-bound, so no second GPU is proposed; the allocation model underestimates memory by 3.5x (8.0 GB predicted, 27.9 GB measured). S3 calibration job 58771538 **PASS 4/4** (255 s job per `ci_gate_S3.json`; gate runtime 248 s, sampling wall 245 s): 0.01987 s/shot at 20 qubits vs 3.198 s/shot on the laptop (**161x**): a $2\times10^5$-shot sector is 1.10 h instead of 177.7 h; recall criterion not evaluated. `prompts/18` proposed the allowlist lines `S3 04:00:00 1` and `H0P 01:00:00 1` with the measured justification.
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
*Verdict.* T3 adopted by the preregistered rule (largest point ratio among cells with lower interval $>1$ and $R\ge1.25$); the signed bar read **GO** on the adopted cell (on the reference-hit statistic; see the 3a qualification in Section 9); gate **PASS 8/8**. The context-aware cell **collapsed** (about 65x below its null, planner arithmetic 0.012/0.816), unexplained: its statevector and duration were verified equal to the base circuit, so the *logical* circuit is right; the planner's three untested hypotheses are in `reports/H0_2x2_full_hardware_report_20261002.md` section 3. **Both the gain and the collapse failed to replicate four days later (gate `H0_ddrep`, Section 6.21).** *QPU s = 20.0.*

### 6.15 2026-10-02: H0_2x2, the full 2x2 SKQD run on ibm_kingston (`prompts/24` Stage R)

*What.* Under the owner's decision of 2026-10-02 (`data/owner_decision_20261002_run_below_signed_budget.md`: "... start preparing to send the 2x2 circuit anyway to qpus to finish run and see result all the way through to the end, meaning the skqd run for 2x2 plaquettes using 121 s of qpu time"), the 28 coarse circuits (7 references x $k=1..4$) + 2 readout pubs ran in 5 jobs on the pilot's patch with DD cell T3, DD/twirling options off, ALAP; fingerprint `84d59cbf9b5973d1` at preregistration (commit `a5e2c09` 2026-10-02T14:38:28-06:00), submission (21:05:55 UTC) and retrieval. Jobs `db01pddj371s73dnnqm0` (3.0 s), `db01pdtj371s73dnnqmg` (3.0), `db01pe04oijs73e8cl30` (4.0), `db01pelj371s73dnnqo0` (22.0), `db01peql7guc73cfndc0` (21.0).
*Numbers* (all `validation/H0_2x2.json`, detail in Appendix blocks (c)-(e)). Shot plan by rule D3' at the adopted $f$: $N_4=13\,100$ ($B{=}0$) / 31 400 ($B{=}1$), 133 907 coarse shots in all. Pooled $f$ over the seven $k=1$ circuits (267 shots each): **0.1271, 68 % [0.1174, 0.1375], 95 % [0.1084, 0.1479]** (173 reference hits vs 0.46 expected from garbage; per circuit 0.1024-0.1390). Readout min diagonal 0.9417, survival product 0.8338. Sector support: $B=0$: 69 505 shots, 9 454 accepted, $|B_{\rm all}|=38/38$, $|B_{\rm sig}|=35/38$ (exact 99.9 % support 16); $B=1$: 64 402 shots, 7 885 accepted, $20/20$, $19/20$ (13). Energies on $B_{\rm sig}$: $B=0$ $E_R=-3.6402188765$ vs exact $-3.6407665507$ ($E_R-E_0=5.48\times10^{-4}$), $r_H=0.0603$, Weinstein $[-3.700489,-3.640219]$, Kato-Temple $[-3.641574,-3.640219]$; $B=1$ $E_R=-1.8615822852$ vs $-1.8615880345$ ($5.75\times10^{-6}$), $r_H=5.95\times10^{-3}$ (below the exact gap $E_1-E_R=0.0418$, so the gap assumption holds and the lowest cluster level is certified), Weinstein $[-1.867536,-1.861582]$, Kato-Temple $[-1.862424,-1.861582]$; every interval contains the exact $E_0$. Saturation: $Na/\dim=16.97$ / 15.72. **Controls:** garbage-only (100 seeds): uniformly random strings give $|B|=38$ and 20 and $E_R=E_0$ to $4\times10^{-16}$ in every seed: **the processor could have output white noise and the $B_{\rm all}$ energies would be identical**; random-at-equal-size (200 seeds): the hardware's $B_{\rm sig}$ energy sits at the **5.0th percentile** for $B=0$ (size 35: random mean $-3.63266\pm0.00639$) and the **28.5th percentile** for $B=1$ (size 19; only 18 distinct random bases exist, so the percentile is coarse).
*Verdict.* Gate **PASS 8/8** (a measurement gate). Publishability (planner, `reports/H0_2x2_full_hardware_report_20261002.md`): **not** publishable as an SKQD physics result; publishable as a methods note (honest sampling at a noise-saturated size) and, after replication, a short note on the XY4 finding (**the replication of 2026-10-06 did not confirm the gain, Section 6.21; the XY4 note is withdrawn, Section 9.5**). *QPU s = 53.0* (3+3+4+22+21). Account after: **102 s consumed, 498 s remaining** of 600.

### 6.16 2026-10-02: the 2x3/2x4 device question (`prompts/25`, `26`, `27`); Q0P_2x3

*K0 verdict (planner, `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md`; the 5 477-CZ circuit and the $1.14\times10^{-2}$ ceiling below are the planner's 2026-10-02 survey values, superseded on 2026-10-05/06 by gate `K0_2x3_2x4`'s exact 5 659-CZ circuit and ceilings $9.83\times10^{-3}$ / $6.72\times10^{-3}$ on the two records, Section 6.20, and by the K1 measurement, Section 6.22).* On the committed kingston record (20261002T1906Z: CZ error min $8.164\times10^{-4}$, 10th percentile $1.146\times10^{-3}$, median $1.804\times10^{-3}$; $T_2$ median 147 $\mu$s, CZ 68 ns): 2x3 routed 5 477 CZ gives a ceiling $f\le(1-\epsilon_{2,\min})^{n_{CZ}}=1.14\times10^{-2}$, below the worst-case bar 0.05 by 4.4x before one-qubit, readout and idle errors, which lower it to about $10^{-4}$: **NO-GO**; 2x4 routed 148 726 CZ needs $\epsilon_2\le2.0\times10^{-5}$ for $f=0.05$ (the best edge is 41x worse): ceiling $\sim10^{-53}$: **NO-GO**; "no 2x2 technique can change it". **IonQ** (vendor pages read 2026-10-02; `data/ionq_2x3_feasibility_20261001.json`): Forte / Forte Enterprise (36 qubits; spec 2q 0.4 %, 1q 0.02 %, SPAM 0.5 %; day-measured DRB 99.3 % / 99.5 %; T2 about 1 s; ZZ 950 $\mu$s) give 2x3 gate-only $f=8.61\times10^{-5}$ (virtual $R_z$; Aria $3.52\times10^{-5}$) with a serial-idle estimate of $e^{-22}$; Aria is retired; Tempo is a late-2026 projection whose 99.9 % target gives $f\approx0.077$, still below 0.1; 2x4 is far out of reach (and its 208 399 native gates exceed IonQ's 150 000-gate job limit). 2x2 on Forte is feasible (gate-only $f=0.303$).
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
*`prompts/30` (planner, `CV_2x3_plan`).* Finding: coverage is checked as recall but the energy only at the final point; convergence against shots, against $k$, and weighted coverage are checked nowhere as a criterion. Defines the weighted coverage $W(B)=\sum_{s\in B}|c_s|^2$ (exact ground state of each sector; the captured weight of `support_metrics`), nested subsamples (prefixes of each circuit's shot sequence at $\phi\in\{1/16,1/8,1/4,1/2,1\}$), a Krylov curve cumulative over $k=1..4$, 200 random equal-size bases at every point, **one computed constant** $E_{\rm tol}=E_R(R\cup\text{top 80 \% of }S_{999})-E_0$ (the Ritz error H1's own recall target tolerates; planner expectation of order $10^{-2}$ from Table 3, `oracle|80` = 1.010e-2 / 1.024e-2), and **criteria CV0-CV5** (structural; shot convergence $E_R(N/2)-E_R(N)\le E_{\rm tol}$; certificate $r_H(N/2)\le0.1$ ($B=0$) / 0.15 ($B=1$) with $E_0\in[E_R-r_H,E_R]$; Krylov convergence $E_R(B^{(3)})-E_R(B^{(4)})\le E_{\rm tol}$, failure = STOP because a $k=5$ circuit is a family change; below the random 2.5th percentile with $E_{\rm rand,2.5\%}-E_R\ge E_{\rm tol}$ and weight above the random 97.5th percentile; $W(B_{\rm sig}(N))\ge0.99$) and a **re-sizing rule** (uniform multiplier $s\in\{2,4,8\}$ on D3'-R, smallest passing on prefixes of the same samples; $s=8$ failing = STOP; planner arithmetic: 418 167 HQC at $f=0.10$ becomes about 8.4e5 / 1.7e6 / 3.3e6). Stage E / P test $f$ only (two references cannot generate a support). A 2x2 information block applies the same curves to the H0_2x2 counts, labelled "not a device test (saturation)". Laptop about 1 executor day, 0 QPU s, 0 HQC. **Executed the same day; its first run failed and `prompts/31` corrected the criteria; the passing result is in Section 6.19.**
*`proposal/quantinuum_access_request_draft_20261005.md`* (a draft by the coordinator for the owner to edit; nothing sent): two routes, (A) the OLCF Quantum Computing User Program (QCUP; default emulator quota "6000 seconds"; hardware credits "must be justified using results from an emulator"; eligibility to be confirmed by the owner) and (B) Sales@Quantinuum.com for a research agreement with Nexus access; ask for the emulator first (about 10 000 eHQC: two $k=1$ circuits at 800 shots and two $k=4$ circuits at 200), then, if the preregistered rule passes ($\hat f_{\rm ideal}\ge0.10$ with 95 % lower bound $\ge0.05$), a hardware pilot of the same four circuits (about 10 000 HQC); five questions to the vendor (measured 2q error; memory error per layer for a 20-qubit mostly serial 1 900-layer program; parallel gates; how $R_z$ and PhasedX enter HQC; the HQC rate and research allocations). The full-campaign scale for the owner's planning is 3.0-4.2e5 HQC at H2-2 (prompts/28/29), a minimum under the convergence condition. *QPU s = 0, HQC = 0.*

### 6.19 2026-10-05: the 2x3 plan check (`prompts/30`, `prompts/31`; gates `CV_2x3_plan`, `Q0P_2x3_plan`)

*The question (owner decision 2a).* A campaign on the minimum D3'-R sizing may be approved only if an emulation of the plan shows **energy convergence** (the Ritz energy $E_R$ and the certificate width against shots and against the Krylov order $k$) and **weighted coverage**. Gate `CV_2x3_plan` is that emulation: the S1 proxy at clean fraction $0.7f$, 3 seeds (20260914, 1, 2), $f=0.05/0.10/0.15$, both sectors, nested subsamples at 1/16 ... 1 of the plan's shots, 200 random equal-size bases at every point. Criteria (the project's labels): **CV0** structural (nested, monotone, variational, the manual's Table 3 oracle rows reproduced); **CV1** $E_R(N/2)-E_R(N)\le E_{\rm tol}$; **CV2** certificate width at $N/2$ and $N$ meets H1 ($\le0.1$, $B=0$) / H2 ($r_H\le0.15$, $B=1$) and brackets $E_0$; **CV3** convergence in $k$; **CV4** better than random bases of the same size by at least $E_{\rm tol}$; **CV5** captured ground-state weight $W\ge0.99$. The one computed constant is $E_{\rm tol}=E_R(R\cup\text{top 80 \% of }S_{999})-E_0$, the Ritz error that H1's own recall target ($\ge0.8$) tolerates: $1.4225\times10^{-2}$ at $B=0$ (69 states of $S_{999}=86$) and $1.1040\times10^{-2}$ at $B=1$ (76 of 95) (`validation/CV_2x3_plan.json -> data.E_tol`).

*First execution: FAIL 27/36, STOP (2026-10-05, `prompts/LOG.md`).* CV2 and CV3 failed on the **width** over $B_{\rm sig}$ (the signal support) in every $B=0$ cell and CV3 at both sectors; re-sizing to $s=8$ could not rescue $B=0$. The planner's diagnosis (`prompts/31`, max effort; none of it a code bug): **D1** the Weinstein width is $r_H\approx10\sqrt{1-W}$ at 2x3, so a width $\le0.1$ needs $W\ge0.9999$ (173 states, hardest state with weight $1.8\times10^{-5}$, about $6\times10^{6}$ shots per sector by the $k=4$-scaled bound; planner arithmetic) and is unreachable even by the oracle $S_{999}$ ($r_H=0.265$, Block (r)); the manual's certified interval is Weinstein *or* Kato-Temple (Step 5.3) and the criterion had applied the Weinstein width to H1 by planner error. **D2** the $B_{\rm sig}$ cut is a saturation-regime device (2x2, $Na/\dim=17$); at 2x3, $Na/\dim=0.03$-$0.5$, it drops exactly the low-weight states the residual needs and breaks nestedness, while the manual defines $B$ as the union of accepted configurations (Step 5.1). **D3** CV3 tested the $3\to4$ step, which only shows that the $k=4$ circuits are needed; convergence is the $4\to5$ step, which can be emulated without a device (a coarse circuit has the same gate count at every $k$).

*The rulings (`prompts/31`, "Ruling", seven items) and the owner decisions.* (1) Certificates, CV1-CV5 and the D3'-R check are evaluated on $B_{\rm all}\cup$ references at 2x3; the $B_{\rm sig}$ rule (decision P9) stays for 2x2 and for the neural step's training labels. (2) CV2 at $B=0$ reads **Kato-Temple with the exact $E_1$**, at $B=1$ Weinstein $r_H\le0.15$; both thresholds unchanged. **Owner confirmation, verbatim "keep Kato-Temple for B=0, go ahead"** (`data/owner_decision_20261005_kt_certificate.md`), with the recorded caveat that this reading needs an exactly known $E_1$ (classical at 2x3, not beyond exact diagonalisation). (3) CV3 becomes $E_R(B^{(4)})-E_R(B^{(5)})\le E_{\rm tol}$ at equal shots, a failure being an owner item and not a STOP. (4) Re-sizing: the smallest $s\in\{1.5,2,3,4,6,8\}$ per sector. (5) `Q0P_2x3_plan` P3 reads recall on $B_{\rm all}$ and the ruling-2 certificate; preregistration v3. (6) The 2x2 qualification is read under the rule the verdict was preregistered with: GO on $f_{\rm hit}$, **AMBIGUOUS on $\hat f_{\rm ideal}=0.1012$ [0.0938, 0.1091]**; the v3 rule is not applied retroactively (a post-hoc rule change). (7) Decision 2a is checkable.

*Result: `CV_2x3_plan` PASS 37/37 (no STOP) and `Q0P_2x3_plan` PASS 7/7.* Table (maximum over the three seeds unless "min"; every figure from `validation/CV_2x3_plan.json -> data.criteria_by_seed, data.plan`; Blocks (q), (q2)):

| $f$ | sector | $s$ | shots | HQC | CV2 width at $N/2$ (limit) | CV3 $\Delta E_{4\to5}/E_{\rm tol}$ | CV4 margin / $E_{\rm tol}$ (min) | CV5 $W$ (min) |
|---|---|---|---|---|---|---|---|---|
| 0.05 | $B=0$ | 1 | 63 875 | 317 546 | 0.0195 (0.1, KT) | 0.218 | 7.93 | 0.99952 |
| 0.05 | $B=1$ | **2** | 193 600 | 962 114 | 0.1181 (0.15, Weinstein) | 0.264 | 4.74 | 0.99986 |
| 0.10 | $B=0$ | 1 | 34 909 | 173 614 | 0.0252 (0.1, KT) | 0.675 | 8.41 | 0.99951 |
| 0.10 | $B=1$ | **2** | 99 000 | 491 991 | 0.1433 (0.15, Weinstein) | 0.307 | 5.20 | 0.99985 |
| 0.15 | $B=0$ | 1 | 27 309 | 135 860 | 0.0267 (0.1, KT) | 0.206 | 8.36 | 0.99928 |
| 0.15 | $B=1$ | **2** | 67 600 | 335 941 | 0.1343 (0.15, Weinstein) | 0.335 | 5.83 | 0.99976 |

At $B=1$ the factor $s=1.5$ fails CV2 at every $f$ (Weinstein $r_H(N/2)=0.1568$ / 0.1669 / 0.1553 against 0.15; the $s=2$ values are 0.1181 / 0.1433 / 0.1343), so the owner decision of the same evening (`data/owner_decision_20261005_b1_x2_plan.md`, verbatim "approve the 2x shot plan for sector B=1") fixes the plan of record at $B=0$ at $s=1$ and $B=1$ at $s=2$. **Campaign HQC:** 797 157 $\to$ **1 279 660** ($f=0.05$), 418 166 $\to$ **665 605** (0.10), 302 382 $\to$ **471 801** (0.15) (`data.campaign_hqc`; the planner had expected about 663 000 at 0.10, planner arithmetic). In shots: 257 475 / 133 909 / 94 909 and 64 / 53 / 49 jobs (sum of sourced numbers, Block (g)). The $k=4\to5$ step moves $E_R$ by at most 0.68 $E_{\rm tol}$ at the plan's shots (0.0096 absolute at $B=0$, $f=0.10$), so a $k=5$ circuit (a family change) is **not** needed and that owner item disappears. The oracle-width table (Block (r)) is the report's statement of why the Weinstein width $\le0.1$ is out of reach at this family: at $B=0$ the oracle $S_{999}$ (86 states) has $W=0.99904$, $r_H=0.2647$, $\delta_{\rm KT}=0.0259$.

*What this does and does not say.* It is an emulation at a *presumed* clean fraction with the S1 proxy noise model, which Section 8 shows to be an optimistic proxy for real devices; the device number is unknown (Section 6.22). The plan is re-sized again at the measured $\hat f_{\rm ideal}$ before any campaign submission, and no HQC are committed. Stage E / Stage P (the two-reference pilots) test $f$ only: 2 000 shots, 9 949.92 eHQC (emulator) / HQC (hardware), USD 124 374 ESTIMATE at 12.5 USD per HQC (`validation/Q0P_2x3_plan.json -> data.stage_E_v3, stage_P_v3`).

### 6.20 2026-10-05/06: gate K0 and the first K1 attempt, stopped at 0 QPU s (`prompts/25` Part A, `prompts/27` stage 0b)

*K0 (model verdict).* `scripts/gate_K0_2x3_2x4.py` routes the signed 2x3 circuit `B0_ref25_k1` onto the target of a calibration record with an **exactness-gated seed rule**: the plain level-3 transpile with the fewest CZ (seed 6, 5 527 CZ) turned out *not exact* on this circuit (max $\lvert\Delta\psi\rvert=4.9\times10^{-5}$, leakage $2.7\times10^{-9}$; measured cause on qiskit 2.5.2: the level-3 loop's two-qubit peephole pass is not exact at approximation degree 1), so the chosen circuit is seed 7 with **5 659 CZ**, exact to $1.5\times10^{-12}$ (`validation/K0_2x3_2x4.json -> data.2x3.committed.routing`). (The 5 527-CZ figure in the 2026-10-05 report is the inexact circuit.) Committed record 2026-10-02: $f_{\rm ceiling,2q}=(1-\epsilon_{2,\min})^{n_{CZ}}=9.83\times10^{-3}$, gate-only on the routed layout $6.07\times10^{-6}$, idle-aware $1.06\times10^{-16}$ (echo $T_2$) and $3.73\times10^{-38}$ ($T_2^*/T_2^{\rm echo}=0.174$), $\epsilon_2$ needed for $f=0.05$ with nothing else wrong $5.29\times10^{-4}$ against the best edge $8.16\times10^{-4}$.

*K1 attempt.* Under the owner's K1 authorisation (cap 300 s) the executor built and rehearsed the pilot (circuits `B0_ref117_k1` / `B1_ref29_k1`, the two with the largest ideal reference probability 0.92836 / 0.92831), and then **stopped before any submission**: the live `ibm_kingston` target carried no CZ calibration at all (352 of 352 CZ keys without an error value, observed continuously from 21:49Z to 01:26Z, status `maintenance` from about 01:12Z), so the preconditions "gate K0 on the day's record" and the D9 fingerprint could not be met (`prompts/LOG.md` row 2026-10-05/06, commit `4227a94`). 0 QPU s were spent.

### 6.21 2026-10-06: option A, gate `H0_ddrep`: the XY4 gain did not replicate (`prompts/32`)

*Owner decision (verbatim, `data/owner_decision_20261006_A_then_B.md`):* "I want you to do A first, then when that is finished, do B because by that time it might be online". *A0:* the 2x3 IBM NO-GO was recorded as a **model verdict** from K0 in `reports/K0_2x3_ibm_heron_nogo.md` (generated from the JSON; every number a calibration-record computation, none a measurement; `data/K0_2x3_nogo.json`).

*The design (planner, `prompts/32`; arithmetic in `scratch/planner/ddrep_budget_20261006.json`).* One job on `ibm_kingston`, the same 12-qubit patch `[59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95]` (kept by rule P2: it ranked 2 of 750 on the day's record, $f_{\rm dd\,off}=0.0828$ against the winner's 0.0838), the two signed $k=1$ circuits, **seven cells**: T0 (no DD), T1 (context-aware staggered DD, the cell that had collapsed), T3 (client XY4 in windows $\ge1.024\ \mu$s, the adopted cell), and four mechanism cells built from T1/T2: **M1** = T1 with alternating pulse signs (same timing), **M2** = XX pairs in the 194 windows of T2, **M3** = M2 with alternating signs, **M4** = T1 minus all pulses on the two qubits that carry the most T1 pulses (91 and 95); plus four **pulse-train** pubs (XX-8, XX-32, XX-128, XpXm-128 on all 12 qubits) that measure the $x$ pulse's over-rotation $\epsilon_q$ and incoherent per-pulse cost $c_q$ directly. Three hypotheses were preregistered with a reading rule: $H_A$ coherent accumulation in uncompensated $X$ trains, $H_B$ the context-aware pass's output as such, $H_D$ a qubit-specific dense-drive cost on the hot qubits. Classes per cell on $R_i=X_i/X_0$ (excess reference hits over the garbage expectation): COLLAPSED iff the 95 % upper end $<0.25$, INTACT iff the lower end $>1$, else INTERMEDIATE. Replication verdicts: **R1** T3 qualifies under the H0_ddtest adoption rule ($R_{\rm lo}>1$ and $R\ge1.25$); **R2** $\lvert\ln R_{\rm new}-\ln2.819\rvert\le0.162$; **C1** T1 COLLAPSED. The planner wrote down its own expectation before the data: "T3 replicates (R about 2.8); T1 collapses again". Execution estimate 34.04 s, caps 36 s (estimator) / 45 s (billed); the reserve for part B (300 s) was checked first (498 - 45 = 453 s).

*Preconditions and the job.* Device watch 2026-10-06 06:02Z: `active`, 352/352 CZ errors published. Day's record 20261006T0501Z differs from the 2026-10-02 record in **1 110 calibration values** across the six families $T_1$, $T_2$, CZ error, measure error, $\sqrt{x}$ error, $x$ error (ratio of new to old between 0.102 and 111.3; `data/hardware/H0_ddrep_prep/live.json -> diff_against`). Preregistration committed before submission (commit `cd9ce12`), fingerprint `cb40a250fb24387d` at preregistration, submission and retrieval. Job **`db29p6nr11fs7396e4ig`**, 2026-10-06 07:00:40 UTC, 20 pubs x 6 000 shots, DD and twirling off, DONE, **billed 37.0 s** (estimate 34.04 s); account 498 s $\to$ 461 s left (`data/hardware/H0_ddrep_ibm_kingston/account_check_after_20261006T0703Z.json`). Readout minimum diagonal 0.9462.

*Results (95 % intervals; Block (o)).* No-DD baseline T0 $f=0.0818$ [0.0758, 0.0881] (716 reference hits, 2.93 from garbage) **against 0.0400 [0.0358, 0.0446] on 2026-10-02 for the very same QPY files**: a factor 2.04 (my division). T3 $f=0.0732$ [0.0675, 0.0792], $R_{T3}=0.895$ [0.804, 0.996] (2.819 [2.495, 3.185] on 10-02). T1 $0.0529$, $R=0.647$ [0.575, 0.727] (it collapsed to 0.012 on 10-02). M1 0.788 [0.706, 0.880], M2 0.806 [0.723, 0.900], M3 0.888 [0.798, 0.988] (all INTERMEDIATE), **M4 1.150 [1.040, 1.271] INTACT**, the only cell above the baseline. **R1 False, R2 False ($\ln R$: $-0.111$ against $1.036$, difference 1.148 against a tolerance 0.162), C1 False.** On T3 the signed bar reads NO-GO on $f_{\rm hit}$ and on $\hat f_{\rm ideal}=0.0656$ [0.0599, 0.0717] (information). *Mechanism:* matches per hypothesis $H_A$ 1/5, $H_B$ 0/5, $H_D$ 1/5, so the preregistered reading is **"no single hypothesis"**; M3 vs M2 gives $z=1.67$ (compensating the first-order timing effect may matter, marginal at one-sided 1.645). *Pulse trains:* the $x$ pulse over-rotates by $\epsilon_q=0.0148$ to $0.0204$ rad (68 % intervals a few $10^{-4}$ rad wide) on **all 12 qubits**; XX-128 minus XpXm-128 exceeds 0.05 on 12 of 12 qubits (the $H_A$ pattern is True); the incoherent per-pulse cost exceeds three times the record's `x_error` only on qubits 71 and 91 (the $H_D$ pattern, which wanted the hot qubits 91 and 95, is False). The calibration record cannot show this over-rotation: it aliases `x_error` to `sx_error` (the K0 record statistics give the same minimum $9.8\times10^{-5}$ for both), and the planner's RB-level estimate $\sqrt{6\,x_{\rm error}}$ (0.029-0.045 rad per qubit, Block (p)) is 1.5 to 3 times larger than the measured $\epsilon_q$. *Reading:* the 2026-10-02 gain and collapse were specific to that calibration; a coherent $x$ over-rotation is real but, with M1 INTERMEDIATE, does not by itself explain the collapse; and the device's baseline moved more between two days than any decoupling effect moved it within one.

### 6.22 2026-10-06: option B, the K1 2x3 pilot: a firm NO-GO (`prompts/32` part B, `prompts/27` stage 0b)

*Preconditions.* Device watch 07:21Z READY; account 461 s $\ge\max(300,\,1.3\times182.63)$ s; gate `K0_2x3_2x4 --live` PASS 6/6 on the day's record (fingerprint `b948ddc8`, content identical to the 05:01Z record that `H0_ddrep` used); circuits `B0_ref117_k1` / `B1_ref29_k1` rebuilt on that record (each 5 659 CZ, 21 active qubits, 411.2 / 410.8 $\mu$s, 2 408 / 2 404 XY4 pulses, exact to $1.6\times10^{-12}$ / $2.3\times10^{-12}$); preregistration (commit `f8df126`, calibration fingerprint `99035ef0`), dry run PASS 9/9, all preconditions held at submission.

*The job.* **`db2avbe8v0ts73c2i8b0`**, 2026-10-06 08:22:03 UTC, 4 pubs x $10^5$ shots (2 circuits + 2 readout pubs), DD and twirling off in the runtime options, cell T3 in the circuits, DONE, **billed 188.0 s** against an estimate of 182.63 s (1.029, my division; the preregistered expectation of billed time was 211.7-242.4 s); fingerprint equal at preregistration, submission and retrieval; account 461 s $\to$ **273 s** left. Readout minimum diagonal 0.9358 (qubit 92).

*Result (`validation/K1_2x3_fpilot.json`, Block (s)).* **Reference hits: 0 and 0**; the expectation from uniform garbage is $10^5\times2^{-20}=0.0954$ per circuit, 0.191 pooled. Accepted strings 58 (sector $B=0$) and 45 ($B=1$) of $10^5$ each, which is the garbage level (the exhaustive random acceptance gives about 64.6 and 40.6; `prompts/LOG.md`); the decoder re-encodes all 99 accepted strings with 0 mismatches. Pooled $f_{\rm hit}=-1.25\times10^{-6}$ (zero hits minus the garbage expectation; read it as zero), 95 % upper end $2.30\times10^{-5}$; $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ upper 95 % end **$2.06\times10^{-5}$** (per circuit $4.23\times10^{-5}$). The preregistered rule (GO-B $\ge10^{-3}$, GO-A $\ge3\times10^{-4}$, NO-GO below) reads **NO-GO, firm** (the point value and both interval ends agree). The upper bound is 14.6 times below the GO-A threshold and about 4 850 times below the signed bar 0.1 (my arithmetic).

*What it means.* (i) 2x3 on IBM Heron is now a **measured** NO-GO, not only a model verdict; the model's idle-aware ends predicted garbage only (0.0954 expected hits per circuit) and the data agree. (ii) The no-idle gate-only end of the preregistered bracket ($f=1.67\times10^{-5}$, 1.37 expected hits per circuit including garbage) is mildly disfavoured: a Poisson mean of 2.74 pooled gives P(0 hits) $\approx0.065$ (my arithmetic), so the data do not exclude it strongly. (iii) The correction $r_{nc}=1.115$ is a gate-noise value; under idle dephasing the A5 model gives $r<1$, so dividing by it can only lower the estimate and is conservative here. (iv) The report's honest limit: the XY4 cell this job carries did not replicate on the same morning's `H0_ddrep`, so the "XY4 transfer" ends of the bracket are not supported; the decision statistic $f_{\rm hit}$ does not use $R$. (v) Two circuits, one calibration content, one job: a pilot reading for this day, not a device constant.

### 6.23 Other items worth a line

- **Amendment 01 item 4 prerequisite work** (`data/S2D_2x3_device_requirements.json`, `reports/S2D_2x3_device_requirements.md`): requirement stated as the exact half-space $2158\,\tilde\epsilon_2+7310\,\tilde\epsilon_1+20\,\tilde\epsilon_{ro}\le\ln10$: $\epsilon_2\le7.094\times10^{-4}$ at the declared $\epsilon_1,\epsilon_{ro}$ ($9.066\times10^{-4}$ with virtual $R_z$); levers: connectivity spent, virtual $R_z$ and the fixed-angle generator (1 620 RZZ vs 2 158) unspent; the live `ibm_fez` gap: 3.31x in $\epsilon_2$ plus 2.53x routing.
- **Literature** (`reports/ibm_decoherence_literature_20261002.md`; `prompts/low_clean_fraction_techniques.md` read): client-side XY4 / context-aware DD arXiv:2403.06852, ZZ-robust DD arXiv:2506.18010 (equivalent to plain DD on tunable-coupler devices, consistent with T2 = T3 and making the T1 collapse more surprising), the random-baseline critiques arXiv:2608.11569 and arXiv:2605.23697.
- **Environment events:** the `coding` conda environment was repaired on 2026-10-02 (pinned stack qiskit 2.5.2, aer 0.17.2, runtime 0.49.0 re-verified; it reproduced every Stage T number exactly); a power failure interrupted the 2x4 work on 2026-09-30; laptop RAM rose to 62 GiB on 2026-09-30.

## 7. Hardware ledger

Sources: `data/hardware/*/session.json -> jobs[*].{job_id,usage_s,submitted,n_pubs,group_shots}` and `total_usage_s`; `data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json -> usage`; `reports/SESSION_HANDOVER_20260921_24.md`, `reports/SESSION_HANDOVER_20260925_1002.md`; `validation/H0_*.json`, `validation/H0_ddrep.json`, `validation/K1_2x3_fpilot.json`, `data/hardware/H0_ddrep_ibm_kingston/account_check_after_20261006T0703Z.json`, `data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json`. QPU seconds are the billed `usage` the IBM service reports per job. All real quantum jobs so far ran on **IBM Quantum (open plan, instance `open-instance`, 600 s of QPU time per rolling 28-day period)** on the 156-qubit Heron r2 devices `ibm_fez` and `ibm_kingston`. No job has been run on any other quantum computer.

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

| 13 | 2026-10-06 07:00:40 | ibm_kingston | `db29p6nr11fs7396e4ig` | H0_ddrep: 20 pubs x 6 000 | replication of the XY4 gain and the T1 collapse + four mechanism cells + four pulse-train pubs + 2 readout pubs on the 2x2 patch; options off | 37.0 | $R_{T3}=0.895$ [0.804, 0.996] (vs 2.819); T0 0.0818 (vs 0.0400); R1, R2, C1 all False; reading "no single hypothesis" (`validation/H0_ddrep.json`) |
| 14 | 2026-10-06 08:22:03 | ibm_kingston | `db2avbe8v0ts73c2i8b0` | K1: 4 pubs x 100 000 | the 2x3 pilot: two signed $k=1$ circuits (5 659 CZ, XY4 T3) + 2 readout pubs; options off | 188.0 | 0 reference hits in $2\times10^5$ shots vs 0.191 from garbage; $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %): **NO-GO, firm** (`validation/K1_2x3_fpilot.json`) |

(Circuit composition of rows 8-12 is from `data/hardware/H0_2x2_ibm_kingston/session.json -> jobs[*].circuit_ids`: 28 coarse circuits = 14 + 7 at the 267-shot floor plus 5 + 2 $k=4$ circuits at $N_4$, and 2 readout pubs at 4 000 shots.)

### 7.2 Totals and budget

| quantity | value | source |
|---|---|---|
| ibm_fez, 2026-09-22 (canary + diagnostic) | 2.0 + 15.0 = **17.0 s** | `session.json -> total_usage_s` (canary 2.0; J1-J4 5.0+4.0+3.0+3.0) |
| ibm_kingston, 2026-10-02 (pilot + DD test + full run) | 12.0 + 20.0 + 53.0 = **85.0 s** | `session.json` files (pilot 12.0; ddtest 20.0; H0_2x2 3+3+4+22+21 = 53.0) |
| ibm_kingston, 2026-10-06 (DD replication + 2x3 pilot) | 37.0 + 188.0 = **225.0 s** | `data/hardware/H0_ddrep_ibm_kingston/session.json`, `data/hardware/K1_2x3_ibm_kingston/session.json -> total_usage_s` |
| ibm_kingston, all days | 85.0 + 225.0 = **310.0 s** (sum of sourced numbers) | the three lines above |
| **total QPU time used** | 17.0 + 85.0 + 225.0 = **327.0 s** (sum of sourced numbers) | the account counter after the last retrieval: `usage_consumed_seconds` **327** (`data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json`) |
| plan allowance | 600 s per period (`usage_limit_seconds` 600); the period is a rolling window whose `start_time` / `end_time` move with the check (at the last check 2026-09-08T08:26Z to 2026-10-06T08:26Z) | same file |
| **remaining** | **273 s** (`usage_remaining_seconds` 273) | same file |
| number of real jobs | 14 (1 canary + 4 diagnostic + 1 pilot + 1 ddtest + 5 full-run + 1 ddrep + 1 K1) | `session.json` files |
| estimate-to-billed ratio | full 2x2 run 41.7 s estimated vs 53.0 s billed (1.27; planner arithmetic from the report); `H0_ddrep` 34.04 s vs 37.0 s (1.087, my division); K1 182.63 s vs 188.0 s (1.029, my division) | `reports/H0_2x2_full_hardware_report_20261002.md` section 5; `validation/H0_ddrep.json -> data.live`; `validation/K1_2x3_fpilot.json -> data.live` |
| throughput | `H0_ddrep` 120 000 shots in 37.0 s = 3 243 shots/s; K1 400 000 shots in 188.0 s = 2 128 shots/s (both my division; K1's circuits are 411 $\mu$s long, 2x2's 44 $\mu$s) | the two sessions |
| the 400 IBM minutes | requested allocation **not yet visible** to the account (only `open-instance` is) as of `reports/SESSION_HANDOVER_20260925_1002.md` section 1; nothing newer in the repository | that file |
| authorised next spend | **none**: the K1 authorisation (cap 300 s) was used (188.0 s); the owner's decision of 2026-10-06 covered A and B only; the 273 s are unallocated | `data/owner_decision_20261005_k1_2x3_fpilot.md`, `data/owner_decision_20261006_A_then_B.md` |

Note on the budget history: the owner's "600 second budget" and the plan numbers quoted at various times (583 s left after the fez work, 571 s after the kingston pilot, 551 s after the DD test, 498 s after the full run, 461 s after `H0_ddrep`, 273 s after K1) are the account counter at those moments (`data/hardware/*/account_check*.json`: consumed 17, 29, 49, 102, 139, 327 s). My inference, not verified in a file: because the period is a rolling 28-day window, the 17.0 s spent on `ibm_fez` on 2026-09-22 would leave the window on about 2026-10-20 and the 273 s would then become about 290 s.

### 7.3 Everything else that cost compute (no QPU time)

| resource | job / run | cost | source |
|---|---|---|---|
| Perlmutter A100 (CI) | smoke job 58717267 | pass | `validation/ci_smoke.json` |
| Perlmutter A100 (CI) | L4 job 58737320 (crashed, OOM) | 608 s | `prompts/LOG.md` |
| Perlmutter A100 (CI) | L4 job 58741899 (PASS) | 686 s | `validation/ci_gate_L4.json` |
| Perlmutter A100 (CI) | S3 calibration job 58771538 (PASS) | 255 s | `validation/ci_gate_S3.json` |
| Perlmutter A100 (CI) | S2_2x4 job 59162991 (PASS) | 99 s | `validation/ci_gate_S2_2x4.json` |
| Quantinuum (HQC / eHQC) | none: no Nexus account, no allocation | **0 HQC, 0 eHQC** | `prompts/LOG.md` row prompts/26 Stage A |
| IonQ (Braket / Azure) | none | **0 USD** | `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` |
| laptop | the longest gate runs: S2 436 s; H0P 1 179 s; H0P_repro 1 741 s; CF_traj 1 201 s; Q0P_2x3_plan 781 s; CV_2x3_plan 679 s; K0_2x3_2x4 943 s (includes the test suite); the K1 circuit builds took 1 223 s and 1 250 s each (`prompts/LOG.md`); the H0_ddrep dry run sampling 1 738 s | within the 30-minute rule | `validation/*.json -> runtime_s` |

### 7.4 What the hardware ledger says

- 14 jobs used 327 s: 17 s on `ibm_fez` (two failures to reach the planned run: a NO-GO and a diagnosis) and 310 s on `ibm_kingston` (one NO-GO, one adopted mitigation that did not replicate, one full 2x2 run, one replication and one 2x3 pilot that ended in a firm NO-GO).
- 53 of the 327 s (16 %, my division) bought the only full SKQD run on hardware, at 2x2; 188 of 327 s (57 %, my division) bought a measurement of a null (no 2x3 reference hit).
- The cost structure: the per-job billing floor is about 2-2.5 s regardless of shots (`SESSION_HANDOVER_20260921_24.md` section 4), so a session of many small jobs is job-count dominated; long circuits are shot-rate dominated (2 128 shots/s for the 411 $\mu$s 2x3 circuits against 3 243 shots/s for the 44 $\mu$s 2x2 circuits).
- Next planned spend: **none on IBM**. What to do with the 273 s is an open owner question (Section 9.6); Quantinuum emulator / pilot (about 9 950 eHQC / 9 950 HQC) pending access.

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
9. **Runtime XY4 plus Pauli twirling did not help on fez; client-side XY4 restricted to windows of at least 1 $\mu$s helped by about 2.8x on kingston; staggered context-aware DD collapsed.** Same-job ratios (95 %): T2 2.793 [2.472, 3.157], T3 2.819 [2.495, 3.185], T1 0.012 [0.004, 0.031] against pulse-cost nulls 0.841 / 0.944 / 0.816 (`validation/H0_ddtest.json -> data.decision.cells`). Twirling cannot raise a clean fraction (it preserves average error, arXiv:1512.01098). The context-aware collapse is unexplained; the planner notes that arXiv:2506.18010 predicts little difference between staggered and plain DD on tunable-coupler devices, which makes the collapse more surprising. One job, one patch, one calibration content: **not a replicated result**, and the replication of 2026-10-06 (gate `H0_ddrep`, lesson 29) **failed**: $R_{T3}=0.895$ [0.804, 0.996], the baseline doubled, the context-aware cell was no longer collapsed ($R_{T1}=0.647$). Read this item as the record of what one calibration showed, not as a finding about XY4 on this device.
10. **Patch selection and scheduling are first-order levers but not rescues**: the idle-aware patch rule was worth 1.41x on the record that flew and 3.31x device-wide on fez; ALAP with explicit delays cut the scheduled duration to 0.710x (`validation/S2D_levers.json -> data.verdict.duration_ratio_best`); the exact family is kept because the fixed-angle generator is 3.7 % *longer* in time though 2.2 % shallower in depth. Neither alone reaches the bar; with client XY4 on the kingston patch the $k=1$ circuits reached $f\approx0.11$-$0.13$ on the reference-hit statistic **on 2026-10-02 only**: on 2026-10-06 the same circuits gave 0.0732 [0.0675, 0.0792] with XY4 and 0.0818 [0.0758, 0.0881] without (lesson 28), below the bar either way.
11. **Superconducting devices cannot run 2x3 or 2x4 of this family.** 2x3 routes to 5 477 CZ; even at the record's best edge error $8.164\times10^{-4}$ on every gate the ceiling is $f\le1.14\times10^{-2}$ (K0 verdict); 2x4 needs $T_2/t_{2q}=638\,742$ against Heron's 1 038. Dynamical decoupling removes only idle error, so it cannot change that. **Since 2026-10-06 this is a measurement and not only a model verdict** (lesson 31): the K1 pilot saw no reference hit in $2\times10^5$ shots, upper 95 % bound $2.06\times10^{-5}$ on $\hat f_{\rm ideal}$. (The 5 477-CZ figure in this item is the planner's survey value; the exactness-gated route that K0 and K1 actually use is 5 659 CZ, Section 6.20.)
12. **IonQ Forte-class machines cannot run 2x3 either** (gate-only $f=8.6\times10^{-5}$; the circuit is 2 158 serial two-qubit gates at 950 $\mu$s each); only Quantinuum's QCCD machines meet the signed gate-error bar on published numbers (H2-2 0.150, Helios-1 0.164, H1-1 0.111), with the transport (memory) error unknown and decisive. Error correction is a 2029-class option; detection codes are a net loss (planner, `reports/2x3_qec_amplification_strategy_20261002.md`).
13. **The calibration-content fingerprint behaves.** It stayed constant through three stamp-only updates on 2026-09-22 and fired on the one real recalibration; on kingston it was `84d59cbf9b5973d1` throughout 2026-10-02. Readout on the kingston patch: min diagonal 0.9417 against the live expectation 0.9525; survival product 0.8338 against the manual's design 0.82 (`validation/H0_2x2.json -> data.readout`).

### 8.3 Statistics and the meaning of "clean"

14. **Accepted shots are not clean shots.** The decoder accepts near-clean strings at a rate comparable to pure noise; on fez 13 of 35 accepted strings were distance-2 codewords of ideal probability 0. The yield inversion of the manual's Step 4.4 overstated the clean fraction by a factor 15 (0.0101 vs $6.65\times10^{-4}$; `validation/H0_model.json -> data.C2_pooled_device_clean_count`). Simulated Aer shows the same effect (34-42 % of accepted shots on the FakeFez snapshot), so it needed no hardware to find and was derivable from the exhaustive decoder enumeration of gate E2 (owner-approved rule M4.4).
15. **The right measurement is the reference-string statistic** ($f_{\rm hit}$), cross-checked by the mixture estimator; the C6 ruling scoped their agreement to circuits whose reference probability is at least 0.5 (at low $p_{\rm ref}$ the two estimators use nearly disjoint information, combined relative sigma 0.172).
16. **$f_{\rm hit}$ estimates the ideal-sample fraction, not the fault-free fraction.** The Pauli-trajectory decomposition (CF_traj, PASS 7/7) shows the shots that return to the reference are single phase-type events that do not change the measured string, most of them sampling the ideal distribution exactly; $r_{nc}=f_{\rm hit}/f_{\rm ideal}=1.115$ (upper 95 % end; `data/cf_trajectories/r_nc.json`). The first candidate statistic ($f_T$, tail-class fraction) was withdrawn because noise *scatters* shots into low-probability states and inflates it 21-39x. Consequence for 2x2: under the conservative correction the "signed bar GO" reads **AMBIGUOUS** (0.103 with lower 95 % bound 0.096, planner arithmetic at $r_{nc}=1.10$; owner decision 3a). Under idle dephasing at 2x2 the reference-hit fraction *under*-estimates $f_{\rm ideal}$ in the A5 model ($r=0.674$ and $0.902$ at the two $T_2$ ends), so the correction is not one-directional.
17. **The floor theorem** (CF_traj): the effective clean rate of every $S_{99}$ state is at least $f_{\rm ideal}(1-2\delta/p_c)$; measured minima 1.089 / 1.040 / 1.100 / 1.041 of $f_{\rm ideal}$ on the four arms, so sizing on $f_{\rm ideal}$ is safe by construction.
18. **At $k=4$ the mixture estimator overstates $f_{\rm ideal}$ by 27 %** (bias 1.274 [1.170, 1.402]).
19. **Rule D3' is not a finite plan at 2x3** ($N_4\sim8.8\times10^{35}$ at $f=0.1$ because 32 of 677 and 11 of 426 states have total $k=4$ probability below $10^{-6}$), and was measuring the wrong set: none of those states is in the 99.9 % support. The replacement D3'-R (31 / 42 states of $S_{99}$ at $\lambda^*$, then recall of $S_{999}\ge0.9$ with probability $\ge0.95$) cost 418 166 HQC at $f=0.10$ as a base plan (reproduced by gate `Q0P_2x3_plan` P1); after the convergence check doubled sector $B=1$ the plan of record costs **665 605 HQC** at $f=0.10$ (`validation/CV_2x3_plan.json -> data.campaign_hqc`).
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

### 8.6 Lessons added on 2026-10-06

28. **Day-to-day calibration variation is larger than the dynamical-decoupling effects.** On the 2026-10-02 calibration the frozen no-DD circuits gave a pooled clean fraction 0.0400 [0.0358, 0.0446]; on the 2026-10-06 calibration the *same QPY files* on the *same patch* gave 0.0818 [0.0758, 0.0881], a factor 2.04 (my division; `validation/H0_ddtest.json`, `validation/H0_ddrep.json -> data.cells.T0`). Between the two days 1 110 values of the calibration record changed (the six families $T_1$, $T_2$, CZ error, measure error, $\sqrt{x}$ error, $x$ error), by factors from 0.102 to 111.3, and the patch's calibration fingerprint changed (`84d59cbf9b5973d1` $\to$ `cb40a250fb24387d`). The largest same-day DD effects of 2026-10-06 are ratios 0.647 (T1) to 1.150 (M4); the 2026-10-02 XY4 gain (2.819) is about the size of the day-to-day change of the baseline itself. A one-day A/B test cannot separate a mitigation from the calibration it ran on; a baseline (T0) must be in every job, as it was.
29. **The XY4 non-replication.** Gate `H0_ddrep` (preregistered, same QPYs for T0/T1/T3): R1 False (T3 no longer qualifies: $R_{T3}=0.895$ [0.804, 0.996], its 95 % interval excludes 1 from *above*), R2 False, C1 False (T1 not collapsed). Consequences: the 2x2 "signed bar GO" of 2026-10-02 was a one-day result (and on 2026-10-06 T3 reads NO-GO on both $f_{\rm hit}$ and $\hat f_{\rm ideal}=0.0656$ [0.0599, 0.0717]); the XY4 technical note is not supported as written (Section 9.5); the "XY4 transfer" columns of the K0 and K1 predictions rest on an $R$ that did not hold. Honest limits: one job, one patch, one calibration content per day; the planner's preregistered expectation ("T3 replicates; T1 collapses again") was wrong on both counts, which is the reason the test was run.
30. **The calibration record cannot see the $x$ pulse.** The record aliases `x_error` to `sx_error` (both minima $9.8\times10^{-5}$ in `validation/K0_2x3_2x4.json`), and the pulse-train pubs of `H0_ddrep` show a coherent over-rotation $\epsilon_q=0.0148$-$0.0204$ rad on all 12 patch qubits (XX-128 minus XpXm-128 above 0.05 on 12 of 12), about 1.5-3 times smaller than the RB-level estimate $\sqrt{6\,x_{\rm error}}$ (0.029-0.045 rad). Any decoupling sequence that applies the same $x$ pulse many times accumulates this coherent error: XX-128 reached $P_1=0.76$-0.98. Whether it explains the collapse is open (M1 INTERMEDIATE; the reading is "no single hypothesis"); the incoherent per-pulse cost exceeds three times the record's `x_error` only on qubits 71 and 91 (the $H_D$ pattern wanted 91 and 95, so it is False), while M4, the cell that removes the pulses on 91 and 95, is the one INTACT cell.
31. **2x3 on IBM Heron is a measured NO-GO.** K0's model verdict (idle-aware $f\sim10^{-16}$ on a 5 659-CZ, 411 $\mu$s circuit) was tested by K1: 0 reference hits in $2\times10^5$ shots, accepted strings at the garbage level, $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %), firm NO-GO against a GO-A threshold of $3\times10^{-4}$. The measurement removes the last IBM-side uncertainty about 2x3; the remaining device route in the repository's survey is Quantinuum. For scale, K0 puts the two-qubit error needed for $f=0.05$ on this routed circuit at $\epsilon_2=5.3\times10^{-4}$ with nothing else wrong, against the best calibrated edge $8.2\times10^{-4}$ (and that is only the two-qubit ceiling).
32. **The plan check changed the cost, not the plan's shape.** The emulation showed that the certificate widths, not the shot counts, set the cost: Weinstein width $\le0.1$ is out of reach for any affordable support (oracle $S_{999}$ has $r_H=0.265$ at $B=0$), Kato-Temple with the exact $E_1$ is met at $s=1$, and sector $B=1$ needs twice the shots for $r_H\le0.15$. The campaign minimum rose from 418 166 to 665 605 HQC at $f=0.10$ (+59 %, my division). Two planner criteria had to be corrected after a failed first run (width read on the wrong basis and wrong certificate; CV3 on the wrong step); the corrections were rulings with the owner's confirmation, not tolerance changes.
33. **A readiness check must test what the experiment needs.** On the night of 2026-10-05/06 `ibm_kingston` reported `operational` while in maintenance and publishing no two-qubit calibration; the project's device watch therefore requires status `active` and every CZ error present. The first K1 attempt stopped at 0 QPU s for that reason, and the order of the owner's decision (A, then B) made use of the wait.

## 9. Where we are now and where we are heading

Sources: `CLAUDE.md` status paragraph, `reports/SESSION_HANDOVER_20260925_1002.md`, `prompts/27`-`32`, `data/owner_decision_20261005_*.md`, `data/owner_decision_20261006_A_then_B.md`, `proposal/quantinuum_access_request_draft_20261005.md`, `reports/H0_2x2_full_hardware_report_20261002.md` section 6, `reports/qpu_survey_2x3_20261002.md`, `reports/H0_ddrep_ibm_kingston.md`, `reports/K1_2x3_fpilot.md`, `prompts/LOG.md`. State of the repository on 2026-10-06: branch `master`, level with `origin/master` (`git status -sb`), HEAD at the start of writing `9444b8c`.

### 9.1 One-paragraph state of every track

- **Physics core (E1-E3, S1, CS):** done and reproduced on cloud and laptop (all PASS).
- **Circuit layer:** exact structured circuits verified at 2x2, 2x3 and 2x4 (S2, S2_2x4 PASS); native-gate versions of the 44 2x3 circuits frozen for Quantinuum (Q0P_2x3 PASS); the routed IBM version of the 2x3 circuit (5 659 CZ, exact to $1.5\times10^{-12}$) built for K0 / K1.
- **2x2 hardware:** the full SKQD run is done (H0_2x2 PASS, 53.0 s). The campaign is *closeable*; the report's verdict is "methods note, not an SKQD physics result". The DD follow-up (option A of the owner's 2026-10-06 decision) is done: **the XY4 gain did not replicate**, so there is no 2x2 mitigation result left to publish.
- **2x3 hardware:** one job exists and it is a **measured NO-GO on IBM** (K1: 0 reference hits in $2\times10^5$ shots; $\hat f_{\rm ideal}\le2.06\times10^{-5}$). The only device class that meets the signed gate-error bar on published numbers is Quantinuum H2-2 / Helios-1; access is not yet requested (draft only).
- **2x4:** compiled, verified, requirement measured; no device can run it (requirement $T_2/t_{2q}=638\,742$).
- **Neural / ML step:** only the minimal ridge ranker, only on exact amplitudes (S1). Not applied to any hardware data.
- **Classical statistics machinery for the 2x3 plan:** complete. D3'-R signed as the minimum sizing (2a); $f_{\rm ideal}$ referent and $r_{nc}=1.115$ signed (1a); CF_traj PASS; the convergence / coverage / certificate check `CV_2x3_plan` PASS 37/37 with $B=1$ doubled (owner-approved plan of record: 1 279 660 / 665 605 / 471 801 HQC at $f=0.05/0.10/0.15$); `Q0P_2x3_plan` PASS 7/7. No HQC committed.

### 9.2 Work completed since the previous report (nothing is in progress)

All items that the previous report listed as work in progress finished and are committed: the K1 pilot (Section 6.22, NO-GO), `prompts/29` Part B' and `prompts/30` (Section 6.19, with the `prompts/31` corrections), and the K0 gate (Section 6.20, PASS 6/6 on 2026-10-06). The working tree is clean except for one untracked, empty-counts directory (`data/hardware/H0_ddrep_dryrun_prototype/`; the owner may delete it). Two small housekeeping items recorded in `prompts/LOG.md`: `scripts/update_status.py` does not register `K0_2x3_2x4` in `validation/gates.md`, and `validation/BLOCKED.md` (gitignored) is stale.

**Not done although proposed in `prompts/27`:** Stage 0 (`T0_2x3_tiers`), Stage 0c (`T0c_levers`: no-plaq1, fixed-angle + no-plaq1, truncated multiplexed rotations, SqDRIFT-style random products) and Stage 1 (`S3H_2x3`, Helios-class device model on the GPU, needs a CI token): no gate JSON exists for any of them.

### 9.3 The Quantinuum route (the only device route that reaches the signed bar)

Facts (all `reports/qpu_survey_2x3_20261002.md`, `data/quantinuum/devices_20261002.json`; vendor numbers were read on 2026-10-02, none measured by this project):

| device | qubits | 2q error | gate-only $f$ (2x3) | $f$ with memory (low / mid / high, ESTIMATE) | HQC per full D3-type campaign (ESTIMATE) |
|---|---|---|---|---|---|
| H2-2 | 56 | $8.3\times10^{-4}$ | **0.1502** | 0.1454 / 0.1398 / 0.1130 | 507 144 (102 100 shots, 60.1 machine-hours at the mid scenario) |
| Helios-1 | 98 | $7.9\times10^{-4}$ | **0.1642** | 0.1378 / 0.1117 / 0.0352 | 634 299 |
| H1-1 | 20 | $9.7\times10^{-4}$ | 0.1113 | 0.1049 / 0.0977 / 0.0661 | 725 197 |
| H2-1 | 56 | $1.1\times10^{-3}$ | 0.0860 | 0.0815 / 0.0764 / 0.0535 | 927 358 |

The memory (transport) error of a 20-qubit, mostly serial, 1 925-two-qubit-layer program is *unknown* (three ESTIMATE scenarios); the vendor emulator (H2-2E) carries the real transport schedule and replaces it.

**The staged plan** (after `prompts/26`, `28`, `29`, `31`; decision 2a signs the minimum sizing, the decision of 2026-10-05 approves the $B=1$ doubling, no HQC committed):
- **Stage E (emulator H2-2E):** two $k=1$ circuits at 800 shots and two $k=4$ circuits at 200 shots: **9 949.92 eHQC** (gate-computed: `validation/Q0P_2x3_plan.json -> data.stage_E_v3.hqc_total`, 4 jobs, 2 000 shots; v1 was 11 936 eHQC). Read $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ with GO rule v3: GO iff lower 95 % $\ge0.05$ and point $\ge0.10$; NO-GO iff upper 95 % $<0.10$; AMBIGUOUS otherwise (one top-up).
- **Stage P (hardware pilot on H2-2):** the same four circuits and shots, **9 949.92 HQC** (USD 124 374 ESTIMATE at 12.5 USD per HQC).
- **Campaign (plan of record, gate `CV_2x3_plan` / `Q0P_2x3_plan`; Appendix block (g)):** rule D3'-R with sector $B=0$ at $s=1$ and $B=1$ at $s=2$, sized at $\hat f_{\rm ideal}$ and re-sized at the measured value before any submission. At $f=0.10$: **133 909 shots, 53 jobs, 665 605 HQC**, about 78.8 machine-hours at the mid memory scenario and an Azure-Standard-equivalent 8.32e6 USD at 12.5 USD per HQC (ESTIMATE: the pay-as-you-go and research rates are not public; the hours and USD are sums of the per-sector ESTIMATE fields in `validation/CV_2x3_plan.json -> data.plan`, my addition); at $f=0.05$: 257 475 shots, **1 279 660 HQC** (151.4 machine-hours); at $f=0.15$: 94 909 shots, **471 801 HQC** (55.8 machine-hours). For comparison the un-doubled base plan was 418 166 HQC at $f=0.10$. The convergence condition (decision 2a) is met; the factor $s=2$ at $B=1$ is the whole of the re-sizing, and no further multiple is expected unless the measured $f$ differs. Commercial purchase is not realistic (the only published rate is the Azure Standard plan: 125 000 USD per month for 10 000 HQC); the realistic routes are a QCUP allocation or a research agreement.
- **Access (not yet requested):** the drafted email to Sales@Quantinuum.com (route B; also the project summary for QCUP, route A). QCUP: default hardware quota 0 HQC, emulator quota 6 000 s, requests must be justified by emulator results; eligibility ("US national labs, universities, government, and industry") to be confirmed by the owner. Helios-1 needs a Guppy/HUGR program (Stage A9 not built).

*My reading (not a project statement):* every Quantinuum number above is a vendor-published or planner-estimated *prediction*; the project's one device-versus-model comparison on IBM missed by a factor of about 330 before idle dephasing was included and, on 2026-10-06, the same circuits' clean fraction moved by a factor of 2 between days, so the first emulator stage (Stage E, which carries the vendor's real transport schedule) is the first informative number for 2x3 on this route and should be read before any larger budget is discussed.

### 9.4 IonQ and 2x4

- **IonQ:** no accessible IonQ device can run 2x3 (Forte / Forte Enterprise gate-only $f=8.6\times10^{-5}$; Aria retired; Tempo is a projection whose 99.9 % target gives $f\approx0.077$, below 0.1). 2x2 on Forte Enterprise is feasible (gate-only $f=0.303$), costing about 5-20 kUSD at Braket rates (`reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` section 4.4); it would be a cross-platform check only. No IonQ submission tooling exists (Section 4.2).
- **2x4:** compiled and verified; on a Heron device the gate-only ceiling is $\sim10^{-53}$; the all-to-all circuit needs 69 688 CZ and $T_2/t_{2q}=638\,742$; IonQ's job limit (150 000 gates) is below the 208 399 native gates. No action planned (`prompts/27` D7: defer).

### 9.5 Publishability

*Source: `reports/H0_2x2_full_hardware_report_20261002.md` section 6 (planner, written 2026-10-02, with the field survey of arXiv abstracts fetched that day), updated here for the results of 2026-10-06 (`validation/H0_ddrep.json`, `validation/K1_2x3_fpilot.json`). The planner has not rewritten its section 6 after the replication; the updates below are my reading of the new gate results and are marked as such.*

- **Today's 2x2 result can claim:** a validated, preregistered, end-to-end SKQD pipeline for a 2+1D SU(2) gauge theory with staggered quarks on a Heron processor (intertwiner-labelled basis, Gauss-law decoder with 0 mismatches over 58 hardware strings in the full run and 0 over 58 and 99 strings in the two 2026-10-06 jobs, exact structured circuits, ALAP, a calibration-content guard, certified Ritz energies with their controls); a signal support of 35/38 and 19/20 states; a quantified statement of why the all-state energies carry no device information; and measured clean fractions on 12-qubit, 588-CZ, 44 $\mu$s circuits **with their dates**: on 2026-10-02 0.0413 [0.0361, 0.0470] without decoupling and 0.1271 [0.1084, 0.1479] in the full run with client XY4; on 2026-10-06 0.0818 [0.0758, 0.0881] without decoupling and 0.0732 [0.0675, 0.0792] with XY4, on the same frozen circuits and patch. **Caveats that must travel with the 2x2 signed-bar statement:** (a) it was a GO on $f_{\rm hit}$ under the preregistered rule and reads AMBIGUOUS on $\hat f_{\rm ideal}=f_{\rm hit}/r_{nc}$ (adopted cell 0.1012 [0.0938, 0.1091], `validation/CF_estimator_2x2_info.json`; decision 3a; the idle-dephasing correction on `ibm_kingston` is unmeasured and the A5 model bracket has $r=0.67$-$0.90$); (b) **it is a one-day result**: four days later the same cell read NO-GO (0.0732 on $f_{\rm hit}$, 0.0656 [0.0599, 0.0717] on $\hat f_{\rm ideal}$), and the baseline itself moved by a factor 2.04 (my division), so the "day-to-day caveat" is part of the claim; (c) the wording in `prompts/31` ruling 6 is the planner's proposed external text.
- **It cannot claim:** an SKQD accuracy result (saturation), a device-support-quality result (recall 1.0 is reached by noise alone; no CIPSI control on hardware data), a claim about the circuit family's clean fraction (the bar was read on $k=1$ circuits only), **a dynamical-decoupling gain (it did not replicate)**, "neural-enhanced", or any physics number beyond reproduction of known exact values.
- **Verdict (planner, 2026-10-02, with my update):** publishable as (a) a methods / technical note on running sample-based diagonalization honestly at a size where noise saturates the subspace (clean-fraction estimators, near-clean term, saturation rule, signal-support definition, garbage/random baselines, the 2x2 run as worked example). The planner's option (b), **a short note on client-side XY4 raising the clean fraction 2.8x on a Heron r2, is no longer supported as written**: its precondition ("after replication") failed. *My reading:* what the replication adds that can be written honestly is a negative-result section for the methods note: the same-circuit baseline varied by 2.04x between two calibrations, a one-job A/B test cannot be trusted across days, a coherent $x$-pulse over-rotation of 0.015-0.020 rad exists on all 12 qubits and is invisible in the calibration record, and 2x3 on IBM Heron has a measured upper limit $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %). Not publishable as an SKQD result for SU(2) lattice gauge theory.
- **Context:** "first SU(2) with dynamical matter on hardware" is not available as a claim (arXiv:2102.08920, 2021; arXiv:2602.18080, 2026); the manual's own claim is the 2x3 result "first quantum-centric spectroscopy of a non-Abelian gauge theory with dynamical matter in two spatial dimensions".
- **What a publishable physics claim needs, in the plan's order:** (1) a lattice where noise cannot saturate the sector: at 2x3 the saturation parameter is $2\times10^5\times0.00146/677=0.43$ at most (planner arithmetic, upper bound), which needs a 2x3 device, **and IBM Heron is now measured not to be one**; (2) the primary endpoint P1, device vs CIPSI at equal $|B|$ with bootstrap bands over circuits, on that lattice; (3) the clean fraction measured on the whole circuit family ($k=2..4$); (4) repeat runs (second calibration window, patch, device; 2026-10-06 shows why: the repeat is where a one-day result fails); (5) the ML step credited or nulled under Step 7.5 on hardware data; (6) the release bundle (raw bit strings, calibration records, circuits, decoder).
- **Claim tiers for the first 2x3 hardware run** (`prompts/27`, evaluated per sector on $B_{\rm sig}$ with references always included; since `prompts/31` the 2x3 certificates and convergence criteria are read on $B_{\rm all}\cup$ references, the tier definitions below are as `prompts/27` wrote them): **Tier A** $|B_{\rm sig}|\ge40$; $E_R(B_{\rm sig})-E_0$ below the 2.5th percentile of 200 random equal-size bases (bands not overlapping); $\le1.5\times$ the BFS error at equal size; $E_0$ in the Weinstein interval. **Tier B** Tier A plus recall of the 99.9 % support $\ge0.8$ (gate H1), gap-assumed certified width $\le0.1$ containing $E_0$ (H1; now the Kato-Temple reading with the exact $E_1$), cluster energy certified to $\pm r_H\le0.15$ at $B=1$ (H2). **Tier C** Tier B plus $|B_{\rm sig}|\ge300$ and device error $\le0.5\times$ the BFS error at equal size. Thresholds are preregistered and may not be tuned to the outcome. The planner's proxy emulation (prototype, 2026-10-02, not a gate) suggests that with $f\approx0.17$ and $2\times10^5$ shots per sector $|B_{\rm sig}|=200$, $E_R(B_{\rm sig})-E_0=1.5037\times10^{-3}$, recall 0.988 (`prompts/27` T0.1).

### 9.6 Open owner decisions (numbered; as of 2026-10-06)

Decisions that were open on 2026-10-05 and are **now made** are not listed; they are recorded in Section 3.4 (K1 execution and its cap; Part B' 1a / 2a / 3a; Kato-Temple at $B=0$; the $B=1$ doubling; the 2x2 DD replication and the K1 order; the re-sizing multiple; the $k=5$ question, which disappeared because CV3 holds; pushing, because `master` is level with `origin`).

1. **Send the Quantinuum access request.** The draft `proposal/quantinuum_access_request_draft_20261005.md` (route A, the OLCF Quantum Computing User Program; route B, Sales@Quantinuum.com for a research agreement with Nexus access) is unsent; the owner edits and sends it, and confirms eligibility for route A. This is now the only path to any 2x3 hardware data.
2. **The Stage E and Stage P budgets** (separate written decisions; signing 2a and the $B=1$ doubling committed none): Stage E on the vendor emulator H2-2E, 9 949.92 eHQC (4 jobs, 2 000 shots); Stage P on H2-2, 9 949.92 HQC (USD 124 374 ESTIMATE).
3. **Approval of a full 2x3 campaign** once Stage P has measured $\hat f_{\rm ideal}$: plan of record 665 605 HQC at $f=0.10$ (133 909 shots, 53 jobs), 1 279 660 at 0.05, 471 801 at 0.15, re-sized at the measured $f$ before submission. Needs access (item 1) and a budget; Section 9.3 gives the realistic routes. **Gap I found:** the plan of record covers sectors $B=0$ and $B=1$ only; the static-charge sectors of the manual's Step 9.2 (static pair $r=1$, $r=2$) have no shot plan anywhere in `validation/Q0P_2x3_plan.json` (no "static" string in it).
4. **IonQ 2x2.** Whether to run 2x2 on Forte Enterprise as a cross-platform check (5-20 kUSD at Braket rates, planner estimate) and what to ask IonQ (measured Tempo two-qubit error, gate time, $T_2$, parallelism, raw bit strings with debiasing off). No IonQ submission tooling exists.
5. **What to do with the 273 s left on the IBM open plan.** The owner's 2026-10-06 decision covered options A and B only, and both are spent. No file proposes a further spend. Facts for the decision: a 2x3 run on IBM is a measured NO-GO, so any use is 2x2; 2x2 already has its full run; the replication showed that a single-day, single-job comparison on IBM is not reliable (a new 2x2 job would need its own T0 baseline in the same job, as `H0_ddrep` had); `H0_ddrep` cost 37.0 s; nothing prevents leaving the seconds unspent.
6. **The 400 IBM minutes** (allocation awaiting approval; not visible to the account as of the last handover). If it arrives it does not change the 2x3 verdict on IBM.
7. **Perlmutter CI tokens:** `S3H` for the Helios-class device-model stage (`prompts/27` D2), a token for the 2x4 native-gate verification, and the production S3 job (2x3 recall criterion; 4.4 h for four sectors, but the criterion is not a hardware criterion until the corrected model is in).
8. **The publishability route** (Section 9.5): whether to write the methods note now; whether it carries the replication, the baseline variation and the K1 upper limit as a negative-result section (my suggestion); the status of the XY4 note (not supported as written); and the exact wording of the 2x2 qualification for external text (`prompts/31` ruling 6; the log lists it as an owner item; I found no owner file that confirms the wording, only decision 3a, which accepts the qualification).
9. **The 0.82 readout factor** double-counts readout survival on Quantinuum; removing it lowers every shot count by 18 % (owner's call; `reports/2x3_shot_rule_estimator_ruling_20261003.md` section 5).
10. **Amendment 01 item 4** (the 2x3 device; needs vendor gate durations and $T_1/T_2$, not only error rates; IBM is excluded by measurement, Quantinuum remains) and **item 5** (the shot quota of Step 9.2, which scales as $1/f$ and which the plan of record now answers for two of four sectors, item 3).
11. **Unsigned cheaper 2x3 circuit variants** (no-plaq1 $f=0.31$, fixed-angle + no-plaq1 $f=0.36$ on Helios gate-only; `prompts/27` D4): adopt only after the unrun stage T0c shows recall $\ge0.9$; needs a signature (amendment item 3).
12. **The ML step:** whether to build the graph network of manual Step 7 and run the seven-protocol comparison once 2x3 data exist; until then the word "neural" is a plan, not a result.
13. **Housekeeping (no physics):** delete the untracked empty directory `data/hardware/H0_ddrep_dryrun_prototype/`; decide whether to register `K0_2x3_2x4` in `scripts/update_status.py`; push the report commit (the coordinator's call, `CLAUDE.md` rule 5).

### 9.7 Gaps and discrepancies in this report (numbers I could not source or reconcile)

1. **The canary's predicted accepted count.** `CLAUDE.md` quotes "8 accepted of 267 against the preregistered $\ge10$ and the simulated 71"; `prompts/15` D5 quotes a predicted 39.9; `validation/H0_canary.json -> data.f_comparison` gives a predicted yield 0.18725, which corresponds to 50.0 expected accepted shots of 267 **(my multiplication of sourced numbers)**. I could not reconcile the three; Section 6.7 uses the JSON values and the go-rule threshold of 10.
2. **Time zones.** The `environment.timestamp` strings in the gate JSON are in the time zone of the run (MDT, PDT or UTC) and are shown as recorded; ordering across zones in block (a) is approximate (within hours). The 2026-10-06 hardware times in Sections 6.21, 6.22 and block (i) are UTC from the `session.json` files; the gate JSON of the same jobs say MDT (UTC minus 6 h).
3. **Numbers taken from documents rather than JSON.** The following have no JSON key I could cite and come from prose reports or `prompts/LOG.md` (named where used): the CI jobs' timings and utilisations, the GPU speed-ups (19.8x, 161x, about 300x), the planner's 2x2 `AMBIGUOUS` arithmetic at $r_{nc}=1.10$, the 94 % of shots at $k=4$, the `S2D` shot-quota numbers 556 000 / 808 104, the memory scenarios' cost ESTIMATEs, the K1 expected-billed range 211.7-242.4 s, the K1 circuit build times (1 223 s / 1 250 s), the H0_ddrep dry-run sampling time (1 738 s), the garbage acceptance counts 64.6 / 40.6 of $10^5$ for K1, the "ranked 2 of 750" patch statement, and the statement that the live `ibm_kingston` record of 2026-10-05/06 had 352 of 352 CZ keys without an error (the JSON of that unusable record is under `data/hardware/K0_prep/`; I read the statement in `prompts/LOG.md`).
4. **Planner arithmetic still not reproduced by a gate:** the first-run diagnosis numbers of `prompts/31` D1 (173 states for $W\ge0.9999$, hardest state weight $1.8\times10^{-5}$, about $6\times10^6$ shots per sector), the USD figures and machine-hours (ESTIMATE inputs), the memory/transport scenarios, and the Tier-claim proxy emulation of `prompts/27` T0.1. **Now reproduced by gates:** the D3'-R plan (`Q0P_2x3_plan` P1), the re-sized plan and its HQC (`CV_2x3_plan`, P4/P7 of `Q0P_2x3_plan`), the Stage E / P plans (`Q0P_2x3_plan -> data.stage_E_v3 / stage_P_v3`), the oracle-width table (`CV_2x3_plan -> data.oracle_width_reproduction`, 196 fields, maximum scaled difference $3.2\times10^{-14}$).
5. **Values not computed in the repository.** The random acceptance of the 2x4 decoder; any measurement of Quantinuum, IonQ, Google or other non-IBM devices (all vendor numbers were read from web pages by the planner on 2026-10-01/02 and are not measurements by this project); the memory/transport error of any ion-trap device for this circuit; the mechanism of the 2026-10-02 context-aware DD collapse (not replicated, so open in a different sense); the static-sector shot plan; any 2x3 clean fraction above the K1 upper limit.
6. **Unclear count.** Test counts in Section 4.6 are the last values recorded in the cited JSON/LOG rows (the newest 342 passed / 19 skipped), not a fresh run (I ran no tests, as instructed).
7. **Derived statements that no file makes in these words (my comparisons, labelled where used):** that the day-to-day change of the no-DD baseline (factor 2.04) exceeds the same-day DD effects of 2026-10-06 (ratios 0.647-1.150) and is comparable to the 2026-10-02 XY4 gain (2.819); that the K1 upper bound is 14.6x below GO-A and about 4 850x below the bar; that P(0 hits) for the no-idle bracket is about 0.065; that the 273 s may grow to about 290 s on 2026-10-20 (inference about a rolling window, unverified); the machine-hour and USD sums for the re-sized campaign.
8. **"Five most important numbers"** in Section 1 are my selection; the project itself does not rank numbers. Every figure that the refresh task named was found in the named files; the one place where a source now disagrees with the previous report is the K0 gate, whose old FAIL 5/6 numbers (5 527 CZ, $f_{\rm ceiling}=1.095\times10^{-2}$) were superseded by the exact 5 659-CZ circuit (Section 6.20).

## 10. Progress measure

Source: `reports/H0_2x2_full_hardware_report_20261002.md` section 2 (planner, 2026-10-02): the SKQD plan was broken into 51 rows (33 rows of the manual's Steps 0-11 and 18 rows of amendment 01, the owner decisions and the preregistration discipline) and each row was scored against the *2x2 hardware campaign* with its evidence. Status key: **F** = fulfilled; **FD** = fulfilled with a deviation (named); **ND** = not done (reason named). The tally printed by the report is: **fulfilled 31, fulfilled with deviation 12, not done 8** (I recounted the table: F 31, FD 12, ND 8). The first count in the report text reads "33 manual rows + 18 amendment/decision rows". Note on scope: this scores the plan against the 2x2 hardware run only; all 2x3/2x4 hardware rows are, by that scope, "not done".

Share of the 51 rows: F 31/51 = 60.8 %, FD 12/51 = 23.5 %, ND 8/51 = 15.7 % **(sum of sourced counts)**.

**Not re-scored on 2026-10-06.** The planner's table was written on 2026-10-02 and no file re-scores it; the new results (the replication, the 2x3 pilot) change no F / FD / ND count by the table's own scope (the 2x2 campaign), but two row notes are now incomplete and I have appended a marker to them: row A2 ("met on $k=1$ only") must also say that the $k=1$ result was one calibration's and did not repeat, and row 9.2 stays ND with one more fact (the only 2x3 job, K1, measured a null on IBM).

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
| 9.2 | 2x3 production, four sectors, $\le 500$ CZ, $2\times10^5$ shots per sector, two calibration windows | ND | **[2026-10-06 marker, not the planner's:** the only 2x3 hardware job, K1 (188.0 s on `ibm_kingston`), saw 0 reference hits in $2\times10^5$ shots; $\hat f_{\rm ideal}\le2.06\times10^{-5}$ (95 %)] |
| 9.3 | Optional 2x4 hardware only if H1-H2 pass | ND | (by design) |
| 10 | Gates E1-E3, S1 (done), S2, S3, H0, H1, H2, P1, M1 | FD |  |
| 10 (error budget) | Truncation ($j_{\max}$), subspace (certified interval), device (recall, false positives, yield, CIPSI comparison), shot (bootstrap over circuits), classical | FD |  |
| 10 (reporting) | Raw bitstrings, calibration snapshots, circuits and decoder released | FD | in the repository, not yet a public release bundle |
| 11 | Six-week timeline: 2x2 in week 3, 2x3 in week 4 | FD |  |
| A1 | Patch selected on the day by the exhaustive idle-aware rule R1' on the full device; re-frozen onto that patch | F |  |
| A2 | Budget criterion: $f = f_{\rm gates}\,e^{-S_{\rm idle}}$ on the scheduled circuit, mean $\ge 0.1$, worst $\ge 0.05$; $T_2$ convention named | FD | met on $k=1$ only; family-level unknown; owner waiver in force. **[2026-10-06 marker, not the planner's:** the $k=1$ result was one day's; on 2026-10-06 the same cell T3 gave $f_{\rm hit}=0.0732$ and $\hat f_{\rm ideal}=0.0656$, below the bar] |
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
| H0 | **realised by measurement gates**: H0_canary (NO-GO), H0_diag, H0_kpilot (NO-GO), H0_ddtest (PASS), **H0_2x2 (PASS)**, H0_ddrep (PASS; replication did not confirm the H0_ddtest gain); "measured $f$ within 30 % of the model" was read measurement-to-measurement | Section 5 |
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
| 2x2 hardware | calibration and full run | **done** (measurement gates); the DD mitigation did not replicate | H0_2x2 PASS; H0_ddrep PASS (negative); 14 jobs on IBM in all, 327 s of 600 s |
| clean-fraction statistics | estimator, near-clean term, $r_{nc}$, floor theorem | **done** | CF_traj PASS 7/7 |
| 2x3 plan check | D3'-R, convergence and coverage criteria CV0-CV5, Stage E/P plans | **done** (emulation; no device statement) | `CV_2x3_plan` PASS 37/37, `Q0P_2x3_plan` PASS 7/7; plan of record 665 605 HQC at $f=0.10$ |
| 2x3 hardware access | a device that can run 2x3 (Quantinuum) and an allocation | **not started** (draft email only); IBM Heron **measured NO-GO** (K1) | Section 9.3, 6.22 |
| 2x3 hardware results | H1, H2, P1 | **open** (the one 2x3 job is a null) | needs the 2x3 hardware access row above |
| neural step | graph network, recovery, seven-protocol comparison, M1 | **open** | only the ridge baseline exists |
| 2x4 | transfer and optional hardware | **simulator verified, hardware infeasible today** | S2_2x4 PASS |
| release | raw bit strings, calibration records, circuits, decoder, methods note | **not started** (data are in the repository) | Section 9.5 |

## 11. DATA APPENDIX for plotting

**How to use.** Every block below is a fenced ```csv block that can be copied straight into pandas (`pd.read_csv(io.StringIO(text))`), R or a spreadsheet. Each block has a title, the source file(s) and key(s) it was generated from (the blocks were generated by a script that reads the JSON files directly, so no number was typed by hand; two small exceptions are marked inline: the survey rows of devices other than Quantinuum and IonQ come from the planner's survey table, and the r_nc-corrected block (b2) is my division of sourced numbers; blocks (a), (b), (g), (i) extend the 2026-10-05 versions with the 2026-10-05/06 rows, and blocks (b3), (o)-(u) are new and were generated by a script, `gen_blocks.py`, that reads `validation/*.json` directly), and the units of its columns. Empty cells mean "not available in the source". Floats are printed with 6 significant digits. Blocks: (a) gate timeline, (b) clean-fraction history (b2 corrected by r_nc), (c) the H0_ddtest cells, (d) H0_2x2 energies, certificate intervals and baselines (d2, per-state counts d3), (e) B_all / B_sig support growth versus k, (f) device survey (f2 for 2x2), (g) 2x3 shots and HQC versus f for each shot rule, (h) CF_traj arms, (i) cumulative QPU seconds, (j) gate counts and device requirements, (k) exact reference energies (k2 derived quantities), (l) the 51 plan rows, (m) the 2x2 shot plan, (n) the S2D_levers Aer curves and the kingston pilot comparison (n2); **new:** (b3) $\hat f_{\rm ideal}$ as computed by the gates, (o) the seven H0_ddrep cells, (p) the pulse-train over-rotation per qubit, (q) the CV_2x3_plan cells (CV2 widths, CV3 steps, re-sizing $s$), (q2) the $B=1$ re-sizing ladder, (r) the oracle-width table, (s) the K1 pilot result, (t) the K0 2x3 readiness on two calibration records, (u) the calibration-record statistics of the two days.

**Caution for the plotting assistant.** (1) The clean-fraction statistics in block (b) are *different estimators* (yield-inverted, reference-string `f_hit`, mixture); do not draw them as one series without saying so. (2) All device-prediction numbers (f in blocks (f), (g)) are **models** (planner arithmetic or ESTIMATE), not measurements; the only measured clean fractions are in blocks (b), (b3), (c), (o), (s). (4) Block (g) now carries the re-sized plan of record beside the older rules; the older rows are alternatives, not the plan. (3) Intervals are 95 % unless a column says 68 %.

#### (a) Gate timeline

**Source:** every `validation/*.json` with a criteria list (`environment.timestamp`, `status`, `criteria[*].passed`, `runtime_s`, `environment.git_commit`); 46 rows (38 on 2026-10-05; regenerated from the JSON, so the K0 row now reads PASS 6/6 and the CV_2x2_info / CF_estimator rows carry their final timestamps). Dates are in the time zone the run recorded (MDT/PDT/UTC); the same gate name can appear twice because `L4_p2_*` records carry `gate` = `L4`.

**Columns and units:** `date` ISO date; `time` hh:mm:ss in `tz`; `file` JSON file stem; `gate` the gate name inside the file; `status` PASS or FAIL; `criteria_passed`, `criteria_total` counts; `runtime_s` seconds (wall time of the gate run); `commit` short git hash

The CI wrapper results are separate: L4 job 58741899 686 s PASS; S3 job 58771538 255 s PASS; S2_2x4 job 59162991 99 s PASS (`validation/ci_gate_*.json`).

```csv
date,time,tz,file,gate,status,criteria_passed,criteria_total,runtime_s,commit
2026-09-14,16:43:44,MDT,E1,E1,PASS,23,23,427,57b3bff
2026-09-14,16:44:00,MDT,E2,E2,PASS,51,51,15,57b3bff
2026-09-14,16:44:36,MDT,E3,E3,PASS,85,85,36,57b3bff
2026-09-14,16:48:20,MDT,S1,S1,PASS,12,12,223,57b3bff
2026-09-14,18:00:36,MDT,L4_p2_3e-3,L4,FAIL,2,4,1376,30684f2
2026-09-14,18:24:06,MDT,L4_p2_1e-3,L4,FAIL,2,4,1012,30684f2
2026-09-14,21:37:07,UTC,CS,CS,PASS,4,4,4,3c32216
2026-09-15,15:04:26,MDT,L3,L3,FAIL,0,2,14,5d60461
2026-09-15,15:12:59,MDT,S2,S2,FAIL,3,5,436,5d60461
2026-09-15,20:18:31,MDT,S2_fixed,S2_fixed,FAIL,5,9,301,2fbcf29
2026-09-15,20:19:58,MDT,L5,L5,PASS,6,6,3,0420211
2026-09-15,20:20:11,MDT,L2,L2,PASS,4,4,8,0420211
2026-09-16,07:02:12,MDT,S2D,S2D,FAIL,6,8,213,89102d2
2026-09-16,11:46:01,MDT,S3_smoke,S3_smoke,FAIL,1,2,295,1223e92
2026-09-16,12:28:26,MDT,L4_fez,L4_fez,PASS,4,4,450,3722018
2026-09-16,13:15:46,MDT,H0P,H0P,PASS,16,16,1179,2392fb3
2026-09-21,17:57:49,MDT,H0P_rehearsal,H0P_rehearsal,PASS,18,18,175,1e5c03b
2026-09-22,01:22:38,PDT,L4,L4,PASS,4,4,677,n/a
2026-09-22,11:46:55,MDT,H0P_ibm_fez,H0P_ibm_fez,PASS,18,18,319,1e6d7d3
2026-09-22,14:16:46,MDT,H0_diag_dryrun,H0_diag_dryrun,FAIL,6,7,1,9cfe3ec
2026-09-22,14:46:44,MDT,H0_diag,H0_diag,FAIL,6,8,1,4d1e8f6
2026-09-22,16:36:34,MDT,S2D_idle,S2D_idle,FAIL,6,15,406,2c6edb6
2026-09-22,18:01:22,PDT,S3,S3,PASS,4,4,248,n/a
2026-09-30,15:28:44,MDT,H0P_repro,H0P_repro,PASS,15,15,1741,6180c6a
2026-09-30,15:31:18,MDT,H0_model,H0_model,PASS,5,5,2,6180c6a
2026-09-30,15:41:37,MDT,H0_dryrun,H0_dryrun,PASS,9,9,10,6180c6a
2026-09-30,15:41:49,MDT,H0_canary,H0_canary,FAIL,3,6,11,6180c6a
2026-10-01,09:15:29,PDT,S2_2x4,S2_2x4,PASS,12,12,0,n/a
2026-10-02,11:13:55,MDT,S2D_levers,S2D_levers,PASS,9,9,489,782580c
2026-10-02,12:04:30,MDT,H0_kpilot_dryrun,H0_kpilot_dryrun,PASS,9,9,49,761369f
2026-10-02,12:31:53,MDT,H0_kpilot,H0_kpilot,FAIL,8,9,450,fc3a5a2
2026-10-02,14:10:22,MDT,H0_ddtest_dryrun,H0_ddtest_dryrun,PASS,8,8,15,aa4da1e
2026-10-02,14:37:48,MDT,H0_ddtest,H0_ddtest,PASS,8,8,601,d4b3855
2026-10-02,15:04:52,MDT,H0_2x2_dryrun,H0_2x2_dryrun,PASS,8,8,17,4e979a0
2026-10-02,16:04:51,MDT,H0_2x2,H0_2x2,PASS,8,8,444,da715fc
2026-10-02,21:36:57,MDT,Q0P_2x3,Q0P_2x3,PASS,7,7,926,8072b8d
2026-10-05,13:47:33,MDT,CF_traj,CF_traj,PASS,7,7,1201,a8ebbaa
2026-10-05,17:28:05,MDT,CF_estimator_2x2_info,CF_estimator_2x2_info,PASS,2,2,4,3d5f05a
2026-10-05,17:40:48,MDT,CV_2x3_plan,CV_2x3_plan,PASS,37,37,679,3d5f05a
2026-10-05,17:41:27,MDT,CV_2x2_info,CV_2x2_info,PASS,2,2,14,3d5f05a
2026-10-05,17:56:24,MDT,Q0P_2x3_plan,Q0P_2x3_plan,PASS,7,7,781,3d5f05a
2026-10-06,00:59:27,MDT,H0_ddrep_dryrun,H0_ddrep_dryrun,PASS,8,8,14,cd9ce12
2026-10-06,01:11:17,MDT,H0_ddrep,H0_ddrep,PASS,8,8,422,36c48a2
2026-10-06,01:38:10,MDT,K0_2x3_2x4,K0_2x3_2x4,PASS,6,6,943,880961d
2026-10-06,02:20:48,MDT,K1_2x3_fpilot_dryrun,K1_2x3_fpilot_dryrun,PASS,9,9,430,f8df126
2026-10-06,02:33:45,MDT,K1_2x3_fpilot,K1_2x3_fpilot,PASS,8,8,422,504d452
```

#### (b) Clean-fraction history per hardware run

**Source:** `validation/H0_canary.json`, `H0_model.json`, `H0_kpilot.json`, `H0_ddtest.json`, `H0_2x2.json`, **`H0_ddrep.json` and `K1_2x3_fpilot.json` (new rows at the end, 2026-10-06)** (keys in the last column). The H0_diag runs J1-J4 and the canary enter only through the pooled fez row (6 reference hits in 8 267 shots).

**Columns and units:** `f` clean-fraction statistic (dimensionless probability per shot); `lo`,`hi` interval ends at the stated `level`; `shots` shots the statistic uses (for pooled rows the sum over circuits; for H0_2x2 pooled the 7 k=1 circuits x 267); `stat` names the estimator. Different statistics are NOT interchangeable: the yield-inverted value overstates the clean fraction (15x on fez); the reference-string value `f_hit` estimates the ideal-sample fraction (ratio r_nc = 1.115). The K1 rows (2x3, `ibm_kingston`) have a *negative* `f` because the statistic subtracts the garbage expectation (0.0954 per circuit) from zero observed hits; read the interval's upper end. The H0_ddrep T0 / T1 / T3 rows are the same circuits as the H0_ddtest rows of 2026-10-02 above (compare T0: 0.0400 vs 0.0818).

```csv
run,date,device,circuit,statistic,f,lo,hi,interval_level,shots,note,source_key
H0_canary,2026-09-22,ibm_fez,B0_ref06_k1_rep1 (663 CZ),yield-inverted (y=0.82f+(1-f)a),0.0255145,,,,267,"DD on, twirling on; 8 accepted; NOT a clean-shot measurement",validation/H0_canary.json data.f_comparison
H0_canary,2026-09-22,ibm_fez,B0_ref06_k1_rep1 (663 CZ),prediction: gate-only model,0.219522,,,,267,prediction,validation/H0_canary.json data.f_comparison
H0_model (5 fez pubs),2026-09-22,ibm_fez,B0_ref06_k1 pooled over canary + J1-J4,reference-string f_clean (readout factor 0.82),0.000664981,0.000267503,0.0012635,68% Garwood,8267,"6 hits vs 2.018 from garbage; interval is 68%, not 95%",validation/H0_model.json data.C2_pooled_device_clean_count.pooled_reference_test
H0_kpilot,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.041293,0.0361148,0.0469982,95%,8000,"DD off, twirling off; NO-GO",validation/H0_kpilot.json data.decision
H0_kpilot,2026-10-02,ibm_kingston,B0_ref06_k1,reference-string f_hit,0.0403927,0.0332439,0.0486082,95%,4000,,validation/H0_kpilot.json data.decision.f_by_circuit
H0_kpilot,2026-10-02,ibm_kingston,B1_ref07_k1,reference-string f_hit,0.0421874,0.034898,0.0505359,95%,4000,,validation/H0_kpilot.json data.decision.f_by_circuit
H0_kpilot,2026-10-02,ibm_kingston,B0_ref06_k4,reference-string f_hit,0.0384758,0.0211611,0.0635501,95%,4000,,validation/H0_kpilot.json data.decision.f_by_circuit
H0_ddtest T0,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.0400315,0.035844,0.0445691,95%,12000,cell T0,validation/H0_ddtest.json data.decision.cells.T0
H0_ddtest T1,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.000466785,-1.96655e-05,0.00133721,95%,12000,cell T1,validation/H0_ddtest.json data.decision.cells.T1
H0_ddtest T2,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.111821,0.104764,0.119227,95%,12000,cell T2,validation/H0_ddtest.json data.decision.cells.T2
H0_ddtest T3,2026-10-02,ibm_kingston,pooled 2 k=1 circuits,reference-string f_hit,0.112853,0.105763,0.120292,95%,12000,cell T3,validation/H0_ddtest.json data.decision.cells.T3
H0_2x2,2026-10-02,ibm_kingston,pooled 7 k=1 circuits,reference-string f_hit,0.127053,0.108428,0.147942,95%,1869,DD cell T3; 173 hits vs 0.456 from garbage,validation/H0_2x2.json data.clean_fraction.pooled
H0_2x2,2026-10-02,ibm_kingston,B0_ref06_k1,reference-string f_hit,0.13411,0.0866992,0.198013,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref06_k1,mixture estimator,0.127551,,,,267,"68 percent interval in source: [0.11235706313885048, 0.1414890748184295]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref17_k1,reference-string f_hit,0.128636,0.0823605,0.191382,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref17_k1,mixture estimator,0.138705,,,,267,"68 percent interval in source: [0.12550506985006343, 0.14913202094957254]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref21_k1,reference-string f_hit,0.138953,0.0906493,0.203693,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref21_k1,mixture estimator,0.148416,,,,267,"68 percent interval in source: [0.13767737943758027, 0.1561715400780899]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref30_k1,reference-string f_hit,0.138953,0.0906493,0.203693,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref30_k1,mixture estimator,0.128372,,,,267,"68 percent interval in source: [0.1178297362522436, 0.13645570114493744]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref43_k1,reference-string f_hit,0.108,0.0660441,0.166513,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B0_ref43_k1,mixture estimator,0.127889,,,,267,"68 percent interval in source: [0.12391147402301594, 0.1278889193386316]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref07_k1,reference-string f_hit,0.138375,0.090272,0.202845,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref07_k1,mixture estimator,0.132496,,,,267,"68 percent interval in source: [0.12253408105946641, 0.13970340414288612]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref14_k1,reference-string f_hit,0.102413,0.0617701,0.15957,95%,267,,validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_2x2,2026-10-02,ibm_kingston,B1_ref14_k1,mixture estimator,0.101259,,,,267,"68 percent interval in source: [0.09038906250384834, 0.10963820058819713]",validation/H0_2x2.json data.clean_fraction.per_k1_circuit
H0_ddrep T0,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0817751,0.0757532,0.0881453,95%,12000,cell T0; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.T0
H0_ddrep T1,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0528757,0.0480506,0.05805,95%,12000,cell T1; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.T1
H0_ddrep T3,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0731741,0.0674826,0.0792142,95%,12000,cell T3; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.T3
H0_ddrep M1,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0644584,0.059122,0.0701436,95%,12000,cell M1; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M1
H0_ddrep M2,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0659492,0.0605505,0.0716968,95%,12000,cell M2; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M2
H0_ddrep M3,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0726007,0.0669319,0.0786181,95%,12000,cell M3; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M3
H0_ddrep M4,2026-10-06,ibm_kingston,pooled 2 k=1 circuits (B0_ref06_k1 + B1_ref07_k1),reference-string f_hit,0.0940459,0.0875813,0.100858,95%,12000,cell M4; DD off in runtime options; job db29p6nr11fs7396e4ig,validation/H0_ddrep.json data.cells.M4
H0_ddrep T0,2026-10-06,ibm_kingston,B0_ref06_k1,reference-string f_hit,0.0871053,0.0783659,0.0965467,95%,6000,,validation/H0_ddrep.json data.cells.T0.f_by_circuit
H0_ddrep T0,2026-10-06,ibm_kingston,B1_ref07_k1,reference-string f_hit,0.0764796,0.0683291,0.0853283,95%,6000,,validation/H0_ddrep.json data.cells.T0.f_by_circuit
K1_2x3_fpilot,2026-10-06,ibm_kingston,"B0_ref117_k1 (2x3, 5659 CZ)",reference-string f_hit,-1.25277e-06,-1.25277e-06,4.72052e-05,95%,100000,0 reference hits vs 0.0954 from garbage; negative = zero hits minus the garbage expectation; read the upper end,validation/K1_2x3_fpilot.json data.circuits.B0_ref117_k1
K1_2x3_fpilot,2026-10-06,ibm_kingston,"B1_ref29_k1 (2x3, 5659 CZ)",reference-string f_hit,-1.25284e-06,-1.25284e-06,4.72077e-05,95%,100000,0 reference hits vs 0.0954 from garbage; negative = zero hits minus the garbage expectation; read the upper end,validation/K1_2x3_fpilot.json data.circuits.B1_ref29_k1
K1_2x3_fpilot,2026-10-06,ibm_kingston,pooled 2 circuits (2x3),reference-string f_hit,-1.2528e-06,-1.2528e-06,2.29768e-05,95%,200000,0 reference hits vs 0.190735 from garbage; NO-GO firm,validation/K1_2x3_fpilot.json data.pooled
K1_2x3_fpilot,2026-10-06,ibm_kingston,B0_ref117_k1,prediction: gate-only on the routed layout (no idle),1.67113e-05,,,,100000,prediction (preregistered),validation/K1_2x3_fpilot.json data.prediction_prereg.B0_ref117_k1.f_bracket
```

#### (b2) The same three pooled values divided by r_nc (MY ARITHMETIC from sourced numbers)

**Source:** `f` and 95 % ends from the files above; `r_nc` = 1.1151352098 from `validation/CF_traj.json -> data.pooled_k1.r_nc` (`data/cf_trajectories/r_nc.json`). The combined interval that includes the uncertainty of r_nc is wider than shown (the planner combines Garwood and bootstrap variances on the log scale; I did not).

**Columns and units:** `f_hit` etc. dimensionless; `f_over_rnc` = f_hit / r_nc; `verdict_vs_0.1` compares the 95 % interval of f_hit/r_nc (without the r_nc uncertainty) with the mean bar 0.1

```csv
run,f_hit,lo95,hi95,r_nc,f_over_rnc,lo95_over_rnc,hi95_over_rnc,interval_vs_bar,bar
H0_kpilot pooled,0.041293,0.0361148,0.0469982,1.11514,0.0370296,0.032386,0.0421457,below,0.1 (mean bar)
H0_ddtest T3 (adopted),0.112853,0.105763,0.120292,1.11514,0.101202,0.0948432,0.107872,straddles,0.1 (mean bar)
H0_2x2 pooled,0.127053,0.108428,0.147942,1.11514,0.113935,0.0972327,0.132667,straddles,0.1 (mean bar)
```

#### (b3) \hat f_ideal = f_hit / r_nc as computed by the gates (sourced, not my division)

**Source:** `validation/CF_estimator_2x2_info.json -> data.rows` (the 2x2 records of 2026-10-02), `validation/H0_ddrep.json -> data.replication.f_hat_ideal_T3` (its interval is at confidence 0.9545, z = 2.0000, not 0.95), `validation/K1_2x3_fpilot.json -> data.pooled`. $r_{nc}=1.1151352098$ and its 95 % interval [1.0286, 1.1151] (`data/cf_trajectories/r_nc.json`); the intervals combine the Garwood (hit count) and bootstrap ($r_{nc}$) uncertainties on the log scale.

**Columns and units:** `f_hit` and `f_hat_ideal` dimensionless; `recorded_rule_on_f_hat_ideal` the preregistered 2x2 rule (lower 95 % end $\ge0.1$ is GO, upper end $<0.1$ is NO-GO, else AMBIGUOUS) applied to $\hat f_{\rm ideal}$; `v3_rule_on_f_hat_ideal` the rule of the 2x3 stages (GO iff lower $\ge0.05$ and point $\ge0.10$), not applied retroactively (`prompts/31` ruling 6); `recorded_verdict` the verdict written in the original gate. For K1 the decision rule is GO-B $\ge10^{-3}$, GO-A $\ge3\times10^{-4}$.

```csv
record,field,f_hit,f_hit_lo95,f_hit_hi95,f_hat_ideal,f_hat_ideal_lo95,f_hat_ideal_hi95,recorded_rule_on_f_hat_ideal,v3_rule_on_f_hat_ideal,recorded_verdict
H0_kpilot,data.decision.f_pool,0.041293,0.0361148,0.0469982,0.0370296,0.0321937,0.042406,NO-GO,NO-GO,NO-GO (kpilot)
H0_ddtest,data.decision.cells.T0.f_pool,0.0400315,0.035844,0.0445691,0.0358983,0.0319141,0.0402621,NO-GO,NO-GO,
H0_ddtest,data.decision.cells.T1.f_pool,0.000466785,-1.96655e-05,0.00133721,0.00041859,0,0.00120008,NO-GO,NO-GO,
H0_ddtest,data.decision.cells.T2.f_pool,0.111821,0.104764,0.119227,0.100276,0.0928731,0.108171,AMBIGUOUS,GO,
H0_ddtest,data.decision.cells.T3.f_pool,0.112853,0.105763,0.120292,0.101202,0.0937546,0.109142,AMBIGUOUS,GO,signed bar GO (adopted)
H0_2x2,data.clean_fraction.pooled.f,0.127053,0.108428,0.147942,0.113935,0.0967415,0.133368,AMBIGUOUS,GO,
H0_2x2,data.adopted_configuration.f_pool,0.112853,0.105763,0.120292,0.101202,0.0937546,0.109142,AMBIGUOUS,GO,signed bar GO
H0_ddrep,"data.replication.f_hat_ideal_T3 (2026-10-06, 95.45 % interval)",0.0731741,0.0674826,0.0792142,0.065619,0.059942,0.0717274,NO-GO (upper end 0.0717 < 0.1),NO-GO,signed bar NO-GO (information)
K1_2x3_fpilot,data.pooled (2x3),-1.2528e-06,-1.2528e-06,2.29768e-05,-1.12345e-06,-1.12345e-06,2.06045e-05,NO-GO,"NO-GO (K1 rule: GO-B >= 1e-3, GO-A >= 3e-4)",NO-GO firm
```

#### (c) H0_ddtest cells (ibm_kingston, job db01005j371s73dnmbd0, 2 circuits x 6 000 shots per cell)

**Note (2026-10-06):** these are the 2026-10-02 values; the same cells T0, T1, T3 on 2026-10-06 and four new mechanism cells are in block (o).

**Source:** `validation/H0_ddtest.json -> data.decision.cells.<cell>` (`f_pool`, `f_pool_95`, `R`, `R_95`, `null_ratio`, `accepted`, `reference_hits`, `qualifies`) and `data.decision.adopted`.

**Columns and units:** `n_pulses_total` sum over the two circuits of inserted DD pulses (per circuit in the source; T1 862 each); `f` reference-string clean fraction of the pooled two circuits; `f_lo95`,`f_hi95` 95 % interval; `R` = f(cell)/f(T0) with its 95 % interval; `null_ratio` the ratio the pulse error alone would give (pulse cost exp(-nats)); `accepted`, `reference_hits` summed over the two circuits

```csv
cell,description,n_pulses_total,f,f_lo95,f_hi95,R,R_lo95,R_hi95,null_ratio,accepted,reference_hits,qualifies,adopted
T0,no DD (baseline),0,0.0400315,0.035844,0.0445691,1,,,1,526,352,,False
T1,"context-aware staggered X (qiskit ContextAwareDynamicalDecoupling, min window 512 ns)",1724,0.000466785,-1.96655e-05,0.00133721,0.0116604,0.00438888,0.0309796,0.816228,102,7,False,False
T2,client XY4 in every idle window >= 256 ns,1556,0.111821,0.104764,0.119227,2.79333,2.4719,3.15656,0.841058,1429,978,True,False
T3,client XY4 in idle windows >= 1.024 us only,488,0.112853,0.105763,0.120292,2.81912,2.49509,3.18523,0.944388,1456,987,True,True
```

#### (d) H0_2x2 Ritz energies versus exact E0, certificate intervals (per sector)

**Source:** `validation/H0_2x2.json -> data.energies.<sector>.{B_all,B_sig}` (`E_R`, `abs_error`, `rH`, `weinstein_gap_assumed`, `kato_temple`, `gap_assumption_holds`, `E0_inside_gap_assumed_weinstein`) and `data.support.<sector>` (`dim`, `shots`, `accepted`, `Na_over_dim`).

**Columns and units:** energies in lattice units (dimensionless); `abs_error` = |E_R - E0|; `rH` Hamiltonian residual; Weinstein/Kato-Temple intervals as [lo, hi] (the gap-assumed interval is [E_R - delta, E_R]); `Na_over_dim` = N a / dim, the saturation parameter (rule C22)

```csv
sector,basis,basis_size,E_R,E0_exact,abs_error,rH,weinstein_lo,weinstein_hi,kato_temple_lo,kato_temple_hi,gap_assumption_holds,E0_in_weinstein,sector_dim,shots,accepted,Na_over_dim
B=0,B_all,38,-3.64077,-3.64077,0,6.14037e-15,-3.64077,-3.64077,-3.64077,-3.64077,True,True,38,69505,9454,16.969
B=0,B_sig,35,-3.64022,-3.64077,0.000547674,0.0602701,-3.70049,-3.64022,-3.64157,-3.64022,True,True,38,69505,9454,16.969
B=1,B_all,20,-1.86159,-1.86159,0,1.50912e-15,-1.86159,-1.86159,-1.86159,-1.86159,True,True,20,64402,7885,15.7231
B=1,B_sig,19,-1.86158,-1.86159,5.74934e-06,0.00595351,-1.86754,-1.86158,-1.86242,-1.86158,True,True,20,64402,7885,15.7231
```

#### (d2) H0_2x2 baselines: random equal-size bases and garbage-only (per sector)

**Source:** `validation/H0_2x2.json -> data.baselines.<sector>.{random_equal_size,garbage_only}`.

**Columns and units:** `n_seeds` number of random draws (200 seeds 23-222 for random subsets of the sector codewords including the references; 100 seeds 11-110 for uniformly random 12-bit strings run through the decoder at the hardware shot counts); `basis_size` size of each random basis (for garbage-only the mean decoded support size); E columns are the Ritz energy distribution of the baseline in lattice units; `hardware_E_R` the hardware value compared (B_sig for the random baseline, B_all for garbage-only); `hardware_percentile` the percentile of the hardware value within the baseline (5.0 means only 5 % of random bases are at least as good as the hardware for B=0; for garbage-only 100 means the hardware value equals the garbage-only value)

```csv
sector,baseline,n_seeds,basis_size,E_R_mean,E_R_std,E_R_p2.5,E_R_p97.5,E_R_min,E_R_max,hardware_E_R,hardware_percentile
B=0,random_equal_size,200,35,-3.63266,0.00638631,-3.64036,-3.61855,-3.64069,-3.61337,-3.64022,5
B=0,garbage_only,100,38,-3.64077,4.46326e-16,-3.64077,-3.64077,-3.64077,-3.64077,-3.64077,100
B=1,random_equal_size,200,19,-1.85411,0.00794102,-1.86158,-1.84104,-1.86158,-1.84104,-1.86158,28.5
B=1,garbage_only,100,20,-1.86159,6.6949e-16,-1.86159,-1.86159,-1.86159,-1.86159,-1.86159,100
```

#### (d3) H0_2x2 per-state counts and exact ground-state weights (one row per sector state)

**Source:** `validation/H0_2x2.json -> data.support.<sector>.per_state`.

**Columns and units:** `n_s` accepted count of the state over all shots of the sector; `mu_s` expected count from uniform noise N a/dim; `z` one-sided Poisson significance above mu_s; `ground_state_weight` exact |<b|Omega>|^2 (dimensionless, sums to 1 over the sector); `label` is the project's (j2 flux labels); (n labels)

```csv
sector,basis_index,label,n_s,mu_s,z,in_B_all,in_B_sig,ground_state_weight,is_reference
B=0,3,"(0,0,0,0); (0,0,2,2)",374,16.969,86.6718,True,True,0.00171136,False
B=0,5,"(0,0,0,0); (0,2,0,2)",304,16.969,69.6788,True,True,0.00171136,False
B=0,6,"(0,0,0,0); (0,2,2,0)",764,16.969,181.347,True,True,0.819498,True
B=0,9,"(0,0,0,0); (2,0,0,2)",169,16.969,36.9066,True,True,2.03589e-05,False
B=0,10,"(0,0,0,0); (2,0,2,0)",391,16.969,90.7987,True,True,0.00171136,False
B=0,12,"(0,0,0,0); (2,2,0,0)",443,16.969,103.422,True,True,0.00171136,False
B=0,17,"(0,0,0,1); (0,2,1,1)",634,16.969,149.789,True,True,0.0407652,True
B=0,18,"(0,0,0,1); (2,0,1,1)",335,16.969,77.2043,True,True,0.000110977,False
B=0,21,"(0,0,1,0); (0,1,2,1)",704,16.969,166.782,True,True,0.0407652,True
B=0,22,"(0,0,1,0); (2,1,0,1)",289,16.969,66.0375,True,True,0.000110977,False
B=0,25,"(0,0,1,1); (0,1,1,2)",283,16.969,64.5809,True,True,0.00097665,False
B=0,26,"(0,0,1,1); (2,1,1,0)",137,16.969,29.1384,True,True,1.22896e-05,False
B=0,29,"(0,1,0,0); (1,1,0,2)",218,16.969,48.8017,True,True,0.000110977,False
B=0,30,"(0,1,0,0); (1,1,2,0)",639,16.969,151.002,True,True,0.0407652,True
B=0,32,"(0,1,0,1); (1,1,1,1)",368,16.969,85.2153,True,True,0.00222583,False
B=0,34,"(0,1,1,0); (1,0,2,1)",308,16.969,70.6498,True,True,0.00097665,False
B=0,35,"(0,1,1,0); (1,2,0,1)",67,16.969,12.1454,True,True,1.22896e-05,False
B=0,38,"(0,1,1,1); (1,0,1,2)",139,16.969,29.6239,True,True,2.69479e-05,False
B=0,39,"(0,1,1,1); (1,2,1,0)",76,16.969,14.3302,True,True,7.81328e-05,False
B=0,42,"(1,0,0,0); (1,0,1,2)",186,16.969,41.0335,True,True,0.000110977,False
B=0,43,"(1,0,0,0); (1,2,1,0)",563,16.969,132.553,True,True,0.0407652,True
B=0,46,"(1,0,0,1); (1,0,2,1)",91,16.969,17.9716,True,True,1.22896e-05,False
B=0,47,"(1,0,0,1); (1,2,0,1)",395,16.969,91.7697,True,True,0.00097665,False
B=0,49,"(1,0,1,0); (1,1,1,1)",403,16.969,93.7118,True,True,0.00222583,False
B=0,51,"(1,0,1,1); (1,1,0,2)",112,16.969,23.0695,True,True,2.69479e-05,False
B=0,52,"(1,0,1,1); (1,1,2,0)",97,16.969,19.4281,True,True,7.81328e-05,False
B=0,55,"(1,1,0,0); (0,1,1,2)",44,16.969,6.56197,True,True,1.22896e-05,False
B=0,56,"(1,1,0,0); (2,1,1,0)",272,16.969,61.9106,True,True,0.00097665,False
B=0,59,"(1,1,0,1); (0,1,2,1)",30,16.969,3.16337,True,False,7.81328e-05,False
B=0,60,"(1,1,0,1); (2,1,0,1)",171,16.969,37.3921,True,True,2.69479e-05,False
B=0,63,"(1,1,1,0); (0,2,1,1)",55,16.969,9.2323,True,True,7.81328e-05,False
B=0,64,"(1,1,1,0); (2,0,1,1)",161,16.969,34.9646,True,True,2.69479e-05,False
B=0,69,"(1,1,1,1); (0,0,2,2)",28,16.969,2.67786,True,False,2.51948e-06,False
B=0,71,"(1,1,1,1); (0,2,0,2)",26,16.969,2.19234,True,False,2.51948e-06,False
B=0,72,"(1,1,1,1); (0,2,2,0)",59,16.969,10.2033,True,True,0.00129327,False
B=0,75,"(1,1,1,1); (2,0,0,2)",37,16.969,4.86267,True,True,4.48908e-07,False
B=0,76,"(1,1,1,1); (2,0,2,0)",50,16.969,8.01851,True,True,2.51948e-06,False
B=0,78,"(1,1,1,1); (2,2,0,0)",32,16.969,3.64888,True,True,2.51948e-06,False
B=1,7,"(0,0,0,0); (0,2,2,2)",555,15.7231,136.001,True,True,0.437467,True
B=1,11,"(0,0,0,0); (2,0,2,2)",719,15.7231,177.36,True,True,0.00480969,False
B=1,13,"(0,0,0,0); (2,2,0,2)",492,15.7231,120.113,True,True,0.00480969,False
B=1,14,"(0,0,0,0); (2,2,2,0)",669,15.7231,164.751,True,True,0.437467,True
B=1,19,"(0,0,0,1); (2,2,1,1)",826,15.7231,204.345,True,True,0.0270718,False
B=1,23,"(0,0,1,0); (2,1,2,1)",1171,15.7231,291.351,True,True,0.0270718,False
B=1,27,"(0,0,1,1); (2,1,1,2)",698,15.7231,172.064,True,True,0.00065098,False
B=1,31,"(0,1,0,0); (1,1,2,2)",455,15.7231,110.782,True,True,0.0270718,False
B=1,36,"(0,1,1,0); (1,2,2,1)",212,15.7231,49.4993,True,True,0.0022532,False
B=1,40,"(0,1,1,1); (1,2,1,2)",135,15.7231,30.0806,True,True,9.32586e-07,False
B=1,44,"(1,0,0,0); (1,2,1,2)",540,15.7231,132.218,True,True,0.0270718,False
B=1,48,"(1,0,0,1); (1,2,2,1)",351,15.7231,84.5539,True,True,0.0022532,False
B=1,53,"(1,0,1,1); (1,1,2,2)",27,15.7231,2.84393,True,False,9.32586e-07,False
B=1,57,"(1,1,0,0); (2,1,1,2)",218,15.7231,51.0125,True,True,0.00065098,False
B=1,61,"(1,1,0,1); (2,1,2,1)",176,15.7231,40.4204,True,True,9.32586e-07,False
B=1,65,"(1,1,1,0); (2,2,1,1)",191,15.7231,44.2033,True,True,9.32586e-07,False
B=1,73,"(1,1,1,1); (0,2,2,2)",80,15.7231,16.2101,True,True,0.000670039,False
B=1,77,"(1,1,1,1); (2,0,2,2)",115,15.7231,25.0368,True,True,3.16517e-06,False
B=1,79,"(1,1,1,1); (2,2,0,2)",131,15.7231,29.0718,True,True,3.16517e-06,False
B=1,80,"(1,1,1,1); (2,2,2,0)",124,15.7231,27.3065,True,True,0.000670039,False
```

#### (e) B_all and B_sig support growth versus k (cumulative over circuits with k <= k_max)

**Source:** `validation/H0_2x2.json -> data.support.<sector>.k_growth`.

**Columns and units:** `k_max` largest Krylov order included; `shots` cumulative shots of the sector over circuits with k <= k_max (94 % of the shots are at k = 4); `B_all` and `B_sig` support sizes (number of sector states); `sector_dim` 38 or 20

Reading note: at k_max = 4 the shot count jumps by a factor of about 17 (B=0: 4 005 -> 69 505), so the k-resolved curve mostly tracks shots rather than depth (planner report, lesson 9).

```csv
sector,sector_dim,k_max,shots,B_all,B_sig
B=0,38,1,1335,21,8
B=0,38,2,2670,26,13
B=0,38,3,4005,34,19
B=0,38,4,69505,38,35
B=1,20,1,534,9,3
B=1,20,2,1068,13,6
B=1,20,3,1602,16,10
B=1,20,4,64402,20,19
```

#### (f) Device survey for the signed 2x3 circuit family: gate-only f, f under the memory scenarios, and cost

**Source:** `data/quantinuum/devices_20261002.json -> rows.2x3|*` (Quantinuum rows), `data/ionq_2x3_feasibility_20261001.json -> results` (IonQ rows), `reports/qpu_survey_2x3_20261002.md` section 3 and `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` section 2.3 (the other devices; planner arithmetic with an ESTIMATE routing overhead where marked).

**Columns and units:** `n_2q` two-qubit gates per circuit; `eps2`, `eps1`, `eps_ro` error rates per gate / per qubit (dimensionless); `f_gate_only_mean`, `f_gate_only_worst` clean fraction from gate and readout errors only; `f_mem_low/mid/high` clean fraction including the transport/memory term of the ESTIMATE scenarios (round time 0.5 / 1.1 / 4.4 ms); `shots_total` D3-type union shot rule scaled as 1/f; `hqc_est` HQC = 5 + C(N_1q+10N_2q+5N_m)/5000 per job summed (ESTIMATE); `usd_est` at 12.5 USD per HQC (Azure Standard-plan equivalent, ESTIMATE; pay-as-you-go not public); `machine_h_mid_est` hours at the mid scenario (ESTIMATE). Blank = not available in the sources. For non-Quantinuum rows `f_gate_only_mean` holds the survey's gate-only value.

Signed bar: mean f >= 0.1 over the family and worst >= 0.05 (amendment 01 item 2). Only H2-2, Helios-1 and (marginally) H1-1 reach it on gate errors alone.

```csv
device,platform,lattice,n_2q,eps2,eps1,eps_ro,f_gate_only_mean,f_gate_only_worst,f_mem_low,f_mem_mid,f_mem_high,shots_total,hqc_est,usd_est,machine_h_mid_est,source,note
H2-2,trapped ion (QCCD),2x3,2158,0.00083,2.8e-05,0.000935,0.150157,0.149997,0.145378,0.139845,0.112966,102100,507144,6339299,60.1,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_h2_2,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
Helios-1,trapped ion (QCCD),2x3,2158,0.00079,3e-05,0.00048,0.164197,0.16401,0.137837,0.111728,0.0352008,127700,634299,7928733,75.1,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_helios_1,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
H1-1,trapped ion (QCCD),2x3,2158,0.00097,1.8e-05,0.0023,0.111327,0.111251,0.104918,0.097713,0.0660704,146000,725197,9064966,85.9,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_h1_1,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
H2-1,trapped ion (QCCD),2x3,2158,0.0011,1.9e-05,0.001,0.0860245,0.0859623,0.0815105,0.0764053,0.0535337,186700,927358,11591969,109.8,data/quantinuum/devices_20261002.json rows.2x3|quantinuum_h2_1,vendor numbers read 2026-10-02; memory and cost are ESTIMATE
IonQ Aria (retired 2026),trapped ion,2x3,2158,0.004,0.0005,0.0039,3.52042e-05,,,,,,,,,data/ionq_2x3_feasibility_20261001.json results.2x3|ionq_aria|virtual_rz,virtual Rz; f incl. serial idle estimate 6.09826e-12
IonQ Forte,trapped ion,2x3,2158,0.004,0.0002,0.005,8.6081e-05,,,,,,,,,data/ionq_2x3_feasibility_20261001.json results.2x3|ionq_forte|virtual_rz,virtual Rz; f incl. serial idle estimate 
"IonQ Tempo (targets, late 2026)",trapped ion,2x3,2158,,,,0.077,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic: reports/qpu_survey_2x3_20261002.md table row 5 (99.9 % target; no gate time or T2 published)
Google Willow chip 2 (iswap-like 1.4e-3),superconducting,2x3,3884,,,,0.0013,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,"planner arithmetic, routing 1.8 ESTIMATE (qpu_survey rank 6); proposal-only access"
"IBM Heron / ibm_kingston best edge, ceiling",superconducting,2x3,5477,0.0008164,,,0.0001,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,gate-only ceiling f<=1.14e-2 at 5477 routed CZ (ionq_devices_2x3_2x4_planner_analysis_20261002.md 2.3); about 1e-4 with 1q+readout; K0 gate: 1.095e-2
Infleqtion Sqale (raw 98.8 %),neutral atom,2x3,3884,,,,1.4e-05,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic (qpu_survey rank 9); private beta
QuEra Gemini (99.2 % global),neutral atom,2x3,3884,,,,1.3e-08,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic (qpu_survey rank 10); consultation
IBM Nighthawk / Heron-class median 2.15e-3,superconducting,2x3,5477,0.00215,,,3e-06,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic (qpu_survey rank 11)
Rigetti Cepheus / IQM Emerald (99.5 %),superconducting,2x3,3884,0.005,,,1e-09,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,planner arithmetic: f < 1e-9 (qpu_survey rank 12)
AQT IBEX Q1,trapped ion,2x3,2158,0.013,,,5e-13,,,,,,,,,reports/qpu_survey_2x3_20261002.md section 3,12 qubits < 20 and a 2000-gate cap (qpu_survey rank 13); f_2q only; eps2 = 1 - 0.987 from the product page
```

#### (f2) The 2x2 circuit on the other devices (information; not a plan item)

**Source:** `data/quantinuum/devices_20261002.json -> rows.2x2|*`, `data/ionq_2x3_feasibility_20261001.json -> results.2x2|*`, `validation/H0_2x2.json`.

**Columns and units:** as block (f); 2x2 circuit of 256 two-qubit gates (all-to-all). The IBM row is the measured pooled reference-hit fraction with DD, 588 routed CZ.

```csv
device,lattice,n_2q,eps2,f_gate_only_mean,f_mem_low,f_mem_mid,f_mem_high,source
H2-2,2x2,256,0.00083,0.787461,0.786953,0.786344,0.783003,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_h2_2
Helios-1,2x2,256,0.00079,0.799066,0.796282,0.792953,0.774892,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_helios_1
H1-1,2x2,256,0.00097,0.751405,0.750683,0.749818,0.745078,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_h1_1
H2-1,2x2,256,0.0011,0.737831,0.737038,0.736088,0.730883,data/quantinuum/devices_20261002.json rows.2x2|quantinuum_h2_1
ionq_aria,2x2,256,0.004,0.260928,,,,data/ionq_2x3_feasibility_20261001.json results.2x2|ionq_aria|virtual_rz
ionq_forte,2x2,256,0.004,0.302881,,,,data/ionq_2x3_feasibility_20261001.json results.2x2|ionq_forte|virtual_rz
"IBM ibm_kingston, T3 measured (reference-hit statistic)",2x2,588,,0.127053,,,,"validation/H0_2x2.json (588 routed CZ on the patch; measured, not a model)"
```

#### (g) 2x3 shots and HQC versus clean fraction f, for each shot rule (planner prototype rows; the D3'-R base rows and the re-sized rows are now reproduced by gates)

**Source:** `scratch/planner/d3s_2x3_shot_rule_20261003.json -> plans["<sector>|f=<f>"].<rule>` (shots_total, jobs, hqc_total, recall floors, probabilities); the rows labelled D3'-R reproduce the table of `reports/2x3_shot_rule_estimator_ruling_20261003.md` section 2.4 (e.g. f=0.10: 34 909 + 49 203 shots, 418 166 HQC). This JSON is a planner prototype; gate `Q0P_2x3_plan` (P1) has since reproduced the D3'-R rows to the shot (criterion P1, whose text names $f=0.10$ while the log row of 2026-10-05 says all three $f$; `validation/Q0P_2x3_plan.json -> data.plan_table`), and gate `CV_2x3_plan` produced the **re-sized plan of record** (the last nine rows, three per $f$: `rule` = "D3'-R x s ...", from `validation/CV_2x3_plan.json -> data.plan.<f>.<sector>.{final_shots_total, final_jobs, final_hqc, resized_by}`; the `s` column is the multiplier, $B=0$ at 1 and $B=1$ at 2). The other rules (D3'-S, S99-only, D3-type union) remain planner prototype arithmetic and are alternatives, not the plan. The "both" rows are sums over the two sectors **(sum of sourced numbers)**.

**Columns and units:** `f` the clean (ideal-sample) fraction fed to the rule, dimensionless; `shots` total shots of the sector (or both); `jobs` Quantinuum jobs of <= 10 000 shots; `hqc` HQC = sum over jobs of [5 + C(N_1q + 10 N_2q + 5 N_m)/5000], 4.9666 HQC per shot at the mean counts (ESTIMATE of cost; USD at 12.5 USD per HQC would be hqc x 12.5); `recall_floor_S999` expected recall of the 99.9 % support from clean shots alone; `P_recall_ge_0.9` probability that clean shots alone recall >= 0.9 of S999; `n_S999_below_lambda_star` S999 states with expected clean count < 6.2958; `lambda_min` minimum expected clean count (over S99 for D3'-R and the S99 rule, over S999 otherwise) at y = 0.82 x 0.7 x f

```csv
rule,f,sector,shots,jobs,hqc,recall_floor_S999,P_recall_ge_0.9,n_S999_below_lambda_star,lambda_min
D3'-R (ruling),0.05,B=0,63875,35,317546,0.940225,0.953118,45,7.24961
D3'-R (ruling),0.05,B=1,96503,20,479612,0.950075,0.993485,34,6.30634
D3'-R (ruling),0.05,both,160378,55,797157,,,,
D3'-R (ruling),0.10,B=0,34909,33,173614,0.941808,0.960341,45,7.3424
D3'-R (ruling),0.10,B=1,49203,16,244553,0.949956,0.993329,34,6.29926
D3'-R (ruling),0.10,both,84112,49,418166,,,,
D3'-R (ruling),0.15,B=0,27309,33,135860,0.94272,0.965226,47,7.7371
D3'-R (ruling),0.15,B=1,33503,13,166522,0.950151,0.993515,34,6.31865
D3'-R (ruling),0.15,both,60812,46,302382,,,,
"D3'-S (lambda* on every S999 state, LP allocation)",0.05,B=0,375000,66,1.8636e+06,0.999863,,,6.30077
"D3'-S (lambda* on every S999 state, LP allocation)",0.05,B=1,735000,84,3.65269e+06,0.999895,,,6.29653
"D3'-S (lambda* on every S999 state, LP allocation)",0.05,both,1110000,150,5.51628e+06,,,,
"D3'-S (lambda* on every S999 state, LP allocation)",0.10,B=0,190300,49,945788,0.999869,,,6.30801
"D3'-S (lambda* on every S999 state, LP allocation)",0.10,B=1,368700,47,1.83232e+06,0.999896,,,6.2979
"D3'-S (lambda* on every S999 state, LP allocation)",0.10,both,559000,96,2.77811e+06,,,,
"D3'-S (lambda* on every S999 state, LP allocation)",0.15,B=0,128600,42,639183,0.99987,,,6.31405
"D3'-S (lambda* on every S999 state, LP allocation)",0.15,B=1,246500,35,1.22503e+06,0.999895,,,6.29765
"D3'-S (lambda* on every S999 state, LP allocation)",0.15,both,375100,77,1.86422e+06,,,,
D3'-S k=4-scaled allocation (as D3'),0.05,B=0,732008,104,3.6377e+06,0.99996,,,6.30201
D3'-S k=4-scaled allocation (as D3'),0.05,B=1,1062903,117,5.28227e+06,0.999959,,,6.29606
D3'-S k=4-scaled allocation (as D3'),0.05,both,1794911,221,8.91997e+06,,,,
D3'-S k=4-scaled allocation (as D3'),0.10,B=0,368008,64,1.82886e+06,0.99996,,,6.30792
D3'-S k=4-scaled allocation (as D3'),0.10,B=1,532503,63,2.64637e+06,0.999959,,,6.29794
D3'-S k=4-scaled allocation (as D3'),0.10,both,900511,127,4.47524e+06,,,,
D3'-S k=4-scaled allocation (as D3'),0.15,B=0,246408,48,1.22458e+06,0.99996,,,6.30692
D3'-S k=4-scaled allocation (as D3'),0.15,B=1,355503,45,1.76674e+06,0.999959,,,6.29626
D3'-S k=4-scaled allocation (as D3'),0.15,both,601911,93,2.99133e+06,,,,
lambda* on S99 only (LP),0.05,B=0,48700,35,242144,0.873018,0.185866,48,6.34723
lambda* on S99 only (LP),0.05,B=1,96800,20,481085,0.950111,0.993525,34,6.31066
lambda* on S99 only (LP),0.05,both,145500,55,723228,,,,
lambda* on S99 only (LP),0.10,B=0,27000,33,134315,0.869123,0.156051,48,6.36359
lambda* on S99 only (LP),0.10,B=1,49500,16,246026,0.950029,0.993411,34,6.30791
lambda* on S99 only (LP),0.10,both,76500,49,380341,,,,
lambda* on S99 only (LP),0.15,B=0,20200,33,100536,0.822438,0.0107314,48,6.40712
lambda* on S99 only (LP),0.15,B=1,33800,13,167995,0.95026,0.993634,34,6.33564
lambda* on S99 only (LP),0.15,both,54000,46,268532,,,,
D3-type union reading (Stage A record),0.05,B=0,204320,32,1.01528e+06,0.98489,,,1.0796
D3-type union reading (Stage A record),0.05,B=1,203100,24,1.00791e+06,0.928152,,,0.533317
D3-type union reading (Stage A record),0.05,both,407420,56,2.02319e+06,,,,
D3-type union reading (Stage A record),0.10,B=0,102208,32,507960,0.984904,,,1.08011
D3-type union reading (Stage A record),0.10,B=1,101604,12,504222,0.928202,,,0.5336
D3-type union reading (Stage A record),0.10,both,203812,44,1.01218e+06,,,,
D3-type union reading (Stage A record),0.15,B=0,68128,32,338640,0.9849,,,1.07994
D3-type union reading (Stage A record),0.15,B=1,67704,12,336010,0.928157,,,0.533348
D3-type union reading (Stage A record),0.15,both,135832,44,674650,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=1",0.05,B=0,63875,35,317546,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=2",0.05,B=1,193600,29,962114,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1)",0.05,both,257475,64,1279660,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=1",0.10,B=0,34909,33,173614,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=2",0.10,B=1,99000,20,491991,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1)",0.10,both,133909,53,665605,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=1",0.15,B=0,27309,33,135860,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1); s=2",0.15,B=1,67600,16,335941,,,,
"D3'-R x s (CV_2x3_plan re-sized; s=1 at B=0, s=2 at B=1)",0.15,both,94909,49,471801,,,,
```

#### (h) CF_traj: per-arm f0', f_hit, benign fraction, f_ideal and r (with 95 % bootstrap intervals)

**Source:** `validation/CF_traj.json -> data.arms.<arm>.stats`, `data.pooled_k1.stats`, `data.A5_2x2_arm.ends.<end>` (the A5 rows use the 2x2 circuit `B0_ref06_k1` with DD cell T3 under a twirled idle model at the two T2 ends; `star` = free-induction T2*, `echo` = Hahn-echo T2). The pooled row's `r` upper end is **r_nc = 1.1151352098** (`data/cf_trajectories/r_nc.json`). Arm `B0_ref25_k1__xx` is the bit-flip-only control. C7: the k=4 mixture-estimator bias is 1.27436 [1.16999, 1.40205] (`data.C7_k4_mixture.bias_ratio`).

**Columns and units:** `K` number of Pauli trajectories; `n_zz`,`n_phasedx` gate counts of the circuit (2158 two-qubit gates at 2x3; 588 sites at 2x2); `p_ref` ideal probability of the reference string; `f0_prime` fault-free fraction (no gate error and the reference read out correctly), dimensionless; `f_hit` reference-hit fraction; `b` benign fraction of faulty trajectories within total-variation distance 1e-3 of the ideal; `f_ideal` = f0' + (1 - f0') b; `r` = f_hit / f_ideal; `min_feff_over_fideal_S99` the floor-theorem quantity (>= 0.95 required); `rho_T` information only (withdrawn statistic). Each estimate is followed by `_lo`,`_hi` = 95 % interval

```csv
arm,K,n_two_qubit,n_phasedx,p_ref,f0_prime,f_hit,f_hit_lo,f_hit_hi,b,b_lo,b_hi,f_ideal,f_ideal_lo,f_ideal_hi,r,r_lo,r_hi,min_feff_over_fideal_S99,min_lo,min_hi,rho_T
B0_ref25_k1,720,2158,3091,0.915021,0.172087,0.238733,0.224073,0.254904,0.0569444,0.0416667,0.075,0.219232,0.206583,0.23418,1.08895,1.04969,1.13613,1.08895,1.04829,1.13314,3.07375
B1_ref57_k1,240,2158,2989,0.912199,0.172365,0.257455,0.228477,0.290026,0.0875,0.0541667,0.125,0.244783,0.217195,0.275819,1.05177,0.987028,1.126,1.04031,0.980229,1.10469,3.85601
B0_ref25_k4,240,2158,3063,0.236292,0.172188,0.245912,0.218692,0.276283,0.0583333,0.0291667,0.0916667,0.220477,0.196333,0.248071,1.11536,1.03564,1.21968,1.09967,1.01952,1.18691,1.6194
B0_ref25_k1__xx,120,2158,3091,0.915021,0.172087,0.179345,0.172291,0.193086,0,0,0,0.172087,0.172087,0.172087,1.04218,1.00119,1.12202,1.04101,1.00077,1.11958,2.77239
"pooled k=1 (B0_ref25_k1 + B1_ref57_k1, 800+800 shots)",,,,,,0.24808,0.23082,0.266234,,,,0.232007,0.216487,0.249826,1.06927,1.02859,1.11514,,,,
"A5 2x2 star (T3 circuit, K=2000)",2000,588,,0.883276,1.64125e-06,0.0188678,0.0139073,0.0240857,0.028,0.021,0.0350125,0.0280016,0.0210016,0.0350141,0.673813,0.538634,0.834637,,,,
"A5 2x2 echo (T3 circuit, K=2000)",2000,588,,0.883276,0.0915231,0.288124,0.272764,0.301992,0.251,0.2305,0.269,0.319551,0.300927,0.335903,0.901652,0.884234,0.918329,,,,
```

#### (i) Cumulative QPU seconds over time (IBM open plan, 600 s allowance)

**Source:** `data/hardware/*/session.json -> jobs[*].{submitted,job_id,usage_s,n_pubs,group_shots}`, `backend`; the final cumulative 327 s equals the account counter `usage_consumed_seconds` 327 (`data/hardware/K1_2x3_ibm_kingston/account_check_after_20261006T0826Z.json`; 139 s after job 13 in `data/hardware/H0_ddrep_ibm_kingston/account_check_after_20261006T0703Z.json`; 102 s after job 12 in `data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json`). `remaining_of_600_s` is my subtraction 600 - cumulative **(sum of sourced numbers)**; the account's own remaining value after the last job is 273.

**Columns and units:** `submitted_utc` job submission time (UTC); `usage_s` billed QPU seconds of the job; `cumulative_s` running total; `remaining_of_600_s` allowance left; `n_pubs` circuits (pubs) in the job; `shots_per_pub`

The two newest rows (2026-10-06) are the `H0_ddrep` job and the K1 pilot; no QPU job has run after 2026-10-06 08:22 UTC as far as the repository records show.

```csv
submitted_utc,device,job_id,what,usage_s,cumulative_s,remaining_of_600_s,n_pubs,shots_per_pub
2026-09-22 17:48:32,ibm_fez,dapbusac505c73chv0og,canary,2,2,598,3,267
2026-09-22 20:42:56,ibm_fez,dapegkcak42c73cierv0,diag J1 (both options off),5,7,593,5,2000
2026-09-22 20:43:55,ibm_fez,dapeh3318flc739m51e0,diag J2 (XY4),4,11,589,3,2000
2026-09-22 20:44:13,ibm_fez,dapeh7ac505c73ci2o60,diag J3 (twirling),3,14,586,1,2000
2026-09-22 20:44:27,ibm_fez,dapehb4ak42c73cietig,diag J4 (XY4 + twirling),3,17,583,1,2000
2026-10-02 18:12:35,ibm_kingston,davv8504oijs73e88fvg,H0_kpilot,12,29,571,8,4000
2026-10-02 20:11:42,ibm_kingston,db01005j371s73dnmbd0,H0_ddtest,20,49,551,10,6000
2026-10-02 21:05:55,ibm_kingston,db01pddj371s73dnnqm0,H0_2x2,3,52,548,14,267
2026-10-02 21:05:57,ibm_kingston,db01pdtj371s73dnnqmg,H0_2x2,3,55,545,7,267
2026-10-02 21:05:59,ibm_kingston,db01pe04oijs73e8cl30,H0_2x2,4,59,541,2,4000
2026-10-02 21:06:00,ibm_kingston,db01pelj371s73dnnqo0,H0_2x2,22,81,519,5,13100
2026-10-02 21:06:02,ibm_kingston,db01peql7guc73cfndc0,H0_2x2,21,102,498,2,31400
2026-10-06 07:00:40,ibm_kingston,db29p6nr11fs7396e4ig,H0_ddrep,37,139,461,20,6000
2026-10-06 08:22:03,ibm_kingston,db2avbe8v0ts73c2i8b0,K1_2x3_fpilot,188,327,273,4,100000
```

#### (j) 2x2 / 2x3 / 2x4 gate counts and device requirements

**Source:** `validation/S2.json -> data.{2x2,2x3}.{per_term_cz,per_term_cz_routed,coarse_step}`, `validation/S2_2x4.json -> data.term_cost` and `data.schedule.schedule_*.rows` (the `B0_ref0_k1` rows; Heron durations from `data/hardware/H0_diag_prep/calibration_20260922T1400Z.json`).

**Columns and units:** `value` is a count of two-qubit gates (CZ, or IR CX where stated), a transpiled depth, a duration in microseconds, a dimensionless utilisation, or a ratio T2 / t_2q (the coherence time over the two-qubit gate time the device must have for f = 0.1 with T1 -> infinity). `quantity` names which. 

Note: the `per_term_ir_cx_before_transpile_*` rows are IR CX counts of each term circuit before the transpiler merges gates (so they differ from the transpiled per-term CZ rows of the 2x2 and 2x3 lattices); the same per-term table with all columns is in `reports/S2_2x4_compilation_and_device_requirement.md` (hop0 278 CX ... plaq1 66 468 CX; sum of the 13 hop/plaquette terms 71 520 exact and 16 546 fixed-angle).

```csv
lattice,kind,item,value,source
2x2,per_term_cz_all_to_all,diag,8,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop0,60,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop1,48,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop2,66,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,hop3,44,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_all_to_all,plaq0,30,validation/S2.json data.2x2.per_term_cz
2x2,per_term_cz_routed,diag,8,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop0,122,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop1,92,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop2,149,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,hop3,72,validation/S2.json data.2x2.per_term_cz_routed
2x2,per_term_cz_routed,plaq0,73,validation/S2.json data.2x2.per_term_cz_routed
2x2,coarse_step_all_to_all_cz,total,256,validation/S2.json data.2x2.coarse_step.all_to_all.cz
2x2,coarse_step_all_to_all_depth,total,736,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x2,coarse_step_routed_cz,total,618,validation/S2.json data.2x2.coarse_step.routed.cz
2x2,coarse_step_routed_depth,total,1294,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x3,per_term_cz_all_to_all,diag,20,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop0,194,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop1,48,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop2,182,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop3,184,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop4,358,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop5,156,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,hop6,44,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,plaq0,214,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_all_to_all,plaq1,764,validation/S2.json data.2x3.per_term_cz
2x3,per_term_cz_routed,diag,20,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop0,433,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop1,82,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop2,415,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop3,396,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop4,846,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop5,275,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,hop6,72,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,plaq0,497,validation/S2.json data.2x3.per_term_cz_routed
2x3,per_term_cz_routed,plaq1,1698,validation/S2.json data.2x3.per_term_cz_routed
2x3,coarse_step_all_to_all_cz,total,2164,validation/S2.json data.2x3.coarse_step.all_to_all.cz
2x3,coarse_step_all_to_all_depth,total,7325,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x3,coarse_step_routed_cz,total,5477,validation/S2.json data.2x3.coarse_step.routed.cz
2x3,coarse_step_routed_depth,total,11540,"validation/S2.json (transpiled depth, basis rz/sx/x/cz)"
2x3,per_term_ir_cx_before_transpile_exact,hop0,278,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop1,54,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop2,258,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop3,260,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop4,390,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop5,244,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,hop6,54,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,plaq0,228,validation/S2_2x4.json data.term_cost.2x3|exact
2x3,per_term_ir_cx_before_transpile_exact,plaq1,806,validation/S2_2x4.json data.term_cost.2x3|exact
2x4,per_term_ir_cx_before_transpile_exact,hop0,278,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop1,54,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop2,258,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop3,1548,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop4,390,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop5,542,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop6,260,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop7,390,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop8,244,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,hop9,54,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,plaq0,228,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,plaq2,806,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_exact,plaq1,66468,validation/S2_2x4.json data.term_cost.2x4|exact
2x4,per_term_ir_cx_before_transpile_fixed,hop0,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop1,52,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop2,280,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop3,536,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop4,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop5,536,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop6,280,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop7,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop8,272,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,hop9,52,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,plaq0,286,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,plaq1,12952,validation/S2_2x4.json data.term_cost.2x4|fixed
2x4,per_term_ir_cx_before_transpile_fixed,plaq2,484,validation/S2_2x4.json data.term_cost.2x4|fixed
2x2,"schedule[exact,all_to_all]",n_2q,256,validation/S2_2x4.json data.schedule.schedule_2_exact
2x2,"schedule[exact,all_to_all]",cz_depth,202,same
2x2,"schedule[exact,all_to_all]",duration_us,21.22,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x2,"schedule[exact,all_to_all]",qubit_time_utilisation,0.1877,same
2x2,"schedule[exact,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,625.1,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x2,"schedule[exact,all_to_all]",serial_bound_T2_over_t_2q,667.1,closed-form serial bound
2x2,"schedule[exact,heavy_hex_3]",n_2q,618,validation/S2_2x4.json data.schedule.schedule_2_exact
2x2,"schedule[exact,heavy_hex_3]",cz_depth,426,same
2x2,"schedule[exact,heavy_hex_3]",duration_us,41.24,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x2,"schedule[exact,heavy_hex_3]",qubit_time_utilisation,0.216,same
2x2,"schedule[exact,heavy_hex_3]",T2_req_over_t_2q_f0.1_T1inf,1276.8,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x2,"schedule[exact,heavy_hex_3]",serial_bound_T2_over_t_2q,1744.6,closed-form serial bound
2x3,"schedule[exact,all_to_all]",n_2q,2164,validation/S2_2x4.json data.schedule.schedule_3_exact
2x3,"schedule[exact,all_to_all]",cz_depth,1926,same
2x3,"schedule[exact,all_to_all]",duration_us,213.84,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x3,"schedule[exact,all_to_all]",qubit_time_utilisation,0.0929,same
2x3,"schedule[exact,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,11999.7,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x3,"schedule[exact,all_to_all]",serial_bound_T2_over_t_2q,9398.1,closed-form serial bound
2x3,"schedule[exact,heavy_hex_5]",n_2q,5477,validation/S2_2x4.json data.schedule.schedule_3_exact
2x3,"schedule[exact,heavy_hex_5]",cz_depth,3692,same
2x3,"schedule[exact,heavy_hex_5]",duration_us,363.78,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x3,"schedule[exact,heavy_hex_5]",qubit_time_utilisation,0.1091,same
2x3,"schedule[exact,heavy_hex_5]",T2_req_over_t_2q_f0.1_T1inf,21526.7,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x3,"schedule[exact,heavy_hex_5]",serial_bound_T2_over_t_2q,30922.2,closed-form serial bound
2x3,"schedule[exact,fakefez]",n_2q,5737,validation/S2_2x4.json data.schedule.schedule_3_exact
2x3,"schedule[exact,fakefez]",cz_depth,3749,same
2x3,"schedule[exact,fakefez]",duration_us,364.39,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x3,"schedule[exact,fakefez]",qubit_time_utilisation,0.1177,same
2x3,"schedule[exact,fakefez]",T2_req_over_t_2q_f0.1_T1inf,22500,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x3,"schedule[exact,fakefez]",serial_bound_T2_over_t_2q,31144.3,closed-form serial bound
2x4,"schedule[exact,all_to_all]",n_2q,69688,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,all_to_all]",cz_depth,68653,same
2x4,"schedule[exact,all_to_all]",duration_us,7920.58,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,all_to_all]",qubit_time_utilisation,0.0577,same
2x4,"schedule[exact,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,638742,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,all_to_all]",serial_bound_T2_over_t_2q,423712,closed-form serial bound
2x4,"schedule[exact,heavy_hex_5]",n_2q,145958,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,heavy_hex_5]",cz_depth,108091,same
2x4,"schedule[exact,heavy_hex_5]",duration_us,11033.6,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,heavy_hex_5]",qubit_time_utilisation,0.0865,same
2x4,"schedule[exact,heavy_hex_5]",T2_req_over_t_2q_f0.1_T1inf,873536,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,heavy_hex_5]",serial_bound_T2_over_t_2q,919137,closed-form serial bound
2x4,"schedule[exact,heavy_hex_7]",n_2q,148850,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,heavy_hex_7]",cz_depth,108634,same
2x4,"schedule[exact,heavy_hex_7]",duration_us,11013,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,heavy_hex_7]",qubit_time_utilisation,0.0912,same
2x4,"schedule[exact,heavy_hex_7]",T2_req_over_t_2q_f0.1_T1inf,861392,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,heavy_hex_7]",serial_bound_T2_over_t_2q,905026,closed-form serial bound
2x4,"schedule[exact,fakefez]",n_2q,148726,validation/S2_2x4.json data.schedule.schedule_4_exact
2x4,"schedule[exact,fakefez]",cz_depth,108053,same
2x4,"schedule[exact,fakefez]",duration_us,10998.2,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[exact,fakefez]",qubit_time_utilisation,0.0916,same
2x4,"schedule[exact,fakefez]",T2_req_over_t_2q_f0.1_T1inf,858529,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[exact,fakefez]",serial_bound_T2_over_t_2q,904272,closed-form serial bound
2x4,"schedule[fixed,all_to_all]",n_2q,14048,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,all_to_all]",cz_depth,13656,same
2x4,"schedule[fixed,all_to_all]",duration_us,1564.64,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,all_to_all]",qubit_time_utilisation,0.0587,same
2x4,"schedule[fixed,all_to_all]",T2_req_over_t_2q_f0.1_T1inf,126067,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,all_to_all]",serial_bound_T2_over_t_2q,85413.6,closed-form serial bound
2x4,"schedule[fixed,heavy_hex_5]",n_2q,30208,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,heavy_hex_5]",cz_depth,21216,same
2x4,"schedule[fixed,heavy_hex_5]",duration_us,2109.22,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,heavy_hex_5]",qubit_time_utilisation,0.0894,same
2x4,"schedule[fixed,heavy_hex_5]",T2_req_over_t_2q_f0.1_T1inf,163723,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,heavy_hex_5]",serial_bound_T2_over_t_2q,196788,closed-form serial bound
2x4,"schedule[fixed,heavy_hex_7]",n_2q,28925,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,heavy_hex_7]",cz_depth,19649,same
2x4,"schedule[fixed,heavy_hex_7]",duration_us,2032.7,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,heavy_hex_7]",qubit_time_utilisation,0.0891,same
2x4,"schedule[fixed,heavy_hex_7]",T2_req_over_t_2q_f0.1_T1inf,169701,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,heavy_hex_7]",serial_bound_T2_over_t_2q,188430,closed-form serial bound
2x4,"schedule[fixed,fakefez]",n_2q,28765,validation/S2_2x4.json data.schedule.schedule_4_fixed
2x4,"schedule[fixed,fakefez]",cz_depth,19484,same
2x4,"schedule[fixed,fakefez]",duration_us,1998.49,"T_s of the ASAP schedule at Heron durations (cz 68 ns, sx/x 24 ns)"
2x4,"schedule[fixed,fakefez]",qubit_time_utilisation,0.0871,same
2x4,"schedule[fixed,fakefez]",T2_req_over_t_2q_f0.1_T1inf,172796,"T2 required / t_2q for f = 0.1, T1 -> infinity"
2x4,"schedule[fixed,fakefez]",serial_bound_T2_over_t_2q,193634,closed-form serial bound
```

#### (k) Exact reference energies per lattice and sector

**Source:** `data/references.json -> references` (the output of gate E3; `validation/E3.json` PASS 85/85).

**Columns and units:** energies in lattice units (m = 3 g^2/16); `B` baryon number = twoB/2; `W` spectral width E_max - E_min of the sector block; `emax` largest eigenvalue; `dt` = pi/W the Krylov time step; `support99`, `support999` numbers of configurations carrying 99 % / 99.9 % of the ground-state weight; `PR` participation ratio. For the 2x4 sectors only the lowest levels from Lanczos are tabulated; for static-charge sectors only 3 levels are stored

```csv
lattice,g2,m,twoB,B,dim,E0,E1,E2,W,Emax,dt,support99,support999,PR
2x2,4,0.75,0,0,38,-3.64077,-0.962245,-0.850567,12.8222,9.18144,0.245012,9,16,1.47438
2x2,4,0.75,2,1,20,-1.86159,-1.81975,0.208229,9.46425,7.60266,0.331943,8,13,2.59238
2x3,4,0.75,0,0,677,-5.6026,-2.8886,-2.86518,20.0813,14.4787,0.156443,31,86,1.91384
2x3,4,0.75,2,1,426,-3.82608,-3.80173,-3.66866,16.8023,12.9763,0.186973,42,95,3.56092
2x3,4,0.75,4,2,95,-2.01182,-1.86224,-1.84389,13.4486,11.4368,0.2336,15,22,1.50427
2x3,2,0.375,0,0,677,-4.22161,-2.72359,-2.70321,12.2336,8.01204,0.256799,137,326,5.93582
2x3,2,0.375,2,1,426,-3.08661,-2.97297,-2.79396,10.2927,7.20607,0.305226,135,240,11.9219
2x3,1,0.1875,0,0,677,-4.39179,-3.42014,-3.25049,10.3818,5.98998,0.302607,396,549,33.8312
2x4,4,0.75,0,0,12843,-7.56521,-4.8436,-4.83747,27.3901,19.8249,0.114698,76,305,2.4883
2x4,4,0.75,2,1,8934,-5.78016,-5.77413,-5.65409,24.1081,18.3279,0.130313,127,470,4.78485
2x3+static r=1,4,0.75,0,0,1089,-4.21542,-3.51247,-1.87712,17.7109,13.4954,0.177382,48,133,3.19288
2x3+static r=2,4,0.75,0,0,978,-3.01275,-2.65282,-2.65198,15.7007,12.6879,0.200093,69,174,6.1483
2x3+static r=1,2,0.375,0,0,1089,-3.43963,-2.74384,-2.26699,11.2319,7.79226,0.279703,226,512,8.37376
2x3+static r=2,2,0.375,0,0,978,-2.84759,-2.50289,-2.49183,10.5054,7.65779,0.299046,268,530,14.8782
```

#### (k2) Derived quantities and the j_max = 1 truncation shift

**Source:** `data/references.json -> derived`, `-> truncation_2x2`.

**Columns and units:** `quantity` D0 meson-like gap, MB baryon mass, binding = E0(B=2) - E0(B=0) - 2 MB, V1, V2 static potentials at separations 1 and 2 (lattice units); for the truncation rows: E0_half (jmax 1/2), E0_one (jmax 1), shift = E0_one - E0_half, dim_half, dim_one (state counts in the B=0 sector)

```csv
key,quantity,value
2x3|g2=4.0,D0,2.714
2x3|g2=4.0,MB,1.77652
2x3|g2=4.0,binding,0.0377436
2x3|g2=4.0,V1,1.38718
2x3|g2=4.0,V2,2.58985
2x3|g2=2.0,D0,1.49802
2x3|g2=2.0,MB,1.135
2x3|g2=2.0,binding,0.174795
2x3|g2=2.0,V1,0.781983
2x3|g2=2.0,V2,1.37403
2x4|g2=4.0,D0,2.72162
2x4|g2=4.0,MB,1.78505
2x4|g2=2.0,D0,1.50282
2x4|g2=2.0,MB,1.15598
2x2 truncation|g2=4.0,E0_half,-3.64077
2x2 truncation|g2=4.0,E0_one,-3.64269
2x2 truncation|g2=4.0,shift,-0.00192045
2x2 truncation|g2=4.0,dim_half,38
2x2 truncation|g2=4.0,dim_one,74
2x2 truncation|g2=2.0,E0_half,-2.67121
2x2 truncation|g2=2.0,E0_one,-2.70967
2x2 truncation|g2=2.0,shift,-0.0384592
2x2 truncation|g2=2.0,dim_half,38
2x2 truncation|g2=2.0,dim_one,74
2x2 truncation|g2=1.0,E0_half,-2.71752
2x2 truncation|g2=1.0,E0_one,-3.05857
2x2 truncation|g2=1.0,shift,-0.341051
2x2 truncation|g2=1.0,dim_half,38
2x2 truncation|g2=1.0,dim_one,74
```

#### (l) The 51 plan rows and their status (2x2 hardware campaign)

**Source:** `reports/H0_2x2_full_hardware_report_20261002.md` section 2 (planner scoring); full text in Section 10.1 of this file.

**Columns and units:** `row` the plan-row id used by the report; `group` manual (33 rows) or amendment/decision (18 rows); `status` F fulfilled, FD fulfilled with deviation, ND not done. Tally F 31, FD 12, ND 8

```csv
row,group,status
0,manual,F
1.1,manual,F
1.2,manual,F
1.3,manual,F
1.4,manual,F
1.5,manual,F
2.1-2.3,manual,F
2.4,manual,F
2.5,manual,F
3,manual,F
4.1,manual,F
4.2,manual,F
4.3,manual,FD
4.4,manual,FD
5.1,manual,F
5.2,manual,F
5.3,manual,F
5.4,manual,F
6.1-6.2,manual,FD
6.3,manual,ND
6.4,manual,ND
7.1-7.2,manual,FD
7.3,manual,ND
7.5,manual,ND
8.1-8.2,manual,F
8.3,manual,FD
9.1,manual,FD
9.2,manual,ND
9.3,manual,ND
10,manual,FD
10 (error budget),manual,FD
10 (reporting),manual,FD
11,manual,FD
A1,amendment/decision,F
A2,amendment/decision,FD
A3,amendment/decision,F
A4,amendment/decision,ND
A5,amendment/decision,ND
M4.4,amendment/decision,F
D8',amendment/decision,F
D1',amendment/decision,F
D3'-f,amendment/decision,F
D3''-H0,amendment/decision,FD
D5',amendment/decision,F
C2',amendment/decision,F
C3',amendment/decision,F
H0P-Y',amendment/decision,F
D9,amendment/decision,F
prereg,amendment/decision,F
dry runs,amendment/decision,F
owner 2026-10-02,amendment/decision,F
```

#### (m) The 2x2 shot plan actually flown (rule D3' at the adopted f)

**Source:** `validation/H0_2x2.json -> data.shot_plan`.

**Columns and units:** `N4` shots per k=4 circuit; the k=1,2,3 circuits ran at the 267-shot floor; `total_coarse_shots` over all 28 coarse circuits

```csv
quantity,value
N4_B=0,13100
N4_B=1,31400
total_coarse_shots,133907
```

#### (n) S2D_levers: Aer clean fraction versus the dephasing ratio r = T2*/T2echo, per lever row (2x2 circuit on the ibm_kingston patch)

**Source:** `validation/S2D_levers.json -> data.rows.<row>.{manifest,compile}` and `data.aer.<row>.<r>` (scheduled Aer at the record of 2026-10-01 with each qubit's dephasing time replaced by r x its echo T2; 4 000 shots, reference-string and mixture estimators). `data.verdict` gives r_crit(0.1) = 0.3302 (Aer interpolated; 0.7261 analytic bound) over all rows and 0.3285 for the signed family; the pilot measured an equivalent r of about 0.172 (`validation/H0_kpilot.json`).

**Columns and units:** `row` lever row (L0_asis = the canary as is, ASAP or ALAP scheduled; L1_seed = re-seeded transpile; L2_order = reordered terms; L3_rx = fractional rx; L4_all = all levers; L1_seed_alap = the signed term family with ALAP, the row the pilot and the full run used); `n_cz`,`n_rzz` two-qubit gates; `duration_us` ASAP/ALAP critical path T_s in microseconds; `twoq_layers` two-qubit layers; `r` dephasing ratio; `f_ref`, `f_ref_lo68`, `f_ref_hi68` reference-string clean fraction with its 68 % interval; `f_mix` mixture estimator; `shots` Aer shots

```csv
row,schedule,fractional,n_cz,n_rzz,duration_us,twoq_layers,r,f_ref,f_ref_lo68,f_ref_hi68,f_mix,shots
L0_asis_asap,asap,False,663,0,47.964,455,1.0,0.11771,0.11133,0.124445,0.121716,4000
L0_asis_asap,asap,False,663,0,47.964,455,0.5,0.0538542,0.0495338,0.0585336,0.0563266,4000
L0_asis_asap,asap,False,663,0,47.964,455,0.25,0.0117438,0.00971151,0.0141505,0.0125648,4000
L0_asis_asap,asap,False,663,0,47.964,455,0.174,0.00345976,0.00265646,0.0044541,0.00357271,8000
L0_asis_alap,alap,False,663,0,47.964,455,1.0,0.165688,0.158121,0.173609,0.164426,4000
L0_asis_alap,alap,False,663,0,47.964,455,0.5,0.114258,0.107972,0.120899,0.110984,4000
L0_asis_alap,alap,False,663,0,47.964,455,0.25,0.0345248,0.0310616,0.0383504,0.0323474,4000
L0_asis_alap,alap,False,663,0,47.964,455,0.174,0.0151955,0.0128886,0.0178733,0.0136954,4000
L1_seed,asap,False,588,0,44.24,412,1.0,0.146014,0.138909,0.153472,0.14989,4000
L1_seed,asap,False,588,0,44.24,412,0.5,0.0776707,0.0724855,0.0832127,0.0814008,4000
L1_seed,asap,False,588,0,44.24,412,0.25,0.0176116,0.0151306,0.0204619,0.0178837,4000
L1_seed,asap,False,588,0,44.24,412,0.174,0.00829211,0.00657786,0.0103861,0.00814562,4000
L2_order,asap,False,584,0,37.272,350,1.0,0.18985,0.18175,0.198303,0.190489,4000
L2_order,asap,False,584,0,37.272,350,0.5,0.124268,0.117713,0.131178,0.127404,4000
L2_order,asap,False,584,0,37.272,350,0.25,0.0462605,0.0422549,0.0506262,0.0463095,4000
L2_order,asap,False,584,0,37.272,350,0.174,0.0113986,0.00939587,0.0137762,0.0112632,4000
L3_rx,asap,True,356,226,34.068,349,1.0,0.216428,0.20778,0.225428,0.213106,4000
L3_rx,asap,True,356,226,34.068,349,0.5,0.158095,0.150702,0.16584,0.155492,4000
L3_rx,asap,True,356,226,34.068,349,0.25,0.0586865,0.0541772,0.0635543,0.0579117,4000
L3_rx,asap,True,356,226,34.068,349,0.174,0.0238246,0.0209436,0.0270715,0.0243143,4000
L4_all,alap,True,356,226,34.068,349,1.0,0.243696,0.23452,0.253224,0.242642,4000
L4_all,alap,True,356,226,34.068,349,0.5,0.180531,0.172632,0.188782,0.178805,4000
L4_all,alap,True,356,226,34.068,349,0.25,0.0683512,0.063486,0.0735739,0.0677443,4000
L4_all,alap,True,356,226,34.068,349,0.174,0.0290021,0.0258261,0.0325422,0.0278078,4000
L1_seed_alap,alap,False,588,0,44.24,412,1.0,0.216083,0.207442,0.225076,0.216958,4000
L1_seed_alap,alap,False,588,0,44.24,412,0.5,0.166034,0.158458,0.173962,0.163942,4000
L1_seed_alap,alap,False,588,0,44.24,412,0.25,0.0735287,0.0684832,0.0789313,0.0725077,4000
L1_seed_alap,alap,False,588,0,44.24,412,0.174,0.0334893,0.0300781,0.0372632,0.0311589,4000
```

#### (n2) Kingston pilot: the day's Aer prediction at r = 1 (echo T2) and r = 0.174 against the measurement

**Source:** `validation/H0_kpilot.json -> data.aer_at.<circuit>` (`r=1`, `r=0.174`) and `data.decision.f_pool`.

**Columns and units:** dimensionless clean fractions per shot; the measured pooled value 0.0413 matches the r = 0.174 end (about 0.041-0.046), not the echo end (about 0.21-0.24)

```csv
circuit,aer_f_at_r_1,aer_f_at_r_0.174
B0_ref06_k1,0.211397,0.0413219
B1_ref07_k1,0.226755,0.0457617
B0_ref06_k4,0.237881,0.0554602
"MEASURED pooled (kingston, 2026-10-02)",0.041293,
```


#### (o) H0_ddrep cells: the seven DD cells of 2026-10-06 against the 2026-10-02 values (ibm_kingston, job db29p6nr11fs7396e4ig, 2 circuits x 6 000 shots per cell)

**Source:** `validation/H0_ddrep.json -> data.cells.<cell>` (`f_pool`, `f_pool_95`, `excess_hits`, `reference_hits`, `accepted`, `n_pulses_per_circuit`, `R`, `R_95`, `class`, `null_ratio`) and, for the last two columns, `validation/H0_ddtest.json -> data.decision.cells.<cell>` (cells T0, T1, T3 only; M1-M4 did not exist on 2026-10-02).

**Columns and units:** `n_pulses_total` pulses inserted over the two circuits; `accepted` accepted shots and `reference_hits` reference-string hits summed over the two circuits (12 000 shots); `excess_hits` = reference hits minus the garbage expectation 2.93; `f` pooled reference-string clean fraction with its 95 % interval; `R` = excess hits of the cell over those of T0 (T0 = 1) with its 95 % interval; `class` COLLAPSED (upper end < 0.25), INTACT (lower end > 1) or INTERMEDIATE; `null_ratio` the ratio the pulse cost alone would give; `f_20261002`, `R_20261002` the same cell on 2026-10-02. Reading: R1 False, R2 False, C1 False; the mechanism reading is "no single hypothesis".

```csv
cell,description,n_pulses_total,accepted,reference_hits,excess_hits,f,f_lo95,f_hi95,R,R_lo95,R_hi95,class,null_ratio,f_20261002,R_20261002
T0,no DD (baseline),0,1134,716,713.07,0.0817751,0.0757532,0.0881453,1,,,,1,0.0400315,1
T1,context-aware staggered X (committed H0_ddtest QPY),1724,785,464,461.07,0.0528757,0.0480506,0.05805,0.646599,0.575131,0.726947,INTERMEDIATE,0.840694,0.000466785,0.0116604
T3,client XY4 in idle windows >= 1.024 us (committed H0_ddtest QPY),488,981,641,638.07,0.0731741,0.0674826,0.0792142,0.894821,0.804175,0.995684,INTERMEDIATE,0.953771,0.112853,2.81912
M1,T1 with alternating pulse signs (same timing),1724,859,565,562.07,0.0644584,0.059122,0.0701436,0.78824,0.705743,0.88038,INTERMEDIATE,0.840694,,
M2,XX pairs in T2's 194 windows (ratio 4.0),778,974,578,575.07,0.0659492,0.0605505,0.0716968,0.806471,0.722572,0.900111,INTERMEDIATE,0.922343,,
M3,M2 with alternating signs,778,997,636,633.07,0.0726007,0.0669319,0.0786181,0.887809,0.797696,0.988102,INTERMEDIATE,0.922343,,
M4,T1 minus all pulses on hot qubits 91 and 95,1228,1322,823,820.07,0.0940459,0.0875813,0.100858,1.15006,1.04024,1.27146,INTACT,0.879885,,
```

#### (p) Pulse trains: x-pulse over-rotation epsilon_q and per-pulse cost c_q per qubit (H0_ddrep)

**Source:** `validation/H0_ddrep.json -> data.trains.per_qubit.<qubit>` (`P1` readout-corrected, `epsilon`, `epsilon_68`, `c_per_pulse`, `c_68`, `x_error_record`, `c_over_x_error`, `epsilon_RB_level_sqrt_6_x_error`) and `data.hot_qubits`. Fit rule (fixed before the data): $c_q=(P_1(\mathrm{XpXm\text{-}128})-P_1(\mathrm{XX\text{-}8}))/120$, floor$_n=P_1(\mathrm{XX\text{-}8})+(n-8)c_q$, $\epsilon_q=\arg\min_{[0,\pi/8]}\sum_{n=8,32,128}(P_1(\mathrm{XX\text{-}}n)-\mathrm{floor}_n-\sin^2(n\epsilon/2))^2$ on a 0.0001 rad grid, 68 % intervals by a parametric bootstrap (2 000 draws, seed 32).

**Columns and units:** `P1_*` readout-corrected probability of measuring 1 after a train of 8, 32 or 128 pulses (XX = repeated $X$, XpXm = alternating $+X,-X$), dimensionless; `epsilon_rad` coherent over-rotation per $x$ pulse in radians with its 68 % interval; `eps_RB_level_sqrt6xerr_rad` the planner's reference $\sqrt{6\,x_{\rm error}}$ in radians; `c_per_pulse` incoherent cost per pulse (dimensionless probability) with its 68 % interval; `x_error_record` the calibration record's `x_error` (aliased to `sx_error`); `c_over_x_error` the ratio; `hot_qubit_M4` 1 for the two qubits whose pulses cell M4 removes. Summary: $\epsilon_q\ge0.01$ rad and XX-128 minus XpXm-128 $>0.05$ on 12 of 12 qubits; $c_q>3\,x_{\rm error}$ on qubits 71 and 91.

```csv
qubit,P1_XX8,P1_XX32,P1_XX128,P1_XpXm128,epsilon_rad,eps_lo68,eps_hi68,eps_RB_level_sqrt6xerr_rad,c_per_pulse,c_lo68,c_hi68,x_error_record,c_over_x_error,hot_qubit_M4
59,0.00644395,0.0663049,0.873495,0.0301848,0.0181,0.018,0.0182,0.0336174,0.000197841,0.000172546,0.000223164,0.000188355,1.05036,0
71,0.00675333,0.0482863,0.75688,0.0916765,0.0148,0.0147,0.015,0.0297698,0.000707693,0.000673183,0.000739775,0.000147707,4.79119,0
72,0.0125912,0.0759124,0.930657,0.0248175,0.0195,0.0193,0.0196,0.0287484,0.000101886,6.55568e-05,0.00013751,0.000137745,0.739667,0
73,0.0136387,0.0830565,0.921839,0.0556041,0.0186,0.0185,0.0187,0.0356369,0.000349711,0.000320728,0.000377923,0.000211665,1.6522,0
74,0.00929054,0.0923986,0.976182,0.035473,0.0204,0.0203,0.0206,0.0376763,0.000218187,0.000196906,0.000242609,0.000236584,0.922239,0
75,0.00632695,0.0536936,0.835328,0.0280438,0.0173,0.0172,0.0174,0.0296218,0.000180974,0.000155688,0.000205661,0.000146242,1.23749,0
79,0.00340948,0.0422775,0.766962,0.0368224,0.0159,0.0158,0.016,0.0377649,0.000278441,0.000252568,0.000303574,0.000237699,1.1714,0
91,0.00768425,0.0625218,0.936605,0.137269,0.0171,0.017,0.0173,0.0362902,0.00107987,0.00104258,0.00112035,0.000219497,4.91975,1
92,0.00194346,0.0284452,0.763604,0.0913428,0.0149,0.0148,0.015,0.0447153,0.000744994,0.000705252,0.000785669,0.000333243,2.23559,0
93,0.0131801,0.0755323,0.960122,0.0474823,0.0196,0.0195,0.0197,0.0340982,0.000285851,0.000259184,0.000313863,0.000193781,1.47512,0
94,0.000350816,0.0691107,0.92475,0.0443782,0.0189,0.0187,0.019,0.0320854,0.000366895,0.000331089,0.000403159,0.000171579,2.13834,0
95,0.0144416,0.0827876,0.951134,0.0654912,0.019,0.0189,0.0191,0.0301252,0.000425413,0.000392347,0.000454426,0.000151255,2.81255,1
```

#### (q) CV_2x3_plan cells: certificate widths, convergence steps, weight and the re-sizing multiplier (S1-proxy emulation, three seeds, maximum or minimum over seeds as the column says)

**Source:** `validation/CV_2x3_plan.json -> data.criteria_by_seed.<f>.<sector>.<seed>.{CV1,CV2,CV3,CV4,CV5}`, `data.cv3_at_2Nc_information`, `data.plan.<f>.<sector>.{resized_by, final_shots_total, final_jobs, final_hqc}`, `data.E_tol` ($E_{\rm tol}=1.4225\times10^{-2}$ at $B=0$, $1.1040\times10^{-2}$ at $B=1$; `data.constants` for the thresholds). Basis `B_all | refs` (`prompts/31` ruling 1). An emulation of the plan at clean fraction $0.7f$, not a device statement.

**Columns and units:** `s_final` re-sizing multiplier; `hqc_final` HQC (rounded to an integer) of the sector at that multiplier; `cv2_certificate` the certificate read (Kato-Temple with the exact $E_1$ at $B=0$, Weinstein at $B=1$) and `cv2_threshold` its width limit; `cv2_width_N_half_max_over_seeds` and `cv2_width_N_max` the worst width over seeds at $N/2$ and at $N$ (lattice energy units); `rH_*` the Weinstein half-width $r_H$ at the same points (information at $B=0$); `KT_width_*` the Kato-Temple width (information at $B=1$, where the cluster gap makes it uninformative); `cv1_ratio_max` $[E_R(N/2)-E_R(N)]/E_{\rm tol}$ (limit 1); `cv3_dE_k4_k5_max` $E_R(B^{(4)})-E_R(B^{(5)})$ at equal shots, `cv3_ratio_to_Etol_max` its ratio to $E_{\rm tol}$ (limit 1), `cv3_dE_at_2Nc_info_max` the same at $2N_c$ shots (information); `cv4_margin_over_Etol_min` (random 2.5th percentile minus $E_R$)/$E_{\rm tol}$ at $N$ (limit 1); `cv5_W_min` captured ground-state weight (limit 0.99).

```csv
f,sector,s_final,shots_final,jobs_final,hqc_final,cv2_certificate,cv2_threshold,cv2_width_N_half_max_over_seeds,cv2_width_N_max,rH_N_half_max,rH_N_max,KT_width_N_half_max,KT_width_N_max,cv1_ratio_max,cv3_dE_k4_k5_max,cv3_ratio_to_Etol_max,cv3_dE_at_2Nc_info_max,cv4_margin_over_Etol_min,cv5_W_min,all_cv1_to_cv5_ok
0.05,B=0,1,63875,35,317546,kato_temple_exact_E1,0.1,0.0194892,0.00973772,0.229696,0.162464,0.0194892,0.00973772,0.279115,0.00309976,0.217906,0.00145608,7.93132,0.999524,True
0.05,B=1,2,193600,29,962114,weinstein,0.15,0.118073,0.0853809,0.118073,0.0853809,0.616841,0.31201,0.132269,0.00291957,0.26445,0.00231958,4.73738,0.999859,True
0.10,B=0,1,34909,33,173614,kato_temple_exact_E1,0.1,0.0251712,0.011034,0.260939,0.172931,0.0251712,0.011034,0.449226,0.00960404,0.675141,0.00206,8.41479,0.999509,True
0.10,B=1,2,99000,20,491991,weinstein,0.15,0.143297,0.0837356,0.143297,0.0837356,0.946879,0.300009,0.166833,0.0033855,0.306653,0.00196274,5.19717,0.999854,True
0.15,B=0,1,27309,33,135860,kato_temple_exact_E1,0.1,0.0267184,0.0139266,0.268819,0.194232,0.0267184,0.0139266,0.364973,0.0029331,0.20619,0.00176459,8.36328,0.999281,True
0.15,B=1,2,67600,16,335941,weinstein,0.15,0.134337,0.107993,0.134337,0.107993,0.826125,0.513501,0.138849,0.00370291,0.335404,0.00287604,5.83481,0.999758,True
```

#### (q2) The B=1 re-sizing ladder: why s = 2 (s = 1.5 fails CV2 at every f)

**Source:** `validation/CV_2x3_plan.json -> data.resize_summary.<f>.B=1.<s>` (the grid was {1.5, 2, 3, 4, 6, 8}; $B=0$ passes at $s=1$ so its ladder is empty). Columns: `shots_total` the sector's shots at that multiplier; `cv2_width_half_max` the worst Weinstein $r_H(N/2)$ over seeds on `B_all` (limit 0.15), `cv2_width_full_max` at $N$; `rH_half_B_sig_max` the same on the signal support (information: the $B_{\rm sig}$ cut keeps the width above the limit, the reason for `prompts/31` ruling 1); `ok_all_seeds` and the four criteria flags.

```csv
f,sector,s_tried,shots_total,cv2_width_half_max,cv2_width_full_max,rH_half_B_all_max,rH_half_B_sig_max,ok_all_seeds,CV1,CV2,CV4,CV5
0.05,B=1,1.5,145650,0.156787,0.09236,0.156787,0.273303,False,True,False,True,True
0.05,B=1,2,193600,0.118073,0.0853809,0.118073,0.229369,True,True,True,True,True
0.10,B=1,1.5,74700,0.166921,0.104398,0.166921,0.225461,False,True,False,True,True
0.10,B=1,2,99000,0.143297,0.0837356,0.143297,0.210536,True,True,True,True,True
0.15,B=1,1.5,51150,0.155289,0.111444,0.155289,0.222578,False,True,False,True,True
0.15,B=1,2,67600,0.134337,0.107993,0.134337,0.202807,True,True,True,True,True
```

#### (r) The oracle-width table: what the exact ground-state support of weight 1 - eps can certify (2x3, g^2 = 4)

**Source:** `validation/CV_2x3_plan.json -> data.oracle_width.<sector>.rows.<eps>` (reproduces the planner prototype `scratch/planner/oracle_width_20261005.json` to $3.2\times10^{-14}$, 196 fields; `data.oracle_width_reproduction`). `E1` is the exact first excited level (the $B=0$ gap $E_1-E_0=2.714$; at $B=1$ the cluster gap is 0.0244). For each cut $S_\varepsilon$ (the smallest set carrying $1-\varepsilon$ of the ground-state weight, plus the references) the table gives the Ritz error and the certificates of the *oracle* basis, i.e. the best any support of that size can do.

**Columns and units:** `eps` the weight cut; `size_S_eps_union_refs` number of states; `ER_minus_E0` Ritz error (lattice units); `rH` Hamiltonian residual = Weinstein half-width; `rH_estimate` the planner's estimate $\sqrt{\sum_{n\notin B}(E_0-H_{nn})^2|\Omega_n|^2}$; `W` captured weight and `one_minus_W`; `kt_width_exact_E1` Kato-Temple width $r_H^2/(E_1-E_R)$ (blank where the Ritz value is not below $E_1$, so the bound does not apply); `gap_holds` whether $r_H<E_1-E_R$. At $B=0$ even the oracle $S_{999}$ has $r_H=0.265$ and the Weinstein width reaches 0.1 only at $\varepsilon=10^{-4}$ (173 states); the Kato-Temple width is $0.0259$ already at $S_{999}$.

```csv
sector,eps,size_S_eps_union_refs,ER_minus_E0,rH,rH_estimate,W,one_minus_W,kt_width_exact_E1,gap_holds
B=0,0.01,31,0.0579401,0.608693,0.753279,0.990595,0.00940546,0.139495,True
B=0,0.001,86,0.00805673,0.264705,0.304772,0.999037,0.000962875,0.0258945,True
B=0,0.0003,116,0.00240824,0.144916,0.168288,0.999703,0.000297298,0.00774474,True
B=0,0.0001,173,0.000977034,0.100163,0.110841,0.9999,9.97644e-05,0.00369792,True
B=0,3e-05,231,0.000293686,0.0557288,0.0612972,0.999971,2.94854e-05,0.00114445,True
B=0,1e-05,288,0.000102949,0.0334254,0.0364659,0.99999,9.97844e-06,0.00041168,True
B=0,1e-06,429,1.21832e-05,0.0124195,0.0129707,0.999999,9.96221e-07,5.68332e-05,True
B=1,0.01,42,0.0526099,0.553735,0.682156,0.990385,0.00961541,,False
B=1,0.001,95,0.00716494,0.235486,0.269152,0.999027,0.000972936,3.22564,False
B=1,0.0003,130,0.0022323,0.132281,0.147202,0.9997,0.000299678,0.790908,False
B=1,0.0001,165,0.000878776,0.0901342,0.0982597,0.999903,9.74948e-05,0.346038,False
B=1,3e-05,211,0.000293714,0.0547243,0.0580958,0.999971,2.94745e-05,0.124456,False
B=1,1e-05,242,0.000103058,0.0331099,0.0345999,0.99999,9.87792e-06,0.0452007,False
B=1,1e-06,306,1.12374e-05,0.011571,0.0119051,0.999999,9.66837e-07,0.00549961,True
```

#### (s) The K1 pilot: 2x3 on ibm_kingston (job db2avbe8v0ts73c2i8b0), the two signed k = 1 circuits, 10^5 shots each

**Source:** `validation/K1_2x3_fpilot.json -> data.circuits.<circuit>`, `data.pooled`, `data.decision`, `data.prediction_prereg`. Pooled result: 0 reference hits in $2\times10^5$ shots against 0.190735 expected from garbage; $f_{\rm hit}=-1.2528\times10^{-6}$ with 95 % interval [$-1.2528\times10^{-6}$, $2.2977\times10^{-5}$]; $\hat f_{\rm ideal}=-1.1235\times10^{-6}$, 95 % upper end $2.0605\times10^{-5}$; decision NO-GO, firm (GO-B $\ge10^{-3}$, GO-A $\ge3\times10^{-4}$); readout minimum diagonal 0.9358; 188.0 s billed; account 273 s left.

**Columns and units:** `reference_int_index` the circuit's reference configuration; `p_reference` its ideal output probability (dimensionless); `garbage_acceptance_a` the decoder's random acceptance of 20-qubit strings; `routed_cz` CZ count after routing; `scheduled_duration_us` ALAP duration in $\mu$s; `n_xy4_pulses` inserted pulses; `accepted` accepted shots of $10^5$ (garbage level is $10^5a$ = 64.6 and 40.6); `distinct_accepted` distinct accepted strings; `garbage_expected_ref_hits` $=10^5\times2^{-20}$; `f_hit_hi95`, `f_hat_ideal_hi95` 95 % upper ends; `pred_f_gates_layout_no_idle` the preregistered gate-only prediction on the routed layout and `pred_expected_ref_hits_no_idle` the hits it implies (including garbage); the idle-aware ends of the bracket predict garbage only (0.0954 hits per circuit).

```csv
circuit,sector,reference_int_index,p_reference,sector_dim,garbage_acceptance_a,routed_cz,scheduled_duration_us,n_xy4_pulses,shots,accepted,distinct_accepted,garbage_expected_ref_hits,reference_hits,f_hit_hi95,f_hat_ideal_hi95,pred_f_gates_layout_no_idle,pred_expected_ref_hits_no_idle
B0_ref117_k1,B=0,117,0.928357,677,0.000645638,5659,411.152,2408,100000,58,57,0.0953674,0,4.72052e-05,4.23314e-05,1.67113e-05,1.36752
B1_ref29_k1,B=1,29,0.928308,426,0.000406265,5659,410.768,2404,100000,45,42,0.0953674,0,4.72077e-05,4.23336e-05,1.67429e-05,1.36986
```

#### (t) K0: the 2x3 circuit B0_ref25_k1 routed onto ibm_kingston, on two calibration records (a model, not a measurement)

**Source:** `validation/K0_2x3_2x4.json -> data.2x3.committed` and `data.2x3.live` (the verdict record is `committed`, the 2026-10-02 record; `live` is the 2026-10-06 06:52Z record). `S_idle` in nats; `f_idle_aware_*` $=f_{\rm gates}e^{-S_{\rm idle}}$ on the ALAP schedule at the echo $T_2$ and at $T_2^*=0.174\,T_2^{\rm echo}$ (without the 2x2-transferred XY4 gain, which did not replicate). `f_ceiling_2q` $=(1-\epsilon_{2,\min})^{n_{CZ}}$ with the record's best CZ error; `f_best_patch_bound` best CZ, one-qubit and readout error everywhere; `f_gates_layout` the gate-and-readout product on the chosen layout. This block supersedes the IBM row of block (f) (5 477 CZ, ceiling $1.14\times10^{-2}$), which used the plain level-3 circuit that is not exact.

```csv
record,stamp,fingerprint8,last_update_date,routed_cz,active_qubits,alap_duration_us,eps2_min,f_ceiling_2q,f_best_patch_bound,f_gates_layout,S_idle_echo_nats,f_idle_aware_echo,S_idle_T2star_nats,f_idle_aware_T2star,eps2_needed_for_f_0.05,best_edge_misses_by_factor,garbage_ref_hits_per_circuit_1e5_shots,exactness_max_abs_delta,leakage
committed,20261002T1906Z,e4ecac38,2026-10-02T13:06:57-06:00,5659,21,410.256,0.000816415,0.00983329,0.0029669,6.06884e-06,24.774,1.05654e-16,74.169,3.73174e-38,0.000529375,1.54223,0.0954,1.47019e-12,2.04281e-13
live,20261006T0652Z,b948ddc8,2026-10-06T00:52:19-06:00,5659,21,411.152,0.000883702,0.00671723,0.00204042,1.67078e-05,23.0309,1.66237e-15,67.9413,5.20442e-35,0.000529375,1.66933,0.0954,1.61297e-12,2.01505e-13
```

#### (u) Calibration-record statistics of ibm_kingston on the two K0 records (day-to-day variation)

**Source:** `validation/K0_2x3_2x4.json -> data.records.<record>.stats`. Between the 2026-10-02 and 2026-10-05/06 full records 1 110 leaves changed in the six families (`data/hardware/H0_ddrep_prep/live.json -> diff_against`: ratios 0.102 to 111.3). Columns: CZ error statistics over the 342 calibrated CZ keys (dimensionless), median $\sqrt{x}$ and readout errors, median $T_1$ and $T_2$ in $\mu$s, and the minima of `x_error` and `sx_error` (equal: the record aliases the two). The medians move by about 1.5 to 7 percent (my reading of the table); the single-circuit clean fraction moved by 2.04x (block (o)), so the record's summary statistics do not carry the variation that matters.

```csv
record,stamp,cz_error_min,cz_error_p10,cz_error_median,cz_error_mean,sx_error_median,measure_error_median,T1_median_us,T2_median_us,x_error_min,sx_error_min,n_cz_calibrated,n_cz_uncalibrated
committed,20261002T1906Z,0.000816415,0.00114591,0.00180416,0.00549304,0.00024671,0.00897217,228.897,147.265,9.99091e-05,9.99091e-05,342,10
live,20261006T0652Z,0.000883702,0.00125281,0.00188416,0.00576294,0.000242951,0.00836182,220.859,137.054,9.80754e-05,9.80754e-05,342,10
```

### Suggested plots

| # | plot | block and columns | how |
|---|---|---|---|
| 1 | **Timeline of gate verdicts** | (a): `date`, `gate`, `status` | scatter or strip chart, x = date, y = gate name (sorted by first date), colour = PASS / FAIL, marker size = `criteria_total`; annotate FAILs with `criteria_passed/criteria_total` |
| 2 | **Clean fraction of every hardware measurement (log y)** | (b): `run`, `f`, `lo`, `hi`, `statistic` | error bars on a log axis, x = run in time order, symbol by `statistic`; put the gate-only prediction 0.2195 (canary) and the signed bar 0.1 (and 0.05) as horizontal lines; shows the fall from 0.22 (model) to 6.65e-4 (fez measured), the rise to 0.127 (kingston with XY4, 2026-10-02) and, from block (b)'s new rows, the 2026-10-06 return to 0.073-0.082 and the 2x3 upper limit below 1e-4 |
| 3 | **DD A/B test** | (c): `cell`, `f`, `f_lo95`, `f_hi95`, `R`, `null_ratio` | bar chart of `f` with error bars; second panel `R` with its interval against the pulse-cost null (`null_ratio`) and the adoption threshold R >= 1.25; T1 is the collapsed cell |
| 4 | **Energy error and certificate for the 2x2 run** | (d): `E_R`, `E0_exact`, `weinstein_lo/hi`, `kato_temple_lo/hi`; (d2) random-basis `E_R_p2.5/p97.5/mean` | for each sector draw the exact E0 as a line, the B_sig E_R as a point with the Weinstein and Kato-Temple intervals as nested bars, and the random-equal-size 2.5-97.5 % band; also plot `abs_error` (log y) for B_sig vs B_all to show that B_all is exact by construction |
| 5 | **Garbage-only vs hardware** | (d2) `garbage_only` rows | single panel: histogram placeholder (all 100 seeds equal E0), shows that white noise reproduces the B_all energy |
| 6 | **Per-state counts vs exact weight** | (d3): `n_s`, `mu_s`, `ground_state_weight`, `in_B_sig` | scatter, x = exact weight (log), y = count (log), horizontal line at `mu_s`; colour by `in_B_sig`; shows which states carry signal above the noise expectation |
| 7 | **Support growth with Krylov order** | (e): `k_max`, `B_all`, `B_sig`, `shots`, `sector_dim` | two panels (one per sector), x = k_max, lines for B_all and B_sig as a fraction of `sector_dim`, secondary axis `shots` (log) to show that growth tracks shots |
| 8 | **Device landscape for 2x3** | (f): `device`, `f_gate_only_mean`, `f_mem_low/mid/high` | horizontal bar chart on a log x-axis of `f_gate_only_mean`, with a range bar from `f_mem_high` to `f_mem_low` for the Quantinuum rows; vertical lines at 0.1 and 0.05 |
| 9 | **Cost of a 2x3 campaign vs clean fraction** | (g): rows with `sector` = both: `f`, `hqc`, `shots`, `rule` | log-log lines, x = f, y = hqc, one line per rule; mark D3'-R; secondary y for shots; add the 1/f guide |
| 10 | **Near-clean correction** | (h): `arm`, `f_hit`, `f_ideal`, `r` with intervals | dot plot of r with error bars per arm and the pooled row, horizontal lines at 1 and r_nc = 1.115; second panel f_hit vs f_ideal vs f0_prime per arm; A5 rows show the opposite sign under idle dephasing |
| 11 | **QPU budget burn-down** | (i): `submitted_utc`, `cumulative_s`, `remaining_of_600_s` | step plot of cumulative seconds vs time with the 600 s line; label jobs by `what` |
| 12 | **Idle dephasing prediction vs measurement** | (n): `r`, `f_ref` for `L1_seed_alap`, `L4_all`; (n2) | line plot of Aer f vs r (log y) for each row with 68 % bands; overlay the measured kingston pilot f = 0.0413 and the H0_2x2 f = 0.127 (with XY4) as horizontal lines; mark r_crit = 0.33 |
| 13 | **Circuit cost by lattice** | (j): rows `coarse_step_*_cz`, `schedule[...]` `duration_us`, `T2_req_over_t_2q_f0.1_T1inf` | grouped bar chart on log y: CZ count (all-to-all vs routed) for 2x2, 2x3, 2x4; second panel the T2/t_2q requirement vs Heron's harmonic mean 1038 (a horizontal line) |
| 14 | **Per-term gate cost** | (j) rows `per_term_cz_all_to_all`, `per_term_ir_cx_before_transpile_*` | stacked or grouped bars per term for each lattice; shows plaq1 dominating at 2x3 and 2x4 (93 % of the 2x4 IR CX) |
| 15 | **Exact spectrum** | (k): `lattice`, `twoB`, `E0`, `E1`, `E2`, `support999`, `dt` | bar or table plot of E0 and gaps by sector; scatter of `support999` vs `dim` (log-log) to show sparsity; `PR` vs g2 for the 2x3 B=0 sector |
| 16 | **Plan fulfilment** | (l): `group`, `status` | stacked bar of F / FD / ND per group (manual 33 rows, amendments 18 rows) and overall (31 / 12 / 8) |
| 17 | **Day-to-day variation of the same circuits** | (o): `cell`, `f`, `f_lo95`, `f_hi95`, `f_20261002` for T0, T1, T3; (u) | paired bars (2026-10-02 vs 2026-10-06) with 95 % error bars for T0 / T1 / T3; annotate the ratio 2.04 for T0 and R_T3 2.819 vs 0.895; second panel the record statistics of (u) as a percent change to show that the summary statistics barely move while the clean fraction doubles |
| 18 | **H0_ddrep ratios and classes** | (o): `cell`, `R`, `R_lo95`, `R_hi95`, `null_ratio`, `class` | forest plot of R per cell on a log x-axis with the lines R = 1, R = 0.25 (collapse threshold) and R = 1.25 (adoption threshold); colour by class (M4 INTACT, the rest INTERMEDIATE); mark the 2026-10-02 R_T3 = 2.819 and R_T1 = 0.012 as hollow points |
| 19 | **x-pulse over-rotation per qubit** | (p): `qubit`, `epsilon_rad`, `eps_lo68`, `eps_hi68`, `eps_RB_level_sqrt6xerr_rad`, `c_over_x_error`, `hot_qubit_M4` | dot plot of epsilon_q with 68 % bars per qubit and the RB-level estimate as a second marker; second panel c_q / x_error_record with the line at 3; highlight qubits 91 and 95 |
| 20 | **Pulse-train signal** | (p): `P1_XX8`, `P1_XX32`, `P1_XX128`, `P1_XpXm128` | per-qubit lines of P1 against train length (8, 32, 128) for XX and the XpXm-128 end point; shows the coherent growth ($\sin^2$) of the uncompensated train |
| 21 | **2x3 plan: convergence margins** | (q): `f`, `sector`, `cv2_width_N_half_max_over_seeds`, `cv2_threshold`, `cv3_ratio_to_Etol_max`, `cv1_ratio_max`, `cv4_margin_over_Etol_min`, `cv5_W_min` | small-multiples grid, one panel per criterion, bars per (f, sector) against the limit line; shows that B=1 at s = 2 sits 4-21 % below the 0.15 limit while B=0 has more than a factor 3.7 of room on Kato-Temple |
| 22 | **Why B=1 needs s = 2** | (q2): `s_tried`, `cv2_width_half_max`, `rH_half_B_sig_max`, per `f` | width at N/2 versus s (1.5, 2) with the 0.15 limit; B_all and B_sig side by side |
| 23 | **Oracle width table** | (r): `sector`, `eps`, `size_S_eps_union_refs`, `rH`, `kt_width_exact_E1`, `W` | log-log of r_H against 1 - W (or against size) for B=0 and B=1 with horizontal lines at 0.1 and 0.15; the B=0 Kato-Temple curve on the same axes shows that H1 is met two orders of magnitude earlier |
| 24 | **Campaign cost: base vs re-sized** | (g): rows `D3'-R (ruling)` and `D3'-R x s` with sector = both | grouped bars of HQC at f = 0.05, 0.10, 0.15 (797 157 / 418 166 / 302 382 base; 1 279 660 / 665 605 / 471 801 re-sized); optional shots on a secondary axis |
| 25 | **K1: what the null excludes** | (s) and (b) K1 rows | log-x plot of the clean-fraction scale: the K1 95 % upper bound 2.06e-5 (arrow), the preregistered no-idle gate-only prediction 1.67e-5, the GO-A / GO-B thresholds 3e-4 / 1e-3, the signed bar 0.1 and the 2x2 values 0.04-0.13; shows the 2x3 pilot below every threshold |
| 26 | **Budget burn-down (extended)** | (i): 14 rows | the plot-11 step chart now ends at 327 s used, 273 s left; label the two 2026-10-06 jobs |

**What a good chart script can add:** a second multi-panel figure "the 2026-10-06 reversal" (plots 17, 18, 19 side by side) shows the day-to-day baseline change, the failed XY4 replication and the over-rotation measurement on one page; and the original "story of the clean fraction" figure (plots 2, 3, 12) should now end with the 2026-10-06 points (0.0818 without DD, 0.0732 with XY4, and the K1 upper limit 2.06e-5 on the 2x3 axis) instead of ending at the 2026-10-02 high (model 0.22, measured 6.65e-4 on fez, 0.041 on kingston without DD, 0.113-0.127 with XY4 on that day only).

## 12. Glossary

Terms in alphabetical order. **(project label)** marks names invented inside this project (mostly by its planner agent), which are not standard terms.

- **$a$ (random acceptance)** *(project symbol)*: the fraction of uniformly random bit strings that the decoder accepts into a sector; $a=\dim/4096$ at 2x2 ($0.00927734375$ for $B=0$, $0.0048828125$ for $B=1$), $0.146\,\%$ at 2x3.
- **Accepted shot / yield**: a shot whose bit string passes all decoder checks; yield = accepted shots divided by shots. Not the same as a clean shot.
- **Aer**: Qiskit's classical simulator (`qiskit-aer`); `AerSimulator.from_backend(...)` builds a noise model from a device calibration.
- **ALAP / ASAP**: "as late as possible" / "as soon as possible" scheduling of gates in a circuit; ALAP writes the idle waits as explicit `delay` instructions and moves qubits' first gates later, so qubits idle in $|0\rangle$ (which does not dephase) rather than in superposition.
- **Amendment 01**: the project's signed modification of the manual (`proposal/amendment_01_devices_and_budgets.md`): items 1-3 signed 2026-09-23, items 4-5 open.
- **B (baryon number)**: conserved quark number divided by the number of colours; $B=0$ vacuum sector, $B=1$ one-baryon sector. Project key `twoB` = $2B$. Also, loosely, $B$ or $|B|$ = the support (see **support**).
- **$B_{\rm all}$, $B_{\rm sig}$** *(project labels, `prompts/24` decision P9)*: $B_{\rm all}$ = every accepted state of the sector; $B_{\rm sig}$ ("signal support") = states whose count exceeds the uniform-noise expectation $\mu_s=Na/\dim$ at the one-sided $3\sigma$ Poisson level.
- **BFS**: breadth-first neighbour growth; a classical control that adds Hamiltonian neighbours of the current support.
- **Braket / Azure**: Amazon Braket and Microsoft Azure Quantum, cloud routes to IonQ and Quantinuum devices.
- **Calibration fingerprint (rule D9)** *(project label)*: a sha256 hash of the calibration-record numbers the prediction reads; submission requires the live hash to equal the preregistered one.
- **Calibration drift (day-to-day variation)** *(descriptive term)*: the change of a device's calibration record between days (on `ibm_kingston`, 1 110 values changed between 2026-10-02 and 2026-10-06, by factors 0.102 to 111.3); the clean fraction of the same frozen circuits moved by a factor 2.04 between those days, more than any decoupling effect seen on 2026-10-06.
- **Canary** *(project term)*: the first small QPU job (3 pubs x 267 shots on `ibm_fez`, 2.0 s) whose result decided whether the main run would go ahead.
- **CF_traj** *(project gate)*: Pauli-trajectory decomposition proving that the reference-hit excess is a near-clean term; also yields $r_{nc}$.
- **CIPSI**: configuration interaction by perturbation with selection; classical selected-CI method that grows a subspace by scoring Hamiltonian neighbours $|\langle c|H|\psi_R\rangle|^2/(H_{cc}-E_R)$.
- **Circuit family**: the 28 (2x2) or 44 (2x3) coarse-step circuits = references $\times\ k=1..4$.
- **Clean fraction $f$**: probability that a shot carries no error at all (manual Step 4.4); see also $f_0$, $f_{\rm hit}$, $f_{\rm ideal}$.
- **Clifford / T gate / non-Clifford**: gate classes in fault-tolerant quantum computing; non-Clifford gates (such as arbitrary rotations) are expensive to protect by error correction.
- **Codeword / codec / decoder**: the bit string assigned to a physical basis state; the module that maps states to bit strings; the per-shot checker that rejects non-physical strings.
- **Coarse step** *(manual term)*: one circuit $\prod_\gamma e^{-iH_\gamma k\Delta t}$ for a reference configuration, order $k=1..4$.
- **Coarse-step order $k$**: the multiple of $\Delta t$ used in the circuit.
- **Context-aware DD**: dynamical decoupling in which neighbouring qubits receive mutually orthogonal pulse patterns so that $ZZ$ crosstalk is also cancelled (arXiv:2403.06852).
- **Corner / interior vertex**: lattice sites with two / three link ends; they use 3 / 4 qubits.
- **CV0-CV5** *(project criteria, `prompts/30`, amended by `prompts/31`)*: convergence and weighted-coverage criteria for the 2x3 plan check (gate `CV_2x3_plan`): CV0 structural checks; CV1 $E_R(N/2)-E_R(N)\le E_{\rm tol}$ (convergence in shots); CV2 the certificate width at $N/2$ and $N$ meets H1 / H2 (Kato-Temple with the exact $E_1$ at $B=0$, width $\le0.1$; Weinstein $r_H\le0.15$ at $B=1$); CV3 $E_R(B^{(4)})-E_R(B^{(5)})\le E_{\rm tol}$ (convergence in the Krylov order, the $k=4\to5$ step); CV4 better than random bases of equal size by at least $E_{\rm tol}$; CV5 captured weight $W\ge0.99$. Evaluated on $B_{\rm all}\cup$ references.
- **CZ / RZZ / ZZPhase**: two-qubit gates: controlled-Z (IBM native), $e^{-i\varphi Z\otimes Z/2}$ (ion-trap native), and Quantinuum's name for the latter (angle in half-turns).
- **D3', D3'-R, D3'-S, D3-type union** *(project labels)*: shot-sizing rules. D3': every sector state must get $\lambda^*$ expected clean counts from the $k=4$ circuits at $0.7f$ (used at 2x2, infinite at 2x3); D3'-R ("recall"): $\lambda^*$ on every state of $S_{99}$ plus recall of $S_{999}\ge0.9$ with probability $\ge0.95$ (signed as the minimum 2x3 sizing); D3'-S: $\lambda^*$ on every state of $S_{999}$; D3-type union: the manual's eq. (5) rule scaled by $1/(0.7f)$.
- **DD (dynamical decoupling)**: sequences of $\pi$-pulses in idle windows that cancel slowly varying phase errors; each pulse costs its own gate error. **XY4**: the four-pulse sequence $X\,Y\,X\,Y$.
- **Devicewatch** *(project script `h0_devicewatch.py`)*: a free metadata poll that declares a device ready only when its status is `active` and every CZ error is published; `operational` alone is not enough (the 2026-10-06 record of `ibm_kingston` read operational while in maintenance).
- **Dirac sea**: the vacuum reference configuration (odd sites doubly occupied, even sites empty, no flux).
- **Dressed-site basis**: the gauge-invariant basis built from local singlets at each vertex (spin-network basis).
- **Dry run**: running the real submission/analysis path on a simulator before any hardware spend.
- **$E_0$, $E_R$**: exact ground-state energy; Ritz energy (lowest eigenvalue in the chosen subspace).
- **echo $T_2$ / free-induction $T_2^*$**: dephasing time measured with one refocusing pulse (the number in IBM calibration records) / of free evolution (what an idle qubit in a circuit feels).
- **Electric term**: the part of $H$ proportional to $g^2 j(j+1)$.
- **eHQC**: the Quantinuum credit unit on its emulators.
- **$\epsilon_q$ (over-rotation) and $c_q$ (per-pulse cost)** *(project labels, gate `H0_ddrep`)*: the coherent angle in radians by which one $x$ pulse of qubit $q$ over-rotates, and its incoherent error per pulse, fitted from pulse trains of 8, 32 and 128 pulses (XX-$n$: $n$ repeated $X$; XpXm-$n$: alternating $+X,-X$, which cancels a coherent over-rotation). Measured $\epsilon_q=0.0148$-$0.0204$ rad on all 12 patch qubits.
- **$E_{\rm tol}$** *(project constant, `prompts/30`)*: $E_R(R\cup\text{top 80 \% of }S_{999})-E_0$, the Ritz error the manual's own recall target tolerates; $1.4225\times10^{-2}$ ($B=0$) and $1.1040\times10^{-2}$ ($B=1$) at 2x3.
- **Executor / planner / reviewer / runner / scribe**: the project's agent roles (Section 4.4).
- **$f_0, f_0'$**: fault-free fraction (no gate error); $f_0'$ includes correct readout of the reference string.
- **$f_{\rm hit}$** *(project label)*: reference-string clean fraction: (count of the circuit's most probable ideal string minus accidental hits) / (shots $\times$ ideal probability $\times$ readout factor).
- **$f_{\rm ideal}$, $\hat f_{\rm ideal}$** *(project labels)*: ideal-sample fraction (shots that sample the ideal output distribution to within TV distance $10^{-3}$: fault-free plus benign-fault shots) and its device estimator $f_{\rm hit}/r_{nc}$.
- **$f_T$** *(project label, withdrawn)*: tail-class clean fraction; inflated by noise scattering.
- **Floor theorem** *(project term)*: the effective clean rate of each state is at least $f_{\rm ideal}(1-2\delta/p_c)$.
- **Firm (NO-GO)** *(project term, gate `K1_2x3_fpilot`)*: a decision is called firm when the point value and both ends of the 95 % interval fall in the same class.
- **Gate (project sense)**: a script whose result is recorded in `validation/<GATE>.json`; **validation gate** vs **measurement gate** (Section 4.3).
- **Garbage-only / random-equal-size baselines** *(project terms)*: control analyses of the 2x2 run: uniformly random bit strings at the same shot counts through the decoder; random subsets of the sector codewords of the same size as $B_{\rm sig}$.
- **Gauss's law**: the local constraint that colour charge cancels at every site; physical states satisfy $G_a(x)|\psi\rangle=0$.
- **Gauge theory / SU(2) / staggered quarks / link / plaquette / Kogut-Susskind**: see Section 2.1.
- **Givens rotation / Gray code / multiplexed rotation**: building blocks of the exact structured circuits (two-level rotations, ordering of control patterns, rotations controlled on many qubits).
- **Hamiltonian $H$, residual $r_H$**: the energy operator; $r_H=\|(H-E_R)\psi_R\|$.
- **H0_ddrep, K0, K1** *(project gate names)*: H0_ddrep = the one-job replication on `ibm_kingston` of the XY4 gain and the context-aware collapse, with four mechanism cells and four pulse-train pubs (2026-10-06); K0 = the model analysis of how the 2x3 circuit routes and what clean fraction a calibration record allows on `ibm_kingston` (`K0_2x3_2x4`); K1 = the 2x3 clean-fraction pilot on `ibm_kingston` (`K1_2x3_fpilot`, 2026-10-06).
- **Hot qubits** *(project term)*: the two patch qubits (91 and 95) that carry the most pulses in cell T1 and whose pulses cell M4 removes (qubit 91 is also the patch's worst $T_1$/$T_2$ qubit in the record, 99 / 68 $\mu$s, `prompts/32`).
- **Heavy-hex, Heron (r2)**: IBM's qubit connectivity pattern and processor generation (156 qubits). **Nighthawk**: IBM's newer square-lattice processor.
- **HQC**: Hardware Quantum Credit, Quantinuum's billing unit, $\mathrm{HQC}=5+C(N_{1q}+10N_{2q}+5N_m)/5000$ per job ($C$ shots).
- **Idle window / idle budget $S_{\rm idle}$**: time a qubit waits while others are gated / the resulting relaxation error in nats, $S_{\rm idle}=S_{T_1}+S_{T_2}$.
- **Intertwiner label $\iota$**: label distinguishing two gauge-singlet combinations at a vertex.
- **IR (intermediate representation)**: the project's backend-independent circuit gate list.
- **Iceberg code**: a distance-2 error-detecting code $[[k+2,k,2]]$ for trapped ions.
- **Kato-Temple / Weinstein**: error-bound formulas for an eigenvalue from a residual (Section 2.7); "gap-assumed" means they assume the nearest exact level to $E_R$ is the ground state; at 2x3 the project reads Kato-Temple with the *exactly known* $E_1$ for the $B=0$ width (owner decision 2026-10-05).
- **Krylov space**: the span of $e^{-ik\Delta t H}|b_0\rangle$.
- **$\lambda^*=6.2958$**: the Poisson mean at which a count of at least 3 has probability 0.95.
- **Leakage**: weight of a circuit's output outside the valid codeword space (required below $10^{-9}$).
- **Link consistency**: the decoder check that the two ends of a link agree on its flux bit.
- **M1-M4, T0-T3 (cells)** *(project labels, `H0_ddtest`, `H0_ddrep`)*: dynamical-decoupling variants run on the same two circuits: T0 none, T1 context-aware staggered $X$, T2 client XY4 in every window $\ge256$ ns, T3 client XY4 in windows $\ge1.024\ \mu$s, M1 T1 with alternating pulse signs, M2 XX pairs in T2's windows, M3 M2 with alternating signs, M4 T1 minus the pulses on qubits 91 and 95.
- **Measurement gate**: see Gate.
- **Mixture estimator** *(project term)*: fits one weight separating the ideal distribution from uniform noise over all accepted strings.
- **Near-clean string / near-clean term (rule M4.4)** *(project terms)*: a string with a few errors that still passes all decoder checks; the additional term in the yield model.
- **NO-GO / GO-A / GO-B / AMBIGUOUS** *(project decision words)*: outcomes of preregistered go rules.
- **COLLAPSED / INTACT / INTERMEDIATE** *(project classes, `H0_ddrep`)*: a cell's ratio $R=X_i/X_0$ of excess reference hits to those of the no-DD cell is COLLAPSED if its 95 % upper end is below 0.25, INTACT if its lower end is above 1, else INTERMEDIATE.
- **Oracle-width table** *(project term, `prompts/31`)*: for each cut $\varepsilon$ the Ritz error and certificate widths of the exact (oracle) support of weight $1-\varepsilon$; the statement of what the best possible support of that size certifies (block (r)).
- **Participation ratio (PR)**: effective number of configurations in a state, $1/\sum_b|c_b|^4$.
- **Patch**: the set of physical qubits used; **rule R1'** *(project)*: exhaustive embedding search scored by the idle-aware clean fraction.
- **Pauli twirling**: random Pauli gates around each two-qubit gate, undone afterwards; reshapes errors but does not reduce the average error.
- **PhasedX**: Quantinuum native one-qubit rotation $R_z(b)R_x(a)R_z(-b)$.
- **Preregistration**: writing circuits, shots, decision rule and prediction to a committed file before the device data exist.
- **Pub**: one circuit with its parameters submitted in a Qiskit SamplerV2 job.
- **Pulse train** *(project term)*: a circuit of $n$ repeated single-qubit pulses on every qubit used to measure the pulse's own error (block (p)).
- **QCCD**: quantum charge-coupled device architecture (trapped ions physically moved between zones; all-to-all connectivity). **QCUP**: the DOE/ORNL Quantum Computing User Program. **QPY**: Qiskit's circuit serialization format. **QPU**: quantum processing unit.
- **QEC**: quantum error correction.
- **$r_{nc}$** *(project label)*: near-clean correction = upper 95 % bound of the pooled $f_{\rm hit}/f_{\rm ideal}(10^{-3})$ from CF_traj; $1.115$.
- **$r_{\rm crit}$, $r_{\rm eff}$** *(project labels)*: the break-even ratio $T_2^*/T_2^{\rm echo}$ above which $f\ge0.1$ (0.3285 preregistered) and the ratio the pilot measured (0.0974).
- **Recall $R_\varepsilon$**: $|B\cap S_\varepsilon|/|S_\varepsilon|$.
- **Reference configuration**: starting configuration $|b_0\rangle$ of a circuit (Dirac sea, one-meson states, diquark states).
- **Re-sizing multiplier $s$** *(project label, `prompts/30`/`31`)*: the uniform factor applied to a sector's D3'-R shots (grid 1.5, 2, 3, 4, 6, 8; smallest passing wins); plan of record $s=1$ at $B=0$, $s=2$ at $B=1$.
- **Ritz value / Ritz vector**: eigenvalue / eigenvector of $H$ restricted to a subspace.
- **Rule C22 (noise saturation)** *(project label)*: once $Na/\dim\gtrsim5$ the sector is filled by noise alone.
- **S99, S999** *(project notation)*: smallest sets carrying 99 % / 99.9 % of the ground-state weight (the 99.9 % support).
- **Saturation parameter $Na/\dim$**: expected accidental hits per sector state.
- **SKQD / SQD**: sample-based Krylov / sample-based quantum diagonalization.
- **Stage E / Stage P / Stage T / Stage R / Stage A** *(project labels)*: E = emulator run, P = hardware pilot (Quantinuum plan), T = the DD test, R = the full 2x2 run (`prompts/24`), A = the native-gate compilation (`prompts/26`).
- **Static charge**: an infinitely heavy quark used to probe the potential $V(r)$.
- **Structured gates**: the exact circuit construction of gate S2.
- **Support**: the set $B$ of decoded configurations used for the projected diagonalization.
- **$T_1$, $T_2$**: energy-relaxation and dephasing times. **PTA** (Pauli-twirled approximation) *(project usage)*: the analytic bound that charges every error as fatal.
- **Tier A / B / C** *(project, `prompts/27`)*: preregistered levels of a 2x3 hardware claim (Section 9.5).
- **TV distance**: total-variation distance between two probability distributions.
- **VQE**: variational quantum eigensolver (the older approach in the literature).
- **Weight $W(B)$**: $\sum_{s\in B}|c_s|^2$ (captured ground-state weight).
- **Yield model**: $y=0.82f+(1-f)a+$ near-clean term.
- **0.82 readout factor**: the manual's survival of 20-qubit readout at 1 % error each.
- **30-minute rule**: the laptop rule of Section 4.3.

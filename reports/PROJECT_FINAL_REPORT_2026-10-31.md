# su2qc-skqd: final project report and hand-over (2026-10-31)

- **Date:** 2026-10-31.  **Git commit at writing:** `855c48b2` (`git rev-parse --short HEAD`), branch `master`.
- **Why this file exists:** the owner (Digonto) is shutting down the laptop and will continue on a desktop from a
  GitHub clone plus a USB backup.  This report is meant to let him, or a fresh Claude session with no other context,
  pick up every thread.
- **Prompt in force:** the coordinator's brief of 2026-10-31 ("write the detailed final report of the whole
  su2qc-skqd project").  The newest numbered plan is `prompts/36a_CV_2x4_plan_fix_20261019.md`; later work was done
  on direct owner requests recorded in `prompts/LOG.md` and in the compression study's `notes/`.
- **Earlier full reports** (superseded by this one, kept for detail): `reports/PROJECT_FULL_REPORT_20261015.md`,
  `reports/PROJECT_FULL_REPORT_20261013.md`, `reports/PACKAGE_FULL_REPORT_20261006.md`,
  `reports/PACKAGE_FULL_REPORT_20261005.md`, `reports/SESSION_HANDOVER_20260925_1002.md`,
  `reports/SESSION_HANDOVER_20260921_24.md`, and the 2x2 hardware story
  `reports/H0_2x2_full_hardware_report_20261002.md`.
- **Rule used throughout:** every number is copied from a file in this repository, named next to it (usually
  `validation/<GATE>.json`, `data/...json`, or a generated report).  Numbers marked *(my arithmetic)* are sums or
  ratios of cited numbers.  Nothing was re-run for this report (a reading/writing task only).
- **Privacy:** the paper draft is private and is not quoted here (section 10 gives only its
  status).  No credential, key or token appears in this file.

> **Two status files are out of date; trust this report and the JSON files.**  `CLAUDE.md` (project section) still
> says the QPU spend is 17.0 s and that the owner's nine changes of `prompts/20` are open; both are stale (section 4
> and 11).  `validation/gates.md` and `reports/PROJECT_STATUS.md` were last regenerated on 2026-10-21 and do not yet
> list `QV_2x4_02..05`, `SKQD_2x4`, `C2_XY4`, `C2_ECHO` results (section 3).  `validation/BLOCKED.md` (git-ignored,
> local only) carries a STOP from 2026-10-06 20:09 UTC that was superseded two hours later (section 11).

---

## Contents

1. Executive summary
2. Physics and method
3. Gate-by-gate history and status table
4. Hardware history (IBM)
5. Perlmutter GPU CI
6. The circuit-compression study (genie-opus)
7. Noise models and the noisy SKQD campaign
8. The classical selected-CI baseline
9. Quantinuum Nexus
10. Paper and talk status
11. Open items and next steps (prioritised)
12. Desktop set-up guide
13. File map
14. Appendix: every report and validation JSON

---

## 1. Executive summary

### 1.1 What was asked (the project goal)

Implement and test **neural-enhanced sample-based Krylov quantum diagonalization (SKQD)** for **SU(2) lattice gauge
theory with staggered quarks on $2\times L_x$ ladders** ($L_x = 2, 3, 4$), following the reference document
`proposal/SU2QC_Project2_rev2_SKQD_Implementation_Manual.md` (SU2QC Project 2, rev. 2).  In plain words:

- **Lattice gauge theory** puts a quantum field theory on a grid: quarks (matter particles) sit on the grid points
  ("sites"), and the force-carrying gauge field sits on the connections between them ("links").  **SU(2)** is the
  symmetry group of the gauge field (a two-colour cousin of the strong force).  **Staggered quarks** are a way to put
  fermions on a lattice with one fermion component per site.  A **ladder** is a grid two sites tall and $L_x$ sites
  long.
- **SKQD** uses a quantum computer only to *choose* a small set of basis states: it prepares time-evolved states,
  measures them, and the classical computer then diagonalizes the exact Hamiltonian inside the span of the measured
  states.  The answer is *variational* (never below the true ground energy) whatever the quantum device does, and it
  carries a mathematical error bar (a "certificate", section 2.4).
- The work is organised as **gates**: a named check with a script that writes `validation/<GATE>.json` with
  `"status": "PASS"` or `"FAIL"` (Rule 1 of `CLAUDE.md`: prose never decides a gate).

### 1.2 Main achievements (each with its file)

1. **Physics core verified.** Gauss's law, state counts, exact reference energies and the manual's Tables 1-4 are
   reproduced: gates E1 (23 criteria), E2 (51), E3 (85), S1 (12) all PASS (`validation/E1.json`, `E2.json`,
   `E3.json`, `S1.json`; table in `validation/gates.md`).
2. **Exact, gauge-invariant circuits for all three ladders.**  A structured synthesis engine builds the coarse
   time-step circuits exactly (deviation from the exact state $\le 3.2\times10^{-13}$ at $2\times4$,
   `validation/S2_2x4.json` criterion C5).  The cost is the problem: $2\times4$ needs 69,688 CZ gates per coarse step
   all-to-all (`validation/S2_2x4.json`; `prompts/LOG.md` 2026-09-30).
3. **A real 2x2 SKQD run on IBM hardware** (ibm_kingston, 2026-10-02): gate H0_2x2 PASS 8/8, exact ground energies
   recovered in both sectors from hardware samples (`validation/H0_2x2.json`), after a long diagnosis of why the
   first attempt on ibm_fez failed (idle-time dephasing, section 4).
4. **Hardware verdicts for 2x3 and 2x4 on superconducting devices:** no-go, by model and by a measured pilot
   (gate K1_2x3_fpilot: clean fraction consistent with zero, $\hat f_{\rm ideal} = -1.1\times10^{-6}$, 95 % upper end
   $2.1\times10^{-5}$, `validation/K1_2x3_fpilot.json` `data.decision`).
5. **Noiseless SKQD at 2x4 on GPUs** (Perlmutter, 2026-10-22..26): gate SKQD_2x4 PASS 9/9; $E_0$ certified in both
   sectors; $E_R - E_0 = 8.1\times10^{-3}$ ($B=0$) and $1.3\times10^{-3}$ ($B=1$) at the plan point
   (`validation/SKQD_2x4.json` criterion K4).
6. **Circuit compression by an AI-driven loop (genie-opus study):** at $2\times4$ the two-qubit count falls from
   71,548 (frozen) to 1,492 (class A v2, exact on every state) and 580-763 (class B v2, exact on its own input);
   factors 48x and 106x (`2x4_compression_using_ai_v1/MANUAL_lgt_circuit_compression.md` §1.2).  The middle plaquette
   term alone went from 66,468 to 220 two-qubit gates (`2x4_compression_using_ai_v1/reports/003-full-compression-report.md`).
   A Lean 4 project (11 files, 66 machine-checked `#print axioms` statements, no `sorry`) proves the reusable
   algebra (section 6.6).
7. **Noisy SKQD simulations with the compressed circuits** under published Quantinuum H2-2 / Helios-1 noise models:
   $E_0$ inside the certificate in 30 of 30 (cell, sector) rows
   (`2x4_compression_using_ai_v1/noise/reports/004-noisy-skqd-campaign.md` §4).
8. **Every frozen and compressed family passed Quantinuum's free H2-2 syntax checker** (602 jobs, 0 final errors), except
   the frozen 2x4 set, whose upload Nexus refused with HTTP 500 (536 + 66 jobs *(my arithmetic)*; section 9).
9. **Classical baseline computed:** CIPSI (a selected-configuration-interaction method) at equal subspace size beats
   SKQD's energy in 31 of 32 non-trivial rows (`prompts/LOG.md` 2026-10-29; `reports/selected_ci_baseline.md`).
10. **A private paper draft (v3, 24 pages)** and a talk deck exist (section 10).

### 1.3 Current state in one page

| area | state | evidence |
|---|---|---|
| exact physics (E1-E3, S1) | PASS, reproduced on cloud and laptop | `validation/gates.md` |
| circuits 2x2 / 2x3 / 2x4 | exact; frozen families signed; compressed families kept separate | `validation/S2.json`, `S2_2x4.json`, `QV_2x4_01.json`; study §6 |
| IBM hardware | 2x2 done (H0_2x2 PASS); 2x3/2x4 no-go; 327 s of the 600 s account used | section 4 |
| Quantinuum hardware | **no shots run, 0 HQC spent**; syntax checks only | section 9 |
| GPU CI (Perlmutter) | 60 jobs run; 2x4 noiseless SKQD PASS; 2x3 four-class campaign mostly done | section 5 |
| noisy simulations | 2x3 campaign 33 (IBM and Quantinuum models) and the compressed-family campaign (report 004) done | sections 5.5, 7 |
| paper | private draft v3, 24 pages; placeholders open | section 10 |
| test suite | one known pre-existing failure `tests/test_q0p_plan.py::test_d3r_plan_reproduces_prototype` | section 11 |
| open decisions | $r_{\rm nc}$ value, amendment items 4-5, Aer bug report filing, QV_2x4_05 ruling, deferred class-2 jobs, the held branch | section 11 |

---

## 2. Physics and method

### 2.1 The model: SU(2) Kogut-Susskind ladder with staggered quarks

**Hamiltonian** (Kogut-Susskind form, the standard lattice Hamiltonian; `src/skqd/hamiltonian.py` docstring, as
transcribed in `2x4_compression_using_ai_v1/MANUAL_lgt_circuit_compression.md` §1.0):

$$H=-\tfrac12\sum_{l=(x\to y)}\bigl[\eta_l\,\psi^\dagger_{x}U(l)\psi_{y}+{\rm h.c.}\bigr]+m\sum_x(-1)^{x_1+x_2}n_x
+\frac{g^2}{2}\sum_lE_l^2-\frac1{2g^2}\sum_P\bigl(W_P+W_P^\dagger\bigr).$$

- $\psi_x$: quark field at site $x$ (two colours); $U(l)$: the SU(2) matrix on link $l$; $n_x$: number of quarks on
  site $x$ (0, 1 or 2); $(-1)^{x_1+x_2}$: the staggering sign.
- First term: **hopping** (a quark moves along a link and changes the link's gauge field).  Second: **mass**.
  Third: **electric energy** $E_l^2 = j_l(j_l+1)$, $j_l$ the link's spin.  Fourth: **plaquette** (magnetic) term,
  $W_P$ the trace of the product of the four link matrices around a square ("plaquette").
- Parameters used everywhere: coupling $g^2 = 4$, mass $m = 3g^2/16 = 0.75$ (`skqd.exact.mass_default`).
- **Truncation:** $j_{\max} = \tfrac12$, so each link is either "no flux" ($j=0$) or "flux" ($j=\tfrac12$).  The
  error of this truncation at $2\times2$, $g^2=4$ is a ground-energy shift of $-0.0019$ ($-3.6408 \to -3.6427$ at
  $j_{\max}=1$; `reports/E3_exact_references.md`, truncation table).
- **Baryon number** $B$: a conserved quark count relative to the "Dirac sea" (the empty-staggered reference).  The
  project works in sectors $2B = 0$ ("$B=0$") and $2B = 2$ ("$B=1$").

**Gauss's law** (the local constraint that colour charge flowing into a site balances the charge on it) selects the
**physical states**.  Counts (`validation/E2.json`; `reports/E2_counts_codewords_decoder.md`):

| lattice | qubits | physical states | sector dims $\{2B:\dim\}$ |
|---|---|---|---|
| 2x2 | 12 | 82 | $\{0{:}38,\ 2{:}20, \dots\}$ |
| 2x3 | 20 | 1,727 | $\{0{:}677,\ 2{:}426,\dots\}$ |
| 2x4 | 28 | 37,165 | $\{0{:}12843,\ 2{:}8934,\dots\}$ |

**Exact reference energies** at $g^2 = 4$ (`reports/E3_exact_references.md` Table 1, from `validation/E3.json`), in
lattice units:

| lattice | $B$ | $E_0$ | next levels | $\Delta t = \pi/W$ | support 99 % / 99.9 % |
|---|---|---|---|---|---|
| 2x2 | 0 | $-3.6408$ | $-0.9622$ | 0.245 | 9 / 16 |
| 2x2 | 1 | $-1.8616$ | $-1.8197,\ 0.2082$ | 0.332 | 8 / 13 |
| 2x3 | 0 | $-5.6026$ | $-2.8886$ | 0.156 | 31 / 86 |
| 2x3 | 1 | $-3.8261$ | $-3.8017,\ -3.6687$ | 0.187 | 42 / 95 |
| 2x4 | 0 | $-7.5652$ | $-4.8436$ | 0.115 | 76 / 305 |
| 2x4 | 1 | $-5.7802$ | $-5.7741,\ -5.6541$ | 0.130 | 127 / 470 |

$W$ is the sector's spectral width ($E_{\max} - E_0$).  "Support 99.9 %" is the number of basis states that carry
99.9 % of the exact ground state's probability (section 2.5).  The $B=1$ sectors have a **near-degenerate cluster**:
lowest splittings 0.042 (2x2), 0.024 (2x3) and 0.006 (2x4) (`reports/E3_exact_references.md`).  This tiny gap is why
$B=1$ is always the harder certificate.

### 2.2 Gauge-invariant basis and codec

- **Basis** (`src/skqd/basis.py`, `src/skqd/vertex.py`): "dressed" states labelled by link spins $\{j_l\}$, quark
  numbers $\{n_x\}$ and an **intertwiner** label $\{\iota_x\}$ (which of the two independent SU(2)-singlet couplings
  a vertex with three flux-carrying links uses).  Every basis state satisfies Gauss's law by construction.
- **Codec** (`src/skqd/codec.py`; "codeword" = the bit string that stores one basis state on qubits): each vertex owns
  a contiguous block of qubits in site order.  A corner vertex (2 link ends) uses 3 qubits $(q_1,q_2,q_3)$: the two
  flux bits and $q_3 = n/2$ when the flux parity is even, $q_3 = 0$ when $n=1$ ($q_3=1$ is a **flag**, i.e. an
  invalid string).  An interior vertex (3 link ends) uses 4 qubits, the last being $n/2$, a flag, or $\iota$.  Each
  link's flux is stored twice (once at each end), which gives built-in error detection.
- **Decoder** (`src/skqd/codec.py` docstring): split the measured string into vertex blocks, reject any flagged
  vertex, reject any link whose two copies disagree, read the labels, reject the wrong sector, look the state up.
- **Random-string acceptance** (how often pure noise passes the decoder): 2.002 % at 2x2 (exhaustive), 0.146 % at
  2x3, 0.012 % at 2x4 (sampled; `reports/E2_counts_codewords_decoder.md`).  Per sector at 2x2:
  $a_{B=0} = 38/4096 = 0.00928$, $a_{B=1} = 20/4096 = 0.00488$ (`validation/H0_2x2.json` criterion R4).

### 2.3 The SKQD workflow

1. **References** (`skqd.krylov.references`): at $B=0$ the Dirac sea plus one "one-meson" state per link; at $B=1$
   one "diquark" state per even site.  Counts 5+2 (2x2), 8+3 (2x3), 11+4 (2x4)
   (`2x4_compression_using_ai_v1/MANUAL_lgt_circuit_compression.md` §1.0).
2. **Coarse step circuits:** for each reference and $k = 1..4$ (and $k=5$ for the convergence check), one circuit
   that applies each Hamiltonian term's exact exponential $e^{-ik\Delta t H_\gamma}$ in a fixed order
   ("coarse step"; a single first-order product step at angle $k\Delta t$).  Circuit sets: 28 (2x2), 44 (2x3),
   60 + 15 at $k=5$ (2x4).
3. **Sample** each circuit in the computational basis; **decode** each shot; the basis $B_{\rm all}$ = references
   plus every accepted state.
4. **Diagonalize** $H$ projected on $B_{\rm all}$: the lowest eigenvalue is the **Ritz value** $E_R \ge E_0$.
5. **Certify** (section 2.4) and check **convergence** (section 2.5).

The "neural-enhanced" part of the manual (an ML ranker of candidate states) was tested in S1 (leakage-safe ridge
model, Spearman rank correlation 0.862 / 0.888, `validation/S1.json`) but gate M1 ("ML uses credited only under
Step 7.5") is still open; no ML result is claimed.

### 2.4 Certificates

With $\psi_R$ the Ritz vector and the **residual** $r_H = \lVert (H - E_R)\psi_R\rVert$ (`src/skqd/skqd.py`,
`certify`):

- **Weinstein interval:** $[E_R - r_H,\ E_R]$.  It always contains *some* exact eigenvalue; it is the ground-energy
  interval when $r_H < E_1 - E_R$ ("gap assumption").  Used at $B=1$ (near-degenerate cluster).
- **Kato-Temple interval:** $[E_R - r_H^2/(\alpha - E_R),\ E_R]$ with $\alpha$ a lower bound on the first excited
  level.  The project uses $\alpha = $ exact $E_1$ at $B=0$ (owner confirmation
  `data/owner_decision_20261005_kt_certificate.md`; `certify(...).kt_rigorous`).  Much tighter than Weinstein when the
  gap is large (2.72 at 2x4 $B=0$).
- **$E_{\rm tol}$** (energy tolerance used by the convergence criteria; `skqd.skqd.h1_energy_tolerance`):
  $E_{\rm tol} = E_R(\text{references} \cup \text{top } 80\,\% \text{ of } S_{99.9}) - E_0$.  Values: 0.01423 / 0.01104
  at 2x3 $B=0/1$ (`validation/CV_2x3_plan.json`, LOG 2026-10-05), 0.014495 / 0.012534 at 2x4
  (`validation/CV_2x4_plan.json` criterion A2).

### 2.5 Shot rules and the convergence checks CV1-CV5

- **$S_{99.9}$** ("S999"): the smallest set of basis states holding 99.9 % of the exact ground state's weight
  (`skqd.skqd.exact_support`, $\epsilon = 10^{-3}$).  **Recall** = fraction of $S_{99.9}$ inside the sampled basis;
  **$W$** = exact ground-state weight inside the basis.
- **$\lambda^*$**: the smallest Poisson mean with $P(X \ge 3) \ge 0.95$, i.e. "seen at least three times with 95 %
  probability": $\lambda^* = 6.2958$ (`skqd.skqd.poisson_lambda_star`; manual eq. (5) rounds it to 6.3).
- **Manual eq. (5):** $S \ge \lambda^*/(0.82\, f\, p)$ shots per circuit, with $f$ the **clean-shot fraction**
  (probability that a shot carries no error), 0.82 the readout survival factor and $p$ the configuration's ideal
  probability (`skqd.skqd.shot_rule`).
- **Rule D3'** (`scripts/h0_support_plan.py`, prompts/16): the $k=4$ circuits get the smallest multiple of 100 shots
  that gives every sector state an expected clean count $\ge \lambda^*$ at $0.7\times f$; other circuits a floor of
  267 shots.
- **Rule D3'-R** (`reports/2x3_shot_rule_estimator_ruling_20261003.md`, prompts/28-29): $\lambda^*$ on every
  $S_{99}$ state by a minimum-shot linear programme with floor 267, then the $k=4$ circuits topped up until
  $P(\text{clean-only recall of } S_{99.9} \ge 0.9) \ge 0.95$, with yield $y = 0.82\times0.7\times f$.  At 2x4,
  $f=1$: 14,547 ($B=0$) and 24,404 ($B=1$) shots (`validation/CV_2x4_plan.json` A3).
- **Convergence re-sizing** (prompts/30-31, 36a): the plan is multiplied by the smallest $s$ on a grid at which
  CV1, CV2, CV4, CV5 hold at half and full plan on an exact emulation (3 seeds).  2x4 result: $s=1$ at $B=0$,
  $s=12$ at $B=1$ (final 14,547 / 294,000 shots; `validation/CV_2x4_plan.json` A4; owner sign-off
  `data/owner_decision_20261021_2x4_cv_plan.md`).
- **CV checks** (`scripts/gate_CV.py`; definitions as in
  `2x4_compression_using_ai_v1/noise/reports/004-noisy-skqd-campaign.md` §1):
  - **CV0** (structural): nested shot prefixes, $E_R$ non-increasing, $E_R \ge E_0 - 10^{-9}$.
  - **CV1:** $E_R(N/2) - E_R(N) \le E_{\rm tol}$ (energy stable when shots are halved).
  - **CV2:** certificate width at $N/2$ and $N$: Kato-Temple width $r_H^2/(E_1-E_R) \le 0.1$ at $B=0$; Weinstein
    $r_H \le 0.15$ at $B=1$; $E_0$ inside.
  - **CV3:** $E_R(k\le4) - E_R(k\le5) \le E_{\rm tol}$ at equal shots (Krylov depth converged).
  - **CV4:** every prefix beats the 2.5th percentile of 200 random equal-size bases by at least $E_{\rm tol}$
    (seeds 23..222).
  - **CV5:** $W \ge 0.99$.
- **Why 2x4 $B=1$ needs 20x the shots of $B=0$** (294,000 / 14,547 *(my arithmetic: 20.2)*): $B=0$ reads the
  Kato-Temple width with a large gap (2.72, `prompts/36_2x4_full_pipeline.md` R4), while $B=1$, with its 0.006
  cluster splitting, must read the Weinstein radius $r_H$ itself; $r_H$ scales like $\sqrt{1-W}$ (planner ruling
  `prompts/36a_CV_2x4_plan_fix_20261019.md`: "r_H ~ 10 sqrt(1 - W) at 2x4 B=1 as at 2x3"), so $r_H \le 0.15$ needs a missed weight well
  below the $\approx 10^{-3}$ that D3'-R targets.  The re-sizing ladder (CV2 fails up to $s=8$ with $r_H(sN/2)$ up to
  0.167, passes at $s=12$) is in `validation/CV_2x4_plan.json` (`data.resize_ladder`, `data.plan.final`).

### 2.6 Conventions (fixed; do not change without re-running E1-E3)

- `src/skqd/su2.py`: left generator $L_a = -J_a^T$, right generator $R_a = +J_a$; matter charge
  $Q_a = \psi^\dagger \tfrac{\sigma_a}{2}\psi$; $[L_a, U] = -(T_a U)$, $[R_a, U] = +(U T_a)$, $T_a = \sigma_a/2$.
- `src/skqd/lattice.py`: site index $x_1 L_y + x_2$; links oriented $+x$, $+y$; phase $\eta = i$ on x-links and
  $(-1)^{x_1+x_2}$ (start site) on y-links.
- `src/skqd/codec.py`: qubit layout above (section 2.2).
- `src/skqd/reference_sim.py`: qubit $k$ = bit $k$ (little-endian, index $=\sum_k q_k 2^k$, Qiskit's statevector
  convention); a Qiskit counts key is reversed to get the package's bit tuple.
- CUDA-Q result strings list qubit 0 first (`prompts/LOG.md` L5 row, 2026-09-14).

---

## 3. Gate-by-gate history and status

"Measurement gate" = a gate whose PASS means "preregistered, measured, verified, consistent", not "the number is
good".  Dates are the `validation/gates.md` run times unless stated.  Status from each `validation/<GATE>.json`
`status` field.

### 3.1 Foundations (exact physics and emulation)

| gate | what | status | date | key numbers (file) |
|---|---|---|---|---|
| E1 | Gauss's law, kernel, two builders agree | **PASS** 23/23 | 2026-09-14 | 82-dim kernel at 2x2; builders agree on all 82 levels (`validation/E1.json`) |
| E2 | state counts, codewords, decoder | **PASS** 51/51 | 2026-09-14 | Table 2 reproduced; 2x3 random acceptance 0.146 % (`validation/E2.json`) |
| E3 | exact references, $\Delta t$ | **PASS** 85/85 | 2026-09-14 | Table 1 above (`validation/E3.json`) |
| S1 | emulated support recall, controls | **PASS** 12/12 | 2026-09-14 | 2x3 recall of $S_{99.9}$ at $f=0.1$, $2\times10^5$ shots: 1.0 ($B=0$), 0.989 ($B=1$); 2x4 proxy 0.934 (`validation/S1.json`) |
| CS | term structure in codeword space | **PASS** 4/4 | 2026-09-14 | `validation/CS.json` |

### 3.2 Circuits and budgets (laptop, IBM-oriented)

| gate | what | status | date | key numbers (file) |
|---|---|---|---|---|
| L2 | Qiskit = numpy reference, 2x2 | **PASS** | 2026-09-15 | max deviation $3.7\times10^{-15}$ over 35 circuits (`prompts/LOG.md`; `validation/L2.json`) |
| L3 | transpiled CZ counts (generic synthesis) | **FAIL** (expected) | 2026-09-15 | 35,606 CZ all-to-all, 55,459 routed vs budget 250 (`validation/L3.json`) |
| L4 | Aer noisy sampling, 2x2 | **PASS** (on GPU) | 2026-09-22 | yields 0.458 / 0.441 vs model 0.378 / 0.376; job 58741899 (`validation/L4.json`) |
| L5 | CUDA-Q = reference, 2x2 | **PASS** | 2026-09-15 | `qpp-cpu` target; the `nvidia` target needs compute capability $\ge 7.0$ (`validation/L5.json`) |
| S2 | structured exact circuits, CZ budget | **FAIL** on cost only | 2026-09-15 | 2x2 618 routed (budget 250), 2x3 5,477 (budget 500); exactness $1.9\times10^{-14}$ (`validation/S2.json`) |
| S2_fixed | fixed-angle generator | **FAIL** | 2026-09-15 | cost floor 3,736 routed CZ at 2x3 (`validation/S2_fixed.json`) |
| S2D | device-resolved $f$ budgets | **FAIL** | 2026-09-16 | 2x2 FakeFez mean $f$ 0.1248; 2x3 0.0534 < 0.1; shots/sector 4,605,472 (`validation/S2D.json`) |
| S2D_idle | S2D on the idle-aware $f$ | **FAIL** | 2026-09-22 | live ibm_fez echo-$T_2$ mean $f$ 0.00671 (`validation/S2D_idle.json`); not in the gate table |
| L4_fez | L4 on FakeFez | **PASS** | 2026-09-16 | `validation/L4_fez.json` |
| S3_smoke | S3 pipeline at 2 shots | **FAIL** by construction | 2026-09-16 | `validation/S3_smoke.json` |
| S3 | GPU throughput calibration | **PASS** (calibration only; recall criterion not evaluated) | 2026-09-22 | 0.0199 s/shot at 20 qubits vs laptop 3.198 (`CLAUDE.md` status; `validation/S3.json`) |
| S2_2x4 | 2x4 circuits compiled and verified | **PASS** 12/12 | 2026-10-01 | 69,688 CZ, $T_2/t_{2q}$ needed 638,742; GPU leakage $1.10\times10^{-12}$ (`validation/S2_2x4.json`) |
| ENC_compare | alternative encodings | **PASS** (measurement) | 2026-10-08 | dedup codec 20 → 13 qubits at 2x3, two-qubit gates ×0.926; not adopted (`validation/ENC_compare.json`) |

### 3.3 IBM hardware chain (details in section 4)

| gate | what | status | date | key numbers |
|---|---|---|---|---|
| H0P | H0 preparation, FakeFez | **PASS** 16/16 | 2026-09-16 | `validation/H0P.json` |
| H0P_rehearsal | D3' plan rehearsal | **PASS** 18/18 | 2026-09-21 | `validation/H0P_rehearsal.json` |
| H0P_ibm_fez | live-calibration prediction | **PASS** 18/18 | 2026-09-22 | `validation/H0P_ibm_fez.json` |
| H0_dryrun | analysis on dry-run counts | **PASS** 9/9 | 2026-09-30 | `validation/H0_dryrun.json` |
| H0_canary | 3-pub canary, ibm_fez | **FAIL** (NO-GO) | 2026-09-22 | measured $f$ 0.0255 vs predicted 0.2195 (`validation/H0_canary.json`) |
| H0_diag | diagnostic, ibm_fez | **FAIL** 6/8 | 2026-09-22 | idle relaxation confirmed (section 4) (`validation/H0_diag.json`) |
| H0_model | scheduled-Aer post-diction | **PASS** 5/5 | 2026-09-30 | ratio 1.05 at $T_2^*$ vs 49.58 at echo $T_2$ (`prompts/LOG.md` 2026-09-30) |
| S2D_levers | 2x2 duration levers, kingston | **PASS** 9/9 | 2026-10-02 | best duration 0.710× the canary (`validation/S2D_levers.json`) |
| H0_kpilot | kingston pilot | **FAIL** 8/9 (NO-GO) | 2026-10-02 | $f_{\rm pool}$ 0.0413 (`validation/H0_kpilot.json`) |
| H0_ddtest | client-side DD A/B test | **PASS** 8/8 | 2026-10-02 | XY4 adopted, $f$ 0.1129 (`validation/H0_ddtest.json`) |
| H0_2x2 | full 2x2 SKQD on kingston | **PASS** 8/8 | 2026-10-02 | exact $E_0$ in both sectors from $B_{\rm all}$ (`validation/H0_2x2.json`) |
| H0_ddrep | DD replication | **PASS** 8/8 (gain not replicated) | 2026-10-06 | $R_{T3}$ 0.895 (`validation/H0_ddrep.json`) |
| K0_2x3_2x4 | kingston readiness of 2x3/2x4 | **PASS** 6/6 (verdict NO-GO) | 2026-10-06 | 5,659 routed CZ, idle-aware $f \approx 10^{-15}$ (`validation/K0_2x3_2x4.json`) |
| K1_2x3_fpilot | 2x3 clean-fraction pilot | **PASS** 8/8 (decision NO-GO, firm) | 2026-10-06 | section 4.4 (`validation/K1_2x3_fpilot.json`) |
| H0, H1, H2, P1, M1 | the manual's hardware/endpoint/ML gates | **open** | — | `validation/gates.md` |

### 3.4 Shot plans, estimators and convergence

| gate | what | status | date | key numbers |
|---|---|---|---|---|
| CF_traj | Pauli-trajectory decomposition; near-clean ratio $r_{\rm nc}$ | **PASS** 7/7 | 2026-10-05 | pooled $r(10^{-3})$ 1.069 [1.029, 1.115]; $r_{\rm nc} = 1.115$ (`validation/CF_traj.json`, `data/cf_trajectories/r_nc.json`) |
| CF_estimator_2x2_info | 2x2 $f$ relabelled $f_{\rm hit}$ | **PASS** (information) | 2026-10-05 | `validation/CF_estimator_2x2_info.json` |
| CV_2x2_info | CV curves on H0_2x2 counts | **PASS** (information; saturation) | 2026-10-05 | `validation/CV_2x2_info.json` |
| Q0P_2x3_plan | rule D3'-R, GO rule v3 | **PASS** 7/7 | 2026-10-05 | `validation/Q0P_2x3_plan.json` |
| CV_2x3_plan | 2x3 convergence and re-sizing | **PASS** 37/37 | 2026-10-05 | $E_{\rm tol}$ 0.01423 / 0.01104 (`validation/CV_2x3_plan.json`) |
| CV_2x4_plan | 2x4 plan, acceptance, CV1-CV5 | **PASS** 10/10 (after OD1-OD4 signed) | 2026-10-21 | final plan 14,547 / 294,000 shots (`validation/CV_2x4_plan.json`) |
| SKQD_2x4 | 2x4 noiseless SKQD from GPU samples | **PASS** 9/9 | 2026-10-28 (run at `18f29d1`, committed in `7b9bf32`) | section 5.4 (`validation/SKQD_2x4.json`) |

### 3.5 Quantinuum preparation (0 HQC spent)

| gate | what | status | date | key numbers |
|---|---|---|---|---|
| Q0P_2x2 | native build 2x2 | **PASS** 5/5 | 2026-10-13 | 252 ZZ; gate-only $f$ H2-2 0.7929 (`validation/Q0P_2x2.json`) |
| Q0P_2x3 | native build 2x3 | **PASS** 7/7 | 2026-10-02 | 2,158 ZZ; HQC/shot 4.9666; $f$ H2-2 0.150 (`validation/Q0P_2x3.json`) |
| Q0P_2x4 | native build 2x4 | **FAIL** (Q1 deferred to GPU; Q7 one test failure) | 2026-10-13 | 69,676 (opt-3) / 71,548 (structured) ZZ; Q1L 79/79 (`validation/Q0P_2x4.json`) |
| QN_2x2 | noiseless + noise models 2x2 | **PASS** 5/5 | 2026-10-13 | `validation/QN_2x2.json` |
| QN_2x4 | analytic $f$ 2x4 | **PASS** 2/2 | 2026-10-14 | $\log_{10} f_0 \in [-26.1, -24.4]$ under E1 (`validation/QN_2x4.json`) |
| QEMU_2x2 | local H2-1LE emulator | **PASS** 3/3 | 2026-10-13 | `validation/QEMU_2x2.json` |
| QEMU_2x3_laptop_smoke | emulator path smoke | **PASS** | 2026-10-13 | `validation/QEMU_2x3_laptop_smoke.json` |
| QEMU_2x4 | — | **infeasible** | 2026-10-13 | `validation/QEMU_2x4.json` |
| QH_2x2 / QH_2x3 | Helios Guppy/HUGR on Selene | **PASS** / **PASS** (information) | 2026-10-13 | `validation/QH_2x2.json`, `QH_2x3.json` |
| QH_2x4 | — | **not attempted** | — | `validation/QH_2x4.json` |
| QSC_prepared | syntax-check job sets | **prepared** (later run, section 9) | 2026-10-13 | `validation/QSC_prepared.json` |

### 3.6 GPU slots and the 2x3 four-class campaign (details in section 5)

| gate | status | date | key numbers |
|---|---|---|---|
| QV_2x4_01 | **PASS** 4/4 | 2026-10-19 | frozen 2x4 source = structured (max $\lvert\Delta\psi\rvert$ $9.8\times10^{-13}$) (`validation/QV_2x4_01.json`) |
| QV_2x4_02 | **PASS** 11/11 | 2026-10-22 | 20 circuits, 1,310 s, GPU util 89.6 % (`validation/QV_2x4_02.json`) |
| QV_2x4_03 | **PASS** 11/11 | 2026-10-26 | 30 circuits, 1,961 s (`validation/QV_2x4_03.json`) |
| QV_2x4_04 | **PASS** 11/11 | 2026-10-26 | 25 circuits, 1,632 s (`validation/QV_2x4_04.json`) |
| QV_2x4_05 | **FAIL** on S3 only | 2026-10-26 | 13 native circuits exact; `seconds_per_shot` null (no shots by design) (`validation/QV_2x4_05.json`) |
| QV_2x4_06, 07 | not requested (reserve) | — | `ci/parts/` |
| C1_IDEAL | **PASS** 10/10 | 2026-10-09 (job 59570217) | `validation/C1_IDEAL.json` |
| C3_AER | **PASS** 10/10 | 2026-10-09 (job 59570221) | `validation/C3_AER.json` |
| C2_CAL | **PASS** 12/12 | 2026-10-13 (job 59736871) | superseded by the decision file (section 5.5) |
| C2_KCHK | **FAIL** (S3, S6) | 2026-10-15 | found the Aer GPU Kraus bug (`validation/C2_KCHK.json`) |
| C2_XY4 | **PASS** 9/9 | 2026-10-18 (job 59965088) | `validation/C2_XY4.json` |
| C2_ECHO | **PASS** 9/9 | 2026-10-26 (job 60327713) | `validation/C2_ECHO.json` |
| C4_* (class 4, 20 runs + 17 part slots) | mostly **PASS**; FAIL: C4_FCELLS_A, C4_CF, C4_PART_02, C4_PART_04 (all on S6 shot minimum) | 2026-10-09..15 | table in `reports/C33_campaign_report.md` |
| C33_campaign | **FAIL** (assembly: 23 of 34 token JSONs at 2026-10-18) | 2026-10-18 | P15 S3 recall 1.0 both sectors (`validation/C33_campaign.json`) |

---

## 4. Hardware history (IBM Quantum)

**QPU** = quantum processing unit (the real quantum chip).  The account is IBM's open plan
(`ibm_quantum_platform` channel, open instance), **600 s of QPU time** in the period of record.

### 4.1 Spend, job by job

| date | device | gate | job id(s) | billed s | source |
|---|---|---|---|---|---|
| 2026-09-22 | ibm_fez | H0_canary | `dapbusac505c73chv0og` | 2.0 | `data/hardware/H0_ibm_fez_canary/session.json` `usage_s` |
| 2026-09-22 | ibm_fez | H0_diag (J1-J4) | `dapegkcak42c73cierv0`, `dapeh3318flc739m51e0`, `dapeh7ac505c73ci2o60`, `dapehb4ak42c73cietig` | 15.0 (5+4+3+3) | `validation/H0_diag.json` `data.total_usage_s` |
| 2026-10-02 | ibm_kingston | H0_kpilot | `davv8504oijs73e88fvg` | 12.0 | `validation/H0_kpilot.json` `data.live.usage_s` |
| 2026-10-02 | ibm_kingston | H0_ddtest | `db01005j371s73dnmbd0` | 20.0 | `validation/H0_ddtest.json` `data.live.usage_s` |
| 2026-10-02 | ibm_kingston | H0_2x2 | 5 jobs `db01pddj…`, `db01pdtj…`, `db01pe04…`, `db01pelj…`, `db01peql…` | 53.0 | `validation/H0_2x2.json` `data.live.usage_s` |
| 2026-10-06 | ibm_kingston | H0_ddrep | `db29p6nr11fs7396e4ig` | 37.0 | `validation/H0_ddrep.json` |
| 2026-10-06 | ibm_kingston | K1_2x3_fpilot | `db2avbe8v0ts73c2i8b0` | 188.0 | `validation/K1_2x3_fpilot.json` |
| **total** | | | | **327 s of 600 s** | account counter after K1: `usage_consumed_seconds` 327, remaining 273 (`validation/K1_2x3_fpilot.json` `data.live.account.after`) |

The sum $2 + 15 + 12 + 20 + 53 + 37 + 188 = 327$ s *(my arithmetic)* equals the account counter.  **`CLAUDE.md`'s
"17.0 s spent in total" is the ibm_fez part only and is out of date.**  No later IBM job exists in the repository.
Whether the 600 s allowance has reset since 2026-10-06 is not recorded here (check the account).

### 4.2 The ibm_fez canary and the idle-relaxation diagnosis (2026-09-21..30)

1. **Preparation.**  84 frozen coarse-step circuits (2x2, $k=1..4$, $r=1,2,3$ repetitions) transpiled onto FakeFez,
   663 CZ per repetition (`data/hardware/H0_prep/`; `prompts/LOG.md` 2026-09-16).  The first live prediction failed
   one criterion because the frozen shot plan saturated the $B=1$ sector only by chance (probability 0.0762);
   rule **D3'** replaced it (`reports/H0P_ibm_fez_escalation_20260921.md`).  A content **fingerprint** of the
   calibration (sha256 of the 30-qubit and 54-edge numbers the prediction reads) gates submission (rule D9,
   prompts/17).
2. **Canary NO-GO.**  8 accepted of 267 shots against a preregistered $\ge 10$ and a simulated 71; measured $f$ 0.0255
   vs predicted 0.2195 (`validation/H0_canary.json`).  The main 6-job submission was never run.
3. **Diagnostic H0_diag** (15 s): job J1 (dynamical decoupling and twirling both off) gave **35 accepted of 2000**
   against a preregistered $30.8\pm5.5$ for idle-time relaxation and $374.5\pm17.4$ for the "sampler options"
   hypothesis; the options hypothesis is rejected at about 20 $\sigma$ (`prompts/LOG.md` 2026-09-22;
   `validation/H0_diag.json`).  **Idle relaxation**: the routed circuit is nearly serial, so each qubit waits
   19-42 µs while others are gated, and dephasing during those waits destroys the state; neither the gate-only $f$
   model nor unscheduled Aer simulation contains it.
4. **Re-plan** (`reports/H0_replan_planner_analysis_20260922.md`): the accepted shots were mostly **near-clean**
   (strings with a few errors that still decode), not clean: 6 reference-string hits in 8,267 shots against 2.02
   expected from noise gives $f_{\rm clean} = 6.7\times10^{-4}$; the yield inversion overstated the clean fraction
   about 15x.  Gate **H0_model** then showed the right model is Aer on the *scheduled* circuit at the measured
   free-induction dephasing time $T_2^*$: 4.18 predicted vs 3.98 observed reference hits (ratio 1.05), against 197.4
   at the echo $T_2$ (ratio 49.58) (`prompts/LOG.md` 2026-09-30; `validation/H0_model.json`).
5. **The nine named changes of prompts/20** (D8', D1', D3'-f, D3''-H0, D5', C2', C3', H0P-Y', M4.4) were **all approved
   on 2026-09-30** and applied in code (`data/H0_replan_owner_decisions.md`; `prompts/LOG.md` 2026-09-30 rows).
   Rule M4.4 (near-clean term in the yield model; eq. (5) takes the *clean* fraction) is written into the amendment
   (`proposal/amendment_01_devices_and_budgets.md` §3).  This item is **closed**.

### 4.3 Amendment 01

`proposal/amendment_01_devices_and_budgets.md` (generated by `scripts/make_amendment.py`):

- **Item 1 (signed 2026-09-23):** patch selection by an idle-aware objective (`scripts/h0_patch_select.py`).
- **Item 2 (signed):** the budget criterion is read on the scheduled circuit's idle-aware $f$, thresholds 0.1 / 0.05
  unchanged.
- **Item 3 (signed):** the exact circuit family is kept and judged on duration.
- **Item 4 (OPEN): the 2x3 device.**  Requirement $n_{2q}\tilde\varepsilon_2 + n_{1q}\tilde\varepsilon_1 +
  n_m\tilde\varepsilon_{\rm ro} \le \ln(1/f_{\rm target}) - S_{\rm idle}$ (`skqd.device_req.target_with_idle`):
  $\varepsilon_2 \le 7.094\times10^{-4}$ is necessary, not sufficient; a vendor must also declare gate durations,
  $T_1/T_2$ and whether qubits idle serially.
- **Item 5 (OPEN): the shot quota of manual Step 9.2** (`reports/S2D_shot_quota_decision_20260922.md`); its figures
  scale as $1/f$ and wait for item 4.
- **Gate S2D's 2x2 PASS is withdrawn as a hardware statement** (idle-aware mean $f$ $6.71\times10^{-3}$ against 0.1,
  `validation/S2D_idle.json`).

### 4.4 ibm_kingston: the 2x2 run and the 2x3 pilot (2026-10-02..06)

- **H0_kpilot** (12 s): NO-GO, $f_{\rm pool}$ 0.0413 [0.0361, 0.0470], $r_{\rm eff}$ 0.0974 below $r_{\rm crit}$ 0.3285
  (`prompts/LOG.md` 2026-10-02).
- **H0_ddtest** (20 s): client-side **XY4** dynamical decoupling (four $\pi$ pulses $X\,Y\,X\,Y$ inserted into idle
  windows) raised $f$ from 0.0400 (no DD) to 0.1129 [0.1058, 0.1203]; adopted.  Context-aware X-only DD collapsed $f$
  to 0.0005 (cause not established) (`validation/H0_ddtest.json`).
- **H0_2x2** (53 s, owner decision `data/owner_decision_20261002_run_below_signed_budget.md`): 28 signed circuits with
  XY4, D3' shot plan 13,100 / 31,400 on the $k=4$ circuits, 133,907 coarse shots.  Pooled $k=1$ $f$ 0.1271.
  Results (`validation/H0_2x2.json` `data.energies`):
  - $B_{\rm all}$ (all accepted states) = the whole sector (38/38 and 20/20): $E_R = E_0$ exactly
    ($-3.6407665507$, $-1.8615880345$).  Labelled **"not a device test"**: at 2x2 noise alone fills the sector.
  - $B_{\rm sig}$ (states above the noise floor at 3 $\sigma$): 35/38 and 19/20; $E_R - E_0 = 5.48\times10^{-4}$
    ($B=0$, Kato-Temple width $1.36\times10^{-3}$) and $5.75\times10^{-6}$ ($B=1$, Weinstein width
    $5.95\times10^{-3}$) (`reports/selected_ci_baseline.md` Tables 1-2).
- **H0_ddrep** (37 s): the XY4 gain did **not** replicate (baseline T0 0.0818; $R_{T3} = 0.895$, R1 and R2 false);
  mechanism reading "no single hypothesis" (`validation/H0_ddrep.json` `data.replication`, `data.mechanism`).
- **K0** (model, 0 s): 2x3 on kingston = 5,659 routed CZ, 411 µs, idle-aware $f$ $1.66\times10^{-15}$ (echo) to
  $5.2\times10^{-35}$ ($T_2^*$) (`prompts/LOG.md` 2026-10-06; `reports/K0_2x3_ibm_heron_nogo.md`).  2x4 routed
  148,726 CZ, $f \sim 10^{-53}$ (`reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` §2).
- **K1_2x3_fpilot** (188 s, $4\times10^5$ shots): $\hat f_{\rm ideal} = f_{\rm hit}/r_{\rm nc} = -1.12\times10^{-6}$,
  95 % interval $[-1.1\times10^{-6},\ 2.06\times10^{-5}]$; thresholds GO-B $10^{-3}$, GO-A $3\times10^{-4}$;
  **decision NO-GO, firm** (`validation/K1_2x3_fpilot.json` `data.decision`).

**Meaning.**  2x2 SKQD works end to end on a superconducting device; 2x3 and 2x4 cannot run there with these circuits
(idle dephasing on long, nearly serial circuits), which is why the project turned to trapped ions (Quantinuum) and
to circuit compression.

---

## 5. Perlmutter GPU CI

### 5.1 How it works

**CI** (continuous integration) here means: Perlmutter (the NERSC supercomputer) pulls this GitHub repository every
hour at :07 UTC and runs allow-listed jobs on an NVIDIA A100 GPU.  No agent has a Perlmutter login (`CLAUDE.md`
"skqd-ci" section; `SKQD-CI-SETUP.md`; `ci/README.md`).

1. Commit and push the change to `master`.
2. `scripts/ci_request.sh TOKEN [TOKEN ...]` writes one request file per token `ci/requests/<NNN>-<TOKEN>.txt` in one
   commit and pushes (sync by fetch + merge, never rebase; push retried 3 times).  `--legacy` writes the old
   one-job `ci/request.txt`.
3. `scripts/ci_check.sh [TOKEN]` reports pending/submitted/done/refused (exit 0 done, 2 pending, 3 refused/error).
   Check no more often than every 15 minutes.
4. The CI writes `validation/ci_gate_<TOKEN>.json`, `reports/ci-<jobid>.out` and `ci/status/<TOKEN>.json` (never edit
   these, nor `ci/status.json`, `ci/poll.sh`).
5. The concurrent poller is `ci/poll_concurrent.sh` (installed on Perlmutter with `ci/install_skqd_ci.sh`); the
   allow-lists are `ci/allowed_jobs.campaign33`, `ci/allowed_jobs.campaign33a`, `ci/allowed_jobs.q35`; generic
   slots read their content from `ci/parts/`.
6. Limits (enforced on Perlmutter): walltime per token 15-60 min, 1 GPU (shared QOS), a daily job cap; never more than
   3 requests in a row without a PASS (then write `prompts/BLOCKED_<gate>.md`).

### 5.2 The qiskit version split

The laptop's `coding` env pins qiskit 2.5.2 / qiskit-aer 0.17.2.  The GPU build `qiskit-aer-gpu` 0.15.1 is incompatible
with qiskit 2.x, so **code the CI runs must work on qiskit 1.4.3** (RUNBOOK "Engine and HPC policy";
`CLAUDE.md`).  The laptop keeps a "twin" venv `~/.local/share/su2qc-qiskit143` (qiskit 1.4.3 / aer 0.15.1) to dry-run
CI code; QPY circuit files for the CI are written at QPY version 13 (qiskit 1.4.3 cannot read v17;
`prompts/LOG.md` 2026-09-30).

### 5.3 Jobs and results

60 job logs exist (`reports/ci-*.out`, job ids 58717267 to 60327713); 55 numbered requests in `ci/requests/`
(001-055).  Milestones:

| job | token | result | key numbers |
|---|---|---|---|
| 58737320 | L4 | crashed (GPU out of memory) | fixed by `circuits_qiskit.shot_chunk_for` (`prompts/LOG.md` 2026-09-22) |
| 58741899 | L4 | **PASS** 4/4 | 0.00103 s/shot vs laptop 0.02037: **19.8x**; peak 27,915 MiB; mean GPU utilization 15.3 % |
| 58771538 | S3 | PASS (calibration) | 0.0199 s/shot at 20 qubits vs laptop 3.198: 161x (`CLAUDE.md`) |
| 59162991 | S2_2x4 C6 | **PASS** | leakage $1.10\times10^{-12}$ of the 279,083-instruction circuit; 0.23 ms/instruction vs 0.0699 s on the laptop (~300x) |
| 59491455.. (wave 1) | campaign 33 | 3 died on a missing `threadpoolctl` | fixed by a preflight import check (`prompts/LOG.md` 2026-10-07) |
| 59570217..59828887 | C1, C2, C3, C4 tokens | see 5.5 | |
| 60009475 | QV_2x4_01 | **PASS** 4/4 | frozen 2x4 source = structured |
| 60093511 | smoke | done | `validation/ci_smoke.json` |
| 60112521, 60327663, 60327665 | QV_2x4_02, 03, 04 | **PASS** 11/11 each | ~63 s per circuit; mean GPU utilization 88.8-89.6 %; peak 4,557 MiB |
| 60327711 | QV_2x4_05 | **FAIL** on S3 | `seconds_per_shot` null (native statevector runs, no shots) |
| 60327713 | C2_ECHO | **PASS** 9/9 | 1,449 s |

Two lessons recorded in the log: low GPU utilization (15 %) at 12 qubits means more GPUs would not help, so none were
requested (memory note `gpu-scaling-needs-measured-evidence`); a Slurm step did not inherit the allocation's 32 CPUs
until `srun --cpus-per-task` was added to `jobs/gate.sbatch` (prompts/33e).

### 5.4 The 2x4 noiseless SKQD pipeline (prompts/36, 36a)

- 75 IR-level-0 circuit bundles (60 family + 15 at $k=5$), 142,284 instructions per coarse-step body plus the
  reference's X gates (`validation/CV_2x4_plan.json` A7, rule corrected under OD3).
- Owner sign-off OD1-OD4 on 2026-10-21 (`data/owner_decision_20261021_2x4_cv_plan.md`).
- GPU sampling: the final plan asks the GPU for 1,411,324 shots (slots 02-04; `prompts/LOG.md` 2026-10-21) with 0 per-state test failures
  and exactness $\le 5.8\times10^{-13}$ (`validation/SKQD_2x4.json` K1-K3).
- **Result** (`validation/SKQD_2x4.json`):

| point | sector | $\lvert B_{\rm all}\rvert$ | recall $S_{99.9}$ | $E_R-E_0$ | certificate width | $E_0$ inside |
|---|---|---|---|---|---|---|
| plan | $B=0$ | 496 | 0.931 | $8.10\times10^{-3}$ | 0.0258 (KT) | yes |
| plan | $B=1$ | 1,768 | 0.998 | $1.28\times10^{-3}$ | 0.103 (W) | yes |
| uniform $2\times10^5$/sector | $B=0$ | 1,155 | 0.987 | $1.29\times10^{-3}$ | 0.0046 | yes |
| uniform $2\times10^5$/sector | $B=1$ | 1,110 | 0.974 | $4.22\times10^{-3}$ | 0.185 | yes |

CV1-CV5 all pass in both sectors on the real sampled sequences (K5); CV3 ($k=4\to5$) is 0.233 $E_{\rm tol}$ ($B=0$)
and 0.155 $E_{\rm tol}$ ($B=1$) (commit `7b9bf32` message).  The $B=0$ plan row is the weakest noiseless reading
(recall 0.931).

### 5.5 The 2x3 four-class campaign (prompts/33..33f)

Owner request 2026-10-06: every 2x3 simulation redone on the GPU in four classes (`reports/C33_campaign_report.md`,
`validation/C33_campaign.json`):

1. **Class 1** (no noise): C1_IDEAL PASS: 50 circuits, 1,441 states, 0 per-state failures; recall 1.0 at the $f=0.10$
   plan (`validation/C1_IDEAL.json`).
2. **Class 2** (IBM noise from the committed 2026-10-06 kingston record): the GPU Kraus representation of thermal
   relaxation was found wrong (GPU Kraus mean Hamming weight 3.00 vs CPU Kraus 7.46 on the same circuit;
   `data/campaign33/aer_gpu_kraus_report/README.md`).  Production representation decided **RM** (relaxation written
   without Kraus instructions, $T_2 := \min(T_2, T_1)$) by Fisher's exact test on four CPU references
   (`data/campaign33/c2_representation_decision.json`).  C2_XY4 and C2_ECHO PASS; **C2_GATE, C2_STAR, C2_COH not yet
   requested** (deferred past the 2026-10-21..28 maintenance).
3. **Class 3** (Quantinuum native, noiseless): C3_AER PASS (44 circuits, 1,393 states).
4. **Class 4** (noise scenarios E1-E8, plan-of-record runs): most PASS; the S3 recall criterion holds with recall 1.0
   in both sectors at $2\times10^5$ (`validation/C33_campaign.json` P15).  Deferred: C4_F3_*, C4_F6_* (owner's call).

---

## 6. The circuit-compression study (genie-opus)

A separate study in `2x4_compression_using_ai_v1/` (plus data folders `2x3_compression_using_ai_v1/`,
`2x2_compression_using_ai_v1/`), run by the agent **genie-opus** (`.claude/agents/genie-opus.md`, Opus 5.5 at high
effort), started 2026-10-19 (commit `db0bd79`).  It imports the package read-only and carries no gate status of the
package.  Full technique manual: `2x4_compression_using_ai_v1/MANUAL_lgt_circuit_compression.md` (1,190 lines,
revision 2 after cold-read review `reviews/002-manual-cold-read.md`).  Reports: `reports/001-…` to `004-…`.

### 6.1 The techniques (manual §3, steps a-k)

In plain words (each "frame" is a cheap basis change applied before a term and undone after it — the agent's own
label):

- (a) an **independent evaluator** that reproduces the frozen baseline first (71,548 / 70,300);
- (b) structure tests on each term's matrix;
- (c) **corner frames** for plaquettes: rotate each corner so the term becomes one multiplexed rotation;
- (d) sign fixing over $\mathbb F_2$ (bit-vector algebra);
- (e) **clean ancillas** from the duplicated link bits (a qubit that is always $\lvert0\rangle$ on codewords because its
  information is stored elsewhere) and **dark-state flags**;
- (f) **sparse-Walsh multiplexors** (a uniformly controlled rotation whose angle table has few nonzero Walsh
  coefficients, so most CNOTs drop out), with a MILP (mixed-integer linear programme) certificate of minimality;
- (g) hop frames: vertex factorisation, parity fold, bright frames, Jordan-Wigner sign;
- (h) **angle-linear synthesis**: the gate skeleton must not depend on $k$;
- (i) **class B**: restrict each term to the states reachable from the circuit's own reference;
- (j) peephole and CNOT-run resynthesis;
- (k) conversion to Quantinuum native gates.

### 6.2 Class A vs class B

- **Class A = operator-exact**: equal to the exact product of term exponentials on every codeword (every valid
  lattice state).  Usable anywhere.
- **Class B = input-specific**: exact only on its own reference input, for one coarse step.  Valid only for "prepare
  its own reference with X gates, one coarse step, measure in the computational basis"; on a random superposition it
  is off by $2.3\times10^{-2}$ in max amplitude at 2x4 (manual §9; `reviews/001`).

Accuracy bar for both (`prompts/35b_2x4_exactness_ruling.md` R1): $\max_s\lvert\psi_s e^{-i\varphi} - t_s\rvert <
10^{-10}$ against `skqd.krylov.coarse_states`, leakage $< 10^{-9}$.

### 6.3 The middle plaquette (`plaq1`) step by step

`plaq1` is the 2x4 middle plaquette whose four corners are all interior vertices: 66,468 of the 71,520 term CNOTs
(92.9 %) of the frozen circuit (`reports/003-full-compression-report.md` §2).  Construction trials and the loop
(same report; `data/archive_it1..5.json`, `data/report003_tables.json`):

| step | `plaq1` two-qubit gates |
|---|---|
| frozen | 66,468 |
| CF1 (corner frames + one multiplexor, 11 controls) | 2,110 |
| CF2 first try (clean ancillas + dark-state flags) | 356 (8 controls, bug) |
| CF2 final (iteration 1) | **238** (7 controls) |
| iteration 3+ (`cfg_sw`, sparse Walsh), class A | **220** |
| class B, mean over 15 references (it3-it5) | 155.7 |

Whole class-A term sum by iteration: 71,520 → 4,588 → 4,440 → 3,074 → 2,734 → 1,774 (same report).  Teaching
material: `reports/plaq1_compression_steps_2x4.pdf`, `reports/plaq1_compression_teaching.pdf` (+ `_edited`),
sources in `reports/plaq1_compression_steps_src/` and `reports/plaq1_compression_teaching_src/`.

### 6.4 Family gate counts and clean-shot fractions

From the manual §1.2 table and `reports/quantinuum_sc_20261028_all_lattices.md` §3.2.  $f_{\rm pkg}$ = the package's
gate-only clean-shot fraction $(1-\varepsilon_2)^{n_{2q}}(1-\varepsilon_1)^{n_{1q}}(1-\varepsilon_{\rm ro})^{n_m}$
on H2-2 (`skqd.device_req.clean_shot_fraction`); $f_{\rm full}$ = the noise agent's full model (section 7).

| lattice | family | circuits | ZZ (two-qubit) | 2q depth | $f_{\rm pkg}$ H2-2 | source |
|---|---|---|---|---|---|---|
| 2x2 | frozen | 28 | 252 | 201 | 0.793 | `validation/Q0P_2x2.json` |
| 2x2 | `compressed_circuit_llm_2x2_classA` | 28 | 245 | 188 | 0.79287 (frozen 0.79288) | `2x2_compression_using_ai_v1/data/c2x2/summary_2x2.json` (via `notes/011`) |
| 2x2 | `…_2x2_classB` | 28 | 55-162 (mean 119.4) | 45-137 | 0.854-0.941 (mean 0.888) | same |
| 2x3 | frozen | 44 | 2,158 | 1,925 | 0.150 | `validation/Q0P_2x3.json` |
| 2x3 | `…_2x3_classA` | 44 | 871 | 611 | 0.445 | manual §1.2 |
| 2x3 | `…_2x3_classB` | 44 | 309-465 (387.6) | 170-290 | 0.692 | manual §1.2 |
| 2x4 | frozen (structured) | 75 | 71,548 | 70,300 | $4.18\times10^{-29}$ | `validation/QN_2x4.json` |
| 2x4 | `…_2x4_classA_v1` | 75 | 1,736-1,740 | 1,275-1,280 | 0.2005-0.2009 (4 circ.) | manual §1.2 |
| 2x4 | `…_2x4_classB_v1` | 75 | 582-800 (683.5) | 292-469 | 0.4718-0.5751 (4 circ.) | manual §1.2 |
| 2x4 | `…_2x4_classA_v2` | 75 | **1,492** | 948 | 0.2512 | manual §1.2 |
| 2x4 | `…_2x4_classB_v2` | 75 | **580-763 (675.0)** | 292-429 | 0.5293 | manual §1.2 |

Notes: at 2x2, class A saves 7 ZZ but its native form has 623 PhasedX gates against the frozen 405-425, so $f$ is
unchanged (`notes/011-2x2-families.md`).  Independent verification: reviewer-opus confirmed v1 class A with 8
random-superposition Aer runs (`reviews/001-independent-verification.md`, "CONFIRMED WITH NOTES"); the
random-superposition test has **not** been run by an independent agent on 2x4 class A v2 or 2x3 class A (manual §1.2).

### 6.5 $k=5$ sets (2026-10-28)

- **Frozen** (package, executor-opus): `data/quantinuum/circuits_2x2_k5/` (7 + 2 calibration) and
  `data/quantinuum/circuits_2x3_k5/` (11 + 2); $\Delta t$ pinned bit for bit to the frozen manifests; verify PASS:
  $\max\lvert\Delta\psi\rvert$ $2.29\times10^{-14}$ / $7.16\times10^{-14}$
  (`data/quantinuum/circuits_2x{2,3}_k5/verify.json`; `prompts/LOG.md` 2026-10-28).
- **Compressed add-ons** (genie-opus): `compressed_circuit_llm_2x{2,3}_class{A,B}_k5`, same skeleton and counts as
  $k=1..4$ (enforced by `freeze_family.py --addon-of`), certified $\le 9.2\times10^{-13}$
  (`2x4_compression_using_ai_v1/notes/014-k5-addons-2x2-2x3.md`; `data/k5_addons_2x2_2x3.json`).
- 2x4 already had $k=5$ in every family (75 circuits).

### 6.6 Lean proofs

**Lean 4** is a proof assistant (a programming language in which mathematical statements are checked by computer).
`2x4_compression_using_ai_v1/lean/` (toolchain `leanprover/lean4:v4.35.0`, Mathlib tag v4.35.0, file `lean-toolchain`):
11 files in `Compress2x4/` (`Sanity`, `Exp`, `Bits`, `Peephole`, `Reach`, `Budget`, `Ucr`, `Pair`, `Glue`,
`Rounding`, `Conj`).  Last build "completed successfully (9059 jobs)"; no `sorry`/`admit`; 66 `#print axioms`, of
which 63 depend only on `propext`, `Classical.choice`, `Quot.sound` and 3 on no axiom
(`data/c4_lean_build.log`, as reported in the manual §6.1).  What is proved: generic algebra (exponentials agree on
invariant subspaces, CNOT networks as xor-linear maps, multiplexor walk identities, reachability induction,
rounding and truncation bounds).  What stays numerical: each term's factorisation, each Walsh solve, each full
circuit's check (manual §6.3).  Build: `cd 2x4_compression_using_ai_v1/lean && lake build` (`.lake/` ≈ 7.3 GB).

### 6.7 Folder layout per lattice (`notes/012-folder-split.md`)

- `2x4_compression_using_ai_v1/`: all shared code (`src/c2x4/`, `scripts/`, `lean/`, `tests/`, `families.py` loader,
  `noise/src`, `noise/scripts`), the manual, `notes/`, `reviews/`, study reports, 2x4 families
  `data/families/compressed_circuit_llm_2x4_*`, 2x4 noise results `noise/data/results/2x4/`.
- `2x3_compression_using_ai_v1/`: 2x3 data only (`data/c2x3/`, families, native exports, noise results, hardware).
- `2x2_compression_using_ai_v1/`: 2x2 data only (`data/c2x2/`, families, `native_2x2/`, syntax-check records,
  `examples/2x2_sandbox/`).
- Loader: `sys.path.insert(0, "2x4_compression_using_ai_v1"); from families import get_family` (API in
  `notes/009-family-api.md`).

### 6.8 The owner's separation rule (in force)

Quoted from `notes/008-owner-decisions-C1-C6.md` via manual §10: "keep the frozen circuits that have already been
tested separate from Class A and Class B, these will be known as compressed_circuit_llm_2x4_class[A,B] from now on.
I will tell you what to test when …" and "like i said, keep them separate and I will tell you what to use where."
So: compressed families are **never** substituted into frozen circuits, gates, preregistrations, GPU slots or hardware
plans until the owner says so; results go to separate files (also memory note `compressed-circuits-separate`).

---

## 7. Noise models and the noisy SKQD campaign

### 7.1 Noise models (`2x4_compression_using_ai_v1/noise/reports/002-noise-models.md`)

Built from **published** device numbers only (owner decision C5: no backend, no live calibration).  All channels are
**Pauli channels** (a random $X$, $Y$ or $Z$ error with some probability), so each simulated shot is a "trajectory"
with a few inserted faults, simulated exactly by a sparse simulator (`noise/src/traj_sparse.py`, validated against
Aer to $2.7\times10^{-12}$).  Models: Quantinuum H2-2 and Helios-1 (gate error, angle-dependent RZZ error, memory
error per layer), IonQ Forte/Tempo (serial schedule, idle dephasing), IBM Heron r2/r3 (routing on a reconstructed
heavy-hex map, thermal relaxation as a Pauli twirl), plus no-memory / no-idle bounding variants.  Parameters, e.g.
H2-2: $r_{1q} = 2.8\times10^{-5}$, $r_{2q} = 8.3\times10^{-4}$, memory $1.2\times10^{-4}$ per layer (report 002 §3).

### 7.2 Results (`noise/reports/004-noisy-skqd-campaign.md`, generated from
`noise/data/results/noisy_skqd_campaign_summary.json`)

- **What:** every circuit of the compressed families (and the frozen 2x2/2x3 sets) sampled under H2-2 (primary) and
  Helios-1, full SKQD analysis on noisy and on ideal samples of the same size.  15 cells, 175.4 thread-hours of
  sampling (report 004 §2).  Per circuit, shots $N_c' = \lceil N_c/f_c\rceil_{100}$ (noiseless plan divided by the
  model clean fraction).
- **Certificates:** $E_0$ inside the certificate in **30 of 30** (cell, sector) rows with noise and 30 of 30 ideal;
  lowest recall of $S_{99.9}$ with noise 0.964 (§4).
- **CV pass counts over 30 rows, noisy (ideal):** CV1 30 (30), CV2 26 (26), CV3 30 (30), CV4 17 (18), CV5 30 (30)
  (§4).  CV4 fails at 2x2 because the sectors saturate; the only noise-caused verdict change is CV4 for the frozen
  2x3 $B=1$ cell (margin 0.198 vs 1.407 $E_{\rm tol}$, §3.5).
- **Examples (H2-2):** 2x3 class B $B=0$: acceptance 0.727, $f_{\rm hit}$ 0.696, $E_R-E_0 = 6.72\times10^{-4}$ noisy
  vs $7.65\times10^{-4}$ ideal; 2x4 class B v2 $B=0$: acceptance 0.588, $E_R-E_0 = 3.57\times10^{-3}$ noisy vs
  $4.22\times10^{-3}$ ideal (§3.1).
- **$r_{\rm nc}$** (near-clean ratio, $f_{\rm hit}/f_{\rm ideal}$): [0.996, 1.133] for the compressed families,
  [1.012, 1.359] for the frozen ones; for the frozen 2x3 circuits the reference-hit estimator overstates the clean
  fraction, the same effect H0_diag found on hardware (§4).
- **Price of the frozen circuits:** for equal expected clean shots the frozen 2x3 set needs 9.5x (vs class A) and
  17.5x (vs class B) the shots, and 51x / 197x the sampling cost (§3.4).

### 7.3 Caveats

1. **Simulation only.**  No hardware shot was taken on any Quantinuum device.  Models are Pauli channels from
   published numbers; coherent errors, leakage and crosstalk are not modelled (report 002 §5).
2. **2x4 $B=1$ is under-shot:** the campaign used the 1x D3'-R plan (24,404 noiseless shots before $1/f$ scaling)
   instead of the 12x plan of record (294,000); CV2 fails there for noisy and ideal samples alike, so the failure is
   the shot count, not the noise (§3.3).  The uncut plan of record would have cost 7,692.7 thread-hours (1,131 h wall at 10 threads), against 179.7
   thread-hours planned for the campaign as run (`2x4_compression_using_ai_v1/noise/notes/campaign_budget.md`).
3. The frozen 2x3 circuits were simulated on their IR gate list (2,590 two-qubit gates), not the native 2,158, so
   their campaign $f$ (0.032) is below the native analytic 0.0552 (§5).
4. Not sampled: Helios-1 frozen 2x3, Helios-1 2x4 class A v2, 2x4 class A v1 (§5).
5. 2x2 is not a noise-robustness test (sectors saturate).

### 7.4 Where the raw shot data live

The npz shot sequences and chunk metadata **are committed** (commit `b2a1da36`, 2,678 files, about 23 MB *(du of the
tracked files)*): `<lattice>_compression_using_ai_v1/noise/data/results/<lattice>/<family>/<device>/skqd_samples/`.
(Report 004 §5 still says they are not committed; that sentence predates `b2a1da36`.)  Per-cell analysis:
`.../noisy_skqd.json`; loader `results.load(lattice, family, device, "noisy_skqd")`.  The trajectory cache
`2x4_compression_using_ai_v1/noise/.cache/` (≈551 MB) is git-ignored (USB only).

---

## 8. The classical selected-CI baseline

`reports/selected_ci_baseline.md`, generated by `python scripts/selected_ci_baseline.py --report` from
`data/baselines/selected_ci_2x{2,3,4}.json` (code `src/skqd/selected_ci.py`, tests `tests/test_selected_ci.py`),
2026-10-29, owner request (paper referee weakness "no classical baseline").

- **CIPSI** ("configuration interaction by perturbation with multiconfigurational zeroth-order wave functions selected
  by iterative process"): grows a set of basis states by ranking neighbours with the Epstein-Nesbet score
  $e_a = \lvert\langle a\vert H\vert\psi_S\rangle\rvert^2/(E_{\rm var}(S) - H_{aa})$; $E_{\rm PT2} = \sum_a e_a$ is a
  perturbative estimate of the missing energy.  Compared against **oracle** (top exact-weight states) and **random**
  sets (200 seeds) at SKQD's subspace size.
- **Result:** 32 non-trivial equal-size rows; CIPSI (main schedule) below SKQD's $E_R$ in 31, best schedule in 32,
  oracle in 32; SKQD below the random median in 32 and below all 200 random sets in 30 (`prompts/LOG.md`
  2026-10-29).  Example 2x3 $B=0$ C1_IDEAL plan ($\lvert B\rvert = 333$): SKQD $1.80\times10^{-4}$, CIPSI
  $5.48\times10^{-5}$, oracle $5.60\times10^{-5}$, random median $1.15\times10^{-1}$; CIPSI reaches SKQD's error at
  253 states.  Exception: 2x4 $B=1$ plan ($\lvert B\rvert = 1768$): SKQD $1.28\times10^{-3}$ beats CIPSI main
  $2.57\times10^{-3}$ (fixed batch $2.97\times10^{-4}$, oracle $3.00\times10^{-4}$) (`reports/selected_ci_baseline.md`
  Table 1).
- **Meaning:** on these small ladders a classical selection is as good as or better than SKQD's sampled subspace at
  equal size; SKQD is far better than random.  This is an honest limitation for the paper, not a failure of the
  pipeline.

---

## 9. Quantinuum Nexus

**Nexus** is Quantinuum's cloud service; **qnexus** its Python client; **HQC** (H-System Quantum Credit) its billing
unit.

- **Install.**  `qnexus` 0.51.0 with pytket 2.18.4 / pytket-quantinuum 0.59.3 / pytket-qiskit 0.78.0 in the venv
  `~/.local/share/su2qc-quantinuum/venv`, built on top of the `coding` env with `--system-site-packages` (nothing
  installed into `coding`; `prompts/LOG.md` 2026-10-02; `env/su2qc-quantinuum-venv-requirements.txt`).  The conda env
  `su2qc-jepa` also holds `qnexus` 0.51.2 (`env/su2qc-jepa.yml`; coordinator note).  Local emulators: pecos venv
  `~/.local/share/su2qc-pecos` (H2-1LE), Selene venv `~/.local/share/su2qc-selene` (Helios HUGR).
- **HQC formula** (`skqd.quantinuum_native.hqc_job`; checked equal to the checker's cost to $\le 1.1\times10^{-13}$
  HQC in every family):
  $$\mathrm{HQC} = 5 + C\,\frac{N_{1q} + 10\,N_{2q} + 5\,N_m}{5000},$$
  $C$ shots, $N_{1q}$ PhasedX gates, $N_{2q}$ ZZPhase gates, $N_m$ initialisations + measurements
  (`reports/quantinuum_sc_20261028_all_lattices.md`).
- **H2-2SC syntax checker** (compiles as the machine would, returns the cost, every shot all zeros; free):
  - 2026-10-28, 10 families, **536/536 jobs COMPLETED, 0 errors** at 200 shots/job.  Lattice totals (HQC at 200
    shots): 2x2 frozen 3,561.12, class A 3,716.00, class B 1,949.28; 2x3 frozen 43,926.00, class A 20,153.60, class B
    9,197.12; 2x4 class A v1 67,923.08, class B v1 27,223.96, class A v2 58,469.80, class B v2 26,865.00
    (`reports/quantinuum_sc_20261028_all_lattices.md` §3).
  - HQC per shot (mean): 2x2 frozen 0.6109; 2x3 frozen 4.9666, class A 2.2652, class B 1.0201; 2x4 class B v2 1.7660
    (same table).
  - 2026-10-28, $k=5$ sets: **66/66 COMPLETED** (3 frozen 2x3 jobs after one retry of an `INTEGRATION_TIMEOUT`);
    $k=5$ totals 2x2 frozen 890.00, 2x3 frozen 10,948.20 HQC (`reports/quantinuum_sc_k5_2x2_2x3.md` §3).
  - **Frozen 2x4 upload: HTTP 500** "Internal Server Error - Cancelled", twice, during `qnx.circuits.upload` of a
    32.6 MB circuit (28 qubits, 71,548 ZZ, 210,994 PhasedX); H2-2SC never saw it; formula-only total 2,224,511.84 HQC
    for 60 circuits at 200 shots (`reports/quantinuum_sc_20261028_frozen_2x3_2x4.md` §3.2, §6).
  - Quota snapshots showed 0 s simulation and compilation time before/after every family; only stored data grew.  A
    direct HQC-balance reading was **not** established (needs the Nexus web portal) (`reports/quantinuum_sc_20261028_all_lattices.md` §4).
- **No hardware shots were run on any Quantinuum device; 0 HQC were spent.**  Cost estimates of a real 2x3 campaign
  (D3'-R at $f = 0.10$: 418,166 HQC, labelled ESTIMATE) are in `validation/Q0P_2x3_plan.json` / `prompts/LOG.md`
  2026-10-05.  An access-request draft exists: `proposal/quantinuum_access_request_draft_20261005.md`.
- **Login on the desktop (commands only; never paste a token into a file or a chat):**
  ```bash
  mamba activate su2qc-jepa        # or: source ~/.local/share/su2qc-quantinuum/venv/bin/activate
  qnx login                        # interactive browser/device login; stores the session in your home directory
  python -c "import qnexus as qnx; print(qnx.devices.get_all())"   # read-only check that the session works
  ```
  Syntax checks are run with `scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits <dir> --all
  --max-cost <N> --project <name>` then `--retrieve`, `--status` (exact commands in each family's `summary.json`
  `produced_by`).  IBM equivalent: `python scripts/ibm_account.py --save` (reads the key from a hidden prompt or
  `$QISKIT_IBM_TOKEN`, never from the command line), then `python scripts/ibm_account.py --check`.

---

## 10. Paper and talk status (private)

- **Location:** `paper/` (LaTeX sources, figures, tables, `provenance.json`, `talk/`), **git-excluded** through
  `.git/info/exclude` (`/paper/`, `/reports/su2qc_skqd_paper_draft*.pdf`; owner 2026-10-30).  Copies:
  `reports/su2qc_skqd_paper_draft.pdf`, `_v2.pdf`, `_v3.pdf` (also excluded).  Kept on the laptop and the USB backup
  only.  **`.git/info/exclude` is not cloned: re-add both lines on the desktop before any `git add -A`** (section 12).
- **Format:** PRD style (REVTeX 4.2). Its title and section list are deliberately left out of this public report;
  see `paper/main.tex` on the laptop or the USB backup.
- **v3 (2026-10-30), 24 pages, built with Tectonic (conda env `latex`).**  Changes in summary (from the private
  `paper/CHANGES_v3.md`, not quoted): the four variants of the clean-shot fraction $f$ defined and labelled
  consistently; the reason the 2x4 $B=1$ plan is 20x the $B=0$ plan explained (section 2.5 above); the shot ratios
  between frozen and compressed families defined; every number is a generated macro traced in `provenance.json`
  (510 macros).  No measured result changed.
- **Talk:** deck artifact (private claude.ai link) https://claude.ai/artifact/Bnv7we9UHeTnNotSqzp7uu; deck sources in
  `paper/talk/deck/`; script `paper/talk/talk_script.pdf` (+ `.tex`, `.md`); definitions handout
  `paper/talk/talk_handout_definitions.pdf`; checklist `paper/talk/talk_checklist.md`.
- **Placeholders still to fill:** author surname, affiliation, acknowledgments, AI-use disclosure, DOI (the title page
  and the talk title slide carry them too) — checklist §F item 7.
- **Checklist §F items still open (owner's call):** item 4 (the strict $E_{\rm tol}$ equality check that flags a
  $4.6\times10^{-9}$ recomputation difference), item 5 (single out the 2x4 $B=0$ plan row as the weakest noiseless
  reading: recall 0.931), item 7 (placeholders).  Item 6 (unused macros) is only partly done.

---

## 11. Open items and next steps (prioritised)

**Priority 1 — needed before anything else on the desktop**

1. **Protect the private paper on the new clone** (`.git/info/exclude` lines, section 12.2).  Otherwise a
   `git add -A` would publish it.
2. **The unmerged branch `c33f-r4-omp-binding`** (one commit `c502f528`, "prompts/33f R4 (HELD for the owner: changes
   the engine and HPC policy)": `jobs/gate.sbatch` stops exporting `OMP_PROC_BIND` / `OMP_PLACES`).  It exists **only
   locally** (not on `origin`).  Recover it on the desktop from the USB copy's `.git` (section 12.3) and decide:
   merge (it amends RUNBOOK's engine policy; owner sign-off needed) or drop.  The seven agent worktrees under
   `.claude/worktrees/` (branches c33a, c33b, c33c, c33e, q35, c33f, worktree-agent-a9f60fe…) are all merged except
   this branch; they are not needed on the desktop.
3. **Pre-existing failing test** `tests/test_q0p_plan.py::test_d3r_plan_reproduces_prototype` (`assert same` in
   `sector_sets`); it fails identically at the clean commit `7b9bf32` (`prompts/LOG.md` 2026-10-28/29 rows).  Diagnose
   (likely a tie-break or BLAS-thread ordering difference in the D3'-R prototype comparison) before trusting a full
   `pytest` run as a regression signal.  It also makes `Q0P_2x4` criterion Q7 fail.

**Priority 2 — owner decisions recorded as open**

4. **$r_{\rm nc}$ decision** (`prompts/33c_class2_representation_and_cf_reruling.md` §5 item 1): the GPU re-measurement
   C4_CF gives pooled $r(10^{-3}) = 1.055$ [1.033, 1.078] (`reports/C4_CF.md`), which excludes the value in force
   $r_{\rm nc} = 1.115$ (`data/cf_trajectories/r_nc.json`).  Decide whether to replace it by 1.078 (every
   $\hat f_{\rm ideal}$ rises 3.4 %, no tier changes) or keep 1.115 with both stated.  Nothing changes until then.
   (The $k=4$ arm, $r = 1.172$ [1.128, 1.217], is above both; $r_{\rm nc}$ is a $k=1$ quantity.)
5. **Aer bug report** (`data/campaign33/aer_gpu_kraus_report/`, README "Not filed yet: the owner reads it first"):
   qiskit-aer-gpu 0.15.1 GPU statevector with Kraus relaxation samples a different distribution than CPU; bundle with
   `reproduce.py`, circuits and raw counts.  Owner to read and file upstream (GitHub issue on qiskit-aer).
6. **QV_2x4_05 S3 telemetry ruling:** the slot ran 13 native statevector circuits (no shots by design) and fails only
   S3 because `seconds_per_shot` is null (`validation/QV_2x4_05.json`).  A planner ruling is needed: scope S3's
   seconds-per-shot field to sampling runs (then re-assemble, no GPU re-run) or accept the FAIL as recorded.  Q0P_2x4's
   Q1 bar for these 13 natives is recorded in the slot (N1) and should be folded into Q0P_2x4 (prompts/36 R9).
7. **Amendment 01 items 4 and 5** (section 4.3): the 2x3 device (needs vendor durations and $T_1/T_2$, not only error
   rates) and the shot quota.  For Quantinuum, the memory term per layer stands in for $S_{\rm idle}$; the owner decides
   whether that is accepted as item 4's input.
8. **Paper placeholders and checklist §F items 4, 5, 7** (section 10).
9. **Frozen 2x4 syntax-check upload** (HTTP 500): options listed, none tried — ask Quantinuum support for the upload
   size limit/route, try a newer `qnexus` in a separate venv, or submit a smaller-footprint encoding (needs a plan)
   (`reports/quantinuum_sc_20261028_frozen_2x3_2x4.md` §6).  Compressed 2x4 families passed the checker already.
10. **2x3 IBM-noise class-2 jobs C2_GATE, C2_STAR, C2_COH** — deferred until after the 2026-10-21..28 maintenance, RM
    representation, not yet requested (`prompts/33c` §4 table; `prompts/33f` R3).  Also deferred: C4_F3_*, C4_F6_*
    (`reports/C33_campaign_report.md`), and a re-assembly of `C33_campaign` now that C2_XY4/C2_ECHO exist.
11. **The owner's nine named changes of prompts/20:** **closed** — all nine approved 2026-09-30 and applied
    (`data/H0_replan_owner_decisions.md`; `prompts/LOG.md`).  Update `CLAUDE.md`'s status paragraph accordingly.

**Priority 3 — science next steps**

12. **Quantinuum hardware** (the only device class on which 2x3/2x4 are plausible): obtain access and an HQC budget;
    first a small pilot with a compressed family (owner decides which family is used where, section 6.8).  Gate H1
    (2x3 $B=0$ certified interval $\le 0.1$, recall $\ge 0.8$) and H2 (2x3 $B=1$) are open.
13. **2x4 compressed families under noise at the plan of record** (the $B=1$ campaign used 1x, section 7.3): needs
    ~43x more trajectory time — a GPU job (desktop RTX 3070 or Perlmutter).
14. **Independent random-superposition test** of 2x4 class A v2 and 2x3 class A by a second agent (manual §1.2).
15. Gate M1 (ML credit) and P1 (endpoint curves) remain open; nothing has been claimed for them.

**Housekeeping found while writing**

16. `validation/BLOCKED.md` (git-ignored) still says "prompts/33 STOP: base family ['NAT-O0'] fails the exactness bar
    (2026-10-06 20:09:07 UTC)".  It is **stale**: `data/campaign33/circuits/index.json` (created 2026-10-06 22:12:45
    UTC, commit `7fec49b`) records `base_families_exact` NAT-O0 = true, and C3_AER passed on NAT-O0.  Delete or
    annotate it locally.
17. `prompts/BLOCKED_CV_2x4_plan.md` was resolved by the OD1-OD4 sign-off (2026-10-21).
18. Regenerate `validation/gates.md` / `reports/PROJECT_STATUS.md` (`python scripts/update_status.py`) so the table
    shows QV_2x4_02..05, SKQD_2x4, C2_XY4, C2_ECHO.
19. *(Done 2026-10-31.)* The three local venvs `su2qc-qiskit143` (CI twin), `su2qc-pecos` and `su2qc-selene` are now
    exported to `env/<venv>-venv-requirements.txt` (see `env/README.md`).

---

## 12. Desktop set-up guide

### 12.1 Clone

```bash
mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/digonto10602/su2qc-skqd
cd su2qc-skqd
```

### 12.2 Keep the paper private on the new clone (do this first)

```bash
cat >> .git/info/exclude <<'EOF'
# keep the paper private (owner, 2026-10-30)
/paper/
/reports/su2qc_skqd_paper_draft*.pdf
EOF
git check-ignore -v paper reports/su2qc_skqd_paper_draft_v3.pdf   # both must print a rule
```

### 12.3 Restore what is not in git from the USB

The USB holds the full project at `/run/media/digimonk/digontos_drive_128gb/su2qc-skqd/` **on the laptop**.  On the
desktop the mount point will differ (it depends on the user name and the desktop environment, e.g.
`/run/media/<user>/digontos_drive_128gb` or `/media/<user>/digontos_drive_128gb`); find it with `lsblk -f` or
`findmnt | grep digontos`.  The drive is **NTFS**: it does not keep Unix permissions or symbolic links reliably, so
use `rsync -rt` (no `-a`), and rebuild rather than copy anything that relies on symlinks (the Lean `.lake`).

```bash
USB=/run/media/$USER/digontos_drive_128gb/su2qc-skqd     # adjust to the real mount point
REPO=~/Projects/su2qc-skqd

# private paper and its PDF copies
rsync -rt "$USB/paper/"                                  "$REPO/paper/"
rsync -rt "$USB"/reports/su2qc_skqd_paper_draft*.pdf      "$REPO/reports/"

# caches (git-ignored; large or slow to rebuild)
rsync -rt "$USB/2x4_compression_using_ai_v1/noise/.cache/"  "$REPO/2x4_compression_using_ai_v1/noise/.cache/"   # ~551 MB
rsync -rt "$USB/2x4_compression_using_ai_v1/data/cache/"    "$REPO/2x4_compression_using_ai_v1/data/cache/"     # ~63 MB
rsync -rt "$USB/2x4_compression_using_ai_v1/reviews/001_cache/" "$REPO/2x4_compression_using_ai_v1/reviews/001_cache/"
rsync -rt "$USB/2x4_compression_using_ai_v1/reviews/001_lean/"  "$REPO/2x4_compression_using_ai_v1/reviews/001_lean/"
rsync -rt "$USB/2x2_compression_using_ai_v1/examples/2x2_sandbox/cache/" "$REPO/2x2_compression_using_ai_v1/examples/2x2_sandbox/cache/"
rsync -rt "$USB/data/S2_2x4/cache/"                      "$REPO/data/S2_2x4/cache/"                 # ~26 MB, regenerable in < 20 min
rsync -rt "$USB/data/campaign33/circuits/NAT-O0-k5/"     "$REPO/data/campaign33/circuits/NAT-O0-k5/" # raw *.pytket.json (gz copies are in git)
rsync -rt "$USB/data/campaign33/circuits/.cache/"        "$REPO/data/campaign33/circuits/.cache/"
rsync -rt "$USB/data/campaign33/engine_probes/qir/"      "$REPO/data/campaign33/engine_probes/qir/"
rsync -rt "$USB/results/"                                "$REPO/results/"
rsync -rt "$USB/validation/cloud/"                       "$REPO/validation/cloud/"
rsync -rt "$USB/2x4_compression_using_ai_v1/noise/logs/" "$REPO/2x4_compression_using_ai_v1/noise/logs/"     # ignored queue logs

# project agent memory (git-ignored)
rsync -rt "$USB/.claude/agent-memory/"                   "$REPO/.claude/agent-memory/"

# the unmerged branch c33f-r4-omp-binding was pushed to origin on 2026-10-31 (HELD for the owner, not merged):
git -C "$REPO" fetch origin c33f-r4-omp-binding:c33f-r4-omp-binding
```

- **Lean `.lake` (~7.3 GB):** rebuild instead of copying: `cd 2x4_compression_using_ai_v1/lean && lake build`
  (downloads Mathlib v4.35.0 and compiles; acceptance in manual §6.1).  Copying from NTFS is possible but symlinks
  inside `.lake` may break.
- **graphify-out (~123 MB):** regenerate, do not copy: `graphify update .` (the graph is navigation only).
- `validation/BLOCKED.md` is stale (item 16); no need to restore it.

### 12.4 Environments

The coordinator exported the environments to `env/` (`env/README.md`):

| file | what | create with |
|---|---|---|
| `env/coding.yml` | main env: the `skqd` package, qiskit 2.5.2 / qiskit-aer 0.17.2 (pinned), CUDA-Q 0.15.1 | `mamba env create -f env/coding.yml` |
| `env/latex.yml` | Tectonic, builds the paper and talk PDFs | `mamba env create -f env/latex.yml` |
| `env/su2qc-jepa.yml` | holds `qnexus` 0.51.2 | `mamba env create -f env/su2qc-jepa.yml` |
| `env/su2-quantinuum.yml` | older pytket 1.23 env, reference only | `mamba env create -f env/su2-quantinuum.yml` |
| `env/su2qc-quantinuum-venv-requirements.txt` | venv used for the H2-2SC syntax checks, on top of `coding` | `$(mamba run -n coding which python) -m venv --system-site-packages ~/.local/share/su2qc-quantinuum/venv && ~/.local/share/su2qc-quantinuum/venv/bin/pip install -r env/su2qc-quantinuum-venv-requirements.txt` |
| `env/graphify-venv-requirements.txt` | graphify 0.9.53, isolated from `coding` | `python3 -m venv ~/.local/share/graphify/venv && ~/.local/share/graphify/venv/bin/pip install -r env/graphify-venv-requirements.txt`, then put its `bin/` on `PATH` |

Also exported (2026-10-31): `env/su2qc-qiskit143-venv-requirements.txt` (the qiskit 1.4.3 / aer 0.15.1 twin of the
Perlmutter CI stack), `env/su2qc-pecos-venv-requirements.txt` and `env/su2qc-selene-venv-requirements.txt`.  All
three are isolated venvs built from the `coding` env's Python 3.12.14; the commands are in `env/README.md`.

**Lean toolchain:** install `elan` (https://github.com/leanprover/elan); the toolchain `leanprover/lean4:v4.35.0` is
pinned in `2x4_compression_using_ai_v1/lean/lean-toolchain`; `lake` comes with it.

### 12.5 Claude Code set-up

- **In the repository (cloned):** `CLAUDE.md`, `.claude/agents/` (`planner-fable`, `executor-opus`, `runner-sonnet`,
  `reviewer-opus`, `scribe-haiku`, `genie-opus`), `.claude/skills/gate/`, `.claude/settings.json`.
  `.claude/settings.local.json` is tracked but locally modified on the laptop (the permission deny of `ci/poll.sh`
  edits lives there; check it).  `.claude/agent-memory/` comes from the USB (12.3).
- **User level (`~/.claude/`, not in git):** `CLAUDE.md` (global report rules), `agents/` (auditor, builder, fixer,
  planner, tester), `bin/` (`acceptance-check`, `acceptance-lock`, `next-num`), `hooks/` (`guard.py`,
  `session_start.py`), `skills/` (graphify and others), `settings.json`.  Copy these from the laptop/USB if the
  coordinator backed them up.
- **USB backup of the Claude set-up (done 2026-10-31), at `<usb>/claude_memory_backup/`:**
  - `user_claude_config/` holds `~/.claude/{CLAUDE.md, settings.json, agents, bin, skills, hooks, templates}`.
    There are no credentials; log in again on the desktop.
  - `projects/<project>/memory/` holds Claude's auto-memory, **one folder per project**, each with a `KEY.txt` giving
    the laptop key. `projects/INDEX.md` maps each folder to its laptop project path.
  - For this project use `projects/Projects-su2qc-skqd__CURRENT/memory/`, which has 7 files, including
    `compressed-circuits-separate` and `keep-two-threads-free`. The `__older_subset` folder has only 5.
  - Claude Code keys project memory by the absolute path, with `/` and `.` replaced by `-`. After cloning, run
    `claude` once in the clone, then:
    `cp -r <usb>/claude_memory_backup/projects/Projects-su2qc-skqd__CURRENT/memory ~/.claude/projects/-home-<user>-Projects-su2qc-skqd/`
    (match your clone path).

### 12.6 What the RTX 3070 desktop can run that the laptop could not

The laptop's GTX 1060 Max-Q has compute capability 6.1, below CUDA-Q's `nvidia` target minimum 7.0 (`prompts/LOG.md`
L5 row).  The RTX 3070 (compute capability 8.6, 8 GB) can run:

- **CUDA-Q `nvidia` target** (RUNBOOK engine table: L5 at 2x2, then L5 extended to 2x3 (20 qubits) and 2x4 (28
  qubits); 28 qubits in double precision is 4.3 GB of statevector — fits in 8 GB).
- **GPU Aer** for noisy sampling — but only with qiskit-aer-gpu 0.15.1, which requires a qiskit 1.4.3 env (the twin),
  not `coding`.  Note the documented GPU Kraus bug (item 5): use the RM representation for thermal relaxation.
- The deferred heavy jobs: noisy 2x4 trajectories at the plan of record (section 7.3), the S3 device-model job
  (`slurm/s3_2x3.sbatch`, 2x3 at $2\times10^5$ shots/sector), larger Selene/pecos emulations.
- Keep the owner's rules: 30-minute rule for interactive runs, leave 2 threads free (memory note
  `keep-two-threads-free`; cap parallelism at 10 on the laptop — re-check the desktop's core count), and propose more
  GPUs only with measured scaling.

### 12.7 First-day checklist

```bash
cd ~/Projects/su2qc-skqd
mamba activate coding
python scripts/check_package.py          # must print PACKAGE OK
pytest -q tests                          # expect exactly one known failure: test_q0p_plan.py::test_d3r_plan_reproduces_prototype
graphify update .                        # rebuild graphify-out/ (seconds, no API cost)
python scripts/update_status.py          # regenerate validation/gates.md and reports/PROJECT_STATUS.md
scripts/ci_check.sh                      # CI state (exit 0 = all done)
git branch -a                            # c33f-r4-omp-binding present after 12.3?
git check-ignore -v paper                # paper still private?
nvidia-smi                               # GPU visible?
```

Then read, in this order: this report §11, `prompts/LOG.md` (last rows), `prompts/36a_CV_2x4_plan_fix_20261019.md`,
`2x4_compression_using_ai_v1/README.md`, `2x4_compression_using_ai_v1/noise/reports/004-noisy-skqd-campaign.md`.

---

## 13. File map (top level)

| path | what |
|---|---|
| `CLAUDE.md` | agent operating manual + skqd-ci rules (status paragraph stale, see banner) |
| `README.md`, `LICENSE`, `pyproject.toml`, `Makefile`, `requirements*.txt` | package entry points (`make check`, `make test`, `make gates`, `make status`) |
| `RUNBOOK.md` | first-session runbook and the binding engine/HPC policy for Perlmutter |
| `SKQD-CI-SETUP.md` | how the Perlmutter CI was installed |
| `proposal/` | the reference manual, amendment 01, Quantinuum access-request draft |
| `src/skqd/` | the package: physics core (`su2`, `fermions`, `lattice`, `vertex`, `basis`, `hamiltonian`, `fullspace`, `codec`, `codec_dedup`, `exact`), SKQD (`krylov`, `skqd`, `noise`, `controls`, `ml`, `selected_ci`), circuits (`circuits_ir`, `circuits_qiskit`, `circuits_cudaq`, `reference_sim`, `sparse_sim`, `quantinuum_native`), hardware (`hardware`, `idle`, `coherence`, `device_req`, `hpc`), `campaign33/`, `report` |
| `scripts/` | 93 gate and helper scripts (`run_gate.py`, `gate_*.py`, `h0_*.py`, `campaign33*.py`, `quantinuum_*.py`, `selected_ci_baseline.py`, `ci_request.sh`, `ci_check.sh`, `update_status.py`) |
| `tests/` | pytest suite (57 entries) |
| `validation/` | every gate's JSON (machine-readable truth), `gates.md`, `archive/`, `dryrun/` |
| `reports/` | human-readable gate reports, planner analyses, full reports, CI logs `ci-*.out`, PDFs |
| `data/` | reference numbers, hardware records (`data/hardware/`), shot plans, owner decisions, campaign-33 data, Quantinuum circuits (`data/quantinuum/`), baselines |
| `prompts/` | every plan (00-36a), `LOG.md` (execution log), `README.md`, `ROUTING.md`, `ESCALATION_TEMPLATE.md` |
| `ci/` | CI requests, status, allow-lists, parts, pollers |
| `jobs/` | Slurm batch files used by the CI (`gate.sbatch`, `smoke.sbatch`, `env/`) |
| `slurm/` | `s3_2x3.sbatch` (S3 device-model job) |
| `results/` | git-ignored run outputs (USB) |
| `scratch/` | planner prototypes and executor scratch (partly ignored) |
| `env/` | exported environments (new, 2026-10-31) |
| `2x4_compression_using_ai_v1/` | compression study: code, Lean, manual, notes, reviews, noise study, 2x4 data |
| `2x3_compression_using_ai_v1/`, `2x2_compression_using_ai_v1/` | per-lattice study data |
| `paper/` | **private**, git-excluded: paper and talk |
| `graphify-out/` | git-ignored code graph (regenerate) |
| `.claude/` | agents, skills, settings; `agent-memory/` and `worktrees/` ignored |

---

## 14. Appendix: every report and validation JSON

The lists below were generated from the files themselves on 2026-10-31 (first heading of each report; `title` and
`status` of each JSON).  `ci-*.out` logs and `validation/ci_*.json` CI files are listed by count only.

### 14.1 Package reports (`reports/*.md`)

| file | first heading |
|---|---|
| `reports/2x3_four_class_campaign_plan_20261006.md` | The 2x3 four-class simulation campaign on Perlmutter — plan for the owner (2026-10-06) |
| `reports/2x3_qec_amplification_strategy_20261002.md` | 2x3 on quantum hardware: can error correction, error detection or an "amplifier" give a substantial result? (planner analysis, 2026-10-02) |
| `reports/2x3_shot_rule_estimator_ruling_20261003.md` | Planner ruling (2026-10-03): the 2x3 shot rule and the clean-fraction estimator |
| `reports/C1_IDEAL.md` | Campaign 33 token C1_IDEAL (class 1): IR-L0, NAT-O0, IBM-U/T0/T3 exactness vs the exact Krylov states; noiseless sampling at the f=0.10 plan and 2e5 … |
| `reports/C2_CAL.md` | Campaign 33 token C2_CAL (class 2): 21-qubit timing ladder {8,32,128,512} on B0_ref117_k1 (IBM-T0), Kraus vs PTA, cuStateVec vs batched; sizes C2_* |
| `reports/C2_ECHO.md` | Campaign 33 token C2_ECHO (class 2): I-ECHO on IBM-T0 |
| `reports/C2_KCHK.md` | Campaign 33 token C2_KCHK (class 2): prompts/33d R3 + 33e R2: the GPU Kraus check on IBM-T0 B0_ref117_k1 (I-ECHO); run 2 (default, --content cpu_only… |
| `reports/C2_XY4.md` | Campaign 33 token C2_XY4 (class 2): I-XY4 on IBM-T3, echo and star halves (information) |
| `reports/C33_F1_B1.md` | Campaign 33 split run F1_B1: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F2_B1.md` | Campaign 33 split run F2_B1: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F4_B0a.md` | Campaign 33 split run F4_B0a: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F4_B0b.md` | Campaign 33 split run F4_B0b: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F4_B1a.md` | Campaign 33 split run F4_B1a: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F4_B1b.md` | Campaign 33 split run F4_B1b: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F5_B1.md` | Campaign 33 split run F5_B1: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F7_B1.md` | Campaign 33 split run F7_B1: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F8_B0a.md` | Campaign 33 split run F8_B0a: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F8_B0b.md` | Campaign 33 split run F8_B0b: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F8_B1a.md` | Campaign 33 split run F8_B1a: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_F8_B1b.md` | Campaign 33 split run F8_B1b: the 2 parts merged (prompts/33a step D4) |
| `reports/C33_campaign_report.md` | 2x3 four-class campaign: matrix, S3-quota merges and the comparison with every earlier 2x3 result |
| `reports/C3_AER.md` | Campaign 33 token C3_AER (class 3): NAT-O0 noiseless on Aer: per-state agreement; f=1 SKQD reference of the native family |
| `reports/C4_CF.md` | Campaign 33 token C4_CF (class 4): CF_traj redo on the GPU: K=2000 faulty Pauli trajectories per arm |
| `reports/C4_F1_B0.md` | Campaign 33 token C4_F1_B0 (class 4): E1 x O0 plan-of-record run, B=0 |
| `reports/C4_F1_B1.md` | Campaign 33 token C4_F1_B1 (class 4): E1 x O0 plan-of-record run, B=1 |
| `reports/C4_F2_B0.md` | Campaign 33 token C4_F2_B0 (class 4): E2 x O0, B=0 |
| `reports/C4_F2_B1.md` | Campaign 33 token C4_F2_B1 (class 4): E2 x O0, B=1 |
| `reports/C4_F4_B0a.md` | Campaign 33 token C4_F4_B0a (class 4): E7(0.10) x O0, S3-quota half a, B=0 (1e5) |
| `reports/C4_F4_B0b.md` | Campaign 33 token C4_F4_B0b (class 4): E7(0.10) x O0, S3-quota half b, B=0 (1e5) |
| `reports/C4_F4_B1a.md` | Campaign 33 token C4_F4_B1a (class 4): E7(0.10) x O0, S3-quota half a, B=1 (1e5) |
| `reports/C4_F4_B1b.md` | Campaign 33 token C4_F4_B1b (class 4): E7(0.10) x O0, S3-quota half b, B=1 (1e5) |
| `reports/C4_F5_B0.md` | Campaign 33 token C4_F5_B0 (class 4): E7(0.07) x O0 at the f=0.10 plan, B=0 |
| `reports/C4_F5_B1.md` | Campaign 33 token C4_F5_B1 (class 4): E7(0.07) x O0 at the f=0.10 plan, B=1 |
| `reports/C4_F7_B0.md` | Campaign 33 token C4_F7_B0 (class 4): E1 x the chosen exact variant, B=0 |
| `reports/C4_F7_B1.md` | Campaign 33 token C4_F7_B1 (class 4): E1 x the chosen exact variant, B=1 |
| `reports/C4_F8_B0a.md` | Campaign 33 token C4_F8_B0a (class 4): E8, S3-quota half a, B=0: the S3 recall criterion |
| `reports/C4_F8_B0b.md` | Campaign 33 token C4_F8_B0b (class 4): E8, S3-quota half b, B=0 |
| `reports/C4_F8_B1a.md` | Campaign 33 token C4_F8_B1a (class 4): E8, S3-quota half a, B=1 |
| `reports/C4_F8_B1b.md` | Campaign 33 token C4_F8_B1b (class 4): E8, S3-quota half b, B=1 |
| `reports/C4_FCELLS_A.md` | Campaign 33 token C4_FCELLS_A (class 4): 10-min ladder then f-cells E1,E2,E3,E4,E5a/b/c x O0-O4 (+O6 info) |
| `reports/C4_FCELLS_B.md` | Campaign 33 token C4_FCELLS_B (class 4): f-cells E6a/b/c, E7(0.05/0.07/0.10/0.15) x O0-O4; faithful S3 redo (IR-L3-RZZ, E8, 32 x 100, seed 11) |
| `reports/C4_PART_01.md` | Campaign 33 token C4_PART_01 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_01.json in the requested commi… |
| `reports/C4_PART_02.md` | Campaign 33 token C4_PART_02 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_02.json in the requested commi… |
| `reports/C4_PART_03.md` | Campaign 33 token C4_PART_03 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_03.json in the requested commi… |
| `reports/C4_PART_04.md` | Campaign 33 token C4_PART_04 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_04.json in the requested commi… |
| `reports/C4_PART_05.md` | Campaign 33 token C4_PART_05 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_05.json in the requested commi… |
| `reports/C4_PART_06.md` | Campaign 33 token C4_PART_06 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_06.json in the requested commi… |
| `reports/C4_PART_07.md` | Campaign 33 token C4_PART_07 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_07.json in the requested commi… |
| `reports/C4_PART_08.md` | Campaign 33 token C4_PART_08 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_08.json in the requested commi… |
| `reports/C4_PART_09.md` | Campaign 33 token C4_PART_09 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_09.json in the requested commi… |
| `reports/C4_PART_10.md` | Campaign 33 token C4_PART_10 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_10.json in the requested commi… |
| `reports/C4_PART_11.md` | Campaign 33 token C4_PART_11 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_11.json in the requested commi… |
| `reports/C4_PART_12.md` | Campaign 33 token C4_PART_12 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_12.json in the requested commi… |
| `reports/C4_PART_13.md` | Campaign 33 token C4_PART_13 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_13.json in the requested commi… |
| `reports/C4_PART_14.md` | Campaign 33 token C4_PART_14 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_14.json in the requested commi… |
| `reports/C4_PART_15.md` | Campaign 33 token C4_PART_15 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_15.json in the requested commi… |
| `reports/C4_PART_16.md` | Campaign 33 token C4_PART_16 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_16.json in the requested commi… |
| `reports/C4_PART_17.md` | Campaign 33 token C4_PART_17 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_17.json in the requested commi… |
| `reports/CF_estimator_2x2_information_20261003.md` | CF_estimator_2x2_info — the recorded 2x2 clean-fraction values, by statistic (information) |
| `reports/CF_traj.md` | Gate CF_traj: Pauli-trajectory decomposition of the A6 reference-hit excess and the near-clean correction r_nc (prompts/28 Part A, re-assembled under… |
| `reports/CV_2x2_information_20261005.md` | Gate CV_2x2_info — the CV curves on the recorded H0_2x2 ibm_kingston counts (information; not a device test (saturation)) |
| `reports/CV_2x3_plan.md` | Gate CV_2x3_plan — energy convergence (shots, Krylov k) and weighted coverage of the 2x3 D3'-R plan in the S1 proxy emulation (owner decision 2a), on… |
| `reports/CV_2x4_plan.md` | Gate CV_2x4_plan — the 2x4 noiseless shot plan (D3'-R at y = 1), its convergence in the exact emulation, the decoder acceptance, the IR-L0 bundles an… |
| `reports/E1_gauss_law_two_builders.md` | Gate E1 — Gauss's law, kernel, sector split, two-builder agreement (2x2) |
| `reports/E2_counts_codewords_decoder.md` | Gate E2 — state counts, vertex tables, codewords and decoder |
| `reports/E3_exact_references.md` | Gate E3 — exact references, static sectors, derived quantities, Krylov step |
| `reports/ENC_compare.md` | Gate ENC_compare -- encoding comparison at fixed physics (prompts/34) |
| `reports/H0P_heron_preparation.md` | Gate H0P — H0 preparation on the FakeFez calibration snapshot |
| `reports/H0P_ibm_fez_escalation_20260921.md` | H0P_ibm_fez escalation (2026-09-21) — the B=1 support did not saturate: cause, odds, decision |
| `reports/H0P_ibm_fez_heron_preparation.md` | Gate H0P_ibm_fez — H0 preparation on the ibm_fez calibration snapshot |
| `reports/H0P_rehearsal_heron_preparation.md` | Gate H0P_rehearsal — H0 preparation on the FakeFez calibration snapshot |
| `reports/H0P_repro_heron_preparation.md` | Gate H0P_repro — H0 preparation on the FakeFez calibration snapshot |
| `reports/H0_2x2_dryrun.md` | Gate H0_2x2_dryrun -- the full 2x2 SKQD run, dry run (local Aer on the FakeKingston snapshot at 1000 shots per pub; a path check) |
| `reports/H0_2x2_full_hardware_report_20261002.md` | The 2x2 plaquette hardware run: full report against the SKQD plan |
| `reports/H0_2x2_ibm_kingston.md` | Gate H0_2x2 -- the full 2x2 SKQD run, ibm_kingston |
| `reports/H0_2x2_prereg_20261002T1949Z.md` | H0_2x2 preregistration -- ibm_kingston, calibration `84d59cbf9b5973d1` |
| `reports/H0_canary_hardware_2x2.md` | Gate H0_canary — 2x2 calibration session on ibm_fez |
| `reports/H0_canary_planner_analysis_20260922.md` | H0 canary NO-GO — planner analysis and ruling (2026-09-22) |
| `reports/H0_ddrep_dryrun.md` | Gate H0_ddrep_dryrun -- XY4 replication and the T1-collapse mechanism, dry run (local Aer on the FakeKingston snapshot; a path check, not a predictio… |
| `reports/H0_ddrep_ibm_kingston.md` | Gate H0_ddrep -- XY4 replication and the T1-collapse mechanism, ibm_kingston |
| `reports/H0_ddrep_prereg_20261006T0501Z.md` | H0_ddrep preregistration -- ibm_kingston, calibration `cb40a250fb24387d` |
| `reports/H0_ddrep_prereg_prototype_20261002T1906Z.md` | H0_ddrep preregistration -- ibm_kingston, calibration `84d59cbf9b5973d1` (OFFLINE PROTOTYPE on the committed record -- not a preregistration) |
| `reports/H0_ddtest_dryrun.md` | Gate H0_ddtest_dryrun -- client-side DD A/B test, dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction) |
| `reports/H0_ddtest_ibm_kingston.md` | Gate H0_ddtest -- client-side DD A/B test, ibm_kingston |
| `reports/H0_ddtest_prereg_20261002T1906Z.md` | H0_ddtest preregistration -- ibm_kingston, calibration `84d59cbf9b5973d1` |
| `reports/H0_device_survey_20260922.md` | Device survey for the 2x2 H0 patch (prompts/20 part E) |
| `reports/H0_device_survey_live_20260930.md` | Device survey for the 2x2 H0 patch (prompts/20 part E) |
| `reports/H0_diag_dryrun_hardware_2x2.md` | Gate H0_diag_dryrun — the H0 diagnostic session on AerSimulator.from_backend(FakeFez) [local testing mode] |
| `reports/H0_diag_hardware_2x2.md` | Gate H0_diag — the H0 diagnostic session on ibm_fez |
| `reports/H0_diag_prereg.md` | H0 idle-aware model — data/hardware/H0_diag_prep on ibm_fez (2026-09-22T08:00:30-06:00) |
| `reports/H0_dryrun_hardware_2x2.md` | Gate H0_dryrun — 2x2 calibration session on AerSimulator.from_backend(FakeFez) [local testing mode] |
| `reports/H0_idle_model_frozen_set.md` | H0 idle-aware model — data/hardware/H0_prep on ibm_fez (2026-09-22T08:00:30-06:00) |
| `reports/H0_kpilot_dryrun.md` | Gate H0_kpilot_dryrun -- the kingston T2* pilot, dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction) |
| `reports/H0_kpilot_ibm_kingston.md` | Gate H0_kpilot -- the kingston T2* pilot, ibm_kingston |
| `reports/H0_kpilot_prereg_20261002T1627Z.md` | H0_kpilot preregistration -- ibm_kingston, calibration `ec74eb8bf15dde41` |
| `reports/H0_model_postdiction_2x2.md` | Gate H0_model — post-diction of the H0 hardware counts at both ends of the T2 bracket |
| `reports/H0_patch_select.md` | T2-aware patch selection for the 2x2 H0 run |
| `reports/H0_patch_select_fake_fez_20260922.md` | T2-aware patch selection for the 2x2 H0 run |
| `reports/H0_patch_select_fake_marrakesh_20260922.md` | T2-aware patch selection for the 2x2 H0 run |
| `reports/H0_patch_select_ibm_fez_20260922.md` | T2-aware patch selection for the 2x2 H0 run |
| `reports/H0_patch_select_ibm_marrakesh_20260922.md` | T2-aware patch selection for the 2x2 H0 run |
| `reports/H0_prereg_draft.md` | H0 preregistration (draft) — 2x2 calibration session on a Heron-class device |
| `reports/H0_prereg_ibm_fez.md` | H0 preregistration (draft) — 2x2 calibration session on a Heron-class device |
| `reports/H0_replan_planner_analysis_20260922.md` | H0 re-plan after the diagnostic — planner analysis and rulings (2026-09-22) |
| `reports/H0_support_plan_FakeFez.md` | H0 shot plan (rule D3') — FakeFez |
| `reports/H0_support_plan_ibm_fez.md` | H0 shot plan (rule D3') — ibm_fez |
| `reports/H0_support_plan_live_20260921.md` | H0 shot plan (rule D3') — data/hardware/H0_ibm_fez/calibration_20260921T2053Z.json |
| `reports/K0_2x3_2x4.md` | Gate K0_2x3_2x4 -- ibm_kingston readiness of 2x3 and 2x4 |
| `reports/K0_2x3_ibm_heron_nogo.md` | 2x3 on IBM Heron: NO-GO on the K0 analysis (a model verdict, not a measurement) |
| `reports/K1_2x3_fpilot.md` | Gate K1_2x3_fpilot -- the 2x3 clean-fraction pilot, ibm_kingston |
| `reports/K1_2x3_fpilot_dryrun.md` | Gate K1_2x3_fpilot_dryrun -- the 2x3 clean-fraction pilot, dry run (path check on the FakeKingston snapshot) |
| `reports/K1_2x3_fpilot_prereg_20261006T0745Z.md` | K1_2x3_fpilot preregistration -- ibm_kingston, calibration `99035ef05c36019e` |
| `reports/L2_qiskit_check.md` | Laptop gate L2 — Qiskit circuits versus the numpy reference (2x2) |
| `reports/L3_cz_counts.md` | Laptop gate L3 — transpiled CZ counts at 2x2 (gate S2 measurement) |
| `reports/L4_aer_noise.md` | Laptop gate L4 — Aer noise-model sampling at 2x2 (S3 preparation) |
| `reports/L4_fez_aer_noise.md` | Laptop gate L4_fez — Aer noise-model sampling at 2x2 (S3 preparation) |
| `reports/L5_cudaq_check.md` | Laptop gate L5 — CUDA-Q circuits versus the numpy reference (2x2) |
| `reports/PACKAGE_FULL_REPORT_20261005.md` | su2qc-skqd: full package report (2026-10-05) |
| `reports/PACKAGE_FULL_REPORT_20261006.md` | su2qc-skqd: full package report (2026-10-06) |
| `reports/PROJECT_FULL_REPORT_20261013.md` | su2qc-skqd: full project report for a judge (2026-10-13) |
| `reports/PROJECT_FULL_REPORT_20261015.md` | su2qc-skqd: full project report for a judge (2026-10-15) |
| `reports/PROJECT_STATUS.md` | Project status (generated by scripts/update_status.py, 2026-10-21 15:22 UTC) |
| `reports/Q0P_2x2.md` | Gate Q0P_2x2 — signed 2x2 circuits compiled to the Quantinuum native gate set, verified exactly and costed (prompts/35 T1) |
| `reports/Q0P_2x3.md` | Gate Q0P_2x3 — signed 2x3 circuits compiled to the Quantinuum native gate set, verified exactly, costed and packaged (Stage A; Stage E/P not run) |
| `reports/Q0P_2x3_plan.md` | Gate Q0P_2x3_plan — the 2x3 shot rule D3'-R (minimum sizing, owner decision 2a), the f_hat_ideal statistic and GO rule v3, Stage E / P v3, the emulat… |
| `reports/Q0P_2x3_prereg.md` | Q0P_2x3 preregistration block v3 (prompts/28 B3 as amended by prompts/29 Part B', prompts/30 and prompts/31) |
| `reports/Q0P_2x4.md` | Gate Q0P_2x4 — signed 2x4 circuits compiled to the Quantinuum native gate set, proven equal to their IR by local equivalence and costed (prompts/35 T… |
| `reports/QEMU_2x2.md` | Gate QEMU_2x2 — 2x2 native circuits on Quantinuum's local emulator (pytket-quantinuum H2-1LE, pytket-pecos, noiseless state vector; prompts/35 T4) |
| `reports/QEMU_2x3_laptop_smoke.md` | QEMU_2x3_laptop_smoke |
| `reports/QEMU_2x4.md` | QEMU_2x4 — 2x4 on the local emulator H2-1LE: infeasible (prompts/35 3.6) |
| `reports/QH_2x2.md` | Gate QH_2x2 — 2x2 native circuits as Helios Guppy/HUGR programs on Selene (Quest, IdealErrorModel), offline (prompts/35 T6) |
| `reports/QH_2x3.md` | Gate QH_2x3 — 2x3 native circuits as Helios Guppy/HUGR programs on Selene (Quest, IdealErrorModel), offline (prompts/35 T6; information) |
| `reports/QH_2x4.md` | QH_2x4 — not attempted |
| `reports/QN_2x2.md` | Gate QN_2x2 — 2x2 native circuits under noiseless sampling and the Quantinuum noise models (prompts/35 T2 + T3) |
| `reports/QN_2x4.md` | Gate QN_2x4 — 2x4 native circuits under the Quantinuum noise models: analytic fault-free fraction and gate-only f (prompts/35 T3, R3; nothing sampled) |
| `reports/QSC_prepared.md` | QSC_prepared — T5 syntax checks prepared, not run |
| `reports/QV_2x4_01.md` | QV_2x4_01 |
| `reports/QV_2x4_02.md` | QV_2x4_02 |
| `reports/QV_2x4_03.md` | QV_2x4_03 |
| `reports/QV_2x4_04.md` | QV_2x4_04 |
| `reports/QV_2x4_05.md` | QV_2x4_05 |
| `reports/S1_support_emulation_controls.md` | Gate S1 — emulated support generation, certification and classical controls |
| `reports/S2D_2x3_device_requirements.md` | Device requirements for the 2x3 coarse-step circuits (20 qubits, all-to-all) |
| `reports/S2D_device_budgets.md` | Gate S2D — device-resolved budgets for the exact circuits (2x2 Heron, 2x3 all-to-all RZZ) |
| `reports/S2D_idle_device_budgets.md` | Gate S2D's criterion on the idle-aware f — 2x2 on Heron |
| `reports/S2D_levers_2x2_kingston.md` | Gate S2D_levers -- the 2x2 coarse step on ibm_kingston: duration levers, f at both T2 ends, r_crit |
| `reports/S2D_levers_C6_ruling_20261002.md` | Ruling on criterion C6 of gate S2D_levers (planner, 2026-10-02) |
| `reports/S2D_levers_patch_select_ibm_kingston_20260930.md` | T2-aware patch selection for the 2x2 H0 run |
| `reports/S2D_levers_planner_analysis_20261001.md` | 2x2 on IBM: can the duration levers reach f >= 0.1? — planner analysis (2026-10-01) |
| `reports/S2D_recall_at_predicted_f.md` | 2x3 recall at the clean-shot fractions predicted by gate S2D (production budget 2e5 shots per sector) |
| `reports/S2D_shot_quota_decision_20260922.md` | Amendment 01, open item 5 — the shot quota of manual Step 9.2: analysis and recommendation (2026-09-22) |
| `reports/S2_2x4_compilation_and_device_requirement.md` | Gate S2_2x4 — the 2x4 coarse step compiled, verified, and its device requirement |
| `reports/S2_2x4_planner_analysis_20260930.md` | 2x4 compilation and device requirement — planner analysis (2026-09-30) |
| `reports/S2_duration_and_idle_2x2.md` | Circuit family under DURATION, not gate count — 2x2, 2026-09-22T08:00:30-06:00 |
| `reports/S2_escalation_analysis.md` | Gate S2 escalation — what compilation and term ablation can and cannot gain |
| `reports/S2_fixed_angle_circuits.md` | Fixed-angle generator (gate-S2 escalation, prompts/11) — cost floor, leakage and recall |
| `reports/S2_structured_circuits.md` | Gate S2 — structured circuits for the hopping and interior-corner plaquette terms |
| `reports/S3_device_model.md` | Gate S3 — GPU throughput calibration of the 2x3 B=0 circuit set (reduced size; the S3 recall criterion is NOT evaluated) |
| `reports/S3_smoke_device_model.md` | Gate S3 (smoke) — device-model sampling of the 2x3 B=1 circuit set |
| `reports/SESSION_HANDOVER_20260921_24.md` | Session handover — 21 to 24 September 2026 |
| `reports/SESSION_HANDOVER_20260925_1002.md` | Session handover — 25 September to 2 October 2026 |
| `reports/SKQD_2x4.md` | SKQD_2x4 — the 2x4 noiseless SKQD pipeline on the Aer GPU samples of slots QV_2x4_02..06 (prompts/36 section 2.2) |
| `reports/circuit_structure.md` | Structure of the Hamiltonian terms in codeword space (input to gate S2) |
| `reports/encodings_candidate_list_20261007.md` | Candidate encodings for SU(2) + staggered quarks on 2xL ladders at $j_{\max}=\tfrac12$ (planner list, 2026-10-07) |
| `reports/ibm_decoherence_literature_20261002.md` | Idle-time dephasing and coherent errors on IBM Heron: what the literature offers for the 2x2 circuit, ranked for a 571-second budget |
| `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md` | 2x3 and 2x4 on ibm_kingston, and on IonQ — planner analysis (2026-10-02) |
| `reports/laptop_vs_hpc_plan.md` | What runs where: laptop (i7-8750H, GTX 1060 Max-Q 6 GB) versus desktop / cluster / QPU |
| `reports/qpu_survey_2x3_20261002.md` | Which quantum computer can run the signed 2x3 circuits? Device survey and ranking (2026-10-02) |
| `reports/quantinuum_sc_20261028_2x2_frozen_vs_compressed.md` | H2-2SC syntax check: frozen vs compressed 2x2 circuits (2026-10-28) |
| `reports/quantinuum_sc_20261028_all_lattices.md` | H2-2SC syntax check of every frozen and compressed circuit family, 2x2 / 2x3 / 2x4 (2026-10-28) |
| `reports/quantinuum_sc_20261028_frozen_2x2.md` | H2-2SC syntax check of the frozen 2x2 circuits (2026-10-28) |
| `reports/quantinuum_sc_20261028_frozen_2x3_2x4.md` | H2-2SC syntax check of the frozen 2x3 and 2x4 circuits (2026-10-28) |
| `reports/quantinuum_sc_k5_2x2_2x3.md` | H2-2SC syntax check of the k = 5 circuit sets, 2x2 and 2x3 (2026-10-28) |
| `reports/selected_ci_baseline.md` | Classical selected-CI baseline for SKQD (2x2, 2x3, 2x4) |

Other report files: `reports/physical_states_catalogue.pdf`, `reports/physical_states_catalogue_latex.pdf`, `reports/plaq1_compression_steps_2x4.pdf`, `reports/plaq1_compression_teaching.pdf`, `reports/plaq1_compression_teaching_edited.pdf`, `reports/valid_states_2x4_plaquettes.pdf`, `reports/physical_states_catalogue_all_states.csv`, generator folders `reports/*_src/`, `reports/dryrun/` (dry-run reports).  The private paper PDFs `reports/su2qc_skqd_paper_draft*.pdf` are git-excluded.
CI job logs: 60 files `reports/ci-<jobid>.out` (written by the CI; do not edit).

### 14.2 Compression-study reports, notes and reviews

| file | first heading |
|---|---|
| `2x4_compression_using_ai_v1/MANUAL_lgt_circuit_compression.md` | Manual: compressing Trotterised coarse-step circuits of lattice gauge theories (the genie-opus technique) |
| `2x4_compression_using_ai_v1/README.md` | 2x4_compression_using_ai_v1 |
| `2x4_compression_using_ai_v1/reports/001-phase1-study-and-comparison.md` | 001 — Phase 1: the two reference documents, the package's 2x4 compilation, and what an AI-guided compression loop could do to it |
| `2x4_compression_using_ai_v1/reports/002-phase2-compression-results.md` | 002 — Phase 2: the 2x4 coarse-step circuits compressed 25–120x, verified at the package bar, with the rewrite rules proved in Lean |
| `2x4_compression_using_ai_v1/reports/003-full-compression-report.md` | 003 — Full report: compressing the 2x4 SKQD coarse-step circuits from 71 548 to 582–1 740 two-qubit gates |
| `2x4_compression_using_ai_v1/reports/004-c4-c3-second-round-and-2x3.md` | 004 — C4: one more 2x4 round (v2 families) and C3: the 2x3 compressed families |
| `2x4_compression_using_ai_v1/noise/README.md` | noise/ — C5 + C6: compressed circuits under published device noise models |
| `2x4_compression_using_ai_v1/noise/reports/001-quantinuum-device-info.md` | 001 — Quantinuum device information from public sources (C6) |
| `2x4_compression_using_ai_v1/noise/reports/002-noise-models.md` | 002 — Noise models built from published device data (C5) |
| `2x4_compression_using_ai_v1/noise/reports/003-noise-results.md` | 003 — Compressed circuits under published noise models: accuracy and behaviour (C5) |
| `2x4_compression_using_ai_v1/noise/reports/004-noisy-skqd-campaign.md` | 004 -- Noisy SKQD campaign with the compressed circuits (2x2, 2x3, 2x4) |
| `2x4_compression_using_ai_v1/noise/notes/campaign_budget.md` | Noisy SKQD campaign: timing and shot budget |
| `2x4_compression_using_ai_v1/notes/001-phase2-plan.md` | 001 — Phase-2 build plan: an evaluator-guided compression loop for the 2x4 coarse-step circuits |
| `2x4_compression_using_ai_v1/notes/002-owner-answers-phase2-go.md` | 002 — Owner answers to the phase-1 questions; phase 2 approved (2026-10-21) |
| `2x4_compression_using_ai_v1/notes/003-phase2-iteration-plan-corner-factorisation.md` | 003 — Phase-2 plan in force: corner-factorised plaquette (family F2) first, then hops |
| `2x4_compression_using_ai_v1/notes/004-approximate-class-tolerance.md` | 004 — The approximate class: what is dropped, the tolerance, and why it is enough for SKQD |
| `2x4_compression_using_ai_v1/notes/005-planner-request-ultimate-compression-review.md` | 005 — Planner request: is the best verified 2x4 family the ultimate compression? (review + help) |
| `2x4_compression_using_ai_v1/notes/006-certified-pruned-verification.md` | 006 — Full-circuit verification by certified pruned simulation (change of method for A2; the bar is unchanged) |
| `2x4_compression_using_ai_v1/notes/007-planner-review-ultimate-compression.md` | 007 — Planner review: is the best verified 2x4 family the ultimate compression? Lower bounds, next steps, the class-B ruling, and what adoption would… |
| `2x4_compression_using_ai_v1/notes/008-owner-decisions-C1-C6.md` | 008 — Owner decisions C1–C6 on the compressed circuits (2026-10-21) |
| `2x4_compression_using_ai_v1/notes/009-family-api.md` | 009 — Family loader API for the noise agent (C5) and later users |
| `2x4_compression_using_ai_v1/notes/010-c4-c3-work-plan.md` | 010 — Work plan for C4 (one more 2x4 round, hard stop) and C3 (2x3) |
| `2x4_compression_using_ai_v1/notes/011-2x2-families.md` | 011 — 2x2 compressed families (owner request 2026-10-28) |
| `2x4_compression_using_ai_v1/notes/012-folder-split.md` | 012 — One folder per lattice (2x2, 2x3, 2x4) |
| `2x4_compression_using_ai_v1/notes/013-native-exports-2x3-2x4.md` | 013 — Quantinuum native exports of the 2x3 and 2x4 compressed families (for the H2-2SC syntax check) |
| `2x4_compression_using_ai_v1/notes/014-k5-addons-2x2-2x3.md` | 014 — k = 5 add-on families for the compressed 2x2 and 2x3 families |
| `2x4_compression_using_ai_v1/reviews/001-independent-verification.md` | 001 — Independent verification of the phase-2 compression claim (class A 1 736–1 740 ZZ, class B 582–800 ZZ) |
| `2x4_compression_using_ai_v1/reviews/002-manual-cold-read.md` | Review 002 — cold read of `MANUAL_lgt_circuit_compression.md` (as an agent from another LGT project) |
| `2x3_compression_using_ai_v1/README.md` | 2x3_compression_using_ai_v1 |
| `2x2_compression_using_ai_v1/README.md` | 2x2_compression_using_ai_v1 |

### 14.3 Validation JSONs (`validation/*.json`, CI-written `ci_*.json` excluded)

| file | status | criteria | title |
|---|---|---|---|
| `validation/C1_IDEAL.json` | PASS | 10 (0 failing) | Campaign 33 token C1_IDEAL (class 1): IR-L0, NAT-O0, IBM-U/T0/T3 exactness vs the exact Krylov states; noiseless sampling at the … |
| `validation/C2_CAL.json` | PASS | 12 (0 failing) | Campaign 33 token C2_CAL (class 2): 21-qubit timing ladder {8,32,128,512} on B0_ref117_k1 (IBM-T0), Kraus vs PTA, cuStateVec vs b… |
| `validation/C2_ECHO.json` | PASS | 9 (0 failing) | Campaign 33 token C2_ECHO (class 2): I-ECHO on IBM-T0 |
| `validation/C2_KCHK.json` | FAIL | 13 (2 failing) | Campaign 33 token C2_KCHK (class 2): prompts/33d R3 + 33e R2: the GPU Kraus check on IBM-T0 B0_ref117_k1 (I-ECHO); run 2 (default… |
| `validation/C2_XY4.json` | PASS | 9 (0 failing) | Campaign 33 token C2_XY4 (class 2): I-XY4 on IBM-T3, echo and star halves (information) |
| `validation/C33_F1_B1.json` | PASS | 4 (0 failing) | Campaign 33 split run F1_B1: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F1_B1_cv3_part1of2.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_16 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_16.json in… |
| `validation/C33_F1_B1_cv3_part2of2.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_17 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_17.json in… |
| `validation/C33_F1_B1_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_10 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_10.json in… |
| `validation/C33_F2_B1.json` | PASS | 4 (0 failing) | Campaign 33 split run F2_B1: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F2_B1_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_12 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_12.json in… |
| `validation/C33_F4_B0a.json` | FAIL | 3 (2 failing) | Campaign 33 split run F4_B0a: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F4_B0a_part2of2.json` | FAIL | 8 (1 failing) | Campaign 33 token C4_PART_02 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_02.json in… |
| `validation/C33_F4_B0b.json` | FAIL | 3 (2 failing) | Campaign 33 split run F4_B0b: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F4_B0b_part2of2.json` | FAIL | 8 (1 failing) | Campaign 33 token C4_PART_04 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_04.json in… |
| `validation/C33_F4_B1a.json` | PASS | 3 (0 failing) | Campaign 33 split run F4_B1a: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F4_B1a_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_03 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_03.json in… |
| `validation/C33_F4_B1b.json` | PASS | 3 (0 failing) | Campaign 33 split run F4_B1b: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F4_B1b_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_05 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_05.json in… |
| `validation/C33_F5_B1.json` | PASS | 4 (0 failing) | Campaign 33 split run F5_B1: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F5_B1_cv3_part1of2.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_14 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_14.json in… |
| `validation/C33_F5_B1_cv3_part2of2.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_15 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_15.json in… |
| `validation/C33_F5_B1_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_01 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_01.json in… |
| `validation/C33_F7_B1.json` | PASS | 4 (0 failing) | Campaign 33 split run F7_B1: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F7_B1_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_11 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_11.json in… |
| `validation/C33_F8_B0a.json` | PASS | 3 (0 failing) | Campaign 33 split run F8_B0a: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F8_B0a_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_06 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_06.json in… |
| `validation/C33_F8_B0b.json` | PASS | 3 (0 failing) | Campaign 33 split run F8_B0b: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F8_B0b_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_08 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_08.json in… |
| `validation/C33_F8_B1a.json` | PASS | 3 (0 failing) | Campaign 33 split run F8_B1a: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F8_B1a_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_07 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_07.json in… |
| `validation/C33_F8_B1b.json` | PASS | 3 (0 failing) | Campaign 33 split run F8_B1b: the 2 parts merged (prompts/33a step D4) |
| `validation/C33_F8_B1b_part2of2.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_09 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_09.json in… |
| `validation/C33_campaign.json` | FAIL | 5 (2 failing) | 2x3 four-class campaign: matrix, S3-quota merges and the comparison with every earlier 2x3 result |
| `validation/C33_fcells_part1of4.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_13 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_13.json in… |
| `validation/C3_AER.json` | PASS | 10 (0 failing) | Campaign 33 token C3_AER (class 3): NAT-O0 noiseless on Aer: per-state agreement; f=1 SKQD reference of the native family |
| `validation/C4_CF.json` | FAIL | 8 (1 failing) | Campaign 33 token C4_CF (class 4): CF_traj redo on the GPU: K=2000 faulty Pauli trajectories per arm |
| `validation/C4_F1_B0.json` | PASS | 8 (0 failing) | Campaign 33 token C4_F1_B0 (class 4): E1 x O0 plan-of-record run, B=0 |
| `validation/C4_F1_B1.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F1_B1 (class 4): E1 x O0 plan-of-record run, B=1 |
| `validation/C4_F2_B0.json` | PASS | 8 (0 failing) | Campaign 33 token C4_F2_B0 (class 4): E2 x O0, B=0 |
| `validation/C4_F2_B1.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F2_B1 (class 4): E2 x O0, B=1 |
| `validation/C4_F4_B0a.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F4_B0a (class 4): E7(0.10) x O0, S3-quota half a, B=0 (1e5) |
| `validation/C4_F4_B0b.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F4_B0b (class 4): E7(0.10) x O0, S3-quota half b, B=0 (1e5) |
| `validation/C4_F4_B1a.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F4_B1a (class 4): E7(0.10) x O0, S3-quota half a, B=1 (1e5) |
| `validation/C4_F4_B1b.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F4_B1b (class 4): E7(0.10) x O0, S3-quota half b, B=1 (1e5) |
| `validation/C4_F5_B0.json` | PASS | 8 (0 failing) | Campaign 33 token C4_F5_B0 (class 4): E7(0.07) x O0 at the f=0.10 plan, B=0 |
| `validation/C4_F5_B1.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F5_B1 (class 4): E7(0.07) x O0 at the f=0.10 plan, B=1 |
| `validation/C4_F7_B0.json` | PASS | 8 (0 failing) | Campaign 33 token C4_F7_B0 (class 4): E1 x the chosen exact variant, B=0 |
| `validation/C4_F7_B1.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F7_B1 (class 4): E1 x the chosen exact variant, B=1 |
| `validation/C4_F8_B0a.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F8_B0a (class 4): E8, S3-quota half a, B=0: the S3 recall criterion |
| `validation/C4_F8_B0b.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F8_B0b (class 4): E8, S3-quota half b, B=0 |
| `validation/C4_F8_B1a.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F8_B1a (class 4): E8, S3-quota half a, B=1 |
| `validation/C4_F8_B1b.json` | PASS | 7 (0 failing) | Campaign 33 token C4_F8_B1b (class 4): E8, S3-quota half b, B=1 |
| `validation/C4_FCELLS_A.json` | FAIL | 8 (1 failing) | Campaign 33 token C4_FCELLS_A (class 4): 10-min ladder then f-cells E1,E2,E3,E4,E5a/b/c x O0-O4 (+O6 info) |
| `validation/C4_FCELLS_B.json` | PASS | 8 (0 failing) | Campaign 33 token C4_FCELLS_B (class 4): f-cells E6a/b/c, E7(0.05/0.07/0.10/0.15) x O0-O4; faithful S3 redo (IR-L3-RZZ, E8, 32 x … |
| `validation/C4_PART_01.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_01 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_01.json in… |
| `validation/C4_PART_02.json` | FAIL | 8 (1 failing) | Campaign 33 token C4_PART_02 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_02.json in… |
| `validation/C4_PART_03.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_03 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_03.json in… |
| `validation/C4_PART_04.json` | FAIL | 8 (1 failing) | Campaign 33 token C4_PART_04 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_04.json in… |
| `validation/C4_PART_05.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_05 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_05.json in… |
| `validation/C4_PART_06.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_06 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_06.json in… |
| `validation/C4_PART_07.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_07 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_07.json in… |
| `validation/C4_PART_08.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_08 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_08.json in… |
| `validation/C4_PART_09.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_09 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_09.json in… |
| `validation/C4_PART_10.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_10 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_10.json in… |
| `validation/C4_PART_11.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_11 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_11.json in… |
| `validation/C4_PART_12.json` | PASS | 8 (0 failing) | Campaign 33 token C4_PART_12 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_12.json in… |
| `validation/C4_PART_13.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_13 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_13.json in… |
| `validation/C4_PART_14.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_14 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_14.json in… |
| `validation/C4_PART_15.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_15 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_15.json in… |
| `validation/C4_PART_16.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_16 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_16.json in… |
| `validation/C4_PART_17.json` | PASS | 7 (0 failing) | Campaign 33 token C4_PART_17 (class 4): prompts/33a step D: generic class-4 part slot; its content is ci/parts/C4_PART_17.json in… |
| `validation/CF_estimator_2x2_info.json` | PASS | 2 (0 failing) | the recorded 2x2 clean-fraction values labelled by statistic, the corrected f_hat_ideal and the 2x2 signed-bar qualification (inf… |
| `validation/CF_traj.json` | PASS | 7 (0 failing) | Pauli-trajectory decomposition of the A6 reference-hit excess and the near-clean correction r_nc (prompts/28 Part A, re-assembled… |
| `validation/CS.json` | PASS | 4 (0 failing) | Structure of the Hamiltonian terms in codeword space (input to S2) |
| `validation/CV_2x2_info.json` | PASS | 2 (0 failing) | the CV curves on the recorded H0_2x2 ibm_kingston counts (information; not a device test (saturation)) |
| `validation/CV_2x3_plan.json` | PASS | 37 (0 failing) | energy convergence (shots, Krylov k) and weighted coverage of the 2x3 D3'-R plan in the S1 proxy emulation (owner decision 2a), o… |
| `validation/CV_2x4_plan.json` | PASS | 10 (0 failing) | the 2x4 noiseless shot plan (D3'-R at y = 1), its convergence in the exact emulation, the decoder acceptance, the IR-L0 bundles a… |
| `validation/E1.json` | PASS | 23 (0 failing) | Gauss's law, kernel dimension, sector split, two-builder agreement (2x2) |
| `validation/E2.json` | PASS | 51 (0 failing) | State counts (Table 2), vertex tables, codewords and decoder |
| `validation/E3.json` | PASS | 85 (0 failing) | Exact references (Table 1), static sectors, derived quantities, dt per sector |
| `validation/ENC_compare.json` | PASS | 8 (0 failing) | encoding comparison at fixed physics: current vertex-local codec vs the dedup codec E2 (one bit per link) and the E5' assignment … |
| `validation/H0P.json` | PASS | 16 (0 failing) | H0 preparation on the FakeFez calibration snapshot: frozen circuit set, predicted yield curve by repetition, readout confusion, R… |
| `validation/H0P_ibm_fez.json` | PASS | 18 (0 failing) | H0 preparation on the ibm_fez calibration of the session day: frozen circuit set, predicted yield curve by repetition, readout co… |
| `validation/H0P_rehearsal.json` | PASS | 18 (0 failing) | H0 preparation on the FakeFez calibration snapshot: frozen circuit set, predicted yield curve by repetition, readout confusion, R… |
| `validation/H0P_repro.json` | PASS | 15 (0 failing) | H0 preparation on the FakeFez calibration snapshot: frozen circuit set, predicted yield curve by repetition, readout confusion, R… |
| `validation/H0_2x2.json` | PASS | 8 (0 failing) | the full 2x2 SKQD run on ibm_kingston below the signed budget (owner decision 2026-10-02): both sectors, D3' at the measured f, d… |
| `validation/H0_2x2_dryrun.json` | PASS | 8 (0 failing) | the full 2x2 SKQD run on ibm_kingston below the signed budget (owner decision 2026-10-02): both sectors, D3' at the measured f, d… |
| `validation/H0_canary.json` | FAIL | 6 (3 failing) | 2x2 calibration session on ibm_fez: decoder validity, bit order, yield versus CZ count, readout confusion, Ritz consistency |
| `validation/H0_ddrep.json` | PASS | 8 (0 failing) | one-job replication of the XY4 gain (T0 vs T3) and of the context-aware collapse (T1) with four mechanism cells and four pulse-tr… |
| `validation/H0_ddrep_dryrun.json` | PASS | 8 (0 failing) | one-job replication of the XY4 gain (T0 vs T3) and of the context-aware collapse (T1) with four mechanism cells and four pulse-tr… |
| `validation/H0_ddtest.json` | PASS | 8 (0 failing) | one-job A/B test of client-side DD (context-aware, XY4, XY4-long) against the no-DD baseline on the pilot's two k = 1 circuits; a… |
| `validation/H0_ddtest_dryrun.json` | PASS | 8 (0 failing) | one-job A/B test of client-side DD (context-aware, XY4, XY4-long) against the no-DD baseline on the pilot's two k = 1 circuits; a… |
| `validation/H0_diag.json` | FAIL | 8 (2 failing) | H0 diagnostic session on ibm_fez: the DD x twirling factorial of the frozen canary circuit and the windowed idle tests that decid… |
| `validation/H0_diag_dryrun.json` | FAIL | 7 (1 failing) | H0 diagnostic session on ibm_fez: the DD x twirling factorial of the frozen canary circuit and the windowed idle tests that decid… |
| `validation/H0_dryrun.json` | PASS | 9 (0 failing) | 2x2 calibration session on AerSimulator.from_backend(FakeFez) [local testing mode]: decoder validity, bit order, yield versus CZ … |
| `validation/H0_kpilot.json` | FAIL | 9 (1 failing) | ibm_kingston pilot on the selected patch: windowed Ramsey at two lengths (T2*/T2_echo ratio r_eff vs r_crit), T1, the signed k = … |
| `validation/H0_kpilot_dryrun.json` | PASS | 9 (0 failing) | ibm_kingston pilot on the selected patch: windowed Ramsey at two lengths (T2*/T2_echo ratio r_eff vs r_crit), T1, the signed k = … |
| `validation/H0_model.json` | PASS | 5 (0 failing) | post-diction of the H0 hardware counts by the scheduled-Aer model at both ends of the T2 bracket; the clean-yield statistic |
| `validation/K0_2x3_2x4.json` | PASS | 6 (0 failing) | ibm_kingston readiness of 2x3 and 2x4 on a calibration record: routed CZ, gate-only, idle-aware and XY4-transfer f (prompts/25 Pa… |
| `validation/K1_2x3_fpilot.json` | PASS | 8 (0 failing) | the 2x3 clean-fraction pilot on ibm_kingston: two signed k = 1 circuits (largest p_ref per sector), routed as gate K0, ALAP + cli… |
| `validation/K1_2x3_fpilot_dryrun.json` | PASS | 9 (0 failing) | the 2x3 clean-fraction pilot on ibm_kingston: two signed k = 1 circuits (largest p_ref per sector), routed as gate K0, ALAP + cli… |
| `validation/L2.json` | PASS | 4 (0 failing) | Qiskit circuits reproduce the numpy reference at 2x2 |
| `validation/L3.json` | FAIL | 2 (2 failing) | Transpiled CZ counts of the exact 2x2 circuits (S2 measurement) |
| `validation/L4.json` | PASS | 4 (0 failing) | Aer noise-model sampling at 2x2 (S3 preparation) |
| `validation/L4_fez.json` | PASS | 4 (0 failing) | Aer noise-model sampling at 2x2 (S3 preparation), calibration snapshot FakeFez |
| `validation/L4_p2_1e-3.json` | FAIL | 4 (2 failing) | Aer noise-model sampling at 2x2 (S3 preparation) |
| `validation/L4_p2_3e-3.json` | FAIL | 4 (2 failing) | Aer noise-model sampling at 2x2 (S3 preparation) |
| `validation/L5.json` | PASS | 6 (0 failing) | CUDA-Q circuits versus the numpy reference at 2x2 |
| `validation/Q0P_2x2.json` | PASS | 5 (0 failing) | signed 2x2 circuits compiled to the Quantinuum native gate set, verified exactly and costed (prompts/35 T1) |
| `validation/Q0P_2x3.json` | PASS | 7 (0 failing) | signed 2x3 circuits compiled to the Quantinuum native gate set, verified exactly, costed and packaged (Stage A; Stage E/P not run) |
| `validation/Q0P_2x3_plan.json` | PASS | 7 (0 failing) | the 2x3 shot rule D3'-R (minimum sizing, owner decision 2a), the f_hat_ideal statistic and GO rule v3, Stage E / P v3, the emulat… |
| `validation/Q0P_2x4.json` | FAIL | 6 (2 failing) | signed 2x4 circuits compiled to the Quantinuum native gate set, proven equal to their IR by local equivalence and costed (prompts… |
| `validation/QEMU_2x2.json` | PASS | 3 (0 failing) | 2x2 native circuits on Quantinuum's local emulator (pytket-quantinuum H2-1LE, pytket-pecos, noiseless state vector; prompts/35 T4) |
| `validation/QEMU_2x3_laptop_smoke.json` | PASS | 2 (0 failing) | 2x3 C3_LE engine path on the laptop pecos venv (prompts/35 3.6; a smoke test, not the C3_LE token) |
| `validation/QEMU_2x4.json` | infeasible | 0 (0 failing) | 2x4 on the local emulator H2-1LE: infeasible (prompts/35 3.6) |
| `validation/QH_2x2.json` | PASS | 4 (0 failing) | 2x2 native circuits as Helios Guppy/HUGR programs on Selene (Quest, IdealErrorModel), offline (prompts/35 T6) |
| `validation/QH_2x3.json` | PASS | 4 (0 failing) | 2x3 native circuits as Helios Guppy/HUGR programs on Selene (Quest, IdealErrorModel), offline (prompts/35 T6; information) |
| `validation/QH_2x4.json` | not attempted | 0 (0 failing) | 2x4 Helios Guppy/HUGR + Selene: not attempted (prompts/35 3.7) |
| `validation/QN_2x2.json` | PASS | 5 (0 failing) | 2x2 native circuits under noiseless sampling and the Quantinuum noise models (prompts/35 T2 + T3) |
| `validation/QN_2x4.json` | PASS | 2 (0 failing) | 2x4 native circuits under the Quantinuum noise models: analytic fault-free fraction and gate-only f (prompts/35 T3, R3; nothing s… |
| `validation/QSC_prepared.json` | prepared | 0 (0 failing) | T5 syntax checks prepared (job records only; needs the owner's Nexus login) |
| `validation/QV_2x4_01.json` | PASS | 4 (0 failing) | QV_2x4_01: 2x4 native and source statevectors on the Aer GPU vs the exact coarse states (prompts/35b section 4) |
| `validation/QV_2x4_02.json` | PASS | 11 (0 failing) | QV_2x4_02: SK-B1 + CV3-B1: the 16 B=1 family circuits + the 4 B=1 k = 5 circuits, sampled (prompts/36 section 4) |
| `validation/QV_2x4_03.json` | PASS | 11 (0 failing) | QV_2x4_03: SK-B0a: B=0 refs 102, 1338, 11026, 16833, 2086, 281 (k = 1..4) + their 6 k = 5, sampled (prompts/36 section 4) |
| `validation/QV_2x4_04.json` | PASS | 11 (0 failing) | QV_2x4_04: SK-B0b: B=0 refs 3166, 345, 474, 682, 6930 (k = 1..4) + their 5 k = 5, sampled (prompts/36 section 4) |
| `validation/QV_2x4_05.json` | FAIL | 12 (1 failing) | QV_2x4_05: NAT: the 13 native structured k = 1 circuits slot 01 did not run (frozen source, R7) (prompts/36 section 4) |
| `validation/S1.json` | PASS | 12 (0 failing) | Emulated support recall, certification and size-matched classical controls (2x3, 2x4) |
| `validation/S2.json` | FAIL | 5 (2 failing) | Structured basic-gate circuits: hopping chains and interior-corner plaquettes |
| `validation/S2D.json` | FAIL | 8 (2 failing) | Device-resolved budgets for the exact circuits: 2x2 on Heron, 2x3 on an all-to-all RZZ device, shot rule and S3 job size |
| `validation/S2D_idle.json` | FAIL | 15 (9 failing) | Gate S2D's 2x2 criterion (mean f >= 0.1, worst f >= 0.05) re-evaluated on the idle-aware clean-shot fraction, at both ends of the… |
| `validation/S2D_levers.json` | PASS | 9 (0 failing) | 2x2 duration levers on ibm_kingston: compile/schedule levers measured, f predicted at both T2 ends, r_crit (measurement gate) |
| `validation/S2_2x4.json` | PASS | 12 (0 failing) | 2x4 coarse step compiled to exact circuits, verified and measured: counts, duration, idle budget and the T2/t_2q requirement (a m… |
| `validation/S2_2x4_gpu.json` | None | 0 (0 failing) |  |
| `validation/S2_fixed.json` | FAIL | 9 (4 failing) | Fixed-angle generator (same codeword pairs, one angle per flip pattern): cost floor, leakage and recall |
| `validation/S3.json` | PASS | 4 (0 failing) | GPU throughput calibration of the 2x3 B=0 circuit set (reduced size; the S3 recall criterion is NOT evaluated) |
| `validation/S3_smoke.json` | FAIL | 2 (1 failing) | Device-model sampling of the 2x3 B=1 circuit set (gate S3) |
| `validation/SKQD_2x4.json` | PASS | 9 (0 failing) | the 2x4 noiseless SKQD pipeline on the Aer GPU samples of slots QV_2x4_02..06 (prompts/36 section 2.2) |

CI-written files: 51 `validation/ci_gate_<TOKEN>.json` / `ci_smoke.json` (do not edit).  Sub-folders: `validation/archive/` (byte-identical archives of superseded CI JSONs), `validation/dryrun/` (laptop dry runs).  `validation/S2_2x4_gpu.json` has no status field (raw GPU stage output merged into `S2_2x4.json`).

### 14.4 Plans (`prompts/`)

| file | first heading |
|---|---|
| `prompts/00_bootstrap_and_push.md` | 00 — Bootstrap: check the package, create the public GitHub repository, push |
| `prompts/01_laptop_L1_reproduce_cloud_gates.md` | 01 — L1: reproduce the cloud-verified gates on the laptop |
| `prompts/02_laptop_L2_qiskit_check.md` | 02 — L2: Qiskit circuits reproduce the numpy reference (2x2, 12 qubits) |
| `prompts/03_laptop_L3_cz_counts_S2.md` | 03 — L3: transpiled CZ counts of the exact circuits (measurement for gate S2) |
| `prompts/04_laptop_L4_aer_noise_S3.md` | 04 — L4: Aer noise-model sampling at 2x2 (gate S3 preparation) |
| `prompts/05_laptop_L5_cudaq_check.md` | 05 — L5: CUDA-Q version of the 2x2 circuits on the GTX 1060 Max-Q |
| `prompts/06_S2b_plaquette_interior_and_hopping_decomposition.md` | 06 — S2-b: structured hopping gates and interior-corner plaquette gates within the CZ budget |
| `prompts/07_hardware_H0_2x2_calibration.md` | 07 — H0: first QPU session, 2x2 calibration run (12 qubits) |
| `prompts/08_month_plan_and_reporting.md` | 08 — One-month plan to H1/H2 (2x3 hardware spectroscopy) with the gate table |
| `prompts/09_L4_fix_20260914.md` | 09 — L4 fix (2026-09-14): honour the 30-minute rule when the circuits carry ~35 000 CZ |
| `prompts/10_L5_fix_20260914.md` | 10 — L5 fix (2026-09-14): CUDA-Q 0.15.1 `SampleResult` API in the convention tests |
| `prompts/11_S2_planner_decision_20260915.md` | 11 — S2 planner decision (2026-09-15): the exact coarse step cannot meet the CZ budget in this encoding; measure the floor, then the owner … |
| `prompts/12_combined_plan_device_budgets_S3_prep.md` | 12 — Combined plan: 2x2 on Heron, 2x3 exact circuits on an all-to-all device — device-resolved budgets, shot rule, S3 preparation |
| `prompts/13_H0_preparation_heron_and_S3_desktop_job.md` | 13 — H0 preparation on Heron (gate H0P) and the S3 desktop job |
| `prompts/14_H0P_fix_yield_model_20260916.md` | 14 — H0P fix (2026-09-16): the yield model must include the manual's garbage-acceptance term |
| `prompts/15_H0_session_ibm_fez.md` | 15 — H0: first QPU session on ibm_fez (2x2 calibration run, manual Step 9.1, gate H0) |
| `prompts/16_H0P_ibm_fez_fix_20260921.md` | 16 — H0P_ibm_fez fix (2026-09-21): the shot plan must guarantee the saturation that criterion 3 presupposes |
| `prompts/17_H0_submission_window_20260922.md` | 17 — H0 submission window (2026-09-22): the preflight must test the calibration CONTENT of the frozen patch, not its timestamp |
| `prompts/18_gpu_allowlist_proposal_20260922.md` | 18 — Proposed GPU allowlist lines for S3 and H0P (owner action on Perlmutter) |
| `prompts/19_H0_canary_diagnostic_20260922.md` | 19 — H0 canary NO-GO: diagnostic session on ibm_fez (idle-time model, DD/twirling factorial) |
| `prompts/20_H0_replan_clean_yield_20260922.md` | 20 — H0 re-plan: the clean-yield statistic, the scheduled-Aer prediction at both ends of the T2 bracket, the post-diction gate H0_model, an… |
| `prompts/21_kingston_T2star_pilot.md` | 21 — The ibm_kingston pilot: in-circuit T2*/T2_echo on the selected patch, and the direct f_clean of the best schedulable signed circuit (g… |
| `prompts/21a_H0_kpilot_dryrun_K3_ruling_20261002.md` | 21a — Ruling on the Part-D STOP of prompts/21: the dry-run K3 on the FakeKingston snapshot |
| `prompts/22_2x4_compilation_and_device_requirement.md` | 22 — 2x4: compile the coarse step to exact circuits, measure its duration and idle budget, derive the device requirement |
| `prompts/23_ibm_2x2_duration_reduction.md` | 23 — 2x2 on IBM: measure the duration levers and decide what the signed f >= 0.1 criterion needs |
| `prompts/24_ibm_2x2_mitigation_test_then_full_skqd.md` | 24 — IBM 2x2 inside the 571 s: Stage T (one preregistered dynamical-decoupling A/B test against the pilot baseline, gate H0_ddtest) and Sta… |
| `prompts/25_2x3_2x4_kingston_check_and_ionq_prep.md` | 25 — 2x3 and 2x4: the ibm_kingston readiness check (gate K0_2x3_2x4) and the IonQ preparation (gates I0P_2x3, I0P_2x4) |
| `prompts/26_2x3_circuits_for_quantinuum_h2_helios.md` | 26 — The signed 2x3 circuits for Quantinuum H2-2 / Helios-1 (gate Q0P_2x3): native compilation, exact verification, emulator and submission… |
| `prompts/27_2x3_substantial_result_strategy.md` | 27 — A substantial 2x3 result: the staged plan (simulator stages first, then the device question) |
| `prompts/28_2x3_shot_rule_and_clean_fraction_estimator.md` | 28 — The 2x3 shot rule (D3'-R) and the clean-fraction estimator: decisive trajectory test, tail-class statistic, Stage E / P GO rule, 2x2 i… |
| `prompts/29_cf_traj_reruling_ideal_sample_fraction.md` | 29 — Re-ruling after the CF_traj STOP (rho_T > 1.5): the ideal-sample fraction f_ideal, the corrected reference-hit statistic, completion o… |
| `prompts/30_convergence_and_coverage_criteria.md` | 30 — Energy-convergence and weighted-coverage criteria for the 2x3 plan check (owner decision 2a, 2026-10-05): definitions, preregistered c… |
| `prompts/31_CV_2x3_plan_fix_20261005.md` | 31 — CV_2x3_plan fix (2026-10-05): the certificate basis at 2x3 ($B_{\rm all}$, manual Step 5.1), the H1 width read on the Kato–Temple inte… |
| `prompts/32_2x2_dd_replication_and_T1_mechanism.md` | 32 — Owner decision 2026-10-06, option A then B: the 2x3 IBM NO-GO recorded on K0; one preregistered job on ibm_kingston that replicates th… |
| `prompts/33_2x3_four_class_perlmutter_campaign.md` | 33 — The 2x3 four-class simulation campaign on Perlmutter (ideal / IBM noise / Quantinuum-based ideal / Quantinuum-based with errors and op… |
| `prompts/33a_campaign33_first_wave_reruling.md` | 33a — Campaign 33, addendum after the first CI wave: threadpoolctl, the C2_CAL ladder, Kraus vs PTA, re-sizing |
| `prompts/33b_campaign33_scenario_aware_sizing_and_waves.md` | 33b — Campaign 33, addendum 2: scenario-aware class-4 sizing, slot re-use, what runs before the 2026-10-21 maintenance |
| `prompts/33c_class2_representation_and_cf_reruling.md` | 33c — Campaign 33, addendum 3 (after wave 1 of 33b): the class-2 representation, the RM arm as a bug, C4_CF accepted as recorded, the next … |
| `prompts/33d_gpu_kraus_check_and_class2_representation.md` | 33d — Campaign 33, addendum 4: the Aer GPU Kraus path is the suspect, not the RM channel; C2_KCHK decides the class-2 representation |
| `prompts/33e_kchk_cpu_arm_fix_and_class2_timing.md` | 33e — Campaign 33, addendum 5: C2_KCHK run 2 (the CPU arm on the node's CPUs), the laptop CPU reference now, class 2 after the maintenance |
| `prompts/33f_k2_exact_test_rm_production_and_upstream.md` | 33f — Campaign 33, addendum 6: K2 judged by the exact test, production = RM, C2_XY4 now, the OMP binding, the qiskit-aer report |
| `prompts/34_encoding_comparison.md` | 34 — Encoding comparison: does a different qubit encoding shorten the 2x3 circuits? (gate ENC_compare) |
| `prompts/35_quantinuum_all_circuits_test.md` | 35 — Every SKQD circuit of 2x2, 2x3 and 2x4 tested for Quantinuum devices, tier by tier (gates Q0P_2x2, QN_2x2, QEMU_2x2, QH_2x2, Q0P_2x4, … |
| `prompts/35a_quantinuum_tests_rulings.md` | 35a — Addendum to prompts/35: Q2 corrected, the pytket angle rounding, the 2x2 T3 cap, level-0-only at 2x4 |
| `prompts/35b_2x4_exactness_ruling.md` | 35b — Ruling on the 2x4 STOP: the state bar is measured, not bounded; a second (structured) source for 2x4; the k >= 2 builds wait for one … |
| `prompts/36_2x4_full_pipeline.md` | 36 — The 2x4 pipeline: noiseless SKQD end to end on the GPU, the 2x4 shot plan, the slot layout (gates CV_2x4_plan, SKQD_2x4; slots QV_2x4_… |
| `prompts/36a_CV_2x4_plan_fix_20261019.md` | 36a — CV_2x4_plan fix (2026-10-19): the B=1 plan is shot-limited, not family-limited; the re-sizing ladder beyond s = 8 and CV3 at the plan… |
| `prompts/BLOCKED_CV_2x4_plan.md` | BLOCKED — CV_2x4_plan (prompts/36 Part A), 2026-10-19, executor-opus |
| `prompts/ESCALATION_TEMPLATE.md` | NN — <GATE> fix (<date>) |
| `prompts/README.md` | prompts/ — the prompt chain |
| `prompts/ROUTING.md` | Model and effort routing |
| `prompts/low_clean_fraction_techniques.md` | Getting good estimates when the clean fraction is below 0.1 |

*End of report.*


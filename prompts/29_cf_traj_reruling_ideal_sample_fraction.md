# 29 — Re-ruling after the CF_traj STOP (rho_T > 1.5): the ideal-sample fraction f_ideal, the corrected reference-hit statistic, completion of CF_traj, and the amended Part B of prompts/28
executor: executor-opus   effort: high
time budget: Part A' about 2 h of laptop wall time in background chunks <= 27 min each; Part B' as prompts/28 Part B (about one executor day) with the amendments below   machine: laptop (0 QPU s, 0 HQC, 0 eHQC; no push)

Planner: Fable 5.1 (high), 2026-10-05.  Inputs read: `validation/CF_traj.json`, `reports/CF_traj.md`,
`data/cf_trajectories/*/chunk*.json` (commits d3142ef..9071df6).  Every number below is from those files or
is planner arithmetic on their trajectory records (labelled).  This prompt supersedes prompts/28 Part B1 (the
tail-class statistic), the GO rule v2 of B3 and the sizing input of B3; everything else in prompts/28 stands.

## 1 What CF_traj established (physics, not a bug)

- C2 PASS: the trajectory prediction of the A6 reference hits is 62.58 +- 2.64 against 64 observed
  (two-sided Poisson P = 0.891); the bit-flip-only control on the real Aer path gave 40 hits against 45.95
  predicted (band [33, 60]); C5: no `rzz` merging, no transpile step.  **The reference-hit excess is the
  near-clean term; the Aer path is sound.**
- C3 PASS: the Z-only stratum predicts 11.04 for the phase-only check's 11 of 40.
- STOP fired on $\rho_T$ (3.18 [2.19, 4.33] in B0, 3.86 [2.71, 5.19] in B1, and 2.77 even under bit flips
  only).  The run was truncated: B0_ref25_k1 240 of 720 trajectories, the k = 4 arm and the 2x2 arm not run.

## 2 Planner analysis of the trajectory records (planner arithmetic on `data/cf_trajectories/*/chunk*.json`)

**2.1 Which errors return to the reference.**  Of the 240 B0_ref25_k1 trajectories 17 return
($p_\tau(\mathrm{ref}) > 0.5$) and carry 95 % of $h_{\rm ref}$; 11 of the 17 are single-event trajectories with
Paulis `ZY` (5), `IY` (4), `Z` (1), `ZI` (1); in B1 18 of 24 returns are single-event: `IY` (8), `ZI` (6), `ZY`
(3), `Z` (1).  No single native-frame `X` event ever returns (the xx arm: 0 of 45 single-event trajectories).
Reading: the returning errors are those that act as a **phase in the computational frame at their position** —
a native $Z$ where the qubit is in its computational frame, a native $Y$ inside a PhasedX-rotated block where
$Y$ maps to a computational $Z$.  The executor is right that most returns are "non-Z" in the native-frame
bookkeeping; the planner's "Z-type" diagnosis is right about the mechanism (phase-like errors on a
near-basis state) and wrong as a native-Pauli label.  The correct classifier is the local frame, not the
Pauli letter.

**2.2 Returns are benign.**  Of the returning trajectories 11 of 17 (B0) and 18 of 24 (B1) have total-variation
distance **exactly 0** from the ideal distribution (the error commutes to a phase), and all but one of the
rest are below 0.04.  So the near-clean shots that hit the reference are, almost all of them, *ideal samples*:
their output distribution is the ideal one.  Define the **ideal-sample fraction**
$f_{\rm ideal}(\delta) = f_0' + (1 - f_0')\,b(\delta)$, with $b(\delta)$ the fraction of faulty trajectories within
TV distance $\delta$ of the ideal (pre-readout).  From the records (K = 240 each):

| arm | $f_0'$ | $f_{\rm hit}$ | $f_{\rm ideal}(10^{-3})$ | $f_{\rm hit}/f_{\rm ideal}(10^{-3})$ | $f_{\rm ideal}(0.03)$ | $f_{\rm hit}/f_{\rm ideal}(0.03)$ |
|---|---|---|---|---|---|---|
| B0_ref25_k1 | 0.1721 | 0.2319 | 0.2100 | 1.104 | 0.2238 | 1.036 |
| B1_ref57_k1 | 0.1724 | 0.2575 | 0.2448 | 1.052 | 0.2655 | 0.970 |
| B0 bit-flip only | 0.1721 | 0.1793 | 0.1721 | 1.042 | 0.1790 | 1.002 |

**$f_{\rm hit}$ is an estimator of $f_{\rm ideal}$ with a model bias of 5-10 % at $\delta = 10^{-3}$ and
within 4 % at $\delta = 0.03$.**  It is *not* an estimator of $f_0'$ (bias 35-49 %), and $f_0'$ itself is a
bookkeeping convention (the gate-only 0.150 and Aer's 0.172 differ only by whether the identity Pauli of the
depolarizing channel is counted as an error — the same ambiguity as a harmless $Z$).

**2.3 Why $f_T$ is inflated, and why it is withdrawn.**  The tail class $T_c$ of the k = 1 circuits has 9 / 7
states, all at Hamming distance 3 (one hop, $p_c \approx 0.011$-0.016) or 8 ($p_c \approx 0.0014$-0.0020) from the
reference; none is a one-bit-flip neighbour (the coordinator's hypothesis in that form is not what the records
show — single flips do not decode to states of positive $p_c$).  The per-state inflation
$(1 - f_0')\langle p_\tau(s)\rangle / (f_0' p_c(s))$ is 0.3-2.3 for the distance-3 states and **21-39 for the
distance-8 states**: noise *scatters* weight into every codeword at a rate of order $10^{-3}$-$10^{-2}$, which
is negligible against $p_{\rm ref} = 0.91$ and large against $p_c = 10^{-3}$.  Any statistic built on
low-probability states is swamped by scattering, under every channel (the bit-flip arm has $\rho_T = 2.8$).
$f_T$ is withdrawn.  The scattering is *good news for the shot rule*: every S99 state is sampled at
$\ge 1.33\,f_0'$ (B0) / $1.48\,f_0'$ (B1), above $f_{\rm ideal}/f_0' = 1.22$ / 1.42.

**2.4 The floor theorem.**  For any noise, $f_{\rm eff}(s) \ge f_{\rm ideal}(\delta)\,(1 - 2\delta/p_c(s))$ for every
state: ideal-sample shots deliver $p_c(s)$ (up to $2\delta$) and every other shot contributes $\ge 0$.  So
**$f_{\rm ideal}$ is a safe sizing input for every state of S99** (at $\delta = 10^{-3}$ and $p_c \ge 10^{-2}$ the
loss is $< 20$ %, inside the 0.7 margin).  The records confirm it: $\min_{S99} f_{\rm eff}/f_{\rm ideal}
= 1.33/1.22 = 1.09$ (B0), $1.48/1.42 = 1.04$ (B1).

## 3 Re-ruling

**(1) The statistic.**  The clean-fraction bar ($f \ge 0.1$ mean, $\ge 0.05$ worst; numbers unchanged) refers to
the **ideal-sample fraction $f_{\rm ideal}$ at $\delta = 10^{-3}$** — the fraction of shots whose output
distribution is the ideal one — which is the physical content of the manual's "clean shots"; the gate-only
prediction $f_{\rm gate}$ (0.150 on H2-2) is its floor ($f_{\rm gate} \le f_0' \le f_{\rm ideal}$; CF_traj:
$f_{\rm ideal}/f_{\rm gate}$ = 1.40 / 1.63 under the A6 channel).  The device-side estimator for the GO rules
and the sizing is the **corrected reference-hit fraction**
$$\hat f_{\rm ideal} = f_{\rm hit} / r_{\rm nc},$$
with $f_{\rm hit}$ the pooled reference-string statistic of the k = 1 circuits exactly as recorded in every
hardware gate (`pooled_reference_string_test`, readout factor 1.0 on Quantinuum), and $r_{\rm nc}$ the **upper
95 % bootstrap bound** of the pooled $f_{\rm hit}/f_{\rm ideal}(10^{-3})$ over the completed k = 1 arms of
CF_traj (point values 1.104 / 1.052 at K = 240; the completed run fixes it).  Dividing by $r_{\rm nc} > 1$ makes
the bar harder, never looser.  The interval of $\hat f_{\rm ideal}$ combines the Garwood interval of the hit
count with the bootstrap interval of $r_{\rm nc}$ on the log scale (as the H0_ddtest ratio rule).  Caveat to be
written into every use: $r_{\rm nc}$ is a gate-noise (A6 channel) value; on H2-2 the memory term is 5-30 % of
the gate term (survey), so the composition stays gate-dominated; on IBM devices (idle dephasing) it is unknown
and A5 gives the only model estimate.  The reference count also stays the C3' bit-order test.  The k = 4
circuits give the cross-check: the mixture estimator (`clean_fraction_mixture`, readout factor 1.0) at k = 4,
whose bias against $f_{\rm ideal}$ the k = 4 arm measures (section 4, C7).

**(2) Complete CF_traj.**  Yes: the remaining B0_ref25_k1 chunks (480 trajectories, seeds 102-103; about 55 min
at the measured 6.8 s per statevector throughput, two background chunks), the k = 4 arm (240, seed 301, about
27 min) and the optional A5 2x2 arm **at both ends of the T2 bracket** (echo and T2*; the executor's bracket
option) are to be run.  $r_{\rm nc}$ needs the full K (the benign fraction $b$ rests on 11-21 trajectories at
K = 240, interval [0.021, 0.075] in B0); the k = 4 arm gives the mixture cross-check bias and the per-state
S99 rates on the production circuit family; A5 gives the 2x2 model number.  The gate is then re-assembled
under the amended criteria of section 4 (the $\rho_T$ STOP is retired because $f_T$ is withdrawn).

**(3) Consequences.**
- D3'-R unchanged in form; its input is $f = \hat f_{\rm ideal}$ of Stage P, $y = 0.82 \times 0.7 \times
  \hat f_{\rm ideal}$.  Safe by the floor theorem (2.4) when the device's near-clean ratio is $\le r_{\rm nc}/0.7$;
  the preregistered mid-campaign check on S99 (prompts/28 B3) stays as the guard beyond that.
- GO rule **v3** for Stage E and Stage P: statistic $\hat f_{\rm ideal}$ pooled over the stage's k = 1 circuits;
  **GO iff $\hat f_{\rm ideal,lo95} \ge 0.05$ and $\hat f_{\rm ideal} \ge 0.10$; NO-GO iff
  $\hat f_{\rm ideal,hi95} < 0.10$; AMBIGUOUS otherwise** (one top-up by Poisson scaling); C3' per k = 1 circuit;
  the k = 4 mixture estimate with its CF_traj-measured bias reported beside it (information, and a STOP for the
  planner if it disagrees with $\hat f_{\rm ideal}$ by more than a factor 1.5 either way).  Stage E **v3** =
  `B0_ref25_k1` 800, `B1_ref57_k1` 800, `B0_ref25_k4` 200, `B1_ref57_k4` 200 on H2-2E (planner arithmetic: 2,000
  shots, about 9,950 eHQC; expected reference hits at $f_{\rm hit} = 0.23$: $1600 \times 0.23 \times 0.914 \approx 336$,
  Garwood 95 % about $\pm 11$ %); Stage P **v3** the same four circuits and shots on H2-2 (about 9,950 HQC).  The
  v2 rebalancing towards k = 4 (for $f_T$) is dropped.
- 2x2 information block (prompts/28 B4, amended): every recorded 2x2 $f$ is $f_{\rm hit}$, an estimator of
  $f_{\rm ideal}$ with a gate-noise bias of 1.05-1.10 (CF_traj) and an unknown bias under idle dephasing (A5's two
  ends are the model bracket).  Planner arithmetic to be reproduced: with $r_{\rm nc} = 1.10$ the H0_2x2 adopted
  cell gives $\hat f_{\rm ideal} = 0.1129/1.10 = 0.103$ with lower 95 % bound $0.1058/1.10 = 0.096 < 0.1$ — under
  the v3 rule the 2x2 "signed bar GO" would read **AMBIGUOUS**, not GO.  No verdict of any 2x2 gate changes
  (same statistic on both sides, or $f$-independent); the qualification is stated, the records are not edited.

## 4 Part A' — complete and re-assemble CF_traj (laptop; no HQC)

A'1. Run `scripts/cf_trajectories.py` for B0_ref25_k1 chunks 1-2 (seeds 102, 103; 240 each), B0_ref25_k4
     (seed 301; 240), as background chunks $\le 27$ min; A5 at both T2 ends (K = 2000 each, 12 qubits).
A'2. Amend `scripts/gate_CF_traj.py`: per arm add $b(\delta)$ for $\delta \in \{10^{-3}, 10^{-2}, 0.03\}$,
     $f_{\rm ideal}(\delta)$, $r(\delta) = f_{\rm hit}/f_{\rm ideal}(\delta)$ with 95 % bootstrap intervals (B = 2000,
     seed 2028), the pooled (B0 + B1) $r(10^{-3})$ and its upper 95 % bound **= $r_{\rm nc}$** (written to
     `data/cf_trajectories/r_nc.json` with the commit and the K per arm), $\min_{S99} f_{\rm eff}/f_{\rm ideal}$,
     the return classification of 2.1 (single-event returns by Pauli; the fraction of returns with TV = 0), and
     for the k = 4 arm the mixture-estimator expectation: `clean_fraction_mixture` (readout factor 1.0)
     applied to the population mixture $N [f_0' p_c + (1 - f_0')\langle p_\tau\rangle]$ at $N = 200$ and $N = 2000$,
     reported as $w$-implied $f$ against $f_{\rm ideal}$ (its bias ratio).  Keep $\rho_T$ as information.
A'3. Criteria (replace C1/C4 of prompts/28; C2, C3, C5, C6 unchanged): C1 the planned K reached on all four
     arms and A5 recorded (both ends or "not run" with the reason); C4' $r(\delta)$, $f_{\rm ideal}(\delta)$,
     $\min_{S99} f_{\rm eff}/f_{\rm ideal} \ge 0.95$ on every arm (the floor theorem check), $r_{\rm nc}$ written;
     C7 the k = 4 mixture bias ratio reported with its interval.  STOP flags: C2 low side; A4-like count;
     **new:** $r_{\rm nc} > 1.3$ (then the correction is too large for the 0.7 margin to also cover the device's
     unknown composition — the planner returns); the k = 4 mixture bias outside [0.67, 1.5].

## 5 Part B' — prompts/28 Part B with these amendments

- B1 replaced: no tail-class functions.  Add `skqd.skqd.corrected_clean_fraction(pooled, r_nc, r_nc_95)`
  returning $\hat f_{\rm ideal}$ with the combined interval (log-scale sum of the Garwood and bootstrap
  variances), citing `data/cf_trajectories/r_nc.json`; tests on synthetic inputs.  Keep the `analyse_dryrun`
  shadowed-variable fix.
- B2 unchanged (`d3r_plan`).
- B3: GO rule v3, Stage E/P v3 (800/800/200/200), sizing input $\hat f_{\rm ideal}$; the preregistration block
  v2 is rendered with these (one version: "v2", since v1 was never used for a shot); the emulated check and
  the mid-campaign rule unchanged.
- B4: the 2x2 block as amended in 3(3), with the A5 bracket numbers.
- Everything else (outputs, STOPs, do-not-touch, LOG rows) as prompts/28.

## 6 What the owner must do

1. Confirm that the signed bar refers to $f_{\rm ideal}$ (shots that sample the ideal distribution) and that the
   measured statistic is $\hat f_{\rm ideal} = f_{\rm hit}/r_{\rm nc}$ — or insist on the gate-only convention, in
   which case no count-based device statistic exists and the planner must say so in the preregistration.
2. Confirm D3'-R (prompts/28) with the $\hat f_{\rm ideal}$ input, and the v3 plans.
3. Note the 2x2 qualification (the H0_2x2 "signed bar GO" is AMBIGUOUS under v3 at $r_{\rm nc} = 1.10$).

## LOG rows

| date | prompts/29 Part A' / Part B' | CF_traj (re-assembled) / Q0P_2x3_plan | executor-opus | the numbers: K per arm, $r(10^{-3})$ per arm and pooled, $r_{\rm nc}$, $f_{\rm ideal}$, $\min_{S99} f_{\rm eff}/f_{\rm ideal}$, the k = 4 mixture bias, A5 both ends; then the D3'-R table, the v3 plans, the 2x2 block | commit | open items |

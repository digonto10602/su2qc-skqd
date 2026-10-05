# 30 — Energy-convergence and weighted-coverage criteria for the 2x3 plan check (owner decision 2a, 2026-10-05): definitions, preregistered constants, the re-sizing rule, the 2x2 information block, and where convergence enters Stage E / Stage P / the campaign
executor: executor-opus   effort: high
time budget: about 1 executor day on top of prompts/29 Part B' (run B' and this prompt together); laptop sampling about 10 min, Ritz/baseline evaluation about 30-40 min in background chunks of <= 27 min (one chunk per f); no foreground command above 30 min   machine: laptop (0 QPU s, 0 HQC, 0 eHQC; no push)

Planner: Fable 5.1 (high), 2026-10-05.  Inputs read: `data/owner_decision_20261005_partB.md`, prompts/27, 28, 29,
`validation/S1.json` (`data.production`, `data.table3`, `data.table4`, `data.recall_vs_shots`,
`data.multi_reference_5e4`), `validation/H0_2x2.json` (`data.support`, `data.energies`, `data.baselines`),
`data/S2D_recall_at_f.json`, `data/cf_trajectories/r_nc.json`, `scratch/planner/d3s_2x3_shot_rule_20261003.json`,
the manual Steps 4.4, 5.2-5.4, 6, 10.  Every number below is from those files or is planner arithmetic on them
(labelled).  **This prompt amends prompts/29 Part B' (section 5 there) and prompts/27 T0 / Stage E / Stage P /
Stage 3; everything in those prompts not amended here stays in force.**  The parallel K1 executor's files are
off limits (section 8).

## 1 Goal

Owner decision 2a (verbatim: "1a, 2a with the convergence condition, 3a"): rule D3'-R is signed as the **minimum**
2x3 shot sizing, and **no full 2x3 campaign is approved unless the emulated check of the plan shows energy
convergence ($E_R$ and the certificate width against shots and against Krylov $k$) and weighted coverage** under
criteria the planner adds.  The owner's question was "useful-string coverage and energy convergence should also
be checked, is it being checked?" — the answer found: coverage is checked as recall (H0_2x2, D3'-R P2/P3, the
prompts/27 tiers), the energy only at the final point ($E_R$ vs $E_0$, Weinstein / Kato-Temple); **convergence
against shots, against $k$, and weighted coverage are checked nowhere as a criterion**.  This prompt defines
them (section 2), fixes their constants from the manual's targets and the D3'-R recall target (section 3), makes
them a gate (`CV_2x3_plan`) that Q0P_2x3_plan's preregistration v2 includes as criterion P7, fixes the re-sizing
rule when the minimum plan fails them (section 4), computes the same curves from the H0_2x2 hardware counts as an
information block labelled "not a device test (saturation)" (section 5), and states where convergence enters
Stage E / P and the campaign (section 6).

## 2 Definitions (all sectors: 2x3, $g^2 = 4$, $m = 3g^2/16$; $B = 0$ and $B = 1$; the 2x2 block uses the same definitions on `Model(2)`)

**2.1 Exact objects.**  $H$ = `Model(3).H(g2)`; the sector reference `r = Model(3).reference(g2, twoB, k=4)`
with $E_0$ = `r.E0`, $E_1$ = `r.energies[1]`, $\Delta t$ = `r.dt`, and the exact ground state
$|\Omega\rangle$ with weights $|c_s|^2$ on the sector's basis indices (`r.indices`, `r.ground`; the vector
`prob_full` exactly as `scripts/s2d_recall_at_predicted_f.py` builds it).  $E_0$ must equal
`data/references.json` to $10^{-12}$ (the H0_2x2 `E0_matches_references_json` check): $-5.6026$ ($B=0$),
$-3.8261$ ($B=1$), Table 1.  $E_{\max} - E_0 = \pi/\Delta t$ (the anti-aliasing rule, manual 1.4; planner
arithmetic: $\pi/0.156 = 20.1$ at $B=0$, $\pi/0.187 = 16.8$ at $B=1$ — the executor computes it from `r.dt`).
For $B=1$ the ground state is the lowest member of the near-degenerate cluster (splitting 0.024, manual 1.5):
$|c_s|^2$ is taken from that one eigenvector (non-degenerate, `numpy.linalg.eigh` of the dense sector block),
and the cluster-projected weight $W_{\rm cl}(B) = \frac{1}{3}\sum_{j=0}^{2}\sum_{s\in B}|c^{(j)}_s|^2$ over the
three cluster states ($E_0$, $-3.8017$, $-3.6687$) is reported as information.
Supports: $S_{999}$ = `exact_support(prob_full, 1e-3)` (86 / 95 states), $S_{99}$ = `exact_support(prob_full,
1e-2)` (31 / 42), references $R$ = `krylov.references(basis, twoB)` (8 / 3).

**2.2 Weighted coverage.**  $W(B) = \sum_{s\in B}|c_s|^2$ = `support_metrics(B, prob_full, 1e-3)["captured_weight"]`
(already implemented; no new function).  Its rigorous link to the energy is manual eq. (6):
$0 \le E_R - E_0 \le \frac{(1 - W)(E_{\max} - E_0)}{W}$, reported beside every $W$ as information (it is a worst-case
bound; the emulations sit far below it).

**2.3 The sampled bases and the nested subsamples.**  For one (sector, $f$, seed): the D3'-R plan gives
$N_c$ shots to circuit $c$ (prompts/28 B2, `d3r_plan`; the signed family, $k = 1..4$ coarse circuits from every
reference; 32 circuits at $B=0$, 12 at $B=1$).  The emulation is the S1 proxy exactly as prompts/28 B3 states it
(`skqd.noise` with $P_{\rm RO} = 0.01$, clean fraction $0.7\,f$ **for the criteria** — the sizing margin — with
garbage at gate E2's acceptance; seeds $\{20260914, 1, 2\}$, the `s2d_recall_at_predicted_f.py` seeds).
**Nested subsamples are prefixes of each circuit's shot sequence**: add
`skqd.noise.measure_and_decode_sequence(codec, codewords, psi, shots, f, p_ro, rng, target_twoB)` returning,
per shot in sampling order, the decoded basis index or the rejection reason; it must make exactly the two random
calls of `measure_and_decode` (`rng.choice`, then `corrupt_shots`) and decode the unique strings once, so that
its histogram over all shots is identical to `measure_and_decode`'s at the same seed (a test).  Sample
$8 N_c$ shots per circuit once per (sector, $f$, seed); the subsample at fraction $\phi$ is the first
$\mathrm{round}(\phi N_c)$ shots of every circuit, $\phi \in \{1/16, 1/8, 1/4, 1/2, 1\}$ (the criteria) and
$\{2, 4, 8\}$ (the re-sizing grid of section 4).  By construction $B(\phi N) \subseteq B(\phi' N)$ for
$\phi < \phi'$.
Two bases per point: $B_{\rm all}(\phi N) = R \cup \{\text{accepted strings}\}$ and
$B_{\rm sig}(\phi N) = R \cup \{s : n_s \text{ one-sided } 3\sigma \text{ Poisson above } \mu_s = \phi N a/\dim\}$
with `sig_support` of `scripts/gate_H0_2x2.py` and $a$ the sector's exhaustive garbage acceptance (prompts/24 P9,
unchanged).  **The criteria are evaluated on $B_{\rm sig}$ (the preregistered device support); $B_{\rm all}$ is
reported beside it.**  (Planner note: at 2x3, $\mu_s \approx 35{,}000 \times 0.0015/677 \approx 0.08 \ll 1$, so
$B_{\rm sig}$ keeps states seen twice or more; the D3'-R guarantee of $\lambda^*$ hits on $S_{99}$ puts every
$S_{99}$ state in $B_{\rm sig}$ with probability $\ge 0.95$, the $S_{999}$ tail seen once is not.  If a criterion
passes on $B_{\rm all}$ and fails on $B_{\rm sig}$, that is reported as such and the re-sizing applies; the
P9 definition is not changed.)

**2.4 The energy curve against shots.**  $E_R(\phi N) = $ `ritz(H, B_sig(phi N)).ER`, $r_H(\phi N)$ = `.rH`,
the certificate `certify(res, E0, E1)` (Weinstein $[E_R - r_H, E_R]$, Kato-Temple with $\alpha$ = second Ritz
value, `gap_assumption_holds`), $W(\phi N)$, $|B_{\rm sig}|$, $|B_{\rm all}|$, recall of $S_{999}$ and $S_{99}$
on both bases, false positives — at every $\phi$.  Monotonicity is exact (nested bases): $E_R(\phi N)$ is
non-increasing in $\phi$ and $\ge E_0$; both are structural checks (CV0).

**2.5 The Krylov curve.**  Cumulative over coarse steps: $B^{(k)} = R \cup \{\text{accepted from circuits with
} k' \le k\}$, $k = 1..4$, with the same quantities as 2.4.  Two versions: (a) **at the plan's allocation**
(the operational curve: what the campaign shows if it stops after $k$; D3'-R puts most shots on $k = 4$, so this
curve is dominated by the allocation — information only); (b) **at equal shots per circuit**, $N_c = N_{\rm
sector}/n_{\rm circuits}$ rounded up to 100 (planner arithmetic at $f = 0.10$: $34{,}909/32 \to 1{,}100$ at $B=0$,
$49{,}203/12 \to 4{,}200$ at $B=1$), sampled separately with the same seeds — **the criterion curve**, because
it isolates the dependence on $k$ from the shot allocation.  The equal-shots sampling is also run at $2N_c$ for
information (is the $k$ plateau shot-limited or $k$-limited).

**2.6 Random equal-size baselines.**  At every subsample point and every $k$ of 2.4-2.5: 200 bases
`controls.random_support(sector_idx, R, |B_sig|, rng)` with seeds $23..222$ (`RANDOM_SEEDS` of
`gate_H0_2x2.py`; references always included, prompts/27 T0.d), each with $E_R$, $r_H$, $W$; report mean, 2.5th
and 97.5th percentiles, and the percentile of the device value (`percentile_of`).  Saturation is the regime in
which these baselines reach the device values (the 2x2 case, section 5).

**2.7 The H1-derived energy tolerance $E_{\rm tol}$ (the one constant of the plateau tests; computed, not
chosen).**  Gate H1 (manual Step 10) accepts a $B=0$ support with recall $\ge 0.8$ of $S_{999}$.  The best such
support is the top $\lceil 0.8\,|S_{999}|\rceil$ states of $S_{999}$ by weight (69 at $B=0$, 76 at $B=1$) plus
the references; its Ritz error is the energy resolution the H1 recall target itself tolerates:
$$E_{\rm tol}(\text{sector}) = E_R\big(R \cup S_{999}^{\,\rm top\,80\%}\big) - E_0 .$$
Add `skqd.skqd.h1_energy_tolerance(H, prob_full, refs, recall_target=0.8, eps=1e-3)` returning it with the
state list.  Planner expectation from Table 3 (`data.table3`, oracle at $|B| = 80$: $1.010\times10^{-2}$ at $B=0$,
$1.024\times10^{-2}$ at $B=1$; at $|B| = 40$: $2.49\times10^{-2}$ / $5.70\times10^{-2}$): $E_{\rm tol}$ of order
$10^{-2}$ in both sectors; the computed value replaces this.  Cross-check (CV0): the same code path reproduces
`data.table3["B=0|oracle|40"].err` $= 2.4928334\times10^{-2}$ and `["B=0|oracle|80"].err` $= 1.0099926\times10^{-2}$
to $10^{-9}$ through `controls.oracle` (same function as gate S1).  For $B=1$ also report
$E_{\rm tol}^{\rm D3'R}$ with `recall_target=0.9` (the D3'-R target; information).

## 3 Preregistered criteria for the 2x3 plan check (gate `CV_2x3_plan`; the condition of decision 2a)

Evaluated per sector at each $f$ of the plan table ($\{0.05, 0.10, 0.15\}$, prompts/28 B3) and **in every one of
the three seeds** (3 of 3; three seeds cannot establish the 95 % of the D3'-R rule — say so in the report — so
the conservative reading is used).  $N$ is the D3'-R sector total at that $f$ (section 4 changes $N$ when
re-sizing).  The constants: $E_{\rm tol}$ (2.7, computed), $0.1$ (H1 width), $0.15$ (H2 cluster $r_H$),
$0.99$ (the weight of $S_{99}$, the set D3'-R guarantees at $\lambda^*$), $2.5\,\%$ (the Tier-A random
percentile already preregistered in prompts/27).  No other constant exists.

- **CV0 (structural; FAIL = bug, not a physics result):** nestedness and monotonicity of 2.4-2.5 to $10^{-12}$;
  $E_R \ge E_0 - 10^{-9}$ everywhere; the sequence sampler's histogram equals `measure_and_decode`'s; $E_0$ matches
  `data/references.json` to $10^{-12}$; the Table 3 oracle reproduction of 2.7; every random baseline contains $R$.
- **CV1 — plateau of $E_R$ against shots:** $E_R(N/2) - E_R(N) \le E_{\rm tol}$ on $B_{\rm sig}$.  Reading: the
  last doubling of the plan moves the energy by less than the error H1's own recall target tolerates.  Report
  the ratio $[E_R(N/2) - E_R(N)]/E_{\rm tol}$, the whole curve $\phi = 1/16..1$, and the fitted slope of
  $\log(E_R - E_0)$ against $\log\phi$ over the last three points (information; Table 4 and S1 production give
  about $-1$: $9.6\times10^{-3}$ at $10^4$, $4.0\times10^{-3}$ at $3\times10^4$, $3.2\times10^{-4}$ at $2\times10^5$
  shots, planner reading of `data.table4` and `data.production`).
- **CV2 — the certificate meets H1 / H2 with one doubling of margin:** at $B=0$: $r_H(N/2) \le 0.1$ (the H1
  width) and $E_0 \in [E_R - r_H, E_R]$ at $N/2$ and at $N$; at $B=1$: $r_H(N/2) \le 0.15$ (H2: cluster energy
  certified to $\pm r_H \le 0.15$) and $E_0 \in [E_R - r_H, E_R]$ at $N/2$ and $N$.  `gap_assumption_holds` is
  reported with each interval (at $B=1$ it is expected false, as S1 production records: `gap_holds: false`;
  the Weinstein statement "some eigenvalue in $[E_R - r_H, E_R + r_H]$" is the rigorous one there, manual 5.3).
  The width curve $r_H(\phi N)$ is reported in full; **no plateau constant is imposed on the width**: the
  certificate is rigorous for any $B$, it must meet the target, and shrinking further with shots is not a
  requirement of H1/H2 (stated in the report).
- **CV3 — plateau against Krylov $k$ (equal shots per circuit, 2.5(b)):** $E_R(B^{(3)}) - E_R(B^{(4)}) \le
  E_{\rm tol}$ and $r_H(B^{(4)}) \le 0.1$ ($B=0$) / $0.15$ ($B=1$).  The allocation curve 2.5(a) and the $2N_c$
  curve are information.  **A CV3 failure is a STOP, not a re-sizing**: it says the signed family ($k \le 4$) has
  not converged in $k$ at that budget, and a $k = 5$ circuit is a family change (owner signature, amendment 01
  item 3).  The executor reports the $2N_c$ curve so the owner can see whether more shots or more $k$ is the
  remedy.
- **CV4 — convergence beats random equal-size bases (not saturation):** at every $\phi$ and every $k$,
  $E_R(B_{\rm sig}) <$ the 2.5th percentile of the 200 random bases of the same size (prompts/27 Tier A rule),
  and at $N$: $E^{\rm rand}_{2.5\%}(|B_{\rm sig}(N)|) - E_R(B_{\rm sig}(N)) \ge E_{\rm tol}$ and
  $W(B_{\rm sig}(N)) >$ the 97.5th percentile of the random $W$.  Reading: the device basis is better than a
  random basis of its size by at least the tolerance that CV1 resolves — a saturated sector (2x2) fails this by
  construction, a converging one at 2x3 passes it by two orders (Table 3: random at $|B| = 320$ has error
  $0.12$ / $0.10$).
- **CV5 — weighted coverage:** $W(B_{\rm sig}(N)) \ge 0.99$ in every seed (the weight carried by $S_{99}$, the
  set D3'-R guarantees).  Information: $W(\phi N)$ for all $\phi$, $W(B_{\rm all})$, $W_{\rm cl}$ at $B=1$, the
  eq. (6) bound, recall of $S_{999}$ / $S_{99}$ on both bases (prompts/28 P3's recall $\ge 0.9$ stays as it is
  and is evaluated on $B_{\rm sig}$ with $B_{\rm all}$ beside it).

**Gate status:** `CV_2x3_plan` PASS iff CV0-CV5 hold at every $f$ on the final plan of section 4 in all three
seeds and both sectors.  **Q0P_2x3_plan gains criterion P7:** "`validation/CV_2x3_plan.json` status PASS and its
plan equals the plan table's rows (per-circuit shots identical)".  The prereg v2 block (prompts/29 B3) gets a
section "Convergence and coverage (decision 2a)" rendered from the CV JSON only (P5's grep test covers it).

## 4 The re-sizing rule (what happens when the D3'-R minimum fails CV1, CV2, CV4 or CV5)

Uniform scaling: for the failing $f$, the plan becomes $s \times$ D3'-R shots per circuit (every circuit,
floor circuits included; $267 s$ rounded up to 100), with $s$ the smallest of $\{2, 4, 8\}$ at which CV1, CV2,
CV4, CV5 hold in all three seeds and both sectors **on the prefixes of the same $8N$ samples** (the criteria at
$sN$ use the $sN/2$ prefix; nothing is re-sampled).  The $\phi \ge 2$ points are evaluated only when the $1\times$
plan fails (lazy; the samples exist).  If $s = 8$ still fails: STOP, the planner returns.  The re-sized plan
replaces the D3'-R row of the plan table as "D3'-R$\times s$" with its HQC (`cost_of_plan`, the formula of
`data/quantinuum/devices_20261002.json billing`, $\le 10{,}000$ shots per job, 5 HQC per job), USD at the ESTIMATE
rate, and machine hours; the report carries a before/after table and the LOG row the new cost — **the executor
does not decide; the new cost returns to the owner** (decision 2a).  Planner arithmetic for orientation (HQC is
nearly linear in shots): the $f = 0.10$ minimum is $173{,}614 + 244{,}553 = 418{,}167$ HQC
(`scratch/planner/d3s_2x3_shot_rule_20261003.json plans.*.D3R.hqc_total`), so $s = 2$ is about $8.4\times10^5$,
$s = 4$ about $1.7\times10^6$, $s = 8$ about $3.3\times10^6$ HQC; the executor's `cost_of_plan` values replace
these.  Both sectors scale with the same $s$ only if both fail; otherwise each sector gets its own $s$ (state
which).  The D3'-R guarantees (P2) hold a fortiori for every $s \ge 1$ (superset); P2 is re-evaluated anyway.
**Before any campaign submission the gate is re-run at the measured $\hat f_{\rm ideal}$ of Stage P (rounded
down to 0.01)**, since the plan is sized at that $f$ (section 6).

## 5 The 2x2 information block (gate `CV_2x2_info`; 0 QPU s)

Same script, `--source counts data/hardware/H0_2x2_ibm_kingston/counts` on `Model(2)`, both sectors, the
recorded per-circuit histograms of `validation/H0_2x2.json` (never edited).  Hardware counts are histograms, not
shot sequences, so the nested subsamples are drawn **without replacement** (multivariate hypergeometric) per
circuit at $\phi \in \{1/16, 1/8, 1/4, 1/2, 1\}$, nested by accumulation, with 20 preregistered draws
(seeds $2030..2049$); the curves report mean / min / max over the draws.  The Krylov curve uses the recorded
`k_growth` structure (`data.support.*.k_growth`: 1,335 / 2,670 / 4,005 / 69,505 shots at $B=0$) at the
allocation only (no equal-shots version exists on hardware).  $E_{\rm tol}$ at 2x2 by 2.7 ($\lceil 0.8 \times 16
\rceil = 13$ of $S_{999}$ at $B=0$, $\lceil 0.8 \times 13\rceil = 11$ at $B=1$).  Random baselines as 2.6 (the
H0_2x2 seeds).  **CV1-CV5 are computed and tabulated but carry no verdict**; the gate's criteria are CV0 only
(structural), and the JSON and report carry the label `"not a device test (saturation)"` with the evidence:
$N a/\dim = 16.97$ / $15.72$ (`data.support.*.Na_over_dim`, $\ge 5$ = `saturates_from_noise`), $|B_{\rm all}| = \dim$
in both sectors, the garbage-only baseline at $E_0$ to $10^{-15}$ (`data.baselines.*.garbage_only.E_R`), and the
expectation that CV4's margin $E^{\rm rand}_{2.5\%} - E_R$ is below $E_{\rm tol}$ (random bases of 35 of 38
states reach $E_0$).  The recorded verdicts of H0_2x2 are not touched; the report's one-paragraph reading is:
the 2x2 curves are flat because the sector saturates from garbage, which is why the 2x3 criteria are needed
and why CV4 exists.

## 6 Where convergence enters Stage E / Stage P and the campaign (amends prompts/27 Stage 3 and prompts/29 B3)

- **Stage E (H2-2E) and Stage P (H2-2): $f$ only.**  The v3 plans (`B0_ref25_k1` 800, `B1_ref57_k1` 800,
  `B0_ref25_k4` 200, `B1_ref57_k4` 200) sample two references per sector and cannot generate the support; their
  GO rule is v3 on $\hat f_{\rm ideal} = f_{\rm hit}/r_{\rm nc}$ ($r_{\rm nc} = 1.115$, `data/cf_trajectories/r_nc.json`)
  and nothing else.  Any Ritz energy from their accepted strings is reported as information labelled "two
  references only: not a support, no convergence statement".
- **The campaign (prompts/27 Stage 3 run; prompts/28 B3 sizing):** (i) sized by D3'-R at
  $y = 0.82 \times 0.7 \times \hat f_{\rm ideal}$ of Stage P, re-sized by section 4 if `CV_2x3_plan` at that $f$ says
  so, the cost returned to the owner before submission; (ii) submitted in **two halves per circuit**
  ($\lceil N_c/2\rceil$ shots of every circuit in the first half, in jobs of $\le 10{,}000$), the mid-campaign
  check of prompts/28 B3 generalised from the $k = 4$ circuits to all circuits — the first half is then the
  **real** $N/2$ prefix; (iii) CV1-CV5 preregistered on the hardware counts with the $N/2$ point = the first
  half (real time order) and the finer points by hypergeometric subsampling within halves (seeds $2030..2049$,
  information); $E_{\rm tol}$, the H1/H2 widths, 0.99 and the random seeds exactly as in section 3; (iv) outcome
  rule: the certificates and the H1 / H2 / P1 rows are reported for any $B$ (they are rigorous or gap-assumed
  as labelled), but a campaign that fails CV1, CV2, CV4 or CV5 on hardware is labelled "not converged at the
  plan" in every table and the P1 curve is reported to $|B_{\rm sig}|$ with that label; one top-up by $s = 2$
  (section 4) is possible only under a new owner decision; a CV3 failure on hardware is reported as a family
  result (no top-up).  The prereg v2 block states (i)-(iv).

## 7 Steps (executor-opus; after or interleaved with prompts/29 Part B')

Orientation rule (binding): `graphify-out/graph.json` exists — use `graphify query "<question>"`,
`graphify explain "<symbol>"`, `graphify path "A" "B"`, `graphify affected "<symbol>"` before grepping or reading
whole files; after changing code run `graphify update .`.  Start with `graphify explain "measure_and_decode"`,
`graphify explain "support_metrics"`, `graphify explain "sig_support"`, `graphify explain "random_subsets"`,
`graphify explain "energy_block"`, `graphify explain "oracle"`, `graphify affected "corrupt_shots"`.

1. (1 h) `src/skqd/noise.py`: `measure_and_decode_sequence` (2.3).  `src/skqd/skqd.py`: `h1_energy_tolerance`
   (2.7).  Default paths untouched (a test that `measure_and_decode` output is byte-identical to before on a
   fixed seed).  Tests in `tests/test_cv.py`: histogram identity at seed 7 on a 2x2 state; `h1_energy_tolerance`
   returns $E_R(R \cup S_{999}) - E_0$ at `recall_target=1.0` and reproduces Table 3's oracle rows at
   `recall_target` chosen to give 40 / 80 states (through `controls.oracle`); nested-prefix bases are subsets.
2. (4 h) `scripts/gate_CV.py` with `--source emulated-plan --f 0.05 0.10 0.15 --seeds 20260914 1 2` (reads the
   D3'-R plans from `validation/Q0P_2x3_plan.json` written by prompts/29 B3 — run B3 first, or build the plan
   through `d3r_plan` in-process if the JSON does not exist yet, recording which) and
   `--source counts <dir> --model 2` (section 5); `--quick` = one seed, $f = 0.10$, 50 random seeds.  Output via
   `skqd.report.GateResult`: `validation/CV_2x3_plan.json`, `reports/CV_2x3_plan.md`, `validation/CV_2x2_info.json`,
   `reports/CV_2x2_information_20261005.md`; the curves (every $\phi$, every $k$, every seed, every random
   percentile) in the JSON under `data.curves`, the plan actually used under `data.plan` with `resized_by`.
   Runtime: sampling about 10 min in total (planner arithmetic: $3 \times 8 \times 305{,}000 \approx 7.3\times10^6$
   shots at the $3.5\times10^4$ shots/s of `data/S2D_recall_at_f.json`); Ritz + 200 random bases at
   $3 \times 3 \times 2 \times (5 + 4 + 4)$ points about 30 min — run one background chunk per $f$ (<= 27 min each),
   cache the sampled sequences under `data/cv/<sector>_<f>_<seed>.npz` (git-ignored if > 5 MB; say so).
3. (1 h) Q0P_2x3_plan (prompts/29 B3): criterion P7 and the prereg v2 section (section 3 here); the P5 grep
   test extended to the CV numbers.
4. (1 h) Section 5 block; `validation/gates.md` rows (`CV_2x3_plan`, `CV_2x2_info` as a note under H0_2x2);
   one paragraph in `reports/PROJECT_STATUS.md`; `graphify update .`; `pytest -q tests`;
   `python scripts/check_package.py`.
5. LOG rows (one per gate) and `git commit <paths>` (retry on `.git/index.lock`); **no push**.

## 8 Pass criteria (machine-checkable)

- `validation/CV_2x3_plan.json`: `status` PASS; `criteria[*].name` contains `CV0`, `CV1`, `CV2`, `CV3`, `CV4`,
  `CV5` for each (sector, $f$); `data.E_tol.B=0` and `.B=1` present with their state lists; `data.plan.resized_by`
  $\in \{1, 2, 4, 8\}$ per (sector, $f$) with the before/after HQC when $> 1$; `data.curves` complete (no
  `completed: false` unless the 30-minute rule bit, with the reason).
- `validation/Q0P_2x3_plan.json`: criterion P7 present and consistent with the CV JSON (per-circuit shots equal).
- `validation/CV_2x2_info.json`: `status` PASS on CV0 only; `data.label == "not a device test (saturation)"`;
  CV1-CV5 values present under `data.information`.
- `reports/Q0P_2x3_prereg.md` (v2) contains the section "Convergence and coverage (decision 2a)" whose numbers
  grep against the CV JSON (the P5 test).
- `pytest -q tests` and `python scripts/check_package.py` pass; `tests/test_cv.py` present.

## 9 Outputs

`src/skqd/noise.py`, `src/skqd/skqd.py` (additions only), `scripts/gate_CV.py`, `tests/test_cv.py`,
`validation/CV_2x3_plan.json`, `reports/CV_2x3_plan.md`, `validation/CV_2x2_info.json`,
`reports/CV_2x2_information_20261005.md`, `data/cv/*` (cache), the P7 / prereg v2 changes in
`scripts/gate_Q0P_2x3.py` and `reports/Q0P_2x3_prereg.md`, `validation/gates.md`, `reports/PROJECT_STATUS.md`,
`prompts/LOG.md`; git commit of these paths only; no push.

## 10 Escalation and STOP (binding)

- STOP (planner returns): CV3 fails at any $f$ in any sector (family question, section 3); $s = 8$ still fails
  (section 4); CV0 fails after one retry (a bug in the sampler, the subset logic or the oracle path — write
  `validation/BLOCKED.md` with the first differing quantity); the Table 3 oracle rows do not reproduce to
  $10^{-9}$ (CLAUDE.md rule 3); any criterion constant, the readout factor, the margin, $\lambda^*$, the signed
  family, the P9 $B_{\rm sig}$ rule or a signed bar would have to change.
- Retry rule: one re-run per failing criterion after writing the cause into the report; a second failure is
  BLOCKED.
- Re-sizing is not an escalation: it is the preregistered rule of section 4, applied mechanically and reported;
  the owner sees the new cost in the LOG row and the hand-back.
- **Do not touch (binding):** `src/skqd/su2.py`, `lattice.py`, `codec.py`, `reference_sim.py`, `device_req.py`;
  every existing `validation/*.json`; every frozen circuit under `data/hardware/` and `data/quantinuum/`;
  `A6_NOISE`; every criterion constant of every existing gate; `ci/`; `prompts/00`-`29`; other agents' LOG rows.
  **The parallel K1 executor's files (prompts/25 Part A + prompts/27 stage 0b):** anything matching
  `scripts/gate_K0*`, `scripts/gate_K1*`, `scripts/h0_submit.py`, `scripts/h0_backends.py`, `scripts/h0_qpu_time.py`,
  `validation/K0*`, `validation/K1*`, `reports/K0*`, `reports/K1*`, `data/hardware/K0*`, `data/hardware/K1*`,
  `data/hardware/*kingston*` created after 2026-10-05, `data/owner_decision_20261005_k1_2x3_fpilot.md`.  For the
  shared files `validation/gates.md`, `reports/PROJECT_STATUS.md`, `prompts/LOG.md`: re-read immediately before
  editing, append or edit only your own rows / paragraph, commit only your own paths, retry on `.git/index.lock`.

## 11 What the owner must do (the executor cannot)

1. Read the `CV_2x3_plan` verdict and, if any (sector, $f$) was re-sized, the new HQC / USD / machine-hour cost
   (section 4) — the campaign budget is a separate written decision (2a: "signing commits no HQC").
2. If CV3 fails: decide whether a $k = 5$ coarse circuit may be added to the family (amendment 01 item 3) or the
   campaign is run with the $k \le 4$ family and the result labelled.
3. Nothing else; Stage E / P GO rules and the Quantinuum access steps are unchanged.

## LOG row (append to `prompts/LOG.md`, one per gate)

| date | prompts/30_convergence_and_coverage_criteria.md (with prompts/29 Part B') | CV_2x3_plan / CV_2x2_info / Q0P_2x3_plan P7 | executor-opus | PASS/FAIL with: $E_{\rm tol}$ per sector; per (sector, $f$) the CV1 ratio, $r_H(N/2)$, $r_H(N)$, CV3's $\Delta E_k$, CV4's margin, $W(N)$, `resized_by` and the before/after HQC; the 2x2 block's CV4 margin against $E_{\rm tol}$ | commit | open owner items (section 11) |

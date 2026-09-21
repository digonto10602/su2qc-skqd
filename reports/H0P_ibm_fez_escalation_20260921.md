# H0P_ibm_fez escalation (2026-09-21) — the B=1 support did not saturate: cause, odds, decision

Planner memo (planner-fable, max effort) for the STOP-A hold of `prompts/15_H0_session_ibm_fez.md` part B.
Decision and executable plan: `prompts/16_H0P_ibm_fez_fix_20260921.md`.  No QPU time was spent for this memo
and none is authorised by it.

**Sources.**  Every quoted number is either (a) read from a JSON of this repository — the key is named — or
(b) a **planner computation [PC]** made on 2026-09-21 with the repository's own code (`skqd.krylov.apply_groups`
on the frozen circuits' angles k·dt in the group order of `h0_build_circuits.step_gates`, `skqd.exact.Model`,
`skqd.skqd.poisson_lambda_star`, the live per-circuit f of `validation/H0P_ibm_fez.json`).  The [PC] numbers were
cross-checked against the noiseless statevector of four frozen QPY circuits (`skqd.hardware.logical_statevector`,
max |Δp| = 4.9e-15) and are reproduced, and superseded, by `data/H0_shot_plan_*.json` written by step A'1–A'2 of
prompts/16 — the pass criteria there pin them.  The reproduction snippet is in the appendix.

## 1. The failure (validation/H0P_ibm_fez.json, commit 51ac0e6; calibration 2026-09-21T14:53:59-06:00)

- `criteria[2]` "B=1: decoded support reproduces the exact E0 = -1.8616": value 5.749340166172345e-06, threshold
  |E_R − E_0| < 1e-06, FAIL.  The other 15 criteria PASS.
- `data.analysis.by_sector["B=1"]`: shots 3912, accepted 358, `support_size_decoded` 19, `sector_dimension` 20,
  references [14, 7], E_R −1.8615822851948547, exact E_0 −1.8615880345350209, r_H 5.95e-03, Weinstein bracket
  [−1.8675, −1.8616] containing E_0, `captured_weight` 0.9999990674143225 (missing weight 9.326e-07).
- `data.analysis.by_sector["B=0"]`: accepted 974, support 38/38, abs_error 0.0.
- `by_sector_repetition`: r = 1 simulated yields 0.1657 (B=0, f_cal 0.1788) / 0.1554 (B=1, f_cal 0.1782); r = 2
  0.0231 / 0.0173; r = 3 0.0158 / 0.0109.  The B3 stop rule (yield ≥ 0.05) did not fire.
- For comparison `validation/H0P.json` (FakeFez snapshot, 2026-09-16, same seed and shot plan): B=1 accepted 327,
  support 20/20; B=0 accepted 928, 38/38; r = 1 yields 0.1493 / 0.1353 at f_cal 0.1261 / 0.1214.

## 2. The executing agent's diagnosis, verified

The agent argued: "the missing state carries ~9.3e-07 of the ground-state weight, so at 358 accepted shots its
expected count from the ideal amplitude is ~3e-04; it appeared on FakeFez only because noise scattered a shot onto
it".  The weight is right (four B=1 states — basis indices 40, 53, 61, 65 — carry 9.326e-07 each [PC], matching
`captured_weight`), the inference is wrong: **the support is sampled from the coarse-step states
|ψ_c⟩ = U_k^r |ref⟩, not from the ground state.**  In the sampled states those four configurations are not rare
[PC]:

| B=1 state (index; j2; n) | ground-state weight | largest ideal p over the 24 circuits | largest ideal p over the 8 r = 1 circuits |
|---|---|---|---|
| 53; (1,0,1,1); (1,1,2,2) | 9.33e-07 | 4.60e-02 (B1_ref07_k4_rep2) | 3.07e-03 (B1_ref07_k4_rep1) |
| 40; (0,1,1,1); (1,2,1,2) | 9.33e-07 | 3.04e-02 (B1_ref07_k4_rep1) | 3.04e-02 |
| 61; (1,1,0,1); (2,1,2,1) | 9.33e-07 | 8.47e-02 (B1_ref14_k4_rep3) | 4.14e-02 (B1_ref07_k4_rep1) |
| 65; (1,1,1,0); (2,2,1,1) | 9.33e-07 | 4.21e-02 (B1_ref07_k4_rep1) | 4.21e-02 |

So the expected number of clean observations of the weakest state under the frozen plan is 0.33, not 3e-04
(section 3), and — the consequence that matters — it scales with the shots.  Which of the four was missing on
2026-09-21 is not recorded in the JSON (the support's state list was not written; prompts/16 adds it); by the
plan's expected counts state 53 is the probable one (P(missing) 0.31 vs 0.06 / 0.03 / 0.03 [PC]).

## 3. What the frozen shot plan actually guarantees [PC]

Expected clean count of a sector state s under the plan: λ_s = Σ_c N_c · 0.82 · f_c · p_c(s) over all 24 (B=1) or
60 (B=0) circuits, with N_c = 267 / 130 / 92 (r = 1 / 2 / 3), f_c the day's calibration f of
`data.f_recomputed_on_the_day.per_circuit` (0.1775–0.1788 at r = 1, 0.0069–0.0075 at r = 2, 0.0006–0.0008 at
r = 3) and p_c(s) the ideal probability.  Garbage acceptances — the manual's second yield term (1 − f) a, a =
0.00488 (B=1) / 0.00928 (B=0), `data.analysis.random_acceptance`, uniform over the sector's codewords — add
g_s = Σ_c N_c (1 − f_c) a / dim per state.  With independent Poisson counts, P(s seen) = 1 − e^{−λ_s − g_s}.

| sector | garbage hits per state | weakest states: λ_s (live f / FakeFez f) | P(all states seen), clean only | P(all states seen), clean + garbage |
|---|---|---|---|---|
| B=1 (20) | 0.86 | 53: 0.33 / 0.34; 77: 0.91 / 0.70; 79: 1.26 / 0.91; 40: 1.89 / 1.39; 73: 2.51 / 1.94; 65: 2.67 / 1.93; 61: 2.82 / 2.05; 80: 3.22 / 2.44 | 0.076 / 0.035 | 0.42 / 0.33 |
| B=0 (38) | 2.15 | 55: 0.53 / 0.42; 59: 0.63 / 0.49; 69: 0.82 / 0.69; 71: 0.84 / 0.71; 75: 0.86 / 0.62; 35: 0.89 / 0.72; 78: 1.20 / 0.96; 76: 1.33 / 1.05 | 0.004 / 0.001 | 0.60 / 0.54 |

Three facts follow.
1. **Neither sector saturates from clean shots under the frozen plan**, on either calibration.  The premise of
   criterion 3 ("the sectors saturate", prompts/07; manual Sec. 9.1 and line 32 "any 10³-shot run saturates its
   sectors") is false for this circuit set at 267 shots per circuit and f ≈ 0.12–0.18.
2. The 38/38 and 20/20 supports of the committed runs were filled by garbage acceptances: a non-clean shot that
   happens to be one of the sector's codewords lands on a uniformly random sector state and is, physically, a
   legitimate member of the support (E_R of the full sector is E_0 regardless of how the states got there), but
   it makes the outcome of criterion 3 a coin flip: P(both sectors saturate) = 0.60 × 0.42 = 0.25 on the live
   calibration, 0.54 × 0.33 = 0.18 on FakeFez.  The H0P PASS of 2026-09-16 on criterion 3 was an 18 % event; the
   B=1 FAIL of 2026-09-21 a 58 % event.  Nothing about the device or the calibration is being measured by it.
3. The same coin flip would be tossed on the QPU by gate H0 (prompts/07 criterion 3, escalation branch (a)):
   a FAIL of that kind would not be evidence about the device, and a PASS would not be evidence about the bit
   order.

## 4. Answers to the three questions

**Q1 — is criterion 3 the right preparation criterion with this shot plan?**  The criterion is right as written
in the prereg — "Ritz energies of the *saturated* sectors reproduce E_0 to 1e-6" is the manual's bit-order and
convention check, exact when the premise holds (E_R = E_0 to float precision on the full sector).  The plan is
wrong: it was sized in prompts/15 D3 for the f comparison only ("more device shots would not sharpen a comparison
whose prediction side is simulated at 267 shots") and never for the premise of criterion 3, which nobody computed.
The reachability claim is therefore not "the plan provably cannot guarantee it" — it provably can, at a computable
cost (section 5) — but "the plan as frozen does not".

**Q2 — gate H0 on the device.**  With the frozen plan, criterion 3 on the device has P(PASS) ≈ 0.25 independent of
the bit order.  The gate must be run with a plan under which saturation is a *prediction* (P ≥ 0.99 from clean
shots for any device that passes criterion 2), so that a non-saturated support on the device is a ≤ 1 % event
that is reported with the missing states and their predicted counts (escalation (a) of prompts/15 stays and
becomes actionable).  The criterion and its tolerance are not changed.

**Q3 — the options.**  (i) Waiting for a calibration on which the prediction saturates is cherry-picking a noise
realisation: P(sat) is 0.25–0.42 on any calibration in this f range, so the wait selects the seed, not the
device.  Rejected.  (ii) Judging criterion 3 on `support_size_decoded` plus the Weinstein bracket is a relaxation
designed after the failure; the bracket [E_R − r_H, E_R] contains E_0 for almost any sector-valid support and
tests nothing about bit order.  Rejected — and unnecessary, because (iii) exists.  (iii) A denser r = 1 prediction
is the correct lever, generalised: it must cover B=0 as well (P = 0.004 from clean shots) and be sized by a rule,
not by a number picked today — the manual's own shot rule (eq. 5, `skqd.skqd.shot_rule`, λ* = 6.296 for "seen at
least three times with 95 %") applied to the rarest sector state of the frozen circuits.  Adopted (section 5).
(iv) Changing the B=1 references would touch the frozen set, would not fix B=0, and is not needed: the missing
states are reachable.  Rejected.

## 5. Decision — rule D3' replaces the r = 1 shot counts of D3; no criterion or threshold changes

**D3'.**  r = 2 and r = 3 stay at 130 / 92 shots (the yield-versus-CZ shape).  Every r = 1 circuit keeps the floor
267.  The k = 4 circuits of each sector (the coarse step at the largest angle 4Δt, which spread the reference
furthest — the minimal-cost allocation below selects exactly these) receive N₄(sector) shots, the smallest
multiple of 100 such that every sector state has expected clean count ≥ λ* from the r = 1 circuits alone at the
clean yield y_c = 0.82 × 0.7 × f_c, where f_c is the calibration f of the session day (the same
`gate_S2D.analyse_on_backend` value the prediction uses) and 0.7 is the lower edge of criterion 2 (measured f within
30 % of the prediction): **a device that passes criterion 2 saturates both sectors with the manual's 95 %/three-hit
guarantee per state.**  Garbage acceptances are not counted (conservative).  Values [PC]:

| calibration | N₄(B=0) | N₄(B=1) | r = 1 shots (B=0 + B=1) | min λ_s at 0.7 f_cal (r = 1 only) | P(saturate), clean, at 0.7 f_cal | at f_cal | r = 1 QPU execution | session estimate |
|---|---|---|---|---|---|---|---|---|
| ibm_fez 2026-09-21T14:53:59-06:00 (f_cal 0.1788 / 0.1782) | 8200 | 19700 | 45005 + 41002 = 86007 | 6.35 / 6.30 | 0.9978 / 0.9983 | 0.99987 / 0.99989 | 25.4 s | 69.9 s |
| FakeFez snapshot (f_cal 0.1261 / 0.1214) | 11700 | 28100 | 62505 + 57802 = 120307 | 6.32 / 6.31 | 0.9979 / 0.9984 | 0.99988 / 0.99990 | 35.6 s | 80.0 s |

(QPU seconds from `data/hardware/H0_ibm_fez/qpu_time_estimate.json`: r = 1 group 7476 shots in 2.209 s, i.e.
295.5 µs per shot; session = 46.70 s − 2.21 s + the new r = 1 time.  Both under the D6 cap of 120 s; 1.2–1.3 min of
the 10-min month.)  The unconstrained per-circuit optimum (linear programme, same constraint) needs 24139 + 22402
shots on the live calibration — about half — but up to four distinct shot counts per sector, i.e. up to ten jobs
under the runtime's "one shot count per job" rule; D3' needs one extra count per sector, six jobs in all.  The
factor two (≈ 12 s of QPU) buys a plan that is one sentence to preregister and symmetric over the references.

**What changes (named, before any submission).**  (1) Frozen item 3 of prompts/15, "the shot plan (D3)": the
r = 1 counts become the rule D3' above; the counts it produces on the day are written to
`data/hardware/H0_ibm_fez/shot_plan_<stamp>.json` together with the prediction and are frozen from then on
(h0_submit checks their stamp).  (2) Gate H0P gains two preparation criteria, "shot plan: every sector state has
expected clean count ≥ λ* in the r = 1 circuits at 0.7 × f_cal" (one per sector) — the script-checked statement
that the premise of criterion 3 is planned, not assumed.  (3) `analyse_records` records `support_states_decoded`,
`missing_states` and the per-state predicted/observed counts (outputs only; the criteria code of gate_H0.py is
untouched).  (4) The session has six main jobs instead of four; D6's per-job overhead check reads "6 jobs".
**What does not change.**  The frozen circuits `data/hardware/H0_prep` (byte-for-byte), the four prereg
criteria of `reports/H0_prereg_draft.md` section 4 and their constants (F_TOLERANCE 0.30, RANDOM_ACCEPT_MAX 0.01,
E0_TOL 1e-6, DIAG_MIN 0.9, RO_FACTOR 3, READOUT_FACTOR 0.82), the r = 2 / 3 shots, the 4000 calibration shots, the
sampler options (D8), the canary (D5: B0_ref06_k1_rep1 at 267 shots, a k = 1 circuit, unchanged by D3'), the
budget caps (D6), the prediction-on-the-day rule (D1), the stop rules of B3, and the H0 escalation clauses.

**Why this is a correction and not a post-hoc adjustment.**  The argument uses no device data and no outcome of
the failed run: the ideal amplitudes of the frozen circuits, the manual's shot rule and the calibration f were all
available on 2026-09-16, and the computation shows the plan's criterion-3 outcome was a coin flip *then*.  The
remedy raises no tolerance and adds shots — it makes the test stricter, because a bit-order error can no longer
hide behind an unsaturated support, and the E_0 check becomes deterministic at the criterion's own lower edge.
The one number chosen by the planner, the margin 0.7, is not new: it is the tolerance of criterion 2.

## 6. Residual risk on the device, and what the gate does with it

If the device passes criterion 2, each of the ~15 weak states is missing with probability ≤ e^{−6.3} = 0.2 % and
both sectors saturate with probability ≥ 0.997 (clean shots; garbage only helps).  A missing state with predicted
λ_s ≥ 6.3 is then a signal about that codeword (decoder or bit order), which is precisely what criterion 3 is for;
the per-state table of predicted versus observed counts (change 3) makes it visible.  If the device fails
criterion 2 by being worse than 0.7 × f_pred, the support may also not saturate, but the gate then fails on
criterion 2 and the prompts/07 clause (b) governs (the 2x3 budget is not spent).  No branch needs a criterion
change after the fact.

## Appendix — reproduction of the [PC] numbers (repository code only; ~10 s)

```
python - <<'EOF'
import sys, json, numpy as np; sys.path.insert(0,'src')
from skqd.exact import Model; from skqd.krylov import references, term_groups, apply_groups, basis_vector
from skqd.skqd import poisson_lambda_star, READOUT_FACTOR
M=Model(2); g2=4.0; G=term_groups(M.terms,g2,3*g2/16); lam_star=poisson_lambda_star(3,0.95)
D=json.load(open('validation/H0P_ibm_fez.json'))['data']; fl=D['f_recomputed_on_the_day']['per_circuit']
a={s:v['fraction'] for s,v in D['analysis']['random_acceptance'].items()}; shots={1:267,2:130,3:92}
for sec,twoB in (('B=0',0),('B=1',2)):
    ref=M.reference(g2,twoB); idx=ref.indices; dim=len(idx); P={}
    for r0 in references(M.basis,twoB):
        for k in range(1,5):
            psi=basis_vector(M.basis.dim,r0)
            for r in (1,2,3):
                psi=apply_groups(G,psi,k*ref.dt); P[f"B{twoB//2}_ref{r0:02d}_k{k}_rep{r}"]=(np.abs(psi)**2)[idx]
    for fk in ('f_live','f_manifest'):
        lam=sum(shots[int(c[-1])]*READOUT_FACTOR*fl[c][fk]*p for c,p in P.items())
        gar=sum(shots[int(c[-1])]*(1-fl[c][fk])*a[sec]/dim for c in P)
        r1=[c for c in P if c.endswith('rep1')]; k4=[c for c in r1 if 'k4' in c]
        A={c:READOUT_FACTOR*0.7*fl[c][fk]*P[c] for c in r1}
        N4=int(np.ceil(np.max((lam_star-267*sum(A[c] for c in r1 if c not in k4))/sum(A[c] for c in k4))/100)*100)
        print(sec,fk,'P(sat) clean %.4f with garbage %.4f'%(np.prod(1-np.exp(-lam)),np.prod(1-np.exp(-lam-gar))),'N4',N4)
EOF
```

# Session handover — 25 September to 2 October 2026

Written at the end of the session so that the next one (human or agent) can pick up without
re-reading the log.  Follows `reports/SESSION_HANDOVER_20260921_24.md`.  Every number below is
copied from the file named next to it (Rule 1); if a number and its file disagree, the file wins.

> **Superseded in part — read section 7 ("Update, 2 October 2026 evening") first.**  Client-side XY4
> dynamical decoupling turned the 2x2 NO-GO below into a GO, and the full 2x2 SKQD hardware run is done.

**One-sentence summary (as of the morning of 2 October):** the 2x2 lattice was given its best shot on IBM Heron (shorter
schedules, better patch, one preregistered pilot on ibm_kingston) and measured a clean-shot
fraction of 0.041 against the signed budget of 0.1, so **2x2 on IBM is NO-GO on today's
devices**; 2x4 is compiled and verified; 2x3 is infeasible on IonQ.

**Quantum machine time: 29 s of the 600 s open-plan allowance used (571 s left).** Three jobs
in total: the canary (2.0 s), the H0_diag factorial (15.0 s), the kingston pilot (12.0 s).

---

## 1. How to resume

1. `cd ~/Projects/su2qc-skqd-v0.1.0 && git pull && python scripts/check_package.py && pytest -q tests`
   (last run: 233 passed, 2 skipped, PACKAGE OK).
2. Read this file, then `prompts/LOG.md` (newest rows at the bottom) and `validation/BLOCKED.md`
   (gitignored, local only: it holds the open K5 question and the history of every STOP).
3. In Claude Code: `claude --continue` in this directory resumes the conversation; a fresh session
   only needs this file.
4. Agents (owner decision 2026-10-01): planner `.claude/agents/planner-fable.md` = Fable 5.1 at
   high effort, executor `.claude/agents/executor-opus.md` = Opus 5.5 at high effort.
5. IBM account: `python scripts/ibm_account.py --check` (the key is stored; never pass it on a
   command line).  Only `open-instance` is visible; the 400-minute allocation is not yet.

## 2. Gate table changes in this period

| gate | status | file | one line |
|---|---|---|---|
| S2_2x4 | **PASS 12/12** | `validation/S2_2x4.json` | 2x4 circuits compiled and verified exact; GPU stage on Perlmutter job 59162991 (`validation/S2_2x4_gpu.json`) |
| H0_model | **PASS 5/5** | `validation/H0_model.json` | scheduled Aer at the measured free-induction T2* post-dicts the fez hardware |
| S2D_levers | **PASS 9/9** | `validation/S2D_levers.json` | prompts/23: duration levers on kingston; ALAP is the lever; C6 scoped to p_ref >= 0.5 by the planner ruling `reports/S2D_levers_C6_ruling_20261002.md` |
| H0_kpilot (dry run) | **PASS 9/9** | `validation/H0_kpilot_dryrun.json` | K3 form per `prompts/21a` |
| H0_kpilot | **FAIL 8/9 (K5), decision NO-GO** | `validation/H0_kpilot.json` | the one kingston pilot job |

## 3. The kingston pilot (prompts/21, 21a) — the result of this period

- Job `davv8504oijs73e88fvg`, 8 pubs x 4000 shots, dynamical decoupling and twirling off (D8'),
  billed 12.0 s against an estimate of 9.04 s and a 30 s cap.  Calibration fingerprint
  `ec74eb8bf15dde41` identical at preregistration, submission and retrieval.
- Circuit: `L1_seed_alap` (the signed term family, re-seeded, ALAP-scheduled) on patch
  [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95].
- **Direct clean fraction, pooled over the two k = 1 circuits: f = 0.0413, 95 % [0.0361, 0.0470]**
  (242 reference hits, 1.95 expected from garbage).  Preregistered rule: NO-GO because the upper
  end is below 0.1.  The planner had predicted NO-GO in writing beforehand.
- Equivalent dephasing ratio from the circuit's own f: about 0.17, the same as ibm_fez's 0.174;
  the bar was r_crit 0.3285 (preregistered) / 0.2788 (day's grid).
- K5 fails: the windowed Ramsey gave readout-corrected P0 below 1/2 on 9 of 12 qubits, which pure
  decay cannot do — a detuning or static-ZZ signature that this design (all 12 qubits in
  superposition, no detuning model) cannot separate from decay.  r_eff 0.0974 is therefore biased
  low and `model_consistent` reads False (ratio 3.27; 2.97 with the reference statistic on both
  sides).  The NO-GO rests on the direct f and does not depend on K5.
- For information: at the measured f the D3' shot plan would be N4 36200 (B=0) / 86300 (B=1),
  about 121 s of execution — i.e. running anyway is possible within the allowance, but below the
  signed budget.

## 4. Other work completed in this period

- **Perlmutter GPU CI** adopted with the owner's engine/HPC policy (`RUNBOOK.md`).  L4 PASS on
  GPU, S3 calibration PASS, S2_2x4 GPU stage done.  Aer seeds shot j with seed + j, so chunked
  runs stride seeds by chunk size (`src/skqd/circuits_qiskit.py`); QPY for Perlmutter is written
  at version 13 (qiskit 1.4.3 there, 2.5.2 here).
- **Amendment 01** (`proposal/amendment_01_devices_and_budgets.md`): items 1–3 SIGNED 2026-09-23;
  M4.4 near-clean acceptance term added; errata (2x2 is 256 CZ all-to-all / 618 routed).
- **The owner's nine decisions** of prompts/20 approved one by one
  (`data/H0_replan_owner_decisions.md`); D8' (options off) is the default in `scripts/h0_submit.py`.
- **IonQ feasibility** (`data/ionq_2x3_feasibility_20261001.json`, published specs, gate-only):
  2x3 f = 3.52e-05 (Aria) / 8.61e-05 (Forte) → infeasible; 2x2 f = 0.261 (Aria) / 0.303 (Forte)
  → feasible on gate errors alone (idle term not published for Forte).
- **Literature catalogue** `prompts/low_clean_fraction_techniques.md` (owner) read; prompts/23 was
  written from it.
- Laptop RAM is 62 GiB since 2026-09-30.

## 5. Open decisions for the owner

1. **Direction for 2x2 on IBM** after the NO-GO: (a) run below budget (~121 s of execution at
   f = 0.041); (b) adopt a technique from the catalogue that changes the circuit, which needs a
   signature; (c) move 2x2 to IonQ, where the gate-only f clears 0.1; (d) wait for better devices.
   Recommendation: a planner re-plan with the measured 0.041 before any further QPU spend.
2. **K5 of H0_kpilot**: accept FAIL as recorded, or ask the planner to rule that this Ramsey design
   cannot test K5 on this device.  No re-run without a second QPU job.  Does not change NO-GO.
3. **Amendment item 4** (the 2x3 device: needs vendor gate durations and T1/T2, not only error
   rates) and **item 5** (shot quota, scales as 1/f).
4. **The 400 IBM minutes** awaiting approval; the main 6-job H0 submission stays held.

## 6. Standing constraints (unchanged)

No QPU spend without the owner's go; IBM key never printed or on a command line; no Perlmutter
login (CI by `scripts/ci_request.sh`, at most 6 jobs per UTC day, BLOCKED file after 3 failures in
a row); never edit `ci/status.json`, `ci/poll.sh`, `reports/ci-*.out`, `validation/ci_*.json`;
preregistered records are never rewritten — corrections are new gates; 30-minute laptop rule.

---

## 7. Update, 2 October 2026 evening (prompts/24 and 25)

**One-sentence summary:** client-side XY4 dynamical decoupling (DD) raised the 2x2 clean fraction on
ibm_kingston about 2.8x, past the signed budget, and the full 2x2 SKQD hardware run passed; 2x3 and
2x4 are not runnable on ibm_kingston or on any IonQ device that exists today.

**IBM time: 102 s of 600 s used, 498 s left**
(`data/hardware/H0_2x2_ibm_kingston/account_check_after_20261002T2157Z.json`).  All work is
committed; everything up to 8ec5db8 is pushed, the three commits after it (aa6d883, 918e01d and this
update) are local until pushed.

### 7.1 What ran (all on ibm_kingston, calibration fingerprint `84d59cbf9b5973d1` throughout)

| step | gate / file | QPU | result |
|---|---|---|---|
| literature search + plan | `reports/ibm_decoherence_literature_20261002.md`, `prompts/24` | 0 s | XY4 / context-aware DD ranked first |
| Stage T, DD A/B test | `validation/H0_ddtest.json` PASS 8/8 | 20.0 s | no DD f 0.0400 [0.0358, 0.0446]; XY4 in windows >= 1.024 us (T3, adopted) f 0.1129 [0.1058, 0.1203], ratio 2.819 [2.495, 3.185]; XY4 everywhere 2.793; context-aware DD **collapsed** (ratio 0.012, unexplained) |
| Stage R, full 2x2 SKQD | `validation/H0_2x2.json` PASS 8/8, `reports/H0_2x2_ibm_kingston.md` | 53.0 s | 5 jobs, 133 907 coarse shots; f (7 k = 1 circuits) 0.1271 [0.1084, 0.1479]; E_R on the above-noise support within 5.5e-4 (B=0) / 5.7e-6 (B=1) of exact E0, certificates contain E0 |

Owner decision recorded: `data/owner_decision_20261002_run_below_signed_budget.md` (with XY4 the run
turned out to be inside the budget for the k = 1 circuits).

### 7.2 How to read it

- At 2x2 random noise fills both sectors (about 16-17 noise hits per state), so the exact energy from
  all decoded states is **not** a device result: uniformly random strings reproduce it in 100/100 seeds.
- The device-dependent reading is the above-noise support B_sig: 5th percentile of random equal-size
  bases in B=0 (a modest signal), 28.5th in B=1 (no evidence).
- Full plan-versus-evidence report and publishability verdict:
  `reports/H0_2x2_full_hardware_report_20261002.md` (51 plan rows: 31 fulfilled, 12 with deviation,
  8 not done; the neural/ML step was not applied to hardware data).  Verdict: not publishable as an
  SKQD physics result; publishable as a methods note (honest sampling at a noise-saturated size); the
  XY4 finding could become a short technical note after replication and a test of the context-aware
  DD collapse.

### 7.3 2x3 and 2x4 (prompts/25, `reports/ionq_devices_2x3_2x4_planner_analysis_20261002.md`)

- **ibm_kingston: NO-GO for both, and DD cannot change it.**  DD removes only idle error.  2x3 has
  5477 routed CZ (`validation/S2.json`); even at the device's best edge error 8.164e-4 on every CZ the
  ceiling is f <= 1.14e-2, below the worst-case bar 0.05.  2x4 has 148 726 routed CZ
  (`validation/S2_2x4.json`), ceiling about 1e-53.
- **IonQ: infeasible on every device available today** (vendor pages read 2026-10-02): Forte /
  Forte Enterprise give 2x3 f about 8.6e-5 on published specs; Aria is retired; Tempo is a late-2026
  projection whose 99.9 % target gives 2x3 f about 0.077, still under 0.1.  2x4 is far out of reach.
  2x2 on Forte Enterprise is feasible (a cross-platform check).
- What 2x3 needs: two-qubit error <= 7.4e-4 AND the 2158-gate circuit run well inside T2.
- prompts/25 has the executor build (0 QPU s): gate K0_2x3_2x4 (the kingston verdict on the day's
  record), IonQ native-gate compilation verified exactly, `ionq_account.py` / `ionq_submit.py`
  (key never printed), a device/cost table, gates I0P_2x3 / I0P_2x4.  **Status at this writing:
  see `prompts/LOG.md` and `git log` for how far the executor got.**

### 7.4 Open decisions for the owner

1. 2x2 campaign: close it (methods note + release bundle, 0 s), or spend about 32 s on a DD
   replication plus three cells testing why context-aware DD collapsed.
2. IonQ: whether to run 2x2 on Forte Enterprise as a cross-platform check (about $5-20k on Braket);
   what to ask IonQ (measured Tempo two-qubit error, gate time, T2, parallelism; raw bit strings with
   debiasing off).
3. Whether any cheaper, unsigned 2x3 circuit variant may be considered for a future device (needs a
   signature; none reaches 0.1 on Forte).
4. A Perlmutter CI token for the 2x4 native-gate verification.
5. Amendment items 4 and 5; the 400 IBM minutes still pending.

### 7.5 Resume

`git pull && python scripts/check_package.py && pytest -q tests`, then read this section,
`prompts/LOG.md` (newest rows) and the newest prompt (`prompts/25_*`).  The `coding` environment was
repaired on 2026-10-02; the pinned stack (qiskit 2.5.2, aer 0.17.2, runtime 0.49.0) was verified
afterwards and reproduced every Stage T number exactly.

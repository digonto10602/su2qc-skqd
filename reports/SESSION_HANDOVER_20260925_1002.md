# Session handover — 25 September to 2 October 2026

Written at the end of the session so that the next one (human or agent) can pick up without
re-reading the log.  Follows `reports/SESSION_HANDOVER_20260921_24.md`.  Every number below is
copied from the file named next to it (Rule 1); if a number and its file disagree, the file wins.

**One-sentence summary:** the 2x2 lattice was given its best shot on IBM Heron (shorter
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

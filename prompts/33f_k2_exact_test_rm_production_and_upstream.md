# 33f — Campaign 33, addendum 6: K2 judged by the exact test, production = RM, C2_XY4 now, the OMP binding, the qiskit-aer report

executor: executor-opus   effort: high
time budget: laptop code about 3 h (0 QPU s, 0 HQC); Perlmutter: `C2_XY4` (queues through the maintenance if needed)
machine: laptop + Perlmutter CI
date: 2026-10-18   planner: Fable 5.1 (high)   prompt number: 33f (addendum to `prompts/33d`, `33e`)

Trigger: `C2_KCHK` run 2 (job 59828887) FAIL 8/14 on S3 (affinity 1) and S6 (Kraus 7 < 8) with K1 `bug_confirmed`
($z_w = -6.65$: GPU Kraus 3.00 $\pm$ 0.24 vs CI-CPU Kraus 8.43 $\pm$ 0.78 at 7 shots), K3 `none`, K4 `agree`
(CI CPU vs laptop CPU: $z$ 0.91 / $-0.35$), K2 `blocked` with both weights inside $3\sigma$ (1.80, $-1.26$) and five
"blocking" clbits, all from `rm_gpu_cusv` (512 shots) against the 7-shot `kraus_cpu` arm.  Laptop reference of
record (`data/campaign33/c33c_diag/summary.json`, the 1.4.3 / 0.15.1 twin): CPU Kraus 67 shots 7.463 $\pm$ 0.269, CPU
RM 78 shots 7.269 $\pm$ 0.274; against GPU RM 7.43 $\pm$ 0.10: $z_w$ 0.10 and $-0.56$, no clbit beyond $3\sigma$
(max $|z|$ 2.49, 2.10); against GPU Kraus: $z = 12.5$.  Two C2_KCHK failures in a row: no third request without this
ruling.  Planner arithmetic: `scratch/planner/campaign33f_k2_exact_test_20261018.json`.

**Rule 1 binding; no tolerance is loosened (the per-test level 0.0027 of 33a is kept); 0 QPU s.**

---

## 0. The rulings

**R1 — K2's statistic, derived.**  K2 asks whether two engines sample the same distribution; per clbit the null
hypothesis is a common marginal $p$.  The Wald score $z = (\hat p_1-\hat p_2)/\sqrt{\hat p_1(1-\hat p_1)/N_1 +
\hat p_2(1-\hat p_2)/N_2}$ estimates the variance under the *alternative*, separately per arm; it is the large-$N$
approximation of the exact test and is undefined — not conservative, not strict, undefined — when a small arm
returns $\hat p_2\in\{0,1\}$ (its term is 0 and $z$ is set by the other arm's tiny error: the 7-12 of clbits 2, 3, 5).
The test the $3\sigma$ Wald was approximating is **Fisher's exact test on the $2\times2$ table** (the conditional
distribution of the small arm's count given the common $p$, which needs no variance estimate), flagged at the same
per-test level $P(|Z|>3) = 0.0027$, Bonferroni 20 × 0.0027 = 0.054 as before.  Wald and Fisher coincide at large
$N$; at 7 shots only Fisher is a test.  This is a correction of a mis-specified statistic, not a tolerance change;
the pooled-variance $z$ the executor reported as information is the score-test approximation of the same thing.
Applied to run 2 (planner arithmetic, the executor's script recomputes it): clbit 2 ($\hat p_{\rm GPU} = 0.146$, CPU 0/7)
$p = 0.60$; clbit 3 (0.213, 0/7) 0.35; clbit 5 (0.088, 0/7) 1.0; clbit 8 (0.414, 6/7) 0.045; clbit 17 (0.422, 6/7)
0.046; smallest $p$ over the 20 clbits 0.045 against the CPU Kraus arm and 0.074 against the 12-shot CPU RM arm:
**no clbit is flagged**; the power is stated as in 33d (a marginal difference below 0.57 is invisible at 7 shots,
below 0.44 at 12).

**R2 — the evidence decides production = RM; no third CI run.**  K2 is read on every CPU reference that passed K4
(CI arms: Kraus 7, RM 12; laptop arms: Kraus 67, RM 78 — same qiskit / aer / numpy versions, the wheel named), each
against `rm_gpu_cusv` (512) with Fisher per clbit and the weight $z$: CI arms — weights 1.80 / $-1.26$, no flag
(R1); laptop arms — weights 0.10 / $-0.56$, max $|z|$ 2.49 / 2.10 (Fisher agrees at that $N$), no flag, and at 67 / 78
shots a marginal difference above 0.19 would have been visible.  Four references, two stacks, one answer.  A third
C2_KCHK with 28 threads would add about 40 Kraus shots — fewer than the laptop's 67 — and could not improve the
decision; it is not requested.  The decision is written by a laptop script (`scripts/campaign33_c2_decide.py`) into
**`data/campaign33/c2_representation_decision.json`** (every input named with its JSON path and job id, the
Fisher table for all four references, the power lines, `production_representation: rm`, `reference_arm: none`
(K3), `kraus_gpu: unusable (aer 0.15.1 GPU Kraus path, see aer_gpu_kraus_report)`), and `run_c2_cell` reads **that
file** (S0 of 33d: FAIL without it).  No harvested JSON is edited; `validation/C2_KCHK.json` stays FAIL on S3/S6 and
the gate table says "decision in data/campaign33/c2_representation_decision.json (prompts/33f)".

**R3 — C2_XY4 now, and what follows.**  `C2_XY4` is requested as soon as R2's file and R4's sbatch change are
merged and pushed, whatever the queue does with the 2026-10-21 reservation: IBM-T3, echo half, both K1 circuits,
production RM at 100 % of the window (no reference arm), S6 minimum 1 000 production shots per circuit (expected
about 2 500 at 0.417 s/shot).  After the maintenance: `smoke` first (R4's affinity check), then `C2_ECHO`, `C2_GATE`,
`C2_STAR`, `C2_COH` on RM.  Before the maintenance, on the laptop (no GPU): `python scripts/campaign33.py --stage
assemble` on everything harvested (classes 1, 3, 4 except F3/F6; C4_CF as recorded; C2_CAL / C2_KCHK as
calibrations) → the first `reports/C33_campaign_report.md`; and 33b step A if still open (the seed rule is needed
before any slot is re-used for F3 / F6).

**R4 — (b) the main-thread binding: unset the OpenMP binding, policy amended.**  `OMP_PROC_BIND=spread` +
`OMP_PLACES=threads` make the OpenMP runtime bind the master thread to place 0 when `qiskit_aer` initialises it on
import; everything after (the driver's decoding, Ritz, bootstrap, and every subprocess) then runs on one CPU.  It
changes no number: the arithmetic depends on the thread *count* (fixed by `OMP_NUM_THREADS` and `threadpool_limits`),
not on placement.  Ruling: remove both exports from `jobs/gate.sbatch` (keep `SLURM_CPU_BIND=cores` and the
thread-count exports), amend RUNBOOK line 362 accordingly ("no OpenMP binding: it pins the master thread on Aer
import"), keep `record_step_cpus` and S3's `cpu_affinity == SLURM_CPUS_PER_TASK` clause as the check.  No re-run of
E1-E3 (no convention or thread-count change); the `smoke` token after the maintenance records `cpu_affinity: 32`
and is the gate for every later request.  **Without R4 every future token FAILs S3** (the clause is merged), so R4
precedes the `C2_XY4` request.

**R5 — the qiskit-aer report: confirmed enough to file.**  Three independent exhibits: (1) the GPU-vs-GPU
inconsistency of one channel under fusion on/off and kernel choice (no-fusion 1.14 $\pm$ 0.22 vs cuStateVec 3.00
$\pm$ 0.24, $z = 5.7$; native 3.57 $\pm$ 0.25), (2) GPU Kraus vs CPU Kraus on the identical software versions, two
CPU stacks agreeing (K4): $z = -6.65$ (CI, 7 shots) and 12.5 (laptop, 67 shots), (3) the same channel expressed
without Kraus instructions (RM; identical super-operators on 17 of 21 qubits) agreeing with CPU Kraus on both
stacks.  The executor assembles `data/campaign33/aer_gpu_kraus_report/` (the owner files on `Qiskit/qiskit-aer`):
- `README.md`: the claim in one paragraph (GPU statevector with Kraus instructions returns a distribution that
  differs from the CPU statevector of the same version and from itself across fusion / kernel options, in the
  direction of excess relaxation), the table of every arm with job id / source JSON / shots / $\bar w\pm$ se /
  s per shot, the statistics (weight $z$, Fisher per clbit), the versions (qiskit 1.4.3, qiskit-aer-gpu 0.15.1,
  numpy 2.5.3, python 3.12.14, the CUDA / cuStateVec / driver versions and the GPU model from the job logs and
  `run.gpu_telemetry`), and the small-scale negative results (1-, 2-, 8-qubit statevector vs density-matrix agree) —
  with the reading of the 0.16.x / 0.17.x release notes (33d R4) stated as "no fix found" or "fixed in x.y.z";
- `circuit_IBM-T0_B0_ref117_k1.qpy.gz` (QPY v13, sha256) and `circuit.qasm3` if `qasm3.dumps` accepts the delays;
- `noise_model_kraus.json` (`NoiseModel.to_dict()`), `noise_model_rm.json`, `relaxation_pass.json` (per-qubit
  $T_1$ / $T_2$, `dt`, the op type) since custom passes are not in `to_dict`;
- `reproduce.py`: loads the QPY, rebuilds the model from the dicts, applies the pass, runs CPU and GPU
  (cuStateVec on/off, fusion on/off) with the recorded seeds and prints $\bar w$ per arm — self-contained, no
  `skqd` import;
- `counts/` — the raw counts of every arm (`.npz` and JSON) with their seeds and chunking;
- `logs/` — `reports/ci-59780907.out`, `reports/ci-59828887.out`, the laptop segment JSONs;
- `environment/` — `pip freeze` of the `skqd` env (from the job log if present, else the owner adds it) and the
  laptop twin.
Not before the owner reads it; nothing in the report is a number that is not in a committed JSON.

## 1. Executor steps (laptop, about 3 h)

1. `scripts/campaign33_c2_decide.py` and `data/campaign33/c2_representation_decision.json` per R2 (Fisher per clbit,
   `scipy.stats.fisher_exact`, two-sided; the Wald and pooled $z$ kept as information); `run_c2_cell` reads it;
   test: on the committed JSONs the file says `rm`, flags nothing, and on a synthetic 0/7 vs 0.15 case Fisher gives
   0.60 where Wald gave 7-12.  `C2_XY4`: RM at 100 %, no reference arm, S6 1 000 per circuit; dry run.
2. `jobs/gate.sbatch` and RUNBOOK per R4; `tests/test_ci_gpu_mode.py` asserts the two exports are absent.
3. `data/campaign33/aer_gpu_kraus_report/` per R5, with `reproduce.py` executed on the laptop CPU for 2 shots as a
   smoke test (the GPU branches skipped with a message).
4. Assembly draft (R3) on the harvested JSONs; `pytest -q tests`; `graphify update .`; LOG row; commit.

## 2. Pass criteria

- `data/campaign33/c2_representation_decision.json`: `production_representation == "rm"`, `reference_arm == "none"`,
  four references listed with their job ids / paths, `fisher_min_p >= 0.0027` for each, power lines present.
- `validation/dryrun/C2_XY4.json`: S0 read from the decision file, 2 runs, one arm (`production`, rm).
- `jobs/gate.sbatch` without `OMP_PROC_BIND` / `OMP_PLACES`; RUNBOOK line amended; the test PASSes.
- `data/campaign33/aer_gpu_kraus_report/README.md` and every file of R5 present; `reproduce.py` runs on the CPU.
- `git diff --stat` shows nothing under `src/skqd/{su2,lattice,codec*,reference_sim,circuits_ir}.py`.

## 3. Requests (coordinator)

| when | tokens |
|---|---|
| steps 1-2 merged and pushed | `C2_XY4` (now; it may queue through the maintenance) |
| after the maintenance, first | `smoke` (must show `cpu_affinity: 32`) |
| then | `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` (RM) |
| then, owner's call | the 33b deferred list (F3 15 jobs, F6 10, f-cells B-D 3, cv3 F2_B1 2, C4_CF 2-part) |

No third `C2_KCHK`.

## 4. What needs the owner

1. File the qiskit-aer issue from `data/campaign33/aer_gpu_kraus_report/` when the executor hands it over.
2. The deferred-list decision after the maintenance (33b section 2, ranks 14-16; C4_CF K = 2000).
3. Note for the record: class-2 production is RM — the Kraus channel with $T_2 := \min(T_2, T_1)$ on four qubits —
   because aer 0.15.1's GPU Kraus path is unusable; every class-2 JSON says so in `noise.representation_reason`.

# 33d — Campaign 33, addendum 4: the Aer GPU Kraus path is the suspect, not the RM channel; C2_KCHK decides the class-2 representation

executor: executor-opus   effort: high
time budget: laptop code + tests about 0.5 executor day (0 QPU s, 0 HQC); Perlmutter: one 60-min job (`C2_KCHK`)
before `C2_XY4` is requested
machine: laptop (code, CPU tests, commit) + Perlmutter CI
date: 2026-10-13   planner: Fable 5.1 (high)   prompt number: 33d (addendum to `prompts/33`, `33a`, `33b`, `33c`; 33c R1
and R2 are corrected here, everything else stays in force)

Trigger: the 33c executor's diagnostics (branch c33c, commits 3ce492a..9f6db28, `data/campaign33/c33c_diag/summary.json`,
written by `scripts/c33c_diag_full.py` with the GPU arms from `validation/C2_CAL.json` job 59736871).  Mean Hamming
weight of IBM-T0 `B0_ref117_k1` under I-ECHO: **CPU Kraus 7.47 $\pm$ 0.56 (19 shots, qiskit 1.4.3 / aer 0.15.1, the CI
twin), CPU RM 6.92 $\pm$ 0.57 (24), GPU RM 7.42 $\pm$ 0.08 (1024), GPU Kraus 2.40 $\pm$ 0.14 (640), GPU PTA 9.96 $\pm$ 0.10
(512).**  CPU Kraus vs GPU Kraus $z_w = 8.8$; CPU Kraus vs GPU RM $z_w = 0.10$.  The RM and Kraus passes attach
identical errors at all 55 delay sites of qubit 53 (super-operator difference 0.0 on both stacks); the one-qubit
$P(1)$ check passes for both ($e^{-400/292.7} = 0.2550$: RM 0.2614, Kraus 0.2510).  Qubit 53 is dephased at the
measurement ($T_2 = 68\ \mu$s, followed by an `sx`), so $P(1)\approx0.5$ there: GPU RM 0.519, GPU Kraus 0.142.

**Rule 1 binding; no criterion, tolerance, bar or convention changes; 0 QPU s.**  Code orientation: `graphify explain
"ibm_spec"`, `graphify explain "kraus_record_model"`, `graphify explain "simulator"` (tokens_run), `graphify explain
"make_simulator"`, `graphify explain "run_c2_cal"`, `graphify affected "C2_CELLS"` first.

---

## 0. The rulings

**R0 — 33c R1/R2 are withdrawn.**  My relaxation expectation (2.64 bits) neglected the measurement-basis rotation
(`sx` after the last idle on most qubits) and the $T_2$ dephasing, so it had no power to tell 2.4 from 7.4; the
executor's CPU reference on the identical stack settles it: the T0 Kraus weight is 7.4-7.5, the channels of RM and
Kraus are identical where they should be, and the one GPU arm that disagrees with everything else is **Kraus on the
cuStateVec path**.  The premise "RM is a bug" is false; the premise "Kraus-GPU is physical" is false.  What stands
from 33c: the device/T0 gap is now 9.77 against about 7.4 (the RM/CPU value, $z\approx30$), to be tested on the
flown T3 circuit by `C2_XY4` (R1's XY4-symmetrisation mechanism remains the hypothesis, now with the right number);
`C2_XY4` stays the primary class-2 cell, echo half only; C4_CF accepted as recorded; F8 unchanged.

**R1 — the class-2 representation.**  Production is **RM on the GPU**, conditional on one check (`C2_KCHK`, R3): RM
is Kraus's exact channel on 17 of the 21 qubits and differs on four only by $T_2 := \min(T_2, T_1)$ (at most a
factor 1.23 in $T_2$: 59, 69, 92, 95), it contains no Kraus instruction, it costs 0.35 s/shot, and it already agrees
with CPU Kraus in weight ($z_w = 0.10$).  CPU Kraus is not a production engine: 174 s/shot on the laptop, so the 256
shots per circuit S6 demands would take 12 h per circuit, and the CI runs GPU jobs only.  Kraus on another GPU
engine (Aer's native statevector kernels with `cuStateVec_enable=False`, or cuStateVec with fusion off) is measured
in `C2_KCHK` as a candidate for the cells' 20 % reference arm only; a density-matrix check is impossible at 21
qubits ($4^{21}$ amplitudes).  What is **not yet** established is that the GPU reset/Pauli path is right either:
`cpu_rm_vs_gpu_rm` in the diag summary has max $|z|$ marginal 13.2 on clbits 1 and 2 — CPU RM found 0 of 24 where
GPU RM gives 0.145 / 0.120 ($P\approx0.02$ and $0.05$ each under the GPU value, a 1-in-1000 coincidence together) —
so `C2_KCHK` carries a CPU RM arm with as many shots as the node can give.

**R2 — which harvested results used Kraus on the GPU.**  Audit of `src/skqd/campaign33/noise.py` and `cf_gpu.py`:
`quantinuum_spec` (E1-E8, all class-4 tokens) builds `depolarizing_error` and `pauli_error` only, plus classical
readout errors — unitary mixtures, no Kraus; E3's angle-dependent pass caches `depolarizing_error`, E5's memory
term is `pauli_error`; `cf_gpu` inserts explicit Paulis into the IR and runs noiseless statevectors; C1/C3 are
noiseless.  Kraus instructions exist only in `kraus_record_model` (gates and delays of the four $T_2>T_1$ qubits,
and every two-qubit error touching them: 6 580 `kraus` entries in `to_dict`) — i.e. **only the Kraus arms of
`C2_CAL` runs 1-3**.  Nothing harvested from class 1, 3, 4 or C4_CF is affected; **nothing is re-run.**  Older GPU
gates (S3, L4) used depolarizing errors only.  The executor records this audit as `data/campaign33/kraus_audit.json`
(every noise builder, the instruction classes it emits, read from the built models' `to_dict` and custom passes
with `kraus_instructions`), and `tests/test_campaign33_noise.py` asserts 0 Kraus instructions in every E1-E8 model.

**R3 — the minimal GPU check: token `C2_KCHK`** (class 2, walltime 01:00:00, 1 GPU, env `skqd`; allowlist line
`C2_KCHK      01:00:00 1`).  Circuit IBM-T0 `B0_ref117_k1`, model I-ECHO on the 2026-10-06 record (the C2_CAL
configuration), double precision, seeds by the token rule, **raw counts of every chunk stored in the JSON** (21-bit
strings, at most about 1 200 shots per arm) and as `results/campaign33/C2_KCHK/<arm>.npz`.  Arms:

| arm | engine / options | shots | purpose |
|---|---|---|---|
| `kraus_gpu_cusv` | GPU, `cuStateVec_enable=True`, `batched_shots_gpu=False` (C2_CAL's path) | 256 fixed | reproduces the 2.40 |
| `rm_gpu_cusv` | same path, RM | 512 fixed | the production candidate |
| `kraus_gpu_native` | GPU, `cuStateVec_enable=False`, `batched_shots_gpu=False` | target 256, minimum 64, deadline-stopped | is the bug in the cuStateVec path only? |
| `kraus_gpu_cusv_nofusion` | C2_CAL's path with `fusion_enable=False` | target 128, minimum 32 | is it the fusion of Kraus sites? |
| `kraus_cpu` | CPU statevector in a **separate process started first** (`max_parallel_threads` = the node's CPUs minus 4), chunks of 4 | minimum 16, then the window | the reference on the identical stack |
| `rm_cpu` | same process, alternating chunks with `kraus_cpu` | minimum 16, then the window | resolves the clbit 1/2 flag |

Window 0.75 of the remaining budget for both processes; GPU arms in the order listed, each deadline-stopped at
a chunk boundary; the CPU process is stopped at the same deadline and its JSON merged.  Statistics per arm: $\bar w$
with its standard error, the 20 per-clbit marginals, accepted / distinct / hits / rejections, s/shot; pairwise
comparisons with the P4a statistic (|z| $\le3$ on $\bar w$ and on every marginal, two-sample, the Bonferroni line
stated) — the constant is 33a's, reused, not changed; the power at the CPU shot count is written next to every
marginal verdict (at 40 CPU shots a marginal difference below 0.24 is invisible: say so).  Criteria:
- **K1** (physics, the bug confirmation): `kraus_gpu_cusv` vs `kraus_cpu` — `confirmed` iff $|z_w| > 3$ (expected
  $\approx9$); `not_confirmed` otherwise (then C2_CAL's Kraus arm was a fluctuation and the decision of C2_CAL is
  reinstated).  Both outcomes PASS the token (it is a calibration); the field `bug_confirmed` is the decision.
- **K2** (the production decision): `production_representation = rm` iff `rm_gpu_cusv` agrees with **both**
  `rm_cpu` and `kraus_cpu` at $|z_w|\le3$ and no marginal beyond the Bonferroni expectation (at the stated power);
  else `blocked` — then `prompts/BLOCKED_C33.md` for class 2 (no engine delivers 256 trusted shots per circuit in
  60 min) and the three deferred cells and `C2_XY4` wait for the owner.
- **K3** (the reference-arm path): `validated_kraus_gpu_path` = the first of `kraus_gpu_native`,
  `kraus_gpu_cusv_nofusion` that agrees with `kraus_cpu` at $|z_w|\le3$ with its measured s/shot; `none` otherwise.
  The cells' 20 % reference arm uses it when it exists and is dropped (production RM at 100 %) when it does not.
- S1-S5 as every token; S6 = every minimum above reached.
- `supersedes_decision_of: {"token": "C2_CAL", "job": "59736871", "field": "decision.production_representation"}`:
  the C2_CAL JSON is not rewritten; `validation/gates.md` gets the note at assembly.

**R4 — upstream.**  Yes, after K1 says `confirmed` and the executor has read the qiskit-aer release notes of 0.16.x
and 0.17.x for a cuStateVec Kraus / non-unitary fix (URL and date recorded in the LOG row): the owner files the issue
on `Qiskit/qiskit-aer` with the QPY v13 circuit, the noise-model `to_dict`, the seeds, the raw counts of the GPU and
CPU arms and the versions (aer 0.15.1, the CUDA / cuStateVec versions from the job's environment block).  A smaller
reproducer is a GPU bisection over the circuit depth (the executor's 1-, 2- and 8-qubit checks agree, so the trigger
is size or site count) — after the maintenance, one CI job, only if upstream asks.  Not before confirmation.

**R5 — C2_CAL run 3's P4a decision does not stand.**  "production = kraus" was reached by comparing RM with the arm
now under test; the comparison was between a correct and a suspect execution of the same channel, so it decides
nothing about the channel.  The record is kept unedited (rule 1); `C2_KCHK` is the decision of record for the
representation, and `C2_CAL`'s `decision` block is read through `supersedes_decision_of`.  P4c's "PTA matches the
device" stands as information and is explained by unitality (33c R1, unchanged in that respect).

## 1. Executor steps (laptop, about 0.5 day)

1. `C2_KCHK` in `scripts/gate_tokens.json` and `ci/allowed_jobs.campaign33` (+ the generated-text test), `tokens_run.
   run_c2_kchk` per R3 (reuse `run_c2_cal`'s arm machinery and `Sampler`; new: the native / no-fusion simulator
   options in `make_simulator`, the CPU subprocess with its own deadline, raw counts in the JSON); dry run on the
   laptop (`--shots-scale`, 2 shots per arm, CPU only) writes `validation/dryrun/C2_KCHK.json` with every field.
2. `run_c2_cell`: the production representation and the reference-arm path are read from `validation/C2_KCHK.json`
   (`decision.production_representation`, `decision.validated_kraus_gpu_path`); absent that file the cell refuses to
   run on the CI (`S0 representation decided`: FAIL) — never a silent default.  `C2_XY4` stays echo-only, both K1
   circuits, S6 minimum 1 000 production shots per circuit when RM (33a's constant for RM) — expected about 2 400
   per circuit at 0.35 s/shot.
3. `data/campaign33/kraus_audit.json` and the zero-Kraus test of R2.
4. `pytest -q tests` (laptop) and the campaign33 tests on the 1.4.3 twin; `graphify update .`; LOG row (with the
   aer release-note reading of R4); commit on c33c; the coordinator merges and pushes.

## 2. Pass criteria

- `validation/C2_KCHK.json` (CI): `status: PASS`; `data.bug_confirmed` in {true, false}; `decision.production_representation`
  in {`rm`, `blocked`}; `decision.validated_kraus_gpu_path` in {`kraus_gpu_native`, `kraus_gpu_cusv_nofusion`, `none`};
  every arm's raw counts present (sum of counts = `shots_done`); `kraus_cpu.shots_done >= 16`, `rm_cpu.shots_done >= 16`;
  `supersedes_decision_of` present.
- `data/campaign33/kraus_audit.json` lists E1-E8, I-GATE/ECHO/STAR/XY4/COH (kraus, rm, pta) and CF with their
  instruction classes; the test asserts 0 Kraus in E1-E8.
- `validation/dryrun/C2_XY4.json` shows `S0 representation decided` evaluated from a stub `C2_KCHK.json`.
- `git diff --stat` shows nothing under `src/skqd/{su2,lattice,codec*,reference_sim,circuits_ir}.py`.

## 3. Requests (coordinator)

| when | tokens |
|---|---|
| after step 1 is merged and pushed and the owner has appended `C2_KCHK      01:00:00 1` | `C2_KCHK` (alone; the F-run batches of 33c keep the queue full around it) |
| `C2_KCHK` harvested with `production_representation: rm` | `C2_XY4` (with the next F batch of 33c) |
| `production_representation: blocked` | no class-2 request; `prompts/BLOCKED_C33.md`; the queue slot goes to the next F batch |
| after the maintenance, if RM is production | `C2_ECHO`, `C2_GATE`, `C2_STAR`, `C2_COH` on RM (the Kraus 20 % arm only if K3 validated a path) |

The must-run set before 2026-10-21 is unchanged (24 jobs); `C2_KCHK` replaces `C2_ECHO` in the should-run set.  If
`C2_KCHK` cannot be harvested by 2026-10-18, `C2_XY4` slips past the maintenance and its slot goes to the next F
batch.

## 4. What needs the owner

1. Append `C2_KCHK      01:00:00 1` to `~/skqd-ci/allowed_jobs` (one line; the repo file `ci/allowed_jobs.campaign33`
   gains it in the same commit).
2. If K1 confirms: file the qiskit-aer issue with the attachments of R4 (the executor prepares the bundle under
   `data/campaign33/aer_gpu_kraus_report/`).  Optional, after the maintenance: a scratch env on Perlmutter with a
   newer `qiskit-aer-gpu` that still satisfies qiskit 1.4.3, re-running `C2_KCHK` there — only if the release notes
   name a fix.
3. Note: 33c's relaxation estimate was wrong and is withdrawn (R0); the physics claim about XY4 symmetrisation is
   untested until `C2_XY4` runs on a trusted representation.

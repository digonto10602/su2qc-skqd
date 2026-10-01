# 2x2 on IBM: can the duration levers reach f >= 0.1? — planner analysis (2026-10-01)

planner-fable, for `prompts/23_ibm_2x2_duration_reduction.md`.  **0 QPU seconds used, none authorised.**
Every number below is read from a named JSON key or is a labelled planner computation (P1–P10) whose
reproduction snippet is in section 6; the snippets run on the laptop in the `coding` environment (P7 takes
6 minutes, P5 2.5 minutes, the rest seconds) and write nothing into `data/` or `validation/`.

## 0. The two findings that change the question

1. **The catalogue's cost model does not apply here.**  `prompts/low_clean_fraction_techniques.md` prices every
   technique with f = (1 − ε)^N_2q.  On this project the gate-only product was 15–50x optimistic for the 2x2
   step (`validation/H0_model.json`: the scheduled-Aer prediction at the measured free-induction T2 post-dicts
   the hardware clean count to 1.05x, the echo end is 49.58x off; `validation/H0_diag.json`: idle-time
   relaxation is the cause).  Its "B3: fractional R_ZZ halves N_2q, f → √f" does not transfer either: the 2x2
   step in the `rzz` basis has 252 two-qubit gates against 256 in the `cz` basis all-to-all and 584 against 588
   on the heavy-hex map (P4) — the circuits are Gray-code ladders of multiplexed Ry rotations, and only a
   one-control rotation collapses into one R_ZZ; the 2x3 count already said so (2158 RZZ against 2164 CZ,
   `data/S2D_2x3_device_requirements.json`).  Techniques must be judged on the **scheduled duration and idle
   budget**, which is what prompts/23 measures.
2. **The PTA scenario arithmetic of the owner's analysis is a bound, and on ibm_kingston's best patch the
   prediction of record sits higher.**  The owner's table (0.056 as recorded, 0.118 with the duration halved,
   0.093 with DD to the T1 limit, ...) is the analytic PTA bound f_gates e^{−S_T1−S_T2} on the survey winner.
   P6 reproduces its 0.05622 and 0.11759 exactly.  But the PTA is a bound (prompts/20 H0P-Y': PTA 2.843e-03 ≤
   Aer-scheduled 1.465e-02 ≤ unscheduled 1.258e-01 on FakeFez, `validation/H0_model.json`), and the planner's
   Aer anchor on the kingston winner (P7, FakeKingston base carrying the live survey record, 2000 shots) gives
   **f_clean = 0.080 at the echo end with the frozen canary relabelled as it is (ASAP), and 0.104 with the same
   gates scheduled ALAP** — i.e. at the echo end the signed bar is reached on that patch with no new circuit at
   all.  At the fez-transferred free-induction end (every T2 x 0.174) the same two numbers are 0.0059 and 0.029.
   So the question "can 2x2 meet f ≥ 0.1 on IBM" is not decided by duration: it is decided by the in-circuit
   dephasing time of the kingston patch, which no committed record contains and a 1-s `ramw` pub measures.
   What prompts/23 can decide offline is (a) how far the compile-level levers move both ends, and (b) the
   break-even ratio r_crit = T2*/T2_echo above which f ≥ 0.1 — the number the pilot's measurement is read
   against.

## 1. Facts (committed JSON)

| item | value | key |
|---|---|---|
| frozen canary `B0_ref06_k1_rep1` on the fez record | 663 CZ, depth 1328, 455 CZ layers, T 43.71 us, S_T1 0.7553, S_T2 2.5676, f_gates 0.2103, PTA f 7.58e-03; packing bound T_min 24.74 us (1.77x) | `data/S2_duration_compare.json: circuits["exact|frozen|B0_ref06_k1_rep1"], rescheduling_headroom` |
| H0_model post-diction | T2* end 1.05x, echo end 49.58x of the pooled clean count; FakeFez sandwich PTA 2.843e-03 ≤ scheduled 1.465e-02 ≤ unscheduled 1.258e-01 | `validation/H0_model.json: criteria[3], data.C1_estimator_validation` |
| measured fez ratios T2_used / T2_echo (12 qubits of patch 1, incl. bounds) | 0.070, 0.070, 0.102, 0.107, 0.123, 0.132, 0.174, 0.263, 0.394, 0.411, 0.678, 1.209; median 0.153; the 9-measured fallback of S2D_idle is 0.174 | `validation/H0_model.json: data.t2_override_table`; `validation/S2D_idle.json: data.t2_bracket` |
| kingston survey winner | [82, 83, 96, 102, 103, 104, 105, 106, 107, 117, 125, 126]; mapping 117→82, 122→102, 123→103, 124→96, 125→83, 136→104, 141→107, 142→106, 143→105, 144→117, 145→125, 146→126; f_gates 0.24930, S_T1 0.49389, S_T2 0.99550, PTA f 0.056220, T_total 50.14 us, idle summed 442.6 us, min T2 131.8 us | `data/H0_device_survey_live_20260930.json: devices[2].patch_select.winner` |
| kingston record | `data/hardware/device_survey_20260922/ibm_kingston_20260930T2255Z.json`, stamp 20260930T2255Z, 156 qubits / 176 edges, `missing_errors == []`, cz 68 ns, sx 32 ns, measure 2.18 us, dt 4 ns, rep delay 250 us | the record |
| 2x2 per-term CZ (all-to-all / routed) | diag 8/8, hop0 60/122, hop1 48/92, hop2 66/149, hop3 44/72, plaq0 30/73; coarse step 256 / 618 | `validation/S2.json: data.2x2` |
| IonQ 2x2 | gate-only f Aria 0.216 (physical rz) / 0.261 (virtual rz), Forte 0.281 / 0.303 — all meet 0.1; **with the serial-idle estimate** Aria 0.0506 / 0.0810 (duration 0.278 / 0.227 s at 600-us gates against T2 = 1 s); Forte: no published gate times, idle not computable | `data/ionq_2x3_feasibility_20261001.json: results["2x2|..."]` |

## 2. Planner computations

**P1 — why `h0_patch_select.py` refuses on kingston.**  Live kingston qubit 146 carries `T1_s = None`,
`T2_s = None`, `sx_error = 1.0`, `measure_error = 0.5010` (an uncalibrated qubit); the other eleven qubits of
the frozen patch 117–146 are fully characterised.  `search()` scores every embedding that `record_covers`
accepts and then asserts that the identity embedding is among the scored ones; the identity embedding was
*skipped* for coverage ("qubit 146 has no T1_s"), so the assertion fires with the message "the enumeration is
wrong" — which it is not.  The survey routed around it by calling the enumeration directly
(`h0_device_survey.patch_search_without_the_incumbent`).  Fix: in `search()`, distinguish "the incumbent is
not in the enumeration" (a real bug, keep raising) from "the incumbent is in the enumeration but not covered
by the record" (a device fact: `incumbent = None`, the reason recorded, the consistency check skipped, every
`gain` field None-safe).  Never a defaulted T1/T2 for 146.

**P2 — best-of-N transpilation (lever B4), 24 seeds.**  The B = 0 reference-6 k = 1 coarse step (default term
order, exact family) transpiled on the FakeKingston coupling map (the Heron r2 layout; no calibration), basis
rz/sx/x/cz, level 3, `seed_transpiler` 0..23, each scheduled ASAP on a uniform record with kingston durations
(cz 68 ns, sx/x 32 ns, measure 2.18 us): T_s **44.24–50.18 us** (median 47.40), CZ **588–668**, max busy
qubit 24.4–38.9 us; 22 of 24 route inside 12 qubits, 2 use 15–16.  The frozen canary on the same record:
47.96 us, 663 CZ, busiest qubit 27.12 us.  Best seed (2): 44.24 us, 588 CZ — **0.92x** the canary.  One
level-3 transpile of this circuit takes 0.1 s, so thousands of seeds are affordable.

**P3 — what the critical path is made of.**  Longest path of the frozen canary's DAG at fez durations: 455
CZ (30.94 us) + 532 one-qubit pulses (12.77 us at 24 ns) = 43.71 us (= `T_s`).  On kingston (sx 32 ns) the
same path is 30.94 + 17.02 = 47.96 us: **the one-qubit pulses are 35 % of the duration on this device.**
The busiest qubit (physical 143 on fez) runs 259 CZ and 297 sx/x pulses, 24.74 us of its own gates — the
packing floor.

**P4 — fractional-gate bases (lever B3), offline, seed 2.**  Neither offline snapshot exposes `rzz`/`rx`
(FakeKingston ops: cz, delay, id, if_else, measure, measure_2, reset, rz, sx, x), so this row is the generic
basis count; the live durations are what prompts/23 reads.

| basis | map | two-qubit gates | ops | depth | 2q layers | 1q-pulse layers | rzz angles (units of π) |
|---|---|---|---|---|---|---|---|
| rz sx x cz | all-to-all | 256 | sx 443, x 98, rz 379 | 736 | 202 | 313 | — |
| rz sx x rzz | all-to-all | 252 | sx 421, x 135, rz 671 | 858 | 201 | 328 | 0.5 x248, 0.058 x4 |
| rz sx x rx rzz | all-to-all | 252 | rx 395, rz 522 | 599 | 201 | 190 | 0.5 x248, 0.058 x4 |
| rz sx x rx cz | all-to-all | 256 | rx 376, rz 231, x 1 | 495 | 202 | 188 | — |
| rz sx x cz | heavy-hex | 588 | sx 1214, x 67, rz 702 | 1294 | 412 | 520 | — |
| rz sx x rzz | heavy-hex | 584 | sx 1139, x 120, rz 1581 | 1540 | 410 | 521 | 0.5 x580, 0.058 x4 |
| rz sx x rx rzz | heavy-hex | 584 | rx 1026, rz 1294 | 1257 | 410 | 379 | 0.5 x580, 0.058 x4 |
| rz sx x rx cz | heavy-hex | 588 | rx 610, sx 467, rz 534 | 1033 | 412 | 398 | — |

R_ZZ changes the two-qubit count by −1.6 % and every angle is in (0, π/2] (the four 0.058π are the physical
rotation angles at k = 1; they scale with k and stay below π/2 at k = 4).  The `rx` gate is the one that
touches the critical path: one-qubit pulse layers fall from 520 to 398 on the heavy-hex map (−23 %), which is
worth up to ~0.23 x 17 us ≈ 4 us (8 %) on kingston **if** the live `rx` duration equals the `sx` duration — a
number only the live fractional target carries.

**P5 — term order (lever 3), all 720 orders at seed 2.**  The six term gate lists (diag 20, hop0 132, hop1 94,
hop2 132, hop3 90, plaq0 54 IR gates) concatenated in every permutation after the reference preparation,
transpiled and scheduled as in P2: T_s **35.78–51.52 us** (median 45.43).  Default order
(diag, hop0, hop1, hop2, hop3, plaq0): 44.24 us, 588 CZ, 12 active qubits.  Best: (plaq0, hop2, diag, hop1,
hop3, hop0) 35.78 us, 629 CZ, **15 active qubits**; third (hop2, hop3, diag, hop1, hop0, plaq0) 36.56 us,
601 CZ, 15 active.  Term order is a larger duration lever (±20 %) than the seed (±8 %), but the short orders
route through ancillas that idle for the whole circuit, so the objective of the scan must be the idle-aware f,
not T.  A reordered step is a different coarse-step operator (the terms do not commute): its ideal
distributions, reach and p_ref must be recomputed, and the family is a new one for the owner to sign.

**P6 — the PTA on the kingston winner.**  Frozen canary relabelled along the survey mapping, scheduled on
the kingston record, record T1 and echo T2 scaled by a uniform ratio r:

| case | f (PTA) | S_T1 | S_T2 | note |
|---|---|---|---|---|
| r = 1, as scheduled | **0.056220** | 0.49389 | 0.99550 | reproduces the survey winner; S_DD 0.2795 over 232 DD-eligible windows |
| r = 0.174, as scheduled | 7.667e-04 | 0.49389 | 5.2905 | the fez 9-measured fallback ratio |
| r = 1, every window halved | 0.11759 | 0.24934 | 0.50212 | the owner's "duration halved 0.118" |
| r = 0.174, every window halved | 0.012165 | 0.24934 | 2.7708 | |

Break-even ratios (PTA): r_crit(0.1) does not exist at the full or at 0.75x duration (even r = 1 gives
0.056 / 0.081) and is **0.754 at half duration**; r_crit(0.05) = 0.893 / 0.602 / 0.364 at 1.0 / 0.75 / 0.5x.
375 idle windows, longest 27.74 us, per-qubit idle 20.8–46.0 us; winner T2 132–380 us, T1 107–366 us.

**P7 — the prediction of record on the same patch (Aer, scheduled, clean-yield statistic).**
`backend_from_record(record, base=FakeKingston(), strict=True)` round-trips the survey record (qubit 146 is
None in both, so the fingerprint check passes); `AerSimulator.from_backend(base, seed_simulator=11)`;
`transpile(relabelled canary, backend=base, optimization_level=0, scheduling_method=..., seed_transpiler=7)`
(663 CZ unchanged, 519 delays ASAP / 521 ALAP); 2000 shots; decoded with `reference_string_test` and
`clean_fraction_mixture` (garbage expectation 0.488 reference hits per 2000):

| T2 ratio r | schedule | accepted | reference hits | f_clean (reference) | f_clean (mixture) | PTA on the delay windows (S_T1, S_T2, leading delays excluded) |
|---|---|---|---|---|---|---|
| 1 (echo) | ASAP | 221 | 116 | **0.0797** | 0.0795 | 0.4938, 0.9954 (= P6) |
| 1 (echo) | ALAP | 309 | 151 | **0.1039** | 0.1070 | 0.4193, 0.8437 |
| 0.5 | ASAP | 161 | 67 | 0.0459 | 0.0477 | 0.4938, 1.9568 |
| 0.174 | ASAP | 48 | 9 | 0.0059 | 0.0064 | 0.4938, 5.2896 |
| 0.174 | ALAP | 134 | 42 | 0.0287 | 0.0271 | 0.4193, 4.5204 |

Aer / PTA at the echo end = 0.0797 / 0.0562 = **1.42x** (the bound is tighter here than the 5.15x on FakeFez
because the windows are short against kingston's T2).  **ALAP is a parameter-free lever**: the same gates,
scheduled as late as possible with explicit delays, leave 11–21 us of idle time in |0> before the first gate of
qubits 82, 83, 102 and 126 where neither T1 nor T2 acts; 1.30x at the echo end and 4.9x at r = 0.174 (9 hits,
±33 %).  Each 2000-shot cell took 66–81 s on this laptop.

**P8 — what the levers are worth, from P2–P7 (planner expectation, to be measured by prompts/23).**  Seeds
0.92x in duration, order up to 0.81x at the cost of 3 ancilla qubits, `rx` up to 0.92x; combined perhaps
0.65–0.75x — **not 0.5x**: the packing floor (P3) is the busiest qubit's own 259 CZ + 297 pulses, and halving
needs a re-synthesis that cuts that qubit's gate count, which no transpiler setting does.  In f, with ALAP:
echo end ≈ 0.15–0.2, transferred end (r = 0.174) ≈ 0.05–0.08; r_crit(0.1) with the full stack of order
0.25–0.4 against the fez patch-1 ratios 0.07–1.21 (median 0.153).  These are expectations; the gate measures.

**P9 — "diag last / dropped" is not a lever.**  A diagonal term applied last changes no measured
probability and could be dropped from the sampled circuit, but at 2x2 it is 8 CZ of 618 (1.3 %;
`validation/S2.json`).  Noted and dropped.

**P10 — garbage saturation at 2x2 (C22).**  With N a / dim ≥ 5 the sector fills from accidentally-valid
noise alone: B = 0 (a = 0.00928, dim 38) at N ≥ 20 474 shots, B = 1 (a = 0.00488, dim 20) at N ≥ 20 492 —
every plan the project has made.  So at 2x2 the SKQD energy is exact whatever the hardware does, any hardware
claim rests on the clean-shot statistic (C2'/C3'), and configuration recovery (catalogue C3/C4) is excluded
at 2x2 because it would manufacture the support.

## 3. What prompts/23 therefore asks

Measure, on the live kingston record and with the chain the owner signed (Aer on the **scheduled** circuit,
T2 at both ends of the bracket, read with the **clean-yield** statistic, the PTA bound alongside): the rows
as-is ASAP, as-is ALAP, best seed, best (order, seed) by the idle-aware objective, + fractional `rx`/`rzz`
from the live target, all combined; for each the scheduled T, S_T1, S_T2 at both ends, f (PTA and Aer) at
r ∈ {1, 0.5, 0.25, 0.174}, the 0.1 / 0.05 bars, and r_crit.  Verdict fields: `duration_halved_reachable`
(T_best / T_as-is ≤ 0.5), `meets_0.1_at_echo`, `meets_0.1_at_transfer_0.174`, `r_crit_0.1`.  Then the
pilot (prompts/21) measures T2* on the patch and the prediction at the measured table decides H0.

## 4. Honest limits

- The transferred T2* end (uniform r) is a planner construction, not a measurement; T2* need not scale with
  the echo T2 and is qubit-specific (fez: 0.07–1.21).  Only the `ramw` pub on the kingston patch replaces it.
- Aer's dephasing on a delay is exponential (Markovian); the real free-induction decay is often closer to
  Gaussian over short windows, which is why the pilot measures two window lengths (D5').
- The H0_model post-diction (1.05x) was made with ASAP scheduling against a hardware run whose server-side
  schedule is not on record; submitting circuits with explicit delays (ALAP) removes that ambiguity for the
  next run and is the recommendation whatever the levers give.
- A reordered coarse step is a new circuit family: exactness (statevector against `apply_groups` in the new
  order), leakage, reach of the exact 99.9 % support and p_ref are all re-verified in prompts/23, and the
  owner signs the family before any freeze.
- 2x3 on IBM is out of scope: the gate-only product alone over the 5477 routed CZ of `validation/S2.json` on
  this record's CZ errors is of order e^{−13} (prompts/23 prints the exact value); no duration lever rescues it.
- IonQ for 2x2: gate-only 0.22–0.30 meets the bar, but the same idle physics at 600-us gates puts Aria at
  0.051–0.081 by the serial estimate and Forte is not computable without published gate times (section 1);
  the vendor spec of amendment 01 item 4 (t_2q, T2* under the vendor's DD) decides, not this analysis.

## 5. Snippets (laptop, `coding` environment; nothing writes into data/ or validation/)

P1 (1 s):
```python
import json; rec = json.load(open('data/hardware/device_survey_20260922/ibm_kingston_20260930T2255Z.json'))
for q in [117,122,123,124,125,136,141,142,143,144,145,146]:
    v = rec['qubits'][str(q)]; print(q, v['T1_s'], v['T2_s'], v['sx_error'], v['measure_error'])
# expected: every qubit characterised except 146: None None 1.0 0.5009765625
```

P2 / P5 (seeds: 3 s; orders: 145 s):
```python
import sys, itertools, numpy as np; sys.path.insert(0,'src'); sys.path.insert(0,'scripts')
from qiskit import transpile; from qiskit_ibm_runtime.fake_provider import FakeKingston
from skqd.exact import Model; from skqd.codec import Codec; from skqd.circuits_ir import CircuitFactory
from skqd import circuits_qiskit as cq, idle, coherence; from h0_build_circuits import repeated_coarse_step
M = Model(2); F = CircuitFactory(M, 4.0); n = Codec(M.basis).n_qubits; dt = float(M.reference(4.0, 0).dt)
cmap = FakeKingston().coupling_map; edges = sorted({(int(a), int(b)) for a, b in cmap})
rec = coherence.uniform_record(156, edges, t_2q=68e-9, t_1q=32e-9, t_ro=2.18e-6, T1=250e-6, T2=200e-6)
def T(tq): s = idle.schedule_asap(tq, rec); return s['T_s']*1e6, int(tq.count_ops()['cz']), len(s['active'])
qc = cq.ir_to_qiskit(repeated_coarse_step(F, 6, 1, dt, 1), n, measure=True)
print([T(transpile(qc, coupling_map=cmap, basis_gates=['rz','sx','x','cz'], optimization_level=3, seed_transpiler=s)) for s in range(24)])
# expected: T 44.24 (seed 2, 588 CZ) ... 50.18 (seed 16); the frozen canary QPY on `rec`: 47.96 us, 663 CZ
parts = {'diag': F.diag_gates(dt)}; parts.update({f'hop{l}': F.hop_gates(l, dt) for l in range(F.lat.n_links)})
parts.update({f'plaq{P}': F.plaq_gates(P, dt, True) for P in range(len(F.lat.plaquettes))}); prep = F.prepare(6)
rows = sorted((T(transpile(cq.ir_to_qiskit(prep + sum((parts[k] for k in o), []), n, measure=True), coupling_map=cmap,
                basis_gates=['rz','sx','x','cz'], optimization_level=3, seed_transpiler=2)), o) for o in itertools.permutations(parts))
print(rows[0], rows[-1])   # expected: (35.78, 629, 15, (plaq0, hop2, diag, hop1, hop3, hop0)) ... (51.52, 665, 15, ...)
```

P3 (2 s): longest path of `circuit_to_dag(canary)` with weights cz 68 ns, sx/x 24 ns, rz/barrier/measure 0,
carrying the cz / 1q counts of the predecessor with the latest finish: 455 CZ + 532 pulses = 43.71 us.

P4 (10 s): `transpile(qc, basis_gates=B, coupling_map=cm, optimization_level=3, seed_transpiler=2)` for B in
the four bases of the table and cm in (None, cmap); `tq.depth(filter_function=...)` for the layer counts;
`abs(params[0])/pi` of every rzz for the angle histogram.

P6 (5 s):
```python
import json, math, gzip, numpy as np; from qiskit import qpy; import h0_patch_select as ps, h0_idle_model as im; from skqd import idle
qc = qpy.load(gzip.open('data/hardware/H0_prep/circuits/B0_ref06_k1_rep1.qpy.gz'))[0]
king = json.load(open('data/hardware/device_survey_20260922/ibm_kingston_20260930T2255Z.json'))
mp = {117:82,122:102,123:103,124:96,125:83,136:104,141:107,142:106,143:105,144:117,145:125,146:126}
rc = ps.relabel(ps.circuit_ops(qc), qc.num_qubits, qc.num_clbits, mp); sch = im.schedule(rc, king)
with np.errstate(divide='ignore', invalid='ignore'): fg = im.f_on_record(rc, king)[0]
def f(r, scale=1.0):
    s = dict(sch, per_qubit={q: dict(v, windows_s=[w*scale for w in v['windows_s']]) for q, v in sch['per_qubit'].items()})
    _, tot = idle.idle_budget(s, king, t2_s={q: king['qubits'][str(q)]['T2_s']*r for q in sch['active']})
    return fg*math.exp(-tot['S_T1']-tot['S_T2']), tot['S_T1'], tot['S_T2']
print(f(1.0), f(0.174), f(1.0, 0.5), f(0.174, 0.5))   # 0.056220 / 7.667e-04 / 0.11759 / 0.012165
```

P7 (6 min): the P6 relabelled circuit; `backend_from_record(king, base=FakeKingston(), strict=True)`;
for r != 1 `apply_t2_override(base, {'per_qubit': {q: {'T2_s': T2_q * r}}})` on the 12 winner qubits;
`transpile(rc, backend=base, optimization_level=0, scheduling_method='asap'|'alap', seed_transpiler=7)`;
`AerSimulator.from_backend(base, seed_simulator=11).run(sched, shots=2000)`; decode with `Codec.decode` and
`skqd.skqd.reference_string_test(n_ref, 2000, p_ref, a, 38)` / `clean_fraction_mixture`.  Expected: the table
of P7 (echo ASAP 221 accepted / 116 reference hits, f_clean 0.0797; echo ALAP 309 / 151, 0.1039).

P10: `5 * 38 / 0.00928 = 20474`, `5 * 20 / 0.00488 = 20492` (acceptances from `validation/H0_model.json:
data.C2_pooled_device_clean_count.garbage_acceptance` and the B = 1 exhaustive value 0.488 % of
`reports/H0_replan_planner_analysis_20260922.md` section 6).

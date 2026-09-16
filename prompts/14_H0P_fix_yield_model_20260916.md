# 14 — H0P fix (2026-09-16): the yield model must include the manual's garbage-acceptance term
executor: executor-opus   effort: high
time budget: 3 hours; each run < 30 min   machine: laptop (CPU)

> Written by planner-fable after gate H0P (prompt 13) returned FAIL on 3 of 16 criteria
> (`validation/H0P.json`, commit 701fbcb): the simulated yield of the r = 2 and r = 3 repetition circuits is
> 3.0x, 8.3x and 5.6x the model 0.82 f.  The r = 1 points and every other criterion pass.

## Failure (validation/H0P.json)
- B=0 r=2 (1308 CZ): simulated yield 0.0381 vs 0.82 f = 0.0127, ratio 3.01 (criterion [1/3, 3])
- B=0 r=3 (1910 CZ): 0.0174 vs 0.0021, ratio 8.28
- B=1 r=3 (1944 CZ): 0.0109 vs 0.0020, ratio 5.57
- a pinned re-run reproduced the values exactly (deterministic seeds), so this is structural, not sampling noise

## Diagnosis
Manual Step 4.4 defines the accepted-shot yield as "≈ 0.82 f plus the garbage that decodes as valid".  The gate
scripts implemented only the first term.  The second term is the decoder's acceptance of a uniformly random
string into the target sector, a = 82/4096 = 0.0200 for the 2x2 model over all sectors and, per sector,
0.00928 (B=0) and 0.00488 (B=1) — measured exhaustively in gate E2 and again in H0P ("random-bit-string
acceptance").  A shot that is not clean is close to uniformly random after ~1000 CZ, so the yield is
y = 0.82 f + (1 - f) a, and 0.82 f alone is only valid while f >> a/0.82 = 0.011.  With the full model the six
H0P points sit within 1.30-1.75x (column "ratio vs floor model" of the executor's table), the same factor
seen at r = 1 and in L4_fez (1.39), which is the known conservatism of the 0.82 readout factor.  This is a
correction of the scripts to the manual's definition, not a relaxation: the criterion (ratio within a factor 3)
stays, the model gains the term the manual already names.  The clean-shot rule is unaffected: the shot budget
(`shot_rule`) must keep using the clean yield 0.82 f, because garbage acceptances do not add support.

## Fix
1. `src/skqd/skqd.py`: add `yield_model(f, a, readout_factor=0.82)` returning `readout_factor * f + (1 - f) * a`,
   and `clean_fraction_from_yield(y, a, readout_factor=0.82)` inverting it (f = (y - a) / (readout_factor - a));
   unit tests for both, including the limit a = 0.
2. `scripts/gate_H0P.py`, `scripts/gate_H0.py`, `scripts/laptop_L4_aer_noise.py`: compute a per sector from the
   decoder exhaustively at 2x2 (`Codec` over all 4096 strings, as H0P already does) or from gate E2's random-string
   acceptance at 2x3; compare simulated/measured yields with `yield_model(f, a)`; in gate_H0.py derive the
   measured f with `clean_fraction_from_yield` (H0's 30 % criterion is on f); keep the old 0.82 f column in the
   tables next to the new one so both are visible.  Record a and the model name in every JSON.
3. `scripts/gate_S2D.py`: unchanged for the shot budget (clean yield), but add the floor-model yield as an
   informational column in the report.
4. Re-run: `python scripts/run_gate.py H0P --timeout 1800` (same shots and seeds as prompt 13 so the ratios are
   comparable), `python scripts/run_gate.py L4 --timeout 1800 --backend FakeFez --budget-minutes 20 --pilot-shots
   50 --min-shots 1 --out L4_fez`, and `python scripts/gate_H0.py` on the existing dry-run counts (`--out H0_dryrun`;
   do not re-sample the counts).  Regenerate `reports/H0_prereg_draft.md` (it must state the full model and a).
5. `pytest -q tests`; `python scripts/update_status.py`; commit; `python scripts/run_gate.py H0P --push` on PASS.

## Pass criteria
- validation/H0P.json status PASS with all six yield ratios (full model) inside [1/3, 3]; no other criterion changed
- validation/L4_fez.json and validation/H0_dryrun.json regenerated with the full model; tests pass

## Outputs
src/skqd/skqd.py, the three scripts, validation/{H0P,L4_fez,H0_dryrun}.json, reports/{H0P_heron_preparation,
H0_prereg_draft,L4_fez_aer_noise,H0_dryrun_hardware_2x2}.md, prompts/LOG.md.  Push: yes on PASS.

## Escalation
If any full-model ratio still falls outside [1/3, 3], do not touch the factor 0.82 or the bounds: report the
per-r ratios and stop — the planner then decides whether the readout factor has to be computed from the
calibration (product of per-qubit readout survivals, which S2D already knows) instead of the fixed 0.82.

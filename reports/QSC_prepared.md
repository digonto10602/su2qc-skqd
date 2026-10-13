# QSC_prepared — T5 syntax checks prepared, not run

Status: **prepared** (no PASS claimed).  Generated from `validation/QSC_prepared.json`.

Criterion for the owner's run: every circuit compiles on the syntax checker; the checker's ZZ count equals the frozen count (else the no_opt=True resubmission rule of prompts/26 E1); 0 HQC (syntax checkers are free).

| set | device | program | circuits | jobs | owner command |
|---|---|---|---|---|---|
| QSC_2x2_H2-2SC | H2-2SC | pytket | 30 | 30 | `$V scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x2 --all --out data/hardware/QSC_2x2_H2-2SC` |
| QSC_2x3_H2-2SC | H2-2SC | pytket | 46 | 46 | `$V scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x3 --all --out data/hardware/QSC_2x3_H2-2SC` |
| QSC_2x4_opt3_H2-2SC | H2-2SC | pytket | 17 | 17 | `$V scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x4 --only <the 15 k=1 opt3 ids + CAL_zeros CAL_x0> --out data/hardware/QSC_2x4_opt3_H2-2SC` |
| QSC_2x4_structured_H2-2SC | H2-2SC | pytket | 17 | 17 | `$V scripts/quantinuum_submit.py --syntax-check --device H2-2SC --circuits data/quantinuum/circuits_2x4 --only <the 15 k=1 structured ids + CAL_zeros CAL_x0> --out data/hardware/QSC_2x4_structured_H2-2SC` |
| QSC_2x2_Helios-1SC | Helios-1SC | hugr | 29 | 29 | `$V scripts/quantinuum_submit.py --syntax-check --device Helios-1SC --circuits data/quantinuum/circuits_2x2_helios --program hugr --all --out data/hardware/QSC_2x2_Helios-1SC` |

# Gate QEMU_2x2 — 2x2 native circuits on Quantinuum's local emulator (pytket-quantinuum H2-1LE, pytket-pecos, noiseless state vector; prompts/35 T4)

Status: **PASS**.  Generated from `validation/QEMU_2x2.json`.

What PASS means: "the 28 frozen 2x2 native circuits run on Quantinuum's own local emulator (offline, noiseless state vector) and reproduce their exact distributions; not a device statement".

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| M1 all 28 circuits ran with >= 20 shots; 0 per-state failures (5 sigma, p_s >= 1e-3); fraction outside the exact support 0 on every circuit | {'circuits': 28, 'min_shots': 785, 'failures': 0, 'max_fraction_outside': 0.0, 'max_z': 2.8980183417122816} | 28; >= 20; 0; 0 | PASS |
| M2 versions (pytket, pytket-quantinuum, pytket-pecos, quantum-pecos) and the rate recorded | {'versions': {'pytket': '2.18.4', 'pytket-quantinuum': '0.59.3', 'pytket-pecos': '0.3.3', 'quantum-pecos': '0.8.0.dev8'}, 'seconds_per_shot': 0.6548160552978516} | recorded | PASS |
| M3 hqc == 0 | 0 | 0 | PASS |

| circuit | shots | s/shot | states tested | max z | outside support | reference hits |
|---|---|---|---|---|---|---|
| B0_ref06_k1 | 785 | 0.06398 | 6 | 2.104 | 0.0 | 692 |
| B0_ref06_k2 | 785 | 0.08136 | 16 | 2.507 | 0.0 | 503 |
| B0_ref06_k3 | 785 | 0.05535 | 26 | 2.237 | 0.0 | 234 |
| B0_ref06_k4 | 785 | 0.07288 | 35 | 2.475 | 0.0 | 90 |
| B0_ref17_k1 | 785 | 0.05742 | 6 | 0.9181 | 0.0 | 697 |
| B0_ref17_k2 | 785 | 0.06916 | 18 | 1.556 | 0.0 | 484 |
| B0_ref17_k3 | 785 | 0.06856 | 27 | 2.573 | 0.0 | 232 |
| B0_ref17_k4 | 785 | 0.0551 | 30 | 2.626 | 0.0 | 82 |
| B0_ref21_k1 | 785 | 0.05885 | 6 | 2.24 | 0.0 | 715 |
| B0_ref21_k2 | 785 | 0.02656 | 19 | 2.853 | 0.0 | 445 |
| B0_ref21_k3 | 785 | 0.03076 | 29 | 1.85 | 0.0 | 257 |
| B0_ref21_k4 | 785 | 0.03018 | 36 | 2.138 | 0.0 | 97 |
| B0_ref30_k1 | 785 | 0.03803 | 6 | 1.263 | 0.0 | 702 |
| B0_ref30_k2 | 785 | 0.06564 | 17 | 1.076 | 0.0 | 472 |
| B0_ref30_k3 | 785 | 0.08422 | 24 | 2.156 | 0.0 | 248 |
| B0_ref30_k4 | 785 | 0.06979 | 29 | 2.502 | 0.0 | 66 |
| B0_ref43_k1 | 785 | 0.07698 | 6 | 1.331 | 0.0 | 692 |
| B0_ref43_k2 | 785 | 0.05746 | 19 | 1.485 | 0.0 | 498 |
| B0_ref43_k3 | 785 | 0.06844 | 28 | 1.7 | 0.0 | 243 |
| B0_ref43_k4 | 785 | 0.0588 | 32 | 2.061 | 0.0 | 78 |
| B1_ref07_k1 | 785 | 0.06504 | 7 | 1.904 | 0.0 | 705 |
| B1_ref07_k2 | 785 | 0.07162 | 14 | 2.898 | 0.0 | 504 |
| B1_ref07_k3 | 785 | 0.05776 | 20 | 2.139 | 0.0 | 258 |
| B1_ref07_k4 | 785 | 0.0627 | 20 | 2.147 | 0.0 | 105 |
| B1_ref14_k1 | 785 | 0.0585 | 5 | 1.86 | 0.0 | 696 |
| B1_ref14_k2 | 785 | 0.06952 | 9 | 2.181 | 0.0 | 474 |
| B1_ref14_k3 | 785 | 0.05649 | 12 | 1.728 | 0.0 | 261 |
| B1_ref14_k4 | 785 | 0.06328 | 12 | 2.04 | 0.0 | 108 |

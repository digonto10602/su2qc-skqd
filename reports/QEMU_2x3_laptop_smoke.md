# QEMU_2x3_laptop_smoke

Status: **PASS**.

| check | value | criterion | result |
|---|---|---|---|
| engine set up and ran in dry mode (1 shot per k = 1 f-cell circuit + the 1-shot ladder) | {'engine': 'pytket-quantinuum H2-1LE local emulator (pytket-pecos / quantum-pecos), state-vector, noiseless (CPU)', 'shots_per_circuit': 1, 'ladder': [{'shots': 1, 'seconds': 98.26554131507874, 'seconds_per_shot': 98.26554131507874, 'distinct': 1}], 'error': None} | ran | PASS |
| decode check (P9 of the token, information in dry mode): every observed string in the circuit's sector | [{'name': "P9 every observed string decodes into the circuit's sector", 'value': {'B0_ref25_k1': 0, 'B1_ref57_k1': 0}, 'threshold': '0 outside', 'passed': True, 'gating': False}] | information | PASS |

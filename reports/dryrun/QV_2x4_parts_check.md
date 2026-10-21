# dryrun/QV_2x4_parts_check

| check | value | criterion | result |
|---|---|---|---|
| P1 every run of slots 02..05: bundle sha256, load, instruction count, 28 qubits, q[k] -> c[k], seed rule, prefixes inside the order-kept block; prediction fits; status ready | {'QV_2x4_02': {'runs': 20, 'status': 'ready', 'mismatches': [], 'predicted_s': 1314.0114207275656, 'predicted_s_slow_sampling': 2216.8914207275657, 'fits': True, 'ok': True}, 'QV_2x4_03': {'runs': 30, 'status': 'ready', 'mismatches': [], 'predicted_s': 1850.8673596896137, 'predicted_s_slow_sampling': 2123.8409596896136, 'fits': True, 'ok': True}, 'QV_2x4_04': {'runs': 25, 'status': 'ready', 'mismatches': [], 'predicted_s': 1541.831275909457, 'predicted_s_slow_sampling': 1764.284275909457, 'fits': True, 'ok': True}, 'QV_2x4_05': {'runs': 13, 'status': 'ready', 'mismatches': [], 'predicted_s': 2629.351849542787, 'predicted_s_slow_sampling': 2629.351849542787, 'fits': True, 'ok': True}} | all ok | PASS |
| P2 slots 06..08 are reserve | {'QV_2x4_06': 'reserve (re-runs); no content', 'QV_2x4_07': 'reserve (re-runs); no content', 'QV_2x4_08': 'reserve (re-runs); no content'} | reserve | PASS |

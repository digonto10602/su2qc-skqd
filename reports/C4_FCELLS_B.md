# Campaign 33 token C4_FCELLS_B (class 4): f-cells E6a/b/c, E7(0.05/0.07/0.10/0.15) x O0-O4; faithful S3 redo (IR-L3-RZZ, E8, 32 x 100, seed 11)

**Status: PASS** — `python scripts/campaign33.py --token C4_FCELLS_B`.  Environment: Python 3.12.14, numpy 2.5.3, scipy 1.18.1, Linux-6.4.0-150600.23.125_15.0.29-cray_shasta_c-x86_64-with-glibc2.38, 128 CPUs, commit n/a, 2026-10-13 08:08:10 PDT.  Runtime 1866 s.  Prompt prompts/33_2x3_four_class_perlmutter_campaign.md.

## Engine and resources

Engine Qiskit Aer statevector (double precision); device GPU (requested GPU, available ['CPU', 'GPU']); GPU mode policy; GPUs 1; tasks 1; wall 1866 s; GPU node-hours (shared QOS, G/4 x t) 0.1296; E(p) None (one task: E(p) needs T_1 and T_p from two task counts (not measured)); seconds per shot 0.02444; peak GPU memory 1783 MiB; mean GPU utilisation 52.15 %; versions {'qiskit': '1.4.3', 'qiskit_aer': '0.15.1', 'numpy': '2.5.3', 'scipy': '1.18.1', 'threadpoolctl': '3.7.0', 'python': '3.12.14'}.  Phases (s): preflight_s 14.5, ladder_s 0.0, cells_s 1710.9.

## f-cells

| scenario | variant | shots | f_hit (k=1 pooled) | f_hit 95 % | f_hat_ideal | GO v3 (info) | accepted B0_k1 | f0 B0_k1 |
|---|---|---|---|---|---|---|---|---|
| E6a | NAT-O0 | 2000 | 0.5274 | [0.4909, 0.566] | 0.473 | GO | 0.5887 | 0.4149 |
| E6b | NAT-O0 | 2000 | 0.06772 | [0.05504, 0.08245] | 0.06073 | NO-GO | 0.1212 | 0.02957 |
| E6c | NAT-O0 | 2000 | 0.008208 | [0.004241, 0.01434] | 0.007361 | NO-GO | 0.0275 | 0.00087 |
| E7_0.05 | NAT-O0 | 2000 | 0.1095 | [0.09315, 0.1278] | 0.09815 | AMBIGUOUS | 0.1713 | 0.06138 |
| E7_0.07 | NAT-O0 | 2000 | 0.1594 | [0.1396, 0.1812] | 0.1429 | GO | 0.2225 | 0.08415 |
| E7_0.10 | NAT-O0 | 2000 | 0.1751 | [0.1543, 0.1979] | 0.157 | GO | 0.255 | 0.1176 |
| E7_0.15 | NAT-O0 | 2000 | 0.26 | [0.2345, 0.2875] | 0.2331 | GO | 0.3225 | 0.1719 |
| E6a | NAT-O1 | 2000 | 0.5028 | [0.4671, 0.5405] | 0.4509 | GO | 0.5763 | 0.4148 |
| E6b | NAT-O1 | 2000 | 0.06567 | [0.05319, 0.0802] | 0.05889 | NO-GO | 0.11 | 0.02956 |
| E6c | NAT-O1 | 2000 | 0.006156 | [0.002814, 0.01169] | 0.00552 | NO-GO | 0.01875 | 0.000869 |
| E7_0.05 | NAT-O1 | 2000 | 0.1108 | [0.09441, 0.1293] | 0.09938 | AMBIGUOUS | 0.1913 | 0.06136 |
| E7_0.07 | NAT-O1 | 2000 | 0.1402 | [0.1217, 0.1608] | 0.1258 | GO | 0.2 | 0.08412 |
| E7_0.10 | NAT-O1 | 2000 | 0.1888 | [0.1672, 0.2125] | 0.1693 | GO | 0.2687 | 0.1175 |
| E7_0.15 | NAT-O1 | 2000 | 0.2387 | [0.2144, 0.2652] | 0.2141 | GO | 0.3325 | 0.1719 |
| E6a | NAT-O2 | 2000 | 0.5069 | [0.4711, 0.5448] | 0.4546 | GO | 0.5825 | 0.4151 |
| E6b | NAT-O2 | 2000 | 0.05541 | [0.044, 0.06887] | 0.04969 | NO-GO | 0.115 | 0.02962 |
| E6c | NAT-O2 | 2000 | 0.009576 | [0.005235, 0.01607] | 0.008588 | NO-GO | 0.025 | 0.0008728 |
| E7_0.05 | NAT-O2 | 2000 | 0.1019 | [0.08622, 0.1197] | 0.09141 | AMBIGUOUS | 0.185 | 0.06143 |
| E7_0.07 | NAT-O2 | 2000 | 0.1416 | [0.123, 0.1623] | 0.127 | GO | 0.2288 | 0.08421 |
| E7_0.10 | NAT-O2 | 2000 | 0.1724 | [0.1518, 0.195] | 0.1546 | GO | 0.2387 | 0.1177 |
| E7_0.15 | NAT-O2 | 2000 | 0.2442 | [0.2195, 0.2709] | 0.219 | GO | 0.32 | 0.1721 |
| E6a | NAT-O3 | 2000 | 0.4748 | [0.4401, 0.5114] | 0.4257 | GO | 0.5887 | 0.415 |
| E6b | NAT-O3 | 2000 | 0.06499 | [0.05258, 0.07945] | 0.05828 | NO-GO | 0.1125 | 0.0296 |
| E6c | NAT-O3 | 2000 | 0.003419 | [0.00111, 0.007981] | 0.003066 | NO-GO | 0.0275 | 0.0008714 |
| E7_0.05 | NAT-O3 | 2000 | 0.1211 | [0.1039, 0.1403] | 0.1086 | GO | 0.1888 | 0.06141 |
| E7_0.07 | NAT-O3 | 2000 | 0.1307 | [0.1128, 0.1506] | 0.1172 | GO | 0.1913 | 0.08418 |
| E7_0.10 | NAT-O3 | 2000 | 0.184 | [0.1627, 0.2074] | 0.165 | GO | 0.255 | 0.1176 |
| E7_0.15 | NAT-O3 | 2000 | 0.2216 | [0.1982, 0.2471] | 0.1988 | GO | 0.31 | 0.172 |
| E6a | NAT-O4 | 2000 | 0.5021 | [0.4665, 0.5398] | 0.4503 | GO | 0.5613 | 0.415 |
| E6b | NAT-O4 | 2000 | 0.0602 | [0.04828, 0.07417] | 0.05398 | NO-GO | 0.1237 | 0.0296 |
| E6c | NAT-O4 | 2000 | 0.009576 | [0.005235, 0.01607] | 0.008588 | NO-GO | 0.0275 | 0.0008714 |
| E7_0.05 | NAT-O4 | 2000 | 0.1033 | [0.08748, 0.1212] | 0.09263 | AMBIGUOUS | 0.1638 | 0.06141 |
| E7_0.07 | NAT-O4 | 2000 | 0.1313 | [0.1134, 0.1513] | 0.1178 | GO | 0.1938 | 0.08418 |
| E7_0.10 | NAT-O4 | 2000 | 0.171 | [0.1505, 0.1936] | 0.1534 | GO | 0.25 | 0.1176 |
| E7_0.15 | NAT-O4 | 2000 | 0.2442 | [0.2195, 0.2709] | 0.219 | GO | 0.3287 | 0.172 |

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| P10 each variant's f_hit vs the O0 cell (Delta, sigma, verdict reported; an exact optimisation may move f) | 28 | fields present | PASS |
| P12 faithful S3 redo: accepted count inside the binomial 95 % band of S3's 695 / 3200 | 656 | in (650, 741) at 3200 shots (yield 0.2172) | PASS |
| S1 the run happened on the requested device (GPU under the CI) | GPU (available ['CPU', 'GPU']) | GPU | PASS |
| S2 wall time inside the walltime budget | 1866 s | <= min(walltime 3600 s, 3600 s) and <= 1.1 x budget + 120 s | PASS |
| S3 telemetry and run block present (policy fields non-null on the CI) | {'engine': True, 'device': True, 'wall_seconds': True, 'seconds_per_shot': True, 'gpus': True} | every policy field non-null on the CI; present on the laptop | PASS |
| S4 every seed and every chunk recorded | True | true | PASS |
| S5 no out-of-memory retry left unrecorded | 0 recorded | each OOM split recorded | PASS |
| S6 shots >= the token's minimum | full | no reduction below the minimum | PASS |

Every number above is computed by `scripts/campaign33.py` and stored in `validation/C4_FCELLS_B.json`.

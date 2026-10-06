# Gate H0_ddrep_dryrun -- XY4 replication and the T1-collapse mechanism, dry run (local Aer on the FakeKingston snapshot; a path check, not a prediction)

**Status: PASS** -- `scripts/gate_H0_ddrep.py --stage assemble --counts data/hardware/H0_ddrep_dryrun/counts --dry-run --out H0_ddrep_dryrun`.
Runtime 14 s.  Every number below is computed by the script from the raw counts and from `data/hardware/H0_ddrep_prep/prereg_cb40a250fb24387d.json` and is
stored in `validation/H0_ddrep_dryrun.json`.  Prompt in force: `prompts/32_2x2_dd_replication_and_T1_mechanism.md (part A)`; owner decision `data/owner_decision_20261006_A_then_B.md`.

## 0. What PASS means

preregistered, measured, verified, consistent; there is no criterion on R1, R2, C1, the classes or the mechanism reading. Aer cannot show a DD gain: its relaxation on a delay is Markovian, so the dry-run ratios sit near the null values exp(-S_DD) and are path checks, not predictions (P10 of prompts/24); the train pubs on Aer sit at the readout floor plus the snapshot's incoherent x error (no coherent pulse error).

## 1. Preregistration

`data/hardware/H0_ddrep_prep/prereg_cb40a250fb24387d.json`, written 2026-10-06 06:29:26 UTC at commit `4f0e87b` on the patch record `data/hardware/H0_ddrep_prep/calibration_20261006T0501Z.json`
(fingerprint `cb40a250fb24387d2caed751bc9cb8c2b15378a67471fc93da873e057d6ee6e4`).  Patch [59, 71, 72, 73, 74, 75, 79, 91, 92, 93, 94, 95] (reproduced: True); hot qubits of M4
[91, 95]; 20 pubs x 6000 shots; execution estimate 34.04 s.

## 2. Live block

| item | value |
|---|---|
| job id(s) / status | ['d2c78230-d377-4e47-b465-bb6ffb198268'] / ['DONE'] |
| usage (s) | 0.0 |
| preflight estimate (s) | None |
| fingerprint at prereg / submission / retrieval | `cb40a250fb24387d` / `n/a` / `n/a` |
| prereg match at submission / retrieval | None / None |
| retrieval diff | None |
| prereg commit time / submitted | None (added in None, None) / None |
| account usage before / after | 102 s (498 left) / None s (None left) |
| sampler options | {'default_shots': 6000, 'dynamical_decoupling': {'enable': False}, 'twirling': {'enable_gates': False, 'enable_measure': False}, 'error_mitigation': 'none: SamplerV2 returns raw bit strings; no resilience level, no readout mitigation of expectation values (prompts/07 step 2)'} |

## 3. The seven cells

| cell | accepted | ref hits | garbage exp. | excess X | f_pool [95 %] | R = X_i/X_0 | R 95 % | R bootstrap 95 % | null e^-S_DD | class | pulses (2 circuits) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T0 | 2474 | 1724 | 2.93 | 1721.1 | 0.1974 [0.1880, 0.2071] | 1.000 | n/a | n/a | 1.000 | - | 0 |
| T1 | 1852 | 1268 | 2.93 | 1265.1 | 0.1451 [0.1370, 0.1535] | 0.735 | [0.684, 0.790] | [0.683, 0.789] | 0.841 | INTERMEDIATE | 1724 |
| T3 | 2129 | 1431 | 2.93 | 1428.1 | 0.1638 [0.1552, 0.1727] | 0.830 | [0.774, 0.890] | [0.773, 0.890] | 0.954 | INTERMEDIATE | 488 |
| M1 | 1933 | 1285 | 2.93 | 1282.1 | 0.1470 [0.1389, 0.1555] | 0.745 | [0.693, 0.801] | [0.692, 0.801] | 0.841 | INTERMEDIATE | 1724 |
| M2 | 1997 | 1355 | 2.93 | 1352.1 | 0.1551 [0.1467, 0.1637] | 0.786 | [0.732, 0.844] | [0.733, 0.842] | 0.922 | INTERMEDIATE | 778 |
| M3 | 2093 | 1399 | 2.93 | 1396.1 | 0.1601 [0.1516, 0.1689] | 0.811 | [0.756, 0.870] | [0.755, 0.871] | 0.922 | INTERMEDIATE | 778 |
| M4 | 2099 | 1398 | 2.93 | 1395.1 | 0.1600 [0.1515, 0.1688] | 0.811 | [0.755, 0.870] | [0.755, 0.868] | 0.880 | INTERMEDIATE | 1228 |

Per circuit:

| cell | circuit | accepted | ref hits | f reference [95 %] | f mixture [68 %] | C6 dev (info) | pulses |
|---|---|---|---|---|---|---|---|
| T0 | B0_ref06_k1 | 1327 | 868 | 0.1994 [0.1861, 0.2134] | 0.2018 [0.1982, 0.2053] | 0.012 | 0 |
| T0 | B1_ref07_k1 | 1147 | 856 | 0.1954 [0.1822, 0.2092] | 0.1963 [0.1933, 0.1992] | 0.005 | 0 |
| T1 | B0_ref06_k1 | 970 | 605 | 0.1389 [0.1278, 0.1507] | 0.1408 [0.1376, 0.1440] | 0.014 | 862 |
| T1 | B1_ref07_k1 | 882 | 663 | 0.1512 [0.1397, 0.1635] | 0.1510 [0.1484, 0.1534] | 0.002 | 862 |
| T3 | B0_ref06_k1 | 1125 | 703 | 0.1614 [0.1495, 0.1741] | 0.1650 [0.1615, 0.1684] | 0.022 | 244 |
| T3 | B1_ref07_k1 | 1004 | 728 | 0.1661 [0.1540, 0.1789] | 0.1678 [0.1649, 0.1706] | 0.010 | 244 |
| M1 | B0_ref06_k1 | 1020 | 624 | 0.1433 [0.1320, 0.1552] | 0.1443 [0.1410, 0.1476] | 0.008 | 862 |
| M1 | B1_ref07_k1 | 913 | 661 | 0.1508 [0.1393, 0.1630] | 0.1537 [0.1510, 0.1564] | 0.020 | 862 |
| M2 | B0_ref06_k1 | 1045 | 655 | 0.1504 [0.1388, 0.1626] | 0.1506 [0.1473, 0.1539] | 0.001 | 388 |
| M2 | B1_ref07_k1 | 952 | 700 | 0.1597 [0.1478, 0.1723] | 0.1610 [0.1582, 0.1637] | 0.008 | 390 |
| M3 | B0_ref06_k1 | 1138 | 711 | 0.1633 [0.1512, 0.1760] | 0.1677 [0.1642, 0.1711] | 0.027 | 388 |
| M3 | B1_ref07_k1 | 955 | 688 | 0.1570 [0.1452, 0.1694] | 0.1611 [0.1583, 0.1638] | 0.026 | 390 |
| M4 | B0_ref06_k1 | 1109 | 657 | 0.1508 [0.1393, 0.1631] | 0.1577 [0.1542, 0.1612] | 0.046 | 614 |
| M4 | B1_ref07_k1 | 990 | 741 | 0.1691 [0.1569, 0.1820] | 0.1699 [0.1671, 0.1725] | 0.005 | 614 |

Classes per circuit cell on R_i = X_i / X_0 (gate_H0_ddtest.ratio_interval, Poisson 95 %): COLLAPSED iff R_hi95 < 0.25; INTACT iff R_lo95 > 1; INTERMEDIATE otherwise.  If X_i <= 0 (no excess reference hits) the interval is [0, U_i / L_0] with U_i = the Garwood 97.5 % upper limit of the cell's pooled reference count minus its garbage expectation and L_0 = the Garwood 2.5 % lower limit of T0's count minus T0's garbage expectation (executor addition fixed before data: the ratio_interval of gate_H0_ddtest is undefined there).

## 4. Replication verdicts (P6)

- R1 gain replicated (T3 qualifies under the H0_ddtest rule): **False**.
- R2 magnitude consistent: **False** -- ln R_new -0.1866 vs ln R_old 1.0364, |difference|
  1.2230 against the tolerance 0.1408.
- C1 collapse replicated (T1 COLLAPSED): **False**.
- Signed bar on T3 (information): on f_hit **GO**; on f_hat_ideal = f_hit / r_nc (1.1151)
  **GO** (f_hat_ideal 0.1469, 95 % [0.1373, 0.1570]).

## 5. Mechanism (P5)

| cell | observed class | H_A predicts (match) | H_B predicts (match) | H_D predicts (match) |
|---|---|---|---|---|
| T1 | INTERMEDIATE | COLLAPSED (no) | COLLAPSED (no) | COLLAPSED (no) |
| M1 | INTERMEDIATE | INTACT (no) | COLLAPSED (no) | COLLAPSED (no) |
| M2 | INTERMEDIATE | not INTACT, and R_M2 < R_M3 (yes) | INTACT (no) | INTACT (no) |
| M3 | INTERMEDIATE | INTACT (no) | INTACT (no) | INTACT (no) |
| M4 | INTERMEDIATE | not INTACT (yes) | not INTACT (yes) | INTACT (no) |

Reading (preregistered rule): **no single hypothesis**.  Cells matched per hypothesis: H_A 2/5, H_B 1/5, H_D 0/5.
M3 vs M2 (first-order compensation on the runtime timing): ln(R_M3/R_M2) = 0.0320 +- 0.0382,
z = 0.84 (compensation matters: False).  M3 vs T3 (information):
ln = -0.0227 +- 0.0376.

## 6. Pulse trains (P4)

| qubit | P1 XX-8 | P1 XX-32 | P1 XX-128 | P1 XpXm-128 | epsilon (rad) [68 %] | c per pulse [68 %] | x_error record | c / x_error |
|---|---|---|---|---|---|---|---|---|
| 59 | 0.0037 | 0.0071 | 0.0207 | 0.0216 | 0.0000 [0.0000, 0.0007] | 1.49e-04 [1.3e-04, 1.7e-04] | 1.88e-04 | 0.79 |
| 71 | 0.0024 | 0.0030 | 0.0111 | 0.0108 | 0.0003 [0.0000, 0.0008] | 7.04e-05 [5.3e-05, 8.7e-05] | 1.48e-04 | 0.48 |
| 72 | -0.0026 | 0.0019 | 0.0056 | 0.0106 | 0.0000 [0.0000, 0.0000] | 1.10e-04 [6.9e-05, 1.5e-04] | 1.38e-04 | 0.80 |
| 73 | 0.0071 | 0.0095 | 0.0398 | 0.0375 | 0.0007 [0.0000, 0.0013] | 2.53e-04 [2.1e-04, 2.9e-04] | 2.12e-04 | 1.20 |
| 74 | 0.0020 | 0.0118 | 0.0430 | 0.0421 | 0.0005 [0.0000, 0.0011] | 3.34e-04 [3.1e-04, 3.6e-04] | 2.37e-04 | 1.41 |
| 75 | -0.0003 | 0.0050 | 0.0076 | 0.0088 | 0.0000 [0.0000, 0.0006] | 7.58e-05 [5.7e-05, 9.6e-05] | 1.46e-04 | 0.52 |
| 79 | -0.0015 | 0.0017 | 0.0109 | 0.0080 | 0.0008 [0.0003, 0.0011] | 7.92e-05 [6.2e-05, 9.6e-05] | 2.38e-04 | 0.33 |
| 91 | -0.0007 | 0.0037 | 0.0303 | 0.0301 | 0.0001 [0.0000, 0.0010] | 2.57e-04 [2.3e-04, 2.8e-04] | 2.19e-04 | 1.17 |
| 92 | 0.0042 | 0.0186 | 0.0405 | 0.0358 | 0.0011 [0.0000, 0.0019] | 2.63e-04 [1.8e-04, 3.4e-04] | 3.33e-04 | 0.79 |
| 93 | 0.0007 | 0.0064 | 0.0221 | 0.0266 | 0.0000 [0.0000, 0.0000] | 2.16e-04 [2.0e-04, 2.4e-04] | 1.94e-04 | 1.12 |
| 94 | 0.0056 | 0.0141 | 0.0258 | 0.0331 | 0.0000 [0.0000, 0.0000] | 2.29e-04 [2.0e-04, 2.6e-04] | 1.72e-04 | 1.33 |
| 95 | 0.0005 | 0.0054 | 0.0332 | 0.0303 | 0.0008 [0.0000, 0.0012] | 2.48e-04 [2.3e-04, 2.7e-04] | 1.51e-04 | 1.64 |

Readings: H_A pattern False (epsilon >= 0.01 on 0 qubits, XX-128 - XpXm-128 > 0.05 on
0); H_B pattern True; H_D pattern False (c > 3 x_error on
[], hot ['91', '95']).  Aer has no coherent pulse error: the dry-run trains sit at the readout floor plus the snapshot's incoherent x error; the epsilon fit reads noise

Rule: Executor operationalisation of P4's table (fixed before data): per qubit P1 = readout-corrected P(1) (p - (1 - P00)) / (P00 + P11 - 1) with the job's own confusion diagonal; c_q = (P1(XpXm-128) - P1(XX-8)) / 120; floor_n = P1(XX-8) + (n - 8) c_q; epsilon_q = argmin over [0, pi/8] (grid 1e-4 rad) of sum_{n in 8, 32, 128} (P1(XX-n) - floor_n - sin^2(n epsilon / 2))^2; 68 % intervals by a parametric bootstrap (2000 draws, seed 32: binomial train and confusion counts).  H_A pattern: epsilon_q >= 0.01 on >= 6 of 12 qubits AND P1(XX-128) - P1(XpXm-128) > 0.05 on >= 6 of 12 qubits.  H_B pattern ('all four at the floor'): on every qubit P1(XX-128) - P1(XpXm-128) <= 0.05 and P1(XX-32) - floor_32 <= 0.05.  H_D pattern: c_q > 3 x_error_q on at least one of the two hot qubits and c_q <= 3 x_error_q on every other qubit (x_error of the preregistered patch record).

## 7. The 2x3 IBM NO-GO (K0, recorded with this gate)

NO-GO for 2x3 on IBM Heron (ibm_kingston) on the K0 analysis: a model verdict, not a measurement: routed CZ 5659, ALAP 410.3 us, f_gates on the layout 6.069e-06,
f_idle_aware 1.057e-16 (echo) / 3.732e-38 (T2*), garbage reference hits
0.0954 per circuit at 100000 shots
(`reports/K0_2x3_ibm_heron_nogo.md`).  Every number above is computed from the calibration record named; none is a measurement on the device.  Option B (prompts/32) is the one measurement this verdict allows: the K1 pilot as an upper limit.

## 8. Readout

Smallest confusion diagonal 0.8527; preregistered live expectation min
0.9565 (qubit 72).

## 9. Honest limits

- One job, one patch, one calibration content; drift between submission and retrieval is reported, not corrected.
- The classes are preregistered thresholds on Poisson intervals, not fits; the reading rule names a hypothesis class, not a
  microscopic cause.
- The null ratios e^-S_DD assume the record's x error for every inserted pulse, and the record's x error is aliased to sx.
- The train fit assumes a coherent over-rotation epsilon plus an incoherent per-pulse cost on a floor anchored at XX-8; other
  coherent errors (axis tilt, detuning during the train) enter epsilon.
- Two k = 1 circuits are not a family-level statement.

## 10. Criteria

| check | value | criterion | result |
|---|---|---|---|
| D1 preregistration committed before the submission | n/a (dry run) | device run only | PASS |
| D2 one job DONE, usage <= 45 s, estimate <= 36 s, 20 x 6000 counts, DD/twirling off, B reserve | n/a (dry run) | device run only | PASS |
| D3 readout (dry run: agreement with the snapshot's readout model, prompts/21a; the device criterion >= 0.9 is evaluated only on device counts) | 12/12 qubits with |z| <= 3; min diagonal 0.8527 (information); live expectation min 0.9565 (qubit 72) | all 12 within 3 binomial sigma; live expectation >= 0.9 | PASS |
| D4 decoder round trip over every accepted string of the 14 coarse pubs | 0 mismatches over 56 strings | 0 | PASS |
| D5 circuits: 14/14 coarse circuits pass dd_checks (i)-(v) and dd_exactness; T0/T1/T3 byte-identical to H0_ddtest when patch_reproduced; the P3 identities hold; the train pubs' op lists are the declared trains; kingston basis | 14/14 circuits; reuse ok True (patch reproduced True); identities ok True; trains ok True; max |d| 5.7e-13 | all hold | PASS |
| D6 dry-run gate PASS on the day's build | n/a (this is the dry run) | device run only | PASS |
| D7 replication, mechanism, trains and k0_2x3_nogo complete; classes, R1, R2, C1 and the reading recomputed from the recorded intervals; k0 fields equal validation/K0_2x3_2x4.json's | missing []; recomputed equal True; k0 mismatches [] | complete, equal, none | PASS |
| D8 pytest -q tests and scripts/check_package.py | n/a (--skip-tests) | all pass | PASS |

# Gate QN_2x4 — 2x4 native circuits under the Quantinuum noise models: analytic fault-free fraction and gate-only f (prompts/35 T3, R3; nothing sampled)

Status: **PASS**.  Generated from `validation/QN_2x4.json`.

What PASS means: "the analytic fault-free fraction f0 of every built 2x4 native circuit under the 11 Quantinuum scenarios and the gate-only f per device are tabulated; nothing is sampled because at 2x4 every scenario gives f ~ 0 (R3: (1 - eps2)^n_zz with n_zz ~ 7e4)".

## Criteria

| check | value | criterion | result |
|---|---|---|---|
| A1 the table is complete over the built circuits x 11 scenarios x 4 devices | {'circuits': 79, 'scenarios': 11, 'devices': 4, 'max_f0_any_scenario': 0.35090942140987547, 'E1_log10_f0_range': [-26.121648927069632, -24.387760067112136]} | complete | PASS |
| A2 sampled_shots == 0 and the reason (R3) in what_pass_means | {'sampled_shots': 0} | 0 | PASS |

## log10 f0 per scenario (min / max over the built circuits)

| scenario | min | max |
|---|---|---|
| E1 | -26.12 | -24.39 |
| E2 | -25.09 | -23.31 |
| E3 | -42.63 | -38.77 |
| E4 | -25.04 | -23.44 |
| E5a | -27.32 | -25.56 |
| E5b | -28.75 | -26.96 |
| E5c | -36.65 | -34.67 |
| E6a | -13.06 | -12.19 |
| E6b | -52.26 | -48.79 |
| E6c | -104.6 | -97.66 |
| E7_0.10_lat | -0.7312 | -0.4548 |

## Gate-only f per device (data.analytic.devices: the device table formula on the frozen counts)

| device | f mean | eps2 for mean f 0.1 | eps2 for worst f 0.05 |
|---|---|---|---|
| H2-2 | 4.184e-29 | n/a | n/a |
| Helios-1 | 4.873e-28 | n/a | n/a |
| H1-1 | 1.470e-32 | n/a | n/a |
| H2-1 | 1.116e-36 | n/a | n/a |

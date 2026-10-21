# noise/ — C5 + C6: compressed circuits under published device noise models

Owner decisions C5 and C6 (`../notes/008-owner-decisions-C1-C6.md`, signed 2026-10-21): device information and noise
models from **internet-published data only** (no backend, no API call, no live calibration, no fake-backend snapshot);
noiseless accuracy and noisy behaviour of the compressed families; results kept separate and easily callable.

Nothing here is used by the package or its gates.  The compressed families are not substituted anywhere (notes/008).

## Layout

| path | what |
|---|---|
| `data/device_specs_{quantinuum,ibm,ionq}.json` | every published number with URL, access date, source date and qualification; `model_inputs` = the subset the models use |
| `src/noise_models.py` | the device models (Pauli channels), native compilation, heavy-hex map, analytic clean fraction |
| `src/traj_sparse.py` | the trajectory engine: the package's sparse simulator (`skqd.sparse_sim`) on the IR gate list with sampled Pauli faults |
| `src/circuits.py` | circuit access: v1 built with genie's builders (cache in `.cache/`, gitignored), genie's frozen families through `families.get_family_ir` (notes/009), the package's frozen circuits |
| `src/targets.py` | exact targets from the package (`krylov.coarse_states`, `CodewordEmbedding`, `validation/E3.json` dt) |
| `src/results.py` | **the loader** (below) |
| `scripts/` | `accuracy_sv.py` + `accuracy_queue.sh` (test 1), `noisy_run.py` + `noisy_queue.py` (test 2), `analytic_f.py`, `validate_engine.py`, `aggregate.py`, report generators |
| `data/results/<lattice>/<family>/<device>/<test>.json` | results; `data/results/index.json` lists them |
| `data/checks/` | supporting checks (native compilation exact, v1 build = genie's frozen files) |
| `reports/001-quantinuum-device-info.md`, `002-noise-models.md`, `003-noise-results.md` | the reports |

## Names

- Families (owner's naming): `compressed_circuit_llm_2x4_classA`, `compressed_circuit_llm_2x4_classB` (v1 = the
  reviewer-verified it5), later `_v2` and `compressed_circuit_llm_2x3_class[A,B]`; `frozen` = the package's tested
  circuits (2x3: `data/quantinuum/circuits_2x3`; 2x4: `data/quantinuum/circuits_2x4`, analytic only).
- Devices: `quantinuum_h2_2`, `quantinuum_helios_1`, `ionq_forte`, `ionq_tempo` (target specification),
  `ibm_heron_r2_fez`, `ibm_heron_r3_boston`; variants `quantinuum_*_nomem` (memory channel off) and
  `ionq_*_noidle` (idle relaxation off); `noiseless` for test 1.
- Tests: `accuracy` (noiseless, device `noiseless`), `analytic_f`, `noise_behaviour`, `skqd_energy`, `engine_validation`.

## Loader

```python
import sys; sys.path.insert(0, "2x4_compression_using_ai_v1/noise/src")
import results
results.list_available()                                   # [(lattice, family, device, test), ...]
d  = results.load("2x4", "compressed_circuit_llm_2x4_classB", "quantinuum_h2_2", "noise_behaviour")  # dict
df = results.table("noise_behaviour", "2x4")               # pandas DataFrame, one row per (family, device, circuit)
sm = results.summary("analytic_f", "2x3")                  # one row per (family, device): the JSON summary blocks
results.index()                                            # data/results/index.json
```

Every result JSON carries `provenance` (git commit, machine, command, UTC time); noisy and analytic ones also carry
`noise_spec_file`, `noise_spec_sha256` and the `noise_model_params` used; runs carry their seeds and engine.

## Reproduce

```bash
cd 2x4_compression_using_ai_v1/noise
python scripts/build_v1.py                         # 150 v1 circuits with genie's builders (~15 min), cache in .cache/
python scripts/check_v1_vs_frozen.py               # equals genie's frozen files bit for bit
nohup nice -n 10 bash scripts/accuracy_queue.sh > logs/accuracy_queue.log 2>&1 &   # test 1 (~1 day at 2x4)
python scripts/analytic_f.py 2x3 frozen            # and 2x4 <family>, 2x4 frozen <devices...>
python scripts/validate_engine.py 2x3 frozen quantinuum_h2_2 B0_ref117_k1 5 7
nohup nice -n 10 python scripts/noisy_queue.py --workers 3 > logs/noisy_queue.log 2>&1 &   # test 2
python scripts/aggregate.py                        # per-family files, skqd_energy, index.json
python scripts/report_001_quantinuum.py; python scripts/report_002_models.py; python scripts/report_003_results.py
```

Environment: the `coding` conda env (qiskit 2.5.2, qiskit-aer 0.17.2, numpy, scipy, pandas), used read-only; nothing
installed.  CPU only; no CI, QPU, backend or API key.

#!/usr/bin/env python3
"""
Entry point for `python scripts/run_gate.py S3` (and therefore for the Perlmutter CI, which runs
exactly that with no further arguments: jobs/gate.sbatch, `srun python scripts/run_gate.py
$CI_GATE`).

`run_gate.py` resolves a gate token G to `scripts/gate_G.py` and then reads `validation/G.json`,
so the S3 job needs a script with this name and has to write `validation/S3.json`.  All the work
is in `scripts/s3_device_model.py`; this file only forwards the command line to it, so a run by
hand and a run through the gate runner are the same code path.

  python scripts/run_gate.py S3                      # under the CI: the reduced-size GPU
                                                     # throughput CALIBRATION (see below)
  python scripts/run_gate.py S3 --lattice 3 --sector 0 --shots-per-sector 200000 --tag B0_r1

NOTE ON WHAT A CI RUN MEANS.  Under the CI (CI_GATE / SLURM_JOB_ID) `s3_device_model.py` switches
itself to `--calibration`: the criteria it evaluates are about COMPUTE THROUGHPUT at 20 qubits
(device, timing ladder, memory fit, wall time), and the S3 physics criterion (recall >= 0.9 with
the production budget) is NOT evaluated.  A PASS of that run therefore means "the calibration
completed as specified", never "gate S3 passed"; `validation/S3.json` says so in its title, its
`data.run_kind` and its `data.gate_S3_criterion`, and `scripts/update_status.py` marks the row in
`validation/gates.md` accordingly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from s3_device_model import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

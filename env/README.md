# Software environments (exported 2026-10-31 from the laptop)

These files recreate the Python, LaTeX and Lean environments this project used on the laptop. They were
exported with `conda env export --no-builds` and `pip freeze`. Exact build strings are omitted, so
conda may pick slightly different builds on the desktop.

| File | What it is | Recreate with |
|---|---|---|
| `coding.yml` | Main env: the `skqd` package, qiskit 2.5.2 / qiskit-aer 0.17.2 (pinned), CUDA-Q 0.15.1, cuQuantum | `mamba env create -f env/coding.yml` |
| `latex.yml` | Tectonic 0.17, which builds the paper and talk PDFs | `mamba env create -f env/latex.yml` |
| `su2-quantinuum.yml` | Older pytket 1.23 / qiskit 0.45 env, kept for reference | `mamba env create -f env/su2-quantinuum.yml` |
| `su2qc-jepa.yml` | Env holding `qnexus` 0.51.2, the Quantinuum Nexus client | `mamba env create -f env/su2qc-jepa.yml` |
| `su2qc-quantinuum-venv-requirements.txt` | The venv `~/.local/share/su2qc-quantinuum/venv`, used for the H2-2SC syntax-checker runs. It is built **on top of** `coding` with `--system-site-packages`. | `~/anaconda3/envs/coding/bin/python -m venv --system-site-packages ~/.local/share/su2qc-quantinuum/venv && ~/.local/share/su2qc-quantinuum/venv/bin/pip install -r env/su2qc-quantinuum-venv-requirements.txt` |
| `su2qc-qiskit143-venv-requirements.txt` | Venv `~/.local/share/su2qc-qiskit143/venv`, the local twin of the Perlmutter CI stack (qiskit 1.4.3). Isolated: no system site-packages. | `~/anaconda3/envs/coding/bin/python -m venv ~/.local/share/su2qc-qiskit143/venv && ~/.local/share/su2qc-qiskit143/venv/bin/pip install -r env/su2qc-qiskit143-venv-requirements.txt` |
| `su2qc-pecos-venv-requirements.txt` | Venv `~/.local/share/su2qc-pecos/venv` (PECOS, the Quantinuum-style noisy emulator). Isolated. | same pattern, with `su2qc-pecos` |
| `su2qc-selene-venv-requirements.txt` | Venv `~/.local/share/su2qc-selene/venv` (Selene emulator). Isolated. | same pattern, with `su2qc-selene` |
| `graphify-venv-requirements.txt` | The isolated graphify 0.9.53 venv at `~/.local/share/graphify/venv`, which builds the code map | `python3 -m venv ~/.local/share/graphify/venv && ~/.local/share/graphify/venv/bin/pip install -r env/graphify-venv-requirements.txt` |

**Lean 4.** Install `elan` (https://github.com/leanprover/elan). The toolchain is pinned in
`2x4_compression_using_ai_v1/lean/lean-toolchain` (`leanprover/lean4:v4.35.0`). Run `lake build` in that
folder to rebuild `.lake/`, which takes about 7.3 GB. Alternatively, copy `.lake/` from the USB backup.

**GPU on the desktop (RTX 3070).** The laptop's GTX 1060 has compute capability 6.1, so the CUDA-Q
`nvidia` target and GPU Aer never ran there. On the desktop, check `nvidia-smi` first, then follow
`RUNBOOK.md` ("Engine and HPC policy"). Note that qiskit-aer-gpu 0.15.1 is incompatible with
qiskit 2.5.2: that is why the Perlmutter CI path uses qiskit 1.4.3.

**Credentials are never stored in this repo.** For Quantinuum Nexus, run `qnx login` from the
`su2qc-jepa` env or the venv above. For IBM, save the account with `QiskitRuntimeService.save_account(...)`
in the `coding` env.

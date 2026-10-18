"""prompts/33f coordinator check: is the step CPU set recorded before qiskit_aer pins the main thread?"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
from skqd.hpc import record_step_cpus, step_cpu_count, cpu_affinity  # noqa: E402

record_step_cpus()
print("env OMP_PROC_BIND", os.environ.get("OMP_PROC_BIND"), "OMP_PLACES", os.environ.get("OMP_PLACES"))
print("before aer: start-record", step_cpu_count(), "now", cpu_affinity())
import qiskit_aer  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402

AerSimulator().available_devices()
print("after aer (", qiskit_aer.__version__, "): start-record", step_cpu_count(), "now", cpu_affinity())

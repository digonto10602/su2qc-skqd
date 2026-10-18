"""What types does NoiseModel.to_dict(serializable=False) contain (aer 0.15.1), and does from_dict round-trip it?"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
import numpy as np  # noqa: E402
from qiskit_aer.noise import NoiseModel  # noqa: E402

from skqd.campaign33 import noise as N  # noqa: E402
from skqd.campaign33 import tokens_run as TR  # noqa: E402

rec = TR.load_record()
spec = N.ibm_spec(rec, "I-ECHO", "kraus", "echo")
d = spec.noise_model.to_dict(serializable=False)
types = Counter()


def walk(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            walk(v, path + "/" + str(k))
    elif isinstance(x, (list, tuple)):
        types[(type(x).__name__, path.split("/")[-1])] += 1
        for v in x:
            walk(v, path)
    else:
        types[(type(x).__name__, path.split("/")[-1], str(getattr(x, "dtype", "")))] += 1


walk(d)
for k, v in types.most_common(40):
    print(k, v)
back = NoiseModel.from_dict(d)
print("round trip of the non-serializable dict equal:", back == spec.noise_model)

import warnings  # noqa: E402
from qiskit.quantum_info import SuperOp  # noqa: E402
print("basis", sorted(back.basis_gates) == sorted(spec.noise_model.basis_gates), sorted(back.basis_gates)[:10],
      sorted(spec.noise_model.basis_gates)[:10])
ea, eb = N._local_errors(spec.noise_model), N._local_errors(back)
print("local error keys equal:", set(ea) == set(eb), len(ea), len(eb))
worst = 0.0
for k in ea:
    a = SuperOp(ea[k].to_quantumchannel()).data
    b = SuperOp(eb[k].to_quantumchannel()).data
    worst = max(worst, float(np.max(np.abs(a - b))))
print("max superop diff over local errors:", worst)
ra, rb = spec.noise_model._local_readout_errors, back._local_readout_errors
print("readout keys equal:", set(ra) == set(rb),
      max(float(np.max(np.abs(np.asarray(ra[q].probabilities) - np.asarray(rb[q].probabilities)))) for q in ra))
print("default errors:", spec.noise_model._default_quantum_errors.keys(), back._default_quantum_errors.keys())
print("noise_instructions", sorted(spec.noise_model.noise_instructions) == sorted(back.noise_instructions))
print("custom passes", len(spec.noise_model._custom_noise_passes), len(back._custom_noise_passes))

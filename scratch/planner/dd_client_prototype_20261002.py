# Planner prototype (2026-10-02, 0 QPU s): client-side DD insertion into the committed pilot circuit
# data/hardware/H0_kpilot_prep/circuits/B0_ref06_k1.qpy.gz on the record calibration_20261002T1627Z.json.
# Produces the numbers of reports/ibm_decoherence_literature_20261002.md section 6. Not a gate; not production code.
# Run: python scratch/planner/dd_client_prototype_20261002.py  (about 1 min on the i7-8750H)
import json, os, sys, gzip, math, time
from collections import Counter
import numpy as np
ROOT="/home/digimonk/Projects/su2qc-skqd-v0.1.0"
sys.path.insert(0, ROOT+"/scripts"); sys.path.insert(0, ROOT+"/src")
from qiskit import qpy, transpile
from qiskit.circuit.library import XGate, YGate
from qiskit.transpiler import InstructionDurations, PassManager
from qiskit_ibm_runtime.transpiler.passes.scheduling import ALAPScheduleAnalysis, PadDynamicalDecoupling
from qiskit.transpiler.passes import ALAPScheduleAnalysis as QALAP, ContextAwareDynamicalDecoupling
from qiskit_ibm_runtime.fake_provider import FakeKingston
from skqd.hardware import logical_statevector
from h0_backends import backend_from_record
from gate_S2D_levers import delay_schedule

rec=json.load(open(ROOT+"/data/hardware/H0_kpilot_prep/calibration_20261002T1627Z.json"))
with gzip.open(ROOT+"/data/hardware/H0_kpilot_prep/circuits/B0_ref06_k1.qpy.gz","rb") as fh:
    tq=qpy.load(fh)[0]
print("ops before", dict(tq.count_ops()))
dt=rec["dt_s"]
# windows
sch=delay_schedule(tq, rec, include_leading=False)
ws=[w for q,v in sch["per_qubit"].items() for w in v["windows_s"]]
if True:
    ws=np.array(ws)
    print("n windows", len(ws), "total idle s", ws.sum(), "median", np.median(ws), "max", ws.max())
    xdur=32e-9
    for L,name in ((4*xdur,"XY4 len 128ns"),):
        print(name, "windows >= 2x seq", int((ws>=2*L).sum()), "idle in them", ws[ws>=2*L].sum(), "windows >= 1x", int((ws>=L).sum()))
    print("windows >= 1us", int((ws>=1e-6).sum()), "idle in them", ws[ws>=1e-6].sum())
    print("windows >= 2us", int((ws>=2e-6).sum()), "idle in them", ws[ws>=2e-6].sum())
# durations from the record
entries=[]
for q,v in rec["qubits"].items():
    q=int(q)
    entries += [("sx",[q],v["sx_duration_s"],"s"),("x",[q],v["x_duration_s"],"s"),("y",[q],v["x_duration_s"],"s"),("rz",[q],0.0,"s"),("measure",[q],v["measure_duration_s"],"s")]
for v in rec["edges"].values():
    a,b=v["target_key"]; entries.append(("cz",[a,b],v["cz_duration_s"],"s"))
dur=InstructionDurations(entries, dt=dt)
ACT=[59,71,72,73,74,75,79,91,92,93,94,95]
def sv(circ):
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    pos={p:i for i,p in enumerate(ACT)}
    cc=QuantumCircuit(12); cc.global_phase=circ.global_phase
    for inst in circ.data:
        nm=inst.operation.name
        if nm in ("delay","barrier","measure"): continue
        qs=[pos[circ.find_bit(q).index] for q in inst.qubits]
        cc.append(inst.operation, qs)
    return np.asarray(Statevector(cc).data)
psi0=sv(tq)
def inserted(out, base):
    c=Counter()
    for circ,sign in ((out,+1),(base,-1)):
        for inst in circ.data:
            if inst.operation.name in ("x","y","sx","rz"):
                c[(inst.operation.name,int(circ.find_bit(inst.qubits[0]).index))]+=sign
    return c
xerr={int(q):v["x_error"] for q,v in rec["qubits"].items()}
def report(name,out):
    c=inserted(out,tq)
    nx=sum(v for (g,q),v in c.items() if g in("x","y"))
    cost=sum(v*xerr[q] for (g,q),v in c.items() if g in("x","y"))
    per_q=Counter()
    for (g,q),v in c.items():
        if g in ("x","y"): per_q[q]+=v
    psi=sv(out)
    # compare up to global phase
    ov=np.vdot(psi0,psi); d=np.max(np.abs(psi*np.exp(-1j*np.angle(ov))-psi0))
    print(f"{name}: inserted x/y {nx}, pulse cost sum eps {cost:.4f} nats -> factor {math.exp(-cost):.3f}; per-qubit {dict(sorted(per_q.items()))}; ops {dict(out.count_ops())}; max|dpsi| {d:.2e}; |ov| {abs(ov):.12f}")
    return out
t=time.time()
pm=PassManager([ALAPScheduleAnalysis(durations=dur), PadDynamicalDecoupling(durations=dur, dd_sequences=[XGate(),YGate(),XGate(),YGate()], sequence_min_length_ratios=[2.0], pulse_alignment=1)])
outA=report("client XY4 ratio2", pm.run(tq)); print("t",time.time()-t)
pm=PassManager([ALAPScheduleAnalysis(durations=dur), PadDynamicalDecoupling(durations=dur, dd_sequences=[XGate(),XGate()], sequence_min_length_ratios=[2.0], pulse_alignment=1)])
outX=report("client XX ratio2", pm.run(tq))
# staggered via coupling map
from qiskit.transpiler import CouplingMap
edges=[tuple(v["target_key"]) for v in rec["edges"].values()]
cm=CouplingMap(edges+[(b,a) for a,b in edges])
pm=PassManager([ALAPScheduleAnalysis(durations=dur), PadDynamicalDecoupling(durations=dur, dd_sequences=[XGate(),XGate()], sequence_min_length_ratios=[2.0], pulse_alignment=1, coupling_map=cm, alt_spacings=[0.25,0.5,0.25])])
try:
    outS=report("client XX staggered(coupling_map)", pm.run(tq))
except Exception as e: print("staggered failed", repr(e)[:300])
# context-aware
t=time.time()
be=backend_from_record(rec, base=FakeKingston(), strict=True); be=be[0] if isinstance(be,tuple) else be
tgt=be.target
try:
    pm=PassManager([QALAP(target=tgt), ContextAwareDynamicalDecoupling(target=tgt, pulse_alignment=1)])
    outC=report("ContextAwareDD (qiskit)", pm.run(tq)); print("t",time.time()-t)
except Exception as e:
    import traceback; traceback.print_exc()
# duration check of outA
from h0_qpu_time import circuit_duration_s
for nm,o in (("base",tq),("XY4",outA),("XX",outX)):
    print(nm,"duration s", circuit_duration_s(o, tgt.durations(), tgt))
try: print("CA duration", circuit_duration_s(outC, tgt.durations(), tgt))
except Exception as e: print(e)

print("---- scan ----")
for ratio in (2.0, 4.0, 8.0, 16.0):
    pm=PassManager([ALAPScheduleAnalysis(durations=dur), PadDynamicalDecoupling(durations=dur, dd_sequences=[XGate(),YGate(),XGate(),YGate()], sequence_min_length_ratios=[ratio], pulse_alignment=1)])
    o=pm.run(tq); c=inserted(o,tq); nx=sum(v for (g,q),v in c.items() if g in("x","y")); cost=sum(v*xerr[q] for (g,q),v in c.items() if g in("x","y"))
    thr=ratio*4*xdur; cov=ws[ws>=thr].sum()/ws.sum()
    print(f"XY4 ratio {ratio}: min window {thr*1e9:.0f} ns, windows {int((ws>=thr).sum())}, idle covered {cov:.3f}, pulses {nx}, cost {cost:.4f} nats, factor {math.exp(-cost):.3f}")
for md in (64, 128, 250, 500, 1000):
    pm=PassManager([QALAP(target=tgt), ContextAwareDynamicalDecoupling(target=tgt, pulse_alignment=1, min_duration=md)])
    o=pm.run(tq); c=inserted(o,tq); nx=sum(v for (g,q),v in c.items() if g in("x","y")); cost=sum(v*xerr[q] for (g,q),v in c.items() if g in("x","y"))
    psi=sv(o); ov=np.vdot(psi0,psi)
    print(f"CA min_duration {md} dt ({md*4} ns): pulses {nx}, cost {cost:.4f} nats, factor {math.exp(-cost):.3f}, |ov| {abs(ov):.6f}, dur {circuit_duration_s(o, tgt.durations(), tgt)*1e6:.3f} us")

print("---- leading-window check ----")
def leading_pulses(o):
    first_gate_seen={q:False for q in ACT}; lead=Counter(); trail=Counter(); measured={q:False for q in ACT}
    for inst in o.data:
        nm=inst.operation.name
        qs=[o.find_bit(q).index for q in inst.qubits]
        if nm in ("barrier",): continue
        for q in qs:
            if q not in first_gate_seen: continue
            if nm=="measure": measured[q]=True; continue
            if nm in ("x","y") and not first_gate_seen[q]: lead[q]+=1
            elif nm in ("x","y") and measured[q]: trail[q]+=1
            elif nm not in ("delay",): first_gate_seen[q]=True
    return dict(lead), dict(trail)
print("base leading x (the circuit's own):", leading_pulses(tq))
print("XY4 ratio2 leading/trailing pulses:", leading_pulses(outA))
print("CA default leading/trailing:", leading_pulses(outC))
print("leading_s per qubit:", {q: round(v*1e6,2) for q,v in sch["leading_s"].items()})

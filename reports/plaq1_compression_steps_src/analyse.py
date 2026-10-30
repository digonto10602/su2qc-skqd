import os, sys, json, time, pickle
STUDY='/home/digimonk/Projects/su2qc-skqd/2x4_compression_using_ai_v1'; ROOT=os.path.dirname(STUDY)
sys.path.insert(0, os.path.join(STUDY,'src')); sys.path.insert(0, os.path.join(ROOT,'src'))
import c2x4.env as env
HERE=os.path.dirname(os.path.abspath(__file__)); CACHE=os.path.join(HERE,'cache')
env.CACHE=CACHE; env.archive_path=lambda l: os.path.join(HERE,f'archive_{l}.json')
import c2x4.problem as problem, c2x4.family as family
problem.CACHE=CACHE; family.CACHE=CACHE
from c2x4.problem import get_problem
from c2x4 import plaqfactor
from c2x4.evaluate import counts, verify_term_operator
from c2x4.proposals import PROPOSALS
from c2x4.sparsemux import use_sparse_mux
P=get_problem(4); th=P.theta(0,1); nm='plaq1'
out={'theta':th}
def rec(label, g, info=None):
    c=counts(g); r=verify_term_operator(P, nm, g, th)
    d={'n_2q':c['n_2q'],'depth_2q':c['depth_2q'],'max_dev':r['max_dev'],'max_leak':r['max_leak'],'counts':{k:v for k,v in c.items() if k not in('n_2q','depth_2q')}}
    if info is not None: d['info']=info
    out[label]=d; print(label, d['n_2q'], d['depth_2q'], f"{d['max_dev']:.2e}", flush=True)
t=time.time()
g0=P.baseline_term_ir(nm, th); rec('frozen', g0)
g,i=plaqfactor.cf1_gates(P,nm,th,1,return_info=True); rec('cf1',g,{k:v for k,v in i.items() if k in('p1','omega','n_rotations','multiplexer','frame_2q','corners')})
g,i=plaqfactor.cf2_gates(P,nm,th,1,return_info=True); rec('cf2',g,i)
with use_sparse_mux():
    g,i=plaqfactor.cf2_gates(P,nm,th,1,return_info=True); rec('cf2_sw',g,i)
g=PROPOSALS['cf2_lin_milp']['fn'](P,nm,th,None,None); rec('cf2_lin_milp',g)
fac=plaqfactor.factorise(P,nm,plaqfactor.corners_of(P,1))
out['factorise']={k:(v.tolist() if hasattr(v,'tolist') else v) for k,v in fac.items() if k!='mats'}
out['corner_mats']=[m.tolist() for m in fac['mats']]
pickle.dump(out, open('plaq1_steps.pkl','wb'))
print('wall', time.time()-t)

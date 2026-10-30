import os, sys, pickle, time
exec(open('analyse.py').read().split("P=get_problem(4)")[0])
P=get_problem(4); th=P.theta(0,1); nm='plaq1'
t=time.time()
g,i=plaqfactor.cf2_gates(P,nm,th,1,return_info=True)
corners=plaqfactor.corners_of(P,1)
pickle.dump({'gates':g,'info':i,'corners':corners,'theta':th}, open('cf2_gates.pkl','wb'))
print(len(g), time.time()-t)
for c in corners: print({k:v for k,v in c.items() if k!='mats'})
n2=0
for k,(nm_,qs,par) in enumerate(g[:120]):
    print(k, nm_, qs, None if par is None or nm_=='unitary' else round(float(par),4))

import sys, json, time, numpy as np, scipy.sparse as sp, scipy.sparse.csgraph as csg
sys.path.insert(0, '/home/digimonk/Projects/su2qc-skqd/src')
from skqd.exact import Model
from skqd.codec import Codec
from skqd.reference_sim import term_support, localize
G2 = 4.0
t = time.time(); M = Model(4); print('model', time.time()-t, 'dim', M.basis.dim)
C = Codec(M.basis); lat = M.lat; ends = lat.ends()
site_of_q = {}
for s in range(lat.n_sites):
    for i in range(C.widths[s]):
        q = C.offsets[s] + i
        if i < len(ends[s]): site_of_q[int(q)] = (int(s), 'flux', ends[s][i][0], ends[s][i][1])
        else: site_of_q[int(q)] = (int(s), 'matter', None, None)
def decode_site(s, bits):  # bits: list of this site's bits in qubit order
    k = len(ends[s]); fl = bits[:k]; m = bits[k]; f = sum(fl)
    if k == 2:
        if fl[0] == fl[1]: return dict(n=2*m, iota=None, valid=True)
        return dict(n=1, iota=None, valid=(m == 0))
    if f % 2 == 0: return dict(n=2*m, iota=None, valid=True)
    if f == 1: return dict(n=1, iota=None, valid=(m == 0))
    return dict(n=1, iota=m, valid=True)
out = {'lattice': {'links': lat.links, 'plaquettes': lat.plaquettes, 'ends': {s: ends[s] for s in ends},
       'widths': [int(w) for w in C.widths], 'offsets': [int(o) for o in C.offsets],
       'site_of_q': {q: v for q, v in site_of_q.items()}, 'coords': [lat.coords(s) for s in range(lat.n_sites)]}}
for P in range(3):
    O = -M.terms.plaq[P] / (2 * G2)
    sup = term_support(M, 'plaq', P)
    states, h, pos = localize(M, O, sup)
    A = np.abs(h) > 1e-12; np.fill_diagonal(A, False)
    nc, lab = csg.connected_components(sp.csr_matrix(A), directed=False)
    recs = []
    for i, s in enumerate(states):
        bits = [(s >> j) & 1 for j in range(len(sup))]
        gq = {sup[j]: bits[j] for j in range(len(sup))}
        sites = {}
        for site in sorted({site_of_q[q][0] for q in sup}):
            qs = list(range(C.offsets[site], C.offsets[site] + C.widths[site]))
            sb = [gq[q] for q in qs]
            d = decode_site(site, sb); d['bits'] = sb; d['qubits'] = qs
            d['flux'] = {int(ends[site][e][0]): sb[e] for e in range(len(ends[site]))}
            sites[site] = d
        nb = [(int(j), float(h[i, j].real), float(h[i, j].imag)) for j in np.nonzero(A[i])[0]]
        recs.append(dict(idx=i, int=int(s), bits=bits, sites=sites, block=int(lab[i]), nbrs=nb))
    hist = {}
    for c in range(nc):
        n = int((lab == c).sum()); hist[n] = hist.get(n, 0) + 1
    print(f'plaq{P}', len(sup), 'qubits', len(states), 'states', nc, 'blocks', dict(sorted(hist.items())))
    out[f'plaq{P}'] = dict(support=[int(q) for q in sup], n_states=len(states), n_blocks=int(nc),
                           block_hist={str(k): v for k, v in sorted(hist.items())}, states=recs,
                           diag_max=float(np.abs(np.diag(h)).max()))
import pickle; pickle.dump(out, open("vs.pkl","wb")); json.dump(json.loads(json.dumps(out, default=int)) if False else {}, open('valid_states_2x4.json', 'w'))
print('done', time.time()-t)

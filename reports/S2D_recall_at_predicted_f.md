# 2x3 recall at the clean-shot fractions predicted by gate S2D (production budget 2e5 shots per sector)

Produced by `scripts/s2d_recall_at_predicted_f.py`; numbers in `data/S2D_recall_at_f.json`.  Environment: Python 3.12.14, numpy 2.5.2, scipy 1.18.0, Linux-7.2.3-arch1-3-x86_64-with-glibc2.44, 12 CPUs, commit 94d2137, 2026-09-16 07:27:44 MDT.  Runtime 136 s.

Gate S2D (`validation/S2D.json`) predicts f = 0.0534 for the exact 2x3 coarse-step circuits on the declared all-to-all
device (eps2 = 1e-3, eps1 = 1e-4, eps_ro = 2e-3), or 0.0817 if rz is virtual.  The operational requirement behind the
CZ budget is gate S1's criterion: recall of the 99.9 % support >= 0.9 with 2e5 shots per sector.  This table applies that
criterion at those f (S1 proxy emulation, all references, coarse steps k = 1..4, three seeds).

| sector | f | circuits | shots/circuit | recall (3 seeds) | min recall | |B| | yield | E0 in Weinstein | N_sector, shot rule per sector |
|---|---|---|---|---|---|---|---|---|---|
| B=0 | 0.1 | 32 | 6250 | 1.000 / 1.000 / 1.000 | 1.0 | 333/333/350 | 0.0881 | yes | 71500 |
| B=0 | 0.0817 | 32 | 6250 | 1.000 / 1.000 / 1.000 | 1.0 | 329/323/341 | 0.0743 | yes | 84714 |
| B=0 | 0.0534 | 32 | 6250 | 1.000 / 0.988 / 1.000 | 0.9883720930232558 | 313/311/320 | 0.0508 | yes | 123954 |
| B=0 | 0.03 | 32 | 6250 | 0.988 / 0.953 / 1.000 | 0.9534883720930233 | 284/290/302 | 0.0315 | yes | 199952 |
| B=1 | 0.1 | 12 | 16667 | 1.000 / 0.989 / 0.989 | 0.9894736842105263 | 244/248/260 | 0.0886 | yes | 71075 |
| B=1 | 0.0817 | 12 | 16667 | 0.979 / 0.989 / 0.979 | 0.9789473684210527 | 242/259/253 | 0.0737 | yes | 85440 |
| B=1 | 0.0534 | 12 | 16667 | 0.958 / 0.989 / 0.989 | 0.9578947368421052 | 224/237/222 | 0.0505 | yes | 124569 |
| B=1 | 0.03 | 12 | 16667 | 0.958 / 0.958 / 0.937 | 0.9368421052631579 | 220/216/211 | 0.0314 | yes | 200806 |

The last column is the manual's shot rule (a configuration of ideal probability p = 1e-3 seen >= 3 times with 95 %
probability, lambda* = 6.296) applied to the sector as a whole (the support is the union over circuits), N = lambda*/(p y);
gate S2D applied it per circuit and multiplied by the number of circuits, which is the reading that fails the 2e5 quota.

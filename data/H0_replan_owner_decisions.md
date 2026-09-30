# Owner decisions on the nine named changes of prompts/20

Recorded one at a time as the owner rules on them.  Nothing here is applied to code until every
decision is taken; the executor prompt that applies them will cite this file.

| id | change | owner ruling | date | notes |
|---|---|---|---|---|
| D8' | production sampler options: dynamical decoupling off, gate and measurement twirling off | **APPROVED** | 2026-09-30 | Approved on the parameter-free argument, not on the factorial ranking: the refocusing efficiency of the decoupling and the pulse cost of the twirling are neither computable from the calibration nor measured on the patch. The factorial's 35/27/25/17 ordering is the near-clean acceptance term, not a clean-shot measurement (2/1/1/0 reference hits). Client-side multi-cycle decoupling on the long-idle qubits, with runtime decoupling off, may return as a preregistered comparison once the pilot shows a clean fraction above about 1 per cent. |

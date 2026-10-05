# Owner decisions, 2026-10-05: prompts/29 Part B' (Digonto)

Verbatim: "1a, 2a with the convergence condition, 3a" (in reply to the three Part B' decisions as
described by the coordinator on 2026-10-05).

1a. The signed budget bar (mean f >= 0.1, worst >= 0.05) refers to the ideal-sample fraction f_ideal
    (shots that sample the ideal output distribution: fault-free plus benign-fault shots), measured on a
    device as f_hat_ideal = f_hit / r_nc with r_nc = 1.115 (data/cf_trajectories/r_nc.json, gate CF_traj).
2a. Rule D3'-R (prompts/28, prompts/29) is signed as the MINIMUM 2x3 shot sizing, with input
    y = 0.82 x 0.7 x f_hat_ideal, together with the Stage E / Stage P v3 plans (800/800/200/200).
    Condition: approval of any full 2x3 campaign additionally requires that the emulated check of the
    plan shows energy convergence (E_R and certificate width against shots and against Krylov k) and
    weighted coverage, under criteria the planner adds; if not met, the planner re-sizes and the new cost
    returns to the owner.  Signing commits no HQC; Stage E / P budgets are separate written decisions.
3a. The 2x2 qualification is accepted: the 2x2 "signed bar GO" (H0_ddtest / H0_2x2) was read on f_hit; under
    the conservative gate-noise correction it may read AMBIGUOUS; external citations carry this qualification.
    No recorded verdict is edited.

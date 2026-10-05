# Quantinuum access request — draft for the owner (2026-10-05)

Drafted by the coordinator for Digonto to edit and send.  Nothing here has been sent.  Fill in the
bracketed fields.  Every number is taken from the file named after it; check them before sending.

Two routes (reports/qpu_survey_2x3_20261002.md, "access"):

- **A. OLCF Quantum Computing User Program (QCUP)**: apply at myOLCF (year-round form).  Default
  emulator quota "6000 seconds"; hardware credits are requested monthly and "must be justified using
  results from an emulator".  Eligibility: the OLCF page lists "US national labs, universities,
  government, and industry"; Quantinuum's page says "Researchers in the United States may apply".
  **Confirm your eligibility first.**
- **B. Quantinuum directly**: Sales@Quantinuum.com for a research agreement with Nexus access;
  technical questions to QCsupport@quantinuum.com.

Ask for the **emulator first**.  The hardware request needs emulator results anyway.

---

## Draft email (route B; also usable as the project summary for route A)

**To:** Sales@Quantinuum.com  (cc: QCsupport@quantinuum.com)
**Subject:** Research access request: SU(2) lattice gauge theory by sample-based Krylov diagonalization on H2-2 / Helios

Dear Quantinuum team,

I am [name, position, institution], leading a project on non-Abelian (SU(2)) lattice gauge theory
with staggered quarks on 2×L ladders. The method is sample-based Krylov quantum diagonalization
(SKQD). We would like research access to Quantinuum Nexus: first the H2-2 emulator (H2-2E), then a
small hardware pilot on H2-2 or Helios-1.

**Why Quantinuum.** We surveyed the accessible quantum computers (2026-10-02). Our 2×3 lattice
circuits use 20 qubits and 2,158 two-qubit (ZZPhase) gates on all-to-all connectivity. Of the
machines we surveyed, only H2-2 and Helios-1 give an expected clean-shot fraction above our
preregistered bar of 0.1, on published gate and SPAM errors alone (0.150 and 0.164; our
validation file `validation/Q0P_2x3.json`). Superconducting devices need about 5,500 two-qubit gates
after routing and stay below 0.011.

**What is ready:**
- **Circuits.** All 44 circuits (both gauge sectors, Krylov steps k = 1–4) are compiled to the
  Quantinuum native gate set (Rz, PhasedX, ZZPhase) with pytket. They are verified against an
  exact state-vector simulation to 2.1×10⁻¹³ and frozen with checksums.
- **Tooling.** Our submission tooling caps every job with `max_cost`.
- **Validation.** We completed one end-to-end run of the full pipeline on IBM hardware for the 2×2
  lattice. That run validated the analysis, including a preregistered dynamical-decoupling test.

**What we request:**
1. **Emulator access (H2-2E)**, about 10,000 eHQC. The run is two k = 1 circuits at 800 shots each
   and two k = 4 circuits at 200 shots each (prompts/29, plan v3). It measures the idle/transport
   memory error of our ~1,900-layer serial circuit, which no published number determines.
2. **If the emulator result passes** our preregistered rule (corrected clean fraction ≥ 0.10 with
   95 % lower bound ≥ 0.05): a hardware pilot of the same four circuits, about 10,000 HQC.

**Questions that decide our plan:**
1. The current measured two-qubit gate error on H2-2 and Helios-1.
2. The memory (idle/transport) error per layer for a 20-qubit, largely serial program of about
   1,900 two-qubit layers, and how well H2-2E reproduces it.
3. How many two-qubit gates run in parallel for such a program.
4. How single-qubit Rz and PhasedX gates enter the HQC cost formula.
5. The pay-as-you-go or research HQC rate, and whether research or academic allocations exist.

All our data, gates and reports are versioned in a public repository
(https://github.com/digonto10602/su2qc-skqd). I can share the frozen circuits and the
preregistration before any run.

Best regards,
[name]
[institution, email, phone]

---

## Notes for the owner (not for sending)

- **Do not attach any API key or token.** Nexus logs in through `scripts/quantinuum_account.py --login`
  (tokens stay in `~/.qnx/auth/`).
- **Check before sending:**
  - the repository is public, or remove that sentence;
  - the 2×2 IBM statement carries the qualification of decision 3a
    (`data/owner_decision_20261005_partB.md`) if you quote a clean fraction;
  - the eHQC/HQC figures are planner estimates (prompts/29) until gate Q0P_2x3_plan reproduces them.
- **Full campaign scale, for your own planning:** 3.0–4.2×10⁵ HQC at H2-2 (prompts/28/29), a
  minimum under the convergence condition of decision 2a.

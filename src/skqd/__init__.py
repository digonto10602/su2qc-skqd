"""skqd — sample-based Krylov quantum diagonalization for SU(2) + staggered quarks on 2 x Lx ladders.

Physics core (validated in reports/):
    lattice, su2, fermions, vertex, basis, hamiltonian, fullspace, codec, exact
SKQD workflow:
    krylov, noise, skqd, controls, ml, certification
Circuit layer (laptop gates, not executable in the cloud sandbox where the package was built):
    circuits_qiskit, circuits_cudaq, reference_sim
"""
__version__ = "0.1.0"

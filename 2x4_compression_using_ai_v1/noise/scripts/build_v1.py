"""Build the 150 v1 circuits (compressed_circuit_llm_2x4_class[A,B]) with genie's builders, cache redirected."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import circuits
if __name__ == "__main__":
    circuits.build_v1(log=lambda s: print(s, flush=True))
    print("BUILD_DONE", flush=True)

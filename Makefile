PY ?= python3
.PHONY: check test gates status structure clean
check:
	$(PY) scripts/check_package.py
test:
	$(PY) -m pytest -q tests || $(PY) scripts/run_tests_no_pytest.py
gates:
	$(PY) scripts/run_gate.py E1 && $(PY) scripts/run_gate.py E2 && $(PY) scripts/run_gate.py E3 && $(PY) scripts/run_gate.py S1
status:
	$(PY) scripts/update_status.py
structure:
	$(PY) scripts/report_circuit_structure.py
clean:
	rm -rf validation/BLOCKED.md src/skqd/__pycache__ tests/__pycache__ scripts/__pycache__

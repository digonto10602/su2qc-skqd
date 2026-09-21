#!/usr/bin/env python3
"""
IBM Quantum account setup and backend check for gate H0 (prompts/07 step 2).

This repository assumes no IBM account: `scripts/h0_submit.py --dry-run` runs the whole
submission path locally.  The production path `--backend <name>` needs a saved account,
which is what `--save` writes here, and a device on which the FROZEN circuit set of
`scripts/h0_build_circuits.py` is actually executable, which is what `--check` verifies.

  --save    takes the API key and saves it to the qiskit default account file
            ~/.qiskit/qiskit-ibm.json.  Nothing secret is printed.  The key is read, in
            order, from --token-file, $QISKIT_IBM_TOKEN, a hidden prompt (a terminal
            only), or piped stdin -- never from a command-line argument, which would be
            visible in `ps`, in the shell history and in any agent transcript.
  --check   lists the backends the account can reach and, for each one with enough qubits,
            checks the frozen set against the LIVE device: the physical qubits the
            transpiler chose must exist, every two-qubit edge the circuits use must be in
            the live coupling map, and the basis gates must cover the frozen operations.

As of qiskit-ibm-runtime 0.49 the only channel is `ibm_quantum_platform` (IBM Cloud);
the legacy `ibm_quantum` channel no longer exists.  Get an API key at
https://quantum.cloud.ibm.com -> your instance -> API key.

Usage: python scripts/ibm_account.py --save
       python scripts/ibm_account.py --check [--prep data/hardware/H0_prep]
"""
import argparse
import glob
import gzip
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def open_service():
    """QiskitRuntimeService() with a diagnosis instead of a traceback when the key is bad."""
    import json
    import re

    from qiskit_ibm_runtime import QiskitRuntimeService

    try:
        return QiskitRuntimeService()
    except Exception as exc:
        path = os.path.expanduser("~/.qiskit/qiskit-ibm.json")
        detail = []
        if os.path.exists(path):
            for name, acct in json.load(open(path)).items():
                tok = acct.get("token", "")
                detail.append(f"  saved account '{name}': channel {acct.get('channel')}, "
                              f"instance {'set' if acct.get('instance') else 'not set'}, "
                              f"key {len(tok)} characters "
                              f"({'hex' if re.fullmatch(r'[0-9a-fA-F]+', tok or 'x') else 'base64-ish'})")
                if re.fullmatch(r"[0-9a-fA-F]{100,}", tok or ""):
                    detail.append("  -> that is a LEGACY quantum-computing.ibm.com token (128 hex "
                                  "characters).  The ibm_quantum channel was retired; the "
                                  "ibm_quantum_platform channel needs an IBM Cloud API key.")
                elif len(tok) != 44:
                    detail.append(f"  -> an IBM Cloud API key is 44 characters, this one is "
                                  f"{len(tok)}: most likely the paste lost a character.")
        raise SystemExit(
            f"cannot open the IBM account: {exc}\n" + "\n".join(detail) + "\n"
            "  Get a fresh key at https://quantum.cloud.ibm.com -> Manage -> API keys "
            "(copy the whole value; it is shown once), then save it again:\n"
            "    python scripts/ibm_account.py --save --token-file <file> --delete-token-file")


def read_token(args):
    """The API key, from the least exposed source available.

    Never from the command line: an argument is visible in `ps`, in the shell history
    and -- when the command is run from an agent session -- in the transcript.
    """
    if args.token_file:
        path = os.path.expanduser(args.token_file)
        with open(path) as fh:
            token = next((ln.strip() for ln in fh if ln.strip()), "")
        if not token:
            raise SystemExit(f"{path} is empty")
        print(f"  key read from {path}", flush=True)
        return token, path
    for var in ("QISKIT_IBM_TOKEN", "IBM_QUANTUM_TOKEN"):
        if os.environ.get(var, "").strip():
            print(f"  key read from ${var}", flush=True)
            return os.environ[var].strip(), None
    if sys.stdin.isatty():
        from getpass import getpass
        print("IBM Quantum Platform API key (https://quantum.cloud.ibm.com, input is hidden):",
              flush=True)
        return getpass("  API key: ").strip(), None
    token = sys.stdin.readline().strip()          # piped, e.g. pass/gpg/secret-tool
    if token:
        print("  key read from stdin", flush=True)
        return token, None
    raise SystemExit(
        "no API key and no terminal to ask on.\n"
        "This command has no TTY, so the hidden prompt cannot run.  Choose one:\n"
        "  (a) run it in your own terminal:      python scripts/ibm_account.py --save\n"
        "  (b) put the key in a file with your editor, then:\n"
        "        python scripts/ibm_account.py --save --token-file ~/.ibm_key --delete-token-file\n"
        "  (c) pipe it from a secret store:\n"
        "        pass show ibm/quantum | python scripts/ibm_account.py --save\n"
        "Do NOT pass the key as a command-line argument: it would be visible in `ps`, "
        "in the shell history and in any agent transcript.")


def do_save(args):
    from qiskit_ibm_runtime import QiskitRuntimeService

    token, token_path = read_token(args)
    if not token:
        raise SystemExit("no key entered; nothing saved")
    instance = args.instance
    if instance is None and sys.stdin.isatty():
        print("Instance CRN (optional -- press Enter to let the service resolve your instances):",
              flush=True)
        instance = input("  CRN: ").strip() or None

    QiskitRuntimeService.save_account(
        token=token,
        channel=args.channel,
        instance=instance,
        set_as_default=True,
        overwrite=True,
    )
    path = os.path.expanduser("~/.qiskit/qiskit-ibm.json")
    print(f"\nsaved to {path} (channel {args.channel}, "
          f"instance {'given' if instance else 'resolved by the service'})", flush=True)
    if token_path and args.delete_token_file:
        os.remove(token_path)
        print(f"  removed {token_path}", flush=True)
    print("verifying the account by opening the service ...", flush=True)
    service = open_service()
    names = [b.name for b in service.backends()]
    print(f"  account OK: {len(names)} backend(s) reachable: {', '.join(names) or '(none)'}")
    print("\nnext: python scripts/ibm_account.py --check")
    return 0


def frozen_requirements(prep):
    """What the frozen circuit set needs of a device: qubits, edges, operations."""
    from qiskit import qpy

    mans = sorted(glob.glob(os.path.join(prep, "circuits", "*.json")))
    if not mans:
        raise SystemExit(f"no manifests in {prep}/circuits -- run scripts/h0_build_circuits.py first")
    qubits, edges, ops = set(), set(), set()
    snapshot, n_qubits_snapshot = None, None
    for p in mans:
        m = json.load(open(p))
        snapshot = snapshot or m["backend"]
        n_qubits_snapshot = n_qubits_snapshot or m["backend_qubits"]
        qubits.update(m["physical_qubits"])
        ops.update(m["ops"])
        with gzip.open(os.path.join(prep, "circuits", m["qpy"]), "rb") as fh:
            qc = qpy.load(fh)[0]
        for inst in qc.data:
            if len(inst.qubits) == 2:
                a, b = (qc.find_bit(q).index for q in inst.qubits)
                edges.add((a, b))
            for q in inst.qubits:
                qubits.add(qc.find_bit(q).index)
    return {
        "snapshot": snapshot, "snapshot_qubits": n_qubits_snapshot,
        "n_circuits": len(mans), "qubits": sorted(qubits),
        "edges": sorted(edges), "ops": sorted(ops),
    }


def check_backend(backend, req):
    """Is the frozen set executable on this live backend, as frozen?"""
    t = backend.target
    live_ops = set(t.operation_names)
    cmap = backend.coupling_map
    live_edges = set(map(tuple, cmap)) if cmap is not None else None
    problems = []
    if backend.num_qubits < req["snapshot_qubits"]:
        problems.append(f"{backend.num_qubits} qubits < the {req['snapshot_qubits']} of "
                        f"the {req['snapshot']} snapshot")
    missing_q = [q for q in req["qubits"] if q >= backend.num_qubits]
    if missing_q:
        problems.append(f"physical qubits absent on this device: {missing_q}")
    if live_edges is not None:
        missing_e = [e for e in req["edges"]
                     if e not in live_edges and (e[1], e[0]) not in live_edges]
        if missing_e:
            problems.append(f"{len(missing_e)} two-qubit edge(s) not in the coupling map, "
                            f"e.g. {missing_e[:5]}")
    missing_op = [o for o in req["ops"] if o not in live_ops and o not in ("barrier",)]
    if missing_op:
        problems.append(f"operations not in the basis: {missing_op} (basis: {sorted(live_ops)})")
    # non-operational qubits among the ones we use
    try:
        bad = [q for q in req["qubits"] if backend.qubit_properties(q) is None]
        if bad:
            problems.append(f"no calibration data for qubits {bad}")
    except Exception:
        pass
    return problems


def do_check(args):
    prep = os.path.join(ROOT, args.prep)
    req = frozen_requirements(prep)
    print(f"frozen set: {req['n_circuits']} circuits transpiled onto {req['snapshot']} "
          f"({req['snapshot_qubits']} qubits)")
    print(f"  uses {len(req['qubits'])} physical qubits {req['qubits']}")
    print(f"  uses {len(req['edges'])} distinct two-qubit edges")
    print(f"  operations {req['ops']}\n")

    service = open_service()
    backends = service.backends()
    if not backends:
        raise SystemExit("the account reaches no backends; check the instance of your API key")
    print(f"{len(backends)} backend(s) reachable:\n")
    usable = []
    for b in backends:
        try:
            status = b.status()
            pending, operational = status.pending_jobs, status.operational
        except Exception:
            pending, operational = None, None
        head = (f"  {b.name}: {b.num_qubits} qubits, "
                f"processor {getattr(b, 'processor_type', {}) or {}}, "
                f"{'operational' if operational else 'NOT operational'}"
                f"{'' if pending is None else f', {pending} pending jobs'}")
        print(head)
        problems = check_backend(b, req)
        if problems:
            for p in problems:
                print(f"      x {p}")
        else:
            print(f"      OK: the frozen set runs on {b.name} as frozen")
            usable.append(b.name)
    print()
    if usable:
        print(f"usable as frozen: {', '.join(usable)}")
        print(f"  submit with: python scripts/h0_submit.py --backend {usable[0]} "
              f"--shots-by-rep 1:267 2:130 3:92 --out data/hardware/H0_{usable[0]}")
    else:
        print("NO reachable backend runs the frozen set as frozen.")
        print("  The circuits are pinned to a calibration snapshot; for a different device")
        print("  re-freeze them first:  python scripts/h0_build_circuits.py --backend <name>")
        print("  then re-run gate H0P (it re-predicts the yields from that day's calibration)")
        print("  before submitting -- reports/H0_prereg_draft.md section 2 requires it.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true", help="prompt for the API key and save it")
    ap.add_argument("--check", action="store_true", help="list backends and validate the frozen set")
    ap.add_argument("--channel", default="ibm_quantum_platform")
    ap.add_argument("--token-file", default=None,
                    help="file whose first non-empty line is the API key (no TTY needed)")
    ap.add_argument("--delete-token-file", action="store_true",
                    help="remove --token-file after a successful save")
    ap.add_argument("--instance", default=None, help="instance CRN (optional)")
    ap.add_argument("--prep", default=os.path.join("data", "hardware", "H0_prep"))
    args = ap.parse_args()
    if not (args.save or args.check):
        ap.error("choose --save or --check")
    if args.save:
        do_save(args)
    if args.check:
        do_check(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

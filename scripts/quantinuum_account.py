#!/usr/bin/env python3
"""
prompts/26 A7: Quantinuum Nexus account handling for the 2x3 submission path.

This repository assumes NO Nexus account (prompts/26 Stage A runs with 0 HQC and no login).  The
script exists so that the owner can log in once Stage E is authorised.

  --login     qnexus.login() (browser), or with --credentials qnexus.login_with_credentials(),
              which itself reads the e-mail with input() and the password with getpass (a hidden
              prompt; piped stdin when there is no terminal).  The password and the token NEVER
              pass through a command-line argument, an environment variable read by this script,
              a print, or a file written by this script.  qnexus keeps its own token store:
              ~/.qnx/auth/ (qnexus 0.51.0: `qnexus/config.py` token_path ".qnx/auth", resolved by
              `qnexus/client/utils.py` as Path.home() / CONFIG.token_path; the docstring of
              `login_with_token` names the "~/.qnx/auth/ directory"); tokens "should last 30 days"
              (https://docs.quantinuum.com/nexus/).
  --check     lists qnx.devices.get_all() and writes data/hardware/quantinuum_devices_<stamp>.json with
              a sha256 fingerprint of the device list.  Quantinuum publishes no per-job calibration
              record, so this fingerprint is the closest analogue of rule D9 (IBM) and is weaker: it
              changes when the device LIST changes, not when a device is recalibrated.
  --logout    qnexus.logout() (deletes the stored tokens).
  --status    whether a token store exists (file names only; contents are never read or printed).

Usage: ~/.local/share/su2qc-quantinuum/venv/bin/python scripts/quantinuum_account.py --status
"""
import argparse
import hashlib
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOKEN_DIR = os.path.join(os.path.expanduser("~"), ".qnx", "auth")


def token_store_status():
    """Existence of the qnexus token files -- names only, never contents."""
    if not os.path.isdir(TOKEN_DIR):
        return {"token_dir": "~/.qnx/auth", "exists": False, "files": []}
    return {"token_dir": "~/.qnx/auth", "exists": True, "files": sorted(os.listdir(TOKEN_DIR))}


def device_list_fingerprint(rows):
    """sha256 of the canonical JSON of the device list (sorted rows, sorted keys)."""
    canon = json.dumps(sorted(rows, key=lambda r: json.dumps(r, sort_keys=True, default=str)),
                       sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def do_login(credentials: bool):
    import qnexus as qnx

    if credentials:
        qnx.login_with_credentials()       # input() for the e-mail, getpass for the password
    else:
        qnx.login()                        # browser flow
    print("logged in; qnexus stored its tokens under ~/.qnx/auth (not read here)")
    return 0


def do_check():
    import qnexus as qnx

    try:
        qnx.users.get_self()
    except Exception as exc:
        raise SystemExit(f"no usable Nexus login ({type(exc).__name__}); run --login first") from None
    devs = qnx.devices.get_all()
    df = devs.df()
    rows = json.loads(df.to_json(orient="records", default_handler=str))
    stamp = time.strftime("%Y%m%dT%H%MZ", time.gmtime())
    rec = {"created": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
           "source": "qnexus.devices.get_all()", "devices": rows,
           "fingerprint_sha256": device_list_fingerprint(rows),
           "note": ("Quantinuum publishes no per-job calibration record; this fingerprint changes "
                    "with the device list only (the D9 analogue is limited)")}
    out = os.path.join(ROOT, "data", "hardware", f"quantinuum_devices_{stamp}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        raise SystemExit(f"{out} exists")
    with open(out, "w") as fh:
        json.dump(rec, fh, indent=1)
    print(f"{len(rows)} device(s); fingerprint {rec['fingerprint_sha256'][:16]}; wrote {os.path.relpath(out, ROOT)}")
    return 0


def do_logout():
    import qnexus as qnx

    qnx.logout()
    print("logged out (qnexus deleted its stored tokens)")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(description="Quantinuum Nexus account (no secret ever on argv)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--login", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--logout", action="store_true")
    g.add_argument("--status", action="store_true")
    ap.add_argument("--credentials", action="store_true",
                    help="--login with e-mail/password prompts instead of the browser (hidden prompt)")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.login:
        return do_login(args.credentials)
    if args.check:
        return do_check()
    if args.logout:
        return do_logout()
    print(json.dumps(token_store_status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

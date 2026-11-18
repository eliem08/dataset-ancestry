import argparse
import csv
import json
import os
import sys

from .core import USES, Lineage, hash_dir
from .licenses import LICENSES, lookup


def build_parser():
    ap = argparse.ArgumentParser(prog="dataset-ancestry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("report", "dot"):
        p = sub.add_parser(name)
        p.add_argument("manifest")
        p.add_argument("dataset")
    c = sub.add_parser("check")
    c.add_argument("manifest")
    c.add_argument("dataset")
    c.add_argument(
        "--use",
        required=True,
        choices=USES,
    )
    h = sub.add_parser("hash")
    h.add_argument("dir")
    lic = sub.add_parser("licenses", help="list recognised licences, or look one name up")
    lic.add_argument("name", nargs="?", help="a licence name as written in your manifest, e.g. 'CC BY-SA 3.0'")
    return ap


def _run(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "licenses":
        if a.name:
            found = lookup(a.name)
            if not found:
                print(f"{a.name!r} is not recognised; it will be reported as an unknown licence")
                return 1
            canon, flags = found
            print(f"{a.name!r} -> {canon}: {', '.join(sorted(flags)) or 'no obligations'}")
            return 0
        for canon, flags in LICENSES.items():
            print(f"{canon:<24} {', '.join(f'{k}={v}' if v is not True else k for k, v in flags.items()) or '-'}")
        print("plus every Creative Commons licence and version (CC-BY, -SA, -NC, -ND, 1.0 to 4.0, ported)")
        return 0
    if a.cmd == "hash":
        print(json.dumps(hash_dir(a.dir), indent=2))
        return 0
    lin = Lineage.load(a.manifest)
    if a.cmd == "dot":
        print(lin.to_dot(a.dataset))
        return 0
    if a.cmd == "check":
        ok, reasons = lin.check(a.dataset, a.use)
        print(f"{a.use}: {'ALLOWED' if ok else 'BLOCKED'}")
        for r in reasons:
            print(f"  - {r}")
        return 0 if ok else 2
    ob = lin.obligations(a.dataset)
    print(
        f"Ancestry of {a.dataset}: {len(lin.ancestors(a.dataset))} ancestors, sources: {', '.join(lin.sources(a.dataset))}"
    )
    for field_name, value in ob.__dict__.items():
        if value:
            print(f"  {field_name}: {value}")
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

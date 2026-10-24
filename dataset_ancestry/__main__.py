import argparse
import json
import sys

from .core import Lineage, hash_dir


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dataset-ancestry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("report", "dot"):
        p = sub.add_parser(name)
        p.add_argument("manifest")
        p.add_argument("dataset")
    c = sub.add_parser("check")
    c.add_argument("manifest")
    c.add_argument("dataset")
    c.add_argument("--use", required=True, choices=["commercial_training", "research", "redistribution", "commercial_redistribution"])
    h = sub.add_parser("hash")
    h.add_argument("dir")
    a = ap.parse_args(argv)
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
    print(f"Ancestry of {a.dataset}: {len(lin.ancestors(a.dataset))} ancestors, sources: {', '.join(lin.sources(a.dataset))}")
    for field_name, value in ob.__dict__.items():
        if value:
            print(f"  {field_name}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

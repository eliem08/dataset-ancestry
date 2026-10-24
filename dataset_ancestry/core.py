"""Dataset lineage graph, content hashing and licence-obligation propagation."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

__all__ = ["LICENSES", "Lineage", "hash_dir", "Obligations"]

# flags: by=attribution, sa=share-alike/copyleft, nc=non-commercial, nd=no-derivatives, known=recognised
LICENSES = {
    "CC0-1.0": {}, "public-domain": {}, "MIT": {"by": True}, "Apache-2.0": {"by": True}, "BSD-3-Clause": {"by": True},
    "CC-BY-4.0": {"by": True}, "CC-BY-SA-4.0": {"by": True, "sa": "CC-BY-SA"}, "CC-BY-NC-4.0": {"by": True, "nc": True},
    "CC-BY-NC-SA-4.0": {"by": True, "nc": True, "sa": "CC-BY-NC-SA"}, "CC-BY-ND-4.0": {"by": True, "nd": True},
    "CC-BY-NC-ND-4.0": {"by": True, "nc": True, "nd": True}, "ODC-By-1.0": {"by": True}, "ODbL-1.0": {"by": True, "sa": "ODbL"},
    "GPL-3.0": {"by": True, "sa": "GPL"}, "proprietary-owned": {"owned": True}, "proprietary-licensed": {"restricted": True},
}


@dataclass
class Obligations:
    attribution: list = field(default_factory=list)
    non_commercial: list = field(default_factory=list)
    share_alike: dict = field(default_factory=dict)  # family -> [datasets]
    no_derivatives: list = field(default_factory=list)
    restricted: list = field(default_factory=list)
    unknown: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_dir(path: str) -> dict:
    """Return per-file hashes and a root hash over the sorted (relpath, hash) pairs."""
    files = {}
    for r, dirs, fs in os.walk(path):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for f in sorted(fs):
            full = os.path.join(r, f)
            files[os.path.relpath(full, path).replace("\\", "/")] = _file_hash(full)
    root = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(files.items())).encode()).hexdigest()
    return {"root": root, "files": files}


class Lineage:
    def __init__(self, datasets: dict):
        self.ds = datasets
        for name, d in datasets.items():
            for p in d.get("parents", []):
                if p not in datasets:
                    raise ValueError(f"{name} references unknown parent {p}")
            if not d.get("parents") and "license" not in d:
                raise ValueError(f"source dataset {name} has no license")

    @classmethod
    def load(cls, path: str) -> "Lineage":
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh)["datasets"])

    def ancestors(self, name: str) -> list[str]:
        """All ancestors (excluding self), parents before grandparents, cycle-checked."""
        seen, order, stack = set(), [], set()

        def visit(n):
            if n in stack:
                raise ValueError(f"cycle detected at {n}")
            stack.add(n)
            for p in self.ds[n].get("parents", []):
                if p not in seen:
                    seen.add(p)
                    order.append(p)
                    visit(p)
            stack.discard(n)

        visit(name)
        return order

    def sources(self, name: str) -> list[str]:
        nodes = [name] + self.ancestors(name)
        return [n for n in nodes if not self.ds[n].get("parents")]

    def obligations(self, name: str) -> Obligations:
        ob = Obligations()
        for src in self.sources(name):
            lic = self.ds[src].get("license", "")
            flags = LICENSES.get(lic)
            if flags is None:
                ob.unknown.append(f"{src} ({lic or 'none'})")
                continue
            if flags.get("by"):
                ob.attribution.append(self.ds[src].get("attribution", src) + f" [{lic}]")
            if flags.get("nc"):
                ob.non_commercial.append(src)
            if flags.get("sa"):
                ob.share_alike.setdefault(flags["sa"], []).append(src)
            if flags.get("nd"):
                ob.no_derivatives.append(src)
            if flags.get("restricted"):
                ob.restricted.append(src)
        if len(ob.share_alike) > 1:
            ob.conflicts.append(f"incompatible share-alike licences combined: {sorted(ob.share_alike)}")
        if ob.share_alike and any(LICENSES.get(self.ds[s].get("license"), {}).get("owned") for s in self.sources(name)):
            ob.conflicts.append("share-alike data merged with proprietary data: the derivative must be released under the SA licence")
        if ob.no_derivatives and self.ds[name].get("parents"):
            ob.conflicts.append(f"derivative built from no-derivatives sources: {ob.no_derivatives}")
        return ob

    def check(self, name: str, use: str) -> tuple[bool, list[str]]:
        ob = self.obligations(name)
        reasons = list(ob.conflicts)
        if ob.unknown:
            reasons.append(f"unknown licences: {ob.unknown}")
        if use in ("commercial_training", "redistribution", "commercial_redistribution") and ob.non_commercial:
            reasons.append(f"non-commercial ancestors: {ob.non_commercial}")
        if use in ("redistribution", "commercial_redistribution") and ob.restricted:
            reasons.append(f"third-party proprietary ancestors can't be redistributed: {ob.restricted}")
        if use == "redistribution" and any(LICENSES.get(self.ds[s].get("license"), {}).get("owned") for s in self.sources(name)):
            reasons.append("contains your own proprietary data - redistribution would publish it")
        notes = []
        if ob.attribution:
            notes.append(f"attribution required: {len(ob.attribution)} source(s)")
        if ob.share_alike and use != "research":
            notes.append(f"share-alike applies to derived datasets: {sorted(ob.share_alike)}")
        return (not reasons), reasons + notes

    def verify(self, name: str, data_dir: str) -> tuple[bool, str]:
        expected = self.ds[name].get("root_hash")
        if not expected:
            return False, "no root_hash recorded in manifest"
        actual = hash_dir(data_dir)["root"]
        return (actual == expected), ("match" if actual == expected else f"drift: manifest {expected[:12]} != disk {actual[:12]}")

    def to_dot(self, name: str) -> str:
        nodes = [name] + self.ancestors(name)
        lines = ["digraph lineage {", "  rankdir=BT;", "  node [shape=box, style=rounded];"]
        for n in nodes:
            d = self.ds[n]
            label = n + (f"\\n{d['license']}" if "license" in d else f"\\n({d.get('transform', 'derived')})")
            color = "red" if LICENSES.get(d.get("license", ""), {}).get("nc") else "black"
            lines.append(f'  "{n}" [label="{label}", color={color}];')
            for p in d.get("parents", []):
                lines.append(f'  "{p}" -> "{n}";')
        lines.append("}")
        return "\n".join(lines)

"""Dataset lineage graph, content hashing and licence-obligation propagation."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

from .licenses import LICENSES, lookup

__all__ = ["LICENSES", "USES", "Lineage", "hash_dir", "Obligations"]

USES = ("commercial_training", "research", "redistribution", "commercial_redistribution")


@dataclass
class Obligations:
    attribution: list = field(default_factory=list)
    non_commercial: list = field(default_factory=list)
    share_alike: dict = field(default_factory=dict)  # family -> [datasets]
    no_derivatives: list = field(default_factory=list)
    restricted: list = field(default_factory=list)
    unknown: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    weak_copyleft: list = field(default_factory=list)
    use_policy: list = field(default_factory=list)  # acceptable-use terms to pass on downstream
    user_cap: list = field(default_factory=list)  # separate licence needed above 700M monthly users
    model_naming: list = field(default_factory=list)  # derived models must carry the licensor's name
    other_llm_ban: list = field(default_factory=list)  # may not be used to improve other LLMs


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
    def load(cls, path: str) -> Lineage:
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
        if not isinstance(doc, dict) or not isinstance(doc.get("datasets"), dict):
            raise ValueError(f"{path}: expected an object with a 'datasets' map")
        return cls(doc["datasets"])

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
        nodes = [name, *self.ancestors(name)]
        return [n for n in nodes if not self.ds[n].get("parents")]

    def obligations(self, name: str) -> Obligations:
        ob = Obligations()
        for src in self.sources(name):
            lic = self.ds[src].get("license", "")
            found = lookup(lic)
            if found is None:
                ob.unknown.append(f"{src} ({lic or 'none'})")
                continue
            lic, flags = found
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
            for flag, bucket in (
                ("weak", ob.weak_copyleft),
                ("use_policy", ob.use_policy),
                ("mau_cap", ob.user_cap),
                ("naming", ob.model_naming),
                ("no_other_llm", ob.other_llm_ban),
            ):
                if flags.get(flag):
                    bucket.append(f"{src} [{lic}]")
        families = set(ob.share_alike)
        cc_sa_4 = all(
            (lookup(self.ds[s].get("license", "")) or ("",))[0] == "CC-BY-SA-4.0"
            for s in ob.share_alike.get("CC-BY-SA", [])
        )
        if families == {"CC-BY-SA", "GPL"} and cc_sa_4:
            pass  # CC BY-SA 4.0 lists GPLv3 as a compatible licence: the combination must be released as GPLv3
        elif len(families) > 1:
            ob.conflicts.append(f"incompatible share-alike licences combined: {sorted(ob.share_alike)}")
        if ob.share_alike and any(
            (lookup(self.ds[s].get("license", "")) or ("", {}))[1].get("owned") for s in self.sources(name)
        ):
            ob.conflicts.append(
                "share-alike data merged with proprietary data: the derivative must be released under the SA licence"
            )
        if ob.no_derivatives and self.ds[name].get("parents"):
            ob.conflicts.append(f"derivative built from no-derivatives sources: {ob.no_derivatives}")
        return ob

    def check(self, name: str, use: str) -> tuple[bool, list[str]]:
        if use not in USES:  # an unknown use must never fall through to "allowed"
            raise ValueError(f"use must be one of {list(USES)}, got {use!r}")
        ob = self.obligations(name)
        reasons = list(ob.conflicts)
        if ob.unknown:
            reasons.append(f"unknown licences: {ob.unknown}")
        if use in ("commercial_training", "redistribution", "commercial_redistribution") and ob.non_commercial:
            reasons.append(f"non-commercial ancestors: {ob.non_commercial}")
        if use in ("redistribution", "commercial_redistribution") and ob.restricted:
            reasons.append(f"third-party proprietary ancestors can't be redistributed: {ob.restricted}")
        if use == "redistribution" and any(
            (lookup(self.ds[s].get("license", "")) or ("", {}))[1].get("owned") for s in self.sources(name)
        ):
            reasons.append("contains your own proprietary data - redistribution would publish it")
        notes = []
        if ob.attribution:
            notes.append(f"attribution required: {len(ob.attribution)} source(s)")
        if ob.share_alike and use != "research":
            notes.append(f"share-alike applies to derived datasets: {sorted(ob.share_alike)}")
            if set(ob.share_alike) == {"CC-BY-SA", "GPL"}:
                notes.append("CC BY-SA 4.0 + GPLv3: release the combined dataset under GPLv3 (one-way compatibility)")
        if ob.other_llm_ban and use in ("commercial_training", "research"):
            notes.append(
                f"Llama 2 terms: these may not be used to improve any LLM other than Llama 2 and its derivatives: "
                f"{ob.other_llm_ban}"
            )
        if ob.use_policy:
            notes.append(f"acceptable-use terms must be passed on to your users: {ob.use_policy}")
        if ob.user_cap and use.startswith("commercial"):
            notes.append(f"over 700 million monthly active users needs a separate licence from Meta: {ob.user_cap}")
        if ob.model_naming and use == "commercial_training":
            notes.append(
                f"a model trained on these must carry the licensor's name (e.g. 'Llama ...'): {ob.model_naming}"
            )
        if ob.weak_copyleft and use != "research":
            notes.append(f"weak copyleft: modified files stay under their licence: {ob.weak_copyleft}")
        return (not reasons), reasons + notes

    def verify(self, name: str, data_dir: str) -> tuple[bool, str]:
        expected = self.ds[name].get("root_hash")
        if not expected:
            return False, "no root_hash recorded in manifest"
        actual = hash_dir(data_dir)["root"]
        return (actual == expected), (
            "match" if actual == expected else f"drift: manifest {expected[:12]} != disk {actual[:12]}"
        )

    def to_dot(self, name: str) -> str:
        nodes = [name, *self.ancestors(name)]
        lines = ["digraph lineage {", "  rankdir=BT;", "  node [shape=box, style=rounded];"]
        for n in nodes:
            d = self.ds[n]
            label = n + (f"\\n{d['license']}" if "license" in d else f"\\n({d.get('transform', 'derived')})")
            color = "red" if (lookup(d.get("license", "")) or ("", {}))[1].get("nc") else "black"
            lines.append(f'  "{n}" [label="{label}", color={color}];')
            for p in d.get("parents", []):
                lines.append(f'  "{p}" -> "{n}";')
        lines.append("}")
        return "\n".join(lines)

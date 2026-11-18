"""Licence table: Creative Commons (every version, by pattern), common SPDX software and data licences, and
AI model licences. Names are matched without regard to case, spaces, underscores or a trailing "license".

Flags:
  by        attribution or licence notice must travel with the data
  sa        share-alike / copyleft family; derived data must use the same licence
  weak      weak copyleft (modified files stay under the licence; the whole need not)
  nc        non-commercial only
  nd        no derivatives
  owned     your own proprietary data
  restricted  someone else's proprietary data under contract
  use_policy  an acceptable-use policy that must be passed on to downstream users
  mau_cap   needs a separate licence above 700 million monthly active users (Llama)
  naming    derived models must carry the licensor's name (Llama 3 and later)
  no_other_llm  outputs may not be used to improve other large language models (Llama 2)

This is a decision aid, not legal advice: it reads the licence names you record, not the licence texts.
"""

from __future__ import annotations

import re

LICENSES: dict[str, dict] = {
    # public domain and permissive
    "CC0-1.0": {},
    "public-domain": {},
    "PDDL-1.0": {},
    "Unlicense": {},
    "0BSD": {},
    "CC-PDDC": {},
    "MIT": {"by": True},
    "ISC": {"by": True},
    "Zlib": {"by": True},
    "Apache-2.0": {"by": True},
    "BSD-2-Clause": {"by": True},
    "BSD-3-Clause": {"by": True},
    "ODC-By-1.0": {"by": True},
    "CDLA-Permissive-1.0": {"by": True},
    "CDLA-Permissive-2.0": {"by": True},
    "OGL-UK-3.0": {"by": True},
    "Etalab-2.0": {"by": True},
    "DL-DE-BY-2.0": {"by": True},
    # copyleft
    "ODbL-1.0": {"by": True, "sa": "ODbL"},
    "CDLA-Sharing-1.0": {"by": True, "sa": "CDLA-Sharing"},
    "GPL-2.0-only": {"by": True, "sa": "GPL-2.0"},
    "GPL-2.0-or-later": {"by": True, "sa": "GPL"},
    "GPL-3.0-only": {"by": True, "sa": "GPL"},
    "GPL-3.0-or-later": {"by": True, "sa": "GPL"},
    "AGPL-3.0-only": {"by": True, "sa": "GPL"},  # GPLv3 section 13 allows combining with AGPLv3
    "AGPL-3.0-or-later": {"by": True, "sa": "GPL"},
    "LGPL-2.1-only": {"by": True, "weak": True},
    "LGPL-2.1-or-later": {"by": True, "weak": True},
    "LGPL-3.0-only": {"by": True, "weak": True},
    "LGPL-3.0-or-later": {"by": True, "weak": True},
    "MPL-2.0": {"by": True, "weak": True},
    "EPL-2.0": {"by": True, "weak": True},
    # AI model licences
    "OpenRAIL": {"by": True, "use_policy": True},
    "OpenRAIL-M": {"by": True, "use_policy": True},
    "BigScience-OpenRAIL-M": {"by": True, "use_policy": True},
    "CreativeML-OpenRAIL-M": {"by": True, "use_policy": True},
    "BigCode-OpenRAIL-M": {"by": True, "use_policy": True},
    "Llama-2": {"by": True, "use_policy": True, "mau_cap": True, "no_other_llm": True},
    "Llama-3": {"by": True, "use_policy": True, "mau_cap": True, "naming": True},
    "Llama-3.1": {"by": True, "use_policy": True, "mau_cap": True, "naming": True},
    "Llama-3.2": {"by": True, "use_policy": True, "mau_cap": True, "naming": True},
    "Llama-3.3": {"by": True, "use_policy": True, "mau_cap": True, "naming": True},
    "Llama-4": {"by": True, "use_policy": True, "mau_cap": True, "naming": True},
    "Gemma": {"by": True, "use_policy": True},
    # proprietary
    "proprietary-owned": {"owned": True},
    "proprietary-licensed": {"restricted": True},
}

ALIASES = {
    "pd": "public-domain",
    "publicdomain": "public-domain",
    "cc0": "CC0-1.0",
    "apache": "Apache-2.0",
    "apache2": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "bsd": "BSD-3-Clause",
    "bsd-3": "BSD-3-Clause",
    "bsd-2": "BSD-2-Clause",
    "odc-pddl": "PDDL-1.0",
    "odc-pddl-1.0": "PDDL-1.0",
    "odc-by": "ODC-By-1.0",
    "odbl": "ODbL-1.0",
    "gpl-2.0": "GPL-2.0-only",
    "gpl-3.0": "GPL-3.0-only",
    "gplv2": "GPL-2.0-only",
    "gplv3": "GPL-3.0-only",
    "agpl-3.0": "AGPL-3.0-only",
    "lgpl-2.1": "LGPL-2.1-only",
    "lgpl-3.0": "LGPL-3.0-only",
    "llama2": "Llama-2",
    "llama-2-community": "Llama-2",
    "llama3": "Llama-3",
    "llama3.1": "Llama-3.1",
    "llama3.2": "Llama-3.2",
    "llama3.3": "Llama-3.3",
    "llama4": "Llama-4",
    "gemma-terms-of-use": "Gemma",
    "bigscience-bloom-rail-1.0": "BigScience-OpenRAIL-M",
    "creativeml-openrail": "CreativeML-OpenRAIL-M",
}

CC = re.compile(r"^cc-?(by(?:-nc)?(?:-sa|-nd)?)(?:-(\d\.\d))?(?:-[a-z]{2,3})?$")
_LOWER = {k.lower(): k for k in LICENSES}


def _key(name: str) -> str:
    s = str(name).strip().lower().replace("_", "-").replace(" ", "-")
    s = re.sub(r"-(community-)?licen[cs]e(-agreement)?$", "", s)
    s = re.sub(r"^(meta-)?llama-?(\d(?:\.\d)?)$", r"llama\2", s)
    return re.sub(r"-+", "-", s)


def lookup(name: str) -> tuple[str, dict] | None:
    """(canonical id, flags) for a licence name, or None when it is not recognised."""
    if not name:
        return None
    k = _key(name)
    k = ALIASES.get(k, k)
    if k in LICENSES:
        return k, LICENSES[k]
    if k.lower() in _LOWER:
        canon = _LOWER[k.lower()]
        return canon, LICENSES[canon]
    m = CC.match(k.lower())
    if m:  # every Creative Commons variant and version; ported versions (-fr, -de) share the flags
        parts = m.group(1).split("-")
        flags: dict = {"by": True}
        if "nc" in parts:
            flags["nc"] = True
        if "nd" in parts:
            flags["nd"] = True
        if "sa" in parts:
            flags["sa"] = "CC-BY-NC-SA" if "nc" in parts else "CC-BY-SA"
        canon = f"CC-{m.group(1).upper()}" + (f"-{m.group(2)}" if m.group(2) else "")
        return canon, flags
    return None

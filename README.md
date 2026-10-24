# dataset-ancestry

[![CI](https://github.com/eliem08/dataset-ancestry/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/dataset-ancestry/actions/workflows/ci.yml)

> **Ancestry for datasets** — where your training data came from.

"Is this fine-tuning set safe to use commercially?" Nobody can answer,
because the set was built from a filtered merge of a scrape of a dataset that
was CC-BY-NC three hops back. `dataset-ancestry` records dataset lineage as
a graph, propagates licence obligations from every ancestor, and tells you
what you may do with the result.

## What the MVP does

- **Lineage manifest** (`ancestry.json`): source datasets (licence, URL, content hash)
  and derived datasets (transform, parents)
- **Content fingerprints**: SHA-256 per file and a Merkle-style dataset root hash;
  `verify` detects drift between manifest and files on disk
- **Ancestor resolution** with cycle detection
- **Licence propagation** over the full ancestry:
  - attribution list (every `BY` ancestor)
  - `NC` (non-commercial) and `SA` / copyleft (share-alike) inherited
  - `ND` ancestors block derivatives entirely
  - unknown / proprietary licences flagged
  - incompatible combinations (e.g. CC-BY-SA + CC-BY-NC-SA vs GPL) reported
- **Use check**: `commercial_training`, `research`, `redistribution` → allowed / blocked + reasons
- **Graph export** to Graphviz DOT

## Quickstart

```bash
pip install -e .
dataset-ancestry report examples/ancestry.json my-finetune-v3
dataset-ancestry check examples/ancestry.json my-finetune-v3 --use commercial_training
dataset-ancestry dot examples/ancestry.json my-finetune-v3 > lineage.dot
dataset-ancestry hash ./data/my-finetune-v3
```

Licence rules are a simplified model for triage — not legal advice.

## Roadmap

- Auto-ingest lineage from Hugging Face dataset cards and data pipeline runs (dbt, Airflow)
- Sample-level provenance (which rows came from which ancestor) for takedown requests
- Signed provenance attestations (in-toto / SLSA style) for model releases

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
dataset_ancestry/core.py       domain logic (pure, importable, fully tested)
dataset_ancestry/__main__.py   CLI (`dataset-ancestry ...` / `python -m dataset_ancestry ...`)
tests/                unit tests + generated CLI smoke tests
examples/             sample inputs used by the docs and smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #34).

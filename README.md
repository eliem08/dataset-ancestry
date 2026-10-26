<!-- sell-kit:start -->
# Dataset Ancestry

[![CI](https://github.com/eliem08/dataset-ancestry/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/dataset-ancestry/actions/workflows/ci.yml)

> **Know where your training data came from and what you are allowed to do with it.**

**Who it's for:** ML teams and legal counsel shipping models trained on mixed datasets.

**The problem:** Fine-tuning sets are merges of scrapes of datasets, and nobody can say whether commercial use is allowed.

**What you get:** A lineage graph that propagates licence obligations from every source, checks a proposed use and verifies content hashes against the manifest.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install dataset_ancestry-0.1.0-py3-none-any.whl
dataset-ancestry report examples/ancestry.json my-finetune-v3
dataset-ancestry check examples/ancestry.json instruct-mix --use commercial_training
dataset-ancestry dot examples/ancestry.json my-finetune-v3
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
dataset-ancestry-web --port 8000          # then open http://127.0.0.1:8000
dataset-ancestry-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t dataset-ancestry . && docker run -p 8000:8000 -e API_KEYS=sk_... -v dataset-ancestry-data:/data dataset-ancestry
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `dataset-ancestry-web usage` prints calls per key for billing.

Endpoints: `POST /api/report`, `POST /api/dot`, `POST /api/check`, `POST /api/hash`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Deploy and sell

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/eliem08/dataset-ancestry)

`render.yaml` (one click, above) and `fly.toml` (`fly launch --copy-config`) both run the Dockerfile with a persistent `/data` volume and a `/healthz` check.
To sell self-serve, set four variables and point a Stripe webhook at `https://<your-host>/billing/webhook` (events `checkout.session.completed` and `customer.subscription.deleted`):

| Variable | Example |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `STRIPE_PRICES` | `team=price_123,business=price_456` |
| `PUBLIC_URL` | `https://dataset-ancestry.example.com` |

Buyers pick a plan on `/pricing`, pay on Stripe Checkout and see their API key once on the success page. Cancelling the subscription revokes the key. A selling server always requires a key.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Team** | $99 per month | Unlimited lineage graphs; Use checks; Hash verification |
| **Business** | $499 per month | Audit-ready reports; Custom licence library; Multiple teams |
| **Enterprise** | $2,000 per month | Legal review workflow; On-prem; SLA |

To start a trial or buy a plan, [request access](https://github.com/eliem08/dataset-ancestry/issues/new?title=Dataset%20Ancestry%20trial&labels=sales).

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

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

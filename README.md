# Backstory

Graph-native long-term memory for conversational agents.

Hack Hydra Track 03 — Memory and Context Retrieval.

Tell it something once. Come back later. It still knows what changed, and it
will say so when the history does not contain the answer.

HydraDB OSS (`graph-node`) is the source of truth for facts, entities,
SUPERSEDES, CONTRADICTS, and evidence quotes. A SQLite sidecar only allocates
integer ids and holds rebuildable indexes. Hydra Cloud is not used.

This repository does **not** claim a LongMemEval-S score. Commands below are
the ones we actually ship.

## Requirements

- Docker Desktop
- Python 3.11+

## Run HydraDB

```powershell
cd backstory
docker compose up -d
```

Wait until `http://127.0.0.1:9090/readyz` returns 200.

## Install and smoke-test HydraDB

```powershell
python -m pip install -e ".[dev]"
python -m backstory.tools.smoke_hydradb
```

That script writes real nodes/edges, queries current vs historical state,
checks SUPERSEDES and CONTRADICTS, confirms `IS NULL` and undirected patterns
are rejected, then can be re-run with `--persist-only` after a container
restart.

```powershell
docker compose restart hydradb
python -m backstory.tools.smoke_hydradb --persist-only
```

If smoke fails, fix HydraDB integration. Do not fall back to Postgres.

## Engine tests

```powershell
pytest -q
```

## Four demos

```powershell
python -m backstory.demo.load_demo
```

Then:

```powershell
python -m backstory.api.app
```

Open http://127.0.0.1:8000 — one screen: remember, ask, evidence, timeline.

## Evaluation

Smallest offline official-shaped run (no 115k haystacks, no OpenAI):

```powershell
python -m backstory.eval.run_smoke_eval
```

LongMemEval (download the cleaned files yourself into `data/lme/`):

```powershell
python -m backstory.eval.ingest_lme --dataset data/lme/longmemeval_oracle.json --limit 10
python -m backstory.eval.ask_lme --dataset data/lme/longmemeval_oracle.json --limit 10 --out runs/oracle10.jsonl
python vendor/longmemeval/evaluate_qa.py gpt-4o runs/oracle10.jsonl data/lme/longmemeval_oracle.json
```

The last command is the official judge and needs `OPENAI_API_KEY`.

## How HydraDB is used

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

If HydraDB were replaced by a vector store we would lose current-vs-historical
lookup, SUPERSEDES lineage, CONTRADICTS as structure, and constraint-aware
abstention that is not “nearest neighbor ≠ empty.”

## License

MIT for Backstory. HydraDB is AGPL-3.0 and runs as a separate Docker service.
See NOTICE.

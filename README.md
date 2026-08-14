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

LongMemEval oracle (download the cleaned files yourself into `data/lme/`,
from https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned).
Everything below is driven by `backstory.eval.run_official`, which ingests
each instance's haystack sessions in date order, asks Backstory, writes
`{question_id, hypothesis}` jsonl, and (if `OPENAI_API_KEY` is set) invokes
the official judge itself:

```powershell
# One question, ingest+ask only, no judge call:
python -m backstory.eval.run_official --dataset data/lme/longmemeval_oracle.json --ids 6aeb4375 --skip-official-judge

# A stratified 12-question slice (2 per official type) across the full 500:
python -m backstory.eval.slice_lme --dataset data/lme/longmemeval_oracle.json --per-type 2 --out data/lme/oracle_strat12.json
python -m backstory.eval.run_official --dataset data/lme/oracle_strat12.json --limit 0 --out-dir runs/lme/strat12 --skip-official-judge

# Same slice, official judge (needs OPENAI_API_KEY; scores gpt-4o-2024-08-06 yes/no per item):
python -m backstory.eval.run_official --dataset data/lme/oracle_strat12.json --limit 0 --out-dir runs/lme/strat12

# Full LongMemEval-S 500 (slow, needs OPENAI_API_KEY):
python -m backstory.eval.run_official --dataset data/lme/longmemeval_oracle.json --limit 0
```

Each run writes `runs/lme/<out-dir>/hypotheses.jsonl`, per-question
`traces/<id>.json` (retrieval + answer), and `summary_unofficial.json`
(a loose token-overlap diagnostic — **not** the scored metric). The judge's
own output lands at `<hyp_file>.eval-results-gpt-4o` next to the hyp file,
written by `vendor/longmemeval/evaluate_qa.py` (the official scorer;
requires `OPENAI_API_KEY`, do not substitute the internal diagnostic for it).

Backstory vs. a naive-graph ablation vs. a session-RAG baseline on the same
12-question slice:

```powershell
python -m backstory.eval.run_compare
```

Writes `runs/lme/strat12/compare.json` (also unofficial contains-match; see
`docs/LONGMEMEVAL_VALIDATION.md` for the last measured numbers and caveats).

## How HydraDB is used

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

If HydraDB were replaced by a vector store we would lose current-vs-historical
lookup, SUPERSEDES lineage, CONTRADICTS as structure, and constraint-aware
abstention that is not “nearest neighbor ≠ empty.”

## License

MIT for Backstory. HydraDB is AGPL-3.0 and runs as a separate Docker service.
See NOTICE.

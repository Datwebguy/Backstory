# ARCHITECTURE VALIDATION REPORT

Validated 2026-08-14 against:

- HydraDB OSS `ghcr.io/hydra-db/hydradb:latest` (live HTTP API)
- `cypher-compat.md` and `src/query/opencypher.rs`
- LongMemEval README + official example figure
- Official `evaluate_qa.py` judge contract

This document freezes the architecture that the code implements. Claims below
were either confirmed live or are explicitly marked as remaining work.

## 1. Final schema

### Nodes

| Label | Why it exists | Required properties |
|---|---|---|
| `User` | Partition root for sessions | `user_key`, `name` |
| `Session` | Chronology + citation unit | `session_key`, `occurred_at`, `title` |
| `Message` | Turn-level provenance; **quote lives here** so evidence is graph-readable | `role`, `ordinal`, `occurred_at`, `content` |
| `Entity` | Resolution hub (people, places, orgs, things) | `canonical_key`, `name`, `entity_type` |
| `Fact` | Versioned claim | `predicate`, `object_text`, `fact_kind`, `predicate_class`, `stated_at`, `valid_from`, `valid_until`, `event_at`, `is_current`, `confidence`, `status`, `polarity`, `qualifiers`, `speaker`, `atom_hash` |
| `Decision` | Groups a choice plus supporting facts (demo D). Not required by LME types. | `question`, `choice_text`, `stated_at`, `is_final` |

**Entity + Fact + Decision collapse: kept.** Preferences, events, instructions,
people, places, projects are `fact_kind` / `entity_type` / `predicate_class`.
A separate Preference/Event/Location label would not add a query HydraDB can
run that Fact/Entity cannot. Decision stays because `BASED_ON` / `FOLLOWS` is
a different relation pattern than `SUPERSEDES` (which is same-predicate replacement).

**Removed:** `STATED` (User→Fact). Redundant with
`User -[:HAS_SESSION]-> Session <-[:STATED_IN]- Fact`. The earlier report was
inconsistent; this is the frozen name.

### Edges

`HAS_SESSION`, `CONTAINS`, `STATED_IN`, `SUPPORTED_BY`, `ABOUT`,
`OBJECT_ENTITY`, `MENTIONS`, `ALIAS_OF`, `SUPERSEDES`, `CONTRADICTS`
(both directions), `INVOLVES`, `DECIDED`, `BASED_ON`, `ABOUT_ENTITY`, `FOLLOWS`.

HydraDB UNWIND CREATE requires **exactly one label on each endpoint**, so every
edge type has a fixed (src_label, dst_label) pair. See `EDGE_LABELS` in
`src/backstory/hydra/schema.py`.

### Example queries (legal subset)

Current home:

```cypher
MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $entity_id})
WHERE f.predicate = 'lives_in' AND f.is_current = true
RETURN f.object_text AS city
```

History:

```cypher
MATCH (cur:Fact {id: $fid})-[:SUPERSEDES*1..8]->(old:Fact)
RETURN old.object_text AS city, old.stated_at AS stated_at
```

As-of (ISO strings; empty `valid_until` is `''` because `IS NULL` is rejected):

```cypher
MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $entity_id})
WHERE f.predicate = $predicate AND f.valid_from <= $as_of
  AND (f.valid_until = $open OR f.valid_until >= $as_of)
RETURN f.object_text AS city
```

## 2. Final data flow

```
session turns
  → persist Message.content in HydraDB + sidecar turn index
  → extract atoms (structured for demos/tests; LLM optional)
  → conservative entity resolve
  → ADD / SUPERSEDE / CONTRADICT / IGNORE
  → HydraDB UNWIND MERGE SET + labeled MATCH CREATE

question
  → seed entities (exact key/name/alias; lexical embed is optional extra)
  → HydraDB: ALIAS_OF*1..2, ABOUT, STATED_IN, SUPERSEDES, CONTRADICTS
  → evidence pack from graph properties (including quotes)
  → gated abstain / qualify / answer
  → template answer, or LLM if a key is present
```

## 3. HydraDB responsibilities

Source of truth for structured memory:

- all nodes and relationships
- current vs historical (`is_current`, `valid_*`)
- SUPERSEDES lineage
- CONTRADICTS pairs
- Message quotes
- bounded multi-hop and (when used) `algo.SPpaths`

Live-confirmed HydraDB rules:

- Vertex ids are integers
- UNWIND upsert = MERGE by id + **exactly one SET label**
- UNWIND CREATE endpoints = **exactly one label each**
- `IS NULL`, `CONTAINS`, `IN`, undirected patterns are rejected
- String `<=` / `>=` on ISO-8601 timestamps is the temporal filter
- Variable-length `*1..N` requires a **fixed source id** (cannot start from an unbound node)
- Docker Desktop named volumes need `user: "0:0"` or the node hits EACCES on `_writer_leases`

## 4. Sidecar responsibilities

SQLite only:

- integer id allocator
- alias / name index (rebuildable from Entity nodes)
- optional lexical embedding table for **entry-point seeds only**
- raw turn copy for working memory

The sidecar must not answer a question. Retrieval always loads facts via HydraDB.

## 5. Temporal model

Minimum that works with HydraDB:

- `stated_at`: when it was said (session clock, ISO-8601)
- `valid_from` / `valid_until`: world interval; open end is `""`
- `is_current`: boolean index because we cannot write `WHERE valid_until IS NULL`
- `event_at`: optional event time for “how many months since…”

Tradeoff: `is_current` can drift if a write fails after SUPERSEDES. Mutate
closes the old fact, then writes the edge. Tests cover out-of-order arrival:
older `stated_at` becomes historical, not current.

Relative phrases (“last month”) are resolved at ask time against `question_date`
in the reasoner, not stored as a Hydra date type (none exists).

## 6. Update model

Predicate classes:

- `unique_state` (lives_in, works_at): at most one current Fact per subject+predicate
- `set_membership` (owns): ADD, do not supersede (LME bike-count KU)
- `preference`: polarity updates via SUPERSEDES when `update_of` is set
- `event`: always ADD

Only the same `(subject, predicate)` — and for set_membership the same object —
can be invalidated. Unrelated facts are left alone.

## 7. Contradiction model

If two current unique_state values exist and the new atom has **no** update
language, write `CONTRADICTS` both ways and keep both `is_current = true`.
Ask path returns `qualify`, not a guessed city.

Like → unlike → like again uses explicit `update_of` and SUPERSEDES.

## 8. Entity-resolution model

Deterministic only in the default path:

1. `user` / `I` / `me` → `user:{user_key}` entity
2. exact `canonical_key`
3. exact alias table (`@sam` if registered)
4. unique exact name
5. else create

`Sam` and `Samuel` stay distinct unless an extractor alias links them.
`my old manager` is not auto-merged.

## 9. Abstention model

Not “empty pack or LLM shrug.” Official LME example: 10-gal and 20-gal tanks
exist; question asks about a **30-gallon** tank.

Gates:

1. no candidates → abstain
2. no relevant facts → abstain
3. asked numeric constraint unmatched → abstain
4. named entity in the question never appears in evidence → abstain
5. which/first comparison missing one alternative → abstain
6. unresolved current conflict on a “now” unique_state question → qualify
7. else answer

Thresholds were not invented as scores. The 30-gallon rule is a parsed
constraint check, tested in `tests/test_abstention.py`.

## 10. Benchmark integration

Primary: LongMemEval-S (or oracle slice).

```
python -m backstory.eval.ingest_lme --dataset data/lme/longmemeval_s_cleaned.json --limit 10
python -m backstory.eval.ask_lme --dataset data/lme/longmemeval_s_cleaned.json --limit 10 --out runs/oracle10.jsonl
python vendor/longmemeval/evaluate_qa.py gpt-4o runs/oracle10.jsonl data/lme/longmemeval_s_cleaned.json
```

The official judge requires `OPENAI_API_KEY`. Without it we run:

```
python -m backstory.eval.run_smoke_eval
```

which writes official-shaped JSON + `{question_id, hypothesis}` jsonl from the
four demos. That command is the smallest reproducible eval we can execute
offline.

LME-V2 has a first-class adapter (`backstory.eval.lme_v2_adapter` /
`run_lme_v2`) that flattens trajectory text (goal, thought, action, URL,
clipped accessibility tree) into Backstory sessions. It is **not** an
official LME-V2 evaluation: the official harness scores multimodal web
and enterprise agent trajectories (up to 500 trajectories / 115M tokens)
and this project ignores screenshots. LongMemEval-S remains the
benchmark that matches conversational memory. Do not report adapter
output as an LME-V2 leaderboard number.

BEAM is wired up and run on a slice (`backstory.eval.run_beam`). Unlike
LME-V2 it is the same problem this project addresses: multi session
conversational memory. Seven of its ten probed abilities map onto
mechanisms implemented here, which makes it a closer fit than
LongMemEval's answer-recall framing:

| BEAM ability | Backstory mechanism |
|---|---|
| `abstention` | `decide()` abstention gates |
| `contradiction_resolution` | `CONTRADICTS` edges, both directions |
| `knowledge_update` | `SUPERSEDES` lineage, `is_current` |
| `multi_session_reasoning` | ABOUT fan-in across sessions |
| `temporal_reasoning` | `valid_from` / `valid_until`, `as_of` |
| `event_ordering` | `stated_at` / `event_at` ordering |
| `preference_following` | `fact_kind=preference` |

The remaining three (`information_extraction`, `instruction_following`,
`summarization`) exercise extraction and generation quality rather than
graph structure.

Scores from that runner are labelled "judged against BEAM rubrics", not
as official BEAM scores: it uses BEAM's own published per-question
rubrics with an LLM judge, rather than BEAM's
`src/evaluation/compute_metrics.py`, which additionally requires
sentence-transformers and a LangChain model. Per-question records are
written out so the official scorer can be run over them later.

## 11. Four demo flows

| Demo | LME/BEAM type | Official-shaped example | Graph | LLM/template sees |
|---|---|---|---|---|
| A Knowledge update | `knowledge-update` | road/mountain/commuter + hybrid = 4 bikes; we also demo works_at A→B | SUPERSEDES works_at; owns is additive | current employer + history |
| B Multi-session | `multi-session` | instruments across sessions / Ada facts | Entity Ada ← ABOUT facts from 3 sessions | synthesis of current Ada facts |
| C Abstention | `_abs` | 10/20-gal tanks vs 30-gal question | owns facts exist; constraint fails | deterministic refuse |
| D Decision | BEAM event-order flavored | not an LME type | prefers MacBook SUPERSEDED, bought ThinkPad | reconstruct from BASED_ON / facts |

## 12. Known limitations

- Live UNWIND rules were only partially green when Docker Desktop flapped on
  this Windows host. Re-run `python -m backstory.tools.smoke_hydradb` after
  `docker compose up`.
- No native vector index in HydraDB OSS. Lexical 64-d bags are a seed helper.
- Entity resolution will miss Samuel↔Sam without an explicit alias.
- Extraction quality dominates LME-S if the LLM path is used; demos/tests use
  structured atoms so versioning is not hostage to extraction.
- We do not claim LME-S superiority. We have not run the 500-question set.
- Decision nodes are written only when the caller supplies them; demo D
  currently stores preference/event Facts and answers from those.

## 13. Why this is better than session vector RAG

Vector RAG returns “Lagos” and “Abuja” as similar sentences. Backstory stores
them as two Facts, one `is_current`, linked by `SUPERSEDES`, queryable as-of a
date, and will abstain when the asked slot (30-gallon) is missing even though
related tank facts exist. That is the Track 03 problem. HydraDB is where those
relationships live.

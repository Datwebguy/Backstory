# BACKSTORY — LONGMEMEVAL VALIDATION REPORT

Date: 2026-08-18

Architecture: **unchanged**. Failures below do not justify a schema or store swap.

Latest official run (2026-08-18, hybrid): heuristic extract + new
abstention/counting engine + gpt-4o-mini answers + official
`evaluate_qa.py gpt-4o` (`gpt-4o-2024-08-06`).

```
python -m backstory.eval.run_official `
  --dataset data/lme/oracle_strat12.json --limit 0 `
  --heuristic-extract --out-dir runs/lme/strat12_hybrid
```

| Official metric | Old hyps (pre-fix) | Hybrid re-ingest |
|---|---|---|
| Overall accuracy | 0.3333 (4/12) | **0.75 (9/12)** |
| Abstention (`_abs`) | 0.0 (0/2) | **1.0 (2/2)** |
| knowledge-update | 0.5 (1/2) | 1.0 (2/2) |
| temporal-reasoning (includes 2 `_abs`) | 0.5 (2/4) | 1.0 (4/4) |
| multi-session | 0.0 (0/2) | 0.5 (1/2) |
| single-session-user | 0.5 (1/2) | 1.0 (2/2) |
| single-session-preference | 0.0 (0/2) | 0.0 (0/2) |

Artifact: `runs/lme/strat12_hybrid/hypotheses.jsonl.eval-results-gpt-4o`

This is **not** a LongMemEval-S 500 score. It is not a claim that
Backstory beats RAG. Three official fails remain: clothing count
(`0a995998`), Premiere preference, Sony preference.

Earlier same-day baseline on stale template hyps:
`runs/lme/strat12/hyp_backstory.jsonl.eval-results-gpt-4o` (4/12).

## 1. Exact commands

```powershell
cd C:\Users\DELL\backstory
# official dataset (README + HF cleaned card)
python -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json', r'data\lme\longmemeval_oracle.json')"

# smallest official-path instance
python -m backstory.eval.run_official --dataset data/lme/longmemeval_oracle.json --ids e47becba --out-dir runs/lme/tiny1

# stratified 12 (2 per requested type)
python -m backstory.eval.slice_lme --dataset data/lme/longmemeval_oracle.json --per-type 2 --out data/lme/oracle_strat12.json
python -m backstory.eval.run_compare

# official hybrid re-ingest + judge (ran 2026-08-18; gpt-4o-2024-08-06; 9/12)
python -m backstory.eval.run_official --dataset data/lme/oracle_strat12.json --limit 0 --heuristic-extract --out-dir runs/lme/strat12_hybrid
```

Official README contract used:

```
export OPENAI_API_KEY=YOUR_API_KEY
python3 evaluate_qa.py gpt-4o your_hypothesis_file ../../data/longmemeval_oracle.json
```

Hypothesis format written: one jsonl line per item, `{question_id, hypothesis}`.

## 2. Environment / setup

| Item | Value |
|---|---|
| Dataset | `xiaowu0162/longmemeval-cleaned` `longmemeval_oracle.json` (500 items, 15,388,478 bytes) |
| Why oracle first | Official README’s first eval command uses oracle; only evidence sessions, not 115k fillers |
| HydraDB | `ghcr.io/hydra-db/hydradb:latest` local Docker, `/readyz` 200 |
| Extract / answer | hybrid: heuristic extract, gpt-4o-mini answers |
| Official judge | **ran** — `gpt-4o-2024-08-06`, overall **0.75** on this 12-slice |
| Required for official score | `OPENAI_API_KEY`; judge `gpt-4o`; optional org `OPENAI_ORGANIZATION` |
| Required for LLM extract/answer | same key (or compatible `OPENAI_BASE_URL`) plus extract/answer models |

## 3. Dataset / configuration

Oracle instance fields match the README: `question_id`, `question_type`, `question`, `answer`, `question_date`, `haystack_*`, `answer_session_ids`. Abstention = `question_id` ends with `_abs` (30 of 500).

Tiny: `e47becba` (single-session-user, degree).  
Main: 12 oracle items, 2 each of knowledge-update, temporal-reasoning, multi-session, single-session-user, single-session-preference, abstention.

## 4–6. Results

**Official gpt-4o judge: 4/12 (0.3333) on these hyps. Abstention 0/2.**

Unofficial contains-match (too loose; can fire on words like “and”). Use only to locate failures. It happened to match the official overall on this slice (also 4/12) but not always the same items.

| System | n | unofficial hit | unofficial acc |
|---|---|---|---|
| Backstory (Hydra + versioning) | 12 | 4 | 4/12 |
| Naive graph (ignore `is_current` at ask) | 12 | 4 | 4/12 |
| Session lexical RAG | 12 | 4 | 4/12 |

Tiny official-path check: `e47becba` → hypothesis `Business Administration` (gold match). Pipeline ingest → graph → ask → jsonl works.

### By question type (unofficial)

| Type | n | Backstory | Naive | RAG |
|---|---|---|---|---|
| knowledge-update | 2 | 1 | 1 | 1 |
| temporal-reasoning | 2 | 2 | 2 | 2 |
| multi-session | 2 | 0 | 0 | 0 |
| single-session-user | 2 | 1 | 1 | 1 |
| single-session-preference | 2 | 0 | 0 | 0 |
| abstention | 2 | 0 | 0 | 0 |

Abstained by Backstory on this slice: **0 / 12**. Both official abstention items were **answered**.

## 7. Baseline comparison

Same 12 questions, same template/heuristic (no LLM on either side).

Session RAG and Backstory hit the same unofficial boxes, **but not the same answers**.

Knowledge-update `6a1eabeb` (personal best 5K):

- Gold: `25:50` (updated in a later session; earlier session said `27:12`)
- **Backstory: `25:50`** — `personal_best` unique_state, later statement current
- **RAG: first-ranked sentence still contains `27:12`** (stale)

That is the one clean “graph/update vs bag-of-sessions” difference on this slice. It is **not** an official score.

## 8. Graph ablation

Version A: full ask path (`is_current`, CONTRADICTS, SUPERSEDES edges still in the graph).  
Version B: same stored graph, `naive=True` (treat every retrieved fact as current).

Unofficial hits identical (4/12). Ablation is **query-time only**; SUPERSEDES was still written at ingest. This slice did not contain a “now vs previously” question where ignoring `is_current` flips the unofficial bit. **Do not read this as “version edges do nothing.”** The 5K example above is the versioning effect versus RAG, not versus naive ask.

## 9. Top failures (representative)

| ID | Type | Gold | Backstory | Stage |
|---|---|---|---|---|
| `6aeb4375` | knowledge-update | four Korean restaurants | `12` | reasoning: `how many` counted all current facts, not restaurant entities |
| `0a995998` | multi-session | 3 clothing items | `11` | same counting bug |
| `6d550036` | multi-session | 2 projects | `9` | same |
| `118b2229` | SSU | 45 minutes each way | commute mentioned, duration missing | extraction (duration never atomized) |
| `8a2466db` | preference | Premiere Pro resources | `to use` | reasoning: no LLM personalization; heuristic junk object |
| `06878be2` | preference | Sony-compatible gear | restates user question | reasoning (preference questions need generation, not fact echo) |
| `gpt4_70e84552_abs` | abstention | refuse (no cow purchase) | answers about the fence | abstention: retrieved related fence evidence, did not detect missing conjunct |
| `gpt4_93159ced_abs` | abstention | refuse (not at Google) | answers about commute/hours | abstention: did not detect false premise |

## 10. Root causes

1. **No LLM** — extract + answer + official judge all need `OPENAI_API_KEY`. Heuristic extract stores turn snippets; template answer is not a reader LLM.
2. **Counting** — `how many` uses `len(current facts)`, which counts `stated` snippets.
3. **Abstention** — official `_abs` items are *false-premise / missing conjunct*, not empty graphs. Related evidence exists, so the gate says `answer`.
4. **Preference** — official gold is a rubric for a personalized recommendation. We emit a memory snippet.
5. **Unofficial metric** — token overlap is not `evaluate_qa.py`. RAG’s 27:12 line can still “hit” if a common token matches.

Not root causes: HydraDB downtime, schema labels, sidecar answering, Cypher subset (writes/reads succeeded).

## 11. Recommended next changes (not architecture)

Keep HydraDB + Fact/Entity/Decision.

1. Set `OPENAI_API_KEY` and rerun `evaluate_qa.py gpt-4o` on `runs/lme/strat12/hyp_backstory.jsonl` (and regenerate hyps with LLM extract/answer).
2. Stop using `len(facts)` for “how many”; count distinct `OBJECT_ENTITY` of the asked type.
3. Abstention: if the question is an OR of two events, require evidence for **both** or refuse.
4. Preference: when `fact_kind=preference` or Premiere/Sony-like constraints exist, generate a recommendation from those constraints (LLM reader).
5. Strengthen ablation: a real Version B would skip writing SUPERSEDES/`is_current` at ingest, not only ignore them at ask.

## 12. Does the architecture survive?

**Yes.** Nothing here requires leaving HydraDB, expanding the node zoo, or promoting the sidecar. The 5K update shows versioned facts can beat session RAG on the exact Track 03 skill. The losses are extract/reason/abstain quality, plus the missing official judge key.

## Demo ↔ official type

| Demo | Official type | Oracle-like behavior on this run |
|---|---|---|
| A Company A→B | knowledge-update | `6a1eabeb` updated 25:50 vs RAG 27:12 |
| B Ada across sessions | multi-session | counting/synthesis still weak without a reader |
| C missing school | abstention | official `_abs` are harder (false premise); our empty-slot refuse still holds on the product demo |
| D ThinkPad chain | multi-session + event order | not scored here; still product-only |

## Artifacts

- `data/lme/longmemeval_oracle.json`
- `data/lme/oracle_strat12.json`
- `runs/lme/tiny1/hypotheses.jsonl`
- `runs/lme/strat12/hyp_backstory.jsonl`
- `runs/lme/strat12/hyp_naive.jsonl`
- `runs/lme/strat12/hyp_rag.jsonl`
- `runs/lme/strat12/compare.json`
- `runs/lme/strat12/traces/*.json`

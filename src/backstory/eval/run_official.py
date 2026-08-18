"""Official LongMemEval path.

Ingest oracle/S instances in date order, ask Backstory, write
{question_id, hypothesis} jsonl, then invoke vendor/longmemeval/evaluate_qa.py.

Official contract (LongMemEval README):
  python3 evaluate_qa.py gpt-4o hyp.jsonl longmemeval_oracle.json
  OPENAI_API_KEY required for the judge (gpt-4o-2024-08-06)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from backstory.config import Settings
from backstory.engine.memory import MemoryEngine
from backstory.eval.ingest_lme import _iso, ingest_instance
from backstory.eval.slice_lme import item_type, load_dataset, slice_items
from backstory.hydra.client import HydraClient


def warn_if_local_store(context: str) -> None:
    """Long ingest dies the same way as hydra-db/hydradb#81 on local FS."""
    provider = os.getenv("CLOUD_PROVIDER", "local").strip().lower()
    if provider and provider != "local":
        return
    print(
        f"WARNING [{context}]: HydraDB is probably on CLOUD_PROVIDER=local. "
        "Short smoke runs are fine; a 500-question or BEAM ingest can hit "
        "hydra-db/hydradb#81 (PutMode::Update not implemented). "
        "For long runs use docker compose -f docker-compose.yml "
        "-f docker-compose.s3.yml up -d after filling .env."
    )


def write_trace(path: Path, item: dict, answer, seeds: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "question_id": item["question_id"],
        "question_type": item_type(item),
        "question": item["question"],
        "gold": item.get("answer"),
        "hypothesis": answer.text,
        "action": answer.action,
        "reason": answer.reason,
        "seed_ids": seeds,
        "evidence": [
            {
                "fact_id": fact.fact_id,
                "predicate": fact.predicate,
                "object_text": fact.object_text[:240],
                "is_current": fact.is_current,
                "status": fact.status,
                "stated_at": fact.stated_at,
            }
            for fact in answer.evidence[:12]
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def unofficial_contains(gold: str, hyp: str) -> bool:
    g = " ".join(str(gold).lower().split())
    h = " ".join(str(hyp).lower().split())
    if len(g) < 4:
        return g in h
    tokens = [t for t in g.replace("(", " ").replace(")", " ").split() if len(t) > 2]
    if not tokens:
        return g in h
    return sum(1 for t in tokens if t in h) >= max(1, len(tokens) // 3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/lme/longmemeval_oracle.json")
    parser.add_argument("--per-type", type=int, default=0, help="0 = use --limit from file start")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--ids", default="", help="comma-separated question_ids")
    parser.add_argument("--out-dir", default="runs/lme")
    parser.add_argument("--naive-graph", action="store_true")
    parser.add_argument("--skip-official-judge", action="store_true")
    parser.add_argument(
        "--judge-only",
        action="store_true",
        help="Score an existing hypotheses.jsonl with evaluate_qa.py gpt-4o; no ingest",
    )
    parser.add_argument("--hyp", default="", help="Hypothesis jsonl for --judge-only")
    parser.add_argument(
        "--heuristic-extract",
        action="store_true",
        help="Skip per-turn LLM extract; keep LLM answers and the official judge",
    )
    args = parser.parse_args()

    if args.judge_only:
        hyp_path = Path(args.hyp or Path(args.out_dir) / "hypotheses.jsonl")
        return _run_official_judge(hyp_path, args.dataset)

    warn_if_local_store("longmemeval")
    items = load_dataset(Path(args.dataset))
    if args.ids:
        wanted = {part.strip() for part in args.ids.split(",") if part.strip()}
        items = [item for item in items if item["question_id"] in wanted]
    elif args.per_type:
        items = slice_items(items, args.per_type)
    elif args.limit:
        items = items[: args.limit]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / "sidecar"
    settings = Settings(
        backstory_data_dir=data_dir,
        backstory_llm_extract=not args.heuristic_extract,
    )
    engine = MemoryEngine(settings=settings, hydra=HydraClient(settings))
    hyp_path = out_dir / "hypotheses.jsonl"
    traces_dir = out_dir / "traces"

    if not engine.hydra.ready():
        print("HydraDB is not ready")
        return 2

    rows = []
    try:
        with hyp_path.open("w", encoding="utf-8") as handle:
            for item in items:
                print("INGEST", item["question_id"], item_type(item), flush=True)
                ingest_instance(engine, item)
                seeds = engine.retriever.seed_entities(item["question"], f"lme:{item['question_id']}")
                answer = engine.ask(
                    user_key=f"lme:{item['question_id']}",
                    question=item["question"],
                    question_date=_iso(item.get("question_date") or ""),
                    naive=args.naive_graph,
                )
                rec = {"question_id": item["question_id"], "hypothesis": answer.text}
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
                handle.flush()
                write_trace(traces_dir / f"{item['question_id']}.json", item, answer, seeds)
                hit = unofficial_contains(str(item.get("answer") or ""), answer.text)
                rows.append({**rec, "type": item_type(item), "action": answer.action, "unofficial_contains": hit})
                print("ASK", item["question_id"], answer.action, "contains", hit, flush=True)
    finally:
        engine.close()

    summary = {
        "n": len(rows),
        "unofficial_contains": sum(1 for r in rows if r["unofficial_contains"]),
        "by_type": {},
        "official_judge": None,
        "note": "unofficial_contains is diagnostic only; official judge is evaluate_qa.py gpt-4o",
    }
    for row in rows:
        bucket = summary["by_type"].setdefault(row["type"], {"n": 0, "contains": 0, "abstain": 0})
        bucket["n"] += 1
        bucket["contains"] += int(row["unofficial_contains"])
        bucket["abstain"] += int(row["action"] == "abstain")
    (out_dir / "summary_unofficial.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if args.skip_official_judge:
        return 0
    return _run_official_judge(hyp_path, args.dataset)


def _run_official_judge(hyp_path: Path, dataset: str) -> int:
    if not hyp_path.exists():
        print(f"Hypothesis file missing: {hyp_path}")
        return 2
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY missing: official evaluate_qa.py was not run.")
        print("Required: OPENAI_API_KEY and judge model gpt-4o (gpt-4o-2024-08-06).")
        print("This is not an official LongMemEval number.")
        return 0
    cmd = [
        sys.executable,
        "vendor/longmemeval/evaluate_qa.py",
        "gpt-4o",
        str(hyp_path),
        dataset,
    ]
    print("OFFICIAL", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())

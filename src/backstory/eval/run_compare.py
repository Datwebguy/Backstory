"""One ingest, then Backstory / naive-graph / session-RAG on the same slice."""

from __future__ import annotations

import json
from pathlib import Path

from backstory.config import Settings
from backstory.engine.memory import MemoryEngine
from backstory.eval.baselines import rag_answer
from backstory.eval.ingest_lme import _iso, ingest_instance
from backstory.eval.run_official import unofficial_contains, write_trace
from backstory.eval.slice_lme import item_type, load_dataset
from backstory.hydra.client import HydraClient


def main() -> None:
    dataset = Path("data/lme/oracle_strat12.json")
    items = load_dataset(dataset)
    out_dir = Path("runs/lme/strat12")
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(backstory_data_dir=out_dir / "sidecar")
    engine = MemoryEngine(settings=settings, hydra=HydraClient(settings))
    if not engine.hydra.ready():
        raise SystemExit("HydraDB is not ready")

    files = {
        "backstory": (out_dir / "hyp_backstory.jsonl").open("w", encoding="utf-8"),
        "naive": (out_dir / "hyp_naive.jsonl").open("w", encoding="utf-8"),
        "rag": (out_dir / "hyp_rag.jsonl").open("w", encoding="utf-8"),
    }
    results = []
    try:
        for item in items:
            qid = item["question_id"]
            print("INGEST", qid, item_type(item), flush=True)
            ingest_instance(engine, item)
            user_key = f"lme:{qid}"
            seeds = engine.retriever.seed_entities(item["question"], user_key)
            full = engine.ask(
                user_key=user_key,
                question=item["question"],
                question_date=_iso(item.get("question_date") or ""),
                naive=False,
            )
            naive = engine.ask(
                user_key=user_key,
                question=item["question"],
                question_date=_iso(item.get("question_date") or ""),
                naive=True,
            )
            rag = rag_answer(item)
            files["backstory"].write(json.dumps({"question_id": qid, "hypothesis": full.text}) + "\n")
            files["naive"].write(json.dumps({"question_id": qid, "hypothesis": naive.text}) + "\n")
            files["rag"].write(json.dumps({"question_id": qid, "hypothesis": rag}) + "\n")
            for handle in files.values():
                handle.flush()
            write_trace(out_dir / "traces" / f"{qid}.json", item, full, seeds)
            row = {
                "question_id": qid,
                "type": item_type(item),
                "question": item["question"],
                "gold": item.get("answer"),
                "backstory": full.text,
                "backstory_action": full.action,
                "backstory_reason": full.reason,
                "naive": naive.text,
                "rag": rag,
                "backstory_contains": unofficial_contains(str(item.get("answer") or ""), full.text),
                "naive_contains": unofficial_contains(str(item.get("answer") or ""), naive.text),
                "rag_contains": unofficial_contains(str(item.get("answer") or ""), rag),
            }
            results.append(row)
            print(
                "ASK",
                qid,
                item_type(item),
                "B",
                int(row["backstory_contains"]),
                "N",
                int(row["naive_contains"]),
                "R",
                int(row["rag_contains"]),
                full.action,
                flush=True,
            )
    finally:
        engine.close()
        for handle in files.values():
            handle.close()

    def tally(key: str) -> dict:
        by: dict[str, dict] = {}
        for row in results:
            bucket = by.setdefault(row["type"], {"n": 0, "hit": 0})
            bucket["n"] += 1
            bucket["hit"] += int(row[key])
        return {
            "n": len(results),
            "hit": sum(1 for r in results if r[key]),
            "by_type": by,
        }

    summary = {
        "note": "contains-match is unofficial. Official judge needs OPENAI_API_KEY + evaluate_qa.py gpt-4o",
        "backstory": tally("backstory_contains"),
        "naive_graph": tally("naive_contains"),
        "session_rag": tally("rag_contains"),
        "rows": results,
    }
    (out_dir / "compare.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("backstory", "naive_graph", "session_rag")}, indent=2))


if __name__ == "__main__":
    main()

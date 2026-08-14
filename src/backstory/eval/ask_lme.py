from __future__ import annotations

import argparse
import json
from pathlib import Path

from backstory.engine.memory import MemoryEngine
from backstory.eval.ingest_lme import _iso, load_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    items = load_dataset(Path(args.dataset))
    if args.limit:
        items = items[: args.limit]
    engine = MemoryEngine()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out_path.open("w", encoding="utf-8") as handle:
            for item in items:
                user_key = f"lme:{item['question_id']}"
                answer = engine.ask(
                    user_key=user_key,
                    question=item["question"],
                    question_date=_iso(item.get("question_date") or ""),
                )
                row = {"question_id": item["question_id"], "hypothesis": answer.text}
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(item["question_id"], answer.action)
    finally:
        engine.close()


if __name__ == "__main__":
    main()

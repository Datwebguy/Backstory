"""Same-subset baselines. Not the official memory engine.

1) session lexical RAG: rank haystack sessions by token overlap, answer from them
2) used via run_official --naive-graph for graph without current-state
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backstory.eval.ingest_lme import _iso
from backstory.eval.slice_lme import item_type, load_dataset, slice_items


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def rag_answer(item: dict) -> str:
    q = tokens(item["question"])
    scored: list[tuple[int, str]] = []
    for date, sess in zip(item.get("haystack_dates") or [], item.get("haystack_sessions") or []):
        blob = " ".join(turn.get("content") or "" for turn in sess)
        scored.append((len(q & tokens(blob)), f"[{_iso(date)}] {blob}"))
    scored.sort(reverse=True)
    pack = " ".join(chunk for _, chunk in scored[:2])
    if not pack.strip():
        return "I don't have enough information from your previous conversations to answer that."
    # Prefer the sentence with most query overlap.
    sents = re.split(r"(?<=[.!?])\s+", pack)
    sents.sort(key=lambda s: len(q & tokens(s)), reverse=True)
    return sents[0][:500]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--per-type", type=int, default=2)
    parser.add_argument("--ids", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    items = load_dataset(Path(args.dataset))
    if args.ids:
        wanted = {part.strip() for part in args.ids.split(",") if part.strip()}
        items = [item for item in items if item["question_id"] in wanted]
    else:
        items = slice_items(items, args.per_type)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for item in items:
            hyp = rag_answer(item)
            handle.write(json.dumps({"question_id": item["question_id"], "hypothesis": hyp}) + "\n")
            print(item_type(item), item["question_id"], hyp[:100])


if __name__ == "__main__":
    main()

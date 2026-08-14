"""Ingest a LongMemEval JSON file into Backstory.

Official instance shape (README):
  question_id, question_type, question, answer, question_date,
  haystack_session_ids, haystack_dates, haystack_sessions, answer_session_ids

Sessions are ingested in haystack date order. Extraction uses the LLM if
OPENAI_API_KEY is set; otherwise only pre-supplied atoms (tests) work.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backstory.engine.memory import MemoryEngine


def load_dataset(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    raise ValueError(f"Expected a JSON list in {path}")


def ingest_instance(engine: MemoryEngine, item: dict) -> None:
    user_key = f"lme:{item['question_id']}"
    dates = item.get("haystack_dates") or []
    sessions = item.get("haystack_sessions") or []
    ids = item.get("haystack_session_ids") or []
    triples = list(zip(ids, dates, sessions, strict=False))
    triples.sort(key=lambda t: t[1] or "")
    for session_key, occurred_at, turns in triples:
        engine.ingest_session(
            user_key=user_key,
            session_key=str(session_key),
            occurred_at=_iso(occurred_at),
            turns=list(turns or []),
            title=str(session_key),
        )


def _iso(value: str) -> str:
    # LME uses strings like "2023/05/20 (Sat) 14:30"
    text = (value or "").strip()
    if not text:
        return "2023-01-01T00:00:00"
    if "T" in text and len(text) >= 19:
        return text[:19]
    parts = text.replace("(", " ").replace(")", " ").split()
    date = parts[0].replace("/", "-") if parts else "2023-01-01"
    time = "00:00"
    for part in parts[1:]:
        if ":" in part:
            time = part
            break
    if len(time) == 5:
        time = time + ":00"
    return f"{date}T{time}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    items = load_dataset(Path(args.dataset))
    if args.limit:
        items = items[: args.limit]
    engine = MemoryEngine()
    try:
        if not engine.hydra.ready():
            raise SystemExit("HydraDB not ready")
        for item in items:
            ingest_instance(engine, item)
            print("ingested", item.get("question_id"))
    finally:
        engine.close()


if __name__ == "__main__":
    main()

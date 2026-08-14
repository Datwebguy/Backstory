from __future__ import annotations

from backstory.demo.scenarios import USER, QUESTIONS, all_sessions
from backstory.engine.memory import MemoryEngine


def load(engine: MemoryEngine, user_key: str = USER) -> None:
    for session in all_sessions():
        engine.ingest_session(
            user_key=user_key,
            session_key=session["session_key"],
            occurred_at=session["occurred_at"],
            turns=session["turns"],
            title=session.get("title") or "",
            preextracted=session.get("atoms") or [],
        )


def ask_all(engine: MemoryEngine, user_key: str = USER) -> list[dict]:
    out = []
    for item in QUESTIONS:
        answer = engine.ask(
            user_key=user_key,
            question=item["question"],
            question_date=item["question_date"],
        )
        out.append(
            {
                "id": item["id"],
                "question": item["question"],
                "hypothesis": answer.text,
                "action": answer.action,
                "reason": answer.reason,
                "evidence": [
                    {
                        "fact_id": f.fact_id,
                        "predicate": f.predicate,
                        "object_text": f.object_text,
                        "is_current": f.is_current,
                        "stated_at": f.stated_at,
                        "quote": f.quote,
                    }
                    for f in answer.evidence
                ],
            }
        )
    return out


def main() -> None:
    engine = MemoryEngine()
    try:
        if not engine.hydra.ready():
            raise SystemExit("HydraDB is not ready. Run docker compose up -d")
        load(engine)
        for row in ask_all(engine):
            print(f"{row['id']}: {row['hypothesis']}  [{row['action']}/{row['reason']}]")
    finally:
        engine.close()


if __name__ == "__main__":
    main()

from pathlib import Path

from backstory.config import Settings
from backstory.engine.memory import MemoryEngine
from backstory.hydra.client import HydraClient


def _engine(tmp_path: Path) -> MemoryEngine:
    # Hermetic on purpose: see test_versioning.py's _engine for why.
    settings = Settings(backstory_data_dir=tmp_path, openai_api_key="")
    return MemoryEngine(settings=settings, hydra=HydraClient(settings))


def test_like_unlike_like_again(tmp_path: Path):
    engine = _engine(tmp_path)
    user = "pref-user"
    try:
        for when, text, obj, polarity, update in [
            ("2023-01-01T00:00:00", "I like Apple.", "Apple", 1, None),
            ("2023-02-01T00:00:00", "I don't like Apple anymore.", "Apple", -1, "likes"),
            ("2023-03-01T00:00:00", "I actually like Apple again.", "Apple", 1, "likes"),
        ]:
            engine.ingest_session(
                user_key=user,
                session_key=when,
                occurred_at=when,
                turns=[{"role": "user", "content": text}],
                preextracted=[
                    {
                        "subject": "user",
                        "predicate": "likes",
                        "object_text": obj,
                        "polarity": polarity,
                        "fact_kind": "preference",
                        "update_of": update,
                    }
                ],
            )
        current = engine.hydra.query(
            """
            MATCH (f:Fact)
            WHERE f.predicate = $p AND f.is_current = true
            RETURN f.polarity AS polarity, f.object_text AS obj
            """,
            {"p": "likes"},
        ).mappings()
        assert any(int(row["polarity"]) == 1 and row["obj"] == "Apple" for row in current)
        history = engine.hydra.query(
            "MATCH (a:Fact)-[:SUPERSEDES]->(b:Fact) RETURN count(*) AS n"
        )
        assert int(history.first_scalar()) >= 1
    finally:
        engine.close()


def test_unresolved_conflict_is_qualified(tmp_path: Path):
    engine = _engine(tmp_path)
    user = "conflict-user"
    try:
        engine.ingest_session(
            user_key=user,
            session_key="c1",
            occurred_at="2023-01-01T00:00:00",
            turns=[{"role": "user", "content": "John lives in Lagos."}],
            preextracted=[
                {
                    "subject": "John",
                    "subject_type": "person",
                    "predicate": "lives_in",
                    "object_text": "Lagos",
                }
            ],
        )
        engine.ingest_session(
            user_key=user,
            session_key="c2",
            occurred_at="2023-01-02T00:00:00",
            turns=[{"role": "user", "content": "John lives in Abuja."}],
            preextracted=[
                {
                    "subject": "John",
                    "subject_type": "person",
                    "predicate": "lives_in",
                    "object_text": "Abuja",
                }
            ],
        )
        answer = engine.ask(user_key=user, question="Where does John currently live?")
        assert answer.action in {"qualify", "abstain"}
        assert "Lagos" in " ".join(f.object_text for f in answer.evidence)
        assert "Abuja" in " ".join(f.object_text for f in answer.evidence)
        john = engine.sidecar.entity_by_name("John")[0]
        both_current = engine.hydra.query(
            """
            MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $eid})
            WHERE f.predicate = $p AND f.is_current = true
            RETURN count(*) AS n
            """,
            {"eid": john, "p": "lives_in"},
        )
        assert int(both_current.first_scalar()) == 2
    finally:
        engine.close()

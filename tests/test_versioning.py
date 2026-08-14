from pathlib import Path

from backstory.config import Settings
from backstory.engine.memory import MemoryEngine
from backstory.hydra.client import HydraClient


def _engine(tmp_path: Path) -> MemoryEngine:
    settings = Settings(backstory_data_dir=tmp_path)
    return MemoryEngine(settings=settings, hydra=HydraClient(settings))


def test_lagos_then_abuja_keeps_history(tmp_path: Path):
    engine = _engine(tmp_path)
    user = "ku-user"
    try:
        engine.ingest_session(
            user_key=user,
            session_key="s4",
            occurred_at="2023-02-04T10:00:00",
            turns=[{"role": "user", "content": "I live in Enugu."}],
            preextracted=[
                {
                    "subject": "user",
                    "predicate": "lives_in",
                    "object_text": "Enugu",
                    "object_entity": "Enugu",
                    "object_type": "place",
                    "update_of": None,
                }
            ],
        )
        engine.ingest_session(
            user_key=user,
            session_key="s18",
            occurred_at="2023-06-18T10:00:00",
            turns=[{"role": "user", "content": "I moved to Jos."}],
            preextracted=[
                {
                    "subject": "user",
                    "predicate": "lives_in",
                    "object_text": "Jos",
                    "object_entity": "Jos",
                    "object_type": "place",
                    "update_of": "lives_in",
                }
            ],
        )
        now = engine.ask(user_key=user, question="Where do I live now?")
        assert "Jos" in now.text
        assert now.action == "answer"
        person = engine.sidecar.entity_by_key(f"user:{user}")
        hist = engine.hydra.query(
            """
            MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $eid})
            WHERE f.predicate = $p AND f.object_text = $city
            RETURN f.is_current AS is_current
            """,
            {"eid": person, "p": "lives_in", "city": "Enugu"},
        )
        assert not hist.first_scalar()
        chain = engine.hydra.query(
            """
            MATCH (new:Fact)-[:SUPERSEDES]->(old:Fact)-[:ABOUT]->(e:Entity {id: $eid})
            WHERE new.object_text = $new AND old.object_text = $old
            RETURN count(*) AS n
            """,
            {"eid": person, "new": "Jos", "old": "Enugu"},
        )
        assert int(chain.first_scalar()) >= 1
        # Unrelated predicate must survive.
        engine.ingest_session(
            user_key=user,
            session_key="s5",
            occurred_at="2023-03-01T10:00:00",
            turns=[{"role": "user", "content": "I have a sister named Tomi."}],
            preextracted=[
                {
                    "subject": "user",
                    "predicate": "has_sister",
                    "object_text": "Tomi",
                    "object_entity": "Tomi",
                    "object_type": "person",
                }
            ],
        )
        sister = engine.hydra.query(
            """
            MATCH (f:Fact)
            WHERE f.predicate = $p AND f.object_text = $name AND f.is_current = true
            RETURN f.object_text AS name
            """,
            {"p": "has_sister", "name": "Tomi"},
        )
        assert sister.first_scalar() == "Tomi"
    finally:
        engine.close()


def test_additive_owns_is_not_supersede(tmp_path: Path):
    engine = _engine(tmp_path)
    user = "bikes-user"
    try:
        engine.ingest_session(
            user_key=user,
            session_key="b1",
            occurred_at="2023-01-01T00:00:00",
            turns=[{"role": "user", "content": "I have a road bike and a mountain bike."}],
            preextracted=[
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "road bike",
                    "object_entity": "road bike",
                    "fact_kind": "state",
                },
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "mountain bike",
                    "object_entity": "mountain bike",
                    "fact_kind": "state",
                },
            ],
        )
        engine.ingest_session(
            user_key=user,
            session_key="b2",
            occurred_at="2023-02-01T00:00:00",
            turns=[{"role": "user", "content": "I just got a hybrid bike."}],
            preextracted=[
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "hybrid bike",
                    "object_entity": "hybrid bike",
                    "fact_kind": "state",
                }
            ],
        )
        answer = engine.ask(user_key=user, question="How many bikes do I currently own?")
        assert answer.text.strip() == "3"
    finally:
        engine.close()


def test_out_of_order_older_fact_does_not_win(tmp_path: Path):
    engine = _engine(tmp_path)
    user = "ooo-user"
    try:
        engine.ingest_session(
            user_key=user,
            session_key="new",
            occurred_at="2023-06-01T00:00:00",
            turns=[{"role": "user", "content": "I live in Calabar."}],
            preextracted=[
                {
                    "subject": "user",
                    "predicate": "lives_in",
                    "object_text": "Calabar",
                    "update_of": "lives_in",
                    "stated_at": "2023-06-01T00:00:00",
                }
            ],
        )
        engine.ingest_session(
            user_key=user,
            session_key="old",
            occurred_at="2023-01-01T00:00:00",
            turns=[{"role": "user", "content": "I live in Ibadan."}],
            preextracted=[
                {
                    "subject": "user",
                    "predicate": "lives_in",
                    "object_text": "Ibadan",
                    "update_of": "lives_in",
                    "stated_at": "2023-01-01T00:00:00",
                }
            ],
        )
        answer = engine.ask(user_key=user, question="Where do I live now?")
        assert "Calabar" in answer.text
    finally:
        engine.close()

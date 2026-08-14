"""Frozen Backstory graph schema for HydraDB OSS.

Live smoke against graph-node (2026-08-14) showed the UNWIND rules are
stricter than the high-level README:

- Vertex upsert MUST be: UNWIND $rows AS row MERGE (n {id: row.vertex})
  SET n:OneLabel, n.prop = row.prop, ...
  Exactly one SET label. Every SET value must be row.<field>.
- Edge CREATE MUST be: UNWIND $rows AS row
  MATCH (s:SrcLabel {id: row.source_vertex}), (d:DstLabel {id: row.destination_vertex})
  CREATE (s)-[:REL]->(d)
  Each endpoint has exactly one label. Labels may differ (Fact -> Entity).
- Undirected patterns and IS NULL are rejected (confirmed live).

STATED was dropped. Ownership is User -[:HAS_SESSION]-> Session
<-[:STATED_IN]- Fact.
"""

from __future__ import annotations

USER = "User"
SESSION = "Session"
MESSAGE = "Message"
ENTITY = "Entity"
FACT = "Fact"
DECISION = "Decision"

HAS_SESSION = "HAS_SESSION"
CONTAINS = "CONTAINS"
STATED_IN = "STATED_IN"
SUPPORTED_BY = "SUPPORTED_BY"
ABOUT = "ABOUT"
OBJECT_ENTITY = "OBJECT_ENTITY"
MENTIONS = "MENTIONS"
ALIAS_OF = "ALIAS_OF"
SUPERSEDES = "SUPERSEDES"
CONTRADICTS = "CONTRADICTS"
INVOLVES = "INVOLVES"
DECIDED = "DECIDED"
BASED_ON = "BASED_ON"
ABOUT_ENTITY = "ABOUT_ENTITY"
FOLLOWS = "FOLLOWS"

PREDICATE_CLASS = {
    "lives_in": "unique_state",
    "works_at": "unique_state",
    "works_as": "unique_state",
    "commute_duration": "unique_state",
    "located_in": "unique_state",
    "owns_count": "unique_state",
    "owns": "set_membership",
    "has": "set_membership",
    "has_pet": "set_membership",
    "plays": "set_membership",
    "likes": "preference",
    "dislikes": "preference",
    "prefers": "preference",
    "instruction": "instruction",
    "happened": "event",
    "visited": "event",
    "bought": "event",
    "decided": "decision",
}

OPEN_UNTIL = ""

USER_PROPS = ["user_key", "name"]
SESSION_PROPS = ["session_key", "occurred_at", "title"]
MESSAGE_PROPS = ["role", "ordinal", "occurred_at", "content"]
ENTITY_PROPS = ["canonical_key", "name", "entity_type"]
FACT_PROPS = [
    "predicate",
    "object_text",
    "fact_kind",
    "predicate_class",
    "stated_at",
    "valid_from",
    "valid_until",
    "event_at",
    "is_current",
    "confidence",
    "status",
    "polarity",
    "qualifiers",
    "speaker",
    "atom_hash",
]
DECISION_PROPS = ["question", "choice_text", "stated_at", "is_final"]

EDGE_LABELS = {
    HAS_SESSION: (USER, SESSION),
    CONTAINS: (SESSION, MESSAGE),
    STATED_IN: (FACT, SESSION),
    SUPPORTED_BY: (FACT, MESSAGE),
    ABOUT: (FACT, ENTITY),
    OBJECT_ENTITY: (FACT, ENTITY),
    MENTIONS: (MESSAGE, ENTITY),
    ALIAS_OF: (ENTITY, ENTITY),
    SUPERSEDES: (FACT, FACT),
    CONTRADICTS: (FACT, FACT),
    INVOLVES: (FACT, ENTITY),
    DECIDED: (USER, DECISION),
    BASED_ON: (DECISION, FACT),
    ABOUT_ENTITY: (DECISION, ENTITY),
    FOLLOWS: (DECISION, DECISION),
}


def upsert_query(label: str, properties: list[str]) -> str:
    assignments = ", ".join(f"n.{name} = row.{name}" for name in properties)
    return (
        f"UNWIND $rows AS row MERGE (n {{id: row.vertex}}) "
        f"SET n:{label}, {assignments}"
    )


UPSERT_USER = upsert_query(USER, USER_PROPS)
UPSERT_SESSION = upsert_query(SESSION, SESSION_PROPS)
UPSERT_MESSAGE = upsert_query(MESSAGE, MESSAGE_PROPS)
UPSERT_ENTITY = upsert_query(ENTITY, ENTITY_PROPS)
UPSERT_FACT = upsert_query(FACT, FACT_PROPS)
UPSERT_DECISION = upsert_query(DECISION, DECISION_PROPS)


def create_rel_query(rel_type: str, src_label: str | None = None, dst_label: str | None = None) -> str:
    if src_label is None or dst_label is None:
        src_label, dst_label = EDGE_LABELS[rel_type]
    return (
        "UNWIND $rows AS row "
        f"MATCH (s:{src_label} {{id: row.source_vertex}}), "
        f"(d:{dst_label} {{id: row.destination_vertex}}) "
        f"CREATE (s)-[:{rel_type}]->(d)"
    )


CURRENT_UNIQUE_FACT = """
MATCH (e:Entity {id: $entity_id})
MATCH (f:Fact)-[:ABOUT]->(e)
WHERE f.predicate = $predicate AND f.is_current = true
RETURN f.id AS fact_id, f.object_text AS object_text, f.stated_at AS stated_at, f.status AS status, f.polarity AS polarity
"""

FACT_HISTORY = """
MATCH (cur:Fact {id: $fact_id})-[:SUPERSEDES*1..8]->(old:Fact)
RETURN old.id AS fact_id, old.object_text AS object_text, old.stated_at AS stated_at, old.valid_until AS valid_until, old.is_current AS is_current
ORDER BY old.stated_at
"""

AS_OF_FACTS = """
MATCH (e:Entity {id: $entity_id})
MATCH (f:Fact)-[:ABOUT]->(e)
WHERE f.predicate = $predicate AND f.valid_from <= $as_of AND (f.valid_until = $open OR f.valid_until >= $as_of)
RETURN f.id AS fact_id, f.object_text AS object_text, f.valid_from AS valid_from, f.valid_until AS valid_until, f.is_current AS is_current
"""

CLOSE_FACT = """
MATCH (f:Fact {id: $fid})
SET f.is_current = $is_current, f.valid_until = $until, f.status = $status
"""

MARK_FACT_STATUS = """
MATCH (f:Fact {id: $fid})
SET f.status = $status
"""

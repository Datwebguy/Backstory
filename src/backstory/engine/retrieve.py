"""Graph-first retrieval.

Sidecar embeddings, if present, may only propose seed entity ids.
Every answer-relevant fact is loaded by HydraDB traversal:
  seed entity -> ALIAS_OF*1..2 -> ABOUT facts -> STATED_IN / SUPERSEDES / CONTRADICTS
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from backstory.engine.normalize import canonical_key, mention_keys, norm_text
from backstory.hydra.client import HydraClient
from backstory.sidecar.store import SidecarStore


@dataclass
class RetrievedFact:
    fact_id: int
    predicate: str
    object_text: str
    fact_kind: str
    stated_at: str
    valid_from: str
    valid_until: str
    is_current: bool
    status: str
    polarity: int
    confidence: float
    qualifiers: str
    speaker: str
    subject_id: int
    subject_name: str
    session_at: str
    quote: str
    contradicted_by: list[int] = field(default_factory=list)
    superseded_by: int | None = None
    source: str = "graph"


class Retriever:
    def __init__(self, hydra: HydraClient, sidecar: SidecarStore):
        self.hydra = hydra
        self.sidecar = sidecar

    def seed_entities(self, question: str, user_key: str) -> list[int]:
        seeds: list[int] = []
        user_id = self.sidecar.entity_by_key(f"user:{user_key}")
        if user_id:
            seeds.append(user_id)
        tokens = _content_tokens(question)
        for token in tokens:
            alias = self.sidecar.lookup_alias(token)
            if alias and alias not in seeds:
                seeds.append(alias)
            for entity_id in self.sidecar.entity_by_name(token):
                if entity_id not in seeds:
                    seeds.append(entity_id)
            for etype in ("person", "place", "org", "thing"):
                key = canonical_key(token, etype)
                hit = self.sidecar.entity_by_key(key)
                if hit and hit not in seeds:
                    seeds.append(hit)
        # Embedding seeds are optional and appended, never exclusive.
        seeds.extend(self._embedding_seeds(question, already=set(seeds)))
        return seeds[:16]

    def _embedding_seeds(self, question: str, already: set[int]) -> list[int]:
        rows = self.sidecar.all_embeddings("entity")
        if not rows:
            return []
        q_vec = _bag_vector(question)
        scored: list[tuple[float, int]] = []
        for row in rows:
            hid = int(row["hydra_id"])
            if hid in already:
                continue
            score = _cosine(q_vec, row["vector"])
            if score > 0.15:
                scored.append((score, hid))
        scored.sort(reverse=True)
        return [hid for _, hid in scored[:6]]

    def facts_for_entities(self, entity_ids: list[int], *, as_of: str | None = None) -> list[RetrievedFact]:
        facts: list[RetrievedFact] = []
        seen: set[int] = set()
        for entity_id in entity_ids:
            expanded = self._expand(entity_id)
            for eid in expanded:
                rows = self._load_about(eid, as_of=as_of)
                for row in rows:
                    fid = int(row["fact_id"])
                    if fid in seen:
                        continue
                    seen.add(fid)
                    facts.append(self._row_to_fact(row, eid))
        return facts

    def _expand(self, entity_id: int) -> list[int]:
        ids = {entity_id}
        # HydraDB: variable-length MATCH requires a *fixed source id*.
        # Incoming aliases are therefore one hop from the known node.
        outgoing = self.hydra.query(
            """
            MATCH (e:Entity {id: $eid})-[:ALIAS_OF*1..2]->(canon:Entity)
            RETURN canon.id AS id
            """,
            {"eid": entity_id},
        )
        incoming = self.hydra.query(
            """
            MATCH (alias:Entity)-[:ALIAS_OF]->(e:Entity {id: $eid})
            RETURN alias.id AS id
            """,
            {"eid": entity_id},
        )
        for result in (incoming, outgoing):
            for value in result.scalars("id"):
                if value is not None:
                    ids.add(int(value))
        return list(ids)

    def _load_about(self, entity_id: int, as_of: str | None) -> list[dict[str, Any]]:
        if as_of:
            cypher = """
            MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $eid})
            MATCH (f)-[:STATED_IN]->(s:Session)
            MATCH (f)-[:SUPPORTED_BY]->(m:Message)
            WHERE f.valid_from <= $as_of AND (f.valid_until = $open OR f.valid_until >= $as_of)
            RETURN f.id AS fact_id, f.predicate AS predicate, f.object_text AS object_text,
                   f.fact_kind AS fact_kind, f.stated_at AS stated_at, f.valid_from AS valid_from,
                   f.valid_until AS valid_until, f.is_current AS is_current, f.status AS status,
                   f.polarity AS polarity, f.confidence AS confidence, f.qualifiers AS qualifiers,
                   f.speaker AS speaker, e.name AS subject_name, s.occurred_at AS session_at,
                   m.content AS quote
            """
            return self.hydra.query(cypher, {"eid": entity_id, "as_of": as_of, "open": ""}).mappings()
        cypher = """
        MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $eid})
        MATCH (f)-[:STATED_IN]->(s:Session)
        MATCH (f)-[:SUPPORTED_BY]->(m:Message)
        RETURN f.id AS fact_id, f.predicate AS predicate, f.object_text AS object_text,
               f.fact_kind AS fact_kind, f.stated_at AS stated_at, f.valid_from AS valid_from,
               f.valid_until AS valid_until, f.is_current AS is_current, f.status AS status,
               f.polarity AS polarity, f.confidence AS confidence, f.qualifiers AS qualifiers,
               f.speaker AS speaker, e.name AS subject_name, s.occurred_at AS session_at,
               m.content AS quote
        """
        return self.hydra.query(cypher, {"eid": entity_id}).mappings()

    def attach_conflicts(self, facts: list[RetrievedFact]) -> list[RetrievedFact]:
        for fact in facts:
            result = self.hydra.query(
                """
                MATCH (f:Fact {id: $fid})-[:CONTRADICTS]->(g:Fact)
                RETURN g.id AS id
                """,
                {"fid": fact.fact_id},
            )
            fact.contradicted_by = [int(v) for v in result.scalars("id") if v is not None]
            hist = self.hydra.query(
                """
                MATCH (newer:Fact)-[:SUPERSEDES]->(f:Fact {id: $fid})
                RETURN newer.id AS id
                """,
                {"fid": fact.fact_id},
            )
            newer = hist.first_scalar()
            if newer is not None:
                fact.superseded_by = int(newer)
        return facts

    def _row_to_fact(self, row: dict[str, Any], subject_id: int) -> RetrievedFact:
        return RetrievedFact(
            fact_id=int(row["fact_id"]),
            predicate=row.get("predicate") or "",
            object_text=row.get("object_text") or "",
            fact_kind=row.get("fact_kind") or "state",
            stated_at=row.get("stated_at") or "",
            valid_from=row.get("valid_from") or "",
            valid_until=row.get("valid_until") or "",
            is_current=bool(row.get("is_current")),
            status=row.get("status") or "",
            polarity=int(row.get("polarity") or 1),
            confidence=float(row.get("confidence") or 0),
            qualifiers=row.get("qualifiers") or "",
            speaker=row.get("speaker") or "user",
            subject_id=subject_id,
            subject_name=row.get("subject_name") or "",
            session_at=row.get("session_at") or "",
            quote=row.get("quote") or "",
        )


def _content_tokens(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9@']+", text)
    stop = {
        "the", "a", "an", "my", "i", "me", "do", "did", "what", "where", "when",
        "how", "why", "is", "are", "was", "were", "to", "of", "in", "on", "for",
        "and", "or", "with", "about", "currently", "now", "many", "much",
    }
    out = []
    for word in words:
        low = word.lower()
        if low in stop or len(low) < 2:
            continue
        out.append(low)
        out.extend(mention_keys(word))
    # keep multiword names
    lowered = norm_text(text)
    for n in range(2, 4):
        parts = lowered.split()
        for i in range(len(parts) - n + 1):
            out.append(" ".join(parts[i : i + n]))
    return list(dict.fromkeys(out))


def _bag_vector(text: str) -> list[float]:
    # Deterministic lexical vector so tests work without an embedding API.
    vec = [0.0] * 64
    for token in _content_tokens(text):
        vec[hash(token) % 64] += 1.0
    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

"""Graph mutations: ADD / SUPERSEDE / CONTRADICT / IGNORE.

Safety rule: only the same (subject_entity, predicate) — and for
set_membership the same object entity — can be invalidated.

Out-of-order: compare stated_at strings (ISO-8601). A later-arriving older
fact does not become current.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backstory.engine.normalize import Atom
from backstory.engine.resolve import EntityResolver, ResolvedEntity
from backstory.hydra import schema as S
from backstory.hydra.client import HydraClient
from backstory.sidecar.store import SidecarStore


@dataclass
class MutationResult:
    action: str
    fact_id: int
    superseded_id: int | None = None
    contradicted_id: int | None = None


class GraphMutator:
    def __init__(self, hydra: HydraClient, sidecar: SidecarStore, resolver: EntityResolver):
        self.hydra = hydra
        self.sidecar = sidecar
        self.resolver = resolver
        self._seen_hashes: set[str] = set()

    def ensure_user(self, user_key: str, name: str = "user") -> int:
        existing = self.sidecar.lookup_alias(f"_user_node:{user_key}")
        if existing:
            return existing
        user_id = self.sidecar.next_id()
        self.hydra.write(
            S.UPSERT_USER,
            {"rows": [{"vertex": user_id, "user_key": user_key, "name": name}]},
        )
        person_id = self.sidecar.next_id()
        self.hydra.write(
            S.UPSERT_ENTITY,
            {
                "rows": [
                    {
                        "vertex": person_id,
                        "canonical_key": f"user:{user_key}",
                        "name": name,
                        "entity_type": "person",
                    }
                ]
            },
        )
        self.sidecar.put_entity(person_id, f"user:{user_key}", name, "person")
        self.sidecar.put_alias(f"_user_node:{user_key}", user_id, name, "user_node")
        return user_id

    def write_session(
        self,
        user_id: int,
        session_key: str,
        occurred_at: str,
        title: str,
    ) -> int:
        session_id = self.sidecar.next_id()
        self.hydra.write(
            S.UPSERT_SESSION,
            {
                "rows": [
                    {
                        "vertex": session_id,
                        "session_key": session_key,
                        "occurred_at": occurred_at,
                        "title": title,
                    }
                ]
            },
        )
        self.hydra.write(
            S.create_rel_query(S.HAS_SESSION),
            {"rows": [{"source_vertex": user_id, "destination_vertex": session_id}]},
        )
        return session_id

    def write_message(
        self,
        session_id: int,
        user_key: str,
        session_key: str,
        role: str,
        ordinal: int,
        occurred_at: str,
        content: str,
    ) -> int:
        message_id = self.sidecar.next_id()
        # HydraDB string properties hold the quote so evidence can be read
        # from the graph, not only the sidecar.
        self.hydra.write(
            S.UPSERT_MESSAGE,
            {
                "rows": [
                    {
                        "vertex": message_id,
                        "role": role,
                        "ordinal": ordinal,
                        "occurred_at": occurred_at,
                        "content": content[:4000],
                    }
                ]
            },
        )
        self.hydra.write(
            S.create_rel_query(S.CONTAINS),
            {"rows": [{"source_vertex": session_id, "destination_vertex": message_id}]},
        )
        self.sidecar.put_turn(
            message_id=message_id,
            user_key=user_key,
            session_key=session_key,
            role=role,
            ordinal=ordinal,
            occurred_at=occurred_at,
            content=content,
        )
        return message_id

    def write_entity(self, resolved: ResolvedEntity) -> None:
        if not resolved.created:
            return
        self.hydra.write(
            S.UPSERT_ENTITY,
            {
                "rows": [
                    {
                        "vertex": resolved.entity_id,
                        "canonical_key": resolved.canonical_key,
                        "name": resolved.name,
                        "entity_type": resolved.entity_type,
                    }
                ]
            },
        )

    def current_facts(self, entity_id: int, predicate: str) -> list[dict[str, Any]]:
        result = self.hydra.query(
            """
            MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $entity_id})
            WHERE f.predicate = $predicate AND f.is_current = true
            RETURN f.id AS fact_id, f.object_text AS object_text, f.stated_at AS stated_at,
                   f.polarity AS polarity, f.status AS status, f.atom_hash AS atom_hash
            """,
            {"entity_id": entity_id, "predicate": predicate},
        )
        return result.mappings()

    def apply_atom(
        self,
        atom: Atom,
        *,
        session_id: int,
        message_id: int,
        user_id: int,
        user_key: str,
    ) -> MutationResult | None:
        digest = atom.hash()
        if digest in self._seen_hashes:
            return MutationResult("ignore_duplicate", 0)
        subject, obj = self.resolver.resolve_atom(atom, user_key=user_key)
        self.write_entity(subject)
        if obj:
            self.write_entity(obj)

        current = self.current_facts(subject.entity_id, atom.predicate)
        for row in current:
            if row.get("atom_hash") == digest or (
                _norm(row.get("object_text") or "") == _norm(atom.object_text)
                and int(row.get("polarity") or 1) == atom.polarity
            ):
                self._seen_hashes.add(digest)
                return MutationResult("ignore_duplicate", int(row["fact_id"]))

        action = self._decide_action(atom, current)
        fact_id = self._insert_fact(
            atom,
            digest,
            subject,
            obj,
            session_id,
            message_id,
            user_id,
            is_current=(action != "add_historical"),
            status="superseded" if action == "add_historical" else "active",
        )

        superseded = None
        contradicted = None
        if action == "add_historical":
            for row in current:
                if self._same_slot(atom, row):
                    self.hydra.write(
                        S.create_rel_query(S.SUPERSEDES),
                        {"rows": [{"source_vertex": int(row["fact_id"]), "destination_vertex": fact_id}]},
                    )
                    superseded = int(row["fact_id"])
        elif action == "supersede":
            for row in current:
                if self._same_slot(atom, row):
                    self._close_fact(int(row["fact_id"]), atom.stated_at, status="superseded")
                    self.hydra.write(
                        S.create_rel_query(S.SUPERSEDES),
                        {"rows": [{"source_vertex": fact_id, "destination_vertex": int(row["fact_id"])}]},
                    )
                    superseded = int(row["fact_id"])
        elif action == "contradict":
            for row in current:
                if self._same_slot(atom, row):
                    self._mark_contradicted(int(row["fact_id"]))
                    self.hydra.write(
                        S.create_rel_query(S.CONTRADICTS),
                        {
                            "rows": [
                                {"source_vertex": fact_id, "destination_vertex": int(row["fact_id"])},
                                {"source_vertex": int(row["fact_id"]), "destination_vertex": fact_id},
                            ]
                        },
                    )
                    contradicted = int(row["fact_id"])
            self.hydra.write(
                S.CLOSE_FACT,
                {"fid": fact_id, "is_current": True, "until": S.OPEN_UNTIL, "status": "contradicted"},
            )

        self._seen_hashes.add(digest)
        return MutationResult(action, fact_id, superseded, contradicted)

    def _decide_action(self, atom: Atom, current: list[dict[str, Any]]) -> str:
        if not current:
            return "add"
        if atom.predicate_class == "set_membership":
            return "add"
        if atom.predicate_class == "event":
            return "add"
        # A new personal name replaces the old one. Two "my name is"
        # statements are a correction, not two current names and not a
        # contradiction to qualify at ask time.
        if atom.predicate in {"name", "has_name", "full_name", "called"}:
            newest = max(current, key=lambda r: r.get("stated_at") or "")
            if _norm(newest.get("object_text") or "") == _norm(atom.object_text):
                return "add"
            if (atom.stated_at or "") < (newest.get("stated_at") or ""):
                return "add_historical"
            return "supersede"
        # unique_state / preference / instruction
        if atom.update_of or _looks_like_update(atom):
            # Out-of-order: if incoming is older than current, keep current and store history.
            newest = max(current, key=lambda r: r.get("stated_at") or "")
            if (atom.stated_at or "") < (newest.get("stated_at") or ""):
                return "add_historical"
            return "supersede"
        # Same predicate, different object, no update language → conflict.
        return "contradict"

    def _same_slot(self, atom: Atom, row: dict[str, Any]) -> bool:
        if atom.predicate_class == "set_membership":
            return _norm(row.get("object_text") or "") == _norm(atom.object_text)
        return True

    def _insert_fact(
        self,
        atom: Atom,
        digest: str,
        subject: ResolvedEntity,
        obj: ResolvedEntity | None,
        session_id: int,
        message_id: int,
        user_id: int,
        is_current: bool = True,
        status: str = "active",
    ) -> int:
        fact_id = self.sidecar.next_id()
        valid_until = atom.stated_at if not is_current else S.OPEN_UNTIL
        self.hydra.write(
            S.UPSERT_FACT,
            {
                "rows": [
                    {
                        "vertex": fact_id,
                        "predicate": atom.predicate,
                        "object_text": atom.object_text,
                        "fact_kind": atom.fact_kind,
                        "predicate_class": atom.predicate_class,
                        "stated_at": atom.stated_at,
                        "valid_from": atom.event_at or atom.stated_at,
                        "valid_until": valid_until,
                        "event_at": atom.event_at or "",
                        "is_current": is_current,
                        "confidence": atom.confidence,
                        "status": status,
                        "polarity": atom.polarity,
                        "qualifiers": atom.qualifiers,
                        "speaker": atom.speaker,
                        "atom_hash": digest,
                    }
                ]
            },
        )
        rels = [
            (S.ABOUT, fact_id, subject.entity_id),
            (S.STATED_IN, fact_id, session_id),
            (S.SUPPORTED_BY, fact_id, message_id),
        ]
        if obj:
            rels.append((S.OBJECT_ENTITY, fact_id, obj.entity_id))
        for rel, src, dst in rels:
            self.hydra.write(
                S.create_rel_query(rel),
                {"rows": [{"source_vertex": src, "destination_vertex": dst}]},
            )
        return fact_id

    def _close_fact(self, fact_id: int, until: str, status: str) -> None:
        self.hydra.write(
            S.CLOSE_FACT,
            {"fid": fact_id, "is_current": False, "until": until, "status": status},
        )

    def _mark_contradicted(self, fact_id: int) -> None:
        self.hydra.write(
            S.MARK_FACT_STATUS,
            {"fid": fact_id, "status": "contradicted"},
        )


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _looks_like_update(atom: Atom) -> bool:
    text = (atom.object_text or "").lower()
    if atom.polarity < 0 and atom.predicate in {"likes", "prefers"}:
        return True
    hints = ("moved", "no longer", "used to", "switched", "changed", "instead", "anymore")
    return any(h in text for h in hints)

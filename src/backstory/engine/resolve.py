"""Conservative entity resolution.

Order:
1. Exact canonical_key
2. Exact alias table (including extractor-provided aliases)
3. Exact name (case-insensitive), only if unique
4. Otherwise create a new Entity

We do not fuzzy-merge Sam/Samuel unless an extractor alias or explicit
alias table says so. Over-merge is worse than a missed merge on LME.
"""

from __future__ import annotations

from dataclasses import dataclass

from backstory.engine.normalize import Atom, canonical_key, mention_keys, norm_text
from backstory.sidecar.store import SidecarStore


@dataclass
class ResolvedEntity:
    entity_id: int
    canonical_key: str
    name: str
    entity_type: str
    created: bool


class EntityResolver:
    def __init__(self, sidecar: SidecarStore):
        self.sidecar = sidecar

    def resolve(
        self,
        name: str,
        entity_type: str,
        aliases: list[str] | None = None,
        user_key: str | None = None,
    ) -> ResolvedEntity:
        if user_key and norm_text(name) in {"user", "i", "me", "myself"}:
            existing = self.sidecar.entity_by_key(f"user:{user_key}")
            if existing is not None:
                return ResolvedEntity(existing, f"user:{user_key}", name, "person", created=False)
        key = canonical_key(name, entity_type)
        existing = self.sidecar.entity_by_key(key)
        if existing is not None:
            self._remember_aliases(existing, name, aliases)
            return ResolvedEntity(existing, key, name, entity_type, created=False)

        for mention in mention_keys(name) + [norm_text(a) for a in (aliases or [])]:
            alias_id = self.sidecar.lookup_alias(mention)
            if alias_id is not None:
                self._remember_aliases(alias_id, name, aliases)
                return ResolvedEntity(alias_id, key, name, entity_type, created=False)

        name_hits = self.sidecar.entity_by_name(name)
        if len(name_hits) == 1:
            self._remember_aliases(name_hits[0], name, aliases)
            return ResolvedEntity(name_hits[0], key, name, entity_type, created=False)

        entity_id = self.sidecar.next_id()
        self.sidecar.put_entity(entity_id, key, name, entity_type)
        self._remember_aliases(entity_id, name, aliases)
        return ResolvedEntity(entity_id, key, name, entity_type, created=True)

    def resolve_atom(self, atom: Atom, user_key: str | None = None) -> tuple[ResolvedEntity, ResolvedEntity | None]:
        subject = self.resolve(atom.subject, atom.subject_type, atom.aliases, user_key=user_key)
        obj = None
        if atom.object_entity:
            obj = self.resolve(atom.object_entity, atom.object_type, user_key=user_key)
        return subject, obj

    def _remember_aliases(self, entity_id: int, name: str, aliases: list[str] | None) -> None:
        for mention in mention_keys(name) + [norm_text(a) for a in (aliases or [])]:
            if mention:
                self.sidecar.put_alias(mention, entity_id, name, "resolve")

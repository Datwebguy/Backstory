from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


HANDLE_RE = re.compile(r"^@[\w.]+$")


def norm_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def canonical_key(name: str, entity_type: str = "thing") -> str:
    cleaned = norm_text(name)
    cleaned = cleaned.lstrip("@")
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return f"{entity_type}:{cleaned}" if cleaned else f"{entity_type}:unknown"


def mention_keys(surface: str) -> list[str]:
    raw = (surface or "").strip()
    keys = {norm_text(raw)}
    if HANDLE_RE.match(raw):
        keys.add(norm_text(raw[1:]))
    # Samuel -> sam is NOT automatic; only exact/alias hits.
    return [k for k in keys if k]


def atom_hash(
    subject_key: str,
    predicate: str,
    object_text: str,
    stated_at: str,
    polarity: int,
) -> str:
    payload = "|".join(
        [norm_text(subject_key), norm_text(predicate), norm_text(object_text), stated_at, str(polarity)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


@dataclass
class Atom:
    subject: str
    subject_type: str
    predicate: str
    object_text: str
    object_entity: str | None = None
    object_type: str = "thing"
    fact_kind: str = "state"
    predicate_class: str = "unique_state"
    polarity: int = 1
    qualifiers: str = ""
    confidence: float = 0.8
    speaker: str = "user"
    stated_at: str = ""
    event_at: str = ""
    source_ordinal: int = 0
    aliases: list[str] = field(default_factory=list)
    update_of: str | None = None  # explicit supersession hint from extractor

    def hash(self) -> str:
        return atom_hash(
            canonical_key(self.subject, self.subject_type),
            self.predicate,
            self.object_text,
            self.stated_at,
            self.polarity,
        )

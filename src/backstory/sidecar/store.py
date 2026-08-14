"""SQLite sidecar: integer id allocator, alias table, raw turn index, embeddings.

HydraDB is the source of truth for structured memory. This file is:
- an id allocator (Hydra vertex ids are u64; we mint them)
- a rebuildable lexical/alias index
- an optional embedding table for entry-point recall

Nothing in here is allowed to answer a user question by itself.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aliases (
    mention_norm TEXT PRIMARY KEY,
    entity_id INTEGER NOT NULL,
    surface TEXT NOT NULL,
    source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS turns (
    message_id INTEGER PRIMARY KEY,
    user_key TEXT NOT NULL,
    session_key TEXT NOT NULL,
    role TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    occurred_at TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS embeddings (
    hydra_id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    vector_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entity_index (
    entity_id INTEGER PRIMARY KEY,
    canonical_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL
);
"""


class SidecarStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        # Fresh sidecars start far apart so concurrent tests do not reuse
        # HydraDB integer ids already committed in the shared graph.
        start = (time.time_ns() % 1_500_000_000) + 10_000
        self._conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES ('next_id', ?)",
            (str(start),),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def next_id(self) -> int:
        cur = self._conn.execute("SELECT value FROM meta WHERE key = 'next_id'")
        value = int(cur.fetchone()["value"])
        self._conn.execute("UPDATE meta SET value = ? WHERE key = 'next_id'", (str(value + 1),))
        self._conn.commit()
        return value

    def next_ids(self, n: int) -> list[int]:
        return [self.next_id() for _ in range(n)]

    def put_alias(self, mention_norm: str, entity_id: int, surface: str, source: str) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO aliases(mention_norm, entity_id, surface, source)
            VALUES (?, ?, ?, ?)
            """,
            (mention_norm, entity_id, surface, source),
        )
        self._conn.commit()

    def lookup_alias(self, mention_norm: str) -> int | None:
        cur = self._conn.execute(
            "SELECT entity_id FROM aliases WHERE mention_norm = ?", (mention_norm,)
        )
        row = cur.fetchone()
        return int(row["entity_id"]) if row else None

    def put_entity(self, entity_id: int, canonical_key: str, name: str, entity_type: str) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO entity_index(entity_id, canonical_key, name, entity_type)
            VALUES (?, ?, ?, ?)
            """,
            (entity_id, canonical_key, name, entity_type),
        )
        self.put_alias(canonical_key, entity_id, name, "canonical")
        self.put_alias(_norm(name), entity_id, name, "name")
        self._conn.commit()

    def entity_by_key(self, canonical_key: str) -> int | None:
        cur = self._conn.execute(
            "SELECT entity_id FROM entity_index WHERE canonical_key = ?", (canonical_key,)
        )
        row = cur.fetchone()
        return int(row["entity_id"]) if row else None

    def entity_by_name(self, name: str) -> list[int]:
        cur = self._conn.execute(
            "SELECT entity_id FROM entity_index WHERE name = ? COLLATE NOCASE", (name,)
        )
        return [int(r["entity_id"]) for r in cur.fetchall()]

    def put_turn(self, **kwargs: Any) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO turns(message_id, user_key, session_key, role, ordinal, occurred_at, content)
            VALUES (:message_id, :user_key, :session_key, :role, :ordinal, :occurred_at, :content)
            """,
            kwargs,
        )
        self._conn.commit()

    def recent_turns(self, user_key: str, limit: int) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT * FROM turns WHERE user_key = ?
            ORDER BY occurred_at DESC, ordinal DESC LIMIT ?
            """,
            (user_key, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
        rows.reverse()
        return rows

    def put_embedding(self, hydra_id: int, kind: str, text: str, vector: Iterable[float]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings(hydra_id, kind, text, vector_json) VALUES (?, ?, ?, ?)",
            (hydra_id, kind, text, json.dumps(list(vector))),
        )
        self._conn.commit()

    def all_embeddings(self, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            cur = self._conn.execute("SELECT * FROM embeddings WHERE kind = ?", (kind,))
        else:
            cur = self._conn.execute("SELECT * FROM embeddings")
        out = []
        for row in cur.fetchall():
            item = dict(row)
            item["vector"] = json.loads(item["vector_json"])
            out.append(item)
        return out


def _norm(text: str) -> str:
    return " ".join(text.strip().lower().split())

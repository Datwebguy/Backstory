"""Map BEAM conversations onto Backstory sessions.

BEAM structure, confirmed against the published data rather than assumed:

    chat.json  = [ batch, ... ]
    batch      = {"batch_number": int, "turns": [ [message, ...], ... ]}
    message    = {"role": "user"|"assistant", "content": str,
                  "time_anchor": "March-15-2024" (first user message of a
                  batch only), ...}

Each batch carries exactly one time anchor and represents one dated
conversation, so a batch maps to a Backstory session and its flattened
messages map to that session's turns. A conversation therefore ingests
as several sessions on different dates, which is the multi-session
history Backstory is built to reason over.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ABILITIES = (
    "abstention",
    "contradiction_resolution",
    "event_ordering",
    "information_extraction",
    "instruction_following",
    "knowledge_update",
    "multi_session_reasoning",
    "preference_following",
    "summarization",
    "temporal_reasoning",
)


def _iso(anchor: str | None, fallback_index: int) -> str:
    """BEAM anchors look like 'March-15-2024'."""
    if anchor:
        try:
            return datetime.strptime(anchor, "%B-%d-%Y").strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass
    # Keep ordering stable when an anchor is missing or malformed.
    return f"2024-01-{min(fallback_index + 1, 28):02d}T00:00:00"


def batch_anchor(batch: dict[str, Any]) -> str | None:
    for group in batch.get("turns") or []:
        for message in group:
            anchor = message.get("time_anchor")
            if anchor:
                return anchor
    return None


def conversation_sessions(chat: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One Backstory session per BEAM batch, in chronological order."""
    sessions: list[dict[str, Any]] = []
    for position, batch in enumerate(chat):
        turns: list[dict[str, str]] = []
        for group in batch.get("turns") or []:
            for message in group:
                content = (message.get("content") or "").strip()
                if not content:
                    continue
                turns.append(
                    {
                        "role": message.get("role") or "user",
                        "content": content,
                    }
                )
        if not turns:
            continue
        occurred_at = _iso(batch_anchor(batch), position)
        sessions.append(
            {
                "session_key": f"batch-{batch.get('batch_number', position + 1)}",
                "occurred_at": occurred_at,
                "turns": turns,
            }
        )
    sessions.sort(key=lambda s: s["occurred_at"])
    return sessions


def load_conversation(path: Path) -> list[dict[str, Any]]:
    chat = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(chat, list):
        raise ValueError(f"Expected a JSON list of batches in {path}")
    return conversation_sessions(chat)


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Flatten BEAM's ability-keyed question file into a flat list."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    questions: list[dict[str, Any]] = []
    for ability, items in raw.items():
        for ordinal, item in enumerate(items or []):
            question = (item.get("question") or "").strip()
            if not question:
                continue
            questions.append(
                {
                    "ability": ability,
                    "question_id": f"{ability}:{ordinal}",
                    "question": question,
                    "ideal_response": item.get("ideal_response") or "",
                    "rubric": item.get("rubric") or [],
                    "difficulty": item.get("difficulty") or "",
                }
            )
    return questions


def discover(root: Path, tier: str) -> list[tuple[str, Path, Path]]:
    """Find (conversation_id, chat.json, probing_questions.json) triples."""
    found: list[tuple[str, Path, Path]] = []
    tier_dir = root / tier
    if not tier_dir.exists():
        return found
    for conv_dir in sorted(tier_dir.iterdir(), key=lambda p: (len(p.name), p.name)):
        if not conv_dir.is_dir():
            continue
        chat = conv_dir / "chat.json"
        questions = conv_dir / "probing_questions.json"
        if chat.exists() and questions.exists():
            found.append((conv_dir.name, chat, questions))
    return found

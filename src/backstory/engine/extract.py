"""Turn extraction.

Two paths:
- structured atoms supplied by tests/demos (no LLM)
- optional LLM JSON extraction when OPENAI_API_KEY is set

The engine never requires the LLM path for correctness of versioning,
contradictions, or the four demos.
"""

from __future__ import annotations

import json
from typing import Any

from backstory.engine.normalize import Atom
from backstory.hydra.schema import PREDICATE_CLASS

EXTRACT_PROMPT = """You extract durable memory atoms from a conversation window.
Return JSON: {"atoms": [ ... ]}

Each atom:
- subject: string (usually "user" or a person name)
- subject_type: person|place|org|thing
- predicate: snake_case (lives_in, works_at, owns, likes, visited, ...)
- object_text: short object/value
- object_entity: optional entity name if the object is an entity
- object_type: person|place|org|thing
- fact_kind: state|preference|instruction|event|decision
- polarity: 1 for asserted, -1 for negated
- qualifiers: optional compact k=v;k=v string (capacity=30;unit=gal)
- confidence: 0-1
- aliases: extra surface forms for the subject
- update_of: if this clearly replaces a previous value of the same predicate, repeat the predicate

Rules:
- Skip chit-chat and acknowledgements.
- Keep atoms grounded in THIS window only.
- If the user moved / changed / no longer X, set update_of to that predicate and polarity accordingly.
- If the user added another item (another bike), this is NOT an update; it is a new owns atom.
- Assistant-offered durable facts use speaker=assistant and subject as appropriate.
- Max 8 atoms.

Window:
{window}
"""


def classify_predicate(predicate: str, fact_kind: str) -> str:
    if predicate in PREDICATE_CLASS:
        return PREDICATE_CLASS[predicate]
    if fact_kind == "preference":
        return "preference"
    if fact_kind == "event":
        return "event"
    if fact_kind == "instruction":
        return "instruction"
    if fact_kind == "decision":
        return "decision"
    return "unique_state"


def atoms_from_dicts(raw: list[dict[str, Any]], stated_at: str, speaker: str = "user") -> list[Atom]:
    atoms: list[Atom] = []
    for item in raw:
        kind = item.get("fact_kind") or "state"
        predicate = item.get("predicate") or "has"
        atoms.append(
            Atom(
                subject=item.get("subject") or "user",
                subject_type=item.get("subject_type") or "person",
                predicate=predicate,
                object_text=item.get("object_text") or "",
                object_entity=item.get("object_entity"),
                object_type=item.get("object_type") or "thing",
                fact_kind=kind,
                predicate_class=classify_predicate(predicate, kind),
                polarity=int(item.get("polarity", 1)),
                qualifiers=item.get("qualifiers") or "",
                confidence=float(item.get("confidence", 0.8)),
                speaker=item.get("speaker") or speaker,
                stated_at=item.get("stated_at") or stated_at,
                event_at=item.get("event_at") or "",
                source_ordinal=int(item.get("source_ordinal", 0)),
                aliases=list(item.get("aliases") or []),
                update_of=item.get("update_of"),
            )
        )
    return atoms


def extract_with_llm(
    window_text: str,
    stated_at: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
) -> list[Atom]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Extract only grounded memory atoms as JSON."},
            {"role": "user", "content": EXTRACT_PROMPT.format(window=window_text)},
        ],
    )
    content = completion.choices[0].message.content or '{"atoms":[]}'
    payload = json.loads(content)
    return atoms_from_dicts(payload.get("atoms") or [], stated_at)

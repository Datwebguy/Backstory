"""Four benchmark-aligned product demos with structured atoms.

These are the same memory operations LongMemEval tests, told as one user's
life so a human can follow them in the UI.
"""

from __future__ import annotations

from typing import Any

USER = "demo-user-ui"


def scenario_a_knowledge_update() -> list[dict[str, Any]]:
    """LME knowledge-update: old employer superseded; current is Company B.

    Also includes an additive owns update (hybrid bike style) so we do not
    treat every KU as overwrite.
    """
    return [
        {
            "session_key": "s04",
            "occurred_at": "2023-02-04T10:00:00",
            "title": "New job",
            "turns": [
                {"role": "user", "content": "I'm working at Company A."},
                {"role": "assistant", "content": "Nice — how is it going there?"},
            ],
            "atoms": [
                {
                    "subject": "user",
                    "subject_type": "person",
                    "predicate": "works_at",
                    "object_text": "Company A",
                    "object_entity": "Company A",
                    "object_type": "org",
                    "fact_kind": "state",
                    "update_of": None,
                }
            ],
        },
        {
            "session_key": "s17",
            "occurred_at": "2023-05-17T10:00:00",
            "title": "I left",
            "turns": [
                {"role": "user", "content": "I left Company A last week."},
                {"role": "assistant", "content": "Sorry to hear that. What's next?"},
            ],
            "atoms": [
                {
                    "subject": "user",
                    "subject_type": "person",
                    "predicate": "works_at",
                    "object_text": "unemployed",
                    "object_type": "org",
                    "fact_kind": "state",
                    "update_of": "works_at",
                }
            ],
        },
        {
            "session_key": "s23",
            "occurred_at": "2023-06-23T10:00:00",
            "title": "Company B",
            "turns": [
                {"role": "user", "content": "I joined Company B."},
                {"role": "assistant", "content": "Congrats on the new role."},
            ],
            "atoms": [
                {
                    "subject": "user",
                    "subject_type": "person",
                    "predicate": "works_at",
                    "object_text": "Company B",
                    "object_entity": "Company B",
                    "object_type": "org",
                    "fact_kind": "state",
                    "update_of": "works_at",
                }
            ],
        },
    ]


def scenario_b_distributed() -> list[dict[str, Any]]:
    """LME multi-session: facts about one colleague arrive far apart."""
    return [
        {
            "session_key": "s03",
            "occurred_at": "2023-01-12T09:00:00",
            "title": "Atlas migration lead",
            "turns": [
                {"role": "user", "content": "Priya is the tech lead on the Atlas migration."}
            ],
            "atoms": [
                {
                    "subject": "Priya",
                    "subject_type": "person",
                    "predicate": "works_as",
                    "object_text": "tech lead on the Atlas migration",
                    "fact_kind": "state",
                    "aliases": ["she"],
                }
            ],
        },
        {
            "session_key": "s11",
            "occurred_at": "2023-03-08T09:00:00",
            "title": "Priya in Berlin",
            "turns": [{"role": "user", "content": "Priya is based in the Berlin office."}],
            "atoms": [
                {
                    "subject": "Priya",
                    "subject_type": "person",
                    "predicate": "located_in",
                    "object_text": "Berlin office",
                    "object_entity": "Berlin office",
                    "object_type": "place",
                    "fact_kind": "state",
                }
            ],
        },
        {
            "session_key": "s24",
            "occurred_at": "2023-07-02T09:00:00",
            "title": "Billing API rewrite",
            "turns": [{"role": "user", "content": "She now owns the billing API rewrite."}],
            "atoms": [
                {
                    "subject": "Priya",
                    "subject_type": "person",
                    "predicate": "owns",
                    "object_text": "billing API rewrite",
                    "fact_kind": "state",
                    "aliases": ["she"],
                }
            ],
        },
    ]


def scenario_c_abstention() -> list[dict[str, Any]]:
    """Official LME abstention shape, in a professional setting.

    Same mechanism as LongMemEval's own abstention example: two sized
    things are on record and the question asks about a third size that
    is not. Only the surface content differs.
    """
    return [
        {
            "session_key": "s07",
            "occurred_at": "2023-04-01T12:00:00",
            "title": "Environment sizing",
            "turns": [
                {
                    "role": "user",
                    "content": "We moved staging onto a 16 GB instance last week.",
                },
                {
                    "role": "user",
                    "content": "Production still runs on the 32 GB instance.",
                },
            ],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "16 GB instance",
                    "object_entity": "16 GB instance",
                    "object_type": "thing",
                    "fact_kind": "state",
                    "qualifiers": "capacity=16;unit=gb",
                },
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "32 GB instance",
                    "object_entity": "32 GB instance",
                    "object_type": "thing",
                    "fact_kind": "state",
                    "qualifiers": "capacity=32;unit=gb",
                },
                {
                    "subject": "staging",
                    "subject_type": "thing",
                    "predicate": "located_in",
                    "object_text": "16 GB instance",
                    "fact_kind": "state",
                },
            ],
        }
    ]


def scenario_d_decision() -> list[dict[str, Any]]:
    """Decision/history reconstruction — not an LME type, BEAM event-order flavored."""
    return [
        {
            "session_key": "s02",
            "occurred_at": "2023-01-20T18:00:00",
            "title": "MongoDB plan",
            "turns": [
                {"role": "user", "content": "We're planning to use MongoDB for the events store."}
            ],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "prefers",
                    "object_text": "MongoDB",
                    "object_entity": "MongoDB",
                    "object_type": "thing",
                    "fact_kind": "preference",
                }
            ],
        },
        {
            "session_key": "s10",
            "occurred_at": "2023-03-01T18:00:00",
            "title": "Postgres instead",
            "turns": [{"role": "user", "content": "I think we'll go with Postgres instead."}],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "prefers",
                    "object_text": "Postgres",
                    "object_entity": "Postgres",
                    "object_type": "thing",
                    "fact_kind": "preference",
                    "update_of": "prefers",
                }
            ],
        },
        {
            "session_key": "s17b",
            "occurred_at": "2023-04-09T18:00:00",
            "title": "Consistency requirement",
            "turns": [
                {"role": "user", "content": "We need strong consistency for billing records."}
            ],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "needs",
                    "object_text": "strong consistency for billing records",
                    "fact_kind": "state",
                }
            ],
        },
        {
            "session_key": "s29",
            "occurred_at": "2023-06-01T18:00:00",
            "title": "Postgres chosen",
            "turns": [{"role": "user", "content": "We standardised on Postgres."}],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "decided",
                    "object_text": "Postgres",
                    "object_entity": "Postgres",
                    "object_type": "thing",
                    "fact_kind": "decision",
                    "event_at": "2023-06-01T18:00:00",
                },
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "Postgres",
                    "object_entity": "Postgres",
                    "object_type": "thing",
                    "fact_kind": "state",
                },
            ],
        },
    ]


def all_sessions() -> list[dict[str, Any]]:
    sessions = []
    sessions.extend(scenario_a_knowledge_update())
    sessions.extend(scenario_b_distributed())
    sessions.extend(scenario_c_abstention())
    sessions.extend(scenario_d_decision())
    sessions.sort(key=lambda s: s["occurred_at"])
    return sessions


QUESTIONS = [
    {
        "id": "demo-a",
        "question": "Where do I work now?",
        "question_date": "2023-07-01T00:00:00",
        "expect_contains": ["Company B"],
        "expect_action": "answer",
        "capability": "knowledge-update",
    },
    {
        "id": "demo-b",
        "question": "What do I know about Priya?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["Berlin", "billing"],
        "expect_action": "answer",
        "capability": "multi-session",
    },
    {
        "id": "demo-c",
        "question": "How many services run on the 64 GB instance?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["don't have enough information"],
        "expect_action": "abstain",
        "capability": "abstention",
    },
    {
        "id": "demo-d",
        "question": "Why did we choose Postgres?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["Postgres"],
        "expect_action": "answer",
        "capability": "decision-history",
    },
    {
        "id": "demo-vendor",
        "question": "What was the name of our previous hosting vendor?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["don't have enough information"],
        "expect_action": "abstain",
        "capability": "abstention",
    },
]

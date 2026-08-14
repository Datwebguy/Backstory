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
    """LME multi-session: facts about Ada arrive far apart."""
    return [
        {
            "session_key": "s03",
            "occurred_at": "2023-01-12T09:00:00",
            "title": "Family",
            "turns": [{"role": "user", "content": "My sister is Ada."}],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "has_sister",
                    "object_text": "Ada",
                    "object_entity": "Ada",
                    "object_type": "person",
                    "fact_kind": "state",
                    "aliases": ["my sister"],
                }
            ],
        },
        {
            "session_key": "s11",
            "occurred_at": "2023-03-08T09:00:00",
            "title": "Ada in London",
            "turns": [{"role": "user", "content": "Ada lives in London."}],
            "atoms": [
                {
                    "subject": "Ada",
                    "subject_type": "person",
                    "predicate": "lives_in",
                    "object_text": "London",
                    "object_entity": "London",
                    "object_type": "place",
                    "fact_kind": "state",
                }
            ],
        },
        {
            "session_key": "s24",
            "occurred_at": "2023-07-02T09:00:00",
            "title": "Medicine",
            "turns": [{"role": "user", "content": "She's studying medicine."}],
            "atoms": [
                {
                    "subject": "Ada",
                    "subject_type": "person",
                    "predicate": "studies",
                    "object_text": "medicine",
                    "fact_kind": "state",
                    "aliases": ["she", "my sister"],
                }
            ],
        },
    ]


def scenario_c_abstention() -> list[dict[str, Any]]:
    """Official LME abstention shape: tanks exist, 30-gallon does not."""
    return [
        {
            "session_key": "s07",
            "occurred_at": "2023-04-01T12:00:00",
            "title": "Fish tanks",
            "turns": [
                {
                    "role": "user",
                    "content": "I upgraded my old 10-gallon tank, which has my betta fish, Bubbles.",
                },
                {
                    "role": "user",
                    "content": "I added decorations to the 20-gallon tank to create more hiding places for the fish.",
                },
            ],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "10-gallon tank",
                    "object_entity": "10-gallon tank",
                    "object_type": "thing",
                    "fact_kind": "state",
                    "qualifiers": "capacity=10;unit=gal",
                },
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "20-gallon tank",
                    "object_entity": "20-gallon tank",
                    "object_type": "thing",
                    "fact_kind": "state",
                    "qualifiers": "capacity=20;unit=gal",
                },
                {
                    "subject": "Bubbles",
                    "subject_type": "thing",
                    "predicate": "lives_in",
                    "object_text": "10-gallon tank",
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
            "title": "MacBook plan",
            "turns": [{"role": "user", "content": "I'm planning to buy a MacBook."}],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "prefers",
                    "object_text": "MacBook",
                    "object_entity": "MacBook",
                    "object_type": "thing",
                    "fact_kind": "preference",
                }
            ],
        },
        {
            "session_key": "s10",
            "occurred_at": "2023-03-01T18:00:00",
            "title": "Windows instead",
            "turns": [{"role": "user", "content": "I think I'll get Windows instead."}],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "prefers",
                    "object_text": "Windows laptop",
                    "object_entity": "Windows laptop",
                    "object_type": "thing",
                    "fact_kind": "preference",
                    "update_of": "prefers",
                }
            ],
        },
        {
            "session_key": "s17b",
            "occurred_at": "2023-04-09T18:00:00",
            "title": "Coding need",
            "turns": [{"role": "user", "content": "I need something good for coding."}],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "needs",
                    "object_text": "good for coding",
                    "fact_kind": "state",
                }
            ],
        },
        {
            "session_key": "s29",
            "occurred_at": "2023-06-01T18:00:00",
            "title": "ThinkPad",
            "turns": [{"role": "user", "content": "I bought a ThinkPad."}],
            "atoms": [
                {
                    "subject": "user",
                    "predicate": "bought",
                    "object_text": "ThinkPad",
                    "object_entity": "ThinkPad",
                    "object_type": "thing",
                    "fact_kind": "event",
                    "event_at": "2023-06-01T18:00:00",
                },
                {
                    "subject": "user",
                    "predicate": "owns",
                    "object_text": "ThinkPad",
                    "object_entity": "ThinkPad",
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
        "question": "What do I know about Ada?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["London", "medicine"],
        "expect_action": "answer",
        "capability": "multi-session",
    },
    {
        "id": "demo-c",
        "question": "How many fish are there in my 30-gallon tank?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["don't have enough information"],
        "expect_action": "abstain",
        "capability": "abstention",
    },
    {
        "id": "demo-d",
        "question": "Why did I choose the ThinkPad?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["ThinkPad"],
        "expect_action": "answer",
        "capability": "decision-history",
    },
    {
        "id": "demo-school",
        "question": "What was the name of my secondary school?",
        "question_date": "2023-07-15T00:00:00",
        "expect_contains": ["don't have enough information"],
        "expect_action": "abstain",
        "capability": "abstention",
    },
]

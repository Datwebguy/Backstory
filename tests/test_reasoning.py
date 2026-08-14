from backstory.engine.abstain import Decision
from backstory.engine.reason import template_answer
from backstory.engine.retrieve import RetrievedFact


def _fact(**kwargs) -> RetrievedFact:
    base = dict(
        fact_id=1,
        predicate="tried_restaurant",
        object_text="Seoul Garden",
        fact_kind="state",
        stated_at="2023-04-01T00:00:00",
        valid_from="2023-04-01T00:00:00",
        valid_until="",
        is_current=True,
        status="active",
        polarity=1,
        confidence=0.9,
        qualifiers="",
        speaker="user",
        subject_id=1,
        subject_name="user",
        session_at="2023-04-01T00:00:00",
        quote="I tried Seoul Garden last week.",
    )
    base.update(kwargs)
    return RetrievedFact(**base)


def test_how_many_counts_distinct_objects_not_raw_facts():
    # Re-affirming the same restaurant across sessions (additive predicate)
    # must not inflate the count. Mirrors LongMemEval 6aeb4375: four Korean
    # restaurants scored as 12 because every mention was counted.
    facts = [
        _fact(fact_id=1, object_text="Seoul Garden"),
        _fact(fact_id=2, object_text="Seoul Garden", quote="Went back to Seoul Garden again."),
        _fact(fact_id=3, object_text="Kimchi House"),
        _fact(fact_id=4, object_text="Bibim Bap Co"),
    ]
    decision = Decision("answer", "sufficient", facts)
    answer = template_answer("How many Korean restaurants have I tried?", decision)
    assert answer == "3"


def test_how_many_ignores_superseded_and_negated_facts():
    facts = [
        _fact(fact_id=1, object_text="Seoul Garden"),
        _fact(fact_id=2, object_text="Kimchi House", is_current=False, status="superseded"),
        _fact(fact_id=3, object_text="Old Spot", polarity=-1),
    ]
    decision = Decision("answer", "sufficient", facts)
    answer = template_answer("How many Korean restaurants have I tried?", decision)
    assert answer == "1"

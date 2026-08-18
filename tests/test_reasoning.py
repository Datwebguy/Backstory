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


def test_how_many_ignores_stated_snippets():
    # Heuristic extract stores each turn as a `stated` blob. Counting
    # those rows is how the 12-slice reported 12/11/9 against gold 4/3/2.
    blobs = [
        _fact(
            fact_id=10 + i,
            predicate="stated",
            object_text=f"Long assistant turn {i} that happens to mention Korean restaurants in my city.",
            quote=f"Long assistant turn {i} that happens to mention Korean restaurants in my city.",
        )
        for i in range(8)
    ]
    restaurants = [
        _fact(fact_id=1, object_text="Seoul Garden"),
        _fact(fact_id=2, object_text="Kimchi House"),
        _fact(fact_id=3, object_text="Bibim Bap Co"),
        _fact(fact_id=4, object_text="Hanok BBQ"),
    ]
    decision = Decision("answer", "sufficient", blobs + restaurants)
    answer = template_answer("How many Korean restaurants have I tried?", decision)
    assert answer == "4"


def test_template_answers_are_natural_sentences():
    facts = [
        _fact(fact_id=1, predicate="has", object_text="a sister named Ada", quote="I have a sister named Ada."),
        _fact(fact_id=2, predicate="lives_in", object_text="London", quote="I live in London."),
    ]
    decision = Decision("answer", "sufficient", facts)
    answer = template_answer("What do I know about myself?", decision)
    assert "has a sister named Ada." not in answer
    assert "Ada" in answer
    assert "London" in answer
    assert answer[0].isupper()


def test_name_questions_use_current_not_second_name():
    older = _fact(fact_id=1, predicate="name", object_text="Eben", is_current=False, status="superseded")
    newer = _fact(fact_id=2, predicate="name", object_text="Prince", stated_at="2023-08-01T00:00:00")
    decision = Decision("answer", "sufficient", [older, newer])
    assert template_answer("What is my name?", decision) == "Your name is Prince. Earlier it was Eben."
    second = template_answer("What is my second name?", decision)
    assert "Prince" in second
    assert "second name is Prince" not in second.lower()
    names = template_answer("What are my names?", decision)
    assert "Prince" in names and "Eben" in names


def test_about_me_answers_in_sentences():
    facts = [
        _fact(fact_id=1, predicate="name", object_text="Prince", quote="my name is Prince"),
        _fact(fact_id=2, predicate="lives_in", object_text="Lagos", quote="I live in Lagos."),
    ]
    decision = Decision("answer", "sufficient", facts)
    answer = template_answer("what can you remember about me?", decision)
    assert "Prince" in answer
    assert "Lagos" in answer


def test_how_many_ignores_superseded_and_negated_facts():
    facts = [
        _fact(fact_id=1, object_text="Seoul Garden"),
        _fact(fact_id=2, object_text="Kimchi House", is_current=False, status="superseded"),
        _fact(fact_id=3, object_text="Old Spot", polarity=-1),
    ]
    decision = Decision("answer", "sufficient", facts)
    answer = template_answer("How many Korean restaurants have I tried?", decision)
    assert answer == "1"

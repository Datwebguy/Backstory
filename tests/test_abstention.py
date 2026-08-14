from backstory.engine.abstain import decide
from backstory.engine.retrieve import RetrievedFact


def _fact(**kwargs) -> RetrievedFact:
    base = dict(
        fact_id=1,
        predicate="owns",
        object_text="10-gallon tank",
        fact_kind="state",
        stated_at="2023-04-01T00:00:00",
        valid_from="2023-04-01T00:00:00",
        valid_until="",
        is_current=True,
        status="active",
        polarity=1,
        confidence=0.9,
        qualifiers="capacity=10;unit=gal",
        speaker="user",
        subject_id=1,
        subject_name="user",
        session_at="2023-04-01T00:00:00",
        quote="I upgraded my old 10-gallon tank",
    )
    base.update(kwargs)
    return RetrievedFact(**base)


def test_empty_pack_abstains():
    decision = decide("What was the name of my secondary school?", [])
    assert decision.action == "abstain"


def test_constraint_mismatch_abstains():
    facts = [
        _fact(),
        _fact(fact_id=2, object_text="20-gallon tank", qualifiers="capacity=20;unit=gal", quote="20-gallon tank"),
    ]
    decision = decide("How many fish are there in my 30-gallon tank?", facts)
    assert decision.action == "abstain"
    assert decision.reason.startswith("missing_constraint")


def test_false_premise_named_employer_abstains():
    # Graph only knows about NovaTech; question asserts a job at Google
    # that was never stated. Mirrors LongMemEval gpt4_93159ced_abs.
    facts = [
        _fact(
            fact_id=3,
            predicate="works_at",
            object_text="NovaTech",
            qualifiers="",
            quote="I'm working on a project at NovaTech.",
        ),
    ]
    decision = decide("How long have I worked before my current job at Google?", facts)
    assert decision.action == "abstain"
    assert decision.reason.startswith("false_premise_entity")


def test_true_named_entity_does_not_abstain():
    # Same shape, but the named entity actually is in evidence -> must not
    # trip the false-premise gate.
    facts = [
        _fact(
            fact_id=4,
            predicate="works_at",
            object_text="Google",
            qualifiers="",
            quote="I just started my current job at Google.",
        ),
    ]
    decision = decide("Where do I currently work at Google now?", facts)
    assert decision.action == "answer"


def test_false_premise_unmentioned_person_abstains():
    # "Peter" never appears anywhere in memory -> false premise, even
    # though the question isn't a "now/current" question. Mirrors
    # LongMemEval gpt4_70e84552_abs (fence vs. buying cows from Peter).
    facts = [
        _fact(
            fact_id=5,
            predicate="completed",
            object_text="fixing the fence",
            qualifiers="",
            quote="Congratulations on fixing that broken fence!",
        ),
    ]
    decision = decide(
        "Which task did I complete first, fixing the fence or purchasing three cows from Peter?",
        facts,
    )
    assert decision.action == "abstain"
    assert decision.reason.startswith("false_premise_entity")

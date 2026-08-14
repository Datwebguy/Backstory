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

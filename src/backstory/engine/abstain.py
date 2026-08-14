"""Guarded abstention. The LLM does not get to invent a 'no'.

Inspired by the official LongMemEval abstention example:
  history has 10-gallon and 20-gallon tanks
  question asks about a 30-gallon tank
  correct: refuse, because the asked constraint is missing

Gates, in order:
1. no candidate facts at all -> abstain
2. asked constraint (number+unit, named entity) not matched -> abstain
3. asked predicate family has zero relevant facts -> abstain
4. only contradicted current facts for a unique_state 'now' question -> qualify
5. otherwise answer (possibly with history)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backstory.engine.normalize import norm_text
from backstory.engine.retrieve import RetrievedFact

ABSTAIN_TEXT = (
    "I don't have enough information from your previous conversations to answer that."
)


@dataclass
class Decision:
    action: str  # answer | qualify | abstain
    reason: str
    facts: list[RetrievedFact]


CONSTRAINT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[- ]?(gallon|gal|minute|minutes|month|months|year|years|bike|bikes)?",
    re.I,
)

NOW_RE = re.compile(r"\b(now|currently|current|today)\b", re.I)
PREV_RE = re.compile(r"\b(previously|before|used to|last year|ago)\b", re.I)


def decide(question: str, facts: list[RetrievedFact]) -> Decision:
    if not facts:
        return Decision("abstain", "no_candidates", [])

    relevant = [f for f in facts if _relevant(question, f)]
    if not relevant:
        return Decision("abstain", "no_relevant_facts", facts)

    constraint = _asked_constraint(question)
    if constraint and not any(_satisfies_constraint(f, constraint) for f in relevant):
        return Decision("abstain", f"missing_constraint:{constraint}", relevant)

    if _asks_now(question):
        current = [f for f in relevant if f.is_current]
        unique = [f for f in current if f.predicate in {"lives_in", "works_at", "works_as", "located_in"}]
        if unique:
            open_conflicts = [f for f in unique if f.status == "contradicted" or f.contradicted_by]
            if open_conflicts and len({norm_text(f.object_text) for f in unique}) > 1:
                return Decision("qualify", "unresolved_conflict", unique)
        if not current and not _asks_history(question):
            return Decision("abstain", "no_current_fact", relevant)

    return Decision("answer", "sufficient", relevant)


def _relevant(question: str, fact: RetrievedFact) -> bool:
    q = norm_text(question)
    blob = norm_text(
        " ".join([fact.predicate, fact.object_text, fact.subject_name, fact.qualifiers, fact.quote])
    )
    stop = {
        "the", "what", "where", "when", "how", "why", "does", "did", "was",
        "name", "know", "tell", "about", "currently", "current", "many",
    }
    q_tokens = {
        t.strip("?.,!;:")
        for t in q.split()
        if len(t.strip("?.,!;:")) > 2 and t.strip("?.,!;:") not in stop
    }
    b_tokens = {t.strip("?.,!;:") for t in blob.split()}
    if q_tokens & b_tokens:
        return True
    # commute / duration style
    if "commute" in q and "commute" in blob:
        return True
    if any(w in q for w in ("live", "lived", "living")) and fact.predicate == "lives_in":
        return True
    if any(w in q for w in ("work", "job", "employer")) and fact.predicate.startswith("work"):
        return True
    if "like" in q and fact.predicate in {"likes", "dislikes", "prefers"}:
        return True
    if any(w in q for w in ("own", "have", "how many")) and fact.predicate in {"owns", "has"}:
        return True
    return False


def _asked_constraint(question: str) -> str | None:
    match = CONSTRAINT_RE.search(question)
    if not match:
        return None
    amount, unit = match.group(1), (match.group(2) or "").lower()
    if not unit:
        return None
    # "how many months" is a temporal ask, not an entity constraint
    if unit in {"month", "months", "minute", "minutes", "year", "years"}:
        return None
    return f"{amount}:{unit.rstrip('s')}"


def _satisfies_constraint(fact: RetrievedFact, constraint: str) -> bool:
    amount, unit = constraint.split(":")
    blob = norm_text(" ".join([fact.object_text, fact.qualifiers, fact.quote]))
    if amount in blob and unit in blob:
        return True
    if f"{amount}-{unit}" in blob or f"{amount} {unit}" in blob:
        return True
    return False


def _asks_now(question: str) -> bool:
    return bool(NOW_RE.search(question))


def _asks_history(question: str) -> bool:
    return bool(PREV_RE.search(question))

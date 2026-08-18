"""Guarded abstention. The LLM does not get to invent a 'no'.

Inspired by the official LongMemEval abstention example:
  history has 10-gallon and 20-gallon tanks
  question asks about a 30-gallon tank
  correct: refuse, because the asked constraint is missing

Gates, in order:
1. no candidate facts at all -> abstain
2. asked predicate family has zero relevant facts -> abstain
3. asked constraint (number+unit) not matched -> abstain
4. question names a proper noun (person/org/place) that appears nowhere
   in the retrieved evidence -> abstain (false premise, e.g. "my job at
   Google" when the graph only knows about NovaTech)
5. comparison / "which first, A or B" question where at least one
   alternative has no supporting evidence -> abstain (missing conjunct)
6. only contradicted current facts for a unique_state 'now' question -> qualify
7. otherwise answer (possibly with history)
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
    r"(\d+(?:\.\d+)?)\s*[- ]?"
    r"(gallon|gal|gb|tb|mb|core|cores|cpu|cpus|node|nodes|seat|seats|"
    r"licence|licences|license|licenses|replica|replicas|"
    r"minute|minutes|month|months|year|years|bike|bikes)?",
    re.I,
)

NOW_RE = re.compile(r"\b(now|currently|current|today)\b", re.I)
PREV_RE = re.compile(r"\b(previously|before|used to|last year|ago)\b", re.I)
WHY_RE = re.compile(r"\b(why|reason|because|rationale)\b", re.I)

# Predicates that carry the justification behind a choice. A "why"
# question needs these even though they rarely share vocabulary with the
# thing being asked about: "why did we choose Postgres" has no token in
# common with "needs strong consistency for billing records".
REASON_PREDICATES = {"needs", "decided", "prefers", "requires", "wants"}

# The heuristic extractor always emits "name"; an LLM extractor is free
# to phrase the predicate differently (has_name, full_name, ...) despite
# prompt guidance, so anything that means the same thing is accepted.
NAME_PREDICATES = {"name", "has_name", "full_name", "called"}


def decide(question: str, facts: list[RetrievedFact]) -> Decision:
    if not facts:
        return Decision("abstain", "no_candidates", [])

    relevant = [f for f in facts if _relevant(question, f)]
    if not relevant:
        return Decision("abstain", "no_relevant_facts", facts)
    relevant = _add_supporting_history(question, relevant, facts)

    constraint = _asked_constraint(question)
    if constraint and not any(_satisfies_constraint(f, constraint) for f in relevant):
        return Decision("abstain", f"missing_constraint:{constraint}", relevant)

    named = _asked_named_entities(question)
    if named:
        evidence_blob = _evidence_blob(facts)
        unmatched = [n for n in named if norm_text(n) not in evidence_blob]
        if unmatched:
            return Decision("abstain", f"false_premise_entity:{unmatched[0]}", relevant)

    # Official _abs items are often "which first, A or B?" when only A
    # exists. Related evidence is not enough: every alternative the
    # question treats as real has to appear in the graph, or we refuse.
    alternatives = _asked_alternatives(question)
    if alternatives:
        evidence_blob = _evidence_blob(facts)
        missing = [alt for alt in alternatives if not _covers_alternative(alt, evidence_blob)]
        if missing:
            return Decision("abstain", f"missing_conjunct:{missing[0][:40]}", relevant)

    if _asks_now(question):
        current = [f for f in relevant if f.is_current]
        unique = [f for f in current if f.predicate in {"lives_in", "works_at", "works_as", "located_in"} | NAME_PREDICATES]
        if unique:
            open_conflicts = [f for f in unique if f.status == "contradicted" or f.contradicted_by]
            if open_conflicts and len({norm_text(f.object_text) for f in unique}) > 1:
                return Decision("qualify", "unresolved_conflict", unique)
        if not current and not _asks_history(question):
            return Decision("abstain", "no_current_fact", relevant)

    return Decision("answer", "sufficient", relevant)


# Words a person may reasonably use for the same stored concept. Exact
# token matching alone fails the obvious cases: a fact stored as
# "birthday" is invisible to a question asking "birthdate", and an
# LLM-chosen predicate like born_in is invisible to "when was I born".
_SYNONYM_GROUPS = (
    {"birthday", "birthdate", "birth", "born", "dob"},
    {"name", "called", "named"},
    {"job", "work", "works", "worked", "employer", "role", "title"},
    {"live", "lives", "lived", "living", "based", "located", "location"},
    {"email", "mail", "address"},
    {"phone", "mobile", "number"},
)

_STEM_PREFIX = 5


def _expand_synonyms(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for group in _SYNONYM_GROUPS:
        if expanded & group:
            expanded |= group
    return expanded


def _tokens_overlap(q_tokens: set[str], b_tokens: set[str]) -> bool:
    """Relevance match that tolerates synonyms and word endings.

    Exact intersection first, then the same comparison after synonym
    expansion, then a shared word stem so plurals and inflections
    (instance/instances, birthday/birthdate) line up. Kept deliberately
    conservative: a shared prefix must be at least _STEM_PREFIX
    characters, so short words cannot collide by accident.
    """
    if q_tokens & b_tokens:
        return True
    expanded = _expand_synonyms(q_tokens)
    if expanded & b_tokens:
        return True
    for qt in expanded:
        if len(qt) < _STEM_PREFIX:
            continue
        for bt in b_tokens:
            if len(bt) < _STEM_PREFIX:
                continue
            if qt[:_STEM_PREFIX] == bt[:_STEM_PREFIX]:
                return True
    return False


def _add_supporting_history(
    question: str,
    relevant: list[RetrievedFact],
    facts: list[RetrievedFact],
) -> list[RetrievedFact]:
    """Pull in the context a relevant fact points at, without widening the topic.

    Two additions, both anchored to facts already judged relevant, so
    this cannot introduce an unrelated subject:

    1. Whatever a relevant fact replaced. "Why did we choose Postgres"
       matched the current Postgres facts by name, but the answer lives
       in the MongoDB preference that Postgres superseded. Following
       SUPERSEDES backwards is the thing a graph can do that a snippet
       store cannot, and it is what the knowledge-update and
       decision-history cases are actually about.
    2. For a "why" question only, the requirement style facts that
       justify a choice. These share no vocabulary with the question by
       nature, so token matching will never reach them.
    """
    chosen = {f.fact_id: f for f in relevant}
    relevant_ids = set(chosen)

    for fact in facts:
        if fact.fact_id in chosen:
            continue
        if fact.superseded_by is not None and fact.superseded_by in relevant_ids:
            chosen[fact.fact_id] = fact

    if WHY_RE.search(question):
        for fact in facts:
            if fact.fact_id not in chosen and fact.predicate in REASON_PREDICATES:
                chosen[fact.fact_id] = fact

    # Preserve the caller's ordering (current first, then by date).
    return [f for f in facts if f.fact_id in chosen]


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
    # Predicates are snake_case, so born_in has to become {born, in} for a
    # question asking "when was I born" to reach it.
    b_tokens = {t.strip("?.,!;:") for t in blob.replace("_", " ").split()}
    if _tokens_overlap(q_tokens, b_tokens):
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
    if any(w in q for w in ("name", "called")) and fact.predicate in NAME_PREDICATES:
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


_QUESTION_STARTERS = {
    "how", "what", "where", "when", "why", "which", "who", "whose",
    "do", "does", "did", "is", "are", "was", "were", "should", "could",
    "would", "can", "will", "have", "has", "had", "tell", "i", "i'm",
}


def _asked_named_entities(question: str) -> list[str]:
    """Proper-noun-like tokens the question asserts as fact.

    Used to catch false-premise questions ("my current job at Google")
    where the named entity was never mentioned anywhere in memory.
    Sentence-initial capitals are skipped since English capitalizes the
    first word regardless of whether it's a proper noun.
    """
    words = question.strip().split()
    names = []
    for i, word in enumerate(words):
        core = word.strip("?.,!;:\"'")
        if not core or not core[0].isupper() or core.upper() == core:
            continue
        if i == 0 or core.lower() in _QUESTION_STARTERS:
            continue
        if len(core) < 3:
            continue
        names.append(core)
    return names


_ALT_STOP = {
    "the", "a", "an", "my", "our", "your", "his", "her", "their",
    "first", "then", "later", "from", "with", "that", "this", "those",
    "these", "did", "do", "does", "have", "has", "had", "was", "were",
    "been", "and", "for", "into", "onto",
}


def _asked_alternatives(question: str) -> list[str]:
    """Split a which/first comparison into the events it treats as real.

    Official abstention items often ask which of two tasks happened
    first when only one was ever stated. This is an engine rule, not a
    per-question special case: every alternative must be grounded.
    """
    if not re.search(r"\b(which|first)\b", question, re.I):
        return []
    if not re.search(r"\bor\b", question, re.I):
        return []
    tail = question
    if "," in question:
        tail = question[question.rfind(",") + 1 :]
    tail = tail.strip(" ?.!")
    parts = re.split(r"\s+or\s+", tail, flags=re.I)
    alts = [part.strip(" '\"") for part in parts if len(part.strip(" '\"")) > 2]
    return alts if len(alts) >= 2 else []


def _covers_alternative(alt: str, evidence_blob: str) -> bool:
    tokens = [
        t
        for t in re.findall(r"[a-z0-9]+", norm_text(alt))
        if len(t) > 2 and t not in _ALT_STOP
    ]
    if not tokens:
        return True
    hits = sum(1 for t in tokens if t in evidence_blob)
    return hits >= max(1, (len(tokens) + 1) // 2)


def _evidence_blob(facts: list[RetrievedFact]) -> str:
    return norm_text(
        " ".join(f"{f.object_text} {f.qualifiers} {f.quote} {f.subject_name}" for f in facts)
    )


def _asks_now(question: str) -> bool:
    return bool(NOW_RE.search(question))


def _asks_history(question: str) -> bool:
    return bool(PREV_RE.search(question))

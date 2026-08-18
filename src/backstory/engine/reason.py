"""Answer generation from a graph evidence pack.

If the abstention gate says abstain, this module is not called.
If the LLM is unavailable, a deterministic template still answers
simple current-state / count / history questions so tests and demos work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backstory.engine.abstain import ABSTAIN_TEXT, NAME_PREDICATES, Decision
from backstory.engine.normalize import norm_text
from backstory.engine.retrieve import RetrievedFact


@dataclass
class Answer:
    text: str
    action: str
    reason: str
    evidence: list[RetrievedFact]


def render_pack(decision: Decision) -> str:
    lines = []
    for fact in decision.facts:
        flag = "current" if fact.is_current else "historical"
        if fact.status == "contradicted":
            flag = "conflict"
        lines.append(
            f"- [{flag}] {fact.subject_name} {fact.predicate} {fact.object_text} "
            f"(stated {fact.stated_at or fact.session_at}; quote: {fact.quote[:180]})"
        )
    return "\n".join(lines) if lines else "(no facts)"


_STATED_PREDICATES = {"stated"}
_GENERIC_COUNT_WORDS = {
    "item", "items", "thing", "things", "one", "ones", "lot", "lots",
    "kind", "kinds", "type", "types",
}
_COUNT_STOP = {
    "have", "has", "had", "did", "do", "does", "am", "is", "are", "was",
    "were", "i", "we", "you", "my", "our", "the", "a", "an", "to", "from",
    "in", "on", "at", "of", "or", "and", "need", "needed", "currently",
    "currently", "been", "being", "that", "this", "for", "with",
}


def template_answer(question: str, decision: Decision) -> str:
    if decision.action == "abstain":
        return ABSTAIN_TEXT
    facts = decision.facts
    if decision.action == "qualify":
        options = ", ".join(sorted({f.object_text for f in facts if f.is_current}))
        return (
            f"I have conflicting current information ({options}) and do not have "
            "a later statement that resolves it."
        )
    q = question.lower()
    if "how many" in q:
        return str(_count_distinct_objects(question, facts))
    if any(w in q for w in ("where do i live", "where do i currently live", "where do i live now")):
        current = next((f for f in facts if f.is_current and f.predicate == "lives_in"), None)
        if current:
            history = [f for f in facts if f.predicate == "lives_in" and not f.is_current]
            extra = ""
            if history:
                extra = " Previously you lived in " + ", ".join(h.object_text for h in history) + "."
            return f"You live in {current.object_text}.{extra}"
    if any(w in q for w in ("my name", "i called", "call me", "who am i")):
        current = next((f for f in facts if f.is_current and f.predicate in NAME_PREDICATES), None)
        if current:
            return f"Your name is {current.object_text.strip().title()}."
    if "work" in q and "now" in q:
        current = next((f for f in facts if f.is_current and f.predicate.startswith("work")), None)
        if current:
            return _fact_sentence(current)
    if "why" in q:
        sentences = [_fact_sentence(f) for f in facts]
        return "Based on your earlier statements: " + " ".join(s.rstrip(".") + "." for s in sentences if s)
    if "what do i know" in q or "tell me about" in q:
        sentences = [_fact_sentence(f) for f in facts if f.is_current]
        return " ".join(s for s in sentences if s) or ABSTAIN_TEXT
    current = [f for f in facts if f.is_current] or facts
    q_tokens = {t for t in question.lower().split() if len(t) > 2}

    def score(fact: RetrievedFact) -> int:
        blob = f"{fact.object_text} {fact.quote} {fact.predicate}".lower()
        lexical = sum(1 for t in q_tokens if t in blob)
        structured = 2 if fact.predicate not in _STATED_PREDICATES else 0
        short = 1 if len(fact.object_text or "") < 80 else 0
        return lexical + structured + short

    current.sort(key=score, reverse=True)
    sentence = _fact_sentence(current[0])
    if sentence:
        return sentence
    quote = (current[0].quote or "").strip()
    if quote:
        return _first_sentence(quote)
    return current[0].object_text


def _count_distinct_objects(question: str, facts: list[RetrievedFact]) -> int:
    """Count distinct *objects of the asked type*, not raw current fact rows.

    Re-affirming the same restaurant (or bike, project, …) across sessions
    must not inflate the number. Full-turn `stated` snippets are never
    countable objects on their own.
    """
    current = [f for f in facts if f.is_current and f.polarity > 0]
    structured = [f for f in current if f.predicate not in _STATED_PREDICATES]
    focus = _asked_count_focus(question)
    pool = structured or current
    if focus:
        typed = [f for f in pool if _fact_matches_focus(f, focus)]
        if typed:
            pool = typed
    names: set[str] = set()
    for fact in pool:
        if fact.predicate in _STATED_PREDICATES or len(fact.object_text or "") >= 80:
            names.update(_names_from_text(f"{fact.object_text} {fact.quote}", focus))
            continue
        names.add(norm_text(fact.object_text))
    names.discard("")
    return len(names)


def _asked_count_focus(question: str) -> set[str]:
    match = re.search(r"how many\s+(.+)", question.lower())
    if not match:
        return set()
    focus: set[str] = set()
    for word in re.findall(r"[a-z]+", match.group(1)):
        if word in _COUNT_STOP:
            if focus:
                break
            continue
        focus.add(word)
        if word.endswith("s") and len(word) > 4:
            focus.add(word[:-1])
        elif not word.endswith("s"):
            focus.add(word + "s")
    return {w for w in focus if w not in _GENERIC_COUNT_WORDS}


def _fact_matches_focus(fact: RetrievedFact, focus: set[str]) -> bool:
    blob = norm_text(f"{fact.predicate} {fact.object_text} {fact.quote} {fact.qualifiers}")
    return any(token in blob for token in focus)


def _names_from_text(text: str, focus: set[str]) -> set[str]:
    names: set[str] = set()
    for quoted in re.findall(r"[\"']([^\"']{2,60})[\"']", text):
        names.add(norm_text(quoted))
    for title in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text):
        if norm_text(title) in focus:
            continue
        names.add(norm_text(title))
    return names


def _fact_sentence(fact: RetrievedFact) -> str:
    obj = (fact.object_text or "").strip().rstrip(".")
    if not obj or fact.predicate in _STATED_PREDICATES:
        return ""
    who = (fact.subject_name or "").strip()
    subject = "You" if not who or who.lower() in {"user", "you", "i", "me"} else who
    pred = fact.predicate
    if pred in NAME_PREDICATES:
        return f"Your name is {obj.title()}."
    if pred == "lives_in":
        return f"{subject} live{'s' if subject != 'You' else ''} in {obj}."
    if pred == "located_in":
        if subject == "You":
            return f"You are based in {obj}."
        return f"{subject} is based in {obj}."
    if pred == "works_at":
        return f"{subject} work{'s' if subject != 'You' else ''} at {obj}."
    if pred == "works_as":
        return f"{subject} work{'s' if subject != 'You' else ''} as {obj}."
    if pred == "owns":
        return f"{subject} own{'s' if subject != 'You' else ''} {obj}."
    if pred == "has":
        return f"{subject} have {obj}." if subject == "You" else f"{subject} has {obj}."
    if pred == "likes":
        return f"{subject} like{'s' if subject != 'You' else ''} {obj}."
    if pred == "graduated":
        return f"{subject} graduated with {obj}."
    if pred == "personal_best":
        return f"Your personal best is {obj}."
    if pred == "commute":
        return f"Your commute is {obj}."
    human = pred.replace("_", " ")
    return f"{subject} {human} {obj}."


def _first_sentence(text: str) -> str:
    chunk = " ".join(text.split())
    for sep in (". ", "? ", "! "):
        if sep in chunk:
            return chunk.split(sep, 1)[0].rstrip(".?!") + "."
    return chunk[:240]


def llm_answer(
    question: str,
    question_date: str,
    decision: Decision,
    *,
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    pack = render_pack(decision)
    prompt = f"""Answer using ONLY the evidence pack. If the pack is insufficient, say you do not have enough information.
Do not invent names, places, or numbers.
Write one or two natural sentences. Do not echo raw predicates
("has sister Ada. lives in London."). If the question is "how many",
count distinct objects of the asked type, never the number of evidence rows.
If the question assumes something the pack never states, refuse.

Question date: {question_date}
Question: {question}

Evidence pack:
{pack}

Write a concise answer. Mention dates when they matter. If evidence conflicts, say so.
"""
    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are Backstory. You only speak from retrieved memories."},
            {"role": "user", "content": prompt},
        ],
    )
    return _normalize_llm_text((completion.choices[0].message.content or "").strip())


_TEXT_NORMALIZE = str.maketrans({
    " ": " ",  # narrow no-break space
    " ": " ",  # no-break space
    " ": " ",  # thin space
    "‐": "-",  # hyphen
    "‑": "-",  # non-breaking hyphen
    "‒": "-",  # figure dash
    "–": "-",  # en dash
    "—": "-",  # em dash
})


def _normalize_llm_text(text: str) -> str:
    """Some models favor typographic whitespace/dash variants that render
    identically on screen but are not ASCII, silently breaking any exact
    or substring match (e.g. "Company B" != "Company B").
    """
    return text.translate(_TEXT_NORMALIZE)

"""Answer generation from a graph evidence pack.

If the abstention gate says abstain, this module is not called.
If the LLM is unavailable, a deterministic template still answers
simple current-state / count / history questions so tests and demos work.
"""

from __future__ import annotations

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
        current = [f for f in facts if f.is_current and f.polarity > 0]
        # Re-affirming the same fact across sessions (additive predicates
        # like "owns"/"likes") produces one Fact per mention; the count the
        # user wants is distinct objects, not raw fact rows.
        distinct_objects = {norm_text(f.object_text) for f in current}
        return str(len(distinct_objects))
    if any(w in q for w in ("where do i live", "where do i currently live", "where do i live now")):
        current = next((f for f in facts if f.is_current and f.predicate == "lives_in"), None)
        if current:
            history = [f for f in facts if f.predicate == "lives_in" and not f.is_current]
            extra = ""
            if history:
                extra = " Previously: " + ", ".join(h.object_text for h in history) + "."
            return f"{current.object_text}.{extra}"
    if any(w in q for w in ("my name", "i called", "call me", "who am i")):
        current = next((f for f in facts if f.is_current and f.predicate in NAME_PREDICATES), None)
        if current:
            return f"Your name is {current.object_text.strip().title()}."
    if "work" in q and "now" in q:
        current = next((f for f in facts if f.is_current and f.predicate.startswith("work")), None)
        if current:
            return current.object_text
    if "why" in q:
        bits = [f"{f.predicate} {f.object_text}" for f in facts]
        return "Based on your earlier statements: " + "; ".join(bits) + "."
    if "what do i know" in q or "tell me about" in q:
        return " ".join(f"{f.predicate.replace('_', ' ')} {f.object_text}." for f in facts if f.is_current)
    current = [f for f in facts if f.is_current] or facts
    q_tokens = {t for t in question.lower().split() if len(t) > 2}

    def score(fact: RetrievedFact) -> int:
        blob = f"{fact.object_text} {fact.quote} {fact.predicate}".lower()
        return sum(1 for t in q_tokens if t in blob)

    current.sort(key=score, reverse=True)
    return current[0].object_text


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

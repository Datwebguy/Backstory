"""Memory engine facade: ingest sessions and answer questions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backstory.config import Settings, get_settings
from backstory.engine.abstain import ABSTAIN_TEXT, decide
from backstory.engine.extract import atoms_from_dicts, extract_with_llm, heuristic_extract
from backstory.engine.mutate import GraphMutator
from backstory.engine.normalize import Atom
from backstory.engine.reason import Answer, llm_answer, template_answer
from backstory.engine.resolve import EntityResolver
from backstory.engine.retrieve import Retriever
from backstory.hydra.client import HydraClient
from backstory.sidecar.store import SidecarStore
from backstory.sidecar.embeddings import lexical_embed

# Per turn character budget for the LLM extraction window. See the note
# where the window is built in ingest_session.
_WINDOW_CHARS_PER_TURN = 700


@dataclass
class IngestReport:
    session_id: int
    atoms: int
    mutations: list[str]


class MemoryEngine:
    def __init__(self, settings: Settings | None = None, hydra: HydraClient | None = None):
        self.settings = settings or get_settings()
        self.settings.backstory_data_dir.mkdir(parents=True, exist_ok=True)
        self.hydra = hydra or HydraClient(self.settings)
        self.sidecar = SidecarStore(self.settings.backstory_data_dir / "sidecar.sqlite")
        self.resolver = EntityResolver(self.sidecar)
        self.mutator = GraphMutator(self.hydra, self.sidecar, self.resolver)
        self.retriever = Retriever(self.hydra, self.sidecar)

    def close(self) -> None:
        self.hydra.close()
        self.sidecar.close()

    def ingest_session(
        self,
        *,
        user_key: str,
        session_key: str,
        occurred_at: str,
        turns: list[dict[str, Any]],
        title: str = "",
        preextracted: list[dict[str, Any]] | None = None,
    ) -> IngestReport:
        user_id = self.mutator.ensure_user(user_key)
        session_id = self.mutator.write_session(user_id, session_key, occurred_at, title or session_key)
        mutations: list[str] = []
        atom_count = 0
        window: list[str] = []
        for idx, turn in enumerate(turns):
            role = turn.get("role") or "user"
            content = turn.get("content") or ""
            message_id = self.mutator.write_message(
                session_id, user_key, session_key, role, idx, occurred_at, content
            )
            # Cap each turn's contribution to the extraction window. Real
            # conversations (and benchmark haystacks) contain very long
            # assistant turns, and an uncapped six turn window makes every
            # extraction prompt grow without bound: measured at roughly one
            # turn per minute on a 130k token conversation, versus seconds
            # once bounded. Durable facts appear early in a turn, so the
            # head of each message is what extraction actually needs.
            window.append(f"{role.upper()}: {content[:_WINDOW_CHARS_PER_TURN]}")
            if len(window) > 6:
                window = window[-6:]
            atoms: list[Atom] = []
            if preextracted is not None:
                # preextracted is session-level; apply on last turn only
                if idx == len(turns) - 1:
                    atoms = atoms_from_dicts(preextracted, occurred_at)
            elif self.settings.openai_api_key and role in {"user", "assistant"}:
                # The LLM is an upgrade to extraction quality, never a
                # requirement for storing a fact. A missing client
                # library, a rate limit, or a provider outage must not
                # cost the user their memory, so fall back to the
                # heuristic path rather than failing the whole ingest.
                try:
                    atoms = extract_with_llm(
                        "\n".join(window),
                        occurred_at,
                        api_key=self.settings.openai_api_key,
                        base_url=self.settings.openai_base_url,
                        model=self.settings.backstory_extract_model,
                    )
                except Exception:
                    atoms = heuristic_extract(content, occurred_at, speaker=role)
            elif role in {"user", "assistant"}:
                atoms = heuristic_extract(content, occurred_at, speaker=role)
            for atom in atoms:
                if not atom.stated_at:
                    atom.stated_at = occurred_at
                result = self.mutator.apply_atom(
                    atom,
                    session_id=session_id,
                    message_id=message_id,
                    user_id=user_id,
                    user_key=user_key,
                )
                if result:
                    mutations.append(result.action)
                    atom_count += 1
                    self.sidecar.put_embedding(
                        result.fact_id,
                        "fact",
                        f"{atom.predicate} {atom.object_text}",
                        lexical_embed(f"{atom.predicate} {atom.object_text}"),
                    )
        return IngestReport(session_id=session_id, atoms=atom_count, mutations=mutations)

    def ask(
        self,
        *,
        user_key: str,
        question: str,
        question_date: str = "",
        as_of: str | None = None,
        naive: bool = False,
    ) -> Answer:
        seeds = self.retriever.seed_entities(question, user_key)
        facts = self.retriever.facts_for_entities(seeds, as_of=as_of)
        facts = self.retriever.attach_conflicts(facts)
        # Prefer current facts for "now" questions by sorting
        facts.sort(key=lambda f: (not f.is_current, f.stated_at))
        if naive:
            for fact in facts:
                fact.is_current = True
                fact.status = "active"
                fact.contradicted_by = []
        decision = decide(question, facts)
        if decision.action == "abstain":
            return Answer(ABSTAIN_TEXT, decision.action, decision.reason, decision.facts)
        text = ""
        if self.settings.openai_api_key:
            # Same reasoning as extraction: a provider failure should
            # degrade the wording, not lose the answer. The evidence pack
            # is already assembled from the graph at this point.
            try:
                text = llm_answer(
                    question,
                    question_date,
                    decision,
                    api_key=self.settings.openai_api_key,
                    base_url=self.settings.openai_base_url,
                    model=self.settings.backstory_answer_model,
                )
            except Exception:
                text = ""
        if not text:
            text = template_answer(question, decision)
        return Answer(text, decision.action, decision.reason, decision.facts)


def default_data_dir() -> Path:
    return Path("runs/local")

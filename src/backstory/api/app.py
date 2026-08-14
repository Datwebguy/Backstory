from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backstory.config import get_settings
from backstory.demo.load_demo import load
from backstory.demo.scenarios import USER
from backstory.engine.memory import MemoryEngine
from backstory.hydra.client import HydraClient


@lru_cache(maxsize=1)
def engine() -> MemoryEngine:
    return MemoryEngine()


app = FastAPI(title="Backstory", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TurnIn(BaseModel):
    role: str
    content: str


class SessionIn(BaseModel):
    user_key: str = USER
    session_key: str
    occurred_at: str
    title: str = ""
    turns: list[TurnIn]
    atoms: list[dict] | None = None


class AskIn(BaseModel):
    user_key: str = USER
    question: str
    question_date: str = ""


@app.get("/api/health")
def health() -> dict:
    hydra = HydraClient()
    try:
        return {"ok": hydra.ready(), "hydra": hydra.ready()}
    finally:
        hydra.close()


@app.post("/api/sessions")
def create_session(body: SessionIn) -> dict:
    if not engine().hydra.ready():
        raise HTTPException(503, "HydraDB is not ready")
    report = engine().ingest_session(
        user_key=body.user_key,
        session_key=body.session_key,
        occurred_at=body.occurred_at,
        turns=[t.model_dump() for t in body.turns],
        title=body.title,
        preextracted=body.atoms,
    )
    return {"session_id": report.session_id, "atoms": report.atoms, "mutations": report.mutations}


@app.post("/api/ask")
def ask(body: AskIn) -> dict:
    if not engine().hydra.ready():
        raise HTTPException(503, "HydraDB is not ready")
    answer = engine().ask(
        user_key=body.user_key,
        question=body.question,
        question_date=body.question_date,
    )
    return {
        "text": answer.text,
        "action": answer.action,
        "reason": answer.reason,
        "evidence": [
            {
                "fact_id": f.fact_id,
                "predicate": f.predicate,
                "object_text": f.object_text,
                "is_current": f.is_current,
                "status": f.status,
                "stated_at": f.stated_at,
                "session_at": f.session_at,
                "quote": f.quote,
            }
            for f in answer.evidence
        ],
    }


@app.post("/api/demo/load")
def load_demo() -> dict:
    load(engine())
    return {"ok": True, "user_key": USER}


@app.get("/api/timeline")
def timeline(user_key: str = USER) -> dict:
    facts = engine().retriever.facts_for_entities(
        engine().retriever.seed_entities("timeline history facts", user_key)
    )
    facts.sort(key=lambda f: f.stated_at or f.session_at)
    return {
        "facts": [
            {
                "fact_id": f.fact_id,
                "predicate": f.predicate,
                "object_text": f.object_text,
                "is_current": f.is_current,
                "status": f.status,
                "stated_at": f.stated_at,
                "quote": f.quote,
            }
            for f in facts
        ]
    }


web = Path(__file__).resolve().parents[3] / "apps" / "web"
if web.exists():
    app.mount("/", StaticFiles(directory=web, html=True), name="web")


def main() -> None:
    import uvicorn

    uvicorn.run("backstory.api.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

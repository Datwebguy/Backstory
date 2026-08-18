from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from backstory.api import auth
from backstory.config import get_settings
from backstory.demo.load_demo import isolated_demo_key, load
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
_settings = get_settings()
app.add_middleware(
    SessionMiddleware,
    secret_key=_settings.session_secret,
    same_site="lax",
    https_only=_settings.session_https_only,
)
app.state.oauth = auth.register_oauth(_settings)
app.include_router(auth.router)


class TurnIn(BaseModel):
    role: str
    content: str


class SessionIn(BaseModel):
    session_key: str
    occurred_at: str
    title: str = ""
    turns: list[TurnIn]
    atoms: list[dict] | None = None


class AskIn(BaseModel):
    question: str
    question_date: str = ""
    scope: str = "real"


def _effective_user_key(user_key: str, scope: str) -> str:
    """Demo scenarios never touch the account's real memory.

    They write into a deterministic per-account sandbox namespace
    instead, so a signed-in user's own facts never mix with fictional
    demo content, and the sandbox is still fully isolated per account
    (derived from the authenticated session, never client-chosen).
    """
    return isolated_demo_key(user_key) if scope == "demo" else user_key


@app.get("/api/health")
def health() -> dict:
    hydra = HydraClient()
    try:
        return {"ok": hydra.ready(), "hydra": hydra.ready()}
    finally:
        hydra.close()


@app.post("/api/sessions")
def create_session(body: SessionIn, user_key: str = Depends(auth.require_user)) -> dict:
    if not engine().hydra.ready():
        raise HTTPException(503, "HydraDB is not ready")
    report = engine().ingest_session(
        user_key=user_key,
        session_key=body.session_key,
        occurred_at=body.occurred_at,
        turns=[t.model_dump() for t in body.turns],
        title=body.title,
        preextracted=body.atoms,
    )
    return {"session_id": report.session_id, "atoms": report.atoms, "mutations": report.mutations}


@app.post("/api/ask")
def ask(body: AskIn, user_key: str = Depends(auth.require_user)) -> dict:
    if not engine().hydra.ready():
        raise HTTPException(503, "HydraDB is not ready")
    answer = engine().ask(
        user_key=_effective_user_key(user_key, body.scope),
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
def load_demo(user_key: str = Depends(auth.require_user)) -> dict:
    if not engine().hydra.ready():
        raise HTTPException(503, "HydraDB is not ready")
    demo_key = _effective_user_key(user_key, "demo")
    load(engine(), user_key=demo_key)
    return {"ok": True, "user_key": demo_key}


@app.get("/api/timeline")
def timeline(user_key: str = Depends(auth.require_user)) -> dict:
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


WEB_DIR = (
    Path(_settings.backstory_web_dir)
    if _settings.backstory_web_dir
    else Path(__file__).resolve().parents[3] / "apps" / "web"
)
LANDING = WEB_DIR / "index.html"
APP_UI = WEB_DIR / "app.html"


def _serve(path: Path) -> FileResponse:
    if not path.exists():
        raise HTTPException(500, f"UI file missing: {path}")
    return FileResponse(path, headers={"Cache-Control": "no-store, max-age=0"})


@app.get("/")
def home() -> FileResponse:
    return _serve(LANDING)


@app.get("/app")
def app_ui() -> FileResponse:
    return _serve(APP_UI)


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run("backstory.api.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

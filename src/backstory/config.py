from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hydra_http_url: str = "http://127.0.0.1:8443"
    hydra_bolt_url: str = "bolt://127.0.0.1:7687"
    hydra_admin_url: str = "http://127.0.0.1:9090"
    hydra_token: str = "backstory-local-dev-token-32bytes!"
    hydra_namespace: str = "default"
    hydra_graph_id: str = "default"
    hydra_cell_id: str = "cell-0"

    backstory_data_dir: Path = Path("runs/local")

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    backstory_extract_model: str = "gpt-4o-mini"
    backstory_answer_model: str = "gpt-4o-mini"
    backstory_embed_model: str = "text-embedding-3-small"
    backstory_judge_model: str = "gpt-4o"

    working_memory_turns: int = 8
    retrieve_seed_k: int = 12
    evidence_fact_limit: int = 12

    google_client_id: str = ""
    google_client_secret: str = ""
    session_secret: str = "backstory-dev-session-secret-change-me"


def get_settings() -> Settings:
    return Settings()

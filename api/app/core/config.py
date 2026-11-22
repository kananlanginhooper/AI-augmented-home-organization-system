"""Runtime settings. The only place environment variables (and the .env file) are read."""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.environ.get("ENV_FILE", ".env"), extra="ignore")

    # Database: DATABASE_URL wins; otherwise Postgres from DB_*; with neither, a local SQLite file (tests).
    database_url: str = ""
    db_host: str = ""
    db_port: int = 5432
    db_name: str = "home_organization_inventory"
    db_user: str = "home_organization_inventory"
    db_password: str = ""

    ui_base_path: str = "/"
    public_url: str = ""
    frame_ancestors: str = ""
    login: str = "off"
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    ui_dir: Path = Path("ui")

    photo_dir: Path = Path("data/photos")

    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "high"
    ai_worker: str = "on"

    gameplan_api_url: str = ""
    gameplan_api_token: str = ""
    gameplan_area: str = "Home"

    @cached_property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        if not self.db_host:
            return "sqlite:///./local.db"
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)

    @property
    def ui_base(self) -> str:
        base = self.ui_base_path.strip("/")
        return f"/{base}/" if base else "/"

    @property
    def frame_ancestor_list(self) -> list[str]:
        return self.frame_ancestors.split()

    @property
    def api_worker_enabled(self) -> bool:
        return bool(self.anthropic_api_key) and self.ai_worker == "on"


settings = Settings()

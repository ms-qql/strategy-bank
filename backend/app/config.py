"""Typisierte App-Konfiguration via pydantic-settings."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    # OpenCode ist bereits global auf diesem Host authentifiziert (eigenes
    # Provider-Credential-Management) — die App übergibt nie einen API-Key.
    opencode_binary: str = "/home/dev/.opencode/bin/opencode"
    extraction_model: str = "opencode-go/deepseek-v4-flash"
    extraction_prompt_version: str = "v1"
    extraction_timeout_seconds: float = 300.0

    source_max_bytes: int = 2 * 1024 * 1024  # 2 MB, siehe PROJ-1 Edge Cases

    # CORS: Dev-Default fürs Next.js-Frontend (Port 3000). Prod via .env
    # überschreiben (CSV-String, z. B. "https://app.example.com,https://www.example.com").
    cors_allow_origins: list[str] = ["http://localhost:3000"]

    env: str = "development"

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


settings = Settings()  # type: ignore[call-arg]

"""Typisierte App-Konfiguration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    # OpenCode ist bereits global auf diesem Host authentifiziert (eigenes
    # Provider-Credential-Management) — die App übergibt nie einen API-Key.
    opencode_binary: str = "/home/dev/.opencode/bin/opencode"
    extraction_model: str = "openrouter/anthropic/claude-sonnet-5"
    extraction_prompt_version: str = "v1"
    extraction_timeout_seconds: float = 300.0

    source_max_bytes: int = 2 * 1024 * 1024  # 2 MB, siehe PROJ-1 Edge Cases

    env: str = "development"


settings = Settings()  # type: ignore[call-arg]

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Validators below intentionally accept both dotenv-friendly strings and
    # JSON values; automatic decoding would reject values such as `*` first.
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="", extra="ignore", enable_decoding=False
    )

    app_env: str = "development"
    database_url: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8820
    public_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    operator_token: str = ""

    ai_base_url: str = "https://api.penguinsaichat.dpdns.org/v1"
    ai_api_key: str = ""
    ai_primary_model: str = "gpt-5.6-luna"
    ai_alternate_model: str = "gpt-5.5"
    ai_model_prices_json: dict[str, dict[str, float]] = Field(default_factory=dict)
    ai_max_output_tokens: int = 1800
    ai_timeout_seconds: int = 180
    ai_retry_attempts: int = 2

    # Four hours between chapters gives the 18-chapter MVP roughly three days
    # of public playback after the first chapter starts.
    playback_interval_seconds: float = 14_400.0
    chapter_target_words: int = 900

    @field_validator("public_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [item.strip() for item in str(value or "").split(",") if item.strip()]

    @field_validator("ai_model_prices_json", mode="before")
    @classmethod
    def parse_prices(cls, value: Any) -> dict[str, dict[str, float]]:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        parsed = json.loads(str(value))
        if not isinstance(parsed, dict):
            raise ValueError("AI_MODEL_PRICES_JSON must be an object")
        return parsed


@lru_cache
def get_settings() -> Settings:
    return Settings()

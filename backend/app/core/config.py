from functools import lru_cache
from typing import Annotated, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./persomy.sqlite"
    log_level: str = "INFO"

    trusted_origins: Annotated[List[str], NoDecode] = ["http://localhost:3000"]
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    session_cookie_name: str = "persomy_session"
    csrf_cookie_name: str = "persomy_csrf"

    session_absolute_hours: int = 12
    session_idle_minutes: int = 120

    login_max_failures_per_account: int = 5
    login_max_failures_per_ip: int = 20
    login_window_minutes: int = 15

    password_min_length: int = 12

    # Clé Fernet (base64 urlsafe, 32 octets) qui chiffre les secrets TOTP. Vide = 2FA indisponible.
    two_factor_key: str = ""

    # Aucun fournisseur IA par défaut : tant qu'il est vide, aucun appel IA n'est possible.
    ai_provider: str = ""
    ai_timeout_seconds: int = 60
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:3b-instruct"

    @field_validator("trusted_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @field_validator("cookie_samesite")
    @classmethod
    def _check_samesite(cls, value: str) -> str:
        value = value.lower()
        if value not in {"lax", "strict", "none"}:
            raise ValueError("cookie_samesite must be lax, strict or none")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

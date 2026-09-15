from typing import List, Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ── Database ──────────────────────────────────────────────────────────────
    # DB_TARGET controls which compose profile is active (informational only —
    # the actual connection target is determined by DATABASE_URL content).
    # Values: "supabase" | "local"
    DB_TARGET: str = "local"

    # Session-mode pooler URL (default). See backend/supabase/README.md for
    # where to get these values from the Supabase dashboard Connect dialog.
    # Do NOT add ?sslmode=... — TLS is configured via SUPABASE_SSL_REQUIRED.
    DATABASE_URL: str = "postgresql+asyncpg://lenny:lenny@localhost:5432/lenny_growth"
    ALEMBIC_DATABASE_URL: str = "postgresql://lenny:lenny@localhost:5432/lenny_growth"

    # ── Supabase connection settings ──────────────────────────────────────────
    # SUPABASE_POOL_MODE: "session" (default, IPv4, supports prepared stmts)
    #                     "transaction" (disables prepared stmts automatically)
    #                     "direct" (IPv6 only unless IPv4 add-on is enabled)
    SUPABASE_POOL_MODE: str = "session"

    # SUPABASE_SSL_REQUIRED: true for Supabase (TLS enforced), false for local.
    SUPABASE_SSL_REQUIRED: bool = False

    # SUPABASE_CA_CERT_PATH: optional path to the project root certificate
    # downloaded from Project Settings > Database > SSL Certificate.
    # Leave empty to verify against system CAs.
    SUPABASE_CA_CERT_PATH: Optional[str] = None

    # ── LLM Provider ─────────────────────────────────────────────────────────
    LLM_PROVIDER: Literal["groq", "ollama"] = "ollama"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # ── Embedding provider (Phase 3) ──────────────────────────────────────────
    # EMBEDDING_PROVIDER: "ollama" (default) | "nomic"
    # When EMBEDDING_FALLBACK_ENABLED=true, the cloud provider is tried if
    # Ollama fails and NOMIC_API_KEY is set. If both fail, embed_query()
    # returns None and the existing grounded-refusal path fires unchanged.
    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_FALLBACK_ENABLED: bool = False
    NOMIC_API_KEY: str = ""  # placeholder — do not commit a real key

    # EMBEDDING_DIM is a hard contract. Changing a provider to a different dim
    # requires a full corpus re-ingest. Never truncate or pad silently.
    EMBEDDING_DIM: int = 768

    # ── Agent Sidecar (Internal HTTP) ─────────────────────────────────────────
    AGENT_SIDECAR_URL: str = "http://localhost:4000"

    # ── App & Logging ─────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:5173"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 20

    # ── Feature Flags ─────────────────────────────────────────────────────────
    ENABLE_SHIP30_SKILL: bool = True
    ENABLE_HTML_ARTIFACTS: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("GROQ_API_KEY")
    def validate_groq_key(cls, v: str, info) -> str:
        # Fails fast on startup if groq is selected but key is missing
        return v


settings = Settings()

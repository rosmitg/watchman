from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    SECRET_KEY: str = "changeme"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Shared secret for trusted service-to-service calls (e.g. STK's backend
    # triggering brief generation). When set and presented in the
    # X-Internal-Secret header, the caller may pass the user_id directly instead
    # of a Supabase JWT. Empty disables the internal path.
    INTERNAL_SERVICE_SECRET: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://watchman:watchman@localhost:5432/watchman"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = ""

    # Alpaca
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"

    # News
    NEWS_API_KEY: str = ""

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "watchman-dev"

    # Voyage AI
    VOYAGE_API_KEY: str = ""

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "watchman"

    # HuggingFace
    HUGGINGFACE_API_KEY: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    @property
    def is_cloud_sql(self) -> bool:
        """True when DATABASE_URL targets a Cloud SQL Unix socket (production).

        Cloud Run mounts the instance socket at /cloudsql/<INSTANCE_CONNECTION_NAME>,
        so the production DATABASE_URL contains that path rather than a host:port.
        """
        return "/cloudsql/" in self.DATABASE_URL


settings = Settings()

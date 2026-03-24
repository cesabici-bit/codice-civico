"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_prefix="CC_", env_file=".env")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/codicecivico"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Ingestion
    camera_sparql_endpoint: str = "https://dati.camera.it/sparql"
    senato_sparql_endpoint: str = "https://dati.senato.it/sparql"
    openpolis_api_url: str = "http://api3.openpolis.it"
    anac_data_url: str = "https://dati.anticorruzione.it/opendata"
    giustizia_stats_url: str = "https://datiestatistiche.giustizia.it"

    # NLP / Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"  # or LLaMAntino when available

    # Scheduler
    scheduler_enabled: bool = False

    # Logging
    log_level: str = "INFO"


settings = Settings()

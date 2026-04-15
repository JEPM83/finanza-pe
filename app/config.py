from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "sqlite:///./data/finanza.db"

    # Anthropic
    anthropic_api_key: str = ""

    # Green API (WhatsApp)
    green_api_instance: str = ""
    green_api_token: str = ""
    whatsapp_number: str = ""

    # Google Cloud
    gcs_bucket_name: str = "perifericos"
    gcs_project_id: str = "accuracy-393817"

    # Gmail OAuth2
    gmail_client_id: str = ""
    gmail_client_secret: str = ""

    # Seguridad
    secret_key: str = "dev-secret-key"

    # Configuración general
    app_env: str = "development"
    log_level: str = "INFO"
    gmail_poll_interval_minutes: int = 5
    backup_hour: int = 2
    tipo_cambio_hour: int = 9

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()

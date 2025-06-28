from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    database_url: str
    sync_database_url: str
    clerk_domain: str
    clerk_webhook_secret: str
    clerk_secret_key: str
    # redis_url: str = "redis://localhost:6379/0"
    # celery_broker_url: str = "redis://localhost:6379/0"
    # celery_result_backend: str = "redis://localhost:6379/0"

    # AI Configuration
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # Vertex AI Configuration
    # google_cloud_project: str | None = None
    # google_cloud_location: str = "us-central1"
    # google_application_credentials: str | None = None
    # google_genai_model: str | None = None

    # Azure Storage Configuration
    azure_storage_connection_string: str | None = None
    azure_storage_container_name: str = "profile-images"

    debug: bool = True

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'),
        env_file_encoding="utf-8"
    )

settings = Settings()
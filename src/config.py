from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    sync_database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    # redis_url: str = "redis://localhost:6379/0"
    # celery_broker_url: str = "redis://localhost:6379/0"
    # celery_result_backend: str = "redis://localhost:6379/0"
    openai_api_key: str
    google_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )

settings = Settings()
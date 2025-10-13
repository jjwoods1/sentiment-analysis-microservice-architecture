from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "audio-transcripts"
    MINIO_SECURE: bool = False

    # API Security
    API_KEY: str

    # External Services
    AUTH_URL: str
    AUTH_USERNAME: str
    AUTH_PASSWORD: str
    SPLIT_URL: str
    TRANSCRIPTION_URL: str
    SENTIMENT_URL: str
    ANALYSIS_URL: str
    STORAGE_URL: str = "http://storage-api:8002"
    NOTIFICATION_URL: str = "http://notification-api:8003"

    # Frontend
    FRONTEND_URL: Optional[str] = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

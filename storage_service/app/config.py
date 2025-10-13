from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MinIO Configuration
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "audio-transcripts"
    MINIO_SECURE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    competitors_file: str = "competitors.txt"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

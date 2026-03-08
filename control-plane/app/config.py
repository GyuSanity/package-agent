from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/deploydb"
    sync_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/deploydb"

    class Config:
        env_file = ".env"


settings = Settings()

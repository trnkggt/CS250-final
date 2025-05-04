from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, computed_field


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        extra = "allow"

    AWS_REGION: str

    SECRET: str

    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str

    CELERY_BROKER_URL: str
    CELERY_BACKEND_URL: str

    FRONT_URL: str

    @computed_field
    @property
    def database_url(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            host=self.DB_HOST,
            port=self.DB_PORT,
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            path=f"{self.DB_NAME}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            host=self.DB_HOST,
            port=self.DB_PORT,
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            path=f"{self.DB_NAME}"
        )


settings = Settings()
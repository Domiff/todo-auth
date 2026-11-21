from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings as _BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).parent.parent.parent


class BaseSettings(_BaseSettings):
    IS_DEBUG: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AppSettings(BaseSettings):
    APP_NAME: str = "Todo auth"
    APP_TITLE: str = "Todo auth API"
    APP_VERSION: str = "1"


class DBSettings(BaseSettings):
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DB_ECHO: bool = False

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class CORSSettings(BaseSettings):
    CORS_ORIGINS: list[str]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]


class AdminSettings(BaseSettings):
    ADMIN_SECRET_KEY: str
    ADMIN_BASE_URL: str = "/admin"


class AuthSettings(BaseSettings):
    JWT_PRIVATE_KEY: Path = BASE_DIR / "keys" / "jwt-private.pem"
    JWT_PUBLIC_KEY: Path = BASE_DIR / "keys" / "jwt-public.pem"
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRES: int = 900
    JWT_REFRESH_TOKEN_EXPIRES: int = 2_592_000


class RedisSettings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_USER: str
    REDIS_PASSWORD: str
    CONNECTION_POOL_MAXSIZE: int = 10
    EXPIRE: int = 60 * 60

    @property
    def url(self) -> str:
        return (
            f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}"
            f"@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )


class RabbitMQSettings(BaseSettings):
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672

    @property
    def url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"
        )


class UvicornSettings(BaseSettings):
    UVICORN_HOST: str = "0.0.0.0"
    UVICORN_PORT: int = 8010
    UVICORN_PROXY_HEADERS: bool = True
    UVICORN_FORWARDED_ALLOW_IPS: str = "*"
    UVICORN_ROOT_PATH: str = ""


class Settings:
    app: AppSettings = AppSettings()
    cors: CORSSettings = CORSSettings()
    db: DBSettings = DBSettings()
    admin: AdminSettings = AdminSettings()
    auth: AuthSettings = AuthSettings()
    redis: RedisSettings = RedisSettings()
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    uvicorn: UvicornSettings = UvicornSettings()


settings = Settings()

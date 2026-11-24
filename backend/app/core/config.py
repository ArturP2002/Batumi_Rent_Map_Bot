import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = Path(os.environ.get("ENV_FILE", str(_ROOT / ".env")))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = "replace_me"
    webapp_url: str = "http://localhost:5173"
    admin_telegram_ids: str = ""

    init_data_max_age_seconds: int = 86400
    session_secret: str = "dev-session-secret-change-me"
    session_ttl_seconds: int = 86400

    database_url: str = "postgresql+asyncpg://batumi:batumi@localhost:5435/batumi_rent"
    redis_url: str = "redis://localhost:6380/0"

    s3_endpoint: str = "http://localhost:9010"
    s3_public_url: str = "http://localhost:9010"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "batumi-photos"
    s3_region: str = "us-east-1"

    default_city_lat: float = 41.6168
    default_city_lon: float = 41.6367
    timezone: str = "Asia/Tbilisi"

    geocoder_url: str = "https://nominatim.openstreetmap.org/search"
    geocoder_user_agent: str = "BatumiRentMap/1.0"

    max_photos_per_property: int = 10
    max_photo_bytes: int = 5 * 1024 * 1024

    cors_origins: str = "*"
    debug: bool = True
    api_internal_url: str = "http://localhost:8001"

    @property
    def admin_ids(self) -> set[int]:
        if not self.admin_telegram_ids.strip():
            return set()
        return {int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

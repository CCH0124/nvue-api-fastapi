from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """應用程式配置，封裝所有環境變數與全域設定"""
    base_url: str = Field(default="https://127.0.0.1:443/nvue_v1", alias="NVUE_BASE_URL")
    username: str = Field(default="admin", alias="NVUE_USERNAME")
    password: str = Field(default="password", alias="NVUE_PASSWORD")

    retries: int = Field(default=10, alias="NVUE_RETRIES")
    poll_interval: int = Field(default=1, alias="NVUE_POLL_INTERVAL")
    dummy_sleep: int = Field(default=5, alias="NVUE_DUMMY_SLEEP")

    # Pydantic 配置：支援 .env 檔案並忽略大小寫
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
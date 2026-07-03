import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    ALLOWED_TELEGRAM_USER_ID: int
    API_SECRET_KEY: str
    TARGET_PHONE_NUMBER: str = "199"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        extra="ignore"
    )

settings = Settings()

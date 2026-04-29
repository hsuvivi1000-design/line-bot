from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LINE Messaging API
    line_channel_secret: str
    line_channel_access_token: str

    # Google Gemini
    gemini_api_key: str

    # 服務設定
    port: int = 8000
    log_level: str = "INFO"
    session_max_history: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

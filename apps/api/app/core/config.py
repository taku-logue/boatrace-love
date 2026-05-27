from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # mypyの呼び出しエラーを回避するためデフォルト値を設定（実行時は.envで上書きされます）
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file="../../.env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

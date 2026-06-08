from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_model_root() -> Path:
    if Path("/data").exists():
        return Path("/data") / "processed" / "models"

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "apps").exists() and (parent / "data").exists():
            return parent / "data" / "processed" / "models"
    return current.parents[2] / "data" / "processed" / "models"


class Settings(BaseSettings):
    # mypyの呼び出しエラーを回避するためデフォルト値を設定（実行時は.envで上書きされます）
    DATABASE_URL: str = ""
    MODEL_ROOT: Path = _default_model_root()
    DEFAULT_MODEL_NAME: str = "lgbm_win_v1"
    DEFAULT_MODEL_VIEW: str = "pre_race_no_odds"
    PREDICTION_CACHE_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file="../../.env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

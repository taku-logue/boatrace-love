from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    race_id: str | None = None
    details: dict[str, Any] | None = None


class ModelMetadataResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    model_version: str
    model_view: str
    target: str | None = None
    feature_columns: list[str]
    categorical_columns: list[str]
    created_at: str | None = None
    dataset_sha256: str | None = None
    schema_sha256: str | None = None
    bundle_path: str


class PredictionEntryResponse(BaseModel):
    rank: int
    boat_no: int
    racer_registration_no: str | None = None
    racer_name: str | None = None
    racer_class: str | None = None
    raw_win_probability: float
    win_probability: float
    is_missing_period_stats: bool
    is_missing_pre_race: bool
    is_missing_weather: bool
    is_missing_odds: bool
    feature_summary: dict[str, Any] | None = None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    race_id: str
    race_date: date | None = None
    venue_code: str | None = None
    race_no: int | None = None
    model_name: str
    model_version: str
    model_view: str
    prediction_status: str
    predicted_at: datetime
    probability_sum: float
    entries: list[PredictionEntryResponse]

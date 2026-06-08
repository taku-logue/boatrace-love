from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.features.build import build_feature_dataset
from app.ml.dataset import (
    AUDIT_COLUMNS,
    IDENTIFIER_COLUMNS,
    RESULT_COLUMNS,
    DatasetValidationError,
    validate_feature_frame,
)
from app.prediction.errors import PredictionAPIError

EXPECTED_BOATS = set(range(1, 7))
METADATA_COLUMNS = (
    "race_id",
    "race_date",
    "boat_no",
    "venue_code",
    "venue_code_x",
    "venue_code_y",
    "race_no",
    "racer_registration_no",
    "racer_name",
    "racer_class",
    "is_missing_period_stats",
    "is_missing_pre_race",
    "is_missing_weather",
    "is_missing_odds",
)


@dataclass(frozen=True)
class PreparedPredictionFeatures:
    features: pd.DataFrame
    metadata: pd.DataFrame


def build_prediction_features(
    session: Session,
    race_id: str,
    model_view: str,
) -> PreparedPredictionFeatures:
    try:
        feature_dataset = build_feature_dataset(
            session,
            model_view=model_view,
            race_id=race_id,
        )
    except ValueError as exc:
        raise PredictionAPIError(
            "unsupported_model_view",
            "Requested model_view is not supported.",
            422,
            race_id=race_id,
            details={"model_view": model_view},
        ) from exc

    if feature_dataset.empty:
        raise PredictionAPIError(
            "race_not_found",
            "Race does not exist or has no entries.",
            404,
            race_id=race_id,
        )
    return prepare_prediction_features(feature_dataset, race_id)


def prepare_prediction_features(df: pd.DataFrame, race_id: str) -> PreparedPredictionFeatures:
    missing = sorted({"race_id", "race_date", "boat_no"} - set(df.columns))
    if missing:
        raise PredictionAPIError(
            "feature_unavailable",
            "Prediction feature dataset is missing required metadata columns.",
            422,
            race_id=race_id,
            details={"missing": missing},
        )

    working = df.loc[df["race_id"] == race_id].copy()
    if working.empty:
        raise PredictionAPIError(
            "race_not_found",
            "Race does not exist or has no entries.",
            404,
            race_id=race_id,
        )
    if working["race_id"].nunique() != 1:
        raise PredictionAPIError(
            "feature_unavailable",
            "Prediction feature dataset must contain exactly one race.",
            422,
            race_id=race_id,
        )

    boat_numbers = pd.to_numeric(working["boat_no"], errors="coerce")
    actual_boats = set(boat_numbers.dropna().astype(int).tolist())
    if len(working) != 6 or actual_boats != EXPECTED_BOATS:
        raise PredictionAPIError(
            "incomplete_entries",
            "Prediction requires exactly 6 entries for one race.",
            422,
            race_id=race_id,
            details={"entry_count": len(working), "boat_numbers": sorted(actual_boats)},
        )

    working["frame_no"] = boat_numbers.astype("int8")
    target_columns = {column for column in working.columns if column.startswith("target_")}
    excluded_columns = IDENTIFIER_COLUMNS | AUDIT_COLUMNS | RESULT_COLUMNS | target_columns
    feature_columns = [column for column in working.columns if column not in excluded_columns]
    if not feature_columns:
        raise PredictionAPIError(
            "feature_unavailable",
            "No prediction feature columns remain after exclusions.",
            422,
            race_id=race_id,
        )

    features = working.loc[:, feature_columns].copy()
    try:
        validate_feature_frame(features)
    except DatasetValidationError as exc:
        raise PredictionAPIError(
            "feature_unavailable",
            "Prediction features contain forbidden columns.",
            422,
            race_id=race_id,
            details={"error": str(exc)},
        ) from exc

    metadata = working.loc[:, [column for column in METADATA_COLUMNS if column in working]].copy()
    return PreparedPredictionFeatures(
        features=features.reset_index(drop=True),
        metadata=metadata.reset_index(drop=True),
    )


def metadata_value(row: pd.Series, *columns: str) -> Any:
    for column in columns:
        if column in row and pd.notna(row[column]):
            return row[column]
    return None

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.ml.evaluate import EvaluationError, normalize_probabilities_by_race
from app.ml.preprocessing import PreprocessingError
from app.ml.train import predict_positive_probability
from app.prediction.errors import PredictionAPIError
from app.prediction.features import (
    PreparedPredictionFeatures,
    build_prediction_features,
    metadata_value,
)
from app.prediction.model_store import ModelStore
from app.prediction.schemas import PredictionEntryResponse, PredictionResponse

FeatureBuilder = Callable[[Session, str, str], PreparedPredictionFeatures]


class PredictionService:
    def __init__(
        self,
        model_store: ModelStore,
        *,
        feature_builder: FeatureBuilder = build_prediction_features,
    ) -> None:
        self.model_store = model_store
        self.feature_builder = feature_builder

    def latest_model_metadata(self, model_name: str) -> Any:
        return self.model_store.load_bundle(model_name, "latest").to_metadata_response()

    def predict_race(
        self,
        session: Session,
        race_id: str,
        *,
        model_name: str,
        model_version: str,
        model_view: str,
        include_features: bool = False,
    ) -> PredictionResponse:
        bundle = self.model_store.load_bundle(model_name, model_version)
        if bundle.model_view != model_view:
            raise PredictionAPIError(
                "unsupported_model_view",
                "Requested model_view does not match the loaded model bundle.",
                422,
                race_id=race_id,
                details={
                    "requested_model_view": model_view,
                    "bundle_model_view": bundle.model_view,
                },
            )

        prepared = self.feature_builder(session, race_id, model_view)
        features = self._align_features(prepared.features, bundle.feature_columns, race_id)
        try:
            transformed = bundle.preprocessor.transform(features)
        except PreprocessingError as exc:
            raise PredictionAPIError(
                "preprocessing_mismatch",
                "Prediction features do not match the model preprocessing contract.",
                422,
                race_id=race_id,
                details={"error": str(exc)},
            ) from exc

        try:
            raw_probabilities = predict_positive_probability(bundle.model, transformed)
            normalized_probabilities = normalize_probabilities_by_race(
                prepared.metadata["race_id"],
                raw_probabilities,
            )
        except (EvaluationError, ValueError) as exc:
            raise PredictionAPIError(
                "prediction_failed",
                "Model prediction failed.",
                500,
                race_id=race_id,
                details={"error": str(exc)},
            ) from exc

        predicted_at = datetime.now(UTC)
        return self._response_from_predictions(
            prepared=prepared,
            raw_probabilities=raw_probabilities,
            normalized_probabilities=normalized_probabilities,
            model_name=bundle.model_name,
            model_version=bundle.model_version,
            model_view=bundle.model_view,
            predicted_at=predicted_at,
            include_features=include_features,
        )

    def _align_features(
        self,
        features: pd.DataFrame,
        expected_columns: list[str],
        race_id: str,
    ) -> pd.DataFrame:
        actual_columns = list(features.columns)
        missing = [column for column in expected_columns if column not in features.columns]
        extra = [column for column in actual_columns if column not in expected_columns]
        if missing or extra:
            raise PredictionAPIError(
                "preprocessing_mismatch",
                "Prediction feature columns differ from the model feature contract.",
                422,
                race_id=race_id,
                details={"missing": missing, "extra": extra},
            )
        return features.loc[:, expected_columns].copy()

    def _response_from_predictions(
        self,
        *,
        prepared: PreparedPredictionFeatures,
        raw_probabilities: np.ndarray[Any, np.dtype[np.float64]],
        normalized_probabilities: np.ndarray[Any, np.dtype[np.float64]],
        model_name: str,
        model_version: str,
        model_view: str,
        predicted_at: datetime,
        include_features: bool,
    ) -> PredictionResponse:
        if len(prepared.metadata) == 0:
            raise PredictionAPIError(
                "feature_unavailable",
                "Prediction metadata is empty.",
                422,
            )

        frame = prepared.metadata.copy()
        frame["raw_win_probability"] = raw_probabilities.astype(float)
        frame["win_probability"] = normalized_probabilities.astype(float)
        frame["boat_no"] = pd.to_numeric(frame["boat_no"], errors="raise").astype(int)
        frame = frame.sort_values(["win_probability", "boat_no"], ascending=[False, True]).copy()
        frame["rank"] = range(1, len(frame) + 1)

        first = prepared.metadata.iloc[0]
        entries = [
            PredictionEntryResponse(
                rank=int(row["rank"]),
                boat_no=int(row["boat_no"]),
                racer_registration_no=_optional_str(metadata_value(row, "racer_registration_no")),
                racer_name=_optional_str(metadata_value(row, "racer_name")),
                racer_class=_optional_str(metadata_value(row, "racer_class")),
                raw_win_probability=float(row["raw_win_probability"]),
                win_probability=float(row["win_probability"]),
                is_missing_period_stats=_bool_value(row, "is_missing_period_stats"),
                is_missing_pre_race=_bool_value(row, "is_missing_pre_race"),
                is_missing_weather=_bool_value(row, "is_missing_weather"),
                is_missing_odds=_bool_value(row, "is_missing_odds"),
                feature_summary=(
                    {
                        "feature_count": len(prepared.features.columns),
                        "missing_flag_count": _missing_flag_count(row),
                    }
                    if include_features
                    else None
                ),
            )
            for _, row in frame.iterrows()
        ]

        return PredictionResponse(
            race_id=str(metadata_value(first, "race_id")),
            race_date=_date_value(metadata_value(first, "race_date")),
            venue_code=_optional_str(
                metadata_value(first, "venue_code", "venue_code_x", "venue_code_y")
            ),
            race_no=_optional_int(metadata_value(first, "race_no")),
            model_name=model_name,
            model_version=model_version,
            model_view=model_view,
            prediction_status="ok",
            predicted_at=predicted_at,
            probability_sum=float(np.sum(normalized_probabilities)),
            entries=entries,
        )


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None or pd.isna(value) else int(value)


def _date_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    return pd.to_datetime(value).date()


def _bool_value(row: pd.Series, column: str) -> bool:
    if column not in row or pd.isna(row[column]):
        return False
    return bool(row[column])


def _missing_flag_count(row: pd.Series) -> int:
    return sum(
        _bool_value(row, column)
        for column in (
            "is_missing_period_stats",
            "is_missing_pre_race",
            "is_missing_weather",
            "is_missing_odds",
        )
    )

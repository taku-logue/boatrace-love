from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.prediction.errors import PredictionAPIError
from app.prediction.features import PreparedPredictionFeatures
from app.prediction.model_store import ModelStore
from app.prediction.service import PredictionService
from tests.prediction.helpers import write_tiny_model_bundle


def test_prediction_service_returns_ranked_probabilities(tmp_path: Path) -> None:
    write_tiny_model_bundle(tmp_path)
    store = ModelStore(tmp_path, default_model_view="pre_race_no_odds")
    service = PredictionService(store, feature_builder=_feature_builder(_prepared_features()))

    response = service.predict_race(
        MagicMock(),
        "20260601_01_01",
        model_name="lgbm_win_v1",
        model_version="latest",
        model_view="pre_race_no_odds",
        include_features=True,
    )

    assert response.race_id == "20260601_01_01"
    assert response.model_version == "20260608T000000Z"
    assert len(response.entries) == 6
    assert abs(response.probability_sum - 1.0) < 1e-12
    assert response.entries[0].rank == 1
    assert response.entries[0].feature_summary == {
        "feature_count": 3,
        "missing_flag_count": 0,
    }


def test_prediction_service_rejects_feature_contract_drift(tmp_path: Path) -> None:
    write_tiny_model_bundle(tmp_path)
    store = ModelStore(tmp_path, default_model_view="pre_race_no_odds")
    prepared = _prepared_features()
    prepared = PreparedPredictionFeatures(
        features=prepared.features.drop(columns=["is_missing_odds"]),
        metadata=prepared.metadata,
    )
    service = PredictionService(store, feature_builder=_feature_builder(prepared))

    with pytest.raises(PredictionAPIError) as exc_info:
        service.predict_race(
            MagicMock(),
            "20260601_01_01",
            model_name="lgbm_win_v1",
            model_version="latest",
            model_view="pre_race_no_odds",
        )

    assert exc_info.value.error_code == "preprocessing_mismatch"
    assert exc_info.value.status_code == 422
    assert exc_info.value.details["missing"] == ["is_missing_odds"]


def _prepared_features() -> PreparedPredictionFeatures:
    race_id = "20260601_01_01"
    boats = list(range(1, 7))
    return PreparedPredictionFeatures(
        features=pd.DataFrame(
            {
                "frame_no": boats,
                "recent_win_rate": [0.75, 0.45, 0.25, 0.2, 0.1, 0.05],
                "is_missing_odds": [False, False, False, False, False, False],
            }
        ),
        metadata=pd.DataFrame(
            {
                "race_id": [race_id] * 6,
                "race_date": [pd.Timestamp("2026-06-01")] * 6,
                "venue_code_x": ["01"] * 6,
                "race_no": [1] * 6,
                "boat_no": boats,
                "racer_registration_no": [f"10{boat_no:02d}" for boat_no in boats],
                "racer_name": [f"選手{boat_no}" for boat_no in boats],
                "racer_class": ["A1", "A2", "B1", "B1", "B2", "B2"],
                "is_missing_period_stats": [False] * 6,
                "is_missing_pre_race": [False] * 6,
                "is_missing_weather": [False] * 6,
                "is_missing_odds": [False] * 6,
            }
        ),
    )


def _feature_builder(prepared: PreparedPredictionFeatures):
    def builder(*_args: object, **_kwargs: object) -> PreparedPredictionFeatures:
        return prepared

    return builder

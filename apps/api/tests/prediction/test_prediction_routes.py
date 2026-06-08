from datetime import UTC, date, datetime
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.prediction.errors import PredictionAPIError
from app.prediction.schemas import (
    ModelMetadataResponse,
    PredictionEntryResponse,
    PredictionResponse,
)
from app.routers.dependencies import get_model_store, get_prediction_service


def test_models_latest_route_returns_metadata() -> None:
    app.dependency_overrides[get_model_store] = lambda: _FakeModelStore()
    try:
        response = TestClient(app).get("/models/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["model_name"] == "lgbm_win_v1"
    assert body["model_version"] == "20260608T000000Z"
    assert body["feature_columns"] == ["frame_no"]


def test_prediction_route_returns_prediction_response() -> None:
    app.dependency_overrides[get_prediction_service] = lambda: _FakePredictionService()
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        response = TestClient(app).get("/races/20260601_01_01/prediction")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["race_id"] == "20260601_01_01"
    assert body["probability_sum"] == 1.0
    assert body["entries"][0]["rank"] == 1


def test_prediction_route_returns_top_level_error_response() -> None:
    app.dependency_overrides[get_prediction_service] = lambda: _ErrorPredictionService()
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        response = TestClient(app).get("/races/missing/prediction")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "race_not_found",
        "message": "Race does not exist.",
        "race_id": "missing",
    }


class _FakeBundle:
    def to_metadata_response(self) -> ModelMetadataResponse:
        return ModelMetadataResponse(
            model_name="lgbm_win_v1",
            model_version="20260608T000000Z",
            model_view="pre_race_no_odds",
            target="target_win",
            feature_columns=["frame_no"],
            categorical_columns=[],
            created_at="2026-06-08T00:00:00+00:00",
            bundle_path="/tmp/models/lgbm_win_v1/20260608T000000Z",
        )


class _FakeModelStore:
    def load_bundle(self, *_args: object, **_kwargs: object) -> _FakeBundle:
        return _FakeBundle()


class _FakePredictionService:
    def predict_race(self, *_args: object, **_kwargs: object) -> PredictionResponse:
        return PredictionResponse(
            race_id="20260601_01_01",
            race_date=date(2026, 6, 1),
            venue_code="01",
            race_no=1,
            model_name="lgbm_win_v1",
            model_version="20260608T000000Z",
            model_view="pre_race_no_odds",
            prediction_status="ok",
            predicted_at=datetime(2026, 6, 8, tzinfo=UTC),
            probability_sum=1.0,
            entries=[
                PredictionEntryResponse(
                    rank=1,
                    boat_no=1,
                    raw_win_probability=0.4,
                    win_probability=1.0,
                    is_missing_period_stats=False,
                    is_missing_pre_race=False,
                    is_missing_weather=False,
                    is_missing_odds=False,
                )
            ],
        )


class _ErrorPredictionService:
    def predict_race(self, *_args: object, **_kwargs: object) -> PredictionResponse:
        raise PredictionAPIError(
            "race_not_found",
            "Race does not exist.",
            404,
            race_id="missing",
        )

from pathlib import Path

import pytest

from app.prediction.errors import PredictionAPIError
from app.prediction.model_store import ModelStore
from tests.prediction.helpers import write_tiny_model_bundle


def test_model_store_loads_latest_complete_bundle(tmp_path: Path) -> None:
    write_tiny_model_bundle(tmp_path, model_version="20260607T000000Z")
    latest_path = write_tiny_model_bundle(tmp_path, model_version="20260608T000000Z")

    store = ModelStore(tmp_path, default_model_view="pre_race_no_odds")
    bundle = store.load_bundle("lgbm_win_v1", "latest")

    assert bundle.model_version == "20260608T000000Z"
    assert bundle.bundle_path == latest_path
    assert bundle.feature_columns == ["frame_no", "recent_win_rate", "is_missing_odds"]
    assert bundle.to_metadata_response().model_view == "pre_race_no_odds"


def test_model_store_rejects_invalid_identifiers(tmp_path: Path) -> None:
    store = ModelStore(tmp_path, default_model_view="pre_race_no_odds")

    with pytest.raises(PredictionAPIError) as exc_info:
        store.load_bundle("../secret", "latest")

    assert exc_info.value.error_code == "model_not_found"
    assert exc_info.value.status_code == 404


def test_model_store_reports_missing_bundle(tmp_path: Path) -> None:
    store = ModelStore(tmp_path, default_model_view="pre_race_no_odds")

    with pytest.raises(PredictionAPIError) as exc_info:
        store.load_bundle("missing_model", "latest")

    assert exc_info.value.error_code == "model_not_found"
    assert exc_info.value.status_code == 404

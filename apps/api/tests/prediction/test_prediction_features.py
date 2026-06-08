import pandas as pd
import pytest

from app.prediction.errors import PredictionAPIError
from app.prediction.features import prepare_prediction_features


def test_prepare_prediction_features_excludes_targets_from_features() -> None:
    prepared = prepare_prediction_features(_feature_dataset(), "20260601_01_01")

    assert list(prepared.features.columns) == [
        "venue_code_x",
        "race_no",
        "recent_win_rate",
        "is_missing_odds",
        "frame_no",
    ]
    assert "target_win" not in prepared.features.columns
    assert len(prepared.metadata) == 6


def test_prepare_prediction_features_rejects_incomplete_entries() -> None:
    df = _feature_dataset().iloc[:5].copy()

    with pytest.raises(PredictionAPIError) as exc_info:
        prepare_prediction_features(df, "20260601_01_01")

    assert exc_info.value.error_code == "incomplete_entries"
    assert exc_info.value.status_code == 422


def _feature_dataset() -> pd.DataFrame:
    boats = list(range(1, 7))
    return pd.DataFrame(
        {
            "race_id": ["20260601_01_01"] * 6,
            "race_date": [pd.Timestamp("2026-06-01")] * 6,
            "venue_code_x": ["01"] * 6,
            "race_no": [1] * 6,
            "boat_no": boats,
            "racer_registration_no": [f"10{boat_no:02d}" for boat_no in boats],
            "racer_name": [f"選手{boat_no}" for boat_no in boats],
            "recent_win_rate": [0.75, 0.45, 0.25, 0.2, 0.1, 0.05],
            "is_missing_odds": [False] * 6,
            "target_win": [1, 0, 0, 0, 0, 0],
        }
    )

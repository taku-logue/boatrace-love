import json
from pathlib import Path

import pandas as pd

from app.ml.preprocessing import FeaturePreprocessor
from app.ml.train import TrainingConfig, save_model, train_lightgbm


def tiny_training_frames() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    train_features = pd.DataFrame(
        {
            "frame_no": list(range(1, 7)) * 4,
            "recent_win_rate": [0.8, 0.4, 0.3, 0.2, 0.1, 0.05] * 4,
            "is_missing_odds": [False, False, False, False, False, False] * 4,
        }
    )
    train_target = pd.Series([1, 0, 0, 0, 0, 0] * 4)
    valid_features = pd.DataFrame(
        {
            "frame_no": list(range(1, 7)) * 2,
            "recent_win_rate": [0.75, 0.45, 0.25, 0.2, 0.1, 0.05] * 2,
            "is_missing_odds": [False, False, False, False, False, False] * 2,
        }
    )
    valid_target = pd.Series([1, 0, 0, 0, 0, 0] * 2)
    return train_features, train_target, valid_features, valid_target


def write_tiny_model_bundle(
    root: Path,
    *,
    model_name: str = "lgbm_win_v1",
    model_version: str = "20260608T000000Z",
    model_view: str = "pre_race_no_odds",
) -> Path:
    train_features, train_target, valid_features, valid_target = tiny_training_frames()
    preprocessor = FeaturePreprocessor.fit(train_features)
    model = train_lightgbm(
        preprocessor.transform(train_features),
        train_target,
        preprocessor.transform(valid_features),
        valid_target,
        TrainingConfig(n_estimators=20, min_child_samples=2),
    )

    bundle_path = root / model_name / model_version
    bundle_path.mkdir(parents=True)
    save_model(model, bundle_path / "model.joblib")
    preprocessor.save(bundle_path / "preprocessing_config.json")
    _write_json(bundle_path / "feature_columns.json", preprocessor.feature_columns)
    _write_json(bundle_path / "categorical_columns.json", preprocessor.categorical_columns)
    _write_json(
        bundle_path / "model_metadata.json",
        {
            "model_name": model_name,
            "model_version": model_version,
            "model_view": model_view,
            "target": "target_win",
            "feature_columns": preprocessor.feature_columns,
            "created_at": "2026-06-08T00:00:00+00:00",
        },
    )
    return bundle_path


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

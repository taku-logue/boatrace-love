from pathlib import Path

import pandas as pd

from app.ml.train import (
    TrainingConfig,
    feature_importance_frame,
    load_model,
    predict_positive_probability,
    save_model,
    train_lightgbm,
)


def test_lightgbm_baseline_trains_and_saves(tmp_path: Path) -> None:
    train_features = pd.DataFrame(
        {
            "frame_no": list(range(1, 7)) * 4,
            "recent_win_rate": [0.8, 0.4, 0.3, 0.2, 0.1, 0.05] * 4,
        }
    )
    train_target = pd.Series([1, 0, 0, 0, 0, 0] * 4)
    valid_features = pd.DataFrame(
        {
            "frame_no": list(range(1, 7)) * 2,
            "recent_win_rate": [0.75, 0.45, 0.25, 0.2, 0.1, 0.05] * 2,
        }
    )
    valid_target = pd.Series([1, 0, 0, 0, 0, 0] * 2)

    model = train_lightgbm(
        train_features,
        train_target,
        valid_features,
        valid_target,
        TrainingConfig(n_estimators=20, min_child_samples=2),
    )
    probabilities = predict_positive_probability(model, valid_features)
    model_path = save_model(model, tmp_path / "model.joblib")
    loaded_model = load_model(model_path)

    assert len(probabilities) == len(valid_features)
    assert model_path.exists()
    assert (
        predict_positive_probability(loaded_model, valid_features).tolist()
        == probabilities.tolist()
    )
    assert feature_importance_frame(model)["feature"].tolist() == [
        "recent_win_rate",
        "frame_no",
    ]

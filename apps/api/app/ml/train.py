from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
from lightgbm import LGBMClassifier, early_stopping
import numpy as np
from numpy.typing import NDArray
import pandas as pd


@dataclass(frozen=True)
class TrainingConfig:
    objective: str = "binary"
    n_estimators: int = 300
    learning_rate: float = 0.05
    num_leaves: int = 31
    max_depth: int = -1
    min_child_samples: int = 10
    subsample: float = 0.9
    subsample_freq: int = 1
    colsample_bytree: float = 0.9
    reg_alpha: float = 0.0
    reg_lambda: float = 0.0
    random_state: int = 42
    n_jobs: int = -1
    verbosity: int = -1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def train_lightgbm(
    train_features: pd.DataFrame,
    train_target: pd.Series,
    valid_features: pd.DataFrame,
    valid_target: pd.Series,
    config: TrainingConfig,
) -> LGBMClassifier:
    if train_features.empty or valid_features.empty:
        raise ValueError("Training and validation features must not be empty")
    if train_target.nunique() < 2:
        raise ValueError("Training target must contain both positive and negative examples")
    if list(train_features.columns) != list(valid_features.columns):
        raise ValueError("Training and validation feature columns must match")

    model = LGBMClassifier(**config.to_dict())
    model.fit(
        train_features,
        train_target,
        eval_set=[(valid_features, valid_target)],
        eval_names=["valid"],
        eval_metric="binary_logloss",
        categorical_feature="auto",
        callbacks=[early_stopping(stopping_rounds=30, first_metric_only=True, verbose=False)],
    )
    return model


def predict_positive_probability(
    model: LGBMClassifier,
    features: pd.DataFrame,
) -> NDArray[np.float64]:
    probabilities = np.asarray(model.predict_proba(features), dtype=np.float64)
    if probabilities.ndim != 2 or probabilities.shape[1] != 2:
        raise ValueError(f"Expected binary class probabilities, got shape={probabilities.shape}")
    return probabilities[:, 1]


def feature_importance_frame(model: LGBMClassifier) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature": model.feature_name_,
            "importance": model.feature_importances_,
        }
    ).sort_values(["importance", "feature"], ascending=[False, True], ignore_index=True)


def save_model(model: LGBMClassifier, path: str | Path) -> Path:
    model_path = Path(path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    return model_path


def load_model(path: str | Path) -> LGBMClassifier:
    model_path = Path(path)
    try:
        model = joblib.load(model_path)
    except FileNotFoundError as exc:
        raise ValueError(f"Model file does not exist: {model_path}") from exc
    if not isinstance(model, LGBMClassifier):
        raise ValueError(f"Model artifact is not an LGBMClassifier: {model_path}")
    return model

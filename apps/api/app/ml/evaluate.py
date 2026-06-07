from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss  # type: ignore[import-untyped]


class EvaluationError(ValueError):
    """Raised when race-level predictions cannot be evaluated."""


@dataclass(frozen=True)
class EvaluationMetrics:
    log_loss: float
    brier_score: float
    race_hit_rate: float
    mean_predicted_winner_probability: float
    probability_sum_error_mean: float
    probability_sum_error_max: float
    row_count: int
    race_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_probabilities_by_race(
    race_ids: pd.Series,
    raw_probabilities: NDArray[np.float64],
) -> NDArray[np.float64]:
    probabilities = np.asarray(raw_probabilities, dtype=np.float64)
    if len(race_ids) != len(probabilities):
        raise EvaluationError("race_ids and raw_probabilities must have equal length")
    if len(probabilities) == 0:
        raise EvaluationError("Cannot normalize an empty prediction array")
    if not np.isfinite(probabilities).all():
        raise EvaluationError("Raw probabilities contain non-finite values")
    if (probabilities < 0).any():
        raise EvaluationError("Raw probabilities must be non-negative")

    frame = pd.DataFrame(
        {
            "race_id": race_ids.reset_index(drop=True),
            "raw_probability": probabilities,
        }
    )
    race_sums = frame.groupby("race_id")["raw_probability"].transform("sum")
    race_sizes = frame.groupby("race_id")["raw_probability"].transform("size")
    sum_values = race_sums.to_numpy(dtype=np.float64)
    normalized = np.divide(
        probabilities,
        sum_values,
        out=1.0 / race_sizes.to_numpy(dtype=np.float64),
        where=sum_values > 0,
    )
    return np.asarray(normalized, dtype=np.float64)


def evaluate_predictions(
    race_ids: pd.Series,
    targets: pd.Series,
    probabilities: NDArray[np.float64],
) -> EvaluationMetrics:
    y_true = np.asarray(targets, dtype=np.int8)
    y_probability = np.asarray(probabilities, dtype=np.float64)
    if len(race_ids) != len(y_true) or len(y_true) != len(y_probability):
        raise EvaluationError("race_ids, targets, and probabilities must have equal length")
    if len(y_true) == 0:
        raise EvaluationError("Cannot evaluate empty predictions")
    if not np.isin(y_true, [0, 1]).all():
        raise EvaluationError("Targets must contain only 0/1")
    if not np.isfinite(y_probability).all():
        raise EvaluationError("Probabilities contain non-finite values")

    clipped = np.clip(y_probability, 1e-15, 1 - 1e-15)
    frame = pd.DataFrame(
        {
            "race_id": race_ids.reset_index(drop=True),
            "target": y_true,
            "probability": y_probability,
        }
    )
    race_target_sums = frame.groupby("race_id")["target"].sum()
    invalid_target_races = race_target_sums[race_target_sums != 1]
    if not invalid_target_races.empty:
        raise EvaluationError(
            "Every evaluated race must have exactly one winner; "
            f"invalid={invalid_target_races.to_dict()}"
        )

    selected_indexes = frame.groupby("race_id")["probability"].idxmax()
    race_hit_rate = float(frame.loc[selected_indexes, "target"].mean())
    winner_probabilities = frame.loc[frame["target"] == 1, "probability"]
    probability_sums = frame.groupby("race_id")["probability"].sum()
    probability_sum_errors = (probability_sums - 1.0).abs()

    return EvaluationMetrics(
        log_loss=float(log_loss(y_true, clipped, labels=[0, 1])),
        brier_score=float(brier_score_loss(y_true, clipped)),
        race_hit_rate=race_hit_rate,
        mean_predicted_winner_probability=float(winner_probabilities.mean()),
        probability_sum_error_mean=float(probability_sum_errors.mean()),
        probability_sum_error_max=float(probability_sum_errors.max()),
        row_count=len(frame),
        race_count=int(frame["race_id"].nunique()),
    )


def prediction_frame(
    metadata: pd.DataFrame,
    targets: pd.Series,
    raw_probabilities: NDArray[np.float64],
    normalized_probabilities: NDArray[np.float64],
    model_name: str,
    model_version: str,
    predicted_at: str,
) -> pd.DataFrame:
    if not (
        len(metadata) == len(targets) == len(raw_probabilities) == len(normalized_probabilities)
    ):
        raise EvaluationError("Prediction frame inputs must have equal length")
    result = metadata.reset_index(drop=True).copy()
    result["target_win"] = np.asarray(targets, dtype=np.int8)
    result["raw_win_probability"] = np.asarray(raw_probabilities, dtype=np.float64)
    result["win_probability"] = np.asarray(normalized_probabilities, dtype=np.float64)
    result["model_name"] = model_name
    result["model_version"] = model_version
    result["predicted_at"] = predicted_at
    return result

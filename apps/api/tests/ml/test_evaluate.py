import numpy as np
import pandas as pd

from app.ml.evaluate import evaluate_predictions, normalize_probabilities_by_race


def test_normalization_and_race_metrics() -> None:
    race_ids = pd.Series(["r1"] * 3 + ["r2"] * 3)
    targets = pd.Series([1, 0, 0, 0, 1, 0])
    raw = np.array([0.7, 0.2, 0.1, 0.1, 0.8, 0.1], dtype=np.float64)

    normalized = normalize_probabilities_by_race(race_ids, raw)
    metrics = evaluate_predictions(race_ids, targets, normalized)

    sums = (
        pd.DataFrame({"race_id": race_ids, "probability": normalized})
        .groupby("race_id")["probability"]
        .sum()
    )
    assert np.allclose(sums.to_numpy(), 1.0)
    assert metrics.race_hit_rate == 1.0
    assert metrics.probability_sum_error_max < 1e-12
    assert metrics.mean_predicted_winner_probability == 0.75


def test_zero_probabilities_are_normalized_uniformly() -> None:
    normalized = normalize_probabilities_by_race(
        pd.Series(["r1", "r1"]),
        np.array([0.0, 0.0], dtype=np.float64),
    )

    assert normalized.tolist() == [0.5, 0.5]

import pandas as pd
import pytest
from pathlib import Path

from app.ml.preprocessing import (
    MISSING_CATEGORY,
    UNKNOWN_CATEGORY,
    FeaturePreprocessor,
    PreprocessingError,
)


def test_preprocessor_reuses_training_category_mapping() -> None:
    train = pd.DataFrame(
        {
            "motor_no": [1, 2, 3],
            "is_missing_odds": [False, True, False],
            "racer_class": ["A1", "A2", None],
        }
    )
    future = pd.DataFrame(
        {
            "motor_no": [4, None],
            "is_missing_odds": [True, False],
            "racer_class": ["B1", None],
        }
    )

    preprocessor = FeaturePreprocessor.fit(train)
    transformed = preprocessor.transform(future)

    assert transformed["is_missing_odds"].dtype == "int8"
    assert transformed["racer_class"].astype(str).tolist() == [
        UNKNOWN_CATEGORY,
        MISSING_CATEGORY,
    ]
    assert preprocessor.category_mappings["racer_class"] == [
        MISSING_CATEGORY,
        UNKNOWN_CATEGORY,
        "A1",
        "A2",
    ]


def test_preprocessor_rejects_feature_drift() -> None:
    preprocessor = FeaturePreprocessor.fit(pd.DataFrame({"value": [1, 2]}))

    with pytest.raises(PreprocessingError, match="Feature columns differ"):
        preprocessor.transform(pd.DataFrame({"other": [1]}))


def test_preprocessor_roundtrip(tmp_path: Path) -> None:
    train = pd.DataFrame({"value": [1, 2], "racer_class": ["A1", "A2"]})
    preprocessor = FeaturePreprocessor.fit(train)
    config_path = preprocessor.save(tmp_path / "preprocessing_config.json")

    loaded = FeaturePreprocessor.load(config_path)

    assert loaded.to_dict() == preprocessor.to_dict()

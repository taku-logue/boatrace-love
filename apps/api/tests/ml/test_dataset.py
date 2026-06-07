import json
from pathlib import Path

import pandas as pd
import pytest

from app.features.export import dataframe_schema
from app.ml.dataset import (
    DatasetValidationError,
    load_training_dataset,
    prepare_dataset,
    validate_feature_frame,
)


def _write_dataset(tmp_path: Path, df: pd.DataFrame) -> tuple[Path, Path]:
    dataset_path = tmp_path / "dataset.parquet"
    schema_path = tmp_path / "dataset.schema.json"
    df.to_parquet(dataset_path, index=False)
    loaded = pd.read_parquet(dataset_path)
    schema_path.write_text(json.dumps(dataframe_schema(loaded)), encoding="utf-8")
    return dataset_path, schema_path


def test_load_and_prepare_training_dataset(tmp_path: Path) -> None:
    race_ids = ["202605300101"] * 6 + ["202605300102"] * 6
    df = pd.DataFrame(
        {
            "race_id": race_ids,
            "race_date": pd.to_datetime(["2026-05-30"] * 12),
            "boat_no": list(range(1, 7)) * 2,
            "venue_code": ["01"] * 12,
            "racer_registration_no": [str(1001 + index) for index in range(12)],
            "racer_name": [f"Racer {index}" for index in range(12)],
            "motor_no": list(range(11, 23)),
            "target_win": [1, 0, 0, 0, 0, 0] * 2,
            "target_top2": [1, 1, 0, 0, 0, 0] * 2,
            "exclude_reason": [None] * 6 + [None, None, None, None, None, "missing_result"],
        }
    )
    dataset_path, schema_path = _write_dataset(tmp_path, df)

    loaded = load_training_dataset(dataset_path, schema_path)
    prepared = prepare_dataset(loaded)

    assert len(loaded) == 6
    assert prepared.target.tolist() == [1, 0, 0, 0, 0, 0]
    assert prepared.metadata["boat_no"].tolist() == [1, 2, 3, 4, 5, 6]
    assert "frame_no" in prepared.features
    assert "boat_no" not in prepared.features
    assert "target_win" not in prepared.features
    assert "racer_registration_no" not in prepared.features


def test_load_training_dataset_detects_schema_mismatch(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "race_id": ["r1"],
            "race_date": pd.to_datetime(["2026-05-30"]),
            "boat_no": [1],
            "target_win": [1],
        }
    )
    dataset_path, schema_path = _write_dataset(tmp_path, df)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["row_count"] = 99
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    with pytest.raises(DatasetValidationError, match="Row count mismatch"):
        load_training_dataset(dataset_path, schema_path)


def test_validate_feature_frame_rejects_result_columns() -> None:
    features = pd.DataFrame({"motor_no": [1], "finish_position": [1]})

    with pytest.raises(DatasetValidationError, match="Leakage detected"):
        validate_feature_frame(features)

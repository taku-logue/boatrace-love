import json

import pandas as pd

from app.features.export import (
    dataset_metadata_path,
    export_dataset_to_parquet,
    verify_parquet_roundtrip,
)


def test_export_dataset_to_parquet_writes_schema_metadata(tmp_path):
    df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01"],
            "boat_no": [1],
            "target_win": [1],
        }
    )

    out_path = export_dataset_to_parquet(df, tmp_path, "boat_features_v1", "pre_race_no_odds")
    metadata_path = dataset_metadata_path(out_path)

    assert out_path.exists()
    assert metadata_path.exists()
    schema = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert schema["row_count"] == 1
    assert schema["column_count"] == 3
    assert list(schema["columns"]) == ["race_id", "boat_no", "target_win"]
    assert verify_parquet_roundtrip(out_path, df)["row_count"] == 1

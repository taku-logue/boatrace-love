import json
from pathlib import Path

import pandas as pd


def dataset_metadata_path(dataset_path: Path) -> Path:
    return dataset_path.with_suffix(".schema.json")


def dataframe_schema(df: pd.DataFrame) -> dict[str, object]:
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": {column: str(dtype) for column, dtype in df.dtypes.items()},
    }


def verify_parquet_roundtrip(path: Path, expected_df: pd.DataFrame) -> dict[str, object]:
    loaded = pd.read_parquet(str(path))
    if len(loaded) != len(expected_df):
        raise ValueError(
            f"Parquet row count mismatch: expected={len(expected_df)} actual={len(loaded)}"
        )
    if list(loaded.columns) != list(expected_df.columns):
        raise ValueError("Parquet columns do not match the source DataFrame")
    return dataframe_schema(loaded)


def export_dataset_to_parquet(
    df: pd.DataFrame, base_dir: str | Path, version: str, model_view: str
) -> Path:
    """
    データセットを指定されたディレクトリにParquet形式で保存する。
    """
    out_dir = Path(base_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ファイル名の生成（例: dataset_boat_features_v1_pre_race_no_odds.parquet）
    filename = f"dataset_{version}_{model_view}.parquet"
    out_path = out_dir / filename

    df.to_parquet(out_path, index=False, engine="pyarrow")
    schema = verify_parquet_roundtrip(out_path, df)
    metadata_path = dataset_metadata_path(out_path)
    metadata_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return out_path

from pathlib import Path

import pandas as pd


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

    # Parquet形式で保存（pyarrow エンジンを使用）
    df.to_parquet(out_path, index=False, engine="pyarrow")

    return out_path

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.features.leakage import DataLeakageError, validate_no_leakage

IDENTIFIER_COLUMNS = {
    "race_id",
    "race_date",
    "boat_no",
    "racer_registration_no",
    "racer_name",
}
AUDIT_COLUMNS = {
    "exclude_reason",
    "odds_fetched_at",
}
RESULT_COLUMNS = {
    "finish_position",
    "result_status",
    "decision",
    "start_timing",
    "payout_yen",
    "popularity",
}
REQUIRED_COLUMNS = {"race_id", "race_date", "boat_no"}


class DatasetValidationError(ValueError):
    """Raised when a Phase 5 dataset violates the Phase 6 input contract."""


@dataclass(frozen=True)
class PreparedDataset:
    features: pd.DataFrame
    target: pd.Series
    metadata: pd.DataFrame


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        value = json.loads(schema_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetValidationError(f"Schema file does not exist: {schema_path}") from exc
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(f"Schema JSON is invalid: {schema_path}") from exc
    if not isinstance(value, dict):
        raise DatasetValidationError("Schema JSON root must be an object")
    return value


def validate_schema(df: pd.DataFrame, schema: dict[str, Any]) -> None:
    expected_rows = schema.get("row_count")
    expected_columns = schema.get("column_count")
    expected_dtypes = schema.get("columns")

    if expected_rows != len(df):
        raise DatasetValidationError(
            f"Row count mismatch: schema={expected_rows!r}, parquet={len(df)}"
        )
    if expected_columns != len(df.columns):
        raise DatasetValidationError(
            f"Column count mismatch: schema={expected_columns!r}, parquet={len(df.columns)}"
        )
    if not isinstance(expected_dtypes, dict):
        raise DatasetValidationError("Schema 'columns' must be an object")

    expected_names = list(expected_dtypes)
    actual_names = list(df.columns)
    if expected_names != actual_names:
        raise DatasetValidationError(
            f"Column order mismatch: schema={expected_names}, parquet={actual_names}"
        )

    actual_dtypes = {column: str(dtype) for column, dtype in df.dtypes.items()}
    mismatches = {
        column: {"schema": expected_dtypes[column], "parquet": actual_dtypes[column]}
        for column in expected_names
        if expected_dtypes[column] != actual_dtypes[column]
    }
    if mismatches:
        raise DatasetValidationError(f"Column dtype mismatch: {mismatches}")


def load_training_dataset(
    dataset_path: str | Path,
    schema_path: str | Path,
    target_column: str = "target_win",
) -> pd.DataFrame:
    dataset = Path(dataset_path)
    schema_file = Path(schema_path)
    if not dataset.exists():
        raise DatasetValidationError(f"Dataset file does not exist: {dataset}")

    try:
        df = pd.read_parquet(dataset)
    except (OSError, ValueError) as exc:
        raise DatasetValidationError(f"Could not read Parquet dataset: {dataset}") from exc

    validate_schema(df, _load_schema(schema_file))

    missing = sorted((REQUIRED_COLUMNS | {target_column}) - set(df.columns))
    if missing:
        raise DatasetValidationError(f"Required columns are missing: {missing}")
    if df.empty:
        raise DatasetValidationError("Dataset is empty")

    filtered = df.copy()
    if "exclude_reason" in filtered.columns:
        filtered = filtered.loc[filtered["exclude_reason"].isna()].copy()
    if filtered.empty:
        raise DatasetValidationError("No eligible rows remain after exclude_reason filtering")

    filtered["race_date"] = pd.to_datetime(filtered["race_date"], errors="raise").dt.normalize()
    target_values = pd.to_numeric(filtered[target_column], errors="coerce")
    if target_values.isna().any():
        raise DatasetValidationError(f"Target column contains missing values: {target_column}")
    if not target_values.isin([0, 1]).all():
        raise DatasetValidationError(f"Target column must contain only 0/1: {target_column}")
    filtered[target_column] = target_values.astype("int8")

    race_summary = filtered.groupby("race_id").agg(
        row_count=("boat_no", "size"),
        boat_count=("boat_no", "nunique"),
        winner_count=(target_column, "sum"),
    )
    complete_race_ids = race_summary.index[
        (race_summary["row_count"] == 6)
        & (race_summary["boat_count"] == 6)
        & (race_summary["winner_count"] == 1)
    ]
    filtered = filtered.loc[filtered["race_id"].isin(complete_race_ids)].copy()
    valid_boat_sets = filtered.groupby("race_id")["boat_no"].apply(
        lambda values: (
            set(pd.to_numeric(values, errors="coerce").dropna().astype(int)) == set(range(1, 7))
        )
    )
    filtered = filtered.loc[filtered["race_id"].isin(valid_boat_sets[valid_boat_sets].index)].copy()
    if filtered.empty:
        raise DatasetValidationError("No complete six-boat races with exactly one winner remain")
    return filtered.reset_index(drop=True)


def validate_feature_frame(features: pd.DataFrame) -> None:
    try:
        validate_no_leakage(features)
    except DataLeakageError as exc:
        raise DatasetValidationError(str(exc)) from exc

    forbidden = sorted((IDENTIFIER_COLUMNS | RESULT_COLUMNS) & set(features.columns))
    if forbidden:
        raise DatasetValidationError(
            f"Identifier or result columns remain in features: {forbidden}"
        )


def prepare_dataset(
    df: pd.DataFrame,
    target_column: str = "target_win",
) -> PreparedDataset:
    missing = sorted((REQUIRED_COLUMNS | {target_column}) - set(df.columns))
    if missing:
        raise DatasetValidationError(f"Required columns are missing: {missing}")

    working = df.copy()
    working["frame_no"] = pd.to_numeric(working["boat_no"], errors="raise").astype("int8")

    target_columns = {column for column in working.columns if column.startswith("target_")}
    excluded_columns = IDENTIFIER_COLUMNS | AUDIT_COLUMNS | RESULT_COLUMNS | target_columns
    feature_columns = [column for column in working.columns if column not in excluded_columns]
    if not feature_columns:
        raise DatasetValidationError("No feature columns remain after exclusions")

    features = working.loc[:, feature_columns].copy()
    validate_feature_frame(features)

    metadata_columns = [
        column
        for column in ("race_id", "race_date", "boat_no", "venue_code", "race_no")
        if column in working.columns
    ]
    metadata = working.loc[:, metadata_columns].copy()
    target = working[target_column].astype("int8").copy()
    target.name = target_column
    return PreparedDataset(features=features, target=target, metadata=metadata)

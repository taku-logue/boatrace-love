from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype

MISSING_CATEGORY = "__MISSING__"
UNKNOWN_CATEGORY = "__UNKNOWN__"


class PreprocessingError(ValueError):
    """Raised when model features cannot be transformed consistently."""


@dataclass
class FeaturePreprocessor:
    feature_columns: list[str]
    numeric_columns: list[str]
    boolean_columns: list[str]
    categorical_columns: list[str]
    category_mappings: dict[str, list[str]]

    @classmethod
    def fit(cls, features: pd.DataFrame) -> "FeaturePreprocessor":
        if features.empty:
            raise PreprocessingError("Cannot fit preprocessing on an empty feature frame")

        numeric_columns: list[str] = []
        boolean_columns: list[str] = []
        categorical_columns: list[str] = []
        category_mappings: dict[str, list[str]] = {}

        for column in features.columns:
            series = features[column]
            if is_bool_dtype(series.dtype):
                boolean_columns.append(column)
            elif is_numeric_dtype(series.dtype):
                numeric_columns.append(column)
            elif is_datetime64_any_dtype(series.dtype):
                raise PreprocessingError(
                    f"Datetime feature must be transformed or excluded explicitly: {column}"
                )
            else:
                categorical_columns.append(column)
                values = sorted(
                    {
                        str(value)
                        for value in series.dropna().tolist()
                        if str(value) not in {MISSING_CATEGORY, UNKNOWN_CATEGORY}
                    }
                )
                category_mappings[column] = [MISSING_CATEGORY, UNKNOWN_CATEGORY, *values]

        return cls(
            feature_columns=list(features.columns),
            numeric_columns=numeric_columns,
            boolean_columns=boolean_columns,
            categorical_columns=categorical_columns,
            category_mappings=category_mappings,
        )

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        missing = sorted(set(self.feature_columns) - set(features.columns))
        extra = sorted(set(features.columns) - set(self.feature_columns))
        if missing or extra:
            raise PreprocessingError(
                f"Feature columns differ from fitted config: missing={missing}, extra={extra}"
            )

        transformed = features.loc[:, self.feature_columns].copy()
        for column in self.numeric_columns:
            transformed[column] = pd.to_numeric(transformed[column], errors="coerce")
        for column in self.boolean_columns:
            transformed[column] = transformed[column].fillna(False).astype("int8")
        for column in self.categorical_columns:
            categories = self.category_mappings[column]
            known_values = set(categories)
            values = transformed[column].map(
                lambda value: MISSING_CATEGORY if pd.isna(value) else str(value)
            )
            values = values.map(lambda value: value if value in known_values else UNKNOWN_CATEGORY)
            transformed[column] = pd.Categorical(values, categories=categories)
        return transformed

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_columns": self.feature_columns,
            "numeric_columns": self.numeric_columns,
            "boolean_columns": self.boolean_columns,
            "categorical_columns": self.categorical_columns,
            "category_mappings": self.category_mappings,
            "missing_category": MISSING_CATEGORY,
            "unknown_category": UNKNOWN_CATEGORY,
        }

    @classmethod
    def load(cls, path: str | Path) -> "FeaturePreprocessor":
        config_path = Path(path)
        try:
            value = json.loads(config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise PreprocessingError(f"Could not load preprocessing config: {config_path}") from exc
        required = {
            "feature_columns",
            "numeric_columns",
            "boolean_columns",
            "categorical_columns",
            "category_mappings",
        }
        if not isinstance(value, dict) or not required.issubset(value):
            raise PreprocessingError(f"Preprocessing config is incomplete: {config_path}")
        return cls(
            feature_columns=list(value["feature_columns"]),
            numeric_columns=list(value["numeric_columns"]),
            boolean_columns=list(value["boolean_columns"]),
            categorical_columns=list(value["categorical_columns"]),
            category_mappings={
                str(column): list(categories)
                for column, categories in value["category_mappings"].items()
            },
        )

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return output_path

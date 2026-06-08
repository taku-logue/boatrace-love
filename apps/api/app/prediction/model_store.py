from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from lightgbm import LGBMClassifier

from app.ml.preprocessing import FeaturePreprocessor, PreprocessingError
from app.ml.train import load_model
from app.prediction.errors import PredictionAPIError
from app.prediction.schemas import ModelMetadataResponse

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
REQUIRED_ARTIFACTS = (
    "model.joblib",
    "model_metadata.json",
    "feature_columns.json",
    "categorical_columns.json",
    "preprocessing_config.json",
)


@dataclass(frozen=True)
class LoadedModelBundle:
    model_name: str
    model_version: str
    model_view: str
    bundle_path: Path
    metadata: dict[str, Any]
    feature_columns: list[str]
    categorical_columns: list[str]
    preprocessor: FeaturePreprocessor
    model: LGBMClassifier

    def to_metadata_response(self) -> ModelMetadataResponse:
        return ModelMetadataResponse(
            model_name=self.model_name,
            model_version=self.model_version,
            model_view=self.model_view,
            target=_optional_str(self.metadata.get("target")),
            feature_columns=self.feature_columns,
            categorical_columns=self.categorical_columns,
            created_at=_optional_str(self.metadata.get("created_at")),
            dataset_sha256=_optional_str(self.metadata.get("dataset_sha256")),
            schema_sha256=_optional_str(self.metadata.get("schema_sha256")),
            bundle_path=str(self.bundle_path),
        )


class ModelStore:
    def __init__(
        self,
        model_root: str | Path,
        *,
        default_model_view: str,
        cache_enabled: bool = True,
    ) -> None:
        self.model_root = Path(model_root).resolve(strict=False)
        self.default_model_view = default_model_view
        self.cache_enabled = cache_enabled
        self._cache: dict[tuple[str, float], LoadedModelBundle] = {}

    def load_bundle(self, model_name: str, model_version: str = "latest") -> LoadedModelBundle:
        safe_model_name = _validate_identifier(model_name, "model_name")
        safe_model_version = (
            self.latest_version(safe_model_name)
            if model_version == "latest"
            else _validate_identifier(model_version, "model_version")
        )
        bundle_path = self._bundle_path(safe_model_name, safe_model_version)
        self._validate_required_artifacts(bundle_path, safe_model_name, safe_model_version)
        signature = _artifact_signature(bundle_path)
        cache_key = (str(bundle_path), signature)
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        metadata = _read_json_object(bundle_path / "model_metadata.json")
        feature_columns = _read_string_list(bundle_path / "feature_columns.json")
        categorical_columns = _read_string_list(bundle_path / "categorical_columns.json")
        model = _load_lgbm_model(bundle_path / "model.joblib")
        preprocessor = _load_preprocessor(bundle_path / "preprocessing_config.json")

        metadata_model_name = metadata.get("model_name")
        metadata_model_version = metadata.get("model_version")
        if metadata_model_name not in (None, safe_model_name):
            raise PredictionAPIError(
                "model_bundle_invalid",
                "Model metadata name does not match the bundle path.",
                422,
                details={"metadata_model_name": metadata_model_name, "model_name": safe_model_name},
            )
        if metadata_model_version not in (None, safe_model_version):
            raise PredictionAPIError(
                "model_bundle_invalid",
                "Model metadata version does not match the bundle path.",
                422,
                details={
                    "metadata_model_version": metadata_model_version,
                    "model_version": safe_model_version,
                },
            )
        if metadata.get("feature_columns") not in (None, feature_columns):
            raise PredictionAPIError(
                "model_bundle_invalid",
                "Model metadata feature columns differ from feature_columns.json.",
                422,
            )
        if preprocessor.feature_columns != feature_columns:
            raise PredictionAPIError(
                "model_bundle_invalid",
                "Preprocessing feature columns differ from feature_columns.json.",
                422,
            )
        if preprocessor.categorical_columns != categorical_columns:
            raise PredictionAPIError(
                "model_bundle_invalid",
                "Preprocessing categorical columns differ from categorical_columns.json.",
                422,
            )

        model_view = _optional_str(metadata.get("model_view")) or self.default_model_view
        bundle = LoadedModelBundle(
            model_name=safe_model_name,
            model_version=safe_model_version,
            model_view=model_view,
            bundle_path=bundle_path,
            metadata=metadata,
            feature_columns=feature_columns,
            categorical_columns=categorical_columns,
            preprocessor=preprocessor,
            model=model,
        )
        if self.cache_enabled:
            self._cache[cache_key] = bundle
        return bundle

    def latest_version(self, model_name: str) -> str:
        safe_model_name = _validate_identifier(model_name, "model_name")
        model_directory = self._model_directory(safe_model_name)
        if not model_directory.exists():
            raise PredictionAPIError(
                "model_not_found",
                "Model directory does not exist.",
                404,
                details={"model_name": safe_model_name},
            )
        candidates = [
            path.name
            for path in model_directory.iterdir()
            if path.is_dir() and all((path / artifact).exists() for artifact in REQUIRED_ARTIFACTS)
        ]
        if not candidates:
            raise PredictionAPIError(
                "model_not_found",
                "No complete model bundle exists for the requested model.",
                404,
                details={"model_name": safe_model_name},
            )
        return sorted(candidates)[-1]

    def _model_directory(self, model_name: str) -> Path:
        model_directory = (self.model_root / model_name).resolve(strict=False)
        _ensure_under_root(model_directory, self.model_root)
        return model_directory

    def _bundle_path(self, model_name: str, model_version: str) -> Path:
        bundle_path = (self._model_directory(model_name) / model_version).resolve(strict=False)
        _ensure_under_root(bundle_path, self.model_root)
        return bundle_path

    def _validate_required_artifacts(
        self,
        bundle_path: Path,
        model_name: str,
        model_version: str,
    ) -> None:
        missing = [
            artifact for artifact in REQUIRED_ARTIFACTS if not (bundle_path / artifact).exists()
        ]
        if missing:
            raise PredictionAPIError(
                "model_not_found",
                "Model bundle is missing required artifacts.",
                404,
                details={
                    "model_name": model_name,
                    "model_version": model_version,
                    "missing": missing,
                },
            )


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _validate_identifier(value: str, field_name: str) -> str:
    if not value or value in {".", ".."} or not IDENTIFIER_PATTERN.fullmatch(value):
        raise PredictionAPIError(
            "model_not_found",
            "Model identifier is invalid.",
            404,
            details={field_name: value},
        )
    return value


def _ensure_under_root(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PredictionAPIError(
            "model_not_found",
            "Model path is outside of the configured model root.",
            404,
        ) from exc


def _artifact_signature(bundle_path: Path) -> float:
    return max((bundle_path / artifact).stat().st_mtime for artifact in REQUIRED_ARTIFACTS)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise PredictionAPIError(
            "model_bundle_invalid",
            "Could not read model bundle JSON.",
            422,
            details={"path": str(path)},
        ) from exc
    if not isinstance(value, dict):
        raise PredictionAPIError(
            "model_bundle_invalid",
            "Model bundle JSON must be an object.",
            422,
            details={"path": str(path)},
        )
    return value


def _read_string_list(path: Path) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise PredictionAPIError(
            "model_bundle_invalid",
            "Could not read model bundle JSON list.",
            422,
            details={"path": str(path)},
        ) from exc
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PredictionAPIError(
            "model_bundle_invalid",
            "Model bundle JSON must be a string list.",
            422,
            details={"path": str(path)},
        )
    return value


def _load_lgbm_model(path: Path) -> LGBMClassifier:
    try:
        return load_model(path)
    except ValueError as exc:
        raise PredictionAPIError(
            "model_bundle_invalid",
            "Could not load LightGBM model artifact.",
            422,
            details={"path": str(path)},
        ) from exc


def _load_preprocessor(path: Path) -> FeaturePreprocessor:
    try:
        return FeaturePreprocessor.load(path)
    except PreprocessingError as exc:
        raise PredictionAPIError(
            "model_bundle_invalid",
            "Could not load preprocessing config.",
            422,
            details={"path": str(path)},
        ) from exc

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any

LOCAL_API_PATH = Path(__file__).resolve().parent.parent / "apps" / "api"
if LOCAL_API_PATH.exists():
    sys.path.insert(0, str(LOCAL_API_PATH))
sys.path.append("/app")

from app.ml.dataset import load_training_dataset, prepare_dataset  # noqa: E402
from app.ml.evaluate import (  # noqa: E402
    evaluate_predictions,
    normalize_probabilities_by_race,
    prediction_frame,
)
from app.ml.preprocessing import FeaturePreprocessor  # noqa: E402
from app.ml.registry import log_training_run  # noqa: E402
from app.ml.split import split_by_race_date  # noqa: E402
from app.ml.train import (  # noqa: E402
    TrainingConfig,
    feature_importance_frame,
    predict_positive_probability,
    save_model,
    train_lightgbm,
)


def default_data_root() -> Path:
    if Path("/data").exists():
        return Path("/data")
    return Path(__file__).resolve().parent.parent / "data"


def default_tracking_uri() -> str:
    configured = os.getenv("MLFLOW_TRACKING_URI")
    if configured:
        return configured
    return "http://mlflow:5000" if Path("/data").exists() else "http://127.0.0.1:5000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 6: Phase 5 datasetからLightGBMの1着確率モデルを学習する"
    )
    parser.add_argument("--dataset", type=Path, required=True, help="Phase 5 Parquet path")
    parser.add_argument("--schema", type=Path, help="Phase 5 schema JSON path")
    parser.add_argument("--target", default="target_win", help="Target column")
    parser.add_argument("--model-name", default="lgbm_win_v1", help="Model name")
    parser.add_argument(
        "--experiment-name",
        default="boatrace_phase6_baseline",
        help="MLflow experiment name",
    )
    parser.add_argument("--tracking-uri", default=default_tracking_uri(), help="MLflow URI")
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--model-view", default="pre_race_no_odds")
    parser.add_argument("--feature-set-version", default="boat_features_v1")
    parser.add_argument("--train-ratio", type=float, default=0.6)
    parser.add_argument("--valid-ratio", type=float, default=0.2)
    parser.add_argument("--min-races-per-split", type=int, default=1)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--skip-mlflow",
        action="store_true",
        help="Skip MLflow logging for isolated development or tests",
    )
    return parser.parse_args()


def _date_range(df: Any) -> tuple[str, str]:
    values = df["race_date"]
    return str(values.min().date()), str(values.max().date())


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    schema_path = args.schema or args.dataset.with_suffix(".schema.json")
    loaded = load_training_dataset(args.dataset, schema_path, args.target)
    splits = split_by_race_date(
        loaded,
        train_ratio=args.train_ratio,
        valid_ratio=args.valid_ratio,
        min_races=args.min_races_per_split,
    )

    train_data = prepare_dataset(splits.train, args.target)
    valid_data = prepare_dataset(splits.valid, args.target)
    test_data = prepare_dataset(splits.test, args.target)

    preprocessor = FeaturePreprocessor.fit(train_data.features)
    train_features = preprocessor.transform(train_data.features)
    valid_features = preprocessor.transform(valid_data.features)
    test_features = preprocessor.transform(test_data.features)

    training_config = TrainingConfig(random_state=args.random_state)
    model = train_lightgbm(
        train_features,
        train_data.target,
        valid_features,
        valid_data.target,
        training_config,
    )

    predicted_at = datetime.now(UTC).isoformat()
    model_version = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    model_directory = args.data_root / "processed" / "models" / args.model_name / model_version
    report_directory = args.data_root / "processed" / "reports" / args.model_name / model_version
    model_directory.mkdir(parents=True, exist_ok=False)
    report_directory.mkdir(parents=True, exist_ok=False)

    valid_raw = predict_positive_probability(model, valid_features)
    valid_normalized = normalize_probabilities_by_race(valid_data.metadata["race_id"], valid_raw)
    test_raw = predict_positive_probability(model, test_features)
    test_normalized = normalize_probabilities_by_race(test_data.metadata["race_id"], test_raw)
    valid_metrics = evaluate_predictions(
        valid_data.metadata["race_id"], valid_data.target, valid_normalized
    )
    test_metrics = evaluate_predictions(
        test_data.metadata["race_id"], test_data.target, test_normalized
    )

    save_model(model, model_directory / "model.joblib")
    preprocessor.save(model_directory / "preprocessing_config.json")
    _write_json(model_directory / "feature_columns.json", preprocessor.feature_columns)
    _write_json(
        model_directory / "categorical_columns.json",
        preprocessor.categorical_columns,
    )
    shutil.copy2(schema_path, report_directory / "input_schema.json")
    feature_importance_frame(model).to_csv(report_directory / "feature_importance.csv", index=False)

    valid_predictions = prediction_frame(
        valid_data.metadata,
        valid_data.target,
        valid_raw,
        valid_normalized,
        args.model_name,
        model_version,
        predicted_at,
    )
    test_predictions = prediction_frame(
        test_data.metadata,
        test_data.target,
        test_raw,
        test_normalized,
        args.model_name,
        model_version,
        predicted_at,
    )
    valid_predictions.to_parquet(report_directory / "valid_predictions.parquet", index=False)
    test_predictions.to_parquet(report_directory / "test_predictions.parquet", index=False)

    train_start, train_end = _date_range(splits.train)
    valid_start, valid_end = _date_range(splits.valid)
    test_start, test_end = _date_range(splits.test)
    dataset_sha256 = _sha256(args.dataset)
    schema_sha256 = _sha256(schema_path)
    evaluation_report = {
        "model_name": args.model_name,
        "model_version": model_version,
        "model_view": args.model_view,
        "feature_set_version": args.feature_set_version,
        "target": args.target,
        "dataset_path": str(args.dataset.resolve()),
        "dataset_sha256": dataset_sha256,
        "schema_path": str(schema_path.resolve()),
        "schema_sha256": schema_sha256,
        "split": {
            "train": {
                "start_date": train_start,
                "end_date": train_end,
                "rows": len(splits.train),
                "races": int(splits.train["race_id"].nunique()),
            },
            "valid": {
                "start_date": valid_start,
                "end_date": valid_end,
                "rows": len(splits.valid),
                "races": int(splits.valid["race_id"].nunique()),
            },
            "test": {
                "start_date": test_start,
                "end_date": test_end,
                "rows": len(splits.test),
                "races": int(splits.test["race_id"].nunique()),
            },
        },
        "training_config": training_config.to_dict(),
        "best_iteration": model.best_iteration_,
        "valid_metrics": valid_metrics.to_dict(),
        "test_metrics": test_metrics.to_dict(),
        "predicted_at": predicted_at,
    }
    _write_json(report_directory / "evaluation_report.json", evaluation_report)
    _write_json(
        model_directory / "model_metadata.json",
        {
            "model_name": args.model_name,
            "model_version": model_version,
            "target": args.target,
            "feature_columns": preprocessor.feature_columns,
            "preprocessing_config": "preprocessing_config.json",
            "dataset_sha256": dataset_sha256,
            "schema_sha256": schema_sha256,
            "created_at": predicted_at,
        },
    )

    mlflow_run_id: str | None = None
    if not args.skip_mlflow:
        params = {
            "model_name": args.model_name,
            "model_view": args.model_view,
            "feature_set_version": args.feature_set_version,
            "target": args.target,
            "dataset_path": str(args.dataset.resolve()),
            "dataset_sha256": dataset_sha256,
            "schema_path": str(schema_path.resolve()),
            "schema_sha256": schema_sha256,
            "train_start_date": train_start,
            "train_end_date": train_end,
            "valid_start_date": valid_start,
            "valid_end_date": valid_end,
            "test_start_date": test_start,
            "test_end_date": test_end,
            **{f"lgbm_{key}": value for key, value in training_config.to_dict().items()},
        }
        metrics = {
            **{f"valid_{key}": float(value) for key, value in valid_metrics.to_dict().items()},
            **{f"test_{key}": float(value) for key, value in test_metrics.to_dict().items()},
        }
        mlflow_run_id = log_training_run(
            tracking_uri=args.tracking_uri,
            experiment_name=args.experiment_name,
            run_name=f"{args.model_name}-{model_version}",
            params=params,
            metrics=metrics,
            model_directory=model_directory,
            report_directory=report_directory,
        )

    print("Phase 6 model training completed")
    print(f"model: {model_directory / 'model.joblib'}")
    print(f"report: {report_directory / 'evaluation_report.json'}")
    print(f"valid log loss: {valid_metrics.log_loss:.6f}")
    print(f"test log loss: {test_metrics.log_loss:.6f}")
    print(f"test race hit rate: {test_metrics.race_hit_rate:.2%}")
    print(f"MLflow run id: {mlflow_run_id or 'skipped'}")


if __name__ == "__main__":
    main()

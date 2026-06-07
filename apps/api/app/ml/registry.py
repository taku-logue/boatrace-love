from pathlib import Path
from typing import Any

import mlflow


def log_training_run(
    *,
    tracking_uri: str,
    experiment_name: str,
    run_name: str,
    params: dict[str, Any],
    metrics: dict[str, float],
    model_directory: str | Path,
    report_directory: str | Path,
) -> str:
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as run:
        normalized_params = {
            key: value if isinstance(value, (str, int, float, bool)) else str(value)
            for key, value in params.items()
        }
        mlflow.log_params(normalized_params)
        mlflow.log_metrics(metrics)
        mlflow.log_artifacts(str(model_directory), artifact_path="model")
        mlflow.log_artifacts(str(report_directory), artifact_path="reports")
        return str(run.info.run_id)

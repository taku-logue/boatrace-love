import argparse
import subprocess
import sys
from pathlib import Path

from prefect import flow, task


def default_script_path() -> Path:
    docker_script = Path("/scripts/phase3_run_all_pipeline.py")
    if docker_script.exists():
        return docker_script
    return Path(__file__).resolve().with_name("phase3_run_all_pipeline.py")


def default_api_cwd() -> Path:
    docker_api = Path("/app")
    if docker_api.exists():
        return docker_api
    return Path(__file__).resolve().parents[1] / "apps" / "api"


@task(name="run-phase3-ingestion-cli")
def run_phase3_ingestion_cli(
    *,
    from_date: str,
    to_date: str | None = None,
    only: str = "all",
    venue_code: str | None = None,
    dry_run: bool = False,
    skip_download: bool = False,
    skip_quality: bool = False,
    sleep_seconds: float = 1.0,
    quality_min_join_rate: float = 0.95,
    http_retries: int = 3,
    http_backoff_seconds: float = 2.0,
    http_timeout_seconds: float = 30.0,
) -> str:
    command = [
        sys.executable,
        str(default_script_path()),
        "--from-date",
        from_date,
        "--only",
        only,
        "--sleep-seconds",
        str(sleep_seconds),
        "--quality-min-join-rate",
        str(quality_min_join_rate),
        "--http-retries",
        str(http_retries),
        "--http-backoff-seconds",
        str(http_backoff_seconds),
        "--http-timeout-seconds",
        str(http_timeout_seconds),
    ]
    if to_date:
        command.extend(["--to-date", to_date])
    if venue_code:
        command.extend(["--venue-code", venue_code])
    if dry_run:
        command.append("--dry-run")
    if skip_download:
        command.append("--skip-download")
    if skip_quality:
        command.append("--skip-quality")

    result = subprocess.run(
        command,
        cwd=default_api_cwd(),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Phase 3 ingestion CLI failed with exit code {result.returncode}")
    return result.stdout


@flow(name="phase3-race-cards-and-results-ingestion")
def phase3_ingestion_flow(
    from_date: str,
    to_date: str | None = None,
    only: str = "all",
    venue_code: str | None = None,
    dry_run: bool = False,
    skip_download: bool = False,
    skip_quality: bool = False,
    sleep_seconds: float = 1.0,
    quality_min_join_rate: float = 0.95,
    http_retries: int = 3,
    http_backoff_seconds: float = 2.0,
    http_timeout_seconds: float = 30.0,
) -> str:
    return run_phase3_ingestion_cli(
        from_date=from_date,
        to_date=to_date,
        only=only,
        venue_code=venue_code,
        dry_run=dry_run,
        skip_download=skip_download,
        skip_quality=skip_quality,
        sleep_seconds=sleep_seconds,
        quality_min_join_rate=quality_min_join_rate,
        http_retries=http_retries,
        http_backoff_seconds=http_backoff_seconds,
        http_timeout_seconds=http_timeout_seconds,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 3 ingestion through Prefect.")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date")
    parser.add_argument("--only", choices=["all", "race_cards", "race_results"], default="all")
    parser.add_argument("--venue-code")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--quality-min-join-rate", type=float, default=0.95)
    parser.add_argument("--http-retries", type=int, default=3)
    parser.add_argument("--http-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--http-timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    phase3_ingestion_flow(
        from_date=args.from_date,
        to_date=args.to_date,
        only=args.only,
        venue_code=args.venue_code,
        dry_run=args.dry_run,
        skip_download=args.skip_download,
        skip_quality=args.skip_quality,
        sleep_seconds=args.sleep_seconds,
        quality_min_join_rate=args.quality_min_join_rate,
        http_retries=args.http_retries,
        http_backoff_seconds=args.http_backoff_seconds,
        http_timeout_seconds=args.http_timeout_seconds,
    )


if __name__ == "__main__":
    main()

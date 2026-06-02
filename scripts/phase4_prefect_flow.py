from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from prefect import flow, task


def default_script_path() -> Path:
    docker_script = Path("/scripts/phase4_run_live_pipeline.py")
    if docker_script.exists():
        return docker_script
    return Path(__file__).resolve().with_name("phase4_run_live_pipeline.py")


def default_api_cwd() -> Path:
    docker_api = Path("/app")
    if docker_api.exists():
        return docker_api
    return Path(__file__).resolve().parents[1] / "apps" / "api"


@task(name="run-phase4-live-ingestion-cli")
def run_phase4_live_ingestion_cli(
    *,
    race_date: str,
    venue_code: str | None = None,
    race_no: int | None = None,
    only: str = "all",
    dry_run: bool = False,
    data_root: str | None = None,
    sleep_seconds: float = 1.0,
    http_retries: int = 3,
    http_backoff_seconds: float = 2.0,
    http_timeout_seconds: float = 10.0,
) -> str:
    command = [
        sys.executable,
        str(default_script_path()),
        "--race-date",
        race_date,
        "--only",
        only,
        "--sleep-seconds",
        str(sleep_seconds),
        "--http-retries",
        str(http_retries),
        "--http-backoff-seconds",
        str(http_backoff_seconds),
        "--http-timeout-seconds",
        str(http_timeout_seconds),
    ]
    if data_root:
        command.extend(["--data-root", data_root])
    if venue_code:
        command.extend(["--venue-code", venue_code])
    if race_no is not None:
        command.extend(["--race-no", str(race_no)])
    if dry_run:
        command.append("--dry-run")

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
        raise RuntimeError(f"Phase 4 live ingestion CLI failed with exit code {result.returncode}")
    return result.stdout


@flow(name="phase4-live-data-ingestion")
def phase4_live_ingestion_flow(
    race_date: str,
    venue_code: str | None = None,
    race_no: int | None = None,
    only: str = "all",
    dry_run: bool = False,
    data_root: str | None = None,
    sleep_seconds: float = 1.0,
    http_retries: int = 3,
    http_backoff_seconds: float = 2.0,
    http_timeout_seconds: float = 10.0,
) -> str:
    return run_phase4_live_ingestion_cli(
        race_date=race_date,
        venue_code=venue_code,
        race_no=race_no,
        only=only,
        dry_run=dry_run,
        data_root=data_root,
        sleep_seconds=sleep_seconds,
        http_retries=http_retries,
        http_backoff_seconds=http_backoff_seconds,
        http_timeout_seconds=http_timeout_seconds,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 live ingestion through Prefect.")
    parser.add_argument("--race-date", required=True)
    parser.add_argument("--venue-code")
    parser.add_argument("--race-no", type=int, choices=range(1, 13))
    parser.add_argument(
        "--only",
        choices=["all", "venues", "race_cards", "pre_race", "odds"],
        default="all",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data-root")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--http-retries", type=int, default=3)
    parser.add_argument("--http-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--http-timeout-seconds", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    phase4_live_ingestion_flow(
        race_date=args.race_date,
        venue_code=args.venue_code,
        race_no=args.race_no,
        only=args.only,
        dry_run=args.dry_run,
        data_root=args.data_root,
        sleep_seconds=args.sleep_seconds,
        http_retries=args.http_retries,
        http_backoff_seconds=args.http_backoff_seconds,
        http_timeout_seconds=args.http_timeout_seconds,
    )


if __name__ == "__main__":
    main()

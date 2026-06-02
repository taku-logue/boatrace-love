import argparse
import hashlib
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_API_PATH = REPO_ROOT / "apps" / "api"
if LOCAL_API_PATH.exists():
    sys.path.append(str(LOCAL_API_PATH))
sys.path.append("/app")

from app.db.session import engine  # noqa: E402
from app.ingestion.archive import LzhExtractor  # noqa: E402
from app.ingestion.encoding import detect_encoding  # noqa: E402
from app.ingestion.race_cards.load import upsert_race_cards  # noqa: E402
from app.ingestion.race_cards.parse import parse_race_card_file  # noqa: E402
from app.ingestion.race_downloads import (  # noqa: E402
    RaceFileKind,
    RaceDownloadTarget,
    build_race_download_target,
    extracted_storage_path,
    filter_records_by_venue,
    iter_dates,
    lzh_storage_path,
    path_for_raw_file_record,
)
from app.ingestion.race_quality import (  # noqa: E402
    format_race_quality_report,
    run_race_quality_checks,
)
from app.ingestion.race_results.load import upsert_race_results  # noqa: E402
from app.ingestion.race_results.parse import parse_race_result_file  # noqa: E402
from app.models.downloads import DownloadFile  # noqa: E402
from app.models.management import DataSource, IngestionRun, RawFile  # noqa: E402

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

RETRYABLE_HTTP_STATUS_CODES = {408, 429, 500, 502, 503, 504}


@dataclass
class TargetSummary:
    data_type: str
    race_date: date
    status: str
    races: int = 0
    raw_rows: int = 0
    dependent_rows: int = 0
    payouts: int = 0
    error_message: str | None = None


@dataclass(frozen=True)
class DownloadRetryConfig:
    retries: int = 3
    backoff_seconds: float = 2.0
    timeout_seconds: float = 30.0


def default_data_root() -> Path:
    env_value = os.environ.get("BOATRACE_DATA_DIR")
    if env_value:
        return Path(env_value)
    if Path("/data").exists():
        return Path("/data")
    return REPO_ROOT / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download, extract, parse, and load BOAT RACE B/K files."
    )
    parser.add_argument("--from-date", required=True, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to-date", help="End date in YYYY-MM-DD format. Defaults to from-date.")
    parser.add_argument(
        "--only",
        choices=["all", "race_cards", "race_results"],
        default="all",
        help="Limit the pipeline to one data type.",
    )
    parser.add_argument(
        "--venue-code",
        help="Optional two-digit venue code. Raw rows remain file-level; normalized rows are filtered.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=default_data_root(),
        help="Data directory. Defaults to BOATRACE_DATA_DIR, /data in Docker, or repo data/.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print targets without DB writes.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Use existing LZH files under data/raw/official_downloads.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Interval between official site requests.",
    )
    parser.add_argument(
        "--skip-quality",
        action="store_true",
        help="Skip post-ingestion data quality checks.",
    )
    parser.add_argument(
        "--quality-min-join-rate",
        type=float,
        default=0.95,
        help="Warning threshold for race card/result join rate.",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=3,
        help="Retry count for timeout, network, 408, 429, and 5xx download failures.",
    )
    parser.add_argument(
        "--http-backoff-seconds",
        type=float,
        default=2.0,
        help="Initial exponential backoff delay between download retries.",
    )
    parser.add_argument(
        "--http-timeout-seconds",
        type=float,
        default=30.0,
        help="HTTP timeout seconds for official data downloads.",
    )
    return parser.parse_args()


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_or_create_source(session: Session) -> DataSource:
    source = session.execute(
        select(DataSource).where(DataSource.name == "BOAT RACE Official")
    ).scalar_one_or_none()
    if source is not None:
        return source

    source = DataSource(
        name="BOAT RACE Official",
        base_url="https://www.boatrace.jp",
        description="BOAT RACE official downloadable data",
    )
    session.add(source)
    session.flush()
    return source


def start_run(session: Session, source_id: int) -> IngestionRun:
    run = IngestionRun(
        source_id=source_id,
        job_name="phase3_race_cards_and_results",
        status="running",
    )
    session.add(run)
    session.flush()
    return run


def finish_run(session: Session, run: IngestionRun, status: str, error_message: str | None) -> None:
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.error_message = error_message
    session.flush()


def upsert_download_file(
    session: Session,
    source_id: int,
    target: RaceDownloadTarget,
    status: str,
) -> DownloadFile:
    stmt = (
        insert(DownloadFile)
        .values(
            source_id=source_id,
            data_type=target.data_type,
            period_year=target.period_year,
            period_term=target.period_term,
            display_name=target.display_name,
            source_url=target.source_url,
            source_filename=target.source_filename,
            status=status,
        )
        .on_conflict_do_update(
            index_elements=["data_type", "period_year", "period_term", "source_url"],
            set_={
                "source_id": source_id,
                "display_name": target.display_name,
                "source_filename": target.source_filename,
                "status": status,
                "last_seen_at": func.now(),
                "error_message": None,
            },
        )
        .returning(DownloadFile.id)
    )
    download_file_id = session.execute(stmt).scalar_one()
    download_file = session.get(DownloadFile, download_file_id)
    if download_file is None:
        raise RuntimeError(f"download_files row not found: {download_file_id}")
    return download_file


def create_raw_file(
    session: Session,
    *,
    source_id: int,
    ingestion_run_id: int,
    file_type: str,
    source_url: str | None,
    local_path: Path,
    data_root: Path,
    sha256: str,
    metadata: dict[str, Any],
) -> RawFile:
    raw_file = RawFile(
        source_id=source_id,
        ingestion_run_id=ingestion_run_id,
        file_type=file_type,
        source_url=source_url,
        local_path=path_for_raw_file_record(local_path, data_root),
        sha256=sha256,
        file_metadata=metadata,
    )
    session.add(raw_file)
    session.flush()
    return raw_file


def is_retryable_status_code(status_code: int) -> bool:
    return status_code in RETRYABLE_HTTP_STATUS_CODES


def is_retryable_download_exception(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return is_retryable_status_code(exc.response.status_code)
    return isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
        ),
    )


def retry_delay_seconds(backoff_seconds: float, retry_index: int) -> float:
    return backoff_seconds * (2**retry_index)


def download_to_path(
    url: str,
    destination: Path,
    retry_config: DownloadRetryConfig | None = None,
) -> bool:
    retry_config = retry_config or DownloadRetryConfig()
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial_destination = destination.with_name(f"{destination.name}.part")
    attempts = retry_config.retries + 1

    for attempt_index in range(attempts):
        try:
            with httpx.stream(
                "GET",
                url,
                follow_redirects=True,
                timeout=retry_config.timeout_seconds,
                headers={"User-Agent": "BOATRACE-LOVE/phase3-ingestion"},
            ) as response:
                if response.status_code == 404:
                    return False
                response.raise_for_status()
                with partial_destination.open("wb") as file:
                    for chunk in response.iter_bytes():
                        file.write(chunk)
            partial_destination.replace(destination)
            return True
        except Exception as exc:
            partial_destination.unlink(missing_ok=True)
            can_retry = attempt_index < retry_config.retries and is_retryable_download_exception(
                exc
            )
            if not can_retry:
                raise
            delay = retry_delay_seconds(retry_config.backoff_seconds, attempt_index)
            print(
                "Retrying download after {delay:.1f}s ({attempt}/{max_attempts}): {url}".format(
                    delay=delay,
                    attempt=attempt_index + 1,
                    max_attempts=attempts,
                    url=url,
                )
            )
            time.sleep(delay)

    raise RuntimeError(f"Download retry loop exhausted unexpectedly: {url}")


def extract_text_file(data_root: Path, target: RaceDownloadTarget, lzh_path: Path) -> Path:
    temp_dir = data_root / "tmp" / "phase3" / target.data_type / target.period_term
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    extracted_files = LzhExtractor.extract_lzh(str(lzh_path), str(temp_dir))
    text_candidates = [
        Path(path) for path in extracted_files if Path(path).suffix.upper() == ".TXT"
    ]
    if not text_candidates:
        raise RuntimeError(f"TXT file not found in extracted archive: {lzh_path}")

    destination = extracted_storage_path(data_root, target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(text_candidates[0], destination)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return destination


def filter_payouts_by_races(
    payout_records: list[dict[str, Any]], race_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    race_ids = {str(record["race_id"]) for record in race_records}
    return [record for record in payout_records if str(record.get("race_id")) in race_ids]


def process_target(
    session: Session,
    *,
    source_id: int,
    run_id: int,
    data_root: Path,
    target: RaceDownloadTarget,
    venue_code: str | None,
    dry_run: bool,
    skip_download: bool,
    retry_config: DownloadRetryConfig,
) -> TargetSummary:
    lzh_path = lzh_storage_path(data_root, target)
    text_path = extracted_storage_path(data_root, target)

    if dry_run:
        return TargetSummary(
            data_type=target.data_type, race_date=target.race_date, status="dry-run"
        )

    download_file = upsert_download_file(session, source_id, target, "discovered")

    if not skip_download or not lzh_path.exists():
        found = download_to_path(target.source_url, lzh_path, retry_config)
        if not found:
            download_file.status = "not_found"
            download_file.error_message = "Official LZH file returned 404"
            session.flush()
            return TargetSummary(
                data_type=target.data_type,
                race_date=target.race_date,
                status="not_found",
                error_message=download_file.error_message,
            )

    lzh_sha256 = sha256_file(lzh_path)
    raw_lzh_file = create_raw_file(
        session,
        source_id=source_id,
        ingestion_run_id=run_id,
        file_type="lzh",
        source_url=target.source_url,
        local_path=lzh_path,
        data_root=data_root,
        sha256=lzh_sha256,
        metadata={
            "data_type": target.data_type,
            "race_date": target.race_date.isoformat(),
            "source_filename": target.source_filename,
        },
    )

    text_path = extract_text_file(data_root, target, lzh_path)
    text_sha256 = sha256_file(text_path)
    encoding = detect_encoding(str(text_path))
    extracted_file = create_raw_file(
        session,
        source_id=source_id,
        ingestion_run_id=run_id,
        file_type="txt",
        source_url=None,
        local_path=text_path,
        data_root=data_root,
        sha256=text_sha256,
        metadata={
            "data_type": target.data_type,
            "race_date": target.race_date.isoformat(),
            "encoding": encoding,
            "extracted_from_lzh": target.source_filename,
            "raw_lzh_file_id": raw_lzh_file.id,
        },
    )

    download_file.raw_lzh_file_id = raw_lzh_file.id
    download_file.extracted_file_id = extracted_file.id
    download_file.sha256 = lzh_sha256
    download_file.status = "completed"
    download_file.error_message = None

    if target.data_type == "race_cards":
        race_records, raw_records, entry_records = parse_race_card_file(
            str(text_path), download_file.id, extracted_file.id, target.race_date
        )
        filtered_races, filtered_entries = filter_records_by_venue(
            race_records, entry_records, venue_code
        )
        upsert_race_cards(session, filtered_races, raw_records, filtered_entries)
        return TargetSummary(
            data_type=target.data_type,
            race_date=target.race_date,
            status="completed",
            races=len(filtered_races),
            raw_rows=len(raw_records),
            dependent_rows=len(filtered_entries),
        )

    race_records, raw_records, result_records, payout_records = parse_race_result_file(
        str(text_path), download_file.id, extracted_file.id, target.race_date
    )
    filtered_races, filtered_results = filter_records_by_venue(
        race_records, result_records, venue_code
    )
    filtered_payouts = filter_payouts_by_races(payout_records, filtered_races)
    upsert_race_results(session, filtered_races, raw_records, filtered_results, filtered_payouts)
    return TargetSummary(
        data_type=target.data_type,
        race_date=target.race_date,
        status="completed",
        races=len(filtered_races),
        raw_rows=len(raw_records),
        dependent_rows=len(filtered_results),
        payouts=len(filtered_payouts),
    )


def target_kinds(only: str) -> list[RaceFileKind]:
    if only == "all":
        return ["race_cards", "race_results"]
    return [cast(RaceFileKind, only)]


def print_summary(summaries: list[TargetSummary]) -> None:
    print("\nPhase 3 ingestion summary")
    for summary in summaries:
        print(
            "- {date} {kind}: {status} "
            "races={races} raw_rows={raw_rows} rows={rows} payouts={payouts}".format(
                date=summary.race_date.isoformat(),
                kind=summary.data_type,
                status=summary.status,
                races=summary.races,
                raw_rows=summary.raw_rows,
                rows=summary.dependent_rows,
                payouts=summary.payouts,
            )
        )
        if summary.error_message:
            print(f"  error={summary.error_message}")


def main() -> None:
    args = parse_args()
    start_date = parse_date(args.from_date)
    end_date = parse_date(args.to_date) if args.to_date else start_date
    data_root = args.data_root.resolve()
    dates = iter_dates(start_date, end_date)

    if args.venue_code and (len(args.venue_code) != 2 or not args.venue_code.isdigit()):
        raise ValueError("--venue-code must be a two-digit code")
    if args.http_retries < 0:
        raise ValueError("--http-retries must be 0 or greater")
    if args.http_backoff_seconds < 0:
        raise ValueError("--http-backoff-seconds must be 0 or greater")
    if args.http_timeout_seconds <= 0:
        raise ValueError("--http-timeout-seconds must be greater than 0")

    retry_config = DownloadRetryConfig(
        retries=args.http_retries,
        backoff_seconds=args.http_backoff_seconds,
        timeout_seconds=args.http_timeout_seconds,
    )

    targets = [
        build_race_download_target(kind, race_date)
        for race_date in dates
        for kind in target_kinds(args.only)
    ]

    if args.dry_run:
        print("Dry-run targets")
        for target in targets:
            print(f"- {target.race_date.isoformat()} {target.data_type}: {target.source_url}")
        return

    summaries: list[TargetSummary] = []
    with SessionLocal() as session:
        source = get_or_create_source(session)
        run = start_run(session, source.id)
        session.commit()

        run_error: str | None = None
        for target in targets:
            try:
                summary = process_target(
                    session,
                    source_id=source.id,
                    run_id=run.id,
                    data_root=data_root,
                    target=target,
                    venue_code=args.venue_code,
                    dry_run=args.dry_run,
                    skip_download=args.skip_download,
                    retry_config=retry_config,
                )
                summaries.append(summary)
                session.commit()
                if not args.skip_download:
                    time.sleep(args.sleep_seconds)
            except Exception as exc:
                session.rollback()
                run_error = str(exc)
                summaries.append(
                    TargetSummary(
                        data_type=target.data_type,
                        race_date=target.race_date,
                        status="failed",
                        error_message=run_error,
                    )
                )
                break

        run = session.get(IngestionRun, run.id)
        if run is None:
            raise RuntimeError("ingestion run disappeared during processing")
        finish_run(session, run, "failed" if run_error else "completed", run_error)
        session.commit()

    print_summary(summaries)
    if any(summary.status == "failed" for summary in summaries):
        raise SystemExit(1)

    if not args.skip_quality:
        with SessionLocal() as session:
            report = run_race_quality_checks(
                session,
                from_date=start_date,
                to_date=end_date,
                venue_code=args.venue_code,
                min_join_rate=args.quality_min_join_rate,
            )
        print(format_race_quality_report(report))
        if not report.passed:
            raise SystemExit(2)


if __name__ == "__main__":
    main()

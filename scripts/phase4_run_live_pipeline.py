from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_API_PATH = REPO_ROOT / "apps" / "api"
if LOCAL_API_PATH.exists():
    sys.path.append(str(LOCAL_API_PATH))
sys.path.append("/app")

from app.db.session import engine  # noqa: E402
from app.ingestion.html_fetcher import (  # noqa: E402
    default_data_root,
    fetch_html,
    path_for_raw_file_record,
    save_raw_html,
    sha256_text,
)
from app.ingestion.live import (  # noqa: E402
    parse_live_active_venues,
    parse_live_beforeinfo_html,
    parse_live_odds_tf_html,
    parse_live_race_card_html,
    upsert_live_fetch_status,
    upsert_odds_snapshots,
    upsert_pre_race_info,
)
from app.ingestion.race_cards.load import upsert_race_cards  # noqa: E402
from app.models.management import DataSource, IngestionRun, RawFile  # noqa: E402

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

PAGE_PATHS = {
    "venues": "index",
    "race_cards": "racelist",
    "pre_race": "beforeinfo",
    "odds": "oddstf",
}


@dataclass(frozen=True)
class HttpRetryConfig:
    retries: int
    backoff_seconds: float
    timeout_seconds: float
    sleep_seconds: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch, save, parse, and load same-day BOAT RACE live HTML data."
    )
    parser.add_argument(
        "--race-date",
        default=date.today().isoformat(),
        help="Race date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument("--venue-code", help="Optional two-digit venue code.")
    parser.add_argument("--race-no", type=int, choices=range(1, 13), help="Optional race number.")
    parser.add_argument(
        "--only",
        choices=["all", "venues", "race_cards", "pre_race", "odds"],
        default="all",
        help="Limit the pipeline to one live data kind.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print targets without DB writes.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=default_data_root(),
        help="Data directory. Defaults to BOATRACE_DATA_DIR, /data in Docker, or repo data/.",
    )
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--http-retries", type=int, default=3)
    parser.add_argument("--http-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--http-timeout-seconds", type=float, default=10.0)
    return parser.parse_args()


def build_url(
    page_kind: str,
    target_date: date,
    venue_code: str | None = None,
    race_no: int | None = None,
) -> str:
    date_str = target_date.strftime("%Y%m%d")
    path = PAGE_PATHS[page_kind]
    if page_kind == "venues":
        return f"https://www.boatrace.jp/owpc/pc/race/{path}?hd={date_str}"
    if venue_code is None or race_no is None:
        raise ValueError("venue_code and race_no are required for race-level pages")
    return (
        f"https://www.boatrace.jp/owpc/pc/race/{path}"
        f"?rno={race_no}&jcd={venue_code.zfill(2)}&hd={date_str}"
    )


def fetch_with_retry(url: str, retry: HttpRetryConfig) -> str | None:
    for attempt in range(retry.retries + 1):
        html = fetch_html(
            url,
            sleep_seconds=retry.sleep_seconds if attempt == 0 else 0,
            timeout_seconds=retry.timeout_seconds,
        )
        if html is not None:
            return html
        if attempt < retry.retries:
            time.sleep(retry.backoff_seconds * (2**attempt))
    return None


def get_or_create_source(session: Session) -> DataSource:
    source = session.execute(
        select(DataSource).where(DataSource.name == "BOAT RACE Official")
    ).scalar_one_or_none()
    if source is not None:
        return source

    source = DataSource(
        name="BOAT RACE Official",
        base_url="https://www.boatrace.jp",
        description="BOAT RACE official live HTML pages",
    )
    session.add(source)
    session.flush()
    return source


def start_run(session: Session, source_id: int) -> IngestionRun:
    run = IngestionRun(
        source_id=source_id,
        job_name="phase4_live_data_ingestion",
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


def record_raw_html(
    session: Session,
    *,
    source_id: int,
    ingestion_run_id: int,
    data_root: Path,
    path: Path,
    source_url: str,
    html: str,
    metadata: dict[str, Any],
) -> RawFile:
    local_path = path_for_raw_file_record(path, data_root)
    digest = sha256_text(html)
    existing = session.execute(
        select(RawFile).where(
            RawFile.local_path == local_path,
            RawFile.source_url == source_url,
            RawFile.sha256 == digest,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    raw_file = RawFile(
        source_id=source_id,
        ingestion_run_id=ingestion_run_id,
        file_type="html",
        source_url=source_url,
        local_path=local_path,
        sha256=digest,
        file_metadata=metadata,
    )
    session.add(raw_file)
    session.flush()
    return raw_file


def record_fetch_status(
    session: Session,
    *,
    target_date: date,
    venue_code: str,
    race_no: int | None,
    data_kind: str,
    source_url: str,
    fetched_at: datetime,
    status: str,
    raw_file_id: int | None,
    ingestion_run_id: int | None,
    row_count: int | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    upsert_live_fetch_status(
        session,
        race_date=target_date,
        venue_code=venue_code,
        race_no=race_no,
        data_kind=data_kind,
        source_url=source_url,
        status=status,
        fetched_at=fetched_at,
        raw_file_id=raw_file_id,
        ingestion_run_id=ingestion_run_id,
        row_count=row_count,
        error_message=error_message,
        metadata=metadata,
    )


def fetch_active_venues(target_date: date, retry: HttpRetryConfig) -> list[str]:
    url = build_url("venues", target_date)
    html = fetch_with_retry(url, retry)
    if html is None:
        return []
    return parse_live_active_venues(html)


def process_live_race_card(
    session: Session,
    *,
    target_date: date,
    venue_code: str,
    race_no: int,
    dry_run: bool,
    retry: HttpRetryConfig,
    data_root: Path,
    source_id: int | None,
    ingestion_run_id: int | None,
) -> bool:
    url = build_url("race_cards", target_date, venue_code, race_no)
    if dry_run:
        print(f"[dry-run] race_cards: {url}")
        return True

    fetched_at = datetime.now(timezone.utc)
    html = fetch_with_retry(url, retry)
    if html is None:
        record_fetch_status(
            session,
            target_date=target_date,
            venue_code=venue_code,
            race_no=race_no,
            data_kind="race_cards",
            source_url=url,
            fetched_at=fetched_at,
            status="failed",
            raw_file_id=None,
            ingestion_run_id=ingestion_run_id,
            error_message="HTML fetch failed",
        )
        return False

    raw_path = save_raw_html(html, target_date, "racelist", venue_code, race_no, data_root)
    raw_file = record_raw_html(
        session,
        source_id=source_id or 0,
        ingestion_run_id=ingestion_run_id or 0,
        data_root=data_root,
        path=raw_path,
        source_url=url,
        html=html,
        metadata={
            "data_kind": "race_cards",
            "race_date": target_date.isoformat(),
            "venue_code": venue_code.zfill(2),
            "race_no": race_no,
            "parser_version": "phase4_live_race_cards_v1",
            "fetch_method": "httpx",
        },
    )
    race_records, entry_records = parse_live_race_card_html(html, target_date, venue_code, race_no)
    for race_record in race_records:
        race_record["raw_card_file_id"] = raw_file.id

    if not entry_records:
        record_fetch_status(
            session,
            target_date=target_date,
            venue_code=venue_code,
            race_no=race_no,
            data_kind="race_cards",
            source_url=url,
            fetched_at=fetched_at,
            status="not_found",
            raw_file_id=raw_file.id,
            ingestion_run_id=ingestion_run_id,
            row_count=0,
        )
        return False

    upsert_race_cards(session, race_records, [], entry_records)
    record_fetch_status(
        session,
        target_date=target_date,
        venue_code=venue_code,
        race_no=race_no,
        data_kind="race_cards",
        source_url=url,
        fetched_at=fetched_at,
        status="completed",
        raw_file_id=raw_file.id,
        ingestion_run_id=ingestion_run_id,
        row_count=len(entry_records),
    )
    return True


def process_live_beforeinfo(
    session: Session,
    *,
    target_date: date,
    venue_code: str,
    race_no: int,
    dry_run: bool,
    retry: HttpRetryConfig,
    data_root: Path,
    source_id: int | None,
    ingestion_run_id: int | None,
) -> None:
    url = build_url("pre_race", target_date, venue_code, race_no)
    if dry_run:
        print(f"[dry-run] pre_race: {url}")
        return

    fetched_at = datetime.now(timezone.utc)
    html = fetch_with_retry(url, retry)
    if html is None:
        record_fetch_status(
            session,
            target_date=target_date,
            venue_code=venue_code,
            race_no=race_no,
            data_kind="pre_race",
            source_url=url,
            fetched_at=fetched_at,
            status="failed",
            raw_file_id=None,
            ingestion_run_id=ingestion_run_id,
            error_message="HTML fetch failed",
        )
        return

    raw_path = save_raw_html(html, target_date, "beforeinfo", venue_code, race_no, data_root)
    raw_file = record_raw_html(
        session,
        source_id=source_id or 0,
        ingestion_run_id=ingestion_run_id or 0,
        data_root=data_root,
        path=raw_path,
        source_url=url,
        html=html,
        metadata={
            "data_kind": "pre_race",
            "race_date": target_date.isoformat(),
            "venue_code": venue_code.zfill(2),
            "race_no": race_no,
            "parser_version": "phase4_live_beforeinfo_v1",
            "fetch_method": "httpx",
        },
    )
    records = parse_live_beforeinfo_html(html, target_date, venue_code, race_no)
    if records:
        upsert_pre_race_info(session, records, fetched_at)

    record_fetch_status(
        session,
        target_date=target_date,
        venue_code=venue_code,
        race_no=race_no,
        data_kind="pre_race",
        source_url=url,
        fetched_at=fetched_at,
        status="completed" if records else "not_found",
        raw_file_id=raw_file.id,
        ingestion_run_id=ingestion_run_id,
        row_count=len(records),
    )


def process_live_odds(
    session: Session,
    *,
    target_date: date,
    venue_code: str,
    race_no: int,
    dry_run: bool,
    retry: HttpRetryConfig,
    data_root: Path,
    source_id: int | None,
    ingestion_run_id: int | None,
) -> None:
    url = build_url("odds", target_date, venue_code, race_no)
    if dry_run:
        print(f"[dry-run] odds: {url}")
        return

    fetched_at = datetime.now(timezone.utc)
    html = fetch_with_retry(url, retry)
    if html is None:
        record_fetch_status(
            session,
            target_date=target_date,
            venue_code=venue_code,
            race_no=race_no,
            data_kind="odds",
            source_url=url,
            fetched_at=fetched_at,
            status="failed",
            raw_file_id=None,
            ingestion_run_id=ingestion_run_id,
            error_message="HTML fetch failed",
        )
        return

    raw_path = save_raw_html(html, target_date, "oddstf", venue_code, race_no, data_root)
    raw_file = record_raw_html(
        session,
        source_id=source_id or 0,
        ingestion_run_id=ingestion_run_id or 0,
        data_root=data_root,
        path=raw_path,
        source_url=url,
        html=html,
        metadata={
            "data_kind": "odds",
            "bet_type": "win",
            "race_date": target_date.isoformat(),
            "venue_code": venue_code.zfill(2),
            "race_no": race_no,
            "parser_version": "phase4_live_oddstf_v1",
            "fetch_method": "httpx",
        },
    )
    records = parse_live_odds_tf_html(html, target_date, venue_code, race_no, fetched_at)
    if records:
        upsert_odds_snapshots(session, records)

    record_fetch_status(
        session,
        target_date=target_date,
        venue_code=venue_code,
        race_no=race_no,
        data_kind="odds",
        source_url=url,
        fetched_at=fetched_at,
        status="completed" if records else "not_found",
        raw_file_id=raw_file.id,
        ingestion_run_id=ingestion_run_id,
        row_count=len(records),
    )


def selected_venues(
    target_date: date,
    venue_code: str | None,
    retry: HttpRetryConfig,
    dry_run: bool,
) -> list[str]:
    if venue_code:
        return [venue_code.zfill(2)]

    index_url = build_url("venues", target_date)
    if dry_run:
        print(f"[dry-run] venues: {index_url}")
    venues = fetch_active_venues(target_date, retry)
    if dry_run:
        print(f"[dry-run] active venues: {venues}")
    return venues


def main() -> None:
    args = parse_args()
    target_date = date.fromisoformat(args.race_date)
    retry = HttpRetryConfig(
        retries=args.http_retries,
        backoff_seconds=args.http_backoff_seconds,
        timeout_seconds=args.http_timeout_seconds,
        sleep_seconds=args.sleep_seconds,
    )
    race_numbers = [args.race_no] if args.race_no is not None else list(range(1, 13))
    venues = selected_venues(target_date, args.venue_code, retry, args.dry_run)

    if args.only == "venues":
        print(f"active venues: {venues}")
        return
    if not venues:
        print("active venues were not found")
        return

    with SessionLocal() as session:
        source: DataSource | None = None
        run: IngestionRun | None = None
        if not args.dry_run:
            source = get_or_create_source(session)
            run = start_run(session, source.id)

        try:
            for venue_code in venues:
                for race_no in race_numbers:
                    has_race_card = True
                    if args.only in {"all", "race_cards"}:
                        has_race_card = process_live_race_card(
                            session,
                            target_date=target_date,
                            venue_code=venue_code,
                            race_no=race_no,
                            dry_run=args.dry_run,
                            retry=retry,
                            data_root=args.data_root,
                            source_id=source.id if source else None,
                            ingestion_run_id=run.id if run else None,
                        )
                        if not has_race_card and args.only == "all":
                            break

                    if args.only in {"all", "pre_race"} and has_race_card:
                        process_live_beforeinfo(
                            session,
                            target_date=target_date,
                            venue_code=venue_code,
                            race_no=race_no,
                            dry_run=args.dry_run,
                            retry=retry,
                            data_root=args.data_root,
                            source_id=source.id if source else None,
                            ingestion_run_id=run.id if run else None,
                        )

                    if args.only in {"all", "odds"} and has_race_card:
                        process_live_odds(
                            session,
                            target_date=target_date,
                            venue_code=venue_code,
                            race_no=race_no,
                            dry_run=args.dry_run,
                            retry=retry,
                            data_root=args.data_root,
                            source_id=source.id if source else None,
                            ingestion_run_id=run.id if run else None,
                        )

                if not args.dry_run:
                    session.flush()

            if run is not None:
                finish_run(session, run, "completed", None)
            if not args.dry_run:
                session.commit()
        except Exception as exc:
            if run is not None:
                finish_run(session, run, "failed", str(exc))
            session.commit()
            raise


if __name__ == "__main__":
    main()

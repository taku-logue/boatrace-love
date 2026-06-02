from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.ingestion.race_cards.load import upsert_race_cards
from app.ingestion.race_results.load import upsert_race_results
from app.models.downloads import DownloadFile
from app.models.management import RawFile
from app.models.payouts import Payout
from app.models.race_cards import RaceCardRaw, RaceEntry
from app.models.race_master import Race
from app.models.race_results import RaceResult, RaceResultRaw


def open_test_session() -> tuple[Session, object, object]:
    try:
        connection = engine.connect()
        connection.execute(text("SELECT 1"))
        connection.rollback()
    except SQLAlchemyError as exc:
        pytest.skip(f"PostgreSQL is not available for integration test: {exc}")

    transaction = connection.begin()
    return Session(bind=connection), transaction, connection


def add_raw_file(session: Session, local_path: str) -> RawFile:
    raw_file = RawFile(
        file_type="txt",
        local_path=local_path,
        sha256="0" * 64,
        file_metadata={"test": True},
    )
    session.add(raw_file)
    session.flush()
    return raw_file


def add_download_file(
    session: Session, data_type: str, raw_file_id: int, suffix: str
) -> DownloadFile:
    download_file = DownloadFile(
        data_type=data_type,
        period_year=2099,
        period_term=f"2099-01-01-{suffix}",
        display_name=f"test {data_type} {suffix}",
        source_url=f"https://example.test/{data_type}/{suffix}.lzh",
        source_filename=f"{suffix}.lzh",
        status="completed",
        extracted_file_id=raw_file_id,
        sha256="1" * 64,
    )
    session.add(download_file)
    session.flush()
    return download_file


def test_upsert_race_cards_is_idempotent_against_postgres():
    session, transaction, connection = open_test_session()
    try:
        raw_file_1 = add_raw_file(session, "data/raw/extracted/test/cards-1.txt")
        raw_file_2 = add_raw_file(session, "data/raw/extracted/test/cards-2.txt")
        download_file = add_download_file(session, "race_cards", raw_file_1.id, "cards")
        race_id = "20990101_99_01"
        race_records = [
            {
                "race_id": race_id,
                "race_date": date(2099, 1, 1),
                "venue_code": "99",
                "race_no": 1,
                "race_name": "test race",
                "grade": None,
                "distance_m": 1800,
                "deadline_at": None,
                "raw_card_file_id": raw_file_1.id,
            }
        ]
        entry_records = [
            {
                "race_id": race_id,
                "boat_no": 1,
                "racer_registration_no": "9999",
                "racer_name": "BEFORE",
                "racer_class": "A1",
                "branch": "TEST",
                "motor_no": "11",
                "boat_no_assigned": "22",
                "raw_values": {"version": 1},
                "normalized_values": {"version": 1},
            }
        ]
        raw_records = [
            {
                "download_file_id": download_file.id,
                "raw_file_id": raw_file_1.id,
                "line_number": 1,
                "raw_text": "before",
                "raw_fields": {"version": 1},
                "parse_status": "parsed",
                "parse_error": None,
                "parser_version": "race_cards_v1",
            }
        ]

        upsert_race_cards(session, race_records, raw_records, entry_records)
        raw_records[0]["raw_file_id"] = raw_file_2.id
        raw_records[0]["raw_text"] = "after"
        entry_records[0]["racer_name"] = "AFTER"
        upsert_race_cards(session, race_records, raw_records, entry_records)
        session.flush()

        race_count = session.scalar(
            select(func.count()).select_from(Race).where(Race.race_id == race_id)
        )
        raw_count = session.scalar(
            select(text("count(*)"))
            .select_from(RaceCardRaw)
            .where(
                RaceCardRaw.download_file_id == download_file.id,
                RaceCardRaw.line_number == 1,
            )
        )
        entry_count = session.scalar(
            select(text("count(*)"))
            .select_from(RaceEntry)
            .where(
                RaceEntry.race_id == race_id,
                RaceEntry.boat_no == 1,
            )
        )
        raw_row = session.execute(
            select(RaceCardRaw).where(
                RaceCardRaw.download_file_id == download_file.id,
                RaceCardRaw.line_number == 1,
            )
        ).scalar_one()
        entry = session.execute(
            select(RaceEntry).where(RaceEntry.race_id == race_id, RaceEntry.boat_no == 1)
        ).scalar_one()

        assert race_count == 1
        assert raw_count == 1
        assert entry_count == 1
        assert raw_row.raw_file_id == raw_file_2.id
        assert raw_row.raw_text == "after"
        assert entry.racer_name == "AFTER"
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_upsert_race_results_is_idempotent_against_postgres():
    session, transaction, connection = open_test_session()
    try:
        raw_file_1 = add_raw_file(session, "data/raw/extracted/test/results-1.txt")
        raw_file_2 = add_raw_file(session, "data/raw/extracted/test/results-2.txt")
        download_file = add_download_file(session, "race_results", raw_file_1.id, "results")
        race_id = "20990101_99_02"
        race_records = [
            {
                "race_id": race_id,
                "race_date": date(2099, 1, 1),
                "venue_code": "99",
                "race_no": 2,
                "race_name": "test race",
                "grade": None,
                "distance_m": 1800,
                "deadline_at": None,
                "raw_result_file_id": raw_file_1.id,
            }
        ]
        result_records = [
            {
                "race_id": race_id,
                "boat_no": 1,
                "racer_registration_no": "9999",
                "finish_position": 1,
                "entry_course": 1,
                "start_timing": 0.12,
                "decision": "逃げ",
                "result_status": "normal",
                "raw_values": {"version": 1},
                "normalized_values": {"version": 1},
            }
        ]
        payout_records = [
            {
                "race_id": race_id,
                "bet_type": "3連単",
                "combination": "1-2-3",
                "payout_yen": 1200,
                "popularity": 1,
                "raw_values": {"version": 1},
            }
        ]
        raw_records = [
            {
                "download_file_id": download_file.id,
                "raw_file_id": raw_file_1.id,
                "line_number": 1,
                "raw_text": "before",
                "raw_fields": {"version": 1},
                "parse_status": "parsed",
                "parse_error": None,
                "parser_version": "race_results_v1",
            }
        ]

        upsert_race_results(session, race_records, raw_records, result_records, payout_records)
        raw_records[0]["raw_file_id"] = raw_file_2.id
        raw_records[0]["raw_text"] = "after"
        result_records[0]["start_timing"] = 0.08
        payout_records[0]["payout_yen"] = 1500
        payout_records[0]["popularity"] = 2
        payout_records[0]["raw_values"] = {"version": 2}
        upsert_race_results(session, race_records, raw_records, result_records, payout_records)
        session.flush()

        raw_count = session.scalar(
            select(text("count(*)"))
            .select_from(RaceResultRaw)
            .where(
                RaceResultRaw.download_file_id == download_file.id,
                RaceResultRaw.line_number == 1,
            )
        )
        result_count = session.scalar(
            select(text("count(*)"))
            .select_from(RaceResult)
            .where(
                RaceResult.race_id == race_id,
                RaceResult.boat_no == 1,
            )
        )
        payout_count = session.scalar(
            select(text("count(*)"))
            .select_from(Payout)
            .where(
                Payout.race_id == race_id,
                Payout.bet_type == "3連単",
                Payout.combination == "1-2-3",
            )
        )
        raw_row = session.execute(
            select(RaceResultRaw).where(
                RaceResultRaw.download_file_id == download_file.id,
                RaceResultRaw.line_number == 1,
            )
        ).scalar_one()
        result = session.execute(
            select(RaceResult).where(RaceResult.race_id == race_id, RaceResult.boat_no == 1)
        ).scalar_one()
        payout = session.execute(
            select(Payout).where(
                Payout.race_id == race_id,
                Payout.bet_type == "3連単",
                Payout.combination == "1-2-3",
            )
        ).scalar_one()

        assert raw_count == 1
        assert result_count == 1
        assert payout_count == 1
        assert raw_row.raw_file_id == raw_file_2.id
        assert raw_row.raw_text == "after"
        assert float(result.start_timing) == 0.08
        assert payout.payout_yen == 1500
        assert payout.popularity == 2
        assert payout.raw_values == {"version": 2}
    finally:
        session.close()
        transaction.rollback()
        connection.close()

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import engine
from app.ingestion.live.load import upsert_odds_snapshots, upsert_pre_race_info
from app.models.odds import OddsSnapshot, OddsSnapshotEntry
from app.models.pre_race_info import PreRaceEntryInfo, WeatherObservation
from app.models.race_master import Race


def open_test_session() -> tuple[Session, object, object]:
    try:
        connection = engine.connect()
        connection.execute(text("SELECT 1"))
        connection.rollback()
    except SQLAlchemyError as exc:
        pytest.skip(f"PostgreSQL is not available for integration test: {exc}")

    transaction = connection.begin()
    return Session(bind=connection), transaction, connection


def add_race(session: Session, race_id: str) -> None:
    session.add(
        Race(
            race_id=race_id,
            race_date=date(2099, 4, 4),
            venue_code="98",
            race_no=1,
        )
    )
    session.flush()


def test_upsert_pre_race_info_is_idempotent_against_postgres() -> None:
    session, transaction, connection = open_test_session()
    try:
        race_id = "20990404_98_01"
        fetched_at = datetime(2099, 4, 4, 10, 0, tzinfo=timezone.utc)
        add_race(session, race_id)

        records = [
            {
                "race_id": race_id,
                "boat_no": 1,
                "exhibition_time": 6.50,
                "tilt_angle": -0.5,
                "start_exhibition_course": 1,
                "start_exhibition_timing": 0.03,
                "weather": "晴",
                "temperature": 22.0,
                "wind_direction": "is-wind1",
                "wind_speed": 2,
                "water_temperature": 20.0,
                "wave_height": 1,
                "raw_values": {"version": 1},
            }
        ]
        upsert_pre_race_info(session, records, fetched_at)
        records[0]["exhibition_time"] = 6.55
        records[0]["raw_values"] = {"version": 2}
        upsert_pre_race_info(session, records, fetched_at)
        session.flush()

        pre_race_count = session.scalar(
            select(func.count())
            .select_from(PreRaceEntryInfo)
            .where(PreRaceEntryInfo.race_id == race_id)
        )
        weather_count = session.scalar(
            select(func.count())
            .select_from(WeatherObservation)
            .where(WeatherObservation.race_id == race_id)
        )
        entry = session.execute(
            select(PreRaceEntryInfo).where(PreRaceEntryInfo.race_id == race_id)
        ).scalar_one()

        assert pre_race_count == 1
        assert weather_count == 1
        assert entry.exhibition_time == Decimal("6.55")
        assert entry.raw_values == {"version": 2}
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_upsert_odds_snapshots_is_idempotent_against_postgres() -> None:
    session, transaction, connection = open_test_session()
    try:
        race_id = "20990404_98_01"
        fetched_at = datetime(2099, 4, 4, 10, 5, tzinfo=timezone.utc)
        add_race(session, race_id)

        records = [
            {
                "race_id": race_id,
                "bet_type": "win",
                "fetched_at": fetched_at,
                "combination": "1",
                "odds_value": 2.5,
                "raw_values": {"version": 1},
            }
        ]
        upsert_odds_snapshots(session, records)
        records[0]["odds_value"] = 3.0
        records[0]["raw_values"] = {"version": 2}
        upsert_odds_snapshots(session, records)
        session.flush()

        snapshot_count = session.scalar(
            select(func.count()).select_from(OddsSnapshot).where(OddsSnapshot.race_id == race_id)
        )
        entry_count = session.scalar(
            select(func.count())
            .select_from(OddsSnapshotEntry)
            .where(OddsSnapshotEntry.race_id == race_id)
        )
        entry = session.execute(
            select(OddsSnapshotEntry).where(OddsSnapshotEntry.race_id == race_id)
        ).scalar_one()

        assert snapshot_count == 1
        assert entry_count == 1
        assert entry.odds_value == Decimal("3.0")
        assert entry.raw_values == {"version": 2}
    finally:
        session.close()
        transaction.rollback()
        connection.close()

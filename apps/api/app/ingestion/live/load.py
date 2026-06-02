from datetime import date, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.odds import OddsSnapshot, OddsSnapshotEntry
from app.models.pre_race_info import LiveFetchStatus, PreRaceEntryInfo, WeatherObservation


def upsert_live_fetch_status(
    session: Session,
    *,
    race_date: date,
    venue_code: str,
    race_no: int | None,
    data_kind: str,
    source_url: str,
    status: str,
    fetched_at: datetime,
    raw_file_id: int | None = None,
    ingestion_run_id: int | None = None,
    error_message: str | None = None,
    row_count: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    values = {
        "race_date": race_date,
        "venue_code": venue_code.zfill(2),
        "race_no": race_no,
        "data_kind": data_kind,
        "source_url": source_url,
        "status": status,
        "raw_file_id": raw_file_id,
        "ingestion_run_id": ingestion_run_id,
        "fetched_at": fetched_at,
        "error_message": error_message,
        "row_count": row_count,
        "file_metadata": metadata or {},
    }
    stmt = insert(LiveFetchStatus).values(values)
    session.execute(stmt)


def upsert_pre_race_info(
    session: Session,
    records: list[dict[str, Any]],
    fetched_at: datetime,
) -> None:
    if not records:
        return

    first = records[0]
    weather_stmt = insert(WeatherObservation).values(
        {
            "race_id": first["race_id"],
            "fetched_at": fetched_at,
            "weather": first.get("weather"),
            "temperature": first.get("temperature"),
            "wind_direction": first.get("wind_direction"),
            "wind_speed": first.get("wind_speed"),
            "water_temperature": first.get("water_temperature"),
            "wave_height": first.get("wave_height"),
            "raw_values": {
                key: first.get(key)
                for key in (
                    "weather",
                    "temperature",
                    "wind_direction",
                    "wind_speed",
                    "water_temperature",
                    "wave_height",
                )
            },
        }
    )
    weather_stmt = weather_stmt.on_conflict_do_update(
        index_elements=["race_id", "fetched_at"],
        set_={
            "weather": weather_stmt.excluded.weather,
            "temperature": weather_stmt.excluded.temperature,
            "wind_direction": weather_stmt.excluded.wind_direction,
            "wind_speed": weather_stmt.excluded.wind_speed,
            "water_temperature": weather_stmt.excluded.water_temperature,
            "wave_height": weather_stmt.excluded.wave_height,
            "raw_values": weather_stmt.excluded.raw_values,
        },
    )
    session.execute(weather_stmt)

    entry_values = [
        {
            "race_id": record["race_id"],
            "boat_no": record["boat_no"],
            "fetched_at": fetched_at,
            "exhibition_time": record.get("exhibition_time"),
            "tilt_angle": record.get("tilt_angle"),
            "start_exhibition_course": record.get("start_exhibition_course"),
            "start_exhibition_timing": record.get("start_exhibition_timing"),
            "raw_values": record.get("raw_values", {}),
        }
        for record in records
    ]
    entry_stmt = insert(PreRaceEntryInfo).values(entry_values)
    entry_stmt = entry_stmt.on_conflict_do_update(
        index_elements=["race_id", "boat_no", "fetched_at"],
        set_={
            "exhibition_time": entry_stmt.excluded.exhibition_time,
            "tilt_angle": entry_stmt.excluded.tilt_angle,
            "start_exhibition_course": entry_stmt.excluded.start_exhibition_course,
            "start_exhibition_timing": entry_stmt.excluded.start_exhibition_timing,
            "raw_values": entry_stmt.excluded.raw_values,
        },
    )
    session.execute(entry_stmt)


def upsert_odds_snapshots(session: Session, records: list[dict[str, Any]]) -> None:
    if not records:
        return

    grouped_records: dict[tuple[str, str, datetime], list[dict[str, Any]]] = {}
    for record in records:
        key = (record["race_id"], record["bet_type"], record["fetched_at"])
        grouped_records.setdefault(key, []).append(record)

    for (race_id, bet_type, fetched_at), entries in grouped_records.items():
        snapshot_stmt = insert(OddsSnapshot).values(
            {
                "race_id": race_id,
                "bet_type": bet_type,
                "fetched_at": fetched_at,
                "raw_values": {"entry_count": len(entries)},
            }
        )
        snapshot_stmt = snapshot_stmt.on_conflict_do_update(
            index_elements=["race_id", "bet_type", "fetched_at"],
            set_={"raw_values": snapshot_stmt.excluded.raw_values},
        )
        session.execute(snapshot_stmt)

        entry_values = [
            {
                "race_id": race_id,
                "bet_type": bet_type,
                "fetched_at": fetched_at,
                "combination": entry["combination"],
                "odds_value": entry.get("odds_value"),
                "raw_values": entry.get("raw_values", {}),
            }
            for entry in entries
        ]
        entry_stmt = insert(OddsSnapshotEntry).values(entry_values)
        entry_stmt = entry_stmt.on_conflict_do_update(
            index_elements=["race_id", "bet_type", "fetched_at", "combination"],
            set_={
                "odds_value": entry_stmt.excluded.odds_value,
                "raw_values": entry_stmt.excluded.raw_values,
            },
        )
        session.execute(entry_stmt)

from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.race_master import Race
from app.models.race_cards import RaceCardRaw, RaceEntry


def upsert_race_cards(
    session: Session,
    race_records: list[dict[str, Any]],
    raw_records: list[dict[str, Any]],
    entry_records: list[dict[str, Any]],
) -> None:
    """番組表関連テーブルへのUpsert処理"""

    # 1. races へのUpsert (番組表起点)
    if race_records:
        race_stmt = insert(Race).values(race_records)
        race_stmt = race_stmt.on_conflict_do_update(
            index_elements=["race_date", "venue_code", "race_no"],
            set_={
                "raw_card_file_id": race_stmt.excluded.raw_card_file_id,
                "updated_at": race_stmt.excluded.updated_at,
            },
        )
        session.execute(race_stmt)

    # 2. race_card_raw へのUpsert
    if raw_records:
        raw_stmt = insert(RaceCardRaw).values(raw_records)
        raw_stmt = raw_stmt.on_conflict_do_update(
            index_elements=["download_file_id", "line_number"],
            set_={
                "raw_file_id": raw_stmt.excluded.raw_file_id,
                "raw_text": raw_stmt.excluded.raw_text,
                "raw_fields": raw_stmt.excluded.raw_fields,
                "parse_status": raw_stmt.excluded.parse_status,
                "parse_error": raw_stmt.excluded.parse_error,
                "parser_version": raw_stmt.excluded.parser_version,
            },
        )
        session.execute(raw_stmt)

    # 3. race_entries へのUpsert
    if entry_records:
        entry_stmt = insert(RaceEntry).values(entry_records)
        entry_stmt = entry_stmt.on_conflict_do_update(
            index_elements=["race_id", "boat_no"],
            set_={
                "racer_registration_no": entry_stmt.excluded.racer_registration_no,
                "racer_name": entry_stmt.excluded.racer_name,
                "racer_class": entry_stmt.excluded.racer_class,
                "branch": entry_stmt.excluded.branch,
                "motor_no": entry_stmt.excluded.motor_no,
                "boat_no_assigned": entry_stmt.excluded.boat_no_assigned,
                "raw_values": entry_stmt.excluded.raw_values,
                "normalized_values": entry_stmt.excluded.normalized_values,
            },
        )
        session.execute(entry_stmt)

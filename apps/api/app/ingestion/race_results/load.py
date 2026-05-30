from sqlalchemy.dialects.postgresql import insert
from app.models.race_master import Race
from app.models.race_results import RaceResultRaw, RaceResult
from app.models.payouts import Payout

def upsert_race_results(
    session,
    race_records: list[dict],
    raw_records: list[dict],
    result_records: list[dict],
    payout_records: list[dict],
) -> None:
    """競走成績関連テーブルへのUpsert処理"""
    
    # 1. races へのUpsert (競走成績起点)
    if race_records:
        race_stmt = insert(Race).values(race_records)
        race_stmt = race_stmt.on_conflict_do_update(
            index_elements=["race_date", "venue_code", "race_no"],
            set_={
                "raw_result_file_id": race_stmt.excluded.raw_result_file_id,
                "updated_at": race_stmt.excluded.updated_at,
            },
        )
        session.execute(race_stmt)

    # 2. race_result_raw へのUpsert
    if raw_records:
        raw_stmt = insert(RaceResultRaw).values(raw_records)
        raw_stmt = raw_stmt.on_conflict_do_update(
            index_elements=["download_file_id", "line_number"],
            set_={
                "raw_text": raw_stmt.excluded.raw_text,
                "raw_fields": raw_stmt.excluded.raw_fields,
                "parse_status": raw_stmt.excluded.parse_status,
                "parse_error": raw_stmt.excluded.parse_error,
                "parser_version": raw_stmt.excluded.parser_version,
            },
        )
        session.execute(raw_stmt)

    # 3. race_results へのUpsert
    if result_records:
        result_stmt = insert(RaceResult).values(result_records)
        result_stmt = result_stmt.on_conflict_do_update(
            index_elements=["race_id", "boat_no"],
            set_={
                "racer_registration_no": result_stmt.excluded.racer_registration_no,
                "finish_position": result_stmt.excluded.finish_position,
                "entry_course": result_stmt.excluded.entry_course,
                "start_timing": result_stmt.excluded.start_timing,
                "decision": result_stmt.excluded.decision,
                "result_status": result_stmt.excluded.result_status,
                "raw_values": result_stmt.excluded.raw_values,
                "normalized_values": result_stmt.excluded.normalized_values,
            },
        )
        session.execute(result_stmt)
        
    if payout_records:
        payout_stmt = insert(Payout).values(payout_records)
        payout_stmt = payout_stmt.on_conflict_do_update(
            index_elements=["race_id", "bet_type", "combination"],
            set_={
                "payout_yen": payout_stmt.excluded.payout_yen,
            },
        )
        session.execute(payout_stmt)
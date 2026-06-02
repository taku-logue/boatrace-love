from sqlalchemy.dialects.postgresql import insert
from app.models.pre_race_info import PreRaceInfo
from app.models.odds import OddsSnapshot

def upsert_pre_race_info(session, records: list[dict]) -> None:
    """直前情報（展示・気象）をDBへUpsertする"""
    if not records:
        return

    stmt = insert(PreRaceInfo).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["race_id", "boat_no"],
        set_={
            "exhibition_time": stmt.excluded.exhibition_time,
            "tilt_angle": stmt.excluded.tilt_angle,
            "start_exhibition_course": stmt.excluded.start_exhibition_course,
            "start_exhibition_timing": stmt.excluded.start_exhibition_timing,
            "weather": stmt.excluded.weather,
            "temperature": stmt.excluded.temperature,
            "water_temperature": stmt.excluded.water_temperature,
            "wave_height": stmt.excluded.wave_height,
            "wind_direction": stmt.excluded.wind_direction,
            "wind_speed": stmt.excluded.wind_speed,
            "raw_values": stmt.excluded.raw_values,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)
    
def upsert_odds_snapshots(session, records: list[dict]) -> None:
    """オッズスナップショットをDBへUpsertする"""
    if not records:
        return

    stmt = insert(OddsSnapshot).values(records)
    # オッズは「レースID」「券種」「買い目」「取得時刻」の4つで一意になる
    stmt = stmt.on_conflict_do_update(
        index_elements=["race_id", "bet_type", "combination", "fetched_at"],
        set_={
            "odds_value": stmt.excluded.odds_value,
            "raw_values": stmt.excluded.raw_values,
        },
    )
    session.execute(stmt)
from datetime import date


def generate_race_id(race_date: date, venue_code: str, race_no: int) -> str:
    """
    開催日、場コード、レース番号から一意のレースIDを生成する。
    例: 2026-05-30, "23", 1 -> "20260530_23_01"
    """
    date_str = race_date.strftime("%Y%m%d")
    venue_str = str(venue_code).zfill(2)
    race_str = f"{race_no:02d}"
    return f"{date_str}_{venue_str}_{race_str}"

from datetime import date

from app.ingestion.race_id import generate_race_id


def test_generate_race_id_uses_yyyymmdd_venue_and_zero_padded_race_no():
    assert generate_race_id(date(2026, 5, 30), "23", 1) == "20260530_23_01"
    assert generate_race_id(date(2026, 5, 30), "01", 12) == "20260530_01_12"

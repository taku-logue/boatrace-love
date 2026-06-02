from typing import Any

from sqlalchemy.dialects import postgresql

from app.ingestion.race_cards.load import upsert_race_cards
from app.ingestion.race_results.load import upsert_race_results


class RecordingSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(statement)


def compile_postgres_sql(statement: Any) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def test_race_card_raw_upsert_refreshes_raw_file_reference():
    session = RecordingSession()

    upsert_race_cards(
        session,
        [],
        [
            {
                "download_file_id": 1,
                "raw_file_id": 10,
                "line_number": 1,
                "raw_text": "raw card line",
                "raw_fields": {},
                "parse_status": "parsed",
                "parse_error": None,
                "parser_version": "race_cards_v1",
            }
        ],
        [],
    )

    sql = compile_postgres_sql(session.statements[0])

    assert "ON CONFLICT (download_file_id, line_number)" in sql
    assert "raw_file_id = excluded.raw_file_id" in sql


def test_race_result_raw_upsert_refreshes_raw_file_reference():
    session = RecordingSession()

    upsert_race_results(
        session,
        [],
        [
            {
                "download_file_id": 1,
                "raw_file_id": 10,
                "line_number": 1,
                "raw_text": "raw result line",
                "raw_fields": {},
                "parse_status": "parsed",
                "parse_error": None,
                "parser_version": "race_results_v1",
            }
        ],
        [],
        [],
    )

    sql = compile_postgres_sql(session.statements[0])

    assert "ON CONFLICT (download_file_id, line_number)" in sql
    assert "raw_file_id = excluded.raw_file_id" in sql


def test_payout_upsert_refreshes_popularity_and_raw_values():
    session = RecordingSession()

    upsert_race_results(
        session,
        [],
        [],
        [],
        [
            {
                "race_id": "20990101_99_01",
                "bet_type": "trifecta",
                "combination": "1-2-3",
                "payout_yen": 1200,
                "popularity": 5,
                "raw_values": {"source_label": "３連単"},
            }
        ],
    )

    sql = compile_postgres_sql(session.statements[0])

    assert "ON CONFLICT (race_id, bet_type, combination)" in sql
    assert "popularity = excluded.popularity" in sql
    assert "raw_values = excluded.raw_values" in sql

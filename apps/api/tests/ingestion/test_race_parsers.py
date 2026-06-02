from datetime import date

from app.ingestion.race_cards.normalize import normalize_race_card_fields
from app.ingestion.race_cards.parse import parse_race_card_file
from app.ingestion.race_cards.parse import parse_race_card_line
from app.ingestion.race_results.normalize import normalize_race_result_fields
from app.ingestion.race_results.parse import parse_race_result_file


def test_parse_and_normalize_race_card_line():
    line = "1 3811ABCD50EF53A2 6.43 52.71 7.25 62.50 32 46.67 55 40.00"

    parsed = parse_race_card_line(line)
    normalized = normalize_race_card_fields(parsed)

    assert parsed["boat_no"] == "1"
    assert parsed["reg_no"] == "3811"
    assert parsed["racer_class"] == "A2"
    assert normalized["age"] == 50
    assert normalized["weight"] == 53
    assert normalized["national_win_rate"] == 6.43
    assert normalized["motor_2_rate"] == 46.67


def make_result_line(
    *,
    finish_position: str = "01",
    boat_no: str = "1",
    reg_no: str = "3811",
    entry_course: str = "1",
    start_timing: str = "0.04",
) -> str:
    chars = [" "] * 70
    chars[2:4] = list(finish_position.rjust(2))
    chars[6:8] = list(boat_no.rjust(2))
    chars[8:12] = list(reg_no)
    chars[13:21] = list("TEST    ")
    chars[22:24] = list("32")
    chars[26:29] = list(" 55")
    chars[31:35] = list("6.57")
    chars[37:40] = list(entry_course.rjust(3))
    chars[42:47] = list(start_timing.rjust(5))
    chars[52:58] = list("1.49.0")
    return "".join(chars).rstrip()


def test_normalize_race_result_statuses_and_start_timing():
    cases = {
        "F": ("f", None),
        "L": ("l", None),
        "失": ("disqualified", None),
        "欠": ("absent", None),
        "落": ("fall", None),
        "転": ("capsize", None),
        "沈": ("sink", None),
    }
    for raw_status, (expected_status, expected_finish) in cases.items():
        normalized = normalize_race_result_fields(
            {
                "racer_name": "TEST",
                "finish_position": raw_status,
                "entry_course": "1",
                "exhibition_time": "6.70",
                "start_timing": "F.01" if raw_status == "F" else "",
            }
        )
        assert normalized["finish_position"] == expected_finish
        assert normalized["result_status"] == expected_status

    flying = normalize_race_result_fields(
        {
            "racer_name": "TEST",
            "finish_position": "F",
            "entry_course": "1",
            "exhibition_time": "6.70",
            "start_timing": "F.01",
        }
    )
    assert flying["start_timing"] == -0.01


def test_parse_race_card_file_extracts_race_raw_and_entries(tmp_path):
    file_path = tmp_path / "B990101.TXT"
    file_path.write_text(
        "\n".join(
            [
                "23BBGN",
                "  1R",
                "1 3811ABCD50EF53A2 6.43 52.71 7.25 62.50 32 46.67 55 40.00",
            ]
        ),
        encoding="cp932",
    )

    races, raw_rows, entries = parse_race_card_file(
        str(file_path), download_file_id=1, raw_file_id=2, race_date=date(2026, 5, 30)
    )

    assert races[0]["race_id"] == "20260530_23_01"
    assert raw_rows[0]["line_number"] == 3
    assert raw_rows[0]["parser_version"] == "v1.0"
    assert entries[0]["boat_no"] == 1
    assert entries[0]["racer_registration_no"] == "3811"


def test_parse_race_result_file_extracts_results_decision_and_payouts(tmp_path):
    file_path = tmp_path / "K990101.TXT"
    file_path.write_text(
        "\n".join(
            [
                "23KBGN",
                "  1R",
                "着 艇 登番 選手名 ﾚｰｽﾀｲﾑ 逃げ",
                make_result_line(),
                "  1R 1-2-3 1200 1-2-3 320 1-2 450 1-2 200",
                "単勝 1 120",
                "複勝 1 100 2 180",
                "２連単 1-2 450 人気 2",
                "２連複 1-2 200 人気 1",
                "拡連複 1-2 130 人気 1",
                "       1-3 250 人気 4",
                "       2-3 410 人気 7",
                "３連単 1-2-3 1200 人気 5",
                "３連複 1-2-3 320 人気 1",
            ]
        ),
        encoding="cp932",
    )

    races, raw_rows, results, payouts = parse_race_result_file(
        str(file_path), download_file_id=1, raw_file_id=2, race_date=date(2026, 5, 30)
    )

    assert races[0]["race_id"] == "20260530_23_01"
    assert raw_rows[0]["line_number"] == 4
    assert raw_rows[0]["parser_version"] == "v1.1"
    assert results[0]["finish_position"] == 1
    assert results[0]["decision"] == "逃げ"
    payout_keys = {(payout["bet_type"], payout["combination"]): payout for payout in payouts}
    assert set(payout_keys) == {
        ("win", "1"),
        ("place", "1"),
        ("place", "2"),
        ("exacta", "1-2"),
        ("quinella", "1-2"),
        ("quinella_place", "1-2"),
        ("quinella_place", "1-3"),
        ("quinella_place", "2-3"),
        ("trifecta", "1-2-3"),
        ("trio", "1-2-3"),
    }
    assert len(payouts) == len(payout_keys)
    assert payout_keys[("exacta", "1-2")]["popularity"] == 2
    assert payout_keys[("trifecta", "1-2-3")]["popularity"] == 5
    assert payout_keys[("place", "2")]["payout_yen"] == 180

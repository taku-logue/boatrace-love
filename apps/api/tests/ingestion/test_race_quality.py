from datetime import date

from app.ingestion.race_quality import (
    RaceQualityStats,
    evaluate_race_quality_stats,
    format_race_quality_report,
)


def make_stats(**overrides: int) -> RaceQualityStats:
    values = {
        "race_count": 12,
        "race_number_anomalies": 0,
        "venue_day_over_12_races": 0,
        "races_with_entries": 12,
        "races_with_results": 12,
        "races_with_entries_and_results": 12,
        "entry_count_anomalies": 0,
        "result_count_anomalies": 0,
        "duplicate_first_place_races": 0,
        "missing_winner_races": 0,
        "invalid_entry_course_rows": 0,
        "invalid_start_timing_rows": 0,
        "invalid_boat_no_rows": 0,
        "invalid_payout_rows": 0,
        "result_races_without_payouts": 0,
        "raw_parse_error_rows": 0,
    }
    values.update(overrides)
    return RaceQualityStats(**values)


def test_evaluate_race_quality_stats_passes_clean_stats():
    report = evaluate_race_quality_stats(
        make_stats(),
        from_date=date(2026, 5, 30),
        to_date=date(2026, 5, 30),
    )

    assert report.passed
    assert report.issues == []
    assert "issues: none" in format_race_quality_report(report)


def test_evaluate_race_quality_stats_errors_on_structural_anomalies():
    report = evaluate_race_quality_stats(
        make_stats(
            race_number_anomalies=1,
            entry_count_anomalies=2,
            invalid_payout_rows=3,
        ),
        from_date=date(2026, 5, 30),
        to_date=date(2026, 5, 30),
    )

    assert not report.passed
    assert {issue.check_name for issue in report.issues} == {
        "race_number_range",
        "entry_count",
        "payout_values",
    }


def test_evaluate_race_quality_stats_warns_on_low_join_rate():
    report = evaluate_race_quality_stats(
        make_stats(races_with_entries_and_results=10),
        from_date=date(2026, 5, 30),
        to_date=date(2026, 5, 30),
        min_join_rate=0.95,
    )

    assert report.passed
    assert len(report.issues) == 1
    assert report.issues[0].severity == "warning"
    assert report.issues[0].check_name == "card_result_join_rate"

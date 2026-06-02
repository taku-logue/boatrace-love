from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

QualitySeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class RaceQualityIssue:
    check_name: str
    severity: QualitySeverity
    message: str
    count: int


@dataclass(frozen=True)
class RaceQualityMetric:
    name: str
    value: int | float


@dataclass(frozen=True)
class RaceQualityStats:
    race_count: int
    race_number_anomalies: int
    venue_day_over_12_races: int
    races_with_entries: int
    races_with_results: int
    races_with_entries_and_results: int
    entry_count_anomalies: int
    result_count_anomalies: int
    duplicate_first_place_races: int
    missing_winner_races: int
    invalid_entry_course_rows: int
    invalid_start_timing_rows: int
    invalid_boat_no_rows: int
    invalid_payout_rows: int
    result_races_without_payouts: int
    raw_parse_error_rows: int


@dataclass(frozen=True)
class RaceQualityReport:
    from_date: date
    to_date: date
    venue_code: str | None
    metrics: list[RaceQualityMetric]
    issues: list[RaceQualityIssue]

    @property
    def passed(self) -> bool:
        return all(issue.severity != "error" for issue in self.issues)


def _race_filter(alias: str, venue_code: str | None) -> str:
    venue_filter = f" AND {alias}.venue_code = :venue_code" if venue_code else ""
    return f"{alias}.race_date BETWEEN :from_date AND :to_date{venue_filter}"


def _download_filter(alias: str) -> str:
    return f"{alias}.period_term BETWEEN :from_date_iso AND :to_date_iso"


def _base_params(from_date: date, to_date: date, venue_code: str | None) -> dict[str, object]:
    params: dict[str, object] = {
        "from_date": from_date,
        "to_date": to_date,
        "from_date_iso": from_date.isoformat(),
        "to_date_iso": to_date.isoformat(),
    }
    if venue_code:
        params["venue_code"] = venue_code
    return params


def _scalar_int(session: Session, sql: str, params: dict[str, object]) -> int:
    value = session.execute(text(sql), params).scalar_one()
    return int(value or 0)


def collect_race_quality_stats(
    session: Session,
    *,
    from_date: date,
    to_date: date,
    venue_code: str | None = None,
) -> RaceQualityStats:
    params = _base_params(from_date, to_date, venue_code)
    races_where = _race_filter("r", venue_code)
    downloads_where = _download_filter("d")

    race_count = _scalar_int(
        session,
        f"SELECT count(*) FROM races r WHERE {races_where}",
        params,
    )
    race_number_anomalies = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM races r
        WHERE {races_where}
          AND (r.race_no < 1 OR r.race_no > 12)
        """,
        params,
    )
    venue_day_over_12_races = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM (
            SELECT r.race_date, r.venue_code, count(*) AS race_count
            FROM races r
            WHERE {races_where}
            GROUP BY r.race_date, r.venue_code
            HAVING count(*) > 12
        ) AS grouped_races
        """,
        params,
    )
    races_with_entries = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM races r
        WHERE {races_where}
          AND EXISTS (
              SELECT 1 FROM race_entries e WHERE e.race_id = r.race_id
          )
        """,
        params,
    )
    races_with_results = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM races r
        WHERE {races_where}
          AND EXISTS (
              SELECT 1 FROM race_results rr WHERE rr.race_id = r.race_id
          )
        """,
        params,
    )
    races_with_entries_and_results = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM races r
        WHERE {races_where}
          AND EXISTS (
              SELECT 1 FROM race_entries e WHERE e.race_id = r.race_id
          )
          AND EXISTS (
              SELECT 1 FROM race_results rr WHERE rr.race_id = r.race_id
          )
        """,
        params,
    )
    entry_count_anomalies = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM (
            SELECT r.race_id, count(e.id) AS entry_count
            FROM races r
            LEFT JOIN race_entries e ON e.race_id = r.race_id
            WHERE {races_where}
            GROUP BY r.race_id
            HAVING count(e.id) <> 6
        ) AS grouped_entries
        """,
        params,
    )
    result_count_anomalies = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM (
            SELECT rr.race_id, count(rr.id) AS result_count
            FROM race_results rr
            JOIN races r ON r.race_id = rr.race_id
            WHERE {races_where}
            GROUP BY rr.race_id
            HAVING count(rr.id) < 1 OR count(rr.id) > 6
        ) AS grouped_results
        """,
        params,
    )
    duplicate_first_place_races = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM (
            SELECT rr.race_id, count(rr.id) AS first_place_count
            FROM race_results rr
            JOIN races r ON r.race_id = rr.race_id
            WHERE {races_where}
              AND rr.finish_position = 1
            GROUP BY rr.race_id
            HAVING count(rr.id) > 1
        ) AS grouped_first_places
        """,
        params,
    )
    missing_winner_races = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM (
            SELECT rr.race_id
            FROM race_results rr
            JOIN races r ON r.race_id = rr.race_id
            WHERE {races_where}
            GROUP BY rr.race_id
            HAVING sum(CASE WHEN rr.finish_position = 1 THEN 1 ELSE 0 END) = 0
        ) AS grouped_winners
        """,
        params,
    )
    invalid_entry_course_rows = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM race_results rr
        JOIN races r ON r.race_id = rr.race_id
        WHERE {races_where}
          AND rr.entry_course IS NOT NULL
          AND (rr.entry_course < 1 OR rr.entry_course > 6)
        """,
        params,
    )
    invalid_start_timing_rows = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM race_results rr
        JOIN races r ON r.race_id = rr.race_id
        WHERE {races_where}
          AND rr.start_timing IS NOT NULL
          AND (rr.start_timing < -1.0 OR rr.start_timing > 2.0)
        """,
        params,
    )
    invalid_boat_no_rows = _scalar_int(
        session,
        f"""
        SELECT
            (
                SELECT count(*)
                FROM race_entries e
                JOIN races r ON r.race_id = e.race_id
                WHERE {races_where}
                  AND (e.boat_no < 1 OR e.boat_no > 6)
            )
            +
            (
                SELECT count(*)
                FROM race_results rr
                JOIN races r ON r.race_id = rr.race_id
                WHERE {races_where}
                  AND (rr.boat_no < 1 OR rr.boat_no > 6)
            )
        """,
        params,
    )
    invalid_payout_rows = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM payouts p
        JOIN races r ON r.race_id = p.race_id
        WHERE {races_where}
          AND (
              p.payout_yen <= 0
              OR trim(p.bet_type) = ''
              OR trim(p.combination) = ''
              OR (p.popularity IS NOT NULL AND p.popularity <= 0)
          )
        """,
        params,
    )
    result_races_without_payouts = _scalar_int(
        session,
        f"""
        SELECT count(*)
        FROM (
            SELECT rr.race_id, count(p.id) AS payout_count
            FROM race_results rr
            JOIN races r ON r.race_id = rr.race_id
            LEFT JOIN payouts p ON p.race_id = rr.race_id
            WHERE {races_where}
            GROUP BY rr.race_id
            HAVING count(p.id) = 0
        ) AS grouped_payouts
        """,
        params,
    )
    raw_parse_error_rows = _scalar_int(
        session,
        f"""
        SELECT
            (
                SELECT count(*)
                FROM race_card_raw raw
                JOIN download_files d ON d.id = raw.download_file_id
                WHERE {downloads_where}
                  AND d.data_type = 'race_cards'
                  AND raw.parse_status <> 'parsed'
            )
            +
            (
                SELECT count(*)
                FROM race_result_raw raw
                JOIN download_files d ON d.id = raw.download_file_id
                WHERE {downloads_where}
                  AND d.data_type = 'race_results'
                  AND raw.parse_status <> 'parsed'
            )
        """,
        params,
    )

    return RaceQualityStats(
        race_count=race_count,
        race_number_anomalies=race_number_anomalies,
        venue_day_over_12_races=venue_day_over_12_races,
        races_with_entries=races_with_entries,
        races_with_results=races_with_results,
        races_with_entries_and_results=races_with_entries_and_results,
        entry_count_anomalies=entry_count_anomalies,
        result_count_anomalies=result_count_anomalies,
        duplicate_first_place_races=duplicate_first_place_races,
        missing_winner_races=missing_winner_races,
        invalid_entry_course_rows=invalid_entry_course_rows,
        invalid_start_timing_rows=invalid_start_timing_rows,
        invalid_boat_no_rows=invalid_boat_no_rows,
        invalid_payout_rows=invalid_payout_rows,
        result_races_without_payouts=result_races_without_payouts,
        raw_parse_error_rows=raw_parse_error_rows,
    )


def evaluate_race_quality_stats(
    stats: RaceQualityStats,
    *,
    from_date: date,
    to_date: date,
    venue_code: str | None = None,
    min_join_rate: float = 0.95,
) -> RaceQualityReport:
    join_rate = stats.races_with_entries_and_results / stats.race_count if stats.race_count else 0.0
    metrics = [
        RaceQualityMetric("race_count", stats.race_count),
        RaceQualityMetric("races_with_entries", stats.races_with_entries),
        RaceQualityMetric("races_with_results", stats.races_with_results),
        RaceQualityMetric("races_with_entries_and_results", stats.races_with_entries_and_results),
        RaceQualityMetric("card_result_join_rate", round(join_rate, 4)),
    ]

    issues: list[RaceQualityIssue] = []
    if stats.race_count == 0:
        issues.append(
            RaceQualityIssue(
                "race_count",
                "warning",
                "対象期間のracesが0件です",
                stats.race_count,
            )
        )
    if stats.race_number_anomalies:
        issues.append(
            RaceQualityIssue(
                "race_number_range",
                "error",
                "race_noが1から12の範囲外です",
                stats.race_number_anomalies,
            )
        )
    if stats.venue_day_over_12_races:
        issues.append(
            RaceQualityIssue(
                "daily_venue_race_count",
                "error",
                "1日1場で12Rを超える組み合わせがあります",
                stats.venue_day_over_12_races,
            )
        )
    if stats.entry_count_anomalies:
        issues.append(
            RaceQualityIssue(
                "entry_count",
                "error",
                "race_entriesが6艇ではないレースがあります",
                stats.entry_count_anomalies,
            )
        )
    if stats.result_count_anomalies:
        issues.append(
            RaceQualityIssue(
                "result_count",
                "error",
                "race_resultsが1から6件の範囲外のレースがあります",
                stats.result_count_anomalies,
            )
        )
    if stats.race_count and join_rate < min_join_rate:
        issues.append(
            RaceQualityIssue(
                "card_result_join_rate",
                "warning",
                "番組表と結果の結合率がしきい値を下回っています",
                stats.races_with_entries_and_results,
            )
        )
    if stats.duplicate_first_place_races:
        issues.append(
            RaceQualityIssue(
                "duplicate_first_place",
                "error",
                "1着が複数あるレースがあります",
                stats.duplicate_first_place_races,
            )
        )
    if stats.missing_winner_races:
        issues.append(
            RaceQualityIssue(
                "missing_winner",
                "warning",
                "1着が保存されていない結果レースがあります",
                stats.missing_winner_races,
            )
        )
    if stats.invalid_entry_course_rows:
        issues.append(
            RaceQualityIssue(
                "entry_course_range",
                "error",
                "進入コースが1から6の範囲外です",
                stats.invalid_entry_course_rows,
            )
        )
    if stats.invalid_start_timing_rows:
        issues.append(
            RaceQualityIssue(
                "start_timing_range",
                "error",
                "STが想定範囲外です",
                stats.invalid_start_timing_rows,
            )
        )
    if stats.invalid_boat_no_rows:
        issues.append(
            RaceQualityIssue(
                "boat_no_range",
                "error",
                "艇番が1から6の範囲外です",
                stats.invalid_boat_no_rows,
            )
        )
    if stats.invalid_payout_rows:
        issues.append(
            RaceQualityIssue(
                "payout_values",
                "error",
                "払戻の券種、組番、金額、人気に不正値があります",
                stats.invalid_payout_rows,
            )
        )
    if stats.result_races_without_payouts:
        issues.append(
            RaceQualityIssue(
                "missing_payouts",
                "warning",
                "払戻が保存されていない結果レースがあります",
                stats.result_races_without_payouts,
            )
        )
    if stats.raw_parse_error_rows:
        issues.append(
            RaceQualityIssue(
                "raw_parse_status",
                "error",
                "Raw行にparse_status=parsed以外の行があります",
                stats.raw_parse_error_rows,
            )
        )

    return RaceQualityReport(
        from_date=from_date,
        to_date=to_date,
        venue_code=venue_code,
        metrics=metrics,
        issues=issues,
    )


def run_race_quality_checks(
    session: Session,
    *,
    from_date: date,
    to_date: date,
    venue_code: str | None = None,
    min_join_rate: float = 0.95,
) -> RaceQualityReport:
    stats = collect_race_quality_stats(
        session,
        from_date=from_date,
        to_date=to_date,
        venue_code=venue_code,
    )
    return evaluate_race_quality_stats(
        stats,
        from_date=from_date,
        to_date=to_date,
        venue_code=venue_code,
        min_join_rate=min_join_rate,
    )


def format_race_quality_report(report: RaceQualityReport) -> str:
    venue = report.venue_code if report.venue_code else "all"
    lines = [
        "",
        "Phase 3 data quality report",
        f"- period: {report.from_date.isoformat()} to {report.to_date.isoformat()}",
        f"- venue_code: {venue}",
    ]
    for metric in report.metrics:
        lines.append(f"- metric {metric.name}: {metric.value}")

    if not report.issues:
        lines.append("- issues: none")
        return "\n".join(lines)

    lines.append("- issues:")
    for issue in report.issues:
        lines.append(
            "  - [{severity}] {name}: {message} count={count}".format(
                severity=issue.severity,
                name=issue.check_name,
                message=issue.message,
                count=issue.count,
            )
        )
    return "\n".join(lines)

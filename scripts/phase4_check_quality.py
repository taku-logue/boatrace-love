from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_API_PATH = REPO_ROOT / "apps" / "api"
if LOCAL_API_PATH.exists():
    sys.path.append(str(LOCAL_API_PATH))
sys.path.append("/app")

from app.db.session import engine  # noqa: E402


@dataclass
class QualitySummary:
    checked_races: int = 0
    entry_errors: int = 0
    pre_race_errors: int = 0
    weather_errors: int = 0
    odds_errors: int = 0
    fetch_errors: int = 0

    @property
    def passed(self) -> bool:
        return (
            self.entry_errors
            + self.pre_race_errors
            + self.weather_errors
            + self.odds_errors
            + self.fetch_errors
            == 0
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Phase 4 live ingestion data quality.")
    parser.add_argument("--race-date", required=True, help="Race date in YYYY-MM-DD format.")
    return parser.parse_args()


def check_quality(target_date: date) -> QualitySummary:
    summary = QualitySummary()
    date_prefix = target_date.strftime("%Y%m%d")
    print(f"Phase 4 quality check target: {target_date.isoformat()}")

    try:
        with engine.connect() as conn:
            races = conn.execute(
                text(
                    """
                    SELECT race_id
                    FROM races
                    WHERE race_date = :race_date
                    ORDER BY race_id
                    """
                ),
                {"race_date": target_date},
            ).scalars()
            race_ids = list(races)
            print(f"races in database: {len(race_ids)}")

            for race_id in race_ids:
                entry_count = conn.execute(
                    text("SELECT count(*) FROM race_entries WHERE race_id = :race_id"),
                    {"race_id": race_id},
                ).scalar_one()
                if entry_count == 0:
                    continue

                summary.checked_races += 1
                if entry_count != 6:
                    print(f"[entry] {race_id}: expected 6 entries, got {entry_count}")
                    summary.entry_errors += 1

                missing_reg_count = conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM race_entries
                        WHERE race_id = :race_id
                          AND (racer_registration_no IS NULL OR racer_registration_no = '')
                        """
                    ),
                    {"race_id": race_id},
                ).scalar_one()
                if missing_reg_count:
                    print(f"[entry] {race_id}: missing racer_registration_no={missing_reg_count}")
                    summary.entry_errors += int(missing_reg_count)

                pre_race_boat_count = conn.execute(
                    text(
                        """
                        SELECT count(DISTINCT boat_no)
                        FROM pre_race_entry_infos
                        WHERE race_id = :race_id
                        """
                    ),
                    {"race_id": race_id},
                ).scalar_one()
                if pre_race_boat_count not in (0, 6):
                    print(f"[pre_race] {race_id}: expected 0 or 6 boats, got {pre_race_boat_count}")
                    summary.pre_race_errors += 1

                invalid_exhibition_count = conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM pre_race_entry_infos
                        WHERE race_id = :race_id
                          AND exhibition_time IS NOT NULL
                          AND (exhibition_time < 5.0 OR exhibition_time > 9.0)
                        """
                    ),
                    {"race_id": race_id},
                ).scalar_one()
                if invalid_exhibition_count:
                    print(
                        f"[pre_race] {race_id}: invalid exhibition_time={invalid_exhibition_count}"
                    )
                    summary.pre_race_errors += int(invalid_exhibition_count)

                weather_count = conn.execute(
                    text("SELECT count(*) FROM weather_observations WHERE race_id = :race_id"),
                    {"race_id": race_id},
                ).scalar_one()
                if pre_race_boat_count and weather_count == 0:
                    print(f"[weather] {race_id}: weather observation is missing")
                    summary.weather_errors += 1

                odds_entry_count = conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM odds_snapshot_entries
                        WHERE race_id = :race_id
                          AND bet_type = 'win'
                        """
                    ),
                    {"race_id": race_id},
                ).scalar_one()
                if odds_entry_count and odds_entry_count % 6 != 0:
                    print(
                        f"[odds] {race_id}: expected a multiple of 6 win odds, "
                        f"got {odds_entry_count}"
                    )
                    summary.odds_errors += 1

                invalid_odds_count = conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM odds_snapshot_entries
                        WHERE race_id = :race_id
                          AND odds_value IS NOT NULL
                          AND odds_value <= 0
                        """
                    ),
                    {"race_id": race_id},
                ).scalar_one()
                if invalid_odds_count:
                    print(f"[odds] {race_id}: invalid odds_value={invalid_odds_count}")
                    summary.odds_errors += int(invalid_odds_count)

            summary.fetch_errors = int(
                conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM live_fetch_status
                        WHERE race_date = :race_date
                          AND status = 'failed'
                        """
                    ),
                    {"race_date": target_date},
                ).scalar_one()
            )
            if summary.fetch_errors:
                print(f"[fetch] {date_prefix}: failed fetch records={summary.fetch_errors}")
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Phase 4 quality check failed: {exc}") from exc

    print("summary")
    print(f"  checked_races: {summary.checked_races}")
    print(f"  entry_errors: {summary.entry_errors}")
    print(f"  pre_race_errors: {summary.pre_race_errors}")
    print(f"  weather_errors: {summary.weather_errors}")
    print(f"  odds_errors: {summary.odds_errors}")
    print(f"  fetch_errors: {summary.fetch_errors}")
    print("  status: passed" if summary.passed else "  status: failed")
    return summary


def main() -> None:
    args = parse_args()
    summary = check_quality(date.fromisoformat(args.race_date))
    raise SystemExit(0 if summary.passed else 1)


if __name__ == "__main__":
    main()

"""Realign phase4 live snapshot tables.

Revision ID: 6c2f1a91b8e7
Revises: 2401a26dff2a
Create Date: 2026-06-03 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "6c2f1a91b8e7"
down_revision: Union[str, Sequence[str], None] = "2401a26dff2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS live_fetch_status (
            id BIGSERIAL PRIMARY KEY,
            race_date DATE NOT NULL,
            venue_code VARCHAR(2) NOT NULL,
            race_no INTEGER,
            data_kind TEXT NOT NULL,
            source_url TEXT NOT NULL,
            status TEXT NOT NULL,
            raw_file_id BIGINT REFERENCES raw_files(id),
            ingestion_run_id BIGINT REFERENCES ingestion_runs(id),
            fetched_at TIMESTAMPTZ NOT NULL,
            error_message TEXT,
            row_count INTEGER,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_live_fetch_status_race_date
        ON live_fetch_status (race_date)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_live_fetch_status_venue_code
        ON live_fetch_status (venue_code)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS weather_observations (
            race_id VARCHAR NOT NULL REFERENCES races(race_id),
            fetched_at TIMESTAMPTZ NOT NULL,
            weather TEXT,
            temperature NUMERIC,
            wind_direction TEXT,
            wind_speed NUMERIC,
            water_temperature NUMERIC,
            wave_height NUMERIC,
            raw_values JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (race_id, fetched_at)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pre_race_entry_infos (
            race_id VARCHAR NOT NULL REFERENCES races(race_id),
            boat_no INTEGER NOT NULL,
            fetched_at TIMESTAMPTZ NOT NULL,
            exhibition_time NUMERIC,
            tilt_angle NUMERIC,
            start_exhibition_course INTEGER,
            start_exhibition_timing NUMERIC,
            raw_values JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (race_id, boat_no, fetched_at)
        )
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('pre_race_info') IS NOT NULL THEN
                INSERT INTO weather_observations (
                    race_id,
                    fetched_at,
                    weather,
                    temperature,
                    wind_direction,
                    wind_speed,
                    water_temperature,
                    wave_height,
                    raw_values
                )
                SELECT DISTINCT
                    race_id,
                    COALESCE(updated_at, created_at, now()),
                    weather,
                    temperature,
                    wind_direction,
                    wind_speed,
                    water_temperature,
                    wave_height,
                    '{}'::jsonb
                FROM pre_race_info
                ON CONFLICT DO NOTHING;

                INSERT INTO pre_race_entry_infos (
                    race_id,
                    boat_no,
                    fetched_at,
                    exhibition_time,
                    tilt_angle,
                    start_exhibition_course,
                    start_exhibition_timing,
                    raw_values
                )
                SELECT
                    race_id,
                    boat_no,
                    COALESCE(updated_at, created_at, now()),
                    exhibition_time,
                    tilt_angle,
                    start_exhibition_course,
                    start_exhibition_timing,
                    COALESCE(raw_values, '{}'::jsonb)
                FROM pre_race_info
                ON CONFLICT DO NOTHING;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'odds_snapshots'
                  AND column_name = 'combination'
            ) THEN
                ALTER TABLE odds_snapshots RENAME TO odds_snapshots_legacy_2401;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            race_id VARCHAR NOT NULL REFERENCES races(race_id),
            bet_type TEXT NOT NULL,
            fetched_at TIMESTAMPTZ NOT NULL,
            raw_values JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (race_id, bet_type, fetched_at)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS odds_snapshot_entries (
            race_id VARCHAR NOT NULL,
            bet_type TEXT NOT NULL,
            fetched_at TIMESTAMPTZ NOT NULL,
            combination TEXT NOT NULL,
            odds_value NUMERIC,
            raw_values JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (race_id, bet_type, fetched_at, combination),
            FOREIGN KEY (race_id, bet_type, fetched_at)
                REFERENCES odds_snapshots (race_id, bet_type, fetched_at)
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('odds_snapshots_legacy_2401') IS NOT NULL THEN
                INSERT INTO odds_snapshots (race_id, bet_type, fetched_at)
                SELECT DISTINCT race_id, bet_type, fetched_at
                FROM odds_snapshots_legacy_2401
                ON CONFLICT DO NOTHING;

                INSERT INTO odds_snapshot_entries (
                    race_id,
                    bet_type,
                    fetched_at,
                    combination,
                    odds_value,
                    raw_values
                )
                SELECT
                    race_id,
                    bet_type,
                    fetched_at,
                    combination,
                    odds_value,
                    COALESCE(raw_values, '{}'::jsonb)
                FROM odds_snapshots_legacy_2401
                ON CONFLICT DO NOTHING;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS odds_snapshot_entries")
    op.execute("DROP TABLE IF EXISTS odds_snapshots")
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('odds_snapshots_legacy_2401') IS NOT NULL THEN
                ALTER TABLE odds_snapshots_legacy_2401 RENAME TO odds_snapshots;
            END IF;
        END
        $$;
        """
    )
    op.execute("DROP TABLE IF EXISTS pre_race_entry_infos")
    op.execute("DROP TABLE IF EXISTS weather_observations")
    op.execute("DROP TABLE IF EXISTS live_fetch_status")

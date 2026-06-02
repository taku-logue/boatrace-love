"""Repair phase2 raw constraint after phase3 migration cleanup

Revision ID: d5f2f8a0c1e4
Revises: 2aa075ebabae
Create Date: 2026-06-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5f2f8a0c1e4"
down_revision: Union[str, Sequence[str], None] = "2aa075ebabae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_racer_period_stats_raw_file_line'
            ) THEN
                ALTER TABLE racer_period_stats_raw
                ADD CONSTRAINT uq_racer_period_stats_raw_file_line
                UNIQUE (download_file_id, line_number);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # This repair migration restores a Phase 2 invariant. The constraint is owned
    # by the Phase 2 migration, so downgrading this repair should leave it intact.

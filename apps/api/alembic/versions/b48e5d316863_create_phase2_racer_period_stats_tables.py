"""Create phase2 racer period stats tables

Revision ID: b48e5d316863
Revises: fea2050a2b26
Create Date: 2026-05-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b48e5d316863"
down_revision: Union[str, Sequence[str], None] = "fea2050a2b26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "download_files",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("data_type", sa.Text(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_term", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("raw_lzh_file_id", sa.BigInteger(), nullable=True),
        sa.Column("extracted_file_id", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["extracted_file_id"], ["raw_files.id"]),
        sa.ForeignKeyConstraint(["raw_lzh_file_id"], ["raw_files.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "data_type",
            "period_year",
            "period_term",
            "source_url",
            name="uq_download_files_unique_source",
        ),
    )
    op.create_index(op.f("ix_download_files_id"), "download_files", ["id"], unique=False)
    op.create_table(
        "racer_period_stats_raw",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("download_file_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_file_id", sa.BigInteger(), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("raw_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("parse_status", sa.Text(), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["download_file_id"], ["download_files.id"]),
        sa.ForeignKeyConstraint(["raw_file_id"], ["raw_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "download_file_id",
            "line_number",
            name="uq_racer_period_stats_raw_file_line",
        ),
    )
    op.create_index(
        op.f("ix_racer_period_stats_raw_id"),
        "racer_period_stats_raw",
        ["id"],
        unique=False,
    )
    op.create_table(
        "racer_period_stats",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("download_file_id", sa.BigInteger(), nullable=True),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_term", sa.Text(), nullable=False),
        sa.Column("racer_registration_no", sa.Text(), nullable=False),
        sa.Column("racer_name", sa.Text(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.Column("racer_class", sa.Text(), nullable=True),
        sa.Column("raw_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("normalized_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["download_file_id"], ["download_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "period_year",
            "period_term",
            "racer_registration_no",
            name="uq_racer_period_stats_unique_racer",
        ),
    )
    op.create_index(
        op.f("ix_racer_period_stats_id"),
        "racer_period_stats",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_racer_period_stats_id"), table_name="racer_period_stats")
    op.drop_table("racer_period_stats")
    op.drop_index(op.f("ix_racer_period_stats_raw_id"), table_name="racer_period_stats_raw")
    op.drop_table("racer_period_stats_raw")
    op.drop_index(op.f("ix_download_files_id"), table_name="download_files")
    op.drop_table("download_files")

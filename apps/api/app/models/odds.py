from sqlalchemy import Column, DateTime, ForeignKeyConstraint, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .base import Base


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    race_id = Column(String, primary_key=True)
    bet_type = Column(Text, primary_key=True)
    fetched_at = Column(DateTime(timezone=True), primary_key=True)
    raw_values = Column(JSONB, server_default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OddsSnapshotEntry(Base):
    __tablename__ = "odds_snapshot_entries"

    race_id = Column(String, primary_key=True)
    bet_type = Column(Text, primary_key=True)
    fetched_at = Column(DateTime(timezone=True), primary_key=True)
    combination = Column(Text, primary_key=True)
    odds_value = Column(Numeric)
    raw_values = Column(JSONB, server_default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["race_id", "bet_type", "fetched_at"],
            ["odds_snapshots.race_id", "odds_snapshots.bet_type", "odds_snapshots.fetched_at"],
            ondelete="CASCADE",
        ),
    )

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base


class RaceCardRaw(Base):
    __tablename__ = "race_card_raw"
    id = Column(BigInteger, primary_key=True, index=True)
    download_file_id = Column(BigInteger, ForeignKey("download_files.id"))
    raw_file_id = Column(BigInteger, ForeignKey("raw_files.id"))
    line_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    raw_fields = Column(JSONB)
    parse_status = Column(Text, nullable=False)
    parse_error = Column(Text)
    parser_version = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("download_file_id", "line_number", name="uq_race_card_raw_file_line"),
    )


class RaceEntry(Base):
    __tablename__ = "race_entries"
    id = Column(BigInteger, primary_key=True, index=True)
    race_id = Column(String, ForeignKey("races.race_id"), nullable=False)
    boat_no = Column(Integer, nullable=False)
    racer_registration_no = Column(String, nullable=False)
    racer_name = Column(Text)
    racer_class = Column(Text)
    branch = Column(Text)
    motor_no = Column(String)
    boat_no_assigned = Column(String)
    raw_values = Column(JSONB)
    normalized_values = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("race_id", "boat_no", name="uq_race_entries_race_boat"),)

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Numeric,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base


class RaceResultRaw(Base):
    __tablename__ = "race_result_raw"
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
        UniqueConstraint("download_file_id", "line_number", name="uq_race_result_raw_file_line"),
    )


class RaceResult(Base):
    __tablename__ = "race_results"
    id = Column(BigInteger, primary_key=True, index=True)
    race_id = Column(String, ForeignKey("races.race_id"), nullable=False)
    boat_no = Column(Integer, nullable=False)
    racer_registration_no = Column(String, nullable=False)
    finish_position = Column(Integer)
    entry_course = Column(Integer)
    start_timing = Column(Numeric)
    decision = Column(Text)
    result_status = Column(Text)
    raw_values = Column(JSONB)
    normalized_values = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("race_id", "boat_no", name="uq_race_results_race_boat"),)

from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base

class RacerPeriodStatRaw(Base):
    __tablename__ = "racer_period_stats_raw"

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

class RacerPeriodStat(Base):
    __tablename__ = "racer_period_stats"

    id = Column(BigInteger, primary_key=True, index=True)
    download_file_id = Column(BigInteger, ForeignKey("download_files.id"))
    period_year = Column(Integer, nullable=False)
    period_term = Column(Text, nullable=False)
    racer_registration_no = Column(Text, nullable=False)
    racer_name = Column(Text)
    branch = Column(Text)
    racer_class = Column(Text)
    raw_values = Column(JSONB)
    normalized_values = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("period_year", "period_term", "racer_registration_no", name="uq_racer_period_stats_unique_racer"),
    )
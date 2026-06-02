from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .base import Base


class LiveFetchStatus(Base):
    __tablename__ = "live_fetch_status"

    id = Column(BigInteger, primary_key=True, index=True)
    race_date = Column(Date, nullable=False, index=True)
    venue_code = Column(String(2), nullable=False, index=True)
    race_no = Column(Integer)
    data_kind = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    raw_file_id = Column(BigInteger, ForeignKey("raw_files.id"))
    ingestion_run_id = Column(BigInteger, ForeignKey("ingestion_runs.id"))
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    error_message = Column(Text)
    row_count = Column(Integer)
    file_metadata = Column("metadata", JSONB, server_default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    race_id = Column(String, ForeignKey("races.race_id"), primary_key=True)
    fetched_at = Column(DateTime(timezone=True), primary_key=True)
    weather = Column(Text)
    temperature = Column(Numeric)
    wind_direction = Column(Text)
    wind_speed = Column(Numeric)
    water_temperature = Column(Numeric)
    wave_height = Column(Numeric)
    raw_values = Column(JSONB, server_default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PreRaceEntryInfo(Base):
    __tablename__ = "pre_race_entry_infos"

    race_id = Column(String, ForeignKey("races.race_id"), primary_key=True)
    boat_no = Column(Integer, primary_key=True)
    fetched_at = Column(DateTime(timezone=True), primary_key=True)
    exhibition_time = Column(Numeric)
    tilt_angle = Column(Numeric)
    start_exhibition_course = Column(Integer)
    start_exhibition_timing = Column(Numeric)
    raw_values = Column(JSONB, server_default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

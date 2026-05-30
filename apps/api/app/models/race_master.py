from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base

class Venue(Base):
    __tablename__ = "venues"
    venue_code = Column(String(2), primary_key=True, index=True)
    venue_name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Race(Base):
    __tablename__ = "races"
    id = Column(BigInteger, primary_key=True, index=True)
    race_id = Column(String, unique=True, nullable=False, index=True)
    race_date = Column(Date, nullable=False)
    venue_code = Column(String(2), nullable=False)
    race_no = Column(Integer, nullable=False)
    race_name = Column(Text)
    grade = Column(Text)
    distance_m = Column(Integer)
    deadline_at = Column(DateTime(timezone=True))
    raw_card_file_id = Column(BigInteger)
    raw_result_file_id = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('race_date', 'venue_code', 'race_no', name='uq_races_date_venue_no'),
    )
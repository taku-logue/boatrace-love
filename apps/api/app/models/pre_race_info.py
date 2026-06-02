from sqlalchemy import Column, BigInteger, Integer, String, Text, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base

class PreRaceInfo(Base):
    """レース直前情報（展示タイム・チルト・部品交換・気象など）"""
    __tablename__ = "pre_race_info"
    id = Column(BigInteger, primary_key=True, index=True)
    race_id = Column(String, ForeignKey("races.race_id"), nullable=False, index=True)
    boat_no = Column(Integer, nullable=False)
    
    # 展示情報
    exhibition_time = Column(Numeric)
    tilt_angle = Column(Numeric)
    start_exhibition_course = Column(Integer)
    start_exhibition_timing = Column(Numeric)
    
    # 気象・水面情報 (レース単位だが便宜上ここに持たせるか、後で分離)
    weather = Column(Text)
    temperature = Column(Numeric)
    water_temperature = Column(Numeric)
    wave_height = Column(Integer)
    wind_direction = Column(Text)
    wind_speed = Column(Integer)
    
    raw_values = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('race_id', 'boat_no', name='uq_pre_race_info_race_boat'),
    )
from sqlalchemy import Column, BigInteger, Integer, String, Text, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base

class OddsSnapshot(Base):
    """オッズの時系列スナップショット"""
    __tablename__ = "odds_snapshots"
    id = Column(BigInteger, primary_key=True, index=True)
    race_id = Column(String, ForeignKey("races.race_id"), nullable=False, index=True)
    bet_type = Column(Text, nullable=False) # 例: "win" (単勝), "trifecta" (3連単)
    combination = Column(Text, nullable=False) # 例: "1", "1-2-3"
    odds_value = Column(Numeric, nullable=False)
    
    # オッズは変動するため「いつ取得したか」が重要
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    
    raw_values = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # 同じ時間に取得した同じレース・同じ買い目のオッズは一意
        UniqueConstraint('race_id', 'bet_type', 'combination', 'fetched_at', name='uq_odds_snapshots_race_bet_comb_time'),
    )
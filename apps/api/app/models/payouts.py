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


class Payout(Base):
    __tablename__ = "payouts"
    id = Column(BigInteger, primary_key=True, index=True)
    race_id = Column(String, ForeignKey("races.race_id"), nullable=False)
    bet_type = Column(Text, nullable=False)
    combination = Column(Text, nullable=False)
    payout_yen = Column(Integer, nullable=False)
    popularity = Column(Integer)
    raw_values = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("race_id", "bet_type", "combination", name="uq_payouts_race_bet_comb"),
    )

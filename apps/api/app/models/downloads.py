from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base

class DownloadFile(Base):
    __tablename__ = "download_files"

    id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"))
    data_type = Column(Text, nullable=False)
    period_year = Column(Integer, nullable=False)
    period_term = Column(Text, nullable=False)
    display_name = Column(Text)
    source_url = Column(Text, nullable=False)
    source_filename = Column(Text)
    status = Column(Text, nullable=False)
    raw_lzh_file_id = Column(BigInteger, ForeignKey("raw_files.id"))
    extracted_file_id = Column(BigInteger, ForeignKey("raw_files.id"))
    sha256 = Column(Text)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    error_message = Column(Text)

    __table_args__ = (
        UniqueConstraint("data_type", "period_year", "period_term", "source_url", name="uq_download_files_unique_source"),
    )
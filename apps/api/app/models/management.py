from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    base_url = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"))
    job_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    error_message = Column(Text)


class RawFile(Base):
    __tablename__ = "raw_files"
    id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"))
    ingestion_run_id = Column(BigInteger, ForeignKey("ingestion_runs.id"))
    file_type = Column(String, nullable=False)
    source_url = Column(Text)
    local_path = Column(Text, nullable=False)
    sha256 = Column(String)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # SQLAlchemyのBaseが持つ予約語'metadata'と衝突しないよう変数名をfile_metadataにしています
    file_metadata = Column("metadata", JSONB, server_default="{}", nullable=False)

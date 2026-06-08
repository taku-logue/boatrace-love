from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL if settings.DATABASE_URL else "sqlite+pysqlite:///:memory:"
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 戻り値の型 `-> bool` を追加
def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


_settings = get_settings()

engine = create_engine(_settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Provide a transactional scope around a series of operations.

    Yields:
        sqlalchemy.orm.Session: Database session for request scope.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

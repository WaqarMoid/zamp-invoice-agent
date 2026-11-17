import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

is_sqlite = db_url.startswith("sqlite")

connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if is_sqlite:
    connect_args["check_same_thread"] = False
    # Ensure local directory for sqlite file exists
    if "///" in db_url:
        sqlite_path = db_url.split("///")[-1]
        db_dir = os.path.dirname(sqlite_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
else:
    engine_kwargs["pool_size"] = 5

engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    if is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

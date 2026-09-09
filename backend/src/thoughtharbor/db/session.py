"""SQLAlchemy engine and request-scoped session dependencies."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://thoughtharbor:thoughtharbor@localhost:5432/thoughtharbor",
    )


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """Yield one SQLAlchemy session for the lifetime of an API request."""

    with SessionFactory() as session:
        yield session

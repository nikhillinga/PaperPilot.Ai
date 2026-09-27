"""
db.py — Database engine configuration and session provider for PaperPilot.

Initializes SQLModel tables and yields session dependencies for FastAPI endpoints.
"""

from __future__ import annotations

from typing import Generator
from sqlmodel import Session, SQLModel, create_engine

try:
    from app import config, models
except ImportError:
    import config, models

connect_args = {"check_same_thread": False} if "sqlite" in str(config.DATABASE_URL) else {}
engine = create_engine(config.DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Create all registered SQLModel tables in the database."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an active database session."""
    with Session(engine) as session:
        yield session

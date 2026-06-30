import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"

from rinsehq.config import get_settings  # noqa: E402
from rinsehq.infrastructure.db import session as db_session  # noqa: E402
from rinsehq.infrastructure.db.base import Base  # noqa: E402
from rinsehq.infrastructure.db import models  # noqa: F401, E402
from rinsehq.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db_session._engine = engine
    db_session._SessionLocal = test_session_factory

    yield

    Base.metadata.drop_all(bind=engine)
    db_session._engine = None
    db_session._SessionLocal = None


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = db_session.get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_tables(db: Session) -> Generator[None, None, None]:
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    yield

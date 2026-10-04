"""Pytest configuration that never connects to the normal demo database."""

import os
import sys
from pathlib import Path

import psycopg2
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres@127.0.0.1:5432/anvaya_test",
)
test_url = make_url(TEST_DATABASE_URL)
if not test_url.database or not test_url.database.endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must target a database whose name ends in '_test'.")

# This must happen before importing application settings/database bindings.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.api.deps import get_db
from app.core.database import SessionLocal, engine
from app.core.security import create_access_token
from app.main import app
from app.models.identity import User
from seed.seeder import seed_database


def _ensure_test_database() -> None:
    admin_url = test_url.set(database="postgres")
    connection = psycopg2.connect(
        host=admin_url.host or "127.0.0.1",
        port=admin_url.port or 5432,
        user=admin_url.username or "postgres",
        password=admin_url.password,
        dbname="postgres",
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (test_url.database,))
            if not cursor.fetchone():
                cursor.execute(f'CREATE DATABASE "{test_url.database}"')
    finally:
        connection.close()


def _alembic_config() -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """Create/reset only anvaya_test, migrate it, and seed it once per suite."""
    _ensure_test_database()
    config = _alembic_config()
    command.upgrade(config, "head")
    session = SessionLocal()
    has_seed_data = session.query(User.id).first() is not None
    session.close()
    if has_seed_data:
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    seed_database()
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def rollback_each_test():
    """Each request uses a connection whose changes are rolled back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    testing_session = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = testing_session()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(active_session, transaction_ended):
        if transaction_ended.nested and not transaction_ended._parent.nested:
            active_session.begin_nested()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _headers_for(email: str, db_session):
    user = db_session.query(User).filter(User.email == email).first()
    assert user, f"Expected seeded test user {email}."
    token = create_access_token(subject=user.id, extra_claims={"role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(db_session):
    return _headers_for("admin@anvaya.demo", db_session)


@pytest.fixture
def doctor_headers(db_session):
    return _headers_for("drsharma@anvaya.demo", db_session)


@pytest.fixture
def nurse_headers(db_session):
    return _headers_for("nursepriya@anvaya.demo", db_session)


@pytest.fixture
def reception_headers(db_session):
    return _headers_for("reception@anvaya.demo", db_session)

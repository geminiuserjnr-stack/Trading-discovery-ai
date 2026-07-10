import os
import pytest
from sqlalchemy import create_engine

# Set test database URL before any other imports to override Pydantic Settings
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:5432/trading_discovery_test"

from backend.app.config.settings import settings
from backend.app.database.base import Base

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Setup test database schema
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Optionally drop after session completes
    Base.metadata.drop_all(bind=engine)

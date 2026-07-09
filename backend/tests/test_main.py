import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import settings
from backend.app.database.base import Base
from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.services.scheduler.celery_app import celery_app

# Enable eager mode in tests to isolate from actual Celery worker running requirements
celery_app.conf.update(task_always_eager=True)

# Use test-specific/local database
engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Make sure tables exist for testing (if any missing)
    Base.metadata.create_all(bind=engine)
    yield
    # We can choose to keep the tables as they are or drop them
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def override_db(db_session):
    def _get_db_override():
        yield db_session
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "unhealthy")
    assert "database" in data
    assert "redis" in data
    assert "celery" in data


def test_stats_endpoint():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_channels" in data
    assert "total_videos" in data
    assert "german_channels" in data
    assert "processed_videos" in data
    assert "extracted_phrases" in data
    assert "generated_queries" in data
    assert "duplicate_rate" in data
    assert "success_rate" in data
    assert "api_quota" in data
    assert "scheduler_status" in data
    assert "latest_discoveries" in data


def test_queries_endpoint():
    response = client.get("/queries")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_channels_endpoint():
    response = client.get("/channels")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_videos_endpoint():
    response = client.get("/videos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_phrases_endpoint():
    response = client.get("/phrases")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_crawl_endpoint():
    payload = {"query_text": "german trading", "max_results": 10}
    response = client.post("/crawl", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "job_id" in data


def test_search_endpoint():
    payload = {"query_text": "Aktien", "max_results": 5}
    response = client.post("/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "results_found" in data


def test_scheduler_run_endpoint():
    response = client.post("/scheduler/run?job_name=run_search_queue")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "run_search_queue" in data["message"]


def test_scheduler_run_all_triggers():
    # Test remaining manual triggers (including cleanup_old_logs & update_statistics)
    for job in ["refresh_active_channels", "generate_search_queries", "recalculate_rankings", "cleanup_old_logs", "update_statistics"]:
        response = client.post(f"/scheduler/run?job_name={job}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert job in data["message"]


def test_scheduler_run_invalid_job():
    response = client.post("/scheduler/run?job_name=invalid_job")
    assert response.status_code == 400


def test_generator_run_endpoint():
    response = client.post("/generator/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

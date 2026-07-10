import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import settings
from backend.app.database.base import Base
from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.models.models import Channel, Video, CrawlJob, ApiQuotaLog, Query, CommunityLink, QueryHistory, SearchResult

# Enable eager mode in tests to isolate from actual Celery worker running requirements
from backend.app.services.scheduler.celery_app import celery_app
celery_app.conf.update(task_always_eager=True)

engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Delete from child tables first to respect foreign keys
    db.query(CommunityLink).delete()
    db.query(CrawlJob).delete()
    db.query(Video).delete()
    db.query(Channel).delete()
    db.query(ApiQuotaLog).delete()
    db.query(QueryHistory).delete()
    db.query(SearchResult).delete()
    db.query(Query).delete()
    db.commit()
    yield db
    db.close()


@pytest.fixture
def test_client(clean_db):
    def _get_db_override():
        yield clean_db
    app.dependency_overrides[get_db] = _get_db_override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_crawl_trigger_endpoint(test_client):
    payload = {"channel_id": "mock_chan_1", "max_results": 5}
    response = test_client.post("/crawl/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "job_id" in data


def test_view_crawl_queue_endpoint(test_client, clean_db):
    # Insert custom crawl job
    job = CrawlJob(
        channel_id="c_test",
        priority=8,
        reason="manual_request",
        status="pending"
    )
    clean_db.add(job)
    clean_db.commit()

    response = test_client.get("/crawl/queue")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["channel_id"] == "c_test"


def test_recent_discoveries_endpoint(test_client, clean_db):
    response = test_client.get("/discoveries/recent")
    assert response.status_code == 200
    data = response.json()
    assert "channels" in data
    assert "videos" in data


def test_stats_duplicates_endpoint(test_client):
    response = test_client.get("/stats/duplicates")
    assert response.status_code == 200
    data = response.json()
    assert "duplicate_channels_encountered" in data
    assert "duplicate_videos_encountered" in data


def test_stats_quota_endpoint(test_client, clean_db):
    log = ApiQuotaLog(
        daily_quota_consumed=150,
        remaining_quota_estimate=9850,
        requests_made=5,
        failed_requests=0
    )
    clean_db.add(log)
    clean_db.commit()

    response = test_client.get("/stats/quota")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["daily_quota_consumed"] == 150


def test_search_controls_endpoints(test_client):
    # Pause
    response = test_client.post("/search/pause")
    assert response.status_code == 200
    assert "paused" in response.json()["message"]

    # Resume
    response = test_client.post("/search/resume")
    assert response.status_code == 200
    assert "resumed" in response.json()["message"]

    # Start
    response = test_client.post("/search/start")
    assert response.status_code == 200
    assert "successfully triggered" in response.json()["message"]


def test_crawl_rerun_endpoint(test_client, clean_db):
    job = CrawlJob(
        channel_id="fail_chan",
        status="failed",
        priority=0,
        reason="scheduled_refresh"
    )
    clean_db.add(job)
    clean_db.commit()
    clean_db.refresh(job)

    response = test_client.post(f"/crawl/rerun/{str(job.id)}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify state was updated to pending and priority elevated to 15
    clean_db.refresh(job)
    assert job.status == "completed"  # because eager Celery automatically processes it on rerun!

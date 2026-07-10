import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import settings
from backend.app.database.base import Base
from backend.app.models.models import Channel, Video, CrawlJob, CommunityLink
from backend.app.services.crawler.crawl_worker import (
    get_channel_refresh_interval_days,
    schedule_channel_refreshes,
    process_channel_crawl_job,
)

engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from backend.app.models.models import Transcript

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.query(CommunityLink).delete()
    db.query(CrawlJob).delete()
    db.query(Transcript).delete()
    db.query(Video).delete()
    db.query(Channel).delete()
    db.commit()
    yield db
    db.close()


def test_get_channel_refresh_interval_days():
    # New channel (no last crawled)
    c1 = Channel(channel_id="c1", channel_name="New", last_crawled=None)
    assert get_channel_refresh_interval_days(c1) == 0

    # High quality active channel (German + trading)
    c2 = Channel(
        channel_id="c2",
        channel_name="Pro Trading",
        last_crawled=datetime.utcnow() - timedelta(days=2),
        is_german=True,
        is_trading=True,
        needs_manual_review=False
    )
    assert get_channel_refresh_interval_days(c2) == 1


def test_schedule_channel_refreshes(clean_db):
    # Setup standard channel that is overdue for a refresh
    c = Channel(
        channel_id="mock_chan_1",
        channel_name="Overdue German Trading",
        active=True,
        last_crawled=datetime.utcnow() - timedelta(days=5),
        is_german=True,
        is_trading=True,
        needs_manual_review=False
    )
    clean_db.add(c)
    clean_db.commit()

    created_count = schedule_channel_refreshes(clean_db)
    assert created_count == 1

    jobs = clean_db.query(CrawlJob).all()
    assert len(jobs) == 1
    assert jobs[0].channel_id == "mock_chan_1"


def test_process_channel_crawl_job(clean_db):
    # Insert crawl job
    job = CrawlJob(
        channel_id="mock_chan_1",
        reason="new_discovery",
        status="pending"
    )
    clean_db.add(job)
    clean_db.commit()

    success = process_channel_crawl_job(clean_db, job)
    assert success is True

    # Refresh objects from DB
    updated_job = clean_db.query(CrawlJob).filter(CrawlJob.id == job.id).one()
    assert updated_job.status == "completed"

    channel = clean_db.query(Channel).filter(Channel.channel_id == "mock_chan_1").one()
    assert channel.channel_name == "German Trader Elite"
    assert channel.is_german is True

    # Check community links recorded
    links = clean_db.query(CommunityLink).all()
    assert len(links) > 0
    assert any(lk.platform == "discord" for lk in links)

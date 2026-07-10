import os
# Set test database URL before any imports to prevent import-time connection errors
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:5432/trading_discovery_test"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import settings
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.models.models import (
    Query, SearchResult, Channel, Video, CrawlJob,
    CommunityLink, QueryHistory, Transcript, VideoPhrase, PhraseRelationship
)
import backend.app.services.crawler.search_scheduler as ss


@pytest.fixture(scope="module")
def db_engine():
    return create_engine("postgresql://postgres:postgres@127.0.0.1:5432/trading_discovery_test")


@pytest.fixture(scope="module")
def SessionLocalClass(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture(autouse=True)
def clean_db(db_engine, SessionLocalClass):
    # Patch the search_scheduler's SessionLocal to use our test sessionmaker!
    original_session_local = ss.SessionLocal
    ss.SessionLocal = SessionLocalClass

    Base.metadata.create_all(bind=db_engine)
    db = SessionLocalClass()
    # clean out target child tables first in proper dependency order
    db.query(CommunityLink).delete()
    db.query(QueryHistory).delete()
    db.query(CrawlJob).delete()
    db.query(Transcript).delete()
    db.query(VideoPhrase).delete()
    db.query(PhraseRelationship).delete()
    db.query(Video).delete()
    db.query(Channel).delete()
    db.query(SearchResult).delete()
    db.query(Query).delete()
    db.commit()

    yield db

    db.close()
    # Restore original SessionLocal
    ss.SessionLocal = original_session_local


def test_populate_seed_queries(clean_db):
    ss.populate_seed_queries()
    # Check that they exist
    queries = clean_db.query(Query).all()
    assert len(queries) > 0
    assert any(q.query_text == "aktien trading" for q in queries)


def test_execute_next_search(clean_db):
    # Running search automatically seeds and searches
    res = ss.execute_next_search(clean_db)
    assert res is not None
    assert "query_text" in res
    assert "new_channels" in res

    # Verify things were written to DB
    channels = clean_db.query(Channel).all()
    videos = clean_db.query(Video).all()
    results = clean_db.query(SearchResult).all()
    jobs = clean_db.query(CrawlJob).all()

    assert len(channels) > 0
    assert len(videos) > 0
    assert len(results) > 0
    assert len(jobs) > 0

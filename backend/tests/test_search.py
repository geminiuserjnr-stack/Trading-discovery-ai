import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import settings
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.models.models import Query, SearchResult, Channel, Video, CrawlJob, CommunityLink, QueryHistory
from backend.app.services.crawler.search_scheduler import populate_seed_queries, execute_next_search

engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # clean out target child tables first
    db.query(CommunityLink).delete()
    db.query(QueryHistory).delete()
    db.query(CrawlJob).delete()
    db.query(Video).delete()
    db.query(Channel).delete()
    db.query(SearchResult).delete()
    db.query(Query).delete()
    db.commit()
    yield db
    db.close()


def test_populate_seed_queries(clean_db):
    populate_seed_queries()
    # Check that they exist
    queries = clean_db.query(Query).all()
    assert len(queries) > 0
    assert any(q.query_text == "aktien trading" for q in queries)


def test_execute_next_search(clean_db):
    # Running search automatically seeds and searches
    res = execute_next_search(clean_db)
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

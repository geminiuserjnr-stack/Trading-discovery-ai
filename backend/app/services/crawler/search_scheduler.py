import json
import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal
from backend.app.models.models import Query, SearchResult, CrawlJob, Channel, Video, QueryHistory
from backend.app.services.youtube.youtube_service import YouTubeService
from backend.app.workers.discovery_worker import run_discovery_cycle
from backend.app.services.logging.logger import sys_logger


SEED_QUERIES = [
    "aktien trading",
    "daytrading dax",
    "krypto trading deutsch",
    "börse für anfänger",
    "forex trading de",
    "dividenden investieren",
    "skalping trading dax",
]


def populate_seed_queries():
    """Seed the database with initial German trading queries to bootstrap discovery."""
    db = SessionLocal()
    try:
        sys_logger.info("Checking and seeding initial search queries...")
        for query_text in SEED_QUERIES:
            existing = db.query(Query).filter(Query.query_text == query_text).first()
            if not existing:
                q = Query(
                    query_text=query_text,
                    language="de",
                    status="active"
                )
                db.add(q)
        db.commit()
        sys_logger.info("Seed queries checking completed.")
    except Exception as e:
        sys_logger.error(f"Failed to populate seed queries: {e}")
        db.rollback()
    finally:
        db.close()


def store_search_result(db: Session, query_id: Optional[str], video_ids: List[str], channel_ids: List[str], next_page_token: Optional[str], status: str) -> SearchResult:
    """Store the full search results tracking metadata to the search_results table (Module 4)."""
    search_res = SearchResult(
        query_id=query_id,
        search_timestamp=datetime.datetime.utcnow(),
        returned_video_ids=",".join(video_ids),
        returned_channel_ids=",".join(channel_ids),
        next_page_token=next_page_token,
        api_response_status=status
    )
    db.add(search_res)
    db.commit()
    return search_res


def execute_next_search(db: Session) -> Optional[dict]:
    """
    Selects the next active query and performs channel-centric discovery.
    Refactored in Phase 2 to use run_discovery_cycle.
    """
    populate_seed_queries()
    try:
        run_discovery_cycle()
        return {"status": "success"}
    except Exception as e:
        sys_logger.error(f"Search execution failed: {e}")
        return None

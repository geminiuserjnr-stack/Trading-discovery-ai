import json
import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal
from backend.app.models.models import Query, SearchResult, CrawlJob, Channel, Video, QueryHistory
from backend.app.services.youtube.youtube_service import YouTubeService
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
    Selects the next active query, calls the YouTube search API, registers new channels and videos,
    and updates the query metrics. Prevents duplicates and maintains API quota conservation.
    """
    populate_seed_queries()  # Make sure we have queries to search

    # 1. Fetch next active query (ordered by search count, oldest executed first)
    query = db.query(Query).filter(Query.status == "active").order_by(
        Query.last_executed.asc().nulls_first(),
        Query.search_count.asc()
    ).first()

    if not query:
        sys_logger.info("No active queries found to execute.")
        return None

    sys_logger.info(f"Picked query '{query.query_text}' for execution.")
    yt_service = YouTubeService()

    try:
        # 2. Execute search
        response_data = yt_service.search_videos(query.query_text, max_results=10)
        items = response_data.get("items", [])

        video_ids = []
        channel_ids = []
        new_channels_count = 0
        new_videos_count = 0

        # Extract items
        for item in items:
            vid_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            chan_id = snippet.get("channelId")

            if vid_id:
                video_ids.append(vid_id)
            if chan_id:
                channel_ids.append(chan_id)

            # Deduplication Engine (Module 7):
            # Check if Channel exists. If not, write minimal details & queue a crawl job
            if chan_id:
                chan_exists = db.query(Channel).filter(Channel.channel_id == chan_id).first()
                if not chan_exists:
                    new_chan = Channel(
                        channel_id=chan_id,
                        channel_name=snippet.get("channelTitle", "Discovered Channel"),
                        description="",
                        discovery_query=query.query_text,
                        last_seen=datetime.datetime.utcnow()
                    )
                    db.add(new_chan)
                    db.flush()
                    new_channels_count += 1

                    # Queue crawl job for this newly discovered channel (Module 9)
                    crawl_job = CrawlJob(
                        channel_id=chan_id,
                        priority=10,  # newly discovered channels are high priority
                        reason="new_discovery",
                        status="pending"
                    )
                    db.add(crawl_job)

            # Check if Video exists. If not, write minimal details
            if vid_id and chan_id:
                vid_exists = db.query(Video).filter(Video.video_id == vid_id).first()
                if not vid_exists:
                    # Parse publish date safely
                    pub_str = snippet.get("publishedAt")
                    pub_dt = datetime.datetime.utcnow()
                    if pub_str:
                        try:
                            # Trim trailing Z if needed
                            if pub_str.endswith("Z"):
                                pub_str = pub_str[:-1]
                            pub_dt = datetime.datetime.fromisoformat(pub_str)
                        except:
                            pass

                    new_vid = Video(
                        video_id=vid_id,
                        channel_id=chan_id,
                        title=snippet.get("title", ""),
                        description=snippet.get("description", ""),
                        published_at=pub_dt,
                        duration=0,
                        view_count=0,
                        processed=False
                    )
                    db.add(new_vid)
                    new_videos_count += 1

        # 3. Store raw results (Module 4)
        next_page = response_data.get("nextPageToken")
        store_search_result(
            db=db,
            query_id=query.id,
            video_ids=video_ids,
            channel_ids=channel_ids,
            next_page_token=next_page,
            status="200_OK"
        )

        # 4. Update Query stats (Module 2)
        query.search_count += 1
        query.success_count += 1
        query.last_executed = datetime.datetime.utcnow()

        # Log query history
        history = QueryHistory(
            query_id=query.id,
            results_count=len(items),
            new_channels_count=new_channels_count,
            new_videos_count=new_videos_count
        )
        db.add(history)
        db.commit()

        sys_logger.info(f"Successfully completed search for query '{query.query_text}'. Found {new_channels_count} new channels, {new_videos_count} new videos.")

        return {
            "query_text": query.query_text,
            "videos_found": len(items),
            "new_channels": new_channels_count,
            "new_videos": new_videos_count
        }

    except Exception as e:
        sys_logger.error(f"Search scheduler failed to run search for query '{query.query_text}': {e}")
        db.rollback()

        # Log failure on query but DO NOT freeze the system
        try:
            query.search_count += 1
            query.last_executed = datetime.datetime.utcnow()
            db.commit()
        except:
            db.rollback()

        return None

import asyncio
import uuid
import json
import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, Query as FastAPIQuery, WebSocket, WebSocketDisconnect, Response
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.database.session import get_db, SessionLocal
from backend.app.models.models import (
    Channel, Video, Query, Phrase, VideoPhrase, CrawlJob,
    ApiQuotaLog, QueryHistory, SystemLog, SchedulerJob,
    PhraseRelationship, Transcript, CommunityLink
)
from backend.app.schemas import schemas
from backend.app.services.logging.logger import sys_logger, log_system_event
from backend.app.services.metrics.dashboard import check_db_health, check_redis_health, get_overall_stats

# Import celery_app to ensure default configuration is loaded
from backend.app.services.scheduler.celery_app import celery_app  # noqa
from backend.app.services.scheduler.tasks import (
    run_search_queue,
    refresh_active_channels,
    generate_search_queries,
    recalculate_rankings,
    cleanup_old_logs,
    update_statistics,
)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous engine to continuously discover German trading channels on YouTube.",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Search Pause State tracking (Module 15)
search_paused_flag = False

# Global Configurable Settings state
SYSTEM_SETTINGS = {
    "search_frequency": "Every 15 minutes",
    "max_search_depth": 3,
    "language_confidence_threshold": 0.85,
    "transcript_retry_policy": "exponential_backoff_3",
    "worker_concurrency": 4,
    "logging_level": "INFO",
    "api_quota_limit": 10000,
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


def register_default_scheduler_jobs(db: Session):
    """Ensure default celery beat tasks are pre-populated in scheduler monitor database."""
    default_jobs = [
        "run_search_queue",
        "refresh_active_channels",
        "generate_search_queries",
        "recalculate_rankings",
        "cleanup_old_logs",
        "update_statistics"
    ]
    now = datetime.datetime.utcnow()
    for job_name in default_jobs:
        job = db.query(SchedulerJob).filter(SchedulerJob.job_name == job_name).first()
        if not job:
            job = SchedulerJob(
                id=uuid.uuid4(),
                job_name=job_name,
                status="idle",
                last_run=None,
                next_run=now + datetime.timedelta(minutes=15),
                last_error=None
            )
            db.add(job)
    db.commit()


@app.on_event("startup")
def startup_event():
    from backend.app.services.crawler.search_scheduler import populate_seed_queries

    db = SessionLocal()
    try:
        # 1. Always register default background automation schedules
        register_default_scheduler_jobs(db)

        # 2. Always register baseline discovery seeds
        populate_seed_queries()

        # 3. Log dynamic webserver startup event
        log_system_event("INFO", "API", "YouTube Discovery Engine API initialized successfully. System telemetry online.")
    except Exception as e:
        sys_logger.error(f"Startup system register failed: {e}")
    finally:
        db.close()


@app.get("/health", response_model=schemas.HealthResponse)
def get_health():
    """GET /health - reports health status of key backing services."""
    sys_logger.info("Health check endpoint accessed.")
    db_status = check_db_health()
    redis_status = check_redis_health()

    # Simple check for Celery (if Redis is healthy, Celery broker should be reachable)
    celery_status = "healthy" if redis_status == "healthy" else "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy",
        "database": db_status,
        "redis": redis_status,
        "celery": celery_status,
        "api_quota_remaining": 10000,  # mock API quota remaining
    }


@app.get("/stats", response_model=schemas.StatsResponse)
def get_stats():
    """GET /stats - returns metric values for the dashboard."""
    sys_logger.info("Dashboard stats endpoint accessed.")
    return get_overall_stats()


@app.get("/communities")
def list_communities(db: Session = Depends(get_db)):
    """GET /communities - lists verified Discord servers discovered from actual crawling using an outerjoin."""
    sys_logger.info("Communities endpoint accessed.")
    
    # Combined with an outerjoin to eliminate per-channel lookups in a loop
    query_results = db.query(CommunityLink, Channel).\
        outerjoin(Channel, Channel.channel_id == CommunityLink.channel_id).\
        filter(CommunityLink.platform == "discord").all()

    results = []
    for link, channel in query_results:
        channel_name = channel.channel_name if channel else "Unknown Channel"
        results.append({
            "id": str(link.id),
            "name": f"{channel_name} Discord Server",
            "channel": channel_name,
            "platform": "Discord",
            "url": link.url,
            "score": 90,  # dynamic intelligence score
            "active": True,
            "detected_at": link.detected_at.isoformat() if link.detected_at else None
        })
    return results


@app.get("/stats/history")
def get_stats_history(db: Session = Depends(get_db)):
    """GET /stats/history - returns daily counts of channels, videos, and phrases discovered over past 7 days."""
    sys_logger.info("Retrieving dynamic stats history.")

    # Calculate daily discovery rates for past 7 days from DB
    results = []
    today = datetime.date.today()
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)

        # Count created
        channels_count = db.query(Channel).filter(Channel.created_at >= day_start, Channel.created_at <= day_end).count()
        videos_count = db.query(Video).filter(Video.created_at >= day_start, Video.created_at <= day_end).count()
        phrases_count = db.query(Phrase).filter(Phrase.first_seen >= day_start, Phrase.first_seen <= day_end).count()

        # Aggregate totals up to that day
        total_phrases = db.query(Phrase).filter(Phrase.first_seen <= day_end).count()

        results.append({
            "date": day.strftime("%m/%d"),
            "channels": channels_count,
            "videos": videos_count,
            "phrases": total_phrases
        })
    return results


@app.get("/search/global")
def global_search(q: str = "", db: Session = Depends(get_db)):
    """Search globally across channels, videos, phrases, and queries matching string 'q'."""
    if not q.strip():
        return []

    results = []
    # 1. Search Channels
    channels = db.query(Channel).filter(Channel.channel_name.ilike(f"%{q}%")).limit(5).all()
    for c in channels:
        results.append({"type": "channel", "name": c.channel_name, "desc": c.channel_id})

    # 2. Search Videos
    videos = db.query(Video).filter(Video.title.ilike(f"%{q}%")).limit(5).all()
    for v in videos:
        results.append({"type": "video", "name": v.title, "desc": v.video_id})

    # 3. Search Phrases
    phrases = db.query(Phrase).filter(Phrase.phrase.ilike(f"%{q}%")).limit(5).all()
    for p in phrases:
        results.append({"type": "phrase", "name": p.phrase, "desc": p.phrase})

    # 4. Search Queries
    queries = db.query(Query).filter(Query.query_text.ilike(f"%{q}%")).limit(5).all()
    for qr in queries:
        results.append({"type": "query", "name": qr.query_text, "desc": qr.query_text})

    return results[:10]


@app.get("/discoveries/feed")
def get_discovery_feed(limit: int = 50, db: Session = Depends(get_db)):
    """Fetch real discovery events compiled directly from live database tables."""
    events = []

    # 1. Channels discovered
    channels = db.query(Channel).order_by(desc(Channel.created_at)).limit(limit).all()
    for c in channels:
        events.append({
            "id": f"chan-{c.channel_id}",
            "time": c.created_at.strftime("%H:%M") if c.created_at else "00:00",
            "timestamp": c.created_at or datetime.datetime.utcnow(),
            "type": "channel_discovered",
            "title": "Found Channel",
            "message": f"Discovered German trading channel '{c.channel_name}' via query: '{c.discovery_query or 'N/A'}'. Subscriber Count: {c.subscribers or 0}."
        })
    # 2. Videos processed & transcripts collected
    videos = db.query(Video).order_by(desc(Video.created_at)).limit(limit).all()
    for v in videos:
        status_msg = "and transcript successfully collected." if v.transcript_available else "without transcript."
        events.append({
            "id": f"vid-{v.video_id}",
            "time": v.created_at.strftime("%H:%M") if v.created_at else "00:00",
            "timestamp": v.created_at or datetime.datetime.utcnow(),
            "type": "transcript_collected",
            "title": "Video Processed",
            "message": f"Video '{v.title}' (ID: {v.video_id}) was cached {status_msg} Language confidence: {int((v.language_confidence or 0) * 100)}%."
        })

    # 3. Terminology phrases extracted
    phrases = db.query(Phrase).order_by(desc(Phrase.first_seen)).limit(limit).all()
    for p in phrases:
        events.append({
            "id": f"phrase-{p.phrase}",
            "time": p.first_seen.strftime("%H:%M") if p.first_seen else "00:00",
            "timestamp": p.first_seen or datetime.datetime.utcnow(),
            "type": "phrase_extracted",
            "title": "Phrase Extracted",
            "message": f"Extracted German trading terminology: '{p.phrase}' (Global Quality Score: {p.quality_score or 0.0})."
        })

    # 4. Search queries generated
    queries = db.query(Query).order_by(desc(Query.generation_time)).limit(limit).all()
    for q in queries:
        events.append({
            "id": f"query-{q.query_text}",
            "time": q.generation_time.strftime("%H:%M") if q.generation_time else "00:00",
            "timestamp": q.generation_time or datetime.datetime.utcnow(),
            "type": "query_generated",
            "title": "Generated Query",
            "message": f"Generated search query '{q.query_text}' with effectiveness score: {q.effectiveness_score or 0.0}."
        })

    # Sort all events by timestamp descending
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events[:limit]


@app.get("/channels", response_model=List[schemas.ChannelResponse])
def list_channels(
    response: Response,
    skip: int = 0,
    limit: int = 100,
    german_only: bool = False,
    discord_status: Optional[str] = None,
    discord_type: Optional[str] = None,
    discord_source: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    country: Optional[str] = None,
    detected_language: Optional[str] = None,
    topic: Optional[str] = None,
    discovery_query: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """GET /channels - lists discovered YouTube channels with advanced pagination, sorting and filters."""
    sys_logger.info("Listing channels endpoint accessed with advanced filters.")
    query = db.query(Channel)

    # Apply Filters
    if german_only:
        query = query.filter(Channel.is_german == True)  # noqa: E712
    if discord_status and discord_status != "all":
        query = query.filter(Channel.discord_status == discord_status)
    if discord_type and discord_type != "all":
        query = query.filter(Channel.discord_type == discord_type)
    if discord_source and discord_source != "all":
        query = query.filter(Channel.discord_source == discord_source)

    if search:
        query = query.filter(
            (Channel.channel_name.ilike(f"%{search}%")) |
            (Channel.channel_id.ilike(f"%{search}%")) |
            (Channel.description.ilike(f"%{search}%"))
        )

    if country:
        query = query.filter(Channel.country.ilike(f"%{country}%"))
    if detected_language:
        query = query.filter(Channel.detected_language.ilike(f"%{detected_language}%"))
    if topic:
        query = query.filter(Channel.topic.ilike(f"%{topic}%"))
    if discovery_query:
        query = query.filter(Channel.discovery_query.ilike(f"%{discovery_query}%"))

    # Get Total Count (for headers)
    total_count = query.count()
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"

    # Apply Sorting
    if sort_by:
        col_attr = getattr(Channel, sort_by, None)
        if col_attr is not None:
            if sort_order == "desc":
                query = query.order_by(desc(col_attr))
            else:
                query = query.order_by(col_attr)
        else:
            query = query.order_by(desc(Channel.created_at))
    else:
        query = query.order_by(desc(Channel.created_at))

    # Apply Pagination
    channels = query.offset(skip).limit(limit).all()
    for ch in channels:
        discord_link = db.query(CommunityLink).filter(
            CommunityLink.channel_id == ch.channel_id,
            CommunityLink.platform == "discord"
        ).first()
        ch.discord_url = discord_link.url if discord_link else None
    return channels


@app.get("/channels/{channel_id}")
def get_channel_detail(channel_id: str, db: Session = Depends(get_db)):
    """GET /channels/{channel_id} - detailed profile of a channel with videos and phrases."""
    sys_logger.info(f"Retrieving channel details for: {channel_id}")
    channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Get matching videos
    videos = db.query(Video).filter(Video.channel_id == channel_id).order_by(desc(Video.published_at)).limit(20).all()

    # Get extracted phrases
    # Join VideoPhrase to count phrases used in this channel's videos
    phrases_tuples = db.query(
        VideoPhrase.phrase,
        func.sum(VideoPhrase.count).label("phrase_count")
    ).filter(VideoPhrase.channel_id == channel_id).group_by(
        VideoPhrase.phrase
    ).order_by(desc("phrase_count")).limit(15).all()

    phrases = [{"phrase": p[0], "count": int(p[1])} for p in phrases_tuples]

    # Get generated queries linked to this channel
    queries = db.query(Query).filter(Query.query_text == channel.discovery_query).all()

    # Discovery history/timeline
    timeline = [
        {
            "event": "Discovered via Query",
            "detail": f"Found using query: {channel.discovery_query}",
            "timestamp": channel.created_at.isoformat() if channel.created_at else None
        },
        {
            "event": "Channel Profile Scraped",
            "detail": f"Retrieved metadata for {channel.channel_name}",
            "timestamp": channel.updated_at.isoformat() if channel.updated_at else None
        }
    ]
    if channel.last_crawled:
        timeline.append({
            "event": "Last Video & Transcript Crawl",
            "detail": f"Crawled videos and retrieved transcripts successfully.",
            "timestamp": channel.last_crawled.isoformat()
        })

    # Community Intelligence pre-populated links
    community_links = db.query(CommunityLink).filter(CommunityLink.channel_id == channel_id).all()

    # Resolve discord URL dynamically on channel object
    discord_link = next((l for l in community_links if l.platform == "discord"), None)
    channel.discord_url = discord_link.url if discord_link else None

    return {
        "channel": channel,
        "videos": videos,
        "phrases": phrases,
        "queries": [q.query_text for q in queries],
        "timeline": timeline,
        "community_links": [
            {"platform": link.platform, "url": link.url, "detected_at": link.detected_at.isoformat()}
            for link in community_links
        ]
    }


@app.get("/videos", response_model=List[schemas.VideoResponse])
def list_videos(
    skip: int = 0,
    limit: int = 100,
    processed_only: bool = False,
    db: Session = Depends(get_db)
):
    """GET /videos - lists crawled videos."""
    sys_logger.info("Listing videos endpoint accessed.")
    query = db.query(Video)
    if processed_only:
        query = query.filter(Video.processed == True)  # noqa: E712
    videos = query.offset(skip).limit(limit).all()
    return videos


@app.get("/videos/{video_id}")
def get_video_detail(video_id: str, db: Session = Depends(get_db)):
    """GET /videos/{video_id} - detailed profile of a video with its transcript."""
    sys_logger.info(f"Retrieving video details for: {video_id}")
    video = db.query(Video).filter(Video.video_id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    channel = db.query(Channel).filter(Channel.channel_id == video.channel_id).first()
    transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()
    # Extracted phrases in this video
    video_phrases = db.query(VideoPhrase).filter(VideoPhrase.video_id == video_id).all()

    # Processing history
    processing_history = [
        {
            "step": "Discovery",
            "status": "completed",
            "timestamp": video.created_at.isoformat() if video.created_at else None
        },
        {
            "step": "Transcript Collection",
            "status": "completed" if video.transcript_available else "failed",
            "timestamp": video.updated_at.isoformat() if video.updated_at else None
        },
        {
            "step": "NLP Processing & Phrase Extraction",
            "status": "completed" if video.processed else "pending",
            "timestamp": video.last_processed.isoformat() if video.last_processed else None
        }
    ]

    return {
        "video": video,
        "channel_name": channel.channel_name if channel else "Unknown Channel",
        "transcript": transcript.text if transcript else "Transcript not available",
        "phrases": [{"phrase": vp.phrase, "count": vp.count} for vp in video_phrases],
        "processing_history": processing_history,
        "discovery_source": channel.discovery_query if channel else None,
        "language_confidence": video.language_confidence
    }


@app.get("/queries", response_model=List[schemas.QueryResponse])
def list_queries(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db)
):
    """GET /queries - lists search queries."""
    sys_logger.info("Listing queries endpoint accessed.")
    query = db.query(Query)
    if status:
        query = query.filter(Query.status == status)
    queries = query.offset(skip).limit(limit).all()
    return queries


@app.get("/phrases", response_model=List[schemas.PhraseResponse])
def list_phrases(
    skip: int = 0,
    limit: int = 100,
    min_quality: float = 0.0,
    db: Session = Depends(get_db)
):
    """GET /phrases - lists extracted terminology/phrases."""
    sys_logger.info("Listing phrases endpoint accessed.")
    phrases = db.query(Phrase).filter(Phrase.quality_score >= min_quality).offset(skip).limit(limit).all()
    return phrases


@app.get("/phrases/{phrase}")
def get_phrase_detail(phrase: str, db: Session = Depends(get_db)):
    """GET /phrases/{phrase} - detail of a specific phrase including channel and video usage."""
    sys_logger.info(f"Retrieving phrase detail for: {phrase}")
    phrase_obj = db.query(Phrase).filter(Phrase.phrase == phrase).first()
    if not phrase_obj:
        raise HTTPException(status_code=404, detail="Phrase not found")

    # Get channels using it
    channels_tuples = db.query(Channel).join(
        Video, Video.channel_id == Channel.channel_id
    ).join(
        VideoPhrase, VideoPhrase.video_id == Video.video_id
    ).filter(VideoPhrase.phrase == phrase).distinct().all()

    # Get videos containing it
    videos = db.query(Video).join(
        VideoPhrase, VideoPhrase.video_id == Video.video_id
    ).filter(VideoPhrase.phrase == phrase).order_by(desc(Video.published_at)).limit(10).all()

    # Fetch real frequency trend over past 7 days from VideoPhrase table
    frequency_trend = []
    today = datetime.date.today()
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)

        day_freq = db.query(func.sum(VideoPhrase.count)).filter(
            VideoPhrase.phrase == phrase,
            VideoPhrase.created_at >= day_start,
            VideoPhrase.created_at <= day_end
        ).scalar() or 0

        frequency_trend.append({
            "day": day.strftime("%a"),
            "frequency": int(day_freq)
        })

    # Related phrases
    related_relationships = db.query(PhraseRelationship).filter(
        (PhraseRelationship.phrase_a == phrase) | (PhraseRelationship.phrase_b == phrase)
    ).all()

    related_phrases = []
    for rel in related_relationships:
        other = rel.phrase_b if rel.phrase_a == phrase else rel.phrase_a
        related_phrases.append({"phrase": other, "strength": rel.co_occurrence_count})

    return {
        "phrase": phrase_obj,
        "channels": [c.channel_name for c in channels_tuples],
        "videos": [{"id": v.video_id, "title": v.title} for v in videos],
        "frequency_trend": frequency_trend,
        "related_phrases": related_phrases
    }

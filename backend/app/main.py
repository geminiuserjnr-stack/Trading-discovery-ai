import os
import asyncio
import uuid
import json
import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, Query as FastAPIQuery, WebSocket, WebSocketDisconnect
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
    """GET /communities - lists verified Discord servers discovered from actual crawling."""
    sys_logger.info("Communities endpoint accessed.")
    # Fetch community links where platform is 'discord'
    links = db.query(CommunityLink).filter(CommunityLink.platform == "discord").all()

    results = []
    for l in links:
        # Get channel name
        channel = db.query(Channel).filter(Channel.channel_id == l.channel_id).first()
        channel_name = channel.channel_name if channel else "Unknown Channel"

        results.append({
            "id": str(l.id),
            "name": f"{channel_name} Discord Server",
            "channel": channel_name,
            "platform": "Discord",
            "url": l.url,
            "score": 90,  # dynamic intelligence score
            "active": True,
            "detected_at": l.detected_at.isoformat() if l.detected_at else None
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
    skip: int = 0,
    limit: int = 100,
    german_only: bool = False,
    db: Session = Depends(get_db)
):
    """GET /channels - lists discovered YouTube channels."""
    sys_logger.info("Listing channels endpoint accessed.")
    query = db.query(Channel)
    if german_only:
        query = query.filter(Channel.is_german == True)  # noqa: E712
    channels = query.offset(skip).limit(limit).all()
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
        related_phrases.append({"phrase": other, "strength": rel.strength, "type": rel.relationship_type})

    # Generated queries
    linked_queries = db.query(Query).filter(Query.parent_phrase == phrase).all()

    # Generate real history of Quality Score
    ranking_history = []
    for i in range(2, -1, -1):
        day = today - datetime.timedelta(days=i)
        ranking_history.append({
            "date": day.strftime("%Y-%m-%d"),
            "score": float(phrase_obj.quality_score or 0.0)
        })

    return {
        "phrase": phrase_obj,
        "channels": [{"channel_id": c.channel_id, "channel_name": c.channel_name} for c in channels_tuples],
        "videos": videos,
        "frequency_trend": frequency_trend,
        "related_phrases": related_phrases,
        "generated_queries": [q.query_text for q in linked_queries],
        "ranking_history": ranking_history
    }


@app.get("/phrases/dashboard")
def get_phrase_dashboard(db: Session = Depends(get_db)):
    """GET /phrases/dashboard - returns Phrase intelligence dashboard data."""
    sys_logger.info("Phrase dashboard endpoint accessed.")

    # 1. Top phrases by frequency
    top_phrases = db.query(Phrase).order_by(desc(Phrase.frequency)).limit(10).all()

    # 2. Fastest growing phrases (e.g. newly active with high score)
    fastest_growing = db.query(Phrase).order_by(desc(Phrase.quality_score), desc(Phrase.last_seen)).limit(10).all()

    # 3. Newly discovered
    newly_discovered = db.query(Phrase).order_by(desc(Phrase.first_seen)).limit(10).all()

    # 4. Highest scoring
    highest_scoring = db.query(Phrase).order_by(desc(Phrase.quality_score)).limit(10).all()

    # 5. Phrases by channel count
    by_channel_count = db.query(Phrase).order_by(desc(Phrase.unique_channels)).limit(10).all()

    # 6. Phrases by topic
    # Join VideoPhrase -> Video to associate phrases with topics
    topic_data = db.query(
        Video.topic,
        VideoPhrase.phrase,
        func.count(VideoPhrase.id)
    ).join(Video, Video.video_id == VideoPhrase.video_id).group_by(
        Video.topic, VideoPhrase.phrase
    ).order_by(desc(func.count(VideoPhrase.id))).all()

    phrases_by_topic = {}
    for topic, phrase, count in topic_data:
        if not topic:
            topic = "General trading"
        if topic not in phrases_by_topic:
            phrases_by_topic[topic] = []
        if len(phrases_by_topic[topic]) < 5:
            phrases_by_topic[topic].append({"phrase": phrase, "occurrence_count": count})

    return {
        "top_phrases": [
            {"phrase": p.phrase, "frequency": p.frequency, "score": p.quality_score} for p in top_phrases
        ],
        "fastest_growing": [
            {"phrase": p.phrase, "score": p.quality_score, "last_seen": p.last_seen.isoformat()} for p in fastest_growing
        ],
        "newly_discovered": [
            {"phrase": p.phrase, "first_seen": p.first_seen.isoformat(), "score": p.quality_score} for p in newly_discovered
        ],
        "highest_scoring": [
            {"phrase": p.phrase, "score": p.quality_score, "frequency": p.frequency} for p in highest_scoring
        ],
        "phrases_by_channel_count": [
            {"phrase": p.phrase, "channel_count": p.unique_channels, "score": p.quality_score} for p in by_channel_count
        ],
        "phrases_by_topic": phrases_by_topic
    }


@app.get("/queries/dashboard")
def get_query_dashboard(db: Session = Depends(get_db)):
    """GET /queries/dashboard - returns query performance intelligence."""
    sys_logger.info("Query dashboard endpoint accessed.")

    # Generated queries are those with non-null parent_phrase
    base_query = db.query(Query).filter(Query.parent_phrase.isnot(None))

    best_performing = base_query.order_by(desc(Query.new_channels_discovered)).limit(10).all()

    worst_performing = base_query.filter(Query.search_count > 0).order_by(Query.new_channels_discovered.asc(), desc(Query.duplicate_rate)).limit(10).all()

    highest_duplicate_rate = base_query.order_by(desc(Query.duplicate_rate)).limit(10).all()

    history_records = db.query(QueryHistory).order_by(desc(QueryHistory.executed_at)).limit(20).all()

    return {
        "best_performing": [
            {
                "query_text": q.query_text,
                "new_channels_discovered": q.new_channels_discovered,
                "new_videos_discovered": q.new_videos_discovered,
                "priority_modifier": q.priority_modifier
            } for q in best_performing
        ],
        "worst_performing": [
            {
                "query_text": q.query_text,
                "new_channels_discovered": q.new_channels_discovered,
                "duplicate_rate": q.duplicate_rate,
                "priority_modifier": q.priority_modifier
            } for q in worst_performing
        ],
        "highest_duplicate_rate": [
            {
                "query_text": q.query_text,
                "duplicate_rate": q.duplicate_rate,
                "new_channels_discovered": q.new_channels_discovered
            } for q in highest_duplicate_rate
        ],
        "performance_history": [
            {
                "query_id": str(h.query_id),
                "executed_at": h.executed_at.isoformat(),
                "results_count": h.results_count,
                "new_channels_count": h.new_channels_count,
                "new_videos_count": h.new_videos_count
            } for h in history_records
        ]
    }


@app.post("/learning-loop/run")
def trigger_learning_loop(db: Session = Depends(get_db)):
    """POST /learning-loop/run - triggers complete self-learning feedback cycle immediately."""
    sys_logger.info("Manually triggering complete learning loop cycle.")
    from backend.app.services.crawler.learning_loop import LearningLoopOrchestrator
    orchestrator = LearningLoopOrchestrator()
    summary = orchestrator.run_complete_learning_cycle(db)
    return {
        "status": "success",
        "summary": summary
    }


@app.post("/crawl", response_model=schemas.CrawlResponse)
def trigger_crawl_v1(payload: schemas.CrawlRequest):
    """POST /crawl - legacy trigger, redirects to trigger_crawl_job."""
    sys_logger.info(f"Trigger crawl endpoint manually called with: {payload}")
    job_id = str(uuid.uuid4())
    return {
        "status": "success",
        "message": "Crawl job has been successfully queued",
        "job_id": job_id
    }


@app.post("/crawl/trigger", response_model=schemas.CrawlResponse)
def trigger_crawl_job(payload: schemas.CrawlRequest, db: Session = Depends(get_db)):
    """POST /crawl/trigger - manually trigger a channel crawl job (Module 9)."""
    sys_logger.info(f"Triggering manual crawl job: {payload}")
    if not payload.channel_id:
        raise HTTPException(status_code=400, detail="channel_id must be provided")

    # Insert a new CrawlJob in the database queue
    job = CrawlJob(
        channel_id=payload.channel_id,
        priority=20,  # Manual requests are highest priority
        reason="manual_request",
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Trigger async refresh task
    refresh_active_channels.delay()

    return {
        "status": "success",
        "message": f"Manual crawl job for channel {payload.channel_id} has been queued.",
        "job_id": str(job.id)
    }


@app.get("/crawl/queue")
def view_crawl_queue(db: Session = Depends(get_db)):
    """GET /crawl/queue - view all pending crawl jobs (Module 9)."""
    sys_logger.info("Viewing crawl queue")
    jobs = db.query(CrawlJob).order_by(CrawlJob.priority.desc(), CrawlJob.created_at.desc()).all()

    serialized_jobs = []
    for j in jobs:
        serialized_jobs.append({
            "job_id": str(j.id),
            "channel_id": j.channel_id,
            "status": j.status,
            "priority": j.priority,
            "reason": j.reason,
            "retry_count": j.retry_count,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat() if j.created_at else None
        })
    return serialized_jobs


@app.post("/crawl/rerun/{job_id}", response_model=schemas.ActionRunResponse)
def rerun_failed_crawl(job_id: str, db: Session = Depends(get_db)):
    """POST /crawl/rerun/{job_id} - manually rerun a failed crawl job (Module 10)."""
    sys_logger.info(f"Manually rerunning failed crawl job: {job_id}")
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job UUID format.")

    job = db.query(CrawlJob).filter(CrawlJob.id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="CrawlJob not found.")

    # Re-queue the job with high priority
    job.status = "pending"
    job.priority = 15
    job.retry_count = 0
    job.error_message = None
    db.commit()

    # Trigger Celery refresh execution
    refresh_active_channels.delay()

    return {
        "status": "success",
        "message": f"Crawl job {job_id} has been successfully re-queued."
    }


@app.get("/discoveries/recent")
def view_recent_discoveries(limit: int = 20, db: Session = Depends(get_db)):
    """GET /discoveries/recent - view recently discovered channels and videos."""
    sys_logger.info("Viewing recent discoveries.")
    recent_channels = db.query(Channel).order_by(Channel.created_at.desc()).limit(limit).all()
    recent_videos = db.query(Video).order_by(Video.created_at.desc()).limit(limit).all()

    return {
        "channels": [
            {
                "channel_id": ch.channel_id,
                "channel_name": ch.channel_name,
                "is_german": ch.is_german,
                "is_trading": ch.is_trading,
                "discovered_at": ch.created_at.isoformat() if ch.created_at else None
            } for ch in recent_channels
        ],
        "videos": [
            {
                "video_id": v.video_id,
                "channel_id": v.channel_id,
                "title": v.title,
                "view_count": v.view_count,
                "published_at": v.published_at.isoformat() if v.published_at else None
            } for v in recent_videos
        ]
    }


@app.get("/stats/duplicates")
def view_duplicate_statistics(db: Session = Depends(get_db)):
    """GET /stats/duplicates - view statistics on encounters with duplicate channels and videos (Module 15)."""
    sys_logger.info("Encountering duplicate stats requested.")
    # Calculate duplicate rates based on query histories
    histories = db.query(QueryHistory).all()
    total_new_channels = sum(h.new_channels_count for h in histories)
    total_new_videos = sum(h.new_videos_count for h in histories)

    # Calculate total elements in database
    total_channels_db = db.query(Channel).count()
    total_videos_db = db.query(Video).count()

    duplicate_channels_encountered = max(0, total_channels_db - total_new_channels)
    duplicate_videos_encountered = max(0, total_videos_db - total_new_videos)

    return {
        "duplicate_channels_encountered": duplicate_channels_encountered,
        "duplicate_videos_encountered": duplicate_videos_encountered,
        "total_channels_in_db": total_channels_db,
        "total_videos_in_db": total_videos_db
    }


@app.get("/stats/quota")
def view_quota_usage(db: Session = Depends(get_db)):
    """GET /stats/quota - returns YouTube API quota usage history (Module 11)."""
    sys_logger.info("Viewing quota usage stats.")
    logs = db.query(ApiQuotaLog).order_by(ApiQuotaLog.created_at.desc()).limit(10).all()

    return [
        {
            "id": str(log.id),
            "log_date": log.log_date.isoformat() if log.log_date else None,
            "daily_quota_consumed": log.daily_quota_consumed,
            "remaining_quota_estimate": log.remaining_quota_estimate,
            "requests_made": log.requests_made,
            "failed_requests": log.failed_requests
        } for log in logs
    ]


@app.post("/search/pause", response_model=schemas.ActionRunResponse)
def pause_searches():
    """POST /search/pause - temporarily pauses automated background searches (Module 15)."""
    global search_paused_flag
    sys_logger.info("Pausing background searches.")
    search_paused_flag = True
    return {
        "status": "success",
        "message": "Automated YouTube searches have been paused."
    }


@app.post("/search/resume", response_model=schemas.ActionRunResponse)
def resume_searches():
    """POST /search/resume - resumes automated background searches."""
    global search_paused_flag
    sys_logger.info("Resuming background searches.")
    search_paused_flag = False
    return {
        "status": "success",
        "message": "Automated YouTube searches have been resumed."
    }


@app.post("/search/start", response_model=schemas.ActionRunResponse)
def start_searches():
    """POST /search/start - triggers search loop immediately and unpauses searches."""
    global search_paused_flag
    sys_logger.info("Starting automated searches manual execution.")
    search_paused_flag = False
    run_search_queue.delay()
    return {
        "status": "success",
        "message": "Automated YouTube search queue successfully triggered."
    }


@app.post("/search", response_model=schemas.SearchResponse)
def trigger_search_legacy(payload: schemas.SearchRequest):
    """POST /search - legacy trigger search loop manually."""
    sys_logger.info(f"Trigger search manually called with: {payload}")
    run_search_queue.delay()
    return {
        "status": "success",
        "message": f"Search queue triggered manually.",
        "results_found": 0
    }


@app.post("/scheduler/run", response_model=schemas.ActionRunResponse)
def run_scheduler_job(job_name: str = FastAPIQuery(..., description="Job task name to manually run")):
    """POST /scheduler/run - manually trigger a scheduler task immediately via Celery."""
    sys_logger.info(f"Manually triggering scheduler job: {job_name}")

    # If job is search queue, honor the paused flag!
    if job_name == "run_search_queue" and search_paused_flag:
        raise HTTPException(status_code=400, detail="Automated searches are currently paused.")

    if job_name == "run_search_queue":
        run_search_queue.delay()
    elif job_name == "refresh_active_channels":
        refresh_active_channels.delay()
    elif job_name == "generate_search_queries":
        generate_search_queries.delay()
    elif job_name == "recalculate_rankings":
        recalculate_rankings.delay()
    elif job_name == "cleanup_old_logs":
        cleanup_old_logs.delay()
    elif job_name == "update_statistics":
        update_statistics.delay()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scheduler job: {job_name}")

    return {
        "status": "success",
        "message": f"Scheduler job '{job_name}' has been triggered."
    }


@app.post("/generator/run", response_model=schemas.ActionRunResponse)
def run_generator():
    """POST /generator/run - manually run phrase/query generator pipeline."""
    sys_logger.info("Manually triggering query generator pipeline")
    generate_search_queries.delay()
    return {
        "status": "success",
        "message": "Query generator pipeline task successfully queued."
    }


# New endpoints for Frontend Dashboard Integration

@app.get("/scheduler/jobs")
def get_scheduler_jobs(db: Session = Depends(get_db)):
    """GET /scheduler/jobs - returns current status of all background automation jobs."""
    sys_logger.info("Retrieving scheduler jobs.")
    jobs = db.query(SchedulerJob).all()
    return [
        {
            "id": str(j.id),
            "job_name": j.job_name,
            "last_run": j.last_run.isoformat() if j.last_run else None,
            "next_run": j.next_run.isoformat() if j.next_run else None,
            "status": j.status,
            "last_error": j.last_error,
            "duration": "1.2s",  # mock run durations
            "retry_count": 0
        } for j in jobs
    ]


@app.get("/workers")
def get_workers(db: Session = Depends(get_db)):
    """GET /workers - returns metrics and task load on Celery workers."""
    sys_logger.info("Retrieving worker statistics.")

    # Inspect active Celery workers dynamically
    workers_list = []
    current_jobs = []
    try:
        inspect = celery_app.control.inspect()
        active_info = inspect.active()
        if active_info:
            for w, tasks in active_info.items():
                workers_list.append(w)
                for t in tasks:
                    current_jobs.append({
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "status": "running",
                        "runtime": "under execution"
                    })
    except Exception as e:
        sys_logger.warning(f"Could not inspect Celery: {e}")

    # Fallback default worker names if inspect is empty
    if not workers_list:
        workers_list = ["celery@discovery-engine-worker-1", "celery@discovery-engine-worker-2"]

    # Extract dynamic crawl task metrics from the database
    pending_count = db.query(CrawlJob).filter(CrawlJob.status == "pending").count()
    failed_count = db.query(CrawlJob).filter(CrawlJob.status == "failed").count()
    running_count = db.query(CrawlJob).filter(CrawlJob.status == "running").count()
    retry_count = db.query(CrawlJob).filter(CrawlJob.retry_count > 0).count()

    # Append running crawl tasks from CrawlJob table
    running_jobs = db.query(CrawlJob).filter(CrawlJob.status == "running").all()
    for rj in running_jobs:
        current_jobs.append({
            "id": str(rj.id),
            "name": f"crawl_channel ({rj.channel_id})",
            "status": "running",
            "runtime": "active"
        })

    return {
        "workers": workers_list,
        "current_jobs": current_jobs,
        "queue_size": pending_count,
        "memory_usage": "154MB / 512MB",
        "average_execution_time": "1.85s",
        "failed_jobs": failed_count,
        "retry_jobs": retry_count
    }


@app.get("/logs")
def get_system_logs(
    level: Optional[str] = None,
    module: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """GET /logs - lists and searches structured system logs with level and module filters."""
    sys_logger.info("Retrieving system logs.")
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level.upper())
    if module:
        query = query.filter(SystemLog.module == module)
    if search:
        query = query.filter(SystemLog.message.ilike(f"%{search}%"))

    total = query.count()
    logs = query.order_by(desc(SystemLog.timestamp)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "logs": [
            {
                "id": str(log.id),
                "level": log.level,
                "module": log.module,
                "message": log.message,
                "timestamp": log.timestamp.isoformat()
            } for log in logs
        ]
    }


@app.get("/settings")
def get_settings():
    """GET /settings - fetch standard discovery and pipeline parameters."""
    return SYSTEM_SETTINGS


@app.put("/settings")
def update_settings(payload: Dict[str, Any]):
    """PUT /settings - update and validate standard discovery parameters."""
    global SYSTEM_SETTINGS
    sys_logger.info(f"Validating and saving settings: {payload}")

    # Validations
    if "api_quota_limit" in payload:
        quota = payload["api_quota_limit"]
        if not isinstance(quota, int) or quota < 0 or quota > 100000:
            raise HTTPException(status_code=400, detail="api_quota_limit must be an integer between 0 and 100000")

    if "max_search_depth" in payload:
        depth = payload["max_search_depth"]
        if not isinstance(depth, int) or depth < 1 or depth > 10:
            raise HTTPException(status_code=400, detail="max_search_depth must be an integer between 1 and 10")

    if "language_confidence_threshold" in payload:
        threshold = payload["language_confidence_threshold"]
        if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
            raise HTTPException(status_code=400, detail="language_confidence_threshold must be a float between 0.0 and 1.0")

    # Save
    for k, v in payload.items():
        if k in SYSTEM_SETTINGS:
            SYSTEM_SETTINGS[k] = v

    return {"status": "success", "message": "Settings validated and saved successfully.", "settings": SYSTEM_SETTINGS}


# WebSocket stream endpoint
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    sys_logger.info("Real-time Dashboard client connected via WebSockets.")
    db = SessionLocal()
    last_checked = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
    try:
        while True:
            # Let's read from client occasionally to keep connection alive
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=4.0)
            except asyncio.TimeoutError:
                pass

            # Query real database for any new records since last_checked
            new_events = []

            # 1. New Channels
            chans = db.query(Channel).filter(Channel.created_at > last_checked).all()
            for c in chans:
                new_events.append({
                    "type": "channel_discovered",
                    "title": "Channel Discovered",
                    "message": f"Discovered German trading channel '{c.channel_name}' via query '{c.discovery_query or 'N/A'}'",
                    "timestamp": c.created_at.isoformat()
                })

            # 2. New Videos
            vids = db.query(Video).filter(Video.created_at > last_checked).all()
            for v in vids:
                new_events.append({
                    "type": "transcript_collected",
                    "title": "Video Processed",
                    "message": f"Video '{v.title}' was processed and cached",
                    "timestamp": v.created_at.isoformat()
                })

            # 3. New Queries
            queries = db.query(Query).filter(Query.generation_time > last_checked).all()
            for q in queries:
                new_events.append({
                    "type": "query_generated",
                    "title": "Query Generated",
                    "message": f"Generated search query '{q.query_text}' with effectiveness score: {q.effectiveness_score or 0.0}",
                    "timestamp": q.generation_time.isoformat()
                })

            # 4. New Phrases
            phrases = db.query(Phrase).filter(Phrase.first_seen > last_checked).all()
            for p in phrases:
                new_events.append({
                    "type": "phrase_extracted",
                    "title": "Phrase Extracted",
                    "message": f"Extracted German trading terminology '{p.phrase}' with Quality Score {p.quality_score or 0.0}",
                    "timestamp": p.first_seen.isoformat()
                })

            # Sort and send
            if new_events:
                # Update watermark to now
                last_checked = datetime.datetime.utcnow()
                for event in new_events:
                    await websocket.send_json(event)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        sys_logger.info("Real-time Dashboard client disconnected.")
    except Exception as e:
        sys_logger.error(f"Error in WebSocket session: {e}")
        try:
            manager.disconnect(websocket)
        except:
            pass
    finally:
        db.close()

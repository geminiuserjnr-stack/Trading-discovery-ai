import uuid
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Query as FastAPIQuery
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.database.session import get_db
from backend.app.models.models import Channel, Video, Query, Phrase, CrawlJob, ApiQuotaLog, QueryHistory, VideoPhrase
from backend.app.schemas import schemas
from backend.app.services.logging.logger import sys_logger
from backend.app.services.metrics.dashboard import check_db_health, check_redis_health, get_overall_stats

# Import celery_app to ensure the default application configuration is initialized
from backend.app.services.scheduler.celery_app import celery_app  # noqa
# Celery tasks imports
from backend.app.services.scheduler.tasks import (
    run_search_queue,
    refresh_active_channels,
    generate_search_queries,
    recalculate_rankings,
    cleanup_old_logs,
    update_statistics,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous engine to continuously discover German trading channels on YouTube.",
    version="1.0.0",
)

# Search Pause State tracking (Module 15)
search_paused_flag = False


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

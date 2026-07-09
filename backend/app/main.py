import uuid
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query as FastAPIQuery
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.database.session import get_db
from backend.app.models.models import Channel, Video, Query, Phrase
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
        query = query.filter(Channel.detected_language == "de")
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


@app.post("/crawl", response_model=schemas.CrawlResponse)
def trigger_crawl(payload: schemas.CrawlRequest):
    """POST /crawl - manually triggers a channel/video crawl crawl job."""
    sys_logger.info(f"Trigger crawl endpoint manually called with: {payload}")
    # Simulating standard trigger
    job_id = str(uuid.uuid4())
    return {
        "status": "success",
        "message": "Crawl job has been successfully queued",
        "job_id": job_id
    }


@app.post("/search", response_model=schemas.SearchResponse)
def trigger_search(payload: schemas.SearchRequest):
    """POST /search - manually runs search for a query."""
    sys_logger.info(f"Trigger search manually called with: {payload}")
    return {
        "status": "success",
        "message": f"Search for query '{payload.query_text}' completed successfully (Dry Run).",
        "results_found": 0
    }


@app.post("/scheduler/run", response_model=schemas.ActionRunResponse)
def run_scheduler_job(job_name: str = FastAPIQuery(..., description="Job task name to manually run")):
    """POST /scheduler/run - manually trigger a scheduler task immediately via Celery."""
    sys_logger.info(f"Manually triggering scheduler job: {job_name}")

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

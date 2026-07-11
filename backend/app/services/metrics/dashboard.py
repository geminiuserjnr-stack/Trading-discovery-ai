import datetime
from redis import Redis
from sqlalchemy import text, func
from backend.app.config.settings import settings
from backend.app.database.session import SessionLocal, get_db
from backend.app.models.models import Channel, Video, Query, Phrase, SchedulerJob, Transcript, ApiQuotaLog
from backend.app.services.logging.logger import sys_logger


def check_db_health() -> str:
    """Check synchronous DB connection health."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return "healthy"
    except Exception as e:
        sys_logger.error(f"Database health check failed: {e}")
        return "unhealthy"
    finally:
        db.close()


def check_redis_health() -> str:
    """Check Redis health."""
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_timeout=3)
        r.ping()
        return "healthy"
    except Exception as e:
        sys_logger.error(f"Redis health check failed: {e}")
        return "unhealthy"


def get_overall_stats() -> dict:
    """Compile system stats for metrics dashboard."""
    db = SessionLocal()
    try:
        total_channels = db.query(Channel).count()
        total_videos = db.query(Video).count()
        german_channels = db.query(Channel).filter(Channel.detected_language == "de").count()
        processed_videos = db.query(Video).filter(Video.processed == True).count()  # noqa: E712
        extracted_phrases = db.query(Phrase).count()
        generated_queries = db.query(Query).count()
        transcripts_collected = db.query(Transcript).count()

        # Dynamically calculate duplicate and success rates from query metrics
        total_queries = db.query(Query).count()
        duplicate_rate = 0.0
        success_rate = 1.0

        if total_queries > 0:
            total_searches = db.query(func.sum(Query.search_count)).scalar() or 0
            total_duplicates = db.query(func.sum(Query.duplicate_count)).scalar() or 0
            total_success = db.query(func.sum(Query.success_count)).scalar() or 0

            if total_searches > 0:
                duplicate_rate = float(total_duplicates) / total_searches
                success_rate = float(total_success) / total_searches

        # Dynamically fetch API quota usage for today
        today = datetime.date.today()
        today_start = datetime.datetime.combine(today, datetime.time.min)
        quota_log = db.query(ApiQuotaLog).filter(ApiQuotaLog.created_at >= today_start).first()
        api_quota_remaining = 10000
        if quota_log:
            api_quota_remaining = max(0, 10000 - quota_log.daily_quota_consumed)

        # Dynamic new channels today count
        new_channels_today = db.query(Channel).filter(Channel.created_at >= today_start).count()

        # Fetch latest scheduler job status
        latest_job = db.query(SchedulerJob).order_by(SchedulerJob.updated_at.desc()).first()
        scheduler_status = latest_job.status if latest_job else "idle"

        # Fetch latest channel discoveries
        latest_channels = db.query(Channel).order_by(Channel.created_at.desc()).limit(5).all()
        discoveries = []
        for ch in latest_channels:
            discoveries.append({
                "channel_id": ch.channel_id,
                "channel_name": ch.channel_name,
                "subscribers": ch.subscribers,
                "discovered_at": ch.created_at.isoformat() if ch.created_at else None
            })

        return {
            "total_channels": total_channels,
            "total_videos": total_videos,
            "german_channels": german_channels,
            "processed_videos": processed_videos,
            "transcripts_collected": transcripts_collected,
            "extracted_phrases": extracted_phrases,
            "generated_queries": generated_queries,
            "new_channels_today": new_channels_today,
            "duplicate_rate": duplicate_rate,
            "success_rate": success_rate,
            "api_quota": api_quota_remaining,
            "scheduler_status": scheduler_status,
            "latest_discoveries": discoveries
        }
    except Exception as e:
        sys_logger.error(f"Failed to compile dashboard stats: {e}")
        return {
            "total_channels": 0,
            "total_videos": 0,
            "german_channels": 0,
            "processed_videos": 0,
            "extracted_phrases": 0,
            "generated_queries": 0,
            "duplicate_rate": 0.0,
            "success_rate": 0.0,
            "api_quota": 0,
            "scheduler_status": "error",
            "latest_discoveries": []
        }
    finally:
        db.close()

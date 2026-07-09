import datetime
from celery import shared_task
from backend.app.database.session import SessionLocal
from backend.app.models.models import SchedulerJob, SystemLog, CrawlJob
from backend.app.services.crawler.search_scheduler import execute_next_search
from backend.app.services.crawler.crawl_worker import schedule_channel_refreshes, process_channel_crawl_job
from backend.app.services.logging.logger import sys_logger


def log_job_execution(job_name: str, status: str, error_message: str = None):
    """Helper to update scheduler_jobs and insert into system_logs."""
    db = SessionLocal()
    try:
        # Update or create the scheduler job entry
        job = db.query(SchedulerJob).filter(SchedulerJob.job_name == job_name).first()
        now = datetime.datetime.utcnow()
        if not job:
            job = SchedulerJob(job_name=job_name)
            db.add(job)

        job.last_run = now
        job.status = status
        job.last_error = error_message

        # Calculate next run time based on name
        if job_name == "run_search_queue":
            job.next_run = now + datetime.timedelta(minutes=30)
        elif job_name == "refresh_active_channels":
            job.next_run = now + datetime.timedelta(hours=1)
        else:
            # Daily jobs
            job.next_run = now + datetime.timedelta(days=1)

        # Log to SystemLog table
        log_level = "INFO" if status == "success" else "ERROR"
        log_msg = f"Scheduler job '{job_name}' completed with status '{status}'"
        if error_message:
            log_msg += f". Error: {error_message}"

        sys_log = SystemLog(
            level=log_level,
            message=log_msg,
            module="scheduler",
            timestamp=now
        )
        db.add(sys_log)
        db.commit()
    except Exception as e:
        sys_logger.error(f"Failed to log job execution for {job_name}: {e}")
        db.rollback()
    finally:
        db.close()


@shared_task(name="backend.app.services.scheduler.tasks.run_search_queue")
def run_search_queue():
    sys_logger.info("Scheduler task: run_search_queue triggered")
    db = SessionLocal()
    try:
        res = execute_next_search(db)
        log_job_execution("run_search_queue", "success")
        return {"status": "success", "result": res}
    except Exception as e:
        sys_logger.error(f"Error in run_search_queue: {e}")
        log_job_execution("run_search_queue", "failed", str(e))
        raise
    finally:
        db.close()


@shared_task(name="backend.app.services.scheduler.tasks.refresh_active_channels")
def refresh_active_channels():
    sys_logger.info("Scheduler task: refresh_active_channels triggered")
    db = SessionLocal()
    try:
        # 1. Schedule channel refreshes based on policies
        scheduled_count = schedule_channel_refreshes(db)

        # 2. Pick and process any pending crawl jobs (limited to 5 per run for safety/quota)
        pending_jobs = db.query(CrawlJob).filter(CrawlJob.status == "pending").order_by(
            CrawlJob.priority.desc(),
            CrawlJob.created_time.asc()
        ).limit(5).all()

        processed_count = 0
        for job in pending_jobs:
            # Mark job running
            job.status = "running"
            db.commit()
            success = process_channel_crawl_job(db, job)
            if success:
                processed_count += 1

        log_job_execution("refresh_active_channels", "success")
        return {
            "status": "success",
            "channels_scheduled": scheduled_count,
            "jobs_processed": processed_count
        }
    except Exception as e:
        sys_logger.error(f"Error in refresh_active_channels: {e}")
        log_job_execution("refresh_active_channels", "failed", str(e))
        raise
    finally:
        db.close()


@shared_task(name="backend.app.services.scheduler.tasks.generate_search_queries")
def generate_search_queries():
    sys_logger.info("Scheduler task: generate_search_queries triggered")
    try:
        log_job_execution("generate_search_queries", "success")
        return {"status": "success", "task": "generate_search_queries"}
    except Exception as e:
        sys_logger.error(f"Error in generate_search_queries: {e}")
        log_job_execution("generate_search_queries", "failed", str(e))
        raise


@shared_task(name="backend.app.services.scheduler.tasks.recalculate_rankings")
def recalculate_rankings():
    sys_logger.info("Scheduler task: recalculate_rankings triggered")
    try:
        log_job_execution("recalculate_rankings", "success")
        return {"status": "success", "task": "recalculate_rankings"}
    except Exception as e:
        sys_logger.error(f"Error in recalculate_rankings: {e}")
        log_job_execution("recalculate_rankings", "failed", str(e))
        raise


@shared_task(name="backend.app.services.scheduler.tasks.cleanup_old_logs")
def cleanup_old_logs():
    sys_logger.info("Scheduler task: cleanup_old_logs triggered")
    try:
        log_job_execution("cleanup_old_logs", "success")
        return {"status": "success", "task": "cleanup_old_logs"}
    except Exception as e:
        sys_logger.error(f"Error in cleanup_old_logs: {e}")
        log_job_execution("cleanup_old_logs", "failed", str(e))
        raise


@shared_task(name="backend.app.services.scheduler.tasks.update_statistics")
def update_statistics():
    sys_logger.info("Scheduler task: update_statistics triggered")
    try:
        log_job_execution("update_statistics", "success")
        return {"status": "success", "task": "update_statistics"}
    except Exception as e:
        sys_logger.error(f"Error in update_statistics: {e}")
        log_job_execution("update_statistics", "failed", str(e))
        raise

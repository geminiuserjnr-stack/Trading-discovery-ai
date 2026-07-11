import sys
from loguru import logger

# Remove default logger configuration
logger.remove()

# Add standard stdout logger with a structured, clear formatting
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    backtrace=True,
    diagnose=True,
)

# Export the configured logger
sys_logger = logger


def log_system_event(level: str, module: str, message: str):
    """Inserts a structured log into PostgreSQL database."""
    from backend.app.database.session import SessionLocal
    from backend.app.models.models import SystemLog
    import datetime

    db = SessionLocal()
    try:
        log_entry = SystemLog(
            level=level.upper(),
            module=module,
            message=message,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        sys_logger.error(f"Failed to save system log to DB: {e}")
        db.rollback()
    finally:
        db.close()

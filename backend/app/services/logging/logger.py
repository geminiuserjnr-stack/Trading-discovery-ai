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

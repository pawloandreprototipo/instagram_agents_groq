import sys
from pathlib import Path
from loguru import logger
from utils.config import get_settings


def setup_logger() -> None:
    settings = get_settings()
    Path("logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )
    logger.add(
        "logs/instagram_agents.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )

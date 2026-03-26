from __future__ import annotations
from loguru import logger
from models.post import InstagramPost


class ScraperAgent:
    def run(self, username: str, max_posts: int = 0) -> list[InstagramPost]:
        from tools.instagram_tools import _instagram_service
        logger.info(f"[ScraperAgent] Coletando posts de @{username} (max: {max_posts})")
        return _instagram_service.get_posts(username, max_posts)

from __future__ import annotations
from loguru import logger
from models.profile import InstagramProfile


class ProfileAgent:
    def run(self, username: str) -> InstagramProfile:
        from tools.instagram_tools import _instagram_service
        logger.info(f"[ProfileAgent] Coletando perfil de @{username}")
        return _instagram_service.get_profile(username)

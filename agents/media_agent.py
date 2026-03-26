from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from models.post import InstagramPost
from utils.rate_limiter import jitter_sleep

_MAX_WORKERS = 3


class MediaAgent:
    def run(self, posts: list[InstagramPost], force: bool = False) -> list[InstagramPost]:
        from tools.instagram_tools import _media_service
        total = len(posts)

        def process(item: tuple[int, InstagramPost]) -> InstagramPost:
            i, post = item
            jitter_sleep(min_s=1.0, max_s=4.0)
            logger.info(f"[MediaAgent] Baixando post {i}/{total}: {post.post_id}")
            try:
                return _media_service.download_post_media(post, force=force)
            except Exception as e:
                logger.warning(f"Erro ao baixar post {post.post_id}: {e}")
                return post

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {executor.submit(process, (i, p)): i for i, p in enumerate(posts, 1)}
            results: list[tuple[int, InstagramPost]] = []
            for future in as_completed(futures):
                results.append((futures[future], future.result()))

        results.sort(key=lambda x: x[0])
        return [p for _, p in results]

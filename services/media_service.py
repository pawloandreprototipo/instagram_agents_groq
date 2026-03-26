from __future__ import annotations
from pathlib import Path
import httpx
from loguru import logger

from models.post import InstagramPost, MediaItem


class MediaService:
    def __init__(self, posts_base_dir: Path) -> None:
        self._posts_base_dir = posts_base_dir
        self._client = httpx.Client(timeout=30, follow_redirects=True)

    def download_post_media(self, post: InstagramPost, force: bool = False) -> InstagramPost:
        post_dir = self._posts_base_dir / post.post_id
        post_dir.mkdir(parents=True, exist_ok=True)
        post.local_dir = str(post_dir)
        for index, item in enumerate(post.media_items):
            item.local_path = self._download_file(item, post_dir, index, force=force)
        return post

    def _download_file(self, item: MediaItem, directory: Path, index: int, force: bool = False) -> str | None:
        extension = "mp4" if "video" in item.media_type.value else "jpg"
        file_path = directory / f"{item.media_id}_{index}.{extension}"
        if file_path.exists() and not force:
            logger.debug(f"Ja existe, pulando: {file_path}")
            return str(file_path)
        try:
            logger.debug(f"Baixando: {item.url[:80]}...")
            response = self._client.get(item.url)
            response.raise_for_status()
            file_path.write_bytes(response.content)
            return str(file_path)
        except Exception as e:
            logger.warning(f"Falha ao baixar {item.media_id}: {e}")
            return None

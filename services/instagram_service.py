from __future__ import annotations
from pathlib import Path
from instagrapi import Client
from instagrapi.types import Media
from loguru import logger

from models.profile import InstagramProfile
from models.post import InstagramPost, MediaItem, MediaType
from utils.config import get_settings
from utils.rate_limiter import jitter_sleep


class InstagramService:
    def __init__(self, session_file: Path = Path(".instagram_session.json")) -> None:
        self._settings = get_settings()
        self._client = Client()
        self._authenticated = False
        self._session_file = session_file

    def authenticate(self) -> bool:
        try:
            if self._session_file.exists():
                logger.info("Carregando sessao salva...")
                self._client.load_settings(self._session_file)
                try:
                    self._client.account_info()
                    logger.success("Sessao restaurada com sucesso")
                    self._authenticated = True
                    return True
                except Exception:
                    logger.warning("Sessao invalida, fazendo re-login...")
                    self._client = Client()  # reseta o client antes do re-login

            logger.info("Autenticando no Instagram...")
            self._client.login(
                self._settings.instagram_username,
                self._settings.instagram_password,
            )
            self._client.dump_settings(self._session_file)
            self._authenticated = True
            logger.success("Autenticacao bem-sucedida")
            return True
        except Exception as e:
            logger.error(f"Falha na autenticacao: {e}")
            if self._session_file.exists():
                self._session_file.unlink()
                logger.warning("Sessao corrompida removida. Tente novamente.")
            return False

    def _ensure_authenticated(self) -> None:
        if not self._authenticated:
            raise RuntimeError("Nao autenticado. Chame authenticate() primeiro.")

    def get_profile(self, username: str) -> InstagramProfile:
        self._ensure_authenticated()
        logger.info(f"Buscando perfil @{username}...")
        user = self._client.user_info_by_username_v1(username)
        return InstagramProfile(
            username=user.username,
            user_id=str(user.pk),
            full_name=user.full_name or "",
            bio=user.biography or "",
            profile_url=f"https://www.instagram.com/{user.username}/",
            profile_pic_url=str(user.profile_pic_url),
            followers_count=user.follower_count or 0,
            following_count=user.following_count or 0,
            posts_count=user.media_count or 0,
            is_private=user.is_private,
            is_verified=user.is_verified,
            external_url=str(user.external_url) if user.external_url else None,
        )

    def get_posts(self, username: str, max_posts: int = 0) -> list[InstagramPost]:
        self._ensure_authenticated()
        label = f"todos os" if max_posts == 0 else f"ate {max_posts}"
        logger.info(f"Buscando {label} posts de @{username}...")
        user = self._client.user_info_by_username_v1(username)

        posts: list[InstagramPost] = []
        cursor = ""
        page_size = 33

        while True:
            fetch = page_size if max_posts == 0 else min(page_size, max_posts - len(posts))
            medias, cursor = self._client.user_medias_paginated_v1(
                user.pk, amount=fetch, end_cursor=cursor
            )
            posts.extend(self._media_to_post(m) for m in medias)
            if not cursor or (max_posts and len(posts) >= max_posts):
                break
            jitter_sleep(min_s=2.0, max_s=5.0)

        logger.success(f"Total de posts: {len(posts)}")
        return posts

    def _media_to_post(self, media: Media) -> InstagramPost:
        media_type = self._resolve_media_type(media)
        media_items = self._extract_media_items(media, media_type)
        return InstagramPost(
            post_id=str(media.pk),
            shortcode=media.code,
            caption=media.caption_text or "",
            media_type=media_type,
            media_items=media_items,
            likes_count=media.like_count or 0,
            comments_count=media.comment_count or 0,
            taken_at=media.taken_at,
            post_url=f"https://www.instagram.com/p/{media.code}/",
        )

    def _resolve_media_type(self, media: Media) -> MediaType:
        type_map = {1: MediaType.IMAGE, 2: MediaType.VIDEO, 8: MediaType.CAROUSEL}
        media_type = type_map.get(media.media_type, MediaType.IMAGE)
        if media_type == MediaType.VIDEO and getattr(media, "product_type", "") == "clips":
            return MediaType.REEL
        return media_type

    def _extract_media_items(self, media: Media, media_type: MediaType) -> list[MediaItem]:
        items: list[MediaItem] = []
        if media_type == MediaType.CAROUSEL and getattr(media, "resources", None):
            for resource in media.resources:
                item_type = MediaType.VIDEO if resource.video_url else MediaType.IMAGE
                url = str(resource.video_url or resource.thumbnail_url)
                items.append(MediaItem(media_id=str(resource.pk), url=url, media_type=item_type))
        else:
            url = str(media.video_url or media.thumbnail_url)
            items.append(MediaItem(media_id=str(media.pk), url=url, media_type=media_type))
        return items

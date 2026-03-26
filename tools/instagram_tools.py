from __future__ import annotations

_instagram_service = None
_media_service = None
_storage_service = None


def init_tools(instagram_svc, media_svc, storage_svc) -> None:
    global _instagram_service, _media_service, _storage_service
    _instagram_service = instagram_svc
    _media_service = media_svc
    _storage_service = storage_svc

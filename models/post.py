from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    REEL = "reel"


@dataclass
class MediaItem:
    media_id: str
    url: str
    media_type: MediaType
    local_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.media_id,
            "link": self.url,
            "type": self.media_type.value,
            "local_path": self.local_path,
        }


@dataclass
class InstagramPost:
    post_id: str
    shortcode: str
    caption: str
    media_type: MediaType
    media_items: list[MediaItem] = field(default_factory=list)
    likes_count: int = 0
    comments_count: int = 0
    taken_at: datetime | None = None
    post_url: str | None = None
    local_dir: str | None = None

    def to_dict(self) -> dict:
        return {
            "id_pub": self.post_id,
            "shortcode": self.shortcode,
            "post_url": self.post_url,
            "caption": self.caption,
            "media_type": self.media_type.value,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "taken_at": self.taken_at.isoformat() if self.taken_at else None,
            "local_dir": self.local_dir,
            "media": [item.to_dict() for item in self.media_items],
        }

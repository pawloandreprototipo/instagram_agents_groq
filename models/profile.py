from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class InstagramProfile:
    username: str
    user_id: str
    full_name: str
    bio: str
    profile_url: str
    profile_pic_url: str
    followers_count: int
    following_count: int
    posts_count: int
    is_private: bool
    is_verified: bool
    external_url: str | None = None
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "bio": self.bio,
            "profile_url": self.profile_url,
            "profile_pic_url": self.profile_pic_url,
            "external_url": self.external_url,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "posts_count": self.posts_count,
            "is_private": self.is_private,
            "is_verified": self.is_verified,
            "scraped_at": self.scraped_at.isoformat(),
        }

"""Testes para StorageService — cenário: save deve usar to_dict() nos modelos."""
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.post import InstagramPost, MediaItem, MediaType
from models.profile import InstagramProfile
from services.storage_service import StorageService


def make_profile() -> InstagramProfile:
    p = InstagramProfile(
        username="testuser",
        user_id="123",
        full_name="Test User",
        bio="bio aqui",
        profile_url="https://www.instagram.com/testuser/",
        profile_pic_url="https://example.com/pic.jpg",
        followers_count=100,
        following_count=50,
        posts_count=10,
        is_private=False,
        is_verified=False,
    )
    p.scraped_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return p


def make_post() -> InstagramPost:
    item = MediaItem(media_id="m1", url="https://example.com/img.jpg", media_type=MediaType.IMAGE)
    return InstagramPost(
        post_id="p1",
        shortcode="abc123",
        caption="legenda",
        media_type=MediaType.IMAGE,
        media_items=[item],
        likes_count=10,
        comments_count=2,
        post_url="https://www.instagram.com/p/abc123/",
    )


class TestStorageServiceSaveStructure:
    """Garante que save() produz JSON com a estrutura correta (chaves de to_dict)."""

    def test_profile_keys_match_to_dict(self, tmp_path):
        svc = StorageService(output_path=tmp_path / "out.json")
        profile = make_profile()
        post = make_post()
        svc.save(profile, [post])

        data = json.loads((tmp_path / "out.json").read_text())
        assert set(data["profile"].keys()) == set(profile.to_dict().keys())

    def test_post_keys_match_to_dict(self, tmp_path):
        svc = StorageService(output_path=tmp_path / "out.json")
        profile = make_profile()
        post = make_post()
        svc.save(profile, [post])

        data = json.loads((tmp_path / "out.json").read_text())
        assert set(data["posts"][0].keys()) == set(post.to_dict().keys())

    def test_media_items_serialized_as_dicts(self, tmp_path):
        """Bug atual: __dict__ serializa MediaItem como objeto, não como dict com chaves corretas."""
        svc = StorageService(output_path=tmp_path / "out.json")
        profile = make_profile()
        post = make_post()
        svc.save(profile, [post])

        data = json.loads((tmp_path / "out.json").read_text())
        media = data["posts"][0]["media"]
        assert isinstance(media, list)
        assert isinstance(media[0], dict)
        # to_dict() usa "id", "link", "type" — __dict__ usaria "media_id", "url", "media_type"
        assert "id" in media[0]
        assert "link" in media[0]
        assert "type" in media[0]

    def test_post_id_key_is_id_pub(self, tmp_path):
        """to_dict() usa 'id_pub'; __dict__ usaria 'post_id'."""
        svc = StorageService(output_path=tmp_path / "out.json")
        svc.save(make_profile(), [make_post()])
        data = json.loads((tmp_path / "out.json").read_text())
        assert "id_pub" in data["posts"][0]
        assert "post_id" not in data["posts"][0]

    def test_returns_output_path(self, tmp_path):
        svc = StorageService(output_path=tmp_path / "out.json")
        result = svc.save(make_profile(), [make_post()])
        assert result == tmp_path / "out.json"

    def test_file_is_valid_utf8_json(self, tmp_path):
        svc = StorageService(output_path=tmp_path / "out.json")
        svc.save(make_profile(), [make_post()])
        content = (tmp_path / "out.json").read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "profile" in parsed
        assert "posts" in parsed

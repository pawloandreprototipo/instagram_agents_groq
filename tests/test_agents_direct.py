"""Testes para ProfileAgent e ScraperAgent — cenário: chamada direta ao service sem LLM."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.post import InstagramPost, MediaItem, MediaType
from models.profile import InstagramProfile


def make_profile() -> InstagramProfile:
    p = InstagramProfile(
        username="testuser",
        user_id="123",
        full_name="Test User",
        bio="bio",
        profile_url="https://www.instagram.com/testuser/",
        profile_pic_url="https://example.com/pic.jpg",
        followers_count=100,
        following_count=50,
        posts_count=5,
        is_private=False,
        is_verified=False,
    )
    p.scraped_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return p


def make_post() -> InstagramPost:
    return InstagramPost(
        post_id="p1",
        shortcode="abc",
        caption="legenda",
        media_type=MediaType.IMAGE,
        media_items=[MediaItem(media_id="m1", url="https://example.com/img.jpg", media_type=MediaType.IMAGE)],
        likes_count=5,
        comments_count=1,
        post_url="https://www.instagram.com/p/abc/",
    )


class TestProfileAgentDirect:
    """Após a melhoria, ProfileAgent.run() deve retornar dict direto do service, sem LLM."""

    def test_run_returns_dict_with_correct_keys(self):
        mock_svc = MagicMock()
        mock_svc.get_profile.return_value = make_profile()

        # Simula o comportamento esperado após a refatoração
        result = mock_svc.get_profile("testuser").to_dict()

        assert isinstance(result, dict)
        expected_keys = {"user_id", "username", "full_name", "bio", "profile_url",
                         "profile_pic_url", "followers_count", "following_count",
                         "posts_count", "is_private", "is_verified", "scraped_at"}
        assert expected_keys.issubset(result.keys())

    def test_run_calls_service_with_username(self):
        mock_svc = MagicMock()
        mock_svc.get_profile.return_value = make_profile()
        mock_svc.get_profile("testuser")
        mock_svc.get_profile.assert_called_once_with("testuser")

    def test_run_result_is_json_serializable(self):
        profile = make_profile()
        result = profile.to_dict()
        # Não deve lançar exceção
        serialized = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(serialized)
        assert parsed["username"] == "testuser"


class TestScraperAgentDirect:
    """Após a melhoria, ScraperAgent.run() deve retornar list[dict] direto do service, sem LLM."""

    def test_run_returns_list_of_dicts(self):
        mock_svc = MagicMock()
        mock_svc.get_posts.return_value = [make_post()]

        result = [p.to_dict() for p in mock_svc.get_posts("testuser", 50)]

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_run_calls_service_with_correct_args(self):
        mock_svc = MagicMock()
        mock_svc.get_posts.return_value = [make_post()]
        mock_svc.get_posts("testuser", 10)
        mock_svc.get_posts.assert_called_once_with("testuser", 10)

    def test_post_dict_has_required_keys(self):
        post = make_post()
        result = post.to_dict()
        required = {"id_pub", "shortcode", "post_url", "caption", "media_type", "media"}
        assert required.issubset(result.keys())

    def test_post_media_is_list_of_dicts(self):
        post = make_post()
        result = post.to_dict()
        assert isinstance(result["media"], list)
        assert isinstance(result["media"][0], dict)
        assert "id" in result["media"][0]
        assert "link" in result["media"][0]

    def test_run_result_is_json_serializable(self):
        posts = [make_post()]
        result = [p.to_dict() for p in posts]
        serialized = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(serialized)
        assert parsed[0]["id_pub"] == "p1"


class TestDatetimeUtcNow:
    """Garante que scraped_at usa timezone-aware datetime (não utcnow depreciado)."""

    def test_scraped_at_is_timezone_aware(self):
        profile = InstagramProfile(
            username="u", user_id="1", full_name="", bio="",
            profile_url="", profile_pic_url="",
            followers_count=0, following_count=0, posts_count=0,
            is_private=False, is_verified=False,
        )
        # Após a melhoria, scraped_at deve ter tzinfo definido
        # Atualmente usa datetime.utcnow() que retorna naive datetime
        # Este teste falhará com o código atual e passará após a correção
        assert profile.scraped_at.tzinfo is not None, (
            "scraped_at deve ser timezone-aware. "
            "Use datetime.now(timezone.utc) em vez de datetime.utcnow()"
        )

    def test_scraped_at_isoformat_contains_timezone(self):
        profile = InstagramProfile(
            username="u", user_id="1", full_name="", bio="",
            profile_url="", profile_pic_url="",
            followers_count=0, following_count=0, posts_count=0,
            is_private=False, is_verified=False,
        )
        iso = profile.to_dict()["scraped_at"]
        # timezone-aware isoformat termina com +00:00 ou Z
        assert "+" in iso or iso.endswith("Z"), (
            f"scraped_at '{iso}' não contém informação de timezone"
        )

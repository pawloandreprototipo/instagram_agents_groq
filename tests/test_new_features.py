"""Testes para: output por username, paginação e force_download."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.post import InstagramPost, MediaItem, MediaType
from models.profile import InstagramProfile


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_media_item(media_id="m1", media_type=MediaType.IMAGE) -> MediaItem:
    return MediaItem(media_id=media_id, url=f"https://example.com/{media_id}.jpg", media_type=media_type)


def make_post(post_id="p1", items=None) -> InstagramPost:
    return InstagramPost(
        post_id=post_id,
        shortcode=post_id,
        caption="",
        media_type=MediaType.IMAGE,
        media_items=items or [make_media_item()],
    )


def make_profile(username="testuser") -> InstagramProfile:
    p = InstagramProfile(
        username=username, user_id="1", full_name="", bio="",
        profile_url="", profile_pic_url="",
        followers_count=0, following_count=0, posts_count=0,
        is_private=False, is_verified=False,
    )
    p.scraped_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return p


# ---------------------------------------------------------------------------
# 1. Output por username
# ---------------------------------------------------------------------------

class TestOutputPerUsername:
    """output/{username}/posts e output/{username}/profile_data.json"""

    def test_posts_dir_includes_username(self, tmp_path):
        from utils.config import Settings
        s = Settings(
            groq_api_key="x", instagram_username="user", instagram_password="pass",
            output_dir=str(tmp_path),
        )
        assert s.posts_dir(username="cris.agra") == tmp_path / "cris.agra" / "posts"

    def test_json_output_path_includes_username(self, tmp_path):
        from utils.config import Settings
        s = Settings(
            groq_api_key="x", instagram_username="user", instagram_password="pass",
            output_dir=str(tmp_path),
        )
        assert s.json_output_path(username="cris.agra") == tmp_path / "cris.agra" / "profile_data.json"

    def test_media_service_uses_username_dir(self, tmp_path):
        from services.media_service import MediaService
        svc = MediaService(posts_base_dir=tmp_path / "cris.agra" / "posts")
        with patch("httpx.Client") as mock_cls:
            inst = MagicMock()
            inst.get.return_value = MagicMock(content=b"data")
            mock_cls.return_value = inst
            svc = MediaService(posts_base_dir=tmp_path / "cris.agra" / "posts")
            post = make_post("p1")
            svc.download_post_media(post)
        assert (tmp_path / "cris.agra" / "posts" / "p1").is_dir()

    def test_storage_service_saves_in_username_dir(self, tmp_path):
        from services.storage_service import StorageService
        output = tmp_path / "cris.agra" / "profile_data.json"
        svc = StorageService(output_path=output)
        svc.save(make_profile("cris.agra"), [make_post()])
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["profile"]["username"] == "cris.agra"


# ---------------------------------------------------------------------------
# 2. Paginação em get_posts
# ---------------------------------------------------------------------------

class TestGetPostsPagination:
    """get_posts deve usar user_medias_paginated_v1 e iterar páginas."""

    def _make_service(self):
        with patch("services.instagram_service.get_settings") as mock_cfg:
            mock_cfg.return_value.instagram_username = "u"
            mock_cfg.return_value.instagram_password = "p"
            from services.instagram_service import InstagramService
            svc = InstagramService.__new__(InstagramService)
            svc._authenticated = True
            svc._client = MagicMock()
            return svc

    def _make_fake_media(self, pk: str):
        m = MagicMock()
        m.pk = pk
        m.code = f"code_{pk}"
        m.caption_text = ""
        m.media_type = 1
        m.like_count = 0
        m.comment_count = 0
        m.taken_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        m.video_url = None
        m.thumbnail_url = f"https://example.com/{pk}.jpg"
        m.resources = None
        return m

    def test_fetches_all_posts_when_max_is_zero(self):
        """max_posts=0 deve buscar todas as páginas até next_cursor vazio."""
        svc = self._make_service()
        page1 = [self._make_fake_media("1"), self._make_fake_media("2")]
        page2 = [self._make_fake_media("3")]

        svc._client.user_medias_paginated_v1.side_effect = [
            (page1, "cursor1"),
            (page2, ""),
        ]
        svc._client.user_info_by_username_v1.return_value = MagicMock(pk="999")

        posts = svc.get_posts("user", max_posts=0)
        assert len(posts) == 3
        assert svc._client.user_medias_paginated_v1.call_count == 2

    def test_respects_max_posts_limit_across_pages(self):
        """max_posts=2 deve parar após coletar 2 posts mesmo com mais páginas."""
        svc = self._make_service()
        page1 = [self._make_fake_media("1"), self._make_fake_media("2")]
        page2 = [self._make_fake_media("3")]

        svc._client.user_medias_paginated_v1.side_effect = [
            (page1, "cursor1"),
            (page2, ""),
        ]
        svc._client.user_info_by_username_v1.return_value = MagicMock(pk="999")

        posts = svc.get_posts("user", max_posts=2)
        assert len(posts) == 2
        # Não deve ter buscado a segunda página
        assert svc._client.user_medias_paginated_v1.call_count == 1

    def test_passes_cursor_between_pages(self):
        """O cursor da página anterior deve ser passado para a próxima."""
        svc = self._make_service()
        page1 = [self._make_fake_media("1")]
        page2 = [self._make_fake_media("2")]

        svc._client.user_medias_paginated_v1.side_effect = [
            (page1, "cursor_abc"),
            (page2, ""),
        ]
        svc._client.user_info_by_username_v1.return_value = MagicMock(pk="999")

        svc.get_posts("user", max_posts=0)

        calls = svc._client.user_medias_paginated_v1.call_args_list
        assert calls[0][1]["end_cursor"] == ""
        assert calls[1][1]["end_cursor"] == "cursor_abc"

    def test_single_page_no_cursor(self):
        """Quando não há próxima página, deve retornar apenas os posts da primeira."""
        svc = self._make_service()
        page1 = [self._make_fake_media("1"), self._make_fake_media("2")]

        svc._client.user_medias_paginated_v1.return_value = (page1, "")
        svc._client.user_info_by_username_v1.return_value = MagicMock(pk="999")

        posts = svc.get_posts("user", max_posts=0)
        assert len(posts) == 2
        assert svc._client.user_medias_paginated_v1.call_count == 1


# ---------------------------------------------------------------------------
# 3. force_download
# ---------------------------------------------------------------------------

class TestForceDownload:
    """force_download=False deve pular arquivos existentes; True deve re-baixar."""

    def test_skips_existing_file_when_force_false(self, tmp_path):
        from services.media_service import MediaService
        with patch("httpx.Client") as mock_cls:
            inst = MagicMock()
            mock_cls.return_value = inst
            svc = MediaService(posts_base_dir=tmp_path)

        post_dir = tmp_path / "p1"
        post_dir.mkdir()
        existing = post_dir / "m1_0.jpg"
        existing.write_bytes(b"cached")

        post = make_post("p1")
        svc.download_post_media(post, force=False)
        inst.get.assert_not_called()

    def test_redownloads_existing_file_when_force_true(self, tmp_path):
        from services.media_service import MediaService
        with patch("httpx.Client") as mock_cls:
            inst = MagicMock()
            inst.get.return_value = MagicMock(content=b"new_data")
            mock_cls.return_value = inst
            svc = MediaService(posts_base_dir=tmp_path)

        post_dir = tmp_path / "p1"
        post_dir.mkdir()
        existing = post_dir / "m1_0.jpg"
        existing.write_bytes(b"old_data")

        post = make_post("p1")
        svc.download_post_media(post, force=True)
        inst.get.assert_called_once()
        assert existing.read_bytes() == b"new_data"

    def test_downloads_new_file_regardless_of_force(self, tmp_path):
        """Arquivo inexistente deve ser baixado independente do force."""
        from services.media_service import MediaService
        with patch("httpx.Client") as mock_cls:
            inst = MagicMock()
            inst.get.return_value = MagicMock(content=b"data")
            mock_cls.return_value = inst
            svc = MediaService(posts_base_dir=tmp_path)

        post = make_post("p1")
        result = svc.download_post_media(post, force=False)
        inst.get.assert_called_once()
        assert result.media_items[0].local_path is not None

    def test_media_agent_passes_force_to_service(self, tmp_path):
        """MediaAgent deve repassar o parâmetro force ao MediaService."""
        from agents.media_agent import MediaAgent
        from models.post import InstagramPost, MediaItem, MediaType

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = lambda post, force=False: (
            setattr(post, "local_dir", str(tmp_path / post.post_id)) or post
        )

        post = InstagramPost(
            post_id="p1", shortcode="p1", caption="", media_type=MediaType.IMAGE,
            media_items=[MediaItem(media_id="m1", url="https://x.com/img.jpg", media_type=MediaType.IMAGE)],
        )

        with patch("tools.instagram_tools._media_service", mock_svc):
            MediaAgent().run([post], force=True)

        _, kwargs = mock_svc.download_post_media.call_args
        assert kwargs.get("force") is True

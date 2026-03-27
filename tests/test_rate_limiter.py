"""Testes para o mecanismo de delay/jitter entre requisições ao Instagram."""
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRateLimiter:
    """Testa o utilitário de delay com jitter."""

    def test_sleep_is_called_with_value_in_range(self):
        from utils.rate_limiter import jitter_sleep
        with patch("time.sleep") as mock_sleep:
            jitter_sleep(min_s=1.0, max_s=3.0)
        mock_sleep.assert_called_once()
        slept = mock_sleep.call_args[0][0]
        assert 1.0 <= slept <= 3.0

    def test_different_calls_produce_different_values(self):
        from utils.rate_limiter import jitter_sleep
        values = []
        with patch("time.sleep") as mock_sleep:
            for _ in range(20):
                jitter_sleep(min_s=0.5, max_s=5.0)
                values.append(mock_sleep.call_args[0][0])
        # Com 20 amostras num range de 4.5s, é estatisticamente impossível todos serem iguais
        assert len(set(round(v, 3) for v in values)) > 1

    def test_min_equals_max_sleeps_exact_value(self):
        from utils.rate_limiter import jitter_sleep
        with patch("time.sleep") as mock_sleep:
            jitter_sleep(min_s=2.0, max_s=2.0)
        assert mock_sleep.call_args[0][0] == pytest.approx(2.0)


class TestPaginationDelay:
    """Garante que há delay entre páginas na paginação de posts."""

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

    def test_delay_called_between_pages(self):
        """jitter_sleep deve ser chamado uma vez entre as duas páginas."""
        svc = self._make_service()
        page1 = [self._make_fake_media("1")]
        page2 = [self._make_fake_media("2")]
        svc._client.user_medias_paginated_v1.side_effect = [
            (page1, "cursor1"),
            (page2, ""),
        ]
        svc._client.user_info_by_username_v1.return_value = MagicMock(pk="999")

        with patch("services.instagram_service.jitter_sleep") as mock_jitter:
            svc.get_posts("user", max_posts=0)

        # 1 delay entre as 2 páginas
        assert mock_jitter.call_count == 1

    def test_no_delay_on_single_page(self):
        """Com uma única página, não deve haver delay."""
        svc = self._make_service()
        svc._client.user_medias_paginated_v1.return_value = (
            [self._make_fake_media("1")], ""
        )
        svc._client.user_info_by_username_v1.return_value = MagicMock(pk="999")

        with patch("services.instagram_service.jitter_sleep") as mock_jitter:
            svc.get_posts("user", max_posts=0)

        mock_jitter.assert_not_called()

    def test_delay_called_n_minus_1_times_for_n_pages(self):
        """Para N páginas deve haver N-1 delays."""
        svc = self._make_service()
        pages = [([ self._make_fake_media(str(i))], f"c{i}") for i in range(4)]
        pages[-1] = (pages[-1][0], "")  # última página sem cursor
        svc._client.user_medias_paginated_v1.side_effect = pages
        svc._client.user_info_by_username_v1.return_value = MagicMock(pk="999")

        with patch("services.instagram_service.jitter_sleep") as mock_jitter:
            svc.get_posts("user", max_posts=0)

        assert mock_jitter.call_count == 3  # 4 páginas → 3 delays


class TestMediaDownloadDelay:
    """Garante que há delay entre downloads de posts no MediaAgent."""

    def test_delay_called_between_posts(self, tmp_path):
        from agents.media_agent import MediaAgent
        from models.post import InstagramPost, MediaItem, MediaType

        def fake_download(post, force=False):
            post.local_dir = str(tmp_path / post.post_id)
            return post

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = fake_download

        posts = [
            InstagramPost(
                post_id=f"p{i}", shortcode=f"p{i}", caption="",
                media_type=MediaType.IMAGE,
                media_items=[MediaItem(media_id="m1", url="https://x.com/img.jpg", media_type=MediaType.IMAGE)],
            )
            for i in range(3)
        ]

        with patch("tools.instagram_tools._media_service", mock_svc), \
             patch("agents.media_agent.jitter_sleep") as mock_jitter:
            MediaAgent().run(posts)

        assert mock_jitter.call_count >= 1

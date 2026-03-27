"""Testes para MediaAgent — cobre download paralelo e isolamento de erros."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.post import InstagramPost, MediaItem, MediaType


def make_post(post_id="p1") -> InstagramPost:
    return InstagramPost(
        post_id=post_id, shortcode=post_id, caption="",
        media_type=MediaType.IMAGE,
        media_items=[MediaItem(media_id="m1", url="https://example.com/img.jpg", media_type=MediaType.IMAGE)],
    )


class TestMediaAgentRun:

    def test_run_returns_list_of_posts(self, tmp_path):
        from agents.media_agent import MediaAgent
        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = lambda post, force=False: (
            setattr(post, "local_dir", str(tmp_path / post.post_id)) or post
        )
        with patch("tools.instagram_tools._media_service", mock_svc):
            result = MediaAgent().run([make_post("p1")])
        assert isinstance(result, list)
        assert isinstance(result[0], InstagramPost)

    def test_run_sets_local_dir(self, tmp_path):
        from agents.media_agent import MediaAgent

        def fake_download(post, force=False):
            post.local_dir = str(tmp_path / post.post_id)
            return post

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = fake_download
        with patch("tools.instagram_tools._media_service", mock_svc):
            result = MediaAgent().run([make_post("p1")])
        assert result[0].local_dir == str(tmp_path / "p1")

    def test_run_continues_on_single_post_error(self, tmp_path):
        from agents.media_agent import MediaAgent
        call_count = 0

        def fake_download(post, force=False):
            nonlocal call_count
            call_count += 1
            if post.post_id == "p1":
                raise Exception("erro simulado")
            post.local_dir = str(tmp_path / post.post_id)
            return post

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = fake_download
        with patch("tools.instagram_tools._media_service", mock_svc):
            result = MediaAgent().run([make_post("p1"), make_post("p2")])

        assert len(result) == 2
        assert call_count == 2
        assert result[1].local_dir == str(tmp_path / "p2")

    def test_run_parallel_all_posts_processed(self, tmp_path):
        from agents.media_agent import MediaAgent

        def fake_download(post, force=False):
            post.local_dir = str(tmp_path / post.post_id)
            return post

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = fake_download
        with patch("tools.instagram_tools._media_service", mock_svc):
            result = MediaAgent().run([make_post(f"p{i}") for i in range(5)])

        assert len(result) == 5
        assert mock_svc.download_post_media.call_count == 5

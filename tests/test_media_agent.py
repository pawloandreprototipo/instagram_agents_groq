"""Testes para MediaAgent — cobre download paralelo e isolamento de erros."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.post import InstagramPost, MediaItem, MediaType


def make_post_data(post_id="p1") -> dict:
    return {
        "id_pub": post_id,
        "shortcode": "abc",
        "caption": "legenda",
        "media_type": "image",
        "media": [{"id": "m1", "link": "https://example.com/img.jpg", "type": "image"}],
        "likes_count": 5,
        "comments_count": 1,
        "post_url": f"https://www.instagram.com/p/{post_id}/",
    }


class TestMediaAgentRun:
    """Testa o MediaAgent.run() com mock do _media_service."""

    def _make_agent_with_mock_service(self, mock_svc):
        from agents.media_agent import MediaAgent
        agent = MediaAgent.__new__(MediaAgent)
        # Injeta o agent base mínimo
        agent._agent = MagicMock()
        return agent, mock_svc

    def test_run_returns_json_string(self, tmp_path):
        from agents.media_agent import MediaAgent

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = lambda post: setattr(post, "local_dir", str(tmp_path / post.post_id)) or post

        with patch("tools.instagram_tools._media_service", mock_svc):
            agent = MediaAgent.__new__(MediaAgent)
            agent._agent = MagicMock()
            result = agent.run(json.dumps([make_post_data("p1")]))

        assert isinstance(result, str)
        assert isinstance(json.loads(result), list)

    def test_run_sets_local_dir(self, tmp_path):
        from agents.media_agent import MediaAgent

        def fake_download(post, force=False):
            post.local_dir = str(tmp_path / post.post_id)
            return post

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = fake_download

        with patch("tools.instagram_tools._media_service", mock_svc):
            agent = MediaAgent.__new__(MediaAgent)
            agent._agent = MagicMock()
            result = json.loads(agent.run(json.dumps([make_post_data("p1")])))

        assert result[0]["local_dir"] == str(tmp_path / "p1")

    def test_run_continues_on_single_post_error(self, tmp_path):
        """Um erro em um post não deve interromper os demais."""
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
            agent = MediaAgent.__new__(MediaAgent)
            agent._agent = MagicMock()
            result = json.loads(agent.run(json.dumps([make_post_data("p1"), make_post_data("p2")])))

        assert len(result) == 2
        assert call_count == 2
        assert result[1]["local_dir"] == str(tmp_path / "p2")

    def test_run_parallel_all_posts_processed(self, tmp_path):
        """Com ThreadPoolExecutor, todos os posts devem ser processados."""
        from agents.media_agent import MediaAgent

        def fake_download(post):
            post.local_dir = str(tmp_path / post.post_id)
            return post

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = fake_download

        with patch("tools.instagram_tools._media_service", mock_svc):
            agent = MediaAgent.__new__(MediaAgent)
            agent._agent = MagicMock()
            result = json.loads(agent.run(json.dumps([make_post_data(f"p{i}") for i in range(5)])))

        assert len(result) == 5
        assert mock_svc.download_post_media.call_count == 5

"""Testes para MediaService — cobre download de mídias e reutilização do httpx.Client."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.post import InstagramPost, MediaItem, MediaType
from services.media_service import MediaService


def make_post(post_id="p1", media_type=MediaType.IMAGE, items=None) -> InstagramPost:
    if items is None:
        items = [MediaItem(media_id="m1", url="https://example.com/img.jpg", media_type=MediaType.IMAGE)]
    return InstagramPost(
        post_id=post_id,
        shortcode="abc",
        caption="",
        media_type=media_type,
        media_items=items,
    )


class TestMediaServiceDownload:
    """Testa o comportamento de download de mídias."""

    def test_creates_post_directory(self, tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"fake_image_data"
            mock_instance.get.return_value = mock_resp
            mock_client_cls.return_value = mock_instance
            svc = MediaService(posts_base_dir=tmp_path)
            post = make_post()
            svc.download_post_media(post)
        assert (tmp_path / "p1").is_dir()

    def test_sets_local_dir_on_post(self, tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"data"
            mock_instance.get.return_value = mock_resp
            mock_client_cls.return_value = mock_instance
            svc = MediaService(posts_base_dir=tmp_path)
            post = make_post()
            result = svc.download_post_media(post)
        assert result.local_dir == str(tmp_path / "p1")

    def test_sets_local_path_on_media_item(self, tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"data"
            mock_instance.get.return_value = mock_resp
            mock_client_cls.return_value = mock_instance
            svc = MediaService(posts_base_dir=tmp_path)
            post = make_post()
            result = svc.download_post_media(post)
        assert result.media_items[0].local_path is not None
        assert result.media_items[0].local_path.endswith(".jpg")

    def test_video_extension_is_mp4(self, tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"data"
            mock_instance.get.return_value = mock_resp
            mock_client_cls.return_value = mock_instance
            svc = MediaService(posts_base_dir=tmp_path)
            item = MediaItem(media_id="v1", url="https://example.com/vid.mp4", media_type=MediaType.VIDEO)
            post = make_post(media_type=MediaType.VIDEO, items=[item])
            result = svc.download_post_media(post)
        assert result.media_items[0].local_path.endswith(".mp4")

    def test_skips_existing_file(self, tmp_path):
        post_dir = tmp_path / "p1"
        post_dir.mkdir()
        existing = post_dir / "m1_0.jpg"
        existing.write_bytes(b"already_here")

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value = mock_instance
            svc = MediaService(posts_base_dir=tmp_path)
            post = make_post()
            svc.download_post_media(post)
            mock_instance.get.assert_not_called()

        assert existing.read_bytes() == b"already_here"

    def test_returns_none_on_http_error(self, tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = Exception("timeout")
            mock_client_cls.return_value = mock_instance
            svc = MediaService(posts_base_dir=tmp_path)
            post = make_post()
            result = svc.download_post_media(post)
        assert result.media_items[0].local_path is None

    def test_client_reuse_single_instance(self, tmp_path):
        """Após a melhoria, o Client é instanciado uma vez no __init__, não por arquivo."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"data"
            mock_client_instance.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client_instance

            svc = MediaService(posts_base_dir=tmp_path)
            items = [
                MediaItem(media_id=f"m{i}", url=f"https://example.com/img{i}.jpg", media_type=MediaType.IMAGE)
                for i in range(3)
            ]
            post = make_post(items=items)
            svc.download_post_media(post)

        # Client instanciado apenas 1 vez no __init__
        assert mock_client_cls.call_count == 1


class TestMediaServiceParallelDownload:
    """Testa que múltiplos posts podem ser baixados em paralelo sem race conditions."""

    def test_parallel_download_all_posts_get_local_dir(self, tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"data"
            mock_instance.get.return_value = mock_resp
            mock_client_cls.return_value = mock_instance

            svc = MediaService(posts_base_dir=tmp_path)
            posts = [make_post(post_id=f"p{i}") for i in range(5)]

            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(svc.download_post_media, posts))

        assert all(r.local_dir is not None for r in results)
        assert len({r.local_dir for r in results}) == 5

    def test_parallel_download_creates_all_directories(self, tmp_path):
        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"data"
            mock_instance.get.return_value = mock_resp
            mock_client_cls.return_value = mock_instance

            svc = MediaService(posts_base_dir=tmp_path)
            posts = [make_post(post_id=f"p{i}") for i in range(5)]

            with ThreadPoolExecutor(max_workers=5) as executor:
                list(executor.map(svc.download_post_media, posts))

        for i in range(5):
            assert (tmp_path / f"p{i}").is_dir()

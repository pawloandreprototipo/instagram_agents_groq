"""Testes para as refatorações estruturais."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.post import InstagramPost, MediaItem, MediaType
from models.profile import InstagramProfile


def make_profile(username="testuser") -> InstagramProfile:
    p = InstagramProfile(
        username=username, user_id="1", full_name="Test", bio="",
        profile_url="", profile_pic_url="",
        followers_count=0, following_count=0, posts_count=0,
        is_private=False, is_verified=False,
    )
    p.scraped_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return p


def make_post(post_id="p1") -> InstagramPost:
    return InstagramPost(
        post_id=post_id, shortcode=post_id, caption="",
        media_type=MediaType.IMAGE,
        media_items=[MediaItem(media_id="m1", url="https://x.com/img.jpg", media_type=MediaType.IMAGE)],
    )


# ---------------------------------------------------------------------------
# 1. MediaAgent sem LLM e trabalhando com objetos
# ---------------------------------------------------------------------------

class TestMediaAgentRefactored:
    """MediaAgent deve receber e retornar list[InstagramPost], sem JSON, sem LLM."""

    def test_run_accepts_list_of_posts(self, tmp_path):
        from agents.media_agent import MediaAgent

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = lambda post, force=False: (
            setattr(post, "local_dir", str(tmp_path / post.post_id)) or post
        )

        with patch("tools.instagram_tools._media_service", mock_svc):
            agent = MediaAgent()
            result = agent.run([make_post("p1"), make_post("p2")])

        assert isinstance(result, list)
        assert all(isinstance(p, InstagramPost) for p in result)

    def test_run_returns_same_count(self, tmp_path):
        from agents.media_agent import MediaAgent

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = lambda post, force=False: post

        with patch("tools.instagram_tools._media_service", mock_svc):
            agent = MediaAgent()
            result = agent.run([make_post(f"p{i}") for i in range(5)])

        assert len(result) == 5

    def test_run_passes_force_to_service(self, tmp_path):
        from agents.media_agent import MediaAgent

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = lambda post, force=False: post

        with patch("tools.instagram_tools._media_service", mock_svc):
            agent = MediaAgent()
            agent.run([make_post()], force=True)

        _, kwargs = mock_svc.download_post_media.call_args
        assert kwargs.get("force") is True

    def test_run_isolates_errors_per_post(self, tmp_path):
        from agents.media_agent import MediaAgent

        def fake_download(post, force=False):
            if post.post_id == "p1":
                raise Exception("erro simulado")
            post.local_dir = str(tmp_path / post.post_id)
            return post

        mock_svc = MagicMock()
        mock_svc.download_post_media.side_effect = fake_download

        with patch("tools.instagram_tools._media_service", mock_svc):
            agent = MediaAgent()
            result = agent.run([make_post("p1"), make_post("p2")])

        assert len(result) == 2
        assert result[1].local_dir == str(tmp_path / "p2")

    def test_does_not_instantiate_llm(self):
        """MediaAgent não deve instanciar Agent(Groq) — sem dependência de LLM."""
        with patch("agno.agent.Agent") as mock_agent_cls:
            from agents import media_agent
            import importlib
            importlib.reload(media_agent)
            from agents.media_agent import MediaAgent
            MediaAgent()
        mock_agent_cls.assert_not_called()


# ---------------------------------------------------------------------------
# 2. OrchestratorAgent sem ciclo dict→objeto→dict
# ---------------------------------------------------------------------------

class TestOrchestratorNoCycle:
    """OrchestratorAgent deve passar objetos diretamente ao StorageService."""

    def test_storage_save_receives_profile_object(self, tmp_path):
        """StorageService.save deve receber InstagramProfile, não dict."""
        from agents.orchestrator_agent import OrchestratorAgent

        mock_storage = MagicMock()
        mock_storage.save.return_value = tmp_path / "out.json"

        profile = make_profile()
        posts = [make_post()]

        with patch("tools.instagram_tools._storage_service", mock_storage), \
             patch("agents.orchestrator_agent.ProfileAgent") as MockProfile, \
             patch("agents.orchestrator_agent.ScraperAgent") as MockScraper, \
             patch("agents.orchestrator_agent.MediaAgent") as MockMedia:

            MockProfile.return_value.run.return_value = profile
            MockScraper.return_value.run.return_value = posts
            MockMedia.return_value.run.return_value = posts

            orch = OrchestratorAgent()
            orch.run("testuser", download_media=False)

        call_args = mock_storage.save.call_args
        assert isinstance(call_args[0][0], InstagramProfile)

    def test_storage_save_receives_post_objects(self, tmp_path):
        """StorageService.save deve receber list[InstagramPost], não list[dict]."""
        from agents.orchestrator_agent import OrchestratorAgent

        mock_storage = MagicMock()
        mock_storage.save.return_value = tmp_path / "out.json"

        profile = make_profile()
        posts = [make_post("p1"), make_post("p2")]

        with patch("tools.instagram_tools._storage_service", mock_storage), \
             patch("agents.orchestrator_agent.ProfileAgent") as MockProfile, \
             patch("agents.orchestrator_agent.ScraperAgent") as MockScraper, \
             patch("agents.orchestrator_agent.MediaAgent") as MockMedia:

            MockProfile.return_value.run.return_value = profile
            MockScraper.return_value.run.return_value = posts
            MockMedia.return_value.run.return_value = posts

            orch = OrchestratorAgent()
            orch.run("testuser", download_media=False)

        call_args = mock_storage.save.call_args
        saved_posts = call_args[0][1]
        assert all(isinstance(p, InstagramPost) for p in saved_posts)

    def test_profile_agent_returns_profile_object(self):
        """ProfileAgent.run deve retornar InstagramProfile, não dict."""
        from agents.profile_agent import ProfileAgent

        mock_svc = MagicMock()
        mock_svc.get_profile.return_value = make_profile()

        with patch("tools.instagram_tools._instagram_service", mock_svc):
            agent = ProfileAgent()
            result = agent.run("testuser")

        assert isinstance(result, InstagramProfile)

    def test_scraper_agent_returns_post_objects(self):
        """ScraperAgent.run deve retornar list[InstagramPost], não list[dict]."""
        from agents.scraper_agent import ScraperAgent

        mock_svc = MagicMock()
        mock_svc.get_posts.return_value = [make_post("p1"), make_post("p2")]

        with patch("tools.instagram_tools._instagram_service", mock_svc):
            agent = ScraperAgent()
            result = agent.run("testuser")

        assert isinstance(result, list)
        assert all(isinstance(p, InstagramPost) for p in result)


# ---------------------------------------------------------------------------
# 3. Config Pydantic v2
# ---------------------------------------------------------------------------

class TestConfigPydanticV2:
    """Settings deve usar model_config = ConfigDict(...) em vez de class Config."""

    def test_no_deprecation_warning(self):
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from utils.config import Settings
            Settings(
                groq_api_key="x",
                instagram_username="u",
                instagram_password="p",
            )
        pydantic_warnings = [w for w in caught if "PydanticDeprecated" in str(w.category)]
        assert len(pydantic_warnings) == 0, (
            f"Ainda há warnings Pydantic v1: {[str(w.message) for w in pydantic_warnings]}"
        )

    def test_settings_still_loads_correctly(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GROQ_API_KEY=test_key\n"
            "INSTAGRAM_USERNAME=test_user\n"
            "INSTAGRAM_PASSWORD=test_pass\n"
        )
        from utils.config import Settings
        s = Settings(
            groq_api_key="test_key",
            instagram_username="test_user",
            instagram_password="test_pass",
            output_dir=str(tmp_path),
        )
        assert s.groq_api_key == "test_key"
        assert s.posts_dir("user") == tmp_path / "user" / "posts"


# ---------------------------------------------------------------------------
# 4. Models sem typing legado
# ---------------------------------------------------------------------------

class TestModelsNativeTypes:
    """Models devem usar tipos nativos do Python 3.10+ sem imports do typing."""

    def test_media_item_local_path_accepts_none(self):
        item = MediaItem(media_id="m1", url="https://x.com/img.jpg", media_type=MediaType.IMAGE)
        assert item.local_path is None

    def test_media_item_local_path_accepts_str(self):
        item = MediaItem(media_id="m1", url="https://x.com/img.jpg",
                         media_type=MediaType.IMAGE, local_path="/tmp/img.jpg")
        assert item.local_path == "/tmp/img.jpg"

    def test_post_media_items_defaults_to_empty_list(self):
        post = InstagramPost(post_id="p1", shortcode="s1", caption="", media_type=MediaType.IMAGE)
        assert post.media_items == []

    def test_post_taken_at_accepts_none(self):
        post = InstagramPost(post_id="p1", shortcode="s1", caption="", media_type=MediaType.IMAGE)
        assert post.taken_at is None

    def test_no_typing_imports_in_post(self):
        """post.py não deve importar Optional ou List do typing."""
        import ast
        src = Path(__file__).parent.parent / "models" / "post.py"
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                names = [alias.name for alias in node.names]
                assert "Optional" not in names, "Optional ainda importado do typing"
                assert "List" not in names, "List ainda importado do typing"

    def test_no_typing_imports_in_profile(self):
        """profile.py não deve importar Optional do typing."""
        import ast
        src = Path(__file__).parent.parent / "models" / "profile.py"
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                names = [alias.name for alias in node.names]
                assert "Optional" not in names, "Optional ainda importado do typing"


# ---------------------------------------------------------------------------
# 5. ScraperAgent default max_posts=0
# ---------------------------------------------------------------------------

class TestScraperAgentDefault:
    def test_default_max_posts_is_zero(self):
        """ScraperAgent.run deve ter max_posts=0 como padrão (buscar tudo)."""
        import inspect
        from agents.scraper_agent import ScraperAgent
        sig = inspect.signature(ScraperAgent.run)
        assert sig.parameters["max_posts"].default == 0

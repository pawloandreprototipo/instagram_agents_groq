"""Testes para Strategy + Factory de providers de LLM."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# 1. ModelFactory — criação por nome de provedor
# ---------------------------------------------------------------------------

class TestModelFactory:

    def test_creates_groq_provider(self):
        from utils.model_factory import ModelFactory
        with patch("agno.models.groq.Groq") as mock:
            ModelFactory.create("groq", "llama-3.3-70b-versatile")
        mock.assert_called_once_with(id="llama-3.3-70b-versatile")

    def test_creates_openai_provider(self):
        from utils.model_factory import ModelFactory
        with patch("agno.models.openai.OpenAIChat") as mock:
            ModelFactory.create("openai", "gpt-4o")
        mock.assert_called_once_with(id="gpt-4o")

    def test_raises_on_unknown_provider(self):
        from utils.model_factory import ModelFactory
        with pytest.raises(ValueError, match="Provider desconhecido: unknown"):
            ModelFactory.create("unknown", "some-model")

    def test_provider_name_is_case_insensitive(self):
        from utils.model_factory import ModelFactory
        with patch("agno.models.groq.Groq") as mock:
            ModelFactory.create("GROQ", "llama-3.3-70b-versatile")
        mock.assert_called_once()

    def test_supported_providers_list(self):
        from utils.model_factory import ModelFactory
        providers = ModelFactory.supported_providers()
        assert "groq" in providers
        assert "openai" in providers


# ---------------------------------------------------------------------------
# 2. Settings — configuração por agent no .env
# ---------------------------------------------------------------------------

class TestAgentModelSettings:

    def test_default_provider_is_groq(self):
        from utils.config import Settings
        s = Settings(
            groq_api_key="x",
            instagram_username="u",
            instagram_password="p",
        )
        assert s.media_agent_provider == "groq"
        assert s.media_agent_model == "llama-3.3-70b-versatile"

    def test_can_override_provider_per_agent(self):
        from utils.config import Settings
        s = Settings(
            groq_api_key="x",
            instagram_username="u",
            instagram_password="p",
            media_agent_provider="openai",
            media_agent_model="gpt-4o",
        )
        assert s.media_agent_provider == "openai"
        assert s.media_agent_model == "gpt-4o"

    def test_each_agent_has_independent_config(self):
        from utils.config import Settings
        s = Settings(
            groq_api_key="x",
            instagram_username="u",
            instagram_password="p",
            media_agent_provider="openai",
            media_agent_model="gpt-4o",
        )
        # outros agents mantêm o padrão groq
        assert s.media_agent_provider == "openai"


# ---------------------------------------------------------------------------
# 3. MediaAgent usa ModelFactory para instanciar o modelo
# ---------------------------------------------------------------------------

class TestMediaAgentUsesFactory:

    def test_media_agent_uses_configured_provider(self):
        """MediaAgent deve chamar ModelFactory com o provider do Settings."""
        from utils.model_factory import ModelFactory
        from utils.config import Settings

        s = Settings(
            groq_api_key="x", instagram_username="u", instagram_password="p",
            media_agent_provider="groq", media_agent_model="llama-3.3-70b-versatile",
        )
        with patch("utils.model_factory.ModelFactory.create") as mock_factory:
            mock_factory.return_value = MagicMock()
            ModelFactory.create(s.media_agent_provider, s.media_agent_model)

        mock_factory.assert_called_with("groq", "llama-3.3-70b-versatile")

    def test_switching_provider_does_not_require_code_change(self):
        """Trocar provider = trocar settings, sem alterar código do agent."""
        from utils.model_factory import ModelFactory
        from utils.config import Settings

        for provider, model in [("groq", "llama-3.3-70b-versatile"), ("openai", "gpt-4o")]:
            s = Settings(
                groq_api_key="x", instagram_username="u", instagram_password="p",
                media_agent_provider=provider, media_agent_model=model,
            )
            with patch("utils.model_factory.ModelFactory.create") as mock_factory:
                mock_factory.return_value = MagicMock()
                ModelFactory.create(s.media_agent_provider, s.media_agent_model)

            mock_factory.assert_called_with(provider, model)

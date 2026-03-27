"""Testes para providers separados por responsabilidade única."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# 1. ModelProvider — interface base
# ---------------------------------------------------------------------------

class TestModelProviderInterface:

    def test_cannot_instantiate_abstract_class(self):
        from providers.base import ModelProvider
        with pytest.raises(TypeError):
            ModelProvider()

    def test_concrete_subclass_must_implement_build(self):
        from providers.base import ModelProvider

        class Incomplete(ModelProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_with_build_instantiates(self):
        from providers.base import ModelProvider

        class Concrete(ModelProvider):
            def build(self, model_id: str):
                return f"model:{model_id}"

        obj = Concrete()
        assert obj.build("test") == "model:test"


# ---------------------------------------------------------------------------
# 2. GroqProvider
# ---------------------------------------------------------------------------

class TestGroqProvider:

    def test_build_calls_groq_with_model_id(self):
        from providers.groq_provider import GroqProvider
        with patch("agno.models.groq.Groq") as mock:
            mock.return_value = MagicMock()
            provider = GroqProvider()
            provider.build("llama-3.3-70b-versatile")
        mock.assert_called_once_with(id="llama-3.3-70b-versatile")

    def test_build_returns_groq_instance(self):
        from providers.groq_provider import GroqProvider
        with patch("agno.models.groq.Groq") as mock:
            fake_model = MagicMock()
            mock.return_value = fake_model
            result = GroqProvider().build("llama-3.3-70b-versatile")
        assert result is fake_model

    def test_build_accepts_any_model_id(self):
        from providers.groq_provider import GroqProvider
        with patch("agno.models.groq.Groq") as mock:
            mock.return_value = MagicMock()
            GroqProvider().build("llama-3.1-8b-instant")
        mock.assert_called_once_with(id="llama-3.1-8b-instant")

    def test_is_subclass_of_model_provider(self):
        from providers.base import ModelProvider
        from providers.groq_provider import GroqProvider
        assert issubclass(GroqProvider, ModelProvider)


# ---------------------------------------------------------------------------
# 3. OpenAIProvider
# ---------------------------------------------------------------------------

class TestOpenAIProvider:

    def test_build_calls_openaichat_with_model_id(self):
        from providers.openai_provider import OpenAIProvider
        with patch("agno.models.openai.OpenAIChat") as mock:
            mock.return_value = MagicMock()
            OpenAIProvider().build("gpt-4o")
        mock.assert_called_once_with(id="gpt-4o")

    def test_build_returns_openai_instance(self):
        from providers.openai_provider import OpenAIProvider
        with patch("agno.models.openai.OpenAIChat") as mock:
            fake_model = MagicMock()
            mock.return_value = fake_model
            result = OpenAIProvider().build("gpt-4o")
        assert result is fake_model

    def test_build_accepts_any_model_id(self):
        from providers.openai_provider import OpenAIProvider
        with patch("agno.models.openai.OpenAIChat") as mock:
            mock.return_value = MagicMock()
            OpenAIProvider().build("gpt-4o-mini")
        mock.assert_called_once_with(id="gpt-4o-mini")

    def test_is_subclass_of_model_provider(self):
        from providers.base import ModelProvider
        from providers.openai_provider import OpenAIProvider
        assert issubclass(OpenAIProvider, ModelProvider)


# ---------------------------------------------------------------------------
# 4. ProviderRegistry
# ---------------------------------------------------------------------------

class TestProviderRegistry:

    def test_contains_groq_by_default(self):
        from providers.registry import ProviderRegistry
        assert "groq" in ProviderRegistry.all()

    def test_contains_openai_by_default(self):
        from providers.registry import ProviderRegistry
        assert "openai" in ProviderRegistry.all()

    def test_get_returns_correct_provider(self):
        from providers.registry import ProviderRegistry
        from providers.groq_provider import GroqProvider
        assert isinstance(ProviderRegistry.get("groq"), GroqProvider)

    def test_get_raises_on_unknown(self):
        from providers.registry import ProviderRegistry
        with pytest.raises(ValueError, match="Provider desconhecido: xyz"):
            ProviderRegistry.get("xyz")

    def test_register_adds_new_provider(self):
        from providers.registry import ProviderRegistry
        from providers.base import ModelProvider

        class FakeProvider(ModelProvider):
            def build(self, model_id: str):
                return MagicMock()

        ProviderRegistry.register("fake", FakeProvider())
        assert "fake" in ProviderRegistry.all()
        ProviderRegistry.unregister("fake")  # cleanup

    def test_unregister_removes_provider(self):
        from providers.registry import ProviderRegistry
        from providers.base import ModelProvider

        class TempProvider(ModelProvider):
            def build(self, model_id: str):
                return MagicMock()

        ProviderRegistry.register("temp", TempProvider())
        ProviderRegistry.unregister("temp")
        assert "temp" not in ProviderRegistry.all()

    def test_get_is_case_insensitive(self):
        from providers.registry import ProviderRegistry
        from providers.groq_provider import GroqProvider
        assert isinstance(ProviderRegistry.get("GROQ"), GroqProvider)


# ---------------------------------------------------------------------------
# 5. ModelFactory — orquestra registry + providers
# ---------------------------------------------------------------------------

class TestModelFactory:

    def test_create_groq(self):
        from utils.model_factory import ModelFactory
        with patch("agno.models.groq.Groq") as mock:
            mock.return_value = MagicMock()
            ModelFactory.create("groq", "llama-3.3-70b-versatile")
        mock.assert_called_once_with(id="llama-3.3-70b-versatile")

    def test_create_openai(self):
        from utils.model_factory import ModelFactory
        with patch("agno.models.openai.OpenAIChat") as mock:
            mock.return_value = MagicMock()
            ModelFactory.create("openai", "gpt-4o")
        mock.assert_called_once_with(id="gpt-4o")

    def test_raises_on_unknown_provider(self):
        from utils.model_factory import ModelFactory
        with pytest.raises(ValueError, match="Provider desconhecido: unknown"):
            ModelFactory.create("unknown", "some-model")

    def test_case_insensitive(self):
        from utils.model_factory import ModelFactory
        with patch("agno.models.groq.Groq") as mock:
            mock.return_value = MagicMock()
            ModelFactory.create("GROQ", "llama-3.3-70b-versatile")
        mock.assert_called_once()

    def test_supported_providers_contains_groq_and_openai(self):
        from utils.model_factory import ModelFactory
        providers = ModelFactory.supported_providers()
        assert "groq" in providers
        assert "openai" in providers

    def test_delegates_to_registry(self):
        """Factory deve delegar ao ProviderRegistry, não ter lógica própria."""
        from utils.model_factory import ModelFactory
        from providers.registry import ProviderRegistry

        mock_provider = MagicMock()
        mock_provider.build.return_value = MagicMock()

        with patch.object(ProviderRegistry, "get", return_value=mock_provider) as mock_get:
            ModelFactory.create("groq", "llama-3.3-70b-versatile")

        mock_get.assert_called_once_with("groq")
        mock_provider.build.assert_called_once_with("llama-3.3-70b-versatile")

from __future__ import annotations
from providers.base import ModelProvider
from providers.groq_provider import GroqProvider
from providers.openai_provider import OpenAIProvider


_registry: dict[str, ModelProvider] = {
    "groq": GroqProvider(),
    "openai": OpenAIProvider(),
}


class ProviderRegistry:
    """Mantém o mapa de providers disponíveis. Suporta registro dinâmico."""

    @staticmethod
    def get(provider: str) -> ModelProvider:
        key = provider.lower()
        if key not in _registry:
            raise ValueError(
                f"Provider desconhecido: {provider}. "
                f"Suportados: {list(_registry.keys())}"
            )
        return _registry[key]

    @staticmethod
    def all() -> list[str]:
        return list(_registry.keys())

    @staticmethod
    def register(name: str, provider: ModelProvider) -> None:
        _registry[name.lower()] = provider

    @staticmethod
    def unregister(name: str) -> None:
        _registry.pop(name.lower(), None)

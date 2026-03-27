from __future__ import annotations
from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """Interface Strategy — cada provedor implementa build()."""

    @abstractmethod
    def build(self, model_id: str):
        ...


class GroqProvider(ModelProvider):
    def build(self, model_id: str):
        from agno.models.groq import Groq
        return Groq(id=model_id)


class OpenAIProvider(ModelProvider):
    def build(self, model_id: str):
        from agno.models.openai import OpenAIChat
        return OpenAIChat(id=model_id)


_PROVIDERS: dict[str, ModelProvider] = {
    "groq": GroqProvider(),
    "openai": OpenAIProvider(),
}


class ModelFactory:
    """Factory — cria o modelo correto dado provider + model_id."""

    @staticmethod
    def create(provider: str, model_id: str):
        key = provider.lower()
        if key not in _PROVIDERS:
            raise ValueError(
                f"Provider desconhecido: {provider}. "
                f"Suportados: {list(_PROVIDERS.keys())}"
            )
        return _PROVIDERS[key].build(model_id)

    @staticmethod
    def supported_providers() -> list[str]:
        return list(_PROVIDERS.keys())

from __future__ import annotations
from providers.registry import ProviderRegistry


class ModelFactory:
    """Cria o modelo correto delegando ao ProviderRegistry."""

    @staticmethod
    def create(provider: str, model_id: str):
        return ProviderRegistry.get(provider).build(model_id)

    @staticmethod
    def supported_providers() -> list[str]:
        return ProviderRegistry.all()

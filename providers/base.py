from __future__ import annotations
from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """Contrato que todo provider de LLM deve implementar."""

    @abstractmethod
    def build(self, model_id: str):
        ...

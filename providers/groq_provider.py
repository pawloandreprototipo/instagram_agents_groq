from __future__ import annotations
from providers.base import ModelProvider


class GroqProvider(ModelProvider):
    def build(self, model_id: str):
        from agno.models.groq import Groq
        return Groq(id=model_id)

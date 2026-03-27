from __future__ import annotations
from providers.base import ModelProvider


class OpenAIProvider(ModelProvider):
    def build(self, model_id: str):
        from agno.models.openai import OpenAIChat
        return OpenAIChat(id=model_id)

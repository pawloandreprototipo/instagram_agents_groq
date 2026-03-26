from __future__ import annotations
from abc import ABC, abstractmethod
from agno.agent import Agent


class BaseInstagramAgent(ABC):
    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    @abstractmethod
    def run(self, **kwargs) -> str:
        ...

    @property
    def agent(self) -> Agent:
        return self._agent

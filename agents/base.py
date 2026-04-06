"""Base class for all agents."""

import asyncio
from abc import ABC, abstractmethod

from llm.base import BaseLLMProvider


class BaseAgent(ABC):
    def __init__(self, provider: BaseLLMProvider) -> None:
        self._provider = provider

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    async def run(self, query: str) -> str:
        return await asyncio.to_thread(self._provider.chat, query, system_prompt=self.system_prompt)

"""Base class for all agents."""

import asyncio
from abc import ABC, abstractmethod

from llm.base import BaseLLMProvider


class BaseAgent(ABC):
    def __init__(self, provider: BaseLLMProvider, *, timeout_seconds: int = 60) -> None:
        self._provider = provider
        self.timeout_seconds = timeout_seconds

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    async def run(self, query: str) -> str:
        return await asyncio.wait_for(
            asyncio.to_thread(self._provider.chat, query, system_prompt=self.system_prompt),
            timeout=self.timeout_seconds,
        )

"""Shared application context for Discord bot and API server."""

from dataclasses import dataclass

from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from agents.writer_agent import WriterAgent
from config import Settings
from orchestrator.supervisor import Supervisor
from services.router import get_llm_provider
from storage.conversations import ConversationStore
from storage.history import HistoryStore


@dataclass
class AppContext:
    settings: Settings
    supervisor: Supervisor
    store: HistoryStore
    conversations: ConversationStore


def create_app_context(settings: Settings) -> AppContext:
    """Wire up provider, agents, supervisor, and stores."""
    provider = get_llm_provider(settings)
    timeout = settings.ollama_timeout_seconds

    supervisor = Supervisor(
        research_agent=ResearchAgent(provider, timeout_seconds=timeout),
        analyst_agent=AnalystAgent(provider, timeout_seconds=timeout),
        writer_agent=WriterAgent(provider, timeout_seconds=timeout),
        provider=provider,
    )

    store = HistoryStore(
        settings.history_db_path,
        max_records=settings.max_history_records,
        max_size_mb=settings.max_history_size_mb,
    )
    conversations = ConversationStore(settings.conversations_db_path)

    return AppContext(
        settings=settings,
        supervisor=supervisor,
        store=store,
        conversations=conversations,
    )

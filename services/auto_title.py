"""Auto-generate conversation titles from early exchanges."""

import asyncio
import logging

from llm.base import BaseLLMProvider
from storage.conversations import ConversationStore

LOGGER = logging.getLogger(__name__)

_TRIGGER_MESSAGE_COUNT = 2  # 1 user + 1 assistant
_MAX_TITLE_LENGTH = 40

_PROMPT = (
    "다음 대화를 한국어로 8단어 이내의 짧은 제목으로 요약해라. "
    "설명이나 따옴표 없이 제목만 출력한다.\n\n"
    "{snippet}"
)


async def maybe_generate_title(
    store: ConversationStore,
    provider: BaseLLMProvider,
    conversation_id: int,
) -> None:
    """Generate title if conversation has reached trigger and no manual title set."""
    conv = store.get(conversation_id)
    if conv is None or conv.title_locked or conv.title is not None:
        return

    count = store.count_messages(conversation_id)
    if count < _TRIGGER_MESSAGE_COUNT:
        return

    messages = store.list_messages(conversation_id, limit=_TRIGGER_MESSAGE_COUNT)
    snippet = "\n".join(
        f"{'사용자' if m.role == 'user' else '어시스턴트'}: {m.content[:200]}" for m in messages
    )

    try:
        title = await asyncio.to_thread(provider.chat, _PROMPT.format(snippet=snippet))
    except Exception:
        LOGGER.exception("Auto-title generation failed for conversation %d", conversation_id)
        return

    title = title.strip().strip('"').strip("'")
    if not title:
        return
    if len(title) > _MAX_TITLE_LENGTH:
        title = title[:_MAX_TITLE_LENGTH].rstrip()
    store.rename(conversation_id, title, locked=False)
    LOGGER.info("Auto-titled conversation %d: %s", conversation_id, title)

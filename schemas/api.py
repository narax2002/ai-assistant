"""Pydantic models for the FastAPI server."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    provider: str = "auto"
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    response: str
    provider_requested: str
    provider_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ConversationCreate(BaseModel):
    platform: str = "api"
    title: str | None = None
    session_id: str | None = None


class ConversationRename(BaseModel):
    title: str


class ConversationOut(BaseModel):
    id: int
    session_id: str
    title: str | None
    title_locked: bool
    platform: str
    created_at: str
    updated_at: str


class ConversationMessageOut(BaseModel):
    id: int
    role: str
    content: str
    provider_used: str | None
    created_at: str


class ConversationDetail(ConversationOut):
    messages: list[ConversationMessageOut]


class ConversationChatRequest(BaseModel):
    message: str
    provider: str = "auto"
    system_prompt: str | None = None


class ConversationChatResponse(BaseModel):
    response: str
    provider_requested: str
    provider_used: str
    conversation_id: int
    message_id: int


class ResearchAPIRequest(BaseModel):
    query: str


class FollowupAPIRequest(BaseModel):
    question: str
    request_id: str | None = None


class ResearchAPIResponse(BaseModel):
    request_id: str
    summary: str
    comparison: str
    next_actions: str
    sources: str
    total_elapsed_seconds: float
    total_tokens: int


class ProviderStatus(BaseModel):
    name: str
    type: str
    model: str

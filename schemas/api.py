"""Pydantic models for the FastAPI server."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    provider: str = "auto"
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    response: str
    provider_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


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

"""Pydantic schemas for OpenAI-compatible Chat Completions API."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["system", "user", "assistant", "function", "tool"] = "user"
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    reasoning: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(
        default="free-auto",
        description="Model name or virtual alias (e.g. free-auto, free-fast)",
    )
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    temperature: float | None = 0.7
    top_p: float | None = 1.0
    n: int | None = 1
    stream: bool = False
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    presence_penalty: float | None = 0.0
    frequency_penalty: float | None = 0.0
    stop: list[str] | str | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int | None = None


class ChoiceMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: str = "assistant"
    content: str | list[dict[str, Any]] | None = None
    reasoning: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class Choice(BaseModel):
    index: int = 0
    message: ChoiceMessage
    finish_reason: str | None = "stop"


class ChatCompletionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: UsageInfo | None = None

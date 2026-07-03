from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RuntimeChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class RuntimeChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    agent: str = "classifier"
    system_prompt: Optional[str] = None
    context: Optional[dict[str, Any]] = None
    temperature: float = 0.3
    max_tokens: Optional[int] = None


class RuntimePlanRequest(BaseModel):
    task: str = Field(..., min_length=1)
    current_os: str = "unknown"
    current_interactive_elements: list[dict[str, Any]] = []
    current_running_apps: list[dict[str, Any]] = []

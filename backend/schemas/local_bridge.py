from typing import Literal, Optional

from pydantic import BaseModel, Field


class BridgeActionRequest(BaseModel):
    action: Literal[
        "open_app",
        "list_processes",
        "focus_app",
        "click",
        "type_text",
        "hotkey",
        "screenshot",
        "extract_ui",
    ]
    app_name: Optional[str] = Field(default=None, max_length=64)
    x: Optional[int] = None
    y: Optional[int] = None
    clicks: int = 1
    button: str = "left"
    text: Optional[str] = Field(default=None, max_length=4000)
    keys: Optional[list[str]] = None


class BridgeActionResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None


class BridgeInboxMessageRequest(BaseModel):
    text: str = Field(max_length=4000)
    source: str = Field(default="external", max_length=80)
    mode: Literal["ask", "puter", "computer"] = "ask"
    auto_execute: bool = False


class BridgeInboxMessage(BaseModel):
    id: int
    source: str
    text: str
    mode: str
    auto_execute: bool
    created_at: float


class InvocationMessage(BaseModel):
    id: str
    channel_id: str
    conversation_id: str
    direction: Literal["in", "out"]
    payload: dict
    status: str
    created_at: float


class InvocationMessageRequest(BaseModel):
    channel_id: str = Field(max_length=80)
    conversation_id: str = Field(max_length=120)
    payload: dict


class InvocationAckRequest(BaseModel):
    status: Literal["done", "failed", "read"] = "done"
    error: Optional[str] = Field(default=None, max_length=1000)


class InvocationTaskRequest(BaseModel):
    channel_id: str = Field(max_length=80)
    conversation_id: str = Field(max_length=120)
    tool_name: str = Field(max_length=120)
    input: dict = Field(default_factory=dict)
    require_confirmation: bool = True


class InvocationTask(BaseModel):
    id: str
    channel_id: str
    conversation_id: str
    tool_name: str
    status: str
    input: Optional[dict] = None
    result: Optional[dict] = None
    created_at: float
    updated_at: float


class InvocationTaskStatusRequest(BaseModel):
    status: Literal[
        "queued",
        "running",
        "waiting_confirmation",
        "succeeded",
        "failed",
        "canceled",
    ]
    result: Optional[dict] = None


class InvocationEventRequest(BaseModel):
    channel_id: str = Field(max_length=80)
    event_type: str = Field(max_length=120)
    payload: dict = Field(default_factory=dict)
    task_id: Optional[str] = Field(default=None, max_length=120)

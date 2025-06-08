from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .mcp import Tool
from datetime import datetime
from enum import Enum, unique
from .agent import WorkMode
from typing_extensions import TypedDict
from langgraph.graph import MessagesState

class UserMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime

class WorkflowRequest(BaseModel):
    user_id: Optional[str]
    data: Optional[str]

class BaseWorkflow(BaseModel):
    workflow_id: str
    mode: WorkMode
    version: int
    lap: int
    user_input_messages: List[UserMessage]
    deep_thinking_mode: bool
    search_before_planning: bool


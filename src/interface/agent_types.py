from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .mcp_types import Tool
from enum import Enum, unique


@unique
class Lang(str, Enum):
    EN = "en"
    ZH = "zh"
    JP = "jp"
    SP = 'sp'
    DE = 'de'

class LLMType(str, Enum):
    BASIC = "basic"
    REASONING = "reasoning"
    VISION = "vision"
  
class TaskType(str, Enum):
    AGENT_FACTORY = "agent_factory"
    AGENT_WORKFLOW = "agent_workflow"
    
class Agent(BaseModel):
    """Definition for an agent the client can call."""
    user_id: str
    """The id of the user."""
    agent_name: str
    """The name of the agent."""
    nick_name: str
    """The id of the agent."""
    description: str
    """The description of the agent."""
    llm_type: LLMType
    """The type of LLM to use for the agent."""
    selected_tools: List[Tool]
    """The tools that the agent can use."""
    prompt: str
    """The prompt to use for the agent."""
    model_config = ConfigDict(extra="allow")

    
class AgentMessage(BaseModel):
    content: str
    role: str
    
class AgentRequest(BaseModel):
    user_id: str
    lang: Lang
    messages: List[AgentMessage]
    debug: bool
    deep_thinking_mode: bool
    search_before_planning: bool
    task_type: TaskType
    
class listAgentRequest(BaseModel):
    user_id: Optional[str]
    match: Optional[str]
    

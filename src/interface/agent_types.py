from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .mcp_types import Tool
from enum import Enum, unique
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


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
    CODE = 'code'


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
    coor_agents: Optional[list[str]]
    
class listAgentRequest(BaseModel):
    user_id: Optional[str]
    match: Optional[str]
    

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: str

class AgentTool(TypedDict):
    name: str
    description: str

class AgentBuilder(TypedDict):
    """
        For building an agent with specified properties and capabilities
    """
    agent_name: str
    agent_description: str
    thought: str
    llm_type: str
    selected_tools: List[AgentTool]
    prompt: str


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""
    TEAM_MEMBERS: list[str]
    TEAM_MEMBERS_DESCRIPTION: str
    user_id: str
    next: str
    full_plan: str
    deep_thinking_mode: bool
    search_before_planning: bool


class RemoveAgentRequest(BaseModel):
    user_id: str
    agent_name: str

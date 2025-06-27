from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .mcp import Tool
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

class Component(BaseModel):
    component_type: str
    label: str
    name: str
    description: str
    config: dict

COORDINATOR = Component(
    component_type="agent",
    label="coordinator",
    name="coordinator",
    description="Coordinator node that communicate with customers.",
    config={
        "type": "system_agent",
        "name": "coordinator",
    }
)


PLANNER = Component(
    component_type="agent",
    label="planner",
    name="planner",
    description="Planner node that plan the task.",
    config={
        "type": "system_agent",
        "name": "planner",
    }
)

PUBLISHER = Component(
    component_type="condtion",
    label="publisher_condition",
    name="publisher",
    description="Publisher node that publish the task.",
    config={
        "type": "system_agent",
        "name": "publisher",
    }
)

AGENT_FACTORY = Component(
    component_type="agent",
    label="system_agent",
    name="agent_factory",
    description="Agent factory node that create the agent.",
    config={
        "type": "system_agent",
        "name": "agent_factory",
    }
)

class TaskType(str, Enum):
    AGENT_FACTORY = "agent_factory"
    AGENT_WORKFLOW = "agent_workflow"

class WorkMode(str, Enum):
    LAUNCH = "launch"
    POLISH = "polish"
    PRODUCTION = "production"
    AUTO = "auto"


    
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
    workmode: WorkMode
    workflow_id: Optional[str] = None

class listAgentRequest(BaseModel):
    user_id: Optional[str]
    match: Optional[str]

class EditStepsRequest(BaseModel):
    workflow_id: str
    planning_steps: dict

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: str


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""
    TEAM_MEMBERS: list[str]
    TEAM_MEMBERS_DESCRIPTION: str
    user_id: str
    next: str
    full_plan: str
    deep_thinking_mode: bool
    search_before_planning: bool
    workflow_id: str
    workflow_mode: WorkMode="auto"
    initialized: bool=False

class RemoveAgentRequest(BaseModel):
    user_id: str
    agent_name: str
